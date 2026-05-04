import streamlit as st
import pandas as pd
import altair as alt
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
    df = pd.read_sql("""
        select
            f.date_key     as week_date,
            b.brand_term,
            b.brand_type,
            f.interest_score
        from GAP_ANALYTICS.MART.FACT_SEARCH_TRENDS f
        join GAP_ANALYTICS.MART.DIM_BRAND b on f.brand_key = b.brand_id
        order by f.date_key
    """, conn)
    df.columns = df.columns.str.lower()
    df["week_date"] = pd.to_datetime(df["week_date"])
    return df


@st.cache_data(ttl=3600)
def load_revenue() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("""
        select
            date_key       as quarter_date,
            net_sales_usd,
            yoy_growth_pct,
            fiscal_year,
            fiscal_quarter
        from GAP_ANALYTICS.MART.FACT_BRAND_REVENUE
        order by date_key
    """, conn)
    df.columns = df.columns.str.lower()
    df["quarter_date"] = pd.to_datetime(df["quarter_date"])
    return df


def build_retail_bands(min_year: int, max_year: int) -> pd.DataFrame:
    rows = []
    for year in range(min_year, max_year + 1):
        rows += [
            {"start": f"{year}-07-01", "end": f"{year}-08-31", "event": "Back to School"},
            {"start": f"{year}-11-20", "end": f"{year}-11-30", "event": "Black Friday"},
            {"start": f"{year}-12-01", "end": f"{year}-12-31", "event": "Holiday Season"},
            {"start": f"{year}-03-01", "end": f"{year}-04-30", "event": "Spring Sale"},
        ]
    df = pd.DataFrame(rows)
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    return df


def scatter_with_trendline(df_tr: pd.DataFrame, df_rev: pd.DataFrame) -> alt.LayerChart | None:
    gap = df_tr[df_tr["brand_type"] == "gap_brand"].copy()

    # Map each revenue quarter to its date window using consecutive quarter dates
    rev = df_rev.sort_values("quarter_date").reset_index(drop=True)
    rev["period_start"] = rev["quarter_date"].shift(1) + pd.Timedelta(days=1)
    rev.loc[0, "period_start"] = rev.loc[0, "quarter_date"] - pd.Timedelta(weeks=13)

    records = []
    for _, row in rev.iterrows():
        mask = (gap["week_date"] >= row["period_start"]) & (gap["week_date"] <= row["quarter_date"])
        avg = gap.loc[mask, "interest_score"].mean()
        if pd.notna(avg):
            records.append({
                "label": f"Q{int(row['fiscal_quarter'])} FY{int(row['fiscal_year'])}",
                "avg_search": round(avg, 1),
                "net_sales_b": round(row["net_sales_usd"] / 1e9, 2),
            })

    if len(records) < 3:
        return None

    sdf = pd.DataFrame(records)

    points = (
        alt.Chart(sdf)
        .mark_circle(size=90, color="#1f77b4")
        .encode(
            x=alt.X("avg_search:Q", title="Avg Gap Brand Search Interest (quarterly)", scale=alt.Scale(zero=False)),
            y=alt.Y("net_sales_b:Q", title="Net Sales ($ billions)", scale=alt.Scale(zero=False)),
            tooltip=["label:N", "avg_search:Q", "net_sales_b:Q"],
        )
    )
    trendline = points.transform_regression("avg_search", "net_sales_b").mark_line(
        color="#FF4B4B", strokeDash=[6, 3]
    )
    labels = points.mark_text(align="left", dx=8, fontSize=11).encode(text="label:N")

    corr = sdf["avg_search"].corr(sdf["net_sales_b"])
    return (points + trendline + labels).properties(height=380), corr, sdf


# ── App ──────────────────────────────────────────────────────────────────────

st.title("Gap Inc. Brand Analytics")
st.caption("Search interest (Google Trends) · Revenue performance (SEC EDGAR) · Gap brands vs. competitors")

BRAND_COLORS = {
    # Gap Inc. brands — greens and blues
    "Old Navy":        "#1565C0",
    "Gap":             "#2E7D32",
    "Banana Republic": "#00695C",
    "Athleta":         "#0288D1",
    # Competitors — reds, oranges, pinks
    "H&M":             "#C62828",
    "Zara":            "#E65100",
    "J.Crew":          "#AD1457",
    "Levi's":          "#FF6F00",
}

tab1, tab2, tab3 = st.tabs(["Search Interest by Brand", "Seasonality & Retail Moments", "Revenue vs. Search"])

