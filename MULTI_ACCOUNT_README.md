# Multi-Account Twitch Mining System

This system allows you to run multiple Twitch mining accounts simultaneously with automatic TV login activation.

## Features

- **Multi-Account Support**: Run multiple Twitch accounts simultaneously
- **Automatic TV Login**: Each account uses TV login method with automated browser activation
- **Process Isolation**: Each account runs in its own process with separate workspaces
- **Account Management**: Start, stop, restart, and monitor individual accounts
- **Resource Management**: Separate analytics ports, logs, and cookies per account
- **Auto-Restart**: Failed accounts are automatically restarted with backoff
- **Scalable**: Easy to add/remove accounts and prepare for Supabase integration

## Quick Start

### 1. Setup Accounts

Create or update your `pass.txt` file with account credentials:
```
username1:password1
username2:password2
username3:password3
```

### 2. Create Configuration

```bash
python3 multi_account_manager.py --action config --pass-file pass.txt
```

This creates `multi_account_config.json` with your account settings.

### 3. Start All Accounts

```bash
python3 multi_account_manager.py
```

This will:
- Start mining processes for all configured accounts
- Each account gets its own workspace directory (`accounts/username/`)
- Analytics servers start on ports 5000, 5001, 5002, etc.
- TV login codes are automatically activated via Selenium

### 4. Monitor Status

```bash
python3 multi_account_manager.py --action status
```

## File Structure

```
Twitchminer/
├── multi_account_manager.py      # Main management script
├── main.py                       # Modified miner (supports account args)
├── login.py                      # Enhanced for multi-account
├── pass.txt                      # Account credentials
├── multi_account_config.json     # Generated configuration
├── accounts/                     # Account workspaces
│   ├── username1/
│   │   ├── cookies.pkl          # Account-specific cookies
│   │   └── logs/                # Account-specific logs
│   ├── username2/
│   └── username3/
└── activation_code_*.txt         # Temporary TV activation files
```

## Analytics Access

Each account gets its own analytics server:
- Account 1: http://localhost:5000
- Account 2: http://localhost:5001  
- Account 3: http://localhost:5002
- And so on...

## Command Reference

### Multi-Account Manager Commands

```bash
# Start all accounts (default)
python3 multi_account_manager.py

# Generate configuration from pass.txt
python3 multi_account_manager.py --action config

# Check status of all accounts
python3 multi_account_manager.py --action status

# Stop all running accounts
python3 multi_account_manager.py --action stop

# Use custom config file
python3 multi_account_manager.py --config my_config.json
```

### Single Account Commands

```bash
# Run single account interactively
python3 main.py --interactive

# Run single account with parameters
python3 main.py --username myuser --streamers-file rust.txt --analytics-port 5010

# Manual TV login activation
python3 login.py --account-file activation_code_myuser.txt
```

## Configuration

### Multi-Account Settings

Edit `multi_account_config.json` to customize:

```json
{
  "accounts": [
    {
      "username": "username1",
      "password": "password1", 
      "streamers_file": "ruststreamers.txt",
      "analytics_port": 5000
    }
  ],
  "settings": {
    "max_restarts": 3,
    "restart_delay": 60,
    "base_analytics_port": 5000
  }
}
```

### Account-Specific Settings

- **streamers_file**: Which streamers each account should watch
- **analytics_port**: Unique port for each account's web interface
- **max_restarts**: How many times to restart failed accounts
- **restart_delay**: Seconds to wait between restart attempts

## Logging

Each account maintains separate logs:
- `accounts/username/logs/username.log` - Account-specific mining logs
- `login_username.log` - TV activation logs per account
- `multi_account_manager.log` - Overall system logs

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure each account has a unique analytics port
2. **Chrome/Selenium Issues**: Install Chrome/Chromium for TV login automation
3. **File Permissions**: Ensure write access to account directories
4. **Resource Limits**: Monitor CPU/memory usage with many accounts

### Debug Mode

Enable debug logging by modifying the log level in the scripts:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Manual TV Activation

If automatic activation fails, you can manually activate:
1. Note the TV code from the miner logs
2. Go to https://www.twitch.tv/activate
3. Enter the code and login manually

## System Requirements

- **Python 3.7+**
- **Chrome/Chromium** (for Selenium automation)
- **Sufficient RAM** (each account uses ~100-200MB)
- **Network Bandwidth** (each account streams video)

## Scaling Considerations

### For Many Accounts (10+):
- Monitor system resource usage
- Consider distributing across multiple servers
- Implement rate limiting for API calls
- Use proxy rotation if needed

### For Production:
- Set up monitoring and alerting
- Implement database backend (Supabase ready)
- Add API for remote management
- Set up log aggregation

## Future Enhancements

- **Supabase Integration**: Store accounts in database instead of pass.txt
- **Web Interface**: Manage accounts via web UI
- **Account Rotation**: Automatically switch accounts on schedule
- **Proxy Support**: Route each account through different proxies
- **Statistics Dashboard**: Aggregate points/drops across all accounts

## Testing

Run the test suite to verify everything works:

```bash
python3 test_multi_account.py
```

This tests configuration generation, argument parsing, and basic functionality without actually running miners.