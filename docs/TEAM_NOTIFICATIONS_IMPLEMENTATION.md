# Team Notifications Feature Implementation

## Overview

The Team Notifications feature allows team captains to send SMS notifications to their team members using predefined templates or custom messages. This feature is accessible through the Captain's Corner section of the mobile interface.

## Features Implemented

### 1. User Interface
- **New Page**: `/mobile/team-notifications` - Dedicated team notifications interface
- **Captain's Corner Button**: Added "Team Notifications" button to the mobile home page
- **Responsive Design**: Mobile-first design using Tailwind CSS and DaisyUI

### 2. Predefined Templates
Five predefined notification templates are available:

1. **Match Reminder** - Remind team about upcoming match
2. **Practice Reminder** - Remind team about practice session  
3. **Update Availability** - Ask team to update their availability
4. **Send a Poll** - Create a quick team poll
5. **Court Assignments** - Share court assignments with team

### 3. Custom Messages
- Text area for custom message composition
- Character counter (1600 character limit)
- Test mode toggle for validation without sending

### 4. Team Information Display
- Shows current team details (name, league, series)
- Displays member count and SMS recipient count
- Real-time refresh capability

### 5. SMS Integration
- Uses existing Twilio SMS infrastructure
- Sends to all team members with phone numbers
- Excludes sender from recipients
- Comprehensive error handling and retry logic

## Technical Implementation

### Routes Added
```python
# Page route
@admin_bp.route("/mobile/team-notifications")
def serve_team_notifications()

# API endpoints
@admin_bp.route("/api/team-notifications/team-info")
def get_team_notifications_team_info()

@admin_bp.route("/api/team-notifications/templates") 
def get_team_notification_templates()

@admin_bp.route("/api/team-notifications/send", methods=["POST"])
def send_team_notification()
```

### Files Modified

1. **`app/routes/admin_routes.py`**
   - Added team notifications page route
   - Added three API endpoints for team info, templates, and sending

2. **`app/services/notifications_service.py`**
   - Added `get_team_notification_templates()` function
   - Returns structured template objects with title, description, and message

3. **`templates/mobile/team_notifications.html`**
   - New template file for the team notifications interface
   - Responsive design with modern UI components
   - JavaScript for dynamic functionality

4. **`templates/mobile/index.html`**
   - Added "Team Notifications" button to Captain's Corner section

### Database Queries

The feature uses existing database structure:
- `teams` table for team information
- `users` table for member details and phone numbers
- `user_player_associations` for team membership
- `players` table for team relationships

### Security Features

- Authentication required for all endpoints
- User can only send to their own team members
- Sender is excluded from recipients
- Input validation and sanitization
- Activity logging for audit purposes

## Usage Instructions

### For Team Captains

1. **Access**: Navigate to the mobile interface and look for "Team Notifications" in the Captain's Corner section
2. **View Team Info**: See your team details and member count
3. **Use Templates**: Click on any predefined template to populate the message field
4. **Custom Messages**: Write your own message in the custom message section
5. **Test Mode**: Toggle test mode to validate without sending
6. **Send**: Click "Send to Team" to deliver the notification

### Template Customization

Templates can be modified in `app/services/notifications_service.py`:

```python
def get_team_notification_templates() -> Dict[str, Dict[str, str]]:
    return {
        "match_reminder": {
            "title": "Match Reminder",
            "description": "Remind team about upcoming match", 
            "message": "🏓 Match Reminder: Don't forget about tonight's match!..."
        },
        # Add more templates here
    }
```

## Testing

The feature has been tested and verified:
- ✅ Route registration works correctly
- ✅ Template loading functions properly
- ✅ API endpoints require authentication (security)
- ✅ SMS integration uses existing Twilio infrastructure
- ✅ Database queries work with current schema

## Future Enhancements

Potential improvements for future versions:

1. **Notification History**: Store sent notifications in database
2. **Scheduled Notifications**: Send notifications at specific times
3. **Recipient Selection**: Choose specific team members
4. **Template Management**: Allow captains to create custom templates
5. **Delivery Status**: Track SMS delivery status
6. **Rate Limiting**: Prevent spam notifications

## Dependencies

- Existing Twilio SMS infrastructure
- Current database schema (no migrations required)
- Tailwind CSS and DaisyUI for styling
- FontAwesome for icons

## Deployment Notes

- No database migrations required
- Uses existing Twilio configuration
- Compatible with current deployment setup
- No additional environment variables needed 