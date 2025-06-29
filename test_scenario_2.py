#!/usr/bin/env python3
"""
Test script for scenario 2: Player 60, Partner 20, Opp1 30, Opp2 23
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.pti_calculator_service import PTICalculatorService

def test_scenario_2():
    """Test with scenario 2 from user's screenshot"""
    
    print("=== Testing PTI Calculator - Scenario 2 ===")
    
    calculator = PTICalculatorService()
    
    # Inputs from user's screenshot
    player_pti = 60.0
    partner_pti = 20.0
    opp1_pti = 30.0
    opp2_pti = 23.0
    
    player_exp = 3.2   # 30+ matches
    partner_exp = 3.2  # 30+ matches
    opp1_exp = 3.2     # 30+ matches  
    opp2_exp = 4.0     # 10-30 Matches
    
    match_score = "6-2,2-6,6-3"
    
    result = calculator.calculate_pti_adjustments(
        player_pti, partner_pti, opp1_pti, opp2_pti,
        player_exp, partner_exp, opp1_exp, opp2_exp,
        match_score
    )
    
    print("=== OUR RESULTS ===")
    print(f"Spread: {result['spread']}")
    print(f"Adjustment: {result['adjustment']}")
    print()
    print("Before:")
    print(f"  Player - PTI: {result['before']['player']['pti']}, Mu: {result['before']['player']['mu']}, Sigma: {result['before']['player']['sigma']}")
    print(f"  Partner - PTI: {result['before']['partner']['pti']}, Mu: {result['before']['partner']['mu']}, Sigma: {result['before']['partner']['sigma']}")
    print(f"  Opp 1 - PTI: {result['before']['opp1']['pti']}, Mu: {result['before']['opp1']['mu']}, Sigma: {result['before']['opp1']['sigma']}")
    print(f"  Opp 2 - PTI: {result['before']['opp2']['pti']}, Mu: {result['before']['opp2']['mu']}, Sigma: {result['before']['opp2']['sigma']}")
    print()
    print("After:")
    print(f"  Player - PTI: {result['after']['player']['pti']}, Mu: {result['after']['player']['mu']}, Sigma: {result['after']['player']['sigma']}")
    print(f"  Partner - PTI: {result['after']['partner']['pti']}, Mu: {result['after']['partner']['mu']}, Sigma: {result['after']['partner']['sigma']}")
    print(f"  Opp 1 - PTI: {result['after']['opp1']['pti']}, Mu: {result['after']['opp1']['mu']}, Sigma: {result['after']['opp1']['sigma']}")
    print(f"  Opp 2 - PTI: {result['after']['opp2']['pti']}, Mu: {result['after']['opp2']['mu']}, Sigma: {result['after']['opp2']['sigma']}")
    print()
    
    print("=== EXPECTED FROM calc.platform.tennis ===")
    print("Spread: 27.00")
    print("Adjustment: 2.11")
    print()
    print("Before:")
    print("  Player - PTI: 60.00, Mu: 62.14, Sigma: 3.20")
    print("  Partner - PTI: 20.00, Mu: 16.69, Sigma: 3.20") 
    print("  Opp 1 - PTI: 30.00, Mu: 28.05, Sigma: 3.20")
    print("  Opp 2 - PTI: 23.00, Mu: 19.30, Sigma: 4.00")
    print()
    print("After:")
    print("  Player - PTI: 57.89, Mu: 59.71, Sigma: 3.24")
    print("  Partner - PTI: 17.89, Mu: 14.25, Sigma: 3.24")
    print("  Opp 1 - PTI: 32.17, Mu: 30.48, Sigma: 3.24")
    print("  Opp 2 - PTI: 26.32, Mu: 23.06, Sigma: 4.01")

if __name__ == "__main__":
    test_scenario_2() 