import logging
from typing import Any
import re

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.processCompany import process_company
from app.HaikuService import HaikuService
from app.Classifier.risk.RiskRelevanceClassifier import RiskRelevanceClassifier
from app.Classifier.risk.RiskRadarClassifier import RiskRadarClassifier
from app.Classifier.risk.PoliticalImpactClassifier import PoliticalImpactClassifier
from app.Classifier.risk.RiskReportAggregator import RiskReportAggregator
import json

from app.NameSearcher import NameSearcher
from app.supabase_auth import (
    add_tracked_company,
    delete_tracked_company,
    get_company_profile,
    get_tracked_company,
    get_user_from_access_token,
    list_company_news,
    list_tracked_companies,
)

router = APIRouter()
logger = logging.getLogger(__name__)

SAFE_THRESHOLD = 75
WATCHLIST_THRESHOLD = 50


def _normalize_fact_label(value: str) -> str:
    lowered = str(value or "").strip().lower()
    if lowered.startswith("fact") or lowered == "factual":
        return "Fact"
    if lowered.startswith("opinion"):
        return "Opinion"
    if lowered.startswith("inference"):
        return "Inference"
    return "Inference"


def _source_quality_score(source_name: str) -> float:
    source = str(source_name or "").strip().lower()
    if not source:
        return 0.5

    high_patterns = [
        r"reuters", r"bloomberg", r"associated press", r"ap news", r"financial times",
        r"wall street journal", r"sec", r"gov", r"court", r"official", r"npr", r"bbc",
    ]
    low_patterns = [r"blog", r"forum", r"rumor", r"rumour", r"x.com", r"reddit"]

    if any(re.search(pattern, source) for pattern in high_patterns):
        return 0.86
    if any(re.search(pattern, source) for pattern in low_patterns):
        return 0.34
    return 0.62


