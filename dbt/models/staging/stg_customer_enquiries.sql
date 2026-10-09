select
	date as enquiry_date,
	channel,
	work_site,
	category,
	service,
	volume
from {{source('brisbane_open_data', 'customer_enquiries')}}
