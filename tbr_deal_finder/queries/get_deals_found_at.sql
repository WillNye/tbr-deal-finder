SELECT *
FROM seller_deal
WHERE timepoint = $timepoint AND deleted IS NOT TRUE
ORDER BY title, authors, seller, format