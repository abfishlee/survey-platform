# surveys/views.py
import json
import csv
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
# SurveyRoster 모델 임포트 추가
from .models import SurveyMaster, SurveyDesign, SurveyData, SurveyRoster

# 1. 권한 체크 함수
def is_admin(user):
    return user.is_superuser or user.groups.filter(name='Manager').exists()

# 2. 메인 대시보드
@login_required
def dashboard(request):
    user_is_admin = is_admin(request.user)
    return render(request, 'dashboard.html', {'is_admin': user_is_admin})

# 3. 통계설계영역 - 조사 선택 목록
@user_passes_test(is_admin)
def design_list(request):
    surveys = SurveyMaster.objects.all()
    return render(request, 'surveys/design_list.html', {'surveys': surveys})

# 4. 항목설계 화면 (명부항목 풀 / 조사표 문항 속성 정의)
@user_passes_test(is_admin)
def survey_field_design(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design, created = SurveyDesign.objects.get_or_create(survey=survey)

    if request.method == 'POST':
        data = json.loads(request.body)
        design.list_schema = data.get('list_schema', [])
        design.survey_schema = data.get('survey_schema', [])
        design.save()
        return JsonResponse({'status': 'success', 'message': '항목 정의가 저장되었습니다.'})

    return render(request, 'surveys/field_design.html', {
        'survey': survey,
        'list_fields': design.list_schema,
        'survey_questions': design.survey_schema,
    })

# 5. [명부설계] 명부 등록 및 목록 관리
@user_passes_test(is_admin)
def survey_roster_design(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = get_object_or_404(SurveyDesign, survey=survey)
    rosters = survey.rosters.all() # 해당 조사의 명부 목록

    if request.method == 'POST':
        # 신규 명부 생성 (가구, 가구원 등)
        data = json.loads(request.body)
        roster_name = data.get('roster_name')
        parent_id = data.get('parent_id')

        # [신규] 명부 ID(N00001) 생성 로직
        last_roster = SurveyRoster.objects.all().order_by('id').last()
        next_num = 1
        if last_roster and last_roster.roster_code and last_roster.roster_code.startswith('N'):
            try:
                # 'N' 뒤의 숫자만 추출해서 +1
                next_num = int(last_roster.roster_code[1:]) + 1
            except (ValueError, TypeError):
                next_num = 1
        
        new_roster_code = f"N{next_num:05d}" # 예: N00001
        
        SurveyRoster.objects.create(
            survey=survey,
            roster_code=new_roster_code, # 생성된 코드 저장
            roster_name=roster_name,
            parent_roster_id=parent_id if parent_id else None
        )
        return JsonResponse({'status': 'success', 'message': '명부가 등록되었습니다.'})

    return render(request, 'surveys/roster_design.html', {
        'survey': survey,
        'item_pool': design.list_schema, # 항목설계에서 만든 전체 항목 풀
        'rosters': rosters,
    })

# 6. [명부설계] 명부별 항목 맵핑 및 옵션 저장 (AJAX 전용)
@user_passes_test(is_admin)
def save_roster_config(request, roster_id):
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    if request.method == 'POST':
        data = json.loads(request.body)
        # 해당 명부에서 사용할 항목 맵핑 및 표출/검색 옵션 저장
        roster.mapping_config = data.get('mapping_config', [])
        roster.save()
        return JsonResponse({'status': 'success', 'message': '명부 설정이 저장되었습니다.'})

# 7. [자료수집] 조사 선택 목록 (대시보드에서 진입)
@login_required
def collection_list(request):
    surveys = SurveyMaster.objects.all()
    return render(request, 'surveys/collection_survey_list.html', {'surveys': surveys})

# 8. [자료수집] 명부 데이터 리스트 표출 (명부별 동적 화면)
@login_required
def roster_data_view(request, roster_id):
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    config = roster.mapping_config
    
    # 설정된 옵션에 따른 동적 헤더 및 검색 필드 구성
    headers = [c for c in config if c.get('show_in_list')]
    search_fields = [c for c in config if c.get('is_search')]
    
    # 해당 명부에 등록된 데이터만 조회
    data_list = roster.data_records.all()
    
    # 동적 검색 필터링
    for field in search_fields:
        search_val = request.GET.get(field['id'])
        if search_val:
            filter_key = f'list_values__{field["id"]}__icontains'
            data_list = data_list.filter(**{filter_key: search_val})

    return render(request, 'surveys/data_entry_list.html', {
        'roster': roster,
        'headers': headers,
        'search_fields': search_fields,
        'data_list': data_list,
    })

# 9. 명부 양식(CSV) 다운로드
@user_passes_test(is_admin)
def download_roster_template(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = getattr(survey, 'design', None)
    
    if not design:
        return HttpResponse("설계 정보가 없습니다.", status=404)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="template_{survey.survey_code}.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    header = [item['label'] for item in design.list_schema]
    writer.writerow(header)
    
    return response

# 10. 명부 데이터(CSV) 업로드
@user_passes_test(is_admin)
def import_roster_csv(request, survey_id):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        survey = get_object_or_404(SurveyMaster, pk=survey_id)
        design = get_object_or_404(SurveyDesign, survey=survey)
        
        # 파일럿용: 해당 조사의 첫 번째 명부에 데이터 매칭 (실제로는 선택 기능 필요)
        roster = survey.rosters.first()
        if not roster:
            return JsonResponse({'status': 'error', 'message': '명부를 먼저 등록해주세요.'}, status=400)


        # [신규] 명부 레코드 ID(00000001) 시작 번호 계산
        # 시스템 전체 혹은 해당 명부 내 마지막 번호를 가져옵니다
        last_record = SurveyData.objects.all().order_by('id').last()
        next_rec_num = 1
        if last_record and last_record.respondent_id.isdigit():
            next_rec_num = int(last_record.respondent_id) + 1

        
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)
        
        import_count = 0
        for row in reader:
            list_values = {}
            for item in design.list_schema:
                label = item['label']
                field_id = item['id']
                list_values[field_id] = row.get(label, '')
            
            res_id = f"{next_rec_num:08d}"
            
            # roster 필드 참조로 수정됨
            SurveyData.objects.create(
                roster=roster,
                respondent_id=res_id,
                list_values=list_values,
                status='READY'
            )
            next_rec_num += 1 # 번호 증가
            import_count += 1
            
        return JsonResponse({'status': 'success', 'message': f'{import_count}건의 데이터가 임포트되었습니다.'})
    return JsonResponse({'status': 'error', 'message': '잘못된 요청입니다.'}, status=400)

@user_passes_test(is_admin)
def survey_questionnaire_design(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    # 항목설계에서 정의한 전체 문항 풀 가져오기
    design = get_object_or_404(SurveyDesign, survey=survey)
    rosters = survey.rosters.all()

    if request.method == 'POST':
        data = json.loads(request.body)
        roster_id = data.get('roster_id')
        form_name = data.get('form_name')
        
        # S00001 자동 채번 로직
        last_form = SurveyQuestionnaire.objects.all().order_by('id').last()
        next_num = 1
        if last_form and last_form.form_id.startswith('S'):
            next_num = int(last_form.form_id[1:]) + 1
        form_id = f"S{next_num:05d}"

        SurveyQuestionnaire.objects.create(
            roster_id=roster_id,
            form_id=form_id,
            form_name=form_name
        )
        return JsonResponse({'status': 'success'})

    return render(request, 'surveys/questionnaire_design.html', {
        'survey': survey,
        'rosters': rosters,
        'item_pool': design.survey_schema # 항목설계의 조사표 문항 풀
    })

@user_passes_test(is_admin)
def save_questionnaire_design(request, q_id):
    questionnaire = get_object_or_404(SurveyQuestionnaire, pk=q_id)
    if request.method == 'POST':
        data = json.loads(request.body)
        questionnaire.design_data = data.get('design_data', [])
        questionnaire.save()
        return JsonResponse({'status': 'success', 'message': '조사표 설계가 저장되었습니다.'})
    
@login_required
def get_survey_data(request, data_id):
    """조사표 설계와 기존 저장된 답변을 가져오는 API"""
    data_record = get_object_or_404(SurveyData, pk=data_id)
    # 해당 명부의 첫 번째 조사표를 가져옴 (필요시 선택 로직 추가 가능)
    questionnaire = data_record.roster.questionnaires.first()
    
    if not questionnaire:
        return JsonResponse({'status': 'error', 'message': '연결된 조사표 설계가 없습니다.'}, status=404)
        
    return JsonResponse({
        'form_name': questionnaire.form_name,
        'design_data': questionnaire.design_data,
        'saved_values': data_record.survey_values # 기존 입력값
    })

@login_required
def save_survey_response(request, data_id):
    """조사표 답변(A)을 저장하는 API"""
    if request.method == 'POST':
        data_record = get_object_or_404(SurveyData, pk=data_id)
        payload = json.loads(request.body)
        
        # 답변 데이터(A) 저장
        data_record.survey_values = payload.get('answers', {})
        data_record.status = 'ING' # 조사 상태를 '조사중'으로 변경
        data_record.save()
        
        return JsonResponse({'status': 'success', 'message': '데이터가 저장되었습니다.'})    