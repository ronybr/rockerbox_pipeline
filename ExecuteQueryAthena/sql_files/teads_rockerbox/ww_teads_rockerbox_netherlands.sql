UNLOAD (select
    cast(substring(day,1,10) as date) as day,
    advertiser_id as "publisher_id",
    'Weight Watchers' as publisher,
    campaign_id as "campaign_id",
    campaign_name as campaign,
    line_item_id as "placement_id",
    line_item_name as "placement",
    creative_id as "creative_id",
    creative_name as "creative_name",
    case
        when SUBSTR(day, 1, 10) < '2021-12-19'
        then budget_spent * 2 else budget_spent end as spend_eur
from curated_teads."mediascale_belgium_seat_complete"
where advertiser_id = 20591
and (upper(line_item_name) like '%NL_NL%')
and cast(substring(day,1,10) as date) >= date_add('day', -7, current_date))
TO 's3://mediascale-datalake-dev/application_data/rockerbox/rockerbox_netherlands/'
WITH (format = 'PARQUET', compression = 'snappy');