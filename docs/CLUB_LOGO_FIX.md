# Club Logo Fix Documentation

## Issue
The mobile site at `http://localhost:8080/mobile` was showing the wrong logo for Glenbrook RC. Investigation revealed that club logos were not displaying correctly due to missing `logo_filename` values in the database.

## Root Cause
1. The `logo_filename` column was added to the `clubs` table via Alembic migration `001_add_club_logo_filename`
2. The migration correctly set logo filenames for Glenbrook RC and Tennaqua
3. However, when ETL imports run, they clear and recreate the clubs table without preserving the `logo_filename` values
4. This caused the logo filenames to be reset to `NULL`, breaking logo display on the mobile site

## Technical Details

### How Logo Display Works
- Club logos are displayed in `templates/mobile/index.html` using session data
- The session service (`app/services/session_service.py`) pulls the logo from `clubs.logo_filename`
- If `logo_filename` is `NULL`, the default logo is used instead

### Files Affected
- **Display Template**: `templates/mobile/index.html` (lines 21-22)
- **Session Service**: `app/services/session_service.py` (lines 99, 371)
- **Database Model**: `app/models/database_models.py` (line 230)
- **Migration**: `alembic/versions/001_add_club_logo_filename.py`
- **ETL Import**: `data/etl/database_import/import_all_jsons_to_database.py`

## Solution Implemented

### 1. Immediate Fix
Updated the database directly to set correct logo filenames:
```sql
UPDATE clubs SET logo_filename = 'static/images/clubs/glenbrook_rc_logo.png' WHERE name = 'Glenbrook RC';
UPDATE clubs SET logo_filename = 'static/images/clubs/tennaqua_logo.png' WHERE name = 'Tennaqua';
```

### 2. Automated Fix Script
Created `scripts/fix_club_logos.py` to automatically restore club logos after ETL imports:
- Run with: `python scripts/fix_club_logos.py`
- Sets correct logo filenames for clubs that should have logos
- Can be run anytime after ETL imports to restore logos

### 3. ETL Process Enhancement
Modified `import_clubs()` function in the ETL script to preserve logo filenames:
- Now attempts to preserve existing logo filenames when recreating clubs
- Falls back to hardcoded values for known clubs (Glenbrook RC, Tennaqua)
- Prevents logo filenames from being lost during future ETL imports

## Files Created/Modified

### Created
- `scripts/fix_club_logos.py` - Automated logo restoration script
- `docs/CLUB_LOGO_FIX.md` - This documentation

### Modified
- `data/etl/database_import/import_all_jsons_to_database.py` - Enhanced club import to preserve logos

## Current Status
✅ **RESOLVED** - Club logos now display correctly on the mobile site.

## Future Considerations
1. **Logo Management**: Consider adding a proper admin interface for managing club logos
2. **ETL Protection**: The enhanced ETL process should prevent this issue from recurring
3. **New Clubs**: When adding new clubs with logos, update the fix script and ETL mappings

## Testing
1. Visit `http://localhost:8080/mobile` as a Glenbrook RC user - should see correct logo
2. Visit as a Tennaqua user - should see correct logo  
3. Visit as any other club user - should see default logo
4. Run ETL import and verify logos are preserved 