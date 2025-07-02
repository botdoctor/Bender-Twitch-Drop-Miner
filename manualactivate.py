import logging
import platform
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("activate.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prompt for the activation code
activation_code = input("Please enter the Twitch activation code: ").strip()
if not activation_code:
    logger.error("No activation code provided. Exiting.")
    exit(1)
logger.info(f"Using activation code: {activation_code}")

# Read username and password from pass.txt
try:
    with open("pass.txt", "r") as f:
        line = f.readline().strip()
        if ":" not in line:
            logger.error("pass.txt must contain username:password")
            exit(1)
        username, password = line.split(":", 1)
    logger.info(f"Will use account: {username}")
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

try:
    driver = webdriver.Chrome(options=options)
    logger.info("Initialized Chrome WebDriver in headless mode")
except Exception as e:
    logger.error(f"Failed to initialize WebDriver: {e}")
    exit(1)

# Retry logic for network issues
max_retries = 5
retry_delay = 5

try:
    # Navigate to Twitch activate page with retries
    for attempt in range(max_retries):
        try:
            driver.get("https://www.twitch.tv/activate")
            logger.info("Navigated to https://www.twitch.tv/activate")
            logger.info("Initial page source:\n" + driver.page_source[:2000])
            break
        except Exception as e:
            logger.warning(f"Failed to navigate to Twitch (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached. Exiting.")
                raise
            time.sleep(retry_delay)

    # Wait for the code input field
    code_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter Code']"))
    )
    logger.info("Found code input field by placeholder='Enter Code'")

    # Input the activation code
    code_input.clear()
    code_input.send_keys(activation_code)
    logger.info("Entered activation code")

    # Submit the form
    submit_button = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Activate')]"))
    )
    logger.info("Found submit button by text='Activate'")
    submit_button.click()
    logger.info("Submitted activation code")

    # Wait for login page after submitting code
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

    # Click login button
    login_submit = driver.find_element(By.XPATH, "//button[contains(., 'Log In')]")
    login_submit.click()
    logger.info("Submitted login form")

    # Wait for redirect after login
    WebDriverWait(driver, 15).until(
        EC.url_contains("twitch.tv")
    )
    logger.info("Login successful, activation completed")

except TimeoutException as e:
    logger.error(f"Timeout occurred: {e}. Page source:\n" + driver.page_source[:2000])
    raise
except NoSuchElementException as e:
    logger.error(f"Element not found: {e}. Page source:\n" + driver.page_source[:2000])
    raise
except Exception as e:
    logger.error(f"Error during browser automation: {e}")
    raise

finally:
    # Close the browser gracefully
    try:
        driver.quit()
        logger.info("Closed browser")
    except Exception as e:
        logger.warning(f"Error closing browser: {e}")
        # Force kill ChromeDriver process
        if platform.system() == "Linux":
            os.system("pkill chromedriver")
            logger.info("Force killed chromedriver process")
        elif platform.system() == "Windows":
            os.system("taskkill /IM chromedriver.exe /F")
            logger.info("Force killed chromedriver process")