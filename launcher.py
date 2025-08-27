#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
import signal
import json
from datetime import datetime, timezone
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

# Configure logging based on DEBUG environment variable
debug_mode = os.getenv("DEBUG", "false").lower() == "true"
log_level = logging.DEBUG if debug_mode else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Suppress noisy debug logs from various libraries unless in debug mode
if not debug_mode:
    # Suppress HTTP client logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
    
    # Suppress Supabase logs
    logging.getLogger("supabase").setLevel(logging.WARNING)
    logging.getLogger("gotrue").setLevel(logging.WARNING)
    logging.getLogger("storage3").setLevel(logging.WARNING)
    logging.getLogger("realtime").setLevel(logging.WARNING)
    logging.getLogger("postgrest").setLevel(logging.WARNING)
    
    # Suppress WebSocket logs
    logging.getLogger("websocket").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    
    # Suppress TwitchChannelPointsMiner debug logs
    logging.getLogger("TwitchChannelPointsMiner").setLevel(logging.INFO)
    logging.getLogger("TwitchChannelPointsMiner.classes").setLevel(logging.INFO)
    logging.getLogger("TwitchChannelPointsMiner.classes.DatabaseManager").setLevel(logging.INFO)

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
    
    def load_campaign_config(self):
        """Load campaign configuration from JSON file."""
        try:
            with open('campaigns.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(Fore.YELLOW + "  campaigns.json not found, creating default...")
            return {}
        except json.JSONDecodeError:
            print(Fore.RED + "  Error reading campaigns.json")
            return {}
    
    def detect_available_campaigns(self):
        """Auto-detect available campaigns from .txt files."""
        campaign_config = self.load_campaign_config()
        available_campaigns = []
        
        # Scan for .txt files that exist
        for filename, config in campaign_config.items():
            if os.path.isfile(filename):
                # Get or create campaign in database
                campaign = self.db_manager.get_campaign_by_name(config['name'])
                if not campaign:
                    # Auto-create campaign in database
                    try:
                        response = self.db_manager.client.table("campaigns").insert({
                            "campaign_name": config['name'],
                            "game_name": config['game'],
                            "streamer_file": filename,
                            "total_drops": config['drops'],
                            "is_active": True
                        }).execute()
                        if response.data:
                            campaign = response.data[0]
                    except:
                        pass
                
                if campaign:
                    available_campaigns.append({
                        'id': campaign['id'],
                        'campaign_name': config['name'],
                        'game_name': config['game'],
                        'streamer_file': filename,
                        'total_drops': config['drops'],
                        'expected_drops': config['drops']  # Track expected drops
                    })
        
        return available_campaigns
    
    def display_campaign_menu(self, campaigns):
        """Display campaign selection menu."""
        print("\n" + "="*50)
        print(Fore.CYAN + "  Available Campaigns (Auto-Detected)")
        print("="*50)
        print()
        
        if not campaigns:
            print(Fore.RED + "  No campaign files found!")
            print(Fore.YELLOW + "  Add .txt files and configure in campaigns.json")
            return
        
        for idx, campaign in enumerate(campaigns, 1):
            # Get stats for this campaign
            stats = self.db_manager.get_campaign_stats(campaign['id'])
            
            print(Fore.GREEN + f"  [{idx}] {campaign['campaign_name']} ({campaign['game_name']})")
            print(Fore.WHITE + f"      File: {campaign['streamer_file']}")
            print(Fore.YELLOW + f"      Expected drops: {campaign['expected_drops']}")
            print(Fore.CYAN + f"      Available: {stats['available']} | Completed: {stats['completed']}")
        
        print()
        print(Fore.YELLOW + f"  [A] Account Management")
        print(Fore.RED + f"  [B] Back to Main Menu")
        print()
        print("="*50)
    
    def select_campaign(self, campaigns):
        """Get user's campaign selection."""
        while True:
            self.display_campaign_menu(campaigns)
            
            if not campaigns:
                input(Fore.CYAN + "\n  Press Enter to return...")
                return None
            
            choice = input(Fore.CYAN + f"\n  Select option: ").strip().upper()
            
            if choice == 'B':
                return None
            elif choice == 'A':
                return "manage_accounts"
            else:
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(campaigns):
                        return campaigns[choice_num - 1]
                    else:
                        print(Fore.RED + f"\n  Invalid choice. Please select 1-{len(campaigns)}.")
                except ValueError:
                    print(Fore.RED + "\n  Invalid input.")
    
    def display_campaign_stats(self, campaign_id, campaign_name):
        """Display statistics for a specific campaign."""
        stats = self.db_manager.get_campaign_stats(campaign_id)
        
        print("\n" + "="*50)
        print(Fore.CYAN + f"  Campaign: {campaign_name}")
        print("="*50)
        print(Fore.WHITE + f"  Total Accounts: {stats['total_accounts']}")
        print(Fore.GREEN + f"  Available: {stats['available']}")
        print(Fore.YELLOW + f"  In Progress: {stats['in_progress']}")
        print(Fore.CYAN + f"  Partial: {stats['partial']}")
        print(Fore.GREEN + f"  Completed: {stats['completed']}")
        print(Fore.WHITE + f"  Not Started: {stats['not_started']}")
        if stats['sold_with_campaign'] > 0:
            print(Fore.RED + f"  Sold with this campaign: {stats['sold_with_campaign']}")
        print("="*50)
    
    def manage_accounts_menu(self):
        """Display account management menu."""
        accounts = self.db_manager.get_accounts_with_drops(exclude_sold=True)
        
        if not accounts:
            print(Fore.YELLOW + "\n  No accounts with completed campaigns found.")
            input(Fore.CYAN + "\n  Press Enter to continue...")
            return
        
        while True:
            print("\n" + "="*50)
            print(Fore.CYAN + "  Account Management")
            print("="*50)
            print()
            
            for idx, account in enumerate(accounts[:20], 1):  # Show first 20
                campaigns_str = ", ".join(account['campaigns_completed'])
                print(Fore.GREEN + f"  [{idx}] {account['username']}")
                print(Fore.WHITE + f"      Campaigns: {campaigns_str}")
                print(Fore.YELLOW + f"      Total drops: {account['total_drops']}")
            
            if len(accounts) > 20:
                print(Fore.WHITE + f"\n  ... and {len(accounts) - 20} more accounts")
            
            print()
            print(Fore.YELLOW + "  [M] Mark account(s) as sold")
            print(Fore.RED + "  [B] Back")
            print()
            print("="*50)
            
            choice = input(Fore.CYAN + "\n  Select option: ").strip().upper()
            
            if choice == 'B':
                break
            elif choice == 'M':
                self.mark_accounts_sold_menu(accounts)
            else:
                print(Fore.RED + "\n  Invalid choice.")
    
    def mark_accounts_sold_menu(self, accounts):
        """Menu for marking accounts as sold."""
        print("\n" + "="*50)
        print(Fore.YELLOW + "  Mark Accounts as Sold")
        print("="*50)
        print(Fore.RED + "  WARNING: This action cannot be undone!")
        print(Fore.WHITE + "  Enter account numbers separated by commas (e.g., 1,3,5)")
        print(Fore.WHITE + "  Or enter 'ALL' to mark all listed accounts as sold")
        print()
        
        selection = input(Fore.CYAN + "  Enter selection (or 'cancel'): ").strip()
        
        if selection.lower() == 'cancel':
            return
        
        account_ids = []
        if selection.upper() == 'ALL':
            account_ids = [acc['id'] for acc in accounts]
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                account_ids = [accounts[i]['id'] for i in indices if 0 <= i < len(accounts)]
            except (ValueError, IndexError):
                print(Fore.RED + "\n  Invalid selection.")
                return
        
        if not account_ids:
            print(Fore.RED + "\n  No valid accounts selected.")
            return
        
        # Confirmation
        print(Fore.YELLOW + f"\n  About to mark {len(account_ids)} account(s) as sold.")
        confirm = input(Fore.RED + "  Type 'CONFIRM' to proceed: ").strip()
        
        if confirm != 'CONFIRM':
            print(Fore.GREEN + "\n  Operation cancelled.")
            return
        
        # Get reason and notes
        reason = input(Fore.CYAN + "\n  Reason for disposal (optional): ").strip() or None
        notes = input(Fore.CYAN + "  Additional notes (optional): ").strip() or None
        
        # Mark accounts as sold
        success_count = 0
        for account_id in account_ids:
            if self.db_manager.mark_account_sold(account_id, reason, notes):
                success_count += 1
        
        print(Fore.GREEN + f"\n  Successfully marked {success_count}/{len(account_ids)} accounts as sold.")
        input(Fore.CYAN + "\n  Press Enter to continue...")
    
    def run_auto_mode(self):
        """Run the miner in automatic mode with database integration and campaign selection."""
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
        
        # Auto-detect available campaigns from files
        campaigns = self.detect_available_campaigns()
        if not campaigns:
            print(Fore.RED + "\n  No campaign files detected!")
            print(Fore.YELLOW + "  Please add .txt files and configure campaigns.json")
            sys.exit(1)
        
        # Campaign selection loop
        while True:
            selected = self.select_campaign(campaigns)
            
            if selected is None:
                print(Fore.RED + "\n  Returning to main menu...")
                return
            elif selected == "manage_accounts":
                self.manage_accounts_menu()
                continue
            else:
                campaign = selected
                break
        
        campaign_id = campaign['id']
        campaign_name = campaign['campaign_name']
        expected_drops = campaign.get('expected_drops', 0)
        
        # Store expected drops for later use
        self.expected_drops = expected_drops
        self.current_drops = 0
        
        # Display campaign statistics
        self.display_campaign_stats(campaign_id, campaign_name)
        
        print(Fore.YELLOW + f"\n  Target: {expected_drops} drops")
        print(Fore.CYAN + "  Will auto-complete and exit when target reached")
        
        # Check if accounts are available for this campaign
        stats = self.db_manager.get_campaign_stats(campaign_id)
        if stats['available'] == 0:
            print(Fore.RED + f"\n  No available accounts for {campaign_name}!")
            print(Fore.YELLOW + "  All accounts have either completed this campaign or are in use.")
            input(Fore.CYAN + "\n  Press Enter to continue...")
            return
        
        # Ask about partial accounts
        include_partial = False
        if stats['partial'] > 0:
            print(Fore.YELLOW + f"\n  Found {stats['partial']} accounts with partial progress.")
            choice = input(Fore.CYAN + "  Include partial progress accounts? (y/n): ").strip().lower()
            include_partial = choice == 'y'
        
        # Fetch an available account for this campaign
        account = self.db_manager.fetch_available_account_for_campaign(campaign_id, include_partial)
        if not account:
            print(Fore.RED + f"\n  Failed to fetch an available account for {campaign_name}.")
            sys.exit(1)
        
        self.current_account = account
        username = account['username']
        
        print(Fore.GREEN + f"\n  Selected account: {username}")
        
        # Get streamers list - use campaign's streamer file if available
        if campaign.get('streamer_file') and os.path.isfile(campaign['streamer_file']):
            print(Fore.GREEN + f"\n  Using campaign streamer file: {campaign['streamer_file']}")
            with open(campaign['streamer_file'], 'r') as f:
                streamers = [line.strip() for line in f if line.strip()]
        else:
            # Fallback to manual file selection
            streamers = self.get_streamers_file()
        
        # Create miner instance
        self.miner = self.create_miner_instance(username, auto_mode=True)
        
        # Pass database manager and expected drops to miner
        self.miner.db_manager = self.db_manager
        self.miner.twitch.db_manager = self.db_manager
        self.miner.twitch.twitch_miner = self.miner
        self.db_manager.expected_drops = expected_drops
        
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
        
        # Move account to in_progress table with campaign tracking
        if not self.db_manager.move_to_in_progress_with_campaign(account['id'], campaign_id, expected_drops):
            print(Fore.YELLOW + "  Warning: Failed to move account to in_progress table")
        
        print(Fore.GREEN + f"\n  Starting automatic mining for {username}...")
        print(Fore.CYAN + f"  Campaign: {campaign_name}")
        print(Fore.CYAN + f"  Streamers: {len(streamers)}")
        
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
                # Mark campaign as partial if interrupted
                self.db_manager.client.table("account_campaign_progress") \
                    .upsert({
                        "account_id": account['id'],
                        "campaign_id": campaign_id,
                        "status": "partial",
                        "last_progress_update": datetime.now(timezone.utc).isoformat()
                    }) \
                    .execute()
                self.db_manager.release_account(account['id'])
            raise
    
    def create_miner_instance(self, username, auto_mode=False):
        """Create a TwitchChannelPointsMiner instance with common settings."""
        # Get debug mode from environment
        debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        console_log_level = logging.DEBUG if debug_mode else logging.INFO
        file_log_level = logging.DEBUG if debug_mode else logging.INFO
        
        # Get Discord webhook from environment
        discord_webhook = os.getenv("DISCORD_WEBHOOK")
        
        # Configure Discord if webhook is provided
        discord_config = None
        if discord_webhook and discord_webhook != "https://discord.com/api/webhooks/your-webhook-url":
            # Only send drop-related events when not in debug mode
            if debug_mode:
                # In debug mode, send all events for testing
                events = [
                    Events.DROP_CLAIM,
                    Events.STREAMER_ONLINE,
                    Events.STREAMER_OFFLINE,
                    Events.DROP_STATUS
                ]
            else:
                # In production, only send drop-related events
                events = [
                    Events.DROP_CLAIM,
                    Events.DROP_STATUS
                ]
            
            discord_config = Discord(
                webhook_api=discord_webhook,
                events=events
            )
            print(Fore.GREEN + f"  Discord webhook configured (Debug: {debug_mode}, Events: {len(events)})")
        
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
                console_level=console_log_level,  # Use dynamic level
                console_username=True,
                auto_clear=True,
                file_level=file_log_level,  # Use dynamic level
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