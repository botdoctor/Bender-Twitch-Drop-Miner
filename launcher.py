#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
import signal
from colorama import Fore, init
from pathlib import Path

# Initialize colorama for colored output
init(autoreset=True)

from TwitchChannelPointsMiner import TwitchChannelPointsMiner
from TwitchChannelPointsMiner.logger import LoggerSettings, ColorPalette
from TwitchChannelPointsMiner.classes.Chat import ChatPresence
from TwitchChannelPointsMiner.classes.Settings import Priority, Events, FollowersOrder
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer, StreamerSettings
from TwitchChannelPointsMiner.classes.DatabaseManager import DatabaseManager
from TwitchChannelPointsMiner.classes.Discord import Discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomaticMinerLauncher:
    """Launcher for automatic Twitch miner with database integration."""
    
    def __init__(self):
        self.miner = None
        self.db_manager = None
        self.current_account = None
        self.mode = None
        
    def display_menu(self):
        """Display the mode selection menu."""
        print("\n" + "="*50)
        print(Fore.CYAN + "  Twitch Drop Miner - Account Mode Selection")
        print("="*50)
        print()
        print(Fore.GREEN + "  [1] Manual Mode")
        print(Fore.WHITE + "      - Choose account username manually")
        print(Fore.WHITE + "      - Activate manually if needed")
        print()
        print(Fore.YELLOW + "  [2] Auto Mode")
        print(Fore.WHITE + "      - Automatic account from database")
        print(Fore.WHITE + "      - Automatic token injection")
        print(Fore.WHITE + "      - Account status tracking")
        print()
        print(Fore.RED + "  [3] Exit")
        print()
        print("="*50)
        
    def get_mode_selection(self):
        """Get user's mode selection."""
        while True:
            self.display_menu()
            choice = input(Fore.CYAN + "\n  Select mode (1-3): ").strip()
            
            if choice == "1":
                return "manual"
            elif choice == "2":
                return "auto"
            elif choice == "3":
                print(Fore.RED + "\n  Exiting...")
                sys.exit(0)
            else:
                print(Fore.RED + "\n  Invalid choice. Please select 1, 2, or 3.")
    
    def get_streamers_file(self):
        """Prompt for streamers file."""
        while True:
            print()
            filename = input(Fore.CYAN + "  Enter streamer list file (e.g., streamers.txt): ").strip()
            
            if os.path.isfile(filename):
                try:
                    with open(filename, "r") as file:
                        streamer_usernames = [line.strip() for line in file if line.strip()]
                    
                    if streamer_usernames:
                        print(Fore.GREEN + f"  Loaded {len(streamer_usernames)} streamers from {filename}")
                        return streamer_usernames
                    else:
                        print(Fore.RED + f"  File {filename} is empty. Please provide a file with streamer names.")
                except Exception as e:
                    print(Fore.RED + f"  Error reading file: {e}")
            else:
                print(Fore.RED + f"  File '{filename}' not found. Please try again.")
    
    def run_manual_mode(self):
        """Run the miner in manual mode (existing behavior)."""
        print(Fore.GREEN + "\n  Running in Manual Mode")
        print("="*50)
        
        username = input(Fore.CYAN + "\n  Enter Twitch username: ").strip()
        
        if not username:
            print(Fore.RED + "  No username provided. Exiting...")
            sys.exit(1)
        
        streamers = self.get_streamers_file()
        
        # Create miner instance with manual settings
        self.miner = self.create_miner_instance(username)
        
        print(Fore.GREEN + f"\n  Starting manual mining for {username}...")
        print(Fore.YELLOW + "  You may need to activate your account manually if prompted.")
        
        # Convert streamer list to Streamer objects (first 5 get priority)
        streamer_objects = [
            Streamer(username) if i < 5 else username 
            for i, username in enumerate(streamers)
        ]
        
        # Start mining
        self.miner.mine(
            streamer_objects,
            followers=False,
            followers_order=FollowersOrder.ASC
        )
    
    def run_auto_mode(self):
        """Run the miner in automatic mode with database integration."""
        print(Fore.GREEN + "\n  Running in Auto Mode")
        print("="*50)
        
        # Initialize database manager
        try:
            self.db_manager = DatabaseManager()
        except ValueError as e:
            print(Fore.RED + f"\n  Database configuration error: {e}")
            print(Fore.YELLOW + "  Please ensure SUPABASE_URL and SUPABASE_KEY are set in .env file")
            sys.exit(1)
        
        # Clean up any orphaned accounts
        cleaned = self.db_manager.cleanup_orphaned_accounts(max_hours=24)
        if cleaned > 0:
            print(Fore.YELLOW + f"  Cleaned up {cleaned} orphaned accounts")
        
        # Get account statistics
        stats = self.db_manager.get_account_stats()
        print(Fore.CYAN + f"\n  Account Status:")
        print(f"    Available: {stats['available']}")
        print(f"    In Progress: {stats['in_progress']}")
        print(f"    Invalid: {stats['invalid']}")
        
        if stats['available'] == 0:
            print(Fore.RED + "\n  No available accounts in database!")
            print(Fore.YELLOW + "  Please create accounts first or release in-progress accounts.")
            sys.exit(1)
        
        # Fetch an available account
        account = self.db_manager.fetch_available_account()
        if not account:
            print(Fore.RED + "\n  Failed to fetch an available account.")
            sys.exit(1)
        
        self.current_account = account
        username = account['username']
        
        print(Fore.GREEN + f"\n  Selected account: {username}")
        
        # Get streamers list
        streamers = self.get_streamers_file()
        
        # Create miner instance
        self.miner = self.create_miner_instance(username, auto_mode=True)
        
        # Inject token directly
        print(Fore.YELLOW + f"  Injecting token for {username}...")
        
        cookies_path = os.path.join(Path().absolute(), "cookies")
        Path(cookies_path).mkdir(parents=True, exist_ok=True)
        cookies_file = os.path.join(cookies_path, f"{username}.pkl")
        
        # Inject the token
        success = self.miner.twitch.twitch_login.inject_token(
            access_token=account['access_token'],
            user_id=account['user_id'],
            cookies_file=cookies_file
        )
        
        if not success:
            print(Fore.RED + f"  Failed to inject token for {username}")
            self.db_manager.mark_invalid(account['id'], "Token injection failed")
            print(Fore.YELLOW + "  Account marked as invalid. Please try another account.")
            sys.exit(1)
        
        print(Fore.GREEN + "  Token injected successfully!")
        
        # Move account to in_progress table
        campaign_name = f"Mining {len(streamers)} streamers"
        if not self.db_manager.move_to_in_progress(account['id'], campaign_name):
            print(Fore.YELLOW + "  Warning: Failed to move account to in_progress table")
        
        print(Fore.GREEN + f"\n  Starting automatic mining for {username}...")
        
        # Convert streamer list to Streamer objects
        streamer_objects = [
            Streamer(username) if i < 5 else username 
            for i, username in enumerate(streamers)
        ]
        
        # Start mining
        try:
            # The cookie file was created by inject_token, so login() will load it
            # and use the existing token instead of starting device flow
            self.miner.mine(
                streamer_objects,
                followers=False,
                followers_order=FollowersOrder.ASC
            )
        except Exception as e:
            logger.error(f"Mining error: {e}")
            if "ERR_BADAUTH" in str(e) or "401" in str(e):
                self.db_manager.mark_invalid(account['id'], "Authentication failed during mining")
            else:
                self.db_manager.release_account(account['id'])
            raise
    
    def create_miner_instance(self, username, auto_mode=False):
        """Create a TwitchChannelPointsMiner instance with common settings."""
        # Get Discord webhook from environment or use default
        discord_webhook = os.getenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1305673224100642877/zLiaMVlkRGxoG5EjKcMw0Ktnx3gjhxTgSomrvQnP8uYVyJtGTRGEToDufvPK_AHtXVad")
        
        # Configure Discord if webhook is provided
        discord_config = None
        if discord_webhook and discord_webhook != "https://discord.com/api/webhooks/your-webhook-url":
            discord_config = Discord(
                webhook_api=discord_webhook,
                events=[
                    Events.DROP_CLAIM,
                    Events.STREAMER_ONLINE,
                    Events.STREAMER_OFFLINE,
                    Events.DROP_STATUS
                ]
            )
            print(Fore.GREEN + f"  Discord webhook configured")
        
        return TwitchChannelPointsMiner(
            username=username,
            password=None,  # Not used in auto mode
            claim_drops_startup=True,
            priority=[
                Priority.DROPS,
                Priority.ORDER
            ],
            enable_analytics=False,  # Can be enabled if needed
            disable_ssl_cert_verification=False,
            logger_settings=LoggerSettings(
                save=True,
                console_level=logging.INFO,
                console_username=True,
                auto_clear=True,
                file_level=logging.DEBUG,
                emoji=True,
                less=False,
                colored=True,
                color_palette=ColorPalette(
                    STREAMER_online="GREEN",
                    streamer_offline="red",
                    BET_wiN=Fore.MAGENTA
                ),
                discord=discord_config  # Add Discord config here
            ),
            streamer_settings=StreamerSettings(
                make_predictions=False,
                follow_raid=True,
                claim_drops=True,
                claim_moments=False,
                watch_streak=False,
                community_goals=False,
                chat=ChatPresence.ONLINE
            )
        )
    
    def cleanup(self):
        """Clean up resources on exit."""
        if self.db_manager and self.current_account:
            print(Fore.YELLOW + "\n  Cleaning up...")
            # Release account back to available pool
            self.db_manager.release_account(self.current_account['id'])
            print(Fore.GREEN + "  Account released back to pool")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(Fore.YELLOW + "\n  Shutdown signal received...")
        self.cleanup()
        if self.miner:
            self.miner.end(signum, frame)
        sys.exit(0)
    
    def run(self):
        """Main entry point for the launcher."""
        print(Fore.CYAN + "\n" + "="*50)
        print(Fore.CYAN + "     Twitch Drop Miner - Auto Launcher")
        print(Fore.CYAN + "="*50)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Get mode selection
            self.mode = self.get_mode_selection()
            
            # Run selected mode
            if self.mode == "manual":
                self.run_manual_mode()
            elif self.mode == "auto":
                self.run_auto_mode()
                
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n  Interrupted by user")
            self.cleanup()
        except Exception as e:
            print(Fore.RED + f"\n  Error: {e}")
            logger.exception("Unexpected error in launcher")
            self.cleanup()
            sys.exit(1)

if __name__ == "__main__":
    launcher = AutomaticMinerLauncher()
    launcher.run()