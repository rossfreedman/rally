#!/usr/bin/env python3
"""
Scrape the actual tennis PTI calculator to get correct results

This will help us understand what the real calculator should produce
for the user's exact scenario.
"""

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json

def scrape_tennis_calculator():
    """Scrape the actual tennis PTI calculator"""
    
    print("🔍 Scraping Tennis PTI Calculator")
    print("=" * 50)
    
    # User's exact scenario
    test_data = {
        "player_pti": 70,
        "partner_pti": 40, 
        "opp1_pti": 30,
        "opp2_pti": 23,
        "player_exp": "30+ matches",
        "partner_exp": "30+ matches",
        "opp1_exp": "30+ matches", 
        "opp2_exp": "10-30 Matches",
        "score": "6-2,2-6,6-3"
    }
    
    print("📊 Testing scenario:")
    for key, value in test_data.items():
        print(f"   {key}: {value}")
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to calculator
        print("\n🌐 Navigating to calculator...")
        driver.get("https://calc.platform.tennis/calculator2.html")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ptiplayer"))
        )
        
        print("✅ Page loaded successfully")
        
        # Fill in Player PTI
        driver.find_element(By.ID, "ptiplayer").clear()
        driver.find_element(By.ID, "ptiplayer").send_keys(str(test_data["player_pti"]))
        
        # Fill in Partner PTI
        driver.find_element(By.ID, "ptipartner").clear()
        driver.find_element(By.ID, "ptipartner").send_keys(str(test_data["partner_pti"]))
        
        # Fill in Opponent 1 PTI
        driver.find_element(By.ID, "ptiopp1").clear()
        driver.find_element(By.ID, "ptiopp1").send_keys(str(test_data["opp1_pti"]))
        
        # Fill in Opponent 2 PTI
        driver.find_element(By.ID, "ptiopp2").clear()
        driver.find_element(By.ID, "ptiopp2").send_keys(str(test_data["opp2_pti"]))
        
        # Set experience levels
        exp_mapping = {
            "30+ matches": "3.2",
            "10-30 Matches": "4", 
            "1-10 matches": "5",
            "New Player": "7"
        }
        
        # Player experience
        player_exp_select = Select(driver.find_element(By.ID, "sigmaplayer"))
        player_exp_select.select_by_value(exp_mapping[test_data["player_exp"]])
        
        # Partner experience
        partner_exp_select = Select(driver.find_element(By.ID, "sigmapartner"))
        partner_exp_select.select_by_value(exp_mapping[test_data["partner_exp"]])
        
        # Opponent 1 experience
        opp1_exp_select = Select(driver.find_element(By.ID, "sigmaopp1"))
        opp1_exp_select.select_by_value(exp_mapping[test_data["opp1_exp"]])
        
        # Opponent 2 experience
        opp2_exp_select = Select(driver.find_element(By.ID, "sigmaopp2"))
        opp2_exp_select.select_by_value(exp_mapping[test_data["opp2_exp"]])
        
        # Fill in score
        driver.find_element(By.ID, "matchscore").clear()
        driver.find_element(By.ID, "matchscore").send_keys(test_data["score"])
        
        print("✅ All inputs filled")
        
        # Click calculate button
        calculate_btn = driver.find_element(By.ID, "calculateButton")
        calculate_btn.click()
        
        print("⏳ Calculating...")
        time.sleep(3)  # Wait for calculation
        
        # Extract results
        try:
            # Get the results elements
            spread_element = driver.find_element(By.ID, "lblSpread")
            adjustment_element = driver.find_element(By.ID, "lblAdjustment")
            
            # Before values
            player_before = driver.find_element(By.ID, "PlayerRating").text
            partner_before = driver.find_element(By.ID, "PartnerRating").text
            opp1_before = driver.find_element(By.ID, "Opp1Rating").text
            opp2_before = driver.find_element(By.ID, "Opp2Rating").text
            
            # After values
            player_after = driver.find_element(By.ID, "PlayerAdjRating").text
            partner_after = driver.find_element(By.ID, "PartnerAdjRating").text
            opp1_after = driver.find_element(By.ID, "Opp1AdjRating").text
            opp2_after = driver.find_element(By.ID, "Opp2AdjRating").text
            
            results = {
                "spread": spread_element.text,
                "adjustment": adjustment_element.text,
                "before": {
                    "player": player_before,
                    "partner": partner_before,
                    "opp1": opp1_before,
                    "opp2": opp2_before
                },
                "after": {
                    "player": player_after,
                    "partner": partner_after,
                    "opp1": opp1_after,
                    "opp2": opp2_after
                }
            }
            
            print("\n📈 ACTUAL Calculator Results:")
            print(f"   Spread: {results['spread']}")
            print(f"   Adjustment: {results['adjustment']}")
            print(f"\n📋 Before -> After:")
            print(f"   Player: {results['before']['player']} -> {results['after']['player']}")
            print(f"   Partner: {results['before']['partner']} -> {results['after']['partner']}")
            print(f"   Opp 1: {results['before']['opp1']} -> {results['after']['opp1']}")
            print(f"   Opp 2: {results['before']['opp2']} -> {results['after']['opp2']}")
            
            # Save results
            with open('scripts/actual_calculator_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n💾 Results saved to actual_calculator_results.json")
            
            return results
            
        except Exception as e:
            print(f"❌ Error extracting results: {e}")
            # Save page source for debugging
            with open('scripts/calculator_page_source.html', 'w') as f:
                f.write(driver.page_source)
            print("🐛 Page source saved for debugging")
            return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    scrape_tennis_calculator() 