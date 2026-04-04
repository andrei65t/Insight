import json
import sys

from HaikuService import HaikuService


class RiskRadarClassifier:
    SYSTEM_INSTRUCTION = """
You are a supplier risk analyst for procurement intelligence.

Classify the primary risk in the input as exactly one of:
- Financial
- Operational
- Reputation
- Legal
- Compliance
- Cyber
- Geographic
- None

Also assign exactly one severity:
- low
- medium
- high

Definitions:
- Financial = risks related to revenue decline, credit quality, payment issues, insolvency, or financial instability
- Operational = risks related to factory shutdowns, labor shortages, service disruption, delivery issues, or supply continuity
- Reputation = risks related to public criticism, scandals, negative publicity, or trust erosion
- Legal = risks related to lawsuits, court filings, disputes, or legal proceedings
- Compliance = risks related to regulatory review, labor law issues, sanctions, or policy violations
- Cyber = risks related to data breaches, ransomware, cyber incidents, or security failures
- Geographic = risks related to war, sanctions, natural disasters, political instability, or regional disruption
- None = no meaningful supplier-relevant risk is present

Rules:
1. Choose the single most important risk category.
2. Consider source, wording, and business impact.
3. If the information is weak, generic, or not clearly risky, use lower confidence and lower severity.
4. If no meaningful risk is present, return category None and severity low.
5. Return strict JSON only.

JSON schema:
{"category":"Financial|Operational|Reputation|Legal|Compliance|Cyber|Geographic|None","severity":"low|medium|high","confidence":0,"reason":"short explanation"}

Confidence must be an integer between 0 and 100.
"""

    def __init__(self):
        self.ai_service = HaikuService()

    def build_prompt(
        self,
        text: str,
        source_name: str = "Unknown",
        source_type: str = "unknown",
        title: str = "Untitled"
    ) -> str:
        return f"""
Classify the primary supplier-relevant risk and severity.

Examples:

Example 1:
Source: Local Press
Source type: news_site
Title: Company Z shuts factory after flooding
Text: Flooding caused a two-week shutdown at one of Company Z's manufacturing plants.
Output:
{{"category":"Operational","severity":"high","confidence":95,"reason":"Direct production disruption may affect supply continuity."}}

Example 2:
Source: Court Filing
Source type: legal_registry
Title: Environmental damages lawsuit filed against Company Z
Text: A lawsuit seeking damages for environmental harm was filed against Company Z last month.
Output:
{{"category":"Legal","severity":"medium","confidence":94,"reason":"Formal legal dispute may affect trust and cost."}}

Example 3:
Source: Rating Agency Report
Source type: official_report
Title: Company Z downgraded from A to BBB
Text: A rating agency downgraded Company Z's credit rating from A to BBB.
Output:
{{"category":"Financial","severity":"high","confidence":97,"reason":"Credit downgrade may reduce financial resilience."}}

Example 4:
Source: Technology Blog
Source type: blog
Title: Company Z rumored to have suffered data breach
Text: One technology blog claimed Company Z may have experienced a data breach, but no confirmation has been provided.
Output:
{{"category":"Cyber","severity":"low","confidence":68,"reason":"Potential cyber risk mentioned, but unconfirmed."}}

Example 5:
Source: Company Press Release
Source type: official_company_site
Title: Company Z launches community education initiative
Text: Company Z announced a new education initiative in partnership with local schools.
Output:
{{"category":"None","severity":"low","confidence":93,"reason":"No meaningful supplier risk is indicated."}}

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

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            return {
                "category": "None",
                "severity": "low",
                "confidence": 0,
                "reason": "Model response was not valid JSON.",
                "raw_response": raw_response,
            }

        return result


def main() -> None:
    user_input = " ".join(sys.argv[1:]).strip()
    if not user_input:
        user_input = "Flooding caused a two-week shutdown at one of Company Z's manufacturing plants."

    classifier = RiskRadarClassifier()

    try:
        result = classifier.classify(
            text=user_input,
            source_name="Local Press",
            source_type="news_site",
            title="Company Z shuts factory after flooding"
        )
    except Exception as exc:
        print(f"Eroare la clasificare: {exc}")
        return

    print("Rezultat clasificare:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()