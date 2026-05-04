import streamlit as st
import pandas as pd
import snowflake.connector

st.set_page_config(page_title="Gap Inc. Brand Analytics", layout="wide")


@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=st.secrets["SNOWFLAKE_ACCOUNT"],
        user=st.secrets["SNOWFLAKE_USER"],
        password=st.secrets["SNOWFLAKE_PASSWORD"],
        database=st.secrets["SNOWFLAKE_DATABASE"],
        warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
        role=st.secrets["SNOWFLAKE_ROLE"],
        schema="MART",
    )


@st.cache_data(ttl=3600)
def load_search_trends() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql("""
        select
            f.date_key     as week_date,
            b.brand_term,
            b.brand_type,
            f.interest_score
        from GAP_ANALYTICS.MART.FACT_SEARCH_TRENDS f
        join GAP_ANALYTICS.MART.DIM_BRAND b on f.brand_key = b.brand_id
        order by f.date_key
    """, conn)


@st.cache_data(ttl=3600)
def load_revenue() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql("""
        select
            date_key       as quarter_date,
            net_sales_usd,
            yoy_growth_pct,
            fiscal_year,
            fiscal_quarter
        from GAP_ANALYTICS.MART.FACT_BRAND_REVENUE
        order by date_key
    """, conn)


st.title("Gap Inc. Brand Analytics")
st.caption("Search interest (Google Trends) and revenue performance — Gap brands vs. competitors")

tab1, tab2, tab3 = st.tabs(["Brand Comparison", "Seasonality & Retail Moments", "Revenue vs. Search"])

with tab1:
    st.subheader("Weekly Search Interest by Brand")
    df = load_search_trends()
    brands = sorted(df["BRAND_TERM"].unique())
    selected = st.multiselect("Select brands to display", brands, default=brands)
    filtered = df[df["BRAND_TERM"].isin(selected)]
    pivot = filtered.pivot_table(index="WEEK_DATE", columns="BRAND_TERM", values="INTEREST_SCORE")
    st.line_chart(pivot)
    st.caption("Score: 0–100 relative to each brand's own peak. Scores are not directly comparable across brands.")

with tab2:
    st.subheader("Search Interest with Retail Moments")
    df2 = load_search_trends()
    brand_sel = st.selectbox("Select brand", sorted(df2["BRAND_TERM"].unique()))
    brand_df = df2[df2["BRAND_TERM"] == brand_sel].set_index("WEEK_DATE").sort_index()
    st.line_chart(brand_df["INTEREST_SCORE"])
    st.info("Retail moment guide: **Nov–Dec** = Holiday / Black Friday | **Jul–Aug** = Back to School | **Mar–Apr** = Spring Sale")

with tab3:
    st.subheader("Revenue vs. Search Interest (Gap Inc.)")
    df_rev = load_revenue()
    df_tr = load_search_trends()
    gap_avg = (
        df_tr[df_tr["BRAND_TYPE"] == "gap_brand"]
        .groupby("WEEK_DATE")["INTEREST_SCORE"]
        .mean()
        .reset_index()
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Quarterly Net Sales (USD)**")
        st.bar_chart(df_rev.set_index("QUARTER_DATE")["NET_SALES_USD"])
    with col2:
        st.markdown("**Avg Gap Brand Search Interest (weekly)**")
        st.line_chart(gap_avg.set_index("WEEK_DATE")["INTEREST_SCORE"])
    latest_yoy = df_rev.dropna(subset=["YOY_GROWTH_PCT"])
    if not latest_yoy.empty:
        row = latest_yoy.iloc[-1]
        st.metric(
            label=f"YoY Revenue Growth — Q{int(row['FISCAL_QUARTER'])} FY{int(row['FISCAL_YEAR'])}",
            value=f"{row['YOY_GROWTH_PCT']:+.1f}%",
        )
