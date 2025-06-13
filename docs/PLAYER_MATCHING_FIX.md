# Rally User-Player Association System

## Player Matching Fallback Logic

The Rally platform uses a progressive fallback strategy when matching users to tennis players in the database. This ensures maximum compatibility with name variations and incomplete data:

### 🎯 **Primary Search: Fuzzy First Name + Exact Match**
```
fuzzy_first_name + last_name + club + series + league
```
*First name uses fuzzy matching (handles "John" → "Jonathan"), other fields exact*

### 🔄 **Fallback 1: Series + Last Name**  
```
last_name + series + league
```
*Searches by surname and series within the league*

### 🔄 **Fallback 2: Club + Last Name**
```
last_name + club + league  
```
*Searches by surname and club within the league*

### 🔄 **Fallback 3: Last Name Only**
```
last_name + league
```
*Searches by surname only within the league*

### ✅ **Return Logic**
- **1 match found**: ✅ Return the player ID
- **Multiple matches**: ⚠️ Return first match with warning  
- **0 matches**: ❌ Return None

---

## Overview

The Rally platform uses a sophisticated user-player association system that connects authenticated users to their tennis player profiles in the database. This document describes how the system works, from registration through settings updates.

## Architecture

### Core Components

1. **Users Table**: Authentication data only (email, password, name)
2. **Players Table**: Tennis player data (rankings, stats, club/league info)
3. **User-Player Associations Table**: Many-to-many mapping between users and players
4. **Session Management**: User profile data with primary player information

### Key Tables

```sql
-- Users: Authentication only
users (
    id, email, password_hash, first_name, last_name, 
    is_admin, created_at, last_login
)

-- Players: Tennis player data
players (
    id, tenniscores_player_id, first_name, last_name,
    league_id, club_id, series_id, pti, wins, losses, etc.
)

-- User-Player Associations: Many-to-many mapping
user_player_associations (
    id, user_id, player_id, is_primary, created_at
)
```

## Registration Process

When a user registers with league/club/series information:

### Step 1: Create User Record
```python
new_user = User(
    email=email,
    password_hash=hashed_password,
    first_name=first_name,
    last_name=last_name
)
```

### Step 2: Player Lookup
If league/club/series provided, the system performs a database lookup:

```python
tenniscores_player_id = find_player_by_database_lookup(
    first_name=first_name,
    last_name=last_name,
    club_name=club_name,
    series_name=series_name,
    league_id=league_name
)
```

### Step 3: Create Association (if player found)
```python
if tenniscores_player_id:
    association = UserPlayerAssociation(
        user_id=new_user.id,
        player_id=player.id,
        is_primary=True
    )
```

### Step 4: Session Creation
Session includes player data for immediate use:
```python
session['user'] = {
    'id': user.id,
    'email': user.email,
    'first_name': user.first_name,
    'last_name': user.last_name,
    'club': primary_player.club.name,
    'series': primary_player.series.name,
    'league_id': primary_player.league.league_id,
    'league_name': primary_player.league.league_name,
    'tenniscores_player_id': primary_player.tenniscores_player_id,
    'is_admin': user.is_admin
}
```

## Settings Update Process

When a user updates their settings, the system intelligently handles player associations:

### Trigger Conditions for Player Lookup

The system performs a new player lookup when:

1. **Force Retry**: User explicitly requests a retry
2. **No Existing Player ID**: User doesn't have a `tenniscores_player_id`
3. **Settings Changed**: League, club, or series changed from current session

```python
settings_changed = (
    new_league_id != current_league_id or
    new_club != current_club or
    new_series != current_series
)

should_retry_player_id = (
    force_player_id_retry or 
    not current_player_id or
    settings_changed
)
```

### Association Management

When a new player is found:

1. **Unset Previous Primary**: Mark old associations as non-primary
2. **Create New Association**: If player not already associated
3. **Update Primary**: If association exists, make it primary
4. **Update Session**: Refresh all session data with new player info

```python
# Unset previous primary associations
db_session.query(UserPlayerAssociation).filter(
    UserPlayerAssociation.user_id == user_record.id,
    UserPlayerAssociation.is_primary == True
).update({'is_primary': False})

# Create new primary association
association = UserPlayerAssociation(
    user_id=user_record.id,
    player_id=player_record.id,
    is_primary=True
)
```

## Database Lookup Strategy

The `find_player_by_database_lookup()` function uses a progressive fallback strategy:

### Primary Search: Exact Match
```sql
SELECT tenniscores_player_id 
FROM players p
JOIN clubs c ON p.club_id = c.id  
JOIN series s ON p.series_id = s.id
WHERE p.league_id = %league_db_id% 
AND LOWER(TRIM(p.first_name)) = %first_name%
AND LOWER(TRIM(p.last_name)) = %last_name%  
AND LOWER(TRIM(c.name)) = %club_name%
AND LOWER(TRIM(s.name)) = %series_name%
```

### Fallback 1: Drop Club + First Name
```sql
-- Match: last_name + series + league
WHERE LOWER(TRIM(p.last_name)) = %last_name%
AND LOWER(TRIM(s.name)) = %series_name%
```

