SELECT * exclude(deal_id)
FROM retailer_deal
QUALIFY	ROW_NUMBER() OVER (PARTITION BY title, authors, retailer, format ORDER BY timepoint DESC) = 1 AND deleted IS NOT TRUE
ORDER BY title, authors, retailer, format