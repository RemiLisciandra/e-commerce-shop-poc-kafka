-- mart_customer_lifetime : LTV, nombre de commandes et panier moyen par client
with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
    where status = 'confirmed'
)

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    count(o.order_id)                                       as nb_orders,
    coalesce(sum(o.total_ttc), 0)                          as lifetime_value_ttc,
    coalesce(avg(o.total_ttc), 0)                          as avg_basket_ttc,
    coalesce(min(o.source_updated_at), null)               as first_order_at,
    coalesce(max(o.source_updated_at), null)               as last_order_at,
    case
        when count(o.order_id) = 0 then 'no_order'
        when count(o.order_id) = 1 then 'one_time'
        when count(o.order_id) between 2 and 4 then 'recurring'
        else 'loyal'
    end                                                     as customer_segment
from customers c
left join orders o on o.customer_id = c.customer_id
group by c.customer_id, c.first_name, c.last_name, c.email
order by lifetime_value_ttc desc
