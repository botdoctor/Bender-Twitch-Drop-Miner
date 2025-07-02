#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import logging
import subprocess
import multiprocessing
import signal
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("multi_account_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Account:
    username: str
    password: str
    streamers_file: str
    analytics_port: int
    process: Optional[subprocess.Popen] = None
    status: str = "stopped"  # stopped, starting, running, failed
    restart_count: int = 0
    last_restart: float = 0

class MultiAccountManager:
    def __init__(self, config_file: str = "multi_account_config.json"):
        self.config_file = config_file
        self.accounts: List[Account] = []
        self.running = False
        self.max_restarts = 3
        self.restart_delay = 60  # seconds
        self.base_analytics_port = 5000
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop_all_accounts()
        sys.exit(0)
        
    def load_accounts_from_pass_file(self, pass_file: str = "pass.txt") -> None:
        """Load accounts from pass.txt file"""
        try:
            with open(pass_file, 'r') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or ':' not in line:
                    continue
                    
                username, password = line.split(':', 1)
                # Create account-specific streamers file path
                streamers_file = f"ruststreamers.txt"  # Default for now
                analytics_port = self.base_analytics_port + i
                
                account = Account(
                    username=username,
                    password=password,
                    streamers_file=streamers_file,
                    analytics_port=analytics_port
                )
                self.accounts.append(account)
                
            logger.info(f"Loaded {len(self.accounts)} accounts from {pass_file}")
            
        except FileNotFoundError:
            logger.error(f"Pass file {pass_file} not found")
            raise
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")
            raise
            
    def save_config(self) -> None:
        """Save current configuration to JSON file"""
        config = {
            "accounts": [
                {
                    "username": acc.username,
                    "password": acc.password,
                    "streamers_file": acc.streamers_file,
                    "analytics_port": acc.analytics_port
                }
                for acc in self.accounts
            ],
            "settings": {
                "max_restarts": self.max_restarts,
                "restart_delay": self.restart_delay,
                "base_analytics_port": self.base_analytics_port
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
    def load_config(self) -> None:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            self.accounts = []
            for acc_data in config.get("accounts", []):
                account = Account(
                    username=acc_data["username"],
                    password=acc_data["password"],
                    streamers_file=acc_data["streamers_file"],
                    analytics_port=acc_data["analytics_port"]
                )
                self.accounts.append(account)
                
            settings = config.get("settings", {})
            self.max_restarts = settings.get("max_restarts", 3)
            self.restart_delay = settings.get("restart_delay", 60)
            self.base_analytics_port = settings.get("base_analytics_port", 5000)
            
            logger.info(f"Loaded configuration with {len(self.accounts)} accounts")
            
        except FileNotFoundError:
            logger.info(f"Config file {self.config_file} not found, will create new one")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            
    def create_account_workspace(self, account: Account) -> str:
        """Create isolated workspace for account"""
        workspace_dir = f"accounts/{account.username}"
        Path(workspace_dir).mkdir(parents=True, exist_ok=True)
        
        # Create account-specific files
        cookies_file = f"{workspace_dir}/cookies.pkl"
        logs_dir = f"{workspace_dir}/logs"
        Path(logs_dir).mkdir(exist_ok=True)
        
        return workspace_dir
        
    def start_account(self, account: Account) -> bool:
        """Start mining process for a single account"""
        if account.status == "running":
            logger.warning(f"Account {account.username} is already running")
            return True
            
        try:
            workspace_dir = self.create_account_workspace(account)
            
            # Prepare environment variables
            env = os.environ.copy()
            env['ACCOUNT_USERNAME'] = account.username
            env['ACCOUNT_PASSWORD'] = account.password
            env['STREAMERS_FILE'] = account.streamers_file
            env['ANALYTICS_PORT'] = str(account.analytics_port)
            env['WORKSPACE_DIR'] = workspace_dir
            
            # Start the mining process
            cmd = [
                sys.executable, "main.py",
                "--username", account.username,
                "--streamers-file", account.streamers_file,
                "--analytics-port", str(account.analytics_port),
                "--workspace", workspace_dir
            ]
            
            logger.info(f"Starting account {account.username} with command: {' '.join(cmd)}")
            
            account.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd(),
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            account.status = "starting"
            logger.info(f"Started process for account {account.username} (PID: {account.process.pid})")
            
            # Give it a moment to start
            time.sleep(2)
            
            # Check if process is still running
            if account.process.poll() is None:
                account.status = "running"
                return True
            else:
                account.status = "failed"
                logger.error(f"Account {account.username} failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Error starting account {account.username}: {e}")
            account.status = "failed"
            return False
            
    def stop_account(self, account: Account) -> None:
        """Stop mining process for a single account"""
        if account.process is None:
            return
            
        try:
            logger.info(f"Stopping account {account.username}")
            
            if os.name == 'nt':  # Windows
                account.process.terminate()
            else:  # Unix/Linux
                os.killpg(os.getpgid(account.process.pid), signal.SIGTERM)
                
            # Wait for graceful shutdown
            try:
                account.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing account {account.username}")
                if os.name == 'nt':
                    account.process.kill()
                else:
                    os.killpg(os.getpgid(account.process.pid), signal.SIGKILL)
                    
            account.process = None
            account.status = "stopped"
            logger.info(f"Stopped account {account.username}")
            
        except Exception as e:
            logger.error(f"Error stopping account {account.username}: {e}")
            
    def restart_account(self, account: Account) -> bool:
        """Restart a failed account with backoff"""
        current_time = time.time()
        
        # Check restart limits
        if account.restart_count >= self.max_restarts:
            logger.error(f"Account {account.username} exceeded max restarts ({self.max_restarts})")
            return False
            
        # Check restart delay
        if current_time - account.last_restart < self.restart_delay:
            logger.info(f"Account {account.username} restart delayed")
            return False
            
        logger.info(f"Restarting account {account.username} (attempt {account.restart_count + 1})")
        
        self.stop_account(account)
        time.sleep(5)  # Brief pause before restart
        
        if self.start_account(account):
            account.restart_count += 1
            account.last_restart = current_time
            return True
        else:
            account.restart_count += 1
            account.last_restart = current_time
            return False
            
    def monitor_accounts(self) -> None:
        """Monitor all accounts and restart failed ones"""
        for account in self.accounts:
            if account.status == "running" and account.process:
                # Check if process is still alive
                if account.process.poll() is not None:
                    logger.warning(f"Account {account.username} process died")
                    account.status = "failed"
                    
            if account.status == "failed":
                self.restart_account(account)
                
    def start_all_accounts(self) -> None:
        """Start all configured accounts"""
        logger.info(f"Starting all {len(self.accounts)} accounts")
        
        for account in self.accounts:
            if self.start_account(account):
                logger.info(f"Successfully started {account.username}")
                # Stagger the starts to avoid overwhelming the system
                time.sleep(10)
            else:
                logger.error(f"Failed to start {account.username}")
                
    def stop_all_accounts(self) -> None:
        """Stop all running accounts"""
        logger.info("Stopping all accounts")
        
        for account in self.accounts:
            if account.status == "running":
                self.stop_account(account)
                
    def get_status(self) -> Dict:
        """Get status of all accounts"""
        status = {
            "total_accounts": len(self.accounts),
            "running": sum(1 for acc in self.accounts if acc.status == "running"),
            "failed": sum(1 for acc in self.accounts if acc.status == "failed"),
            "stopped": sum(1 for acc in self.accounts if acc.status == "stopped"),
            "accounts": [
                {
                    "username": acc.username,
                    "status": acc.status,
                    "restart_count": acc.restart_count,
                    "analytics_port": acc.analytics_port,
                    "pid": acc.process.pid if acc.process else None
                }
                for acc in self.accounts
            ]
        }
        return status
        
    def run(self) -> None:
        """Main run loop"""
        logger.info("Starting Multi-Account Manager")
        self.running = True
        
        try:
            self.start_all_accounts()
            
            # Main monitoring loop
            while self.running:
                self.monitor_accounts()
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop_all_accounts()
            logger.info("Multi-Account Manager stopped")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Account Twitch Mining Manager")
    parser.add_argument("--config", default="multi_account_config.json", help="Configuration file")
    parser.add_argument("--pass-file", default="pass.txt", help="Password file")
    parser.add_argument("--action", choices=["start", "stop", "status", "config"], default="start", help="Action to perform")
    
    args = parser.parse_args()
    
    manager = MultiAccountManager(args.config)
    
    if args.action == "config":
        # Create initial configuration
        manager.load_accounts_from_pass_file(args.pass_file)
        manager.save_config()
        logger.info(f"Configuration saved to {args.config}")
        
    elif args.action == "status":
        manager.load_config()
        status = manager.get_status()
        print(json.dumps(status, indent=2))
        
    elif args.action == "stop":
        manager.load_config()
        manager.stop_all_accounts()
        
    else:  # start
        manager.load_config()
        if not manager.accounts:
            logger.info("No accounts configured, loading from pass file")
            manager.load_accounts_from_pass_file(args.pass_file)
            manager.save_config()
        manager.run()

if __name__ == "__main__":
    main()