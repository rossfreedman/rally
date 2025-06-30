# Club/Team Switching Implementation

## Overview

Successfully implemented club/team switching functionality that allows users with multiple teams within the same league to switch between their team contexts while staying in the same league. This is separate from and complementary to the existing league switching functionality.

## Use Cases

**Target Users**: Players who belong to multiple teams within the same league
- **Rob Werman**: Has teams in both "Glenbrook RC - Chicago 8" and "Tennaqua - Chicago 7" within APTA Chicago
- **Brett Pierson**: Has teams in both "Tennaqua - Chicago 7" and "Valley Lo - Chicago 8" within APTA Chicago

## Architecture

### API Endpoints

#### 1. `/api/get-user-teams-in-current-league` (GET)
**Purpose**: Get user's teams within their current league only
**Response**:
```json
{
  "success": true,
  "teams": [
    {
      "team_id": 21525,
      "team_name": "Glenbrook RC - 8",
      "club_name": "Glenbrook RC", 
      "series_name": "Chicago 8",
      "match_count": 84,
      "is_current": true
    },
    {
      "team_id": 21971,
      "team_name": "Tennaqua - 7",
      "club_name": "Tennaqua",
      "series_name": "Chicago 7", 
      "match_count": 80,
      "is_current": false
    }
  ],
  "has_multiple_teams": true,
  "current_league_id": 4551
}
```

#### 2. `/api/switch-team-in-league` (POST)
**Purpose**: Switch user's team/club within the same league
**Request**:
```json
{
  "team_id": 21971
}
```
**Response**:
```json
{
  "success": true,
  "team_id": 21971,
  "team_name": "Tennaqua - 7",
  "club_name": "Tennaqua",
  "series_name": "Chicago 7",
  "league_name": "APTA Chicago",
  "message": "Switched to Tennaqua - Chicago 7"
}
```

### Session Service Functions

#### 1. `switch_user_team_in_league(user_email: str, team_id: int) -> bool`
- Validates user has access to the target team
- Verifies team is in the same league as current context
- Returns True if switch is valid

#### 2. `get_session_data_for_user_team(user_email: str, team_id: int) -> Dict`
- Builds session data with specific team context
- Updates all team-related fields (club, series, team_id, club_id, series_id)
- Maintains league context

#### 3. `get_user_teams_in_league(user_email: str, league_id: int) -> List`
- Returns all teams user belongs to within a specific league
- Includes match counts and current team indicators

### UI Components

#### 1. Club Switcher Button
- Added to mobile home page next to league switcher
- Only appears if user has multiple teams in current league
- Triggers club switching modal

#### 2. Club Switching Modal
- Similar design to league switching modal but green-themed
- Shows current team with match statistics
- Lists available teams in same league
- Animated loading and success states

#### 3. JavaScript Functions
- `checkMultipleClubs()`: Detects if user has multiple teams
- `showClubSwitcher()`: Opens the modal and loads team options
- `loadClubSwitcherOptions()`: Populates modal with user's teams
- `switchTeamInLeague()`: Executes the team switch

## Key Design Principles

### 1. **League Isolation**
- Team switching only works within the same league
- League context (`league_id`) never changes during team switching
- Prevents accidental cross-league switches

### 2. **Session Consistency**
- Updates all relevant session fields: `club`, `series`, `team_id`, `club_id`, `series_id`
- Maintains `tenniscores_player_id` for the correct player record
- League fields remain unchanged

### 3. **Security & Validation**
- Verifies user has valid player association with target team
- Ensures team belongs to user's current league
- Graceful error handling for invalid switches

### 4. **UI/UX**
- Non-intrusive: Only shows when user has multiple teams
- Consistent with league switching design patterns
- Clear visual feedback during switching process

## Testing Results

### Test Case: Rob Werman
- **League**: APTA Chicago (ID: 4551)
- **Team 1**: Glenbrook RC - Chicago 8 (ID: 21525, 84 matches)
- **Team 2**: Tennaqua - Chicago 7 (ID: 21971, 80 matches)

**Results**:
✅ Successfully detects multiple teams  
✅ Modal displays both teams with match counts  
✅ Switch validation passes  
✅ Session data updates correctly  
✅ League context preserved  
✅ All IDs (team_id, club_id, series_id) updated accurately  

## Integration Points

### Pages That Benefit
- **Analyze Me**: Now shows data for correct team context
- **My Club**: Filtered by current team context
- **Track Byes & Courts**: Shows data for active team
- **Find People to Play**: Team-specific filtering
- **Schedule**: Team-specific match listings

### Database Impact
- No schema changes required
- Uses existing `league_context` field in `users` table
- Leverages existing team/player associations

## Future Enhancements

1. **Team Context Persistence**: Store team preference in database
2. **Quick Team Switcher**: Add to navigation bar for all pages
3. **Multi-League Team Switching**: Combine with league switching for users with teams across leagues
4. **Team Switching Analytics**: Track which teams users switch to most

## Files Modified

### Backend
- `app/routes/api_routes.py`: Added 2 new API endpoints
- `app/services/session_service.py`: Added 3 new functions

### Frontend  
- `templates/mobile/index.html`: Added club switching modal and JavaScript
- No changes to existing pages - they automatically use new session context

### Testing
- `scripts/test_club_team_switching.py`: Comprehensive test suite

## Deployment Notes

- ✅ No database migrations required
- ✅ Backward compatible with existing functionality
- ✅ No breaking changes to existing APIs
- ✅ Safe to deploy without affecting current users

## Summary

This implementation provides a seamless way for multi-team players to switch between their team contexts within the same league, enhancing the user experience for players like Rob Werman and Brett Pierson who participate in multiple teams. The solution is isolated, secure, and maintains data consistency while providing intuitive UI controls. 