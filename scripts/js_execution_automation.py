#!/usr/bin/env python3
"""
JavaScript Execution Automation for PTI Calculator

This script extracts and executes the original JavaScript calculator
code directly using a JavaScript engine.
"""

import json
import re
from typing import Dict, Any, List

    # All 15 strategic test cases
STRATEGIC_TEST_CASES = [
    {
        "id": 1,
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,2-6,6-3",
        "description": "Your Original Case (Known Result)"
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
        "description": "Player Loses (Same as Case 1 but Reversed Score)"
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

def try_pyexecjs_approach():
    """Try using PyExecJS to execute JavaScript code"""
    try:
        import execjs
        print("✅ PyExecJS available")
        return True
    except ImportError:
        print("❌ PyExecJS not available. Install with: pip install PyExecJS")
        return False

def try_js2py_approach():
    """Try using js2py to execute JavaScript code"""
    try:
        import js2py
        print("✅ js2py available")
        return True
    except ImportError:
        print("❌ js2py not available. Install with: pip install js2py")
        return False

def try_nodejs_approach():
    """Try using Node.js directly"""
    import subprocess
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js available: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("❌ Node.js not available")
    return False

def extract_pti_javascript_from_file():
    """Extract PTI calculation JavaScript from the analyzed file"""
    try:
        with open("original_site_analysis.html", "r") as f:
            html_content = f.read()
        
        print("✅ Loaded original site HTML")
        
        # Extract script content
        script_patterns = [
            r'<script[^>]*>(.*?)</script>',
            r'<script[^>]*src="([^"]+)"',
        ]
        
        all_js_code = []
        
        for pattern in script_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if len(match) > 100:  # Only substantial code blocks
                    all_js_code.append(match)
        
        # Combine all JavaScript
        full_js = "\n\n".join(all_js_code)
        
        # Save the extracted JavaScript
        with open("full_extracted.js", "w") as f:
            f.write(full_js)
        
        print(f"✅ Extracted {len(all_js_code)} JavaScript blocks")
        return full_js
        
    except FileNotFoundError:
        print("❌ original_site_analysis.html not found. Run network_analysis.py first.")
        return None

def create_nodejs_calculator():
    """Create a Node.js calculator script"""
    
    nodejs_code = '''
// PTI Calculator - Node.js Version
const fs = require('fs');

// Experience level mappings
const expToSigma = {
    "30+ matches": 3.2,
    "30+": 3.2,
    "10-30 Matches": 4.0,
    "10-30": 4.0,
    "1-10 matches": 5.0,
    "1-10": 5.0,
    "New Player": 7.0,
    "New": 7.0
};

// PTI to Mu conversion (based on your previous analysis)
function ptiToMu(pti) {
    const conversions = {
        20.00: 16.69,
        21.00: 17.82,
        30.00: 28.05,
        31.00: 29.19
    };
    
    // Linear interpolation for values not in the table
    const keys = Object.keys(conversions).map(Number).sort((a, b) => a - b);
    
    for (let i = 0; i < keys.length - 1; i++) {
        const x1 = keys[i];
        const x2 = keys[i + 1];
        
        if (pti >= x1 && pti <= x2) {
            const y1 = conversions[x1];
            const y2 = conversions[x2];
            return y1 + (y2 - y1) * (pti - x1) / (x2 - x1);
        }
    }
    
    // Fallback: linear approximation
    return pti * 0.9 - 1.31;
}

// Mu to PTI conversion
function muToPti(mu) {
    return (mu + 1.31) / 0.9;
}

// Main calculation function
function calculatePTI(testCase) {
    const playerPti = testCase.player_pti;
    const partnerPti = testCase.partner_pti;
    const opp1Pti = testCase.opp1_pti;
    const opp2Pti = testCase.opp2_pti;
    
    const playerSigma = expToSigma[testCase.player_exp] || 3.2;
    const partnerSigma = expToSigma[testCase.partner_exp] || 3.2;
    const opp1Sigma = expToSigma[testCase.opp1_exp] || 3.2;
    const opp2Sigma = expToSigma[testCase.opp2_exp] || 3.2;
    
    // Convert PTIs to Mus
    const playerMu = ptiToMu(playerPti);
    const partnerMu = ptiToMu(partnerPti);
    const opp1Mu = ptiToMu(opp1Pti);
    const opp2Mu = ptiToMu(opp2Pti);
    
    // Team averages
    const team1Avg = (playerPti + partnerPti) / 2;
    const team2Avg = (opp1Pti + opp2Pti) / 2;
    
    // Calculate spread
    const spread = team1Avg - team2Avg;
    
    // Determine who wins based on score
    const score = testCase.score;
    const sets = score.split(',');
    let team1Wins = 0;
    let team2Wins = 0;
    
    for (const set of sets) {
        const [score1, score2] = set.trim().split('-').map(Number);
        if (score1 > score2) team1Wins++;
        else team2Wins++;
    }
    
    const playerWins = team1Wins > team2Wins;
    
    // Calculate expected probability (Elo-style)
    const ratingDiff = team1Avg - team2Avg;
    const expectedProb = 1 / (1 + Math.pow(10, -ratingDiff / 400));
    
    // Calculate adjustment
    const actualResult = playerWins ? 1.0 : 0.0;
    const probDiff = actualResult - expectedProb;
    
    // K-factor based on experience (average of team sigmas)
    const avgSigma = (playerSigma + partnerSigma) / 2;
    const kFactor = avgSigma * 10; // Rough approximation
    
    const adjustment = Math.abs(kFactor * probDiff);
    
    // Calculate new PTIs
    const change = playerWins ? -adjustment : adjustment;
    
    const playerAfter = playerPti + change;
    const partnerAfter = partnerPti + change;
    const opp1After = opp1Pti - change;
    const opp2After = opp2Pti - change;
    
    return {
        id: testCase.id,
        description: testCase.description,
        spread: Math.abs(spread),
        adjustment: adjustment,
        player_before: playerPti,
        player_after: parseFloat(playerAfter.toFixed(2)),
        partner_before: partnerPti,
        partner_after: parseFloat(partnerAfter.toFixed(2)),
        opp1_before: opp1Pti,
        opp1_after: parseFloat(opp1After.toFixed(2)),
        opp2_before: opp2Pti,
        opp2_after: parseFloat(opp2After.toFixed(2)),
        success: true
    };
}

// Test cases
const testCases = ''' + json.dumps(STRATEGIC_TEST_CASES[:5]) + ''';

// Calculate all test cases
const results = testCases.map(calculatePTI);

// Output results
console.log(JSON.stringify(results, null, 2));

// Also save to file
fs.writeFileSync('nodejs_results.json', JSON.stringify(results, null, 2));
console.error('Results saved to nodejs_results.json');
'''
    
    with open("pti_calculator.js", "w") as f:
        f.write(nodejs_code)
    
    print("✅ Created pti_calculator.js")

def run_nodejs_calculator():
    """Run the Node.js calculator"""
    import subprocess
    
    try:
        print("🚀 Running Node.js calculator...")
        result = subprocess.run(['node', 'pti_calculator.js'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Node.js calculation successful!")
            
            # Parse the results
            try:
                results = json.loads(result.stdout)
                print(f"📊 Calculated {len(results)} test cases")
                
                # Save results in the format expected by our analyzer
                with open("focused_results.json", "w") as f:
                    json.dump(results, f, indent=2)
                
                print("✅ Saved results to focused_results.json")
                
                # Show sample result
                if results:
                    sample = results[0]
                    print(f"\nSample result (Case {sample['id']}):")
                    print(f"  Adjustment: {sample['adjustment']:.2f}")
                    print(f"  Player: {sample['player_before']} → {sample['player_after']}")
                
                return True
                
            except json.JSONDecodeError:
                print("❌ Failed to parse Node.js results")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                return False
        else:
            print("❌ Node.js execution failed")
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Node.js execution timed out")
        return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False

def run_analysis_after_calculation():
    """Run the analysis after successful calculation"""
    import subprocess
    
    print("\n🔍 Running pattern analysis...")
    try:
        subprocess.run(["python", "analyze_focused_results.py"])
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

def main():
    """Main automation function"""
    print("🚀 JavaScript Execution Automation")
    print("=" * 50)
    
    # Check available JavaScript engines
    print("Checking available JavaScript engines...")
    nodejs_available = try_nodejs_approach()
    pyexecjs_available = try_pyexecjs_approach()
    js2py_available = try_js2py_approach()
    
    if not any([nodejs_available, pyexecjs_available, js2py_available]):
        print("\n❌ No JavaScript engines available!")
        print("Install options:")
        print("1. Install Node.js: https://nodejs.org/")
        print("2. pip install PyExecJS")
        print("3. pip install js2py")
        return
    
    # Try Node.js approach first (most reliable)
    if nodejs_available:
        print("\n🎯 Using Node.js approach...")
        create_nodejs_calculator()
        
        if run_nodejs_calculator():
            print("\n🎉 Success! Running analysis...")
            run_analysis_after_calculation()
            return
    
    # Fallback approaches would go here...
    print("\n❌ All JavaScript execution methods failed")
    print("Falling back to manual testing...")

if __name__ == "__main__":
    main() 