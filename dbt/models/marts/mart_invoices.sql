-- mart_invoices : factures enrichies avec infos client et commande
with invoices as (
    select * from {{ ref('stg_invoices') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
)

select
    i.invoice_id,
    i.invoice_number,
    i.order_id,
    o.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    i.total_ht,
    i.total_tva,
    i.total_ttc,
    i.issued_at,
    i.due_date,
    case
        when i.due_date < current_date then 'overdue'
        else 'on_time'
    end                                             as due_status
from invoices i
join orders o on o.order_id = i.order_id
join customers c on c.customer_id = o.customer_id
order by i.issued_at desc
