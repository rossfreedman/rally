#!/usr/bin/env python3
"""
PTI Pattern Analysis Tool

Analyzes patterns from test results to reverse engineer the exact algorithm.
Run this after collecting data from both the original site and our API.
"""

import json
import math
import numpy as np
from typing import Dict, List, Tuple, Any
from collections import defaultdict

def load_data() -> Tuple[List[Dict], List[Dict]]:
    """Load test results from both sources"""
    
    try:
        with open("original_site_results.json", "r") as f:
            original = json.load(f)
    except FileNotFoundError:
        print("❌ original_site_results.json not found!")
        print("Please run manual tests on https://calc.platform.tennis/calculator2.html first")
        return [], []
    
    try:
        with open("our_api_results.json", "r") as f:
            ours = json.load(f)
    except FileNotFoundError:
        print("❌ our_api_results.json not found!")
        print("Run: python scripts/pti_reverse_engineer.py first")
        return [], []
    
    return original, ours

def analyze_adjustment_patterns(original: List[Dict], ours: List[Dict]) -> None:
    """Analyze patterns in PTI adjustments"""
    
    print("=== ADJUSTMENT PATTERN ANALYSIS ===\n")
    
    # Group by scenarios
    scenarios = {
        "favorites_win": [],
        "favorites_lose": [],
        "underdogs_win": [],
        "underdogs_lose": []
    }
    
    for orig, our_data in zip(original, ours):
        if not (orig.get("success", True) and our_data["our_result"]["success"]):
            continue
            
        case = our_data["test_case"]
        team1_favored = case["team1_favored"] 
        player_wins = case["player_wins"]
        
        scenario_key = None
        if team1_favored and player_wins:
            scenario_key = "favorites_win"
        elif team1_favored and not player_wins:
            scenario_key = "favorites_lose"
        elif not team1_favored and player_wins:
            scenario_key = "underdogs_win"
        else:
            scenario_key = "underdogs_lose"
        
        adjustment_ratio = orig["adjustment"] / our_data["our_result"]["adjustment"] if our_data["our_result"]["adjustment"] != 0 else 0
        
        scenarios[scenario_key].append({
            "case": case,
            "original_adj": orig["adjustment"],
            "our_adj": our_data["our_result"]["adjustment"],
            "ratio": adjustment_ratio,
            "spread": case["spread"]
        })
    
    # Analyze each scenario
    for scenario, data in scenarios.items():
        if not data:
            continue
            
        print(f"{scenario.replace('_', ' ').title()}:")
        print(f"  Cases: {len(data)}")
        
        ratios = [d["ratio"] for d in data if d["ratio"] > 0]
        if ratios:
            avg_ratio = np.mean(ratios)
            print(f"  Avg adjustment ratio (original/ours): {avg_ratio:.3f}")
            print(f"  Range: {min(ratios):.3f} - {max(ratios):.3f}")
            
            # Look for patterns by spread
            by_spread = defaultdict(list)
            for d in data:
                spread_bucket = round(d["spread"] / 10) * 10  # Round to nearest 10
                by_spread[spread_bucket].append(d["ratio"])
            
            print("  By spread range:")
            for spread, spread_ratios in sorted(by_spread.items()):
                if spread_ratios:
                    print(f"    Spread ~{spread}: {np.mean(spread_ratios):.3f} (n={len(spread_ratios)})")
        print()

def analyze_rating_changes(original: List[Dict], ours: List[Dict]) -> None:
    """Analyze individual rating change patterns"""
    
    print("=== RATING CHANGE ANALYSIS ===\n")
    
    player_changes = []
    partner_changes = []
    opp_changes = []
    
    for orig, our_data in zip(original, ours):
        if not (orig.get("success", True) and our_data["our_result"]["success"]):
            continue
        
        case = our_data["test_case"]
        
        # Player changes
        orig_player_change = orig["player_after"] - orig["player_before"]
        our_player_change = our_data["our_result"]["player_after"] - our_data["our_result"]["player_before"]
        
        player_changes.append({
            "case": case,
            "original": orig_player_change,
            "ours": our_player_change,
            "ratio": orig_player_change / our_player_change if our_player_change != 0 else 0
        })
        
        # Similar for partner and opponents
        orig_partner_change = orig["partner_after"] - orig["partner_before"]
        our_partner_change = our_data["our_result"]["partner_after"] - our_data["our_result"]["partner_before"]
        
        partner_changes.append({
            "case": case,
            "original": orig_partner_change,
            "ours": our_partner_change,
            "ratio": orig_partner_change / our_partner_change if our_partner_change != 0 else 0
        })
    
    # Analyze player changes
    if player_changes:
        ratios = [p["ratio"] for p in player_changes if p["ratio"] != 0]
        print(f"Player change ratios: avg={np.mean(ratios):.3f}, std={np.std(ratios):.3f}")
        
        # Group by outcome
        wins = [p for p in player_changes if p["case"]["player_wins"]]
        losses = [p for p in player_changes if not p["case"]["player_wins"]]
        
        if wins:
            win_ratios = [w["ratio"] for w in wins if w["ratio"] != 0]
            print(f"  When player wins: avg ratio = {np.mean(win_ratios):.3f}")
            
        if losses:
            loss_ratios = [l["ratio"] for l in losses if l["ratio"] != 0]
            print(f"  When player loses: avg ratio = {np.mean(loss_ratios):.3f}")

