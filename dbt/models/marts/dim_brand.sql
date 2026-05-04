select
    brand_id::integer as brand_id,
    brand_term,
    brand_name,
    brand_type,
    parent_company
from {{ ref('dim_brand_seed') }}
