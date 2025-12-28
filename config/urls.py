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
    
    # 1단계: 항목설계 / 2단계: 명부설계
    path('<int:survey_id>/field_design/', views.survey_field_design, name='survey_field_design'),
    path('<int:survey_id>/roster_design/', views.survey_roster_design, name='survey_roster_design'),
    path('roster/<int:roster_id>/get-config/', views.get_roster_config, name='get_roster_config'),
    path('roster/<int:roster_id>/save-config/', views.save_roster_config, name='save_roster_config'),
    
    # 3단계: 조사표설계 및 버전 관리
    path('<int:survey_id>/questionnaire_design/', views.survey_questionnaire_design, name='survey_questionnaire_design'),
    path('questionnaire/<int:q_id>/versions/', views.get_questionnaire_versions, name='get_questionnaire_versions'),
    path('questionnaire/<int:q_id>/save/', views.save_questionnaire_design, name='save_questionnaire_design'),
    path('questionnaire/version/<int:v_id>/confirm/', views.confirm_questionnaire_version, name='confirm_questionnaire_version'),

    # 자료수집 (Collect)
    path('collect/', views.collection_list, name='collection_list'),
    path('collect/roster/<int:roster_id>/', views.roster_data_view, name='roster_data_view'),
    path('data/<int:data_id>/get-survey/', views.get_survey_data, name='get_survey_data'),
    path('data/<int:data_id>/save-survey/', views.save_survey_response, name='save_survey_response'),
    
    # 유틸리티 (CSV 다운로드/업로드)
    path('<int:survey_id>/download-template/', views.download_roster_template, name='download_template'),
    path('<int:survey_id>/import-roster/', views.import_roster_csv, name='import_roster'),
]