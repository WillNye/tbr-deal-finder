SELECT rd.* EXCLUDE(deal_id), tb.image_url
FROM retailer_deal rd
LEFT JOIN (
    -- Match on title+authors only (NOT format): library-export books are stored
    -- with format='N/A', so a format-aware join would miss their covers. A cover is
    -- edition-agnostic, and MAX() collapses to one cover per title so deals can't fan out.
    SELECT title, authors, MAX(image_url) AS image_url
    FROM tbr_book
    GROUP BY title, authors
) tb
    ON rd.title = tb.title AND rd.authors = tb.authors
WHERE rd.is_internal IS NOT TRUE
QUALIFY	ROW_NUMBER() OVER (PARTITION BY rd.title, rd.authors, rd.retailer, rd.format ORDER BY rd.timepoint DESC) = 1 AND rd.deleted IS NOT TRUE
ORDER BY rd.title, rd.authors, rd.retailer, rd.format