def _build_risk_overview(company_name: str, news_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(news_rows)
    if total == 0:
        return {
            "company": company_name,
            "safe_percentage": 50,
            "risk_percentage": 50,
            "confidence": 30,
            "status": "insufficient_data",
            "status_label": "Insufficient data",
            "color": "yellow",
            "key_drivers": ["No news items available for scoring."],
            "source_mix": {"high_quality": 0, "medium_quality": 0, "low_quality": 0},
            "why_it_matters": "Without enough evidence, supplier risk cannot be estimated reliably.",
            "advice": "Collect more verified sources before making a supplier decision.",
            "evidence": [],
            "thresholds": {
                "safe": SAFE_THRESHOLD,
                "watchlist": WATCHLIST_THRESHOLD,
            },
        }

    factual = 0
    opinion = 0
    inference = 0
    quality_scores: list[float] = []
    evidence_candidates: list[dict[str, Any]] = []
    high_quality = 0
    low_quality = 0

    for row in news_rows:
        label = _normalize_fact_label(row.get("fact_label", ""))
        if label == "Fact":
            factual += 1
        elif label == "Opinion":
            opinion += 1
        else:
            inference += 1

        source_score = _source_quality_score(row.get("source", ""))
        quality_scores.append(source_score)
        if source_score >= 0.8:
            high_quality += 1
        elif source_score <= 0.4:
            low_quality += 1

        label_risk_component = 0.35
        if label == "Opinion":
            label_risk_component = 1.0
        elif label == "Inference":
            label_risk_component = 0.75

        source_risk_component = (1.0 - source_score)
        evidence_score = round((label_risk_component * 0.72 + source_risk_component * 0.28) * 100, 1)
        evidence_candidates.append(
            {
                "title": str(row.get("title", "")),
                "source": str(row.get("source", "Unknown")),
                "date": row.get("date"),
                "link": str(row.get("link", "")),
                "fact_label": label,
                "evidence_score": evidence_score,
                "rationale": (
                    f"{label} signal with source quality score {source_score:.2f} "
                    f"contributes to overall supplier risk."
                ),
            }
        )

    medium_quality = total - high_quality - low_quality
    avg_source_quality = sum(quality_scores) / max(total, 1)

    # Build one dossier text and run the risk pipeline over it to generate an explainable report.
    top_items = news_rows[:12]
    dossier_lines = []
    for row in top_items:
        dossier_lines.append(
            f"- Title: {row.get('title', '')}\n"
            f"  Source: {row.get('source', 'Unknown')}\n"
            f"  Date: {row.get('date', '-') }\n"
            f"  Fact label: {_normalize_fact_label(row.get('fact_label', ''))}\n"
        )
    dossier_text = "\n".join(dossier_lines).strip()

    relevance_result = {"risk_relevant": False, "confidence": 0, "reason": "No dossier."}
    risk_result = {"category": "None", "severity": "low", "confidence": 0, "reason": "No dossier."}
    political_result = {
        "political_or_macro_relevant": False,
        "impact_type": "None",
        "confidence": 0,
        "reason": "No dossier.",
    }
    report_result = {
        "overall_assessment": "No risk report available.",
        "risk_statement": "Insufficient data for structured risk statement.",
        "political_or_macro_note": "",
        "why_it_matters": "",
        "buyer_summary": "Collect more verified evidence before making a supplier decision.",
    }

    if dossier_text:
        try:
            relevance_classifier = RiskRelevanceClassifier()
            risk_classifier = RiskRadarClassifier()
            political_classifier = PoliticalImpactClassifier()
            report_aggregator = RiskReportAggregator()

            relevance_result = relevance_classifier.classify(
                text=dossier_text,
                company_name=company_name,
                source_name="Aggregated multi-source dossier",
                source_type="news_dossier",
                title=f"Risk dossier for {company_name}",
            )

            if relevance_result.get("risk_relevant", False):
                risk_result = risk_classifier.classify(
                    text=dossier_text,
                    company_name=company_name,
                    source_name="Aggregated multi-source dossier",
                    source_type="news_dossier",
                    title=f"Risk dossier for {company_name}",
                )

                political_result = political_classifier.classify(
                    text=dossier_text,
                    company_name=company_name,
                    source_name="Aggregated multi-source dossier",
                    source_type="news_dossier",
                    title=f"Risk dossier for {company_name}",
                )

            report_result = report_aggregator.build(
                company_name=company_name,
                title=f"Risk dossier for {company_name}",
                text=dossier_text,
                relevance_result=relevance_result,
                risk_result=risk_result,
                political_result=political_result,
            )
        except Exception as exc:
            logger.warning("Risk overview AI pipeline fallback for %s: %s", company_name, exc)

    severity_to_base = {"low": 30, "medium": 58, "high": 82}
    base_from_severity = severity_to_base.get(str(risk_result.get("severity", "low")).lower(), 40)
    confidence_from_risk = int(risk_result.get("confidence", 45) or 45)
    confidence_from_risk = max(0, min(100, confidence_from_risk))

    label_risk_pct = ((opinion * 1.0 + inference * 0.72 + factual * 0.3) / total) * 100.0
    source_risk_pct = (1.0 - avg_source_quality) * 100.0
    model_risk_pct = base_from_severity * (0.52 + (confidence_from_risk / 100.0) * 0.48)

    risk_percentage = int(round(model_risk_pct * 0.55 + label_risk_pct * 0.3 + source_risk_pct * 0.15))
    risk_percentage = max(0, min(100, risk_percentage))
    safe_percentage = 100 - risk_percentage

    confidence = int(round((confidence_from_risk * 0.7) + (min(total, 20) / 20 * 30)))
    confidence = max(0, min(95, confidence))

    if safe_percentage >= SAFE_THRESHOLD:
        status = "safe"
        status_label = "Safe"
        color = "green"
    elif safe_percentage >= WATCHLIST_THRESHOLD:
        status = "watchlist"
        status_label = "Watchlist"
        color = "yellow"
    else:
        status = "high_risk"
        status_label = "High risk"
        color = "red"

    key_drivers = [
        f"Risk pipeline: {risk_result.get('category', 'None')} / {risk_result.get('severity', 'low')} (confidence {confidence_from_risk}%).",
        f"Label mix: {factual} Fact, {opinion} Opinion, {inference} Inference.",
        f"Source quality mix: {high_quality} high, {medium_quality} medium, {low_quality} low (avg {avg_source_quality:.2f}).",
    ]

    evidence_top = sorted(evidence_candidates, key=lambda x: x["evidence_score"], reverse=True)[:3]

    political_note = str(report_result.get("political_or_macro_note", "")).strip()
    if political_note:
        key_drivers.append(f"Political/macro note: {political_note}")

    why_it_matters = str(report_result.get("why_it_matters", "")).strip() or (
        "The score combines risk severity, evidence confidence, content certainty, and source reliability "
        "to estimate supplier continuity and compliance exposure."
    )

    advice = str(report_result.get("buyer_summary", "")).strip() or (
        "Monitor this supplier and review critical dependencies before major sourcing decisions."
    )

    return {
        "company": company_name,
        "safe_percentage": safe_percentage,
        "risk_percentage": risk_percentage,
        "confidence": confidence,
        "status": status,
        "status_label": status_label,
        "color": color,
        "key_drivers": key_drivers,
        "source_mix": {
            "high_quality": high_quality,
            "medium_quality": medium_quality,
            "low_quality": low_quality,
        },
        "why_it_matters": why_it_matters,
        "advice": advice,
        "evidence": evidence_top,
        "report": {
            "overall_assessment": str(report_result.get("overall_assessment", "")),
            "risk_statement": str(report_result.get("risk_statement", "")),
            "political_or_macro_note": str(report_result.get("political_or_macro_note", "")),
            "buyer_summary": str(report_result.get("buyer_summary", "")),
        },
        "risk_signal": {
            "risk_relevant": bool(relevance_result.get("risk_relevant", False)),
            "category": str(risk_result.get("category", "None")),
            "severity": str(risk_result.get("severity", "low")),
            "confidence": confidence_from_risk,
        },
        "thresholds": {
            "safe": SAFE_THRESHOLD,
            "watchlist": WATCHLIST_THRESHOLD,
        },
    }


class TrackCompanyRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)


class CompanySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)


class ChatRequest(BaseModel):
    company_name: str
    question: str


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


def _parse_chat_model_response(raw_response: str) -> dict[str, str]:
    raw = str(raw_response or "").strip()
    if not raw:
        return {"answer": "Modelul nu a returnat un raspuns."}

    # Fast path: strict JSON object.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            answer = str(parsed.get("answer", "")).strip()
            if answer:
                return {"answer": answer}
    except json.JSONDecodeError:
        pass

    # Accept JSON wrapped in markdown fences or extra prose.
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, dict):
                answer = str(parsed.get("answer", "")).strip()
                if answer:
                    return {"answer": answer}
        except json.JSONDecodeError:
            pass

    # Fallback: return raw text as answer to avoid 500 errors.
    return {"answer": raw}


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

        company_profile = get_company_profile(company_name=company_name)
        risk_overview = None
        if company_profile:
            financials = company_profile.get("financials")
            if isinstance(financials, dict):
                candidate = financials.get("risk_overview")
                if isinstance(candidate, dict):
                    risk_overview = candidate

            if not isinstance(risk_overview, dict):
                risk_percentage = float(company_profile.get("risk_percentage", 50) or 50)
                risk_percentage = max(0.0, min(100.0, risk_percentage))
                safe_percentage = int(round(100 - risk_percentage))
                risk_level = str(company_profile.get("risk_level", "medium")).strip().lower()
                if risk_level == "low":
                    color = "green"
                    status = "safe"
                    status_label = "Safe"
                elif risk_level == "high":
                    color = "red"
                    status = "high_risk"
                    status_label = "High risk"
                else:
                    color = "yellow"
                    status = "watchlist"
                    status_label = "Watchlist"

                risk_overview = {
                    "safe_percentage": safe_percentage,
                    "risk_percentage": int(round(risk_percentage)),
                    "confidence": 50,
                    "status": status,
                    "status_label": status_label,
                    "color": color,
                    "key_drivers": ["Loaded from persisted company risk profile."],
                    "source_mix": {"high_quality": 0, "medium_quality": 0, "low_quality": 0},
                    "why_it_matters": str(company_profile.get("reputation", "")),
                    "advice": "Review full report details from the latest tracked update.",
                    "report": {
                        "overall_assessment": str(company_profile.get("reputation", "")),
                        "risk_statement": "",
                        "political_or_macro_note": "",
                        "buyer_summary": "",
                    },
                    "risk_signal": {
                        "risk_relevant": True,
                        "category": "None",
                        "severity": str(risk_level),
                        "confidence": 50,
                    },
                    "thresholds": {"safe": SAFE_THRESHOLD, "watchlist": WATCHLIST_THRESHOLD},
                    "evidence": [],
                }

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
            "risk_overview": risk_overview,
            "company_profile": company_profile,
        }
    except HTTPException:
        raise
    except RuntimeError as exc:
        message = str(exc)
        logger.error("GET /tracking/companies/{company_name}/details failed: %s", message)
        if "Invalid or expired access token" in message:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

