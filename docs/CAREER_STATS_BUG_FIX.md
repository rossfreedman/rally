# Career Stats Bug Fix

## Issue Summary
Career stats (career_wins, career_losses, career_matches, career_win_percentage) were being incorrectly overwritten with current season stats during ETL player imports.

## Root Cause
The player import scripts had fallback logic that was causing career stats to be set to current season stats:

```python
# BEFORE (BUGGY CODE):
career_wins_raw = player_data.get("Career Wins", player_data.get("Wins", "0"))
career_losses_raw = player_data.get("Career Losses", player_data.get("Losses", "0"))
```

Since the scraped JSON files only contain:
- `"Wins"` (current season wins)
- `"Losses"` (current season losses)
- `"Win %"` (current season win percentage)

And do NOT contain "Career Wins", "Career Losses", or "Career Win %" fields, the fallback logic was using current season stats as career stats.

## Example Impact
For Jeff Day (player ID: `nndz-WkMrK3didnhnUT09`):
- **Before fix**: Career stats showed 1 win, 1 loss, 2 matches (50%) - same as current season
- **Issue**: The career stats were being overwritten every ETL import with current season stats
- **Expected**: Career stats should accumulate across all seasons and not be overwritten

## Fix Applied

### 1. Changed fallback logic to NOT use current season stats
**Files modified:**
- `data/etl/import/import_players.py`
- `data/etl/import/start_season.py`

**Change:**
```python
# AFTER (FIXED CODE):
# Extract career stats data - ONLY use explicit Career fields, DO NOT fall back to current season
# Career stats should be calculated from match history, not copied from current season stats
career_wins_raw = player_data.get("Career Wins", None)
career_losses_raw = player_data.get("Career Losses", None)
career_win_pct_raw = player_data.get("Career Win %", None)
```

### 2. Added COALESCE to preserve existing career stats
**Change in upsert queries:**
```sql
-- BEFORE:
career_wins = EXCLUDED.career_wins,
career_losses = EXCLUDED.career_losses,
career_matches = EXCLUDED.career_matches,
career_win_percentage = EXCLUDED.career_win_percentage

-- AFTER:
career_wins = COALESCE(EXCLUDED.career_wins, players.career_wins),
career_losses = COALESCE(EXCLUDED.career_losses, players.career_losses),
career_matches = COALESCE(EXCLUDED.career_matches, players.career_matches),
career_win_percentage = COALESCE(EXCLUDED.career_win_percentage, players.career_win_percentage)
```

This ensures that if career stats are NULL/None in the import data, the existing database values are preserved.

## How Career Stats Should Work

### Correct Flow:
1. **Scraper** collects current season stats (wins, losses, win %)
2. **Player import** updates current season stats but PRESERVES existing career stats
3. **Career stats calculation** (separate process) should calculate total career stats from match history
4. Career stats accumulate across seasons and are never overwritten by current season data

## Testing
To verify the fix works:

1. Check that player imports no longer overwrite career stats with current season stats
2. Verify that existing career stats are preserved during imports
3. Ensure career stats can still be updated when explicitly provided in the data

## Related Files
- `data/etl/import/import_players.py` - Main player import logic
- `data/etl/import/start_season.py` - Season start player import
- `app/services/mobile_service.py` - Player analysis display logic (lines 906-922)

## Note on Career Stats Display
The mobile service currently ADDS current season stats to career stats for display:

```python
# In get_player_analysis() function (lines 909-922)
if career_stats and current_season:
    career_stats["wins"] = career_stats.get("wins", 0) + current_season.get("wins", 0)
    career_stats["losses"] = career_stats.get("losses", 0) + current_season.get("losses", 0)
    career_stats["matches"] = career_stats.get("matches", 0) + current_season.get("matches", 0)
```

This means:
- **Database career stats** should store HISTORICAL stats (previous seasons only)
- **Displayed career stats** = database career stats + current season stats

## Recommendations
1. Create a separate process to calculate career stats from match_scores table
2. Run this process at the end of each season to update career stats
3. Career stats should accumulate across all historical match data
4. Do NOT rely on scraped data for career stats - calculate from match history

