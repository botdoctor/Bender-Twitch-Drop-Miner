#!/usr/bin/env python3
"""
Test script to verify the automated login integration works
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add the TwitchChannelPointsMiner to path
sys.path.append(str(Path(__file__).parent))

from TwitchChannelPointsMiner.classes.TwitchLogin import TwitchLogin

def test_automated_login():
    """Test the automated login trigger functionality"""
    print("Testing automated login integration...")
    
    # Create a test TwitchLogin instance
    # We'll use the first username from pass.txt
    try:
        with open("pass.txt", "r") as f:
            line = f.readline().strip()
            if ":" in line:
                username = line.split(":", 1)[0]
            else:
                print("Error: pass.txt must contain username:password format")
                return False
    except FileNotFoundError:
        print("Error: pass.txt not found")
        return False
    
    print(f"Using test username: {username}")
    
    # Create TwitchLogin instance
    login = TwitchLogin(username, None)
    
    # Test the trigger_automated_login method with a dummy code
    test_code = "TESTCODE"
    print(f"Testing automated login trigger with code: {test_code}")
    
    # Call the method
    login.trigger_automated_login(test_code)
    
    # Check if activation_code.txt was created
    time.sleep(1)  # Give it a moment
    
    if os.path.exists("activation_code.txt"):
        with open("activation_code.txt", "r") as f:
            data = json.load(f)
            print(f"✓ activation_code.txt created successfully:")
            print(f"  Username: {data.get('username')}")
            print(f"  Code: {data.get('code')}")
            
            # Verify data
            if data.get('username') == username and data.get('code') == test_code:
                print("✓ Activation code data is correct")
                
                # Clean up
                os.remove("activation_code.txt")
                print("✓ Test cleanup completed")
                return True
            else:
                print("✗ Activation code data is incorrect")
                return False
    else:
        print("✗ activation_code.txt was not created")
        return False

def test_selenium_availability():
    """Test if Selenium and Chrome are available"""
    print("\nTesting Selenium availability...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        print("✓ Selenium imported successfully")
        
        # Test Chrome options (headless)
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        print("✓ Chrome options configured")
        
        # Note: We won't actually start Chrome here to avoid dependencies
        # Just verify the imports work
        return True
        
    except ImportError as e:
        print(f"✗ Selenium import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Twitch Miner Automation Test Suite")
    print("=" * 50)
    
    tests = [
        ("Selenium Availability", test_selenium_availability),
        ("Automated Login Integration", test_automated_login),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "PASS" if result else "FAIL"
            print(f"Result: {status}")
        except Exception as e:
            print(f"Result: ERROR - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! The automation integration is ready.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)