if __package__:
    from app.NewsSearcher import search_news
    from app.SignalNoiseClassifier import SignalNoiseClassifier
    from app.FactOpinionInferenceClassifier import FactOpinionInferenceClassifier
    from app.supabase_auth import add_news_companies
else:
    from NewsSearcher import search_news
    from SignalNoiseClassifier import SignalNoiseClassifier
    from FactOpinionInferenceClassifier import FactOpinionInferenceClassifier
    from supabase_auth import add_news_companies
import json
import html
import re
import requests


def signalClassifier(news_items: list, company_name: str) -> list:
    classifier = SignalNoiseClassifier()
    signal_items = []

    for item in news_items:
        title = item.get("title", "")
        text = item.get("snippet", "")
        source_name = item.get("source", "Unknown")
        link = item.get("link", "")
        date = item.get("date")

        # Some providers return empty snippet; fallback to title so the signal model can still run.
        classify_text = str(text or title).strip()
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
                "text": text,
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


def FactClassifier(items: list) -> list:
    classifier = FactOpinionInferenceClassifier()

    for item in items:
        title = item.get("title", "Untitled")
        source = item.get("source", "Unknown")
        link = item.get("link", "")

        page_html = _fetch_link_html(link)
        clean_text = _html_to_clean_text(page_html)[:12000]

        # If article text cannot be fetched/parsing fails, fallback to snippet/title to still run classification.
        if not clean_text:
            fallback_text = str(item.get("text") or title).strip()
            clean_text = fallback_text[:12000]

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
