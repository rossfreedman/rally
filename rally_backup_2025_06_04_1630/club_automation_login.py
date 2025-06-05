import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import logging
from database import get_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('club_automation.log')
    ]
)

logger = logging.getLogger(__name__)

def get_club_automation_credentials(email):
    """Get Club Automation credentials from database"""
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT club_automation_password FROM users WHERE email = %s', (email,))
            result = cursor.fetchone()
            if not result or not result[0]:
                raise Exception(f"No Club Automation password found for user {email}")
            return email, result[0]

def login_to_tennaqua(email):
    """
    Login to Tennaqua court reservation system using Selenium
    """
    logger.debug("Starting login process...")
    
    # Get credentials from database
    try:
        email, password = get_club_automation_credentials(email)
    except Exception as e:
        logger.error(f"Error getting credentials: {str(e)}")
        return None
    
    # Initialize Chrome webdriver with options
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    
    try:
        logger.debug("Navigating to login page...")
        # Navigate directly to login page
        driver.get("https://tennaqua.clubautomation.com")
        
        # Wait for page to load
        time.sleep(3)  # Increased wait time
        
        logger.debug(f"Current URL: {driver.current_url}")
        logger.debug(f"Page title: {driver.title}")
        
        logger.debug("Looking for username field...")
        # Wait for username field and enter credentials
        username_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='login']"))
        )
        logger.debug("Found username field")
        username_field.send_keys(email)
        
        logger.debug("Looking for password field...")
        # Find and fill password field
        password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        logger.debug("Found password field")
        password_field.send_keys(password)
        
        logger.debug("Looking for login button...")
        # Click login button
        login_button = driver.find_element(By.ID, "loginButton")
        logger.debug("Found login button")
        login_button.click()
        
        logger.debug("Waiting for successful login...")
        # Wait for redirect to member profile page
        WebDriverWait(driver, 15).until(
            lambda d: "member" in d.current_url.lower()
        )
        
        logger.debug("Successfully logged in to Tennaqua")
        
        # Navigate to court reservation page
        logger.debug("Navigating to court reservation page...")
        driver.get("https://tennaqua.clubautomation.com/event/reserve-court")
        
        # Wait for the profile tabs to be visible
        logger.debug("Waiting for profile tabs to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "profileTabs"))
        )
        
        logger.debug("Successfully navigated to court reservation page")
        
        # Find and click the Paddle Tennis tab
        logger.debug("Attempting to find Paddle Tennis tab...")
        try:
            # Wait for the tab to be clickable
            paddle_tennis_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#tab_27.profileTabButton"))
            )
            logger.debug("Found Paddle Tennis tab")
            
            # First try clicking the tab directly
            paddle_tennis_tab.click()
            logger.debug("Clicked Paddle Tennis tab directly")
            
            # Wait for the Paddle Tennis content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#component_paddletennis_location_id"))
            )
            logger.debug("Paddle Tennis content loaded")
            
            # If the content didn't load, try the JavaScript approach
            if not driver.find_elements(By.CSS_SELECTOR, "#component_paddletennis_location_id"):
                logger.debug("Content not loaded, trying JavaScript approach...")
                driver.execute_script("""
                    function changeCourtsLocations(component_name, obj) {
                        showResources(null, 'https://tennaqua.clubautomation.com/'+component_name, 'court-service', function(){
                            if ($('courtsInfo')){
                                showCurrentResources();
                            }
                        }, '&change_service_ajax=1&date='+$('date').value);
                        $j('.location_div').hide();
                        $j('#component_'+component_name+'_location_id').show();
                        $j('#component_'+component_name+'_location_id').children().css({'width': 200});
                        showTab(obj);
                    }
                    changeCourtsLocations('paddletennis', arguments[0]);
                """, paddle_tennis_tab)
                logger.debug("Executed Paddle Tennis tab click via JavaScript")
                
                # Wait again for content to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#component_paddletennis_location_id"))
                )
                logger.debug("Paddle Tennis content loaded after JavaScript execution")
            
            # Wait for the page to load after clicking the tab
            time.sleep(3)
            
            # Verify we're on the Paddle Tennis page
            current_url = driver.current_url
            logger.debug(f"Current URL after clicking Paddle Tennis tab: {current_url}")
            
            # Take a screenshot for debugging
            driver.save_screenshot("paddle_tennis_page.png")
            logger.debug("Saved screenshot of the page")
            
        except Exception as e:
            logger.error(f"Error clicking Paddle Tennis tab: {str(e)}")
            logger.debug("Attempting alternative method to find the tab...")
            
            # Try alternative method - find by text content
            all_tabs = driver.find_elements(By.CLASS_NAME, "profileTabButton")
            for tab in all_tabs:
                if "Paddle Tennis" in tab.text:
                    logger.debug("Found Paddle Tennis tab by text content")
                    tab.click()
                    logger.debug("Clicked Paddle Tennis tab using alternative method")
                    time.sleep(3)
                    break
            
        return driver
        
    except Exception as e:
        logger.error(f"Error during process: {str(e)}")
        logger.error(f"Error type: {e.__class__.__name__}")
        logger.error(f"Error message: {str(e)}")
        if hasattr(e, 'stacktrace'):
            logger.error(f"Stacktrace: {e.stacktrace}")
        logger.error(f"Current URL: {driver.current_url}")
        logger.error(f"Page title: {driver.title}")
        driver.quit()
        return None

if __name__ == "__main__":
    logger.debug("Starting script...")
    # For testing, you would pass the email of the logged-in user
    # In production, this would be called with the current user's email
    driver = login_to_tennaqua("rossfreedman@gmail.com")
    if driver:
        logger.debug("Process successful, keeping browser open for 5 seconds...")
        time.sleep(5)  # Keep browser open briefly to verify
        driver.quit()
    else:
        logger.error("Process failed")
