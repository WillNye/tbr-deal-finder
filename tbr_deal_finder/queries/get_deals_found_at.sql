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
WHERE rd.timepoint = $timepoint AND rd.deleted IS NOT TRUE AND rd.is_internal IS NOT TRUE
  AND rd.is_heartbeat IS NOT TRUE
ORDER BY rd.title, rd.authors, rd.retailer, rd.format
