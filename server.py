#!/usr/bin/env python3

"""
Rally Flask Application

This is the main server file for the Rally platform tennis management application.
Most routes have been moved to blueprints for better organization.
"""

import os
import sys
import json
import secrets
from datetime import timedelta, datetime
from flask import Flask, request, session, jsonify, redirect, send_from_directory, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
import logging

# Import database utilities
from database_config import test_db_connection
from database_utils import execute_query, execute_query_one, execute_update
from utils.auth import login_required
from utils.logging import log_user_activity

# Import blueprints
from app.routes.player_routes import player_bp
from app.routes.auth_routes import auth_bp
from app.routes.admin_routes import admin_bp
from app.routes.mobile_routes import mobile_bp
from app.routes.api_routes import api_bp

# Import act routes initialization
from routes.act import init_act_routes

# Run database migrations before starting the application
print("=== Running Database Migrations ===")
try:
    from run_migrations import run_all_migrations
    migration_success = run_all_migrations()
    if not migration_success:
        print("❌ Database migrations failed - application may not function correctly")
except Exception as e:
    print(f"Migration error: {e}")
    print("⚠️ Continuing with application startup...")

# Simple database connection test
print("=== Testing Database Connection ===")
try:
    success, error = test_db_connection()
    if success:
        print("Database connection successful!")
    else:
        print(f"Database connection warning: {error}")
except Exception as e:
    print(f"Database test error: {e}")

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Determine environment
is_development = os.environ.get('FLASK_ENV') == 'development'

