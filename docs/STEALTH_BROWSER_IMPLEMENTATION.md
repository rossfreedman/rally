# Stealth Browser Implementation - Rally Tennis Scrapers

## Overview

This document describes the implementation of fingerprint evasion capabilities for all Selenium-based scrapers in the Rally project. The implementation uses `undetected-chromedriver` to avoid bot detection on TennisScores.com and similar websites.

## What Was Implemented

### 1. StealthBrowserManager Class

**File**: `data/etl/scrapers/stealth_browser.py`

A new context manager that provides fingerprint evasion capabilities:

- **Uses `undetected-chromedriver`** instead of regular Selenium WebDriver
- **Randomizes user-agent strings** from a pool of realistic Chrome user agents
- **Randomizes window sizes** to avoid consistent fingerprinting
- **Injects JavaScript** to spoof browser fingerprints:
  - `navigator.webdriver = undefined`
  - Realistic `navigator.plugins` array
  - Proper `navigator.languages` configuration
  - Spoofed `window.chrome.runtime` properties
- **Removes automation flags** like `--enable-automation` and `--disable-blink-features=AutomationControlled`
- **Implements retry logic** with exponential backoff
- **Supports both headless and headful modes**

### 2. Updated Scrapers

The following scrapers have been updated to use `StealthBrowserManager`:

#### `scraper_players.py`
- ✅ Replaced `ChromeManager` with `StealthBrowserManager` import
- ✅ Updated context manager usage: `with StealthBrowserManager(headless=True) as driver:`
- ✅ Removed old `ChromeManager` class definition

#### `scraper_stats.py`
- ✅ Replaced `ChromeManager` with `StealthBrowserManager` import
- ✅ Updated context manager usage with fallback support
- ✅ Updated performance metrics to reflect "Stealth Chrome WebDriver"

#### `scraper_player_history.py`
- ✅ Replaced `ChromeManager` with `StealthBrowserManager` import
- ✅ Updated context manager usage: `with StealthBrowserManager(headless=True) as driver:`
- ✅ Removed old `ChromeManager` class definition

#### `scraper_match_scores.py`
- ✅ Replaced `ChromeManager` with `StealthBrowserManager` import
- ✅ Updated context manager usage: `with StealthBrowserManager(headless=True) as driver:`
- ✅ Removed old `ChromeManager` class definition

#### `scraper_schedule.py`
- ✅ **No changes needed** - Uses `requests` library only (no Selenium)

#### `master_scraper.py`
- ✅ **No changes needed** - Orchestrates other scrapers, doesn't use WebDriver directly

### 3. Dependencies

Updated `requirements.txt` to include:
```
undetected-chromedriver>=3.5.5
```

### 4. Test Suite

Created `scripts/test_stealth_browser.py` to verify:
- StealthBrowserManager can be imported and instantiated
- Fingerprint evasion scripts are working
- Real website navigation is successful
- All scrapers can import the new manager

## Key Features

### Fingerprint Evasion Techniques

1. **User Agent Randomization**
   - Pool of 6 realistic Chrome user agents
   - Rotates between Windows, macOS, and Linux
   - Recent Chrome versions (119-120)

2. **Browser Fingerprint Spoofing**
   - Removes `navigator.webdriver` property
   - Injects realistic `navigator.plugins` array
   - Sets proper `navigator.languages` to `['en-US', 'en']`
   - Removes automation detection variables

3. **Window Size Randomization**
   - Common resolutions: 1920x1080, 1366x768, 1536x864, etc.
   - Prevents consistent window size fingerprinting

4. **Chrome Options Optimization**
   - Disables automation flags
   - Uses new headless mode (`--headless=new`)
   - Optimized for both local and containerized environments

### Error Handling & Reliability

1. **Exponential Backoff Retry**
   - Up to 3 retry attempts by default
   - Exponential backoff: 1s, 2s, 4s delays
   - Random jitter to prevent synchronized retries

2. **Comprehensive Logging**
   - Detailed startup and error messages
   - Success confirmations with user agent info
   - Warning messages for partial failures

3. **Context Manager Support**
   - Automatic cleanup on exit
   - Exception handling and logging
   - Proper resource management

## Usage Examples

### Basic Usage
```python
from stealth_browser import StealthBrowserManager

with StealthBrowserManager(headless=True) as driver:
    driver.get("https://example.com")
    # Scraping logic here
```

### Advanced Configuration
```python
with StealthBrowserManager(
    headless=False,  # Show browser window
    max_retries=5,   # More retry attempts
    user_agent_override="Custom User Agent"
) as driver:
    driver.get("https://example.com")
    # Scraping logic here
```

