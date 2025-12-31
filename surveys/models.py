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

# 3. 조사별 권역 설계 (본청-지방청-사무소 레벨 구조)
class SurveyArea(models.Model):
    survey = models.ForeignKey(SurveyMaster, on_delete=models.CASCADE, related_name='areas')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    area_code = models.CharField(max_length=20, verbose_name="권역코드") # 예: 11(본청), 1101(서울지방청)
    area_name = models.CharField(max_length=100, verbose_name="권역명")
    level = models.IntegerField(default=1, verbose_name="권역레벨") # 1: 본청, 2: 지방청, 3: 사무소

    class Meta:
        unique_together = ('survey', 'area_code')
        verbose_name = "조사별 권역 설정"

    def __str__(self):
        return f"[{self.area_code}] {self.area_name} (Lv.{self.level})"


# 4. 명부 모델
class SurveyRoster(models.Model):
    survey = models.ForeignKey(SurveyMaster, on_delete=models.CASCADE, related_name='rosters')
    roster_code = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="명부ID")
    roster_name = models.CharField(max_length=100, verbose_name="명부명")
    parent_roster = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name="상위명부")
    mapping_config = models.JSONField(default=list, verbose_name="항목맵핑설정")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.roster_code}] {self.roster_name}"

# 5. 사용자별 권역 배정 (어떤 사용자가 어느 권역 관리자인지/조사원인지)
class SurveyAreaUser(models.Model):
    survey = models.ForeignKey(SurveyMaster, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_areas')
    area = models.ForeignKey(SurveyArea, on_delete=models.CASCADE)
    is_manager = models.BooleanField(default=False, verbose_name="권역관리자여부")

# 6. 조사표 마스터 (설계 데이터 칼럼 제거됨)
class SurveyQuestionnaire(models.Model):
    roster = models.ForeignKey(SurveyRoster, on_delete=models.CASCADE, related_name='questionnaires')
    form_id = models.CharField(max_length=20, unique=True, verbose_name="조사표ID")
    form_name = models.CharField(max_length=100, verbose_name="조사표명")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.form_id}] {self.form_name}"

# 7. 조사표 버전 관리 모델 (알멩이 저장소)
class QuestionnaireVersion(models.Model):
    questionnaire = models.ForeignKey(SurveyQuestionnaire, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField(verbose_name="버전번호")
    # [추가] 버전별 고유 ID (예: S00001-V1)
    ver_form_id = models.CharField(max_length=50, unique=True, null=True, verbose_name="버전별조사표ID")
    design_data = models.JSONField(default=list, verbose_name="설계데이터")
    is_confirmed = models.BooleanField(default=False, verbose_name="확정여부")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 저장 전 ver_form_id 자동 생성 로직
        if not self.ver_form_id:
            # 부모 모델인 SurveyQuestionnaire의 form_id가 있는지 재확인
            base_id = self.questionnaire.form_id if self.questionnaire else "UNKNOWN"
            self.ver_form_id = f"{base_id}-V{self.version_number}"
        super().save(*args, **kwargs)

# 8. 수집 데이터
class SurveyData(models.Model):
    roster = models.ForeignKey(SurveyRoster, on_delete=models.CASCADE, related_name='data_records', null=True, blank=True)
    
    # [수정] SurveyArea 대신 'SurveyArea' 문자열로 참조하여 NameError 방지
    area = models.ForeignKey('SurveyArea', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="소속권역")
    
    # [수정] User 모델과의 관계도 일관성을 위해 문자열 참조 권장 (필수는 아님)
    assigned_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_workload', verbose_name="담당조사원")
    
    respondent_id = models.CharField(max_length=50, verbose_name="명부레코드ID")
    list_values = models.JSONField(default=dict, verbose_name="명부데이터")
    survey_values = models.JSONField(default=dict, verbose_name="조사표답변")
    status = models.CharField(max_length=20, default='READY')
    updated_at = models.DateTimeField(auto_now=True)
