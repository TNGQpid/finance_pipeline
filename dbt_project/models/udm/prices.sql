{{ config(materialized='table') }}

select
    symbol,
    date::date as date,
    open,
    high,
    low,
    close,
    volume
from {{ source('raw', 'prices') }}
where close is not null
