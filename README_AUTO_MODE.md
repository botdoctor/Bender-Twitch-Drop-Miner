# Automatic Account Management Integration

This document explains the new automatic account management system that integrates with your Supabase database for seamless Twitch Drop mining.

## Overview

The automatic mode allows the miner to:
- Fetch accounts automatically from your Supabase database
- Inject OAuth tokens directly without manual authentication
- Track account status (available, in_progress, invalid)
- Handle failures gracefully with automatic account rotation
- Support multiple concurrent miners with proper account allocation

## Setup

### 1. Database Schema

Create these tables in your Supabase project:

```sql
-- Main accounts table
CREATE TABLE twitch_accounts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255),
    access_token TEXT,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,
    in_use BOOLEAN DEFAULT FALSE,
    is_valid BOOLEAN DEFAULT TRUE,
    invalid_reason TEXT,
    invalidated_at TIMESTAMP
);

-- Accounts currently mining
CREATE TABLE accounts_in_progress (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES twitch_accounts(id),
    username VARCHAR(255),
    access_token TEXT,
    user_id VARCHAR(255),
    started_at TIMESTAMP DEFAULT NOW(),
    last_update TIMESTAMP,
    process_id INTEGER,
    drop_campaign VARCHAR(255),
    drop_progress INTEGER
);
```

### 2. Environment Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your Supabase credentials:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Running the Launcher

Start the launcher with:
```bash
python launcher.py
```

You'll see a menu with two options:

```
==================================================
  Twitch Drop Miner - Account Mode Selection
==================================================

  [1] Manual Mode
      - Choose account username manually
      - Activate manually if needed

  [2] Auto Mode
      - Automatic account from database
      - Automatic token injection
      - Account status tracking

  [3] Exit

==================================================

  Select mode (1-3):
```

### Manual Mode

1. Select option `1`
2. Enter your Twitch username
3. Enter the streamers file (e.g., `streamers.txt`)
4. Follow normal authentication flow if needed

### Auto Mode

1. Select option `2`
2. Enter the streamers file (e.g., `streamers.txt`)
3. The system will:
   - Fetch an available account from database
   - Inject the OAuth token automatically
   - Start mining without manual intervention
   - Track account status in the database

## Account Management

### Adding Accounts to Database

After creating accounts with your Node.js script, they should be automatically added to the `twitch_accounts` table with:
- `username`
- `password` 
- `access_token`
- `user_id`

### Account States

- **Available**: Account is ready to use (`in_use = false`, `is_valid = true`)
- **In Progress**: Account is currently mining (`accounts_in_progress` table)
- **Invalid**: Account token expired or authentication failed (`is_valid = false`)

### Monitoring

Check account status:
```sql
-- Available accounts
SELECT COUNT(*) FROM twitch_accounts WHERE in_use = FALSE AND is_valid = TRUE;

-- In progress
SELECT * FROM accounts_in_progress;

-- Invalid accounts
SELECT * FROM twitch_accounts WHERE is_valid = FALSE;
```

## Error Handling

The system handles various failure scenarios:

1. **Token Expiry (ERR_BADAUTH)**:
   - Account marked as invalid
   - Automatically fetches new account
   - Can be retried with fresh token

2. **Process Crash**:
   - Orphaned accounts cleaned up after 24 hours
   - Released back to available pool

3. **Graceful Shutdown**:
   - CTRL+C releases account properly
   - Account returned to available pool

## Multiple Instances

You can run multiple miners simultaneously:

```bash
# Terminal 1
python launcher.py  # Uses account1

# Terminal 2  
python launcher.py  # Uses account2
```

Each instance will fetch a different account from the pool.

## Troubleshooting

### No Available Accounts
```
Error: No available accounts in database!
```
**Solution**: Create more accounts or check if accounts are stuck in `in_use` state.

### Token Injection Failed
```
Failed to inject token for username
```
**Solution**: Token may be expired. Account will be marked invalid automatically.

### Database Connection Error
```
Database configuration error: SUPABASE_URL and SUPABASE_KEY must be set
```
**Solution**: Ensure `.env` file exists with correct credentials.

## API Reference

### DatabaseManager Methods

- `fetch_available_account()`: Get an unused account
- `move_to_in_progress(account_id)`: Mark account as in use
- `release_account(account_id)`: Return account to pool
- `mark_invalid(account_id, reason)`: Flag expired account
- `cleanup_orphaned_accounts(max_hours)`: Clean stuck accounts
- `get_account_stats()`: Get availability statistics

### TwitchLogin Methods

- `inject_token(access_token, user_id, cookies_file)`: Inject OAuth token
- `create_cookies_file(access_token, user_id, path)`: Create pickle file

## Security Notes

- OAuth tokens are stored in database (ensure proper security)
- Pickle files created locally for session persistence
- No passwords used in auto mode (token-based auth only)
- Tokens expire after 4-6 hours (variable per Twitch)

## Future Enhancements

- [ ] Automatic token refresh mechanism
- [ ] Web dashboard for account management
- [ ] Metrics tracking per account
- [ ] Smart account rotation based on drops
- [ ] Docker containerization for scaling