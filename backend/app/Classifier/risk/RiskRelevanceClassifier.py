import json
import sys

try:
    from app.HaikuService import HaikuService
except ModuleNotFoundError:
    from HaikuService import HaikuService


class RiskRelevanceClassifier:
    SYSTEM_INSTRUCTION = """
You are a supplier risk triage assistant.

Classify the input as:
- risk_relevant = true if it contains meaningful information for supplier risk assessment
- risk_relevant = false if it is generic, promotional, weakly relevant, or not useful for supplier risk assessment

Definitions:
- risk_relevant = information that may affect supplier continuity, trust, operations, legal exposure, compliance, cyber posture, financial stability, or reputation
- not risk_relevant = branding, generic market commentary, awards, community events, product promotion, or vague mentions without decision value

Rules:
1. Focus on supplier risk relevance, not general company relevance.
2. Delivery issues, labor shortages, legal disputes, cyber incidents, regulatory review, payment issues, negative publicity, or operational disruption usually indicate true.
3. CSR, sponsorship, general innovation messaging, generic market trends, or weak mentions usually indicate false.
4. Return strict JSON only.

JSON schema:
{"risk_relevant":true,"confidence":0,"reason":"short explanation"}

Confidence must be an integer between 0 and 100.
"""

    def __init__(self):
        self.ai_service = HaikuService()

    def build_prompt(
        self,
        text: str,
        company_name: str = "Unknown",
        source_name: str = "Unknown",
        source_type: str = "unknown",
        title: str = "Untitled"
    ) -> str:
        return f"""
Determine whether the following item is relevant for supplier risk assessment.

Examples:

Example 1:
Company: Company X
Source: Reuters
Source type: news_agency
Title: Company X shuts factory in Vietnam due to flooding
Text: Company X temporarily closed a production facility after severe flooding disrupted operations.
Output:
{{"risk_relevant":true,"confidence":96,"reason":"Operational disruption affects continuity."}}

Example 2:
Company: Company X
Source: Company Website
Source type: official_company_site
Title: Company X sponsors local marathon
Text: Company X announced sponsorship of a community marathon event this weekend.
Output:
{{"risk_relevant":false,"confidence":94,"reason":"Low relevance to supplier risk."}}

Example 3:
Company: Company Y
Source: Court Registry
Source type: legal_registry
Title: Contract dispute filed against Company Y
Text: A contract dispute was filed against Company Y regarding delayed implementation obligations.
Output:
{{"risk_relevant":true,"confidence":97,"reason":"Legal dispute may affect trust and delivery."}}

Example 4:
Company: Company Z
Source: Industry Blog
Source type: blog
Title: Top 10 supply chain trends for 2026
Text: Analysts discuss broad supply chain themes expected to shape the market next year.
Output:
{{"risk_relevant":false,"confidence":95,"reason":"Generic commentary, not company-specific."}}

Now classify this item:

Company: {company_name}
Source: {source_name}
Source type: {source_type}
Title: {title}
Text: {text}
"""

    def classify(
        self,
        text: str,
        company_name: str = "Unknown",
        source_name: str = "Unknown",
        source_type: str = "unknown",
        title: str = "Untitled"
    ) -> dict:
        text = text.strip()
        if not text:
            raise ValueError("Input text cannot be empty.")

        user_prompt = self.build_prompt(
            text=text,
            company_name=company_name,
            source_name=source_name,
            source_type=source_type,
            title=title,
        )

        raw_response = self.ai_service.send_prompt(
            user_input=user_prompt,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )

        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            return {
                "risk_relevant": False,
                "confidence": 0,
                "reason": "Model response was not valid JSON.",
                "raw_response": raw_response,
            }


def main() -> None:
    user_input = " ".join(sys.argv[1:]).strip()
    if not user_input:
        user_input = "Company X temporarily closed a production facility after severe flooding disrupted operations."

    classifier = RiskRelevanceClassifier()

    result = classifier.classify(
        text=user_input,
        company_name="Company X",
        source_name="Reuters",
        source_type="news_agency",
        title="Company X shuts factory in Vietnam due to flooding",
    )

    print("Rezultat relevanță risc:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()