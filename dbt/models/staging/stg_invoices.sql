with source as (
    select * from {{ source('raw', 'invoices') }}
),

cleaned as (
    select
        id                                          as invoice_id,
        order_id,
        invoice_number,
        issued_at::timestamp                        as issued_at,
        due_date::timestamp                         as due_date,
        total_ht::numeric(10, 2)                    as total_ht,
        total_tva::numeric(10, 2)                   as total_tva,
        total_ttc::numeric(10, 2)                   as total_ttc,
        coalesce("__deleted", false)                as is_deleted,
        to_timestamp("__source_ts_ms" / 1000.0)    as source_updated_at
    from source
    where coalesce("__deleted", false) = false
)

select * from cleaned
