_DDL = """
CREATE TABLE IF NOT EXISTS raw.gap_financials_raw (
    concept     VARCHAR,
    value       NUMBER,
    unit        VARCHAR,
    start_date  DATE,
    end_date    DATE,
    form        VARCHAR,
    filed_date  DATE,
    accn        VARCHAR,
    loaded_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
"""

_INSERT = """
INSERT INTO raw.gap_financials_raw
    (concept, value, unit, start_date, end_date, form, filed_date, accn)
VALUES
    (%(concept)s, %(value)s, %(unit)s, %(start_date)s, %(end_date)s,
     %(form)s, %(filed_date)s, %(accn)s)
"""


def create_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(_DDL)


def load_rows(conn, rows: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE raw.gap_financials_raw")
        for row in rows:
            cur.execute(_INSERT, row)
