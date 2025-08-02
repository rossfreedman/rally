# Pickup Games SMS Notifications Implementation

## Overview

Successfully implemented comprehensive SMS notifications for pickup game join/leave events using the existing Twilio notification infrastructure.

## Features Implemented

### 1. Join Notifications
- **User joins pickup game**: Sends confirmation SMS to the joining user
- **Other participants notified**: All existing participants receive SMS notification about the new player
- **Message includes**: Player name, game details, current player count

### 2. Leave Notifications  
- **User leaves pickup game**: All remaining participants receive SMS notification
- **Message includes**: Player name who left, game details, updated player count

### 3. Confirmation Messages
- **Join confirmation**: User who joined receives confirmation SMS with game details
- **Leave confirmation**: User who left receives confirmation SMS with game details
- **Future notifications**: Informs user they'll be notified of other join/leave events

## Technical Implementation

### New Functions Added to `app/services/notifications_service.py`

1. **`send_pickup_game_join_notifications(game_id, joining_user_id, joining_user_name)`**
   - Notifies all other participants when someone joins
   - Excludes the joining user from notifications
   - Handles users without phone numbers gracefully

2. **`send_pickup_game_leave_notifications(game_id, leaving_user_id, leaving_user_name)`**
   - Notifies all remaining participants when someone leaves
   - Handles users without phone numbers gracefully

3. **`send_pickup_game_join_confirmation(user_id, game_id)`**
   - Sends confirmation SMS to the user who just joined
   - Includes game details and notification expectations

4. **`send_pickup_game_leave_confirmation(user_id, game_id)`**
   - Sends confirmation SMS to the user who just left
   - Includes game details and current player count

### Modified API Routes

1. **`/api/pickup-games/<game_id>/join`** (`app/routes/api_routes.py`)
   - Added SMS notification calls after successful join
   - Sends notifications to other participants
   - Sends confirmation to joining user
   - Non-blocking: join operation succeeds even if notifications fail

2. **`/api/pickup-games/<game_id>/leave`** (`app/routes/api_routes.py`)
   - Added SMS notification calls after successful leave
   - Sends notifications to remaining participants
   - Sends confirmation to the leaving user
   - Non-blocking: leave operation succeeds even if notifications fail

## Message Format

### Join Notification (to other participants)
```
🎾 Rally Pickup Game Update:

[Player Name] just joined this pickup game:

"[Game Description]" on [Date] at [Time].

Current players: [X]/[Y]

Click here to view the game: https://www.lovetorally.com/mobile/pickup-games
```

### Leave Notification (to remaining participants)
```
🎾 Rally Pickup Game Update:

[Player Name] just left this pickup game:

"[Game Description]" on [Date] at [Time].

Current players: [X]/[Y]

Click here to view the game: https://www.lovetorally.com/mobile/pickup-games
```

### Join Confirmation (to joining user)
```
🎾 Rally Pickup Game Confirmation:

You've successfully joined this pickup game:

"[Game Description]" on [Date] at [Time].

Current players: [X]/[Y]

Click here to view the game: https://www.lovetorally.com/mobile/pickup-games

You'll be notified when other players join or leave.
```

### Leave Confirmation (to leaving user)
```
🎾 Rally Pickup Game Confirmation:

You've successfully left this pickup game:

"[Game Description]" on [Date] at [Time].

Current players: [X]/[Y]

Click here to view the game: https://www.lovetorally.com/mobile/pickup-games
```

## Error Handling

- **Graceful degradation**: Join/leave operations succeed even if SMS notifications fail
- **Missing phone numbers**: Users without phone numbers are skipped (logged but don't break the flow)
- **Twilio errors**: Uses existing retry logic for error 21704 (provider disruptions)
- **Database errors**: Proper exception handling with detailed logging

## Testing

Created comprehensive test script: `scripts/test_pickup_game_notifications.py`

### Test Results ✅
- ✅ Found 5 pickup games in database
- ✅ Found 5 users with phone numbers  
- ✅ Found 4 participants with phone numbers
- ✅ Join notifications working (notified 1 participant)
- ✅ Leave notifications working (notified 1 participant, sent actual SMS)
- ✅ Join confirmation working (sent actual SMS)
- ✅ SMS functionality working correctly

## Configuration Requirements

Uses existing Twilio configuration:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN` 
- `TWILIO_SENDER_PHONE`

## Database Requirements

Uses existing tables:
- `pickup_games` - Game details
- `pickup_game_participants` - Participant relationships
- `users` - User details including phone numbers
- `clubs` - Club information

## Usage

The system works automatically when users:
1. **Join a pickup game** via the mobile app or API
2. **Leave a pickup game** via the mobile app or API

No additional user action required - notifications are sent automatically.

## Benefits

1. **Real-time updates**: Players know immediately when someone joins/leaves
2. **Reduced coordination overhead**: No need for manual communication
3. **Better game planning**: Players can see current participation levels
4. **Improved user experience**: Automatic confirmations and updates
5. **Reliable delivery**: Uses proven Twilio infrastructure with retry logic

## Future Enhancements

Potential improvements:
- Notification preferences (opt-in/opt-out)
- Different message templates for different game types
- Integration with push notifications
- Game cancellation notifications
- Reminder notifications before game time 