#!/usr/bin/env python3
"""
Test 100 Random PTI Cases with v3 Algorithm

Test the improved v3 algorithm with proper experience handling against 100 random cases.
"""

import sys
import os
import random
import json
import subprocess
import statistics
from typing import List, Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.pti_calculator_service_v3 import calculate_pti_v3

def generate_random_test_cases(num_cases: int = 100) -> List[Dict[str, Any]]:
    """Generate random test cases covering various scenarios"""
    test_cases = []
    
    experience_levels = ["30+", "10-30", "1-10", "New Player"]
    score_patterns = [
        "6-4,6-4", "6-3,6-4", "6-2,6-4", "6-1,6-4", 
        "7-5,6-4", "7-6,6-4", "6-4,7-5", "6-4,7-6",
        "6-2,2-6,6-3", "6-4,4-6,6-4", "7-5,5-7,6-4",
        "6-1,6-2", "6-0,6-1", "6-3,6-3"
    ]
    
    # Set seed for reproducible results
    random.seed(42)
    
    for i in range(num_cases):
        # Generate PTI values with realistic distribution
        player_pti = round(random.uniform(15.0, 55.0), 1)
        partner_pti = round(random.uniform(15.0, 55.0), 1)
        opp1_pti = round(random.uniform(15.0, 55.0), 1)
        opp2_pti = round(random.uniform(15.0, 55.0), 1)
        
        # Generate experience levels (bias toward 30+ for realistic scenarios)
        weights = [0.6, 0.2, 0.15, 0.05]  # 60% experienced, etc.
        player_exp = random.choices(experience_levels, weights=weights)[0]
        partner_exp = random.choices(experience_levels, weights=weights)[0]
        opp1_exp = random.choices(experience_levels, weights=weights)[0]
        opp2_exp = random.choices(experience_levels, weights=weights)[0]
        
        # Random score
        score = random.choice(score_patterns)
        
        test_case = {
            "id": i + 1,
            "player_pti": player_pti,
            "partner_pti": partner_pti,
            "opp1_pti": opp1_pti,
            "opp2_pti": opp2_pti,
            "player_exp": player_exp,
            "partner_exp": partner_exp,
            "opp1_exp": opp1_exp,
            "opp2_exp": opp2_exp,
            "score": score,
            "description": f"Random Case {i+1}"
        }
        test_cases.append(test_case)
    
    return test_cases

