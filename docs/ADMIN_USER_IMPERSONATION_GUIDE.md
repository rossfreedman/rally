# Admin User Impersonation Feature

## Overview

The admin user impersonation feature allows administrators to temporarily simulate being logged in as any other user for testing and debugging purposes. This is essential for troubleshooting user-specific issues and understanding what different users see in their interface.

## 🔒 Security Features

- **Admin-only access**: Only users with `is_admin=True` can use this feature
- **No admin-to-admin impersonation**: Admins cannot impersonate other admins
- **Session backup**: Original admin session is safely backed up before impersonation
- **Comprehensive logging**: All impersonation actions are logged for audit purposes
- **Visual indicators**: Clear banners show when impersonation is active
- **Secure restoration**: Original admin session can always be restored

## 🎯 How to Use

### 1. Access the Admin Panel
- Log in as an admin user
- Navigate to `/admin`
- Look for the new "Testing & Debug" section at the top

### 2. Start Impersonation
1. In the "User Impersonation" section, select a user from the dropdown
   - The dropdown shows user names, emails, and player IDs
   - Only non-admin users are available for selection
2. Click "Start Impersonation"
3. Confirm the action in the dialog
4. The page will refresh and you'll see the user's view

### 3. While Impersonating
- **Orange banner**: A prominent orange banner appears on all pages showing who you're impersonating
- **User experience**: You see exactly what the impersonated user sees
- **All functionality**: You can navigate and use features as that user
- **Session data**: Their player ID, club, series, and permissions are active

### 4. Stop Impersonation
You can stop impersonation in two ways:
- **From admin panel**: Click "Stop Impersonation" in the admin interface
- **From any page**: Click "Stop" in the orange banner that appears on all pages

## 🔧 Technical Implementation

### New API Endpoints

#### `POST /api/admin/start-impersonation`
- **Purpose**: Start impersonating a user
- **Payload**: `{"user_email": "user@example.com"}`
- **Response**: Success/error message
- **Security**: Requires admin authentication

#### `POST /api/admin/stop-impersonation`
- **Purpose**: Stop impersonation and restore admin session
- **Payload**: None
- **Response**: Success/error message
- **Security**: Requires authentication

#### `GET /api/admin/impersonation-status`
- **Purpose**: Check if currently impersonating
- **Response**: Status and user details
- **Security**: Requires authentication

### Session Management

The impersonation system uses sophisticated session management:

```python
# During impersonation, session contains:
session["impersonation_active"] = True
session["original_admin_session"] = admin_backup
session["impersonated_user_email"] = target_email
session["user"] = target_user_session_data
```

### Visual Indicators

1. **Admin Panel Banner**: Shows on admin page when impersonating
2. **Global Banner**: Orange banner on all pages during impersonation
3. **User Context**: All data reflects the impersonated user's context

## 📋 Use Cases

### Debugging User Issues
- **Problem**: User reports they can't see their matches
- **Solution**: Impersonate them to see exactly what they see
- **Benefit**: Immediate understanding of their specific data/permissions

### Testing User Flows
- **Problem**: Need to test how a specific user type experiences the app
- **Solution**: Impersonate users with different club/league configurations
- **Benefit**: Test edge cases and specific user scenarios

### Data Verification
- **Problem**: User claims their stats are wrong
- **Solution**: Impersonate them to see their exact data calculations
- **Benefit**: Verify calculations and identify data issues

### Permission Testing
- **Problem**: Need to verify role-based access control
- **Solution**: Impersonate users with different permission levels
- **Benefit**: Ensure security and proper access restrictions

## ⚠️ Important Considerations

### Do's
✅ **Use for legitimate testing and debugging**
✅ **Stop impersonation when finished**
✅ **Keep impersonation sessions short**
✅ **Document any findings from impersonation**

### Don'ts
❌ **Don't perform actions that affect the user's data**
❌ **Don't leave impersonation sessions running**
❌ **Don't share impersonation access with non-admins**
❌ **Don't use for unauthorized access to user data**

## 🔄 Session Recovery

### Automatic Recovery
- If you log out while impersonating, the session is automatically cleared
- Browser refresh maintains impersonation state until manually stopped
- Server restart clears all sessions (normal behavior)

### Manual Recovery
If something goes wrong:
1. Clear browser cookies/session data
2. Log in again as admin
3. Impersonation state will be reset

## 📊 Logging and Audit

All impersonation actions are logged:
- **Start impersonation**: Who started, targeting whom, when
- **Stop impersonation**: Who stopped, when
- **Admin actions**: All actions taken while impersonating are marked
- **Audit trail**: Full visibility into admin access patterns

## 🧪 Testing

Use the included test script to verify functionality:

```bash
python scripts/test_admin_impersonation.py
```

This tests:
- API endpoint availability
- Authentication requirements
- Basic functionality

## 🚀 Future Enhancements

Potential improvements for future versions:
- **Time limits**: Auto-expire impersonation sessions
- **User notification**: Option to notify users of impersonation
- **Enhanced logging**: More detailed audit trails
- **Bulk testing**: Impersonate multiple users for batch testing

## 🛠️ Troubleshooting

### Common Issues

**Issue**: Can't see impersonation section
**Solution**: Ensure you're logged in as an admin user

**Issue**: "No users to impersonate" message
**Solution**: Ensure there are non-admin users in the system

**Issue**: Can't stop impersonation
**Solution**: Use the global orange banner "Stop" button on any page

**Issue**: Getting permission errors
**Solution**: Verify your user has `is_admin=True` in the database

### Support

If you encounter issues with the impersonation feature:
1. Check the server logs for error messages
2. Verify your admin status in the database
3. Clear browser session and try again
4. Use the test script to verify API functionality

## 🎉 Conclusion

The admin user impersonation feature provides a powerful and secure way to debug user issues and test the application from different user perspectives. With proper security controls and comprehensive logging, it's a valuable tool for maintaining and improving the Rally platform.

Remember to use this feature responsibly and always stop impersonation when finished! 