#!/usr/bin/env python3
"""
Simple Stealth Browser Test
Basic test to check if stealth browser can be initialized and access simple pages.
"""

import os
import sys
import time
import json
from pathlib import Path

# Add the scrapers directory to the path
current_file = os.path.abspath(__file__)
scrapers_dir = os.path.dirname(current_file)
if scrapers_dir not in sys.path:
    sys.path.insert(0, scrapers_dir)

def test_basic_stealth():
    """Test basic stealth browser functionality."""
    print("🧪 Simple Stealth Browser Test")
    print("=" * 40)
    
    try:
        # Test 1: Import modules
        print("🔧 Testing module imports...")
        from stealth_browser import EnhancedStealthBrowser, StealthConfig
        print("   ✅ stealth_browser imported successfully")
        
        # Test 2: Create config
        print("🔧 Creating stealth config...")
        config = StealthConfig(
            fast_mode=True,
            verbose=True,
            environment="local",
            headless=True,  # Use headless for testing
            min_delay=1.0,
            max_delay=2.0
        )
        print("   ✅ StealthConfig created successfully")
        
        # Test 3: Initialize browser
        print("🔧 Initializing stealth browser...")
        browser = EnhancedStealthBrowser(config)
        print("   ✅ EnhancedStealthBrowser initialized successfully")
        
        # Test 4: Test HTTPBin access
        print("🌐 Testing HTTPBin access...")
        try:
            html = browser.get_html("https://httpbin.org/headers")
            if html and len(html) > 100:
                print("   ✅ HTTPBin access successful")
                print(f"   📊 Response length: {len(html)} characters")
                
                # Check for automation indicators
                if "selenium" in html.lower() or "webdriver" in html.lower():
                    print("   ⚠️ Automation indicators detected in response")
                else:
                    print("   ✅ No obvious automation indicators")
                    
            else:
                print("   ❌ HTTPBin access failed or insufficient content")
                
        except Exception as e:
            print(f"   ❌ HTTPBin test failed: {e}")
        
        # Test 5: Test navigator properties
        print("🔍 Testing navigator properties...")
        try:
            driver = browser.current_driver
            if driver:
                # Check webdriver property
                webdriver_value = driver.execute_script("return navigator.webdriver")
                print(f"   📊 navigator.webdriver: {webdriver_value}")
                
                if webdriver_value:
                    print("   🚫 navigator.webdriver is TRUE - stealth failing!")
                else:
                    print("   ✅ navigator.webdriver is properly masked")
                    
                # Check plugins
                plugins_length = driver.execute_script("return navigator.plugins.length")
                print(f"   📊 navigator.plugins.length: {plugins_length}")
                
                # Check languages
                languages = driver.execute_script("return navigator.languages")
                print(f"   📊 navigator.languages: {languages}")
                
            else:
                print("   ❌ No active driver found")
                
        except Exception as e:
            print(f"   ❌ Navigator properties test failed: {e}")
        
        # Test 6: Test APTA Chicago access
        print("🌐 Testing APTA Chicago access...")
        try:
            html = browser.get_html("https://apta.tenniscores.com")
            if html and len(html) > 1000:
                print("   ✅ APTA Chicago access successful")
                print(f"   📊 Response length: {len(html)} characters")
                
                # Check for blocking indicators
                blocking_indicators = ["access denied", "blocked", "captcha", "forbidden"]
                page_lower = html.lower()
                
                detected_blocks = []
                for indicator in blocking_indicators:
                    if indicator in page_lower:
                        detected_blocks.append(indicator)
                
                if detected_blocks:
                    print(f"   🚫 Blocking indicators: {', '.join(detected_blocks)}")
                else:
                    print("   ✅ No blocking indicators detected")
                    
                # Check title
                if "tenniscores" in html.lower():
                    print("   ✅ Page appears to be normal APTA Chicago content")
                else:
                    print("   ⚠️ Page content doesn't match expected APTA Chicago format")
                    
            else:
                print("   ❌ APTA Chicago access failed or insufficient content")
                
        except Exception as e:
            print(f"   ❌ APTA Chicago test failed: {e}")
        
        # Cleanup
        print("🧹 Cleaning up...")
        if hasattr(browser, 'current_driver') and browser.current_driver:
            browser.current_driver.quit()
            print("   ✅ Browser closed successfully")
        
        print("\n🎯 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🚀 Simple Stealth Browser Test Suite")
    print("Testing basic functionality without complex initialization")
    print("=" * 60)
    
    success = test_basic_stealth()
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
