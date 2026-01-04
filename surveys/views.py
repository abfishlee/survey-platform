import json
import csv
import io
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from .models import (
    SurveyMaster, SurveyDesign, SurveyData, SurveyRoster, 
    SurveyQuestionnaire, QuestionnaireVersion, SurveyArea, SurveyAreaUser, SurveyAnalysis,
    SurveyDegree
    )
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from .superset_utils import execute_superset_sql


# ==========================================
# [공통 유틸리티] 권한 체크 및 보조 함수
# ==========================================

def is_admin(user):
    """사용자가 관리자(슈퍼유저 또는 Manager 그룹)인지 확인"""
    return user.is_superuser or user.groups.filter(name='Manager').exists()

def get_all_child_area_ids(area):
    """
    특정 권역과 그 하부의 모든 권역 ID를 리스트로 반환 (재귀 호출)
    A00을 넣으면 A01, A02, A11, A21... 등 모든 하위 ID를 반환합니다.
    """
    ids = [area.id]
    # 모델 정의 시 related_name='children'을 사용했으므로 바로 접근 가능
    for child in area.children.all():
        ids.extend(get_all_child_area_ids(child))
    return ids

# surveys/views.py 에 잠시 추가
def clear_roster_data(request, roster_id):
    from .models import SurveyData
    count = SurveyData.objects.filter(roster_id=roster_id).count()
    SurveyData.objects.filter(roster_id=roster_id).delete()
    return HttpResponse(f"{count}건의 데이터가 삭제되었습니다. 이제 다시 업로드하세요.")

@user_passes_test(is_admin)
def reset_all_survey_data(request, survey_id):  # survey_id 인자를 추가했습니다.
    """
    survey_id가 0이면 시스템 내의 모든 조사 데이터를 초기화합니다.
    그 외의 번호면 해당 조사만 삭제합니다.
    SurveyMaster 삭제 시 CASCADE 설정에 의해 관련 데이터(Degree, Roster, Data 등)가 함께 삭제됩니다.
    """
    if request.method == 'POST':
        with transaction.atomic():
            if str(survey_id) == '0':
                # 모든 조사 삭제
                count = SurveyMaster.objects.all().count()
                SurveyMaster.objects.all().delete()
                message = f"전체 초기화 성공: {count}건의 모든 조사 프로젝트가 삭제되었습니다."
            else:
                # 특정 조사 하나만 삭제
                survey = get_object_or_404(SurveyMaster, pk=survey_id)
                survey_name = survey.survey_name
                survey.delete()
                message = f"삭제 성공: 조사 '{survey_name}'(ID: {survey_id})와 관련 데이터가 삭제되었습니다."
            
        return HttpResponse(message)
    
    # GET 요청 시 확인 페이지 렌더링
    return render(request, 'surveys/confirm_reset.html', {'survey_id': survey_id})

def get_current_degree(survey):
    return survey.degrees.filter(is_active=True).first()

def check_survey_manager_permission(user, survey):
    """
    슈퍼유저는 무조건 통과.
    일반 유저는 해당 SurveyMaster의 managers에 포함되어 있어야 통과.
    """
    if user.is_superuser:
        return True
    return survey.managers.filter(id=user.id).exists()

# ==========================================
# [메인/목록] 대시보드 및 프로젝트 관리
# ==========================================

@login_required
def dashboard(request):
    """메인 대시보드 화면"""
    return render(request, 'dashboard.html', {'is_admin': is_admin(request.user)})

@user_passes_test(is_admin)
def design_list(request):
    """통계 설계 목록 조회"""
    user = request.user

    if user.is_superuser:
        # 슈퍼유저는 전체 조회 + 정렬
        surveys = SurveyMaster.objects.all().order_by('survey_code')
    else:
        # 일반 매니저는 자신이 배정된 조사만 필터링 + 정렬
        surveys = SurveyMaster.objects.filter(managers=user).order_by('survey_code')
    return render(request, 'surveys/design_list.html', {'surveys': surveys})


# ==========================================
# [1단계: 항목 설계] 명부 및 조사표 기본 필드 정의
# ==========================================

@user_passes_test(is_admin)
def survey_field_design(request, survey_id):
    """명부 항목 및 조사표 문항의 기초 풀(Pool) 설계"""
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design, created = SurveyDesign.objects.get_or_create(survey=survey)

    if not any(item.get('id') == 'area_code' for item in design.list_schema):
        design.list_schema.insert(0, {
            'id': 'area_code', 
            'label': '권역코드', 
            'type': 'text', 
            'is_system': True  # 시스템 필수 항목 표시
        })
        design.save()

    if request.method == 'POST':
        data = json.loads(request.body)
        design.list_schema = data.get('list_schema', [])
        design.survey_schema = data.get('survey_schema', [])
        design.save()
        return JsonResponse({'status': 'success'})
    return render(request, 'surveys/field_design.html', {
        'survey': survey, 
        'list_fields': design.list_schema, 
        'survey_questions': design.survey_schema,
    })

# ==========================================
# [2단계: 명부 설계] 명부 생성 및 필터/목록 맵핑
# ==========================================
@user_passes_test(is_admin)
def survey_roster_design(request, survey_id):
    """조사 명부(Roster) 생성 및 관리"""
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = get_object_or_404(SurveyDesign, survey=survey)
    if request.method == 'POST':
        data = json.loads(request.body)
        last_roster = SurveyRoster.objects.all().order_by('id').last()
        next_num = int(last_roster.roster_code[1:]) + 1 if last_roster and last_roster.roster_code else 1
        SurveyRoster.objects.create(
            survey=survey, roster_code=f"N{next_num:05d}", roster_name=data.get('roster_name'),
            parent_roster_id=data.get('parent_id') or None
        )
        return JsonResponse({'status': 'success'})
    return render(request, 'surveys/roster_design.html', {
        'survey': survey, 'item_pool': design.list_schema, 'rosters': survey.rosters.all(),
    })

