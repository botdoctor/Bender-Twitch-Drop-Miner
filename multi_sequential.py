#!/usr/bin/env python3
"""
Multi-Account Twitch Channel Points Miner (Sequential)
Automatically logs in multiple accounts from pass.txt one at a time
"""

import logging
import os
import sys
import time
from pathlib import Path
from colorama import Fore
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings, Condition, OutcomeKeys, FilterCondition, DelayMode
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

def load_accounts(pass_file="pass.txt"):
    """Load accounts from pass.txt file"""
    accounts = []
    try:
        with open(pass_file, "r", encoding="utf-8") as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if line and ":" in line:
                    username, password = line.split(":", 1)
                    accounts.append((username.strip(), password.strip()))
                elif line:  # Non-empty line without colon
                    print(f"⚠️  Warning: Invalid format on line {line_num}: {line}")
                    
        if not accounts:
            print(f"❌ No valid accounts found in {pass_file}")
            print("Expected format: username:password")
            sys.exit(1)
            
        print(f"📋 Loaded {len(accounts)} accounts from {pass_file}")
        return accounts
        
    except FileNotFoundError:
        print(f"❌ Error: {pass_file} not found")
        print("Create a pass.txt file with format: username:password (one per line)")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading {pass_file}: {e}")
        sys.exit(1)

def load_streamers_from_file(filename):
    """Load streamers from file (checks streamers/ folder first)"""
    # Check if filename includes path, if not, look in streamers/ folder
    if not os.path.dirname(filename):
        streamer_file_path = os.path.join("streamers", filename)
    else:
        streamer_file_path = filename
        
    try:
        with open(streamer_file_path, "r", encoding="utf-8") as file:
            streamer_usernames = [line.strip() for line in file if line.strip()]
            
        if not streamer_usernames:
            print(f"⚠️  Warning: No streamers found in '{streamer_file_path}'")
            return []
            
        print(f"📺 Loaded {len(streamer_usernames)} streamers from '{streamer_file_path}'")
        return streamer_usernames
        
    except FileNotFoundError:
        print(f"❌ Error: The file '{streamer_file_path}' was not found.")
        print("Available streamer files:")
        streamers_dir = Path("streamers")
        if streamers_dir.exists():
            for file in streamers_dir.glob("*.txt"):
                print(f"  - {file.name}")
        else:
            for file in Path(".").glob("*.txt"):
                if file.name not in ["pass.txt", "requirements.txt"]:
                    print(f"  - {file.name}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading streamers file: {e}")
        sys.exit(1)

def enable_automated_login():
    """Enable automated login for multi-account"""
    login_file = "TwitchChannelPointsMiner/classes/TwitchLogin.py"
    try:
        with open(login_file, "r") as f:
            content = f.read()
        
        # Enable automated login
        if "# self.trigger_automated_login(user_code)  # DISABLED: Manual login required" in content:
            content = content.replace(
                "# self.trigger_automated_login(user_code)  # DISABLED: Manual login required",
                "self.trigger_automated_login(user_code)  # ENABLED for multi-account"
            )
            
            with open(login_file, "w") as f:
                f.write(content)
                
            print("🤖 Enabled automated login for multi-account mode")
            return True
        else:
            print("🤖 Automated login already enabled")
            return True
            
    except Exception as e:
        print(f"⚠️  Warning: Could not enable automated login: {e}")
        return False

def disable_automated_login():
    """Restore manual login mode"""
    login_file = "TwitchChannelPointsMiner/classes/TwitchLogin.py"
    try:
        with open(login_file, "r") as f:
            content = f.read()
        
        # Disable automated login
        if "self.trigger_automated_login(user_code)  # ENABLED for multi-account" in content:
            content = content.replace(
                "self.trigger_automated_login(user_code)  # ENABLED for multi-account",
                "# self.trigger_automated_login(user_code)  # DISABLED: Manual login required"
            )
            
            with open(login_file, "w") as f:
                f.write(content)
                
            print("👤 Restored manual login mode")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not restore manual login: {e}")

def create_account_workspace(username):
    """Create account-specific workspace"""
    workspace_dir = f"accounts/{username}"
    Path(workspace_dir).mkdir(parents=True, exist_ok=True)
    
    cookies_file = os.path.join(workspace_dir, "cookies.pkl")
    logs_dir = os.path.join(workspace_dir, "logs")
    Path(logs_dir).mkdir(exist_ok=True)
    
    return workspace_dir, cookies_file, logs_dir

