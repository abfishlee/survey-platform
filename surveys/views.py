import json
import csv
import io
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from .models import (
    SurveyMaster, SurveyDesign, SurveyData, SurveyRoster, 
    SurveyQuestionnaire, QuestionnaireVersion, SurveyArea, SurveyAreaUser # 필요한 모델들 확인
    )
from django.db import transaction


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

@user_passes_test(is_admin)  # 관리자만 삭제 가능하도록 권한 체크
def delete_survey_complete(request, survey_id):
    """
    조사 마스터를 삭제하여 관련 모든 데이터를 일괄 삭제함
    (SurveyDesign, SurveyRoster, SurveyQuestionnaire, SurveyData 등 자동 삭제)
    """
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    survey_name = survey.survey_name
    
    # SurveyMaster 삭제 시 CASCADE 설정에 의해 하위 데이터가 모두 삭제됨
    survey.delete()
    
    return HttpResponse(f"조사 '{survey_name}'(ID: {survey_id})와 관련된 모든 명부, 조사표, 데이터, 내검 규칙이 삭제되었습니다.")
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
    surveys = SurveyMaster.objects.all()
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


@user_passes_test(is_admin)
def save_questionnaire_design(request, q_id):
    """조사표의 새로운 설계 버전 저장"""
    questionnaire = get_object_or_404(SurveyQuestionnaire, pk=q_id)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            design_data = data.get('design_data', [])

            # 트랜잭션을 사용하여 버전 생성 보장
            with transaction.atomic():
                last_v = questionnaire.versions.order_by('version_number').last()
                next_v_num = (last_v.version_number + 1) if last_v else 1
                
                # QuestionnaireVersion 모델의 save()에서 ver_form_id가 자동 생성됨
                new_v = QuestionnaireVersion.objects.create(
                    questionnaire=questionnaire,
                    version_number=next_v_num,
                    design_data=design_data,
                    is_confirmed=False
                )
            
            return JsonResponse({'status': 'success', 'version_number': next_v_num})
            
        except Exception as e:
            # DB 에러나 데이터 형식이 틀린 경우 500 에러와 메시지 반환
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)            
    # POST가 아닌 접근에 대한 처리
    return JsonResponse({'status': 'error', 'message': '잘못된 접근 방식입니다.'}, status=405)

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

@user_passes_test(is_admin)
def survey_assignment(request, survey_id):
    """
    [4단계: 업무량 배정] 통합 뷰
    1. 탭 1: 사용자 <-> 권역 배정 (POST 처리 포함)
    2. 탭 2: 사용자 <-> 명부 레코드 배정 (검색 및 필터링 포함)
    """
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    user = request.user

    # 1. 접속한 관리자의 권할 권역 파악
    admin_mapping = SurveyAreaUser.objects.filter(survey=survey, user=user).select_related('area').first()
    
    if not user.is_superuser and not admin_mapping:
        return HttpResponse("권역 관리 권한이 없습니다.", status=403)

    # 2. 관리 범위(하위 권역) 결정
    # 이미지의 코드 체계(10, 1010...)를 활용하여 상위 코드로 시작하는 모든 하위 권역 필터링
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
    all_users = User.objects.filter(is_active=True).exclude(is_superuser=True)
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
    return render(request, 'surveys/collection_survey_list.html', {'surveys': SurveyMaster.objects.all()})

@login_required
def roster_data_view(request, roster_id):
    """
    명부 데이터 리스트 조회
    - LV1/LV2: 권역 내 전체 명부 조회 및 조사원 배정 권한
    - LV3: 권역 내 본인에게 배정된 명부만 조회
    """
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    survey = roster.survey
    user = request.user
    
    # 1. 사용자의 권역 배정 정보 및 레벨 확인
    mapping = SurveyAreaUser.objects.filter(survey=survey, user=user).select_related('area').first()
    if not user.is_superuser and not mapping:
        return HttpResponse("접근 권한이 없습니다.", status=403)

    # 2. 명부 설계에 'area_code'가 포함되어 있는지 확인
    config = roster.mapping_config if isinstance(roster.mapping_config, list) else []
    is_area_design_exists = any(c.get('id') == 'area_code' for c in config)
    
    # 3. 기본 데이터 쿼리셋
    data_list = roster.data_records.all().select_related('area', 'assigned_user').order_by('id')

    # 4. 사용자의 관리 범위 설정 (슈퍼유저는 전체, 일반은 본인 권역 하위)
    if user.is_superuser:
        base_area_code = ""
        user_level = 0 # 전체 관리자
    else:
        base_area_code = mapping.area.area_code
        user_level = mapping.area.level
        # 기본 필터링 (내 권역 하위만)
        data_list = data_list.filter(area__area_code__startswith=base_area_code)
        if not mapping.is_manager:
             data_list = data_list.filter(assigned_user=user)

    # 5. 검색 파라미터 처리 (계층형 검색)
    sel_lv1 = request.GET.get('sel_lv1', '')
    sel_lv2 = request.GET.get('sel_lv2', '')
    sel_lv3 = request.GET.get('sel_lv3', '')

    if sel_lv3: # 사무소 선택 시
        data_list = data_list.filter(area_id=sel_lv3)
    elif sel_lv2: # 지방청 선택 시
        target_area = get_object_or_404(SurveyArea, pk=sel_lv2)
        data_list = data_list.filter(area__area_code__startswith=target_area.area_code)
    elif sel_lv1: # 본청 선택 시
        target_area = get_object_or_404(SurveyArea, pk=sel_lv1)
        data_list = data_list.filter(area__area_code__startswith=target_area.area_code)

    # 6. 콤보박스용 데이터 준비 (내 레벨 이하만 조회)
    all_managed_areas = SurveyArea.objects.filter(survey=survey, area_code__startswith=base_area_code)
    
    context = {
        'roster': roster,
        'headers': [c for c in config if c.get('show_in_list')],
        'search_fields': [c for c in config if c.get('is_search') and c.get('id') != 'area_code'],
        'data_list': data_list,
        'user_area': mapping.area if mapping else None,
        'user_level': user_level,
        'is_area_design_exists': is_area_design_exists,
        # 콤보박스용
        'lv1_list': all_managed_areas.filter(level=1),
        'lv2_list': all_managed_areas.filter(level=2),
        'lv3_list': all_managed_areas.filter(level=3),
        # 선택 상태 유지
        'sel_lv1': sel_lv1, 'sel_lv2': sel_lv2, 'sel_lv3': sel_lv3,
    }
    return render(request, 'surveys/data_entry_list.html', context)

