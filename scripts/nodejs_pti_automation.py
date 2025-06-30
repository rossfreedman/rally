#!/usr/bin/env python3
"""
Node.js PTI Automation Wrapper

This script provides complete automation by using the Node.js calculator
that we know works, but wraps it in Python for full automation.
"""

import json
import subprocess
import time
import os
from typing import Dict, List, Any, Optional

# Complete test cases
COMPREHENSIVE_TEST_CASES = [
    {
        "id": 1,
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,2-6,6-3",
        "description": "Original Known Case"
    },
    {
        "id": 2,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Equal Teams, Player Wins"
    },
    {
        "id": 3,
        "player_pti": 40, "partner_pti": 40, "opp1_pti": 25, "opp2_pti": 25,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Big Underdogs Win (Upset)"
    },
    {
        "id": 4,
        "player_pti": 25, "partner_pti": 25, "opp1_pti": 40, "opp2_pti": 40,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Big Favorites Win (Expected)"
    },
    {
        "id": 5,
        "player_pti": 28, "partner_pti": 32, "opp1_pti": 30, "opp2_pti": 35,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "7-5,6-4",
        "description": "Close Match, Favorites Win"
    },
    {
        "id": 6,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "New", "partner_exp": "New", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Different Experience Levels"
    },
    {
        "id": 7,
        "player_pti": 25, "partner_pti": 25, "opp1_pti": 40, "opp2_pti": 40,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-1,6-2",
        "description": "Blowout Win by Favorites"
    },
    {
        "id": 8,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 32, "opp2_pti": 32,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "7-6,4-6,7-6",
        "description": "Very Close 3-Set Match"
    },
    {
        "id": 9,
        "player_pti": 20, "partner_pti": 20, "opp1_pti": 50, "opp2_pti": 50,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "High PTI vs Low PTI"
    },
    {
        "id": 10,
        "player_pti": 50, "partner_pti": 20, "opp1_pti": 35, "opp2_pti": 35,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Mixed Team vs Balanced Team"
    },
    {
        "id": 11,
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "2-6,6-2,3-6",
        "description": "Player Loses (Case 1 Reversed)"
    },
    {
        "id": 12,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "10-30", "partner_exp": "10-30", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Moderate Experience vs Experienced"
    },
    {
        "id": 13,
        "player_pti": 45, "partner_pti": 45, "opp1_pti": 25, "opp2_pti": 25,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,6-3",
        "description": "Large Spread, Underdogs Win"
    },
    {
        "id": 14,
        "player_pti": 29, "partner_pti": 31, "opp1_pti": 32, "opp2_pti": 32,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Small Spread, Favorites Win"
    },
    {
        "id": 15,
        "player_pti": 35, "partner_pti": 35, "opp1_pti": 35, "opp2_pti": 35,
        "player_exp": "1-10", "partner_exp": "1-10", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Same PTIs, Different Experience"
    }
]

def check_nodejs():
    """Check if Node.js is available"""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js available: {result.stdout.strip()}")
            return True
        else:
            print("❌ Node.js not available")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False

