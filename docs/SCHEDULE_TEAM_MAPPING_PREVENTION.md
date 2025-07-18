# Schedule Team Mapping Prevention System

## Problem Description

The mobile availability page was showing only practices but not matches because schedule entries had NULL `team_id` values. This occurred when the ETL import process couldn't match team names from the schedule data to team names in the teams table.

### Root Cause
- **Schedule data format**: Team names included " - Series X" suffix (e.g., "Tennaqua S2B - Series 2B")
- **Teams table format**: Team names without suffix (e.g., "Tennaqua S2B")
- **Exact matching failure**: The ETL process used exact string matching, which failed when suffixes didn't match

### Impact
- Mobile availability page showed only practices (which don't require team_id)
- Matches were invisible because they had NULL team_id values
- Users couldn't see upcoming matches in their schedule

## Solution Implemented

### 1. ETL Import Fix (Primary Prevention)
**File**: `data/etl/database_import/import_all_jsons_to_database.py`

The `import_schedules()` function now includes team name normalization:

```python
def normalize_team_name_for_matching(team_name: str) -> str:
    """Normalize team name by removing ' - Series X' suffix for matching"""
    if " - Series " in team_name:
        return team_name.split(" - Series ")[0]
    return team_name
```

**Process**:
1. Try exact match first
2. If no match, try normalized match (remove " - Series X" suffix)
3. Use the matched team_id for the schedule entry

### 2. Post-Import Validation (Secondary Prevention)
**File**: `data/etl/database_import/import_all_jsons_to_database.py`

New function `validate_and_fix_schedule_team_mappings()` runs after import:

- **Detection**: Finds all schedule entries with NULL team_ids
- **Fixing**: Applies the same normalization logic to fix mismatches
- **Reporting**: Logs the number of fixes applied

### 3. Comprehensive Orphan Prevention System
**File**: `scripts/prevent_orphaned_ids.py`

The existing orphan prevention system includes schedule validation:

- **Health checks**: Detects schedule entries with invalid team references
- **Auto-fixing**: Repairs orphaned team_id references
- **Foreign key constraints**: Prevents future orphaned insertions

## Prevention Layers

### Layer 1: Import-Time Prevention
- Team name normalization during ETL import
- Prevents the issue from occurring in the first place

### Layer 2: Post-Import Validation
- Automatic detection and fixing of any missed mappings
- Runs as part of the ETL process

### Layer 3: Health Monitoring
- Ongoing validation through the orphan prevention system
- Can be run manually or as part of maintenance scripts

### Layer 4: Database Constraints
- Foreign key constraints prevent invalid team_id insertions
- Database-level protection against future issues

## Testing the Prevention System

### 1. Verify Current Fix
```bash
# Check if any schedule entries still have NULL team_ids
python scripts/fix_schedule_team_mappings.py --check-only
```

### 2. Test ETL Prevention
```bash
# Run a test ETL import to verify the fix works
python data/etl/database_import/import_all_jsons_to_database.py
```

### 3. Run Health Checks
```bash
# Comprehensive orphaned ID check
python scripts/prevent_orphaned_ids.py --health-check
```

## Monitoring and Maintenance

### Regular Health Checks
Run these commands periodically to ensure the system is working:

```bash
# Check for orphaned schedule team mappings
python scripts/prevent_orphaned_ids.py --health-check

# Check mobile availability data
python scripts/test_live_availability.py
```

### ETL Process Monitoring
The ETL process now includes detailed logging for schedule team mappings:

- ✅ "All schedule entries have valid team mappings" (if no issues)
- 🔧 "Found X schedule entries with NULL team_ids - fixing..." (if issues found)
- 📅 "Schedule team mappings fixed: X entries corrected" (in summary)

## Future Considerations

### Data Source Changes
If the schedule data format changes:
1. Update the `normalize_team_name_for_matching()` function
2. Test with a small dataset first
3. Run validation after import

### Additional Validation
Consider adding these checks:
- Verify that all schedule entries have valid league_id mappings
- Check that practice sessions are properly categorized
- Validate date/time format consistency

## Related Files

- `data/etl/database_import/import_all_jsons_to_database.py` - Main ETL process
- `scripts/fix_schedule_team_mappings.py` - One-time repair script
- `scripts/prevent_orphaned_ids.py` - Comprehensive prevention system
- `app/services/mobile_service.py` - Mobile availability service
- `app/routes/mobile_routes.py` - Mobile availability routes

## Current Status

### ✅ Fixed Issues
- **NSTF League**: Team name normalization successfully fixes " - Series X" suffix mismatches
- **APTA Chicago**: Most entries have proper team mappings (97% success rate)
- **Mobile Availability**: Shows both matches and practices for properly mapped teams

### ⚠️ Known Issues Requiring Manual Intervention
- **CITA League**: 846/857 entries (99%) have NULL team_ids due to fundamental data mismatches
  - Schedule: "Midtown - Palatine - 3.5 & Under Sat"
  - Teams: "Midtown - Palatine - 3.0 & Under Thur"
  - Different skill levels and days between schedule and teams data
  
- **CNSWPL League**: 574/1,233 entries (47%) have NULL team_ids due to fundamental data mismatches
  - **Letter Series**: 504 entries with series A, B, C, D, E, F, G, H, I, J, K, SN
  - **Suffix Mismatches**: 70 entries with "b" suffixes (1b, 2b, 3b, etc.) vs teams table "a" suffixes
  - Schedule: "North Shore I - Series I", "Hinsdale PC 1b - Series 1"
  - Teams: "North Shore 1", "Hinsdale PC 1a"
  - Different series naming conventions between data sources

## Success Metrics

The prevention system is working correctly when:
- ✅ ETL imports complete with detailed league-by-league breakdown
- ✅ NSTF and APTA Chicago leagues have 95%+ team mapping success
- ✅ Mobile availability page shows both matches and practices for properly mapped teams
- ✅ Health checks pass with zero orphaned schedule team references for supported leagues
- ⚠️ Known data mismatches in CITA/CNSWPL are clearly reported for manual intervention 