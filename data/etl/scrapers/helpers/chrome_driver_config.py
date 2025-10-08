#!/usr/bin/env python3
"""
Chrome Driver Configuration for Rally Scrapers
==============================================

Enhanced Chrome driver configuration with stealth settings, viewport control,
and language settings for consistent browser fingerprinting.

Key Features:
- Viewport and window size control
- Language and locale settings
- Stealth and anti-detection options
- Proxy and network configuration
- Mobile User-Agent optimization for lighter markup
- Enhanced CDP blocking for bandwidth optimization
"""

import undetected_chromedriver as uc
from typing import Optional, Tuple
import shutil

# Chrome version detection
CHROME_VERSION_DETECTION = True

# ChromeDriver paths to try
CHROMEDRIVER_PATHS = [
    "/usr/local/bin/chromedriver",
    "/usr/bin/chromedriver", 
    "/opt/chromedriver/chromedriver",
    "/Users/rossfreedman/Library/Application Support/undetected_chromedriver/undetected_chromedriver"
]

# Fallback options
USE_WEBDRIVER_MANAGER = True
USE_UNDETECTED_CHROMEDRIVER = True

# Mobile User-Agent for lighter markup (Chrome on Android)
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.6312.86 Mobile Safari/537.36"
)

# Enhanced blocking patterns for bandwidth optimization
ENHANCED_BLOCK_PATTERNS = [
    # Heavy assets by extension
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.svg",
    "*.mp4", "*.webm", "*.mov", "*.avi", "*.m4v",
    "*.woff", "*.woff2", "*.ttf", "*.otf",
    "*.css.map", "*.js.map", "*.ico",
    
    # Analytics / pixels / beacons
    "*googletagmanager*", "*google-analytics*", "*doubleclick*", "*googleoptimize*",
    "*stats.g.doubleclick*", "*analytics.google*", "*clarity.ms*", "*mixpanel*",
    "*hotjar*", "*segment.io*", "*fullstory*", "*amplitude*", "*newrelic*",
    
    # Third-party CDNs you likely don't need for HTML
    "*cdn.jsdelivr.net*", "*cdnjs.cloudflare.com*", "*unpkg.com*", "*static.chartbeat*",
    "*snap.licdn.com*", "*bat.bing.com*", "*facebook.com/tr*", "*connect.facebook.net*",
    "*gstatic.com/recaptcha*", "*recaptcha.net*", "*googleapis.com*", "*gstatic.com/*"
]

# Chrome options for compatibility
CHROME_OPTIONS = [
    "--no-sandbox",
    "--disable-dev-shm-usage", 
    "--disable-gpu",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-web-security",
    "--allow-running-insecure-content"
]

# Headless mode options
HEADLESS_OPTIONS = [
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage"
]

def build_chrome_options(user_agent: str = None, 
                        lang: str = "en-US", 
                        viewport: Optional[Tuple[int, int]] = None,
                        headless: bool = True,
                        proxy: str = None) -> uc.ChromeOptions:
    """
    Build Chrome options with stealth settings, viewport, and language configuration.
    
    Args:
        user_agent: Custom User-Agent string
        lang: Language setting (e.g., "en-US")
        viewport: Tuple of (width, height) for window size
        headless: Whether to run in headless mode
        proxy: Proxy URL if needed
        
    Returns:
        uc.ChromeOptions: Configured Chrome options
    """
    options = uc.ChromeOptions()
    
    # Basic compatibility options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    
    # Speed optimizations: eager loading strategy (guarded by feature flag)
    try:
        from .settings_stealth import ENABLE_SPEED_OPTIMIZATIONS
    except ImportError:
        try:
            from settings_stealth import ENABLE_SPEED_OPTIMIZATIONS
        except ImportError:
            ENABLE_SPEED_OPTIMIZATIONS = True  # Default to enabled for backward compatibility
    
    if ENABLE_SPEED_OPTIMIZATIONS:
        try:
            options.page_load_strategy = 'eager'  # DOMContentLoaded only
        except Exception:
            pass  # Fallback to default if unsupported
    
    # Stealth and anti-detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-safebrowsing")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--disable-background-networking")
    
    # Language settings
    if lang:
        options.add_argument(f"--lang={lang}")
        options.add_argument(f"--accept-lang={lang}")
    
    # Viewport settings
    if viewport and isinstance(viewport, tuple) and len(viewport) == 2:
        w, h = viewport
        options.add_argument(f"--window-size={w},{h}")
        # Also set the viewport size for consistency
        options.add_argument(f"--force-device-scale-factor=1")
    
    # User-Agent
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")
    
    # Headless mode
    if headless:
        options.add_argument("--headless")
    
    # Proxy configuration
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    
    # Hide automation indicators
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Preferences (base settings always applied)
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.media_stream": 2,
        # Language preferences
        "intl.accept_languages": lang if lang else "en-US,en",
        "spellcheck.dictionary": lang.split('-')[0] if lang else "en",
    }
    
    # Add image blocking only if speed optimizations are enabled
    if ENABLE_SPEED_OPTIMIZATIONS:
        try:
            prefs["profile.managed_default_content_settings.images"] = 2
        except Exception:
            pass
    
    # Add experimental options
    try:
        options.add_experimental_option("prefs", prefs)
    except Exception:
        pass
    
    return options

