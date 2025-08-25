SELECT timepoint
FROM unknown_book_run_history
WHERE ran_successfully = TRUE
ORDER BY timepoint DESC
LIMIT 1