from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from app.supabase_auth import sign_in_with_password, sign_up

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    full_name: str | None = None


@router.post("/login/register")
def register_user(payload: RegisterRequest) -> Any:
    try:
        auth_data = sign_up(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "user": auth_data.get("user"),
        "access_token": auth_data.get("access_token"),
        "refresh_token": auth_data.get("refresh_token"),
        "token_type": "bearer" if auth_data.get("access_token") else None,
        "expires_in": auth_data.get("expires_in"),
    }


@router.post("/login/access-token")
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login via Supabase Auth.
    """
    try:
        auth_data = sign_in_with_password(
            email=form_data.username,
            password=form_data.password,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    access_token = auth_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase did not return an access token",
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": auth_data.get("refresh_token"),
        "expires_in": auth_data.get("expires_in"),
    }
