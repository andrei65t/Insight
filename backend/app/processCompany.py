from NewsSearcher import search_news
from SignalNoiseClassifier import SignalNoiseClassifier
import json


def signalClassifier(news_items: list, company_name: str) -> list:
    classifier = SignalNoiseClassifier()
    signal_items = []

    for item in news_items:
        title = item.get("title", "")
        text = item.get("snippet", "")
        source_name = item.get("source", "Unknown")

        classification = classifier.classify(
            text=text,
            source_name=source_name,
            title=title,
            company=company_name,
        )

        if str(classification.get("label", "")).strip().lower() != "signal":
            continue

        signal_items.append(
            {
                "company": company_name,
                "title": title,
                "text": text,
                "source": source_name,
                "classification": classification,
            }
        )

    return signal_items


def process_company(company_name: str) -> dict:
    result = search_news(company_name)
    news_items = result.get("news", []) if isinstance(result, dict) else []
    signal_items = signalClassifier(news_items, company_name)

    return {
        "company": company_name,
        "items": signal_items,
    }



if __name__ == "__main__":
    sample = process_company("eMAG Group")
    print(json.dumps(sample, ensure_ascii=False, indent=2))