@user_passes_test(is_admin)
def get_roster_config(request, roster_id):
    """명부의 맵핑 설정(목록 노출 여부 등) 조회"""
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    return JsonResponse({'mapping_config': roster.mapping_config})

@user_passes_test(is_admin)
def save_roster_config(request, roster_id):
    """명부의 맵핑 설정 저장"""
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    if request.method == 'POST':
        roster.mapping_config = json.loads(request.body).get('mapping_config', [])
        roster.save()
        return JsonResponse({'status': 'success'})

@user_passes_test(is_admin)
def download_roster_template(request, survey_id):
    """명부 양식 다운로드"""
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = getattr(survey, 'design', None)
    if not design: return HttpResponse("설계 정보가 없습니다.", status=404)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="template_{survey.survey_code}.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow([item['label'] for item in design.list_schema])
    return response

@user_passes_test(is_admin)
def import_roster_csv(request, survey_id):
    """명부 데이터(CSV) 업로드"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        survey = get_object_or_404(SurveyMaster, pk=survey_id)
        design = get_object_or_404(SurveyDesign, survey=survey)
        roster = survey.rosters.first()
        
        if not roster: 
            return JsonResponse({'status': 'error', 'message': '명부를 먼저 등록하세요.'}, status=400)
        
        try:
            with transaction.atomic(): # 대량 입력을 위한 트랜잭션 처리
                # 최신 레코드 ID 조회 및 숫자 추출
                last_record = SurveyData.objects.all().order_by('id').last()
                if last_record and last_record.respondent_id.isdigit():
                    next_rec_num = int(last_record.respondent_id) + 1
                else:
                    next_rec_num = 1
                
                decoded_file = request.FILES['csv_file'].read().decode('utf-8-sig').splitlines()
                reader = csv.DictReader(decoded_file)
                
                for row in reader:
                    # CSV의 '권역코드' 컬럼과 조사 내 권역 매칭
                    area_val = row.get('권역코드')
                    area_obj = SurveyArea.objects.filter(survey=survey, area_code=area_val).first()
                    
                    # 명부 항목 설계에 따른 데이터 매핑
                    list_values = {item['id']: row.get(item['label'], '') for item in design.list_schema}
                    
                    SurveyData.objects.create(
                        roster=roster,
                        area=area_obj, 
                        respondent_id=f"{next_rec_num:08d}",
                        list_values=list_values,
                        status='READY'          
                    )
                    next_rec_num += 1
                    
            return JsonResponse({'status': 'success', 'message': '임포트가 완료되었습니다.'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'오류 발생: {str(e)}'}, status=500)
            
    return JsonResponse({'status': 'error', 'message': '잘못된 요청'}, status=400)

# ==========================================
# [3단계: 조사표 설계] 조사표 생성 및 버전 관리
# ==========================================

@user_passes_test(is_admin)
def survey_questionnaire_design(request, survey_id):
    """조사표(Questionnaire) 생성 관리"""
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = get_object_or_404(SurveyDesign, survey=survey)
    if request.method == 'POST':
        data = json.loads(request.body)
        last_form = SurveyQuestionnaire.objects.all().order_by('id').last()
        next_num = int(last_form.form_id[1:]) + 1 if last_form and last_form.form_id.startswith('S') else 1
        SurveyQuestionnaire.objects.create(
            roster_id=data.get('roster_id'), form_id=f"S{next_num:05d}", form_name=data.get('form_name')
        )
        return JsonResponse({'status': 'success'})
    return render(request, 'surveys/questionnaire_design.html', {
        'survey': survey, 'rosters': survey.rosters.all(), 'item_pool': design.survey_schema
    })

@user_passes_test(is_admin)
def get_questionnaire_versions(request, q_id):
    """특정 조사표의 전체 버전 목록 조회"""
    versions = QuestionnaireVersion.objects.filter(questionnaire_id=q_id).order_by('-version_number')
    data = [{
        'id': v.id, 'version_number': v.version_number,
        'created_at': v.created_at.strftime('%Y-%m-%d %H:%M'),
        'item_count': len(v.design_data), 'is_confirmed': v.is_confirmed,
        'design_data': v.design_data
    } for v in versions]
    return JsonResponse(data, safe=False)


@user_passes_test(is_admin) # [수정] 관리자 권한 체크 추가
def save_questionnaire_design(request, q_id):
    """
    Vue 작업대 설계 데이터를 SurveyQuestionnaire 및 QuestionnaireVersion 모델에 저장함.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            design_items = data.get('design_data', [])
            # 프론트에서 보낸 현재 버전 ID (수정 시 사용)
            version_id = data.get('version_id') 
            is_new_version = data.get('is_new_version', False)

            questionnaire = get_object_or_404(SurveyQuestionnaire, id=q_id)

            with transaction.atomic():
                if is_new_version or not version_id:
                    # [신규 버전 저장 로직]
                    last_version = QuestionnaireVersion.objects.filter(
                        questionnaire=questionnaire
                    ).order_by('-version_number').first()
                    
                    new_version_num = (last_version.version_number + 1) if last_version else 1
                    
                    version_obj = QuestionnaireVersion.objects.create(
                        questionnaire=questionnaire,
                        version_number=new_version_num,
                        design_data=design_items,
                        item_count=len(design_items),
                        is_confirmed=False
                    )
                    msg = f"새로운 버전 V{new_version_num}이(가) 저장되었습니다."
                else:
                    # [기존 버전 덮어쓰기 로직]
                    version_obj = get_object_or_404(QuestionnaireVersion, id=version_id)
                    
                    if version_obj.is_confirmed:
                        return JsonResponse({'status': 'error', 'message': '확정된 버전은 수정할 수 없습니다. 신규 버전으로 저장하세요.'}, status=400)
                    
                    version_obj.design_data = design_items
                    version_obj.item_count = len(design_items)
                    version_obj.save()
                    msg = f"버전 V{version_obj.version_number}의 수정사항이 저장되었습니다."

            return JsonResponse({
                'status': 'success',
                'version_id': version_obj.id,
                'version_number': version_obj.version_number,
                'message': msg
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)

@user_passes_test(is_admin)
def confirm_questionnaire_version(request, v_id):
    """특정 조사표 버전을 최종 확정(실제 수집에 사용)"""
    target = get_object_or_404(QuestionnaireVersion, pk=v_id)
    QuestionnaireVersion.objects.filter(questionnaire=target.questionnaire).update(is_confirmed=False)
    target.is_confirmed = True
    target.save()
    return JsonResponse({'status': 'success'})

@user_passes_test(is_admin)
def delete_questionnaire(request, q_id):
    """조사표 삭제"""
    questionnaire = get_object_or_404(SurveyQuestionnaire, pk=q_id)
    questionnaire.delete() # Cascade 설정으로 인해 버전들도 함께 삭제됨
    return JsonResponse({'status': 'success', 'message': '조사표와 모든 버전이 삭제되었습니다.'})

# ==========================================
# [4단계: 권역/업무 배정] 조직도 및 조사원 할당
# ==========================================
@user_passes_test(is_admin)
def survey_area_design(request, survey_id):
    """조사별 권역 트리(본청-지방청-사무소) 설계 및 저장"""
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                areas_data = data.get('areas', [])
                
                # 기존 권역 정보 초기화 (재설계 시)
                SurveyArea.objects.filter(survey=survey).delete()
                
                # 트리 구조 저장을 위한 매핑 (임시 ID -> 실제 DB ID)
                id_map = {}
                
                # 레벨 순서대로 저장하기 위해 정렬 필요 (또는 프론트에서 트리 순서대로 전송)
                for item in areas_data:
                    parent_obj = id_map.get(item.get('parent_temp_id'))
                    
                    area = SurveyArea.objects.create(
                        survey=survey,
                        parent=parent_obj,
                        area_code=item.get('code'),
                        area_name=item.get('name'),
                        level=item.get('level')
                    )
                    # 프론트엔드에서 준 임시 ID를 키로 실제 생성된 객체 저장
                    id_map[item.get('temp_id')] = area
                
                return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # 기존 등록된 권역 정보 조회
    areas = survey.areas.all().order_by('level', 'area_code')
    return render(request, 'surveys/area_design.html', {
        'survey': survey,
        'areas': areas
    })

@user_passes_test(is_admin)
def assign_records(request):
    """[탭 2 전용] 명부 레코드 일괄 배정 처리 API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            record_ids = data.get('record_ids', [])

            if not user_id: # 배정 취소
                SurveyData.objects.filter(id__in=record_ids).update(assigned_user=None)
            else:
                target_user = get_object_or_404(User, pk=user_id)
                SurveyData.objects.filter(id__in=record_ids).update(assigned_user=target_user)
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)

def survey_assignment(request, survey_id):
    """
    [4단계: 업무량 배정] 통합 뷰
    """
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    user = request.user

    # 1. 접속한 관리자의 권할 권역 파악
    admin_mapping = SurveyAreaUser.objects.filter(survey=survey, user=user).select_related('area').first()
    
    if not user.is_superuser and not admin_mapping:
        return HttpResponse("권역 관리 권한이 없습니다.", status=403)

    # 2. 관리 범위(하위 권역) 결정
    if user.is_superuser:
        managed_areas = SurveyArea.objects.filter(survey=survey)
    else:
        managed_areas = SurveyArea.objects.filter(
            survey=survey, 
            area_code__startswith=admin_mapping.area.area_code
        )
    
    managed_area_ids = managed_areas.values_list('id', flat=True)

    # ---------------------------------------------------------
    # [POST] 탭 1: 사용자별 권역 배정 저장 (드래그 앤 드롭)
    # ---------------------------------------------------------
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            target_user_id = data.get('user_id')
            target_area_id = data.get('area_id')
            
            target_area = get_object_or_404(SurveyArea, id=target_area_id)
            
            # Lv.1, Lv.2(본청, 지방청)에 배정되면 관리자(is_manager) 권한 자동 부여
            is_manager_role = True if target_area.level < 3 else False

            # 기존 배정 정보가 있다면 업데이트, 없으면 생성
            SurveyAreaUser.objects.update_or_create(
                survey=survey, user_id=target_user_id, area_id=target_area_id,
                defaults={'is_manager': is_manager_role}
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # ---------------------------------------------------------
    # [GET] 화면 렌더링 데이터 준비
    # ---------------------------------------------------------
    
    # [검색/필터 파라미터 수집]
    search_surveyor = request.GET.get('search_surveyor', '').strip()
    assignment_filter = request.GET.get('assignment_filter', 'ALL')

    # 탭 1용: 조사원 풀 및 현재 권역 배정 현황
    all_users = survey.managers.filter(is_active=True)
    area_assignments = SurveyAreaUser.objects.filter(
        survey=survey, 
        area_id__in=managed_area_ids
    ).select_related('user', 'area')

    # 탭 2용: 관리 범위 내 명부 레코드 (필터링 적용)
    data_records = SurveyData.objects.filter(
        roster__survey=survey, 
        area_id__in=managed_area_ids
    ).select_related('area', 'assigned_user').order_by('area__area_code', 'id')

    # 필터 1: 조사원명 검색
    if search_surveyor:
        data_records = data_records.filter(assigned_user__username__icontains=search_surveyor)

    # 필터 2: 배정 상태 필터 (전체/미배정/배정완료)
    if assignment_filter == 'UNASSIGNED':
        data_records = data_records.filter(assigned_user__isnull=True)
    elif assignment_filter == 'ASSIGNED':
        data_records = data_records.filter(assigned_user__isnull=False)

    # 탭 2용: 배정 대상 조사원 목록 (내 관할 권역에 소속된 유저들만)
    sub_surveyors = User.objects.filter(
        assigned_areas__survey=survey,
        assigned_areas__area_id__in=managed_area_ids
    ).exclude(id=user.id).distinct()

    return render(request, 'surveys/assignment.html', {
        'survey': survey,
        'areas': managed_areas.order_by('level', 'area_code'),
        'users': all_users,
        'area_assignments': area_assignments,
        'data_records': data_records,
        'surveyors': sub_surveyors,
        'user_area': admin_mapping.area if admin_mapping else None,
        # 검색 상태 유지를 위해 다시 전달
        'search_surveyor': search_surveyor,
        'assignment_filter': assignment_filter
    }) 

@user_passes_test(is_admin)
def remove_survey_assignment(request, survey_id):
    """배정된 조사원 삭제 API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            area_id = data.get('area_id')
            
            # 해당 조건의 배정 정보 삭제
            SurveyAreaUser.objects.filter(
                survey_id=survey_id, 
                user_id=user_id, 
                area_id=area_id
            ).delete()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)

