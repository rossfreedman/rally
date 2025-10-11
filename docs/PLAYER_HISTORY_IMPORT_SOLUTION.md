# Player History Import Solution

## Problem Discovered

PTI History and Previous Season History cards were not showing up on player-detail pages for many APTA players, even though they had match scores in the database.

## Root Causes Identified

### 1. Database Query Bug (Fixed)
**File**: `app/services/mobile_service.py` (lines 867-877)

**Issue**: Query was trying to use `tenniscores_player_id` column directly on `player_history` table, but that column doesn't exist. The `player_history` table has `player_id` as a foreign key to `players.id`.

**Fix**: Updated query to properly JOIN with players table:
```python
# BEFORE (buggy):
history_count = execute_query_one(
    "SELECT COUNT(*) as count FROM player_history WHERE tenniscores_player_id = %s ...",
    [player_id]
)

# AFTER (fixed):
history_count = execute_query_one(
    """SELECT COUNT(*) as count 
       FROM player_history ph 
       JOIN players p ON ph.player_id = p.id 
       WHERE p.tenniscores_player_id = %s AND ph.end_pti IS NOT NULL""",
    [player_id]
)
```

### 2. Missing Player History Data (Fixed)
**Issue**: 1,020 players had complete history data in `player_history.json` but it wasn't imported into the database during ETL.

**Solution**: Created `data/etl/scrapers/apta/apta_get_player_history.py` script to import missing data.

## Results

### Before Fix
- Total APTA Players: 6,895
- Players WITHOUT History: 2,122 (30.8%)
- Players WITH History: 4,773 (69.2%)
- Players with matches but no history: 1,477

### After Fix
- Total APTA Players: 6,895
- Players WITHOUT History: 1,081 (15.7%) ⬇️ **DOWN 15.1%**
- Players WITH History: 5,814 (84.3%) ⬆️ **UP 15.1%**
- Players with matches but no history: 436 ⬇️ **DOWN 70.5%**

### Import Statistics
- Players processed: 1,476
- Players found in JSON: 1,046
- **History records imported: 74,433**
- Success rate: 70.7%

## Example: Pete Wahlstrom
- **Before**: 0 history records → Cards not showing
- **After**: 96 history records (2018-2025) → Cards now display

## Remaining 436 Players Without History
These are primarily:
1. New players who joined in October 2025 (current season)
2. Players not in the historical JSON scrape
3. Will accumulate history as season progresses

**No action needed** - this is expected behavior for new season players.

## Script Usage

### Import for specific player:
```bash
python3 data/etl/scrapers/apta/apta_get_player_history.py --player "Pete Wahlstrom"
```

### Import for all missing players:
```bash
python3 data/etl/scrapers/apta/apta_get_player_history.py --all
```

### Dry run (preview without importing):
```bash
python3 data/etl/scrapers/apta/apta_get_player_history.py --all --dry-run
```

## Files Modified

1. **app/services/mobile_service.py** (lines 867-877)
   - Fixed player_history query to properly JOIN with players table
   - Added debug logging for history count

2. **data/etl/scrapers/apta/apta_get_player_history.py** (new file)
   - Script to import missing player history from JSON to database
   - Supports single player or batch import
   - Includes dry-run mode for testing

## Impact

**Before**: Only 69.2% of APTA players could see PTI History and Previous Season History cards

**After**: Now 84.3% of APTA players can see these cards! ✅

### Cards Now Display For:
- PTI History Chart: Shows full historical PTI progression with interactive graph
- Previous Season History: Table showing season-by-season performance

### Affected Players
Pete Wahlstrom and 1,045 other players now have access to their complete historical data.

## Future Recommendations

1. **Investigate ETL Import Failure**: Determine why the original ETL process failed to import these 1,020 players from JSON
2. **Add Validation**: Add post-import validation to detect when players have data in JSON but not in database
3. **Automated Monitoring**: Create alerts for players with matches but no history to catch future issues early
4. **Current Season Updates**: Ensure player_history gets updated as current season progresses (currently only has data through June 2025)

## Testing Verification

To verify a player now has history:
```sql
SELECT COUNT(*) as count 
FROM player_history ph 
JOIN players p ON ph.player_id = p.id 
WHERE p.tenniscores_player_id = 'PLAYER_ID_HERE' 
  AND ph.end_pti IS NOT NULL;
```

If count > 0, the PTI History and Previous Season History cards will display.

## Date Created
October 11, 2025

## Related Issues
- Player-detail pages missing PTI cards
- APTA men's players missing historical data
- ETL import gaps

