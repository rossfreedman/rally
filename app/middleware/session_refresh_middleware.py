#!/usr/bin/env python3
"""
Session Refresh Middleware
==========================

This middleware automatically refreshes user sessions after ETL imports
when league IDs change, preventing users from experiencing broken league 
context and requiring manual logout/login or league switching.

Key Features:
- Automatically detects when user needs session refresh
- Refreshes session with updated league context from database
- Transparent to user (no manual intervention required)
- Only runs when refresh signals exist
- Efficient (only checks authenticated users)

Integration:
    # In app/__init__.py
    from app.middleware.session_refresh_middleware import SessionRefreshMiddleware
    SessionRefreshMiddleware(app)
"""

import logging
from flask import session, request, g
from typing import Optional

logger = logging.getLogger(__name__)

class SessionRefreshMiddleware:
    """Middleware for automatic session refresh after ETL imports"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self.check_and_refresh_session)
    
    def check_and_refresh_session(self):
        """
        Check if user's session needs refresh and update it automatically
        This runs before every request for authenticated users
        """
        try:
            # Only check for authenticated users
            if not session.get("user") or not session["user"].get("email"):
                return None
            
            user_email = session["user"]["email"]
            
            # Skip for API endpoints that might be called frequently
            if self._should_skip_refresh_check():
                return None
            
            # Check if user needs session refresh
            if self._should_refresh_session(user_email):
                refreshed_session = self._refresh_user_session(user_email)
                
                if refreshed_session:
                    # Update session with fresh data
                    session["user"] = refreshed_session
                    session.modified = True
                    
                    # Set flag to indicate session was refreshed (for logging/debugging)
                    g.session_refreshed = True
                    g.refresh_reason = "etl_league_id_change"
                    
                    logger.info(f"✅ Automatically refreshed session for {user_email}")
                else:
                    logger.warning(f"⚠️  Failed to refresh session for {user_email}")
            
            return None
            
        except Exception as e:
            # Never break the request flow due to refresh errors
            logger.error(f"Session refresh middleware error: {str(e)}")
            return None
    
    def _should_skip_refresh_check(self) -> bool:
        """
        Determine if we should skip refresh check for this request
        Skip for high-frequency API endpoints to avoid performance impact
        """
        # Skip for certain API endpoints
        skip_paths = [
            '/api/heartbeat',
            '/api/health',
            '/api/current-season-matches',
            '/api/team-current-season-matches',
            '/api/get-user-teams',  # Skip to prevent cursor conflicts
            '/api/get-user-teams-in-current-league',  # Skip to prevent cursor conflicts
            '/static/',
            '/favicon.ico',
            '/login',
            '/register',
            '/forgot-password',
            '/api/login',
            '/api/register',
            '/api/forgot-password'
        ]
        
        for skip_path in skip_paths:
            if request.path.startswith(skip_path):
                return True
        
        # Skip for AJAX requests that happen frequently
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Allow refresh on navigation requests but skip on frequent AJAX calls
            if request.path.startswith('/api/') and request.method == 'GET':
                return True
        
        return False
    
    def _should_refresh_session(self, user_email: str) -> bool:
        """Check if user's session should be refreshed"""
        try:
            from data.etl.database_import.session_refresh_service import SessionRefreshService
            return SessionRefreshService.should_refresh_session(user_email)
        except Exception as e:
            # Handle specific database errors gracefully
            if "cursor already closed" in str(e):
                logger.warning(f"Database cursor closed while checking refresh status for {user_email}")
                return False
            elif "connection" in str(e).lower():
                logger.error(f"Database connection error checking refresh status for {user_email}: {str(e)}")
                return False
            else:
                logger.error(f"Error checking refresh status: {str(e)}")
                return False
    
    def _refresh_user_session(self, user_email: str) -> Optional[dict]:
        """Refresh user's session with updated data"""
        try:
            from data.etl.database_import.session_refresh_service import SessionRefreshService
            return SessionRefreshService.refresh_user_session(user_email)
        except Exception as e:
            # Handle specific database errors gracefully
            if "cursor already closed" in str(e):
                logger.warning(f"Database cursor closed while refreshing session for {user_email}")
                return None
            elif "connection" in str(e).lower():
                logger.error(f"Database connection error refreshing session for {user_email}: {str(e)}")
                return None
            else:
                logger.error(f"Error refreshing session: {str(e)}")
                return None


def create_session_refresh_notification_banner():
    """
    Helper function to create a notification banner when session is refreshed
    Can be used in templates to inform users about the refresh
    """
    from flask import g
    
    if hasattr(g, 'session_refreshed') and g.session_refreshed:
        return {
            'show_banner': True,
            'message': 'Your session has been automatically updated with the latest league information.',
            'type': 'info',
            'dismissible': True
        }
    
    return {'show_banner': False}


# Template function registration helper
def register_template_functions(app):
    """Register template functions for session refresh notifications"""
    
    @app.context_processor
    def inject_session_refresh_status():
        """Make session refresh status available in all templates"""
        return {
            'session_refresh_notification': create_session_refresh_notification_banner()
        }


# Optional: Response header middleware to indicate session refresh
class SessionRefreshResponseMiddleware:
    """Additional middleware to add response headers indicating session refresh"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize response middleware"""
        app.after_request(self.add_refresh_headers)
    
    def add_refresh_headers(self, response):
        """Add headers to indicate if session was refreshed"""
        try:
            from flask import g
            
            if hasattr(g, 'session_refreshed') and g.session_refreshed:
                response.headers['X-Session-Refreshed'] = 'true'
                response.headers['X-Refresh-Reason'] = getattr(g, 'refresh_reason', 'unknown')
                
                # Optional: Add notification for JavaScript to handle
                if response.content_type and 'text/html' in response.content_type:
                    # Could inject a JavaScript notification here if needed
                    pass
            
            return response
            
        except Exception as e:
            logger.error(f"Error adding refresh headers: {str(e)}")
            return response 