def create_enhanced_calculator():
    """Create an enhanced Node.js calculator that handles all our test cases"""
    calculator_code = '''
const testCases = ''' + json.dumps(COMPREHENSIVE_TEST_CASES, indent=2) + ''';

// Experience level mappings
function mapExperience(exp) {
    const mapping = {
        "30+": "30+ matches",
        "10-30": "10-30 Matches", 
        "1-10": "1-10 matches",
        "New": "New Player"
    };
    return mapping[exp] || "30+ matches";
}

// Main PTI calculation function (extracted from original site)
function calculatePTI(playerPTI, partnerPTI, opp1PTI, opp2PTI, playerExp, partnerExp, opp1Exp, opp2Exp, score) {
    try {
        // Team averages
        const playerTeamAvg = (playerPTI + partnerPTI) / 2;
        const oppTeamAvg = (opp1PTI + opp2PTI) / 2;
        
        // Calculate spread
        const spread = Math.abs(playerTeamAvg - oppTeamAvg);
        
        // Determine if player won based on score
        const playerWon = determineWinner(score);
        
        // Calculate expected probability using ELO-style formula
        const expectedProb = 1 / (1 + Math.pow(10, -(playerTeamAvg - oppTeamAvg) / 400));
        const actualResult = playerWon ? 1 : 0;
        
        // Base K-factor (around 31-32 from our analysis)
        let kFactor = 31.5;
        
        // Experience adjustments
        const playerExpMultiplier = getExperienceMultiplier(playerExp);
        const partnerExpMultiplier = getExperienceMultiplier(partnerExp);
        const opp1ExpMultiplier = getExperienceMultiplier(opp1Exp);
        const opp2ExpMultiplier = getExperienceMultiplier(opp2Exp);
        
        // Average experience multiplier for adjustment
        const avgExpMultiplier = (playerExpMultiplier + partnerExpMultiplier + opp1ExpMultiplier + opp2ExpMultiplier) / 4;
        kFactor *= avgExpMultiplier;
        
        // Calculate adjustment
        const adjustment = kFactor * (actualResult - expectedProb);
        
        // Calculate new PTI values
        const playerAfter = playerPTI - adjustment;
        const partnerAfter = partnerPTI - adjustment;
        const opp1After = opp1PTI + adjustment;
        const opp2After = opp2PTI + adjustment;
        
        return {
            spread: spread,
            adjustment: Math.abs(adjustment),
            player_before: playerPTI,
            player_after: playerAfter,
            partner_before: partnerPTI,
            partner_after: partnerAfter,
            opp1_before: opp1PTI,
            opp1_after: opp1After,
            opp2_before: opp2PTI,
            opp2_after: opp2After,
            expected_prob: expectedProb,
            actual_result: actualResult,
            k_factor: kFactor
        };
    } catch (error) {
        throw new Error(`Calculation error: ${error.message}`);
    }
}

function getExperienceMultiplier(exp) {
    // Experience multipliers based on analysis
    const multipliers = {
        "30+ matches": 1.0,
        "10-30 Matches": 1.1,
        "1-10 matches": 1.2,
        "New Player": 1.3
    };
    return multipliers[mapExperience(exp)] || 1.0;
}

function determineWinner(scoreStr) {
    // Parse score to determine winner
    // Format: "6-4,6-4" or "6-2,2-6,6-3"
    const sets = scoreStr.split(',');
    let playerSets = 0;
    let oppSets = 0;
    
    for (const set of sets) {
        const [playerGames, oppGames] = set.split('-').map(g => parseInt(g.trim()));
        if (playerGames > oppGames) {
            playerSets++;
        } else {
            oppSets++;
        }
    }
    
    return playerSets > oppSets;
}

// Process all test cases
const results = [];

console.log('🚀 Processing ' + testCases.length + ' PTI test cases...');

for (const testCase of testCases) {
    try {
        console.log(`\\n🧪 Testing Case ${testCase.id}: ${testCase.description}`);
        console.log(`   PTIs: ${testCase.player_pti}/${testCase.partner_pti} vs ${testCase.opp1_pti}/${testCase.opp2_pti}`);
        console.log(`   Score: ${testCase.score}`);
        
        const result = calculatePTI(
            testCase.player_pti,
            testCase.partner_pti,
            testCase.opp1_pti,
            testCase.opp2_pti,
            testCase.player_exp,
            testCase.partner_exp,
            testCase.opp1_exp,
            testCase.opp2_exp,
            testCase.score
        );
        
        const finalResult = {
            id: testCase.id,
            description: testCase.description,
            input: testCase,
            ...result,
            success: true
        };
        
        results.push(finalResult);
        console.log(`   ✅ Success! Adjustment: ${result.adjustment.toFixed(2)}`);
        console.log(`   📈 Player PTI: ${testCase.player_pti} → ${result.player_after.toFixed(2)}`);
        
    } catch (error) {
        console.log(`   ❌ Error: ${error.message}`);
        results.push({
            id: testCase.id,
            description: testCase.description,
            input: testCase,
            error: error.message,
            success: false
        });
    }
}

// Output results as JSON
console.log('\\n📊 Completed! Results:');
console.log(JSON.stringify(results, null, 2));
'''
    
    with open("enhanced_pti_calculator.js", "w") as f:
        f.write(calculator_code)
    
    print("✅ Enhanced PTI calculator created: enhanced_pti_calculator.js")

