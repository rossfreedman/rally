#!/usr/bin/env python3
"""
Test Our Reverse-Engineered PTI Algorithm

Compare our implementation against the expected results from the original site.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.pti_calculator_service_v2 import calculate_pti_v2
import json

def test_original_case():
    """Test against the original known case"""
    print("🧪 Testing Original Case (Your Test Case)")
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
    
    # Our calculation
    result = calculate_pti_v2(
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
        
        print("Expected vs Actual Results:")
        print("-" * 30)
        print(f"Player PTI:  {expected['player_before']} → {expected['player_after']} | Our: {actual['before']['player']['pti']} → {actual['after']['player']['pti']}")
        print(f"Partner PTI: {expected['partner_before']} → {expected['partner_after']} | Our: {actual['before']['partner']['pti']} → {actual['after']['partner']['pti']}")
        print(f"Opp1 PTI:    {expected['opp1_before']} → {expected['opp1_after']} | Our: {actual['before']['opp1']['pti']} → {actual['after']['opp1']['pti']}")
        print(f"Opp2 PTI:    {expected['opp2_before']} → {expected['opp2_after']} | Our: {actual['before']['opp2']['pti']} → {actual['after']['opp2']['pti']}")
        print(f"Adjustment:  {expected['adjustment']} | Our: {actual['adjustment']}")
        print(f"Spread:      {expected['spread']} | Our: {actual['spread']}")
        
        # Calculate accuracy
        player_diff = abs(expected['player_after'] - actual['after']['player']['pti'])
        partner_diff = abs(expected['partner_after'] - actual['after']['partner']['pti'])
        opp1_diff = abs(expected['opp1_after'] - actual['after']['opp1']['pti'])
        opp2_diff = abs(expected['opp2_after'] - actual['after']['opp2']['pti'])
        adj_diff = abs(expected['adjustment'] - actual['adjustment'])
        
        print("\nAccuracy Analysis:")
        print("-" * 20)
        print(f"Player PTI difference:  {player_diff:.2f}")
        print(f"Partner PTI difference: {partner_diff:.2f}")
        print(f"Opp1 PTI difference:    {opp1_diff:.2f}")
        print(f"Opp2 PTI difference:    {opp2_diff:.2f}")
        print(f"Adjustment difference:  {adj_diff:.2f}")
        
        avg_diff = (player_diff + partner_diff + opp1_diff + opp2_diff) / 4
        print(f"Average PTI difference: {avg_diff:.2f}")
        
        if avg_diff < 1.0:
            print("✅ EXCELLENT accuracy!")
        elif avg_diff < 2.0:
            print("✅ GOOD accuracy!")
        elif avg_diff < 5.0:
            print("⚠️ FAIR accuracy - needs improvement")
        else:
            print("❌ POOR accuracy - algorithm needs major fixes")
        
        print("\nAlgorithm Details:")
        print("-" * 18)
        if "details" in actual:
            details = actual["details"]
            print(f"Team averages: {details['team1_avg']} vs {details['team2_avg']}")
            print(f"Expected probability: {details['expected_prob']}")
            print(f"K-factor: {details['k_factor']}")
            print(f"Player wins: {details['player_wins']}")
        
    else:
        print("❌ Algorithm failed to calculate results")
        print(f"Error: {result}")
    
    return result

def test_multiple_cases():
    """Test against multiple cases from our automated analysis"""
    print("\n🧪 Testing Multiple Cases")
    print("=" * 50)
    
    # Load our automated results
    try:
        with open("focused_results.json", "r") as f:
            automated_results = json.load(f)
    except FileNotFoundError:
        print("❌ No automated results found. Run complete automation first.")
        return
    
    print(f"Testing against {len(automated_results)} automated cases...")
    
    total_diff = 0
    successful_tests = 0
    
    for case in automated_results[:5]:  # Test first 5 cases
        # Convert case to our API format
        result = calculate_pti_v2(
            player_pti=case["player_before"],
            partner_pti=case["partner_before"],
            opp1_pti=case["opp1_before"],
            opp2_pti=case["opp2_before"],
            player_exp="30+",  # Most test cases use this
            partner_exp="30+",
            opp1_exp="30+",
            opp2_exp="30+",
            match_score="6-4,6-4"  # Default score for wins
        )
        
        if result["success"]:
            expected_adj = case["adjustment"]
            actual_adj = result["result"]["adjustment"]
            diff = abs(expected_adj - actual_adj)
            total_diff += diff
            successful_tests += 1
            
            print(f"Case {case['id']}: Expected {expected_adj:.2f}, Got {actual_adj:.2f}, Diff: {diff:.2f}")
    
    if successful_tests > 0:
        avg_diff = total_diff / successful_tests
        print(f"\nOverall Average Difference: {avg_diff:.2f}")
        
        if avg_diff < 2.0:
            print("✅ Algorithm is performing well across multiple cases!")
        else:
            print("⚠️ Algorithm needs calibration adjustments")

def main():
    """Main test function"""
    print("🔬 PTI Algorithm Validation Tests")
    print("=" * 60)
    
    # Test original case
    test_original_case()
    
    # Test multiple cases
    test_multiple_cases()
    
    print("\n🎯 Summary")
    print("=" * 15)
    print("If accuracy is good, we can integrate this algorithm into the main PTI calculator.")
    print("If accuracy needs improvement, we can fine-tune the K-factors and multipliers.")

if __name__ == "__main__":
    main() 