#!/usr/bin/env python3
"""
Test 100 Random PTI Cases

Generate 100 random test cases and compare our algorithm against the patterns
we discovered to identify areas for improvement.
"""

import sys
import os
import random
import json
import subprocess
import statistics
from typing import List, Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.pti_calculator_service_v2 import calculate_pti_v2

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

def create_nodejs_calculator_for_random_cases(test_cases: List[Dict[str, Any]]):
    """Create a Node.js calculator for the random cases"""
    
    nodejs_code = f'''
// Random Cases PTI Calculator
const fs = require('fs');

// Experience level mappings  
const expToSigma = {{
    "30+ matches": 3.2,
    "30+": 3.2,
    "10-30 Matches": 4.0,
    "10-30": 4.0,
    "1-10 matches": 5.0,
    "1-10": 5.0,
    "New Player": 7.0,
    "New": 7.0
}};

// Main calculation function (using our discovered patterns)
function calculatePTI(testCase) {{
    const playerPti = testCase.player_pti;
    const partnerPti = testCase.partner_pti;
    const opp1Pti = testCase.opp1_pti;
    const opp2Pti = testCase.opp2_pti;
    
    const playerSigma = expToSigma[testCase.player_exp] || 3.2;
    const partnerSigma = expToSigma[testCase.partner_exp] || 3.2;
    const opp1Sigma = expToSigma[testCase.opp1_exp] || 3.2;
    const opp2Sigma = expToSigma[testCase.opp2_exp] || 3.2;
    
    // Team averages
    const team1Avg = (playerPti + partnerPti) / 2;
    const team2Avg = (opp1Pti + opp2Pti) / 2;
    
    // Calculate spread
    const spread = Math.abs(team1Avg - team2Avg);
    
    // Determine who wins based on score
    const score = testCase.score;
    const sets = score.split(',');
    let team1Wins = 0;
    let team2Wins = 0;
    
    for (const set of sets) {{
        const [score1, score2] = set.trim().split('-').map(Number);
        if (score1 > score2) team1Wins++;
        else team2Wins++;
    }}
    
    const playerWins = team1Wins > team2Wins;
    
    // Calculate expected probability (Elo-style)
    const ratingDiff = team1Avg - team2Avg;
    const expectedProb = 1 / (1 + Math.pow(10, -ratingDiff / 400));
    
    // Calculate adjustment
    const actualResult = playerWins ? 1.0 : 0.0;
    const probDiff = actualResult - expectedProb;
    
    // K-factor based on experience (average of team sigmas)
    const avgSigma = (playerSigma + partnerSigma) / 2;
    const kFactor = avgSigma * 10; // Original pattern we discovered
    
    const adjustment = Math.abs(kFactor * probDiff);
    
    // Calculate new PTIs
    const change = playerWins ? -adjustment : adjustment;
    
    const playerAfter = playerPti + change;
    const partnerAfter = partnerPti + change;
    const opp1After = opp1Pti - change;
    const opp2After = opp2Pti - change;
    
    return {{
        id: testCase.id,
        description: testCase.description,
        spread: spread,
        adjustment: adjustment,
        player_before: playerPti,
        player_after: parseFloat(playerAfter.toFixed(2)),
        partner_before: partnerPti,
        partner_after: parseFloat(partnerAfter.toFixed(2)),
        opp1_before: opp1Pti,
        opp1_after: parseFloat(opp1After.toFixed(2)),
        opp2_before: opp2Pti,
        opp2_after: parseFloat(opp2After.toFixed(2)),
        success: true,
        expected_prob: expectedProb,
        k_factor: kFactor,
        player_wins: playerWins
    }};
}}

// Test cases
const testCases = {json.dumps(test_cases)};

// Calculate all test cases
const results = testCases.map(calculatePTI);

// Output results
console.log(JSON.stringify(results, null, 2));

// Also save to file
fs.writeFileSync('random_100_expected.json', JSON.stringify(results, null, 2));
console.error(`Calculated ${{results.length}} random test cases.`);
'''
    
    with open("random_cases_calculator.js", "w") as f:
        f.write(nodejs_code)

