if __package__:
    from app.NewsSearcher import search_news
    from app.Classifier.SignalNoiseClassifier import SignalNoiseClassifier
    from app.Classifier.FactOpinionInferenceClassifier import FactOpinionInferenceClassifier
    from app.Classifier.risk.RiskRelevanceClassifier import RiskRelevanceClassifier
    from app.Classifier.risk.RiskRadarClassifier import RiskRadarClassifier
    from app.Classifier.risk.PoliticalImpactClassifier import PoliticalImpactClassifier
    from app.Classifier.risk.RiskReportAggregator import RiskReportAggregator
    from app.HaikuService import HaikuService
    from app.supabase_auth import add_news_companies, upsert_company_profile
else:
    from NewsSearcher import search_news
    from Classifier.SignalNoiseClassifier import SignalNoiseClassifier
    from Classifier.FactOpinionInferenceClassifier import FactOpinionInferenceClassifier
    from Classifier.risk.RiskRelevanceClassifier import RiskRelevanceClassifier
    from Classifier.risk.RiskRadarClassifier import RiskRadarClassifier
    from Classifier.risk.PoliticalImpactClassifier import PoliticalImpactClassifier
    from Classifier.risk.RiskReportAggregator import RiskReportAggregator
    from HaikuService import HaikuService
    from supabase_auth import add_news_companies, upsert_company_profile
import json
import html
import re
import requests
import os
from dotenv import load_dotenv

load_dotenv()


HF_SUMMARY_API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-cnn"

RISK_PERCENT_SYSTEM_INSTRUCTION = """
You are a supplier risk scoring assistant.

Given a list of company news items with risk signals, estimate overall company procurement risk as a single percentage.

Rules:
1. Return strict JSON only.
2. risk_percentage must be an integer from 0 to 100.
3. confidence must be an integer from 0 to 100.
4. Consider severity, confidence, legal/compliance/cyber exposure, operational disruption, and consistency across multiple items.
5. If evidence is weak, lower confidence and avoid extreme percentages.

JSON schema:
{"risk_percentage":0,"confidence":0,"reason":"short explanation","key_drivers":["driver1","driver2"]}
"""

COMPANY_PROFILE_SYSTEM_INSTRUCTION = """
You are a supplier risk profile generator.

Return strict JSON with this exact top-level schema:
{
    "risk_level":"low|medium|high",
    "risk_percentage":0,
    "reputation":"short business sentence",
    "financials":{}
}

Rules:
1. risk_percentage must be numeric between 0 and 100.
2. risk_level must be one of low, medium, high.
3. financials must be a JSON object suitable for storage in a JSONB column.
4. Use concise business language.
5. Avoid markdown.
"""


def signalClassifier(news_items: list, company_name: str) -> list:
    classifier = SignalNoiseClassifier()
    signal_items = []

    for item in news_items:
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        source_name = item.get("source", "Unknown")
        link = item.get("link", "")
        date = item.get("date")

        page_html = _fetch_link_html(link)
        full_text = _html_to_clean_text(page_html)[:12000]

        # Use full article text first; fallback to snippet/title only if fetch/parse fails.
        classify_text = str(full_text or snippet or title).strip()
        if not classify_text:
            continue

        classification = classifier.classify(
            text=classify_text,
            source_name=source_name,
            title=title,
            company=company_name,
            link=link,
        )

        if str(classification.get("label", "")).strip().lower() != "signal":
            continue

        signal_items.append(
            {
                "company": company_name,
                "title": title,
                "text": classify_text,
                "link": link,
                "date": date,
                "source": source_name,
                "classification": classification,
            }
        )

    return signal_items


def add_news_to_supabase(news_items: list, company_name: str) -> list:
    def normalize_fact_label(value: str) -> str:
        lowered = str(value or "").strip().lower()
        if lowered.startswith("fact") or lowered == "factual":
            return "Fact"
        if lowered.startswith("opinion"):
            return "Opinion"
        if lowered.startswith("inference"):
            return "Inference"
        # Force a category instead of leaving ambiguous labels as Unknown.
        return "Inference"

    rows = []
    for item in news_items:
        classification = item.get("classification", {})
        fact_label = normalize_fact_label(classification.get("fact_label", "Unknown"))
        rows.append(
            {
                "company": company_name,
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "date": item.get("date"),
                "source": item.get("source", "Unknown"),
                "fact_label": fact_label,
            }
        )
    return add_news_companies(rows)


