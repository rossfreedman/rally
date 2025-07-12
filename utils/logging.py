import json
import logging
import os
from datetime import datetime

from flask import request

logger = logging.getLogger(__name__)

# Ross Freedman's phone number for admin notifications
ADMIN_PHONE_NUMBER = "773-213-8911"


def log_user_activity(user_email, activity_type, **kwargs):
    """Log user activity to the database with enhanced SMS notifications"""
    try:
        # Extract common fields from kwargs
        page = kwargs.pop("page", None)
        action = kwargs.pop("action", None)
        details = kwargs.pop("details", None)

        # Check for impersonation in session (only if we're in a request context)
        is_impersonating = False
        if request:
            from flask import session
            is_impersonating = session.get("impersonating", False)

        # Prepare details for storage - handle complex objects
        details_json = None
        if details:
            try:
                details_json = json.dumps(details, default=str)
            except (TypeError, ValueError) as e:
                logger.warning(f"Could not serialize details for logging: {e}")
                details_json = str(details)

        # Store in database
        try:
            _log_to_database(
                user_email, activity_type, page, action, details_json, is_impersonating
            )
        except Exception as db_error:
            logger.error(f"Database logging failed: {db_error}")
            # Continue with SMS notification even if database fails

        # Check if detailed logging notifications are enabled and send SMS
        try:
            _send_detailed_logging_notification(
                user_email, activity_type, page, action, details, is_impersonating
            )
        except Exception as sms_error:
            logger.error(f"SMS notification failed: {sms_error}")

        return True

    except Exception as e:
        logger.error(f"Activity logging failed: {str(e)}")
        return False