### Convenience Function
```python
from stealth_browser import create_stealth_driver

with create_stealth_driver(headless=True) as driver:
    driver.get("https://example.com")
    # Scraping logic here
```

## Benefits

### Before Implementation
- **Regular Selenium WebDriver** - easily detectable
- **Static user agents** - consistent fingerprinting
- **Automation flags present** - obvious bot detection
- **No JavaScript spoofing** - browser properties revealed automation

### After Implementation
- **Undetected Chrome Driver** - advanced evasion techniques
- **Randomized fingerprints** - harder to track and block
- **Removed automation indicators** - appears as regular browser
- **JavaScript spoofing** - browser properties look natural

## Testing

### Run the test suite:
```bash
cd /path/to/rally
python scripts/test_stealth_browser.py
```

### Expected output:
```
🎾 Rally Tennis Scraper - Stealth Browser Test Suite
============================================================
🧪 Testing StealthBrowserManager...
✅ Successfully imported StealthBrowserManager
🔧 Testing browser creation...
✅ Stealth browser created successfully!
🌐 Testing navigation to test page...
🔍 Testing fingerprint evasion...
   navigator.webdriver: None
   User agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537...
   Languages: ['en-US', 'en']
🌐 Testing real website navigation...
✅ Successfully navigated to real website with Chrome user agent
✅ All stealth browser tests passed!

🔍 Testing scraper imports...
   Testing scraper_players...
   ✅ scraper_players can access StealthBrowserManager
   [... more tests ...]

📊 Scraper import test results: 4/4 successful
============================================================
🎉 ALL TESTS PASSED!
✅ StealthBrowserManager is ready for use
✅ All scrapers should now have fingerprint evasion capabilities
```

## Migration Notes

### What Changed
1. **Import statements** - Added `from stealth_browser import StealthBrowserManager`
2. **Context manager calls** - Changed `ChromeManager()` to `StealthBrowserManager(headless=True)`
3. **Class definitions** - Removed old `ChromeManager` classes
4. **Dependencies** - Added `undetected-chromedriver>=3.5.5`

### What Stayed The Same
1. **Driver interface** - Same Selenium WebDriver API
2. **Scraping logic** - No changes to parsing or data extraction
3. **File structure** - All scrapers remain in same locations
4. **Master scraper** - No changes to orchestration logic

## Performance Impact

### Startup Time
- **Slightly increased** due to fingerprint evasion setup (~1-3 seconds)
- **Random delays** added to avoid pattern detection
- **Auto-download** of compatible ChromeDriver if needed

### Memory Usage
- **Similar to regular Selenium** - undetected-chromedriver is optimized
- **Temporary directories** created for cache and user data
- **Automatic cleanup** when context manager exits

### Success Rate
- **Expected improvement** in scraping success rates
- **Reduced blocking** from bot detection systems
- **More reliable** long-term operation

## Maintenance

### Updating User Agents
Edit the `user_agents` list in `StealthBrowserManager._get_random_user_agent()` to add newer Chrome versions.

### Adjusting Fingerprint Scripts
Modify `StealthBrowserManager._inject_stealth_scripts()` to enhance or add new evasion techniques.

### Monitoring Effectiveness
- Watch for increased failure rates (may indicate detection)
- Monitor scraper logs for unusual errors
- Test periodically with the provided test suite

## Future Enhancements

1. **Proxy Support** - Add rotating proxy capabilities
2. **Residential IPs** - Integration with proxy services
3. **Behavioral Mimicking** - Add human-like mouse movements and typing
4. **Advanced Fingerprinting** - Spoof canvas, WebGL, and audio fingerprints
5. **Adaptive Delays** - Dynamic delays based on site response patterns

## Troubleshooting

### Common Issues

1. **Import Error**: `ModuleNotFoundError: No module named 'undetected_chromedriver'`
   - **Solution**: `pip install undetected-chromedriver>=3.5.5`

2. **Chrome Not Found**: Browser initialization fails
   - **Solution**: Install Google Chrome browser

3. **Permission Errors**: Temporary directory creation fails
   - **Solution**: Ensure write permissions to `/tmp/` or system temp directory

4. **Timeout Errors**: Driver creation takes too long
   - **Solution**: Increase `max_retries` parameter or check network connectivity

### Debug Mode
Set logging level to DEBUG to see detailed browser creation steps:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Conclusion

The stealth browser implementation provides robust fingerprint evasion capabilities for all Rally Tennis Scrapers. This should significantly improve the reliability and longevity of the scraping operations while maintaining the same familiar interface for developers.

All Selenium-based scrapers now automatically use these enhanced evasion techniques, making them much more resilient against bot detection systems used by TennisScores.com and similar sites. 