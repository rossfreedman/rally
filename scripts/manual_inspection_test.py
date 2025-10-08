#!/usr/bin/env python3
"""
Save the actual HTML content for manual inspection to understand the structure.
"""

import sys
import os
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.etl.scrapers.cnswpl.cnswpl_scrape_players import CNSWPLRosterScraper

def manual_inspection_test():
    """Save HTML for manual inspection."""
    print("🔍 Manual Inspection Test")
    print("=" * 30)
    
    # Initialize scraper
    scraper = CNSWPLRosterScraper()
    
    # Test with Sonja Baichwal
    test_url = "/player.php?p=nndz-WkM2eHhyNzhoQT09"
    full_url = f"{scraper.base_url}{test_url}"
    
    # Get browser
    browser = scraper.stealth_browser
    if not hasattr(browser, 'current_driver') or browser.current_driver is None:
        browser.config.force_browser = True
        browser.current_driver = browser._create_driver()
    
    driver = browser.current_driver
    
    try:
        print(f"🌐 Navigating to: {full_url}")
        driver.get(full_url)
        time.sleep(5)
        
        # Save initial HTML
        initial_html = driver.page_source
        with open('manual_initial.html', 'w', encoding='utf-8') as f:
            f.write(initial_html)
        print(f"💾 Saved initial HTML ({len(initial_html)} chars)")
        
        from selenium.webdriver.common.by import By
        
        # Click chronological checkbox
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        if checkboxes:
            print(f"🔄 Clicking chronological checkbox...")
            checkboxes[0].click()
            time.sleep(20)  # Very long wait
            
            # Save after chronological
            chrono_html = driver.page_source
            with open('manual_chronological.html', 'w', encoding='utf-8') as f:
                f.write(chrono_html)
            print(f"💾 Saved chronological HTML ({len(chrono_html)} chars)")
            
            # Try dropdown interaction
            try:
                dropdown = driver.find_element(By.ID, "match_types")
                dropdown.click()
                time.sleep(3)
                all_matches = driver.find_element(By.XPATH, "//option[@value='All']")
                all_matches.click()
                time.sleep(10)
                
                # Save after dropdown
                dropdown_html = driver.page_source
                with open('manual_dropdown.html', 'w', encoding='utf-8') as f:
                    f.write(dropdown_html)
                print(f"💾 Saved dropdown HTML ({len(dropdown_html)} chars)")
                
            except Exception as e:
                print(f"⚠️ Dropdown interaction failed: {e}")
        
        print(f"\n📋 Files created for manual inspection:")
        print(f"   - manual_initial.html (before any clicks)")
        print(f"   - manual_chronological.html (after chronological checkbox)")
        print(f"   - manual_dropdown.html (after dropdown selection)")
        print(f"\n💡 You can open these files in a browser to see what content is actually loading")
        print(f"💡 Compare with your screenshot to identify the missing elements")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    manual_inspection_test()
