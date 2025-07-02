#!/usr/bin/env python3
"""
Multi-Account Twitch Channel Points Miner
Automatically logs in multiple accounts from pass.txt and mines drops
"""

import logging
import os
import sys
import threading
import time
from pathlib import Path
from colorama import Fore
from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Bet import Strategy, BetSettings, Condition, OutcomeKeys, FilterCondition, DelayMode
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings

class MultiAccountMiner:
    def __init__(self):
        self.miners = {}
        self.threads = {}
        self.base_port = 5000
        
    def load_accounts(self, pass_file="pass.txt"):
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
    
    def load_streamers_from_file(self, filename):
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
    
    def create_account_workspace(self, username):
        """Create account-specific workspace"""
        workspace_dir = f"accounts/{username}"
        Path(workspace_dir).mkdir(parents=True, exist_ok=True)
        
        cookies_file = os.path.join(workspace_dir, "cookies.pkl")
        logs_dir = os.path.join(workspace_dir, "logs")
        Path(logs_dir).mkdir(exist_ok=True)
        
        return workspace_dir, cookies_file, logs_dir
    
    def enable_automated_login(self):
        """Temporarily enable automated login for multi-account"""
        # Re-enable automated login in TwitchLogin.py
        login_file = "TwitchChannelPointsMiner/classes/TwitchLogin.py"
        try:
            with open(login_file, "r") as f:
                content = f.read()
            
            # Enable automated login
            content = content.replace(
                "# self.trigger_automated_login(user_code)  # DISABLED: Manual login required",
                "self.trigger_automated_login(user_code)  # ENABLED for multi-account"
            )
            
            with open(login_file, "w") as f:
                f.write(content)
                
            print("🤖 Enabled automated login for multi-account mode")
            return True
            
        except Exception as e:
            print(f"⚠️  Warning: Could not enable automated login: {e}")
            return False
    
    def disable_automated_login(self):
        """Restore manual login mode"""
        login_file = "TwitchChannelPointsMiner/classes/TwitchLogin.py"
        try:
            with open(login_file, "r") as f:
                content = f.read()
            
            # Disable automated login
            content = content.replace(
                "self.trigger_automated_login(user_code)  # ENABLED for multi-account",
                "# self.trigger_automated_login(user_code)  # DISABLED: Manual login required"
            )
            
            with open(login_file, "w") as f:
                f.write(content)
                
            print("👤 Restored manual login mode")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not restore manual login: {e}")
    
    def create_miner_for_account(self, username, password, streamers, account_index):
        """Create TwitchChannelPointsMiner instance for an account"""
        workspace_dir, cookies_file, logs_dir = self.create_account_workspace(username)
        analytics_port = self.base_port + account_index
        
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
        
        return twitch_miner
    
    def run_account(self, username, password, streamers, account_index):
        """Run mining for a single account"""
        import signal
        
        # Ignore signal handlers in threads (they only work in main thread)
        def signal_handler(signum, frame):
            pass
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except:
            pass  # Signal handling might not work in threads
            
        try:
            print(f"🚀 [{username}] Starting miner...")
            
            # Create miner instance
            miner = self.create_miner_for_account(username, password, streamers, account_index)
            self.miners[username] = miner
            
            # Convert streamers - use Streamer objects for first few, usernames for the rest
            streamer_objects = [
                Streamer(name) if i < 5 else name 
                for i, name in enumerate(streamers)
            ]
            
            # Start mining
            miner.mine(
                streamer_objects,
                followers=False,
                followers_order=FollowersOrder.ASC
            )
            
        except Exception as e:
            print(f"❌ [{username}] Error: {e}")
            import traceback
            traceback.print_exc()
    
    def start_all_accounts(self, accounts, streamers):
        """Start mining for all accounts in separate threads"""
        print(f"\n🎮 Starting multi-account miner for {len(accounts)} accounts")
        print(f"📺 Watching {len(streamers)} streamers per account")
        
        for i, (username, password) in enumerate(accounts):
            print(f"\n⚡ Initializing account {i+1}/{len(accounts)}: {username}")
            
            # Create and start thread for this account
            thread = threading.Thread(
                target=self.run_account,
                args=(username, password, streamers, i),
                daemon=True,
                name=f"Miner-{username}"
            )
            
            self.threads[username] = thread
            thread.start()
            
            # Small delay between account starts
            time.sleep(2)
        
        print(f"\n✅ All {len(accounts)} accounts started!")
        print("📊 Analytics URLs:")
        for i, (username, _) in enumerate(accounts):
            port = self.base_port + i
            print(f"  - {username}: http://127.0.0.1:{port}")
        
        print("\n⏹️  Press Ctrl+C to stop all miners")
    
    def stop_all_accounts(self):
        """Stop all mining threads"""
        print("\n⏹️  Stopping all miners...")
        
        for username, thread in self.threads.items():
            if thread.is_alive():
                print(f"🛑 [{username}] Stopping...")
        
        # Wait for threads to finish
        for username, thread in self.threads.items():
            if thread.is_alive():
                thread.join(timeout=5)
        
        print("👋 All miners stopped!")

def main():
    """Main function"""
    print("🎮 Multi-Account Twitch Channel Points Miner")
    print("=" * 50)
    
    # Get streamer file from user
    filename = input("Where would you like to pull the streamers from?: ")
    
    # Initialize multi-account miner
    multi_miner = MultiAccountMiner()
    
    # Enable automated login
    multi_miner.enable_automated_login()
    
    try:
        # Load accounts and streamers
        accounts = multi_miner.load_accounts()
        streamers = multi_miner.load_streamers_from_file(filename)
        
        if not streamers:
            print("❌ No streamers to watch. Exiting.")
            return
        
        # Start all accounts
        multi_miner.start_all_accounts(accounts, streamers)
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            multi_miner.stop_all_accounts()
            
    finally:
        # Restore manual login mode
        multi_miner.disable_automated_login()

if __name__ == "__main__":
    main()