select
	date_trunc('month', enquiry_date)::date as month_start,
	channel,
	sum(volume) as total_enquiry_volume
from {{ref('stg_customer_enquiries')}}
group by 1,2
