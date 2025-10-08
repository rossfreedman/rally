#!/usr/bin/env python3
"""
Simple, standalone test to extract career stats without any scraper complexity.
Just basic Selenium to get career stats from a player page.
"""

import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def simple_career_test():
    """Simple test to extract career stats."""
    print("🎾 Simple Career Stats Test")
    print("=" * 40)
    
    # Create basic Chrome driver
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Don't use headless - let's see what happens
    # options.add_argument("--headless")
    
    try:
        driver = webdriver.Chrome(options=options)
        print("✅ Chrome driver created")
        
        # Test URL for Sonja Baichwal (we know she has career stats)
        test_url = "https://cnswpl.tenniscores.com/player.php?p=nndz-WkM2eHhyNzhoQT09"
        
        print(f"🌐 Navigating to: {test_url}")
        driver.get(test_url)
        
        # Wait for page to load
        print("⏳ Waiting for page to load...")
        time.sleep(5)
        
        # Take screenshot of initial page
        driver.save_screenshot("initial_page.png")
        print("📸 Saved initial_page.png")
        
        # Look for chronological checkbox
        print("🔍 Looking for chronological checkbox...")
        
        try:
            # Wait for checkbox to be present
            checkbox = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox']"))
            )
            
            is_checked = checkbox.is_selected()
            print(f"✅ Found checkbox, currently checked: {is_checked}")
            
            if not is_checked:
                print("🔄 Clicking chronological checkbox...")
                checkbox.click()
                
                # Wait for content to load
                print("⏳ Waiting for AJAX content to load...")
                time.sleep(10)
                
                # Take screenshot after clicking
                driver.save_screenshot("after_chronological.png")
                print("📸 Saved after_chronological.png")
        
        except Exception as e:
            print(f"⚠️ Checkbox interaction failed: {e}")
        
        # Try to find and click "Expand All Matches"
        print("🔍 Looking for Expand All Matches...")
        
        try:
            expand_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Expand All Matches')]")
            print("✅ Found 'Expand All Matches' link")
            expand_link.click()
            
            print("⏳ Waiting for expansion...")
            time.sleep(8)
            
            # Take screenshot after expanding
            driver.save_screenshot("after_expand.png")
            print("📸 Saved after_expand.png")
            
        except Exception as e:
            print(f"⚠️ Expand All not found or failed: {e}")
        
        # Get final HTML content
        html_content = driver.page_source
        print(f"📄 Final HTML: {len(html_content)} characters")
        
        # Save HTML for inspection
        with open('simple_career_final.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("💾 Saved simple_career_final.html")
        
        # Analyze content
        print("\n📊 Content Analysis:")
        
        # Look for career indicators
        indicators = {
            'NIGHT LEAGUE': 'NIGHT LEAGUE' in html_content,
            'SERIES E': 'SERIES E' in html_content,
            'APTA WOMEN': 'APTA WOMEN' in html_content,
            'vs Tennaqua': 'vs Tennaqua' in html_content,
            'vs Valley Lo': 'vs Valley Lo' in html_content,
            '03/10/25': '03/10/25' in html_content,
            '01/20/25': '01/20/25' in html_content,
            'Evanston E (H)': 'Evanston E (H)' in html_content,
        }
        
        found = [name for name, present in indicators.items() if present]
        print(f"Career content found: {found}")
        
        # Count W/L
        w_count = len(re.findall(r'\bW\b', html_content))
        l_count = len(re.findall(r'\bL\b', html_content))
        print(f"Total W/L: {w_count}W/{l_count}L")
        
        # Look for specific match result patterns
        match_results = re.findall(r'(\d{2}/\d{2}/\d{2}).*?([WL])', html_content, re.DOTALL)
        career_w = sum(1 for _, result in match_results if result == 'W')
        career_l = sum(1 for _, result in match_results if result == 'L')
        
        print(f"Match pattern results: {career_w}W/{career_l}L")
        
        if len(found) >= 3:
            print("✅ SUCCESS: Career content is loading!")
        else:
            print("❌ Career content not loading - may need different approach")
        
        # Keep browser open for manual inspection
        print("\n🔍 Browser window left open for manual inspection")
        print("   Check the screenshots and HTML file to see what's loading")
        input("   Press Enter to close browser and finish test...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    simple_career_test()
