# Strategic PTI Algorithm Test Cases

## Goal
Efficiently reverse engineer the PTI algorithm with 15 strategic test cases covering key scenarios.

## Instructions
1. Visit: [https://calc.platform.tennis/calculator2.html](https://calc.platform.tennis/calculator2.html)
2. Test these 15 cases systematically
3. Record results in the JSON format provided
4. Look for patterns to reverse engineer the algorithm

---

## Test Case 1: Your Original Case (Known Result)
- **Player PTI**: 50, **Partner PTI**: 40
- **Opp1 PTI**: 30, **Opp2 PTI**: 23
- **Experience**: All "30+ matches" 
- **Score**: 6-2,2-6,6-3
- **Expected Result**: Player 47.70 (-2.30), Partner 37.70 (-2.30), Opp1 32.39 (+2.39), Opp2 25.39 (+2.39)

```json
{"id": 1, "spread": 37.0, "adjustment": 2.30, "player_before": 50, "player_after": 47.70, "partner_before": 40, "partner_after": 37.70, "opp1_before": 30, "opp1_after": 32.39, "opp2_before": 23, "opp2_after": 25.39}
```

---

## Test Case 2: Equal Teams, Player Wins
- **Player PTI**: 30, **Partner PTI**: 30
- **Opp1 PTI**: 30, **Opp2 PTI**: 30
- **Experience**: All "30+ matches"
- **Score**: 6-4,6-4

```json
{"id": 2, "spread": X.XX, "adjustment": X.XX, "player_before": 30, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}
```

---

## Test Case 3: Big Underdogs Win (Upset)
- **Player PTI**: 40, **Partner PTI**: 40
- **Opp1 PTI**: 25, **Opp2 PTI**: 25
- **Experience**: All "30+ matches"
- **Score**: 6-3,6-4

```json
{"id": 3, "spread": X.XX, "adjustment": X.XX, "player_before": 40, "player_after": XX.XX, "partner_before": 40, "partner_after": XX.XX, "opp1_before": 25, "opp1_after": XX.XX, "opp2_before": 25, "opp2_after": XX.XX}
```

---

## Test Case 4: Big Favorites Win (Expected)
- **Player PTI**: 25, **Partner PTI**: 25
- **Opp1 PTI**: 40, **Opp2 PTI**: 40
- **Experience**: All "30+ matches"
- **Score**: 6-3,6-4

```json
{"id": 4, "spread": X.XX, "adjustment": X.XX, "player_before": 25, "player_after": XX.XX, "partner_before": 25, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}
```

---

## Test Case 5: Close Match, Favorites Win
- **Player PTI**: 28, **Partner PTI**: 32
- **Opp1 PTI**: 30, **Opp2 PTI**: 35
- **Experience**: All "30+ matches"
- **Score**: 7-5,6-4

```json
{"id": 5, "spread": X.XX, "adjustment": X.XX, "player_before": 28, "player_after": XX.XX, "partner_before": 32, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 35, "opp2_after": XX.XX}
```

---

## Test Case 6: Different Experience Levels
- **Player PTI**: 30, **Partner PTI**: 30
- **Opp1 PTI**: 30, **Opp2 PTI**: 30
- **Experience**: Player/Partner "New Player", Opp1/Opp2 "30+ matches"
- **Score**: 6-4,6-4

```json
{"id": 6, "spread": X.XX, "adjustment": X.XX, "player_before": 30, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}
```

---

## Test Case 7: Blowout Win by Favorites
- **Player PTI**: 25, **Partner PTI**: 25
- **Opp1 PTI**: 40, **Opp2 PTI**: 40
- **Experience**: All "30+ matches"
- **Score**: 6-1,6-2

```json
{"id": 7, "spread": X.XX, "adjustment": X.XX, "player_before": 25, "player_after": XX.XX, "partner_before": 25, "partner_after": XX.XX, "opp1_before": 40, "opp1_after": XX.XX, "opp2_before": 40, "opp2_after": XX.XX}
```

---

## Test Case 8: Very Close 3-Set Match
- **Player PTI**: 30, **Partner PTI**: 30
- **Opp1 PTI**: 32, **Opp2 PTI**: 32
- **Experience**: All "30+ matches"
- **Score**: 7-6,4-6,7-6

```json
{"id": 8, "spread": X.XX, "adjustment": X.XX, "player_before": 30, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 32, "opp1_after": XX.XX, "opp2_before": 32, "opp2_after": XX.XX}
```

---

## Test Case 9: High PTI vs Low PTI
- **Player PTI**: 20, **Partner PTI**: 20
- **Opp1 PTI**: 50, **Opp2 PTI**: 50
- **Experience**: All "30+ matches"
- **Score**: 6-4,6-4

```json
{"id": 9, "spread": X.XX, "adjustment": X.XX, "player_before": 20, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 50, "opp1_after": XX.XX, "opp2_before": 50, "opp2_after": XX.XX}
```

---

## Test Case 10: Mixed Team vs Balanced Team
- **Player PTI**: 50, **Partner PTI**: 20
- **Opp1 PTI**: 35, **Opp2 PTI**: 35
- **Experience**: All "30+ matches"
- **Score**: 6-3,6-4

```json
{"id": 10, "spread": X.XX, "adjustment": X.XX, "player_before": 50, "player_after": XX.XX, "partner_before": 20, "partner_after": XX.XX, "opp1_before": 35, "opp1_after": XX.XX, "opp2_before": 35, "opp2_after": XX.XX}
```

---

## Test Case 11: Player Loses (Same as Case 1 but Reversed Score)
- **Player PTI**: 50, **Partner PTI**: 40
- **Opp1 PTI**: 30, **Opp2 PTI**: 23
- **Experience**: All "30+ matches"
- **Score**: 2-6,6-2,3-6

```json
{"id": 11, "spread": X.XX, "adjustment": X.XX, "player_before": 50, "player_after": XX.XX, "partner_before": 40, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 23, "opp2_after": XX.XX}
```

---

## Test Case 12: Moderate Experience vs Experienced
- **Player PTI**: 30, **Partner PTI**: 30
- **Opp1 PTI**: 30, **Opp2 PTI**: 30
- **Experience**: Player/Partner "10-30 Matches", Opp1/Opp2 "30+ matches"
- **Score**: 6-4,6-4

```json
{"id": 12, "spread": X.XX, "adjustment": X.XX, "player_before": 30, "player_after": XX.XX, "partner_before": 30, "partner_after": XX.XX, "opp1_before": 30, "opp1_after": XX.XX, "opp2_before": 30, "opp2_after": XX.XX}
```

---

## Test Case 13: Large Spread, Underdogs Win
- **Player PTI**: 45, **Partner PTI**: 45
- **Opp1 PTI**: 25, **Opp2 PTI**: 25
- **Experience**: All "30+ matches"
- **Score**: 6-2,6-3

```json
{"id": 13, "spread": X.XX, "adjustment": X.XX, "player_before": 45, "player_after": XX.XX, "partner_before": 45, "partner_after": XX.XX, "opp1_before": 25, "opp1_after": XX.XX, "opp2_before": 25, "opp2_after": XX.XX}
```

---

## Test Case 14: Small Spread, Favorites Win
- **Player PTI**: 29, **Partner PTI**: 31
- **Opp1 PTI**: 32, **Opp2 PTI**: 32
- **Experience**: All "30+ matches"
- **Score**: 6-4,6-4

```json
{"id": 14, "spread": X.XX, "adjustment": X.XX, "player_before": 29, "player_after": XX.XX, "partner_before": 31, "partner_after": XX.XX, "opp1_before": 32, "opp1_after": XX.XX, "opp2_before": 32, "opp2_after": XX.XX}
```

---

## Test Case 15: Same PTIs, Different Experience
- **Player PTI**: 35, **Partner PTI**: 35
- **Opp1 PTI**: 35, **Opp2 PTI**: 35
- **Experience**: Player/Partner "1-10 matches", Opp1/Opp2 "30+ matches"
- **Score**: 6-4,6-4

```json
{"id": 15, "spread": X.XX, "adjustment": X.XX, "player_before": 35, "player_after": XX.XX, "partner_before": 35, "partner_after": XX.XX, "opp1_before": 35, "opp1_after": XX.XX, "opp2_before": 35, "opp2_after": XX.XX}
```

---

## Analysis Instructions

After collecting all 15 results, save them as `focused_results.json`:

```json
[
  {"id": 1, "spread": 37.0, "adjustment": 2.30, ...},
  {"id": 2, "spread": X.XX, "adjustment": X.XX, ...},
  ...
]
```

Then analyze patterns:
1. **Equal teams** (Cases 2, 6, 12, 15): How does experience affect adjustments?
2. **Upsets** (Cases 3, 13): How big are adjustments when underdogs win?  
3. **Expected results** (Cases 4, 7): How small are adjustments when favorites win?
4. **Score margin**: Does 6-1,6-2 vs 7-6,4-6,7-6 affect adjustments?
5. **Team composition**: Mixed vs balanced teams (Case 10)

Look for:
- **K-factor patterns** by experience level
- **Scaling factors** for upset vs expected results  
- **Score impact** on adjustment magnitude
- **Base formula** that ties it all together 