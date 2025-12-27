# config/urls.py
from django.contrib import admin
from django.urls import path, include
from surveys import views  # surveys 앱의 views를 불러옵니다

urlpatterns = [
    # 1. 기본 시스템 경로
    path('admin/', admin.site.urls),  # 관리자 페이지
    path('accounts/', include('django.contrib.auth.urls')),  # 로그인/로그아웃 등 인증 경로
    path('', views.dashboard, name='dashboard'),  # 메인 대시보드

    # 2. 통계설계영역 (관리자 전용)
    # 2-1. 설계할 조사를 선택하는 목록 화면
    path('design-list/', views.design_list, name='design_list'),
    
    # 2-2. 항목설계 (명부 및 조사표의 상세 문항 설계)
    path('<int:survey_id>/field_design/', views.survey_field_design, name='survey_field_design'),

    # 3. 명부 관리 및 데이터 임포트 기능 (추가된 기능)
    # 3-1. 설계된 명부 항목에 맞춘 CSV 양식 다운로드
    path('<int:survey_id>/template-download/', views.download_roster_template, name='download_template'),
    
    # 3-2. 작성된 CSV 파일을 통한 명부 데이터 일괄 등록(Import)
    path('<int:survey_id>/import-roster/', views.import_roster_csv, name='import_roster'),

    # 4. 자료수집영역
    # 4-1. 명부 확인 및 조사표 입력 리스트 (설계 옵션에 따른 동적 헤더/검색 적용)
    path('<int:survey_id>/collect/', views.survey_data_entry, name='survey_data_entry'),
]