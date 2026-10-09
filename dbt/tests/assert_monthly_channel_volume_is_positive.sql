select
    month_start,
    channel,
    total_enquiry_volume
from {{ ref('int_monthly_demand_by_channel') }}
where total_enquiry_volume <= 0
