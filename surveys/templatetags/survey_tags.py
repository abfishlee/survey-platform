# surveys/templatetags/survey_tags.py 수정

import json # [추가]
from django import template
from django.utils.safestring import mark_safe # [추가]

register = template.Library()

@register.filter
def dict_get(dictionary, key):
    """딕셔너리에서 변수로 키값을 찾기 위한 필터"""
    if not dictionary:
        return ""
    return dictionary.get(str(key), dictionary.get(key, ""))

# [신규 추가] 조사표 설계를 JSON으로 안전하게 변환하는 필터
@register.filter
def json_encode(value):
    """데이터를 JSON 문자열로 변환하여 템플릿의 data- 속성에 안전하게 전달"""
    try:
        return mark_safe(json.dumps(value, ensure_ascii=False))
    except (TypeError, ValueError):
        return "[]"