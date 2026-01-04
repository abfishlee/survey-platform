from django.contrib import admin
from django.shortcuts import render
# SurveyRoster를 추가로 임포트해야 합니다.
from .models import SurveyMaster, SurveyDesign, SurveyData, SurveyRoster, SurveyDegree, SqlLabManager


class SurveyDegreeInline(admin.TabularInline):
    model = SurveyDegree
    extra = 1  # 기본으로 보여줄 입력 칸 수

@admin.register(SurveyMaster)
class SurveyMasterAdmin(admin.ModelAdmin):
    list_display = ('survey_code', 'survey_name', 'survey_year', 'get_managers_count')
    search_fields = ('survey_name', 'survey_code')
    
    # [핵심] 사용자를 좌우로 넘겨서 쉽게 선택하는 위젯 적용
    filter_horizontal = ('managers',) 
    
    inlines = [SurveyDegreeInline]

    # 목록에서 몇 명이 관리자인지 보여주는 함수
    def get_managers_count(self, obj):
        return obj.managers.count()
    get_managers_count.short_description = "배정된 관리자 수"

@admin.register(SurveyDegree)
class SurveyDegreeAdmin(admin.ModelAdmin):
    list_display = ('survey', 'degree_number', 'degree_title', 'start_date', 'end_date', 'is_active')
    list_filter = ('survey', 'is_active')

@admin.register(SurveyDesign)
class SurveyDesignAdmin(admin.ModelAdmin):
    list_display = ('survey',)

# [신규 추가] 명부 관리 어드민
@admin.register(SurveyRoster)
class SurveyRosterAdmin(admin.ModelAdmin):
    # roster_code를 리스트에 추가
    list_display = ('roster_code', 'roster_name', 'survey', 'parent_roster', 'created_at')
    list_filter = ('survey',)

# SurveyData 모델의 필드가 survey에서 roster로 변경됨에 따른 수정
@admin.register(SurveyData)
class SurveyDataAdmin(admin.ModelAdmin):
    # 'survey' 대신 'roster'를 사용합니다.
    list_display = ('respondent_id', 'roster', 'status', 'updated_at')
    list_filter = ('status', 'roster')

@admin.register(SqlLabManager)
class SqlLabManagerAdmin(admin.ModelAdmin):
    # 1. 메뉴 이름 설정
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    # 2. 리스트 화면 대신 Superset Iframe 보여주기
    def changelist_view(self, request, extra_context=None):
        # Superset 주소 (도커 설정에 맞게 수정하세요)
        superset_url = "http://119.223.104.14:8088/sqllab/"
        
        context = {
            'title': 'SQL 통합 관리 (Superset)',
            # login_url: 자동 로그인을 처리할 주소 (아래에서 설명)
            'superset_login_url': "http://119.223.104.14:8088/login/",
            'next_url': "http://119.223.104.14:8088/sqllab/",  # 로그인 성공 후 이동할 곳
            **(extra_context or {}),
        }
        return render(request, 'admin/sql_lab_embed.html', context)