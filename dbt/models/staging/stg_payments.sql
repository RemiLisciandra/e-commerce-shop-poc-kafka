with source as (
    select * from {{ source('raw', 'payments') }}
),

cleaned as (
    select
        id                                          as payment_id,
        order_id,
        amount::numeric(10, 2)                      as amount,
        status                                      as payment_status,
        payment_method,
        transaction_id,
        coalesce("__deleted", 'false') = 'true'      as is_deleted,
        to_timestamp("__source_ts_ms" / 1000.0)    as source_updated_at
    from source
    where coalesce("__deleted", 'false') = 'false'
)

select * from cleaned
