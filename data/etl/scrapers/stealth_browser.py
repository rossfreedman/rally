#!/usr/bin/env python3
"""
Stealth Browser Manager for Rally Tennis Scraper
Uses undetected-chromedriver with fingerprint evasion techniques to avoid bot detection.
"""

import logging
import os
import random
import tempfile
import time
from contextlib import contextmanager

import undetected_chromedriver as uc

logger = logging.getLogger(__name__)


class StealthBrowserManager:
    """
    Context manager for handling undetected Chrome WebDriver sessions with fingerprint evasion.
    Implements various techniques to avoid bot detection on TennisScores.com and similar sites.
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

    def _get_random_user_agent(self):
        """Get a random realistic user agent string."""
        if self.user_agent_override:
            return self.user_agent_override

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        return random.choice(user_agents)

    def _get_random_window_size(self):
        """Get a random realistic window size."""
        sizes = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1600, 900),
            (1280, 720),
        ]
        return random.choice(sizes)

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
        Create and configure a new undetected Chrome WebDriver instance with fingerprint evasion.

        Returns:
            uc.Chrome: Configured undetected Chrome WebDriver instance
        """
        try:
            self.logger.info("🔧 Creating stealth Chrome WebDriver...")

            # Create Chrome options
            options = uc.ChromeOptions()

            # Essential options for headless mode and containerized environments
            if self.headless:
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
            width, height = self._get_random_window_size()
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
            user_agent = self._get_random_user_agent()
            options.add_argument(f"--user-agent={user_agent}")

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

            # Create the undetected Chrome driver with explicit Chrome version
            # Force download of matching ChromeDriver version
            import subprocess
            import re
            
            try:
                # Get Chrome version more reliably
                chrome_version_output = subprocess.check_output([
                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'
                ], universal_newlines=True)
                chrome_version_match = re.search(r'(\d+)\.', chrome_version_output)
                chrome_major_version = int(chrome_version_match.group(1)) if chrome_version_match else None
                self.logger.info(f"🔍 Detected Chrome version: {chrome_major_version}")
            except:
                chrome_major_version = None
                self.logger.warning("⚠️ Could not detect Chrome version, using auto-detection")
            
            driver = uc.Chrome(
                options=options,
                version_main=chrome_major_version,  # Use detected Chrome version
                driver_executable_path=None,  # Auto-download if needed
                use_subprocess=True,  # Force fresh driver download
            )

            # Inject stealth scripts after driver creation
            self._inject_stealth_scripts(driver)

            # Set page load timeout
            driver.set_page_load_timeout(60)

            # Random startup delay to avoid pattern detection
            startup_delay = random.uniform(1, 3)
            time.sleep(startup_delay)

            self.logger.info(
                f"✅ Stealth Chrome WebDriver created successfully (UA: {user_agent[:50]}...)"
            )
            return driver

        except Exception as e:
            self.logger.error(f"❌ Failed to create stealth Chrome WebDriver: {str(e)}")
            raise

    def __enter__(self):
        """
        Create and return a Chrome WebDriver instance with retries and exponential backoff.

        Returns:
            uc.Chrome: Configured Chrome WebDriver instance
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
        uc.Chrome: Configured undetected Chrome WebDriver instance
    """
    with StealthBrowserManager(
        headless=headless,
        max_retries=max_retries,
        user_agent_override=user_agent_override,
    ) as driver:
        yield driver
