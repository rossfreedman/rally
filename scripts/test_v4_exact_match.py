#!/usr/bin/env python3
"""
Test v4 Algorithm for Exact Reference Match

Verify that our v4 PTI algorithm exactly matches the comprehensive reference data
from the original calc.platform.tennis PTI calculator.
"""

import sys
import os
import json
import statistics
from typing import List, Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.pti_calculator_service_v4 import calculate_pti_v4

def load_comprehensive_results():
    """Load the comprehensive automated results"""
    try:
        with open("comprehensive_pti_results.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ comprehensive_pti_results.json not found. Run nodejs_pti_automation.py first.")
        return None

def test_v4_exact_match():
    """Test v4 algorithm for exact match with reference data"""
    print("🎯 Testing v4 Algorithm for EXACT Reference Match")
    print("=" * 70)
    
    # Load reference results
    reference_results = load_comprehensive_results()
    if not reference_results:
        return
    
    print(f"📊 Testing against {len(reference_results)} reference cases...")
    print()
    
    exact_matches = 0
    close_matches = 0
    failed_cases = 0
    
    max_diff = 0.0
    worst_case = None
    
    detailed_results = []
    
    for ref_result in reference_results:
        test_case = ref_result["input"]
        
        try:
            # Run our v4 algorithm
            v4_result = calculate_pti_v4(
                player_pti=test_case["player_pti"],
                partner_pti=test_case["partner_pti"],
                opp1_pti=test_case["opp1_pti"],
                opp2_pti=test_case["opp2_pti"],
                player_exp=test_case["player_exp"],
                partner_exp=test_case["partner_exp"],
                opp1_exp=test_case["opp1_exp"],
                opp2_exp=test_case["opp2_exp"],
                match_score=test_case["score"]
            )
            
            if v4_result["success"]:
                v4_data = v4_result["result"]
                
                # Compare key values
                ref_adjustment = ref_result["adjustment"]
                ref_player_after = ref_result["player_after"]
                ref_expected_prob = ref_result["expected_prob"]
                ref_k_factor = ref_result["k_factor"]
                
                v4_adjustment = v4_data["adjustment"]
                v4_player_after = v4_data["after"]["player"]["pti"]
                v4_expected_prob = v4_data["details"]["expected_prob"]
                v4_k_factor = v4_data["details"]["k_factor"]
                
                # Calculate differences
                adj_diff = abs(ref_adjustment - v4_adjustment)
                player_diff = abs(ref_player_after - v4_player_after)
                prob_diff = abs(ref_expected_prob - v4_expected_prob)
                k_diff = abs(ref_k_factor - v4_k_factor)
                
                max_single_diff = max(adj_diff, player_diff, prob_diff, k_diff)
                
                # Track worst case
                if max_single_diff > max_diff:
                    max_diff = max_single_diff
                    worst_case = {
                        "case_id": test_case["id"],
                        "description": test_case["description"],
                        "max_diff": max_single_diff,
                        "adj_diff": adj_diff,
                        "player_diff": player_diff,
                        "prob_diff": prob_diff,
                        "k_diff": k_diff
                    }
                
                # Categorize match quality
                if max_single_diff < 0.000001:  # Essentially perfect
                    exact_matches += 1
                    status = "✅ EXACT"
                elif max_single_diff < 0.01:     # Very close
                    close_matches += 1
                    status = "✅ CLOSE"
                else:
                    status = "⚠️ DIFF"
                
                print(f"{status} Case {test_case['id']:2d}: Max diff {max_single_diff:.6f}")
                print(f"        Adj: {ref_adjustment:.6f} → {v4_adjustment:.6f} (Δ{adj_diff:.6f})")
                print(f"        K:   {ref_k_factor:.6f} → {v4_k_factor:.6f} (Δ{k_diff:.6f})")
                
                # Store detailed result
                detailed_results.append({
                    "case_id": test_case["id"],
                    "description": test_case["description"],
                    "status": status,
                    "max_diff": max_single_diff,
                    "reference": {
                        "adjustment": ref_adjustment,
                        "player_after": ref_player_after,
                        "expected_prob": ref_expected_prob,
                        "k_factor": ref_k_factor
                    },
                    "v4": {
                        "adjustment": v4_adjustment,
                        "player_after": v4_player_after,
                        "expected_prob": v4_expected_prob,
                        "k_factor": v4_k_factor
                    },
                    "differences": {
                        "adjustment": adj_diff,
                        "player_after": player_diff,
                        "expected_prob": prob_diff,
                        "k_factor": k_diff
                    }
                })
                
            else:
                failed_cases += 1
                print(f"❌ Case {test_case['id']} failed: {v4_result}")
                
        except Exception as e:
            failed_cases += 1
            print(f"❌ Case {test_case['id']} exception: {e}")
    
    # Analysis
    print(f"\n📊 v4 Exact Match Analysis")
    print("=" * 50)
    
    total_cases = len(reference_results)
    successful_cases = exact_matches + close_matches
    
    print(f"Total cases: {total_cases}")
    print(f"Exact matches (< 0.000001): {exact_matches}")
    print(f"Close matches (< 0.01): {close_matches}")
    print(f"Successful cases: {successful_cases}")
    print(f"Failed cases: {failed_cases}")
    print(f"Success rate: {(successful_cases/total_cases)*100:.1f}%")
    
    if worst_case:
        print(f"\n🔍 Worst Case Analysis:")
        print(f"Case {worst_case['case_id']}: {worst_case['description']}")
        print(f"Maximum difference: {worst_case['max_diff']:.6f}")
        print(f"Adjustment diff: {worst_case['adj_diff']:.6f}")
        print(f"Player PTI diff: {worst_case['player_diff']:.6f}")
        print(f"Probability diff: {worst_case['prob_diff']:.6f}")
        print(f"K-factor diff: {worst_case['k_diff']:.6f}")
    
    # Overall assessment
    print(f"\n🎯 v4 Algorithm Assessment:")
    if exact_matches == total_cases:
        print("🎉 PERFECT! All cases match exactly!")
    elif (exact_matches + close_matches) == total_cases:
        print("✅ EXCELLENT! All cases are very close matches!")
    elif successful_cases >= total_cases * 0.9:
        print("✅ VERY GOOD! 90%+ cases match well!")
    elif successful_cases >= total_cases * 0.7:
        print("✅ GOOD! 70%+ cases match reasonably!")
    else:
        print("⚠️ NEEDS IMPROVEMENT! Less than 70% good matches!")
    
    # Compare with v3 performance
    print(f"\n🚀 Algorithm Progression:")
    print(f"v3 vs Reference: 13.393 avg PTI difference")
    print(f"v4 vs Reference: {max_diff:.6f} max difference")
    print(f"Improvement: {((13.393 - max_diff) / 13.393) * 100:.1f}%")
    
    # Save detailed analysis
    analysis_data = {
        "algorithm_version": "v4",
        "test_type": "exact_reference_match",
        "summary": {
            "total_cases": total_cases,
            "exact_matches": exact_matches,
            "close_matches": close_matches,
            "successful_cases": successful_cases,
            "failed_cases": failed_cases,
            "success_rate_percent": (successful_cases/total_cases)*100,
            "max_difference": max_diff,
            "worst_case": worst_case
        },
        "detailed_results": detailed_results
    }
    
    with open("v4_exact_match_analysis.json", "w") as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"\n💾 Detailed analysis saved to v4_exact_match_analysis.json")
    
    return exact_matches, close_matches, max_diff

