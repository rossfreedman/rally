#!/usr/bin/env python3
"""
PTI Algorithm Reverse Engineering Tool

This script generates comprehensive test cases to compare results between:
1. Original site: https://calc.platform.tennis/calculator2.html
2. Our implementation: http://localhost:8080/pti-calculator

Usage:
1. Run this script to generate test cases
2. Manually test each case on the original site 
3. Run the same cases on our API
4. Analyze patterns to reverse engineer the algorithm
"""

import json
import requests
import itertools
from typing import Dict, List, Tuple, Any

def generate_test_cases() -> List[Dict[str, Any]]:
    """Generate comprehensive test cases covering various scenarios"""
    
    test_cases = []
    
    # PTI ranges to test
    pti_values = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
    
    # Experience levels
    exp_levels = [3.2, 4.0, 5.0, 7.0]  # 30+, 10-30, 1-10, new
    exp_names = ["30+", "10-30", "1-10", "new"]
    
    # Match scores (various outcomes)
    scores = [
        "6-2,6-3",      # Dominant win
        "6-4,6-4",      # Comfortable win  
        "7-5,6-4",      # Close win
        "6-2,2-6,6-3",  # 3-set win
        "2-6,6-3,7-5",  # Comeback win
        "6-7,7-6,7-6",  # Very close 3-set
        "2-6,3-6",      # Dominant loss
        "4-6,4-6",      # Comfortable loss
        "5-7,4-6",      # Close loss
    ]
    
    case_id = 1
    
    # Generate systematic test cases
    print("Generating test cases...")
    
    # Test cases with different PTI spreads
    for player_pti in [20, 30, 40, 50]:
        for partner_pti in [20, 30, 40, 50]:
            for opp1_pti in [20, 30, 40, 50]:
                for opp2_pti in [20, 30, 40, 50]:
                    for score in scores[:3]:  # Limit scores to keep manageable
                        # Skip cases where teams are identical
                        team1_avg = (player_pti + partner_pti) / 2
                        team2_avg = (opp1_pti + opp2_pti) / 2
                        
                        if abs(team1_avg - team2_avg) < 1:  # Skip very close teams
                            continue
                            
                        test_case = {
                            "id": case_id,
                            "player_pti": player_pti,
                            "partner_pti": partner_pti,
                            "opp1_pti": opp1_pti,
                            "opp2_pti": opp2_pti,
                            "player_exp": 3.2,
                            "partner_exp": 3.2,
                            "opp1_exp": 3.2,
                            "opp2_exp": 3.2,
                            "match_score": score,
                            "team1_avg": team1_avg,
                            "team2_avg": team2_avg,
                            "spread": team1_avg + team2_avg - opp1_pti - opp2_pti,
                            "team1_favored": team1_avg < team2_avg,
                            "player_wins": score.count('-') == 1 or (score.count('-') == 2 and int(score.split(',')[0].split('-')[0]) > int(score.split(',')[0].split('-')[1]))
                        }
                        test_cases.append(test_case)
                        case_id += 1
                        
                        if len(test_cases) >= 200:  # Limit to 200 cases
                            break
                    if len(test_cases) >= 200:
                        break
                if len(test_cases) >= 200:
                    break
            if len(test_cases) >= 200:
                break
        if len(test_cases) >= 200:
            break
    
    print(f"Generated {len(test_cases)} test cases")
    return test_cases

