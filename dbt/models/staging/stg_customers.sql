with source as (
    select * from {{ source('raw', 'customers') }}
),

cleaned as (
    select
        id                                          as customer_id,
        email,
        first_name,
        last_name,
        phone,
        address,
        (is_active = 1)                              as is_active,
        coalesce("__deleted", 'false') = 'true'      as is_deleted,
        to_timestamp("__source_ts_ms" / 1000.0)    as source_updated_at
    from source
    where coalesce("__deleted", 'false') = 'false'
)

select * from cleaned