def identify_k_factor_patterns(original: List[Dict], ours: List[Dict]) -> None:
    """Try to identify K-factor patterns"""
    
    print("=== K-FACTOR PATTERN ANALYSIS ===\n")
    
    # For each case, try to back-calculate what K-factor would produce the original result
    k_factors = []
    
    for orig, our_data in zip(original, ours):
        if not (orig.get("success", True) and our_data["our_result"]["success"]):
            continue
            
        case = our_data["test_case"]
        
        # Simple K-factor calculation: adjustment = k * (actual - expected)
        # We need to estimate expected probability
        team1_avg = case["team1_avg"]
        team2_avg = case["team2_avg"]
        rating_diff = team1_avg - team2_avg
        expected_team1_prob = 1 / (1 + math.pow(10, -rating_diff / 400))
        
        actual_result = 1.0 if case["player_wins"] else 0.0
        prob_diff = actual_result - expected_team1_prob
        
        if abs(prob_diff) > 0.01:  # Avoid division by very small numbers
            implied_k = abs(orig["adjustment"]) / abs(prob_diff)
            k_factors.append({
                "case": case,
                "k_factor": implied_k,
                "prob_diff": prob_diff,
                "adjustment": orig["adjustment"]
            })
    
    if k_factors:
        k_values = [k["k_factor"] for k in k_factors]
        print(f"Implied K-factors: avg={np.mean(k_values):.2f}, std={np.std(k_values):.2f}")
        print(f"Range: {min(k_values):.2f} - {max(k_values):.2f}")
        
        # Group by experience level (all 3.2 in our test cases)
        print(f"For experience 3.2: avg K = {np.mean(k_values):.2f}")

def suggest_algorithm_improvements(original: List[Dict], ours: List[Dict]) -> None:
    """Suggest specific improvements to our algorithm"""
    
    print("=== ALGORITHM IMPROVEMENT SUGGESTIONS ===\n")
    
    # Find the most consistent patterns
    adjustments = []
    
    for orig, our_data in zip(original, ours):
        if not (orig.get("success", True) and our_data["our_result"]["success"]):
            continue
            
        case = our_data["test_case"]
        ratio = orig["adjustment"] / our_data["our_result"]["adjustment"] if our_data["our_result"]["adjustment"] != 0 else 0
        
        adjustments.append({
            "case": case,
            "original": orig["adjustment"],
            "ours": our_data["our_result"]["adjustment"],
            "ratio": ratio,
            "error": abs(orig["adjustment"] - our_data["our_result"]["adjustment"])
        })
    
    # Sort by error to find worst cases
    adjustments.sort(key=lambda x: x["error"], reverse=True)
    
    print("Worst mismatches (top 10):")
    for i, adj in enumerate(adjustments[:10]):
        case = adj["case"]
        print(f"{i+1}. Case {case['id']}: Expected {adj['original']:.2f}, Got {adj['ours']:.2f}")
        print(f"   {case['player_pti']}/{case['partner_pti']} vs {case['opp1_pti']}/{case['opp2_pti']}")
        print(f"   Score: {case['match_score']}, Player wins: {case['case']['player_wins']}")
        print(f"   Error: {adj['error']:.2f}")
        print()
    
    # Calculate overall scaling factor
    valid_ratios = [adj["ratio"] for adj in adjustments if adj["ratio"] > 0]
    if valid_ratios:
        overall_scaling = np.median(valid_ratios)
        print(f"Overall scaling factor needed: {overall_scaling:.3f}")
        print(f"Apply this by multiplying all our adjustments by {overall_scaling:.3f}")

def main():
    """Main analysis function"""
    
    print("PTI Pattern Analysis Tool")
    print("=" * 50)
    
    # Load data
    original, ours = load_data()
    if not original or not ours:
        return
    
    print(f"Loaded {len(original)} original results and {len(ours)} our results\n")
    
    # Run analyses
    analyze_adjustment_patterns(original, ours)
    analyze_rating_changes(original, ours)
    identify_k_factor_patterns(original, ours)
    suggest_algorithm_improvements(original, ours)
    
    print("=== NEXT STEPS ===")
    print("1. Apply the suggested scaling factor to our algorithm")
    print("2. Focus on the worst mismatch cases to refine logic")
    print("3. Test specific K-factor values identified")
    print("4. Re-run tests to validate improvements")

if __name__ == "__main__":
    main() 