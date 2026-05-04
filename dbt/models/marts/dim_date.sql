with all_dates as (
    select week_date    as date_day from {{ ref('stg_google_trends') }}
    union
    select quarter_date as date_day from {{ ref('stg_gap_financials') }}
),
dated as (
    select
        date_day,
        extract(year    from date_day)::int    as year,
        extract(month   from date_day)::int    as month,
        extract(quarter from date_day)::int    as quarter,
        extract(week    from date_day)::int    as week_of_year,
        case
            when extract(month from date_day) in (11, 12) then true
            else false
        end as is_holiday_season,
        case
            when extract(month from date_day) = 11
             and extract(day   from date_day) between 24 and 30 then 'Black Friday'
            when extract(month from date_day) in (7, 8)          then 'Back to School'
            when extract(month from date_day) = 12               then 'Holiday Season'
            when extract(month from date_day) in (3, 4)          then 'Spring Sale'
            else null
        end as retail_event_label
    from all_dates
)
select * from dated
