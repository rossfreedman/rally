# Last Season Stats Implementation

## Overview
Added a new "Last Season Stats" card to the mobile player detail page that displays statistics from the 2024-2025 season. This card appears between the "Current Season Stats" and "Career Stats" sections.

## Implementation Details

### 1. Database Table: `match_scores_previous_seasons`
Created a new table to store historical season data with the following structure:
- Mirrors the `match_scores` table schema
- **New column**: `season` (VARCHAR(20)) - identifies the season (e.g., "2024-2025")
- Includes all standard match score fields: player IDs, scores, winner, teams, dates
- Optimized with indices on: season, league_id, match_date, player IDs, and tenniscores_match_id

**SQL Creation:**
```sql
CREATE TABLE match_scores_previous_seasons (
    id SERIAL PRIMARY KEY,
    league_id INTEGER REFERENCES leagues(id),
    match_date DATE,
    home_team TEXT,
    away_team TEXT,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_player_1_id TEXT,
    home_player_2_id TEXT,
    away_player_1_id TEXT,
    away_player_2_id TEXT,
    scores TEXT,
    winner TEXT CHECK (winner IN ('home', 'away', 'tie')),
    tenniscores_match_id TEXT,
    season VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Data Status:**
- **Season**: 2024-2025
- **Total Matches**: 17,698
- **Date Range**: 2024-09-24 to 2025-02-19
- **Player IDs**: 21,457 unique player associations

### 2. Data Import Script: `scripts/import_previous_season_matches.py`
Created a comprehensive import script that:
- Reads match history from `data/leagues/APTA_CHICAGO/match_history_2024_2025.json`
- Validates and transforms data for database insertion
- Maps team names to team IDs using database lookups
- Handles duplicates gracefully
- Provides detailed import statistics and verification

**Key Features:**
- Date parsing in DD-Mon-YY format
- League and team ID resolution
- Duplicate detection by tenniscores_match_id + season
- Transaction-based import with rollback on errors
- Post-import verification queries

### 3. Backend Function: `get_last_season_stats()` in `app/services/mobile_service.py`
Added a new service function that:
- Queries `match_scores_previous_seasons` table for a specific player and season
- Filters by league context when available
- Calculates win/loss records and win rate
- Handles "tie" results appropriately (excluded from win/loss calculation)
- Returns structured data: matches, wins, losses, winRate

**Function Signature:**
```python
def get_last_season_stats(player_id, league_id_int=None, season="2024-2025"):
    """
    Get last season statistics for a player from match_scores_previous_seasons table.
    
    Returns:
        dict: Last season stats with matches, wins, losses, winRate
    """
```

### 4. Route Update: `app/routes/mobile_routes.py`
Modified the `serve_mobile_player_detail()` route to:
- Call `get_last_season_stats()` with the player's ID and league context
- Add last season stats to the `analyze_data` dictionary as `last_season`
- Pass data to template for rendering

**Code Addition:**
```python
# Get last season stats (2024-2025)
from app.services.mobile_service import get_last_season_stats
last_season_stats = get_last_season_stats(actual_player_id, league_id_int, season="2024-2025")
analyze_data["last_season"] = last_season_stats
```

### 5. Template Update: `templates/mobile/player_detail.html`
Added a new card section that:
- Displays between Current Season Stats and Career Stats
- Shows matches, win rate, wins, and losses
- Uses same styling and layout as Current Season Stats card
- Color-codes win rate (green ≥60%, yellow ≥45%, red <45%)
- Gracefully handles missing data with "No data" placeholders

**Visual Design:**
- Header: Dark teal background (#045454) with lime green icon/text (#bff863)
- Icon: `fas fa-calendar-check` to distinguish from other season cards
- Title: "Last Season Stats (2024-2025)"
- Layout: 2-column grid for matches/win rate, centered W-L record display

## Files Modified

1. **Created:**
   - `/Users/rossfreedman/dev/rally/scripts/import_previous_season_matches.py`
   - `/Users/rossfreedman/dev/rally/docs/LAST_SEASON_STATS_IMPLEMENTATION.md`

2. **Modified:**
   - `/Users/rossfreedman/dev/rally/app/models/database_models.py` - Added `MatchScorePreviousSeason` model
   - `/Users/rossfreedman/dev/rally/app/services/mobile_service.py` - Added `get_last_season_stats()` function
   - `/Users/rossfreedman/dev/rally/app/routes/mobile_routes.py` - Updated player detail route
   - `/Users/rossfreedman/dev/rally/templates/mobile/player_detail.html` - Added Last Season Stats card

## Testing

### Manual Testing Steps:
1. Navigate to: `https://rally-staging.up.railway.app/mobile/player-detail/nndz-WkNPd3liejlnUT09_team_59976`
2. Verify the page displays three stat cards in order:
   - Current Season Stats
   - **Last Season Stats (2024-2025)** ← NEW
   - Career Stats
3. Confirm the Last Season Stats card shows:
   - Match count
   - Win rate percentage with appropriate color
   - Wins and losses breakdown

### Database Verification:
```sql
SELECT COUNT(*) FROM match_scores_previous_seasons WHERE season = '2024-2025';
-- Expected: 17,698 matches
```

## Future Enhancements

1. **Multiple Seasons Support**: 
   - Extend to support multiple previous seasons (2023-2024, 2022-2023, etc.)
   - Add dropdown or tabs to switch between seasons

2. **Dynamic Season Detection**:
   - Auto-detect available seasons from database
   - Only show card if previous season data exists

3. **Comparison Feature**:
   - Add side-by-side comparison between current and last season
   - Show trend indicators (↑/↓) for improvements/declines

4. **Additional Stats**:
   - Court-specific performance for last season
   - Top partners from last season
   - Month-by-month progression

## Deployment Notes

### Local Environment:
- ✅ Database table created
- ✅ Data imported (17,698 matches)
- ✅ Code changes complete
- ✅ No syntax errors
- ✅ Ready for testing

### Staging/Production Deployment:
1. Run SQL to create `match_scores_previous_seasons` table
2. Run `scripts/import_previous_season_matches.py` to import 2024-2025 data
3. Deploy code changes to staging
4. Test player detail pages
5. Deploy to production after validation

### Data Refresh:
When updating last season data:
```bash
# Backup existing data
pg_dump rally -t match_scores_previous_seasons > backup.sql

# Clear and re-import
python scripts/import_previous_season_matches.py
```

## Success Criteria

- [x] Database table created and populated
- [x] Backend function queries data correctly
- [x] Route passes data to template
- [x] Template displays Last Season Stats card
- [x] Card positioned between Current Season and Career Stats
- [x] No syntax errors or linter warnings
- [x] Graceful handling of missing data

## Notes

- The implementation follows the exact same pattern as Current Season Stats for consistency
- Win rate calculation excludes "tie" results
- Data is filtered by league context when available
- The system is modular and can easily be extended to support additional seasons

---

**Implementation Date**: October 11, 2025  
**Developer**: AI Assistant  
**Status**: ✅ Complete and Ready for Testing

