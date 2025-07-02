#!/usr/bin/env python3
"""
Simple test to verify the integration changes are correct without dependencies
"""

import json
import os
import re
import sys

def test_dockerfile_changes():
    """Test that Dockerfile has Chrome and Selenium setup"""
    print("Testing Dockerfile changes...")
    
    with open("Dockerfile", "r") as f:
        content = f.read()
    
    checks = [
        ("Chrome dependencies", "google-chrome"),
        ("ChromeDriver download", "chromedriver"),
        ("Selenium support", "wget"),
        ("Chrome environment", "CHROME_BIN"),
        ("Entry point", "run.py")
    ]
    
    results = []
    for check_name, pattern in checks:
        if pattern in content:
            print(f"✓ {check_name}")
            results.append(True)
        else:
            print(f"✗ {check_name} - missing '{pattern}'")
            results.append(False)
    
    return all(results)

def test_requirements_changes():
    """Test that requirements.txt includes selenium"""
    print("\nTesting requirements.txt changes...")
    
    with open("requirements.txt", "r") as f:
        content = f.read()
    
    if "selenium" in content:
        print("✓ Selenium dependency added")
        return True
    else:
        print("✗ Selenium dependency missing")
        return False

def test_run_py_exists():
    """Test that run.py exists and has proper structure"""
    print("\nTesting run.py entry point...")
    
    if not os.path.exists("run.py"):
        print("✗ run.py file missing")
        return False
    
    with open("run.py", "r") as f:
        content = f.read()
    
    checks = [
        ("Environment variables", "os.getenv"),
        ("Username from pass.txt", "pass.txt"),
        ("TwitchChannelPointsMiner import", "TwitchChannelPointsMiner"),
        ("Streamers loading", "streamer_file")
    ]
    
    results = []
    for check_name, pattern in checks:
        if pattern in content:
            print(f"✓ {check_name}")
            results.append(True)
        else:
            print(f"✗ {check_name} - missing '{pattern}'")
            results.append(False)
    
    return all(results)

def test_twitch_login_changes():
    """Test that TwitchLogin.py has automation integration"""
    print("\nTesting TwitchLogin.py automation integration...")
    
    with open("TwitchChannelPointsMiner/classes/TwitchLogin.py", "r") as f:
        content = f.read()
    
    checks = [
        ("JSON import", "import json"),
        ("Subprocess import", "import subprocess"),
        ("Threading import", "import threading"),
        ("Automation trigger", "trigger_automated_login"),
        ("Activation code creation", "activation_code.txt"),
        ("Login script execution", "login.py")
    ]
    
    results = []
    for check_name, pattern in checks:
        if pattern in content:
            print(f"✓ {check_name}")
            results.append(True)
        else:
            print(f"✗ {check_name} - missing '{pattern}'")
            results.append(False)
    
    return all(results)

def test_login_py_structure():
    """Test that login.py has proper structure"""
    print("\nTesting login.py structure...")
    
    if not os.path.exists("login.py"):
        print("✗ login.py file missing")
        return False
    
    with open("login.py", "r") as f:
        content = f.read()
    
    checks = [
        ("Selenium import", "from selenium import webdriver"),
        ("Pass.txt reading", "pass.txt"),
        ("Activation code reading", "activation_code.txt"),
        ("Chrome options", "ChromeOptions"),
        ("Headless mode", "--headless"),
        ("Twitch activation", "twitch.tv/activate")
    ]
    
    results = []
    for check_name, pattern in checks:
        if pattern in content:
            print(f"✓ {check_name}")
            results.append(True)
        else:
            print(f"✗ {check_name} - missing '{pattern}'")
            results.append(False)
    
    return all(results)

def test_docker_compose_structure():
    """Test that docker-compose.yml has proper structure"""
    print("\nTesting docker-compose.yml structure...")
    
    if not os.path.exists("docker-compose.yml"):
        print("✗ docker-compose.yml file missing")
        return False
    
    with open("docker-compose.yml", "r") as f:
        content = f.read()
    
    checks = [
        ("Service definition", "twitch-miner:"),
        ("Volume mounts", "volumes:"),
        ("Environment variables", "environment:"),
        ("Security options", "seccomp:unconfined"),
        ("Capabilities", "SYS_ADMIN")
    ]
    
    results = []
    for check_name, pattern in checks:
        if pattern in content:
            print(f"✓ {check_name}")
            results.append(True)
        else:
            print(f"✗ {check_name} - missing '{pattern}'")
            results.append(False)
    
    return all(results)

def test_pass_txt_format():
    """Test that pass.txt has proper format"""
    print("\nTesting pass.txt format...")
    
    if not os.path.exists("pass.txt"):
        print("✗ pass.txt file missing")
        return False
    
    with open("pass.txt", "r") as f:
        lines = f.readlines()
    
    if not lines:
        print("✗ pass.txt is empty")
        return False
    
    # Test first line format
    first_line = lines[0].strip()
    if ":" in first_line:
        username, password = first_line.split(":", 1)
        if username and password:
            print(f"✓ Pass.txt format correct (found {len(lines)} accounts)")
            return True
    
    print("✗ Pass.txt format incorrect (should be username:password)")
    return False

def main():
    """Run all integration tests"""
    print("=" * 60)
    print("Twitch Miner Docker Integration Validation")
    print("=" * 60)
    
    tests = [
        ("Dockerfile Changes", test_dockerfile_changes),
        ("Requirements.txt Changes", test_requirements_changes),
        ("Run.py Entry Point", test_run_py_exists),
        ("TwitchLogin.py Integration", test_twitch_login_changes),
        ("Login.py Structure", test_login_py_structure),
        ("Docker Compose Setup", test_docker_compose_structure),
        ("Pass.txt Format", test_pass_txt_format),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Integration Test Results")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("The Docker automation setup is ready for testing.")
        print("\nNext steps:")
        print("1. Run: docker-compose up --build")
        print("2. Monitor logs for automated authentication")
        print("3. Check for successful Twitch login")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check the output above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)