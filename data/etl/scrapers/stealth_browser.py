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
                 force_browser: bool = False):
        self.fast_mode = fast_mode
        self.verbose = verbose
        self.environment = environment
        self.force_browser = force_browser
        
        # Environment-specific defaults
        if environment == "local":
            self.min_delay = 1.0 if fast_mode else 1.5
            self.max_delay = 3.0 if fast_mode else 4.0
        elif environment == "staging":
            self.min_delay = 1.5 if fast_mode else 2.5
            self.max_delay = 4.0 if fast_mode else 6.0
        else:  # production
            self.min_delay = 2.0 if fast_mode else 3.0
            self.max_delay = 5.0 if fast_mode else 8.0
        
        # Retry settings
        self.max_retries = 3
        self.base_backoff = 1.0
        self.max_backoff = 10.0
        
        # Proxy settings
        self.requests_per_proxy = 30
        self.session_duration = 600  # 10 minutes
        
        # Detection thresholds
        self.min_page_size = 1000
        self.timeout_seconds = 30
        
        # Browser settings
        self.headless = True
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
    
    def _create_driver(self):
        """Create a new Chrome driver with stealth settings and OS signal leak prevention."""
        # Get a random user agent for this driver
        user_agent = UserAgentManager.get_random_user_agent()
        
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
        
        # Inject stealth scripts with OS-specific overrides
        self._inject_stealth_scripts(driver, user_agent)
        
        return driver
    
    def _create_fresh_options(self, user_agent: str):
        """Create fresh ChromeOptions for each strategy attempt."""
        options = uc.ChromeOptions()
        
        # Basic stealth settings - less restrictive
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        # Don't disable JavaScript - it's needed for most sites
        # options.add_argument("--disable-javascript")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Avoid OS signal leaks - force Windows platform for APTA
        if hasattr(self, 'current_url') and "apta.tenniscores.com" in self.current_url:
            options.add_argument("--platform=Windows")
            options.add_argument("--window-size=1920,1080")
            # Use Windows User-Agent from UA manager
            try:
                from .user_agent_manager import get_user_agent_for_site
            except ImportError:
                import sys
                import os
                current_dir = os.path.dirname(__file__)
                parent_dir = os.path.dirname(current_dir)
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                # Get the absolute path to the scrapers directory
                current_file = os.path.abspath(__file__)
                scrapers_dir = os.path.dirname(current_file)
                if scrapers_dir not in sys.path:
                    sys.path.insert(0, scrapers_dir)
                from user_agent_manager import get_user_agent_for_site
            user_agent = get_user_agent_for_site(self.current_url)
        else:
            # Set window size
            options.add_argument(f"--window-size={self.config.window_width},{self.config.window_height}")
            # Use default User-Agent
            user_agent = UserAgentManager.get_random_user_agent()
        
        options.add_argument(f"--user-agent={user_agent}")
        
        # Headless mode
        if self.config.headless:
            options.add_argument("--headless")
        
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
        stealth_scripts = [
            # Remove webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
            
            # Override permissions
            "const originalQuery = window.navigator.permissions.query; window.navigator.permissions.query = (parameters) => (parameters.name === 'notifications' ? Promise.resolve({state: Notification.permission}) : originalQuery(parameters));",
            
            # Override plugins with realistic plugin array
            "Object.defineProperty(navigator, 'plugins', {get: () => [{name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'}, {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''}, {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''}]});",
            
            # Override languages
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});",
            
            # Override chrome runtime
            "window.chrome = {runtime: {}};",
            
            # Override connection properties
            "Object.defineProperty(navigator, 'connection', {get: () => ({effectiveType: '4g', rtt: 50, downlink: 10, saveData: false})});",
            
            # Override battery API
            "Object.defineProperty(navigator, 'getBattery', {get: () => () => Promise.resolve({charging: true, chargingTime: 0, dischargingTime: Infinity, level: 0.85})});",
            
            # Override media devices
            "Object.defineProperty(navigator, 'mediaDevices', {get: () => ({enumerateDevices: () => Promise.resolve([])})});",
            
            # Override geolocation
            "Object.defineProperty(navigator, 'geolocation', {get: () => ({getCurrentPosition: () => {}, watchPosition: () => {}})});",
            
            # Override service worker
            "Object.defineProperty(navigator, 'serviceWorker', {get: () => ({register: () => Promise.resolve(), getRegistrations: () => Promise.resolve([])})});",
            
            # Override storage
            "Object.defineProperty(navigator, 'storage', {get: () => ({estimate: () => Promise.resolve({usage: 0, quota: 0})})});",
            
            # Override wake lock
            "Object.defineProperty(navigator, 'wakeLock', {get: () => ({request: () => Promise.resolve()})});",
            
            # Override clipboard
            "Object.defineProperty(navigator, 'clipboard', {get: () => ({readText: () => Promise.resolve(''), writeText: () => Promise.resolve()})});",
            
            # Override presentation
            "Object.defineProperty(navigator, 'presentation', {get: () => ({defaultRequest: null, receiver: null})});",
            
            # Override credentials
            "Object.defineProperty(navigator, 'credentials', {get: () => ({create: () => Promise.resolve(), get: () => Promise.resolve(), preventSilentAccess: () => {}})});",
            
            # Override locks
            "Object.defineProperty(navigator, 'locks', {get: () => ({request: () => Promise.resolve(), query: () => Promise.resolve([])})});",
            
            # Override contacts
            "Object.defineProperty(navigator, 'contacts', {get: () => ({select: () => Promise.resolve([])})});",
            
            # Override keyboard
            "Object.defineProperty(navigator, 'keyboard', {get: () => ({lock: () => Promise.resolve(), unlock: () => {}})});",
            
            # Override virtual keyboard
            "Object.defineProperty(navigator, 'virtualKeyboard', {get: () => ({show: () => {}, hide: () => {}})});",
            
            # Override xr
            "Object.defineProperty(navigator, 'xr', {get: () => ({isSessionSupported: () => Promise.resolve(false)})});",
            
            # Override bluetooth
            "Object.defineProperty(navigator, 'bluetooth', {get: () => ({requestDevice: () => Promise.resolve()})});",
            
            # Override usb
            "Object.defineProperty(navigator, 'usb', {get: () => ({requestDevice: () => Promise.resolve()})});",
            
            # Override serial
            "Object.defineProperty(navigator, 'serial', {get: () => ({requestPort: () => Promise.resolve()})});",
            
            # Override hid
            "Object.defineProperty(navigator, 'hid', {get: () => ({requestDevice: () => Promise.resolve()})});",
            
            # Override gamepad
            "Object.defineProperty(navigator, 'gamepad', {get: () => ({getGamepads: () => []})});",
            
            # Override taintEnabled (legacy)
            "Object.defineProperty(navigator, 'taintEnabled', {get: () => false});",
            
            # Override cookieEnabled
            "Object.defineProperty(navigator, 'cookieEnabled', {get: () => true});",
            
            # Override onLine
            "Object.defineProperty(navigator, 'onLine', {get: () => true});",
            
            # Override doNotTrack
            "Object.defineProperty(navigator, 'doNotTrack', {get: () => null});",
            
            # Override maxTouchPoints
            "Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});",
            
            # Override hardwareConcurrency (default)
            "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});",
            
            # Override deviceMemory (default)
            "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});",
            
            # Override platform (default)
            "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});",
            
            # Override vendor
            "Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});",
            
            # Override product
            "Object.defineProperty(navigator, 'product', {get: () => 'Gecko'});",
            
            # Override appName
            "Object.defineProperty(navigator, 'appName', {get: () => 'Netscape'});",
            
            # Override appVersion
            "Object.defineProperty(navigator, 'appVersion', {get: () => '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'});",
            
            # Override userAgent
            "Object.defineProperty(navigator, 'userAgent', {get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'});",
            
            # Override screen properties
            "Object.defineProperty(screen, 'width', {get: () => 1920});",
            "Object.defineProperty(screen, 'height', {get: () => 1080});",
            "Object.defineProperty(screen, 'availWidth', {get: () => 1920});",
            "Object.defineProperty(screen, 'availHeight', {get: () => 1040});",
            "Object.defineProperty(screen, 'colorDepth', {get: () => 24});",
            "Object.defineProperty(screen, 'pixelDepth', {get: () => 24});",
            
            # Override window properties
            "Object.defineProperty(window, 'outerWidth', {get: () => 1920});",
            "Object.defineProperty(window, 'outerHeight', {get: () => 1040});",
            "Object.defineProperty(window, 'innerWidth', {get: () => 1920});",
            "Object.defineProperty(window, 'innerHeight', {get: () => 937});",
            
            # Override device pixel ratio
            "Object.defineProperty(window, 'devicePixelRatio', {get: () => 1});",
            
            # Override timezone
            "Object.defineProperty(Intl, 'DateTimeFormat', {get: () => function() { return {resolvedOptions: () => ({timeZone: 'America/New_York'})} }});",
            
            # Override canvas fingerprinting
            "const originalGetContext = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function(type) { if (type === '2d') { const context = originalGetContext.call(this, type); const originalFillText = context.fillText; context.fillText = function() { return originalFillText.apply(this, arguments); }; } return originalGetContext.call(this, type); };",
            
            # Override WebGL fingerprinting
            "const getParameter = WebGLRenderingContext.prototype.getParameter; WebGLRenderingContext.prototype.getParameter = function(parameter) { if (parameter === 37445) { return 'Intel Inc.'; } if (parameter === 37446) { return 'Intel(R) Iris(TM) Graphics 6100'; } return getParameter.call(this, parameter); };",
            
            # Override audio fingerprinting
            "const originalGetChannelData = AudioBuffer.prototype.getChannelData; AudioBuffer.prototype.getChannelData = function() { const channelData = originalGetChannelData.call(this); const originalSet = channelData.set; channelData.set = function() { return originalSet.apply(this, arguments); }; return channelData; };",
            
            # Override font fingerprinting
            "Object.defineProperty(document, 'fonts', {get: () => ({ready: Promise.resolve(), check: () => true, load: () => Promise.resolve([])})});",
            
            # Override performance timing
            "Object.defineProperty(performance, 'timing', {get: () => ({navigationStart: Date.now() - Math.random() * 1000, loadEventEnd: Date.now(), domContentLoadedEventEnd: Date.now() - Math.random() * 100})});",
            
            # Override memory info
            "Object.defineProperty(performance, 'memory', {get: () => ({usedJSHeapSize: 10000000, totalJSHeapSize: 20000000, jsHeapSizeLimit: 2147483648})});",
            
            # Override network info
            "Object.defineProperty(navigator, 'connection', {get: () => ({effectiveType: '4g', rtt: 50, downlink: 10, saveData: false, type: 'wifi'})});",
        ]
        
        # Add OS-specific overrides for APTA
        if user_agent and "Windows" in user_agent:
            os_override_scripts = [
                # Override platform to Windows
                "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});",
                
                # Override userAgent to match the selected Windows UA
                f"Object.defineProperty(navigator, 'userAgent', {{get: () => '{user_agent}'}});",
                
                # Override appVersion to match Windows
                f"Object.defineProperty(navigator, 'appVersion', {{get: () => '{user_agent.split(' ')[-1]}'}});",
                
                # Override vendor to match Windows
                "Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});",
                
                # Override product to match Windows
                "Object.defineProperty(navigator, 'product', {get: () => 'Gecko'});",
                
                # Override hardwareConcurrency to realistic Windows value
                "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});",
                
                # Override deviceMemory to realistic Windows value
                "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});"
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
            response = make_proxy_request(url, timeout=30)
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
            interaction_delay = random.uniform(1.0, 3.0)
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
