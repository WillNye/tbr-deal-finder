SELECT *
FROM retailer_deal
WHERE timepoint = $timepoint AND deleted IS NOT TRUE
ORDER BY title, authors, retailer, format