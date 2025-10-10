# Orphaned Teams Investigation & Resolution

## Issue Summary

**Problem**: Tennaqua 3 appears in APTA Chicago database at `http://127.0.0.1:8080/mobile/teams-players?team_id=59950` but has no players or matches.

**Root Cause**: Bootstrap process created 110 orphaned teams (11.7% of all teams) across the database that have zero players and zero matches.

## Investigation Results

### Specific Case: Tennaqua 3

Two "Tennaqua 3" teams exist in the database:

| Team ID | League | Series | Players | Matches | Status | Created |
|---------|--------|--------|---------|---------|--------|---------|
| 59183 | CNSWPL | Series 3 | 10 | 0 | ✅ VALID | 2025-09-05 |
| 59950 | APTA_CHICAGO | Series 3 | 0 | 0 | 🚨 ORPHANED | 2025-09-21 |

**Analysis**:
- Team ID 59950 is orphaned - created in wrong league
- Tennaqua only has teams in APTA Chicago: 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 34, 36, 38, 40
- No "Tennaqua 3" exists in APTA Chicago source data (match_scores.json)
- The orphaned team was created by bootstrap process on Sept 21, 2025

### Database-Wide Impact

**Total Orphaned Teams**: 110 out of 941 teams (11.7%)

**By League**:
- APTA Chicago: 98 orphaned teams
- CNSWPL: 12 orphaned teams

**Examples of Orphaned Teams**:
- Skokie 13, Evanston 12, Evanston 13, Lake Bluff 13
- Michigan Shores 10, Michigan Shores 14
- Park Ridge 14, Wilmette 14, Winter Club 12
- Many more (see diagnostic report for full list)

## Root Causes

### 1. Bootstrap Process Over-Creation

The bootstrap scripts (`bootstrap_teams_from_players.py`, `comprehensive_series_team_bootstrap.py`) create teams for every club+series combination found in source data, **without validating**:
- Whether that team actually has players
- Whether that team actually has matches
- Whether that team belongs to the correct league

Example flow:
```python
# bootstrap_teams_from_players.py (line 153-191)
for rec in players:
    series_name = rec.get("Series")
    team_name = rec.get("Series Mapping ID")
    club_name = rec.get("Club")
    
    # Creates team WITHOUT checking if it has players or matches
    ensure_team(team_name, club_id, series_id, league_db_id)
```

### 2. Team Import Without Validation

The match score import (`import_match_scores.py`) uses `upsert_team_unified()` which creates teams on-the-fly:

```python
# import_match_scores.py (line 185-238)
def upsert_team_unified(cur, league_id: int, team_name: str):
    # Automatically creates team if it doesn't exist
    # No validation that team actually has players or matches
    cur.execute("""
        INSERT INTO teams (team_name, display_name, club_id, series_id, league_id)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """)
```

### 3. Historical Data Pollution

- Old teams from previous seasons get recreated without checking if currently active
- Series/club combinations that existed historically but not in current season
- No active season flag to differentiate current vs historical teams

## Impact

**User-Facing Issues**:
1. ❌ Empty team pages (0 players, 0 matches)
2. ❌ Confusing navigation - users land on pages with no data
3. ❌ Incorrect league assignments (e.g., Tennaqua 3 in APTA Chicago)
4. ❌ Database bloat - 11.7% of teams are unused

**Database Issues**:
1. Unnecessary foreign key references
2. Wasted storage
3. Slower queries (more rows to scan)
4. Confusion during debugging

## Solution

### Immediate Cleanup

**Script Created**: `scripts/diagnose_orphaned_teams.py`

**Usage**:
```bash
# Analyze orphaned teams
python3 scripts/diagnose_orphaned_teams.py --analyze

# Dry run cleanup (preview only)
python3 scripts/diagnose_orphaned_teams.py --cleanup

# Actually delete orphaned teams
python3 scripts/diagnose_orphaned_teams.py --cleanup --live
```

**What it does**:
- Identifies teams with 0 players AND 0 matches
- Groups by league for clear reporting
- Provides detailed analysis of specific cases
- Safely deletes orphaned teams (with dry-run option)

### Long-Term Prevention

#### Recommendation 1: Add Validation to Bootstrap

**File**: `data/etl/database_import/bootstrap_teams_from_players.py`

