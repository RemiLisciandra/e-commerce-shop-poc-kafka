with source as (
    select * from {{ source('raw', 'orders') }}
),

cleaned as (
    select
        id                                          as order_id,
        customer_id,
        status,
        total_ht::numeric(10, 2)                    as total_ht,
        total_ttc::numeric(10, 2)                   as total_ttc,
        coalesce("__deleted", 'false') = 'true'      as is_deleted,
        to_timestamp("__source_ts_ms" / 1000.0)    as source_updated_at
    from source
    where coalesce("__deleted", 'false') = 'false'
)

select * from cleaned
