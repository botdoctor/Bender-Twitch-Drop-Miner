# Simplified Campaign Tracking System

## Quick Start

### 1. Configure Campaigns
Edit `campaigns.json` to define your campaigns:
```json
{
  "rust40.txt": {
    "drops": 5,
    "game": "Rust",
    "name": "Rust 40"
  }
}
```

### 2. Run Auto Mode
```bash
python launcher.py
# Select Option 2 (Auto Mode)
# System auto-detects campaigns from .txt files
# Select campaign → Mining starts
```

### 3. Auto-Complete & Exit
- System tracks drops claimed
- When drops_claimed == expected_drops:
  - Campaign marked complete
  - Account released
  - **Program exits automatically**

## Discord Notifications

Set `DISCORD_WEBHOOK` in `.env` to receive:

### Mining Started
```
🎮 Mining Started
Account: username123
Campaign: Rust 40
Expected Drops: 5
Previous Campaigns: Rust 39 ✓
```

### Drop Claimed
```
🎁 Drop Claimed!
Account: username123
Campaign: Rust 40
Progress: 3/5 drops
Status: 60% complete
```

### Campaign Completed
```
✅ Campaign Completed!
Account: username123
Campaign: Rust 40
Total Drops: 5/5
Account Stats: 3 campaigns, 15 total drops
Status: Account released back to pool
```

## Managing Accounts in Supabase

### View All Accounts
1. Go to Supabase → Table Editor
2. Select `account_management_view`
3. You'll see:
   - Username & Password
   - is_sold (toggle to mark as sold)
   - Campaign completions
   - Total drops
   - Status (AVAILABLE/SOLD/IN USE)

### Mark Account as Sold
Simply toggle the `is_sold` boolean to `true` in the view

### Filter Accounts
```sql
-- Available accounts with Rust 40
SELECT * FROM account_management_view 
WHERE is_sold = false 
AND campaigns::text LIKE '%Rust 40%completed%';

-- All unsold accounts with drops
SELECT * FROM accounts_for_sale;
```

## How It Works

### Campaign Auto-Detection
1. System scans for .txt files
2. Matches to campaigns.json
3. Shows only campaigns with files present
4. No manual database management needed

### Drop Tracking
1. Monitors actual drops claimed
2. Updates database in real-time
3. Sends Discord notifications
4. Auto-completes when target reached

### Account Lifecycle
```
Available → In Use → Completed → Available
                         ↓
                    Can Mark as Sold
                         ↓
                    Never Used Again
```

## Files Overview

- `campaigns.json` - Campaign definitions
- `launcher.py` - Auto-detects campaigns, manages flow
- `DatabaseManager.py` - Handles tracking & Discord
- `supabase_account_view.sql` - Creates management views

## Key Features

✅ **Auto-detect campaigns** from .txt files  
✅ **Auto-complete & exit** when drops done  
✅ **Discord notifications** for all events  
✅ **Simple Supabase UI** for sales  
✅ **Never reuse sold accounts**  
✅ **Track multiple campaigns** per account  

## Common Tasks

### Add New Campaign
1. Add streamer file (e.g., rust41.txt)
2. Update campaigns.json:
```json
"rust41.txt": {
  "drops": 5,
  "game": "Rust",
  "name": "Rust 41"
}
```
3. Run launcher - campaign appears automatically

### Sell Accounts
1. Open Supabase
2. Go to `accounts_for_sale` view
3. See all accounts with drops
4. Toggle `is_sold` to true
5. Account never appears in mining again

### Check Progress
Watch Discord notifications or check Supabase:
- `account_management_view` shows all details
- Filter by campaign name to find specific accounts

## Troubleshooting

### Campaign Not Showing
- Check .txt file exists
- Verify campaigns.json has entry
- File must be in root directory

### Not Auto-Exiting
- Check expected_drops in campaigns.json
- Verify drops are being claimed
- Check Discord for progress updates

### Sold Account Appearing
- Ensure is_sold = true in database
- Check account_status = 'sold'
- Run SQL migration if needed