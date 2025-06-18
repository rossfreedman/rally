# Strength of Schedule Feature Documentation

## Overview

The **Strength of Schedule (SoS)** feature provides teams with an objective measure of how difficult their schedule has been compared to other teams in their series. This metric helps teams understand the competitive context of their performance by analyzing the average strength of all opponents they have faced.

## What is Strength of Schedule?

Strength of Schedule is a statistical measure that quantifies the difficulty of a team's schedule by calculating the average performance level of all opponents the team has played. In the Rally app, SoS is calculated as:

```
SoS = (Sum of all opponents' average points per match) / (Number of unique opponents)
```

The higher the SoS value, the tougher the schedule a team has faced.

## User Experience

### Location
The Strength of Schedule section appears on the **My Team** page in the Rally mobile app, positioned between the Team Stats card and the Team Roster section.

### Visual Display
- **User team summary**: Highlighted purple box showing your team's SoS value and ranking
- **League-wide rankings table**: Complete table showing all teams ranked by SoS difficulty
- **Visual highlighting**: User's team is highlighted with purple styling and star icon
- **Comprehensive context**: Shows where your team stands relative to every other team
- **Purple-themed design**: Distinguished from other metrics with a unique color scheme

### Example Display
```
┌─────────────────────────────────────────────────┐
│ 📈 Strength of Schedule Rankings                │
├─────────────────────────────────────────────────┤
│        [Your Team's SoS]                        │
│             6.85                                │
│   #1 toughest schedule out of 10 teams         │
│                                                 │
│ Complete League Rankings                        │
│ Rank │ Team Name            │ SoS  │            │
│ ─────┼──────────────────────┼──────┤            │
│ #1 ⭐│ Tennaqua - 19        │ 6.85 │ (Your Team)│
│ #2   │ Biltmore CC - 19     │ 6.75 │            │
│ #3   │ Evanston - 19        │ 6.70 │            │
│ #4   │ Knollwood - 19       │ 6.67 │            │
│ #5   │ Sunset Ridge - 19    │ 6.62 │            │
│ ...  │ ...                  │ ...  │            │
│                                                 │
│ Calculated from 9 opponents played this season │
│ Higher values indicate tougher schedules        │
└─────────────────────────────────────────────────┘
```

## Calculation Logic

### Step 1: Team Identification
The system determines the user's team using their club and series information:
- **NSTF League**: `"{club} S{series_suffix}"` (e.g., "Tennaqua S2B")
- **Other Leagues**: `"{club} - {series_number}"` (e.g., "Tennaqua - 22")

### Step 2: Completed Matches Identification
Retrieves all completed matches involving the user's team:
- Must have a `winner` field (not null/empty)
- Must have a `match_date` on or before today
- Must be in the same league as the user

### Step 3: Opponent Extraction
Identifies unique opponents from completed matches:
- For each match, determines which team was the opponent
- Creates a set of unique opponent team names

### Step 4: Opponent Performance Calculation
For each opponent, calculates their average points per match:
```sql
SELECT points, matches_won, matches_lost, matches_tied
FROM series_stats
WHERE team = opponent_name AND league_id = user_league_id
```

```python
matches_played = matches_won + matches_lost + matches_tied
average_points = points / matches_played  # Only if matches_played > 0
```

### Step 5: SoS Calculation
```python
sos_value = sum(opponent_average_points) / len(opponent_average_points)
sos_value = round(sos_value, 2)  # Round to 2 decimal places
```

### Step 6: League-Wide Ranking
Calculates SoS for all teams in the same series and ranks them:
- Higher SoS = tougher schedule = better rank
- Provides context: "#X toughest schedule out of Y teams"
- Returns complete rankings list for display in table format

### Step 7: Team Data Compilation
Builds comprehensive rankings data structure:
```python
all_teams_sos = [
    {
        'team_name': 'Tennaqua - 19',
        'sos_value': 6.85,
        'rank': 1,
        'is_user_team': True
    },
    {
        'team_name': 'Biltmore CC - 19', 
        'sos_value': 6.75,
        'rank': 2,
        'is_user_team': False
    },
    # ... rest of teams
]
```

## Technical Implementation

### Database Schema Requirements

**Tables Used:**
- `users` - User authentication and profile data
- `user_player_associations` - Links users to their player records
- `players` - Player information including team assignments
- `clubs` - Club/facility information
- `series` - League divisions/series information
- `leagues` - League organization data
- `match_scores` - Historical match results
- `series_stats` - Team performance statistics

**Key Relationships:**
```
users → user_player_associations → players → clubs/series/leagues
players.club_id + players.series_id → team identification
match_scores → completed games with results
series_stats → team performance metrics
```

### Code Structure

#### Backend Implementation

**Main Function:**
```python
# app/services/mobile_service.py
def calculate_strength_of_schedule(user):
    """
    Calculate Strength of Schedule (SoS) for the user's team.
    Returns: dict with sos_value, rank, total_teams, opponents_count, 
             all_teams_sos (list of all teams ranked), user_team_name, error
    """
```