def test_our_api(test_case: Dict[str, Any], api_url: str = "http://localhost:8080/api/calculate-pti") -> Dict[str, Any]:
    """Test a case against our API"""
    
    payload = {
        "player_pti": test_case["player_pti"],
        "partner_pti": test_case["partner_pti"],
        "opp1_pti": test_case["opp1_pti"],
        "opp2_pti": test_case["opp2_pti"],
        "player_exp": test_case["player_exp"],
        "partner_exp": test_case["partner_exp"],
        "opp1_exp": test_case["opp1_exp"],
        "opp2_exp": test_case["opp2_exp"],
        "match_score": test_case["match_score"]
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return {
                    "success": True,
                    "spread": result["result"]["spread"],
                    "adjustment": result["result"]["adjustment"],
                    "player_before": result["result"]["before"]["player"]["pti"],
                    "player_after": result["result"]["after"]["player"]["pti"],
                    "partner_before": result["result"]["before"]["partner"]["pti"],
                    "partner_after": result["result"]["after"]["partner"]["pti"],
                    "opp1_before": result["result"]["before"]["opp1"]["pti"],
                    "opp1_after": result["result"]["after"]["opp1"]["pti"],
                    "opp2_before": result["result"]["before"]["opp2"]["pti"],
                    "opp2_after": result["result"]["after"]["opp2"]["pti"],
                }
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_manual_test_instructions(test_cases: List[Dict[str, Any]]) -> str:
    """Create instructions for manually testing on the original site"""
    
    instructions = """
# Manual Testing Instructions for Original Site

Visit: https://calc.platform.tennis/calculator2.html

For each test case below:
1. Enter the PTI values and experience levels
2. Enter the match score
3. Record the results (Spread, Adjustment, Before/After PTI values)
4. Save results in the format provided

Test Cases:
"""
    
    for i, case in enumerate(test_cases[:50]):  # First 50 cases for manual testing
        instructions += f"""
## Test Case {case['id']}
- Player PTI: {case['player_pti']}, Exp: 30+ matches
- Partner PTI: {case['partner_pti']}, Exp: 30+ matches  
- Opp1 PTI: {case['opp1_pti']}, Exp: 30+ matches
- Opp2 PTI: {case['opp2_pti']}, Exp: 30+ matches
- Score: {case['match_score']}
- Expected: {"Favorites win" if case['team1_favored'] and case['player_wins'] else "Underdogs win" if not case['team1_favored'] and case['player_wins'] else "Favorites lose" if case['team1_favored'] and not case['player_wins'] else "Underdogs lose"}

Record as JSON:
{{"id": {case['id']}, "spread": X.XX, "adjustment": X.XX, "player_before": {case['player_pti']}, "player_after": XX.XX, "partner_before": {case['partner_pti']}, "partner_after": XX.XX, "opp1_before": {case['opp1_pti']}, "opp1_after": XX.XX, "opp2_before": {case['opp2_pti']}, "opp2_after": XX.XX}}
"""
    
    return instructions

def run_api_tests(test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run all test cases against our API"""
    
    print("Testing our API...")
    results = []
    
    for i, case in enumerate(test_cases):
        print(f"Testing case {i+1}/{len(test_cases)}: {case['id']}")
        
        api_result = test_our_api(case)
        
        result = {
            "test_case": case,
            "our_result": api_result
        }
        results.append(result)
        
        if api_result["success"]:
            print(f"  ✅ Success: Adjustment {api_result['adjustment']}")
        else:
            print(f"  ❌ Error: {api_result['error']}")
    
    return results

def analyze_patterns(original_results: List[Dict], our_results: List[Dict]) -> None:
    """Analyze patterns between original site and our results"""
    
    print("\n=== PATTERN ANALYSIS ===")
    
    # Compare results where both succeeded
    matches = []
    discrepancies = []
    
    for orig, ours in zip(original_results, our_results):
        if orig.get("success") and ours["our_result"]["success"]:
            orig_adj = orig["adjustment"]
            our_adj = ours["our_result"]["adjustment"]
            
            if abs(orig_adj - our_adj) < 0.01:
                matches.append((orig, ours))
            else:
                discrepancies.append((orig, ours))
    
    print(f"Matches: {len(matches)}")
    print(f"Discrepancies: {len(discrepancies)}")
    
    if discrepancies:
        print("\nFirst 10 discrepancies:")
        for i, (orig, ours) in enumerate(discrepancies[:10]):
            case = ours["test_case"]
            print(f"Case {case['id']}: Original={orig['adjustment']:.2f}, Ours={ours['our_result']['adjustment']:.2f}")
            print(f"  Team1 avg: {case['team1_avg']}, Team2 avg: {case['team2_avg']}")
            print(f"  Score: {case['match_score']}, Player wins: {case['player_wins']}")

def main():
    """Main execution function"""
    
    print("PTI Algorithm Reverse Engineering Tool")
    print("=" * 50)
    
    # Generate test cases
    test_cases = generate_test_cases()
    
    # Save test cases for reference
    with open("pti_test_cases.json", "w") as f:
        json.dump(test_cases, f, indent=2)
    print(f"Saved {len(test_cases)} test cases to pti_test_cases.json")
    
    # Create manual testing instructions
    instructions = create_manual_test_instructions(test_cases)
    with open("manual_testing_instructions.md", "w") as f:
        f.write(instructions)
    print("Created manual_testing_instructions.md")
    
    # Test our API
    our_results = run_api_tests(test_cases)
    
    # Save our results
    with open("our_api_results.json", "w") as f:
        json.dump(our_results, f, indent=2)
    print("Saved our API results to our_api_results.json")
    
    print("\n=== NEXT STEPS ===")
    print("1. Follow instructions in manual_testing_instructions.md")
    print("2. Test first 50 cases on https://calc.platform.tennis/calculator2.html")
    print("3. Save original site results as 'original_site_results.json'")
    print("4. Run analysis to find patterns")
    print("\nExample original_site_results.json format:")
    print('[{"id": 1, "spread": 37.0, "adjustment": 2.30, "player_before": 50, "player_after": 47.70, ...}, ...]')

if __name__ == "__main__":
    main() 