from django.db import models
from django.contrib.auth.models import User

# 1. 통계 조사 등록 관리 (시스템 관리 영역 1.2)
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

# 2. 통계 설계 영역 (항목 등록 및 조사표 설계 2.1, 2.2, 2.3)
class SurveyDesign(models.Model):
    survey = models.OneToOneField(SurveyMaster, on_delete=models.CASCADE, related_name='design')
    
    # 명부(List) 항목 설계 (이름, 나이, 주소 등 가변 항목)
    # 형식: [ {"id": "name", "label": "이름", "type": "text"}, ... ]
    list_schema = models.JSONField(default=list, verbose_name="명부항목설계", help_text="명부에 사용될 헤더 항목 정의")
    
    # 조사표(Questionnaire) 문항 설계 (500개 이상의 가변 문항)
    # 형식: [ {"id": "q1", "question": "연간 수입은?", "type": "number"}, ... ]
    survey_schema = models.JSONField(default=list, verbose_name="조사표설계", help_text="조사표 문항 및 입력 방식 정의")
    
    # 에디팅 규칙 설계 (2.4 영역)
    # 형식: [ {"rule_name": "나이체크", "logic": "age < 0", "msg": "나이는 음수일 수 없습니다"} ]
    edit_rules = models.JSONField(default=list, verbose_name="에디팅규칙")

    class Meta:
        verbose_name = "통계 설계"

# 3. 자료 수집 영역 (명부 데이터 및 조사표 답변 3.1)
class SurveyData(models.Model):
    survey = models.ForeignKey(SurveyMaster, on_delete=models.CASCADE, related_name='data_records')
    respondent_id = models.CharField(max_length=50, verbose_name="응답자 고유ID")
    
    # 실제 데이터 저장 (JSONB 활용)
    list_values = models.JSONField(default=dict, verbose_name="명부데이터")   # 명부 실제 값
    survey_values = models.JSONField(default=dict, verbose_name="조사표답변") # 500개 문항 실제 답변
    
    status = models.CharField(
        max_length=20, 
        choices=[('READY', '준비'), ('ING', '조사중'), ('DONE', '완료'), ('ERROR', '에러')],
        default='READY',
        verbose_name="조사상태"
    )
    is_edited = models.BooleanField(default=False, verbose_name="에디팅검증여부")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "수집 데이터"# Create your models here.

# 1. 조사(Survey) 기본 정보 모델 (이미 있다면 생략 가능)
class Survey(models.Model):
    title = models.CharField(max_length=200, verbose_name="조사명")
    description = models.TextField(blank=True, verbose_name="설명")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
# 2. 항목 설계(SurveyField) 모델 - 이번 단계의 핵심!
class SurveyField(models.Model):
    FIELD_TYPES = [
        ('text', '문자열(Text)'),
        ('number', '숫자(Number)'),
        ('date', '날짜(Date)'),
    ]

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='fields')
    logical_name = models.CharField(max_length=100, verbose_name="항목명(논리)") # 예: 나이
    physical_name = models.CharField(max_length=100, verbose_name="필드명(물리)") # 예: age
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    max_length = models.IntegerField(default=255, verbose_name="최대길이")
    display_order = models.IntegerField(default=0, verbose_name="순서")

    class Meta:
        ordering = ['display_order'] # 화면에 보여줄 때 순서대로 정렬