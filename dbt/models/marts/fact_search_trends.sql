with trends as (
    select * from {{ ref('stg_google_trends') }}
),
brands as (
    select * from {{ ref('dim_brand') }}
),
joined as (
    select
        t.week_date      as date_key,
        b.brand_id       as brand_key,
        t.geo,
        t.interest_value as interest_score
    from trends t
    inner join brands b on t.brand_term = b.brand_term
)
select * from joined