def _log_to_database(user_email, activity_type, page, action, details_json, is_impersonating):
    """
    This is a private function called by log_user_activity
    """
    try:
        # Use the same database connection method as the rest of the app
        import psycopg2
        from database_config import get_db_url, parse_db_url
        
        params = parse_db_url(get_db_url())
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()

        # Get current timestamp
        current_time = datetime.now()

        # Insert activity log (using existing user_activity_logs table)
        cursor.execute(
            """
            INSERT INTO user_activity_logs (user_email, activity_type, page, action, details, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_email, activity_type, page, action, details_json, current_time),
        )

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Database logging error: {str(e)}")
        raise


def _send_detailed_logging_notification(user_email, activity_type, page, action, details, is_impersonating):
    """Send SMS notification if detailed logging notifications are enabled"""
    try:
        # Check if detailed logging notifications are enabled
        from app.services.admin_service import get_detailed_logging_notifications_setting
        
        if not get_detailed_logging_notifications_setting():
            return  # Feature is disabled, don't send SMS

        # Check if the user whose activity is being logged is an admin
        # Do not send activity tracking SMS for admin users
        if _is_user_admin(user_email):
            logger.info(f"Skipping activity tracking SMS for admin user: {user_email}")
            return

        # Import SMS service
        from app.services.notifications_service import send_sms_notification

        # Create a human-readable SMS message
        message = _format_activity_for_sms(user_email, activity_type, page, action, details, is_impersonating)

        # Send SMS to admin
        send_sms_notification(ADMIN_PHONE_NUMBER, message)
        
        logger.info(f"Detailed logging SMS sent for {user_email} - {activity_type}")

    except Exception as e:
        logger.error(f"Failed to send detailed logging SMS: {str(e)}")
        raise


def _is_user_admin(user_email):
    """Check if a user is an admin based on their email"""
    try:
        # Use the same database connection method as the rest of the app
        import psycopg2
        from database_config import get_db_url, parse_db_url
        
        params = parse_db_url(get_db_url())
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()

        # Check if user is admin
        cursor.execute(
            "SELECT is_admin FROM users WHERE email = %s",
            (user_email,)
        )
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return bool(result[0])  # result[0] is the is_admin column value
        else:
            # User not found, not an admin
            return False
            
    except Exception as e:
        logger.error(f"Error checking admin status for {user_email}: {str(e)}")
        # On error, assume not admin to err on the side of sending notifications
        return False


def _format_activity_for_sms(user_email, activity_type, page, action, details, is_impersonating):
    """Format user activity into a concise, readable SMS message"""
    
    # Start with basic info
    user_part = user_email.split('@')[0]  # Get username part
    impersonation_note = " [IMPERSONATED]" if is_impersonating else ""
    
    timestamp = datetime.now().strftime("%H:%M")
    base_message = f"🏓 Rally Activity ({timestamp})\n👤 {user_part}{impersonation_note}\n"
    
    # Format based on activity type
    if activity_type == "player_search":
        if action == "search_executed":
            query = details.get("search_query", "Unknown")
            results = details.get("results_count", 0)
            filters_applied = details.get("filters_applied", "")
            base_message += f"🔍 Searched: '{query}' → {results} results"
            if filters_applied:
                base_message += f"\n🧩 Filters: {filters_applied}"
            
            # Add top results if available
            if details.get("top_results"):
                top_names = details["top_results"][:2]  # Limit for SMS
                base_message += f"\n📋 Found: {', '.join(top_names)}"
                
        elif action == "groups_search":
            query = details.get("search_query", "Unknown")
            results = details.get("results_count", 0)
            base_message += f"👥 Groups search: '{query}' → {results} results"
            
        elif action == "find_people_to_play":
            filters = details.get("filters_used", {})
            results = details.get("results_count", 0)
            filter_summary = []
            
            if filters.get("first_name"): filter_summary.append(f"name:{filters['first_name']}")
            if filters.get("series"): filter_summary.append(f"series:{filters['series']}")
            if filters.get("pti_min") or filters.get("pti_max"): 
                filter_summary.append("PTI range")
            
            filter_text = ", ".join(filter_summary) if filter_summary else "no filters"
            base_message += f"🎾 Find players: {filter_text} → {results} results"
    
    elif activity_type == "team_switch":
        if action == "switch_team_context_success":
            from_team = details.get("from_context", {}).get("from_club", "Unknown")
            to_team = details.get("to_context", {}).get("club_name", "Unknown")
            base_message += f"🔄 Team switch: {from_team} → {to_team}"
            
        elif action == "switch_team_context_failed":
            to_team_id = details.get("to_team_id", "Unknown")
            base_message += f"❌ Team switch failed: attempted team ID {to_team_id}"
    
    elif activity_type == "settings_update":
        changes = details.get("changes_made", {})
        change_summary = []
        
        if changes.get("league_changed"): change_summary.append("league")
        if changes.get("club_changed"): change_summary.append("club")
        if changes.get("series_changed"): change_summary.append("series")
        if changes.get("player_lookup_successful"): change_summary.append("found player ID")
        
        if change_summary:
            base_message += f"⚙️ Settings: updated {', '.join(change_summary)}"
        else:
            base_message += f"⚙️ Settings: personal info updated"
    
    elif activity_type == "page_visit":
        if details:
            # If details is a dict, try to get a summary string
            if isinstance(details, dict):
                # Try to use a 'summary' or similar field, else fallback to str(details)
                summary = details.get('summary') or str(details)
                base_message += f"\U0001F4F1 {summary}"
            else:
                base_message += f"\U0001F4F1 {details}"
        else:
            page_name = page or "unknown"
            # Clean up page name for display
            clean_page = page_name.replace("mobile_", "").replace("_", " ").title()
            base_message += f"\U0001F4F1 Visited: {clean_page}"
    
    else:
        # Generic format for other activity types
        activity_name = activity_type.replace("_", " ").title()
        if action:
            action_name = action.replace("_", " ").title()
            base_message += f"🔧 {activity_name}: {action_name}"
        else:
            base_message += f"🔧 {activity_name}"
        
        # Add key details if available
        if details and isinstance(details, dict):
            if details.get("search_query"):
                base_message += f" ('{details['search_query']}')"
            elif details.get("results_count") is not None:
                base_message += f" ({details['results_count']} results)"

    # Ensure message isn't too long for SMS (160 chars is standard limit)
    if len(base_message) > 155:
        base_message = base_message[:152] + "..."
    
    return base_message


def get_user_activity(user_email):
    """Get user activity history"""
    try:
        # Use the same database connection method as the rest of the app
        import psycopg2
        from database_config import get_db_url, parse_db_url
        
        params = parse_db_url(get_db_url())
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()

        # Get activity logs
        cursor.execute(
            """
            SELECT activity_type, page, action, details, ip_address, timestamp
            FROM user_activity_logs
            WHERE user_email = %s
            ORDER BY timestamp DESC
            LIMIT 100
        """,
            (user_email,),
        )

        activities = []
        for row in cursor.fetchall():
            activity_type, page, action, details, ip_address, timestamp = row
            activities.append(
                {
                    "type": activity_type,
                    "page": page,
                    "action": action,
                    "details": details,
                    "ip_address": ip_address,
                    "timestamp": timestamp.isoformat() if timestamp else None,
                }
            )

        cursor.close()
        conn.close()
        return activities
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        return []
