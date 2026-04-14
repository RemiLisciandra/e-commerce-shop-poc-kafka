-- mart_customer_reorders : produits achetés par client (base pour les suggestions de réachat)
with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
    where status = 'confirmed'
),

items as (
    select * from {{ ref('stg_items') }}
)

select
    o.customer_id,
    oi.item_id,
    i.title,
    i.price_ttc,
    sum(oi.quantity)                                as total_qty_purchased,
    count(distinct oi.order_id)                    as nb_orders_with_item,
    max(o.source_updated_at)                       as last_purchased_at,
    i.quantity                                      as current_stock
from order_items oi
join orders o on o.order_id = oi.order_id
join items i on i.item_id = oi.item_id
group by o.customer_id, oi.item_id, i.title, i.price_ttc, i.quantity
order by o.customer_id, last_purchased_at desc
