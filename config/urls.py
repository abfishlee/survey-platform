from django.contrib import admin
from django.urls import path, include
from surveys import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 기본 인증 (로그인/로그아웃)
    path('accounts/', include('django.contrib.auth.urls')),
    
    # 메인 및 설계 목록
    path('', views.dashboard, name='dashboard'),
    path('design-list/', views.design_list, name='design_list'),
    
    # 1단계: 권역설계
    path('<int:survey_id>/area_design/', views.survey_area_design, name='survey_area_design'),

    # 2단계: 항목설계 / 3단계: 명부설계
    path('<int:survey_id>/field_design/', views.survey_field_design, name='survey_field_design'),
    path('<int:survey_id>/roster_design/', views.survey_roster_design, name='survey_roster_design'),
    path('roster/<int:roster_id>/get-config/', views.get_roster_config, name='get_roster_config'),
    path('roster/<int:roster_id>/save-config/', views.save_roster_config, name='save_roster_config'),
    
    # 4단계: 조사표설계 및 버전 관리
    path('<int:survey_id>/questionnaire_design/', views.survey_questionnaire_design, name='survey_questionnaire_design'),
    path('questionnaire/<int:q_id>/versions/', views.get_questionnaire_versions, name='get_questionnaire_versions'),
    path('questionnaire/<int:q_id>/save/', views.save_questionnaire_design, name='save_questionnaire_design'),
    path('questionnaire/version/<int:v_id>/confirm/', views.confirm_questionnaire_version, name='confirm_questionnaire_version'),

    # 자료수집 (Collect)
    path('collect/', views.collection_list, name='collection_list'),
    
    path('collect/<int:survey_id>/degrees/', views.collection_degree_list, name='collection_degree_list'),

    path('collect/roster/<int:roster_id>/degree/<int:degree_id>/', views.roster_data_view, name='roster_data_view'),

    path('data/<int:data_id>/get-survey/', views.get_survey_data, name='get_survey_data'),
    path('data/<int:data_id>/save-survey/', views.save_survey_response, name='save_survey_response'),
    
    # 유틸리티 (CSV 다운로드/업로드)
    path('<int:survey_id>/download-template/', views.download_roster_template, name='download_template'),
    path('<int:survey_id>/import-roster/', views.import_roster_csv, name='import_roster'),

    path('<int:survey_id>/edit_rule_design/', views.survey_edit_rule_design, name='survey_edit_rule_design'),
    # 조사표 삭제 
    path('questionnaire/<int:q_id>/delete/', views.delete_questionnaire, name='delete_questionnaire'),

    # 4단계: 업무량배정 (추후 개발을 위해 경로 선점)
    path('<int:survey_id>/assignment/', views.survey_assignment, name='survey_assignment'),
    path('survey/<int:survey_id>/remove-assignment/', views.remove_survey_assignment, name='remove_survey_assignment'),

    path('clear/<int:roster_id>/', views.clear_roster_data),

    path('survey/<int:survey_id>/delete-all/', views.reset_all_survey_data, name='reset_all_survey_data'),
    path('survey/assign-records/', views.assign_records, name='assign_records'),

    # [추가] 7. 자료분석 화면
    path('survey/<int:survey_id>/collection-analysis/', views.collection_analysis_view, name='collection_analysis'),

    # [추가] 데이터 API
    path('survey/<int:survey_id>/pivot-data/', views.survey_pivot_data_api, name='survey_pivot_data_api'),

    # [추가] 분석 저장 API
    path('survey/<int:survey_id>/analysis/save/', views.save_analysis_config, name='save_analysis_config'),
    
    # [추가] 분석 목록 API (Vue에서 로딩용)
    path('survey/<int:survey_id>/analysis/list-api/', views.get_analysis_list, name='get_analysis_list'),

    # [추가] 분석 목록 화면 (조사원이 볼 화면)
    path('survey/<int:survey_id>/analysis/list/', views.analysis_list_view, name='analysis_list_view'),

    # [수정 후] - 앞에 'survey/'를 붙여서 경로를 맞춰줍니다!
    path('survey/analysis/<int:analysis_id>/view/', views.analysis_viewer_view, name='analysis_viewer'),
    path('survey/analysis/<int:analysis_id>/json/', views.get_analysis_detail, name='get_analysis_detail'),

    # 신규 API 추가
    path('api/execute-sql/', views.get_query_result, name='api_execute_sql'), 
]