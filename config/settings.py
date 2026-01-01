import os
from pathlib import Path
from dotenv import load_dotenv

# 1. 기본 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent

# .env 파일 로드 (BASE_DIR에 위치해야 함)
load_dotenv(BASE_DIR / '.env')

# 2. 보안 및 환경 설정 (.env에서 읽어옴)
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# ALLOWED_HOSTS는 .env에서 콤마(,)로 구분된 문자열을 리스트로 변환
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# 3. 애플리케이션 정의
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_vite',  # Vite 연동 라이브러리
    'surveys',      # 설문 시스템 앱
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# 4. 데이터베이스 설정 (PostgreSQL) - .env에서 정보를 가져오도록 수정 권장
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'survey_db'),
        'USER': os.getenv('DB_USER', 'survey_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'pilot1234!'),
        'HOST': os.getenv('DB_HOST', '119.223.104.14'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# 5. 국제화 설정
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# 6. 정적 파일 및 미디어 설정
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'static''dist',
]

# 7. Django-Vite 통합 설정 (평면형 변수 구조로 변경)
# .env에서 값을 읽어오며, 배포 시에는 자동으로 False가 됨
DJANGO_VITE_DEV_MODE = os.getenv('DJANGO_VITE_DEV_MODE', 'False') == 'True'
DJANGO_VITE_DEV_SERVER_HOST = os.getenv('DJANGO_VITE_DEV_SERVER_HOST', '127.0.0.1')
DJANGO_VITE_DEV_SERVER_PORT = os.getenv('DJANGO_VITE_DEV_SERVER_PORT', '3000')

# 배포(Production) 시 빌드된 자산의 경로 설정
DJANGO_VITE_ASSETS_PATH = BASE_DIR / "static" / "dist"
DJANGO_VITE_MANIFEST_PATH = DJANGO_VITE_ASSETS_PATH / ".vite" / "manifest.json"

# 8. 로그인/로그아웃 리다이렉트
LOGIN_REDIRECT_URL = '/' 
LOGOUT_REDIRECT_URL = '/accounts/login/'

INTERNAL_IPS = ['127.0.0.1', 'localhost']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'