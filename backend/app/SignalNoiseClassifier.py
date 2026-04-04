import json
import sys

try:
    from app.HaikuService import HaikuService
except ModuleNotFoundError:
    from HaikuService import HaikuService


class SignalNoiseClassifier:
    SYSTEM_INSTRUCTION = """
You are a procurement intelligence assistant for supplier monitoring.

Classify the input as exactly one of:
- Signal
- Noise

Definitions:
- Signal = specific, relevant information that may affect supplier trust, continuity, operations, compliance, or reputation
- Noise = generic, low-impact, promotional, weakly relevant, or broad information with little decision value

Rules:
1. Consider recency, specificity, and business impact.
2. Prefer company-specific events over general industry commentary.
3. Operational, legal, compliance, cyber, financial, or reputational developments usually indicate Signal.
4. Promotional, branding, CSR, or generic trend content usually indicates Noise unless it clearly affects supplier reliability.
5. Return strict JSON only.

JSON schema:
{"label":"Signal|Noise","confidence":0,"reason":"short explanation"}

Confidence must be an integer between 0 and 100.
"""

    def __init__(self):
        self.ai_service = HaikuService()

    def build_prompt(
        self,
        text: str,
        source_name: str = "Unknown",
        source_type: str = "unknown",
        title: str = "Untitled",
        company: str = "Unknown",
    ) -> str:
        return f"""
Classify the following item as Signal or Noise.

Examples:

Example 1:
Source: Reuters
Source type: news_agency
Title: Company X shuts factory in Vietnam due to flooding
Text: Company X temporarily closed a production facility after severe flooding disrupted operations.
Output:
{{"label":"Signal","confidence":95,"reason":"Direct company-specific operational disruption with supply impact."}}

Example 2:
Source: Industry Blog
Source type: blog
Title: Top 10 supply chain trends for 2026
Text: Analysts discuss broad supply chain themes expected to shape the market next year.
Output:
{{"label":"Noise","confidence":96,"reason":"Generic industry commentary, not specific to the supplier."}}

Example 3:
Source: Local News
Source type: news_site
Title: Company X investigated for labor law violations
Text: Local authorities opened an investigation into possible labor law breaches involving Company X.
Output:
{{"label":"Signal","confidence":94,"reason":"Company-specific legal and reputational issue with business relevance."}}

Example 4:
Source: Company Website
Source type: official_company_site
Title: Company X sponsors local marathon
Text: Company X announced sponsorship of a community marathon event this weekend.
Output:
{{"label":"Noise","confidence":93,"reason":"Low business relevance for supplier risk or continuity assessment."}}

Now classify this item:

Source: {source_name}
Source type: {source_type}
Company: {company}
Title: {title}
Text: {text}
"""

    def classify(
        self,
        text: str,
        source_name: str = "Unknown",
        title: str = "Untitled",
        company: str = "Untitled",
        link: str = "",
    ) -> dict:
        text = text.strip()
        if not text:
            raise ValueError("Input text cannot be empty.")

        user_prompt = self.build_prompt(
            text=text,
            source_name=source_name,
            title=title,
            company=company,
        )

        raw_response = self.ai_service.send_prompt(
            user_input=user_prompt,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            return {
                "label": "Unknown",
                "confidence": 0,
                "reason": "Model response was not valid JSON.",
                "link": link,
                "raw_response": raw_response,
            }

        result["link"] = link
        return result


def main() -> None:
    user_input = " ".join(sys.argv[1:]).strip()
    if not user_input:
        user_input = "Company X sponsored a local hackathon for University Politehnica of Bucharest students."

    classifier = SignalNoiseClassifier()

    try:
        result = classifier.classify(
            text=user_input,
            source_name="Reuters",
            title="Company X shuts factory in Vietnam due to flooding",
            company = "X"
        )
    except Exception as exc:
        print(f"Eroare la clasificare: {exc}")
        return

    print("Rezultat clasificare:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
