"""
Notification Preferences API Routes
====================================

API endpoints for managing user notification preferences.
"""

import logging
from flask import Blueprint, jsonify, request, session
from functools import wraps

from app.constants.notification_preferences import (
    NOTIFICATION_TYPES,
    DEFAULT_NOTIFICATION_PREFS,
    validate_preferences
)
from database_utils import execute_query_one, execute_query

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
notification_prefs_bp = Blueprint("notification_prefs", __name__)


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function


@notification_prefs_bp.route("/api/me/notification-preferences", methods=["GET"])
@login_required
def get_notification_preferences():
    """
    Get current user's notification preferences
    
    Returns:
        JSON response with:
        - preferences: Dict of notification preference settings
        - sms_enabled: Whether SMS is enabled for this user
        - phone_number: User's phone number (masked)
    """
    try:
        user_email = session["user"]["email"]
        
        # Get user's notification preferences and SMS status
        user_data = execute_query_one(
            """
            SELECT 
                notification_prefs,
                phone_number
            FROM users
            WHERE email = %s
            """,
            [user_email]
        )
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404
        
        # Parse notification preferences (default to all true if NULL)
        prefs = user_data.get("notification_prefs") or DEFAULT_NOTIFICATION_PREFS.copy()
        
        # Ensure all expected keys exist (backward compatibility)
        for key, default in DEFAULT_NOTIFICATION_PREFS.items():
            if key not in prefs:
                prefs[key] = default
        
        # Check if SMS is enabled (user has phone number)
        phone_number = user_data.get("phone_number")
        sms_enabled = bool(phone_number and phone_number.strip())
        
        # Mask phone number for privacy (show last 4 digits)
        masked_phone = None
        if phone_number:
            masked_phone = f"***-***-{phone_number[-4:]}" if len(phone_number) >= 4 else "***"
        
        # Get notification type metadata
        notification_types = []
        for key, info in NOTIFICATION_TYPES.items():
            notification_types.append({
                "key": key,
                "label": info["label"],
                "description": info["description"],
                "enabled": prefs.get(key, info["default"])
            })
        
        return jsonify({
            "success": True,
            "preferences": prefs,
            "notification_types": notification_types,
            "sms_enabled": sms_enabled,
            "phone_number": masked_phone
        })
        
    except Exception as e:
        logger.error(f"Error getting notification preferences: {str(e)}")
        return jsonify({"error": "Failed to get notification preferences"}), 500


@notification_prefs_bp.route("/api/me/notification-preferences", methods=["PUT"])
@login_required
def update_notification_preferences():
    """
    Update current user's notification preferences
    
    Request body:
        {
            "preferences": {
                "sub_requests": true,
                "poll_results": false,
                "pickup_games": true,
                "captain_notifications": true
            }
        }
    
    Returns:
        JSON response with updated preferences
    """
    try:
        user_email = session["user"]["email"]
        
        # Get request data
        data = request.get_json()
        if not data or "preferences" not in data:
            return jsonify({"error": "Missing 'preferences' in request body"}), 400
        
        new_prefs = data["preferences"]
        
        # Validate preferences
        is_valid, error_message = validate_preferences(new_prefs)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Get current preferences to merge with new ones
        user_data = execute_query_one(
            """
            SELECT notification_prefs
            FROM users
            WHERE email = %s
            """,
            [user_email]
        )
        
        if not user_data:
            return jsonify({"error": "User not found"}), 404
        
        # Merge new preferences with existing ones (allow partial updates)
        current_prefs = user_data.get("notification_prefs") or DEFAULT_NOTIFICATION_PREFS.copy()
        updated_prefs = {**current_prefs, **new_prefs}
        
        # Update database
        execute_query(
            """
            UPDATE users
            SET notification_prefs = %s::jsonb
            WHERE email = %s
            """,
            [str(updated_prefs).replace("'", '"').replace("True", "true").replace("False", "false"), user_email]
        )
        
        logger.info(f"Updated notification preferences for user {user_email}")
        
        return jsonify({
            "success": True,
            "message": "Notification preferences updated successfully",
            "preferences": updated_prefs
        })
        
    except Exception as e:
        logger.error(f"Error updating notification preferences: {str(e)}")
        return jsonify({"error": "Failed to update notification preferences"}), 500

