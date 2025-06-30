# Enhanced League & Team Selector Implementation

## Problem Statement

Users like Rob/Robert Werman who belong to multiple teams in the same league need a way to seamlessly switch between their team contexts. Previously, the league selector only handled league switching, but didn't account for users who have multiple teams within a single league.

## Rob Werman's Specific Case

**User:** Rob Werman (rwerman@gmail.com, user_id: 350)
**Teams:**
- **Glenbrook RC - 8** (Chicago 8 series) - APTA Chicago league (team_id: 21525)
- **Tennaqua - 7** (Chicago 7 series) - APTA Chicago league (team_id: 21971)  
- **Tennaqua S2A** (S2A series) - North Shore Tennis Foundation league (team_id: 21979)

**Issue:** When Rob is in APTA Chicago league, he has 2 teams but could only see data mixed from both teams instead of being able to switch between them cleanly.

## Solution Architecture

### 1. Enhanced League/Team Context Manager

**File:** `static/js/enhanced-league-team-context-manager.js`

**Key Features:**
- Extends existing `LeagueContextManager` class
- Auto-detects when users have multiple teams in current league
- Dynamically adds team selector to existing league modal
- Uses existing `/api/switch-team-context` endpoint
- Maintains backward compatibility with single-team users

**Workflow:**
1. On page load, checks if user has multiple teams via `/api/get-user-teams`
2. If multiple teams exist, activates enhanced mode
3. When league selector opens, dynamically injects team options for current league
4. Team switching updates `league_context` field to set user to correct league/team combination

### 2. New API Endpoint

**Endpoint:** `GET /api/get-user-teams`

**Purpose:** Returns user's team information for context switching

**Response:**
```json
{
    "success": true,
    "teams": [
        {
            "id": 21525,
            "team_name": "Glenbrook RC - 8", 
            "club_name": "Glenbrook RC",
            "series_name": "Chicago 8",
            "league_db_id": 4489,
            "league_string_id": "APTA_CHICAGO",
            "league_name": "APTA Chicago",
            "match_count": 15
        },
        {
            "id": 21971,
            "team_name": "Tennaqua - 7",
            "club_name": "Tennaqua", 
            "series_name": "Chicago 7",
            "league_db_id": 4489,
            "league_string_id": "APTA_CHICAGO", 
            "league_name": "APTA Chicago",
            "match_count": 12
        }
    ],
    "current_team": {...},
    "current_league_teams": [...],
    "has_multiple_teams": true,
    "has_multiple_teams_in_current_league": true
}
```

### 3. Enhanced User Experience

**For Single-Team Users:**
- No changes - existing league selector works exactly as before
- Enhanced manager doesn't activate

**For Multi-Team Users (like Rob):**
- League selector now shows **both** league switching AND team switching options
- Team switching section appears when user has multiple teams in current league
- Seamless switching between teams maintains all session context
- Page reloads with new team context, showing only that team's data

**UI Enhancement:**
```
[Existing League Selector Modal]
├── Current League Display (unchanged)
├── [NEW] Team Switching Section
│   ├── "Switch Team (Current League)" header  
│   ├── Glenbrook RC - 8 [Switch] button
│   └── Tennaqua - 7 [Current] button
└── League Switching Section (unchanged)
    ├── APTA Chicago options
    └── NSTF options
```

## Implementation Details

### Files Modified

1. **`static/js/enhanced-league-team-context-manager.js`** (NEW)
   - Enhanced context manager class
   - Team switching logic
   - UI injection for team selector

2. **`app/routes/api_routes.py`**
   - Added `/api/get-user-teams` endpoint
   - Returns user's team data and current context

3. **`templates/mobile/layout.html`**
   - Includes enhanced context manager script
   - Enhanced `switchLeague()` function to use new manager

4. **`templates/mobile/index.html`**
   - Enhanced modal open event to trigger team UI updates

### Database Dependencies

**Uses Existing Tables:**
- `users` table with `league_context` field
- `user_player_associations` table
- `players`, `teams`, `clubs`, `series`, `leagues` tables
- Existing `/api/switch-team-context` endpoint

**No Database Migration Required** - works with current stable system

### Backward Compatibility

- **100% backward compatible**
- Single-team users see no changes
- Existing league switching continues to work
- Falls back gracefully if enhanced manager fails to load

## Testing Scenarios

### Test Case 1: Rob Werman (Multi-Team User)
**Setup:** User belongs to 2+ teams in same league
**Expected:** Team selector appears in league modal
**Result:** Can switch between Glenbrook RC-8 and Tennaqua-7 teams

### Test Case 2: Single-Team User  
**Setup:** User belongs to 1 team per league
**Expected:** No team selector appears, normal league switching
**Result:** Existing behavior maintained

### Test Case 3: Multi-League User (Single Team Each)
**Setup:** User in multiple leagues, 1 team each
**Expected:** League switching only, no team selector
**Result:** Enhanced manager doesn't interfere

## Usage Instructions

### For Rob Werman:

1. **Login** as rwerman@gmail.com
2. **Click league selector** button (pencil icon) on home page  
3. **See enhanced modal** with:
   - Current league: APTA Chicago
   - Team options: "Glenbrook RC - 8" and "Tennaqua - 7"
   - League switching options: NSTF
4. **Click team button** to switch between Glenbrook RC and Tennaqua teams
5. **Page reloads** with new team context
6. **All app data** (my-team, analyze-me, etc.) now filtered to selected team

### For League Switching:

1. **Same interface** - click league button (e.g., "North Shore Tennis Foundation") 
2. **Switches to NSTF** league context with Tennaqua S2A team
3. **Team selector disappears** (only 1 team in NSTF)

## Success Criteria

✅ **Multi-team users can switch between teams seamlessly**
✅ **Single-team users see no changes to existing workflow**  
✅ **No database migration required**
✅ **Uses existing stable API endpoints**
✅ **Backward compatible with all existing functionality**
✅ **Rob Werman can switch between his Glenbrook RC and Tennaqua teams**

## Future Enhancements

- **URL Parameter Support**: `?team_id=21525` for direct team links
- **Team Preferences**: Remember last selected team per league
- **Advanced UI**: Show team stats, match counts in selector
- **Mobile Optimization**: Improved touch/swipe interactions

## Security Considerations

- **Access Control**: Users can only switch to teams they belong to
- **Validation**: All team switches validated against `user_player_associations`
- **Session Security**: Context changes update session safely
- **SQL Injection**: All queries use parameterized statements

This implementation provides a seamless solution for multi-team users like Rob Werman while maintaining full backward compatibility and requiring no database changes. 