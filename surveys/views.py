# surveys/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

# 관리자만 접근 가능한지 체크하는 함수
def is_admin(user):
    return user.is_superuser or user.groups.filter(name='Manager').exists()

@login_required
def dashboard(request):
    # 사용자의 권한 확인
    user_is_admin = is_admin(request.user)
    return render(request, 'dashboard.html', {'is_admin': user_is_admin})

# 2. 설계 영역 (관리자 전용)
@user_passes_test(is_admin)
def design_list(request):
    return render(request, 'surveys/design_list.html')