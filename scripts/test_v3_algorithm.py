#!/usr/bin/env python3
"""
Test PTI Algorithm v3

Test the improved v3 algorithm with proper experience multiplier handling.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.pti_calculator_service_v3 import calculate_pti_v3

def test_original_case():
    """Test against the original known case"""
    print("🧪 Testing Original Case with PTI v3")
    print("=" * 50)
    
    # Expected results from original site
    expected = {
        "player_before": 50.00,
        "player_after": 47.70,
        "partner_before": 40.00,
        "partner_after": 37.70,
        "opp1_before": 30.00,
        "opp1_after": 32.39,
        "opp2_before": 23.00,
        "opp2_after": 25.39,
        "adjustment": 2.30,
        "spread": 37.0
    }
    
    # Our v3 calculation
    result = calculate_pti_v3(
        player_pti=50.0,
        partner_pti=40.0,
        opp1_pti=30.0,
        opp2_pti=23.0,
        player_exp="30+",
        partner_exp="30+",
        opp1_exp="30+",
        opp2_exp="30+",
        match_score="6-2,2-6,6-3"
    )
    
    if result["success"]:
        actual = result["result"]
        
        print("Expected vs v3 Results:")
        print("-" * 30)
        print(f"Player PTI:  {expected['player_before']} → {expected['player_after']} | v3: {actual['before']['player']['pti']} → {actual['after']['player']['pti']}")
        print(f"Partner PTI: {expected['partner_before']} → {expected['partner_after']} | v3: {actual['before']['partner']['pti']} → {actual['after']['partner']['pti']}")
        print(f"Opp1 PTI:    {expected['opp1_before']} → {expected['opp1_after']} | v3: {actual['before']['opp1']['pti']} → {actual['after']['opp1']['pti']}")
        print(f"Opp2 PTI:    {expected['opp2_before']} → {expected['opp2_after']} | v3: {actual['before']['opp2']['pti']} → {actual['after']['opp2']['pti']}")
        print(f"Adjustment:  {expected['adjustment']} | v3: {actual['adjustment']}")
        print(f"Spread:      {expected['spread']} | v3: {actual['spread']}")
        
        # Calculate accuracy
        player_diff = abs(expected['player_after'] - actual['after']['player']['pti'])
        partner_diff = abs(expected['partner_after'] - actual['after']['partner']['pti'])
        opp1_diff = abs(expected['opp1_after'] - actual['after']['opp1']['pti'])
        opp2_diff = abs(expected['opp2_after'] - actual['after']['opp2']['pti'])
        adj_diff = abs(expected['adjustment'] - actual['adjustment'])
        
        print("\nv3 Accuracy Analysis:")
        print("-" * 25)
        print(f"Player PTI difference:  {player_diff:.2f}")
        print(f"Partner PTI difference: {partner_diff:.2f}")
        print(f"Opp1 PTI difference:    {opp1_diff:.2f}")
        print(f"Opp2 PTI difference:    {opp2_diff:.2f}")
        print(f"Adjustment difference:  {adj_diff:.2f}")
        
        avg_diff = (player_diff + partner_diff + opp1_diff + opp2_diff) / 4
        print(f"Average PTI difference: {avg_diff:.2f}")
        
        if avg_diff < 0.1:
            print("✅ PERFECT accuracy!")
        elif avg_diff < 0.5:
            print("✅ EXCELLENT accuracy!")
        elif avg_diff < 1.0:
            print("✅ VERY GOOD accuracy!")
        elif avg_diff < 2.0:
            print("✅ GOOD accuracy!")
        else:
            print("⚠️ Needs improvement")
        
        print("\nv3 Algorithm Details:")
        print("-" * 22)
        if "details" in actual:
            details = actual["details"]
            print(f"Team multiplier: {details['team_multiplier']}")
            print(f"Experience K-factor: {details['experience_k']}")
            print(f"Final K-factor: {details['final_k_factor']}")
            print(f"Expected probability: {details['expected_prob']}")
            print(f"Player wins: {details['player_wins']}")
        
    else:
        print("❌ v3 Algorithm failed to calculate results")
        print(f"Error: {result}")
    
    return result

def test_experience_levels():
    """Test different experience level combinations"""
    print("\n🧪 Testing Experience Level Combinations")
    print("=" * 55)
    
    # Test cases with different experience levels
    test_cases = [
        {
            "name": "All Experienced (30+)",
            "exps": ["30+", "30+", "30+", "30+"],
            "expected_multiplier": 1.0
        },
        {
            "name": "All New Players",
            "exps": ["New Player", "New Player", "New Player", "New Player"],
            "expected_multiplier": 2.19
        },
        {
            "name": "Mixed: New vs Experienced",
            "exps": ["New Player", "New Player", "30+", "30+"],
            "expected_multiplier": 2.19
        },
        {
            "name": "Mixed: 1-10 vs 30+",
            "exps": ["1-10", "1-10", "30+", "30+"],
            "expected_multiplier": 1.56
        },
        {
            "name": "Mixed: 10-30 vs 30+",
            "exps": ["10-30", "10-30", "30+", "30+"],
            "expected_multiplier": 1.25
        }
    ]
    
    for case in test_cases:
        result = calculate_pti_v3(
            player_pti=30.0,
            partner_pti=30.0,
            opp1_pti=30.0,
            opp2_pti=30.0,
            player_exp=case["exps"][0],
            partner_exp=case["exps"][1],
            opp1_exp=case["exps"][2],
            opp2_exp=case["exps"][3],
            match_score="6-4,6-4"
        )
        
        if result["success"]:
            details = result["result"]["details"]
            adjustment = result["result"]["adjustment"]
            
            print(f"{case['name']}:")
            print(f"  Team multiplier: {details['team_multiplier']:.2f} (expected: {case['expected_multiplier']:.2f})")
            print(f"  Experience K: {details['experience_k']:.1f}")
            print(f"  Final K: {details['final_k_factor']:.1f}")
            print(f"  Adjustment: {adjustment:.2f}")
            print()

def main():
    """Main test function"""
    print("🔬 PTI Algorithm v3 Validation Tests")
    print("=" * 60)
    
    # Test original case
    test_original_case()
    
    # Test experience levels
    test_experience_levels()
    
    print("🎯 v3 Testing Complete!")
    print("If accuracy is good, we can run the 100-case test with v3.")

if __name__ == "__main__":
    main() 