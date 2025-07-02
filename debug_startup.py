#!/usr/bin/env python3
"""
Debug script to see why accounts are failing to start
"""

import subprocess
import sys
import os

def debug_main_script():
    """Run main.py with one account to see the actual error"""
    print("🔍 Debugging main.py startup...")
    
    # Test with the first account from pass.txt
    username = "treaclefamousn6g"
    
    cmd = [
        sys.executable, "main.py",
        "--username", username,
        "--streamers-file", "ruststreamers.txt", 
        "--analytics-port", "5000",
        "--workspace", f"accounts/{username}"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        # Run with real-time output to see what's happening
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10
        )
        
        print("STDOUT/STDERR:")
        print(result.stdout)
        print(f"\nReturn code: {result.returncode}")
        
        if result.returncode != 0:
            print("\n❌ main.py failed to start")
            print("This is why the multi-account manager can't start accounts")
        else:
            print("\n✅ main.py started successfully")
            
    except subprocess.TimeoutExpired:
        print("\n⏰ main.py started but timed out (this might be OK)")
        print("It probably started the mining process successfully")
    except Exception as e:
        print(f"\n💥 Error running main.py: {e}")

def check_dependencies():
    """Check if required files and dependencies exist"""
    print("\n📋 Checking dependencies...")
    
    # Check files
    required_files = ["main.py", "ruststreamers.txt", "pass.txt"]
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING!")
    
    # Check Python modules
    required_modules = ["colorama", "requests"]
    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} - NOT INSTALLED!")
    
    # Check TwitchChannelPointsMiner
    try:
        from TwitchChannelPointsMiner import TwitchChannelPointsMiner
        print(f"   ✅ TwitchChannelPointsMiner")
    except ImportError as e:
        print(f"   ❌ TwitchChannelPointsMiner - {e}")

def check_pass_file():
    """Check pass.txt format"""
    print("\n📄 Checking pass.txt...")
    try:
        with open("pass.txt", "r") as f:
            lines = f.readlines()
        
        print(f"   Found {len(lines)} lines")
        for i, line in enumerate(lines[:3]):  # Show first 3
            line = line.strip()
            if ":" in line:
                username = line.split(":")[0]
                print(f"   ✅ Line {i+1}: {username}")
            else:
                print(f"   ❌ Line {i+1}: Invalid format (missing ':')")
                
    except FileNotFoundError:
        print("   ❌ pass.txt not found!")

if __name__ == "__main__":
    check_dependencies()
    check_pass_file()
    debug_main_script()