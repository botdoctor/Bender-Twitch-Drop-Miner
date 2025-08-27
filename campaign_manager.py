#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Campaign Manager CLI Tool
Manages campaigns and account tracking for Twitch Drop Miner
"""

import sys
import os
from datetime import datetime
from colorama import Fore, init
from tabulate import tabulate
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from TwitchChannelPointsMiner.classes.DatabaseManager import DatabaseManager

# Initialize colorama for colored output
init(autoreset=True)

class CampaignManagerCLI:
    """CLI tool for managing campaigns and account tracking."""
    
    def __init__(self):
        load_dotenv()
        try:
            self.db = DatabaseManager()
        except ValueError as e:
            print(Fore.RED + f"Database configuration error: {e}")
            print(Fore.YELLOW + "Please ensure SUPABASE_URL and SUPABASE_KEY are set in .env file")
            sys.exit(1)
    
    def display_menu(self):
        """Display main menu."""
        print("\n" + "="*60)
        print(Fore.CYAN + "  Campaign Manager")
        print("="*60)
        print(Fore.GREEN + "  [1] View All Campaigns")
        print(Fore.GREEN + "  [2] View Campaign Details")
        print(Fore.GREEN + "  [3] Add New Campaign")
        print(Fore.YELLOW + "  [4] View Accounts with Drops")
        print(Fore.YELLOW + "  [5] Mark Accounts as Sold")
        print(Fore.YELLOW + "  [6] View Sold Accounts")
        print(Fore.CYAN + "  [7] Campaign Progress Report")
        print(Fore.CYAN + "  [8] Export Account Data")
        print(Fore.RED + "  [9] Exit")
        print("="*60)
    
    def view_campaigns(self):
        """View all campaigns."""
        campaigns = self.db.get_campaigns(active_only=False)
        
        if not campaigns:
            print(Fore.YELLOW + "\nNo campaigns found.")
            return
        
        headers = ["ID", "Campaign", "Game", "Streamer File", "Drops", "Active", "Created"]
        rows = []
        
        for c in campaigns:
            rows.append([
                c['id'],
                c['campaign_name'],
                c.get('game_name', 'N/A'),
                c.get('streamer_file', 'N/A'),
                c.get('total_drops', 0),
                "✓" if c.get('is_active') else "✗",
                c.get('created_at', 'N/A')[:10] if c.get('created_at') else 'N/A'
            ])
        
        print("\n" + Fore.CYAN + "All Campaigns:")
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    
    def view_campaign_details(self):
        """View detailed stats for a specific campaign."""
        self.view_campaigns()
        
        try:
            campaign_id = int(input(Fore.CYAN + "\nEnter Campaign ID: ").strip())
        except ValueError:
            print(Fore.RED + "Invalid campaign ID.")
            return
        
        # Get campaign info
        campaigns = self.db.get_campaigns(active_only=False)
        campaign = next((c for c in campaigns if c['id'] == campaign_id), None)
        
        if not campaign:
            print(Fore.RED + "Campaign not found.")
            return
        
        # Get stats
        stats = self.db.get_campaign_stats(campaign_id)
        
        print("\n" + "="*60)
        print(Fore.CYAN + f"  Campaign: {campaign['campaign_name']}")
        print("="*60)
        print(f"  Game: {campaign.get('game_name', 'N/A')}")
        print(f"  Streamer File: {campaign.get('streamer_file', 'N/A')}")
        print(f"  Total Drops: {campaign.get('total_drops', 0)}")
        print(f"  Active: {'Yes' if campaign.get('is_active') else 'No'}")
        print("\n" + Fore.YELLOW + "  Account Statistics:")
        print(f"    Total Accounts: {stats['total_accounts']}")
        print(f"    Available: {stats['available']}")
        print(f"    Completed: {stats['completed']}")
        print(f"    In Progress: {stats['in_progress']}")
        print(f"    Partial: {stats['partial']}")
        print(f"    Not Started: {stats['not_started']}")
        print(f"    Sold with Campaign: {stats['sold_with_campaign']}")
        print("="*60)
    
    def add_campaign(self):
        """Add a new campaign."""
        print("\n" + Fore.CYAN + "Add New Campaign")
        print("="*60)
        
        campaign_name = input(Fore.CYAN + "Campaign Name (e.g., 'Rust 41'): ").strip()
        game_name = input(Fore.CYAN + "Game Name (e.g., 'Rust'): ").strip()
        streamer_file = input(Fore.CYAN + "Streamer File (e.g., 'rust41.txt'): ").strip()
        
        try:
            total_drops = int(input(Fore.CYAN + "Total Drops (e.g., 5): ").strip())
        except ValueError:
            total_drops = 0
        
        # Check if file exists
        if streamer_file and not os.path.isfile(streamer_file):
            print(Fore.YELLOW + f"Warning: File '{streamer_file}' does not exist.")
        
        # Insert into database
        try:
            response = self.db.client.table("campaigns").insert({
                "campaign_name": campaign_name,
                "game_name": game_name,
                "streamer_file": streamer_file,
                "total_drops": total_drops,
                "is_active": True
            }).execute()
            
            if response.data:
                print(Fore.GREEN + f"\nCampaign '{campaign_name}' added successfully!")
            else:
                print(Fore.RED + "\nFailed to add campaign.")
        except Exception as e:
            print(Fore.RED + f"\nError adding campaign: {e}")
    
    def view_accounts_with_drops(self):
        """View accounts that have completed campaigns."""
        accounts = self.db.get_accounts_with_drops(exclude_sold=True)
        
        if not accounts:
            print(Fore.YELLOW + "\nNo accounts with completed campaigns found.")
            return
        
        print("\n" + Fore.CYAN + "Accounts with Completed Campaigns:")
        print("="*80)
        
        for idx, account in enumerate(accounts[:30], 1):
            print(Fore.GREEN + f"\n[{idx}] {account['username']}")
            print(Fore.WHITE + f"    Campaigns: {', '.join(account['campaigns_completed'])}")
            print(Fore.YELLOW + f"    Total Drops: {account['total_drops']}")
            print(Fore.CYAN + f"    Status: {account['account_status']}")
        
        if len(accounts) > 30:
            print(Fore.WHITE + f"\n... and {len(accounts) - 30} more accounts")
        
        print("="*80)
        return accounts
    
    def mark_accounts_sold(self):
        """Mark accounts as sold."""
        accounts = self.view_accounts_with_drops()
        
        if not accounts:
            return
        
        print(Fore.YELLOW + "\n" + "="*60)
        print(Fore.YELLOW + "  Mark Accounts as Sold")
        print("="*60)
        print(Fore.RED + "  WARNING: This action cannot be undone!")
        
        selection = input(Fore.CYAN + "\nEnter account numbers (e.g., 1,3,5) or 'cancel': ").strip()
        
        if selection.lower() == 'cancel':
            return
        
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            account_ids = [accounts[i]['id'] for i in indices if 0 <= i < len(accounts)]
        except (ValueError, IndexError):
            print(Fore.RED + "Invalid selection.")
            return
        
        if not account_ids:
            print(Fore.RED + "No valid accounts selected.")
            return
        
        # Confirmation
        print(Fore.YELLOW + f"\nAbout to mark {len(account_ids)} account(s) as sold.")
        confirm = input(Fore.RED + "Type 'CONFIRM' to proceed: ").strip()
        
        if confirm != 'CONFIRM':
            print(Fore.GREEN + "Operation cancelled.")
            return
        
        reason = input(Fore.CYAN + "Reason (optional): ").strip() or None
        notes = input(Fore.CYAN + "Notes (optional): ").strip() or None
        
        success_count = 0
        for account_id in account_ids:
            if self.db.mark_account_sold(account_id, reason, notes):
                success_count += 1
        
        print(Fore.GREEN + f"\nSuccessfully marked {success_count}/{len(account_ids)} accounts as sold.")
    
    def view_sold_accounts(self):
        """View sold accounts."""
        try:
            response = self.db.client.table("twitch_accounts_nodrops") \
                .select("id, username, sold_at, disposal_reason, disposal_notes") \
                .in_("account_status", ["sold", "given_away"]) \
                .order("sold_at", desc=True) \
                .execute()
            
            if not response.data:
                print(Fore.YELLOW + "\nNo sold accounts found.")
                return
            
            print("\n" + Fore.CYAN + "Sold/Given Away Accounts:")
            print("="*80)
            
            headers = ["Username", "Sold Date", "Reason", "Notes"]
            rows = []
            
            for acc in response.data:
                rows.append([
                    acc['username'],
                    acc['sold_at'][:10] if acc['sold_at'] else 'N/A',
                    acc.get('disposal_reason', 'N/A')[:30] if acc.get('disposal_reason') else 'N/A',
                    acc.get('disposal_notes', 'N/A')[:30] if acc.get('disposal_notes') else 'N/A'
                ])
            
            print(tabulate(rows, headers=headers, tablefmt="grid"))
            print(f"\nTotal: {len(response.data)} sold accounts")
            
        except Exception as e:
            print(Fore.RED + f"Error fetching sold accounts: {e}")
    
    def campaign_progress_report(self):
        """Generate a comprehensive campaign progress report."""
        campaigns = self.db.get_campaigns(active_only=True)
        
        if not campaigns:
            print(Fore.YELLOW + "\nNo active campaigns found.")
            return
        
        print("\n" + "="*80)
        print(Fore.CYAN + "  Campaign Progress Report")
        print("="*80)
        
        total_available = 0
        total_completed = 0
        total_drops = 0
        
        for campaign in campaigns:
            stats = self.db.get_campaign_stats(campaign['id'])
            
            print(Fore.GREEN + f"\n{campaign['campaign_name']} ({campaign['game_name']})")
            print("-" * 40)
            
            # Progress bar
            if stats['total_accounts'] > 0:
                completion_rate = (stats['completed'] / stats['total_accounts']) * 100
                progress = int(completion_rate / 2)
                bar = "█" * progress + "░" * (50 - progress)
                print(f"Progress: [{bar}] {completion_rate:.1f}%")
            
            print(f"Available: {stats['available']} | Completed: {stats['completed']} | In Progress: {stats['in_progress']}")
            
            if campaign.get('total_drops'):
                estimated_drops = stats['completed'] * campaign['total_drops']
                print(f"Estimated Drops Claimed: {estimated_drops}")
                total_drops += estimated_drops
            
            total_available += stats['available']
            total_completed += stats['completed']
        
        print("\n" + "="*80)
        print(Fore.CYAN + "  Summary")
        print("="*80)
        print(f"Total Available Accounts Across All Campaigns: {total_available}")
        print(f"Total Completed Campaigns: {total_completed}")
        print(f"Total Estimated Drops Claimed: {total_drops}")
    
    def export_account_data(self):
        """Export account and campaign data to CSV."""
        import csv
        
        filename = f"account_campaign_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            # Get all accounts with campaign progress
            response = self.db.client.table("twitch_accounts_nodrops") \
                .select("*, account_campaign_progress!left(campaign_id, status, drops_claimed, campaigns!inner(campaign_name))") \
                .execute()
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Username', 'Account Status', 'Is Sold', 'Campaign', 'Campaign Status', 'Drops Claimed'])
                
                for account in response.data:
                    username = account['username']
                    account_status = account.get('account_status', 'available')
                    is_sold = account.get('is_sold', False)
                    
                    # Write campaign progress
                    if account.get('account_campaign_progress'):
                        for progress in account['account_campaign_progress']:
                            campaign_name = progress.get('campaigns', {}).get('campaign_name', 'Unknown')
                            status = progress.get('status', 'N/A')
                            drops = progress.get('drops_claimed', 0)
                            writer.writerow([username, account_status, is_sold, campaign_name, status, drops])
                    else:
                        writer.writerow([username, account_status, is_sold, 'None', 'N/A', 0])
            
            print(Fore.GREEN + f"\nData exported successfully to: {filename}")
            
        except Exception as e:
            print(Fore.RED + f"Error exporting data: {e}")
    
    def run(self):
        """Main run loop."""
        while True:
            self.display_menu()
            choice = input(Fore.CYAN + "\nSelect option (1-9): ").strip()
            
            if choice == '1':
                self.view_campaigns()
            elif choice == '2':
                self.view_campaign_details()
            elif choice == '3':
                self.add_campaign()
            elif choice == '4':
                self.view_accounts_with_drops()
            elif choice == '5':
                self.mark_accounts_sold()
            elif choice == '6':
                self.view_sold_accounts()
            elif choice == '7':
                self.campaign_progress_report()
            elif choice == '8':
                self.export_account_data()
            elif choice == '9':
                print(Fore.GREEN + "\nGoodbye!")
                break
            else:
                print(Fore.RED + "\nInvalid choice. Please select 1-9.")
            
            if choice != '9':
                input(Fore.CYAN + "\nPress Enter to continue...")

if __name__ == "__main__":
    cli = CampaignManagerCLI()
    cli.run()