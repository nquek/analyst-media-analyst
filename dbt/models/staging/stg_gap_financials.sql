with source as (
    select * from {{ source('raw', 'gap_financials_raw') }}
),
quarterly as (
    select
        concept,
        value           as net_sales_usd,
        start_date,
        end_date,
        form,
        filed_date,
        accn,
        datediff('day', start_date, end_date) as period_days
    from source
    where form in ('10-Q', '10-K')
      and start_date is not null
      and end_date   is not null
),
single_quarter as (
    select *
    from quarterly
    where period_days between 75 and 105
),
deduped as (
    select *,
        row_number() over (
            partition by start_date, end_date, concept
            order by filed_date desc
        ) as rn
    from single_quarter
)
select
    concept,
    net_sales_usd,
    start_date,
    end_date                                  as quarter_date,
    extract(year    from end_date)::int       as fiscal_year,
    extract(quarter from end_date)::int       as fiscal_quarter,
    form,
    filed_date,
    accn
from deduped
where rn = 1
