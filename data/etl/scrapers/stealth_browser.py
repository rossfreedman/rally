#!/usr/bin/env python3
"""
Stealth Browser Manager for Rally Tennis Scraper
Uses undetected-chromedriver with fingerprint evasion techniques to avoid bot detection.
Now supports IP rotation via Decodo residential proxies using Selenium Wire.
Enhanced with IP validation, request volume tracking, and intelligent throttling.
"""

import json
import logging
import os
import random
import tempfile
import time
import warnings
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="_distutils_hack")
warnings.filterwarnings("ignore", category=UserWarning, module="setuptools")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
# Try to import seleniumwire, but provide fallback if it fails
try:
    from seleniumwire import webdriver
    SELENIUM_WIRE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Selenium Wire not available: {e}")
    SELENIUM_WIRE_AVAILABLE = False
    webdriver = None
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

# Import the new proxy manager
from proxy_manager import get_proxy_rotator

# Global proxy rotator instance
_proxy_rotator = None

def get_proxy_rotator_instance():
    """Get proxy rotator instance for stealth browser."""
    global _proxy_rotator
    if _proxy_rotator is None:
        _proxy_rotator = get_proxy_rotator()
    return _proxy_rotator


def get_decodo_credentials(session_id=None):
    """
    Get Decodo proxy credentials with intelligent rotation.
    
    Args:
        session_id (str, optional): Session ID to append to username for rotation
        
    Returns:
        dict: Decodo credentials with username, password, host, port
    """
    user = os.getenv("DECODO_USER", "sp2lv5ti3g")
    password = os.getenv("DECODO_PASS", "zU0Pdl~7rcGqgxuM69")
    if session_id:
        user = f"{user}-session-{session_id}"
    
    # Get current proxy from rotator
    rotator = get_proxy_rotator_instance()
    proxy_url = rotator.get_proxy()
    
    # Extract host and port from proxy URL
    # Format: http://user:pass@host:port
    proxy_parts = proxy_url.replace("http://", "").split("@")[1]
    host, port = proxy_parts.split(":")
    
    return {
        "username": user,
        "password": password,
        "host": host,
        "port": port
    }


def get_decodo_proxy_url(session_id=None):
    """
    Get Decodo proxy URL for HTTP/HTTPS requests.
    
    Args:
        session_id (str, optional): Session ID for username rotation
        
    Returns:
        str: Proxy URL in format http://username:password@host:port
    """
    creds = get_decodo_credentials(session_id)
    return f"http://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}"


def make_decodo_request(url, session_id=None, timeout=30):
    """
    Make a request through Decodo residential proxy.
    
    Args:
        url (str): Target URL to request
        session_id (str, optional): Session ID for proxy rotation
        timeout (int): Request timeout in seconds
        
    Returns:
        requests.Response: Response object
        
    Raises:
        requests.exceptions.RequestException: If request fails
    """
    proxy = get_decodo_proxy_url(session_id)
    proxies = {
        "http": proxy,
        "https": proxy
    }
    
    logger.info(f"🌐 Decodo Request: {url}")
    response = requests.get(url, proxies=proxies, timeout=timeout)
    response.raise_for_status()
    logger.info("✅ Decodo request successful")
    return response


