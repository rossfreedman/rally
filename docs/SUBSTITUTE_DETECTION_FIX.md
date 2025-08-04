# Substitute Detection Fix

## Issue
The Court Performance This Season section was not showing "Sub for [Series Name]" chips for substitute players in the UI, even though the backend logic was working correctly.

## Root Cause
The `get_player_analysis` function in `app/services/mobile_service.py` was not including the `home_team_id` and `away_team_id` fields in the database query that retrieves player matches. This caused the substitute detection logic to receive `None` values for team IDs, preventing it from identifying substitute players.

## Solution
Added the missing team ID fields to both database queries in the `get_player_analysis` function:

### Before:
```sql
SELECT 
    id,
    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
    home_team as "Home Team",
    away_team as "Away Team",
    winner as "Winner",
    scores as "Scores",
    home_player_1_id as "Home Player 1",
    home_player_2_id as "Home Player 2",
    away_player_1_id as "Away Player 1",
    away_player_2_id as "Away Player 2"
FROM match_scores
```

### After:
```sql
SELECT 
    id,
    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
    home_team as "Home Team",
    away_team as "Away Team",
    home_team_id,
    away_team_id,
    winner as "Winner",
    scores as "Scores",
    home_player_1_id as "Home Player 1",
    home_player_2_id as "Home Player 2",
    away_player_1_id as "Away Player 1",
    away_player_2_id as "Away Player 2"
FROM match_scores
```

## Testing Results
After the fix, the substitute detection is working correctly:

### Debug Output:
```
[DEBUG] Substitute detected! Partner nndz-WkNDd3liZitqQT09 on team 92752, user team is 92755
[DEBUG] Found series name for team 92752: Chicago 19
[DEBUG] Substitute detected! Partner nndz-WkMrK3didnhoUT09 on team 92754, user team is 92755
[DEBUG] Found series name for team 92754: Chicago 21
```

### Court Analysis Output:
```
Court 4:
   matches: 2
   wins: 1
   losses: 1
   winRate: 50.0
   topPartners: 2 partners
      1. Mike Lieberman: 1 matches (Sub for Chicago 21)
      2. Dave Arenberg: 1 matches (Sub for Chicago 19)
```

## Impact
- Substitute players are now correctly identified and displayed with "Sub for [Series Name]" chips
- The UI shows orange chips with exchange icons for substitute players
- Users can easily distinguish between regular team matches and substitute appearances
- Enhanced transparency about player participation across different teams/series

## Technical Details
- **Team ID Comparison**: The system compares `match_team_id` with `user_team_id` to detect substitutes
- **Series Name Lookup**: When a substitute is detected, the system queries the `teams` and `series` tables to get the series name
- **Frontend Display**: The template shows "Sub for {{ partner.substituteSeries }}" in orange chips
- **Database Relationships**: `match_scores.home_team_id/away_team_id` → `teams.id` → `series.id` → `series.name` 