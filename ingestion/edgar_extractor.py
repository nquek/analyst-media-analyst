REVENUE_CONCEPTS = [
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
]

VALID_FORMS = {"10-K", "10-Q"}


def extract_revenue_facts(companyfacts: dict) -> list[dict]:
    rows = []
    us_gaap = companyfacts.get("facts", {}).get("us-gaap", {})

    for concept in REVENUE_CONCEPTS:
        if concept not in us_gaap:
            continue
        usd_entries = us_gaap[concept].get("units", {}).get("USD", [])
        for entry in usd_entries:
            if entry.get("form") not in VALID_FORMS:
                continue
            rows.append({
                "concept": concept,
                "value": entry["val"],
                "unit": "USD",
                "start_date": entry.get("start"),
                "end_date": entry.get("end"),
                "form": entry["form"],
                "filed_date": entry.get("filed"),
                "accn": entry["accn"],
            })
    return rows
