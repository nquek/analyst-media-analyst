import pytest
from ingestion.edgar_extractor import extract_revenue_facts

SAMPLE_FACTS = {
    "entityName": "Gap Inc.",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "label": "Revenues",
                "units": {
                    "USD": [
                        {
                            "start": "2023-02-05",
                            "end": "2024-02-03",
                            "val": 14889000000,
                            "accn": "0000039911-24-000010",
                            "form": "10-K",
                            "filed": "2024-03-19",
                            "frame": "CY2023",
                        },
                        {
                            "end": "2024-05-04",
                            "val": 3496000000,
                            "accn": "0000039911-24-000020",
                            "form": "10-Q",
                            "filed": "2024-06-07",
                        },
                        {
                            "start": "2021-01-31",
                            "end": "2022-01-29",
                            "val": 16670000000,
                            "accn": "0000039911-22-000010",
                            "form": "10-K",
                            "filed": "2022-03-15",
                        },
                    ]
                },
            },
            "NetIncomeLoss": {
                "label": "Net Income (Loss)",
                "units": {
                    "USD": [
                        {
                            "start": "2023-02-05",
                            "end": "2024-02-03",
                            "val": 502000000,
                            "accn": "0000039911-24-000010",
                            "form": "10-K",
                            "filed": "2024-03-19",
                        }
                    ]
                },
            },
        }
    },
}


def test_extracts_10k_and_10q_rows():
    rows = extract_revenue_facts(SAMPLE_FACTS)
    forms = {r["form"] for r in rows}
    assert "10-K" in forms
    assert "10-Q" in forms


def test_excludes_non_revenue_concepts():
    rows = extract_revenue_facts(SAMPLE_FACTS)
    concepts = {r["concept"] for r in rows}
    assert "NetIncomeLoss" not in concepts


def test_row_has_required_keys():
    rows = extract_revenue_facts(SAMPLE_FACTS)
    assert len(rows) > 0
    assert set(rows[0].keys()) == {
        "concept", "value", "unit", "start_date", "end_date",
        "form", "filed_date", "accn",
    }


def test_value_is_numeric():
    rows = extract_revenue_facts(SAMPLE_FACTS)
    for row in rows:
        assert isinstance(row["value"], (int, float))


def test_missing_start_becomes_none():
    rows = extract_revenue_facts(SAMPLE_FACTS)
    ten_q_rows = [r for r in rows if r["form"] == "10-Q"]
    assert len(ten_q_rows) == 1
    assert ten_q_rows[0]["start_date"] is None


def test_empty_facts_returns_empty_list():
    rows = extract_revenue_facts({"facts": {}})
    assert rows == []
