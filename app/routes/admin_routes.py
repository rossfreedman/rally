"""
Admin routes blueprint - handles all administration functionality
This module contains routes for user management, system administration, and user activity tracking.
"""

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, send_from_directory
from functools import wraps
import os
import sqlite3
from utils.auth import login_required
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from app.services.admin_service import (
    get_all_users, get_all_series_with_stats, update_user_info, 
    update_club_name, update_series_name, delete_user_by_email,
    get_user_activity_logs, is_user_admin, log_admin_action
)
import traceback

# Create admin blueprint
admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to check if user is an admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"=== ADMIN_REQUIRED CHECK ===")
        print(f"User in session: {'user' in session}")
        if 'user' in session:
            print(f"User email: {session['user']['email']}")
        
        if 'user' not in session:
            print("No user in session, redirecting to login")
            flash('Please log in first.', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            print(f"Checking admin status for: {session['user']['email']}")
            if not is_user_admin(session['user']['email']):
                print(f"User {session['user']['email']} is not admin, redirecting to index")
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('serve_index'))
                
            print("Admin check passed, proceeding to admin function")
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error checking admin status: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            flash('An error occurred while checking permissions.', 'error')
            return redirect(url_for('serve_index'))
            
    return decorated_function

@admin_bp.route('/admin')
@login_required
@admin_required
def serve_admin():
    """Serve the admin dashboard"""
    print(f"=== SERVE_ADMIN FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"User in session: {session.get('user', 'No user')}")
    
    log_user_activity(session['user']['email'], 'page_visit', page='admin')
    
    # Always use the mobile admin template since it's responsive and works on all devices
    print("Rendering mobile admin template (responsive design)")
    return render_template('mobile/admin.html', session_data={'user': session['user']})

@admin_bp.route('/admin/users')
@login_required
@admin_required
def serve_admin_users():
    """Serve the admin users management page"""
    print(f"=== SERVE_ADMIN_USERS FUNCTION CALLED ===")
    
    log_user_activity(session['user']['email'], 'page_visit', page='admin_users')
    
    # Always use the mobile admin template since it's responsive and works on all devices
    return render_template('mobile/admin_users.html', session_data={'user': session['user']})

@admin_bp.route('/admin/leagues')
@login_required
@admin_required
def serve_admin_leagues():
    """Serve the admin leagues management page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_leagues')
    
    return render_template('mobile/admin_leagues.html', session_data={'user': session['user']})

@admin_bp.route('/admin/clubs')
@login_required
@admin_required
def serve_admin_clubs():
    """Serve the admin clubs management page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_clubs')
    
    return render_template('mobile/admin_clubs.html', session_data={'user': session['user']})

@admin_bp.route('/admin/series')
@login_required
@admin_required
def serve_admin_series():
    """Serve the admin series management page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_series')
    
    return render_template('mobile/admin_series.html', session_data={'user': session['user']})

@admin_bp.route('/admin/etl')
@login_required
@admin_required
def serve_admin_etl():
    """Serve the admin ETL management page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_etl')
    
    return render_template('mobile/admin_etl.html', session_data={'user': session['user']})

@admin_bp.route('/admin/user-activity')
@login_required
@admin_required
def serve_admin_user_activity():
    """Serve the admin user activity page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_user_activity')
    return render_template('mobile/admin_user_activity.html', session_data={'user': session['user']})

@admin_bp.route('/api/admin/users')
@login_required
def get_admin_users():
    """Get all registered users with their club and series information"""
    try:
        users = get_all_users()
        return jsonify(users)
    except Exception as e:
        print(f"Error getting admin users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/series')
@login_required
def get_admin_series():
    """Get all active series with player counts and active clubs"""
    try:
        series = get_all_series_with_stats()
        return jsonify(series)
    except Exception as e:
        print(f"Error getting admin series: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/update-user', methods=['POST'])
@login_required
def update_user():
    """Update a user's information"""
    try:
        data = request.json
        email = data.get('email')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        club_name = data.get('club_name')
        series_name = data.get('series_name')
        
        if not all([email, first_name, last_name, club_name, series_name]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Use service layer to update user
        update_user_info(email, first_name, last_name, club_name, series_name, session['user']['email'])
        return jsonify({'status': 'success'})
            
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/update-club', methods=['POST'])
@login_required
def update_club():
    """Update a club's information"""
    try:
        data = request.json
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        if not all([old_name, new_name]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Use service layer to update club
        update_club_name(old_name, new_name)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating club: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/update-series', methods=['POST'])
@login_required
def update_series():
    """Update a series' information"""
    try:
        data = request.json
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        if not all([old_name, new_name]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Use service layer to update series
        update_series_name(old_name, new_name)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating series: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/delete-user', methods=['POST'])
@login_required
@admin_required
def delete_user():
    """Delete a user from the database"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Use service layer to delete user
        result = delete_user_by_email(email, session['user']['email'])
        return jsonify(result)
            
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/user-activity/<email>')
@login_required
def get_user_activity(email):
    """Get activity logs for a specific user"""
    try:
        # Use service layer to get user activity
        response_data = get_user_activity_logs(email)
        
        # Create response with cache-busting headers
        response = jsonify(response_data)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        print(f"Error getting user activity: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/user-activity')
@login_required
def user_activity():
    """Serve the user activity page"""
    print("\n=== Serving User Activity Page ===")
    print(f"User in session: {'user' in session}")
    print(f"Session contents: {session}")
    
    try:
        print("Attempting to log user activity page visit")
        log_user_activity(
            session['user']['email'],
            'page_visit',
            page='user_activity',
            details='Accessed user activity page'
        )
        print("Successfully logged user activity page visit")
    except Exception as e:
        print(f"Error logging user activity page visit: {str(e)}")
        print(traceback.format_exc())
    
    return send_from_directory('static', 'user-activity.html') 