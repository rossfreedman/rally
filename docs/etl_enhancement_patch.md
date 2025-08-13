# ETL Enhancement Patch - Prevent Orphaned IDs
# Apply these changes to data/etl/database_import/import_all_jsons_to_database.py

## Problem
The current ETL import process creates orphaned foreign key references when team/league lookups fail. Instead of failing gracefully, it inserts NULL values that break data integrity.

## Root Cause
```python
# PROBLEMATIC CODE in import_series_stats() around line 2330:
team_row = cursor.fetchone()
team_db_id = team_row[0] if team_row else None  # ← Creates orphaned data!

cursor.execute("""
    INSERT INTO series_stats (..., team_id, ...)
    VALUES (..., %s, ...)  # ← Inserts None/NULL values
""", (..., team_db_id, ...))
```

## Solution 1: Enhanced import_series_stats method (around line 2330)

Replace this problematic code:
```python
team_row = cursor.fetchone()
team_db_id = team_row[0] if team_row else None
```

With this safe validation:
```python
team_row = cursor.fetchone()
if not team_row:
    self.log(f"⚠️  Skipping series stats for {team}: team not found in database", "WARNING")
    continue
team_db_id = team_row[0]

# Additional validation using helper functions
if not cursor.execute("SELECT validate_team_id(%s)", (team_db_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping series stats for {team}: invalid team_id {team_db_id}", "WARNING")
    continue
```

## Solution 2: Enhanced import_match_history method (around line 2150)

Add validation before INSERT:
```python
# Validate team IDs exist before inserting
if home_team_id and not cursor.execute("SELECT validate_team_id(%s)", (home_team_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping match: invalid home_team_id {home_team_id}", "WARNING")
    continue

if away_team_id and not cursor.execute("SELECT validate_team_id(%s)", (away_team_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping match: invalid away_team_id {away_team_id}", "WARNING") 
    continue

if league_db_id and not cursor.execute("SELECT validate_league_id(%s)", (league_db_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping match: invalid league_id {league_db_id}", "WARNING")
    continue
```

## Solution 3: Enhanced import_schedules method (around line 2850)

Add similar validation:
```python
# Validate team and league IDs before inserting
if home_team_id and not cursor.execute("SELECT validate_team_id(%s)", (home_team_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping schedule: invalid home_team_id {home_team_id}", "WARNING")
    continue

if away_team_id and not cursor.execute("SELECT validate_team_id(%s)", (away_team_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping schedule: invalid away_team_id {away_team_id}", "WARNING")
    continue

if league_db_id and not cursor.execute("SELECT validate_league_id(%s)", (league_db_id,)).fetchone()[0]:
    self.log(f"⚠️  Skipping schedule: invalid league_id {league_db_id}", "WARNING")
    continue
```

## Solution 4: Add post-import validation

Add this method to ComprehensiveETL class:
```python
def post_import_validation(self, conn):
    """Validate no orphaned IDs were created during import"""
    self.log("🔍 Running post-import orphaned ID validation...")
    
    cursor = conn.cursor()
    
    # Check for orphaned league_ids
    validation_queries = [
        ("match_scores.league_id", """
            SELECT COUNT(*) FROM match_scores ms 
            LEFT JOIN leagues l ON ms.league_id = l.id
            WHERE ms.league_id IS NOT NULL AND l.id IS NULL
        """),
        ("match_scores.home_team_id", """
            SELECT COUNT(*) FROM match_scores ms
            LEFT JOIN teams t ON ms.home_team_id = t.id
            WHERE ms.home_team_id IS NOT NULL AND t.id IS NULL
        """),
        ("match_scores.away_team_id", """
            SELECT COUNT(*) FROM match_scores ms
            LEFT JOIN teams t ON ms.away_team_id = t.id
            WHERE ms.away_team_id IS NOT NULL AND t.id IS NULL
        """),
        ("series_stats.league_id", """
            SELECT COUNT(*) FROM series_stats ss
            LEFT JOIN leagues l ON ss.league_id = l.id
            WHERE ss.league_id IS NOT NULL AND l.id IS NULL
        """),
        ("series_stats.team_id", """
            SELECT COUNT(*) FROM series_stats ss
            LEFT JOIN teams t ON ss.team_id = t.id
            WHERE ss.team_id IS NOT NULL AND t.id IS NULL
        """)
    ]
    
    orphaned_issues = []
    for check_name, query in validation_queries:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        if count > 0:
            orphaned_issues.append((check_name, count))
    
    if orphaned_issues:
        self.log("❌ CRITICAL: Orphaned IDs detected after import!", "ERROR")
        for issue_name, count in orphaned_issues:
            self.log(f"   {issue_name}: {count} orphaned records", "ERROR")
        raise Exception("Import failed validation - orphaned IDs detected")
    else:
        self.log("✅ Post-import validation passed - no orphaned IDs")
```

## Solution 5: Call validation in run() method

Add this line before the final commit in run():
```python
# Validate no orphaned IDs were created
self.post_import_validation(conn)
```

## Prevention System Status

✅ **Foreign Key Constraints Added:**
- `fk_match_scores_home_team_id` - Prevents invalid home team references
- `fk_match_scores_away_team_id` - Prevents invalid away team references  
- `fk_series_stats_team_id` - Prevents invalid team references in series stats
- `fk_schedule_home_team_id` - Prevents invalid home team references in schedule
- `fk_schedule_away_team_id` - Prevents invalid away team references in schedule

✅ **Validation Functions Created:**
- `validate_league_id(id)` - Check if league exists
- `validate_team_id(id)` - Check if team exists
- `get_team_id_by_name_and_league(name, league_id)` - Safe team lookup

## Testing the Prevention System

Run this command to test the health monitoring:
```bash
python scripts/prevent_orphaned_ids.py --health-check
```

## Emergency Repair

If orphaned IDs are detected, run:
```bash
python scripts/prevent_orphaned_ids.py --fix-orphaned
```

This patch ensures that:
1. **No orphaned IDs can be inserted** (foreign key constraints)
2. **ETL process fails gracefully** instead of creating orphaned data
3. **Automatic validation** catches any issues immediately
4. **Emergency repair tools** can fix problems quickly

Apply these changes to prevent future orphaned ID issues permanently. 