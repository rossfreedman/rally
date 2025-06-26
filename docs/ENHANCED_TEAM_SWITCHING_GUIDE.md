# Enhanced Team Switching System
**Comprehensive Multi-League & Multi-Team Support**

## Overview

This guide documents the enhanced team switching system that provides bulletproof support for users across multiple leagues and teams. The system replaces the problematic "primary association" concept with dynamic context switching.

## Problem Statement

The original system had several critical issues:

1. **Primary Association Limitations**: Users could only have one "primary" player association, which failed for users in multiple leagues or teams
2. **Rigid Session Context**: Sessions stored single league/club/series data, inadequate for multi-league users
3. **Limited Team Switching**: Only available on one page (track-byes-courts)
4. **Registration Gaps**: Didn't create comprehensive associations for all user affiliations
5. **Poor Multi-League Experience**: Users had to choose between their league contexts, losing access to others

## Solution Architecture

### 1. **Dynamic Context System**

**Before (Problematic):**
```sql
user_player_associations (
    user_id, tenniscores_player_id, is_primary, created_at
)
```

**After (Enhanced):**
```sql
-- Association table (no more primary concept)
user_player_associations (
    user_id, tenniscores_player_id, created_at
)

-- New dynamic context table
user_contexts (
    user_id, active_league_id, active_team_id, last_updated
)
```

### 2. **Key Components**

#### **A. ContextService** (`app/services/context_service.py`)
Central service managing all context operations:
- `switch_context()` - Changes user's active league/team
- `get_context_info()` - Retrieves current context
- `get_user_leagues()` - Lists all user's leagues
- `get_user_teams()` - Lists all user's teams
- `auto_detect_context()` - Intelligently sets initial context

#### **B. Enhanced Registration** (`app/services/enhanced_registration_service.py`)
Comprehensive registration that finds ALL user associations:
- Discovers players across all leagues using multiple strategies
- Creates associations for all high-confidence matches
- Automatically assigns teams to all players
- Sets up appropriate initial context

#### **C. Universal Team Selector** (`templates/components/team_selector.html`)
Reusable component for any page:
- Modal interface for team/league switching
- URL-based context switching with session persistence
- AJAX-based switching for single-page app feel
- Loading states and error handling

#### **D. Enhanced Session Management**
Sessions now include:
```python
{
    # Traditional fields
    "id": user_id,
    "email": email,
    # ... other user fields ...
    
    # Context information
    "context": {
        "team_id": active_team_id,
        "team_name": "Team Name",
        "league_id": active_league_id,
        "league_name": "League Name",
        # ... full context details ...
    },
    
    # Multi-league/team metadata
    "user_leagues": [...],  # All leagues user belongs to
    "user_teams": [...],    # All teams user belongs to
    "is_multi_league": True/False,
    "is_multi_team": True/False,
    "can_switch_leagues": True/False,
    "can_switch_teams": True/False,
}
```

## Implementation Details

### 1. **Database Migration**

```sql
-- Create user contexts table
CREATE TABLE user_contexts (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    active_league_id INTEGER REFERENCES leagues(id),
    active_team_id INTEGER REFERENCES teams(id),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Migrate existing primary associations
INSERT INTO user_contexts (user_id, active_league_id, active_team_id)
SELECT DISTINCT 
    upa.user_id,
    p.league_id,
    p.team_id
FROM user_player_associations upa
JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
WHERE upa.is_primary = TRUE AND p.is_active = TRUE;

-- Drop is_primary column
ALTER TABLE user_player_associations DROP COLUMN is_primary;
```

### 2. **Context Switching Flow**

1. **User Triggers Switch** (via UI or URL parameter)
2. **Validation** - Verify user has access to requested team/league
3. **Update Context** - Modify user_contexts table
4. **Session Update** - Refresh session with new context
5. **Page Reload/Refresh** - Display data for new context

### 3. **Team Selector Integration**

Add to any template:
```html
{% include 'components/team_selector.html' %}
```

Required template variables:
- `user_teams` - List of teams user can access
- `current_team_info` - Current team context (optional)

### 4. **Mobile Route Updates**

Enhanced mobile routes now:
- Check for `?team_id=` URL parameters
- Handle context switching automatically
- Pass team selector data to templates
- Support both URL-based and session-based context

