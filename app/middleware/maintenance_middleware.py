"""
Maintenance Mode Middleware
==========================

Flask middleware to check for maintenance mode and display appropriate page
when ETL is running to prevent users from seeing inconsistent data.
"""

from flask import request, render_template, jsonify, current_app
from functools import wraps
from datetime import datetime
from database_utils import execute_query_one


class MaintenanceMode:
    """Maintenance mode checker and handler"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize maintenance mode with Flask app"""
        app.before_request(self.check_maintenance_mode)
    
    def is_maintenance_active(self):
        """Check if maintenance mode is currently active"""
        try:
            result = execute_query_one("""
                SELECT value FROM system_settings 
                WHERE key = 'maintenance_mode'
            """)
            return result and result['value'].lower() == 'true'
        except Exception:
            # If we can't check the database, assume not in maintenance
            return False
    
    def get_maintenance_info(self):
        """Get maintenance mode information for display"""
        try:
            # Get maintenance reason
            reason_result = execute_query_one("""
                SELECT value FROM system_settings 
                WHERE key = 'maintenance_reason'
            """)
            
            # Get maintenance ETA
            eta_result = execute_query_one("""
                SELECT value FROM system_settings 
                WHERE key = 'maintenance_eta'
            """)
            
            maintenance_info = {
                'reason': reason_result['value'] if reason_result else 'System maintenance in progress',
                'eta': None
            }
            
            if eta_result and eta_result['value']:
                try:
                    maintenance_info['eta'] = datetime.fromisoformat(eta_result['value'])
                except (ValueError, TypeError):
                    pass
            
            return maintenance_info
            
        except Exception:
            return {
                'reason': 'System maintenance in progress',
                'eta': None
            }
    
    def is_admin_bypass_allowed(self):
        """Check if current user is admin and can bypass maintenance mode"""
        try:
            # Check if user is authenticated and admin
            from flask import session
            user = session.get('user', {})
            return user.get('is_admin', False)
        except Exception:
            return False
    
    def should_bypass_maintenance(self):
        """Determine if current request should bypass maintenance mode"""
        # Allow certain paths even during maintenance
        bypass_paths = [
            '/static/',           # Static files
            '/maintenance',       # Maintenance page itself
            '/admin/disable-maintenance',  # Emergency disable endpoint
        ]
        
        # Check if path should be bypassed
        for bypass_path in bypass_paths:
            if request.path.startswith(bypass_path):
                return True
        
        # Check if admin user can bypass
        if self.is_admin_bypass_allowed():
            return True
        
        return False
    
    def check_maintenance_mode(self):
        """Before request handler to check maintenance mode"""
        # Skip maintenance check for certain paths
        if self.should_bypass_maintenance():
            return None
        
        # Check if maintenance mode is active
        if not self.is_maintenance_active():
            return None
        
        # Maintenance mode is active - show maintenance page
        maintenance_info = self.get_maintenance_info()
        
        # Handle API requests with JSON response
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Maintenance mode active',
                'message': maintenance_info['reason'],
                'eta': maintenance_info['eta'].isoformat() if maintenance_info['eta'] else None,
                'maintenance_mode': True
            }), 503
        
        # Handle regular requests with maintenance page
        try:
            return render_template('maintenance.html', 
                                 maintenance_reason=maintenance_info['reason'],
                                 maintenance_eta=maintenance_info['eta']), 503
        except Exception:
            # Fallback if template doesn't exist
            return self.get_fallback_maintenance_html(maintenance_info), 503
    
    def get_fallback_maintenance_html(self, maintenance_info):
        """Fallback maintenance page if template is missing"""
        eta_text = ""
        if maintenance_info['eta']:
            eta_text = f"<p>Estimated completion: {maintenance_info['eta'].strftime('%H:%M:%S')}</p>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rally - Maintenance Mode</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f5f5f5; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; }}
                .reason {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 Maintenance Mode</h1>
                <p>Rally is currently being updated with the latest match data.</p>
                <div class="reason">
                    <strong>{maintenance_info['reason']}</strong>
                    {eta_text}
                </div>
                <p>This page will refresh automatically every 30 seconds.</p>
                <p>Please check back in a few minutes.</p>
            </div>
        </body>
        </html>
        """


def requires_no_maintenance(f):
    """Decorator to ensure function only runs when not in maintenance mode"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        maintenance = MaintenanceMode()
        if maintenance.is_maintenance_active() and not maintenance.should_bypass_maintenance():
            maintenance_info = maintenance.get_maintenance_info()
            
            # Return JSON for API endpoints
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Maintenance mode active',
                    'message': maintenance_info['reason'],
                    'maintenance_mode': True
                }), 503
            
            # Redirect to maintenance page for regular requests
            try:
                return render_template('maintenance.html', 
                                     maintenance_reason=maintenance_info['reason'],
                                     maintenance_eta=maintenance_info['eta']), 503
            except Exception:
                return maintenance.get_fallback_maintenance_html(maintenance_info), 503
        
        return f(*args, **kwargs)
    return decorated_function 