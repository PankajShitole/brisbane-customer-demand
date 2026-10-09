select
    month_start,
    channel,
    count(*) as duplicate_count
from {{ ref('mart_monthly_channel_demand') }}
group by
    month_start,
    channel
having count(*) > 1