def build_mobile_lean_driver(user_agent: str = None, 
                           lang: str = "en-US", 
                           viewport: Optional[Tuple[int, int]] = None,
                           headless: bool = True,
                           proxy: str = None) -> uc.ChromeOptions:
    """
    Build mobile-optimized Chrome options for maximum bandwidth efficiency.
    
    Args:
        user_agent: Custom User-Agent string (defaults to mobile UA)
        lang: Language setting (e.g., "en-US")
        viewport: Tuple of (width, height) for mobile viewport
        headless: Whether to run in headless mode
        proxy: Proxy URL if needed
        
    Returns:
        uc.ChromeOptions: Mobile-optimized Chrome options
    """
    options = uc.ChromeOptions()
    
    # Use mobile UA by default for lighter markup
    if not user_agent:
        user_agent = MOBILE_UA
    
    # Basic compatibility options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    
    # Mobile optimization flags
    options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images at engine level
    options.add_argument(f"--user-agent={user_agent}")  # Set mobile UA
    
    # Network optimization
    options.add_argument("--disable-features=NetworkServiceInProcess")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Speed optimizations: eager loading strategy
    try:
        from .settings_stealth import ENABLE_SPEED_OPTIMIZATIONS
    except ImportError:
        try:
            from settings_stealth import ENABLE_SPEED_OPTIMIZATIONS
        except ImportError:
            ENABLE_SPEED_OPTIMIZATIONS = True
    
    if ENABLE_SPEED_OPTIMIZATIONS:
        try:
            options.page_load_strategy = 'eager'  # DOMContentLoaded only
        except Exception:
            pass
    
    # Stealth and anti-detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-safebrowsing")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-domain-reliability")
    options.add_argument("--disable-component-extensions-with-background-pages")
    
    # Language settings
    if lang:
        options.add_argument(f"--lang={lang}")
        options.add_argument(f"--accept-lang={lang}")
    
    # Mobile viewport settings (default to mobile if not specified)
    if viewport and isinstance(viewport, tuple) and len(viewport) == 2:
        w, h = viewport
        options.add_argument(f"--window-size={w},{h}")
    else:
        # Default mobile viewport
        options.add_argument("--window-size=412,915")
        options.add_argument("--force-device-scale-factor=2.625")
    
    # Headless mode
    if headless:
        options.add_argument("--headless")
    
    # Proxy configuration
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    
    # Hide automation indicators
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Mobile-optimized preferences
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.media_stream": 2,
        # Disable images for bandwidth savings
        "profile.managed_default_content_settings.images": 2,
        # Language preferences
        "intl.accept_languages": lang if lang else "en-US,en",
        "spellcheck.dictionary": lang.split('-')[0] if lang else "en",
        # Mobile-specific optimizations
        "profile.default_content_setting_values.plugins": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.camera": 2,
        "profile.default_content_setting_values.microphone": 2,
    }
    
    # Add experimental options
    try:
        options.add_experimental_option("prefs", prefs)
    except Exception:
        pass
    
    return options

def enable_mobile_cdp_optimization(driver):
    """
    Enable mobile-optimized CDP commands for maximum bandwidth efficiency.
    """
    try:
        from .settings_stealth import ENABLE_SPEED_OPTIMIZATIONS
    except ImportError:
        try:
            from settings_stealth import ENABLE_SPEED_OPTIMIZATIONS
        except ImportError:
            ENABLE_SPEED_OPTIMIZATIONS = True
    
    if not ENABLE_SPEED_OPTIMIZATIONS:
        return
        
    try:
        # Enable network domain
        driver.execute_cdp_cmd("Network.enable", {})
        
        # Block heavy resources with enhanced patterns
        driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": ENHANCED_BLOCK_PATTERNS})
        
        # Set mobile device metrics
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 412, 
            "height": 915, 
            "deviceScaleFactor": 2.625, 
            "mobile": True
        })
        
        # Set mobile User-Agent metadata
        driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {
            "userAgent": MOBILE_UA,
            "platform": "Android",
            "acceptLanguage": "en-US,en",
            "userAgentMetadata": {
                "brands": [
                    {"brand": "Chromium", "version": "123"}, 
                    {"brand": "Google Chrome", "version": "123"}
                ],
                "fullVersion": "123.0.0.0",
                "platform": "Android",
                "platformVersion": "14",
                "architecture": "",
                "model": "Pixel 7",
                "mobile": True
            }
        })
        
        # Set optimized headers
        driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
            "headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "br,gzip",  # Chrome default
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
        })
        
    except Exception as e:
        print(f"Mobile CDP optimization failed: {e}")
