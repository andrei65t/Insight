import requests
import json
from datetime import datetime, timedelta, timezone
import os

def _normalize_news_date(raw_date: str) -> str | None:
    if not raw_date:
        return None

    value = raw_date.strip()
    if not value:
        return None

    lowered = value.lower()
    today = datetime.now(timezone.utc).date()

    if lowered == "today":
        return today.isoformat()
    if lowered == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    relative_match = None
    import re

    relative_match = re.match(r"^(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago$", lowered)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        days_map = {
            "minute": 0,
            "hour": 0,
            "day": 1,
            "week": 7,
            "month": 30,
            "year": 365,
        }
        return (today - timedelta(days=amount * days_map[unit])).isoformat()

    normalized = value.replace("Sept ", "Sep ")
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(normalized, fmt).date().isoformat()
        except ValueError:
            continue

    return None

def search_news(company_name):
    url = "https://google.serper.dev/news"
    payload = {
        "q": company_name + " after:2025-01-01",
        "num": 10,
        "page": 1,
    }
    headers = {
        'X-API-KEY': os.getenv("X_API_KEY"),
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, json=payload)

    rezultat_json = response.json()

    if "news" in rezultat_json:
        for stire in rezultat_json["news"]:
            stire.pop("imageUrl", None)
            stire["date"] = _normalize_news_date(str(stire.get("date", "")))

    #print(json.dumps(rezultat_json, indent=4, ensure_ascii=False))
    return rezultat_json


if __name__ == "__main__":
    search_news()
