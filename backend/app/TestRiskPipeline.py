import json

from app.Classifier.RiskRelevanceClassifier import RiskRelevanceClassifier
from app.Classifier.RiskRadarClassifier import RiskRadarClassifier
from app.Classifier.PoliticalImpactClassifier import PoliticalImpactClassifier
from app.Classifier.RiskReportAggregator import RiskReportAggregator


TEST_CASES = [
    # {
    #     "company_name": "Soft 31",
    #     "source_name": "Local Business News",
    #     "source_type": "news_site",
    #     "title": "Soft 31 delays two software deliveries for manufacturing clients",
    #     "text": "Soft 31 delayed two client software deployments after a staffing shortage affected implementation teams."
    # },
    {
        "company_name": "Soft 31",
        "source_name": "Government Bulletin",
        "source_type": "official_report",
        "title": "New labor rules increase compliance requirements for staffing-heavy service providers",
        "text": "Authorities announced stricter labor compliance checks and overtime documentation requirements for staffing-heavy service providers starting next quarter."
    },
    # {
    #     "company_name": "Soft 31",
    #     "source_name": "Company Blog",
    #     "source_type": "official_company_site",
    #     "title": "Soft 31 launches new AI integration service",
    #     "text": "Soft 31 announced a new AI integration service for logistics customers."
    # },
]


def main() -> None:
    relevance_classifier = RiskRelevanceClassifier()
    risk_classifier = RiskRadarClassifier()
    political_classifier = PoliticalImpactClassifier()
    report_aggregator = RiskReportAggregator()

    all_results = []

    for case in TEST_CASES:
        print("\n" + "=" * 80)
        print(f"Company: {case['company_name']}")
        print(f"Title: {case['title']}")
        print("=" * 80)

        relevance_result = relevance_classifier.classify(
            text=case["text"],
            company_name=case["company_name"],
            source_name=case["source_name"],
            source_type=case["source_type"],
            title=case["title"],
        )
        print("1. Relevance:")
        print(json.dumps(relevance_result, ensure_ascii=False, indent=2))

        risk_result = {
            "category": "None",
            "severity": "low",
            "confidence": 0,
            "reason": "Skipped because text was not risk relevant."
        }
        political_result = {
            "political_or_macro_relevant": False,
            "impact_type": "None",
            "confidence": 0,
            "reason": "Skipped because text was not risk relevant."
        }
        report_result = None

        if relevance_result.get("risk_relevant", False):
            risk_result = risk_classifier.classify(
                text=case["text"],
                company_name=case["company_name"],
                source_name=case["source_name"],
                source_type=case["source_type"],
                title=case["title"],
            )
            print("2. Primary risk:")
            print(json.dumps(risk_result, ensure_ascii=False, indent=2))

            political_result = political_classifier.classify(
                text=case["text"],
                company_name=case["company_name"],
                source_name=case["source_name"],
                source_type=case["source_type"],
                title=case["title"],
            )
            print("3. Political/macro impact:")
            print(json.dumps(political_result, ensure_ascii=False, indent=2))

            report_result = report_aggregator.build(
                company_name=case["company_name"],
                title=case["title"],
                text=case["text"],
                relevance_result=relevance_result,
                risk_result=risk_result,
                political_result=political_result,
            )
            print("4. Risk report:")
            print(json.dumps(report_result, ensure_ascii=False, indent=2))

        all_results.append({
            "input": case,
            "relevance_result": relevance_result,
            "risk_result": risk_result,
            "political_result": political_result,
            "report_result": report_result,
        })

    # print("\n" + "#" * 80)
    # print("FINAL RESULTS")
    # print("#" * 80)
    # print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()