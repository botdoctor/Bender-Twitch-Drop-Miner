-- Campaign Tracking Schema for Twitch Drop Miner
-- This schema allows tracking multiple campaigns per account with full lifecycle management

-- Table to store available campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    campaign_name VARCHAR(255) NOT NULL UNIQUE,
    game_name VARCHAR(255),
    streamer_file VARCHAR(255), -- e.g., 'rust39.txt', 'rust40.txt'
    total_drops INTEGER DEFAULT 0, -- Total number of drops in campaign
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table to track which accounts have completed which campaigns
CREATE TABLE IF NOT EXISTS account_campaign_progress (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL,
    campaign_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'not_started', -- 'not_started', 'in_progress', 'completed', 'partial'
    drops_claimed INTEGER DEFAULT 0,
    total_drops INTEGER,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_progress_update TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, campaign_id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

-- Add account lifecycle management columns to existing table
ALTER TABLE twitch_accounts_nodrops 
ADD COLUMN IF NOT EXISTS account_status VARCHAR(20) DEFAULT 'available' 
    CHECK (account_status IN ('available', 'sold', 'given_away', 'deleted')),
ADD COLUMN IF NOT EXISTS is_sold BOOLEAN DEFAULT false, -- For backwards compatibility
ADD COLUMN IF NOT EXISTS sold_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS disposal_reason TEXT, -- Why account was removed
ADD COLUMN IF NOT EXISTS disposal_notes TEXT, -- Additional notes (who bought it, etc.)
ADD COLUMN IF NOT EXISTS last_campaign_id INTEGER REFERENCES campaigns(id);

-- Add campaign tracking to in-progress table
ALTER TABLE accounts_in_progress 
ADD COLUMN IF NOT EXISTS campaign_id INTEGER REFERENCES campaigns(id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_campaign_progress_account ON account_campaign_progress(account_id);
CREATE INDEX IF NOT EXISTS idx_campaign_progress_campaign ON account_campaign_progress(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_progress_status ON account_campaign_progress(status);
CREATE INDEX IF NOT EXISTS idx_accounts_sold ON twitch_accounts_nodrops(is_sold);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON twitch_accounts_nodrops(account_status);

-- View for mining-available accounts (excludes sold/deleted)
CREATE OR REPLACE VIEW mining_available_accounts AS
SELECT 
    a.*,
    CASE 
        WHEN a.account_status IN ('sold', 'given_away', 'deleted') THEN false
        WHEN a.is_sold = true THEN false
        WHEN a.is_valid = false THEN false
        WHEN a.in_use = true THEN false
        WHEN a.access_token IS NULL OR a.user_id IS NULL THEN false
        ELSE true
    END as truly_available
FROM twitch_accounts_nodrops a
WHERE 
    a.account_status = 'available'
    AND a.is_sold = false
    AND a.is_valid = true;

-- View to get available accounts for a specific campaign
CREATE OR REPLACE VIEW available_accounts_for_campaign AS
SELECT 
    a.id,
    a.username,
    a.access_token,
    a.user_id,
    a.created_at,
    c.id as campaign_id,
    c.campaign_name,
    COALESCE(acp.status, 'not_started') as campaign_status,
    COALESCE(acp.drops_claimed, 0) as drops_claimed,
    c.total_drops
FROM mining_available_accounts a
CROSS JOIN campaigns c
LEFT JOIN account_campaign_progress acp ON a.id = acp.account_id AND c.id = acp.campaign_id
WHERE 
    a.truly_available = true
    AND a.in_use = false
    AND c.is_active = true
    AND (acp.status IS NULL OR acp.status != 'completed');

-- View for accounts with drops (useful for selling)
CREATE OR REPLACE VIEW accounts_with_drops AS
SELECT 
    a.id,
    a.username,
    a.account_status,
    a.is_sold,
    COUNT(DISTINCT acp.campaign_id) as campaigns_completed,
    SUM(acp.drops_claimed) as total_drops_claimed,
    ARRAY_AGG(
        DISTINCT c.campaign_name 
        ORDER BY c.campaign_name
    ) as completed_campaigns,
    MAX(acp.completed_at) as last_completion_date
FROM twitch_accounts_nodrops a
INNER JOIN account_campaign_progress acp ON a.id = acp.account_id
INNER JOIN campaigns c ON acp.campaign_id = c.id
WHERE acp.status = 'completed'
GROUP BY a.id, a.username, a.account_status, a.is_sold
ORDER BY total_drops_claimed DESC, campaigns_completed DESC;

-- Function to mark account as sold
CREATE OR REPLACE FUNCTION mark_account_sold(
    p_account_id INTEGER,
    p_reason TEXT DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE twitch_accounts_nodrops
    SET 
        account_status = 'sold',
        is_sold = true,
        sold_at = CURRENT_TIMESTAMP,
        disposal_reason = p_reason,
        disposal_notes = p_notes,
        in_use = false
    WHERE id = p_account_id;
    
    -- Remove from in_progress if present
    DELETE FROM accounts_in_progress WHERE account_id = p_account_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to get campaign statistics
CREATE OR REPLACE FUNCTION get_campaign_stats(p_campaign_id INTEGER)
RETURNS TABLE(
    total_accounts INTEGER,
    completed INTEGER,
    in_progress INTEGER,
    partial INTEGER,
    not_started INTEGER,
    available INTEGER,
    sold_with_campaign INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT a.id)::INTEGER as total_accounts,
        COUNT(DISTINCT CASE WHEN acp.status = 'completed' THEN a.id END)::INTEGER as completed,
        COUNT(DISTINCT CASE WHEN acp.status = 'in_progress' THEN a.id END)::INTEGER as in_progress,
        COUNT(DISTINCT CASE WHEN acp.status = 'partial' THEN a.id END)::INTEGER as partial,
        COUNT(DISTINCT CASE 
            WHEN acp.status IS NULL OR acp.status = 'not_started' 
            THEN a.id 
        END)::INTEGER as not_started,
        COUNT(DISTINCT CASE 
            WHEN a.account_status = 'available'
            AND a.is_sold = false
            AND a.is_valid = true 
            AND a.in_use = false 
            AND (acp.status IS NULL OR acp.status NOT IN ('completed'))
            THEN a.id 
        END)::INTEGER as available,
        COUNT(DISTINCT CASE 
            WHEN a.account_status IN ('sold', 'given_away')
            AND acp.status = 'completed'
            THEN a.id 
        END)::INTEGER as sold_with_campaign
    FROM twitch_accounts_nodrops a
    LEFT JOIN account_campaign_progress acp 
        ON a.id = acp.account_id 
        AND acp.campaign_id = p_campaign_id
    WHERE a.access_token IS NOT NULL 
        AND a.user_id IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to get account campaign history
CREATE OR REPLACE FUNCTION get_account_history(p_account_id INTEGER)
RETURNS TABLE(
    campaign_name VARCHAR(255),
    game_name VARCHAR(255),
    status VARCHAR(50),
    drops_claimed INTEGER,
    total_drops INTEGER,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.campaign_name,
        c.game_name,
        acp.status,
        acp.drops_claimed,
        acp.total_drops,
        acp.started_at,
        acp.completed_at
    FROM account_campaign_progress acp
    INNER JOIN campaigns c ON acp.campaign_id = c.id
    WHERE acp.account_id = p_account_id
    ORDER BY acp.started_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Sample campaign data
INSERT INTO campaigns (campaign_name, game_name, streamer_file, total_drops, start_date, end_date) VALUES
('Rust 38', 'Rust', 'rust38.txt', 5, '2023-12-01', '2024-01-01'),
('Rust 39', 'Rust', 'rust39.txt', 5, '2024-01-01', '2024-02-01'),
('Rust 40', 'Rust', 'rust40.txt', 5, '2024-02-01', '2024-03-01'),
('Rust Christmas', 'Rust', 'rustmas.txt', 8, '2023-12-15', '2024-01-07'),
('Black Ops 6', 'Call of Duty', 'bo6.txt', 4, '2024-01-15', '2024-02-15'),
('The Finals 2', 'The Finals', 'finals2.txt', 6, '2024-01-20', '2024-02-20'),
('NBA 2K', 'NBA 2K24', 'nba2k.txt', 3, '2024-01-10', '2024-02-10')
ON CONFLICT (campaign_name) DO UPDATE
SET 
    game_name = EXCLUDED.game_name,
    streamer_file = EXCLUDED.streamer_file,
    total_drops = EXCLUDED.total_drops,
    updated_at = CURRENT_TIMESTAMP;

-- Trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_account_campaign_progress_updated_at BEFORE UPDATE ON account_campaign_progress
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();