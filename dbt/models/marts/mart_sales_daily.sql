-- mart_sales_daily : CA HT et TTC par jour, avec nombre de commandes et articles vendus
with orders as (
    select * from {{ ref('stg_orders') }}
    where status = 'confirmed'
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

daily as (
    select
        date_trunc('day', o.source_updated_at)::date  as order_date,
        count(distinct o.order_id)                    as nb_orders,
        sum(oi.quantity)                              as units_sold,
        sum(oi.line_total_ht)                         as revenue_ht,
        sum(oi.line_total_ttc)                        as revenue_ttc
    from orders o
    join order_items oi on oi.order_id = o.order_id
    group by 1
)

select
    order_date,
    nb_orders,
    units_sold,
    revenue_ht,
    revenue_ttc,
    sum(revenue_ttc) over (order by order_date)  as cumulative_revenue_ttc
from daily
order by order_date
