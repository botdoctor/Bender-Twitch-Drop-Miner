-- Simplified Supabase Account Management View
-- This view provides everything you need to manage accounts directly in Supabase

-- Drop the old view if it exists
DROP VIEW IF EXISTS account_management_view CASCADE;

-- Create comprehensive account management view
CREATE OR REPLACE VIEW account_management_view AS
WITH campaign_summary AS (
    SELECT 
        acp.account_id,
        json_agg(
            json_build_object(
                'campaign', c.campaign_name,
                'status', acp.status,
                'drops', COALESCE(acp.drops_claimed, 0) || '/' || COALESCE(c.total_drops, 0),
                'completed', CASE WHEN acp.status = 'completed' THEN true ELSE false END
            ) ORDER BY c.campaign_name
        ) as campaigns,
        COUNT(CASE WHEN acp.status = 'completed' THEN 1 END) as campaigns_completed,
        SUM(CASE WHEN acp.status = 'completed' THEN acp.drops_claimed ELSE 0 END) as total_drops
    FROM account_campaign_progress acp
    INNER JOIN campaigns c ON acp.campaign_id = c.id
    GROUP BY acp.account_id
)
SELECT 
    a.id,
    a.username,
    a.password,
    a.is_sold,  -- Simple boolean to toggle in Supabase UI
    COALESCE(cs.campaigns_completed, 0) as campaigns_completed,
    COALESCE(cs.total_drops, 0) as total_drops_claimed,
    cs.campaigns,
    a.is_valid,
    a.in_use,
    a.last_used,
    a.created_at,
    CASE 
        WHEN a.is_sold = true THEN 'SOLD'
        WHEN a.in_use = true THEN 'IN USE'
        WHEN a.is_valid = false THEN 'INVALID'
        ELSE 'AVAILABLE'
    END as status,
    -- Quick campaign check columns for easy filtering
    EXISTS (
        SELECT 1 FROM account_campaign_progress acp2 
        JOIN campaigns c2 ON acp2.campaign_id = c2.id
        WHERE acp2.account_id = a.id 
        AND c2.campaign_name LIKE 'Rust%' 
        AND acp2.status = 'completed'
    ) as has_rust_drops,
    EXISTS (
        SELECT 1 FROM account_campaign_progress acp3
        JOIN campaigns c3 ON acp3.campaign_id = c3.id  
        WHERE acp3.account_id = a.id
        AND c3.campaign_name LIKE '%40%'
        AND acp3.status = 'completed'
    ) as has_rust40
FROM twitch_accounts_nodrops a
LEFT JOIN campaign_summary cs ON cs.account_id = a.id
WHERE a.access_token IS NOT NULL 
AND a.user_id IS NOT NULL
ORDER BY 
    a.is_sold ASC,  -- Available accounts first
    cs.total_drops DESC NULLS LAST,  -- Then by drops
    a.username;

-- Create an even simpler view for quick account sales
CREATE OR REPLACE VIEW accounts_for_sale AS
SELECT 
    a.id,
    a.username,
    a.password,
    a.is_sold,
    string_agg(
        CASE WHEN acp.status = 'completed' 
        THEN c.campaign_name || ' (' || acp.drops_claimed || ')'
        END, ', ' ORDER BY c.campaign_name
    ) as completed_campaigns,
    SUM(CASE WHEN acp.status = 'completed' THEN acp.drops_claimed ELSE 0 END) as total_drops
FROM twitch_accounts_nodrops a
LEFT JOIN account_campaign_progress acp ON a.id = acp.account_id
LEFT JOIN campaigns c ON acp.campaign_id = c.id
WHERE a.is_sold = false
AND a.is_valid = true
AND a.access_token IS NOT NULL
GROUP BY a.id, a.username, a.password, a.is_sold
HAVING SUM(CASE WHEN acp.status = 'completed' THEN 1 ELSE 0 END) > 0
ORDER BY total_drops DESC;

-- Add helpful comments
COMMENT ON VIEW account_management_view IS 'Main view for managing accounts. Toggle is_sold to mark as sold. Filter by status for available accounts.';
COMMENT ON VIEW accounts_for_sale IS 'Simplified view showing only accounts with drops that are not sold. Perfect for quick sales management.';

-- Grant permissions for views
GRANT SELECT, UPDATE ON account_management_view TO anon, authenticated;
GRANT SELECT ON accounts_for_sale TO anon, authenticated;

-- Example queries to use in Supabase:
-- 1. Find all available accounts with Rust 40:
--    SELECT * FROM account_management_view WHERE is_sold = false AND campaigns::text LIKE '%Rust 40%' AND campaigns::text LIKE '%completed%';
-- 
-- 2. Mark account as sold (just update the boolean):
--    UPDATE twitch_accounts_nodrops SET is_sold = true WHERE id = 123;
--
-- 3. See all unsold accounts with drops:
--    SELECT * FROM accounts_for_sale;
--
-- 4. Filter by specific campaign:
--    SELECT * FROM account_management_view WHERE campaigns::text LIKE '%Rust 39%' AND is_sold = false;