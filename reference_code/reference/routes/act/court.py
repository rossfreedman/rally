from flask import jsonify, request, session
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from .auth import login_required

logger = logging.getLogger(__name__)

def get_chrome_options():
    """Configure Chrome options for headless operation"""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    return chrome_options

def wait_and_click(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    """Wait for an element to be clickable and click it"""
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    element.click()
    return element

def wait_for_element(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    """Wait for an element to be present"""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )

def safe_click(driver, element):
    """Safely click an element using JavaScript"""
    try:
        element.click()
    except:
        driver.execute_script("arguments[0].click();", element)

def find_element_by_multiple_selectors(driver, selectors):
    """Try multiple selectors to find an element"""
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            return element
        except:
            continue
    return None

def navigate_with_retry(driver, url, max_retries=3):
    """Navigate to a URL with retry logic"""
    for attempt in range(max_retries):
        try:
            driver.get(url)
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            continue
    return False

def init_routes(app):
    @app.route('/api/reserve-court', methods=['POST'])
    @login_required
    def reserve_court():
        try:
            data = request.get_json()
            
            # Extract reservation details
            username = data.get('username')
            password = data.get('password')
            date = data.get('date')
            time = data.get('time')
            court = data.get('court')
            
            if not all([username, password, date, time, court]):
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Initialize Chrome driver
            driver = webdriver.Chrome(options=get_chrome_options())
            
            try:
                # Navigate to reservation page
                navigate_with_retry(driver, "https://tennaquaclub.clubautomation.com")
                
                # Login
                username_field = wait_for_element(driver, "input#user")
                password_field = wait_for_element(driver, "input#pass")
                
                username_field.send_keys(username)
                password_field.send_keys(password)
                
                login_button = wait_for_element(driver, "button#login")
                safe_click(driver, login_button)
                
                # Navigate to court reservation
                wait_and_click(driver, "a[href*='court-times']")
                
                # Select date
                date_picker = wait_for_element(driver, "input.datepicker")
                driver.execute_script(f"arguments[0].value = '{date}'", date_picker)
                
                # Select time
                time_selector = wait_for_element(driver, f"select.time-select option[value='{time}']")
                safe_click(driver, time_selector)
                
                # Select court
                court_selector = wait_for_element(driver, f"div[data-court='{court}']")
                safe_click(driver, court_selector)
                
                # Confirm reservation
                confirm_button = wait_for_element(driver, "button.confirm-reservation")
                safe_click(driver, confirm_button)
                
                # Wait for confirmation
                success_message = wait_for_element(driver, "div.reservation-success", timeout=15)
                
                return jsonify({
                    'message': 'Court reserved successfully',
                    'details': {
                        'date': date,
                        'time': time,
                        'court': court
                    }
                })
                
            except Exception as e:
                logger.error(f"Court reservation error: {str(e)}")
                return jsonify({'error': 'Failed to reserve court'}), 500
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Court reservation error: {str(e)}")
            return jsonify({'error': 'Failed to reserve court'}), 500

    return app 