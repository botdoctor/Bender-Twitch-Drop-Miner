# Setup Instructions for Campaign Tracking

## Step 1: Database Setup (REQUIRED)

Run this SQL in your Supabase SQL Editor:

1. Go to Supabase Dashboard
2. Click on "SQL Editor" 
3. Copy and paste the contents of `setup_campaign_tables.sql`
4. Click "Run"

This creates:
- `campaigns` table
- `account_campaign_progress` table  
- Required columns on existing tables
- Indexes and policies

## Step 2: Verify Installation

After running the SQL, you should see:
- "Campaigns table: row_count X"
- "Progress table: row_count 0"

## Step 3: Test the System

1. Run `python launcher.py`
2. Select Option 2 (Auto Mode)
3. You should see campaigns auto-detected from your .txt files
4. Select a campaign to start mining

## Troubleshooting

### "account_campaign_progress table doesn't exist"
- Run `setup_campaign_tables.sql` in Supabase

### "No campaigns showing"
- Check that you have .txt files in the directory
- Verify `campaigns.json` has entries for your files

### "Error fetching campaign"
- This is normal for new campaigns - they auto-create on first selection
- Just ignore the error messages

### Discord Notifications Not Working
- Set `DISCORD_WEBHOOK` in your `.env` file
- Format: `DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE`

## How It Works

1. **Auto-Detection**: Scans for .txt files and matches to campaigns.json
2. **Auto-Creation**: Creates campaigns in database on first use
3. **Drop Tracking**: Monitors drops and auto-completes at target
4. **Discord Updates**: Sends notifications for start/progress/complete
5. **Auto-Exit**: Exits when campaign completes

## Managing Accounts

In Supabase:
1. Go to Table Editor
2. Find `twitch_accounts_nodrops` 
3. Toggle `is_sold` to mark accounts as sold
4. Sold accounts never appear in mining again