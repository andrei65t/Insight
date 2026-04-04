from NewsSearcher import search_news
from SignalNoiseClassifier import SignalNoiseClassifier
from FactOpinionInferenceClassifier import FactOpinionInferenceClassifier
import json
import html
import re
import subprocess


def signalClassifier(news_items: list, company_name: str) -> list:
    classifier = SignalNoiseClassifier()
    signal_items = []

    for item in news_items:
        title = item.get("title", "")
        text = item.get("snippet", "")
        source_name = item.get("source", "Unknown")
        link = item.get("link", "")
        date = item.get("date")

        classification = classifier.classify(
            text=text,
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
    try:
        from supabase_auth import add_news_companies
    except ModuleNotFoundError as exc:
        print(f"Supabase insert skipped (missing dependency): {exc}")
        return []

    rows = []
    for item in news_items:
        classification = item.get("classification", {})
        fact_label = str(classification.get("fact_label", "Unknown"))
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


def _fetch_link_html_with_curl(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    try:
        result = subprocess.run(
            ["curl", "-sL", url],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return result.stdout or ""
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

        page_html = _fetch_link_html_with_curl(link)
        clean_text = _html_to_clean_text(page_html)[:12000]
        if not clean_text:
            item.setdefault("classification", {})
            item["classification"]["fact_label"] = "Unknown"
            continue

        fact_result = classifier.classify(
            text=clean_text,
            source_name=source,
            source_type="news_site",
            title=title,
        )
        fact_label = str(fact_result.get("label", "Unknown"))
        item.setdefault("classification", {})
        item["classification"]["fact_label"] = fact_label

    return items


def process_company(company_name: str) -> dict:
    result = search_news(company_name)
    news_items = result.get("news", []) if isinstance(result, dict) else []
    signal_items = signalClassifier(news_items, company_name)
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
