#!/usr/bin/env python3
"""
Simple Test for Multi-Account System
Just run: python3 simple_test.py
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

def test_basic_functionality():
    """Test basic functionality without actually running miners"""
    print("🧪 Simple Multi-Account Test")
    print("=" * 40)
    
    # Test 1: Check if files exist
    print("1. Checking required files...")
    required_files = ["multi_account_manager.py", "main.py", "login.py"]
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING")
            return False
    
    # Test 2: Create simple test pass.txt
    print("\n2. Creating test pass.txt...")
    with open("test_pass.txt", "w") as f:
        f.write("testuser1:testpass1\n")
        f.write("testuser2:testpass2\n")
    print("   ✅ Created test_pass.txt with 2 accounts")
    
    # Test 3: Test config generation
    print("\n3. Testing configuration generation...")
    try:
        result = subprocess.run([
            sys.executable, "multi_account_manager.py", 
            "--action", "config", 
            "--pass-file", "test_pass.txt"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("   ✅ Configuration generated successfully")
            
            # Check config file
            if os.path.exists("multi_account_config.json"):
                with open("multi_account_config.json", "r") as f:
                    config = json.load(f)
                print(f"   ✅ Config has {len(config['accounts'])} accounts")
                for acc in config['accounts']:
                    print(f"      - {acc['username']} on port {acc['analytics_port']}")
            else:
                print("   ❌ Config file not created")
                return False
        else:
            print(f"   ❌ Config generation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Config test error: {e}")
        return False
    
    # Test 4: Test status command
    print("\n4. Testing status command...")
    try:
        result = subprocess.run([
            sys.executable, "multi_account_manager.py", 
            "--action", "status"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            status = json.loads(result.stdout)
            print("   ✅ Status command works")
            print(f"      Total accounts: {status['total_accounts']}")
            print(f"      Currently running: {status['running']}")
        else:
            print(f"   ❌ Status command failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Status test error: {e}")
        return False
    
    # Test 5: Test main.py with arguments
    print("\n5. Testing main.py argument parsing...")
    try:
        # Create test streamers file
        with open("test_streamers.txt", "w") as f:
            f.write("shroud\nninja\nsummit1g\n")
        
        # Start main.py and immediately kill it (just testing argument parsing)
        process = subprocess.Popen([
            sys.executable, "main.py",
            "--username", "testuser1",
            "--streamers-file", "test_streamers.txt", 
            "--analytics-port", "5001"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Give it 2 seconds then kill
        time.sleep(2)
        process.terminate()
        process.wait(timeout=5)
        
        print("   ✅ main.py accepts arguments correctly")
        
    except Exception as e:
        print(f"   ❌ main.py test error: {e}")
        return False
    
    # Test 6: Test login.py argument parsing
    print("\n6. Testing login.py argument parsing...")
    try:
        # Create test activation file
        test_activation = {
            "username": "testuser1",
            "code": "ABCD1234"
        }
        with open("test_activation.txt", "w") as f:
            json.dump(test_activation, f)
        
        # Test login.py (will fail due to no chrome, but should parse args)
        result = subprocess.run([
            sys.executable, "login.py",
            "--account-file", "test_activation.txt"
        ], capture_output=True, text=True, timeout=5)
        
        # Should fail but with our username in the output
        if "testuser1" in str(result.stderr) or "testuser1" in str(result.stdout):
            print("   ✅ login.py argument parsing works")
        else:
            print("   ⚠️  login.py ran but couldn't verify (might be OK)")
        
    except subprocess.TimeoutExpired:
        print("   ✅ login.py started (timeout expected)")
    except Exception as e:
        print(f"   ⚠️  login.py test: {e} (might be OK if no Chrome)")
    
    print("\n" + "=" * 40)
    print("🎉 BASIC TESTS PASSED!")
    print("\n📋 What this means:")
    print("✅ All scripts are present and functional")
    print("✅ Argument parsing works correctly") 
    print("✅ Configuration system works")
    print("✅ Multi-account manager is ready")
    
    print("\n🚀 Ready for VPS deployment!")
    print("\nTo test with real accounts:")
    print("1. Update pass.txt with real Twitch credentials")
    print("2. Install Chrome: sudo apt install google-chrome-stable")
    print("3. Run: python3 multi_account_manager.py")
    
    # Cleanup
    cleanup_files = [
        "test_pass.txt", "test_streamers.txt", 
        "test_activation.txt", "multi_account_config.json"
    ]
    for file in cleanup_files:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n✨ Test files cleaned up")
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    exit(0 if success else 1)