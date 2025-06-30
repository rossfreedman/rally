#!/usr/bin/env python3
"""
Automated PTI Calculator Testing

This script automatically tests the 15 strategic test cases on the original
PTI calculator site and extracts the results for analysis.

Requirements:
pip install selenium webdriver-manager
"""

import json
import time
from typing import Dict, List, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Test cases from focused_test_cases.md
STRATEGIC_TEST_CASES = [
    {
        "id": 1,
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,2-6,6-3",
        "description": "Your Original Case (Known Result)"
    },
    {
        "id": 2,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Equal Teams, Player Wins"
    },
    {
        "id": 3,
        "player_pti": 40, "partner_pti": 40, "opp1_pti": 25, "opp2_pti": 25,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Big Underdogs Win (Upset)"
    },
    {
        "id": 4,
        "player_pti": 25, "partner_pti": 25, "opp1_pti": 40, "opp2_pti": 40,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Big Favorites Win (Expected)"
    },
    {
        "id": 5,
        "player_pti": 28, "partner_pti": 32, "opp1_pti": 30, "opp2_pti": 35,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "7-5,6-4",
        "description": "Close Match, Favorites Win"
    },
    {
        "id": 6,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "New", "partner_exp": "New", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Different Experience Levels"
    },
    {
        "id": 7,
        "player_pti": 25, "partner_pti": 25, "opp1_pti": 40, "opp2_pti": 40,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-1,6-2",
        "description": "Blowout Win by Favorites"
    },
    {
        "id": 8,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 32, "opp2_pti": 32,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "7-6,4-6,7-6",
        "description": "Very Close 3-Set Match"
    },
    {
        "id": 9,
        "player_pti": 20, "partner_pti": 20, "opp1_pti": 50, "opp2_pti": 50,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "High PTI vs Low PTI"
    },
    {
        "id": 10,
        "player_pti": 50, "partner_pti": 20, "opp1_pti": 35, "opp2_pti": 35,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Mixed Team vs Balanced Team"
    },
    {
        "id": 11,
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "2-6,6-2,3-6",
        "description": "Player Loses (Same as Case 1 but Reversed Score)"
    },
    {
        "id": 12,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "10-30", "partner_exp": "10-30", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Moderate Experience vs Experienced"
    },
    {
        "id": 13,
        "player_pti": 45, "partner_pti": 45, "opp1_pti": 25, "opp2_pti": 25,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,6-3",
        "description": "Large Spread, Underdogs Win"
    },
    {
        "id": 14,
        "player_pti": 29, "partner_pti": 31, "opp1_pti": 32, "opp2_pti": 32,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Small Spread, Favorites Win"
    },
    {
        "id": 15,
        "player_pti": 35, "partner_pti": 35, "opp1_pti": 35, "opp2_pti": 35,
        "player_exp": "1-10", "partner_exp": "1-10", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Same PTIs, Different Experience"
    }
]

