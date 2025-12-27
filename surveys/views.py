# surveys/views.py
import json
import csv
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from .models import SurveyMaster, SurveyDesign, SurveyData #

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

# 4. 항목설계 화면 (명부/조사표 통합 설계)
@user_passes_test(is_admin)
def survey_field_design(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design, created = SurveyDesign.objects.get_or_create(survey=survey)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # 명부(list_schema)와 조사표(survey_schema) JSON 데이터를 각각 저장
            design.list_schema = data.get('list_schema', [])
            design.survey_schema = data.get('survey_schema', [])
            design.save()
            return JsonResponse({'status': 'success', 'message': '설계 내용이 성공적으로 저장되었습니다.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'저장 실패: {str(e)}'}, status=400)

    return render(request, 'surveys/field_design.html', {
        'survey': survey,
        'list_fields': design.list_schema,
        'survey_questions': design.survey_schema,
    })

# 5. [추가] 명부 양식(CSV) 다운로드 기능
@user_passes_test(is_admin)
def download_roster_template(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = getattr(survey, 'design', None)
    
    if not design:
        return HttpResponse("설계 정보가 없습니다.", status=404)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="template_{survey.survey_code}.csv"'
    
    # 한글 깨짐 방지용 BOM 추가
    response.write(u'\ufeff'.encode('utf8'))
    
    writer = csv.writer(response)
    # 설계된 명부 항목의 '라벨(한글명)'들을 CSV 헤더로 작성
    header = [item['label'] for item in design.list_schema]
    writer.writerow(header)
    
    return response

# 6. [추가] 명부 데이터(CSV) 업로드 기능
@user_passes_test(is_admin)
def import_roster_csv(request, survey_id):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        survey = get_object_or_404(SurveyMaster, pk=survey_id)
        design = get_object_or_404(SurveyDesign, survey=survey)
        csv_file = request.FILES['csv_file']
        
        # 파일 인코딩 처리
        decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)
        
        import_count = 0
        for row in reader:
            list_values = {}
            # CSV의 한글 헤더를 설계된 항목의 ID(물리명)로 매핑하여 JSON 생성
            for item in design.list_schema:
                label = item['label']
                field_id = item['id']
                list_values[field_id] = row.get(label, '')
            
            # 첫 번째 컬럼을 응답자 고유ID로 사용하거나 자동 생성
            res_id = list(row.values())[0] if row.values() else f"R_{import_count}"
            
            SurveyData.objects.create(
                survey=survey,
                respondent_id=res_id,
                list_values=list_values,
                status='READY'
            )
            import_count += 1
            
        return JsonResponse({'status': 'success', 'message': f'{import_count}건의 데이터가 성공적으로 임포트되었습니다.'})
    return JsonResponse({'status': 'error', 'message': '잘못된 요청입니다.'}, status=400)

# 7. [추가] 자료수집 영역 - 명부 리스트 및 검색 화면
@login_required
def survey_data_entry(request, survey_id):
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    design = get_object_or_404(SurveyDesign, survey=survey)
    
    # 설계 단계에서 설정된 옵션에 따라 리스트 헤더와 검색 필드 결정
    headers = [item for item in design.list_schema if item.get('show_in_list')]
    search_fields = [item for item in design.list_schema if item.get('is_search')]
    
    # 해당 조사의 전체 데이터 로드
    data_list = SurveyData.objects.filter(survey=survey)
    
    # 동적 검색 필터링 처리 (PostgreSQL JSONField icontains 활용)
    for field in search_fields:
        search_val = request.GET.get(field['id'])
        if search_val:
            filter_key = f'list_values__{field["id"]}__icontains'
            data_list = data_list.filter(**{filter_key: search_val})

    return render(request, 'surveys/data_entry_list.html', {
        'survey': survey,
        'headers': headers,
        'search_fields': search_fields,
        'data_list': data_list,
    })