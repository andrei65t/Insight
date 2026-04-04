from typing import Any, Dict

import requests

from app.config import settings


def _supabase_headers() -> Dict[str, str]:
    return {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


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
