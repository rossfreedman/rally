#!/usr/bin/env python3
"""
Analyze Focused PTI Test Results

Run this after collecting test results from the original site to identify patterns.
"""

import json
import math

def load_focused_results():
    """Load the focused test results"""
    try:
        with open("focused_results.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ focused_results.json not found!")
        print("Please test the 15 cases on https://calc.platform.tennis/calculator2.html first")
        return []

def analyze_k_factors(results):
    """Analyze K-factor patterns"""
    print("=== K-FACTOR ANALYSIS ===\n")
    
    for result in results:
        # Calculate team averages
        team1_avg = (result['player_before'] + result['partner_before']) / 2
        team2_avg = (result['opp1_before'] + result['opp2_before']) / 2
        
        # Calculate expected probability using Elo formula
        rating_diff = team1_avg - team2_avg
        expected_prob = 1 / (1 + math.pow(10, -rating_diff / 400))
        
        # Determine actual result (assume player wins if adjustment is negative)
        actual_result = 1.0 if result['adjustment'] < 0 else 0.0
        prob_diff = actual_result - expected_prob
        
        # Calculate implied K-factor
        if abs(prob_diff) > 0.01:
            k_factor = abs(result['adjustment']) / abs(prob_diff)
            
            print(f"Case {result['id']}: K = {k_factor:.1f}")
            print(f"  Teams: {team1_avg:.1f} vs {team2_avg:.1f}")
            print(f"  Expected: {expected_prob:.3f}, Actual: {actual_result}, Diff: {prob_diff:.3f}")
            print(f"  Adjustment: {result['adjustment']:.2f}")
            print()

def analyze_experience_patterns(results):
    """Analyze how experience affects adjustments"""
    print("=== EXPERIENCE PATTERN ANALYSIS ===\n")
    
    # Compare cases with same PTIs but different experience
    case2 = next((r for r in results if r['id'] == 2), None)  # All 30+ matches
    case6 = next((r for r in results if r['id'] == 6), None)  # New vs 30+ matches
    case12 = next((r for r in results if r['id'] == 12), None)  # 10-30 vs 30+ matches
    case15 = next((r for r in results if r['id'] == 15), None)  # 1-10 vs 30+ matches
    
    if all([case2, case6, case12, case15]):
        print("Equal teams (30 vs 30), different experience levels:")
        print(f"All 30+ matches: Adjustment = {case2['adjustment']:.2f}")
        print(f"New vs 30+ matches: Adjustment = {case6['adjustment']:.2f}")
        print(f"10-30 vs 30+ matches: Adjustment = {case12['adjustment']:.2f}")
        print(f"1-10 vs 30+ matches: Adjustment = {case15['adjustment']:.2f}")
        print()
        
        # Calculate experience multipliers
        base_adj = case2['adjustment']
        if base_adj != 0:
            print("Experience multipliers (relative to 30+ matches):")
            print(f"New player: {case6['adjustment'] / base_adj:.2f}x")
            print(f"10-30 matches: {case12['adjustment'] / base_adj:.2f}x")
            print(f"1-10 matches: {case15['adjustment'] / base_adj:.2f}x")
            print()

def analyze_upset_patterns(results):
    """Analyze upset vs expected result patterns"""
    print("=== UPSET VS EXPECTED PATTERNS ===\n")
    
    case3 = next((r for r in results if r['id'] == 3), None)  # Underdogs win
    case4 = next((r for r in results if r['id'] == 4), None)  # Favorites win
    case13 = next((r for r in results if r['id'] == 13), None)  # Big underdogs win
    
    if all([case3, case4, case13]):
        print("Upset vs Expected patterns:")
        print(f"Case 3 (40/40 vs 25/25, underdogs win): {case3['adjustment']:.2f}")
        print(f"Case 4 (25/25 vs 40/40, favorites win): {case4['adjustment']:.2f}")
        print(f"Case 13 (45/45 vs 25/25, big underdogs win): {case13['adjustment']:.2f}")
        print()
        
        # Check if magnitude is similar but opposite
        if abs(case3['adjustment']) > 0 and abs(case4['adjustment']) > 0:
            ratio = abs(case3['adjustment']) / abs(case4['adjustment'])
            print(f"Upset to expected ratio: {ratio:.2f}")
            print()

def identify_base_formula(results):
    """Try to identify the base formula"""
    print("=== BASE FORMULA IDENTIFICATION ===\n")
    
    # Look for the simplest case (equal teams)
    case2 = next((r for r in results if r['id'] == 2), None)
    
    if case2:
        print("Equal teams case (30/30 vs 30/30):")
        print(f"Adjustment: {case2['adjustment']:.2f}")
        
        # Since teams are equal, expected probability should be 0.5
        # So adjustment = K * (actual - 0.5) = K * 0.5 (if player wins)
        if case2['adjustment'] != 0:
            implied_k = abs(case2['adjustment']) / 0.5
            print(f"Implied base K-factor: {implied_k:.1f}")
            print()

def suggest_algorithm(results):
    """Suggest the algorithm based on patterns"""
    print("=== SUGGESTED ALGORITHM ===\n")
    
    # Find patterns and suggest implementation
    k_factors = []
    
    for result in results:
        team1_avg = (result['player_before'] + result['partner_before']) / 2
        team2_avg = (result['opp1_before'] + result['opp2_before']) / 2
        rating_diff = team1_avg - team2_avg
        expected_prob = 1 / (1 + math.pow(10, -rating_diff / 400))
        actual_result = 1.0 if result['adjustment'] < 0 else 0.0
        prob_diff = actual_result - expected_prob
        
        if abs(prob_diff) > 0.01:
            k_factor = abs(result['adjustment']) / abs(prob_diff)
            k_factors.append(k_factor)
    
    if k_factors:
        avg_k = sum(k_factors) / len(k_factors)
        print(f"Average K-factor: {avg_k:.1f}")
        print()
        print("Suggested algorithm:")
        print("1. Calculate team averages")
        print("2. Calculate expected probability: 1 / (1 + 10^(-(team1_avg - team2_avg)/400))")
        print("3. Determine actual result: 1 if player wins, 0 if loses")
        print(f"4. Calculate adjustment: {avg_k:.0f} * (actual - expected)")
        print("5. Apply experience multipliers based on Cases 6, 12, 15")
        print()

def main():
    """Main analysis function"""
    print("PTI Focused Results Analysis")
    print("=" * 40)
    
    results = load_focused_results()
    if not results:
        return
    
    print(f"Analyzing {len(results)} test cases\n")
    
    analyze_k_factors(results)
    analyze_experience_patterns(results)
    analyze_upset_patterns(results)
    identify_base_formula(results)
    suggest_algorithm(results)
    
    print("=== NEXT STEPS ===")
    print("1. Implement the suggested algorithm")
    print("2. Test against a few cases to validate")
    print("3. Refine based on any remaining discrepancies")

if __name__ == "__main__":
    main() 