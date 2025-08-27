# -*- coding: utf-8 -*-

import logging
import os
import requests
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Suppress Supabase/httpx debug logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

class DatabaseManager:
    """
    Manages Twitch account database operations using Supabase.
    Handles fetching available accounts, moving them between tables,
    and tracking account status for automated mining.
    """
    
    def __init__(self):
        """Initialize Supabase client with environment variables."""
        load_dotenv()
        
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self.current_account = None
        self.current_campaign_id = None
        self.current_campaign_name = None
        self.expected_drops = 0
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK")
        
    def fetch_available_account(self) -> Optional[Dict[str, Any]]:
        """
        Fetch an available account from the twitch_accounts table.
        Prioritizes newest accounts (most recent created_at) that have tokens.
        Skip legacy accounts without tokens.
        
        Returns:
            Dict containing account details or None if no accounts available
        """
        try:
            # Fetch ALL accounts, then filter in Python to avoid Supabase client issues
            response = self.client.table("twitch_accounts_nodrops") \
                .select("*") \
                .eq("in_use", False) \
                .eq("is_valid", True) \
                .order("created_at", desc=True) \
                .execute()
            
            # Filter for accounts with both access_token and user_id
            if response.data:
                for account in response.data:
                    if account.get("access_token") and account.get("user_id"):
                        # Found a valid account with tokens
                        # Mark account as in_use immediately to prevent race conditions
                        self.client.table("twitch_accounts_nodrops") \
                            .update({"in_use": True, "last_used": datetime.now(timezone.utc).isoformat()}) \
                            .eq("id", account["id"]) \
                            .execute()
                        
                        self.current_account = account
                        logger.info(f"Fetched account: {account['username']} (ID: {account['id']}, Created: {account.get('created_at', 'unknown')})")
                        return account
                
                # No accounts with valid tokens found
                logger.warning("No accounts with access_token and user_id found. Legacy accounts without tokens are skipped.")
                return None
            else:
                logger.warning("No available accounts found in database")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching available account: {e}")
            return None
    
    def move_to_in_progress(self, account_id: int, drop_campaign: str = None) -> bool:
        """
        Move account to accounts_in_progress table to track active mining.
        
        Args:
            account_id: ID of the account to move
            drop_campaign: Optional campaign name being mined
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get process ID for tracking
            import os
            process_id = os.getpid()
            
            # Insert into in_progress table
            data = {
                "account_id": account_id,
                "username": self.current_account["username"],
                "access_token": self.current_account["access_token"],
                "user_id": self.current_account["user_id"],
                "started_at": datetime.now(timezone.utc).isoformat(),
                "process_id": process_id,
                "drop_campaign": drop_campaign
            }
            
            response = self.client.table("accounts_in_progress") \
                .insert(data) \
                .execute()
            
            if response.data:
                logger.info(f"Account {self.current_account['username']} moved to in_progress")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error moving account to in_progress: {e}")
            return False
    
    def release_account(self, account_id: int = None) -> bool:
        """
        Release account back to available pool.
        Called on graceful shutdown or when switching accounts.
        
        Args:
            account_id: ID of account to release (uses current if not specified)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if account_id is None and self.current_account:
                account_id = self.current_account["id"]
            
            if account_id is None:
                return False
            
            # Remove from in_progress table
            self.client.table("accounts_in_progress") \
                .delete() \
                .eq("account_id", account_id) \
                .execute()
            
            # Mark as not in use in main table
            self.client.table("twitch_accounts_nodrops") \
                .update({"in_use": False}) \
                .eq("id", account_id) \
                .execute()
            
            logger.info(f"Account {account_id} released back to available pool")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing account: {e}")
            return False
    
    def mark_invalid(self, account_id: int = None, reason: str = "Token expired") -> bool:
        """
        Mark account as invalid when authentication fails.
        
        Args:
            account_id: ID of account to mark invalid
            reason: Reason for marking invalid
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if account_id is None and self.current_account:
                account_id = self.current_account["id"]
            
            if account_id is None:
                return False
            
            # Remove from in_progress if present
            self.client.table("accounts_in_progress") \
                .delete() \
                .eq("account_id", account_id) \
                .execute()
            
            # Mark as invalid in main table
            self.client.table("twitch_accounts_nodrops") \
                .update({
                    "in_use": False,
                    "is_valid": False,
                    "invalid_reason": reason,
                    "invalidated_at": datetime.now(timezone.utc).isoformat()
                }) \
                .eq("id", account_id) \
                .execute()
            
            logger.warning(f"Account {account_id} marked as invalid: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking account as invalid: {e}")
            return False
    
    def cleanup_orphaned_accounts(self, max_hours: int = 24) -> int:
        """
        Clean up accounts that have been in_progress for too long.
        This handles cases where the process crashed without cleanup.
        
        Args:
            max_hours: Maximum hours an account can be in_progress
            
        Returns:
            Number of accounts cleaned up
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_hours)
            
            # Get orphaned accounts
            response = self.client.table("accounts_in_progress") \
                .select("account_id") \
                .lt("started_at", cutoff_time.isoformat()) \
                .execute()
            
            cleaned = 0
            if response.data:
                for record in response.data:
                    if self.release_account(record["account_id"]):
                        cleaned += 1
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} orphaned accounts")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned accounts: {e}")
            return 0
    
    def get_account_stats(self) -> Dict[str, int]:
        """
        Get statistics about account availability.
        
        Returns:
            Dict with counts of available, in_use, and invalid accounts
        """
        try:
            stats = {}
            
            # Count available accounts
            response = self.client.table("twitch_accounts_nodrops") \
                .select("id", count="exact") \
                .eq("in_use", False) \
                .eq("is_valid", True) \
                .execute()
            stats["available"] = response.count or 0
            
            # Count in-use accounts
            response = self.client.table("accounts_in_progress") \
                .select("id", count="exact") \
                .execute()
            stats["in_progress"] = response.count or 0
            
            # Count invalid accounts
            response = self.client.table("twitch_accounts_nodrops") \
                .select("id", count="exact") \
                .eq("is_valid", False) \
                .execute()
            stats["invalid"] = response.count or 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting account stats: {e}")
            return {"available": 0, "in_progress": 0, "invalid": 0}
    
    def update_drop_progress(self, drop_name: str, progress: int) -> bool:
        """
        Update the current drop mining progress for tracking.
        
        Args:
            drop_name: Name of the drop being mined
            progress: Current progress percentage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.current_account:
                return False
            
            self.client.table("accounts_in_progress") \
                .update({
                    "drop_campaign": drop_name,
                    "drop_progress": progress,
                    "last_update": datetime.now(timezone.utc).isoformat()
                }) \
                .eq("account_id", self.current_account["id"]) \
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating drop progress: {e}")
            return False
    
    # ==================== Campaign Management Methods ====================
    
    def get_campaigns(self, active_only: bool = True) -> list:
        """
        Get all available campaigns.
        
        Args:
            active_only: If True, only return active campaigns
            
        Returns:
            List of campaign dictionaries
        """
        try:
            query = self.client.table("campaigns").select("*")
            
            if active_only:
                query = query.eq("is_active", True)
            
            response = query.order("created_at", desc=True).execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error fetching campaigns: {e}")
            return []
    
    def get_campaign_by_name(self, campaign_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific campaign by name.
        
        Args:
            campaign_name: Name of the campaign
            
        Returns:
            Campaign dictionary or None
        """
        try:
            response = self.client.table("campaigns") \
                .select("*") \
                .eq("campaign_name", campaign_name) \
                .execute()
            
            # Handle no results or multiple results
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.error(f"Error fetching campaign {campaign_name}: {e}")
            return None
    
    def fetch_available_account_for_campaign(self, campaign_id: int, include_partial: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetch an available account that hasn't completed the specified campaign.
        Excludes sold accounts and prioritizes accounts that haven't started the campaign.
        
        Args:
            campaign_id: ID of the campaign to check
            include_partial: If True, include accounts with partial progress
            
        Returns:
            Dict containing account details or None if no accounts available
        """
        try:
            # First try to get fresh accounts (never started this campaign)
            response = self.client.table("twitch_accounts_nodrops") \
                .select("*") \
                .eq("in_use", False) \
                .eq("is_valid", True) \
                .eq("is_sold", False) \
                .eq("account_status", "available") \
                .order("created_at", desc=True) \
                .execute()
            
            if response.data:
                for account in response.data:
                    if not account.get("access_token") or not account.get("user_id"):
                        continue
                    
                    # Check if account has any progress on this campaign
                    progress_check = self.client.table("account_campaign_progress") \
                        .select("status") \
                        .eq("account_id", account["id"]) \
                        .eq("campaign_id", campaign_id) \
                        .execute()
                    
                    # If no progress or not completed, use this account
                    if not progress_check.data or \
                       (progress_check.data[0]["status"] != "completed" and 
                        (include_partial or progress_check.data[0]["status"] != "partial")):
                        
                        # Mark account as in_use
                        self.client.table("twitch_accounts_nodrops") \
                            .update({"in_use": True, "last_used": datetime.now(timezone.utc).isoformat()}) \
                            .eq("id", account["id"]) \
                            .execute()
                        
                        self.current_account = account
                        self.current_campaign_id = campaign_id
                        
                        status = "fresh" if not progress_check.data else progress_check.data[0]["status"]
                        logger.info(f"Fetched {status} account for campaign {campaign_id}: {account['username']}")
                        return account
            
            logger.warning(f"No available accounts for campaign {campaign_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching account for campaign: {e}")
            return None
    
    def send_discord_notification(self, title: str, description: str, color: int = 0x00ff00, fields: list = None):
        """
        Send a notification to Discord webhook.
        
        Args:
            title: Title of the embed
            description: Description text
            color: Embed color (hex)
            fields: List of field dictionaries
        """
        if not self.discord_webhook or self.discord_webhook == "https://discord.com/api/webhooks/your-webhook-url":
            return
        
        try:
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "Twitch Drop Miner"}
            }
            
            if fields:
                embed["fields"] = fields
            
            data = {"embeds": [embed]}
            
            response = requests.post(
                self.discord_webhook,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code not in (200, 204):
                logger.error(f"Discord webhook failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
    
    def move_to_in_progress_with_campaign(self, account_id: int, campaign_id: int, expected_drops: int = 0) -> bool:
        """
        Move account to in_progress table with campaign tracking.
        
        Args:
            account_id: ID of the account
            campaign_id: ID of the campaign being mined
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import os
            process_id = os.getpid()
            
            # Get campaign info
            campaign_response = self.client.table("campaigns") \
                .select("campaign_name") \
                .eq("id", campaign_id) \
                .single() \
                .execute()
            
            campaign_name = campaign_response.data["campaign_name"] if campaign_response.data else "Unknown Campaign"
            self.current_campaign_name = campaign_name
            self.expected_drops = expected_drops
            
            # Insert into in_progress table with campaign_id
            data = {
                "account_id": account_id,
                "username": self.current_account["username"],
                "access_token": self.current_account["access_token"],
                "user_id": self.current_account["user_id"],
                "started_at": datetime.now(timezone.utc).isoformat(),
                "process_id": process_id,
                "drop_campaign": campaign_name,
                "campaign_id": campaign_id
            }
            
            response = self.client.table("accounts_in_progress") \
                .insert(data) \
                .execute()
            
            # Update or insert campaign progress
            if response.data:
                progress_data = {
                    "account_id": account_id,
                    "campaign_id": campaign_id,
                    "status": "in_progress",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "last_progress_update": datetime.now(timezone.utc).isoformat()
                }
                
                # Upsert campaign progress
                self.client.table("account_campaign_progress") \
                    .upsert(progress_data) \
                    .execute()
                
                logger.info(f"Account {self.current_account['username']} moved to in_progress for campaign {campaign_name}")
                
                # Send Discord notification for mining start
                self.send_mining_start_notification()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error moving account to in_progress with campaign: {e}")
            return False
    
    def send_mining_start_notification(self):
        """Send Discord notification when mining starts."""
        if not self.current_account or not self.current_campaign_name:
            return
        
        # Get account's previous campaigns
        previous_campaigns = self.get_account_completed_campaigns(self.current_account['id'])
        
        fields = [
            {"name": "Account", "value": self.current_account['username'], "inline": True},
            {"name": "Campaign", "value": self.current_campaign_name, "inline": True},
            {"name": "Expected Drops", "value": str(self.expected_drops), "inline": True}
        ]
        
        if previous_campaigns:
            fields.append({
                "name": "Previous Campaigns",
                "value": ", ".join([f"{c['name']} ✓" for c in previous_campaigns[:3]]),
                "inline": False
            })
        
        self.send_discord_notification(
            title="🎮 Mining Started",
            description=f"Starting drop mining session",
            color=0x3498db,
            fields=fields
        )
    
    def get_account_completed_campaigns(self, account_id: int) -> list:
        """Get list of completed campaigns for an account."""
        try:
            response = self.client.table("account_campaign_progress") \
                .select("campaigns!inner(campaign_name)") \
                .eq("account_id", account_id) \
                .eq("status", "completed") \
                .execute()
            
            if response.data:
                return [{"name": item['campaigns']['campaign_name']} for item in response.data]
            return []
            
        except Exception as e:
            logger.error(f"Error getting completed campaigns: {e}")
            return []
    
    def update_campaign_progress(self, drops_claimed: int, total_drops: int = None) -> bool:
        """
        Update campaign progress for current account.
        
        Args:
            drops_claimed: Number of drops claimed so far
            total_drops: Total drops in campaign (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.current_account or not self.current_campaign_id:
                return False
            
            update_data = {
                "account_id": self.current_account["id"],
                "campaign_id": self.current_campaign_id,
                "drops_claimed": drops_claimed,
                "last_progress_update": datetime.now(timezone.utc).isoformat()
            }
            
            if total_drops is not None:
                update_data["total_drops"] = total_drops
            
            self.client.table("account_campaign_progress") \
                .upsert(update_data) \
                .execute()
            
            # Send Discord notification for drop progress
            if drops_claimed > 0:
                self.send_drop_progress_notification(drops_claimed, self.expected_drops)
            
            # Check if campaign is complete
            if self.expected_drops > 0 and drops_claimed >= self.expected_drops:
                self.mark_campaign_completed(drops_claimed=drops_claimed)
                self.send_campaign_complete_notification(drops_claimed)
                # Return special value to indicate completion
                return "COMPLETE"
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating campaign progress: {e}")
            return False
    
    def mark_campaign_completed(self, account_id: int = None, campaign_id: int = None, drops_claimed: int = 0) -> bool:
        """
        Mark a campaign as completed for an account.
        
        Args:
            account_id: ID of the account (uses current if None)
            campaign_id: ID of the campaign (uses current if None)
            drops_claimed: Number of drops claimed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if account_id is None and self.current_account:
                account_id = self.current_account["id"]
            if campaign_id is None:
                campaign_id = self.current_campaign_id
            
            if not account_id or not campaign_id:
                return False
            
            # Update campaign progress
            self.client.table("account_campaign_progress") \
                .upsert({
                    "account_id": account_id,
                    "campaign_id": campaign_id,
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "drops_claimed": drops_claimed,
                    "last_progress_update": datetime.now(timezone.utc).isoformat()
                }) \
                .execute()
            
            # Update last campaign on account
            self.client.table("twitch_accounts_nodrops") \
                .update({"last_campaign_id": campaign_id}) \
                .eq("id", account_id) \
                .execute()
            
            logger.info(f"Campaign {campaign_id} marked as completed for account {account_id} with {drops_claimed} drops")
            
            # Release the account back to pool
            self.release_account(account_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking campaign completed: {e}")
            return False
    
    def mark_account_sold(self, account_id: int, reason: str = None, notes: str = None) -> bool:
        """
        Mark an account as sold/given away - permanently unavailable.
        
        Args:
            account_id: ID of the account to mark as sold
            reason: Reason for disposal
            notes: Additional notes (who it was sold to, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update account status
            self.client.table("twitch_accounts_nodrops") \
                .update({
                    "account_status": "sold",
                    "is_sold": True,
                    "sold_at": datetime.now(timezone.utc).isoformat(),
                    "disposal_reason": reason,
                    "disposal_notes": notes,
                    "in_use": False
                }) \
                .eq("id", account_id) \
                .execute()
            
            # Remove from in_progress if present
            self.client.table("accounts_in_progress") \
                .delete() \
                .eq("account_id", account_id) \
                .execute()
            
            logger.info(f"Account {account_id} marked as sold")
            return True
            
        except Exception as e:
            logger.error(f"Error marking account as sold: {e}")
            return False
    
    def get_campaign_stats(self, campaign_id: int) -> Dict[str, int]:
        """
        Get statistics for a specific campaign.
        
        Args:
            campaign_id: ID of the campaign
            
        Returns:
            Dict with account counts by status
        """
        try:
            # Try to use the stored function first
            response = self.client.rpc(
                "get_campaign_stats",
                {"p_campaign_id": campaign_id}
            ).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            # Fallback to manual counting
            return self._manual_campaign_stats(campaign_id)
            
        except Exception as e:
            logger.error(f"Error getting campaign stats: {e}")
            return self._manual_campaign_stats(campaign_id)
    
    def _manual_campaign_stats(self, campaign_id: int) -> Dict[str, int]:
        """Manual fallback for campaign stats."""
        try:
            stats = {
                "total_accounts": 0,
                "completed": 0,
                "in_progress": 0,
                "partial": 0,
                "not_started": 0,
                "available": 0,
                "sold_with_campaign": 0
            }
            
            # Get all valid accounts
            accounts = self.client.table("twitch_accounts_nodrops") \
                .select("id, account_status, is_sold, is_valid, in_use") \
                .not_.is_("access_token", None) \
                .not_.is_("user_id", None) \
                .execute()
            
            if not accounts.data:
                return stats
            
            stats["total_accounts"] = len(accounts.data)
            
            # Get campaign progress for all accounts
            progress = self.client.table("account_campaign_progress") \
                .select("account_id, status") \
                .eq("campaign_id", campaign_id) \
                .execute()
            
            progress_map = {p["account_id"]: p["status"] for p in (progress.data or [])}
            
            for account in accounts.data:
                account_id = account["id"]
                status = progress_map.get(account_id, "not_started")
                
                # Count by status
                if status == "completed":
                    stats["completed"] += 1
                    if account.get("account_status") in ("sold", "given_away") or account.get("is_sold"):
                        stats["sold_with_campaign"] += 1
                elif status == "in_progress":
                    stats["in_progress"] += 1
                elif status == "partial":
                    stats["partial"] += 1
                else:
                    stats["not_started"] += 1
                
                # Count available
                if (status != "completed" and 
                    account.get("account_status") == "available" and
                    not account.get("is_sold") and 
                    account.get("is_valid") and 
                    not account.get("in_use")):
                    stats["available"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in manual campaign stats: {e}")
            return {
                "total_accounts": 0,
                "completed": 0,
                "in_progress": 0,
                "partial": 0,
                "not_started": 0,
                "available": 0,
                "sold_with_campaign": 0
            }
    
    def get_accounts_with_drops(self, exclude_sold: bool = True) -> list:
        """
        Get accounts that have completed at least one campaign.
        
        Args:
            exclude_sold: If True, exclude sold accounts
            
        Returns:
            List of accounts with their campaign completions
        """
        try:
            # First check if account_campaign_progress table exists
            try:
                test = self.client.table("account_campaign_progress").select("id").limit(1).execute()
            except:
                logger.warning("account_campaign_progress table doesn't exist yet")
                return []
            
            # Use a simpler query without foreign key joins
            response = self.client.table("account_campaign_progress") \
                .select("account_id, campaign_id, status, drops_claimed") \
                .eq("status", "completed") \
                .execute()
            
            if not response.data:
                return []
            
            # Get account details separately
            accounts_response = self.client.table("twitch_accounts_nodrops") \
                .select("id, username, is_sold, account_status") \
                .execute()
            
            if not accounts_response.data:
                return []
            
            # Get campaigns separately
            campaigns_response = self.client.table("campaigns") \
                .select("id, campaign_name") \
                .execute()
            
            campaign_map = {c["id"]: c["campaign_name"] for c in (campaigns_response.data or [])}
            account_map = {a["id"]: a for a in accounts_response.data}
            
            # Build result
            account_drops = {}
            for progress in response.data:
                account_id = progress["account_id"]
                if account_id not in account_map:
                    continue
                    
                account = account_map[account_id]
                if exclude_sold and (account.get("is_sold") or account.get("account_status") != "available"):
                    continue
                
                if account_id not in account_drops:
                    account_drops[account_id] = {
                        "id": account_id,
                        "username": account["username"],
                        "campaigns_completed": [],
                        "total_drops": 0,
                        "account_status": account.get("account_status", "available"),
                        "is_sold": account.get("is_sold", False)
                    }
                
                campaign_name = campaign_map.get(progress["campaign_id"], "Unknown")
                drops = progress.get("drops_claimed", 0)
                account_drops[account_id]["campaigns_completed"].append(f"{campaign_name} ({drops} drops)")
                account_drops[account_id]["total_drops"] += drops
            
            return sorted(list(account_drops.values()), key=lambda x: x["total_drops"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error fetching accounts with drops: {e}")
            return []
    
    def send_drop_progress_notification(self, drops_claimed: int, expected_drops: int):
        """Send Discord notification for drop progress."""
        if not self.current_account or not self.current_campaign_name:
            return
        
        percentage = (drops_claimed / expected_drops * 100) if expected_drops > 0 else 0
        
        fields = [
            {"name": "Account", "value": self.current_account['username'], "inline": True},
            {"name": "Campaign", "value": self.current_campaign_name, "inline": True},
            {"name": "Progress", "value": f"{drops_claimed}/{expected_drops} drops", "inline": True},
            {"name": "Status", "value": f"{percentage:.0f}% complete", "inline": True}
        ]
        
        self.send_discord_notification(
            title="🎁 Drop Claimed!",
            description=f"Progress update for {self.current_campaign_name}",
            color=0xf39c12,
            fields=fields
        )
    
    def send_campaign_complete_notification(self, drops_claimed: int):
        """Send Discord notification when campaign is completed."""
        if not self.current_account or not self.current_campaign_name:
            return
        
        # Get total account stats
        account_stats = self.get_account_total_stats(self.current_account['id'])
        
        fields = [
            {"name": "Account", "value": self.current_account['username'], "inline": True},
            {"name": "Campaign", "value": self.current_campaign_name, "inline": True},
            {"name": "Total Drops", "value": f"{drops_claimed}/{self.expected_drops}", "inline": True},
            {"name": "Account Stats", "value": f"{account_stats['campaigns']} campaigns, {account_stats['drops']} total drops", "inline": False},
            {"name": "Status", "value": "✅ Account released back to pool", "inline": False}
        ]
        
        self.send_discord_notification(
            title="✅ Campaign Completed!",
            description=f"Successfully completed {self.current_campaign_name}",
            color=0x2ecc71,
            fields=fields
        )
    
    def get_account_total_stats(self, account_id: int) -> dict:
        """Get total stats for an account."""
        try:
            response = self.client.table("account_campaign_progress") \
                .select("status, drops_claimed") \
                .eq("account_id", account_id) \
                .eq("status", "completed") \
                .execute()
            
            if response.data:
                campaigns = len(response.data)
                drops = sum(item.get('drops_claimed', 0) for item in response.data)
                return {"campaigns": campaigns, "drops": drops}
            
            return {"campaigns": 0, "drops": 0}
            
        except Exception as e:
            logger.error(f"Error getting account stats: {e}")
            return {"campaigns": 0, "drops": 0}