# ==========================================
# [5단계: 내검규칙] 내검규칙설계
# ==========================================        
@user_passes_test(is_admin)
def survey_edit_rule_design(request, survey_id):
    """내검 규칙 설계"""
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = get_object_or_404(SurveyDesign, survey=survey)
    
    # [수정] 해당 조사(Master) -> 명부(Roster) -> 조사표(Questionnaire)를 모두 가져옵니다.
    questionnaires = SurveyQuestionnaire.objects.filter(roster__survey=survey)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        design.edit_rules = data.get('edit_rules', [])
        design.save()
        return JsonResponse({'status': 'success', 'message': '내검 규칙이 저장되었습니다.'})

    return render(request, 'surveys/edit_rule_design.html', {
        'survey': survey,
        'edit_rules': design.edit_rules,
        'item_pool': design.survey_schema,
        'questionnaires': questionnaires,  # [반드시 추가]
    })

# ==========================================
# [자료 수집] 실제 조사 수행 및 데이터 입력
# ==========================================
@login_required
def collection_list(request):
    """조사원이 접근 가능한 조사 목록 조회"""
    user = request.user
    
    # 권한 필터링: 슈퍼유저는 전체, 일반 유저는 배정된 조사만
    if user.is_superuser:
        surveys = SurveyMaster.objects.all().order_by('survey_code')
    else:
        surveys = SurveyMaster.objects.filter(managers=user).order_by('survey_code')
        
    return render(request, 'surveys/collection_survey_list.html', {'surveys': surveys})

