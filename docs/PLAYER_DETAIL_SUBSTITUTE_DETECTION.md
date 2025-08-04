# Player Detail Substitute Detection Enhancement

## Issue
The player detail page (`/mobile/player-detail/<player_id>`) was not showing substitute detection for court performance, even though the analyze-me page had this functionality.

## Root Cause
The player detail route was calling `get_player_analysis()` but not passing the `team_id` field that the substitute detection logic requires.

## Solution
Updated the player detail route in `app/routes/mobile_routes.py` to include the `team_id` field in the `player_user_dict`:

### Before:
```python
# Add team context for filtering
if team_id:
    player_user_dict["team_context"] = team_id
    print(f"[DEBUG] Player detail - Using player ID {actual_player_id} with team context {team_id}")
else:
    print(f"[DEBUG] Player detail - Using player ID {actual_player_id} without specific team context")
```

### After:
```python
# Add team context for filtering and substitute detection
if team_id:
    player_user_dict["team_context"] = team_id
    player_user_dict["team_id"] = str(team_id)  # Add team_id for substitute detection
    print(f"[DEBUG] Player detail - Using player ID {actual_player_id} with team context {team_id}")
else:
    print(f"[DEBUG] Player detail - Using player ID {actual_player_id} without specific team context")
```

## Testing Results
After the fix, the player detail page correctly shows substitute detection:

### Mike Lieberman's Court Analysis:
```
Court 4:
   matches: 2
   wins: 2
   losses: 0
   winRate: 100.0
   topPartners: 2 partners
      1. Kurt Kleckner: 1 matches (Sub for Series 21)
      2. Ross Freedman: 1 matches (Sub for Series 21)
```

### Analysis:
- **Mike Lieberman** is playing for his team (Tennaqua - 22, team_id 92755)
- **Kurt Kleckner** and **Ross Freedman** are marked as substitutes from Series 21
- This means when Mike was playing for his team, he had substitute partners from a different series

## Impact
- Player detail pages now show substitute detection with "Sub for [Series Name]" chips
- Users can see when a player's partners were substitutes from different teams/series
- Consistent substitute detection across both analyze-me and player detail pages
- Enhanced transparency about player partnerships and substitute appearances

## Technical Details
- **Team Context**: The player detail route now passes `team_id` to enable substitute detection
- **Series Display**: Uses the same `convert_chicago_to_series_for_ui` function for consistent series naming
- **Database Integration**: Leverages the same team ID comparison logic as the analyze-me page
- **Frontend Display**: Uses the same template logic for showing substitute chips

## URL Format
The player detail page supports composite IDs for team-specific context:
- `/mobile/player-detail/nndz-WkMrK3didnhoUT09_team_92755` - Shows player with specific team context
- `/mobile/player-detail/nndz-WkMrK3didnhoUT09` - Shows player with default team context

## Consistency
Both the analyze-me page and player detail page now use the same:
- Substitute detection logic
- Series name conversion (Chicago → Series)
- Frontend display format
- Database query structure 