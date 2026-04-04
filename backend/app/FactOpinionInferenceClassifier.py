import json
import re
import sys

try:
    from app.HaikuService import HaikuService
except ModuleNotFoundError:
    from HaikuService import HaikuService

class FactOpinionInferenceClassifier:
    SYSTEM_INSTRUCTION = """
You are an information classification assistant for supplier due diligence.

Classify the input as exactly one of:
- Fact
- Opinion
- Inference

Definitions:
- Fact = directly verifiable statement, attributed to an official or reputable source, or clearly supported by evidence
- Opinion = subjective judgment, prediction, commentary, speculation, or unsupported interpretation
- Inference = logical conclusion derived from facts or signals, but not directly confirmed

Rules:
1. Consider the wording, source, and source type.
2. Official filings, official reports, and attributed reporting usually support Fact.
3. Speculative wording such as 'may', 'seems', 'likely', 'probably' often suggests Opinion or Inference.
4. If the text combines evidence into a conclusion that is not directly confirmed, classify it as Inference.
5. Return strict JSON only.

JSON schema:
{"label":"Fact|Opinion|Inference","confidence":0,"reason":"short explanation"}

Confidence must be an integer between 0 and 100.
"""

    def __init__(self):
        self.ai_service = HaikuService()

    @staticmethod
    def _parse_model_json(raw_response: str) -> dict | None:
        # 1) Direct JSON
        try:
            parsed = json.loads(raw_response)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        # 2) JSON fenced block
        fenced = re.search(r"```json\s*(.*?)\s*```", raw_response, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            try:
                parsed = json.loads(fenced.group(1))
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                pass

        # 3) First decodable JSON object found inside mixed text
        decoder = json.JSONDecoder()
        for idx, ch in enumerate(raw_response):
            if ch not in "{[":
                continue
            try:
                parsed, _ = decoder.raw_decode(raw_response[idx:])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                continue

        return None

    def build_prompt(
        self,
        text: str,
        source_name: str = "Unknown",
        source_type: str = "unknown",
        title: str = "Untitled"
    ) -> str:
        return f"""
Classify the following item as Fact, Opinion, or Inference.

Examples:

Example 1:
Source: SEC Filing
Source type: official_filing
Title: Company Y reports Q3 revenue of 4.2 billion dollars
Text: Company Y reported third-quarter revenue of 4.2 billion dollars in its regulatory filing.
Output:
{{"label":"Fact","confidence":97,"reason":"Directly reported in an official regulatory filing."}}

Example 2:
Source: Financial Blog
Source type: blog
Title: Company Y is probably heading for trouble
Text: A market commentator argues that Company Y is probably heading for trouble.
Output:
{{"label":"Opinion","confidence":95,"reason":"Subjective and speculative claim without direct evidence."}}

Example 3:
Source: Industry Forum plus News Roundup
Source type: mixed_sources
Title: Multiple suppliers mention delayed payments from Company Y
Text: Three suppliers reported delayed payments from Company Y, suggesting possible financial stress, though there is no official confirmation.
Output:
{{"label":"Inference","confidence":91,"reason":"The conclusion is logically derived from signals but not officially confirmed."}}

Example 4:
Source: Reuters
Source type: news_agency
Title: Company Z files plant closure notice
Text: Reuters reported that Company Z filed an official plant closure notice with local authorities.
Output:
{{"label":"Fact","confidence":95,"reason":"Attributed reporting tied to a concrete and verifiable filing."}}

Now classify this item:

Source: {source_name}
Source type: {source_type}
Title: {title}
Text: {text}
"""

    def classify(
        self,
        text: str,
        source_name: str = "Unknown",
        source_type: str = "unknown",
        title: str = "Untitled"
    ) -> dict:
        text = text.strip()
        if not text:
            raise ValueError("Input text cannot be empty.")

        user_prompt = self.build_prompt(
            text=text,
            source_name=source_name,
            source_type=source_type,
            title=title,
        )

        raw_response = self.ai_service.send_prompt(
            user_input=user_prompt,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )

        result = self._parse_model_json(raw_response)
        if result is None:
            return {
                "label": "Unknown",
                "confidence": 0,
                "reason": "Model response was not valid JSON.",
                "raw_response": raw_response,
            }

        return result


def main() -> None:
    # Exemplu simplu de rulare din terminal
    user_input = " ".join(sys.argv[1:]).strip()
    if not user_input:
        user_input = "Company Y reported third-quarter revenue of 4.2 billion dollars in its regulatory filing."

    classifier = FactOpinionInferenceClassifier()

    try:
        result = classifier.classify(
            text=user_input,
            source_name="SEC Filing",
            source_type="official_filing",
            title="Company Y reports Q3 revenue"
        )
    except Exception as exc:
        print(f"Eroare la clasificare: {exc}")
        return

    print("Rezultat clasificare:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
