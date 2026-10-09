with monthly_totals as (

    select
        month_start,
        channel,
        total_enquiry_volume,

        sum(total_enquiry_volume) over (
            partition by month_start
        ) as total_monthly_enquiry_volume

    from {{ref('int_monthly_demand_by_channel')}}

)

select
	month_start,
	channel,
	total_enquiry_volume,
	total_monthly_enquiry_volume,
	round(100 * total_enquiry_volume / nullif(total_monthly_enquiry_volume, 0),2) as channel_share_pct

from monthly_totals
