import json
import sys

from GeminiService import GeminiService


class PoliticalImpactClassifier:
    SYSTEM_INSTRUCTION = """
You are a political and macro impact classifier for supplier risk analysis.

Classify whether the input describes a political, regulatory, macroeconomic, or geopolitical development that may affect the company.

Fields:
- political_or_macro_relevant = true or false
- impact_type = one of: Geographic, Compliance, Legal, Operational, Financial, None

Definitions:
- Geographic = war, sanctions, natural disasters, regional instability, border disruption, trade restrictions, election-related instability
- Compliance = regulation, labor law changes, policy obligations, regulatory review, sanctions compliance
- Legal = government legal action, public procurement disputes, enforcement, regulatory lawsuits
- Operational = political or regulatory events affecting delivery, staffing, logistics, manufacturing, or service continuity
- Financial = tariffs, taxes, macro shocks, restrictions, or government action affecting financial performance
- None = no meaningful political or macro impact

Rules:
1. Only mark true if there is a meaningful political, regulatory, macro, or geopolitical connection.
2. Generic company problems without political or macro context should be false.
3. Return strict JSON only.
4. If political_or_macro_relevant is false, impact_type must be None.

JSON schema:
{"political_or_macro_relevant":false,"impact_type":"Geographic|Compliance|Legal|Operational|Financial|None","confidence":0,"reason":"short explanation"}

Confidence must be an integer between 0 and 100.
"""

    def __init__(self):
        self.ai_service = GeminiService()

    def build_prompt(
        self,
        text: str,
        company_name: str = "Unknown",
        source_name: str = "Unknown",
        source_type: str = "unknown",
        title: str = "Untitled"
    ) -> str:
        return f"""
Determine whether this item contains political, regulatory, macroeconomic, or geopolitical impact relevant to the company.

Examples:

Example 1:
Company: Company X
Source: Government News
Source type: official_report
Title: New labor regulation increases overtime compliance checks
Text: Authorities announced stricter overtime enforcement for staffing providers starting next quarter.
Output:
{{"political_or_macro_relevant":true,"impact_type":"Compliance","confidence":96,"reason":"Regulatory change may increase compliance burden."}}

Example 2:
Company: Company X
Source: International News
Source type: news_site
Title: Flooding disrupts transport routes in supplier region
Text: Severe flooding disrupted transport and industrial operations in a region where Company X has delivery partners.
Output:
{{"political_or_macro_relevant":true,"impact_type":"Geographic","confidence":92,"reason":"Regional disruption may affect operations."}}

Example 3:
Company: Company X
Source: Public Procurement Journal
Source type: news_site
Title: State contract award challenged in court
Text: A state procurement award involving Company X was challenged in court by a competing bidder.
Output:
{{"political_or_macro_relevant":true,"impact_type":"Legal","confidence":94,"reason":"Public-sector legal dispute may affect contracts."}}

Example 4:
Company: Company X
Source: Company Blog
Source type: official_company_site
Title: Company X launches new analytics platform
Text: Company X announced a new analytics platform for enterprise customers.
Output:
{{"political_or_macro_relevant":false,"impact_type":"None","confidence":95,"reason":"No political or macro factor present."}}

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
            result = json.loads(raw_response)

            if result.get("political_or_macro_relevant") is False:
                result["impact_type"] = "None"
            
            return result
        except json.JSONDecodeError:
            return {
                "political_or_macro_relevant": False,
                "impact_type": "None",
                "confidence": 0,
                "reason": "Model response was not valid JSON.",
                "raw_response": raw_response,
            }


def main() -> None:
    user_input = " ".join(sys.argv[1:]).strip()
    if not user_input:
        user_input = "Authorities announced stricter overtime enforcement for staffing providers starting next quarter."

    classifier = PoliticalImpactClassifier()

    result = classifier.classify(
        text=user_input,
        company_name="Company X",
        source_name="Government News",
        source_type="official_report",
        title="New labor regulation increases overtime compliance checks",
    )

    print("Rezultat impact politic/macro:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()