# ── Tab 1: Search Interest by Brand ──────────────────────────────────────────
with tab1:
    df = load_search_trends()
    all_brands = sorted(df["brand_term"].unique())

    ctrl_col, chart_col = st.columns([1, 3])

    with ctrl_col:
        st.markdown("### Filters")
        selected = st.multiselect("Brands", all_brands, default=all_brands)

        timeframe_options = {
            "All (5 years)": None,
            "Last 3 years": 3,
            "Last 2 years": 2,
            "Last 1 year": 1,
        }
        timeframe_label = st.radio("Timeframe", list(timeframe_options.keys()), index=0)
        years_back = timeframe_options[timeframe_label]
        st.markdown("---")
        st.markdown("**Color key**")
        st.markdown(
            "<span style='color:#1565C0'>■</span> Old Navy &nbsp;"
            "<span style='color:#2E7D32'>■</span> Gap<br>"
            "<span style='color:#00695C'>■</span> Banana Republic &nbsp;"
            "<span style='color:#0288D1'>■</span> Athleta",
            unsafe_allow_html=True,
        )
        st.caption("Gap Inc. brands")
        st.markdown(
            "<span style='color:#C62828'>■</span> H&M &nbsp;"
            "<span style='color:#E65100'>■</span> Zara<br>"
            "<span style='color:#AD1457'>■</span> J.Crew &nbsp;"
            "<span style='color:#FF6F00'>■</span> Levi's",
            unsafe_allow_html=True,
        )
        st.caption("Competitors")

    with chart_col:
        st.subheader("Weekly Search Interest by Brand")
        filtered = df[df["brand_term"].isin(selected)]
        if years_back is not None:
            cutoff = df["week_date"].max() - pd.DateOffset(years=years_back)
            filtered = filtered[filtered["week_date"] >= cutoff]

        color_scale = alt.Scale(
            domain=list(BRAND_COLORS.keys()),
            range=list(BRAND_COLORS.values()),
        )
        chart = (
            alt.Chart(filtered)
            .mark_line()
            .encode(
                x=alt.X("week_date:T", title="Week"),
                y=alt.Y("interest_score:Q", title="Search Interest (0–100)", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color("brand_term:N", scale=color_scale, legend=alt.Legend(title="Brand")),
                tooltip=[
                    alt.Tooltip("week_date:T", title="Week"),
                    alt.Tooltip("brand_term:N", title="Brand"),
                    alt.Tooltip("interest_score:Q", title="Interest"),
                ],
            )
            .properties(height=400)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)
        st.caption("Score: 0–100 relative to each brand's own peak. Not comparable across brands.")

        if not filtered.empty:
            summary = (
                filtered.groupby("brand_term")["interest_score"]
                .agg(Peak="max", Average="mean", Latest="last")
                .round(1)
                .sort_values("Average", ascending=False)
            )
            st.markdown("**5-Year Summary**")
            st.dataframe(summary, use_container_width=True)

# ── Tab 2: Seasonality & Retail Moments ──────────────────────────────────────
with tab2:
    st.subheader("Search Interest with Retail Moments")
    df2 = load_search_trends()
    brand_sel = st.selectbox("Select brand", sorted(df2["brand_term"].unique()))
    brand_df = df2[df2["brand_term"] == brand_sel].sort_values("week_date")

    min_yr = brand_df["week_date"].dt.year.min()
    max_yr = brand_df["week_date"].dt.year.max()
    bands_df = build_retail_bands(min_yr, max_yr)

    bands = (
        alt.Chart(bands_df)
        .mark_rect(opacity=0.15)
        .encode(
            x=alt.X("start:T"),
            x2=alt.X2("end:T"),
            color=alt.Color(
                "event:N",
                scale=alt.Scale(
                    domain=["Back to School", "Black Friday", "Holiday Season", "Spring Sale"],
                    range=["#FFC107", "#DC3545", "#17A2B8", "#28A745"],
                ),
                legend=alt.Legend(title="Retail Event"),
            ),
        )
    )
    line = (
        alt.Chart(brand_df)
        .mark_line()
        .encode(
            x=alt.X("week_date:T", title="Week"),
            y=alt.Y("interest_score:Q", title="Search Interest (0–100)", scale=alt.Scale(domain=[0, 100])),
            tooltip=[
                alt.Tooltip("week_date:T", title="Week"),
                alt.Tooltip("interest_score:Q", title="Interest"),
            ],
        )
    )

    st.altair_chart((bands + line).properties(height=380).interactive(), use_container_width=True)

    # Seasonality bar chart
    brand_df["month"] = brand_df["week_date"].dt.month
    monthly_avg = (
        brand_df.groupby("month")["interest_score"]
        .mean()
        .reset_index()
        .rename(columns={"month": "Month", "interest_score": "Avg Interest"})
    )
    monthly_avg["Month"] = monthly_avg["Month"].map({
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    })
    st.markdown(f"**Average Monthly Interest — {brand_sel}**")
    st.bar_chart(monthly_avg.set_index("Month")["Avg Interest"])
    st.caption("Which months consistently drive the most search activity for this brand.")

# ── Tab 3: Revenue vs. Search ─────────────────────────────────────────────────
with tab3:
    st.subheader("Revenue vs. Search Interest (Gap Inc.)")
    df_rev = load_revenue()
    df_tr = load_search_trends()

    gap_avg = (
        df_tr[df_tr["brand_type"] == "gap_brand"]
        .groupby("week_date")["interest_score"]
        .mean()
        .reset_index()
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Quarterly Net Sales (USD)**")
        st.bar_chart(df_rev.set_index("quarter_date")["net_sales_usd"])
    with col2:
        st.markdown("**Avg Gap Brand Search Interest (weekly)**")
        st.line_chart(gap_avg.set_index("week_date")["interest_score"])

    latest_yoy = df_rev.dropna(subset=["yoy_growth_pct"])
    if not latest_yoy.empty:
        row = latest_yoy.iloc[-1]
        st.metric(
            label=f"YoY Revenue Growth — Q{int(row['fiscal_quarter'])} FY{int(row['fiscal_year'])}",
            value=f"{row['yoy_growth_pct']:+.1f}%",
        )

    # Scatter: search interest vs revenue
    st.divider()
    st.subheader("Does Search Interest Predict Revenue?")
    result = scatter_with_trendline(df_tr, df_rev)
    if result is None:
        st.info("Not enough overlapping quarters to render scatter plot.")
    else:
        chart, corr, sdf = result
        st.altair_chart(chart, use_container_width=True)
        direction = "positive" if corr > 0 else "negative"
        strength = "strong" if abs(corr) > 0.6 else "moderate" if abs(corr) > 0.3 else "weak"
        st.caption(
            f"Each dot = one fiscal quarter. Pearson r = **{corr:.2f}** "
            f"({strength} {direction} correlation). "
            "Red dashed line = linear trend. "
            "Higher search interest quarters tend to coincide with higher revenue quarters."
        )
