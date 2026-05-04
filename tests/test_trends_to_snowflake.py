import pandas as pd
from unittest.mock import MagicMock, patch

from ingestion.trends_to_snowflake import BRANDS, fetch_trends


def test_brands_list_has_eight_entries():
    assert len(BRANDS) == 8


def test_fetch_trends_returns_rows():
    mock_df = pd.DataFrame(
        {"Old Navy": [80, 60], "isPartial": [False, False]},
        index=pd.to_datetime(["2024-01-07", "2024-01-14"]),
    )
    mock_pytrends = MagicMock()
    mock_pytrends.interest_over_time.return_value = mock_df

    with patch("ingestion.trends_to_snowflake.TrendReq", return_value=mock_pytrends):
        rows = fetch_trends("Old Navy")

    assert len(rows) == 2
    assert rows[0]["brand_term"] == "Old Navy"
    assert rows[0]["interest_value"] == 80
    assert rows[0]["geo"] == "US"


def test_fetch_trends_skips_partial_weeks():
    mock_df = pd.DataFrame(
        {"Gap": [50, 30], "isPartial": [False, True]},
        index=pd.to_datetime(["2024-01-07", "2024-01-14"]),
    )
    mock_pytrends = MagicMock()
    mock_pytrends.interest_over_time.return_value = mock_df

    with patch("ingestion.trends_to_snowflake.TrendReq", return_value=mock_pytrends):
        rows = fetch_trends("Gap")

    assert len(rows) == 1


def test_fetch_trends_returns_empty_on_no_data():
    mock_pytrends = MagicMock()
    mock_pytrends.interest_over_time.return_value = pd.DataFrame()

    with patch("ingestion.trends_to_snowflake.TrendReq", return_value=mock_pytrends):
        rows = fetch_trends("Unknown Brand")

    assert rows == []