# Register blueprints
app.register_blueprint(player_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(mobile_bp)
app.register_blueprint(api_bp)

# Initialize act routes (includes find-subs, availability, schedule, rally_ai, etc.)
init_act_routes(app)
print("✅ Act routes initialized - Find Sub, Availability, Schedule, Rally AI routes enabled")

# Set secret key
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Session config
app.config.update(
    SESSION_COOKIE_SECURE=not is_development,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    SESSION_COOKIE_NAME='rally_session',
    SESSION_COOKIE_PATH='/',
    SESSION_REFRESH_EACH_REQUEST=True
)

# Configure CORS
CORS(app, 
     resources={
         r"/api/*": {
             "origins": ["*"] if is_development else [
                 "https://*.up.railway.app",
                 "https://*.railway.app",
                 "https://lovetorally.com",
                 "https://www.lovetorally.com"
             ],
             "supports_credentials": True,
             "allow_headers": ["Content-Type", "X-Requested-With", "Authorization"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
         }
     },
     expose_headers=["Set-Cookie"])

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# ==========================================
# TEMPLATE FILTERS
# ==========================================

@app.template_filter('parse_date')
def parse_date(value):
    """
    Jinja2 filter to parse a date string or datetime.date into a datetime object.
    Handles multiple date formats.
    """
    from datetime import date
    
    if not value:
        return None
    
    # If already a datetime.date, convert to datetime with default time
    if isinstance(value, date):
        return datetime.combine(value, datetime.strptime('6:30 PM', '%I:%M %p').time())
    
    # If already a datetime, return as is
    if isinstance(value, datetime):
        return value
    
    # Try different date formats for strings
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d-%b-%y"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(str(value), fmt)
            # Add default time of 6:30 PM if not specified
            if dt.hour == 0 and dt.minute == 0:
                dt = dt.replace(hour=18, minute=30)
            return dt
        except ValueError:
            continue
    
    return None

@app.template_filter('pretty_date')
def pretty_date(value):
    """Format dates with day of week"""
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y']
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value
            
        # Format with day of week followed by date
        day_of_week = date_obj.strftime('%A')
        date_str = date_obj.strftime('%-m/%-d/%y')
        return f"{day_of_week} {date_str}"
    except Exception as e:
        print(f"Error formatting date: {e}")
        return value

@app.template_filter('strip_leading_zero')
def strip_leading_zero(value):
    """
    Removes leading zero from hour in a time string like '06:30 pm' -> '6:30 pm'
    """
    import re
    return re.sub(r'^0', '', value) if isinstance(value, str) else value

@app.template_filter('pretty_date_no_year')
def pretty_date_no_year(value):
    """Format dates for display without the year"""
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y']
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value
        
        # Format without year
        day_of_week = date_obj.strftime('%A')
        date_str = date_obj.strftime('%-m/%-d')
        return f"{day_of_week} {date_str}"
        
    except Exception as e:
        print(f"[PRETTY_DATE_NO_YEAR] Error formatting date: {e}")
        return str(value)

@app.template_filter('date_to_mmdd')
def date_to_mmdd(value):
    """Format dates as simple mm/dd"""
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y']
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value
        
        # Format as mm/dd
        return date_obj.strftime('%-m/%-d')
        
    except Exception as e:
        print(f"[DATE_TO_MMDD] Error formatting date: {e}")
        return str(value)

@app.template_filter('pretty_date_with_year')
def pretty_date_with_year(value):
    """Format dates as 'Tuesday 9/24/24'"""
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y']
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value
        
        # Format as "Tuesday 9/24/24"
        day_of_week = date_obj.strftime('%A')
        date_str = date_obj.strftime('%-m/%-d/%y')
        return f"{day_of_week} {date_str}"
        
    except Exception as e:
        print(f"[PRETTY_DATE_WITH_YEAR] Error formatting date: {e}")
        return str(value)

@app.before_request
def log_request_info():
    """Log information about each request"""
    print(f"\n=== Request Info ===")
    print(f"Path: {request.path}")
    print(f"Method: {request.method}")
    print(f"User in session: {'user' in session}")
    if 'user' in session:
        print(f"User email: {session['user']['email']}")
    print("===================\n")

# ==========================================
# CORE ROUTES (Essential routes that stay in server.py)
# ==========================================

@app.route('/')
def serve_index():
    """Serve the index page"""
    if 'user' not in session:
        return redirect('/login')
    return redirect('/mobile')

@app.route('/index.html')
def redirect_index_html():
    """Redirect index.html to mobile"""
    return redirect('/mobile')

@app.route('/contact-sub')
@login_required
def serve_contact_sub():
    """Serve the contact sub page"""
    return send_from_directory('static/components', 'contact-sub.html')

@app.route('/<path:path>')
@login_required
def serve_static(path):
    """Serve static files with authentication"""
    public_files = {
        'login.html', 'signup.html', 'forgot-password.html',
        'rally-logo.png', 'rally-icon.png', 'favicon.ico',
        'login.css', 'signup.css'
    }
    
    def is_public_file(file_path):
        filename = os.path.basename(file_path)
        return (filename in public_files or 
                file_path.startswith('css/') or 
                file_path.startswith('js/') or
                file_path.startswith('images/'))
    
    if is_public_file(path):
        return send_from_directory('.', path)
    
    if 'user' not in session:
        return redirect('/login')
    
    try:
        return send_from_directory('.', path)
    except FileNotFoundError:
        return "File not found", 404

@app.route('/static/components/<path:filename>')
def serve_component(filename):
    """Serve component files"""
    return send_from_directory('static/components', filename)

@app.route('/health')
def healthcheck():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Rally server is running',
        'blueprints_registered': [
            'player_routes', 'auth_routes', 'admin_routes', 
            'mobile_routes', 'api_routes', 'rally_ai_routes'
        ]
    })

@app.route('/player-detail/<player_name>')
@login_required
def serve_player_detail(player_name):
    """Serve the player detail page"""
    try:
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        
        log_user_activity(
            session['user']['email'], 
            'page_visit',
            page='player_detail',
            details=f'Viewed player detail for {player_name}'
        )
        
        return render_template('player_detail.html', 
                             player_name=player_name,
                             session_data=session_data)
    except Exception as e:
        print(f"Error serving player detail: {str(e)}")
        return f"Error loading player detail: {str(e)}", 500

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==========================================
# SERVER STARTUP
# ==========================================

if __name__ == '__main__':
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get('PORT', 8080))
    
    # Determine if we're in development or production
    is_development = os.environ.get('FLASK_ENV') == 'development'
    
    try:
        if is_development:
            print(f"🏓 Starting Rally server locally on port {port}")
            app.run(host='0.0.0.0', port=port, debug=True)
        else:
            print(f"🏓 Starting Rally server in production mode on port {port}")
            app.run(host='0.0.0.0', port=port, debug=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print("Address already in use")
            print(f"Port {port} is in use by another program. Either identify and stop that program, or start the server with a different port.")
        else:
            print(f"Failed to start server: {e}")
        sys.exit(1)
