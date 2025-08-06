# Chrome Driver Configuration
# This file contains settings for Chrome driver compatibility

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
