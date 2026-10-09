with monthly_check as (

    select
        month_start,

        sum(total_enquiry_volume) as calculated_monthly_volume,

        max(total_monthly_enquiry_volume) as reported_monthly_volume,

        sum(channel_share_pct) as summed_channel_share_pct

    from {{ ref('mart_monthly_channel_demand') }}
    group by month_start

)

select *
from monthly_check
where calculated_monthly_volume <> reported_monthly_volume
   or abs(summed_channel_share_pct - 100.0) > 0.1