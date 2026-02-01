

select
    symbol,
    date::date as date,
    open,
    high,
    low,
    close,
    volume
from "finance_dw"."raw"."prices"
where close is not null