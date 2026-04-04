import os
import requests
from dotenv import load_dotenv

load_dotenv()


class HaikuService:
    def __init__(self, api_key: str | None = None, model_id: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing! Check your .env file.")

        self.base_url = "https://openrouter.ai/api/v1"
        self.model_id = model_id or "anthropic/claude-3-haiku"
        # Pentru testare gratuită puteți încerca și:
        # self.model_id = "openrouter/free"

    def send_prompt(self, user_input: str, system_instruction: str | None = None) -> str:
        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": user_input})

        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": 0.1,
        }

        try:
            response = requests.post(
                url=endpoint,
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()
            usage = data.get("usage", {})

            print("\n--- Metrice Consum Model ---")
            print(f"Model:  {self.model_id}")
            print(f"Input:  {usage.get('prompt_tokens', 'n/a')} tokeni")
            print(f"Output: {usage.get('completion_tokens', 'n/a')} tokeni")
            print("----------------------------\n")

            return data["choices"][0]["message"]["content"]

        except requests.RequestException as e:
            print(f"LOG Request Error: {e}")
            raise RuntimeError(f"API request failed: {e}") from e
        except KeyError as e:
            print(f"LOG Response Parse Error: {e}")
            raise RuntimeError(f"Unexpected API response format: {e}") from e


if __name__ == "__main__":
    ai = HaikuService()
    raspuns = ai.send_prompt("Salut, cum te cheama si ce poti face?")
    print(raspuns)