def validate_decodo_us_response(session_id=None):
    """
    Validate that Decodo is returning a US-based IP.
    Calls ip.decodo.com/json through Decodo proxy and checks the result.
    
    Args:
        session_id (str, optional): Session ID for proxy rotation
        
    Returns:
        bool: True if IP is US-based, False otherwise
    """
    try:
        logger.info("🧪 Validating Decodo US IP...")
        
        # Make request through Decodo proxy to check IP
        for attempt in range(3):
            try:
                logger.info(f"🔄 Decodo validation attempt {attempt + 1}/3...")
                response = make_decodo_request("https://ip.decodo.com/json", session_id, timeout=60)
                if response.status_code == 200:
                    break
                else:
                    logger.warning(f"⚠️ Decodo validation attempt {attempt + 1} failed: {response.status_code}")
                    if attempt < 2:
                        time.sleep(5)  # Wait before retry
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️ Decodo validation attempt {attempt + 1} timed out")
                if attempt < 2:
                    time.sleep(5)  # Wait before retry
                continue
            except Exception as e:
                logger.warning(f"⚠️ Decodo validation attempt {attempt + 1} failed: {str(e)}")
                if attempt < 2:
                    time.sleep(5)  # Wait before retry
                continue
        else:
            logger.error("❌ All Decodo validation attempts failed")
            return False
        
        # Parse response
        try:
            ip_data = response.json()
        except json.JSONDecodeError:
            logger.error("❌ Invalid JSON response from Decodo")
            return False
        
        # Extract IP and country information
        ip_address = ip_data.get("ip")
        country_data = ip_data.get("country", {})
        
        if not ip_address:
            logger.error("❌ Could not extract IP from Decodo response")
            return False
        
        # Check if country is US
        country_code = country_data.get("code", "") if isinstance(country_data, dict) else str(country_data)
        logger.info(f"🌍 Decodo IP: {ip_address} (Country: {country_code})")
        
        # Check if IP is US-based
        if country_code.upper() == "US":
            logger.info("✅ Decodo validation successful: US-based IP confirmed")
            return True
        else:
            logger.error(f"❌ Decodo returned non-US IP: {ip_address} (Country: {country_code})")
            return False
            
    except Exception as e:
        logger.error(f"❌ Decodo validation failed: {str(e)}")
        return False


def apply_decodo_proxy_to_chrome(options):
    """
    Apply Decodo proxy settings to Chrome options.
    
    Args:
        options: Chrome options object to modify
    """
    # Get the full proxy URL with credentials
    proxy_url = get_decodo_proxy_url()
    
    # Extract credentials and host from the URL
    # Format: http://username:password@host:port
    if '@' in proxy_url:
        # Remove http:// prefix and extract the proxy server part
        proxy_server = proxy_url.replace("http://", "")
        options.add_argument(f'--proxy-server={proxy_server}')
        logger.info(f"🌐 Applied Decodo proxy to Chrome: {proxy_server}")
    else:
        logger.error("❌ Invalid Decodo proxy URL format")


def configure_seleniumwire_options():
    """
    Configure Selenium Wire options for Decodo proxy integration.
    
    Returns:
        dict: Selenium Wire options dictionary
    """
    creds = get_decodo_credentials()
    
    seleniumwire_options = {
        'proxy': {
            'http': f'http://{creds["username"]}:{creds["password"]}@{creds["host"]}:{creds["port"]}',
            'https': f'http://{creds["username"]}:{creds["password"]}@{creds["host"]}:{creds["port"]}'
        },
        'verify_ssl': False,  # Disable SSL verification for proxy
        'connection_timeout': 30,
        'suppress_connection_errors': False
    }
    
    logger.info("🌐 Configured Selenium Wire with Decodo proxy")
    return seleniumwire_options


def configure_chrome_options(headless=True, user_agent=None):
    """
    Configure Chrome options for stealth browsing.
    
    Args:
        headless (bool): Whether to run browser in headless mode
        user_agent (str): Custom user agent string
        
    Returns:
        uc.ChromeOptions: Configured Chrome options
    """
    options = uc.ChromeOptions()

    # Essential options for headless mode and containerized environments
    if headless:
        options.add_argument("--headless=new")  # Use new headless mode

    # Basic stealth options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")  # Faster loading

    # Remove automation flags
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Random window size for fingerprint diversity
    sizes = [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1600, 900),
        (1280, 720),
    ]
    width, height = random.choice(sizes)
    options.add_argument(f"--window-size={width},{height}")

    # Additional stealth options
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--no-first-run")
    options.add_argument("--safebrowsing-disable-auto-update")
    options.add_argument("--password-store=basic")
    options.add_argument("--use-mock-keychain")

    # Memory optimizations
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=2048")

    # Set user agent
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")
    else:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        options.add_argument(f"--user-agent={random.choice(user_agents)}")

    # Create temporary directories for cache and user data
    cache_dir = tempfile.mkdtemp(prefix="chrome-cache-")
    user_data_dir = tempfile.mkdtemp(prefix="chrome-user-data-")

    options.add_argument(f"--disk-cache-dir={cache_dir}")
    options.add_argument(f"--user-data-dir={user_data_dir}")

    # Set environment variables
    os.environ.setdefault("HOME", tempfile.gettempdir())
    os.environ.setdefault(
        "XDG_CACHE_HOME", os.path.join(tempfile.gettempdir(), ".cache")
    )
    os.environ.setdefault(
        "XDG_CONFIG_HOME", os.path.join(tempfile.gettempdir(), ".config")
    )

    return options


