# Sub Request SMS Selection Feature

## Summary
Added checkbox selection functionality to the create-sub-request page, allowing users to choose which specific subs to notify via SMS.

## Changes Made

### Frontend (templates/mobile/create_sub_request.html)

1. **Added Selection Controls UI**
   - Added checkbox column in the matching players table
   - Added "Select All" header checkbox
   - Added selection control bar showing count of selected players
   - Added "Select All" and "Select None" buttons

2. **JavaScript Functionality**
   - Store matching players array globally
   - Add checkboxes to each player row (default: checked)
   - Track selected player count in real-time
   - Implement select all/none functionality
   - Send selected player IDs in the API request

3. **Key Functions Added**
   - `updateSelectedCount()` - Updates the selected count display
   - `attachCheckboxListeners()` - Attaches change listeners to checkboxes
   - `getSelectedPlayerIds()` - Returns array of selected player IDs

### Backend (app/routes/api_routes.py)

1. **Updated `/api/subfinder` POST endpoint**
   - Accept `selected_player_ids` parameter from request
   - Query database for selected players with phone numbers
   - Send SMS notifications only to selected players
   - Format professional SMS message with date, time, location, notes
   - Return SMS results (sent/failed counts) in response

2. **SMS Message Format**
   ```
   🎾 Sub Request from [Requester Name]:
   
   Need a sub for [match/practice] at [club name]
   [Formatted Date] at [Formatted Time]
   
   [Optional Notes]
   
   View and respond: https://www.lovetorally.com/mobile/active-sub-requests
   ```

### Testing Mode Configuration

**IMPORTANT: Testing mode is already enabled by default**

- `RALLY_TESTING_MODE=true` in config.py (line 12)
- All SMS messages are automatically routed to admin phone during testing
- Admin phone: `+17732138911`
- SMS messages include original recipient for debugging: `[TEST - would send to {original_phone}]`

## How It Works

1. User fills out sub request form
2. Matching players are displayed in a table with checkboxes
3. By default, all players are selected (checked)
4. User can:
   - Click individual checkboxes to select/deselect
   - Click header checkbox to select/deselect all
   - Use "Select All" button to check all
   - Use "Select None" button to uncheck all
5. Selected count is displayed in blue banner
6. When submitted, only selected players receive SMS notifications
7. During testing, all SMS goes to admin phone only

## Security Features

- Testing mode prevents accidental SMS to real users
- Only players with valid phone numbers in database receive SMS
- SMS routing uses safe user_player_associations table
- Proper validation of selected player IDs

## Next Steps

1. Test locally with various selection scenarios
2. Verify SMS routing to admin phone during testing
3. Deploy to staging for testing
4. Once verified, deploy to production

## User Instructions for Testing

1. Go to http://127.0.0.1:8080/mobile/create-sub-request
2. Fill out the form fields
3. Observe matching players displayed with checkboxes (all checked by default)
4. Try the select all/none functionality
5. Submit the request
6. Only admin phone should receive SMS (testing mode active)

