#!/usr/bin/env python3
"""
Comprehensive Twitch Channel Points Miner Test Script
Mimics main.py functionality with account and streamer file configuration
Usage: python3 comprehensive_test.py --username [username] --streamers-file [file]
"""

import logging
import os
import sys
import argparse
from pathlib import Path
from colorama import Fore
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings, Condition, OutcomeKeys, FilterCondition, DelayMode
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

def get_account_config():
    """Get account configuration from command line arguments or interactive input"""
    parser = argparse.ArgumentParser(description="Comprehensive Twitch Channel Points Miner Test")
    parser.add_argument("--username", help="Twitch username")
    parser.add_argument("--streamers-file", help="File containing streamer usernames")
    parser.add_argument("--analytics-port", type=int, default=5000, help="Analytics server port")
    parser.add_argument("--workspace", help="Account workspace directory")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode (prompt for inputs)")
    parser.add_argument("--password", help="Twitch password (use environment variable ACCOUNT_PASSWORD for security)")
    parser.add_argument("--enable-betting", action="store_true", help="Enable betting/predictions (disabled by default for safety)")
    parser.add_argument("--max-streamers", type=int, default=10, help="Maximum number of streamers to watch simultaneously")
    
    args = parser.parse_args()
    
    # Get configuration from arguments, environment variables, or interactive input
    if args.interactive or (not args.username and not os.getenv('ACCOUNT_USERNAME')):
        print("🎮 Comprehensive Twitch Channel Points Miner Test")
        print("=" * 50)
        username = input("Enter your Twitch username: ")
        password = input("Enter your Twitch password (or press Enter to use environment variable): ") or os.getenv('ACCOUNT_PASSWORD')
        filename = input("Enter streamer file name (default: ruststreamers.txt): ") or "ruststreamers.txt"
        analytics_port = int(input("Enter analytics port (default: 5000): ") or "5000")
        workspace_dir = input("Enter workspace directory (optional, press Enter to skip): ") or None
        enable_betting = input("Enable betting/predictions? (y/N): ").lower().startswith('y')
        max_streamers = int(input("Maximum streamers to watch simultaneously (default: 10): ") or "10")
    else:
        username = args.username or os.getenv('ACCOUNT_USERNAME')
        password = args.password or os.getenv('ACCOUNT_PASSWORD')
        filename = args.streamers_file or os.getenv('STREAMERS_FILE', 'ruststreamers.txt')
        analytics_port = args.analytics_port or int(os.getenv('ANALYTICS_PORT', '5000'))
        workspace_dir = args.workspace or os.getenv('WORKSPACE_DIR')
        enable_betting = args.enable_betting or os.getenv('ENABLE_BETTING', '').lower() in ['true', '1', 'yes']
        max_streamers = args.max_streamers or int(os.getenv('MAX_STREAMERS', '10'))
        
    if not username:
        print("❌ Error: Username is required. Use --username or set ACCOUNT_USERNAME environment variable")
        sys.exit(1)
        
    return username, password, filename, analytics_port, workspace_dir, enable_betting, max_streamers

def setup_account_workspace(username, workspace_dir):
    """Setup account-specific workspace and return paths"""
    if workspace_dir:
        # Create workspace directory if it doesn't exist
        Path(workspace_dir).mkdir(parents=True, exist_ok=True)
        
        # Account-specific file paths
        cookies_file = os.path.join(workspace_dir, f"cookies_{username}.pkl")
        logs_dir = os.path.join(workspace_dir, "logs")
        Path(logs_dir).mkdir(exist_ok=True)
        
        return cookies_file, logs_dir
    else:
        # Use default locations
        logs_dir = "logs"
        Path(logs_dir).mkdir(exist_ok=True)
        return f"cookies_{username}.pkl", logs_dir

def load_streamers_from_file(filename, max_streamers=10):
    """Load streamers from file with error handling"""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            streamer_usernames = [line.strip() for line in file if line.strip()]
            
        if not streamer_usernames:
            print(f"⚠️  Warning: No streamers found in '{filename}'")
            return []
            
        # Limit number of streamers if specified
        if max_streamers > 0:
            streamer_usernames = streamer_usernames[:max_streamers]
            
        print(f"📋 Loaded {len(streamer_usernames)} streamers from '{filename}'")
        return streamer_usernames
        
    except FileNotFoundError:
        print(f"❌ Error: The file '{filename}' was not found.")
        print("Available streamer files:")
        for file in Path(".").glob("*streamers*.txt"):
            print(f"  - {file.name}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading streamers file: {e}")
        sys.exit(1)

