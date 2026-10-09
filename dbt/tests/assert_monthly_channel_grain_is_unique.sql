select
    month_start,
    channel,
    count(*) as duplicate_count
from {{ ref('int_monthly_demand_by_channel') }}
group by
    month_start,
    channel
having count(*) > 1
