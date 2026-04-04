import os
import json
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load backend/.env even when running from backend/app
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class LinkSearcher:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing. Set it in backend/.env.")

        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        # Prefer cheapest model first, but fallback to native-search models if needed.
        self.model_candidates = [
            "google/gemma-4-26b-a4b-it",
        ]

    def _call_model(self, model_id: str, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a due-diligence web researcher for B2B partnerships.\n\n"
                        "Task:\n"
                        "Find recent and relevant public links about the company requested by the user that help evaluate whether collaboration is safe and worthwhile.\n\n"
                        "Focus on:\n"
                        "- legal/compliance issues, lawsuits, sanctions, fraud allegations\n"
                        "- financial stability signals (insolvency, layoffs, major debt, failed audits)\n"
                        "- cybersecurity incidents or data breaches\n"
                        "- reputation signals from credible media\n"
                        "- official company information (about page, leadership, reports)\n"
                        "- trusted business profiles (registries, Crunchbase/LinkedIn, etc.)\n"
                        "For each link you find, return a JSON array with the links, give at least 5 links\n"
                        "I want links with news about the company, not websites with its description"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "plugins": [{"id": "web"}],
        }
        if model_id.startswith("openai/"):
            payload["web_search_options"] = {"search_context_size": "high"}

        response = requests.post(self.endpoint, headers=headers, json=payload, timeout=90)

        if not response.ok:
            raise RuntimeError(f"{response.status_code} {response.text}")

        data = response.json()
        return self._extract_json_content(data)

    @staticmethod
    def _extract_json_content(api_response: dict) -> dict:
        content = api_response["choices"][0]["message"]["content"]
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise ValueError("Unexpected content type in model response.")

        cleaned = content.strip()
        match = re.search(r"```json\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()

        return json.loads(cleaned)

    @staticmethod
    def _looks_like_cutoff_response(text: str | dict) -> bool:
        lowered = text.lower() if isinstance(text, str) else json.dumps(text).lower()
        return (
            "knowledge cutoff" in lowered
            or "my knowledge is current up to" in lowered
            or "up to october 2023" in lowered
            or "up to 2023" in lowered
        )

    def search_company_info(self, prompt: str) -> dict:
        last_error = ""

        for model in self.model_candidates:
            try:
                result = self._call_model(model, prompt)
                if self._looks_like_cutoff_response(result):
                    raise RuntimeError("Model returned cutoff-style response (no live web retrieval).")
                print(f"Model used: {model}")
                return result
            except Exception as exc:
                last_error = f"Model {model} failed: {exc}"
                print(last_error)

        raise RuntimeError(f"All model candidates failed. Last error: {last_error}")


if __name__ == "__main__":
    # Editeaza promptul direct aici
    PROMPT = "Cauta pe net si da-mi numele legal al companiei Soft 31. Daca sunt mai multe variante, afiseaza le pe toate, cu un link langa, una sub alta" 
    "What is the latest date you give information from?"

    scraper = LinkSearcher()
    result = scraper.search_company_info(PROMPT)
    print("\n=== WEB RESEARCH RESULT ===\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
