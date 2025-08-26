-- Check account statistics in your database
-- Run this in Supabase SQL Editor to see account status

-- Total accounts
SELECT COUNT(*) as total_accounts FROM twitch_accounts_nodrops;

-- Accounts with tokens (ready to use)
SELECT COUNT(*) as accounts_with_tokens 
FROM twitch_accounts_nodrops 
WHERE access_token IS NOT NULL 
  AND user_id IS NOT NULL
  AND (in_use = FALSE OR in_use IS NULL)
  AND (is_valid = TRUE OR is_valid IS NULL);

-- Legacy accounts without tokens
SELECT COUNT(*) as legacy_accounts_without_tokens 
FROM twitch_accounts_nodrops 
WHERE (access_token IS NULL OR user_id IS NULL);

-- Show newest accounts with tokens (these will be used first)
SELECT id, username, created_at, 
       CASE WHEN access_token IS NOT NULL THEN 'Has Token' ELSE 'No Token' END as token_status,
       CASE WHEN user_id IS NOT NULL THEN 'Has ID' ELSE 'No ID' END as id_status
FROM twitch_accounts_nodrops 
WHERE (in_use = FALSE OR in_use IS NULL)
  AND (is_valid = TRUE OR is_valid IS NULL)
ORDER BY created_at DESC
LIMIT 10;

-- Reset any stuck accounts (optional - run if needed)
-- UPDATE twitch_accounts_nodrops SET in_use = FALSE WHERE in_use = TRUE;