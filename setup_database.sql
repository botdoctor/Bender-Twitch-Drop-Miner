-- Database setup for Twitch Drop Miner Auto Mode
-- Run this in Supabase SQL Editor

-- Add missing columns to existing twitch_accounts_nodrops table
ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS last_used TIMESTAMP;

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS in_use BOOLEAN DEFAULT FALSE;

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE;

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS invalid_reason TEXT;

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS invalidated_at TIMESTAMP;

-- Create the in-progress tracking table
CREATE TABLE IF NOT EXISTS accounts_in_progress (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES twitch_accounts_nodrops(id) ON DELETE CASCADE,
    username VARCHAR(255),
    access_token TEXT,
    user_id VARCHAR(255),
    started_at TIMESTAMP DEFAULT NOW(),
    last_update TIMESTAMP,
    process_id INTEGER,
    drop_campaign VARCHAR(255),
    drop_progress INTEGER
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_twitch_accounts_in_use ON twitch_accounts_nodrops(in_use);
CREATE INDEX IF NOT EXISTS idx_twitch_accounts_is_valid ON twitch_accounts_nodrops(is_valid);
CREATE INDEX IF NOT EXISTS idx_accounts_in_progress_account_id ON accounts_in_progress(account_id);

-- Enable RLS for accounts_in_progress
ALTER TABLE accounts_in_progress ENABLE ROW LEVEL SECURITY;

-- Create policies for accounts_in_progress
CREATE POLICY "Enable all for anonymous users" 
ON accounts_in_progress 
FOR ALL 
TO anon
USING (true)
WITH CHECK (true);

-- Verify the tables
SELECT 'twitch_accounts_nodrops columns:' as info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'twitch_accounts_nodrops' 
ORDER BY ordinal_position;

SELECT 'accounts_in_progress columns:' as info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'accounts_in_progress' 
ORDER BY ordinal_position;

-- Check for any accounts ready to use
SELECT COUNT(*) as available_accounts 
FROM twitch_accounts_nodrops 
WHERE access_token IS NOT NULL 
  AND user_id IS NOT NULL 
  AND (in_use = FALSE OR in_use IS NULL)
  AND (is_valid = TRUE OR is_valid IS NULL);