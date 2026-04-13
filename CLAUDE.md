# CLAUDE.md

## Project Overview

**Project:** Gap Inc. Media Analytics Dashboard
**Role targeted:** Analyst, Media Analytics at Gap Inc.
**Repo:** https://github.com/nquek/analyst-media-analyst

This project builds an end-to-end analytics pipeline that tracks brand search interest and revenue performance for Gap Inc.'s brand portfolio (Old Navy, Gap, Banana Republic, Athleta) benchmarked against competitors (H&M, Zara, J.Crew, Levi's).

## Data Sources

### Source 1: Google Trends (pytrends)
- Weekly search interest (0–100 scale) for 8 brand terms
- Dimensions: time (5 years weekly), US state-level geography
- Loaded to Snowflake raw schema via GitHub Actions (weekly schedule)

### Source 2: SEC EDGAR REST API
- Quarterly net sales by brand segment from Gap Inc. 10-Q/10-K filings
- Base URL: `https://data.sec.gov/`
- Loaded to Snowflake raw schema via GitHub Actions (quarterly schedule)

### Source 3: Web Scrape (Knowledge Base only)
- Gap Inc. investor relations / press releases (gapinc.com)
- Business of Fashion articles about Gap brands
- Retail Dive coverage of Gap Inc.
- Stored in `knowledge/raw/`, automated via GitHub Actions

## Tech Stack

| Layer | Tool |
|---|---|
| Data Warehouse | Snowflake |
| Transformation | dbt |
| Orchestration | GitHub Actions |
| Dashboard | Streamlit (deployed to Streamlit Community Cloud) |
| Knowledge Base | Claude Code |

## Star Schema

- `fact_search_trends` — date_key, brand_key, region_key, interest_score
- `fact_brand_revenue` — date_key, brand_key, net_sales_usd, yoy_growth_pct
- `dim_brand` — brand_id, brand_name, brand_type (`gap_brand` / `competitor`), parent_company
- `dim_date` — date, week, month, quarter, year, is_holiday_season, retail_event_label
- `dim_region` — region_name, state_abbrev, census_region

## Dashboard Structure

Three tabs in Streamlit:
1. **Brand Comparison** — search interest over time (Gap brands vs competitors), state-level heatmap filter
2. **Seasonality & Retail Moments** — annotated time series showing search spikes by retail event (Black Friday, Back-to-School, etc.)
3. **Revenue vs. Search** — dual-axis chart overlaying quarterly revenue with search interest by brand

## Knowledge Base

### Structure
```
knowledge/
  raw/          # 15+ scraped source documents
  wiki/         # Claude Code-generated synthesis pages
    overview.md
    brands-and-competitors.md
    media-and-marketing-themes.md
  index.md      # Index of all wiki pages with one-line summaries
```

### How to Query the Knowledge Base

When answering questions about Gap Inc., its brands, or media/marketing themes:
1. Start with `knowledge/index.md` to identify the most relevant wiki pages
2. Read the relevant wiki page(s) in `knowledge/wiki/`
3. Cross-reference with raw sources in `knowledge/raw/` for specific facts or quotes
4. Synthesize across sources — do not summarize a single document in isolation

Example queries this knowledge base supports:
- "What does my knowledge base say about Athleta's brand positioning?"
- "What marketing themes appear across Gap Inc. press releases?"
- "How has Old Navy's search interest correlated with its revenue performance?"

## Credentials & Secrets

All credentials are stored as environment variables and never committed to the repo.

Required secrets (stored in `.env` locally and GitHub Actions secrets):
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_DATABASE`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_ROLE`
