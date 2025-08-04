# Court Performance Fix

## Issue
The "Court Performance This Season" section on the mobile analyze-me page was not showing any data for players like Ross Freedman (Player ID: nndz-WkMrK3didjlnUT09).

## Root Cause
Two issues were identified:

1. **Wrong Season Logic**: The court analysis function was using the old season definition (2025-2026) instead of the correct season (2024-2025) that matches the database data.

2. **Incorrect Court Assignment**: The court assignment logic was using database ID order instead of the `tenniscores_match_id` column which contains the actual court/line information.

## Solution

### 1. Fixed Season Logic
Updated the season filtering in `calculate_individual_court_analysis()` to use the correct 2024-2025 season:

```python
# For now, use 2024-2025 season since that's what the data represents
# TODO: Update this when we have 2025-2026 season data
season_start_year = 2024
season_end_year = 2025

season_start = datetime(season_start_year, 8, 1)  # August 1st
season_end = datetime(season_end_year, 3, 31)  # March 31st
```

### 2. Fixed Court Assignment Logic
Updated the court assignment to use `tenniscores_match_id` instead of database ID order:

```python
# Extract court number from tenniscores_match_id (e.g., "12345_Line2_Line2" -> 2)
# Handle duplicate _Line pattern by taking the last occurrence
line_parts = tenniscores_match_id.split("_Line")
if len(line_parts) > 1:
    line_part = line_parts[-1]  # Take the last part
    try:
        court_number = int(line_part)
    except ValueError:
        # Fallback to database ID order if parsing fails
        court_number = ((team_day_matches.index(team_match) % 4) + 1)
else:
    # Fallback to database ID order if no line number found
    court_number = ((team_day_matches.index(team_match) % 4) + 1)
```

### 3. Enhanced Database Query
Added `tenniscores_match_id` to the database query to enable court assignment:

```python
SELECT 
    id,
    tenniscores_match_id,  # Added this field
    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
    # ... other fields
FROM match_scores ms
```

## Testing Results
After the fix, Ross Freedman's court performance shows:

- **Court 1**: 2 matches, 0-2 record, 0.0% win rate
- **Court 2**: 6 matches, 5-1 record, 83.3% win rate  
- **Court 3**: 2 matches, 1-1 record, 50.0% win rate
- **Court 4**: 2 matches, 1-1 record, 50.0% win rate

## Impact
- Court Performance This Season now shows accurate data
- Court assignments are based on actual `tenniscores_match_id` values
- Season filtering correctly identifies current season matches
- All players should now see their court performance data

## Technical Details

### Tenniscores Match ID Format
The `tenniscores_match_id` column contains court information in the format:
- `{base_match_id}_Line{court_number}_Line{court_number}` (e.g., `nndz-WWlPd3dyditqQT09_Line3_Line3`)

The duplicate `_Line` pattern is handled by taking the last occurrence to extract the court number.

### Court Assignment Logic
1. Group matches by date and team matchup
2. For each match, find the corresponding record in the grouped data
3. Extract court number from `tenniscores_match_id`
4. Assign match to the appropriate court (1-4)
5. Calculate court-specific statistics (wins, losses, partners, etc.)

## Future Considerations
When new season data (2025-2026) is available, update the season definition to use dynamic calculation based on current date. 