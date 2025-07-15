# Pickup Games Notifications Implementation

## Overview

This implementation adds notifications for active pickup games where the user meets the criteria (PTI range, series requirements, club restrictions, etc.). The notifications appear on the mobile home page alongside other personalized notifications.

## Features

### 1. Smart Criteria Matching
The system checks if the user meets the pickup game criteria:
- **PTI Range**: User's PTI must fall within the game's `pti_low` to `pti_high` range
- **Series Requirements**: User's series must meet the game's series restrictions (if any)
- **Club Restrictions**: If `club_only` is true, user must be from the same club
- **Availability**: Game must have open spots (not full)
- **Participation**: User must not already be participating in the game

### 2. Notification Format
Each pickup game notification includes:
- **Title**: "🎾 Pickup Game Available"
- **Message**: Game description, date/time, and available spots
- **Call-to-Action**: "Join Game" button linking to `/mobile/pickup-games`
- **Priority**: 3 (medium priority in notification hierarchy)

### 3. Date/Time Formatting
- **Today**: Shows "Today at 6:30 PM"
- **Tomorrow**: Shows "Tomorrow at 6:30 PM"  
- **Future dates**: Shows "Monday, Jan 15 at 6:30 PM"

## Technical Implementation

### 1. New Function: `get_pickup_games_notifications()`

**Location**: `app/routes/api_routes.py` (lines 6676-6795)

**Parameters**:
- `user_id`: User's database ID
- `player_id`: User's tenniscores player ID
- `league_id`: User's league ID
- `team_id`: User's team ID

**Logic**:
1. Gets user's PTI and series information from database
2. Finds upcoming pickup games where user meets criteria
3. Formats notifications with game details and available slots
4. Returns list of notification objects

### 2. Integration with Notifications API

**Location**: `app/routes/api_routes.py` (lines 6120-6130)

The function is integrated into the main notifications API with priority 4 (after urgent matches, recent results, and polls, but before personal highlights).

### 3. Database Queries

**User Info Query**:
```sql
SELECT 
    p.pti as user_pti,
    p.series_id as user_series_id,
    s.name as user_series_name,
    c.name as user_club_name
FROM players p
LEFT JOIN series s ON p.series_id = s.id
LEFT JOIN clubs c ON p.club_id = c.id
WHERE p.tenniscores_player_id = %s
ORDER BY p.id DESC
LIMIT 1
```

**Pickup Games Query**:
```sql
SELECT 
    pg.id, pg.description, pg.game_date, pg.game_time,
    pg.players_requested, pg.pti_low, pg.pti_high,
    pg.series_low, pg.series_high, pg.club_only,
    COUNT(pgp.id) as current_participants
FROM pickup_games pg
LEFT JOIN pickup_game_participants pgp ON pg.id = pgp.pickup_game_id
WHERE (pg.game_date > %s) OR (pg.game_date = %s AND pg.game_time > %s)
AND pg.pti_low <= %s AND pg.pti_high >= %s
AND (
    (pg.series_low IS NULL AND pg.series_high IS NULL) OR
    (pg.series_low IS NOT NULL AND pg.series_low <= %s) OR
    (pg.series_high IS NOT NULL AND pg.series_high >= %s) OR
    (pg.series_low IS NOT NULL AND pg.series_high IS NOT NULL AND pg.series_low <= %s AND pg.series_high >= %s)
)
AND (
    pg.club_only = false OR 
    (pg.club_only = true AND EXISTS (
        SELECT 1 FROM players p2 
        WHERE p2.tenniscores_player_id = %s 
        AND p2.club_id = (
            SELECT club_id FROM players WHERE tenniscores_player_id = %s LIMIT 1
        )
    ))
)
AND NOT EXISTS (
    SELECT 1 FROM pickup_game_participants pgp2 
    WHERE pgp2.pickup_game_id = pg.id AND pgp2.user_id = %s
)
GROUP BY pg.id
HAVING COUNT(pgp.id) < pg.players_requested
ORDER BY pg.game_date ASC, pg.game_time ASC
LIMIT 3
```

## Testing

### Test Script: `scripts/test_pickup_games_notifications.py`

The test script verifies:
1. Pickup games tables exist
2. Users and players with PTI exist
3. Can create test pickup games
4. Notifications function works correctly
5. Proper cleanup of test data

**Test Results**:
```
✅ Pickup games notifications test completed successfully!
- Found 1 matching pickup games
- Notification: 🎾 Pickup Game Available - Test Pickup Game - Mixed Doubles - Tomorrow at 6:30 PM (4 spots left)
```

## Usage

### For Users
1. Users will see pickup game notifications on their mobile home page
2. Notifications appear when they meet the game criteria
3. Clicking "Join Game" takes them to the pickup games page
4. Notifications automatically update as games fill up or new games are created

### For Developers
1. The function is automatically called by the notifications API
2. No additional configuration needed
3. Notifications respect the existing priority system
4. Function handles edge cases (no PTI, no series, etc.)

## Future Enhancements

1. **Real-time Updates**: WebSocket notifications when new games are created
2. **Smart Filtering**: Learn user preferences and show more relevant games
3. **Game Recommendations**: Suggest games based on user's playing history
4. **Push Notifications**: Send push notifications for urgent games (last-minute spots)
5. **Game Reminders**: Remind users about games they've joined

## Database Schema

The implementation uses the existing `pickup_games` and `pickup_game_participants` tables:

**pickup_games**:
- `id`, `description`, `game_date`, `game_time`
- `players_requested`, `pti_low`, `pti_high`
- `series_low`, `series_high`, `club_only`
- `creator_user_id`, `created_at`, `updated_at`

**pickup_game_participants**:
- `id`, `pickup_game_id`, `user_id`, `joined_at`

## Error Handling

The function includes comprehensive error handling:
- Graceful handling of missing user PTI
- Safe handling of database connection issues
- Fallback behavior if pickup games tables don't exist
- Logging of errors for debugging

## Performance Considerations

- Queries are optimized with proper indexes
- Results are limited to 3 games per user
- Complex criteria matching is done in SQL for efficiency
- Function is called only when notifications are requested 