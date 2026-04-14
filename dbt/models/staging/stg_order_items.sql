with source as (
    select * from {{ source('raw', 'order_items') }}
),

cleaned as (
    select
        id                                          as order_item_id,
        order_id,
        item_id,
        quantity::integer                           as quantity,
        unit_price_ht::numeric(10, 2)               as unit_price_ht,
        unit_price_ttc::numeric(10, 2)              as unit_price_ttc,
        (quantity * unit_price_ht)::numeric(10, 2)  as line_total_ht,
        (quantity * unit_price_ttc)::numeric(10, 2) as line_total_ttc,
        coalesce("__deleted", 'false') = 'true'      as is_deleted
    from source
    where coalesce("__deleted", 'false') = 'false'
)

select * from cleaned
