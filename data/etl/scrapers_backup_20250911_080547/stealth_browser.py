#!/usr/bin/env python3
"""
Enhanced Stealth Browser Manager for Rally Tennis Scraper
Implements comprehensive anti-detection measures with smart request pacing, IP rotation,
retry logic, CAPTCHA detection, and session fingerprinting.
"""

import json
import logging
import os
import random
import tempfile
import time
import warnings
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="_distutils_hack")
warnings.filterwarnings("ignore", category=UserWarning, module="setuptools")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import subprocess
import re

# Try to import seleniumwire, but provide fallback if it fails
try:
    from seleniumwire import webdriver
    SELENIUM_WIRE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Selenium Wire not available: {e}")
    SELENIUM_WIRE_AVAILABLE = False
    webdriver = None

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

def get_installed_chrome_version():
    """Get the installed Chrome version."""
    try:
        # Try to get Chrome version on macOS
        result = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version_match = re.search(r'Chrome\s+(\d+)\.(\d+)\.(\d+)\.(\d+)', result.stdout)
            if version_match:
                return f"{version_match.group(1)}.{version_match.group(2)}.{version_match.group(3)}"
    except Exception:
        pass
    
    try:
        # Try alternative method
        result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version_match = re.search(r'(\d+)\.(\d+)\.(\d+)', result.stdout)
            if version_match:
                return f"{version_match.group(1)}.{version_match.group(2)}.{version_match.group(3)}"
    except Exception:
        pass
    
    # Fallback to default version
    return "120.0.6099.109"

# Import the proxy manager
try:
    from .proxy_manager import get_proxy_rotator
except ImportError:
    try:
        from proxy_manager import get_proxy_rotator
    except ImportError:
        # Try direct import from current directory
        import sys
        import os
        # Get the absolute path to the scrapers directory
        current_file = os.path.abspath(__file__)
        scrapers_dir = os.path.dirname(current_file)
        if scrapers_dir not in sys.path:
            sys.path.insert(0, scrapers_dir)
        from proxy_manager import get_proxy_rotator

class DetectionType(Enum):
    """Types of detection that can occur during scraping."""
    CAPTCHA = "captcha"
    ACCESS_DENIED = "access_denied"
    RATE_LIMIT = "rate_limit"
    BLANK_PAGE = "blank_page"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

@dataclass
class RequestMetrics:
    """Track metrics for a single request."""
    url: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status_code: Optional[int] = None
    response_size: Optional[int] = None
    detection_type: Optional[DetectionType] = None
    retry_count: int = 0
    proxy_used: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Get request duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

