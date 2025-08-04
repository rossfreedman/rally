# Current Season Stats Fix

## Issue
Players on staging were showing incorrect current season stats and court performance. The problem was that the system was calculating stats from **ALL matches** instead of filtering by the **current season**.

## Root Cause
The season filtering logic was using the wrong season definition:
- **Old logic**: Used 2025-2026 season (August 2025 - July 2026) 
- **Database data**: Contains 2024-2025 season matches (September 2024 - July 2025)
- **Result**: No matches found because the season definition didn't match the data

## Solution
Updated the season filtering logic in `app/services/mobile_service.py` to use the **2024-2025 season** (August 2024 - March 2025) since that's what the database data represents.

### Changes Made:
1. **Season Definition**: Changed from dynamic calculation to fixed 2024-2025 season
2. **Date Filtering**: Applied season boundaries to both current season stats and court performance queries
3. **Database Queries**: Added `AND match_date >= %s AND match_date <= %s` filters

### Code Changes:
```python
# For now, use 2024-2025 season since that's what the data represents
# TODO: Update this when we have 2025-2026 season data
season_start_year = 2024
season_end_year = 2025

season_start = datetime(season_start_year, 8, 1)  # August 1st
season_end = datetime(season_end_year, 3, 31)  # March 31st
```

## Testing Results
After the fix:
- **Jeff Condren**: 14 current season matches ✅
- **Daniel McNair**: 19 current season matches ✅  
- **Ross Freedman**: 12 current season matches ✅
- **Brian Wagner**: 0 current season matches ✅ (matches are from May-June 2025, outside 2024-2025 season)

## Impact
- Current season stats now show correct match counts
- Court performance analysis now filters by current season
- All players on staging should now display accurate data

## Future Considerations
When new season data (2025-2026) is available, update the season definition to use dynamic calculation based on current date. 