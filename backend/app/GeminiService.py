import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiService:
    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.getenv("AI_API_KEY")
        if not api_key:
            raise ValueError("AI_API_KEY is missing! Check your .env file.")
        self.client = genai.Client(api_key=api_key)

    def send_prompt(self, user_input: str, system_instruction: str | None = None) -> str:
        try:
            config = {
                "response_mime_type": "application/json",
                "temperature": 0.3,
            }
            if system_instruction:
                config["system_instruction"] = system_instruction

            response = self.client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=user_input,
                config=config,
            )

            usage = response.usage_metadata
            print("\n--- Metrice Consum Gemini ---")
            print(f"Input:  {usage.prompt_token_count} tokeni")
            print(f"Output: {usage.candidates_token_count} tokeni")
            print("-----------------------------\n")

            return response.text

        except Exception as e:
            print(f"LOG Gemini Error: {e}")
            raise RuntimeError(f"Gemini API Failure: {e}") from e


if __name__ == "__main__":
    service = GeminiService()

    prompt_test = "Spune pe scurt ce este invatarea automata"
    result = service.send_prompt(prompt_test)
    print("Rezultat JSON:", result)
