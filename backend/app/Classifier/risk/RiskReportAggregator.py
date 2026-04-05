import json
import sys

try:
    from app.HaikuService import HaikuService
except ModuleNotFoundError:
    from HaikuService import HaikuService


class RiskReportAggregator:
    SYSTEM_INSTRUCTION = """
You are a procurement risk reporting assistant.

Your task is to create a short, business-friendly supplier risk report based only on the structured inputs provided.

Rules:
1. Use plain business language.
2. Be concise and specific.
3. Mention whether the item is risk relevant.
4. Mention the primary risk category and severity if relevant.
5. Mention political or macro impact only if it is relevant.
6. Explain why the item matters for supplier reliability, continuity, trust, cost, or compliance.
7. Return strict JSON only.

JSON schema:
{
  "overall_assessment":"string",
  "risk_statement":"string",
  "political_or_macro_note":"string",
  "why_it_matters":"string",
  "buyer_summary":"string"
}
"""

    def __init__(self):
        self.ai_service = HaikuService()

    def build_prompt(
        self,
        company_name: str,
        title: str,
        text: str,
        relevance_result: dict,
        risk_result: dict,
        political_result: dict
    ) -> str:
        return f"""
Create a short supplier risk report using only the inputs below.

Company: {company_name}
Title: {title}
Text: {text}

Relevance result:
{json.dumps(relevance_result, ensure_ascii=False, indent=2)}

Primary risk result:
{json.dumps(risk_result, ensure_ascii=False, indent=2)}

Political/macro result:
{json.dumps(political_result, ensure_ascii=False, indent=2)}

Return JSON only.
"""

    def build(
        self,
        company_name: str,
        title: str,
        text: str,
        relevance_result: dict,
        risk_result: dict,
        political_result: dict
    ) -> dict:
        user_prompt = self.build_prompt(
            company_name=company_name,
            title=title,
            text=text,
            relevance_result=relevance_result,
            risk_result=risk_result,
            political_result=political_result,
        )

        raw_response = self.ai_service.send_prompt(
            user_input=user_prompt,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )

        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            return {
                "overall_assessment": "Could not build structured report.",
                "risk_statement": "Model response was not valid JSON.",
                "political_or_macro_note": "",
                "why_it_matters": "",
                "buyer_summary": raw_response,
            }


def main() -> None:
    aggregator = RiskReportAggregator()

    relevance_result = {
        "risk_relevant": True,
        "confidence": 95,
        "reason": "Delivery disruption affects continuity."
    }

    risk_result = {
        "category": "Operational",
        "severity": "medium",
        "confidence": 89,
        "reason": "Staffing shortage delayed client delivery."
    }

    political_result = {
        "political_or_macro_relevant": True,
        "impact_type": "Compliance",
        "confidence": 88,
        "reason": "Regulatory change may increase labor compliance burden."
    }

    result = aggregator.build(
        company_name="Soft 31",
        title="Soft 31 delays two client software deliveries",
        text="Soft 31 delayed two software deliveries after staffing shortages affected implementation teams.",
        relevance_result=relevance_result,
        risk_result=risk_result,
        political_result=political_result,
    )

    print("Risk report:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()