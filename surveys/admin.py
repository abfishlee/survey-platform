from django.contrib import admin
from .models import SurveyMaster, SurveyDesign, SurveyData

@admin.register(SurveyMaster)
class SurveyMasterAdmin(admin.ModelAdmin):
    list_display = ('survey_code', 'survey_name', 'survey_year', 'survey_degree')
    search_fields = ('survey_name', 'survey_code')

@admin.register(SurveyDesign)
class SurveyDesignAdmin(admin.ModelAdmin):
    list_display = ('survey',)

@admin.register(SurveyData)
class SurveyDataAdmin(admin.ModelAdmin):
    list_display = ('respondent_id', 'survey', 'status', 'updated_at')
    list_filter = ('status', 'survey')
