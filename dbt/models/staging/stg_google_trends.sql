with source as (
    select * from {{ source('raw', 'google_trends_raw') }}
),
cleaned as (
    select
        brand_term,
        date::date     as week_date,
        interest_value,
        geo,
        loaded_at
    from source
    where interest_value is not null
)
select * from cleaned
