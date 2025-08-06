#!/usr/bin/env python3
"""
Enhanced APTA Strategies
Implements successful anti-detection strategies for APTA based on analysis
"""

import sys
import os
import time
import random
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedAPTAStrategies:
    """Enhanced strategies for APTA undetectability."""
    
    def __init__(self):
        self.successful_headers = {
            "minimal": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            "realistic": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0"
            },
            "windows_chrome": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Cache-Control": "max-age=0"
            },
            "referrer": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": "https://www.google.com/",
                "DNT": "1"
            }
        }
        
        self.successful_uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        
        self.timing_patterns = [
            [2, 3, 1, 4, 2],  # Human-like
            [1.5, 2.5, 3.5, 1.8, 2.2],  # Random
            [2, 2, 2, 2, 2],  # Consistent
            [0, 0, 0, 0, 0]   # No delays
        ]
    
    def get_enhanced_headers(self, strategy="minimal"):
        """Get enhanced headers based on successful strategies."""
        if strategy in self.successful_headers:
            return self.successful_headers[strategy].copy()
        else:
            return self.successful_headers["minimal"].copy()
    
    def get_random_successful_ua(self):
        """Get a random successful User-Agent."""
        return random.choice(self.successful_uas)
    
    def get_human_like_delay(self):
        """Get a human-like delay pattern."""
        return random.choice(self.timing_patterns)
    
    def create_session_with_enhancements(self):
        """Create an enhanced session for APTA."""
        import requests
        
        session = requests.Session()
        
        # Set enhanced headers
        strategy = random.choice(list(self.successful_headers.keys()))
        session.headers.update(self.get_enhanced_headers(strategy))
        
        # Add additional enhancements
        session.headers.update({
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        })
        
        return session

def enhance_proxy_manager_for_apta():
    """Enhance proxy manager with APTA-specific strategies."""
    logger.info("🔧 Enhancing proxy manager for APTA...")
    
    try:
        from data.etl.scrapers.proxy_manager import get_proxy_rotator
        
        rotator = get_proxy_rotator()
        
        # Add APTA-specific proxy selection logic
        def get_apta_proxy():
            """Get proxy optimized for APTA."""
            proxy = rotator.get_proxy()
            
            # Add APTA-specific proxy validation
            try:
                import requests
                test_response = requests.get(
                    "https://apta.tenniscores.com",
                    proxies={"http": proxy, "https": proxy},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                    },
                    timeout=10
                )
                
                if test_response.status_code == 200 and len(test_response.text) > 10000:
                    logger.info(f"✅ APTA-optimized proxy selected: {proxy}")
                    return proxy
                else:
                    logger.warning(f"⚠️ Proxy failed APTA test: {proxy}")
                    return rotator.get_proxy()  # Try another
                    
            except Exception as e:
                logger.warning(f"⚠️ Proxy test failed: {e}")
                return proxy  # Use anyway
        
        # Monkey patch the rotator
        rotator.get_apta_proxy = get_apta_proxy
        
        logger.info("✅ Proxy manager enhanced for APTA")
        return rotator
        
    except Exception as e:
        logger.error(f"❌ Failed to enhance proxy manager: {e}")
        return None

def enhance_ua_manager_for_apta():
    """Enhance UA manager with APTA-specific strategies."""
    logger.info("🔧 Enhancing UA manager for APTA...")
    
    try:
        from data.etl.scrapers.user_agent_manager import get_user_agent_manager
        
        manager = get_user_agent_manager()
        
        # Add APTA-specific UA selection
        def get_apta_optimized_ua():
            """Get UA optimized for APTA success."""
            successful_apta_uas = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ]
            
            return random.choice(successful_apta_uas)
        
        # Add to manager
        manager.get_apta_optimized_ua = get_apta_optimized_ua
        
        logger.info("✅ UA manager enhanced for APTA")
        return manager
        
    except Exception as e:
        logger.error(f"❌ Failed to enhance UA manager: {e}")
        return None

