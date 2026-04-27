from unittest.mock import patch, MagicMock
import ingestion.edgar_to_snowflake as edgar_module

SAMPLE_JSON = {
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
                        }
                    ]
                },
            }
        }
    },
}


def _make_conn_mock():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


def _set_snowflake_env(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "test_account")
    monkeypatch.setenv("SNOWFLAKE_USER", "test_user")
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "test_password")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "test_database")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "test_warehouse")
    monkeypatch.setenv("SNOWFLAKE_ROLE", "test_role")


def test_main_calls_edgar_url(monkeypatch):
    _set_snowflake_env(monkeypatch)
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_JSON
    mock_resp.raise_for_status = MagicMock()
    conn, _ = _make_conn_mock()

    with patch("ingestion.edgar_to_snowflake.requests.get", return_value=mock_resp) as mock_get, \
         patch("snowflake.connector.connect", return_value=conn):
        edgar_module.main()

    url = mock_get.call_args[0][0]
    assert "CIK0000039911" in url


def test_main_writes_to_snowflake(monkeypatch):
    _set_snowflake_env(monkeypatch)
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_JSON
    mock_resp.raise_for_status = MagicMock()
    conn, cursor = _make_conn_mock()

    with patch("ingestion.edgar_to_snowflake.requests.get", return_value=mock_resp), \
         patch("snowflake.connector.connect", return_value=conn):
        edgar_module.main()

    assert cursor.execute.called
    all_sql = [c[0][0] for c in cursor.execute.call_args_list]
    assert any("gap_financials_raw" in sql for sql in all_sql)


def test_main_closes_connection_on_error(monkeypatch):
    _set_snowflake_env(monkeypatch)
    mock_resp = MagicMock()
    mock_resp.json.return_value = SAMPLE_JSON
    mock_resp.raise_for_status = MagicMock()
    conn, cursor = _make_conn_mock()
    cursor.execute.side_effect = Exception("Snowflake error")

    with patch("ingestion.edgar_to_snowflake.requests.get", return_value=mock_resp), \
         patch("snowflake.connector.connect", return_value=conn):
        try:
            edgar_module.main()
        except Exception:
            pass

    conn.close.assert_called_once()