@login_required
def get_survey_data(request, data_id):
    """
    입력 팝업용 데이터 조회 API (중복 제거 및 기능 통합본)
    조사대상 정보, 확정된 조사표 설계(디자인), 기존 저장 답변, 내검 규칙을 한 번에 반환함.
    """
    # 1. 기초 데이터 로드
    data_record = get_object_or_404(SurveyData, pk=data_id)
    roster = data_record.roster
    survey_master = roster.survey
    
    # 2. 해당 조사의 설계 정보에서 내검(Editing) 규칙 추출
    design = getattr(survey_master, 'design', None)
    edit_rules = design.edit_rules if design else []

    # 3. 연결된 조사표 존재 여부 확인
    questionnaires = roster.questionnaires.all()
    if not questionnaires.exists():
        return JsonResponse({'status': 'error', 'message': '연결된 조사표가 없습니다.'}, status=404)

    # 4. 조사표별 최신 확정 버전 및 저장된 답변 데이터 구성
    survey_forms = []
    for q in questionnaires:
        # 각 조사표의 '확정된(is_confirmed=True)' 버전 중 가장 최신 것 조회
        v = q.versions.filter(is_confirmed=True).order_by('-version_number').first()
        
        if v:
            # 해당 버전의 고유 ID(ver_form_id)를 키로 사용하여 저장된 답변 추출
            # 예: {"S00001-V1": {"q1": "1", "q2": "서울"}}
            saved_values = data_record.survey_values.get(v.ver_form_id, {})
            
            survey_forms.append({
                'q_id': q.id,                 # DB Primary Key
                'form_id': q.form_id,         # 조사표 기본 ID (예: S00001)
                'ver_form_id': v.ver_form_id, # 버전별 고유 ID (예: S00001-V1)
                'form_name': q.form_name,
                'design_data': v.design_data, # 조사표 설계 JSON
                'saved_values': saved_values  # 기존 입력 답변
            })

    # 5. 확정된 버전이 하나도 없는 경우 예외 처리
    if not survey_forms:
        return JsonResponse({'status': 'error', 'message': '확정된 조사표 버전이 하나도 없습니다.'}, status=404)

    # 6. 모든 기능이 통합된 최종 데이터 반환
    return JsonResponse({
        'status': 'success',
        'roster_id': roster.roster_code,      # 명부 코드 (예: N00001)
        'respondent_id': data_record.respondent_id,
        'survey_year': survey_master.survey_year,
        'survey_degree': survey_master.survey_degree,
        'forms': survey_forms,                # 조사표 정보 리스트
        'edit_rules': edit_rules              # 내검 규칙 리스트
    })

    # 3. 조사표별 확정 버전 데이터 구성
    survey_forms = []
    for q in questionnaires:
        # 각 조사표의 '확정된(is_confirmed=True)' 버전 중 가장 최신 것 조회
        v = q.versions.filter(is_confirmed=True).order_by('-version_number').first()
        
        if v:
            # 해당 버전의 고유 ID(ver_form_id)를 키로 사용하여 저장된 답변 추출
            # 데이터 구조 예: data_record.survey_values = {"S00001-V1": {...}, "S00002-V1": {...}}
            saved_values = data_record.survey_values.get(v.ver_form_id, {})
            
            survey_forms.append({
                'q_id': q.id,
                'form_id': q.form_id,         # 조사표 기본 ID (S00001)
                'ver_form_id': v.ver_form_id, # 버전별 고유 ID (S00001-V1)
                'form_name': q.form_name,
                'design_data': v.design_data,
                'saved_values': saved_values
            })

    # 4. 확정된 버전이 하나도 없는 경우 처리
    if not survey_forms:
        return JsonResponse({'status': 'error', 'message': '확정된 조사표 버전이 없습니다.'}, status=404)

    # 5. 최종 데이터 반환 (명부ID, 레코드ID, 차수 등 포함)
    return JsonResponse({
        'status': 'success',
        'roster_id': roster.roster_code,
        'respondent_id': data_record.respondent_id,
        'survey_year': survey_master.survey_year,
        'survey_degree': survey_master.survey_degree,
        'forms': survey_forms  # 여러 개의 조사표 데이터가 들어있는 리스트
    })

@login_required
def save_survey_response(request, data_id):
    """조사 답변 저장 API"""
    if request.method == 'POST':
        data_record = get_object_or_404(SurveyData, pk=data_id)
        data_record.survey_values = json.loads(request.body).get('answers', {})
        data_record.status = 'ING'
        data_record.save()
        return JsonResponse({'status': 'success'})



