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


@st.cache_data(ttl=3600)
def load_brand_segment_revenue() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("""
        select
            date_key       as quarter_date,
            brand_name,
            fiscal_year,
            fiscal_quarter,
            net_sales_m,
            is_derived
        from GAP_ANALYTICS.MART.FACT_BRAND_SEGMENT_REVENUE
        order by date_key, brand_name
    """, conn)
    df.columns = df.columns.str.lower()
    df["quarter_date"] = pd.to_datetime(df["quarter_date"])
    df["quarter_label"] = "Q" + df["fiscal_quarter"].astype(int).astype(str) + " FY" + df["fiscal_year"].astype(int).astype(str)
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

tab1, tab2, tab3 = st.tabs(["Search Interest by Brand", "Search Interest by Seasonality", "Revenue vs. Search Interest (Gap Inc.)"])

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
        timeframe_label = st.radio("Timeframe", list(timeframe_options.keys()), index=0, key="t1_timeframe")
        years_back = timeframe_options[timeframe_label]
        st.markdown("---")
        st.markdown("**Color key**")
        st.caption("Gap Inc. Brands")
        st.markdown(
            "<span style='color:#1565C0'>■</span> Old Navy &nbsp;"
            "<span style='color:#2E7D32'>■</span> Gap<br>"
            "<span style='color:#00695C'>■</span> Banana Republic &nbsp;"
            "<span style='color:#0288D1'>■</span> Athleta",
            unsafe_allow_html=True,
        )
        st.caption("Competitors")
        st.markdown(
            "<span style='color:#C62828'>■</span> H&M &nbsp;"
            "<span style='color:#E65100'>■</span> Zara<br>"
            "<span style='color:#AD1457'>■</span> J.Crew &nbsp;"
            "<span style='color:#FF6F00'>■</span> Levi's",
            unsafe_allow_html=True,
        )

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

# ── Tab 2: Search Interest by Seasonality ────────────────────────────────────
with tab2:
    df2 = load_search_trends()

    ctrl_col2, chart_col2 = st.columns([1, 3])

    with ctrl_col2:
        st.markdown("### Filters")
        brand_sel = st.selectbox("Brand", sorted(df2["brand_term"].unique()))

        t2_options = {
            "All (5 years)": None,
            "Last 3 years": 3,
            "Last 2 years": 2,
            "Last 1 year": 1,
        }
        t2_label = st.radio("Timeframe", list(t2_options.keys()), index=0, key="t2_timeframe")
        t2_years = t2_options[t2_label]

    brand_df = df2[df2["brand_term"] == brand_sel].sort_values("week_date")
    if t2_years is not None:
        t2_cutoff = df2["week_date"].max() - pd.DateOffset(years=t2_years)
        brand_df = brand_df[brand_df["week_date"] >= t2_cutoff]

    with chart_col2:
        st.subheader(f"Search Interest with Retail Moments — {brand_sel}")

        min_yr = brand_df["week_date"].dt.year.min()
        max_yr = brand_df["week_date"].dt.year.max()
        bands_df = build_retail_bands(min_yr, max_yr)
        # Clip bands to the filtered date range
        range_start = brand_df["week_date"].min()
        range_end = brand_df["week_date"].max()
        bands_df = bands_df[bands_df["end"] >= range_start]
        bands_df["start"] = bands_df["start"].clip(lower=range_start)
        bands_df["end"] = bands_df["end"].clip(upper=range_end)

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

        # Monthly avg bar chart
        brand_df = brand_df.copy()
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

