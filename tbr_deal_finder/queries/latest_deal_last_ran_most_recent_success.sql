SELECT timepoint
FROM latest_deal_run_history
WHERE ran_successfully = TRUE
ORDER BY timepoint DESC
LIMIT 1