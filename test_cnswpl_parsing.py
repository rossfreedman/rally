#!/usr/bin/env python3
"""
Quick test of CNSWPL match parsing logic
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'data', 'etl', 'scrapers'))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

def create_driver():
    """Create a Chrome WebDriver instance."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')
    return webdriver.Chrome(options=options)

def main():
    print("🧪 Quick CNSWPL Match Parsing Test")
    print("=" * 50)
    
    # Test with one of the URLs you provided
    test_url = "https://cnswpl.tennisscores.com/?mod=nndz-TjJiOWtOR3QzTU4yalNnT1VzYk5Ndz09&did=nndz-WnkrNXc3MD0%3D"
    
    driver = None
    try:
        driver = create_driver()
        
        print(f"🌐 Navigating to: {test_url}")
        driver.get(test_url)
        
        # Wait for page to load
        time.sleep(3)
        
        print("🔍 Looking for Matches link...")
        try:
            matches_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.LINK_TEXT, "Matches"))
            )
            print("✅ Found Matches link, clicking...")
            matches_link.click()
            time.sleep(3)
        except:
            print("❌ Could not find Matches link")
            return
        
        print("🔍 Looking for match results container...")
        try:
            match_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "match_results_container"))
            )
            print("✅ Found match results container")
        except:
            print("❌ Could not find match results container")
            return
        
        # Test our parsing function
        print("🔍 Testing CNSWPL parsing logic...")
        
        # Import the parsing function
        from scraper_match_scores import parse_cnswpl_matches
        
        # Test the parsing
        matches = parse_cnswpl_matches(match_container, "Division 1", "CNSWPL")
        
        print(f"📊 Results: Found {len(matches)} matches")
        
        if matches:
            print("\n🎯 Sample matches:")
            for i, match in enumerate(matches[:3], 1):  # Show first 3
                print(f"  {i}. {match['Date']}: {match['Home Team']} vs {match['Away Team']}")
                print(f"     {match['Home Player 1']}/{match['Home Player 2']} vs {match['Away Player 1']}/{match['Away Player 2']}")
                print(f"     Score: {match['Scores']}")
        else:
            print("❌ No matches found - parsing may need adjustment")
            
            # Debug: Show page content
            print("\n🔍 Debug - Page content preview:")
            page_text = match_container.text
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            for i, line in enumerate(lines[:20], 1):  # Show first 20 lines
                print(f"  {i:2d}: {line[:100]}...")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("✅ Cleaned up browser")

if __name__ == "__main__":
    main() 