# ── Tab 3: Revenue vs. Search Interest (Gap Inc.) ────────────────────────────
with tab3:
    st.subheader("Revenue vs. Search Interest (Gap Inc.)")
    df_rev = load_revenue()
    df_tr = load_search_trends()

    t3_ctrl, t3_charts = st.columns([1, 3])

    with t3_ctrl:
        st.markdown("### Filters")

        t3_rev_options = {
            "All available": None,
            "Last 3 years": 3,
            "Last 2 years": 2,
            "Last 1 year": 1,
        }
        t3_rev_label = st.radio("Revenue timeframe", list(t3_rev_options.keys()), index=0, key="t3_rev")
        t3_rev_years = t3_rev_options[t3_rev_label]

        st.markdown("")

        t3_search_options = {
            "All (5 years)": None,
            "Last 3 years": 3,
            "Last 2 years": 2,
            "Last 1 year": 1,
        }
        t3_search_label = st.radio("Search timeframe", list(t3_search_options.keys()), index=0, key="t3_search")
        t3_search_years = t3_search_options[t3_search_label]

    with t3_charts:
        # Filter revenue
        df_rev_filtered = df_rev.copy()
        if t3_rev_years is not None:
            rev_cutoff = df_rev["quarter_date"].max() - pd.DateOffset(years=t3_rev_years)
            df_rev_filtered = df_rev_filtered[df_rev_filtered["quarter_date"] >= rev_cutoff]

        # Filter search
        gap_avg = (
            df_tr[df_tr["brand_type"] == "gap_brand"]
            .groupby("week_date")["interest_score"]
            .mean()
            .reset_index()
        )
        gap_avg_filtered = gap_avg.copy()
        if t3_search_years is not None:
            search_cutoff = gap_avg["week_date"].max() - pd.DateOffset(years=t3_search_years)
            gap_avg_filtered = gap_avg_filtered[gap_avg_filtered["week_date"] >= search_cutoff]

        st.markdown("**Quarterly Net Sales — Gap Inc.**")
        rev_chart = (
            alt.Chart(df_rev_filtered)
            .mark_bar(color="#2E7D32")
            .encode(
                x=alt.X("quarter_date:T", title="Quarter"),
                y=alt.Y("net_sales_usd:Q", title="Net Sales (USD)"),
                tooltip=["quarter_date:T", "net_sales_usd:Q", "yoy_growth_pct:Q"],
            )
            .properties(height=280)
        )
        st.altair_chart(rev_chart, use_container_width=True)

        latest_yoy = df_rev_filtered.dropna(subset=["yoy_growth_pct"])
        if not latest_yoy.empty:
            row = latest_yoy.iloc[-1]
            st.metric(
                label=f"YoY Revenue Growth — Q{int(row['fiscal_quarter'])} FY{int(row['fiscal_year'])}",
                value=f"{row['yoy_growth_pct']:+.1f}%",
            )

        st.markdown("**Avg Gap Brand Search Interest (weekly)**")
        search_chart = (
            alt.Chart(gap_avg_filtered)
            .mark_line(color="#E65100")
            .encode(
                x=alt.X("week_date:T", title="Week"),
                y=alt.Y("interest_score:Q", title="Search Interest (0–100)"),
                tooltip=["week_date:T", "interest_score:Q"],
            )
            .properties(height=280)
        )
        st.altair_chart(search_chart, use_container_width=True)

    # Brand segment revenue breakdown
    st.divider()
    st.subheader("Net Sales by Brand — FY2024")
    df_seg = load_brand_segment_revenue()

    brand_seg_colors = {
        "Old Navy":        "#1565C0",
        "Gap":             "#2E7D32",
        "Banana Republic": "#00695C",
        "Athleta":         "#0288D1",
    }
    seg_chart = (
        alt.Chart(df_seg)
        .mark_bar()
        .encode(
            x=alt.X("quarter_label:N", title="Quarter", sort=["Q1 FY2024", "Q2 FY2024", "Q3 FY2024", "Q4 FY2024"]),
            y=alt.Y("net_sales_m:Q", title="Net Sales ($ millions)", stack=True),
            color=alt.Color(
                "brand_name:N",
                scale=alt.Scale(
                    domain=list(brand_seg_colors.keys()),
                    range=list(brand_seg_colors.values()),
                ),
                legend=alt.Legend(title="Brand"),
            ),
            tooltip=[
                alt.Tooltip("quarter_label:N", title="Quarter"),
                alt.Tooltip("brand_name:N", title="Brand"),
                alt.Tooltip("net_sales_m:Q", title="Net Sales ($M)"),
                alt.Tooltip("is_derived:N", title="Derived (Q3)"),
            ],
        )
        .properties(height=380)
    )
    st.altair_chart(seg_chart, use_container_width=True)
    st.caption("Q3 FY2024 figures are derived (annual total minus Q1+Q2+Q4) as the Q3 press release was unavailable at time of scrape.")

    # Scatter: search interest vs revenue
    st.divider()
    st.subheader("Does Search Interest Predict Revenue?")
    result = scatter_with_trendline(df_tr, df_rev)
    if result is None:
        st.info("Not enough overlapping quarters to render scatter plot.")
    else:
        chart, corr, sdf = result
        direction = "positive" if corr > 0 else "negative"
        strength = "strong" if abs(corr) > 0.6 else "moderate" if abs(corr) > 0.3 else "weak"

        key_col, scatter_col = st.columns([1, 3])
        with key_col:
            st.markdown("**Chart Key**")
            st.markdown(
                f"- Each dot = one fiscal quarter\n"
                f"- Pearson r = **{corr:.2f}** ({strength} {direction} correlation)\n"
                f"- Red dashed line = linear trend\n"
                f"- Higher search interest quarters tend to coincide with higher revenue quarters"
            )
        with scatter_col:
            st.altair_chart(chart, use_container_width=True)
