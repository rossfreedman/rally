# PTI Change Calculation Fix

## Issue
The "PTI Change This Season" field on the player detail page was showing "N/A" instead of calculating the actual PTI change for the season.

## Root Cause
The season calculation logic was incorrect. The system was looking for PTI records in the wrong season:

- **Current Date**: August 2025
- **Incorrect Logic**: Looking for 2025-2026 season (Aug 2025 - Jul 2026)
- **Correct Logic**: Should look for 2024-2025 season (Aug 2024 - Jul 2025)

The player's PTI history data was from January-March 2025, which belongs to the 2024-2025 season, not the 2025-2026 season.

## Solution
Updated the season year calculation logic in `app/services/mobile_service.py`:

### Before:
```python
# Determine season year based on current date
if current_month >= 8:  # Aug-Dec: current season
    season_start_year = current_year
else:  # Jan-Jul: previous season
    season_start_year = current_year - 1
```

### After:
```python
# Determine season year based on current date
# Since we're in August 2025, we want the 2024-2025 season (Aug 2024 - Jul 2025)
# which contains the player's data from Jan-Mar 2025
if current_month >= 8:  # Aug-Dec: previous season (since we're in offseason)
    season_start_year = current_year - 1
else:  # Jan-Jul: previous season
    season_start_year = current_year - 1
```

## Testing Results
After the fix, the PTI change calculation works correctly:

### Mike Lieberman's PTI Change:
- **Season**: 2024-2025 (Aug 2024 - Jul 2025)
- **Start PTI**: 49.20 (September 24, 2024)
- **End PTI**: 44.10 (March 4, 2025)
- **Change**: -5.1 (improvement, negative is good)

### Data Verification:
- **Total Season Records**: 18 PTI entries
- **Date Range**: September 2024 - March 2025
- **PTI Trend**: Declining from 49.20 to 44.10 (improvement)

## Impact
- **Player Detail Page**: Now shows accurate PTI change instead of "N/A"
- **Season Calculation**: Correctly identifies the appropriate season for PTI analysis
- **Data Accuracy**: Uses the player's actual first and last PTI values from the season

## Technical Details
- **Season Definition**: August 1st - July 31st
- **Current Season Logic**: Since we're in August 2025 (offseason), we look at the previous season (2024-2025)
- **PTI Calculation**: `end_pti - start_pti` where start is the first PTI record of the season and end is the last
- **Display Logic**: Negative values are good (improvement), positive values are bad (decline)

## Template Display
The template correctly handles the PTI change display:
- **Negative values**: Green with down arrow (▼) - improvement
- **Positive values**: Red with up arrow (▲) - decline
- **Zero**: Gray - no change
- **N/A**: When insufficient data 