def _fetch_link_html(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                )
            },
            timeout=20,
        )
        if response.status_code >= 400:
            return ""
        return response.text or ""
    except Exception:
        return ""


def _html_to_clean_text(raw_html: str) -> str:
    if not raw_html:
        return ""

    text = re.sub(r"(?is)<(script|style|noscript|svg).*?>.*?</\1>", " ", raw_html)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|h1|h2|h3|h4|h5|h6|tr|section|article)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def summarize_text(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""

    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        return text

    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": text}

    try:
        response = requests.post(
            HF_SUMMARY_API_URL,
            headers=headers,
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return text

    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            summary = str(first.get("summary_text", "")).strip()
            if summary:
                return summary

    if isinstance(data, dict):
        summary = str(data.get("summary_text", "")).strip()
        if summary:
            return summary

    return text


def FactClassifier(items: list) -> list:
    classifier = FactOpinionInferenceClassifier()

    for item in items:
        title = item.get("title", "Untitled")
        source = item.get("source", "Unknown")
        clean_text = str(item.get("text", "")).strip()[:12000]

        if not clean_text:
            item.setdefault("classification", {})
            item["classification"]["fact_label"] = "Inference"
            continue

        fact_result = classifier.classify(
            text=clean_text,
            source_name=source,
            source_type="news_site",
            title=title,
        )
        raw_label = str(fact_result.get("label", "Unknown")).strip().lower()
        if raw_label.startswith("fact") or raw_label == "factual":
            fact_label = "Fact"
        elif raw_label.startswith("opinion"):
            fact_label = "Opinion"
        elif raw_label.startswith("inference"):
            fact_label = "Inference"
        else:
            fact_label = "Inference"

        item.setdefault("classification", {})
        item["classification"]["fact_label"] = fact_label

    return items


def apply_risk_filter(items: list, company_name: str) -> list:
    relevance_classifier = RiskRelevanceClassifier()
    risk_classifier = RiskRadarClassifier()
    political_classifier = PoliticalImpactClassifier()
    report_aggregator = RiskReportAggregator()

    filtered_items = []
    for item in items:
        title = item.get("title", "Untitled")
        source_name = item.get("source", "Unknown")
        source_type = "news_site"
        text = str(item.get("text", "")).strip()

        if not text:
            continue

        relevance_result = relevance_classifier.classify(
            text=text,
            company_name=company_name,
            source_name=source_name,
            source_type=source_type,
            title=title,
        )

        if not relevance_result.get("risk_relevant", False):
            continue

        risk_result = risk_classifier.classify(
            text=text,
            company_name=company_name,
            source_name=source_name,
            source_type=source_type,
            title=title,
        )

        political_result = political_classifier.classify(
            text=text,
            company_name=company_name,
            source_name=source_name,
            source_type=source_type,
            title=title,
        )

        report_result = report_aggregator.build(
            company_name=company_name,
            title=title,
            text=text,
            relevance_result=relevance_result,
            risk_result=risk_result,
            political_result=political_result,
        )

        item["risk"] = {
            "relevance": relevance_result,
            "primary": risk_result,
            "political": political_result,
            "report": report_result,
        }
        filtered_items.append(item)

    return filtered_items


def _fallback_risk_percentage_from_items(items: list) -> dict:
    if not items:
        return {
            "risk_percentage": 0,
            "confidence": 30,
            "reason": "No risk items available.",
            "key_drivers": [],
            "method": "fallback",
        }

    severity_weight = {"low": 25, "medium": 55, "high": 82}
    score_sum = 0.0
    conf_sum = 0.0
    used = 0

    for item in items:
        risk = item.get("risk", {}) if isinstance(item, dict) else {}
        primary = risk.get("primary", {}) if isinstance(risk, dict) else {}
        severity = str(primary.get("severity", "medium")).strip().lower()
        confidence = int(primary.get("confidence", 50) or 50)
        confidence = max(0, min(100, confidence))

        base = severity_weight.get(severity, 50)
        weighted = base * (0.45 + (confidence / 100.0) * 0.55)
        score_sum += weighted
        conf_sum += confidence
        used += 1

    avg_score = int(round(score_sum / max(used, 1)))
    avg_conf = int(round(conf_sum / max(used, 1)))

    return {
        "risk_percentage": max(0, min(100, avg_score)),
        "confidence": max(0, min(100, avg_conf)),
        "reason": "Estimated from severity/confidence fallback formula.",
        "key_drivers": ["severity_distribution", "model_confidence"],
        "method": "fallback",
    }


def estimate_company_risk_percentage(company_name: str, items: list) -> dict:
    if not items:
        return _fallback_risk_percentage_from_items(items)

    condensed = []
    for item in items[:25]:
        risk = item.get("risk", {}) if isinstance(item, dict) else {}
        relevance = risk.get("relevance", {}) if isinstance(risk, dict) else {}
        primary = risk.get("primary", {}) if isinstance(risk, dict) else {}
        political = risk.get("political", {}) if isinstance(risk, dict) else {}
        report = risk.get("report", {}) if isinstance(risk, dict) else {}

        condensed.append(
            {
                "title": str(item.get("title", ""))[:180],
                "source": str(item.get("source", ""))[:80],
                "date": item.get("date"),
                "fact_label": item.get("classification", {}).get("fact_label", "Inference"),
                "risk_relevant": relevance.get("risk_relevant", False),
                "relevance_confidence": relevance.get("confidence", 0),
                "risk_category": primary.get("category", "None"),
                "risk_severity": primary.get("severity", "low"),
                "risk_confidence": primary.get("confidence", 0),
                "political_or_macro_relevant": political.get("political_or_macro_relevant", False),
                "impact_type": political.get("impact_type", "None"),
                "buyer_summary": str(report.get("buyer_summary", ""))[:260],
            }
        )

    prompt_payload = {
        "company": company_name,
        "items_count": len(items),
        "risk_items": condensed,
    }

    try:
        service = HaikuService()
        raw = service.send_prompt(
            user_input=json.dumps(prompt_payload, ensure_ascii=False),
            system_instruction=RISK_PERCENT_SYSTEM_INSTRUCTION,
        )
        parsed = json.loads(raw)

        risk_percentage = int(parsed.get("risk_percentage", 0))
        confidence = int(parsed.get("confidence", 0))
        reason = str(parsed.get("reason", "")).strip() or "AI estimated overall supplier risk."
        key_drivers = parsed.get("key_drivers", [])
        if not isinstance(key_drivers, list):
            key_drivers = []

        return {
            "risk_percentage": max(0, min(100, risk_percentage)),
            "confidence": max(0, min(100, confidence)),
            "reason": reason,
            "key_drivers": [str(x)[:80] for x in key_drivers[:6]],
            "method": "ai",
        }
    except Exception:
        return _fallback_risk_percentage_from_items(items)


def _derive_risk_level(risk_percentage: float) -> str:
    if risk_percentage >= 67:
        return "high"
    if risk_percentage >= 34:
        return "medium"
    return "low"


def _source_quality_score(source_name: str) -> float:
    source = str(source_name or "").strip().lower()
    if not source:
        return 0.5

    high_markers = ["reuters", "bloomberg", "financial times", "wall street journal", "npr", "bbc", "gov", "court", "official"]
    low_markers = ["blog", "forum", "rumor", "rumour", "reddit", "x.com"]

    if any(marker in source for marker in high_markers):
        return 0.86
    if any(marker in source for marker in low_markers):
        return 0.34
    return 0.62


def _build_source_mix(items: list) -> dict:
    high = 0
    medium = 0
    low = 0
    for item in items:
        score = _source_quality_score(item.get("source", ""))
        if score >= 0.8:
            high += 1
        elif score <= 0.4:
            low += 1
        else:
            medium += 1
    return {"high_quality": high, "medium_quality": medium, "low_quality": low}


def _build_evidence(items: list) -> list:
    evidence = []
    for item in items:
        risk = item.get("risk", {}) if isinstance(item, dict) else {}
        primary = risk.get("primary", {}) if isinstance(risk, dict) else {}
        severity = str(primary.get("severity", "low")).lower()
        conf = int(primary.get("confidence", 0) or 0)
        sev_weight = {"low": 30, "medium": 60, "high": 85}.get(severity, 40)
        evidence_score = round(sev_weight * (0.5 + (max(0, min(100, conf)) / 100.0) * 0.5), 1)
        evidence.append(
            {
                "title": str(item.get("title", "")),
                "source": str(item.get("source", "Unknown")),
                "date": item.get("date"),
                "link": str(item.get("link", "")),
                "fact_label": item.get("classification", {}).get("fact_label", "Inference"),
                "evidence_score": evidence_score,
                "rationale": str(primary.get("reason", "Risk signal from model output."))[:240],
            }
        )
    return sorted(evidence, key=lambda x: x["evidence_score"], reverse=True)[:3]


def build_company_profile_payload(company_name: str, signal_items: list, risk_filtered_items: list, risk_overview: dict) -> dict:
    factual_count = 0
    opinion_count = 0
    inference_count = 0
    for item in risk_filtered_items:
        label = str(item.get("classification", {}).get("fact_label", "Inference"))
        if label == "Fact":
            factual_count += 1
        elif label == "Opinion":
            opinion_count += 1
        else:
            inference_count += 1

    source_mix = _build_source_mix(risk_filtered_items)
    evidence = _build_evidence(risk_filtered_items)
    first_report = ((risk_filtered_items[0].get("risk", {}).get("report", {})) if risk_filtered_items else {})

    base_risk_pct = int(risk_overview.get("risk_percentage", 50))
    base_conf = int(risk_overview.get("confidence", 40))
    safe_pct = max(0, min(100, 100 - base_risk_pct))

    status = "high_risk"
    status_label = "High risk"
    color = "red"
    if safe_pct >= 75:
        status = "safe"
        status_label = "Safe"
        color = "green"
    elif safe_pct >= 50:
        status = "watchlist"
        status_label = "Watchlist"
        color = "yellow"

    risk_overview_payload = {
        "safe_percentage": safe_pct,
        "risk_percentage": base_risk_pct,
        "confidence": base_conf,
        "status": status,
        "status_label": status_label,
        "color": color,
        "key_drivers": risk_overview.get("key_drivers", []),
        "source_mix": source_mix,
        "why_it_matters": str(first_report.get("why_it_matters", risk_overview.get("reason", ""))),
        "advice": str(first_report.get("buyer_summary", "Monitor supplier risk periodically.")),
        "report": {
            "overall_assessment": str(first_report.get("overall_assessment", "")),
            "risk_statement": str(first_report.get("risk_statement", "")),
            "political_or_macro_note": str(first_report.get("political_or_macro_note", "")),
            "buyer_summary": str(first_report.get("buyer_summary", "")),
        },
        "risk_signal": {
            "risk_relevant": len(risk_filtered_items) > 0,
            "category": str((risk_filtered_items[0].get("risk", {}).get("primary", {}).get("category", "None")) if risk_filtered_items else "None"),
            "severity": str((risk_filtered_items[0].get("risk", {}).get("primary", {}).get("severity", "low")) if risk_filtered_items else "low"),
            "confidence": int((risk_filtered_items[0].get("risk", {}).get("primary", {}).get("confidence", 0)) if risk_filtered_items else 0),
        },
        "thresholds": {"safe": 75, "watchlist": 50},
        "evidence": evidence,
    }

    fallback_profile = {
        "company_name": company_name,
        "risk_level": _derive_risk_level(base_risk_pct),
        "risk_percentage": float(base_risk_pct),
        "reputation": str(first_report.get("overall_assessment", "Insufficient risk report context.")).strip()[:280],
        "financials": {
            "signal_items_count": len(signal_items),
            "risk_filtered_count": len(risk_filtered_items),
            "fact_counts": {
                "factual": factual_count,
                "opinion": opinion_count,
                "inference": inference_count,
            },
            "risk_overview": risk_overview_payload,
        },
    }

    prompt_payload = {
        "company": company_name,
        "signal_items_count": len(signal_items),
        "risk_filtered_count": len(risk_filtered_items),
        "risk_percentage_baseline": base_risk_pct,
        "source_mix": source_mix,
        "fact_counts": {"factual": factual_count, "opinion": opinion_count, "inference": inference_count},
        "report_excerpt": first_report,
        "risk_overview": risk_overview_payload,
    }

    try:
        service = HaikuService()
        raw = service.send_prompt(
            user_input=json.dumps(prompt_payload, ensure_ascii=False),
            system_instruction=COMPANY_PROFILE_SYSTEM_INSTRUCTION,
        )
        parsed = json.loads(raw)

        risk_level = str(parsed.get("risk_level", fallback_profile["risk_level"]))
        if risk_level not in {"low", "medium", "high"}:
            risk_level = fallback_profile["risk_level"]

        risk_percentage = float(parsed.get("risk_percentage", fallback_profile["risk_percentage"]))
        risk_percentage = max(0.0, min(100.0, risk_percentage))

        reputation = str(parsed.get("reputation", fallback_profile["reputation"]))[:280]
        financials = parsed.get("financials", {})
        if not isinstance(financials, dict):
            financials = {}
        financials.setdefault("risk_overview", risk_overview_payload)

        return {
            "company_name": company_name,
            "risk_level": risk_level,
            "risk_percentage": round(risk_percentage, 2),
            "reputation": reputation,
            "financials": financials,
        }
    except Exception:
        return fallback_profile


def process_company(company_name: str) -> dict:
    result = search_news(company_name)
    news_items = result.get("news", []) if isinstance(result, dict) else []
    signal_items = signalClassifier(news_items, company_name)

    # If signal classifier filters everything out, keep a small fallback batch so
    # the company dashboard still has meaningful rows to classify and display.
    if not signal_items and news_items:
        for raw_item in news_items[:5]:
            title = raw_item.get("title", "")
            snippet = raw_item.get("snippet", "")
            source_name = raw_item.get("source", "Unknown")
            link = raw_item.get("link", "")
            date = raw_item.get("date")
            text = str(snippet or title).strip()
            if not text:
                continue

            signal_items.append(
                {
                    "company": company_name,
                    "title": title,
                    "text": text,
                    "link": link,
                    "date": date,
                    "source": source_name,
                    "classification": {
                        "label": "Signal",
                        "confidence": 0,
                        "reason": "Fallback when no signal items were detected.",
                    },
                }
            )

    signal_items = FactClassifier(signal_items)
    risk_filtered_items = apply_risk_filter(signal_items, company_name)

    # Keep a small fallback so dashboards are not empty when risk filter is strict.
    if not risk_filtered_items and signal_items:
        risk_filtered_items = signal_items[:3]

    risk_overview = estimate_company_risk_percentage(company_name, risk_filtered_items)

    inserted_rows = add_news_to_supabase(risk_filtered_items, company_name)
    company_profile = build_company_profile_payload(company_name, signal_items, risk_filtered_items, risk_overview)

    upserted_company = None
    upsert_error = None
    try:
        upserted_company = upsert_company_profile(company_profile)
    except Exception as exc:
        upsert_error = str(exc)

    return {
        "company": company_name,
        "news_inserted": len(inserted_rows),
        "items": risk_filtered_items,
        "signal_items_count": len(signal_items),
        "risk_filtered_count": len(risk_filtered_items),
        "risk_overview": risk_overview,
        "company_profile": upserted_company,
        "company_profile_error": upsert_error,
    }



if __name__ == "__main__":
    sample = process_company("eMAG Group")
    print(json.dumps(sample, ensure_ascii=False, indent=2))
