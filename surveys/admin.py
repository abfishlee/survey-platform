from django.contrib import admin
# SurveyRoster를 추가로 임포트해야 합니다.
from .models import SurveyMaster, SurveyDesign, SurveyData, SurveyRoster 

@admin.register(SurveyMaster)
class SurveyMasterAdmin(admin.ModelAdmin):
    list_display = ('survey_code', 'survey_name', 'survey_year', 'survey_degree')
    search_fields = ('survey_name', 'survey_code')

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