# Court Performance Substitute Detection Enhancement

## Issue
The Court Performance This Season section needed to identify when a player was a substitute (playing for a different team than their own) and display this information with the series name.

## Solution
Enhanced the court performance analysis to detect substitute players and show "Sub for [Series Name]" chips.

### 1. Enhanced Database Query
Added team IDs to the database query to enable substitute detection:

```python
SELECT 
    id,
    tenniscores_match_id,
    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
    ms.match_date,
    ms.home_team as "Home Team",
    ms.away_team as "Away Team",
    ms.home_team_id,      # Added for substitute detection
    ms.away_team_id,      # Added for substitute detection
    ms.winner as "Winner",
    # ... other fields
FROM match_scores ms
```

### 2. Substitute Detection Logic
Added logic to compare match team ID with user's team ID:

```python
# Get user's team ID for substitute detection
user_team_id = user.get("team_id") if user else None

for match in court_matches:
    # Determine if player was on home or away team
    is_home = player_id in [match.get("Home Player 1"), match.get("Home Player 2")]
    
    if is_home:
        match_team_id = match.get("home_team_id")
    else:
        match_team_id = match.get("away_team_id")
    
    # Check if this partner is a substitute (playing for different team than user's team)
    if user_team_id and match_team_id and str(match_team_id) != str(user_team_id):
        partner_win_counts[partner]["is_substitute"] = True
        
        # Get series name for the substitute team
        series_query = """
            SELECT s.name as series_name
            FROM teams t
            JOIN series s ON t.series_id = s.id
            WHERE t.id = %s
        """
        series_result = execute_query_one(series_query, [match_team_id])
        if series_result:
            partner_win_counts[partner]["substitute_series"] = series_result["series_name"]
```

### 3. Enhanced Partner Data Structure
Updated partner data to include substitute information:

```python
partner_data = {
    "name": partner_name,
    "matches": stats["matches"],
    "wins": stats["wins"],
    "losses": stats["matches"] - stats["wins"], 
    "winRate": partner_win_rate
}

# Add substitute information if this partner was a substitute
if stats.get("is_substitute", False):
    substitute_series = stats.get("substitute_series", "Unknown Series")
    partner_data["isSubstitute"] = True
    partner_data["substituteSeries"] = substitute_series
else:
    partner_data["isSubstitute"] = False
```

### 4. Updated Frontend Template
Enhanced the template to show "Sub for [Series Name]" instead of just "Sub":

```html
{% if partner.isSubstitute %}
<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-700 border border-orange-200">
    <i class="fas fa-exchange-alt mr-1"></i>
    Sub for {{ partner.substituteSeries }}
</span>
{% endif %}
```

## Testing Results
After the enhancement, Ross Freedman's court performance shows:

- **Court 1**: 2 matches, 0-2 record, 0.0% win rate
  - Mike Lieberman: 2 matches
- **Court 2**: 6 matches, 5-1 record, 83.3% win rate
  - Brian Stutland: 1 matches
  - Mike Lieberman: 1 matches
  - Andrew Franger: 1 matches
- **Court 3**: 2 matches, 1-1 record, 50.0% win rate
  - Victor Forman: 1 matches
  - Brian Stutland: 1 matches
- **Court 4**: 2 matches, 1-1 record, 50.0% win rate
  - Mike Lieberman: 1 matches **(Sub for Chicago 21)**
  - Dave Arenberg: 1 matches **(Sub for Chicago 19)**

## Impact
- Substitute players are now clearly identified in court performance
- Series name is displayed for substitute matches (e.g., "Sub for Chicago 21")
- Users can easily distinguish between regular team matches and substitute appearances
- Enhanced transparency about player participation across different teams/series

## Technical Details

### Substitute Detection Logic
1. Compare match team ID with user's team ID
2. If different, mark as substitute
3. Query series table to get series name for substitute team
4. Include substitute information in partner data structure

### Database Relationships
- `match_scores.home_team_id` / `away_team_id` → `teams.id`
- `teams.series_id` → `series.id`
- `series.name` provides the series name for substitute teams

### Frontend Display
- Orange chip with exchange icon
- Shows "Sub for [Series Name]" format
- Maintains existing styling and layout 