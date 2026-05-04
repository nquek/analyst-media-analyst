with financials as (
    select * from {{ ref('stg_gap_financials') }}
),
base as (
    select
        quarter_date as date_key,
        2            as brand_key,
        net_sales_usd,
        fiscal_year,
        fiscal_quarter
    from financials
),
with_yoy as (
    select
        f.date_key,
        f.brand_key,
        f.net_sales_usd,
        f.fiscal_year,
        f.fiscal_quarter,
        py.net_sales_usd as prior_year_net_sales,
        case
            when py.net_sales_usd is not null
            then round(
                (f.net_sales_usd - py.net_sales_usd) / py.net_sales_usd * 100,
                2
            )
            else null
        end as yoy_growth_pct
    from base f
    left join base py
        on  py.fiscal_quarter = f.fiscal_quarter
        and py.fiscal_year    = f.fiscal_year - 1
)
select * from with_yoy
