import requests
import json

def search_news(company_name):
    url = "https://google.serper.dev/news"
    payload = {
        "q": company_name + " after:2025-01-01",
        "num": 10,
        "page": 1,
    }
    headers = {
        'X-API-KEY': '3a29d67d1c639a367127544232f00f3bbb4c89a0',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, json=payload)

    rezultat_json = response.json()

    if "news" in rezultat_json:
        for stire in rezultat_json["news"]:
            stire.pop("imageUrl", None)

    #print(json.dumps(rezultat_json, indent=4, ensure_ascii=False))
    return rezultat_json


if __name__ == "__main__":
    search_news()
