-- Quick setup for campaign tracking tables
-- Run this in Supabase SQL Editor to create the necessary tables

-- First ensure campaigns table exists
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(255) NOT NULL UNIQUE,
    game_name VARCHAR(255),
    streamer_file VARCHAR(255),
    total_drops INTEGER DEFAULT 0,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create account campaign progress tracking
CREATE TABLE IF NOT EXISTS account_campaign_progress (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'not_started',
    drops_claimed INTEGER DEFAULT 0,
    total_drops INTEGER,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_progress_update TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, campaign_id)
);

-- Add missing columns to existing tables (safe - won't error if they exist)
ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS account_status VARCHAR(20) DEFAULT 'available';

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS is_sold BOOLEAN DEFAULT false;

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS sold_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS disposal_reason TEXT;

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS disposal_notes TEXT;

ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS last_campaign_id INTEGER REFERENCES campaigns(id);

ALTER TABLE accounts_in_progress 
ADD COLUMN IF NOT EXISTS campaign_id INTEGER REFERENCES campaigns(id);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_campaign_progress_account ON account_campaign_progress(account_id);
CREATE INDEX IF NOT EXISTS idx_campaign_progress_campaign ON account_campaign_progress(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_progress_status ON account_campaign_progress(status);
CREATE INDEX IF NOT EXISTS idx_accounts_sold ON twitch_accounts_nodrops(is_sold);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON twitch_accounts_nodrops(account_status);

-- Enable RLS
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE account_campaign_progress ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Enable all for anonymous users on campaigns" 
ON campaigns 
FOR ALL 
TO anon
USING (true)
WITH CHECK (true);

CREATE POLICY "Enable all for anonymous users on progress" 
ON account_campaign_progress 
FOR ALL 
TO anon
USING (true)
WITH CHECK (true);

-- Insert some sample campaigns (won't duplicate due to UNIQUE constraint)
INSERT INTO campaigns (campaign_name, game_name, streamer_file, total_drops) VALUES
('Rust 38', 'Rust', 'rust38.txt', 5),
('Rust 39', 'Rust', 'rust39.txt', 5),
('Rust 40', 'Rust', 'rust40.txt', 5)
ON CONFLICT (campaign_name) DO NOTHING;

-- Verify tables were created
SELECT 'Campaigns table:' as info, COUNT(*) as row_count FROM campaigns;
SELECT 'Progress table:' as info, COUNT(*) as row_count FROM account_campaign_progress;