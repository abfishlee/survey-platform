# surveys/superset_utils.py
import requests
from django.conf import settings

def get_superset_access_token():
    """
    Superset에 로그인하여 API 호출용 Access Token을 받아옵니다.
    """
    login_url = f"{settings.SUPERSET_URL}/api/v1/security/login"
    
    payload = {
        "username": settings.SUPERSET_USERNAME,
        "password": settings.SUPERSET_PASSWORD,
        "provider": "db"
    }
    
    try:
        response = requests.post(login_url, json=payload)
        response.raise_for_status() # 200 OK가 아니면 에러 발생
        
        # 토큰 추출
        token = response.json().get("access_token")
        return token
    except Exception as e:
        print(f"Superset Login Failed: {e}")
        return None

def execute_superset_sql(sql, database_id=1):
    """
    Superset의 SQLLab API를 호출하여 SQL을 실행하고 결과를 받아옵니다.
    database_id: Superset에 등록된 데이터베이스 ID (기본값 1)
    """
    token = get_superset_access_token()
    if not token:
        return {"error": "Failed to get access token"}

    execute_url = f"{settings.SUPERSET_URL}/api/v1/sqllab/execute/"
    
    headers = {
        "Authorization": f"Bearer {token}", # 받아온 토큰을 헤더에 부착
        "Content-Type": "application/json"
    }
    
    payload = {
        "database_id": database_id,
        "sql": sql,
        "runAsync": False, # 바로 결과를 받기 위해 동기 실행 (데이터가 크면 True로 하고 비동기 처리 필요)
        "json": True,
    }
    
    try:
        response = requests.post(execute_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json() # Superset이 준 결과(JSON) 그대로 반환
    except Exception as e:
        print(f"SQL Execution Failed: {e}")
        # 에러 내용을 자세히 보기 위해 response text도 출력
        if 'response' in locals():
            print(response.text)
        return {"error": str(e)}