@login_required
def collection_degree_list(request, survey_id):
    """[화면] 차수 선택 (Survey -> Degrees)"""
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    
    # 보안 체크
    if not check_survey_manager_permission(request.user, survey):
         return HttpResponse("조회 권한이 없습니다.", status=403)

    # 해당 조사의 모든 차수 가져오기
    degrees = survey.degrees.all().order_by('-degree_number')
    
    # 해당 조사의 명부(Roster) 가져오기 (보통 1개지만, 여러 개일 수 있음)
    rosters = survey.rosters.all()

    return render(request, 'surveys/collection_degree_list.html', {
        'survey': survey,
        'degrees': degrees,
        'rosters': rosters
    })

# surveys/views.py

@login_required
def roster_data_view(request, roster_id, degree_id):
    """
    [화면] 명부 리스트 조회 (Master-Detail 구조 적용)
    1. DB에서는 '차수가 없는(Null)' 원본 명부를 가져옵니다.
    2. '현재 차수(degree_id)'에 해당하는 응답 데이터가 있는지 확인하여 상태(status)를 매핑합니다.
    """
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    degree = get_object_or_404(SurveyDegree, pk=degree_id)
    survey = roster.survey
    user = request.user
    
    # 1. 권한 체크 (사용자의 권역 배정 확인)
    mapping = SurveyAreaUser.objects.filter(survey=survey, user=user).select_related('area').first()
    if not user.is_superuser and not mapping:
        return HttpResponse("이 조사에 대한 권역 배정 정보가 없습니다.", status=403)

    # 2. 명부 설계 설정 로드
    config = roster.mapping_config if isinstance(roster.mapping_config, list) else []
    is_area_design_exists = any(c.get('id') == 'area_code' for c in config)

    # 3. [Master] 원본 명부 데이터 가져오기 (degree가 없는 것)
    master_list = SurveyData.objects.filter(
        roster=roster, 
        degree__isnull=True 
    ).select_related('area', 'assigned_user').order_by('id')

    # 4. [Transaction] 현재 차수의 응답 데이터 상태 조회 (최적화)
    #    (현재 차수에 이미 저장된 데이터들의 상태를 딕셔너리로 가져옴)
    response_status_map = {}
    responses = SurveyData.objects.filter(roster=roster, degree=degree).values('respondent_id', 'status')
    for res in responses:
        response_status_map[res['respondent_id']] = res['status']

    # 5. 권역 필터링 (원본 명부 기준)
    if user.is_superuser:
        base_area_code = ""
        user_level = 0
    else:
        base_area_code = mapping.area.area_code
        user_level = mapping.area.level
        master_list = master_list.filter(area__area_code__startswith=base_area_code)
        if not mapping.is_manager:
             master_list = master_list.filter(assigned_user=user)

    # 6. 검색 파라미터 처리 (계층형 권역 검색)
    sel_lv1 = request.GET.get('sel_lv1', '')
    sel_lv2 = request.GET.get('sel_lv2', '')
    sel_lv3 = request.GET.get('sel_lv3', '')

    if sel_lv3: 
        master_list = master_list.filter(area_id=sel_lv3)
    elif sel_lv2: 
        target_area = get_object_or_404(SurveyArea, pk=sel_lv2)
        master_list = master_list.filter(area__area_code__startswith=target_area.area_code)
    elif sel_lv1: 
        target_area = get_object_or_404(SurveyArea, pk=sel_lv1)
        master_list = master_list.filter(area__area_code__startswith=target_area.area_code)

    # 7. 일반 검색 필드 처리 (이름, 주소 등)
    search_fields = [c for c in config if c.get('is_search') and c.get('id') != 'area_code']
    for field in search_fields:
        val = request.GET.get(field['id'])
        if val:
             master_list = master_list.filter(list_values__contains={field['id']: val})

    # 8. [Display Logic] 리스트 데이터 가공 (상태값 주입)
    #    QuerySet은 순회가 시작될 때 평가되므로, Python 리스트로 변환하며 속성 추가
    display_list = []
    for item in master_list:
        # 이 사람의 현재 차수 상태가 있으면 그걸 쓰고, 없으면 'READY'
        # (주의: 템플릿에서는 item.status_display 를 사용해야 함)
        item.status_display = response_status_map.get(item.respondent_id, 'READY')
        display_list.append(item)

    # 9. 콤보박스용 데이터 준비
    all_managed_areas = SurveyArea.objects.filter(survey=survey, area_code__startswith=base_area_code)
    
    context = {
        'roster': roster,
        'survey': survey,
        'degree': degree,  # [중요] 현재 차수 정보 전달
        'headers': [c for c in config if c.get('show_in_list')],
        'search_fields': search_fields,
        'data_list': display_list, # 가공된 리스트 전달
        'user_area': mapping.area if mapping else None,
        'user_level': user_level,
        'is_area_design_exists': is_area_design_exists,
        'lv1_list': all_managed_areas.filter(level=1),
        'lv2_list': all_managed_areas.filter(level=2),
        'lv3_list': all_managed_areas.filter(level=3),
        'sel_lv1': sel_lv1, 'sel_lv2': sel_lv2, 'sel_lv3': sel_lv3,
    }
    return render(request, 'surveys/data_entry_list.html', context)

