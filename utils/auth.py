from functools import wraps
import logging
from datetime import datetime

from flask import jsonify, redirect, request, session, url_for

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to check if user is logged in and session is valid"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Not authenticated"}), 401
            return redirect(url_for("auth.login"))
        
        # ENHANCEMENT: Check if session needs refreshing after ETL
        if _session_needs_refresh(session):
            logger.info(f"Refreshing stale session for user: {session['user'].get('email', 'unknown')}")
            if not _refresh_session_from_db(session):
                # If refresh fails, force re-login
                session.clear()
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Session expired, please login again"}), 401
                return redirect(url_for("auth.login"))
        
        return f(*args, **kwargs)

    return decorated_function

def _session_needs_refresh(session):
    """Check if session data needs refreshing based on various indicators"""
    try:
        user = session.get("user", {})
        
        # Check 1: Missing required fields that should always be present
        # Note: tenniscores_player_id can be empty string for users without player associations
        core_required_fields = ["id", "email"]
        if not all(user.get(field) for field in core_required_fields):
            return True
        
        # Check that tenniscores_player_id exists (can be empty string)
        if "tenniscores_player_id" not in user:
            return True
            
        # Check 2: Check if session version exists and if ETL has run since
        session_version = session.get("session_version", 0)
        current_version = _get_current_session_version()
        if session_version < current_version:
            return True
            
        # Check 3: Validate that player/team IDs still exist in database (only if player ID exists)
        if user.get("tenniscores_player_id") and not _validate_session_data_exists(user):
            return True
            
        return False
        
    except Exception as e:
        logger.warning(f"Error checking session validity: {e}")
        return True  # Refresh on error to be safe

def _refresh_session_from_db(session):
    """Refresh session data from database"""
    try:
        from app.services.session_service import get_session_data_for_user
        
        user_email = session.get("user", {}).get("email")
        if not user_email:
            return False
            
        fresh_data = get_session_data_for_user(user_email)
        if fresh_data:
            session["user"] = fresh_data
            session["session_version"] = _get_current_session_version()
            session.modified = True
            logger.info(f"Successfully refreshed session for {user_email}")
            return True
        else:
            logger.warning(f"Could not refresh session data for {user_email}")
            return False
            
    except Exception as e:
        logger.error(f"Error refreshing session: {e}")
        return False

def _validate_session_data_exists(user):
    """Validate that session data references still exist in database"""
    try:
        from database_utils import execute_query_one
        
        tenniscores_player_id = user.get("tenniscores_player_id")
        league_id = user.get("league_id")
        
        # If no player ID, user doesn't have player associations - that's valid
        if not tenniscores_player_id:
            return True
            
        # If no league ID, skip database validation
        if not league_id:
            return True
            
        # Check if player still exists with this league
        result = execute_query_one(
            """
            SELECT 1 FROM players p 
            JOIN leagues l ON p.league_id = l.id 
            WHERE p.tenniscores_player_id = %s 
            AND l.id = %s 
            AND p.is_active = true
            """,
            [tenniscores_player_id, league_id]
        )
        
        return result is not None
        
    except Exception as e:
        logger.warning(f"Error validating session data: {e}")
        return True  # Return True on error to avoid unnecessary session refresh

def _get_current_session_version():
    """Get current session version from database or config"""
    try:
        from database_utils import execute_query_one
        
        # Check if we have a session_version table/setting
        result = execute_query_one(
            """
            SELECT value FROM system_settings 
            WHERE key = 'session_version' 
            LIMIT 1
            """,
            []
        )
        
        if result:
            return int(result.get("value", 1))
        else:
            # If no version tracking, use timestamp of last ETL run
            # You can enhance this by tracking ETL runs in a table
            return 1
            
    except Exception:
        # Fallback to basic version
        return 1
