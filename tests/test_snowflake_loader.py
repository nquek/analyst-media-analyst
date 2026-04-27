from unittest.mock import MagicMock
from ingestion.snowflake_loader import create_table, load_rows

SAMPLE_ROWS = [
    {
        "concept": "Revenues",
        "value": 14889000000,
        "unit": "USD",
        "start_date": "2023-02-05",
        "end_date": "2024-02-03",
        "form": "10-K",
        "filed_date": "2024-03-19",
        "accn": "0000039911-24-000010",
    }
]


def _make_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


def test_create_table_runs_ddl():
    conn, cursor = _make_conn()
    create_table(conn)
    cursor.execute.assert_called_once()
    sql = cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "gap_financials_raw" in sql


def test_load_rows_truncates_before_insert():
    conn, cursor = _make_conn()
    load_rows(conn, SAMPLE_ROWS)
    calls = [c[0][0] for c in cursor.execute.call_args_list]
    assert any("TRUNCATE" in sql for sql in calls)
    truncate_idx = next(i for i, sql in enumerate(calls) if "TRUNCATE" in sql)
    insert_idx = next(i for i, sql in enumerate(calls) if "INSERT" in sql)
    assert truncate_idx < insert_idx


def test_load_rows_inserts_one_row_per_entry():
    conn, cursor = _make_conn()
    load_rows(conn, SAMPLE_ROWS)
    insert_calls = [c for c in cursor.execute.call_args_list if "INSERT" in c[0][0]]
    assert len(insert_calls) == 1


def test_load_rows_empty_list_still_truncates():
    conn, cursor = _make_conn()
    load_rows(conn, [])
    calls = [c[0][0] for c in cursor.execute.call_args_list]
    assert any("TRUNCATE" in sql for sql in calls)
    insert_calls = [sql for sql in calls if "INSERT" in sql]
    assert len(insert_calls) == 0
