import json
import csv
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from .models import SurveyMaster, SurveyDesign, SurveyData, SurveyRoster, SurveyQuestionnaire, QuestionnaireVersion
# 1. 권한 체크 함수
def is_admin(user):
    return user.is_superuser or user.groups.filter(name='Manager').exists()

# 2. 메인 대시보드
@login_required
def dashboard(request):
    return render(request, 'dashboard.html', {'is_admin': is_admin(request.user)})

# 3. 통계설계영역 - 조사 선택 목록
@user_passes_test(is_admin)
def design_list(request):
    surveys = SurveyMaster.objects.all()
    return render(request, 'surveys/design_list.html', {'surveys': surveys})

# 4. 항목설계 화면 (1단계)
@user_passes_test(is_admin)
def survey_field_design(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design, created = SurveyDesign.objects.get_or_create(survey=survey)
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

# 5. [명부설계] (2단계) - N00001 자동 채번
@user_passes_test(is_admin)
def survey_roster_design(request, survey_id):
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

# 6. 명부별 항목 맵핑 설정 저장
@user_passes_test(is_admin)
def get_roster_config(request, roster_id):
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    return JsonResponse({'mapping_config': roster.mapping_config})

@user_passes_test(is_admin)
def save_roster_config(request, roster_id):
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    if request.method == 'POST':
        roster.mapping_config = json.loads(request.body).get('mapping_config', [])
        roster.save()
        return JsonResponse({'status': 'success'})

# 7. [조사표설계] (3단계) - 메인 화면 및 S00001 채번
@user_passes_test(is_admin)
def survey_questionnaire_design(request, survey_id):
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

# 8. 조사표 버전 목록 조회 API
@user_passes_test(is_admin)
def get_questionnaire_versions(request, q_id):
    versions = QuestionnaireVersion.objects.filter(questionnaire_id=q_id).order_by('-version_number')
    data = [{
        'id': v.id, 'version_number': v.version_number,
        'created_at': v.created_at.strftime('%Y-%m-%d %H:%M'),
        'item_count': len(v.design_data), 'is_confirmed': v.is_confirmed,
        'design_data': v.design_data
    } for v in versions]
    return JsonResponse(data, safe=False)

# 9. 조사표 설계 신규 버전 저장
@user_passes_test(is_admin)
def save_questionnaire_design(request, q_id):
    questionnaire = get_object_or_404(SurveyQuestionnaire, pk=q_id)
    if request.method == 'POST':
        data = json.loads(request.body)
        last_v = questionnaire.versions.order_by('version_number').last()
        next_v_num = (last_v.version_number + 1) if last_v else 1
        QuestionnaireVersion.objects.create(
            questionnaire=questionnaire, version_number=next_v_num,
            design_data=data.get('design_data', []), is_confirmed=False
        )
        return JsonResponse({'status': 'success'})

# 10. 특정 설계 버전 최종 확정
@user_passes_test(is_admin)
def confirm_questionnaire_version(request, v_id):
    target = get_object_or_404(QuestionnaireVersion, pk=v_id)
    QuestionnaireVersion.objects.filter(questionnaire=target.questionnaire).update(is_confirmed=False)
    target.is_confirmed = True
    target.save()
    return JsonResponse({'status': 'success'})

# 11. 명부 양식(CSV) 다운로드
@user_passes_test(is_admin)
def download_roster_template(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = getattr(survey, 'design', None)
    if not design: return HttpResponse("설계 정보가 없습니다.", status=404)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="template_{survey.survey_code}.csv"'
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow([item['label'] for item in design.list_schema])
    return response

# 12. 명부 데이터(CSV) 업로드 - 00000001 채번
@user_passes_test(is_admin)
def import_roster_csv(request, survey_id):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        survey = get_object_or_404(SurveyMaster, pk=survey_id)
        design = get_object_or_404(SurveyDesign, survey=survey)
        roster = survey.rosters.first()
        if not roster: return JsonResponse({'status': 'error', 'message': '명부를 먼저 등록하세요.'}, status=400)
        
        last_record = SurveyData.objects.all().order_by('id').last()
        next_rec_num = int(last_record.respondent_id) + 1 if last_record and last_record.respondent_id.isdigit() else 1
        
        decoded_file = request.FILES['csv_file'].read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)
        for row in reader:
            list_values = {item['id']: row.get(item['label'], '') for item in design.list_schema}
            SurveyData.objects.create(
                roster=roster, respondent_id=f"{next_rec_num:08d}", list_values=list_values, status='READY'
            )
            next_rec_num += 1
        return JsonResponse({'status': 'success', 'message': '임포트가 완료되었습니다.'})
    return JsonResponse({'status': 'error', 'message': '잘못된 요청'}, status=400)

# 13. [자료수집] 조사 목록
@login_required
def collection_list(request):
    return render(request, 'surveys/collection_survey_list.html', {'surveys': SurveyMaster.objects.all()})

# 14. [자료수집] 명부 데이터 리스트
@login_required
def roster_data_view(request, roster_id):
    roster = get_object_or_404(SurveyRoster, pk=roster_id)
    headers = [c for c in roster.mapping_config if c.get('show_in_list')]
    return render(request, 'surveys/data_entry_list.html', {
        'roster': roster, 'headers': headers, 'data_list': roster.data_records.all(),
        'search_fields': [c for c in roster.mapping_config if c.get('is_search')]
    })

# 15. 입력 팝업용 데이터 조회 API
@login_required
def get_survey_data(request, data_id):
    data_record = get_object_or_404(SurveyData, pk=data_id)
    questionnaire = data_record.roster.questionnaires.first()
    if not questionnaire: return JsonResponse({'status': 'error', 'message': '조사표 없음'}, status=404)
    v = questionnaire.versions.filter(is_confirmed=True).first()
    if not v: return JsonResponse({'status': 'error', 'message': '확정된 버전 없음'}, status=404)
    return JsonResponse({
        'form_name': questionnaire.form_name, 'design_data': v.design_data, 'saved_values': data_record.survey_values
    })

# 16. 조사 답변 저장 API
@login_required
def save_survey_response(request, data_id):
    if request.method == 'POST':
        data_record = get_object_or_404(SurveyData, pk=data_id)
        data_record.survey_values = json.loads(request.body).get('answers', {})
        data_record.status = 'ING'
        data_record.save()
        return JsonResponse({'status': 'success'})