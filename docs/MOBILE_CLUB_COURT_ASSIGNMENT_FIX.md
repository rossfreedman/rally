# Mobile Club Court Assignment Fix

## Issue
The mobile my-club page was not correctly assigning matches to courts on the "Recent Match Results" section. Courts were being assigned based on the order of matches in the array rather than using the actual court/line information from the match data.

## Root Cause
The court assignment logic in `get_mobile_club_data()` was using a fallback approach that assigned court numbers based on the length of matches array instead of using the `tenniscores_match_id` field which contains the actual line/court information.

## Solution

### 1. Enhanced Database Query
Updated `get_recent_matches_for_user_club()` to include the `tenniscores_match_id` field in the database query:

```python
# Before
SELECT 
    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
    ms.home_team as "Home Team",
    # ... other fields
    '' as "Court",
FROM match_scores ms

# After
SELECT 
    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
    ms.home_team as "Home Team",
    # ... other fields
    ms.tenniscores_match_id as "Tenniscores Match ID",
    '' as "Court",
FROM match_scores ms
```

### 2. Fixed Court Assignment Logic
Updated the court assignment logic in `get_mobile_club_data()` to use the `tenniscores_match_id` field:

```python
# Before
court = match.get("court", "")
try:
    court_num = (
        int(court)
        if court and court.strip()
        else len(team_matches[team]["matches"]) + 1
    )
except (ValueError, TypeError):
    court_num = len(team_matches[team]["matches"]) + 1

# After
# FIXED: Use tenniscores_match_id to determine court number from line number
tenniscores_match_id = match.get("tenniscores_match_id", "")
court_num = None

if tenniscores_match_id and "_Line" in tenniscores_match_id:
    # Extract court number from tenniscores_match_id (e.g., "12345_Line2_Line2" -> 2)
    # Handle duplicate _Line pattern by taking the last occurrence
    line_parts = tenniscores_match_id.split("_Line")
    if len(line_parts) > 1:
        line_part = line_parts[-1]  # Take the last part
        try:
            court_num = int(line_part)
        except ValueError:
            # Fallback to database ID order if parsing fails
            court_num = len(team_matches[team]["matches"]) + 1
    else:
        # Fallback to database ID order if no line number found
        court_num = len(team_matches[team]["matches"]) + 1
else:
    # Fallback to database ID order if no tenniscores_match_id
    court_num = len(team_matches[team]["matches"]) + 1
```

### 3. Enhanced Data Normalization
Updated the match data normalization to include the `tenniscores_match_id` field:

```python
normalized_match = {
    # ... other fields
    "tenniscores_match_id": match.get("Tenniscores Match ID", ""),
    # ... other fields
}
```

## Testing Results
Verified the fix works correctly with test data:

- **Court 1**: Matches with `_Line1` in tenniscores_match_id
- **Court 2**: Matches with `_Line2` in tenniscores_match_id  
- **Court 3**: Matches with `_Line3` in tenniscores_match_id
- **Court 4**: Matches with `_Line4` in tenniscores_match_id
- **Court 5**: Matches with `_Line5` in tenniscores_match_id

## Impact
- Mobile my-club page now shows matches on the correct courts
- Court assignments are based on actual match data rather than array position
- Consistent with the court assignment logic used in other parts of the application
- Maintains backward compatibility with fallback logic for edge cases

## Technical Details

### Tenniscores Match ID Format
The `tenniscores_match_id` column contains court information in the format:
- `{base_match_id}_Line{court_number}` (e.g., `nndz-WWlHNnc3djlqQT09_Line4`)
- Some records may have duplicate patterns like `{base_match_id}_Line{court_number}_Line{court_number}`

### Court Assignment Logic
1. Extract the line number from `tenniscores_match_id` using `_Line` as delimiter
2. Handle duplicate patterns by taking the last occurrence
3. Convert the line number to an integer for court assignment
4. Fall back to array position if parsing fails or no match ID is available

## Files Modified
- `app/services/mobile_service.py`: Updated `get_recent_matches_for_user_club()` and `get_mobile_club_data()` functions

## Future Considerations
- Consider adding validation to ensure all match records have proper `tenniscores_match_id` values
- Monitor for any edge cases where match IDs don't follow the expected format
- Consider adding logging for cases where fallback logic is used 