from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.supabase_auth import (
    add_tracked_company,
    get_user_from_access_token,
    list_tracked_companies,
)

router = APIRouter()


class TrackCompanyRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    return token


@router.get("/tracking/companies")
def get_tracked_companies(authorization: str | None = Header(default=None)) -> Any:
    token = _extract_bearer_token(authorization)

    try:
        user = get_user_from_access_token(token)
        user_id = user["id"]
        companies = list_tracked_companies(user_id)
        return {"items": companies}
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/tracking/companies")
def track_company(payload: TrackCompanyRequest, authorization: str | None = Header(default=None)) -> Any:
    token = _extract_bearer_token(authorization)
    company_name = payload.company_name.strip()

    if not company_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_name cannot be empty")

    try:
        user = get_user_from_access_token(token)
        user_id = user["id"]
        item = add_tracked_company(user_id=user_id, company_name=company_name)
        return {"item": item}
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