def create_enhanced_apta_scraper():
    """Create an enhanced scraper specifically for APTA."""
    logger.info("🔧 Creating enhanced APTA scraper...")
    
    class EnhancedAPTAScraper:
        """Enhanced scraper optimized for APTA."""
        
        def __init__(self):
            self.strategies = EnhancedAPTAStrategies()
            self.proxy_rotator = enhance_proxy_manager_for_apta()
            self.ua_manager = enhance_ua_manager_for_apta()
            self.session = self.strategies.create_session_with_enhancements()
            
            # Set proxy
            if self.proxy_rotator:
                proxy = self.proxy_rotator.get_apta_proxy()
                self.session.proxies = {"http": proxy, "https": proxy}
        
        def get_apta_content(self, url, max_retries=3):
            """Get APTA content with enhanced strategies."""
            logger.info(f"🌐 Fetching APTA content: {url}")
            
            for attempt in range(max_retries):
                try:
                    # Rotate strategy for each attempt
                    strategy = random.choice(list(self.strategies.successful_headers.keys()))
                    headers = self.strategies.get_enhanced_headers(strategy)
                    
                    # Update session headers
                    self.session.headers.update(headers)
                    
                    # Add human-like delay
                    if attempt > 0:
                        delay = random.uniform(1, 3)
                        time.sleep(delay)
                    
                    # Make request
                    response = self.session.get(url, timeout=30)
                    
                    if response.status_code == 200 and len(response.text) > 10000:
                        logger.info(f"✅ APTA content fetched successfully: {len(response.text)} chars")
                        return response.text
                    else:
                        logger.warning(f"⚠️ APTA request failed (attempt {attempt + 1}): {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"❌ APTA request error (attempt {attempt + 1}): {e}")
                    
                    # Rotate proxy on failure
                    if self.proxy_rotator:
                        proxy = self.proxy_rotator.get_apta_proxy()
                        self.session.proxies = {"http": proxy, "https": proxy}
            
            logger.error("❌ All APTA attempts failed")
            return None
        
        def scrape_apta_with_enhancements(self, urls):
            """Scrape multiple APTA URLs with enhancements."""
            results = []
            
            for url in urls:
                logger.info(f"📡 Scraping APTA URL: {url}")
                
                content = self.get_apta_content(url)
                if content:
                    results.append({
                        "url": url,
                        "content": content,
                        "length": len(content),
                        "success": True
                    })
                else:
                    results.append({
                        "url": url,
                        "content": None,
                        "length": 0,
                        "success": False
                    })
                
                # Add delay between requests
                time.sleep(random.uniform(2, 5))
            
            return results
    
    return EnhancedAPTAScraper()

def test_enhanced_apta_strategies():
    """Test the enhanced APTA strategies."""
    logger.info("🧪 Testing enhanced APTA strategies...")
    
    # Create enhanced scraper
    scraper = create_enhanced_apta_scraper()
    
    # Test URLs
    test_urls = [
        "https://apta.tenniscores.com",
        "https://apta.tenniscores.com/standings",
        "https://apta.tenniscores.com/schedule"
    ]
    
    # Test scraping
    results = scraper.scrape_apta_with_enhancements(test_urls)
    
    # Analyze results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    logger.info(f"📊 Enhanced APTA Strategy Test Results:")
    logger.info(f"   Total URLs: {len(results)}")
    logger.info(f"   Successful: {len(successful)}")
    logger.info(f"   Failed: {len(failed)}")
    
    for result in results:
        status = "✅" if result["success"] else "❌"
        logger.info(f"   {status} {result['url']}: {result['length']} chars")
    
    return len(successful) > 0

def main():
    """Main function to implement enhanced APTA strategies."""
    logger.info("🚀 Implementing Enhanced APTA Strategies...")
    
    # Test enhanced strategies
    success = test_enhanced_apta_strategies()
    
    if success:
        logger.info("✅ Enhanced APTA strategies working!")
        return True
    else:
        logger.error("❌ Enhanced APTA strategies failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 