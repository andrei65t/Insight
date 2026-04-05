if __package__:
    from app.NewsSearcher import search_news
    from app.Classifier.SignalNoiseClassifier import SignalNoiseClassifier
    from app.Classifier.FactOpinionInferenceClassifier import FactOpinionInferenceClassifier
    from app.supabase_auth import add_news_companies
else:
    from NewsSearcher import search_news
    from Classifier.SignalNoiseClassifier import SignalNoiseClassifier
    from Classifier.FactOpinionInferenceClassifier import FactOpinionInferenceClassifier
    from supabase_auth import add_news_companies
import json
import html
import re
import requests
import os
from dotenv import load_dotenv

load_dotenv()


HF_SUMMARY_API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-cnn"


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
    inserted_rows = add_news_to_supabase(signal_items, company_name)

    return {
        "company": company_name,
        "news_inserted": len(inserted_rows),
        "items": signal_items,
    }



if __name__ == "__main__":
    sample = process_company("eMAG Group")
    print(json.dumps(sample, ensure_ascii=False, indent=2))
