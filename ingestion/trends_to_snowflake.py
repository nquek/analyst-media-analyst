import os
import time

import snowflake.connector
from dotenv import load_dotenv
from pytrends.request import TrendReq

load_dotenv()

BRANDS = [
    "Old Navy",
    "Gap",
    "Banana Republic",
    "Athleta",
    "H&M",
    "Zara",
    "J.Crew",
    "Levi's",
]

_DDL = """
CREATE TABLE IF NOT EXISTS raw.google_trends_raw (
    brand_term      VARCHAR,
    date            DATE,
    interest_value  INTEGER,
    geo             VARCHAR,
    loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
"""

_INSERT = """
INSERT INTO raw.google_trends_raw (brand_term, date, interest_value, geo)
VALUES (%(brand_term)s, %(date)s, %(interest_value)s, %(geo)s)
"""


def fetch_trends(brand: str) -> list[dict]:
    pytrends = TrendReq(hl="en-US", tz=360)
    pytrends.build_payload([brand], timeframe="today 5-y", geo="US")
    df = pytrends.interest_over_time()
    if df.empty:
        return []
    if brand not in df.columns:
        return []
    rows = []
    for date, row in df.iterrows():
        if row.get("isPartial", False):
            continue
        rows.append({
            "brand_term": brand,
            "date": date.date(),
            "interest_value": int(row[brand]),
            "geo": "US",
        })
    return rows


def main() -> None:
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        role=os.environ["SNOWFLAKE_ROLE"],
        schema="raw",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(_DDL)
            cur.execute("TRUNCATE TABLE raw.google_trends_raw")
        total = 0
        for brand in BRANDS:
            try:
                rows = fetch_trends(brand)
            except Exception as exc:
                print(f"[WARN] {brand}: {exc}")
                rows = []
            with conn.cursor() as cur:
                for row in rows:
                    cur.execute(_INSERT, row)
            total += len(rows)
            print(f"[OK] {brand}: {len(rows)} rows")
            time.sleep(5)  # avoid Google Trends rate limits
        print(f"Loaded {total} rows into raw.google_trends_raw.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
