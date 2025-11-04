# Post-ETL Club Cleanup Script

## Purpose
This script automatically consolidates duplicate clubs that may be recreated during ETL imports. It ensures data integrity by preventing duplicate club variations from persisting after imports.

## Problem
ETL imports may recreate duplicate clubs (e.g., "Lifesport Lshire") if the source data contains these variations. This script automatically consolidates them into the correct club (e.g., "Lifesportlshire") to maintain data integrity.

## Usage

### Dry Run (Default)
```bash
python3 data/etl/import/post_etl_club_cleanup.py
```

### Apply Changes Locally
```bash
python3 data/etl/import/post_etl_club_cleanup.py --live
```

### Apply Changes to Staging
```bash
python3 data/etl/import/post_etl_club_cleanup.py --live --staging
```

### Apply Changes to Production
```bash
python3 data/etl/import/post_etl_club_cleanup.py --live --production
```

### Detect Potential Duplicates
```bash
python3 data/etl/import/post_etl_club_cleanup.py --detect
```

## What It Does

1. **Checks for duplicate clubs** defined in `CLUB_CONSOLIDATION_MAPPINGS`
2. **Moves all data** from duplicate club to target club:
   - Players (active and inactive)
   - Teams
   - User contexts
   - Club-league associations (merges intelligently)
3. **Deletes the duplicate club** after all references are moved
4. **Verifies consolidation** to ensure no orphaned records

## Current Consolidation Mappings

- `"Lifesport Lshire"` → `"Lifesportlshire"`

To add more mappings, edit `CLUB_CONSOLIDATION_MAPPINGS` in the script.

## Integration with ETL Workflow

### Option 1: Manual Run After ETL
Run the script manually after each ETL import:
```bash
# After ETL import completes
python3 data/etl/import/post_etl_club_cleanup.py --live
```

### Option 2: Automated Integration
Add to your ETL import script:
```python
# At the end of import_all_jsons_to_database.py or similar
from data.etl.import.post_etl_club_cleanup import post_etl_club_cleanup

# Run cleanup after import
post_etl_club_cleanup(dry_run=False)
```

### Option 3: Scheduled Task
Set up a cron job or scheduled task to run after ETL imports.

## Safety Features

- **Dry run by default** - Shows what would be changed without making updates
- **Verification** - Checks that all data was moved before deleting source club
- **Transaction safety** - Uses database transactions (via execute_update)
- **Idempotent** - Safe to run multiple times (won't break if duplicates don't exist)

## Example Output

```
================================================================================
POST-ETL CLUB CLEANUP
================================================================================
Mode: LIVE UPDATE

Processing: 'Lifesport Lshire' -> 'Lifesportlshire'
--------------------------------------------------------------------------------
   ⚠️  Found duplicate club: 'Lifesport Lshire' (ID: 8711)
   ✅ Target club found: 'Lifesportlshire' (ID: 14202)

   Analyzing data to be consolidated...
      Active players: 15
      Teams: 2
      User contexts: 0
      Club-league associations: 1

   Applying consolidation...
      ✅ Updated 15 players
      ✅ Updated 2 teams
      ✅ Handled 1 club-league associations
      ✅ Deleted duplicate club (ID: 8711)

   ✅ Verification: Consolidation successful for 'Lifesport Lshire'

================================================================================
CLEANUP COMPLETE
  Consolidations applied: 1
  Total records updated: 18
================================================================================
```

## Adding New Consolidation Mappings

To add a new club consolidation mapping:

1. Edit `data/etl/import/post_etl_club_cleanup.py`
2. Add to `CLUB_CONSOLIDATION_MAPPINGS`:
```python
CLUB_CONSOLIDATION_MAPPINGS = {
    "Lifesport Lshire": "Lifesportlshire",
    "Winnetka I": "Winnetka",  # New mapping
    "Winnetka II": "Winnetka",  # New mapping
}
```

3. Run dry run to test:
```bash
python3 data/etl/import/post_etl_club_cleanup.py
```

4. Apply when ready:
```bash
python3 data/etl/import/post_etl_club_cleanup.py --live
```

## Notes

- The script uses exact club name matching (case-sensitive)
- Only processes clubs defined in `CLUB_CONSOLIDATION_MAPPINGS`
- Does not modify club names - only moves data and deletes duplicates
- Safe to run even if no duplicates exist

