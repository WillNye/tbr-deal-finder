SELECT * exclude(deal_id)
FROM retailer_deal
WHERE timepoint = $timepoint AND deleted IS NOT TRUE AND is_internal IS NOT TRUE
ORDER BY title, authors, retailer, format