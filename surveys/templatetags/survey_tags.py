# surveys/templatetags/survey_tags.py

import json
from django import template

register = template.Library()

@register.filter
def dict_get(dictionary, key):
    """
    사전형 데이터에서 키값을 가져오되, 문자열로 들어온 경우도 처리함
    """
    if not dictionary:
        return ""
    
    # 만약 데이터가 문자열(JSON String)로 넘어온 경우 Dict로 변환
    if isinstance(dictionary, str):
        try:
            dictionary = json.loads(dictionary.replace("'", '"'))
        except:
            return ""

    # 키값을 문자열로 변환하여 안전하게 조회
    return dictionary.get(str(key), "")

@register.filter
def json_encode(value):
    from django.utils.safestring import mark_safe
    return mark_safe(json.dumps(value, ensure_ascii=False))