class StealthBrowserManager:
    """
    Context manager for handling undetected Chrome WebDriver sessions with fingerprint evasion.
    Implements various techniques to avoid bot detection on TennisScores.com and similar sites.
    Now supports IP rotation via Decodo residential proxies using Selenium Wire.
    """

    def __init__(self, headless=True, max_retries=3, user_agent_override=None):
        """
        Initialize the Stealth Browser Manager.

        Args:
            headless (bool): Whether to run browser in headless mode (default: True)
            max_retries (int): Maximum number of retries for creating a new driver (default: 3)
            user_agent_override (str): Custom user agent string (optional)
        """
        self.driver = None
        self.headless = headless
        self.max_retries = max_retries
        self.user_agent_override = user_agent_override

        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _inject_stealth_scripts(self, driver):
        """
        Inject JavaScript to spoof browser fingerprints and evade detection.

        Args:
            driver: Chrome WebDriver instance
        """
        try:
            # Spoof navigator.webdriver
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Spoof navigator.plugins
            driver.execute_script(
                """
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "", enabledPlugin: Plugin},
                            description: "",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        },
                        {
                            0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable", enabledPlugin: Plugin},
                            1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable", enabledPlugin: Plugin},
                            description: "",
                            filename: "internal-nacl-plugin",
                            length: 2,
                            name: "Native Client"
                        }
                    ]
                });
            """
            )

            # Spoof navigator.languages
            driver.execute_script(
                """
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """
            )

            # Spoof window.chrome.runtime
            driver.execute_script(
                """
                if (window.chrome && window.chrome.runtime) {
                    Object.defineProperty(window.chrome.runtime, 'onConnect', {
                        get: () => undefined
                    });
                    Object.defineProperty(window.chrome.runtime, 'onMessage', {
                        get: () => undefined
                    });
                }
            """
            )

            # Spoof permissions
            driver.execute_script(
                """
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """
            )

            # Remove automation indicators
            driver.execute_script(
                """
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """
            )

            self.logger.debug("✅ Stealth scripts injected successfully")

        except Exception as e:
            self.logger.warning(f"⚠️ Some stealth scripts failed to inject: {str(e)}")

    def create_driver(self):
        """
        Create and configure a new Chrome WebDriver instance with fingerprint evasion and Decodo proxy.

        Returns:
            webdriver.Chrome: Configured Chrome WebDriver instance with Selenium Wire
        """
        try:
            self.logger.info("🔧 Creating stealth Chrome WebDriver with Decodo proxy...")

            # Configure Chrome options
            options = configure_chrome_options(
                headless=self.headless,
                user_agent=self.user_agent_override
            )

            # Configure Selenium Wire options for proxy (only if available)
            seleniumwire_options = None
            if SELENIUM_WIRE_AVAILABLE:
                seleniumwire_options = configure_seleniumwire_options()

            # Get Chrome driver path using webdriver_manager
            driver_path = ChromeDriverManager().install()
            
            # Fix the path if it's pointing to the wrong file
            if "THIRD_PARTY_NOTICES.chromedriver" in driver_path:
                driver_path = driver_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
                self.logger.info(f"🔧 Fixed ChromeDriver path: {driver_path}")
            
            # Additional fix: ensure we have the correct chromedriver executable
            if not os.path.exists(driver_path) or not os.access(driver_path, os.X_OK):
                # Try to find the actual chromedriver in the same directory
                driver_dir = os.path.dirname(driver_path)
                actual_driver = os.path.join(driver_dir, "chromedriver")
                if os.path.exists(actual_driver) and os.access(actual_driver, os.X_OK):
                    driver_path = actual_driver
                    self.logger.info(f"🔧 Found correct ChromeDriver: {driver_path}")
                else:
                    raise Exception(f"ChromeDriver not found or not executable at {driver_path}")

            # Create the Chrome driver with or without Selenium Wire
            if SELENIUM_WIRE_AVAILABLE and seleniumwire_options:
                driver = webdriver.Chrome(
                    executable_path=driver_path,
                    options=options,
                    seleniumwire_options=seleniumwire_options
                )
            else:
                driver = uc.Chrome(
                    executable_path=driver_path,
                    options=options
                )

            # Inject stealth scripts after driver creation
            self._inject_stealth_scripts(driver)

            # Set page load timeout
            driver.set_page_load_timeout(60)

            # Random startup delay to avoid pattern detection
            startup_delay = random.uniform(1, 3)
            time.sleep(startup_delay)

            # Log proxy usage for debugging
            if seleniumwire_options:
                self.logger.info("✅ Decodo proxy configured and active")
            else:
                self.logger.info("⚠️ No proxy configured - using direct connection")

            user_agent = self.user_agent_override or "Random UA"
            self.logger.info(
                f"✅ Stealth Chrome WebDriver created successfully (UA: {user_agent[:50]}...)"
            )
            return driver

        except Exception as e:
            self.logger.error(f"❌ Failed to create stealth Chrome WebDriver: {str(e)}")
            
            # Check if proxy fallback is allowed
            require_proxy = os.getenv("REQUIRE_PROXY", "false").lower() == "true"
            
            if require_proxy:
                self.logger.error("REQUIRE_PROXY is set — not attempting fallback.")
                raise
            else:
                self.logger.warning("Decodo proxy failed, falling back to direct connection.")
                
                try:
                    # Retry without proxy configuration
                    self.logger.info("🔄 Retrying Chrome setup without proxy...")
                    
                    # Get Chrome driver path again for fallback (in case it failed before)
                    try:
                        driver_path = ChromeDriverManager().install()
                        if "THIRD_PARTY_NOTICES.chromedriver" in driver_path:
                            driver_path = driver_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
                            self.logger.info(f"🔧 Fixed ChromeDriver path: {driver_path}")
                        
                        # Additional fix: ensure we have the correct chromedriver executable
                        if not os.path.exists(driver_path) or not os.access(driver_path, os.X_OK):
                            # Try to find the actual chromedriver in the same directory
                            driver_dir = os.path.dirname(driver_path)
                            actual_driver = os.path.join(driver_dir, "chromedriver")
                            if os.path.exists(actual_driver) and os.access(actual_driver, os.X_OK):
                                driver_path = actual_driver
                                self.logger.info(f"🔧 Found correct ChromeDriver: {driver_path}")
                            else:
                                raise Exception(f"ChromeDriver not found or not executable at {driver_path}")
                                
                    except Exception as driver_error:
                        self.logger.error(f"❌ ChromeDriver installation failed in fallback: {str(driver_error)}")
                        raise
                    
                    # Create the Chrome driver without Selenium Wire proxy
                    driver = uc.Chrome(
                        executable_path=driver_path,
                        options=options
                    )

                    # Inject stealth scripts after driver creation
                    self._inject_stealth_scripts(driver)

                    # Set page load timeout
                    driver.set_page_load_timeout(60)

                    # Random startup delay to avoid pattern detection
                    startup_delay = random.uniform(1, 3)
                    time.sleep(startup_delay)

                    self.logger.info("✅ Chrome WebDriver created successfully without proxy")
                    return driver
                    
                except Exception as fallback_error:
                    self.logger.error(f"❌ Fallback Chrome setup also failed: {str(fallback_error)}")
                    import traceback
                    traceback.print_exc()
                    raise

    def __enter__(self):
        """
        Create and return a Chrome WebDriver instance with retries and exponential backoff.

        Returns:
            webdriver.Chrome: Configured Chrome WebDriver instance
        """
        for attempt in range(self.max_retries):
            try:
                # Clean up any existing driver
                if self.driver is not None:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None

                # Create new driver
                self.driver = self.create_driver()
                return self.driver

            except Exception as e:
                self.logger.error(
                    f"❌ Error creating stealth driver (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                )
                import traceback
                traceback.print_exc()

                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    backoff_time = (2**attempt) + random.uniform(0, 1)
                    self.logger.info(f"⏳ Retrying in {backoff_time:.1f} seconds...")
                    time.sleep(backoff_time)
                else:
                    self.logger.error(
                        f"❌ Failed to create stealth driver after {self.max_retries} attempts"
                    )
                    raise Exception(
                        f"Failed to create stealth Chrome driver after {self.max_retries} retries. Last error: {str(e)}"
                    )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up the Chrome WebDriver instance.

        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)
        """
        self.quit()

        # Log any exceptions that occurred
        if exc_type is not None:
            self.logger.error(
                f"❌ Exception in stealth browser context: {exc_type.__name__}: {exc_val}"
            )

    def quit(self):
        """
        Safely quit the Chrome WebDriver instance with proper cleanup.
        """
        if self.driver is not None:
            try:
                self.logger.debug("🧹 Cleaning up stealth Chrome WebDriver...")
                self.driver.quit()
                self.logger.debug("✅ Stealth Chrome WebDriver cleaned up successfully")
            except Exception as e:
                self.logger.warning(f"⚠️ Error during stealth driver cleanup: {str(e)}")
            finally:
                self.driver = None


# Convenience function for backward compatibility
@contextmanager
def create_stealth_driver(headless=True, max_retries=3, user_agent_override=None):
    """
    Convenience context manager function for creating a stealth browser.

    Args:
        headless (bool): Whether to run browser in headless mode
        max_retries (int): Maximum retry attempts
        user_agent_override (str): Custom user agent string

    Yields:
        webdriver.Chrome: Configured Chrome WebDriver instance with Selenium Wire
    """
    with StealthBrowserManager(
        headless=headless,
        max_retries=max_retries,
        user_agent_override=user_agent_override,
    ) as driver:
        yield driver


# Enhanced Scraping Utilities
class ScraperEnhancements:
    """
    Enhanced scraping utilities for robust, stealthy, and production-ready scraping.
    Provides IP validation, request volume tracking, and intelligent throttling.
    """

    def __init__(self, scraper_name: str, estimated_requests: int = 0, cron_frequency: str = "daily"):
        """
        Initialize scraper enhancements.
        
        Args:
            scraper_name (str): Name of the scraper for logging
            estimated_requests (int): Estimated number of requests per run
            cron_frequency (str): How often the cron runs (e.g., "daily", "hourly")
        """
        self.scraper_name = scraper_name
        self.estimated_requests = estimated_requests
        self.cron_frequency = cron_frequency
        self.request_count = 0
        self.start_time = datetime.now()
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Log request volume awareness
        self._log_request_volume()

    def _log_request_volume(self):
        """Log request volume information and warnings."""
        print(f"\n📊 REQUEST VOLUME ANALYSIS for {self.scraper_name}")
        print("=" * 60)
        print(f"🔢 Estimated requests per run: {self.estimated_requests:,}")
        print(f"⏰ Cron frequency: {self.cron_frequency}")
        
        # Calculate daily volume
        if self.cron_frequency == "daily":
            daily_volume = self.estimated_requests
        elif self.cron_frequency == "hourly":
            daily_volume = self.estimated_requests * 24
        elif self.cron_frequency == "weekly":
            daily_volume = self.estimated_requests / 7
        else:
            daily_volume = self.estimated_requests
        
        print(f"📈 Estimated daily volume: {daily_volume:,.0f} requests")
        
        # Safety thresholds
        safe_threshold = 10000
        if daily_volume > safe_threshold:
            print(f"⚠️  WARNING: Daily volume ({daily_volume:,.0f}) exceeds safe threshold ({safe_threshold:,})")
            print("💡 Consider implementing additional throttling or reducing frequency")
        else:
            print(f"✅ Daily volume ({daily_volume:,.0f}) is within safe limits")
        
        print("=" * 60)

    def validate_ip_region(self, driver) -> Dict[str, str]:
        """
        Validate IP region by navigating to httpbin.org/ip and parsing the response.
        ENFORCES US-based IPs only using Decodo residential proxies.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dict containing IP information and validation results
        """
        try:
            self.logger.info("🌐 Validating IP region for US-based proxy...")
            
            # Try multiple IP validation services
            ip_services = [
                "https://httpbin.org/ip",
                "https://api.ipify.org?format=json",
                "https://ipinfo.io/json"
            ]
            
            for service_url in ip_services:
                try:
                    driver.get(service_url)
                    time.sleep(2)  # Allow page to load
                    
                    # Log the proxy IP for debugging
                    print(f"[StealthBrowser] Trying {service_url}:", driver.page_source[:200] + "...")
                    
                    # Parse the JSON response
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    pre_element = soup.find('pre')
                    
                    if pre_element:
                        try:
                            ip_data = json.loads(pre_element.get_text())
                            ip_address = ip_data.get('origin', ip_data.get('ip', 'Unknown'))
                            
                            # Log the IP address clearly
                            print(f"🌍 Using IP: {ip_address}")
                            
                            # ENFORCE US-based IP verification
                            is_us_based = self._verify_us_ip(ip_address)
                            
                            if is_us_based:
                                self.logger.info(f"✅ IP validation successful: {ip_address} (US-based)")
                                return {
                                    'ip_address': ip_address,
                                    'is_us_based': True,
                                    'validation_successful': True
                                }
                            else:
                                self.logger.error(f"❌ IP {ip_address} is NOT US-based - REJECTING")
                                return {
                                    'ip_address': ip_address,
                                    'is_us_based': False,
                                    'validation_successful': False,
                                    'error': f"IP {ip_address} is not US-based"
                                }
                            
                        except json.JSONDecodeError:
                            continue  # Try next service
                    else:
                        continue  # Try next service
                        
                except Exception as e:
                    continue  # Try next service
            
            # If all services fail, return failure
            self.logger.error("❌ All IP validation services failed")
            return {
                'ip_address': 'Unknown',
                'is_us_based': False,
                'validation_successful': False,
                'error': 'All IP validation services failed'
            }
                
        except Exception as e:
            self.logger.error(f"❌ IP validation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'validation_successful': False, 'error': str(e)}

    def _verify_us_ip(self, ip_address: str) -> bool:
        """
        Verify if IP address is US-based using a free geolocation API.
        
        Args:
            ip_address (str): IP address to verify
            
        Returns:
            bool: True if IP is US-based, False otherwise
        """
        try:
            # Use ipapi.co for free geolocation lookup
            response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                country_code = data.get('country_code', '').upper()
                is_us = country_code == 'US'
                
                if is_us:
                    self.logger.info(f"✅ IP {ip_address} is US-based ({data.get('country_name', 'Unknown')})")
                else:
                    self.logger.warning(f"⚠️ IP {ip_address} is not US-based ({data.get('country_name', 'Unknown')})")
                
                return is_us
            else:
                self.logger.warning(f"⚠️ Could not verify IP geolocation (Status: {response.status_code})")
                return False  # Assume NOT US-based if verification fails
                
        except Exception as e:
            self.logger.warning(f"⚠️ IP geolocation verification failed: {str(e)}")
            return False  # Assume NOT US-based if verification fails

    def throttle_request(self, min_delay: float = 1.5, max_delay: float = 4.5):
        """
        Add intelligent throttling between requests to avoid detection.
        
        Args:
            min_delay (float): Minimum delay in seconds
            max_delay (float): Maximum delay in seconds
        """
        delay = random.uniform(min_delay, max_delay)
        self.logger.debug(f"⏳ Throttling for {delay:.1f} seconds...")
        time.sleep(delay)

    def track_request(self, request_type: str = "page_load"):
        """
        Track request count and log progress.
        
        Args:
            request_type (str): Type of request being tracked
        """
        self.request_count += 1
        elapsed = datetime.now() - self.start_time
        
        # Log every 10th request or if it's a significant milestone
        if self.request_count % 10 == 0 or self.request_count in [1, 5, 25, 50, 100]:
            print(f"📊 {self.scraper_name}: {self.request_count:,} requests completed in {elapsed}")
            
            # Warn if approaching estimated limit
            if self.estimated_requests > 0:
                progress = (self.request_count / self.estimated_requests) * 100
                if progress > 90:
                    print(f"⚠️  Approaching estimated request limit ({progress:.1f}%)")
                elif progress > 100:
                    print(f"🚨 Exceeded estimated request limit by {progress - 100:.1f}%")

    def get_session_summary(self) -> Dict[str, any]:
        """
        Get a summary of the scraping session.
        
        Returns:
            Dict containing session statistics
        """
        elapsed = datetime.now() - self.start_time
        requests_per_minute = (self.request_count / elapsed.total_seconds()) * 60 if elapsed.total_seconds() > 0 else 0
        
        return {
            'scraper_name': self.scraper_name,
            'total_requests': self.request_count,
            'session_duration': str(elapsed),
            'requests_per_minute': round(requests_per_minute, 2),
            'estimated_requests': self.estimated_requests,
            'cron_frequency': self.cron_frequency
        }

    def log_session_summary(self):
        """Log a comprehensive session summary."""
        summary = self.get_session_summary()
        
        print(f"\n📊 SESSION SUMMARY for {self.scraper_name}")
        print("=" * 60)
        print(f"🔢 Total requests: {summary['total_requests']:,}")
        print(f"⏱️  Session duration: {summary['session_duration']}")
        print(f"📈 Requests per minute: {summary['requests_per_minute']}")
        print(f"🎯 Estimated requests: {summary['estimated_requests']:,}")
        print(f"⏰ Cron frequency: {summary['cron_frequency']}")
        
        # Performance analysis
        if summary['estimated_requests'] > 0:
            accuracy = (summary['total_requests'] / summary['estimated_requests']) * 100
            print(f"📊 Estimate accuracy: {accuracy:.1f}%")
        
        print("=" * 60)


def create_enhanced_scraper(scraper_name: str, estimated_requests: int, cron_frequency: str = "daily") -> ScraperEnhancements:
    """
    Factory function to create an enhanced scraper instance.
    
    Args:
        scraper_name (str): Name of the scraper
        estimated_requests (int): Estimated number of requests per run
        cron_frequency (str): How often the cron runs
        
    Returns:
        ScraperEnhancements: Configured scraper enhancements instance
    """
    return ScraperEnhancements(scraper_name, estimated_requests, cron_frequency)


def add_throttling_to_loop():
    """
    Add throttling between loop iterations.
    This function should be called between any looped page loads.
    """
    time.sleep(random.uniform(0.2, 0.5))  # Minimal delay for fast player scraping


def validate_browser_ip(driver) -> bool:
    """
    Quick IP validation for browser instances.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if IP validation was successful
    """
    try:
        driver.get("https://httpbin.org/ip")
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        pre_element = soup.find('pre')
        
        if pre_element:
            ip_data = json.loads(pre_element.get_text())
            ip_address = ip_data.get('origin', 'Unknown')
            print(f"🌍 Using IP: {ip_address}")
            return True
        else:
            print("⚠️ Could not validate IP address")
            return False
            
    except Exception as e:
        print(f"❌ IP validation failed: {str(e)}")
        return False

# Configure Selenium Wire logging to be less verbose
logging.getLogger('seleniumwire').setLevel(logging.WARNING)
logging.getLogger('seleniumwire.handler').setLevel(logging.WARNING)
