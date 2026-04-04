from typing import Any, Dict, List

import requests

try:
    from app.config import settings
except ModuleNotFoundError:
    from config import settings


def _supabase_headers() -> Dict[str, str]:
    return {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def _supabase_service_headers(prefer: str | None = None) -> Dict[str, str]:
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    if not service_key or service_key == "SECRET_KEY":
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is missing. Set it in backend/.env.")

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def sign_in_with_password(email: str, password: str) -> Dict[str, Any]:
    url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
    payload = {"email": email, "password": password}

    response = requests.post(url, headers=_supabase_headers(), json=payload, timeout=30)

    if response.status_code >= 400:
        detail = "Login failed"
        try:
            error_data = response.json()
            detail = error_data.get("error_description") or error_data.get("msg") or detail
        except ValueError:
            pass
        raise RuntimeError(detail)

    return response.json()


def sign_up(email: str, password: str, full_name: str | None = None) -> Dict[str, Any]:
    url = f"{settings.SUPABASE_URL}/auth/v1/signup"
    payload: Dict[str, Any] = {"email": email, "password": password}

    if full_name:
        payload["data"] = {"full_name": full_name}

    response = requests.post(url, headers=_supabase_headers(), json=payload, timeout=30)

    if response.status_code >= 400:
        detail = "Register failed"
        try:
            error_data = response.json()
            detail = error_data.get("error_description") or error_data.get("msg") or detail
        except ValueError:
            pass
        raise RuntimeError(detail)

    return response.json()


def get_user_from_access_token(access_token: str) -> Dict[str, Any]:
    url = f"{settings.SUPABASE_URL}/auth/v1/user"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
    }
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code >= 400:
        raise RuntimeError("Invalid or expired access token")

    return response.json()


def add_tracked_company(user_id: str, company_name: str) -> Dict[str, Any]:
    url = f"{settings.SUPABASE_URL}/rest/v1/{settings.TRACKING_TABLE}"
    payload = [{"user_id": user_id, "company_name": company_name}]
    headers = _supabase_service_headers(prefer="resolution=merge-duplicates,return=representation")

    response = requests.post(
        url,
        headers=headers,
        params={"on_conflict": "user_id,company_name"},
        json=payload,
        timeout=30,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Failed to track company: {response.text}")

    data = response.json()
    return data[0] if isinstance(data, list) and data else {}


def list_tracked_companies(user_id: str) -> List[Dict[str, Any]]:
    url = f"{settings.SUPABASE_URL}/rest/v1/{settings.TRACKING_TABLE}"
    response = requests.get(
        url,
        headers=_supabase_service_headers(),
        params={
            "select": "id,company_name,created_at",
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
        },
        timeout=30,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Failed to fetch tracked companies: {response.text}")

    data = response.json()
    return data if isinstance(data, list) else []


def delete_tracked_company(user_id: str, company_name: str) -> List[Dict[str, Any]]:
    url = f"{settings.SUPABASE_URL}/rest/v1/{settings.TRACKING_TABLE}"
    response = requests.delete(
        url,
        headers=_supabase_service_headers(prefer="return=representation"),
        params={
            "user_id": f"eq.{user_id}",
            "company_name": f"eq.{company_name}",
        },
        timeout=30,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Failed to delete tracked company: {response.text}")

    data = response.json()
    return data if isinstance(data, list) else []


def add_news_companies(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []

    url = f"{settings.SUPABASE_URL}/rest/v1/news_companies"
    headers = _supabase_service_headers(prefer="return=representation")

    response = requests.post(
        url,
        headers=headers,
        json=items,
        timeout=30,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Failed to insert news_companies rows: {response.text}")

    data = response.json()
    return data if isinstance(data, list) else []
