"""
Notification Preferences Constants
===================================

Centralized definition of notification preference types and their defaults.
Used by API, settings page, and notification sending logic.
"""

# Notification preference keys
NOTIFICATION_TYPES = {
    "sub_requests": {
        "key": "sub_requests",
        "label": "Sub Requests",
        "description": "Receive texts when someone needs a substitute player",
        "default": True
    },
    "poll_results": {
        "key": "poll_results",
        "label": "Poll Results",
        "description": "Receive texts about team poll results and voting reminders",
        "default": True
    },
    "pickup_games": {
        "key": "pickup_games",
        "label": "Pickup Games",
        "description": "Receive texts about pickup game invitations and updates",
        "default": True
    },
    "captain_notifications": {
        "key": "captain_notifications",
        "label": "Captain Notifications",
        "description": "Receive texts from your team captain about matches and practices",
        "default": True
    }
}

# Default preferences (all enabled by default)
DEFAULT_NOTIFICATION_PREFS = {
    "sub_requests": True,
    "poll_results": True,
    "pickup_games": True,
    "captain_notifications": True
}

# Allowed preference keys for validation
ALLOWED_PREFERENCE_KEYS = set(NOTIFICATION_TYPES.keys())


def get_default_preferences():
    """
    Get default notification preferences
    
    Returns:
        Dict: Default preferences with all notifications enabled
    """
    return DEFAULT_NOTIFICATION_PREFS.copy()


def validate_preferences(prefs):
    """
    Validate notification preferences dictionary
    
    Args:
        prefs (dict): Preferences to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not isinstance(prefs, dict):
        return False, "Preferences must be a dictionary"
    
    # Check for invalid keys
    invalid_keys = set(prefs.keys()) - ALLOWED_PREFERENCE_KEYS
    if invalid_keys:
        return False, f"Invalid preference keys: {', '.join(invalid_keys)}"
    
    # Check that all values are boolean
    for key, value in prefs.items():
        if not isinstance(value, bool):
            return False, f"Preference '{key}' must be a boolean value"
    
    return True, ""


def get_preference_labels():
    """
    Get human-readable labels for all notification types
    
    Returns:
        Dict: Mapping of preference keys to their labels
    """
    return {key: info["label"] for key, info in NOTIFICATION_TYPES.items()}


def get_preference_descriptions():
    """
    Get descriptions for all notification types
    
    Returns:
        Dict: Mapping of preference keys to their descriptions
    """
    return {key: info["description"] for key, info in NOTIFICATION_TYPES.items()}