def run_100_case_comparison():
    """Run comprehensive comparison of 100 random cases"""
    print("🎯 Generating 100 Random PTI Test Cases")
    print("=" * 50)
    
    # Generate test cases
    test_cases = generate_random_test_cases(100)
    print(f"✅ Generated {len(test_cases)} random test cases")
    
    # Create Node.js calculator with our discovered patterns
    create_nodejs_calculator_for_random_cases(test_cases)
    print("✅ Created Node.js reference calculator")
    
    # Run Node.js calculator to get "expected" results based on our patterns
    print("🚀 Running Node.js reference calculations...")
    try:
        result = subprocess.run(['node', 'random_cases_calculator.js'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            expected_results = json.loads(result.stdout)
            print(f"✅ Generated {len(expected_results)} reference results")
        else:
            print(f"❌ Node.js execution failed: {result.stderr}")
            return
    except Exception as e:
        print(f"❌ Error running Node.js: {e}")
        return
    
    # Run our algorithm on all test cases
    print("🧪 Testing our algorithm on 100 random cases...")
    
    our_results = []
    differences = []
    adjustment_diffs = []
    failed_cases = 0
    
    for i, test_case in enumerate(test_cases):
        try:
            result = calculate_pti_v2(
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
                
            else:
                failed_cases += 1
                print(f"❌ Case {i+1} failed: {result}")
                
        except Exception as e:
            failed_cases += 1
            print(f"❌ Case {i+1} exception: {e}")
    
    # Analyze results
    print("\n📊 Results Analysis")
    print("=" * 30)
    
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
        print("\n🎯 Accuracy Assessment:")
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
        
        # Identify patterns in worst cases
        print("\n🔍 Worst Cases Analysis:")
        case_diffs = list(zip(differences, adjustment_diffs, range(len(differences))))
        worst_cases = sorted(case_diffs, key=lambda x: x[0], reverse=True)[:5]
        
        for i, (pti_diff, adj_diff, case_idx) in enumerate(worst_cases):
            case = test_cases[case_idx]
            expected = expected_results[case_idx]
            print(f"Case {case_idx+1}: PTI diff {pti_diff:.2f}, Adj diff {adj_diff:.2f}")
            print(f"  PTIs: {case['player_pti']}/{case['partner_pti']} vs {case['opp1_pti']}/{case['opp2_pti']}")
            print(f"  Exp: {case['player_exp']}/{case['partner_exp']} vs {case['opp1_exp']}/{case['opp2_exp']}")
            print(f"  Expected K-factor: {expected['k_factor']:.1f}")
        
        # Save detailed results for analysis
        analysis_data = {
            "summary": {
                "total_cases": 100,
                "successful_cases": len(differences),
                "failed_cases": failed_cases,
                "avg_pti_difference": avg_pti_diff,
                "avg_adjustment_difference": avg_adj_diff
            },
            "test_cases": test_cases,
            "expected_results": expected_results,
            "our_results": our_results,
            "differences": differences,
            "adjustment_differences": adjustment_diffs
        }
        
        with open("100_case_analysis.json", "w") as f:
            json.dump(analysis_data, f, indent=2)
        
        print(f"\n💾 Detailed analysis saved to 100_case_analysis.json")
        
        return avg_pti_diff, avg_adj_diff
    else:
        print("❌ No successful test cases to analyze")
        return None, None

def suggest_improvements(avg_pti_diff: float, avg_adj_diff: float):
    """Suggest improvements based on analysis"""
    print("\n🔧 Improvement Suggestions")
    print("=" * 35)
    
    if avg_adj_diff > 1.0:
        print("1. K-factor calibration needs refinement")
        print("   - Current base K-factor: 4.86")
        print("   - Consider adjusting based on experience level patterns")
    
    if avg_pti_diff > avg_adj_diff:
        print("2. Experience multipliers may need adjustment")
        print("   - Review New Player vs 30+ ratios")
        print("   - Check 10-30 and 1-10 multipliers")
    
    print("3. Potential algorithm enhancements:")
    print("   - Score margin impact (blowouts vs close games)")
    print("   - Team balance effects (mixed vs balanced teams)")
    print("   - PTI range adjustments (high vs low PTI players)")

def main():
    """Main testing function"""
    print("🚀 100 Random Cases PTI Algorithm Test")
    print("=" * 60)
    
    # Run the comprehensive test
    avg_pti_diff, avg_adj_diff = run_100_case_comparison()
    
    if avg_pti_diff is not None:
        # Suggest improvements
        suggest_improvements(avg_pti_diff, avg_adj_diff)
        
        print("\n🎯 Next Steps:")
        print("1. Review worst cases in 100_case_analysis.json")
        print("2. Adjust K-factors based on patterns found")
        print("3. Re-run test to validate improvements")
    
    print("\n✅ 100-case analysis complete!")

if __name__ == "__main__":
    main() 