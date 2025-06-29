// Complete PTI Calculator - All 15 Test Cases
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
    const kFactor = avgSigma * 10; // Approximation
    
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
        success: true
    };
}

// All 15 test cases
const testCases = [
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
        "player_exp": "New Player", "partner_exp": "New Player", "opp1_exp": "30+ matches", "opp2_exp": "30+ matches",
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
        "player_exp": "10-30 Matches", "partner_exp": "10-30 Matches", "opp1_exp": "30+ matches", "opp2_exp": "30+ matches",
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
        "player_exp": "1-10 matches", "partner_exp": "1-10 matches", "opp1_exp": "30+ matches", "opp2_exp": "30+ matches",
        "score": "6-4,6-4",
        "description": "Same PTIs, Different Experience"
    }
];

// Calculate all test cases
const results = testCases.map(calculatePTI);

// Output results
console.log(JSON.stringify(results, null, 2));

// Also save to file
fs.writeFileSync('complete_results.json', JSON.stringify(results, null, 2));
fs.writeFileSync('focused_results.json', JSON.stringify(results, null, 2));
console.error(`Results saved! Calculated ${results.length} test cases.`); 