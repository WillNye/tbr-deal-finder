SELECT * exclude(deal_id)
FROM retailer_deal
WHERE is_internal IS NOT TRUE
QUALIFY	ROW_NUMBER() OVER (PARTITION BY title, authors, retailer, format ORDER BY timepoint DESC) = 1 AND deleted IS NOT TRUE
ORDER BY title, authors, retailer, format