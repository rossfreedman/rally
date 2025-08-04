# Current Season Stats Fix

## Issue Description

Players on staging were showing incorrect current season stats and court performance. The problem was that the system was calculating stats from **ALL matches** instead of filtering by the **current season**.

### Affected Players
- Brian Wagner
- Jeff Condren  
- Daniel McNair
- All players on staging (systematic issue)

### Symptoms
- Current season stats showed matches from previous seasons
- Court performance included matches from outside current season
- Win rates and records were inflated with historical data

## Root Cause

The `get_player_analysis()` function in `app/services/mobile_service.py` was not filtering matches by the current season. It was querying ALL matches for a player instead of only current season matches.

### Season Definition
- **Current Season**: August 1st - July 31st
- **Example**: 2025-2026 season = August 1, 2025 to July 31, 2026
- **Current Date**: August 2025 (we're in 2025-2026 season)

### Problem Code
```python
# OLD: No season filtering
history_query = """
    SELECT ... FROM match_scores
    WHERE (home_player_1_id = %s OR ...)
    AND league_id = %s
    ORDER BY match_date DESC
"""
```

## Solution

### 1. Added Current Season Filtering

**Modified Files**:
- `app/services/mobile_service.py`: Added season filtering to match queries
- `app/services/mobile_service.py`: Added season filtering to court analysis queries

### 2. Season Boundary Calculation

```python
# Calculate current season boundaries
current_date = datetime.now()
current_month = current_date.month
current_year = current_date.year

if current_month >= 8:  # Aug-Dec: current season
    season_start_year = current_year
else:  # Jan-Jul: previous season
    season_start_year = current_year - 1
    
season_start = datetime(season_start_year, 8, 1)  # August 1st
season_end = datetime(season_start_year + 1, 7, 31)  # July 31st
```

### 3. Updated Queries

**Player Analysis Query**:
```python
# NEW: Added season filtering
history_query = """
    SELECT ... FROM match_scores
    WHERE (home_player_1_id = %s OR ...)
    AND league_id = %s
    AND match_date >= %s AND match_date <= %s  # SEASON FILTER
    ORDER BY match_date DESC
"""
```

**Court Analysis Query**:
```python
# NEW: Added season filtering
all_matches_on_dates = execute_query(
    """
    SELECT ... FROM match_scores ms
    WHERE ms.match_date = ANY(%s)
    AND ms.league_id = %s
    AND ms.match_date >= %s AND ms.match_date <= %s  # SEASON FILTER
    ORDER BY ms.match_date ASC, ms.id ASC
    """,
    (player_dates, league_id_int, season_start, season_end),
)
```

## Testing Results

### Before Fix
```
Brian Wagner: 3 matches (100.0% win rate) - INCORRECT
Jeff Condren: 14 matches (71.4% win rate) - INCORRECT  
Daniel McNair: 19 matches (42.1% win rate) - INCORRECT
```

### After Fix
```
Brian Wagner: 0 matches (0% win rate) - CORRECT
Jeff Condren: 0 matches (0% win rate) - CORRECT
Daniel McNair: 0 matches (0% win rate) - CORRECT
```

**Explanation**: All matches were from 2024-2025 season, but we're currently in 2025-2026 season, so 0 current season matches is correct.

## Impact

### ✅ Fixed Issues
1. **Current Season Stats**: Now shows only current season matches
2. **Court Performance**: Now shows only current season court assignments
3. **Win Rates**: Now calculated from current season only
4. **Match Counts**: Now accurate for current season

### 🔄 Backward Compatibility
- Career stats remain unchanged (still show all-time stats)
- Player history remains unchanged (still show all matches)
- Only current season calculations are affected

## Verification

The fix was verified by:
1. **Investigation Script**: Confirmed the issue existed
2. **Test Script**: Verified the fix works correctly
3. **Database Queries**: Confirmed season filtering is applied
4. **Multiple Players**: Tested with all affected players

## Future Considerations

1. **Season Transitions**: The fix handles season transitions correctly
2. **Data Consistency**: All current season calculations now use the same logic
3. **Performance**: Season filtering reduces query result sizes
4. **Maintainability**: Clear season boundary logic is documented

## Deployment Notes

- **No Database Changes**: Only query logic changes
- **No Template Changes**: Frontend displays same data structure
- **Backward Compatible**: Existing functionality preserved
- **Immediate Effect**: Fix takes effect immediately upon deployment 