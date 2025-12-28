from django.db import models
from django.contrib.auth.models import User

# 1. 통계 조사 마스터
class SurveyMaster(models.Model):
    survey_code = models.CharField(max_length=20, unique=True, verbose_name="조사코드")
    survey_name = models.CharField(max_length=200, verbose_name="조사명")
    survey_year = models.CharField(max_length=4, verbose_name="조사연도")
    survey_degree = models.IntegerField(default=1, verbose_name="조사차수")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "통계 조사 마스터"
        verbose_name_plural = "통계 조사 마스터 목록"

    def __str__(self):
        return f"[{self.survey_code}] {self.survey_name}"

# 2. 통계 설계
class SurveyDesign(models.Model):
    survey = models.OneToOneField(SurveyMaster, on_delete=models.CASCADE, related_name='design')
    list_schema = models.JSONField(default=list, verbose_name="명부항목설계")
    survey_schema = models.JSONField(default=list, verbose_name="조사표설계")
    edit_rules = models.JSONField(default=list, verbose_name="에디팅규칙")

# 3. 명부 모델
class SurveyRoster(models.Model):
    survey = models.ForeignKey(SurveyMaster, on_delete=models.CASCADE, related_name='rosters')
    roster_code = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="명부ID")
    roster_name = models.CharField(max_length=100, verbose_name="명부명")
    parent_roster = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name="상위명부")
    mapping_config = models.JSONField(default=list, verbose_name="항목맵핑설정")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.roster_code}] {self.roster_name}"

# 4. 조사표 마스터 (설계 데이터 칼럼 제거됨)
class SurveyQuestionnaire(models.Model):
    roster = models.ForeignKey(SurveyRoster, on_delete=models.CASCADE, related_name='questionnaires')
    form_id = models.CharField(max_length=20, unique=True, verbose_name="조사표ID")
    form_name = models.CharField(max_length=100, verbose_name="조사표명")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.form_id}] {self.form_name}"

# 5. 조사표 버전 관리 모델 (알멩이 저장소)
class QuestionnaireVersion(models.Model):
    questionnaire = models.ForeignKey(SurveyQuestionnaire, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField(verbose_name="버전번호")
    design_data = models.JSONField(default=list, verbose_name="설계데이터")
    is_confirmed = models.BooleanField(default=False, verbose_name="확정여부")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']

# 6. 수집 데이터
class SurveyData(models.Model):
    roster = models.ForeignKey(SurveyRoster, on_delete=models.CASCADE, related_name='data_records', null=True, blank=True)
    respondent_id = models.CharField(max_length=50, verbose_name="명부레코드ID")
    list_values = models.JSONField(default=dict, verbose_name="명부데이터")
    survey_values = models.JSONField(default=dict, verbose_name="조사표답변")
    status = models.CharField(max_length=20, default='READY')
    updated_at = models.DateTimeField(auto_now=True)