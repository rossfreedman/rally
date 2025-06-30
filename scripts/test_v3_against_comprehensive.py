#!/usr/bin/env python3
"""
Test v3 Algorithm Against Comprehensive Results

Compare our v3 PTI algorithm against the comprehensive automated results
from the original PTI calculator.
"""

import sys
import os
import json
import statistics
from typing import List, Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.pti_calculator_service_v3 import calculate_pti_v3

def load_comprehensive_results():
    """Load the comprehensive automated results"""
    try:
        with open("comprehensive_pti_results.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ comprehensive_pti_results.json not found. Run nodejs_pti_automation.py first.")
        return None

def test_v3_against_comprehensive():
    """Test v3 algorithm against comprehensive results"""
    print("🚀 Testing v3 Algorithm Against Comprehensive Reference Data")
    print("=" * 70)
    
    # Load reference results
    reference_results = load_comprehensive_results()
    if not reference_results:
        return
    
    print(f"📊 Testing against {len(reference_results)} reference cases...")
    
    v3_results = []
    differences = []
    adjustment_diffs = []
    failed_cases = 0
    
    detailed_comparisons = []
    
    for ref_result in reference_results:
        test_case = ref_result["input"]
        
        try:
            # Run our v3 algorithm
            v3_result = calculate_pti_v3(
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
            
            if v3_result["success"]:
                v3_data = v3_result["result"]
                
                # Compare with reference
                ref_player_after = ref_result["player_after"]
                ref_partner_after = ref_result["partner_after"]
                ref_opp1_after = ref_result["opp1_after"]
                ref_opp2_after = ref_result["opp2_after"]
                ref_adjustment = ref_result["adjustment"]
                
                v3_player_after = v3_data["after"]["player"]["pti"]
                v3_partner_after = v3_data["after"]["partner"]["pti"]
                v3_opp1_after = v3_data["after"]["opp1"]["pti"]
                v3_opp2_after = v3_data["after"]["opp2"]["pti"]
                v3_adjustment = v3_data["adjustment"]
                
                # Calculate differences
                player_diff = abs(ref_player_after - v3_player_after)
                partner_diff = abs(ref_partner_after - v3_partner_after)
                opp1_diff = abs(ref_opp1_after - v3_opp1_after)
                opp2_diff = abs(ref_opp2_after - v3_opp2_after)
                
                avg_pti_diff = (player_diff + partner_diff + opp1_diff + opp2_diff) / 4
                adj_diff = abs(ref_adjustment - v3_adjustment)
                
                differences.append(avg_pti_diff)
                adjustment_diffs.append(adj_diff)
                
                # Store detailed comparison
                detailed_comparisons.append({
                    "case_id": test_case["id"],
                    "description": test_case["description"],
                    "avg_pti_diff": avg_pti_diff,
                    "adj_diff": adj_diff,
                    "ref_adjustment": ref_adjustment,
                    "v3_adjustment": v3_adjustment,
                    "ref_player_after": ref_player_after,
                    "v3_player_after": v3_player_after
                })
                
                print(f"✅ Case {test_case['id']}: PTI diff {avg_pti_diff:.2f}, Adj diff {adj_diff:.2f}")
                
            else:
                failed_cases += 1
                print(f"❌ Case {test_case['id']} failed: {v3_result}")
                
        except Exception as e:
            failed_cases += 1
            print(f"❌ Case {test_case['id']} exception: {e}")
    
    # Analysis
    print(f"\n📊 v3 vs Comprehensive Reference Analysis")
    print("=" * 50)
    
    if differences:
        avg_pti_diff = statistics.mean(differences)
        median_pti_diff = statistics.median(differences)
        max_pti_diff = max(differences)
        min_pti_diff = min(differences)
        
        avg_adj_diff = statistics.mean(adjustment_diffs)
        median_adj_diff = statistics.median(adjustment_diffs)
        max_adj_diff = max(adjustment_diffs)
        
        print(f"Successful cases: {len(differences)}/{len(reference_results)}")
        print(f"Failed cases: {failed_cases}")
        print()
        print("PTI Differences:")
        print(f"  Average: {avg_pti_diff:.3f}")
        print(f"  Median:  {median_pti_diff:.3f}")
        print(f"  Max:     {max_pti_diff:.3f}")
        print(f"  Min:     {min_pti_diff:.3f}")
        print()
        print("Adjustment Differences:")
        print(f"  Average: {avg_adj_diff:.3f}")
        print(f"  Median:  {median_adj_diff:.3f}")
        print(f"  Max:     {max_adj_diff:.3f}")
        
        # Accuracy assessment
        print(f"\n🎯 v3 Accuracy Assessment:")
        if avg_pti_diff < 0.5:
            print("✅ EXCELLENT accuracy!")
        elif avg_pti_diff < 1.0:
            print("✅ VERY GOOD accuracy!")
        elif avg_pti_diff < 2.0:
            print("✅ GOOD accuracy!")
        elif avg_pti_diff < 5.0:
            print("⚠️ FAIR accuracy - room for improvement")
        else:
            print("❌ POOR accuracy - needs significant improvement")
        
        # Show worst cases
        print(f"\n🔍 Worst Cases (Top 5):")
        sorted_comparisons = sorted(detailed_comparisons, key=lambda x: x["avg_pti_diff"], reverse=True)
        
        for i, comp in enumerate(sorted_comparisons[:5]):
            print(f"{i+1}. Case {comp['case_id']}: {comp['description']}")
            print(f"   PTI diff: {comp['avg_pti_diff']:.2f}, Adj diff: {comp['adj_diff']:.2f}")
            print(f"   Reference adj: {comp['ref_adjustment']:.2f}, v3 adj: {comp['v3_adjustment']:.2f}")
            print(f"   Player: {comp['ref_player_after']:.1f}(ref) vs {comp['v3_player_after']:.1f}(v3)")
        
        # Algorithm comparison with previous benchmarks
        print(f"\n🚀 Algorithm Performance Comparison:")
        print(f"v3 vs Comprehensive Reference: {avg_pti_diff:.3f} avg PTI difference")
        print(f"v3 vs 100 Random Cases: 19.944 avg PTI difference")
        
        if avg_pti_diff < 5.0:
            print("✅ v3 performs much better against reference data!")
            print("✅ The comprehensive reference provides better calibration")
        else:
            print("⚠️ v3 still needs improvement even with reference data")
        
        # Save analysis
        analysis_data = {
            "algorithm_version": "v3",
            "test_type": "comprehensive_reference",
            "summary": {
                "total_cases": len(reference_results),
                "successful_cases": len(differences),
                "failed_cases": failed_cases,
                "avg_pti_difference": avg_pti_diff,
                "avg_adjustment_difference": avg_adj_diff,
                "accuracy_assessment": "EXCELLENT" if avg_pti_diff < 0.5 else 
                                     "VERY GOOD" if avg_pti_diff < 1.0 else
                                     "GOOD" if avg_pti_diff < 2.0 else
                                     "FAIR" if avg_pti_diff < 5.0 else "POOR"
            },
            "detailed_comparisons": detailed_comparisons
        }
        
        with open("v3_vs_comprehensive_analysis.json", "w") as f:
            json.dump(analysis_data, f, indent=2)
        
        print(f"\n💾 Analysis saved to v3_vs_comprehensive_analysis.json")
        
        return avg_pti_diff, avg_adj_diff
    else:
        print("❌ No successful test cases to analyze")
        return None, None

def main():
    """Main testing function"""
    avg_pti_diff, avg_adj_diff = test_v3_against_comprehensive()
    
    if avg_pti_diff is not None:
        print(f"\n✨ Summary:")
        print(f"Our v3 algorithm vs comprehensive reference data:")
        print(f"Average PTI difference: {avg_pti_diff:.3f}")
        print(f"Average adjustment difference: {avg_adj_diff:.3f}")
        
        if avg_pti_diff < 2.0:
            print("🎉 v3 is performing well against reference data!")
        else:
            print("🔧 v3 needs further calibration improvements")
    
    print(f"\n🔍 Files created:")
    print("- v3_vs_comprehensive_analysis.json (detailed analysis)")
    print("- comprehensive_pti_results.json (reference data)")

if __name__ == "__main__":
    main() 