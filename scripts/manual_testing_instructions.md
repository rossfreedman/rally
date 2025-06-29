
# Manual Testing Instructions for Original Site

Visit: https://calc.platform.tennis/calculator2.html

For each test case below:
1. Enter the PTI values and experience levels
2. Enter the match score
3. Record the results (Spread, Adjustment, Before/After PTI values)
4. Save results in the format provided

Test Cases:

## Test Case 1
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 1, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 2
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 2, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 3
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 3, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 4
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 4, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 5
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 5, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 6
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 6, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 7
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 7, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 8
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 8, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 9
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 9, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 10
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 10, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 11
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 11, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 12
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 12, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 13
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 13, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 14
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 14, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 15
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 15, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 16
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 16, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 17
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 17, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 18
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 18, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 19
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 19, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 20
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 20, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 21
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 30, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 21, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 22
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 22, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 23
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 23, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 24
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 24, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 25
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 25, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 26
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 26, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 27
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 27, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 28
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 28, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 29
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 29, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 30
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 30, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 31
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 31, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 32
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 32, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 33
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 40, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 33, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 34
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 34, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 35
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 35, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 36
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 36, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 37
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 37, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 38
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 38, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 39
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 30, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 39, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}

## Test Case 40
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 40, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 41
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 41, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 42
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 42, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 43
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 43, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 44
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 44, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 45
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 20, Exp: 30+ matches  
- Opp1 PTI: 50, Exp: 30+ matches
- Opp2 PTI: 50, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Favorites win

Record as JSON:
{"id": 45, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}

## Test Case 46
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 30, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Underdogs win

Record as JSON:
{"id": 46, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 47
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 30, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Underdogs win

Record as JSON:
{"id": 47, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 48
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 30, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 20, Exp: 30+ matches
- Score: 7-5,6-4
- Expected: Underdogs win

Record as JSON:
{"id": 48, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 20, "opp2_after": XX.XX}

## Test Case 49
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 30, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-2,6-3
- Expected: Favorites win

Record as JSON:
{"id": 49, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}

## Test Case 50
- Player PTI: 20, Exp: 30+ matches
- Partner PTI: 30, Exp: 30+ matches  
- Opp1 PTI: 20, Exp: 30+ matches
- Opp2 PTI: 40, Exp: 30+ matches
- Score: 6-4,6-4
- Expected: Favorites win

Record as JSON:
{"id": 50, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 20, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}
