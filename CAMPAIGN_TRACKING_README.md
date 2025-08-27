# Campaign Tracking System

## Overview
The Campaign Tracking System allows you to:
- Track multiple campaigns per account
- Monitor which accounts have completed which campaigns  
- Prevent sold/given away accounts from being reused
- Manage account lifecycle (available → in use → sold)
- Generate reports on campaign progress and account value

## Database Setup

### 1. Run the Schema Script in Supabase
Execute the contents of `campaign_tracking_schema.sql` in your Supabase SQL editor. This will:
- Create campaign tables
- Add account lifecycle tracking
- Set up views and functions
- Insert sample campaign data

### 2. Required Environment Variables
Ensure your `.env` file contains:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

## Using the System

### Auto Mode with Campaign Selection

When you run the launcher in auto mode (`python launcher.py` → Option 2), you'll now see:

```
========================================
  Campaign Selection
========================================

  [1] Rust 39 (Rust)
      Streamer file: rust39.txt
      Total drops: 5
      
  [2] Rust 40 (Rust)
      Streamer file: rust40.txt
      Total drops: 5

  [3] Black Ops 6 (Call of Duty)
      Streamer file: bo6.txt
      Total drops: 4

  [4] Manage Accounts (View/Mark as Sold)
  [5] Back to Main Menu
```

After selecting a campaign, you'll see statistics:
```
Campaign: Rust 40
==================================================
  Total Accounts: 60
  Available: 45
  In Progress: 3
  Partial: 2
  Completed: 10
  Not Started: 45
```

### Account Management

From the campaign selection menu, choose "Manage Accounts" to:
- View accounts with completed drops
- Mark accounts as sold/given away
- See campaign completion history

**Important**: Once an account is marked as sold, it will NEVER appear in mining selections again.

### Campaign Manager CLI

Use `campaign_manager.py` for advanced management:

```bash
python campaign_manager.py
```

Features:
- View all campaigns and their statistics
- Add new campaigns
- View accounts with drops (ready to sell)
- Mark accounts as sold with notes
- Generate progress reports
- Export data to CSV

## Campaign Lifecycle

### 1. Adding a Campaign
```python
# In campaign_manager.py
Campaign Name: Rust 41
Game Name: Rust
Streamer File: rust41.txt
Total Drops: 5
```

### 2. Mining Process
1. Select campaign in auto mode
2. System finds available account (excludes sold)
3. Account moves to `in_progress` status
4. Drops are tracked during mining
5. Campaign marked `completed` when done

### 3. Account States
- **available**: Can be used for mining
- **in_use**: Currently mining (temporary)
- **sold**: Permanently unavailable
- **given_away**: Permanently unavailable

### 4. Selling Accounts
When marking as sold:
- Account becomes permanently unavailable
- Campaign history is preserved
- Can add notes (who bought it, price, etc.)

## Database Tables

### campaigns
Stores campaign information:
- campaign_name (e.g., "Rust 40")
- game_name
- streamer_file
- total_drops
- is_active

### account_campaign_progress
Tracks account progress per campaign:
- account_id
- campaign_id
- status (not_started/in_progress/partial/completed)
- drops_claimed
- completed_at

### Account Modifications
Added to `twitch_accounts_nodrops`:
- account_status (available/sold/given_away)
- is_sold (boolean)
- sold_at (timestamp)
- disposal_reason
- disposal_notes

## Key Features

### Smart Account Selection
The system prioritizes accounts:
1. Fresh accounts (never mined this campaign)
2. Partial progress accounts (if enabled)
3. Never shows sold accounts

### Campaign Statistics
Track per campaign:
- Total accounts available
- Completion rates
- Accounts sold with drops
- Progress visualization

### Safety Features
- Sold accounts never appear in selections
- Confirmation required for marking as sold
- Full audit trail of account lifecycle
- Export capabilities for record keeping

## Common Workflows

### Starting a New Campaign
1. Add campaign in campaign_manager.py
2. Run auto mode from launcher
3. Select the new campaign
4. System finds best available account
5. Mining begins with tracking

### Selling Accounts After Campaign
1. Run campaign_manager.py
2. View accounts with drops
3. Select accounts to mark as sold
4. Add notes (buyer info, price, etc.)
5. Accounts permanently excluded from future mining

### Checking Campaign Progress
1. Run campaign_manager.py
2. Select "Campaign Progress Report"
3. View completion rates and available accounts
4. Export data if needed

## Troubleshooting

### No Available Accounts
- Check if accounts are marked as sold
- Verify accounts have valid tokens
- Check campaign completion status
- Release in_progress accounts if stuck

### Campaign Not Showing
- Ensure campaign is marked as active
- Check if streamer file exists
- Verify campaign was added to database

### Accounts Appearing After Being Sold
- Check both `is_sold` and `account_status` fields
- Ensure database migration completed
- Verify using latest DatabaseManager

## Best Practices

1. **Regular Exports**: Export account data before major sales
2. **Clear Notes**: Document why accounts were sold/given away
3. **Campaign Planning**: Add campaigns before they start
4. **Progress Monitoring**: Check campaign stats regularly
5. **Account Hygiene**: Clean up invalid/orphaned accounts

## Support

For issues or questions about the campaign tracking system:
1. Check this README first
2. Review the SQL schema for database structure
3. Check logs for error messages
4. Ensure all environment variables are set