def run_single_account(username, password, streamers, account_index):
    """Run mining for a single account"""
    print(f"\n🚀 [{username}] Starting account {account_index + 1}...")
    
    workspace_dir, cookies_file, logs_dir = create_account_workspace(username)
    analytics_port = 5000 + account_index
    
    # Create streamer settings
    streamer_settings = StreamerSettings(
        make_predictions=False,          # Disable betting for safety
        follow_raid=True,                # Follow raids for more points
        claim_drops=True,                # Claim drops automatically
        claim_moments=True,              # Claim moments when available
        watch_streak=True,               # Catch watch streaks
        community_goals=True,            # Contribute to community goals
        chat=ChatPresence.ONLINE,        # Join chat when streamer is online
        bet=BetSettings(
            strategy=Strategy.SMART,
            percentage=0,                # No betting for safety
            max_points=0
        )
    )
    
    # Create TwitchChannelPointsMiner instance
    twitch_miner = TwitchChannelPointsMiner(
        username=username,
        password=password,
        claim_drops_startup=True,
        priority=[Priority.DROPS, Priority.ORDER],
        enable_analytics=True,
        disable_ssl_cert_verification=False,
        disable_at_in_nickname=False,
        logger_settings=LoggerSettings(
            save=True,
            console_level=logging.INFO,
            console_username=True,
            auto_clear=True,
            time_zone="",
            file_level=logging.DEBUG,
            emoji=True,
            less=False,
            colored=True,
            color_palette=ColorPalette(
                STREAMER_online="GREEN",
                streamer_offline="red",
                BET_wiN=Fore.MAGENTA
            ),
            username=username  # Account-specific logging
        ),
        streamer_settings=streamer_settings
    )
    
    # Start analytics server
    try:
        twitch_miner.analytics(host="127.0.0.1", port=analytics_port, refresh=5, days_ago=7)
        print(f"📊 [{username}] Analytics: http://127.0.0.1:{analytics_port}")
    except Exception as e:
        print(f"⚠️  [{username}] Analytics failed on port {analytics_port}: {e}")
    
    # Convert streamers - use Streamer objects for first few, usernames for the rest
    streamer_objects = [
        Streamer(name) if i < 5 else name 
        for i, name in enumerate(streamers)
    ]
    
    print(f"🎯 [{username}] Watching {len(streamer_objects)} streamers...")
    
    # Start mining
    try:
        twitch_miner.mine(
            streamer_objects,
            followers=False,
            followers_order=FollowersOrder.ASC
        )
    except KeyboardInterrupt:
        print(f"\n⏹️  [{username}] Stopped by user")
        raise
    except Exception as e:
        print(f"❌ [{username}] Error: {e}")
        raise

def main():
    """Main function"""
    print("🎮 Multi-Account Twitch Channel Points Miner (Sequential)")
    print("=" * 60)
    
    # Get streamer file from user
    filename = input("Where would you like to pull the streamers from?: ")
    
    # Enable automated login
    enable_automated_login()
    
    try:
        # Load accounts and streamers
        accounts = load_accounts()
        streamers = load_streamers_from_file(filename)
        
        if not streamers:
            print("❌ No streamers to watch. Exiting.")
            return
        
        print(f"\n🎯 Will run {len(accounts)} accounts sequentially")
        print("📊 Analytics URLs:")
        for i, (username, _) in enumerate(accounts):
            port = 5000 + i
            print(f"  - {username}: http://127.0.0.1:{port}")
        
        print(f"\n⚠️  Note: Accounts will run one at a time to avoid threading issues")
        print("⏹️  Press Ctrl+C to stop the current account and move to next")
        
        # Run accounts sequentially
        for i, (username, password) in enumerate(accounts):
            try:
                run_single_account(username, password, streamers, i)
            except KeyboardInterrupt:
                choice = input(f"\n❓ Skip to next account? (y/N): ").lower()
                if choice.startswith('y'):
                    continue
                else:
                    print("🛑 Stopping all accounts...")
                    break
            except Exception as e:
                print(f"❌ Account {username} failed: {e}")
                choice = input(f"❓ Continue with next account? (Y/n): ").lower()
                if choice.startswith('n'):
                    break
                continue
        
        print("\n✅ All accounts completed!")
            
    finally:
        # Restore manual login mode
        disable_automated_login()

if __name__ == "__main__":
    main()