def verify_specific_cases():
    """Verify specific known cases with manual calculations"""
    print(f"\n🔬 Manual Verification of Key Cases")
    print("=" * 50)
    
    # Case 1: Original known case
    print("Verifying Case 1 (Original Known Case):")
    print("Input: 50/40 vs 30/23, score: 6-2,2-6,6-3")
    
    result = calculate_pti_v4(50, 40, 30, 23, "30+", "30+", "30+", "30+", "6-2,2-6,6-3")
    
    if result["success"]:
        details = result["result"]["details"]
        print(f"Team averages: {details['team1_avg']} vs {details['team2_avg']}")
        print(f"Expected prob: {details['expected_prob']:.10f}")
        print(f"Experience mult: {details['experience_multiplier']:.6f}")
        print(f"K-factor: {details['k_factor']:.6f}")
        print(f"Adjustment: {result['result']['adjustment']:.6f}")
        print(f"Formula: {details['formula_verification']['calculation']}")
        
        # Compare with known reference
        expected_adjustment = 14.912147033286097
        actual_adjustment = result["result"]["adjustment"]
        diff = abs(expected_adjustment - actual_adjustment)
        
        if diff < 0.000001:
            print("✅ PERFECT MATCH!")
        else:
            print(f"⚠️ Difference: {diff:.10f}")
    
    # Case 6: Experience level difference
    print(f"\nVerifying Case 6 (Experience Levels):")
    print("Input: 30/30 vs 30/30, New/New vs 30+/30+")
    
    result = calculate_pti_v4(30, 30, 30, 30, "New", "New", "30+", "30+", "6-4,6-4")
    
    if result["success"]:
        details = result["result"]["details"]
        print(f"Experience mult: {details['experience_multiplier']:.6f} (should be 1.15)")
        print(f"K-factor: {details['k_factor']:.6f} (should be 36.225)")
        print(f"Adjustment: {result['result']['adjustment']:.6f}")
        
        expected_k = 36.225
        actual_k = details['k_factor']
        k_diff = abs(expected_k - actual_k)
        
        if k_diff < 0.000001:
            print("✅ Experience calculation PERFECT!")
        else:
            print(f"⚠️ K-factor difference: {k_diff:.10f}")

def main():
    """Main testing function"""
    exact_matches, close_matches, max_diff = test_v4_exact_match()
    
    # Manual verification
    verify_specific_cases()
    
    print(f"\n✨ Final Summary:")
    print(f"v4 Algorithm Performance:")
    print(f"- Exact matches: {exact_matches}/15")
    print(f"- Close matches: {close_matches}/15") 
    print(f"- Maximum difference: {max_diff:.6f}")
    
    if exact_matches == 15:
        print("🎉 v4 PERFECTLY matches the reference calculator!")
        print("🚀 Ready for production deployment!")
    elif exact_matches + close_matches == 15:
        print("✅ v4 VERY CLOSELY matches the reference calculator!")
        print("✅ Ready for production with minor precision differences!")
    else:
        print("🔧 v4 needs further refinement for perfect accuracy.")
    
    print(f"\n📁 Files created:")
    print("- v4_exact_match_analysis.json (detailed comparison)")

if __name__ == "__main__":
    main() 