def run_100_case_v3_comparison():
    """Run comprehensive comparison of 100 random cases with v3"""
    print("🎯 Testing v3 Algorithm on 100 Random Cases")
    print("=" * 55)
    
    # Generate same test cases as before (using seed 42)
    test_cases = generate_random_test_cases(100)
    print(f"✅ Generated {len(test_cases)} random test cases")
    
    # Load previous Node.js reference results if available
    try:
        with open("random_100_expected.json", "r") as f:
            expected_results = json.load(f)
        print("✅ Loaded reference results from previous run")
    except FileNotFoundError:
        print("❌ No reference results found. Please run test_100_random_cases.py first.")
        return None, None
    
    # Run our v3 algorithm on all test cases
    print("🧪 Testing v3 algorithm on 100 random cases...")
    
    our_results = []
    differences = []
    adjustment_diffs = []
    failed_cases = 0
    
    experience_performance = {
        "30+": {"diffs": [], "count": 0},
        "10-30": {"diffs": [], "count": 0},
        "1-10": {"diffs": [], "count": 0},
        "New Player": {"diffs": [], "count": 0}
    }
    
    for i, test_case in enumerate(test_cases):
        try:
            result = calculate_pti_v3(
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
            
            if result["success"]:
                our_results.append(result["result"])
                
                # Compare with expected (Node.js reference)
                expected = expected_results[i]
                actual = result["result"]
                
                # Calculate differences
                player_diff = abs(expected["player_after"] - actual["after"]["player"]["pti"])
                partner_diff = abs(expected["partner_after"] - actual["after"]["partner"]["pti"])
                opp1_diff = abs(expected["opp1_after"] - actual["after"]["opp1"]["pti"])
                opp2_diff = abs(expected["opp2_after"] - actual["after"]["opp2"]["pti"])
                
                avg_pti_diff = (player_diff + partner_diff + opp1_diff + opp2_diff) / 4
                adj_diff = abs(expected["adjustment"] - actual["adjustment"])
                
                differences.append(avg_pti_diff)
                adjustment_diffs.append(adj_diff)
                
                # Track performance by experience level
                player_exp = test_case["player_exp"]
                if player_exp in experience_performance:
                    experience_performance[player_exp]["diffs"].append(avg_pti_diff)
                    experience_performance[player_exp]["count"] += 1
                
            else:
                failed_cases += 1
                print(f"❌ Case {i+1} failed: {result}")
                
        except Exception as e:
            failed_cases += 1
            print(f"❌ Case {i+1} exception: {e}")
    
    # Analyze results
    print("\n📊 v3 Results Analysis")
    print("=" * 35)
    
    if differences:
        avg_pti_diff = statistics.mean(differences)
        median_pti_diff = statistics.median(differences)
        max_pti_diff = max(differences)
        min_pti_diff = min(differences)
        
        avg_adj_diff = statistics.mean(adjustment_diffs)
        median_adj_diff = statistics.median(adjustment_diffs)
        
        print(f"Successful cases: {len(differences)}/100")
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
        
        # Accuracy assessment
        print("\n🎯 v3 Accuracy Assessment:")
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
        
        # Experience level performance analysis
        print("\n📈 Performance by Experience Level:")
        print("-" * 40)
        for exp_level, data in experience_performance.items():
            if data["count"] > 0:
                avg_exp_diff = statistics.mean(data["diffs"])
                print(f"{exp_level:12}: {data['count']:2d} cases, avg diff: {avg_exp_diff:.3f}")
        
        # Identify worst cases (less detailed than before since we're focused on overall performance)
        if avg_pti_diff > 1.0:
            print("\n🔍 Sample Worst Cases (top 3):")
            case_diffs = list(zip(differences, adjustment_diffs, range(len(differences))))
            worst_cases = sorted(case_diffs, key=lambda x: x[0], reverse=True)[:3]
            
            for i, (pti_diff, adj_diff, case_idx) in enumerate(worst_cases):
                case = test_cases[case_idx]
                expected = expected_results[case_idx]
                print(f"Case {case_idx+1}: PTI diff {pti_diff:.2f}")
                print(f"  PTIs: {case['player_pti']}/{case['partner_pti']} vs {case['opp1_pti']}/{case['opp2_pti']}")
                print(f"  Exp: {case['player_exp'][:3]}/{case['partner_exp'][:3]} vs {case['opp1_exp'][:3]}/{case['opp2_exp'][:3]}")
        
        # Improvement from v2
        print(f"\n🚀 Improvement from v2:")
        print(f"v2 average difference: 16.738")
        print(f"v3 average difference: {avg_pti_diff:.3f}")
        improvement = ((16.738 - avg_pti_diff) / 16.738) * 100
        print(f"Improvement: {improvement:.1f}%")
        
        # Save v3 results
        analysis_data = {
            "algorithm_version": "v3",
            "summary": {
                "total_cases": 100,
                "successful_cases": len(differences),
                "failed_cases": failed_cases,
                "avg_pti_difference": avg_pti_diff,
                "avg_adjustment_difference": avg_adj_diff,
                "improvement_from_v2_percent": improvement
            },
            "experience_performance": {
                exp: {"count": data["count"], "avg_diff": statistics.mean(data["diffs"]) if data["diffs"] else 0}
                for exp, data in experience_performance.items()
            }
        }
        
        with open("100_case_v3_analysis.json", "w") as f:
            json.dump(analysis_data, f, indent=2)
        
        print(f"\n💾 v3 analysis saved to 100_case_v3_analysis.json")
        
        return avg_pti_diff, avg_adj_diff
    else:
        print("❌ No successful test cases to analyze")
        return None, None

def main():
    """Main testing function"""
    print("🚀 PTI Algorithm v3 - 100 Random Cases Test")
    print("=" * 65)
    
    # Run the comprehensive test
    avg_pti_diff, avg_adj_diff = run_100_case_v3_comparison()
    
    if avg_pti_diff is not None:
        print("\n🎯 v3 Summary:")
        if avg_pti_diff < 1.0:
            print("✅ v3 algorithm is performing excellently!")
            print("✅ Ready for production integration!")
        elif avg_pti_diff < 2.0:
            print("✅ v3 algorithm is performing well!")
            print("✅ Minor calibration may further improve accuracy.")
        else:
            print("⚠️ v3 algorithm needs further refinement.")
    
    print("\n✅ v3 100-case analysis complete!")

if __name__ == "__main__":
    main() 