**Integration Point:**
```python
# app/services/mobile_service.py
def get_mobile_team_data(user):
    # ... existing team data calculation ...
    sos_data = calculate_strength_of_schedule(user)
    return {
        'team_data': team_data,
        'court_analysis': court_analysis,
        'top_players': top_players,
        'strength_of_schedule': sos_data  # New addition
    }
```

**Route Handler:**
```python
# app/routes/mobile_routes.py
@mobile_bp.route('/mobile/my-team')
@login_required
def serve_mobile_my_team():
    result = get_mobile_team_data(session['user'])
    strength_of_schedule = result.get('strength_of_schedule', {})
    
    return render_template('mobile/my_team.html',
                         strength_of_schedule=strength_of_schedule,
                         # ... other template variables ...)
```

#### Frontend Implementation

**Template Location:**
```html
<!-- templates/mobile/my_team.html -->
{% if strength_of_schedule and not strength_of_schedule.error %}
<!-- Strength of Schedule Rankings Card -->
<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <!-- User Team Summary -->
    <div class="bg-purple-50 rounded-lg p-4 border border-purple-100">
        <div class="text-3xl font-bold text-purple-700">{{ strength_of_schedule.sos_value }}</div>
        <div class="text-sm font-semibold text-purple-800">
            #{{ strength_of_schedule.rank }} toughest schedule out of {{ strength_of_schedule.total_teams }} teams
        </div>
    </div>
    
    <!-- League-Wide Rankings Table -->
    <table class="min-w-full text-xs">
        {% for team_sos in strength_of_schedule.all_teams_sos %}
        <tr class="{% if team_sos.is_user_team %}bg-purple-50{% endif %}">
            <td>#{{ team_sos.rank }} {% if team_sos.is_user_team %}⭐{% endif %}</td>
            <td>{{ team_sos.team_name }}</td>
            <td>{{ team_sos.sos_value }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}
```

### Data Flow

```
User Login → Session Data → Mobile Route → get_mobile_team_data() 
    ↓
User Profile → Team Identification → calculate_strength_of_schedule()
    ↓
Database Queries → Match Data + Team Stats → SoS Calculation
    ↓
Template Rendering → Mobile UI Display
```

### Error Handling

The system gracefully handles various error conditions:

**No Team Assignment:**
```python
if not club or not series:
    return {'error': 'User club or series not found'}
```

**No Completed Matches:**
```python
if not team_matches:
    return {'error': 'No completed matches found for team'}
```

**No Opponent Statistics:**
```python
if not opponent_avg_points:
    return {'error': 'No opponent statistics available'}
```

## Security Considerations

### Access Control
- **User-scoped data**: Only displays SoS for the logged-in user's own team
- **Team membership verification**: Uses user's player_id to determine team association
- **League filtering**: All calculations are scoped to the user's specific league

### Data Privacy
- No cross-team data exposure
- User cannot access other teams' detailed opponent information
- Only aggregated, publicly-available statistics are used

## Performance Considerations

### Database Optimization
- Uses indexed fields (`team`, `league_id`, `match_date`)
- Efficient JOIN operations for user → team resolution
- Conditional queries based on league membership

### Calculation Efficiency
- Caches opponent list to avoid redundant queries
- Single database round-trip for each opponent's statistics
- Minimal memory footprint with set-based opponent tracking

### Scalability
- O(n) complexity where n = number of unique opponents
- Typically 8-15 opponents per team in a season
- Suitable for real-time calculation

## Future Enhancements

### Potential Improvements
1. **Historical SoS Tracking**: Store calculated SoS values over time
2. **SoS Trends**: Show how schedule difficulty changes week-by-week
3. **Comparative Analytics**: Compare SoS across different series/leagues
4. **Weighted SoS**: Apply recency weighting to recent vs. older matches
5. **SoS Predictions**: Forecast remaining schedule difficulty

### Advanced Metrics
1. **Adjusted SoS**: Account for home/away game balance
2. **Dynamic SoS**: Real-time updates as opponent performance changes
3. **SoS Variance**: Measure consistency of opponent difficulty
4. **Head-to-Head SoS**: SoS specific to certain matchup types

## Maintenance

### Regular Maintenance Tasks
1. **Data Validation**: Ensure match results are properly recorded
2. **Performance Monitoring**: Track calculation performance as data grows
3. **Accuracy Verification**: Spot-check SoS calculations manually

### Troubleshooting Common Issues
1. **Missing SoS Display**: Check user team assignment and match data
2. **Incorrect Rankings**: Verify series_stats data accuracy
3. **Performance Issues**: Monitor database query execution times

## Testing

### Test Coverage
- Unit tests for SoS calculation logic
- Integration tests for database queries
- UI tests for template rendering
- Edge case testing (no matches, no opponents, etc.)

### Sample Test Data
```python
# Test user with known match history
test_user = {
    'club': 'Tennaqua',
    'series': 'Chicago 22',
    'league_id': 'APTA_CHICAGO'
}
# Expected: SoS calculation with multiple opponents
```

---

*This feature enhances team analysis capabilities by providing objective schedule difficulty metrics, helping teams better understand their competitive performance in context.* 