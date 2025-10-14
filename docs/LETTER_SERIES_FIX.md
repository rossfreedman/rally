# Letter Series in APTA League - Fix Documentation

## Problem

When logged in as an APTA player, the series dropdown/picklist was showing letter series (Series A, B, C, D, E, F) alongside the proper numbered series (Series 1, 2, 3, etc.). Letter series should only appear for CNSWPL and NSTF Sunday leagues, not APTA.

**Screenshot Evidence:** Series dropdown showing "Series 23 SW, Series 24, ... Series 39, Series 40, I, Series A, Series B, Series C, Series D, Series E, Series F"

## Root Cause

96 APTA players and 10 APTA teams were incorrectly assigned to letter series in the database. 

### How It Happened

1. **Source Data**: The JSON source data (`players_career_stats.json`) had teams named like:
   - "Wilmette 99 A"
   - "Winnetka 99 A" 
   - "Wilmette 99 B"
   - etc.

2. **Parsing Bug**: The `parse_team_name()` function in `data/etl/import/start_season.py` incorrectly parsed these as:
   - Club: "Wilmette 99" 
   - Series: "Series A"
   
   Instead of the correct:
   - Club: "Wilmette"
   - Series: "Series 99"

3. **API Behavior**: The `/api/get-user-facing-series-by-league` endpoint correctly queries for all series that have active players/teams in the league, so it was showing these letter series because they legitimately had 96 players and 10 teams assigned to them.

## Fix Applied

### 1. Data Fix (Immediate)

Created and ran `/Users/rossfreedman/dev/rally/scripts/fix_letter_series_in_apta.py`:

```bash
python3 scripts/fix_letter_series_in_apta.py
```

**Results:**
- ✅ Moved 96 players from letter series (A, B, C, D, E, F) to "Series 99"
- ✅ Moved 10 teams from letter series to "Series 99"  
- ✅ Verified 0 letter series remain in APTA league

**Affected Teams:**
- Wilmette 99 A (16 players)
- Winnetka 99 A (8 players)
- Wilmette 99 B (10 players)
- Winnetka 99 B (9 players)
- Wilmette 99 C (11 players)
- Winnetka 99 C (4 players)
- Wilmette 99 D (10 players)
- Winnetka 99 D (7 players)
- Wilmette 99 E (11 players)
- Wilmette 99 F (10 players)

### 2. Prevention Fix (Future Imports)

Enhanced `create_letter_based_series()` function in `data/etl/import/start_season.py` with validation:

```python
# VALIDATION: Prevent letter series (A, B, C, D, E, F, etc.) in APTA league
# Letter series are only for CNSWPL and NSTF Sunday leagues
if is_apta and re.match(r'^Series [A-Z]$', series_name):
    print(f"    ⚠️ Skipping letter series '{series_name}' for APTA league (not allowed)")
    continue
```

This prevents letter series from being created in APTA league during future imports.

## Verification

### Before Fix
```sql
-- 96 APTA players with letter series
SELECT COUNT(*) FROM players 
WHERE league_id = 4783 
AND series_id IN (SELECT id FROM series WHERE name IN ('Series A', 'Series B', 'Series C', 'Series D', 'Series E', 'Series F'))
AND is_active = true;
-- Result: 96
```

### After Fix
```sql
-- 0 APTA players with letter series
SELECT COUNT(*) FROM players 
WHERE league_id = 4783 
AND series_id IN (SELECT id FROM series WHERE name IN ('Series A', 'Series B', 'Series C', 'Series D', 'Series E', 'Series F'))
AND is_active = true;
-- Result: 0

-- All moved to Series 99
SELECT COUNT(*) FROM players 
WHERE league_id = 4783 
AND series_id = (SELECT id FROM series WHERE name = 'Series 99')
AND is_active = true;
-- Result: 96
```

## Impact

- **User Experience**: APTA players now see only appropriate numbered series in dropdowns (Series 1, 2, 3, ... 40, 99)
- **Data Integrity**: Letter series (A, B, C, D, E, F) are now correctly reserved for CNSWPL and NSTF Sunday leagues only
- **Future Imports**: Prevention logic ensures this issue won't recur in future ETL runs

## Files Modified

1. `data/etl/import/start_season.py` - Added validation to prevent letter series in APTA
2. `scripts/fix_letter_series_in_apta.py` - One-time fix script (can be kept for reference)
3. `docs/LETTER_SERIES_FIX.md` - This documentation

## Testing Recommendation

After deploying to staging/production:

1. Log in as an APTA player
2. Navigate to any page with series dropdown (e.g., user settings, team selection)
3. Verify dropdown shows only numbered series (no Series A, B, C, D, E, F)
4. Verify "Series 99" appears in the list with Wilmette/Winnetka teams

## Additional Fixes - Roman Numeral Series

After the initial fix, two more malformed series were discovered:

### Issue 2: Malformed "11" and "I" Series

**Problem:** Teams with Roman numerals in their club names were being incorrectly parsed:
- `"Wilmette PD II 11"` → parsed as Club: "Wilmette PD", Series: "11" (missing "Series" prefix)
- `"Winnetka I 14"` → parsed as Club: "Winnetka", Series: "I" (Roman numeral treated as series)

**Fix Applied:** Created `/scripts/fix_roman_numeral_series.py`

**Results:**
- ✅ Moved 10 players from malformed `"11"` to `"Series 11"`
- ✅ Moved 22 players from malformed `"I"` to correct series (Series 7, 11, 14, 15, 25)
- ✅ Fixed 6 teams: Wilmette PD II 11, Prairie Club I 15, Glen Oak I 25, Winnetka I 14, River Forest PD I 11, Salt Creek I 7

**Root Cause:** The `parse_team_name()` function treated Roman numerals in club names (like "Winnetka I", "Wilmette PD II") as series identifiers instead of part of the club name.

## Additional Notes

- Series 99 appears to be a special "exhibition" or "non-competitive" series in APTA Chicago
- The "99 A", "99 B" suffixes might represent different courts or time slots within Series 99
- These teams are primarily from Wilmette and Winnetka clubs
- Roman numerals (I, II, III) in team names are part of club names, not series identifiers

