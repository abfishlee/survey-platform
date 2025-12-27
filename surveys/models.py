# surveys/models.py
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

# 2. 통계 설계 (명부 항목 및 조사표 문항 정의)
class SurveyDesign(models.Model):
    survey = models.OneToOneField(SurveyMaster, on_delete=models.CASCADE, related_name='design')
    # 명부 항목 정의 풀(Pool)
    list_schema = models.JSONField(default=list, verbose_name="명부항목설계")
    # 조사표 문항 정의
    survey_schema = models.JSONField(default=list, verbose_name="조사표설계")
    edit_rules = models.JSONField(default=list, verbose_name="에디팅규칙")

    class Meta:
        verbose_name = "통계 설계"

# [신규] 명부 모델: 확장성을 위해 상위명부ID(parent)를 포함
class SurveyRoster(models.Model):
    survey = models.ForeignKey(SurveyMaster, on_delete=models.CASCADE, related_name='rosters')
    roster_name = models.CharField(max_length=100, verbose_name="명부명") # 예: 가구명부, 가구원명부
    parent_roster = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name="상위명부")
    # 명부별 맵핑 및 옵션 (어떤 항목을 쓰고, 표출/검색할지 저장)
    mapping_config = models.JSONField(default=list, verbose_name="항목맵핑설정")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.survey.survey_name} - {self.roster_name}"        

# 3. 수집 데이터 (실제 명부 및 답변 데이터)
class SurveyData(models.Model):
    # 이제 조사 데이터는 마스터가 아닌 특정 '명부'에 귀속됩니다
    roster = models.ForeignKey(SurveyRoster, on_delete=models.CASCADE, related_name='data_records', null=True, blank=True)
    respondent_id = models.CharField(max_length=50, verbose_name="명부레코드ID") # 명부 내 유니크 ID
    list_values = models.JSONField(default=dict, verbose_name="명부데이터")
    survey_values = models.JSONField(default=dict, verbose_name="조사표답변")
    status = models.CharField(max_length=20, default='READY')
    updated_at = models.DateTimeField(auto_now=True)