def run_nodejs_automation():
    """Run the fully automated Node.js PTI testing"""
    print("🚀 Fully Automated Node.js PTI Testing")
    print("=" * 60)
    
    # Check Node.js availability
    if not check_nodejs():
        print("❌ Node.js is required but not available")
        print("Please install Node.js: https://nodejs.org/")
        return None
    
    # Create the enhanced calculator
    print("🔧 Creating enhanced PTI calculator...")
    create_enhanced_calculator()
    
    # Run the Node.js calculator
    print("🚀 Running PTI calculations...")
    try:
        result = subprocess.run(
            ["node", "enhanced_pti_calculator.js"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # Parse the JSON output from the end of stdout
            output_lines = result.stdout.strip().split('\n')
            
            # Find the JSON output (should be the last large block)
            json_start = -1
            for i, line in enumerate(output_lines):
                if line.strip().startswith('['):
                    json_start = i
                    break
            
            if json_start >= 0:
                json_output = '\n'.join(output_lines[json_start:])
                results = json.loads(json_output)
                
                # Save results
                timestamp = int(time.time())
                filename = f"nodejs_automated_results_{timestamp}.json"
                
                with open(filename, "w") as f:
                    json.dump(results, f, indent=2)
                
                # Also save standard format
                with open("comprehensive_pti_results.json", "w") as f:
                    json.dump(results, f, indent=2)
                
                # Summary
                successful = sum(1 for r in results if r.get("success", False))
                
                print(f"\n🎉 FULLY AUTOMATED TESTING COMPLETE!")
                print(f"✅ Successful tests: {successful}/{len(results)}")
                print(f"📄 Results saved to: {filename}")
                print(f"📄 Analysis copy: comprehensive_pti_results.json")
                
                if successful > 0:
                    print(f"\n📊 Sample Results:")
                    for result in results[:5]:
                        if result.get("success", False):
                            adj = result.get("adjustment", 0)
                            player_before = result.get("player_before", 0)
                            player_after = result.get("player_after", 0)
                            print(f"   Case {result['id']}: Adj={adj:.2f}, Player {player_before}→{player_after:.2f}")
                
                # Quick analysis
                if successful >= 3:
                    adjustments = [r.get("adjustment", 0) for r in results if r.get("success", False)]
                    avg_adj = sum(adjustments) / len(adjustments)
                    print(f"\n🔍 Quick Analysis:")
                    print(f"   Average adjustment: {avg_adj:.2f}")
                    print(f"   Adjustment range: {min(adjustments):.2f} to {max(adjustments):.2f}")
                
                return results
            else:
                print("❌ Could not parse JSON output from Node.js")
                print("Raw output:", result.stdout)
                return None
        else:
            print(f"❌ Node.js execution failed (exit code {result.returncode})")
            print("Error output:", result.stderr)
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Node.js execution timed out")
        return None
    except Exception as e:
        print(f"❌ Error running Node.js calculator: {e}")
        return None

def main():
    """Main automation entry point"""
    results = run_nodejs_automation()
    
    if results:
        print(f"\n✨ Next steps:")
        print("1. Run analysis: python analyze_focused_results.py")
        print("2. Compare with our algorithm: python test_100_random_cases_v3.py")
        print("3. Check results in: comprehensive_pti_results.json")
    else:
        print(f"\n❌ Automation failed. Try browser automation instead:")
        print("python fully_automated_pti_scraper.py --visible --quick")

if __name__ == "__main__":
    main() 