@dataclass
class SessionMetrics:
    """Track metrics for an entire scraping session."""
    session_id: str
    start_time: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    proxy_rotations: int = 0
    detections: Dict[DetectionType, int] = field(default_factory=dict)
    total_duration: float = 0.0
    leagues_scraped: List[str] = field(default_factory=list)
    http_requests: int = 0
    browser_requests: int = 0
    avg_latency_per_proxy: Dict[str, float] = field(default_factory=dict)
    proxy_success_rates: Dict[str, float] = field(default_factory=dict)
    pool_promotions: int = 0
    pool_demotions: int = 0
    sticky_sessions: int = 0
    
    def add_detection(self, detection_type: DetectionType):
        """Add a detection event."""
        self.detections[detection_type] = self.detections.get(detection_type, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        return {
            "session_id": self.session_id,
            "duration": self.total_duration,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "proxy_rotations": self.proxy_rotations,
            "detections": {k.value: v for k, v in self.detections.items()},
            "leagues_scraped": self.leagues_scraped,
            "http_requests": self.http_requests,
            "browser_requests": self.browser_requests,
            "avg_latency_per_proxy": self.avg_latency_per_proxy,
            "proxy_success_rates": self.proxy_success_rates,
            "pool_promotions": self.pool_promotions,
            "pool_demotions": self.pool_demotions,
            "sticky_sessions": self.sticky_sessions
        }

class UserAgentManager:
    """Manages realistic user agent rotation."""
    
    DESKTOP_USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        """Get a random realistic user agent."""
        return random.choice(cls.DESKTOP_USER_AGENTS)

class StealthConfig:
    """Configuration for stealth behavior."""
    
    def __init__(self, 
                 fast_mode: bool = False,
                 verbose: bool = False,
                 environment: str = "production",
                 force_browser: bool = False,
                 headless: bool = True,
                 min_delay: float = None,
                 max_delay: float = None,
                 max_retries: int = None,
                 base_backoff: float = None,
                 max_backoff: float = None):
        self.fast_mode = fast_mode
        self.verbose = verbose
        self.environment = environment
        self.force_browser = force_browser
        self.headless = headless
        
        # Environment-specific defaults (can be overridden)
        if min_delay is None:
            if environment == "local":
                self.min_delay = 0.5 if fast_mode else 0.8
            elif environment == "staging":
                self.min_delay = 1.5 if fast_mode else 2.5
            else:  # production
                self.min_delay = 2.0 if fast_mode else 3.0
        else:
            self.min_delay = min_delay
            
        if max_delay is None:
            if environment == "local":
                self.max_delay = 1.5 if fast_mode else 2.0
            elif environment == "staging":
                self.max_delay = 4.0 if fast_mode else 6.0
            else:  # production
                self.max_delay = 5.0 if fast_mode else 8.0
        else:
            self.max_delay = max_delay
        
        # Retry settings (can be overridden)
        self.max_retries = max_retries if max_retries is not None else 3
        self.base_backoff = base_backoff if base_backoff is not None else 1.0
        self.max_backoff = max_backoff if max_backoff is not None else 10.0
        
        # Proxy settings
        self.requests_per_proxy = 30
        self.session_duration = 600  # 10 minutes
        
        # Detection thresholds
        self.min_page_size = 1000
        self.timeout_seconds = 20
        
        # Browser settings
        self.window_width = 1920
        self.window_height = 1080

class EnhancedStealthBrowser:
    """Enhanced stealth browser with comprehensive anti-detection measures."""
    
    def __init__(self, config: StealthConfig):
        self.config = config
        # Use sticky sessions by default for better performance
        try:
            self.proxy_rotator = get_proxy_rotator(sticky=True)
        except TypeError:
            # Fallback for older proxy rotator versions
            self.proxy_rotator = get_proxy_rotator()
        
        self.session_metrics = SessionMetrics(
            session_id=f"session_{int(time.time())}",
            start_time=datetime.now()
        )
        self.current_driver = None
        self.current_proxy = None
        self.request_count = 0
        
        logger.info(f"🚀 Enhanced Stealth Browser initialized")
        logger.info(f"   Mode: {'FAST' if config.fast_mode else 'STEALTH'}")
        logger.info(f"   Environment: {config.environment}")
        logger.info(f"   Delays: {config.min_delay}-{config.max_delay}s")
    
    def _create_driver(self, preferred_ua: str = None):
        """Create a new Chrome driver with stealth settings and OS signal leak prevention."""
        # Import settings
        try:
            from .settings_stealth import STEALTH_STICKY_UA, STEALTH_LANG, STEALTH_VIEWPORT, STEALTH_TIMEZONE
        except ImportError:
            from settings_stealth import STEALTH_STICKY_UA, STEALTH_LANG, STEALTH_VIEWPORT, STEALTH_TIMEZONE
        
        # Get user agent - use preferred if provided, otherwise get appropriate one
        if preferred_ua:
            user_agent = preferred_ua
        else:
            # Import UA manager
            try:
                from .user_agent_manager import UserAgentManager
            except ImportError:
                from user_agent_manager import UserAgentManager
            
            ua_mgr = UserAgentManager()
            if STEALTH_STICKY_UA:
                user_agent = ua_mgr.get_sticky_ua()
            else:
                user_agent = ua_mgr.get_user_agent_for_site("https://tenniscores.com")
        
        # Try multiple ChromeDriver strategies
        driver = None
        strategies = [
            ("Basic ChromeDriver", self._try_basic_chromedriver),
            ("Selenium Wire with Proxy", self._try_selenium_wire),
            ("WebDriver Manager", self._try_webdriver_manager),
            ("Undetected ChromeDriver", self._try_undetected_chromedriver),
            ("Standard ChromeDriver", self._try_standard_chromedriver),
            ("Minimal Options", self._try_minimal_options)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"🔧 Trying {strategy_name}...")
                # Create fresh options for each strategy to avoid reuse issues
                fresh_options = self._create_fresh_options(user_agent)
                driver = strategy_func(fresh_options, user_agent)
                if driver:
                    logger.info(f"✅ Successfully created driver using {strategy_name}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ {strategy_name} failed: {e}")
                continue
        
        if not driver:
            raise Exception("All Chrome driver strategies failed")
        
        # Set timezone using CDP command
        try:
            driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": STEALTH_TIMEZONE})
        except Exception as e:
            if hasattr(self.config, 'verbose') and self.config.verbose:
                logger.warning(f"⚠️ Failed to set timezone: {e}")
        
        # Inject stealth scripts with OS-specific overrides
        self._inject_stealth_scripts(driver, user_agent)
        
        return driver
    
    def _create_fresh_options(self, user_agent: str):
        """Create fresh ChromeOptions for each strategy attempt."""
        # Import settings and build function
        try:
            from .settings_stealth import STEALTH_LANG, STEALTH_VIEWPORT
            from .chrome_driver_config import build_chrome_options
        except ImportError:
            from settings_stealth import STEALTH_LANG, STEALTH_VIEWPORT
            from chrome_driver_config import build_chrome_options
        
        # Use the centralized build_chrome_options function
        options = build_chrome_options(
            user_agent=user_agent,
            lang=STEALTH_LANG,
            viewport=STEALTH_VIEWPORT,
            headless=self.config.headless,
            proxy=self.current_proxy if hasattr(self, 'current_proxy') else None
        )
        
        return options
    
    def _try_selenium_wire(self, options, user_agent):
        """Try Selenium Wire with proxy."""
        if not SELENIUM_WIRE_AVAILABLE or not self.current_proxy:
            raise Exception("Selenium Wire not available or no proxy")
        
        seleniumwire_options = {
            'proxy': {
                'http': self.current_proxy,
                'https': self.current_proxy
            },
            'verify_ssl': False
        }
        return webdriver.Chrome(options=options, seleniumwire_options=seleniumwire_options)
    
    def _try_webdriver_manager(self, options, user_agent):
        """Try WebDriver Manager."""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            driver_path = ChromeDriverManager().install()
            # Fix the path - WebDriver Manager sometimes returns the wrong file
            if 'THIRD_PARTY_NOTICES' in driver_path:
                # Extract the correct path to the actual chromedriver executable
                base_dir = os.path.dirname(driver_path)
                correct_path = os.path.join(base_dir, 'chromedriver')
                if os.path.exists(correct_path):
                    driver_path = correct_path
                else:
                    raise Exception(f"Could not find chromedriver executable in {base_dir}")
            
            # Use the working ChromeDriver directly
            from selenium import webdriver
            return webdriver.Chrome(executable_path=driver_path, options=options)
        except Exception as e:
            raise Exception(f"WebDriver Manager failed: {e}")
    
    def _try_undetected_chromedriver(self, options, user_agent):
        """Try undetected-chromedriver."""
        try:
            # Try the most basic approach first
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            
            # Use the working ChromeDriver we know has permissions
            working_driver_path = "/Users/rossfreedman/.wdm/drivers/chromedriver/mac64/139.0.7258.138/chromedriver-mac-arm64/chromedriver"
            if os.path.exists(working_driver_path):
                service = Service(executable_path=working_driver_path)
                return webdriver.Chrome(service=service, options=options)
            else:
                # Fallback to version-based approach
                chrome_version = get_installed_chrome_version()
                version_main = int(chrome_version.split('.')[0])
                return uc.Chrome(options=options, version_main=version_main)
        except Exception as e:
            raise Exception(f"Undetected ChromeDriver failed: {e}")
    
    def _try_standard_chromedriver(self, options, user_agent):
        """Try standard ChromeDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            
            # Use the working ChromeDriver directly
            working_driver_path = "/Users/rossfreedman/.wdm/drivers/chromedriver/mac64/139.0.7258.138/chromedriver-mac-arm64/chromedriver"
            if os.path.exists(working_driver_path):
                service = Service(executable_path=working_driver_path)
                return webdriver.Chrome(service=service, options=options)
            else:
                return webdriver.Chrome(options=options)
        except Exception as e:
            raise Exception(f"Standard ChromeDriver failed: {e}")
    
    def _try_minimal_options(self, options, user_agent):
        """Try with minimal options as last resort."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            
            # Create very minimal options
            minimal_options = webdriver.ChromeOptions()
            minimal_options.add_argument("--no-sandbox")
            minimal_options.add_argument("--disable-dev-shm-usage")
            minimal_options.add_argument("--headless")
            minimal_options.add_argument(f"--user-agent={user_agent}")
            minimal_options.add_argument("--disable-gpu")
            minimal_options.add_argument("--disable-extensions")
            minimal_options.add_argument("--disable-plugins")
            
            # Use the working ChromeDriver directly
            working_driver_path = "/Users/rossfreedman/.wdm/drivers/chromedriver/mac64/139.0.7258.138/chromedriver-mac-arm64/chromedriver"
            if os.path.exists(working_driver_path):
                service = Service(executable_path=working_driver_path)
                return webdriver.Chrome(service=service, options=minimal_options)
            else:
                return webdriver.Chrome(options=minimal_options)
        except Exception as e:
            raise Exception(f"Minimal Options failed: {e}")
    
    def _try_basic_chromedriver(self, options, user_agent):
        """Try the most basic ChromeDriver approach."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            
            # Create very minimal options
            minimal_options = webdriver.ChromeOptions()
            minimal_options.add_argument("--no-sandbox")
            minimal_options.add_argument("--disable-dev-shm-usage")
            minimal_options.add_argument("--headless")
            minimal_options.add_argument(f"--user-agent={user_agent}")
            minimal_options.add_argument("--disable-gpu")
            minimal_options.add_argument("--disable-extensions")
            minimal_options.add_argument("--disable-plugins")
            
            # Use the working ChromeDriver directly
            working_driver_path = "/Users/rossfreedman/.wdm/drivers/chromedriver/mac64/139.0.7258.138/chromedriver-mac-arm64/chromedriver"
            if os.path.exists(working_driver_path):
                service = Service(executable_path=working_driver_path)
                return webdriver.Chrome(service=service, options=minimal_options)
            else:
                return webdriver.Chrome(options=minimal_options)
        except Exception as e:
            raise Exception(f"Basic ChromeDriver failed: {e}")
    
    def _inject_stealth_scripts(self, driver, user_agent: str = None):
        """Inject JavaScript to hide automation indicators and override OS signals."""
        # Enhanced stealth scripts for APTA Chicago - grouped by functionality to avoid scope issues
        stealth_scripts = [
            # Core webdriver removal and automation detection removal
            """
            // Core webdriver removal - most important
            Object.defineProperty(navigator, 'webdriver', {get: function() { return undefined; }, configurable: true});
            delete window.navigator.webdriver;
            
            // Remove automation flags
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // Override chrome runtime
            if (!window.chrome) { window.chrome = {runtime: {}}; }
            
            // Remove automation detection
            if (window.navigator && window.navigator.__proto__) { delete window.navigator.__proto__.webdriver; }
            delete window.navigator.webdriver;
            """,
            
            # Navigator overrides
            """
            // Override permissions
            Object.defineProperty(navigator, 'permissions', {get: function() { return {query: function() { return Promise.resolve({state: 'granted'}); }}; }});
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {get: function() { return []; }});
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {get: function() { return ['en-US', 'en']; }});
            
            // Override connection
            Object.defineProperty(navigator, 'connection', {get: function() { return {effectiveType: '4g', rtt: 50, downlink: 10}; }});
            
            // Override language
            Object.defineProperty(navigator, 'language', {get: function() { return 'en-US'; }});
            
            // Override cookieEnabled
            Object.defineProperty(navigator, 'cookieEnabled', {get: function() { return true; }});
            
            // Override onLine
            Object.defineProperty(navigator, 'onLine', {get: function() { return true; }});
            
            // Override doNotTrack
            Object.defineProperty(navigator, 'doNotTrack', {get: function() { return null; }});
            """,
            
            # Hardware and device overrides
            """
            // Override deviceMemory (only if not already defined)
            if (!navigator.deviceMemory) { Object.defineProperty(navigator, 'deviceMemory', {get: function() { return 8; }, configurable: true}); }
            
            // Override hardwareConcurrency (only if not already defined)
            if (!navigator.hardwareConcurrency) { Object.defineProperty(navigator, 'hardwareConcurrency', {get: function() { return 8; }, configurable: true}); }
            
            // Override maxTouchPoints (only if not already defined)
            if (!navigator.maxTouchPoints) { Object.defineProperty(navigator, 'maxTouchPoints', {get: function() { return 0; }, configurable: true}); }
            
            // Override platform (only if not already defined)
            if (!navigator.platform) { Object.defineProperty(navigator, 'platform', {get: function() { return 'Win32'; }, configurable: true}); }
            
            // Override vendor (only if not already defined)
            if (!navigator.vendor) { Object.defineProperty(navigator, 'vendor', {get: function() { return 'Google Inc.'; }, configurable: true}); }
            
            // Override product (only if not already defined)
            if (!navigator.product) { Object.defineProperty(navigator, 'product', {get: function() { return 'Gecko'; }, configurable: true}); }
            
            // Override appName (only if not already defined)
            if (!navigator.appName) { Object.defineProperty(navigator, 'appName', {get: function() { return 'Netscape'; }, configurable: true}); }
            
            // Override appVersion (only if not already defined)
            if (!navigator.appVersion) { Object.defineProperty(navigator, 'appVersion', {get: function() { return '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'; }, configurable: true}); }
            
            // Override userAgent (only if not already defined)
            if (!navigator.userAgent) { Object.defineProperty(navigator, 'userAgent', {get: function() { return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'; }, configurable: true}); }
            
            // Override taintEnabled (legacy)
            Object.defineProperty(navigator, 'taintEnabled', {get: function() { return false; }});
            """,
            
            # Screen and window overrides
            """
            // Override screen properties (only if not already defined)
            if (!screen.width) { Object.defineProperty(screen, 'width', {get: function() { return 1920; }, configurable: true}); }
            if (!screen.height) { Object.defineProperty(screen, 'height', {get: function() { return 1080; }, configurable: true}); }
            if (!screen.availWidth) { Object.defineProperty(screen, 'availWidth', {get: function() { return 1920; }, configurable: true}); }
            if (!screen.availHeight) { Object.defineProperty(screen, 'availHeight', {get: function() { return 1040; }, configurable: true}); }
            if (!screen.colorDepth) { Object.defineProperty(screen, 'colorDepth', {get: function() { return 24; }, configurable: true}); }
            if (!screen.pixelDepth) { Object.defineProperty(screen, 'pixelDepth', {get: function() { return 24; }, configurable: true}); }
            
            // Override window properties (only if not already defined)
            if (!window.outerWidth) { Object.defineProperty(window, 'outerWidth', {get: function() { return 1920; }, configurable: true}); }
            if (!window.outerHeight) { Object.defineProperty(window, 'outerHeight', {get: function() { return 1040; }, configurable: true}); }
            if (!window.innerWidth) { Object.defineProperty(window, 'innerWidth', {get: function() { return 1920; }, configurable: true}); }
            if (!window.innerHeight) { Object.defineProperty(window, 'innerHeight', {get: function() { return 1040; }, configurable: true}); }
            """,
            
            # Timezone and internationalization
            """
            // Override timezone
            if (typeof Intl !== 'undefined') { 
                Object.defineProperty(Intl, 'DateTimeFormat', {
                    get: function() { 
                        return function() { 
                            return {resolvedOptions: function() { return {timeZone: 'America/Chicago'}; } }; 
                        }; 
                    }
                }); 
            }
            """,
            
            # Media and device APIs
            """
            // Override mediaDevices
            Object.defineProperty(navigator, 'mediaDevices', {get: function() { return {enumerateDevices: function() { return Promise.resolve([]); } }; }});
            
            // Override geolocation
            Object.defineProperty(navigator, 'geolocation', {get: function() { return {getCurrentPosition: function() {}, watchPosition: function() {} }; }});
            
            // Override service worker
            Object.defineProperty(navigator, 'serviceWorker', {get: function() { return {register: function() { return Promise.resolve(); }, getRegistrations: function() { return Promise.resolve([]); } }; }});
            
            // Override storage
            Object.defineProperty(navigator, 'storage', {get: function() { return {estimate: function() { return Promise.resolve({usage: 0, quota: 0}); } }; }});
            
            // Override wake lock
            Object.defineProperty(navigator, 'wakeLock', {get: function() { return {request: function() { return Promise.resolve(); } }; }});
            
            // Override clipboard
            Object.defineProperty(navigator, 'clipboard', {get: function() { return {readText: function() { return Promise.resolve(''); }, writeText: function() { return Promise.resolve(); } }; }});
            
            // Override presentation
            Object.defineProperty(navigator, 'presentation', {get: function() { return {defaultRequest: null, receiver: null}; }});
            
            // Override credentials
            Object.defineProperty(navigator, 'credentials', {get: function() { return {create: function() { return Promise.resolve(); }, get: function() { return Promise.resolve(); }, preventSilentAccess: function() {} }; }});
            
            // Override locks
            Object.defineProperty(navigator, 'locks', {get: function() { return {request: function() { return Promise.resolve(); }, query: function() { return Promise.resolve([]); } }; }});
            
            // Override contacts
            Object.defineProperty(navigator, 'contacts', {get: function() { return {select: function() { return Promise.resolve([]); } }; }});
            
            // Override keyboard
            Object.defineProperty(navigator, 'keyboard', {get: function() { return {lock: function() { return Promise.resolve(); }, unlock: function() {} }; }});
            
            // Override virtual keyboard
            Object.defineProperty(navigator, 'virtualKeyboard', {get: function() { return {show: function() {}, hide: function() {} }; }});
            
            // Override xr
            Object.defineProperty(navigator, 'xr', {get: function() { return {isSessionSupported: function() { return Promise.resolve(false); } }; }});
            
            // Override bluetooth
            Object.defineProperty(navigator, 'bluetooth', {get: function() { return {requestDevice: function() { return Promise.resolve(); } }; }});
            
            // Override usb
            Object.defineProperty(navigator, 'usb', {get: function() { return {requestDevice: function() { return Promise.resolve(); } }; }});
            
            // Override serial
            Object.defineProperty(navigator, 'serial', {get: function() { return {requestPort: function() { return Promise.resolve(); } }; }});
            
            // Override hid
            Object.defineProperty(navigator, 'hid', {get: function() { return {requestDevice: function() { return Promise.resolve(); } }; }});
            
            // Override gamepad
            Object.defineProperty(navigator, 'gamepad', {get: function() { return {getGamepads: function() { return []; } }; }});
            """,
            
            # Function overrides and toString behavior
            """
            // Override toString behavior and hasOwnProperty
            var originalFunction = Function.prototype.toString;
            var originalHasOwnProperty = Object.prototype.hasOwnProperty;
            
            Function.prototype.toString = function() {
                if (this === Function.prototype.toString) return originalFunction.call(this);
                if (this === window.navigator.toString) return '[object Navigator]';
                if (window.navigator.webdriver && this === window.navigator.webdriver.toString) return '[object Navigator]';
                return originalFunction.call(this);
            };
            
            Object.prototype.hasOwnProperty = function(prop) {
                if (prop === 'webdriver') return false;
                return originalHasOwnProperty.call(this, prop);
            };
            
            // Override property descriptors (complete version)
            Object.defineProperty(navigator, 'webdriver', {
                get: function() { return undefined; },
                set: function() {},
                configurable: true
            });
            
            // Override toString for navigator
            navigator.toString = function() { return '[object Navigator]'; };
            
            // Override constructor (simplified)
            navigator.constructor = function Navigator() {};
            
            // Override propertyIsEnumerable
            navigator.propertyIsEnumerable = function(prop) {
                if (prop === 'webdriver') return false;
                return Object.prototype.propertyIsEnumerable.call(this, prop);
            };
            """
        ]
        
        # Add OS-specific overrides for APTA
        if user_agent and "Windows" in user_agent:
            # Extract the last part of the user agent for appVersion
            ua_parts = user_agent.split(' ')
            app_version = ua_parts[-1] if ua_parts else '5.0'
            
            os_override_scripts = [
                # Override platform to Windows
                "Object.defineProperty(navigator, 'platform', {get: function() { return 'Win32'; }});",
                
                # Override userAgent to match the selected Windows UA
                "Object.defineProperty(navigator, 'userAgent', {get: function() { return '" + user_agent + "'; }});",
                
                # Override appVersion to match Windows
                "Object.defineProperty(navigator, 'appVersion', {get: function() { return '" + app_version + "'; }});",
                
                # Override vendor to match Windows
                "Object.defineProperty(navigator, 'vendor', {get: function() { return 'Google Inc.'; }});",
                
                # Override product to match Windows
                "Object.defineProperty(navigator, 'product', {get: function() { return 'Gecko'; }});",
                
                # Override hardwareConcurrency to realistic Windows value
                "Object.defineProperty(navigator, 'hardwareConcurrency', {get: function() { return 8; }});",
                
                # Override deviceMemory to realistic Windows value
                "Object.defineProperty(navigator, 'deviceMemory', {get: function() { return 8; }});"
            ]
            stealth_scripts.extend(os_override_scripts)
        
        for script in stealth_scripts:
            try:
                driver.execute_script(script)
            except Exception as e:
                if self.config.verbose:
                    logger.warning(f"⚠️ Failed to inject stealth script: {e}")
    
    def _should_rotate_proxy(self) -> bool:
        """Determine if we should rotate the proxy."""
        return self.request_count % self.config.requests_per_proxy == 0
    
    def _rotate_proxy(self):
        """Rotate to a new proxy."""
        old_proxy = self.current_proxy
        self.current_proxy = self.proxy_rotator.get_proxy()
        self.session_metrics.proxy_rotations += 1
        
        logger.info(f"🔄 Rotating proxy: {old_proxy} → {self.current_proxy}")
        
        # Recreate driver with new proxy
        if self.current_driver:
            self.current_driver.quit()
        self.current_driver = self._create_driver()
    
    def _detect_blocking(self, html: str, status_code: int) -> Optional[DetectionType]:
        """Detect if the page is blocked or showing CAPTCHA."""
        html_lower = html.lower()
        
        # Check for CAPTCHA indicators (refined to avoid CDN false positives)
        captcha_indicators = [
            "captcha", "robot", "bot check", "verify you are human",
            "cloudflare ray id", "ddos protection by cloudflare", 
            "access denied", "blocked"
        ]
        
        # ALLOW legitimate CDN references 
        if any(cdn in html_lower for cdn in [
            "cdnjs.cloudflare.com", "cdn.cloudflare.com", "ajax.cloudflare.com"
        ]):
            # Only flag if we see actual protection patterns along with CDN
            protection_patterns = ["ray id", "challenge", "checking your browser"]
            if not any(pattern in html_lower for pattern in protection_patterns):
                pass  # Skip CAPTCHA detection for legitimate CDN usage
        
        for indicator in captcha_indicators:
            if indicator in html_lower:
                return DetectionType.CAPTCHA
        
        # Check for blank or very short pages
        if len(html) < self.config.min_page_size:
            return DetectionType.BLANK_PAGE
        
        # Check for access denied
        if "access denied" in html_lower or "blocked" in html_lower:
            return DetectionType.ACCESS_DENIED
        
        # Check status codes
        if status_code == 429:
            return DetectionType.RATE_LIMIT
        elif status_code == 403:
            return DetectionType.ACCESS_DENIED
        
        return None
    
    def _safe_request(self, url: str, max_retries: int = None) -> Tuple[bool, str, Optional[DetectionType]]:
        """Make a safe request with retry logic and detection."""
        if max_retries is None:
            max_retries = self.config.max_retries
        
        # Track current URL for UA management
        self.current_url = url
        
        # Import UA manager functions
        try:
            from .user_agent_manager import report_ua_success, report_ua_failure, get_user_agent_for_site
        except ImportError:
            import sys
            import os
            # Get the absolute path to the scrapers directory
            current_file = os.path.abspath(__file__)
            scrapers_dir = os.path.dirname(current_file)
            if scrapers_dir not in sys.path:
                sys.path.insert(0, scrapers_dir)
            from user_agent_manager import report_ua_success, report_ua_failure, get_user_agent_for_site
        
        # Get User-Agent for this request
        user_agent = get_user_agent_for_site(url)
        
        for attempt in range(max_retries + 1):
            try:
                # Check if we should rotate proxy
                if self._should_rotate_proxy():
                    self._rotate_proxy()
                
                # Make request
                start_time = datetime.now()
                self.current_driver.get(url)
                
                # Wait for page to load
                WebDriverWait(self.current_driver, self.config.timeout_seconds).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Simulate human behavior to avoid detection
                self._simulate_human_behavior(self.current_driver)
                
                # Get page content
                html = self.current_driver.page_source
                title = self.current_driver.title
                
                # Update metrics
                self.request_count += 1
                self.session_metrics.total_requests += 1
                
                # Detect blocking
                detection = self._detect_blocking(html, 200)
                
                if detection:
                    self.session_metrics.add_detection(detection)
                    report_ua_failure(user_agent, url)
                    logger.warning(f"⚠️ Detection on {url}: {detection.value}")
                    
                    if attempt < max_retries:
                        # Rotate proxy and retry with new UA
                        self._rotate_proxy()
                        user_agent = get_user_agent_for_site(url, force_new=True)
                        backoff = min(self.config.base_backoff * (2 ** attempt), self.config.max_backoff)
                        logger.info(f"⏳ Retrying in {backoff}s...")
                        time.sleep(backoff)
                        continue
                    else:
                        return False, html, detection
                
                # Success
                self.session_metrics.successful_requests += 1
                self.session_metrics.browser_requests += 1
                report_ua_success(user_agent, url)
                
                # Add realistic delays with human behavior patterns
                self._add_realistic_delays()
                
                return True, html, None
                
            except TimeoutException:
                logger.warning(f"⏰ Timeout on {url} (attempt {attempt + 1})")
                report_ua_failure(user_agent, url)
                if attempt < max_retries:
                    self._rotate_proxy()
                    user_agent = get_user_agent_for_site(url, force_new=True)
                    time.sleep(self.config.base_backoff * (2 ** attempt))
                    continue
                else:
                    self.session_metrics.add_detection(DetectionType.TIMEOUT)
                    return False, "", DetectionType.TIMEOUT
                
            except Exception as e:
                logger.error(f"❌ Error on {url}: {e}")
                report_ua_failure(user_agent, url)
                if attempt < max_retries:
                    self._rotate_proxy()
                    user_agent = get_user_agent_for_site(url, force_new=True)
                    time.sleep(self.config.base_backoff * (2 ** attempt))
                    continue
                else:
                    self.session_metrics.failed_requests += 1
                    return False, "", DetectionType.UNKNOWN
        
        return False, "", DetectionType.UNKNOWN
    
    def get_html(self, url: str, session_id: str = None) -> str:
        """Get HTML content with HTTP-first strategy and granular retry logic."""
        if self.config.force_browser:
            # Force browser mode
            success, html, detection = self._safe_request(url)
            if not success:
                raise Exception(f"Failed to get {url}: {detection.value if detection else 'Unknown error'}")
            return html
        
        # HTTP-first strategy with granular retry
        max_http_retries = 2  # Try HTTP twice before escalating to browser
        
        for attempt in range(max_http_retries):
            try:
                html = self._try_http_request(url, session_id)
                if html:
                    return html
            except Exception as e:
                if self.config.verbose:
                    logger.info(f"🌐 HTTP attempt {attempt + 1} failed for {url}: {e}")
            
            if attempt < max_http_retries - 1:
                # Swap proxy and retry HTTP
                if self.config.verbose:
                    logger.info(f"🔄 HTTP attempt {attempt + 1} failed, swapping proxy and retrying...")
                self.proxy_rotator._rotate_proxy()
        
        # Fallback to browser if all HTTP attempts fail
        if self.config.verbose:
            logger.info(f"🌐 All HTTP attempts failed for {url}")
            logger.info(f"🔄 Escalating to browser for {url}")
        
        try:
            success, html, detection = self._safe_request(url)
            if not success:
                if self.config.verbose:
                    logger.warning(f"⚠️ Browser also failed for {url}: {detection.value if detection else 'Unknown error'}")
                # Don't crash, return empty string to allow graceful handling
                return ""
            return html
        except Exception as e:
            if self.config.verbose:
                logger.error(f"❌ Browser request failed for {url}: {e}")
            # Don't crash, return empty string to allow graceful handling
            return ""
    
    def _try_http_request(self, url: str, session_id: str = None) -> Optional[str]:
        """Try HTTP request first with proxy rotation and User-Agent management."""
        try:
            from .proxy_manager import make_proxy_request, is_blocked
        except ImportError:
            import sys
            import os
            # Get the absolute path to the scrapers directory
            current_file = os.path.abspath(__file__)
            scrapers_dir = os.path.dirname(current_file)
            if scrapers_dir not in sys.path:
                sys.path.insert(0, scrapers_dir)
            from proxy_manager import make_proxy_request, is_blocked
        
        try:
            from .user_agent_manager import report_ua_success, report_ua_failure, get_user_agent_for_site
        except ImportError:
            import sys
            import os
            # Get the absolute path to the scrapers directory
            current_file = os.path.abspath(__file__)
            scrapers_dir = os.path.dirname(current_file)
            if scrapers_dir not in sys.path:
                sys.path.insert(0, scrapers_dir)
            from user_agent_manager import report_ua_success, report_ua_failure, get_user_agent_for_site
        
        start_time = time.time()
        
        # Get proxy with session support (use existing rotator)
        try:
            proxy_url = self.proxy_rotator.get_proxy(session_id=session_id)
        except TypeError:
            # Fallback for older proxy rotator versions
            proxy_url = self.proxy_rotator.get_proxy()
        
        # Get site-specific User-Agent
        user_agent = get_user_agent_for_site(url)
        
        try:
            response = make_proxy_request(url, timeout=15)
            if not response:
                report_ua_failure(user_agent, url)
                return None
            
            latency = time.time() - start_time
            
            # Check if blocked
            if is_blocked(response):
                self.proxy_rotator.report_blocked()
                report_ua_failure(user_agent, url)
                return None
            
            # Check if content is sufficient
            html = response.text
            if len(html) < self.config.min_page_size:
                if self.config.verbose:
                    logger.info(f"📄 Insufficient content from HTTP ({len(html)} chars)")
                report_ua_failure(user_agent, url)
                return None
            
            # Report success with latency
            self.proxy_rotator.report_success(latency=latency)
            report_ua_success(user_agent, url)
            self.session_metrics.http_requests += 1
            
            if self.config.verbose:
                logger.info(f"✅ HTTP request successful ({len(html)} chars, {latency:.2f}s)")
            
            # Add realistic delays for HTTP requests too
            self._add_realistic_delays()
            
            return html
            
        except Exception as e:
            if self.config.verbose:
                logger.warning(f"⚠️ HTTP request failed: {e}")
            self.proxy_rotator.report_failure()
            report_ua_failure(user_agent, url)
            return None
    
    def __enter__(self):
        """Context manager entry."""
        self.current_proxy = self.proxy_rotator.get_proxy()
        self.current_driver = self._create_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.current_driver:
            self.current_driver.quit()
        
        # Update session metrics
        self.session_metrics.total_duration = (datetime.now() - self.session_metrics.start_time).total_seconds()
        
        # Log summary
        self._log_session_summary()
    
    def _log_session_summary(self):
        """Log session summary."""
        summary = self.session_metrics.get_summary()
        
        logger.info("📊 Session Summary:")
        logger.info(f"   Duration: {summary['duration']:.1f}s")
        logger.info(f"   Requests: {summary['total_requests']} (Success: {summary['successful_requests']}, Failed: {summary['failed_requests']})")
        logger.info(f"   HTTP Requests: {summary['http_requests']}")
        logger.info(f"   Browser Requests: {summary['browser_requests']}")
        logger.info(f"   Success Rate: {summary['success_rate']:.1f}%")
        logger.info(f"   Proxy Rotations: {summary['proxy_rotations']}")
        logger.info(f"   Pool Promotions: {summary['pool_promotions']}")
        logger.info(f"   Pool Demotions: {summary['pool_demotions']}")
        logger.info(f"   Sticky Sessions: {summary['sticky_sessions']}")
        logger.info(f"   Detections: {summary['detections']}")
        logger.info(f"   Leagues Scraped: {summary['leagues_scraped']}")
        
        # Log proxy performance if available
        if summary['avg_latency_per_proxy']:
            logger.info(f"   Avg Latency per Proxy: {summary['avg_latency_per_proxy']}")
        if summary['proxy_success_rates']:
            logger.info(f"   Proxy Success Rates: {summary['proxy_success_rates']}")
        
        # Send summary SMS at end of session
        self._send_session_summary_sms(summary)
    
    def _send_session_summary_sms(self, summary):
        """Send a summary SMS at the end of the scraping session."""
        try:
            # Get proxy health status from the proxy rotator
            if hasattr(self, 'proxy_rotator') and self.proxy_rotator:
                proxy_stats = self.proxy_rotator.get_session_stats()
                
                # Create summary message
                message = (
                    f"Rally Scraping Session Complete\n"
                    f"Duration: {summary['duration']:.1f}s\n"
                    f"Success Rate: {summary['success_rate']:.1f}%\n"
                    f"Total Requests: {summary['total_requests']}\n"
                    f"Proxy Rotations: {summary['proxy_rotations']}\n"
                    f"Healthy Proxies: {proxy_stats.get('healthy_proxies', 'N/A')}\n"
                    f"Blocked Proxies: {proxy_stats.get('blocked_proxies', 'N/A')}\n"
                    f"Leagues: {', '.join(summary['leagues_scraped']) if summary['leagues_scraped'] else 'None'}"
                )
                
                # Send SMS using the proxy manager's SMS function
                try:
                    from .proxy_manager import send_urgent_sms
                    if send_urgent_sms(message):
                        logger.info("📱 Session summary SMS sent successfully")
                    else:
                        logger.warning("⚠️ Failed to send session summary SMS")
                except ImportError:
                    logger.debug("📱 SMS not available - skipping session summary")
                    
        except Exception as e:
            logger.debug(f"📱 Session summary SMS failed: {e}")
    
    def _simulate_human_behavior(self, driver):
        """Simulate realistic human browsing behavior to avoid detection."""
        if not driver or self.config.headless:
            return  # Skip in headless mode
        
        try:
            # Random scroll patterns (like a human reading the page)
            scroll_amount = random.randint(100, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 2.0))
            
            # Sometimes scroll back up
            if random.random() < 0.3:
                driver.execute_script(f"window.scrollBy(0, -{scroll_amount//2});")
                time.sleep(random.uniform(0.3, 1.5))
            
            # Random mouse movements (if not headless)
            if not self.config.headless:
                # Simulate mouse hover over random elements
                try:
                    elements = driver.find_elements(By.TAG_NAME, "a")[:5]  # First 5 links
                    if elements:
                        random_element = random.choice(elements)
                        # Use ActionChains for realistic mouse movement
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_to_element(random_element).perform()
                        time.sleep(random.uniform(0.2, 0.8))
                except Exception:
                    pass  # Ignore if mouse simulation fails
            
            # Random page interaction delays
            interaction_delay = random.uniform(0.5, 1.5)
            time.sleep(interaction_delay)
            
            # Sometimes move mouse to random position
            if random.random() < 0.4 and not self.config.headless:
                try:
                    driver.execute_script("""
                        var event = new MouseEvent('mousemove', {
                            'view': window,
                            'bubbles': true,
                            'cancelable': true,
                            'clientX': arguments[0],
                            'clientY': arguments[1]
                        });
                        document.dispatchEvent(event);
                    """, random.randint(100, 800), random.randint(100, 600))
                except Exception:
                    pass
            
            if self.config.verbose:
                logger.debug(f"🎭 Simulated human behavior: scroll={scroll_amount}, delay={interaction_delay:.1f}s")
                
        except Exception as e:
            if self.config.verbose:
                logger.debug(f"⚠️ Human behavior simulation failed: {e}")
    
    def _add_realistic_delays(self):
        """Add realistic delays between requests to mimic human browsing."""
        # Base delay from config
        base_delay = random.uniform(self.config.min_delay, self.config.max_delay)
        
        # Add jitter for natural variation
        jitter = random.uniform(-0.5, 1.0)  # ±0.5s to +1s variation
        
        # Add time-of-day scaling (slower during business hours)
        hour = datetime.now().hour
        if 9 <= hour <= 17:  # Business hours
            business_multiplier = random.uniform(1.2, 1.8)
            base_delay *= business_multiplier
        
        # Add weekend behavior (slightly slower)
        if datetime.now().weekday() >= 5:  # Weekend
            weekend_multiplier = random.uniform(1.1, 1.4)
            base_delay *= weekend_multiplier
        
        # Ensure minimum delay
        final_delay = max(0.1, base_delay + jitter)
        
        if self.config.verbose:
            logger.debug(f"⏱️ Realistic delay: {final_delay:.1f}s (base: {base_delay:.1f}s, jitter: {jitter:.1f}s)")
        
        time.sleep(final_delay)
        return final_delay

# Convenience function
def detect_environment():
    """Auto-detect the current environment."""
    # Check for Railway environment variables
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return os.getenv("RAILWAY_ENVIRONMENT")
    
    # Check for common production indicators
    if os.getenv("DATABASE_URL") and "railway" in os.getenv("DATABASE_URL", "").lower():
        return "production"
    
    # Check for staging indicators
    if os.getenv("STAGING") or os.getenv("RAILWAY_STAGING"):
        return "staging"
    
    # Check if we're running locally (default)
    if os.path.exists("database_config.py"):
        return "local"
    
    # Fallback to local
    return "local"

def run_preflight_check():
    """Run preflight checks for Chrome/ChromeDriver compatibility and proxy health."""
    logger.info("🔍 Running preflight checks...")
    
    # Check Chrome version
    chrome_version = get_installed_chrome_version()
    logger.info(f"✅ Chrome version: {chrome_version}")
    
    # Test ChromeDriver compatibility
    try:
        test_config = StealthConfig(fast_mode=True, verbose=False)
        test_browser = EnhancedStealthBrowser(test_config)
        test_driver = test_browser._create_driver()
        test_driver.quit()
        logger.info("✅ ChromeDriver compatibility: PASSED")
    except Exception as e:
        logger.warning(f"⚠️ ChromeDriver compatibility: FAILED - {e}")
    
    # Test proxy health
    try:
        try:
            from .proxy_manager import make_proxy_request
        except ImportError:
            import sys
            import os
            # Get the absolute path to the scrapers directory
            current_file = os.path.abspath(__file__)
            scrapers_dir = os.path.dirname(current_file)
            if scrapers_dir not in sys.path:
                sys.path.insert(0, scrapers_dir)
            from proxy_manager import make_proxy_request
        test_response = make_proxy_request("https://nstf.tenniscores.com", timeout=10)
        if test_response:
            logger.info("✅ Proxy health test: PASSED")
        else:
            logger.warning("⚠️ Proxy health test: FAILED")
    except Exception as e:
        logger.warning(f"⚠️ Proxy health test: FAILED - {e}")
    
    # Log proxy pool status
    try:
        proxy_rotator = get_proxy_rotator(sticky=False)
        status = proxy_rotator.get_status()
        logger.info(f"📊 Proxy pool status:")
        logger.info(f"   - Total proxies: {status['total_proxies']}")
        logger.info(f"   - Healthy proxies: {status['healthy_proxies']}")
        logger.info(f"   - Trusted pool: {status['pool_stats']['trusted_pool_size']}")
        logger.info(f"   - Rotating pool: {status['pool_stats']['rotating_pool_size']}")
    except Exception as e:
        logger.warning(f"⚠️ Could not get proxy pool status: {e}")
    
    logger.info("✅ Preflight checks completed")

def create_stealth_browser(fast_mode: bool = False, verbose: bool = False, environment: str = None, force_browser: bool = False) -> EnhancedStealthBrowser:
    """Create an enhanced stealth browser instance."""
    if environment is None:
        environment = detect_environment()
    config = StealthConfig(fast_mode=fast_mode, verbose=verbose, environment=environment, force_browser=force_browser)
    return EnhancedStealthBrowser(config)
