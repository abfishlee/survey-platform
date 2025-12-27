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
    # [추가] N00001 형식의 명부 코드를 저장할 필드
    roster_code = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="명부ID")
    roster_name = models.CharField(max_length=100, verbose_name="명부명")
    parent_roster = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name="상위명부")
    mapping_config = models.JSONField(default=list, verbose_name="항목맵핑설정")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # 출력 시 ID와 이름을 같이 보여주면 관리가 편합니다
        return f"[{self.roster_code}] {self.roster_name}"

class SurveyQuestionnaire(models.Model):
    roster = models.ForeignKey(SurveyRoster, on_delete=models.CASCADE, related_name='questionnaires')
    form_id = models.CharField(max_length=20, unique=True, verbose_name="조사표ID") # S00001
    form_name = models.CharField(max_length=100, verbose_name="조사표명")
    # 최종 확정된 문항 및 구조 정보 (Q1, 질문내용, 타입, 옵션 등 포함)
    design_data = models.JSONField(default=list, verbose_name="조사표설계데이터")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.form_id}] {self.form_name}"        

# 3. 수집 데이터 (실제 명부 및 답변 데이터)
class SurveyData(models.Model):
    # 이제 조사 데이터는 마스터가 아닌 특정 '명부'에 귀속됩니다
    roster = models.ForeignKey(SurveyRoster, on_delete=models.CASCADE, related_name='data_records', null=True, blank=True)
    respondent_id = models.CharField(max_length=50, verbose_name="명부레코드ID") # 명부 내 유니크 ID
    list_values = models.JSONField(default=dict, verbose_name="명부데이터")
    survey_values = models.JSONField(default=dict, verbose_name="조사표답변")
    status = models.CharField(max_length=20, default='READY')
    updated_at = models.DateTimeField(auto_now=True)