from app.LinkSearcher import LinkSearcher
import json

def process_company(company_name: str) -> dict:
    linksearcher = LinkSearcher()
    result = linksearcher.search_company_info(company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sample = process_company("Example Company")
    print(sample)
