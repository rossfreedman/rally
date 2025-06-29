#!/usr/bin/env python3
"""
Calibrate PTI Algorithm from Real Data

Instead of comparing against our Node.js approximation, let's create strategic test cases
that can be manually verified against the original site to improve calibration.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.pti_calculator_service_v3 import calculate_pti_v3
import json

# Strategic test cases that cover key scenarios
# These should be manually tested on the original site for accurate calibration
CALIBRATION_CASES = [
    {
        "id": "original",
        "player_pti": 50.0, "partner_pti": 40.0, "opp1_pti": 30.0, "opp2_pti": 23.0,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,2-6,6-3",
        "description": "Original verified case",
        "expected": {
            "adjustment": 2.30,
            "player_after": 47.70,
            "partner_after": 37.70,
            "opp1_after": 32.39,
            "opp2_after": 25.39
        }
    },
    {
        "id": "new_players",
        "player_pti": 30.0, "partner_pti": 30.0, "opp1_pti": 30.0, "opp2_pti": 30.0,
        "player_exp": "New Player", "partner_exp": "New Player", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "New players vs experienced (equal PTI)",
        "expected": None  # To be manually tested
    },
    {
        "id": "mixed_10_30",
        "player_pti": 30.0, "partner_pti": 30.0, "opp1_pti": 30.0, "opp2_pti": 30.0,
        "player_exp": "10-30", "partner_exp": "10-30", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "10-30 experience vs experienced (equal PTI)",
        "expected": None  # To be manually tested
    },
    {
        "id": "mixed_1_10",
        "player_pti": 30.0, "partner_pti": 30.0, "opp1_pti": 30.0, "opp2_pti": 30.0,
        "player_exp": "1-10", "partner_exp": "1-10", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "1-10 experience vs experienced (equal PTI)",
        "expected": None  # To be manually tested
    },
    {
        "id": "big_spread",
        "player_pti": 45.0, "partner_pti": 45.0, "opp1_pti": 25.0, "opp2_pti": 25.0,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Big spread, favorites win",
        "expected": None  # To be manually tested
    }
]

def test_calibration_cases():
    """Test our algorithm against strategic calibration cases"""
    print("🎯 PTI Algorithm Calibration Test")
    print("=" * 50)
    
    print("Testing strategic cases to identify calibration issues...\n")
    
    results = []
    
    for case in CALIBRATION_CASES:
        print(f"📋 Case: {case['description']}")
        print(f"   PTIs: {case['player_pti']}/{case['partner_pti']} vs {case['opp1_pti']}/{case['opp2_pti']}")
        print(f"   Exp:  {case['player_exp']}/{case['partner_exp']} vs {case['opp1_exp']}/{case['opp2_exp']}")
        print(f"   Score: {case['score']}")
        
        result = calculate_pti_v3(
            player_pti=case["player_pti"],
            partner_pti=case["partner_pti"],
            opp1_pti=case["opp1_pti"],
            opp2_pti=case["opp2_pti"],
            player_exp=case["player_exp"],
            partner_exp=case["partner_exp"],
            opp1_exp=case["opp1_exp"],
            opp2_exp=case["opp2_exp"],
            match_score=case["score"]
        )
        
        if result["success"]:
            details = result["result"]["details"]
            res = result["result"]
            
            print(f"   Our result: Adjustment {res['adjustment']:.2f}")
            print(f"   Team multiplier: {details['team_multiplier']:.2f}")
            print(f"   Final K-factor: {details['final_k_factor']:.1f}")
            
            if case["expected"]:
                expected_adj = case["expected"]["adjustment"]
                actual_adj = res["adjustment"]
                diff = abs(expected_adj - actual_adj)
                print(f"   Expected: {expected_adj:.2f}, Difference: {diff:.2f}")
                
                if diff < 0.1:
                    print("   ✅ PERFECT match!")
                elif diff < 0.5:
                    print("   ✅ EXCELLENT match!")
                elif diff < 1.0:
                    print("   ✅ GOOD match!")
                else:
                    print("   ⚠️ Needs calibration")
            else:
                print("   ❓ Manual verification needed")
                print(f"   Player: {case['player_pti']} → {res['after']['player']['pti']}")
                print(f"   Partner: {case['partner_pti']} → {res['after']['partner']['pti']}")
                print(f"   Opp1: {case['opp1_pti']} → {res['after']['opp1']['pti']}")
                print(f"   Opp2: {case['opp2_pti']} → {res['after']['opp2']['pti']}")
            
            case_result = {
                "case_id": case["id"],
                "description": case["description"],
                "our_adjustment": res["adjustment"],
                "our_results": {
                    "player_after": res["after"]["player"]["pti"],
                    "partner_after": res["after"]["partner"]["pti"],
                    "opp1_after": res["after"]["opp1"]["pti"],
                    "opp2_after": res["after"]["opp2"]["pti"]
                },
                "team_multiplier": details["team_multiplier"],
                "final_k_factor": details["final_k_factor"],
                "expected": case["expected"]
            }
            results.append(case_result)
            
        else:
            print(f"   ❌ Calculation failed: {result}")
        
        print()
    
    # Save results for manual verification
    with open("calibration_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("💾 Calibration results saved to calibration_test_results.json")
    
    return results

def generate_manual_test_instructions():
    """Generate instructions for manual testing on the original site"""
    print("\n📋 Manual Testing Instructions")
    print("=" * 45)
    
    print("To improve calibration, please test these cases on:")
    print("https://calc.platform.tennis/calculator2.html")
    print()
    
    for i, case in enumerate(CALIBRATION_CASES[1:], 2):  # Skip the verified original case
        print(f"🧪 Test Case {i}: {case['description']}")
        print(f"   Player PTI: {case['player_pti']}")
        print(f"   Partner PTI: {case['partner_pti']}")
        print(f"   Opp1 PTI: {case['opp1_pti']}")
        print(f"   Opp2 PTI: {case['opp2_pti']}")
        print(f"   Player Experience: {case['player_exp']}")
        print(f"   Partner Experience: {case['partner_exp']}")
        print(f"   Opp1 Experience: {case['opp1_exp']}")
        print(f"   Opp2 Experience: {case['opp2_exp']}")
        print(f"   Match Score: {case['score']}")
        print("   Record: Adjustment, Player After, Partner After, Opp1 After, Opp2 After")
        print()

def suggest_calibration_improvements(results):
    """Suggest calibration improvements based on results"""
    print("🔧 Calibration Improvement Suggestions")
    print("=" * 50)
    
    # Analyze patterns in our results
    experienced_k = None
    new_player_k = None
    mixed_k_values = []
    
    for result in results:
        if result["case_id"] == "original":
            experienced_k = result["final_k_factor"]
        elif "New Player" in result["description"]:
            new_player_k = result["final_k_factor"]
        elif result["team_multiplier"] != 1.0:
            mixed_k_values.append((result["team_multiplier"], result["final_k_factor"]))
    
    print(f"Current K-factor patterns:")
    if experienced_k:
        print(f"  Experienced players (30+): {experienced_k:.1f}")
    if new_player_k:
        print(f"  New players: {new_player_k:.1f}")
    
    print("\nNext steps:")
    print("1. Test the cases above on the original site")
    print("2. Update the expected results in this script")
    print("3. Adjust the global calibration factor if needed")
    print("4. Re-run calibration to verify improvements")

def main():
    """Main calibration function"""
    print("🚀 PTI Algorithm Calibration System")
    print("=" * 60)
    
    # Test current calibration
    results = test_calibration_cases()
    
    # Generate manual test instructions
    generate_manual_test_instructions()
    
    # Suggest improvements
    suggest_calibration_improvements(results)
    
    print("\n🎯 Calibration Testing Complete!")
    print("Use the manual test cases above to improve accuracy.")

if __name__ == "__main__":
    main() 