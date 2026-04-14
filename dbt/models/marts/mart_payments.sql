-- mart_payments_summary : agrégation des paiements par méthode et statut
with payments as (
    select * from {{ ref('stg_payments') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
)

select
    p.payment_id,
    p.order_id,
    o.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    p.amount,
    p.payment_status,
    p.payment_method,
    p.transaction_id,
    p.source_updated_at                             as paid_at
from payments p
join orders o on o.order_id = p.order_id
join customers c on c.customer_id = o.customer_id
order by p.source_updated_at desc
