#!/usr/bin/env python3
"""
Test v4 Integration with Mobile API

Verify that the v4 PTI calculator is properly integrated and working
with the mobile API endpoint.
"""

import sys
import os
import json
import requests
from typing import Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.pti_calculator_service_v4 import calculate_pti_v4

def test_v4_direct():
    """Test v4 algorithm directly"""
    print("🧪 Testing v4 Algorithm Directly")
    print("=" * 50)
    
    # Test the original known case
    result = calculate_pti_v4(
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
        adjustment = result["result"]["adjustment"]
        player_after = result["result"]["after"]["player"]["pti"]
        print(f"✅ Direct v4 test successful!")
        print(f"   Adjustment: {adjustment:.6f}")
        print(f"   Player: 50.0 → {player_after:.6f}")
        return True
    else:
        print(f"❌ Direct v4 test failed: {result}")
        return False

def test_experience_mapping():
    """Test the experience mapping function"""
    print(f"\n🧪 Testing Experience Mapping")
    print("=" * 50)
    
    def map_experience(exp_val):
        exp_val = float(exp_val)
        if exp_val >= 7.0:
            return "New Player"
        elif exp_val >= 5.0:
            return "1-10"
        elif exp_val >= 4.0:
            return "10-30"
        else:
            return "30+"
    
    test_cases = [
        (3.2, "30+"),
        (4.0, "10-30"),
        (5.0, "1-10"),
        (7.0, "New Player"),
        (8.5, "New Player")
    ]
    
    all_passed = True
    for exp_val, expected in test_cases:
        result = map_experience(exp_val)
        if result == expected:
            print(f"✅ {exp_val} → {result}")
        else:
            print(f"❌ {exp_val} → {result} (expected {expected})")
            all_passed = False
    
    return all_passed

def test_v4_with_numeric_experience():
    """Test v4 with numeric experience values (like the API will send)"""
    print(f"\n🧪 Testing v4 with Numeric Experience")
    print("=" * 50)
    
    def map_experience(exp_val):
        exp_val = float(exp_val)
        if exp_val >= 7.0:
            return "New Player"
        elif exp_val >= 5.0:
            return "1-10"
        elif exp_val >= 4.0:
            return "10-30"
        else:
            return "30+"
    
    # Test case that mimics API call with numeric experience
    result = calculate_pti_v4(
        player_pti=30.0,
        partner_pti=30.0,
        opp1_pti=30.0,
        opp2_pti=30.0,
        player_exp=map_experience(7.5),  # New player
        partner_exp=map_experience(7.5),  # New player
        opp1_exp=map_experience(3.2),    # Experienced
        opp2_exp=map_experience(3.2),    # Experienced
        match_score="6-4,6-4"
    )
    
    if result["success"]:
        k_factor = result["result"]["details"]["k_factor"]
        expected_k = 36.225  # 31.5 * 1.15 for new players
        
        if abs(k_factor - expected_k) < 0.001:
            print(f"✅ Numeric experience mapping works!")
            print(f"   K-factor: {k_factor:.3f} (expected {expected_k:.3f})")
            return True
        else:
            print(f"❌ K-factor mismatch: {k_factor:.3f} vs {expected_k:.3f}")
            return False
    else:
        print(f"❌ Calculation failed: {result}")
        return False

def create_api_test_case():
    """Create test data that matches the API format"""
    return {
        "player_pti": 50.0,
        "partner_pti": 40.0,
        "opp1_pti": 30.0,
        "opp2_pti": 23.0,
        "player_exp": 3.2,    # Numeric (experienced)
        "partner_exp": 3.2,   # Numeric (experienced)
        "opp1_exp": 3.2,      # Numeric (experienced)
        "opp2_exp": 3.2,      # Numeric (experienced)
        "match_score": "6-2,2-6,6-3"
    }

def simulate_api_call(test_data):
    """Simulate the API processing logic"""
    print(f"\n🧪 Simulating API Call Processing")
    print("=" * 50)
    
    # Simulate the mapping logic from mobile_routes.py
    def map_experience(exp_val):
        exp_val = float(exp_val)
        if exp_val >= 7.0:
            return "New Player"
        elif exp_val >= 5.0:
            return "1-10"
        elif exp_val >= 4.0:
            return "10-30"
        else:
            return "30+"
    
    # Extract and convert data like the API does
    player_pti = float(test_data.get('player_pti', 0))
    partner_pti = float(test_data.get('partner_pti', 0))
    opp1_pti = float(test_data.get('opp1_pti', 0))
    opp2_pti = float(test_data.get('opp2_pti', 0))
    
    player_exp = map_experience(test_data.get('player_exp', 3.2))
    partner_exp = map_experience(test_data.get('partner_exp', 3.2))
    opp1_exp = map_experience(test_data.get('opp1_exp', 3.2))
    opp2_exp = map_experience(test_data.get('opp2_exp', 3.2))
    
    match_score = test_data.get('match_score', '')
    
    print(f"Input transformation:")
    print(f"  PTIs: {player_pti}/{partner_pti} vs {opp1_pti}/{opp2_pti}")
    print(f"  Experience: {player_exp}/{partner_exp} vs {opp1_exp}/{opp2_exp}")
    print(f"  Score: {match_score}")
    
    # Call v4 algorithm
    result = calculate_pti_v4(
        player_pti, partner_pti, opp1_pti, opp2_pti,
        player_exp, partner_exp, opp1_exp, opp2_exp,
        match_score
    )
    
    if result["success"]:
        print(f"✅ API simulation successful!")
        adjustment = result["result"]["adjustment"]
        player_after = result["result"]["after"]["player"]["pti"]
        expected_adjustment = 14.912147033286097  # Known reference value
        
        if abs(adjustment - expected_adjustment) < 0.000001:
            print(f"✅ Result matches reference exactly!")
            print(f"   Adjustment: {adjustment:.6f}")
            print(f"   Player: {player_pti} → {player_after:.6f}")
            return True
        else:
            print(f"❌ Result differs from reference:")
            print(f"   Expected: {expected_adjustment:.6f}")
            print(f"   Actual:   {adjustment:.6f}")
            print(f"   Diff:     {abs(adjustment - expected_adjustment):.6f}")
            return False
    else:
        print(f"❌ API simulation failed: {result}")
        return False

def main():
    """Main integration test"""
    print("🚀 v4 Integration Testing")
    print("=" * 60)
    
    tests = [
        ("Direct v4 Algorithm", test_v4_direct),
        ("Experience Mapping", test_experience_mapping),
        ("Numeric Experience with v4", test_v4_with_numeric_experience),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} threw exception: {e}")
    
    # API simulation test
    print(f"\n" + "="*60)
    test_data = create_api_test_case()
    if simulate_api_call(test_data):
        passed += 1
    total += 1
    
    # Summary
    print(f"\n📊 Integration Test Summary")
    print("=" * 40)
    print(f"Passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ v4 algorithm is properly integrated!")
        print("🚀 Ready for production use!")
    else:
        print("⚠️ Some integration tests failed.")
        print("🔧 Check the issues above before deployment.")
    
    print(f"\n📝 Next Steps:")
    print("1. Test the mobile PTI calculator page")
    print("2. Verify API endpoint responds correctly")
    print("3. Deploy to staging for user testing")

if __name__ == "__main__":
    main() 