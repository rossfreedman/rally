# Team-Specific Tracking Fix

## Problem Description

The `/mobile/track-byes-courts` page had a critical flaw for players who play for more than one team in the same league. The issue was that the `player_season_tracking` table only had a unique constraint on `(player_id, league_id, season_year)`, which meant:

1. **Data Sharing**: If a player played for multiple teams in the same league during the same season, they could only have one tracking record that was shared across all teams
2. **Incorrect Display**: The UI would show the same forced byes, unavailability, and injury data for a player regardless of which team they were currently viewing
3. **Data Integrity**: Updates to tracking data would affect all teams, not just the specific team being managed

## Root Cause

The `player_season_tracking` table schema was missing a `team_id` field, causing the unique constraint to be insufficient for multi-team players:

```sql
-- BEFORE (problematic)
CREATE TABLE player_season_tracking (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(255) NOT NULL,  -- tenniscores_player_id
    league_id INTEGER REFERENCES leagues(id),
    season_year INTEGER NOT NULL,
    forced_byes INTEGER DEFAULT 0,
    not_available INTEGER DEFAULT 0,
    injury INTEGER DEFAULT 0,
    -- ... other fields
);

-- Unique constraint was insufficient
UNIQUE(player_id, league_id, season_year)
```

## Solution

### 1. Database Schema Update

Added `team_id` column to the `player_season_tracking` table and updated the unique constraint:

```sql
-- AFTER (fixed)
CREATE TABLE player_season_tracking (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(255) NOT NULL,  -- tenniscores_player_id
    team_id INTEGER NOT NULL REFERENCES teams(id),  -- NEW: Team-specific tracking
    league_id INTEGER REFERENCES leagues(id),
    season_year INTEGER NOT NULL,
    forced_byes INTEGER DEFAULT 0,
    not_available INTEGER DEFAULT 0,
    injury INTEGER DEFAULT 0,
    -- ... other fields
);

-- Updated unique constraint includes team_id
UNIQUE(player_id, team_id, league_id, season_year)
```

### 2. Migration Script

Created `scripts/add_team_id_to_player_season_tracking.py` to safely migrate existing data:

- Adds `team_id` column (nullable initially)
- Populates `team_id` for existing records based on player's current team
- Makes `team_id` NOT NULL after population
- Updates unique constraint to include `team_id`
- Adds foreign key constraint to teams table
- Includes comprehensive verification

### 3. API Updates

Updated `/api/player-season-tracking` endpoint to filter by team:

**GET Request**: Now filters tracking data by `team_id` in addition to `league_id` and `season_year`
```sql
SELECT player_id, forced_byes, not_available, injury
FROM player_season_tracking
WHERE player_id IN (player_ids)
AND team_id = %s           -- NEW: Team-specific filtering
AND league_id = %s
AND season_year = %s
```

**POST Request**: Now includes `team_id` in UPSERT operations
```sql
INSERT INTO player_season_tracking (player_id, team_id, league_id, season_year, tracking_type)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (player_id, team_id, league_id, season_year)  -- NEW: Includes team_id
DO UPDATE SET tracking_type = EXCLUDED.tracking_type
```

### 4. Database Model Updates

Updated `PlayerSeasonTracking` model in `app/models/database_models.py`:

```python
class PlayerSeasonTracking(Base):
    __tablename__ = "player_season_tracking"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(String(255), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)  # NEW
    league_id = Column(Integer, ForeignKey("leagues.id"))
    season_year = Column(Integer, nullable=False)
    # ... other fields
    
    # NEW: Relationship to teams table
    team = relationship("Team")
    
    # Updated unique constraint
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "team_id",      # NEW: Include team_id
            "league_id",
            "season_year",
            name="unique_player_season_tracking",
        ),
    )
```

## Benefits

### 1. **Data Separation**
- Players with multiple teams in the same league now have separate tracking data per team
- Each team can manage their own forced byes, unavailability, and injury tracking
- No more data sharing between teams

### 2. **Improved User Experience**
- Track Byes & Courts page now shows team-specific data
- Players can see different tracking values for each team they play on
- Team captains can manage their team's tracking data independently

### 3. **Data Integrity**
- Foreign key constraint ensures `team_id` references valid teams
- Unique constraint prevents duplicate tracking records per player/team/league/season
- Better data validation and consistency

### 4. **Scalability**
- System now properly supports complex multi-team scenarios
- Future enhancements can build on team-specific foundation
- Better performance with team-based filtering

## Implementation Steps

### 1. Run Migration
```bash
cd /path/to/rally
python scripts/add_team_id_to_player_season_tracking.py
```

### 2. Verify Migration
The migration script includes comprehensive verification:
- Checks column existence
- Validates constraints
- Confirms data integrity
- Tests foreign key relationships

### 3. Test Functionality
Run the test script to verify everything works:
```bash
python scripts/test_team_specific_tracking.py
```

### 4. Deploy Changes
- Commit and push database schema changes
- Deploy updated application code
- Monitor for any issues

## Testing

### Test Scenarios

1. **Multi-Team Player**: Create tracking data for a player on Team A and Team B (same league)
2. **Data Separation**: Verify that forced byes, unavailability, and injury data is different per team
3. **API Compatibility**: Test that GET and POST endpoints work with team filtering
4. **UI Display**: Verify that Track Byes & Courts page shows team-specific data

### Test Script

The `scripts/test_team_specific_tracking.py` script automatically:
- Finds players with multiple teams in the same league
- Creates test tracking data with different values per team
- Verifies data separation
- Tests API compatibility
- Provides comprehensive reporting

## Rollback Plan

If issues arise, the migration can be rolled back:

1. **Drop new constraints**:
```sql
ALTER TABLE player_season_tracking DROP CONSTRAINT fk_player_season_tracking_team_id;
ALTER TABLE player_season_tracking DROP CONSTRAINT unique_player_season_tracking;
```

2. **Restore old constraint**:
```sql
ALTER TABLE player_season_tracking ADD CONSTRAINT unique_player_season_tracking UNIQUE (player_id, league_id, season_year);
```

3. **Drop team_id column**:
```sql
ALTER TABLE player_season_tracking DROP COLUMN team_id;
```

## Future Enhancements

With team-specific tracking in place, future improvements could include:

1. **Team Analytics**: Track team-specific performance metrics
2. **Captain Tools**: Enhanced team management features
3. **League Comparisons**: Compare tracking data across teams
4. **Historical Analysis**: Track changes in team tracking over time

## Conclusion

This fix resolves the critical issue where players with multiple teams in the same league were seeing incorrect, shared tracking data. The solution provides:

- **Immediate fix** for the data sharing problem
- **Long-term foundation** for team-specific features
- **Data integrity** through proper constraints and relationships
- **Backward compatibility** through safe migration
- **Comprehensive testing** to ensure reliability

Players can now properly track their availability and status per team, providing accurate data for team captains and improving the overall user experience on the Track Byes & Courts page.