```python
def ensure_team(team_name: str, club_id: int, series_id: int, league_db_id: int) -> None:
    # NEW: Only create team if it has associated players
    player_count = execute_query_one(
        "SELECT COUNT(*) as count FROM players WHERE team_name = %s AND league_id = %s",
        (team_name, league_db_id)
    )
    
    if player_count and player_count['count'] > 0:
        # Team has players, proceed with creation
        existing_by_combo = execute_query_one(...)
        # ... rest of existing logic
    else:
        # Skip team creation if no players
        return
```

#### Recommendation 2: Add Cleanup Step to ETL

**File**: `data/etl/import/import_all_jsons_to_database.py`

Add new step after import:

```python
def cleanup_orphaned_teams(conn):
    """Remove teams with no players and no matches after import"""
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM teams t
            WHERE (SELECT COUNT(*) FROM players p WHERE p.team_id = t.id) = 0
              AND (SELECT COUNT(*) FROM match_scores ms 
                   WHERE ms.home_team_id = t.id OR ms.away_team_id = t.id) = 0
        """)
        deleted_count = cur.rowcount
        logger.info(f"🧹 Cleaned up {deleted_count} orphaned teams")
    return deleted_count

# Call after all imports complete
cleanup_orphaned_teams(conn)
```

#### Recommendation 3: Enhance Team Import Validation

**File**: `data/etl/import/import_match_scores.py`

```python
def upsert_team_unified(cur, league_id: int, team_name: str) -> Optional[int]:
    """Upsert team using unified team management logic."""
    if not team_name:
        return None
    
    # NEW: Check if team already exists first
    cur.execute("""
        SELECT id FROM teams 
        WHERE team_name = %s AND league_id = %s
    """, (team_name, league_id))
    
    existing = cur.fetchone()
    if existing:
        return existing[0]
    
    # NEW: Only create if we're importing matches (meaning it's active)
    # This prevents creating teams that will remain empty
    
    # Parse team name
    raw_club_name, series_name, _ = parse_team_name(team_name)
    # ... rest of existing logic
```

#### Recommendation 4: Add Active Season Flag

**Migration**: Add `active_season` and `season_year` columns to teams table

```sql
ALTER TABLE teams 
ADD COLUMN active_season BOOLEAN DEFAULT TRUE,
ADD COLUMN season_year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE);

CREATE INDEX idx_teams_active_season ON teams(active_season, season_year);
```

Then update queries to filter:
```python
WHERE active_season = TRUE
```

## Testing

After implementing fixes, verify:

1. ✅ No orphaned teams exist: `python3 scripts/diagnose_orphaned_teams.py --analyze`
2. ✅ Tennaqua 3 only exists in CNSWPL (ID 59183)
3. ✅ APTA Chicago has only valid Tennaqua teams (6, 8, 10, 12, etc.)
4. ✅ Team pages show proper data
5. ✅ ETL doesn't recreate orphaned teams

## Files Modified/Created

**Created**:
- `scripts/diagnose_orphaned_teams.py` - Diagnostic and cleanup tool
- `docs/ORPHANED_TEAMS_INVESTIGATION.md` - This document

**To Modify** (recommendations):
- `data/etl/database_import/bootstrap_teams_from_players.py`
- `data/etl/import/import_match_scores.py`
- `data/etl/import/import_all_jsons_to_database.py`

## Execution Plan

1. ✅ Run diagnostic: `python3 scripts/diagnose_orphaned_teams.py --analyze`
2. ⏳ Review orphaned teams list
3. ⏳ Run cleanup: `python3 scripts/diagnose_orphaned_teams.py --cleanup --live`
4. ⏳ Verify Tennaqua 3 issue resolved
5. ⏳ Implement prevention recommendations
6. ⏳ Test with next ETL run

## Related Issues

- Issue: Tennaqua 3 appearing in APTA Chicago database
- Root Cause: Bootstrap over-creation + lack of validation
- Impact: 110 orphaned teams (11.7% of database)
- Resolution: Cleanup script + prevention system

## Notes

- This is a systemic issue affecting 11.7% of all teams
- Cleanup is safe - only deletes teams with 0 players AND 0 matches
- Prevention system will stop future occurrences
- Consider adding this cleanup to regular ETL process


