
  
    

  create  table "finance_dw"."udm"."prices__dbt_tmp"
  
  
    as
  
  (
    

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
  );
  