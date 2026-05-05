with seed as (
    select * from {{ ref('brand_segment_revenue') }}
),
brands as (
    select * from {{ ref('dim_brand') }}
),
joined as (
    select
        s.quarter_date                       as date_key,
        s.brand_id                           as brand_key,
        b.brand_name,
        b.brand_term,
        s.fiscal_year,
        s.fiscal_quarter,
        s.net_sales_m,
        s.net_sales_m * 1000000.0            as net_sales_usd,
        s.is_derived
    from seed s
    inner join brands b on s.brand_id = b.brand_id
)
select * from joined
