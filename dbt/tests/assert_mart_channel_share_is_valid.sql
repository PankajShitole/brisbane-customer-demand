select
    month_start,
    channel,
    channel_share_pct
from {{ ref('mart_monthly_channel_demand') }}
where channel_share_pct < 0
   or channel_share_pct > 100