@login_required
def get_survey_data(request, data_id):
    """
    [API] 입력 팝업용 데이터 조회
    - data_id: 원본 명부(Master)의 ID
    - request.GET['degree_id']: 현재 입력하려는 차수 ID
    - 기능: 원본 명부 정보 + 해당 차수의 기존 답변(있으면) 병합 반환
    """
    # 1. 파라미터 확인 및 원본 데이터 로드
    degree_id = request.GET.get('degree_id')
    if not degree_id:
        return JsonResponse({'status': 'error', 'message': '차수 정보가 누락되었습니다.'}, status=400)

    master_record = get_object_or_404(SurveyData, pk=data_id)
    roster = master_record.roster
    survey_master = roster.survey
    degree = get_object_or_404(SurveyDegree, pk=degree_id)

    # 2. [핵심] 현재 차수에 저장된 데이터가 있는지 확인
    #    (원본 명부와 respondent_id가 같고, degree가 일치하는 데이터)
    response_record = SurveyData.objects.filter(
        roster=roster,
        degree=degree,
        respondent_id=master_record.respondent_id
    ).first()

    # 답변 데이터가 있으면 로드, 없으면 빈 값
    current_values = response_record.survey_values if response_record else {}
    saved_warnings = current_values.get('_warnings', []) if isinstance(current_values, dict) else []

    # 3. 조사표 설계 및 내검 규칙 로드
    design = getattr(survey_master, 'design', None)
    edit_rules = design.edit_rules if design else []
    
    questionnaires = roster.questionnaires.all()
    if not questionnaires.exists():
        return JsonResponse({'status': 'error', 'message': '연결된 조사표가 없습니다.'}, status=404)

    # 4. 조사표별 최신 확정 버전 구성
    survey_forms = []
    for q in questionnaires:
        v = q.versions.filter(is_confirmed=True).order_by('-version_number').first()
        if v:
            # 해당 버전의 저장된 값 추출 (없으면 빈 딕셔너리)
            form_values = current_values.get(v.ver_form_id, {})
            
            survey_forms.append({
                'q_id': q.id,
                'form_id': q.form_id,
                'ver_form_id': v.ver_form_id,
                'form_name': q.form_name,
                'design_data': v.design_data,
                'saved_values': form_values
            })

    if not survey_forms:
        return JsonResponse({'status': 'error', 'message': '확정된 조사표 버전이 없습니다.'}, status=404)

    return JsonResponse({
        'status': 'success',
        'roster_id': roster.roster_code,
        'respondent_id': master_record.respondent_id,
        'survey_year': survey_master.survey_year,
        'survey_degree': degree.degree_number, # 현재 차수
        'degree_title': degree.degree_title,
        'forms': survey_forms,
        'edit_rules': edit_rules,
        'saved_warnings': saved_warnings
    })

