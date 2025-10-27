# Notification Preferences Implementation

## Overview
This document describes the implementation of user notification preferences in Rally, allowing users to control which SMS notifications they receive.

## Implementation Date
October 27, 2025

## Feature Summary
Users can now manage their notification preferences through a new "Notifications" tab in the Settings page. The system supports four notification types:

1. **Sub Requests** - Receive texts when someone needs a substitute player
2. **Poll Results** - Receive texts about team poll results and voting reminders  
3. **Pickup Games** - Receive texts about pickup game invitations and updates
4. **Captain Notifications** - Receive texts from team captains about matches and practices

## Technical Architecture

### 1. Database Schema
- Added `notification_prefs` JSONB column to `users` table
- Default value: all preferences set to `true`
- Indexed with GIN for fast JSONB queries
- Migration file: `/data/dbschema/migrations/add_notification_prefs.sql`

### 2. Constants & Configuration
- `/app/constants/notification_preferences.py` - Central definition of notification types
- `/config.py` - Added `RALLY_TESTING_MODE` and `ADMIN_PHONE` configuration
- Environment variables:
  - `RALLY_TESTING_MODE` (default: `true`) - Routes all SMS to admin in testing
  - `ADMIN_PHONE` (default: `+17732138911`) - Admin phone for testing mode

### 3. API Endpoints
New blueprint: `/app/routes/notification_preferences_routes.py`

#### GET `/api/me/notification-preferences`
Returns current user's notification preferences and SMS status.

**Response:**
```json
{
  "success": true,
  "preferences": {
    "sub_requests": true,
    "poll_results": true,
    "pickup_games": true,
    "captain_notifications": true
  },
  "notification_types": [...],
  "sms_enabled": true,
  "phone_number": "***-***-8911"
}
```

#### PUT `/api/me/notification-preferences`
Updates user's notification preferences.

**Request:**
```json
{
  "preferences": {
    "sub_requests": true,
    "poll_results": false,
    "pickup_games": true,
    "captain_notifications": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Notification preferences updated successfully",
  "preferences": {...}
}
```

### 4. Testing Mode
**Critical Safety Feature**: When `RALLY_TESTING_MODE=true`, all SMS messages are automatically routed to the admin phone number (`ADMIN_PHONE`).

**Implementation:**
- Modified `/app/services/notifications_service.py`
- The `send_sms_notification()` function checks `RALLY_TESTING_MODE`
- If true, replaces recipient with admin phone and prepends context to message
- Logs clearly show: `🧪 TESTING MODE: Redirecting SMS from {original} to admin {admin_phone}`

**Testing Mode Message Format:**
```
[TEST - would send to +15551234567]

Your original message content here...
```

### 5. UI Integration
**Location:** `/templates/mobile/user_settings.html`

**Features:**
- Tab structure with "Profile" and "Notifications" tabs
- Toggle switches for each notification type
- Automatic disable when SMS not enabled (no phone number)
- Real-time save with success/error feedback
- Yellow warning banner if phone number not configured

**User Experience:**
1. User navigates to Settings → Notifications tab
2. System checks if user has phone number configured
3. If no phone: Shows warning + disables toggles + suggests adding phone
4. If phone configured: Shows 4 toggle switches for notification types
5. User toggles preferences and clicks Save
6. Success message displays for 3 seconds

### 6. Database Migration Steps

#### Local Development:
```bash
cd /Users/rossfreedman/dev/rally
psql -d rally -f data/dbschema/migrations/add_notification_prefs.sql
```

#### Staging Deployment:
```bash
python data/dbschema/dbschema_workflow.py --auto
```

#### Production Deployment:
```bash
python data/dbschema/dbschema_workflow.py --production
```

## File Changes Summary