def setup_driver(headless=True):
    """Setup Chrome WebDriver"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    
    try:
        # Try with webdriver-manager first
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"WebDriver Manager failed: {e}")
        print("Trying with system Chrome...")
        
        # Fallback to system Chrome
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e2:
            print(f"System Chrome failed: {e2}")
            print("Please install Chrome and ChromeDriver manually")
            raise e2

def experience_to_dropdown_value(exp_str: str) -> str:
    """Convert experience string to dropdown value"""
    mapping = {
        "30+": "30+ matches",
        "10-30": "10-30 Matches", 
        "1-10": "1-10 matches",
        "New": "New Player"
    }
    return mapping.get(exp_str, "30+ matches")

def extract_intermediate_calculations(driver) -> Dict[str, float]:
    """Extract spread and adjustment from intermediate calculations"""
    try:
        # Wait for calculations to complete
        time.sleep(2)
        
        # Look for the spread value
        spread_text = driver.find_element(By.XPATH, "//h6[contains(text(), 'Spread:')]").text
        spread = float(spread_text.split(':')[1].strip())
        
        # Look for the adjustment value  
        adjustment_text = driver.find_element(By.XPATH, "//h6[contains(text(), 'Adjustment:')]").text
        adjustment = float(adjustment_text.split(':')[1].strip())
        
        return {"spread": spread, "adjustment": adjustment}
    except Exception as e:
        print(f"❌ Error extracting intermediate calculations: {e}")
        return {"spread": 0, "adjustment": 0}

def extract_before_after_values(driver) -> Dict[str, Dict[str, float]]:
    """Extract before/after PTI values"""
    try:
        # Wait for all calculations to complete
        time.sleep(3)
        
        # Extract Before values
        before_values = {}
        before_sections = driver.find_elements(By.XPATH, "//h5[text()='Before']/following-sibling::h6")
        for section in before_sections:
            text = section.text
            if "Player PTI:" in text:
                before_values["player"] = float(text.split(':')[1].strip())
            elif "Partner PTI:" in text:
                before_values["partner"] = float(text.split(':')[1].strip())
            elif text.startswith("Opp PTI:"):
                if "opp1" not in before_values:
                    before_values["opp1"] = float(text.split(':')[1].strip())
                else:
                    before_values["opp2"] = float(text.split(':')[1].strip())
        
        # Extract After values
        after_values = {}
        after_sections = driver.find_elements(By.XPATH, "//h5[text()='After']/following-sibling::h6")
        for section in after_sections:
            text = section.text
            if "Player PTI:" in text:
                after_values["player"] = float(text.split(':')[1].strip())
            elif "Partner PTI:" in text:
                after_values["partner"] = float(text.split(':')[1].strip())
            elif text.startswith("Opp PTI:"):
                if "opp1" not in after_values:
                    after_values["opp1"] = float(text.split(':')[1].strip())
                else:
                    after_values["opp2"] = float(text.split(':')[1].strip())
        
        return {"before": before_values, "after": after_values}
    except Exception as e:
        print(f"❌ Error extracting before/after values: {e}")
        return {"before": {}, "after": {}}

def test_single_case(driver, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single case on the PTI calculator"""
    print(f"Testing Case {test_case['id']}: {test_case['description']}")
    
    try:
        # Navigate to the calculator
        driver.get("https://calc.platform.tennis/calculator2.html")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "player_pti"))
        )
        
        # Fill in Player PTI and Experience
        driver.find_element(By.NAME, "player_pti").clear()
        driver.find_element(By.NAME, "player_pti").send_keys(str(test_case["player_pti"]))
        
        player_exp_dropdown = Select(driver.find_element(By.NAME, "player_exp"))
        player_exp_dropdown.select_by_visible_text(experience_to_dropdown_value(test_case["player_exp"]))
        
        # Fill in Partner PTI and Experience
        driver.find_element(By.NAME, "partner_pti").clear()
        driver.find_element(By.NAME, "partner_pti").send_keys(str(test_case["partner_pti"]))
        
        partner_exp_dropdown = Select(driver.find_element(By.NAME, "partner_exp"))
        partner_exp_dropdown.select_by_visible_text(experience_to_dropdown_value(test_case["partner_exp"]))
        
        # Fill in Score
        driver.find_element(By.NAME, "score").clear()
        driver.find_element(By.NAME, "score").send_keys(test_case["score"])
        
        # Fill in Opponent 1 PTI and Experience
        driver.find_element(By.NAME, "opp1_pti").clear()
        driver.find_element(By.NAME, "opp1_pti").send_keys(str(test_case["opp1_pti"]))
        
        opp1_exp_dropdown = Select(driver.find_element(By.NAME, "opp1_exp"))
        opp1_exp_dropdown.select_by_visible_text(experience_to_dropdown_value(test_case["opp1_exp"]))
        
        # Fill in Opponent 2 PTI and Experience
        driver.find_element(By.NAME, "opp2_pti").clear()
        driver.find_element(By.NAME, "opp2_pti").send_keys(str(test_case["opp2_pti"]))
        
        opp2_exp_dropdown = Select(driver.find_element(By.NAME, "opp2_exp"))
        opp2_exp_dropdown.select_by_visible_text(experience_to_dropdown_value(test_case["opp2_exp"]))
        
        # Trigger calculation (form should auto-calculate)
        time.sleep(3)
        
        # Extract results
        intermediate = extract_intermediate_calculations(driver)
        before_after = extract_before_after_values(driver)
        
        result = {
            "id": test_case["id"],
            "description": test_case["description"],
            "spread": intermediate["spread"],
            "adjustment": intermediate["adjustment"],
            "player_before": before_after["before"].get("player", test_case["player_pti"]),
            "player_after": before_after["after"].get("player", 0),
            "partner_before": before_after["before"].get("partner", test_case["partner_pti"]),
            "partner_after": before_after["after"].get("partner", 0),
            "opp1_before": before_after["before"].get("opp1", test_case["opp1_pti"]),
            "opp1_after": before_after["after"].get("opp1", 0),
            "opp2_before": before_after["before"].get("opp2", test_case["opp2_pti"]),
            "opp2_after": before_after["after"].get("opp2", 0),
            "success": True
        }
        
        print(f"  ✅ Success: Adjustment {result['adjustment']:.2f}")
        return result
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {
            "id": test_case["id"],
            "description": test_case["description"],
            "error": str(e),
            "success": False
        }

def main():
    """Main automation function"""
    print("🤖 Automated PTI Calculator Testing")
    print("=" * 50)
    
    # Setup driver
    print("Setting up Chrome WebDriver...")
    driver = setup_driver(headless=False)  # Set to True for headless mode
    
    try:
        results = []
        
        for test_case in STRATEGIC_TEST_CASES:
            result = test_single_case(driver, test_case)
            results.append(result)
            time.sleep(2)  # Brief pause between tests
        
        # Save results
        with open("automated_focused_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Completed! Saved {len(results)} results to automated_focused_results.json")
        
        # Show summary
        successful = sum(1 for r in results if r.get("success", False))
        print(f"Successful tests: {successful}/{len(results)}")
        
        if successful > 0:
            print("\n🔍 Running analysis...")
            # Copy results to expected filename for analysis
            with open("focused_results.json", "w") as f:
                json.dump([r for r in results if r.get("success", False)], f, indent=2)
            
            # Import and run analysis
            import subprocess
            subprocess.run(["python", "analyze_focused_results.py"])
        
    finally:
        driver.quit()
        print("Browser closed.")

if __name__ == "__main__":
    main() 