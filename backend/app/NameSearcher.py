import os
import json
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load backend/.env even when running from backend/app
load_dotenv()


class NameSearcher:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing. Set it in backend/.env.")

        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        # Prefer cheapest model first, but fallback to native-search models if needed.
        self.model_candidates = [
            "google/gemma-4-26b-a4b-it",
        ]

    def _query_model(self, model_id: str, prompt: str) -> str:
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
                        "Find the official registered legal name of the company the user requested in JSON format in a vector node named contenders.\n"
                        "including legal suffix\n"
                        "For example: Mister Delivery SRL"
                        "If there are more of them put all of them in the JSON.\n"
                        "If the requested input is not a company name, return a JSON node 'error' saying 'you can only search companies'\n"
                        "In each contender node, return just the legal name of the company and their website.\n"
                        "Return the candidates from all countries\n"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "plugins": [{"id": "web"}],
            "web_search_options": {"search_context_size": "high"},
        }

        response = requests.post(self.endpoint, headers=headers, json=payload, timeout=90)

        if not response.ok:
            raise RuntimeError(f"{response.status_code} {response.text}")

        data = response.json()
        return data

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

    def search_web_info(self, prompt: str) -> dict:
        last_error = ""

        for model in self.model_candidates:
            try:
                result = self._query_model(model, prompt)
                print(f"Model used: {model}")
                return result
            except Exception as exc:
                last_error = f"Model {model} failed: {exc}"
                print(last_error)

        raise RuntimeError(f"All model candidates failed. Last error: {last_error}")


if __name__ == "__main__":
    # Editeaza promptul direct aici
    PROMPT = "SOFT 31"

    searcher = NameSearcher()
    result = searcher.search_web_info(PROMPT)
    print(json.dumps(searcher._extract_json_content(result), ensure_ascii=False, indent=2))
