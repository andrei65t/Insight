import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.processCompany import process_company

from app.NameSearcher import NameSearcher
from app.supabase_auth import (
    add_tracked_company,
    delete_tracked_company,
    get_tracked_company,
    get_user_from_access_token,
    list_company_news,
    list_tracked_companies,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _normalize_fact_label(value: str) -> str:
    lowered = str(value or "").strip().lower()
    if lowered.startswith("fact") or lowered == "factual":
        return "Fact"
    if lowered.startswith("opinion"):
        return "Opinion"
    if lowered.startswith("inference"):
        return "Inference"
    return "Inference"


class TrackCompanyRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)


class CompanySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)


def _normalize_contenders(payload: dict) -> list[dict[str, str]]:
    contenders = payload.get("contenders", [])
    if not isinstance(contenders, list):
        return []

    normalized: list[dict[str, str]] = []
    for item in contenders:
        if not isinstance(item, dict):
            continue
        name = (
            item.get("full_legal_name")
            or item.get("legal_name")
            or item.get("company_name")
            or ""
        )
        website = item.get("website") or ""
        name = str(name).strip()
        website = str(website).strip()
        if not name:
            continue
        normalized.append({"name": name, "website": website})

    return normalized


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
        message = str(exc)
        logger.error("GET /tracking/companies failed: %s", message)
        if "Invalid or expired access token" in message:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
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

        process_company(company_name)
        return {"item": item}
    except RuntimeError as exc:
        message = str(exc)
        logger.error("POST /tracking/companies failed: %s", message)
        if "Invalid or expired access token" in message:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/tracking/companies/{company_name}")
def untrack_company(company_name: str, authorization: str | None = Header(default=None)) -> Any:
    token = _extract_bearer_token(authorization)
    company_name = company_name.strip()

    if not company_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_name cannot be empty")

    try:
        user = get_user_from_access_token(token)
        user_id = user["id"]
        deleted = delete_tracked_company(user_id=user_id, company_name=company_name)
        return {"deleted_count": len(deleted)}
    except RuntimeError as exc:
        message = str(exc)
        logger.error("DELETE /tracking/companies failed: %s", message)
        if "Invalid or expired access token" in message:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/tracking/company-search")
def search_company_candidates(payload: CompanySearchRequest, authorization: str | None = Header(default=None)) -> Any:
    token = _extract_bearer_token(authorization)
    query = payload.query.strip()

    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query cannot be empty")

    try:
        # Validate token first to keep the route consistent with other tracking endpoints.
        get_user_from_access_token(token)

        searcher = NameSearcher()
        api_result = searcher.search_web_info(query)
        parsed = searcher._extract_json_content(api_result)
        contenders = _normalize_contenders(parsed)
        return {"items": contenders}
    except RuntimeError as exc:
        message = str(exc)
        logger.error("POST /tracking/company-search failed: %s", message)
        if "Invalid or expired access token" in message:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {exc}") from exc


@router.get("/tracking/companies/{company_name}/details")
def get_company_details(company_name: str, authorization: str | None = Header(default=None)) -> Any:
    token = _extract_bearer_token(authorization)
    company_name = company_name.strip()

    if not company_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company_name cannot be empty")

    try:
        user = get_user_from_access_token(token)
        user_id = user["id"]

        tracked_item = get_tracked_company(user_id=user_id, company_name=company_name)
        if not tracked_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company is not in tracked list")

        raw_news_rows = list_company_news(company_name=company_name, limit=200)
        news_rows = []
        factual_count = 0
        opinion_count = 0
        inference_count = 0

        for row in raw_news_rows:
            normalized_label = _normalize_fact_label(row.get("fact_label", ""))
            enriched = dict(row)
            enriched["fact_label"] = normalized_label
            news_rows.append(enriched)

            if normalized_label == "Fact":
                factual_count += 1
            elif normalized_label == "Opinion":
                opinion_count += 1
            else:
                inference_count += 1

        latest_date = next((row.get("date") for row in news_rows if row.get("date")), None)

        return {
            "tracked_company": tracked_item,
            "news": news_rows,
            "summary": {
                "total_news": len(news_rows),
                "factual_count": factual_count,
                "opinion_count": opinion_count,
                "inference_count": inference_count,
                "latest_date": latest_date,
            },
        }
    except HTTPException:
        raise
    except RuntimeError as exc:
        message = str(exc)
        logger.error("GET /tracking/companies/{company_name}/details failed: %s", message)
        if "Invalid or expired access token" in message:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
