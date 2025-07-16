# Notification Reorganization Summary

## Overview

Reorganized the notifications on both menu pages (`/mobile` and `/mobile/home_submenu`) to display in a specific order and added two new notification types.

## New Notification Order

The notifications now appear in this order:

1. **📢 Captain's Message** (Priority 1)
   - Shows messages from team captains
   - Uses calendar icon
   - Highest priority

2. **📅 Upcoming Schedule** (Priority 2)
   - Shows next practice and match information
   - Uses calendar with clock icon
   - Always included

3. **🏆 Team Position** (Priority 3) - **NEW**
   - Shows current team standings
   - Displays total points, average points per week, and points back from first place
   - Uses trophy icon
   - Links to `/mobile/my-series`

4. **📊 Team Poll** (Priority 4)
   - Shows latest team poll
   - Uses survey icon
   - Links to `/mobile/polls`

5. **🔥 My Win Streaks** (Priority 5) - **NEW**
   - Shows current player's win streak (3+ matches only)
   - Uses fire icon
   - Links to `/mobile/analyze-me`

6. **🎾 Pickup Games Available** (Priority 6)
   - Shows available pickup games matching user criteria
   - Uses tennis court icon
   - Links to `/mobile/pickup-games`

## Technical Implementation

### Backend Changes

**File**: `app/routes/api_routes.py`

1. **Modified `get_home_notifications()` function**:
   - Reorganized notification collection order
   - Added calls to new notification functions
   - Updated priority values
   - Increased limit from 4 to 6 notifications

2. **Added `get_team_position_notifications()` function**:
   - Queries `series_stats` table for team standings
   - Calculates team position, total points, average points per week
   - Determines points back from first place
   - Returns notification with trophy icon and team position data

3. **Added `get_my_win_streaks_notifications()` function**:
   - Uses same streak calculation logic as my-club page
   - Queries `match_scores` table for player's recent matches
   - Calculates current win streak using SQL window functions
   - Only shows notifications for streaks of 3+ matches
   - Returns notification with fire icon and streak information

4. **Updated existing notification priorities**:
   - Captain's Message: Priority 1 (was 2)
   - Upcoming Schedule: Priority 2 (was 0)
   - Team Poll: Priority 4 (was 2)
   - Pickup Games: Priority 6 (was 3)

### Frontend Changes

**Files**: `templates/mobile/index.html` and `templates/mobile/home_submenu.html`

1. **Updated `getNotificationIcon()` function**:
   - Added trophy icon for team position notifications
   - Added fire icon for win streak notifications
   - Updated icon mappings for personal and team notification types

2. **Enhanced notification titles**:
   - Added emojis to all notification titles for better visual distinction
   - Captain's Message: 📢
   - Upcoming Schedule: 📅
   - Team Position: 🏆
   - Team Poll: 📊
   - My Win Streaks: 🔥
   - Pickup Games: 🎾

## Database Queries

### Team Position Notifications
```sql
-- Get team standings information
SELECT 
    ss.team,
    ss.points,
    ss.matches_won,
    ss.matches_lost,
    ss.matches_tied,
    t.team_name,
    t.series_id,
    s.name as series_name,
    c.name as club_name
FROM series_stats ss
JOIN teams t ON ss.team_id = t.id
JOIN series s ON t.series_id = s.id
JOIN clubs c ON t.club_id = c.id
WHERE ss.team_id = %s 
AND ss.league_id = %s
ORDER BY ss.updated_at DESC
LIMIT 1
```

### Win Streak Notifications
```sql
-- Calculate current player's win streak
WITH match_results AS (
    SELECT 
        match_date,
        CASE 
            WHEN home_player_1_id = %s OR home_player_2_id = %s THEN 
                CASE WHEN winner = home_team THEN 'W' ELSE 'L' END
            ELSE 
                CASE WHEN winner = away_team THEN 'W' ELSE 'L' END
        END as result
    FROM match_scores 
    WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
    AND league_id = %s
    ORDER BY match_date DESC
),
streak_groups AS (
    SELECT 
        result,
        match_date,
        ROW_NUMBER() OVER (ORDER BY match_date DESC) as rn,
        ROW_NUMBER() OVER (PARTITION BY result ORDER BY match_date DESC) as streak_rn,
        ROW_NUMBER() OVER (ORDER BY match_date DESC) - 
        ROW_NUMBER() OVER (PARTITION BY result ORDER BY match_date DESC) as streak_group
    FROM match_results
),
current_streak AS (
    SELECT 
        result,
        COUNT(*) as streak_length
    FROM streak_groups 
    WHERE streak_group = 0
    GROUP BY result
    ORDER BY streak_length DESC
    LIMIT 1
)
SELECT * FROM current_streak
```

## Testing

Created test script: `scripts/test_new_notifications.py`

- Tests individual notification functions
- Verifies notification order
- Checks for syntax errors

## Benefits

1. **Better Organization**: Notifications now follow a logical priority order
2. **Enhanced Information**: Users get team position and personal win streak data
3. **Visual Distinction**: Emojis and icons make notifications easier to identify
4. **Consistent Experience**: Both menu pages show notifications in the same order
5. **Actionable Data**: Team position shows points back from first place
6. **Motivational**: Win streak notifications encourage continued performance

## Future Enhancements

1. **Notification Preferences**: Allow users to customize which notifications they see
2. **Dismiss Functionality**: Let users mark notifications as read
3. **Rich Media**: Add team logos or player photos to notifications
4. **Push Notifications**: Send urgent notifications to mobile devices
5. **Social Features**: Show teammate achievements and milestones 