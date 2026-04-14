-- mart_revenue_by_item : revenus, quantités vendues et stock restant par article
with items as (
    select * from {{ ref('stg_items') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
    where status = 'confirmed'
),

sales as (
    select
        oi.item_id,
        count(distinct oi.order_id)         as nb_orders,
        sum(oi.quantity)                    as total_units_sold,
        sum(oi.line_total_ht)               as total_revenue_ht,
        sum(oi.line_total_ttc)              as total_revenue_ttc
    from order_items oi
    join orders o on o.order_id = oi.order_id
    group by oi.item_id
)

select
    i.item_id,
    i.title,
    i.price_ht,
    i.price_ttc,
    i.tva_rate,
    i.quantity                              as current_stock,
    coalesce(s.nb_orders, 0)               as nb_orders,
    coalesce(s.total_units_sold, 0)        as total_units_sold,
    coalesce(s.total_revenue_ht, 0)        as total_revenue_ht,
    coalesce(s.total_revenue_ttc, 0)       as total_revenue_ttc
from items i
left join sales s on s.item_id = i.item_id
order by total_revenue_ttc desc
