import logging
import platform
import json
import time
import os
import argparse
import sys
if platform.system() == "Windows":
    import msvcrt
else:
    import fcntl
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_logging(username):
    """Setup account-specific logging"""
    log_filename = f"login_{username}.log" if username else "login.log"
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s - {username} - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ],
        force=True  # Force reconfiguration
    )
    return logging.getLogger(__name__)

def get_account_config():
    """Get account configuration from command line arguments"""
    parser = argparse.ArgumentParser(description="Twitch TV Login Automation")
    parser.add_argument("--account-file", default="activation_code.txt", help="Account activation file")
    
    args = parser.parse_args()
    return args.account_file

def main():
    # Get account-specific configuration
    activation_file = get_account_config()
    
    # Initialize logger (will be reconfigured once we know the username)
    logger = logging.getLogger(__name__)
    
    # Read activation code with retries and locking
    activation_code = None
    username = None
    password = None
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with open(activation_file, "r") as f:
                if platform.system() == "Windows":
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1024)
                else:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                code_data = json.load(f)
                if platform.system() == "Windows":
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1024)
                else:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            code_username = code_data.get("username")
            activation_code = code_data.get("code")
            
            if not activation_code or not code_username:
                logger.error(f"Invalid data in {activation_file}: missing username or code")
                exit(1)
                
            username = code_username
            # Setup account-specific logging now that we know the username
            logger = setup_logging(username)
            logger.info(f"Read activation code for {username}: {activation_code}")
            break
            
        except FileNotFoundError:
            logger.warning(f"{activation_file} not found (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                logger.error("Max retries reached. Exiting.")
                exit(1)
            time.sleep(retry_delay)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse {activation_file}: invalid JSON")
            exit(1)
    
    # Read username and password from pass.txt to get the password
    try:
        with open("pass.txt", "r") as f:
            if platform.system() == "Windows":
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1024)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            lines = f.readlines()
            if platform.system() == "Windows":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1024)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
        # Find the matching username in pass.txt
        for line in lines:
            line = line.strip()
            if ":" in line:
                pass_username, pass_password = line.split(":", 1)
                if pass_username == username:
                    password = pass_password
                    break
                    
        if not password:
            logger.error(f"Password not found for username {username} in pass.txt")
            exit(1)
            
        logger.info(f"Found credentials for account: {username}")
        
    except FileNotFoundError:
        logger.error("pass.txt not found")
        exit(1)

    # Set up Selenium WebDriver for Chrome in headless mode
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-webgl")
    options.add_argument("--enable-unsafe-swiftshader")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--ignore-certificate-errors")
    # Add user data directory to avoid conflicts between multiple instances
    options.add_argument(f"--user-data-dir=/tmp/chrome_{username}")

    try:
        # Use explicit ChromeDriver path in Docker container
        chromedriver_path = os.getenv('CHROME_DRIVER', '/usr/local/bin/chromedriver')
        if os.path.exists(chromedriver_path):
            from selenium.webdriver.chrome.service import Service
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        logger.info(f"Initialized Chrome WebDriver in headless mode for {username}")
    except Exception as e:
        logger.error(f"Failed to initialize WebDriver for {username}: {e}")
        exit(1)

    # Retry logic for network issues
    max_retries_network = 5
    retry_delay_network = 5

    # Fix the try/except structure
    try:
        # Navigate to Twitch activate page with retries
        for attempt in range(max_retries_network):
            try:
                driver.get("https://www.twitch.tv/activate")
                logger.info("Navigated to https://www.twitch.tv/activate")
                logger.info("Initial page source:\n" + driver.page_source[:2000])
                break
            except Exception as e:
                logger.warning(f"Failed to navigate to Twitch (attempt {attempt + 1}/{max_retries_network}): {e}")
                if attempt == max_retries_network - 1:
                    logger.error("Max retries reached. Exiting.")
                    raise
                time.sleep(retry_delay_network)
    
    except Exception as e:
        logger.error(f"Failed to navigate to Twitch activate page: {e}")
        driver.quit()
        exit(1)

    # Main automation try block
    try:
        # Wait for the code input field
        code_input = None
        try:
            code_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Code']"))
            )
            logger.info("Found code input field by placeholder='Enter Code'")
        except TimeoutException:
            logger.warning("Could not find input by placeholder, trying alternative locators")
            try:
                code_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ScInputWrapper-sc-6obzdc-1')]//input"))
                )
                logger.info("Found code input field by class")
            except TimeoutException:
                logger.error("Failed to find code input field. Page source:\n" + driver.page_source[:2000])
                raise TimeoutException("Could not locate code input field")

        # Input the activation code
        if code_input:
            code_input.clear()
            code_input.send_keys(activation_code)
            logger.info("Entered activation code")
        else:
            logger.error("No code input field found")
            raise Exception("Code input field not located")

        # Submit the form
        try:
            submit_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Activate')]"))
            )
            logger.info("Found submit button by text='Activate'")
        except TimeoutException:
            logger.warning("Could not find submit button by text, trying alternative locators")
            try:
                submit_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'ScCoreButtonPrimary-sc-1v2hwhq-1')]"))
                )
                logger.info("Found submit button by class")
            except TimeoutException:
                logger.error("Failed to find submit button. Page source:\n" + driver.page_source[:2000])
                raise TimeoutException("Could not locate submit button")

        submit_button.click()
        logger.info("Submitted activation code")

        # Wait for login page after submitting code
        try:
            username_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "login-username"))
            )
            logger.info("Login page detected, entering credentials")

            # Input username
            username_input.send_keys(username)
            logger.info("Entered username")

            # Input password
            password_input = driver.find_element(By.ID, "password-input")
            password_input.send_keys(password)
            logger.info("Entered password")
        except NoSuchElementException:
            logger.error("Failed to find username or password input field. Page source:\n" + driver.page_source[:2000])
            raise

        # Click login button
        try:
            login_submit = driver.find_element(By.XPATH, "//button[contains(., 'Log In')]")
            login_submit.click()
            logger.info("Submitted login form")
        except NoSuchElementException:
            logger.warning("Could not find login button by text, trying alternative")
            login_submit = driver.find_element(By.XPATH, "//button[contains(@class, 'gzKWOA')]")
            login_submit.click()
            logger.info("Submitted login form via alternative button")

        # Wait for redirect after login
        WebDriverWait(driver, 15).until(
            EC.url_contains("twitch.tv")
        )
        logger.info("Login successful, activation completed")

        # Only delete account-specific activation file after successful activation
        if os.path.exists(activation_file):
            os.remove(activation_file)
            logger.info(f"Removed {activation_file} after successful activation")

    except Exception as e:
        logger.error(f"Error during browser automation for {username}: {e}")
        # Do not delete activation file on failure, so it can be retried

    finally:
        # Close the browser gracefully
        try:
            driver.quit()
            logger.info(f"Closed browser for {username}")
        except Exception as e:
            logger.warning(f"Error closing browser for {username}: {e}")
            # Force kill ChromeDriver process
            if platform.system() == "Linux":
                os.system(f"pkill -f 'chrome.*{username}'")
                logger.info(f"Force killed chrome processes for {username}")
            elif platform.system() == "Windows":
                os.system("taskkill /IM chromedriver.exe /F")
                logger.info("Force killed chromedriver process")

if __name__ == "__main__":
    main()