Example implementation:
```python
@mobile_bp.route("/mobile/my-team")
@login_required 
def serve_mobile_my_team():
    user = session["user"]
    
    # Handle URL-based team switching
    requested_team_id = request.args.get('team_id')
    if requested_team_id:
        success, message = ContextService.handle_url_context_switch(
            user["id"], {"team_id": requested_team_id}
        )
        if success:
            # Update session and continue
            enhanced_session = ContextService.create_enhanced_session_data(
                user, user["id"]
            )
            session["user"] = enhanced_session
            session.modified = True
    
    # Get data for current context
    team_data = get_team_data_for_context(user)
    
    return render_template("mobile/my_team.html", 
                         session_data={"user": user},
                         team_data=team_data,
                         user_teams=user.get("user_teams", []),
                         current_team_info=user.get("context"))
```

## Multi-League & Multi-Team Scenarios

### **Scenario 1: User in Multiple Leagues**
- **Example**: Player in both APTA Chicago and NSTF
- **Behavior**: Can switch between leagues, sees data filtered by active league
- **UI**: League selector appears when multiple leagues detected

### **Scenario 2: User on Multiple Teams in Same League**
- **Example**: Rob Werman on both Glenbrook RC and Tennaqua teams in APTA Chicago
- **Behavior**: Can switch between teams, sees team-specific data
- **UI**: Team selector appears when multiple teams detected

### **Scenario 3: User in Multiple Leagues with Multiple Teams Each**
- **Example**: Player in APTA (2 teams) and NSTF (1 team)
- **Behavior**: League switch also updates available teams, maintains context consistency
- **UI**: Both league and team selectors available, with intelligent defaults

## Registration Experience

### **Enhanced Registration Process**

1. **User Provides Info**: Basic info + league/club/series (optional)
2. **Comprehensive Search**: System finds ALL possible player matches across leagues
3. **Association Creation**: Creates associations for all high-confidence matches
4. **Team Assignment**: Ensures all players have team assignments
5. **Context Setup**: Automatically selects best initial context
6. **Session Creation**: Enhanced session with full multi-league support

### **Registration Success Scenarios**

**Single League User:**
- Finds 1 player association
- Sets context automatically
- Standard experience

**Multi-League User:**
- Finds multiple player associations (e.g., APTA + NSTF)
- Creates all associations
- Auto-selects context based on recent activity
- Can switch contexts immediately

**Multi-Team User:**
- Finds multiple teams in same league
- Creates all associations
- Auto-selects team with most recent matches
- Team selector appears for switching

## Login Experience

### **Login Flow**

1. **Authentication**: Standard email/password validation
2. **Association Loading**: Load ALL user's player associations
3. **Context Detection**: Auto-detect appropriate context based on:
   - Most recent team activity
   - Most recent login context
   - User preferences
4. **Session Creation**: Enhanced session with full context support
5. **Redirect**: Redirect with context-appropriate defaults

### **First-Time Login**
- Context auto-detection based on team activity
- Onboarding hints for multi-league/team users
- Immediate access to all features

### **Returning User Login**
- Remembers last active context
- Seamless continuation of previous session
- No disruption to workflow

## API Endpoints

### **Context Management**

```
POST /api/switch-team-context
Body: {"team_id": 123} or {"league_id": 456}
Response: {"success": true, "context": {...}, "message": "Switched to Team Name"}

GET /api/user-context-info  
Response: {
    "success": true,
    "context": {...},
    "leagues": [...],
    "teams": [...],
    "is_multi_league": true,
    "is_multi_team": true
}
```

### **Enhanced Registration**

```python
# Use EnhancedRegistrationService instead of legacy register_user
from app.services.enhanced_registration_service import EnhancedRegistrationService

result = EnhancedRegistrationService.register_user_comprehensive(
    email="user@example.com",
    password="password",
    first_name="John",
    last_name="Doe",
    league_name="APTA Chicago",  # Optional
    club_name="Tennaqua",        # Optional  
    series_name="Series 7"       # Optional
)

# Result includes:
# - associations_count: Number of player associations created
# - teams_assigned_count: Number of teams assigned
# - context_set: Whether initial context was established
```

## Error Handling & Edge Cases

### **Bulletproof Design Considerations**

1. **Network Failures**: Graceful degradation, retry mechanisms
2. **Database Inconsistencies**: Validation and auto-repair
3. **Missing Associations**: Smart fallbacks and user guidance
4. **Session Corruption**: Auto-recovery from database context
5. **Permission Changes**: Real-time validation of team access

### **Common Edge Cases Handled**

- User loses access to current team → Auto-switch to available team
- Database context missing → Rebuild from associations
- Invalid team ID in URL → Ignore and use session context
- Multiple browser tabs → Consistent context across tabs
- Session expiry → Rebuild context on re-login

