SELECT *
FROM seller_deal
QUALIFY	ROW_NUMBER() OVER (PARTITION BY title, authors, seller, format ORDER BY timepoint DESC) = 1 AND deleted IS NOT TRUE
ORDER BY title, authors, seller, format