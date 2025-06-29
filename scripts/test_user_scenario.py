#!/usr/bin/env python3
"""
Test User's Exact PTI Scenario

Testing the exact values from the user's screenshot:
- Player PTI: 70 (30+ matches)  
- Partner PTI: 40 (30+ matches)
- Score: 6-2, 2-6, 6-3
- Opp PTI: 30 (30+ matches) 
- Opp PTI: 23 (10-30 matches)

Expected results should be reasonable PTI adjustments (typically 0.5-3.0 points)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pti_calculator_service_v4 import calculate_pti_v4

def test_user_scenario():
    """Test the exact scenario from user's screenshot"""
    
    print("🧪 Testing User's PTI Scenario")
    print("=" * 50)
    
    # Exact inputs from user's screenshot
    test_case = {
        "player_pti": 70.0,
        "partner_pti": 40.0,
        "opp1_pti": 30.0,
        "opp2_pti": 23.0,
        "player_exp": "30+ matches",  # Maps to "30+"
        "partner_exp": "30+ matches", # Maps to "30+"
        "opp1_exp": "30+ matches",    # Maps to "30+"
        "opp2_exp": "10-30 Matches",  # Maps to "10-30"
        "match_score": "6-2,2-6,6-3"
    }
    
    print("📊 Input Values:")
    print(f"   Player PTI: {test_case['player_pti']} ({test_case['player_exp']})")
    print(f"   Partner PTI: {test_case['partner_pti']} ({test_case['partner_exp']})")  
    print(f"   Score: {test_case['match_score']}")
    print(f"   Opp 1 PTI: {test_case['opp1_pti']} ({test_case['opp1_exp']})")
    print(f"   Opp 2 PTI: {test_case['opp2_pti']} ({test_case['opp2_exp']})")
    
    # Run calculation
    result = calculate_pti_v4(**test_case)
    
    if result.get("success"):
        calc_result = result["result"]
        
        print(f"\n📈 V4 Algorithm Results:")
        print(f"   Spread: {calc_result['spread']}")
        print(f"   Adjustment: {calc_result['adjustment']}")
        
        print(f"\n📋 Before -> After:")
        print(f"   Player: {calc_result['before']['player']['pti']:.1f} -> {calc_result['after']['player']['pti']:.6f}")
        print(f"   Partner: {calc_result['before']['partner']['pti']:.1f} -> {calc_result['after']['partner']['pti']:.6f}")
        print(f"   Opp 1: {calc_result['before']['opp1']['pti']:.1f} -> {calc_result['after']['opp1']['pti']:.6f}")
        print(f"   Opp 2: {calc_result['before']['opp2']['pti']:.1f} -> {calc_result['after']['opp2']['pti']:.6f}")
        
        # Analysis
        print(f"\n🔍 Analysis:")
        details = calc_result.get("details", {})
        print(f"   Team 1 Avg: {details.get('team1_avg', 'N/A')}")
        print(f"   Team 2 Avg: {details.get('team2_avg', 'N/A')}")
        print(f"   Expected Prob: {details.get('expected_prob', 'N/A')}")
        print(f"   Player Wins: {details.get('player_wins', 'N/A')}")
        print(f"   Experience Multiplier: {details.get('experience_multiplier', 'N/A')}")
        print(f"   K-factor: {details.get('k_factor', 'N/A')}")
        
        # Sanity check
        adjustment = calc_result['adjustment']
        if adjustment > 10:
            print(f"\n❌ ISSUE: Adjustment of {adjustment:.6f} is unrealistically high!")
            print(f"   Normal PTI adjustments are typically 0.5-3.0 points")
        elif adjustment < 0.1:
            print(f"\n⚠️  WARNING: Adjustment of {adjustment:.6f} seems very low")
        else:
            print(f"\n✅ Adjustment of {adjustment:.6f} is within reasonable range")
            
    else:
        print(f"\n❌ Calculation failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_user_scenario() 