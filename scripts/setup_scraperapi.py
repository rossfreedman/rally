#!/usr/bin/env python3
"""
Setup script for ScraperAPI with US-based IPs.
This script helps configure ScraperAPI to ensure US-based IP addresses for scraping.
"""

import os
import sys
import requests
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_scraperapi_key():
    """Check if ScraperAPI key is configured."""
    api_key = os.getenv("SCRAPERAPI_KEY")
    if not api_key:
        print("❌ SCRAPERAPI_KEY environment variable not set")
        print("\n💡 To get a ScraperAPI key:")
        print("   1. Go to https://www.scraperapi.com/")
        print("   2. Sign up for a free account")
        print("   3. Get your API key from the dashboard")
        print("   4. Set the environment variable:")
        print("      export SCRAPERAPI_KEY=your_api_key_here")
        return None
    
    print(f"✅ SCRAPERAPI_KEY found: {api_key[:8]}...")
    return api_key

def test_scraperapi_us_ip(api_key):
    """Test ScraperAPI with US-based IP."""
    print("\n🌐 Testing ScraperAPI US-based IP...")
    
    # Test different US proxy endpoints
    us_proxy_urls = [
        f"http://scraperapi-premium-country-us:{api_key}@proxy-server.scraperapi.com:8001",
        f"http://scraperapi-country-us:{api_key}@proxy-server.scraperapi.com:8001",
        f"http://scraperapi-country-us-east:{api_key}@proxy-server.scraperapi.com:8001",
        f"http://scraperapi-country-us-west:{api_key}@proxy-server.scraperapi.com:8001",
        f"http://scraperapi-country-us-central:{api_key}@proxy-server.scraperapi.com:8001"
    ]
    
    for i, proxy_url in enumerate(us_proxy_urls, 1):
        print(f"\n🔍 Testing US proxy {i}/{len(us_proxy_urls)}...")
        try:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxies,
                timeout=30
            )
            
            if response.status_code == 200:
                ip_data = response.json()
                ip_address = ip_data.get('origin', 'Unknown')
                print(f"✅ Proxy {i} working - IP: {ip_address}")
                
                # Check if IP is US-based
                try:
                    geo_response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10)
                    if geo_response.status_code == 200:
                        geo_data = geo_response.json()
                        country = geo_data.get('country_name', 'Unknown')
                        country_code = geo_data.get('country_code', 'Unknown')
                        print(f"📍 IP location: {country} ({country_code})")
                        
                        if country_code == 'US':
                            print("✅ US-based IP confirmed!")
                            return True, proxy_url
                        else:
                            print(f"⚠️ Non-US IP detected: {country_code}")
                    else:
                        print(f"⚠️ Could not verify IP location (Status: {geo_response.status_code})")
                        
                except Exception as geo_e:
                    print(f"⚠️ IP geolocation check failed: {str(geo_e)}")
                    
            else:
                print(f"❌ Proxy {i} failed - Status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Proxy {i} connection failed: {str(e)}")
    
    return False, None

def create_env_file(api_key):
    """Create or update .env file with ScraperAPI configuration."""
    print("\n🔧 Creating .env file with ScraperAPI configuration...")
    
    env_content = f"""# ScraperAPI Configuration
SCRAPERAPI_KEY={api_key}
SCRAPERAPI_REGION=us-premium
REQUIRE_PROXY=true

# Scraper Configuration
HEADLESS_MODE=true
MAX_RETRIES=3
REQUEST_TIMEOUT=60

# Chrome Configuration
CHROMEDRIVER_PATH=
"""
    
    env_file = project_root / ".env"
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created .env file: {env_file}")

