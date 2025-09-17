# Career Stats Consistency Guide

## Overview

This document explains how career stats consistency is maintained across all team assignments for the same player in the Rally platform.

## Problem

When a player is on multiple teams (different clubs/series), the original import logic would create separate database records for each team assignment. However, the upsert logic only updated the specific team assignment being processed, leading to inconsistent career stats across different team assignments for the same player.

### Example Issue
- Player "Stefanos Bezanis" on 4 different teams
- Team 1: 19W-6L (76.00%) ✅
- Team 2: 0W-0L (0.00%) ❌ 
- Team 3: 19W-6L (76.00%) ✅
- Team 4: 19W-6L (76.00%) ✅

## Solution

### 1. Real-time Consistency Check

Added `ensure_career_stats_consistency()` function that runs after each successful player upsert:

```python
def ensure_career_stats_consistency(cur, tenniscores_player_id, league_id, career_wins, career_losses, career_matches, career_win_percentage):
    """
    Ensure career stats are consistent across all team assignments for the same player.
    """
    cur.execute("""
        UPDATE players 
        SET career_wins = %s, 
            career_losses = %s, 
            career_matches = %s,
            career_win_percentage = %s
        WHERE tenniscores_player_id = %s 
        AND league_id = %s
        AND (career_wins != %s OR career_losses != %s OR career_win_percentage != %s)
    """, (career_wins, career_losses, career_matches, career_win_percentage, 
          tenniscores_player_id, league_id, career_wins, career_losses, career_win_percentage))
```

### 2. Post-Import Consistency Check

Added automatic consistency check and fix in the integrity checks:

```python
def fix_career_stats_inconsistencies(cur, league_id):
    """
    Fix inconsistent career stats across all team assignments for the same player.
    Uses the most recent/complete career stats as the source of truth.
    """
```

### 3. Integrity Check Integration

The `run_integrity_checks()` function now includes:

```python
# Check for inconsistent career stats across team assignments
cur.execute("""
    SELECT COUNT(DISTINCT tenniscores_player_id)
    FROM players 
    WHERE league_id = %s 
    AND tenniscores_player_id IS NOT NULL
    AND tenniscores_player_id != ''
    AND tenniscores_player_id IN (
        SELECT tenniscores_player_id
        FROM players 
        WHERE league_id = %s 
        AND tenniscores_player_id IS NOT NULL
        AND tenniscores_player_id != ''
        GROUP BY tenniscores_player_id
        HAVING COUNT(DISTINCT CONCAT(COALESCE(career_wins, 0), '-', COALESCE(career_losses, 0), '-', COALESCE(career_win_percentage, 0))) > 1
    )
""", (league_id, league_id))
```

## How It Works

### During Import

1. **Player Upsert**: Each player is upserted with their career stats
2. **Consistency Check**: After successful upsert, `ensure_career_stats_consistency()` runs
3. **Cross-Team Update**: All other team assignments for the same player are updated with consistent stats

### After Import

1. **Integrity Check**: `run_integrity_checks()` scans for any remaining inconsistencies
2. **Automatic Fix**: If inconsistencies are found, `fix_career_stats_inconsistencies()` fixes them
3. **Verification**: Final check confirms all career stats are consistent

## Benefits

- **No Manual Intervention**: Inconsistencies are fixed automatically during import
- **Data Integrity**: All team assignments for the same player have identical career stats
- **Future-Proof**: Prevents the issue from occurring in future imports
- **Comprehensive**: Covers both real-time fixes and post-import cleanup

## Testing

The system has been tested with:
- ✅ Small sample imports (5 players)
- ✅ Full imports (7,537 players)
- ✅ Multi-team players (68 players with 142 team assignments)
- ✅ Integrity checks pass with 0 issues

## Files Modified

- `data/etl/import/import_players.py`
  - Added `ensure_career_stats_consistency()` function
  - Added `fix_career_stats_inconsistencies()` function
  - Updated `run_integrity_checks()` to include consistency check
  - Modified upsert logic to call consistency check

## Usage

No changes needed in usage - the import script works exactly the same:

```bash
python3 data/etl/import/import_players.py APTA_CHICAGO
```

The consistency checks and fixes happen automatically during the import process.