## Best Practices for Developers

### **Adding Team Switching to New Pages**

1. **Include the Component**:
   ```html
   {% include 'components/team_selector.html' %}
   ```

2. **Pass Required Data**:
   ```python
   user_teams = ContextService.get_user_teams(user_id)
   current_team_info = ContextService.get_context_info(user_id)
   ```

3. **Handle URL Parameters**:
   ```python
   requested_team_id = request.args.get('team_id')
   if requested_team_id:
       ContextService.handle_url_context_switch(user_id, {"team_id": requested_team_id})
   ```

4. **Filter Data by Context**:
   ```python
   # Always filter data by current team/league context
   context_info = ContextService.get_context_info(user_id)
   team_data = get_data_for_team(context_info["team_id"])
   ```

### **Database Query Patterns**

**Always filter by user's current context:**
```sql
-- Good: Context-aware query
SELECT * FROM matches m
JOIN teams t ON m.team_id = t.id
WHERE t.id = %s  -- Current team from context

-- Bad: Unfiltered query
SELECT * FROM matches m  -- Shows all data
```

**Join with user context when needed:**
```sql
SELECT m.*, t.team_name 
FROM matches m
JOIN teams t ON m.team_id = t.id
JOIN user_contexts uc ON t.id = uc.active_team_id
WHERE uc.user_id = %s
```

## Testing Guide

### **Test Scenarios**

1. **Single League User**
   - Registration with player linking
   - Login and data access
   - No team selector should appear

2. **Multi-League User**  
   - Registration creates multiple associations
   - League switching works correctly
   - Data filtering by league context

3. **Multi-Team User**
   - Team switching works correctly
   - Data filtering by team context
   - [Rob Werman scenario from memories][[memory:2232990979383223905]]

4. **Registration Edge Cases**
   - Name variations (Pete/Peter) [[memory:4675543734997784010]]
   - No matches found
   - Multiple high-confidence matches

### **Validation Checklist**

- [ ] Team switching component appears for multi-team users
- [ ] URL parameters work: `?team_id=123`
- [ ] Session persistence across page loads
- [ ] Data filtering by current context
- [ ] Error handling for invalid team IDs
- [ ] Performance: No N+1 queries [[memory:797153081277567227]]
- [ ] Security: Users can only access their teams

## Migration from Legacy System

### **Immediate Steps**

1. **Run Database Migration**: `migrations/add_user_context_table.sql`
2. **Update Session Creation**: Use enhanced `create_session_data()`
3. **Add Team Selectors**: Include component on relevant pages
4. **Update Registration**: Use `EnhancedRegistrationService`

### **Gradual Migration**

1. **Phase 1**: Core pages (my-team, track-byes-courts)
2. **Phase 2**: Analysis pages (analyze-me, team-schedule)
3. **Phase 3**: Administrative pages
4. **Phase 4**: Remove legacy primary association code

### **Backwards Compatibility**

- Legacy session format still supported
- Fallback mechanisms for missing context
- Gradual rollout possible per page

## Performance Considerations

- **Efficient Queries**: Context joins optimized with indexes
- **Caching**: Context info cached in session
- **Batch Operations**: Multiple associations created in single transaction
- **Lazy Loading**: Team/league lists loaded on demand

## Security Considerations

- **Access Validation**: Every context switch validates user permissions
- **SQL Injection**: All queries use parameterized statements  
- **Session Security**: Context changes invalidate potentially stale data
- **Audit Trail**: All context switches logged

## Future Enhancements

- **User Preferences**: Remember preferred context per page
- **Smart Defaults**: ML-based context prediction
- **League Notifications**: Cross-league activity alerts
- **Advanced Filtering**: Multi-team aggregate views
- **Mobile Optimization**: Improved touch interfaces

## Troubleshooting

### **Common Issues**

**Team selector not appearing:**
- Check `user_teams` has multiple teams
- Verify component included in template
- Check JavaScript console for errors

**Context not switching:**
- Verify user has access to requested team
- Check database user_contexts table
- Review browser network tab for API errors

**Data not filtering correctly:**
- Ensure queries use current context
- Check context info in session
- Verify team/league foreign keys

**Performance issues:**
- Check for N+1 queries in team data loading
- Verify database indexes on context tables
- Review query performance with EXPLAIN

This enhanced team switching system provides a robust, scalable solution for multi-league and multi-team users while maintaining backwards compatibility and excellent user experience. 