def test_tennis_site_with_proxy(api_key, proxy_url):
    """Test accessing tennis scores site with US proxy."""
    print("\n🎾 Testing tennis scores site with US proxy...")
    
    try:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Test with a simple request first
        response = requests.get(
            'https://nstf.tenniscores.com',
            proxies=proxies,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Tennis scores site accessible with US proxy")
            print(f"   Status: {response.status_code}")
            print(f"   Content length: {len(response.text)} characters")
            return True
        else:
            print(f"❌ Tennis scores site failed - Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Tennis scores site test failed: {str(e)}")
        return False

def setup_selenium_with_proxy(api_key):
    """Create a test script for Selenium with ScraperAPI proxy."""
    print("\n🔧 Creating Selenium test with ScraperAPI proxy...")
    
    test_script = f"""#!/usr/bin/env python3
\"\"\"
Test script for Selenium with ScraperAPI US proxy.
\"\"\"

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ["SCRAPERAPI_KEY"] = "{api_key}"
os.environ["SCRAPERAPI_REGION"] = "us-premium"
os.environ["REQUIRE_PROXY"] = "true"

def test_selenium_with_proxy():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("🧪 Testing Selenium with ScraperAPI US proxy...")
        
        # Configure Chrome options
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Get ChromeDriver path
        driver_path = ChromeDriverManager().install()
        
        # Fix the path if it's pointing to the wrong file
        if "THIRD_PARTY_NOTICES.chromedriver" in driver_path:
            driver_path = driver_path.replace("THIRD_PARTY_NOTICES.chromedriver", "chromedriver")
            print(f"🔧 Fixed ChromeDriver path: {driver_path}")
        
        # Create driver
        print("🔧 Creating Chrome WebDriver...")
        driver = webdriver.Chrome(executable_path=driver_path, options=options)
        
        # Test navigation to tennis scores site
        print("🌐 Testing navigation to tennis scores site...")
        driver.get("https://nstf.tenniscores.com")
        time.sleep(5)
        
        # Check if page loaded successfully
        page_title = driver.title
        print(f"✅ Tennis page loaded successfully - Title: {{page_title}}")
        
        # Check page content
        body_text = driver.find_element('tag name', 'body').text
        if len(body_text) > 100:
            print("✅ Page content loaded successfully")
            print(f"   Content preview: {{body_text[:200]}}...")
        else:
            print("⚠️ Page content seems minimal")
        
        driver.quit()
        return True
        
    except Exception as e:
        print(f"❌ Selenium with proxy test failed: {{str(e)}}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_selenium_with_proxy()
"""
    
    test_file = project_root / "scripts" / "test_selenium_with_proxy.py"
    with open(test_file, 'w') as f:
        f.write(test_script)
    
    # Make executable
    test_file.chmod(0o755)
    
    print(f"✅ Created Selenium proxy test: {test_file}")

def main():
    """Main setup function."""
    print("🔧 SCRAPERAPI US IP SETUP")
    print("=" * 40)
    
    # Check ScraperAPI key
    api_key = check_scraperapi_key()
    if not api_key:
        print("\n❌ Please set your SCRAPERAPI_KEY environment variable first.")
        print("   export SCRAPERAPI_KEY=your_api_key_here")
        return
    
    # Test US-based IP
    us_ip_working, working_proxy = test_scraperapi_us_ip(api_key)
    
    if us_ip_working:
        print("\n✅ US-based IP confirmed!")
        
        # Test tennis site with proxy
        tennis_ok = test_tennis_site_with_proxy(api_key, working_proxy)
        
        if tennis_ok:
            print("\n🎉 SUCCESS! Tennis scores site accessible with US proxy.")
            
            # Create configuration files
            create_env_file(api_key)
            setup_selenium_with_proxy(api_key)
            
            print("\n💡 Next steps:")
            print("   1. Test Selenium with proxy: python3 scripts/test_selenium_with_proxy.py")
            print("   2. Run scraper: python3 data/etl/scrapers/master_scraper.py")
        else:
            print("\n⚠️ Tennis scores site not accessible even with US proxy.")
            print("   This might be a temporary issue or site blocking.")
    else:
        print("\n❌ Could not get US-based IP from ScraperAPI.")
        print("   Check your ScraperAPI account and plan.")
        print("   Make sure you have access to US-based proxies.")

if __name__ == "__main__":
    main() 