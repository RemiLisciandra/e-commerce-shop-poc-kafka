-- stg_items : nettoyage de la table items ingérée par le JDBC sink
-- La colonne __deleted est ajoutée par le SMT ExtractNewRecordState de Debezium
with source as (
    select * from {{ source('raw', 'items') }}
),

cleaned as (
    select
        id                                          as item_id,
        title,
        description,
        image_url,
        price_ht::numeric(10, 2)                    as price_ht,
        tva_rate::numeric(5, 2)                     as tva_rate,
        price_ttc::numeric(10, 2)                   as price_ttc,
        quantity::integer                           as quantity,
        coalesce("__deleted", false)                as is_deleted,
        to_timestamp("__source_ts_ms" / 1000.0)    as source_updated_at
    from source
    where coalesce("__deleted", false) = false
)

select * from cleaned
