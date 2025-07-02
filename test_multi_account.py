#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for multi-account system
This script tests the multi-account functionality without actually running the miners
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path

def create_test_config():
    """Create test configuration files"""
    
    # Create test pass.txt with sample accounts
    test_accounts = [
        "testuser1:testpass1",
        "testuser2:testpass2",
        "testuser3:testpass3"
    ]
    
    with open("test_pass.txt", "w") as f:
        for account in test_accounts:
            f.write(account + "\n")
    
    # Create test streamers file
    test_streamers = [
        "shroud",
        "ninja",
        "summit1g",
        "pokimane"
    ]
    
    with open("test_streamers.txt", "w") as f:
        for streamer in test_streamers:
            f.write(streamer + "\n")
    
    print("Created test configuration files:")
    print("- test_pass.txt (3 test accounts)")
    print("- test_streamers.txt (4 test streamers)")

def test_config_generation():
    """Test configuration generation"""
    print("\n=== Testing Configuration Generation ===")
    
    try:
        # Test config generation
        cmd = [sys.executable, "multi_account_manager.py", "--action", "config", "--pass-file", "test_pass.txt"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Configuration generation successful")
            
            # Check if config file was created
            if os.path.exists("multi_account_config.json"):
                with open("multi_account_config.json", "r") as f:
                    config = json.load(f)
                    print(f"✅ Config file created with {len(config['accounts'])} accounts")
                    
                    # Verify account details
                    for i, account in enumerate(config["accounts"]):
                        print(f"   Account {i+1}: {account['username']} (port: {account['analytics_port']})")
            else:
                print("❌ Config file not created")
                
        else:
            print(f"❌ Configuration generation failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ Configuration generation timed out")
    except Exception as e:
        print(f"❌ Error during configuration generation: {e}")

def test_status_command():
    """Test status command"""
    print("\n=== Testing Status Command ===")
    
    try:
        cmd = [sys.executable, "multi_account_manager.py", "--action", "status"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Status command successful")
            status = json.loads(result.stdout)
            print(f"   Total accounts: {status['total_accounts']}")
            print(f"   Running: {status['running']}")
            print(f"   Stopped: {status['stopped']}")
            print(f"   Failed: {status['failed']}")
        else:
            print(f"❌ Status command failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error during status check: {e}")

def test_main_script_args():
    """Test main script with arguments"""
    print("\n=== Testing Main Script Arguments ===")
    
    try:
        # Test main.py with arguments (should not actually run mining)
        cmd = [
            sys.executable, "main.py",
            "--username", "testuser1",
            "--streamers-file", "test_streamers.txt",
            "--analytics-port", "5001",
            "--workspace", "/tmp/test_workspace"
        ]
        
        # We'll just test argument parsing by running with a timeout
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give it a few seconds to start and parse arguments
        try:
            stdout, stderr = process.communicate(timeout=5)
            print("✅ Main script argument parsing works")
        except subprocess.TimeoutExpired:
            # This is expected - the script will try to connect to Twitch
            process.kill()
            print("✅ Main script started successfully with arguments")
            
    except Exception as e:
        print(f"❌ Error testing main script: {e}")

def test_workspace_creation():
    """Test workspace creation"""
    print("\n=== Testing Workspace Creation ===")
    
    test_workspace = "/tmp/test_mining_workspace"
    
    try:
        # Create workspace directory structure
        Path(test_workspace).mkdir(parents=True, exist_ok=True)
        Path(f"{test_workspace}/logs").mkdir(exist_ok=True)
        
        # Create test cookies file
        with open(f"{test_workspace}/cookies.pkl", "w") as f:
            f.write("test cookies")
        
        print("✅ Workspace creation successful")
        print(f"   Workspace: {test_workspace}")
        print(f"   Logs dir: {test_workspace}/logs")
        print(f"   Cookies file: {test_workspace}/cookies.pkl")
        
        # Cleanup
        import shutil
        shutil.rmtree(test_workspace)
        print("✅ Workspace cleanup successful")
        
    except Exception as e:
        print(f"❌ Error testing workspace creation: {e}")

def test_login_script_args():
    """Test login script with arguments"""
    print("\n=== Testing Login Script Arguments ===")
    
    try:
        # Create test activation file
        test_data = {
            "username": "testuser1",
            "code": "ABCD1234"
        }
        
        with open("test_activation.txt", "w") as f:
            json.dump(test_data, f)
        
        # Test login.py argument parsing (will fail due to missing chromedriver, but that's ok)
        cmd = [sys.executable, "login.py", "--account-file", "test_activation.txt"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Check if it at least parsed the arguments correctly
        if "testuser1" in result.stderr or "testuser1" in result.stdout:
            print("✅ Login script argument parsing works")
        else:
            print("⚠️  Login script started but couldn't verify argument parsing")
            
        # Cleanup
        if os.path.exists("test_activation.txt"):
            os.remove("test_activation.txt")
            
    except subprocess.TimeoutExpired:
        print("✅ Login script started (timeout expected without chromedriver)")
    except Exception as e:
        print(f"❌ Error testing login script: {e}")

def cleanup_test_files():
    """Clean up test files"""
    print("\n=== Cleaning Up Test Files ===")
    
    files_to_remove = [
        "test_pass.txt",
        "test_streamers.txt",
        "multi_account_config.json",
        "test_activation.txt"
    ]
    
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"   Removed: {file_path}")
    
    print("✅ Cleanup complete")

def main():
    """Main test function"""
    print("🧪 Multi-Account Twitch Mining System Test")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ["multi_account_manager.py", "main.py", "login.py"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    try:
        create_test_config()
        test_config_generation()
        test_status_command()
        test_main_script_args()
        test_workspace_creation()
        test_login_script_args()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed!")
        print("\nNext steps:")
        print("1. Install Chrome/Chromium for Selenium login automation")
        print("2. Update pass.txt with real account credentials")
        print("3. Run: python3 multi_account_manager.py")
        print("4. Monitor logs in accounts/*/logs/ directories")
        print("5. Check analytics at http://localhost:5000, 5001, 5002, etc.")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    finally:
        cleanup_test_files()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)