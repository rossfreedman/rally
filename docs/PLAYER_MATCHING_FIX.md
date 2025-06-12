# APTA Player Matching Fix - Registration vs Settings Update

## Issue Summary

**Problem**: User registration for APTA players was failing to find matches, while the same data in user settings updates was successfully finding matches.

**Example**: John Blume registered for APTA, Tennaqua, Chicago 22 - no match found during registration, but updating his profile in settings with the exact same data found Player ID: `nndz-WkMrK3dMNzVoQT09`.

## Root Cause

The issue was a **parameter order mismatch** between the registration route and the refactored authentication service:

### Legacy Function Signature:
```python
def register_user(email, password, first_name, last_name, club_name, series_name, league_id=None)
```

### New Refactored Function Signature:
```python  
def register_user(email, password, first_name, last_name, league_name=None, club_name=None, series_name=None, selected_player_id=None)
```

### Incorrect Route Call (Before Fix):
```python
# app/routes/auth_routes.py:40 - WRONG ORDER
result = register_user(email, password, first_name, last_name, club_name, series_name, league_id)
```

This caused:
- `club_name` ("Tennaqua") → passed as `league_name`
- `series_name` ("Chicago 22") → passed as `club_name` 
- `league_id` ("APTA_CHICAGO") → passed as `series_name`

## The Fix

### Corrected Route Call:
```python
# app/routes/auth_routes.py:40 - CORRECT ORDER
result = register_user(email, password, first_name, last_name, league_id, club_name, series_name)
```

## Why Settings Update Worked

The settings update flow (`/api/update-settings`) was correctly using the enhanced matching function `find_player_id_by_club_name()` with proper parameters, which includes these fallback strategies:

1. **PRIMARY**: first name + last name + series + club + league
2. **FALLBACK 1**: last name + series + league (drop club and first name)
3. **FALLBACK 2**: last name + series + club + league (drop first name only) ⭐
4. **FALLBACK 3**: last name + club + league (drop series and first name)

**FALLBACK 2** found the match for "John Blume" → "Jonathan Blume":
- Last name: "Blume" ✓
- Series: "Tennaqua - 22" ✓  
- Club: "Tennaqua" ✓
- League: "APTA_CHICAGO" ✓

## Verification

Jonathan Blume's player record in the database:
```json
{
  "League": "APTA_CHICAGO",
  "Series": "Chicago 22", 
  "Series Mapping ID": "Tennaqua - 22",
  "Club": "Tennaqua",
  "Location ID": "TENNAQUA",
  "Player ID": "nndz-WkMrK3dMNzVoQT09",
  "First Name": "Jonathan",
  "Last Name": "Blume",
  "PTI": "50.4",
  "Wins": "10",
  "Losses": "6",
  "Win %": "62.5%",
  "Captain": ""
}
```

Only one player with last name "Blume" exists in APTA_CHICAGO, ensuring unique fallback matches.

## Impact

This fix ensures that:
1. **Registration flow** now uses the same enhanced fallback matching as settings updates
2. **All APTA player matching** is consistent across the application  
3. **Name variations** (like John vs Jonathan) are properly handled during registration
4. **User onboarding** will correctly associate users with their player profiles from the start

## Testing

To verify the fix works:
1. Register a new user with known player data but slight name variation
2. Check that the correct Player ID is found and associated
3. Verify that the fallback matching logs show the progression through matching strategies

## Files Modified

- `app/routes/auth_routes.py` - Fixed parameter order in `register_user()` call 