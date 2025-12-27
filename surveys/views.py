# surveys/views.py
import json  # 추가됨
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse  # 추가됨
from .models import SurveyMaster, SurveyDesign  # SurveyDesign 추가됨

# 관리자만 접근 가능한지 체크하는 함수
def is_admin(user):
    return user.is_superuser or user.groups.filter(name='Manager').exists()

@login_required
def dashboard(request):
    user_is_admin = is_admin(request.user)
    return render(request, 'dashboard.html', {'is_admin': user_is_admin})

@user_passes_test(is_admin)
def design_list(request):
    return render(request, 'surveys/design_list.html')

# 설계 영역 접근 시에도 관리자 권한 체크 추가
@user_passes_test(is_admin)
def survey_field_design(request, survey_id):
    # 1. 조사 마스터 정보 가져오기
    survey = get_object_or_404(SurveyMaster, pk=survey_id)
    
    # 2. 설계 정보 가져오기 혹은 생성하기
    design, created = SurveyDesign.objects.get_or_create(survey=survey)

    # 3. 저장 기능 (POST 요청 처리)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # SurveyDesign 모델의 JSONField에 각각 저장
            design.list_schema = data.get('list_schema', [])
            design.survey_schema = data.get('survey_schema', [])
            design.save()
            return JsonResponse({'status': 'success', 'message': '설계 내용이 성공적으로 저장되었습니다.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'저장 실패: {str(e)}'}, status=400)

    # 4. 화면 표시 (GET 요청 처리)
    # 템플릿 파일명은 실제 생성하신 surveys/field_design.html을 사용합니다.
    return render(request, 'surveys/field_design.html', {
        'survey': survey,
        'list_fields': design.list_schema,
        'survey_questions': design.survey_schema,
    })