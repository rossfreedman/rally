#!/usr/bin/env python3
"""
Fully Automated PTI Calculator Scraper

This script fully automates the PTI testing by:
1. Loading test cases
2. Opening the PTI calculator website
3. Inputting values into the form
4. Scraping all results (spread, adjustment, before/after PTI values)
5. Saving comprehensive results for analysis

No manual intervention required!
"""

import json
import time
import sys
from typing import Dict, List, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import traceback

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
    print("⚠️ webdriver-manager not installed. Install with: pip install webdriver-manager")

# Comprehensive test cases including strategic and edge cases
COMPREHENSIVE_TEST_CASES = [
    {
        "id": 1,
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,2-6,6-3",
        "description": "Original Known Case"
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
        "description": "Player Loses (Case 1 Reversed)"
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

def setup_chrome_driver(headless: bool = False) -> webdriver.Chrome:
    """Setup Chrome WebDriver with optimal settings and Mac ARM compatibility"""
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # Performance and stability options
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Speed up loading
    
    # Try multiple approaches to get a working ChromeDriver
    driver = None
    
    # Approach 1: Try system Chrome first (most reliable)
    try:
        print("   Trying system Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        print("   ✅ System Chrome successful!")
    except Exception as e:
        print(f"   ❌ System Chrome failed: {e}")
        
    # Approach 2: Try webdriver-manager with explicit version
    if not driver and WEBDRIVER_MANAGER_AVAILABLE:
        try:
            print("   Trying webdriver-manager with latest version...")
            service = Service(ChromeDriverManager(version="latest").install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("   ✅ WebDriver Manager successful!")
        except Exception as e:
            print(f"   ❌ WebDriver Manager failed: {e}")
    
    # Approach 3: Try specific Mac ARM paths
    if not driver:
        mac_arm_paths = [
            "/usr/local/bin/chromedriver",
            "/opt/homebrew/bin/chromedriver",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        
        for path in mac_arm_paths:
            try:
                print(f"   Trying Mac ARM path: {path}")
                if path.endswith("Google Chrome"):
                    # For Chrome app bundle, we need to use the system approach
                    continue
                service = Service(path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print(f"   ✅ Mac ARM path successful: {path}")
                break
            except Exception as e:
                print(f"   ❌ Mac ARM path {path} failed: {e}")
    
    if driver:
        # Set timeouts
        driver.implicitly_wait(10)
        driver.set_page_load_timeout(30)
        return driver
    else:
        # Final fallback with helpful error message
        print("\n❌ All ChromeDriver setup methods failed!")
        print("\n🔧 To fix this issue, try one of these solutions:")
        print("1. Install ChromeDriver via Homebrew:")
        print("   brew install --cask chromedriver")
        print("2. Or download manually:")
        print("   https://chromedriver.chromium.org/downloads")
        print("3. Or use system Chrome (make sure Chrome is installed)")
        
        raise Exception("Could not setup ChromeDriver. Please install Chrome and ChromeDriver.")

def experience_to_dropdown_text(exp_str: str) -> str:
    """Convert experience string to exact dropdown text"""
    mapping = {
        "30+": "30+ matches",
        "10-30": "10-30 Matches", 
        "1-10": "1-10 matches",
        "New": "New Player"
    }
    return mapping.get(exp_str, "30+ matches")

def wait_for_calculation(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    """Wait for PTI calculation to complete by checking for results"""
    try:
        # Wait for spread value to appear and be non-empty
        WebDriverWait(driver, timeout).until(
            lambda d: d.find_elements(By.XPATH, "//h6[contains(text(), 'Spread:')]") and
                     d.find_element(By.XPATH, "//h6[contains(text(), 'Spread:')]").text.strip() != "Spread:"
        )
        time.sleep(1)  # Additional buffer for all calculations
        return True
    except TimeoutException:
        print("⚠️ Calculation timeout - proceeding anyway")
        return False

def extract_comprehensive_results(driver: webdriver.Chrome, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Extract all available results from the PTI calculator"""
    results = {
        "id": test_case["id"],
        "description": test_case["description"],
        "input": test_case,
        "success": False,
        "error": None
    }
    
    try:
        # Extract intermediate calculations
        try:
            spread_element = driver.find_element(By.XPATH, "//h6[contains(text(), 'Spread:')]")
            spread_text = spread_element.text.replace("Spread:", "").strip()
            results["spread"] = float(spread_text) if spread_text else 0.0
        except:
            results["spread"] = 0.0
            
        try:
            adjustment_element = driver.find_element(By.XPATH, "//h6[contains(text(), 'Adjustment:')]")
            adjustment_text = adjustment_element.text.replace("Adjustment:", "").strip()
            results["adjustment"] = float(adjustment_text) if adjustment_text else 0.0
        except:
            results["adjustment"] = 0.0
        
        # Extract Before values
        before_values = {}
        try:
            before_section = driver.find_element(By.XPATH, "//h5[text()='Before']")
            before_elements = before_section.find_elements(By.XPATH, "./following-sibling::h6")
            
            for element in before_elements:
                text = element.text.strip()
                if "Player PTI:" in text:
                    before_values["player_pti"] = float(text.split(':')[1].strip())
                elif "Player Mu:" in text:
                    before_values["player_mu"] = float(text.split(':')[1].strip())
                elif "Player Sigma:" in text:
                    before_values["player_sigma"] = float(text.split(':')[1].strip())
                elif "Partner PTI:" in text:
                    before_values["partner_pti"] = float(text.split(':')[1].strip())
                elif "Partner Mu:" in text:
                    before_values["partner_mu"] = float(text.split(':')[1].strip())
                elif "Partner Sigma:" in text:
                    before_values["partner_sigma"] = float(text.split(':')[1].strip())
                elif text.startswith("Opp PTI:"):
                    value = float(text.split(':')[1].strip())
                    if "opp1_pti" not in before_values:
                        before_values["opp1_pti"] = value
                    else:
                        before_values["opp2_pti"] = value
                elif text.startswith("Opp Mu:"):
                    value = float(text.split(':')[1].strip())
                    if "opp1_mu" not in before_values:
                        before_values["opp1_mu"] = value
                    else:
                        before_values["opp2_mu"] = value
                elif text.startswith("Opp Sigma:"):
                    value = float(text.split(':')[1].strip())
                    if "opp1_sigma" not in before_values:
                        before_values["opp1_sigma"] = value
                    else:
                        before_values["opp2_sigma"] = value
        except Exception as e:
            print(f"⚠️ Error extracting before values: {e}")
        
        results["before"] = before_values
        
        # Extract After values
        after_values = {}
        try:
            after_section = driver.find_element(By.XPATH, "//h5[text()='After']")
            after_elements = after_section.find_elements(By.XPATH, "./following-sibling::h6")
            
            for element in after_elements:
                text = element.text.strip()
                if "Player PTI:" in text:
                    after_values["player_pti"] = float(text.split(':')[1].strip())
                elif "Player Mu:" in text:
                    after_values["player_mu"] = float(text.split(':')[1].strip())
                elif "Player Sigma:" in text:
                    after_values["player_sigma"] = float(text.split(':')[1].strip())
                elif "Partner PTI:" in text:
                    after_values["partner_pti"] = float(text.split(':')[1].strip())
                elif "Partner Mu:" in text:
                    after_values["partner_mu"] = float(text.split(':')[1].strip())
                elif "Partner Sigma:" in text:
                    after_values["partner_sigma"] = float(text.split(':')[1].strip())
                elif text.startswith("Opp PTI:"):
                    value = float(text.split(':')[1].strip())
                    if "opp1_pti" not in after_values:
                        after_values["opp1_pti"] = value
                    else:
                        after_values["opp2_pti"] = value
                elif text.startswith("Opp Mu:"):
                    value = float(text.split(':')[1].strip())
                    if "opp1_mu" not in after_values:
                        after_values["opp1_mu"] = value
                    else:
                        after_values["opp2_mu"] = value
                elif text.startswith("Opp Sigma:"):
                    value = float(text.split(':')[1].strip())
                    if "opp1_sigma" not in after_values:
                        after_values["opp1_sigma"] = value
                    else:
                        after_values["opp2_sigma"] = value
        except Exception as e:
            print(f"⚠️ Error extracting after values: {e}")
        
        results["after"] = after_values
        results["success"] = True
        
        return results
        
    except Exception as e:
        results["error"] = str(e)
        results["success"] = False
        print(f"❌ Error extracting results: {e}")
        return results

def test_single_case_comprehensive(driver: webdriver.Chrome, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single case with comprehensive result extraction"""
    print(f"\n🧪 Testing Case {test_case['id']}: {test_case['description']}")
    print(f"   PTIs: {test_case['player_pti']}/{test_case['partner_pti']} vs {test_case['opp1_pti']}/{test_case['opp2_pti']}")
    print(f"   Score: {test_case['score']}")
    
    try:
        # Navigate to calculator
        print("   📡 Loading PTI calculator...")
        driver.get("https://calc.platform.tennis/calculator2.html")
        
        # Wait for page to load completely
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "player_pti"))
        )
        
        # Clear and fill Player PTI
        player_pti_field = driver.find_element(By.NAME, "player_pti")
        player_pti_field.clear()
        player_pti_field.send_keys(str(test_case["player_pti"]))
        
        # Set Player Experience
        player_exp_dropdown = Select(driver.find_element(By.NAME, "player_exp"))
        player_exp_dropdown.select_by_visible_text(experience_to_dropdown_text(test_case["player_exp"]))
        
        # Clear and fill Partner PTI
        partner_pti_field = driver.find_element(By.NAME, "partner_pti")
        partner_pti_field.clear()
        partner_pti_field.send_keys(str(test_case["partner_pti"]))
        
        # Set Partner Experience
        partner_exp_dropdown = Select(driver.find_element(By.NAME, "partner_exp"))
        partner_exp_dropdown.select_by_visible_text(experience_to_dropdown_text(test_case["partner_exp"]))
        
        # Clear and fill Score
        score_field = driver.find_element(By.NAME, "score")
        score_field.clear()
        score_field.send_keys(test_case["score"])
        
        # Clear and fill Opponent 1 PTI
        opp1_pti_field = driver.find_element(By.NAME, "opp1_pti")
        opp1_pti_field.clear()
        opp1_pti_field.send_keys(str(test_case["opp1_pti"]))
        
        # Set Opponent 1 Experience
        opp1_exp_dropdown = Select(driver.find_element(By.NAME, "opp1_exp"))
        opp1_exp_dropdown.select_by_visible_text(experience_to_dropdown_text(test_case["opp1_exp"]))
        
        # Clear and fill Opponent 2 PTI
        opp2_pti_field = driver.find_element(By.NAME, "opp2_pti")
        opp2_pti_field.clear()
        opp2_pti_field.send_keys(str(test_case["opp2_pti"]))
        
        # Set Opponent 2 Experience
        opp2_exp_dropdown = Select(driver.find_element(By.NAME, "opp2_exp"))
        opp2_exp_dropdown.select_by_visible_text(experience_to_dropdown_text(test_case["opp2_exp"]))
        
        # Wait for calculation to complete
        print("   ⏳ Waiting for calculation...")
        wait_for_calculation(driver)
        
        # Extract comprehensive results
        print("   📊 Extracting results...")
        results = extract_comprehensive_results(driver, test_case)
        
        if results["success"]:
            print(f"   ✅ Success! Adjustment: {results.get('adjustment', 'N/A'):.2f}")
            if results.get('after', {}).get('player_pti'):
                print(f"   📈 Player PTI: {test_case['player_pti']} → {results['after']['player_pti']:.2f}")
        else:
            print(f"   ❌ Failed: {results.get('error', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        error_msg = f"Exception in test case {test_case['id']}: {str(e)}"
        print(f"   ❌ {error_msg}")
        return {
            "id": test_case["id"],
            "description": test_case["description"],
            "input": test_case,
            "success": False,
            "error": error_msg
        }

def run_fully_automated_testing(headless: bool = True, max_cases: Optional[int] = None) -> List[Dict[str, Any]]:
    """Run fully automated testing on all test cases"""
    print("🚀 Fully Automated PTI Calculator Scraper")
    print("=" * 60)
    print(f"🎯 Testing {len(COMPREHENSIVE_TEST_CASES)} comprehensive test cases")
    print(f"🌐 Target: https://calc.platform.tennis/calculator2.html")
    print(f"🔧 Headless mode: {'ON' if headless else 'OFF'}")
    
    # Setup driver
    print("\n🔧 Setting up Chrome WebDriver...")
    driver = setup_chrome_driver(headless=headless)
    
    results = []
    successful_tests = 0
    failed_tests = 0
    
    try:
        test_cases = COMPREHENSIVE_TEST_CASES[:max_cases] if max_cases else COMPREHENSIVE_TEST_CASES
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'='*60}")
            print(f"Progress: {i}/{len(test_cases)}")
            
            result = test_single_case_comprehensive(driver, test_case)
            results.append(result)
            
            if result["success"]:
                successful_tests += 1
            else:
                failed_tests += 1
            
            # Brief pause between tests
            time.sleep(2)
        
        # Save comprehensive results
        timestamp = int(time.time())
        filename = f"fully_automated_results_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(results, f, indent=2)
        
        # Also save in standard format for analysis
        with open("comprehensive_pti_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*60}")
        print("🎉 FULLY AUTOMATED TESTING COMPLETE!")
        print(f"✅ Successful tests: {successful_tests}/{len(test_cases)}")
        print(f"❌ Failed tests: {failed_tests}/{len(test_cases)}")
        print(f"📄 Results saved to: {filename}")
        print(f"📄 Analysis copy: comprehensive_pti_results.json")
        
        if successful_tests > 0:
            print(f"\n📊 Sample Results:")
            for result in results[:3]:
                if result["success"]:
                    adj = result.get("adjustment", 0)
                    before_pti = result.get("before", {}).get("player_pti", 0)
                    after_pti = result.get("after", {}).get("player_pti", 0)
                    print(f"   Case {result['id']}: Adj={adj:.2f}, Player {before_pti}→{after_pti:.1f}")
        
        return results
        
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        return results
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        traceback.print_exc()
        return results
    finally:
        print("\n🔒 Closing browser...")
        driver.quit()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fully Automated PTI Calculator Scraper")
    parser.add_argument("--headless", action="store_true", default=True,
                       help="Run in headless mode (default: True)")
    parser.add_argument("--visible", action="store_true",
                       help="Run with visible browser (overrides headless)")
    parser.add_argument("--max-cases", type=int,
                       help="Maximum number of test cases to run")
    parser.add_argument("--quick", action="store_true",
                       help="Quick test with first 5 cases only")
    
    args = parser.parse_args()
    
    # Determine headless mode
    headless = args.headless and not args.visible
    
    # Determine max cases
    max_cases = None
    if args.quick:
        max_cases = 5
    elif args.max_cases:
        max_cases = args.max_cases
    
    print("🎯 Configuration:")
    print(f"   Headless: {'Yes' if headless else 'No'}")
    print(f"   Max cases: {max_cases or 'All 15'}")
    
    # Run the testing
    results = run_fully_automated_testing(headless=headless, max_cases=max_cases)
    
    # Quick analysis
    if results:
        successful = [r for r in results if r.get("success", False)]
        if len(successful) >= 3:
            print(f"\n🔍 Quick Analysis:")
            adjustments = [r.get("adjustment", 0) for r in successful]
            avg_adj = sum(adjustments) / len(adjustments)
            print(f"   Average adjustment: {avg_adj:.2f}")
            print(f"   Adjustment range: {min(adjustments):.2f} to {max(adjustments):.2f}")
    
    print(f"\n✨ Run 'python analyze_focused_results.py' to analyze the results!")

if __name__ == "__main__":
    main() 