@router.post("/tracking/chat")
def chat_with_ai(payload: ChatRequest, authorization: str | None = Header(default=None)) -> Any:
    token = _extract_bearer_token(authorization)
    
    try:
        # 1. Validate user
        get_user_from_access_token(token)
        
        # 2. Fetch context (company profile + news for this company)
        company_profile = get_company_profile(company_name=payload.company_name)
        risk_overview = None
        if company_profile:
            financials = company_profile.get("financials")
            if isinstance(financials, dict):
                candidate = financials.get("risk_overview")
                if isinstance(candidate, dict):
                    risk_overview = candidate

        news = list_company_news(payload.company_name, limit=10)

        if not news and not company_profile:
            return {
                "answer": (
                    f"Nu am găsit date pentru {payload.company_name} (nici profil în companies, nici știri în news_companies). "
                    "Adaugă compania la tracked ca să fie procesată și salvată în baza de date."
                )
            }

        # Extragem textul complet pentru primele 5 articole pentru a furniza detalii AI-ului
        from app.processCompany import _fetch_link_html, _html_to_clean_text
        import concurrent.futures

        def _fetch_content(n):
            html = _fetch_link_html(n.get("link", ""))
            clean = _html_to_clean_text(html)
            n["article_content"] = clean[:3000] if clean else "Nu s-a putut extrage textul complet."
            return n

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            top_news = list(executor.map(_fetch_content, news[:5])) if news else []

        # Celelalte (peste 5) le lăsăm doar ca titluri pentru a nu da timeout
        rest_news = news[5:] if news else []

        profile_context = {
            "company_profile": company_profile or {},
            "risk_overview": risk_overview or {},
        }

        # 3. Build context string
        context_str_parts = []
        for n in top_news:
            context_str_parts.append(
                f"- Titlu: {n['title']}\n  Sursă: {n['source']} | Tip: {n['fact_label']}\n  Conținut extras: {n['article_content']}\n"
            )
        for n in rest_news:
            context_str_parts.append(
                f"- Titlu: {n['title']} | Sursă: {n['source']} | Tip: {n['fact_label']} (fără conținut detaliat)"
            )
        context_str = "\n".join(context_str_parts)
        profile_context_str = json.dumps(profile_context, ensure_ascii=False, indent=2)

        # 4. Initialize Haiku
        service = HaikuService()
        
        system_instr = f"""
        Ești un asistent AI specializat în analiza furnizorilor. 
        Răspunde la întrebarea utilizatorului folosind DOAR contextul oferit mai jos despre compania {payload.company_name}.
        Dacă nu găsești răspunsul în context, spune clar acest lucru.
        Fii concis și profesional.
        Răspunde în limba română.

        IMPORTANT:
        - Contextul "COMPANY_PROFILE_DB" vine din tabela companies și este sursa principală pentru scorul safe/risk.
        - Dacă utilizatorul întreabă de ce este X% safe/risk, explică folosind campurile din risk_overview: safe_percentage, risk_percentage, confidence, key_drivers, why_it_matters, advice, report.
        - Nu inventa procente sau indicatori care nu există în context.

        COMPANY_PROFILE_DB:
        {profile_context_str}
        
        CONTEXT (Știri colectate):
        {context_str}
        
        Returnează răspunsul sub formă de JSON: {{"answer": "textul răspunsului tău"}}
        """
        
        response_text = service.send_prompt(user_input=payload.question, system_instruction=system_instr)
        return _parse_chat_model_response(response_text)

    except RuntimeError as exc:
        message = str(exc)
        logger.error("POST /tracking/chat failed: %s", message)
        if "Invalid or expired access token" in message:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    except Exception as exc:
        logger.error("POST /tracking/chat failed: %s", str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
