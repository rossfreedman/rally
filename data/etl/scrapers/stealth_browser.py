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

# Import the proxy manager
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
            "leagues_scraped": self.leagues_scraped
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
                 environment: str = "production"):
        self.fast_mode = fast_mode
        self.verbose = verbose
        self.environment = environment
        
        # Request pacing
        self.min_delay = 1.0 if fast_mode else 2.0
        self.max_delay = 3.0 if fast_mode else 6.0
        
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
    
    def _create_driver(self) -> webdriver.Chrome:
        """Create a new Chrome driver with stealth settings."""
        options = uc.ChromeOptions()
        
        # Basic stealth settings
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        
        # Set window size
        options.add_argument(f"--window-size={self.config.window_width},{self.config.window_height}")
        
        # Set user agent
        user_agent = UserAgentManager.get_random_user_agent()
        options.add_argument(f"--user-agent={user_agent}")
        
        # Headless mode
        if self.config.headless:
            options.add_argument("--headless")
        
        # Configure Selenium Wire for proxy
        if SELENIUM_WIRE_AVAILABLE:
            seleniumwire_options = {
                'proxy': {
                    'http': self.current_proxy,
                    'https': self.current_proxy
                },
                'verify_ssl': False
            }
            driver = webdriver.Chrome(options=options, seleniumwire_options=seleniumwire_options)
        else:
            driver = uc.Chrome(options=options)
        
        # Inject stealth scripts
        self._inject_stealth_scripts(driver)
        
        return driver
    
    def _inject_stealth_scripts(self, driver: webdriver.Chrome):
        """Inject JavaScript to hide automation indicators."""
        stealth_scripts = [
            # Remove webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
            
            # Override permissions
            "const originalQuery = window.navigator.permissions.query; window.navigator.permissions.query = (parameters) => (parameters.name === 'notifications' ? Promise.resolve({state: Notification.permission}) : originalQuery(parameters));",
            
            # Override plugins
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});",
            
            # Override languages
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});",
            
            # Override chrome
            "window.chrome = {runtime: {}};"
        ]
        
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
        
        # Check for CAPTCHA indicators
        captcha_indicators = [
            "captcha", "robot", "bot check", "verify you are human",
            "cloudflare", "access denied", "blocked"
        ]
        
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
                    logger.warning(f"⚠️ Detection on {url}: {detection.value}")
                    
                    if attempt < max_retries:
                        # Rotate proxy and retry
                        self._rotate_proxy()
                        backoff = min(self.config.base_backoff * (2 ** attempt), self.config.max_backoff)
                        logger.info(f"⏳ Retrying in {backoff}s...")
                        time.sleep(backoff)
                        continue
                    else:
                        return False, html, detection
                
                # Success
                self.session_metrics.successful_requests += 1
                return True, html, None
                
            except TimeoutException:
                logger.warning(f"⏰ Timeout on {url} (attempt {attempt + 1})")
                if attempt < max_retries:
                    self._rotate_proxy()
                    time.sleep(self.config.base_backoff * (2 ** attempt))
                    continue
                else:
                    self.session_metrics.add_detection(DetectionType.TIMEOUT)
                    return False, "", DetectionType.TIMEOUT
                    
            except Exception as e:
                logger.error(f"❌ Error on {url}: {e}")
                if attempt < max_retries:
                    self._rotate_proxy()
                    time.sleep(self.config.base_backoff * (2 ** attempt))
                    continue
                else:
                    self.session_metrics.failed_requests += 1
                    return False, "", DetectionType.UNKNOWN
        
        return False, "", DetectionType.UNKNOWN
    
    def get_html(self, url: str) -> str:
        """Get HTML content with stealth measures."""
        success, html, detection = self._safe_request(url)
        
        if not success:
            raise Exception(f"Failed to get {url}: {detection.value if detection else 'Unknown error'}")
        
        # Add random delay
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        time.sleep(delay)
        
        return html
    
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
        logger.info(f"   Success Rate: {summary['success_rate']:.1f}%")
        logger.info(f"   Proxy Rotations: {summary['proxy_rotations']}")
        logger.info(f"   Detections: {summary['detections']}")
        logger.info(f"   Leagues Scraped: {summary['leagues_scraped']}")

# Convenience function
def create_stealth_browser(fast_mode: bool = False, verbose: bool = False, environment: str = "production") -> EnhancedStealthBrowser:
    """Create an enhanced stealth browser instance."""
    config = StealthConfig(fast_mode=fast_mode, verbose=verbose, environment=environment)
    return EnhancedStealthBrowser(config)
