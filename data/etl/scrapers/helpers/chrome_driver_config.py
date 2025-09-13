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
"""

import undetected_chromedriver as uc
from typing import Optional, Tuple

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