def create_streamer_settings(enable_betting=False):
    """Create streamer settings with optional betting"""
    if enable_betting:
        bet_settings = BetSettings(
            strategy=Strategy.SMART,            # Choose strategy!
            percentage=5,                       # Place 5% of your channel points
            percentage_gap=20,                  # Gap difference between outcomes
            max_points=50000,                   # Maximum points to bet
            stealth_mode=True,                  # Avoid being highest bet
            delay_mode=DelayMode.FROM_END,      # Wait until near end of timer
            delay=6,                           # 6 seconds before end
            minimum_points=20000,               # Only bet if we have 20k+ points
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOTAL_USERS,     # Filter by total users
                where=Condition.LTE,            # Less than or equal to
                value=800                       # 800 users
            )
        )
        print("🎰 Betting/predictions ENABLED")
    else:
        bet_settings = BetSettings(
            strategy=Strategy.SMART,
            percentage=0,                       # 0% = no betting
            max_points=0                        # No betting
        )
        print("🚫 Betting/predictions DISABLED (safer for testing)")
    
    return StreamerSettings(
        make_predictions=enable_betting,        # Enable/disable betting
        follow_raid=True,                       # Follow raids for more points
        claim_drops=True,                       # Claim drops automatically
        claim_moments=True,                     # Claim moments when available
        watch_streak=True,                      # Catch watch streaks
        community_goals=True,                   # Contribute to community goals
        chat=ChatPresence.ONLINE,               # Join chat when streamer is online
        bet=bet_settings
    )

def main():
    """Main function"""
    # Get configuration
    username, password, filename, analytics_port, workspace_dir, enable_betting, max_streamers = get_account_config()
    cookies_file, logs_dir = setup_account_workspace(username, workspace_dir)
    
    print(f"\n🎮 Starting Twitch Channel Points Miner for: {username}")
    print(f"📁 Streamers file: {filename}")
    print(f"📊 Analytics port: {analytics_port}")
    print(f"🍪 Cookies file: {cookies_file}")
    print(f"📝 Logs directory: {logs_dir}")
    print(f"👥 Max streamers: {max_streamers}")
    
    # Load streamers from file
    streamer_usernames = load_streamers_from_file(filename, max_streamers)
    
    if not streamer_usernames:
        print("❌ No streamers to watch. Exiting.")
        sys.exit(1)
    
    print(f"📺 Watching streamers: {', '.join(streamer_usernames[:5])}")
    if len(streamer_usernames) > 5:
        print(f"    ... and {len(streamer_usernames) - 5} more")
    
    # Create streamer settings
    streamer_settings = create_streamer_settings(enable_betting)
    
    # Initialize TwitchChannelPointsMiner
    print("\n⚡ Initializing Twitch Channel Points Miner...")
    twitch_miner = TwitchChannelPointsMiner(
        username=username,
        password=password,  # Will trigger manual login if None
        claim_drops_startup=True,                  # Auto claim all drops on startup
        priority=[                                 # Priority order
            Priority.DROPS,                        # Prioritize drops
            Priority.ORDER                         # Then use order priority
        ],
        enable_analytics=True,                     # Enable analytics
        disable_ssl_cert_verification=False,       # Keep SSL verification
        disable_at_in_nickname=False,              # Require @ for mentions
        logger_settings=LoggerSettings(
            save=True,                             # Save logs to file
            console_level=logging.INFO,            # Console log level
            console_username=True,                 # Show username in logs
            auto_clear=True,                       # Rotate log files
            time_zone="",                          # Use system timezone
            file_level=logging.DEBUG,              # Detailed file logs
            emoji=True,                            # Use emojis in logs
            less=False,                            # Verbose logging
            colored=True,                          # Colored console output
            color_palette=ColorPalette(
                STREAMER_online="GREEN",
                streamer_offline="red",
                BET_wiN=Fore.MAGENTA
            )
        ),
        streamer_settings=streamer_settings
    )
    
    # Start analytics server
    if analytics_port > 0:
        try:
            twitch_miner.analytics(host="127.0.0.1", port=analytics_port, refresh=5, days_ago=7)
            print(f"📊 Analytics server started on http://127.0.0.1:{analytics_port}")
        except Exception as e:
            print(f"⚠️  Analytics server failed to start on port {analytics_port}: {e}")
            print("Continuing without analytics...")
    
    # Convert streamers - use Streamer objects for first few, usernames for the rest
    # This mimics main.py behavior for better performance with many streamers
    streamers = [
        Streamer(username) if i < 5 else username 
        for i, username in enumerate(streamer_usernames)
    ]
    
    print(f"\n🚀 Starting the miner...")
    print(f"💡 Manual login required - complete activation when prompted")
    print(f"🎯 Watching {len(streamers)} streamers for drops and points")
    print(f"⏹️  Press Ctrl+C to stop")
    
    # Start mining
    try:
        twitch_miner.mine(
            streamers,                             # List of streamers
            followers=False,                       # Don't auto-download followers
            followers_order=FollowersOrder.ASC     # Follow date order (if used)
        )
    except KeyboardInterrupt:
        print("\n⏹️  Stopping miner...")
        print("👋 Thanks for using the comprehensive test script!")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        print("Check the logs for more details")
        sys.exit(1)

if __name__ == "__main__":
    main()