### New Files:
1. `/data/dbschema/migrations/add_notification_prefs.sql` - Database migration
2. `/app/constants/notification_preferences.py` - Notification constants
3. `/app/constants/__init__.py` - Constants package init
4. `/app/routes/notification_preferences_routes.py` - API routes
5. `/md/NOTIFICATION_PREFERENCES_IMPLEMENTATION.md` - This documentation

### Modified Files:
1. `/config.py` - Added testing mode configuration
2. `/app/models/database_models.py` - Added notification_prefs column to User model
3. `/app/services/notifications_service.py` - Added testing mode routing
4. `/server.py` - Registered notification_prefs_bp blueprint
5. `/templates/mobile/user_settings.html` - Added Notifications tab with UI

## Testing Checklist

### Local Testing:
- [ ] Run migration successfully
- [ ] Navigate to Settings → Notifications tab
- [ ] Verify 4 toggle switches appear
- [ ] Toggle preferences and save
- [ ] Verify preferences persist after page reload
- [ ] Test with user who has no phone number (toggles should be disabled)
- [ ] Verify `RALLY_TESTING_MODE=true` routes SMS to admin phone

### Staging Testing:
- [ ] Deploy migration to staging
- [ ] Test UI on staging environment
- [ ] Send test SMS notification
- [ ] Verify admin receives redirected message
- [ ] Test with real user account

### Production Testing:
- [ ] Backup production database
- [ ] Deploy migration to production
- [ ] Verify no errors in logs
- [ ] Test with admin account first
- [ ] Gradually enable for all users

## Environment Variables

Add to `.env` file:
```bash
# Notification Testing Mode
RALLY_TESTING_MODE=true  # Set to false in production after testing
ADMIN_PHONE=+17732138911  # Ross's phone for testing
```

## Backward Compatibility
✅ **Fully backward compatible** - No breaking changes:
- New column has default values
- Existing code ignores new column
- Users without preferences get defaults
- SMS sending works with or without preferences

## Security Considerations
1. **Phone Number Privacy**: API masks phone numbers (shows last 4 digits)
2. **Authentication**: All routes require login
3. **Validation**: Strict validation of preference keys
4. **Testing Safety**: Testing mode prevents accidental SMS to users

## Future Enhancements
Potential future improvements:
1. Add notification type for league updates
2. Implement quiet hours (no notifications 10pm-8am)
3. Add notification history/log
4. Email notification preferences
5. Push notification support
6. Per-team notification settings

## Support & Troubleshooting

### Issue: Toggles are disabled
**Solution**: User needs to add phone number in Profile tab

### Issue: Preferences not saving
**Solution**: Check console for errors, verify API endpoints are registered

### Issue: SMS going to wrong number
**Solution**: Check `RALLY_TESTING_MODE` setting in environment

### Issue: Migration fails
**Solution**: Ensure PostgreSQL connection is working, column may already exist

## Deployment Notes
- **Zero Downtime**: Migration is non-blocking (uses IF NOT EXISTS)
- **Rollback Plan**: Drop column if needed: `ALTER TABLE users DROP COLUMN notification_prefs;`
- **Performance Impact**: Minimal - JSONB with GIN index is very efficient
- **Data Migration**: Not needed - defaults applied automatically

## Contact
For questions or issues with this implementation:
- Developer: AI Assistant via Cursor
- Date: October 27, 2025
- Project: Rally Platform Tennis Management

---

## Quick Start Commands

```bash
# Local: Run migration
psql -d rally -f data/dbschema/migrations/add_notification_prefs.sql

# Start server
python server.py

# Test the feature
# 1. Navigate to http://localhost:5000/mobile/settings
# 2. Click "Notifications" tab
# 3. Toggle preferences
# 4. Click Save
```

## API Testing with curl

```bash
# Get current preferences
curl -X GET http://localhost:5000/api/me/notification-preferences \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# Update preferences
curl -X PUT http://localhost:5000/api/me/notification-preferences \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"preferences": {"sub_requests": false, "poll_results": true, "pickup_games": true, "captain_notifications": true}}'
```

