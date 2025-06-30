# Automatic Session Refresh Solution

## Problem
Each time the ETL runs, it changes player IDs, league contexts, and other session-critical data in the database. This causes users to have stale session data until they manually refresh the page or re-login. Users don't know to do this after each background ETL run.

## Solution: Lazy Session Validation with Auto-Refresh

This solution automatically detects and refreshes stale sessions without requiring any user action.

### How It Works

1. **Session Versioning**: Each ETL run increments a `session_version` in the `system_settings` table
2. **Lazy Validation**: The `@login_required` decorator checks session validity on each page load
3. **Auto-Refresh**: Stale sessions are automatically refreshed from the database
4. **Fallback**: If refresh fails, users are gracefully redirected to login

### Components

#### 1. Enhanced `@login_required` Decorator (`utils/auth.py`)

```python
@login_required
def my_route():
    # Session is automatically validated and refreshed if needed
    # Users always see fresh data
```

**Features:**
- Validates session on every protected route access
- Automatically refreshes stale sessions
- Graceful fallback to re-login if refresh fails
- Minimal performance impact

#### 2. Session Version Tracking (`system_settings` table)

```sql
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO system_settings (key, value, description)
VALUES ('session_version', '1', 'Version number incremented after each ETL run');
```

#### 3. ETL Integration

The ETL script automatically increments the session version after successful completion:

```python
def increment_session_version(self, conn):
    """Increment session version to trigger automatic user session refresh"""
    # Updates session_version in system_settings
    # All user sessions become "stale" and will refresh on next page load
```

### Session Validation Logic

The system checks three conditions to determine if a session needs refreshing:

1. **Missing Required Fields**: `id`, `email`, `tenniscores_player_id`
2. **Version Mismatch**: Session version < current system version
3. **Data Validation**: Player/league references still exist in database

### User Experience

**Before (Manual):**
1. ETL runs in background
2. User continues browsing with stale data
3. User sees errors or wrong information
4. User must manually refresh or re-login

**After (Automatic):**
1. ETL runs in background and increments session version
2. User clicks to another page
3. System detects stale session automatically
4. Session refreshes from database seamlessly
5. User sees fresh, correct data
6. **No user action required!**

### Performance Impact

- **Minimal**: Only runs on page loads, not AJAX requests
- **Efficient**: Simple version number comparison
- **Cached**: Database lookup only when refresh needed
- **Graceful**: Doesn't block page loading

### Testing

Run the test script to see the system in action:

```bash
python scripts/test_session_refresh.py
```

This demonstrates:
- Session version tracking
- Stale session detection
- Automatic refresh behavior

### Benefits

✅ **Automatic**: No user action required  
✅ **Seamless**: Invisible to users  
✅ **Reliable**: Always shows fresh data after ETL  
✅ **Graceful**: Fallback to login if needed  
✅ **Efficient**: Minimal performance impact  
✅ **Bulletproof**: Handles edge cases and errors  

### Alternative Solutions Considered

1. **Manual User Notification**: Users wouldn't know when to refresh
2. **Forced Re-login**: Poor user experience
3. **WebSocket Notifications**: Complex, requires real-time infrastructure
4. **Session Invalidation**: Would log out all users during ETL
5. **Polling for Changes**: High server load

### ETL Integration

The solution is fully integrated into your ETL process:

```python
# In import_all_jsons_to_database.py
def run(self):
    # ... ETL process ...
    
    # CRITICAL: Increment session version to trigger user session refresh
    self.increment_session_version(conn)
    
    # Success! All user sessions will auto-refresh on next page load
```

### Monitoring

Check session version in database:

```sql
SELECT key, value, updated_at 
FROM system_settings 
WHERE key = 'session_version';
```

Monitor session refresh activity in application logs:

```
[INFO] Refreshing stale session for user: user@example.com
[INFO] Successfully refreshed session for user@example.com
```

### Maintenance

The system is self-maintaining:
- Session versions increment automatically with each ETL run
- No cleanup or maintenance required
- Table remains small (single row per setting)

### Security

- Session validation ensures users can only access their own data
- Failed refreshes trigger re-authentication
- No sensitive data exposed in version tracking
- Maintains all existing security measures 