### Fallback 2: Drop Series + First Name  
```sql
-- Match: last_name + club + league
WHERE LOWER(TRIM(p.last_name)) = %last_name%
AND LOWER(TRIM(c.name)) = %club_name%
```

### Fallback 3: Last Name Only
```sql
-- Match: last_name + league
WHERE LOWER(TRIM(p.last_name)) = %last_name%
```

### Return Logic
- **1 match found**: Return the player ID
- **Multiple matches**: Return first match with warning
- **0 matches**: Return None

## Session Management

### Primary Player Concept
Each user can have multiple player associations, but only one "primary" player:
- **Primary Player**: Used for session data, default UI values
- **Secondary Players**: Available for selection, team associations

### Session Data Structure
```python
session['user'] = {
    # Basic user info
    'id': user.id,
    'email': user.email,
    'first_name': user.first_name,
    'last_name': user.last_name,
    'is_admin': user.is_admin,
    
    # Primary player info (for UI compatibility)
    'club': primary_player.club.name,
    'series': primary_player.series.name,
    'league_id': primary_player.league.league_id,
    'league_name': primary_player.league.league_name,
    'tenniscores_player_id': primary_player.tenniscores_player_id,
    
    # Legacy compatibility
    'settings': '{}',
    'club_automation_password': ''
}
```

## Alert System

The mobile layout shows an alert when:
```jinja2
{% if session_data and session_data.user and session_data.authenticated and not session_data.user.tenniscores_player_id %}
<!-- Alert: click here to update your profile -->
{% endif %}
```

**Alert appears when**: User has no `tenniscores_player_id` in session
**Alert disappears when**: User successfully associates with a player

## Examples

### Example 1: Successful Registration
User registers with:
- Name: Ross Freedman
- League: APTA Chicago  
- Club: Tennaqua
- Series: Chicago 22

**Result**: 
- User created in `users` table
- Player found: `nndz-WkMrK3didjlnUT09`
- Association created in `user_player_associations`
- Session includes `tenniscores_player_id`
- No alert shown

### Example 2: League Change in Settings
User changes from APTA Chicago to North Shore Tennis Foundation:
- **Current Session**: APTA Chicago / Tennaqua / Chicago 22
- **New Settings**: NSTF / Tennaqua / Series 2B

**Result**:
- Settings change detected
- New player lookup performed
- Different player found: `nndz-WlNhd3hMYi9nQT09`
- Old association marked non-primary
- New association created as primary
- Session updated with NSTF player data

### Example 3: No Player Match
User registers with data that doesn't match any player:

**Result**:
- User created in `users` table
- No player association created
- Session has `tenniscores_player_id: null`
- Alert shown prompting profile completion

## Multiple Players

A user can be associated with players in different leagues:

```sql
-- Example: User associated with players in APTA and NSTF
user_player_associations:
user_id=40, player_id=44859, is_primary=False  -- APTA player
user_id=40, player_id=43427, is_primary=True   -- NSTF player (primary)
```

The primary association determines session data and UI defaults.

## Troubleshooting

### Issue: Alert Still Appears After Registration
**Cause**: Player lookup failed during registration
**Check**: Log messages for lookup attempts
**Solution**: Update settings manually to retry lookup

### Issue: Wrong Player Associated
**Cause**: Multiple players with same name
**Check**: Database for duplicate players
**Solution**: Use more specific criteria or manual association

### Issue: Settings Update Doesn't Find Player
**Cause**: Database lookup strategy unsuccessful
**Check**: Player exists with exact criteria
**Solution**: Try fallback strategies manually

### Debugging Commands

```bash
# Check user associations
SELECT * FROM user_player_associations WHERE user_id = (
    SELECT id FROM users WHERE email = 'user@example.com'
);

# Check player details
SELECT p.*, c.name as club, s.name as series, l.league_name 
FROM players p 
JOIN clubs c ON p.club_id = c.id 
JOIN series s ON p.series_id = s.id 
JOIN leagues l ON p.league_id = l.id 
WHERE p.tenniscores_player_id = 'player_id';

# Test lookup manually
python -c "
from utils.database_player_lookup import find_player_by_database_lookup
result = find_player_by_database_lookup('First', 'Last', 'Club', 'Series', 'LEAGUE_ID')
print(f'Found: {result}')
"
```

## Files and Functions

### Key Files
- `app/services/auth_service_refactored.py` - Registration and authentication
- `app/routes/auth_routes.py` - Registration endpoints  
- `app/routes/api_routes.py` - Settings update endpoints
- `utils/database_player_lookup.py` - Player lookup logic
- `templates/mobile/layout.html` - Alert display logic

### Key Functions
- `register_user()` - Handle new user registration
- `update_settings()` - Handle profile updates
- `find_player_by_database_lookup()` - Core lookup logic
- `create_session_data()` - Session management
- `authenticate_user()` - Login with player data loading

## Migration Notes

This system replaced the legacy approach where user records directly contained foreign keys to league/club/series. The new architecture:

- ✅ Supports multiple player associations per user
- ✅ Uses pure database lookups (no JSON files)
- ✅ Provides consistent registration and settings update logic
- ✅ Maintains session compatibility with legacy code
- ✅ Enables proper user-player relationship management