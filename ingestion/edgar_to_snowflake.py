import os
import requests
import snowflake.connector
from dotenv import load_dotenv
from ingestion.edgar_extractor import extract_revenue_facts
from ingestion.snowflake_loader import create_table, load_rows

load_dotenv()

_EDGAR_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000039911.json"
_HEADERS = {"User-Agent": "Gap Inc. Media Analytics nquek@lion.lmu.edu"}


def main() -> None:
    print("Fetching Gap Inc. companyfacts from SEC EDGAR...")
    resp = requests.get(_EDGAR_URL, headers=_HEADERS)
    resp.raise_for_status()
    rows = extract_revenue_facts(resp.json())
    print(f"Extracted {len(rows)} revenue fact rows.")

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
        create_table(conn)
        load_rows(conn, rows)
        print(f"Loaded {len(rows)} rows into raw.gap_financials_raw.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