def evaluate_edit_rule(condition, answers, design_data_map, target_form_id):
    """
    내검 규칙 조건식을 평가하는 함수
    condition: 조건식 문자열 (예: "{q6}[0][q6_1] == '1'") - originId 사용 가능
    answers: 저장할 답변 데이터 (예: {"S00001-V1": {"q6_1767248816834": [{"q6_1": "2"}]}})
    design_data_map: {form_id: design_data} 맵핑
    target_form_id: 대상 조사표 ID
    """
    import re
    
    # originId -> 실제 ID 매핑 생성
    origin_id_to_real_id = {}
    for form_id, design_data in design_data_map.items():
        for item in design_data:
            if item.get('originId'):
                origin_id_to_real_id[item['originId']] = item.get('id')
    
    # 테이블 열 전체 참조 패턴: {table_id}[*][col] - 모든 행에 대한 검증
    table_column_all_pattern = r'\{(\w+)\}\[\*\]\[(\w+)\]'
    
    def replace_table_column_all(match):
        """열 전체 검증: 모든 행의 해당 열 값들을 리스트로 반환"""
        table_id_or_origin, col_id = match.groups()
        
        
        # originId인 경우 실제 ID로 변환
        actual_table_id = origin_id_to_real_id.get(table_id_or_origin, table_id_or_origin)
        
        # 해당 조사표의 답변 데이터 찾기
        for ver_form_id, form_data in answers.items():
            if form_data.get(actual_table_id) is not None and isinstance(form_data[actual_table_id], list):
                table_data = form_data[actual_table_id]
                # 모든 행의 해당 열 값 추출
                column_values = []
                for row_idx, row in enumerate(table_data):
                    if isinstance(row, dict):
                        val = row.get(col_id, '')
                        column_values.append(f"'{str(val)}'" if val != '' else "''")
                
                if column_values:
                    # 리스트 형태로 반환 (함수에서 사용)
                    result = f"[{', '.join(column_values)}]"
                    return result
        return "[]"
    
    # 테이블 열 전체 참조 치환 (먼저 처리)
    condition = re.sub(table_column_all_pattern, replace_table_column_all, condition)
    
    # 테이블 셀 참조 패턴: {table_id}[row][col] - 특정 셀 검증
    table_cell_pattern = r'\{(\w+)\}\[(\d+)\]\[(\w+)\]'
    
    # 먼저 테이블 셀 참조를 처리
    def replace_table_cell(match):
        table_id_or_origin, row_idx, col_id = match.groups()
        row_idx = int(row_idx)
        
        # originId인 경우 실제 ID로 변환
        actual_table_id = origin_id_to_real_id.get(table_id_or_origin, table_id_or_origin)
        
        # 해당 조사표의 답변 데이터 찾기
        for ver_form_id, form_data in answers.items():
            if form_data.get(actual_table_id) is not None and isinstance(form_data[actual_table_id], list):
                table_data = form_data[actual_table_id]
                if row_idx < len(table_data) and isinstance(table_data[row_idx], dict):
                    cell_value = table_data[row_idx].get(col_id, '')
                    # 문자열로 변환 (비교를 위해)
                    return f"'{str(cell_value)}'" if cell_value != '' else "''"
        return "''"
    
    # 테이블 셀 참조 치환
    condition = re.sub(table_cell_pattern, replace_table_cell, condition)
    
    # 일반 필드 참조 패턴: {field_id} - originId 사용 가능
    def replace_field_ref(match):
        field_id_or_origin = match.group(1)
        # originId인 경우 실제 ID로 변환
        actual_field_id = origin_id_to_real_id.get(field_id_or_origin, field_id_or_origin)
        
        # 해당 조사표의 답변 데이터 찾기
        for ver_form_id, form_data in answers.items():
            if actual_field_id in form_data:
                value = form_data[actual_field_id]
                # 리스트나 딕셔너리는 문자열로 변환하지 않음 (테이블은 이미 처리됨)
                if isinstance(value, (list, dict)):
                    return "''"
                return f"'{str(value)}'" if value != '' else "''"
        return "''"
    
    # 일반 필드 참조 치환
    pattern = r'\{(\w+)\}'
    try:
        evaluated_condition = re.sub(pattern, replace_field_ref, condition)
        
        # 열 전체 검증을 위한 헬퍼 함수 추가
        def all_equal(values, target_value):
            """리스트의 모든 값이 target_value와 같은지 확인"""
            if not isinstance(values, list) or len(values) == 0:
                return False
            target_str = str(target_value).strip("'\"")
            return all(str(v).strip("'\"") if v != "''" else '' == target_str for v in values)
        
        def all_not_empty(values):
            """리스트의 모든 값이 비어있지 않은지 확인"""
            # 디버깅: 값 타입 확인
            
            # 리스트가 아니면 False
            if not isinstance(values, list):
                return False
            
            # 빈 리스트면 False
            if len(values) == 0:
                return False
            
            # 각 값 확인
            for v in values:
                # v는 eval 후 실제 값 (문자열 '' 또는 다른 값)
                # 빈 문자열이거나 None이면 비어있음
                is_empty = (v == '' or v is None or str(v).strip() == '' or v == "''")
                if is_empty:
                    return False
            
            return True
        
        def has_empty(values):
            """리스트에 빈 값이 하나라도 있는지 확인 (all_not_empty의 반대)"""
            
            # 리스트가 아니면 True (비어있다고 간주)
            if not isinstance(values, list):
                return True
            
            # 빈 리스트면 True (비어있다고 간주)
            if len(values) == 0:
                return True
            
            # 각 값 확인 - 하나라도 비어있으면 True
            for v in values:
                is_empty = (v == '' or v is None or str(v).strip() == '' or v == "''")
                if is_empty:
                    return True
            
            return False
        
        def any_equal(values, target_value):
            """리스트의 값 중 하나라도 target_value와 같은지 확인"""
            if not isinstance(values, list) or len(values) == 0:
                return False
            target_str = str(target_value).strip("'\"")
            return any(str(v).strip("'\"") if v != "''" else '' == target_str for v in values)
        
        def _to_number(value):
            """문자열을 숫자로 변환 (실패 시 None)"""
            try:
                val_str = str(value).strip("'\"")
                if val_str == '' or val_str == "''":
                    return None
                # 정수 또는 실수로 변환 시도
                if '.' in val_str:
                    return float(val_str)
                return int(val_str)
            except:
                return None
        
        def all_greater(values, target_value):
            """리스트의 모든 값이 target_value보다 커야 함 (숫자 비교)"""
            if not isinstance(values, list) or len(values) == 0:
                return False
            
            # 빈 값이 하나라도 있으면 False (숫자 비교 불가)
            for idx, v in enumerate(values):
                if v == '' or v is None or str(v).strip() == '' or v == "''":
                    return False
            
            target_num = _to_number(target_value)
            if target_num is None:
                return False
            for idx, v in enumerate(values):
                val_num = _to_number(v)
                if val_num is None or val_num <= target_num:
                    return False
            return True
        
        def all_greater_equal(values, target_value):
            """리스트의 모든 값이 target_value보다 크거나 같아야 함 (숫자 비교)"""
            if not isinstance(values, list) or len(values) == 0:
                return False
            target_num = _to_number(target_value)
            if target_num is None:
                return False
            for v in values:
                val_num = _to_number(v)
                if val_num is None or val_num < target_num:
                    return False
            return True
        
        def all_less(values, target_value):
            """리스트의 모든 값이 target_value보다 작아야 함 (숫자 비교)"""
            if not isinstance(values, list) or len(values) == 0:
                return False
            target_num = _to_number(target_value)
            if target_num is None:
                return False
            for v in values:
                val_num = _to_number(v)
                if val_num is None or val_num >= target_num:
                    return False
            return True
        
        def all_less_equal(values, target_value):
            """리스트의 모든 값이 target_value보다 작거나 같아야 함 (숫자 비교)"""
            if not isinstance(values, list) or len(values) == 0:
                return False
            target_num = _to_number(target_value)
            if target_num is None:
                return False
            for v in values:
                val_num = _to_number(v)
                if val_num is None or val_num > target_num:
                    return False
            return True
        
        
        # 안전한 평가를 위해 제한된 환경에서만 실행
        # 주의: eval 사용은 보안상 위험할 수 있으나, 내부 시스템이므로 허용
        try:
            result = eval(evaluated_condition, {
                "__builtins__": {},
                "all_equal": all_equal,
                "all_not_empty": all_not_empty,
                "has_empty": has_empty,
                "any_equal": any_equal,
                "all_greater": all_greater,
                "all_greater_equal": all_greater_equal,
                "all_less": all_less,
                "all_less_equal": all_less_equal
            }, {})
            
            return bool(result)
        except Exception as eval_error:
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        # 조건식 평가 실패 시 False 반환 (검증 실패로 처리)
        return False

