# config/urls.py
from django.contrib import admin
from django.urls import path, include
from surveys import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', views.dashboard, name='dashboard'),
    
    # 설계 영역 목록
    path('design-list/', views.design_list, name='design_list'),
    
    # 1단계: 항목설계 (필드 및 문항 속성 정의)
    path('<int:survey_id>/field_design/', views.survey_field_design, name='survey_field_design'),
    
    # 2단계: 명부설계 (항목 맵핑 및 CSV 관리)
    path('<int:survey_id>/roster_design/', views.survey_roster_design, name='survey_roster_design'),
    path('roster/<int:roster_id>/save_config/', views.save_roster_config, name='save_roster_config'),
    # 명부 데이터 처리
    path('<int:survey_id>/template-download/', views.download_roster_template, name='download_template'),
    path('<int:survey_id>/import-roster/', views.import_roster_csv, name='import_roster'),
    
    # 자료수집 영역
    path('collect/', views.collection_list, name='collection_list'), # 조사 선택
    path('collect/roster/<int:roster_id>/', views.roster_data_view, name='roster_data_view'), # 명부 리스트

    path('<int:survey_id>/questionnaire_design/', views.survey_questionnaire_design, name='survey_questionnaire_design'),
    path('questionnaire/<int:q_id>/save/', views.save_questionnaire_design, name='save_questionnaire_design'),

    path('data/<int:data_id>/get-survey/', views.get_survey_data, name='get_survey_data'),
    path('data/<int:data_id>/save-survey/', views.save_survey_response, name='save_survey_response'),
]