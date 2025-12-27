# surveys/templatetags/survey_tags.py
from django import template

register = template.Library()

@register.filter
def dict_get(dictionary, key):
    """딕셔너리에서 변수로 키값을 찾기 위한 필터"""
    if not dictionary:
        return ""
    # JSON 데이터 구조상 키가 문자열일 수 있으므로 str(key)로 시도
    return dictionary.get(str(key), dictionary.get(key, ""))