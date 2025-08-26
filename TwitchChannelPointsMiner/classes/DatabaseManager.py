# -*- coding: utf-8 -*-

import logging
import os
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