@login_required
def save_survey_response(request, data_id):
    """
    [API] 조사 답변 저장 (내검 규칙 검증 포함)
    - 수정사항: Warning 발생 시 condition, target_field 정보를 누락 없이 저장하도록 개선
    """
    if request.method == 'POST':
        # 1. 파라미터 및 원본 데이터 로드
        degree_id = request.GET.get('degree_id')
        if not degree_id:
             return JsonResponse({'status': 'error', 'message': '차수 정보가 누락되었습니다.'}, status=400)

        master_record = get_object_or_404(SurveyData, pk=data_id)
        degree = get_object_or_404(SurveyDegree, pk=degree_id)
        
        roster = master_record.roster
        survey_master = roster.survey
        design = getattr(survey_master, 'design', None)
        edit_rules = design.edit_rules if design else []
        
        # 2. 클라이언트가 보낸 답변 데이터 파싱
        try:
            request_data = json.loads(request.body)
            answers = request_data.get('answers', {})
            force_save = request_data.get('force_save', False)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': '잘못된 JSON 형식입니다.'}, status=400)

        # 3. 조사표 설계 데이터 맵핑
        questionnaires = roster.questionnaires.all()
        design_data_map = {}
        for q in questionnaires:
            v = q.versions.filter(is_confirmed=True).order_by('-version_number').first()
            if v:
                design_data_map[q.form_id] = v.design_data
        
        # 4. 내검 규칙 검증
        errors = []
        warnings = [] # 여기에 상세 객체를 담습니다.
        
        for rule in edit_rules:
            target_form_id = rule.get('target_form_id', '')
            form_answers = {}
            
            # 대상 조사표 데이터 추출
            if target_form_id:
                for ver_form_id, form_data in answers.items():
                    form_id = ver_form_id.split('-')[0] if '-' in ver_form_id else ver_form_id
                    if form_id == target_form_id or target_form_id in ver_form_id:
                        form_answers[ver_form_id] = form_data
            else:
                form_answers = answers
            
            if not form_answers: continue
            
            condition = rule.get('condition', '')
            if not condition: continue
            
            # 조건식 평가
            condition_result = evaluate_edit_rule(condition, form_answers, design_data_map, target_form_id)
            
            if condition_result:
                # [핵심 수정] 단순 문자열이 아니라, 상세 정보를 담은 딕셔너리 생성
                violation_info = {
                    'rule_id': rule.get('rule_id'),
                    'message': rule.get('message', f"규칙 {rule.get('rule_id')} 위반"),
                    'condition': condition,          # [필수] 이동을 위해 꼭 필요
                    'target_field': rule.get('target_field'), # [필수] 이동을 위해 꼭 필요
                    'severity': rule.get('severity', 'ERROR')
                }

                if violation_info['severity'] == 'ERROR':
                    # 에러는 메시지만 있어도 됨 (저장 불가라 이동 불필요)
                    errors.append(violation_info['message'])
                else:
                    # 경고는 이동 기능이 필요하므로 객체 전체 저장
                    warnings.append(violation_info)
        
        # ERROR 발생 시 저장 중단
        if errors:
            # 경고 메시지만 추출해서 전달
            warning_messages = [w['message'] for w in warnings]
            return JsonResponse({
                'status': 'error',
                'message': '내검 규칙 위반으로 저장할 수 없습니다.',
                'errors': errors,
                'warnings': warning_messages
            }, status=400)
        
        # WARNING 발생 시 확인 요청 (force_save가 없으면)
        if warnings and not force_save:
            # 클라이언트에게 상세 정보(condition 포함)를 그대로 전달
            # 프론트엔드에서는 warnings 배열을 받아서 메시지를 띄움
            warning_messages = [w['message'] for w in warnings]
            return JsonResponse({
                'status': 'warning',
                'warnings': warning_messages,
                'message': '경고가 있습니다. 저장하시겠습니까?'
            }, status=200)
        
        # 5. [핵심] 차수별 데이터 저장 (Get or Create)
        try:
            with transaction.atomic():
                response_record, created = SurveyData.objects.get_or_create(
                    roster=roster,
                    degree=degree,
                    respondent_id=master_record.respondent_id,
                    defaults={
                        'area': master_record.area,
                        'assigned_user': master_record.assigned_user,
                        'list_values': master_record.list_values,
                        'status': 'ING'
                    }
                )
                
                # [수정] WARNING 메타데이터 저장 시에도 condition 정보 포함!
                # 이전에 이 부분이 {'message': ...} 만 저장해서 문제였음
                answers_to_save = dict(answers)
                if warnings:
                    answers_to_save['_warnings'] = warnings # 전체 객체 리스트 저장
                else:
                    # 경고가 없으면 기존 경고 삭제
                    if '_warnings' in answers_to_save:
                        del answers_to_save['_warnings']

                # 데이터 업데이트
                response_record.survey_values = answers_to_save
                response_record.status = 'ING'
                response_record.save()
                
            return JsonResponse({
                'status': 'success',
                # 저장 완료 후에도 이동 기능을 위해 경고 정보를 다시 내려줌
                'warnings': warnings 
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid Method'}, status=405)

# [화면] 7. 자료분석 페이지 (WebDataRocks를 띄울 껍데기)
def collection_analysis_view(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    return render(request, 'surveys/collection_analysis.html', {
        'survey': survey
    })

# [API] 피벗용 JSON 데이터 제공 (WebDataRocks가 이 데이터를 가져감)
def survey_pivot_data_api(request, survey_id):
    # 해당 조사의 모든 데이터 조회 (최적화를 위해 select_related 사용)
    queryset = SurveyData.objects.filter(
        roster__survey_id=survey_id
    ).select_related('area', 'assigned_user', 'roster', 'degree')
    data_list = []
    
    for record in queryset:
        # 기본 정보
        flat_data = {
            "ID": record.respondent_id,
            "차수": f"{record.degree.degree_number}차" if record.degree else "미지정",
            "차수명": record.degree.degree_title if record.degree else "",
            "권역": record.area.area_name if record.area else "미지정",
            "조사원": record.assigned_user.username if record.assigned_user else "미배정",
            "상태": record.status, 
            "명부명": record.roster.roster_name if record.roster else "",
            "수정일": record.updated_at.strftime("%Y-%m-%d %H:%M")
        }

        # JSON 데이터 병합 (명부 데이터 + 응답 데이터)
        if record.list_values:
            flat_data.update(record.list_values)
        
        # 응답 데이터는 키 충돌 방지를 위해 'Q_' 접두어 붙이기 (선택사항)
        if record.survey_values:
            for k, v in record.survey_values.items():
                flat_data[f"Q_{k}"] = v

        data_list.append(flat_data)

    return JsonResponse(data_list, safe=False)

# [API] 분석 설정 저장하기
@require_POST
def save_analysis_config(request, survey_id):
    try:
        data = json.loads(request.body)
        survey = get_object_or_404(SurveyMaster, pk=survey_id)
        
        # [수정됨] Analysis -> SurveyAnalysis 로 변경
        SurveyAnalysis.objects.create(
            survey=survey,
            title=data.get('title'),
            description=data.get('description', ''),
            report_config=data.get('report') 
        )
        return JsonResponse({'status': 'success', 'message': '분석 주제가 저장되었습니다.'})
    except Exception as e:
        # 에러 로그를 콘솔에 찍어보면 디버깅에 좋습니다
        print(f"저장 에러 발생: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
# [API] 저장된 분석 목록 가져오기
def get_analysis_list(request, survey_id):
    analyses = SurveyAnalysis.objects.filter(survey_id=survey_id).order_by('-created_at')
    data = [{
        'id': a.id,
        'title': a.title,
        'description': a.description,
        'created_at': a.created_at.strftime('%Y-%m-%d %H:%M'),
        'report_config': a.report_config 
    } for a in analyses]
    return JsonResponse(data, safe=False)

# [화면] 분석 목록 조회 페이지 (조사원/관리자용)
def analysis_list_view(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    analyses = SurveyAnalysis.objects.filter(survey_id=survey_id).order_by('-created_at')
    
    # [추가] URL 파라미터 확인: mode가 'viewer'이면 True
    is_viewer_mode = request.GET.get('mode') == 'viewer'

    return render(request, 'surveys/analysis_list.html', {
        'survey': survey,
        'analyses': analyses,
        'is_viewer_mode': is_viewer_mode  # [추가] 템플릿으로 전달
    })

# [API] 특정 분석 리포트의 설정(JSON)을 반환
@login_required
def get_analysis_detail(request, analysis_id):
    analysis = get_object_or_404(SurveyAnalysis, pk=analysis_id)
    
    # [보안 체크]
    is_assigned = SurveyAreaUser.objects.filter(survey=analysis.survey, user=request.user).exists()

    if not request.user.is_superuser and not is_assigned:
        return JsonResponse({'status': 'error', 'message': '권한이 없습니다.'}, status=403)

    return JsonResponse({
        'status': 'success',
        'title': analysis.title,
        'report_config': analysis.report_config
    })

# [화면] 분석 리포트 뷰어 페이지
@login_required
def analysis_viewer_view(request, analysis_id):
    analysis = get_object_or_404(SurveyAnalysis, pk=analysis_id)
    
    # [보안 체크] 상위 조사에 대해 배정 여부 확인
    # (이 줄의 들여쓰기가 위 'analysis =' 줄과 정확히 일치해야 합니다)
    is_assigned = SurveyAreaUser.objects.filter(survey=analysis.survey, user=request.user).exists()

    if not request.user.is_superuser and not is_assigned:
         return HttpResponse("조회 권한이 없습니다.", status=403)
        
    return render(request, 'surveys/analysis_viewer.html', {'analysis': analysis})

# surveys/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .superset_utils import execute_superset_sql
import json

@csrf_exempt  # API 테스트 편의를 위해 CSRF 예외 처리 (실제 개발시엔 토큰 처리 필요)
def get_query_result(request):
    """
    [API] 클라이언트가 요청한 SQL을 Superset에서 실행하고 결과를 반환
    """
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            # 클라이언트가 SQL을 직접 보낸다고 가정 (보안상 위험할 수 있으니 나중엔 저장된 SQL ID로 변경 권장)
            sql_query = body.get('sql') 
            
            if not sql_query:
                return JsonResponse({'status': 'error', 'message': 'SQL 문이 없습니다.'}, status=400)

            # 유틸리티 함수 호출
            # database_id=1 은 Superset의 'examples' DB입니다. (PostgreSQL 연결한 DB ID로 변경 필요)
            result = execute_superset_sql(sql_query, database_id=2)
            
            if 'error' in result:
                return JsonResponse({'status': 'error', 'message': result['error']}, status=500)
            
            # Superset 결과 구조에서 실제 데이터 추출
            # 보통 result['data'] 에 데이터가 들어있음
            return JsonResponse({
                'status': 'success',
                'data': result.get('data', []),
                'columns': result.get('columns', [])
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)