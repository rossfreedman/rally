"""
Temporary Password Middleware
============================

Flask middleware to enforce password change for users with temporary passwords.
Users with temporary passwords can only access the change-password page until they
set a permanent password.
"""

from flask import request, redirect, session, jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class TemporaryPasswordMiddleware:
    """Middleware to enforce password change for users with temporary passwords"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize temporary password middleware with Flask app"""
        app.before_request(self.check_temporary_password)
    
    def check_temporary_password(self):
        """Before request handler to check temporary password status"""
        # Debug logging
        print(f"[MIDDLEWARE_DEBUG] Checking path: {request.path}")
        print(f"[MIDDLEWARE_DEBUG] Session keys: {list(session.keys())}")
        
        # Skip check for unauthenticated users
        if "user" not in session:
            print(f"[MIDDLEWARE_DEBUG] No user in session, skipping check")
            return None
        
        # Skip check for certain paths that should always be accessible
        allowed_paths = [
            '/change-password',           # Change password page
            '/api/change-password',       # Change password API
            '/logout',                    # Logout
            '/api/logout',                # Logout API
            '/static/',                   # Static files
            '/images/',                   # Images
            '/css/',                      # CSS files
            '/js/',                       # JavaScript files
            '/favicon.ico',               # Favicon
            '/health',                    # Health check
            '/api/health',                # Health check API
        ]
        
        # Check if current path should be allowed
        for allowed_path in allowed_paths:
            if request.path.startswith(allowed_path):
                return None
        
        # Check if user has temporary password
        user_data = session.get("user", {})
        has_temporary_password = user_data.get("has_temporary_password", False)
        
        print(f"[MIDDLEWARE_DEBUG] User data keys: {list(user_data.keys())}")
        print(f"[MIDDLEWARE_DEBUG] has_temporary_password: {has_temporary_password}")
        print(f"[MIDDLEWARE_DEBUG] User email: {user_data.get('email', 'unknown')}")
        
        if has_temporary_password:
            logger.info(f"User {user_data.get('email', 'unknown')} with temporary password attempting to access {request.path} - redirecting to change password")
            
            # Handle API requests with JSON response
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Password change required',
                    'message': 'You must change your temporary password before accessing this feature',
                    'redirect': '/change-password',
                    'requires_password_change': True
                }), 403
            
            # Handle regular requests with redirect
            return redirect('/change-password')
        
        return None


def requires_permanent_password(f):
    """Decorator to ensure function only runs for users with permanent passwords"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Not authenticated"}), 401
            return redirect("/login")
        
        user_data = session.get("user", {})
        has_temporary_password = user_data.get("has_temporary_password", False)
        
        if has_temporary_password:
            logger.info(f"User {user_data.get('email', 'unknown')} with temporary password attempting to access {request.path}")
            
            # Return JSON for API endpoints
            if request.path.startswith("/api/"):
                return jsonify({
                    'error': 'Password change required',
                    'message': 'You must change your temporary password before accessing this feature',
                    'redirect': '/change-password',
                    'requires_password_change': True
                }), 403
            
            # Redirect for regular requests
            return redirect('/change-password')
        
        return f(*args, **kwargs)
    
    return decorated_function 