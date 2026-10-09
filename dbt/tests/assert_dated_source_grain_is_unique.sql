select
    enquiry_date,
    channel,
    work_site,
    category,
    service,
    count(*) as duplicate_count
from {{ ref('stg_customer_enquiries') }}
where enquiry_date is not null
group by
    enquiry_date,
    channel,
    work_site,
    category,
    service
having count(*) > 1
