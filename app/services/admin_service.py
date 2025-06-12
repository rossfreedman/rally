"""
Admin service module - handles all admin-related business logic
This module provides functions for user management, club/series administration, and user activity tracking.
"""

import os
import sqlite3
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
import traceback

def get_all_users():
    """Get all registered users with their club and series information"""
    try:
        users = execute_query('''
            SELECT u.id, u.first_name, u.last_name, u.email, u.last_login,
                   c.name as club_name, s.name as series_name
            FROM users u
            LEFT JOIN clubs c ON u.club_id = c.id
            LEFT JOIN series s ON u.series_id = s.id
            ORDER BY u.last_name, u.first_name
        ''')
        return users
    except Exception as e:
        print(f"Error getting admin users: {str(e)}")
        raise e

def get_all_series_with_stats():
    """Get all active series with player counts and active clubs"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get series with player counts and active clubs
        cursor.execute('''
            SELECT s.name, COUNT(u.id) as player_count,
                   GROUP_CONCAT(DISTINCT c.name) as active_clubs
            FROM series s
            LEFT JOIN users u ON s.id = u.series_id
            LEFT JOIN clubs c ON u.club_id = c.id
            GROUP BY s.id
            ORDER BY s.name
        ''')
        
        series = []
        for row in cursor.fetchall():
            series.append({
                'name': row[0],
                'player_count': row[1],
                'active_clubs': row[2] or 'None'
            })
        
        conn.close()
        return series
    except Exception as e:
        print(f"Error getting admin series: {str(e)}")
        raise e

def update_user_info(email, first_name, last_name, club_name, series_name, admin_email):
    """Update a user's information with admin logging"""
    try:
        if not all([email, first_name, last_name, club_name, series_name]):
            raise ValueError('Missing required fields')
            
        # Log admin action
        log_user_activity(
            admin_email, 
            'admin_action', 
            action='update_user',
            details=f"Updated user: {email}"
        )
            
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get club and series IDs
            cursor.execute('SELECT id FROM clubs WHERE name = ?', (club_name,))
            club_result = cursor.fetchone()
            
            cursor.execute('SELECT id FROM series WHERE name = ?', (series_name,))
            series_result = cursor.fetchone()
            
            if not club_result or not series_result:
                raise ValueError('Club or series not found')
                
            club_id = club_result[0]
            series_id = series_result[0]
            
            # Update user
            cursor.execute('''
                UPDATE users 
                SET first_name = ?, last_name = ?, club_id = ?, series_id = ?
                WHERE email = ?
            ''', (first_name, last_name, club_id, series_id, email))
            
            conn.commit()
            return True
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        raise e

def update_club_name(old_name, new_name):
    """Update a club's name"""
    try:
        if not all([old_name, new_name]):
            raise ValueError('Missing required fields')
            
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update club name
        cursor.execute('UPDATE clubs SET name = ? WHERE name = ?', (new_name, old_name))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating club: {str(e)}")
        raise e

def update_series_name(old_name, new_name):
    """Update a series' name"""
    try:
        if not all([old_name, new_name]):
            raise ValueError('Missing required fields')
            
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update series name
        cursor.execute('UPDATE series SET name = ? WHERE name = ?', (new_name, old_name))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating series: {str(e)}")
        raise e

def delete_user_by_email(email, admin_email):
    """Delete a user and all related data from the database"""
    try:
        if not email:
            raise ValueError('Email is required')

        # Get user details for logging before deletion
        user = execute_query_one(
            "SELECT first_name, last_name FROM users WHERE email = %(email)s",
            {'email': email}
        )
        
        if not user:
            raise ValueError('User not found')

        # Delete user and related data
        execute_update("""
            DELETE FROM user_activity_logs WHERE user_email = %(email)s;
            DELETE FROM user_instructions WHERE user_email = %(email)s;
            DELETE FROM player_availability WHERE player_name = %(email)s;
            DELETE FROM users WHERE email = %(email)s;
        """, {'email': email})
        
        # Log the deletion
        log_user_activity(
            admin_email,
            'admin_action',
            action='delete_user',
            details=f"Deleted user: {user['first_name']} {user['last_name']} ({email})"
        )
        
        return {
            'status': 'success',
            'message': 'User deleted successfully',
            'deleted_user': f"{user['first_name']} {user['last_name']}"
        }
            
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        raise e

def get_user_activity_logs(email):
    """Get comprehensive activity logs for a specific user"""
    try:
        print(f"\n=== Getting Activity for User: {email} ===")
        
        # Get user details first
        print("Fetching user details...")
        user = execute_query_one(
            """
            SELECT first_name, last_name, email, last_login
            FROM users
            WHERE email = %(email)s
            """,
            {'email': email}
        )
        
        if not user:
            print(f"User not found: {email}")
            raise ValueError('User not found')
            
        print(f"Found user: {user['first_name']} {user['last_name']}")
            
        # Get activity logs with explicit timestamp ordering
        print("Fetching activity logs...")
        logs = execute_query(
            """
            SELECT id, activity_type, page, action, details, ip_address, 
                   timezone('America/Chicago', timestamp) as central_time
            FROM user_activity_logs
            WHERE user_email = %(email)s
            ORDER BY timestamp DESC, id DESC
            LIMIT 1000
            """,
            {'email': email}
        )
        
        print("\nMost recent activities:")
        for idx, log in enumerate(logs[:5]):  # Print details of 5 most recent activities
            print(f"ID: {log['id']}, Type: {log['activity_type']}, Time: {log['central_time']}")
        
        formatted_logs = [{
            'id': log['id'],
            'activity_type': log['activity_type'],
            'page': log['page'],
            'action': log['action'],
            'details': log['details'],
            'ip_address': log['ip_address'],
            'timestamp': log['central_time'].isoformat()  # Format timestamp as ISO string
        } for log in logs]
        
        print(f"\nFound {len(formatted_logs)} activity logs")
        if formatted_logs:
            print(f"Most recent log ID: {formatted_logs[0]['id']}")
            print(f"Most recent timestamp: {formatted_logs[0]['timestamp']}")
        
        response_data = {
            'user': {
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'email': user['email'],
                'last_login': user['last_login']
            },
            'activities': formatted_logs
        }
        
        print("Returning response data")
        print("=== End Activity Request ===\n")
        
        return response_data
        
    except Exception as e:
        print(f"Error getting user activity: {str(e)}")
        print(traceback.format_exc())
        raise e

def is_user_admin(user_email):
    """Check if a user has admin privileges"""
    try:
        user = execute_query_one(
            "SELECT id, email, is_admin FROM users WHERE email = %(email)s",
            {'email': user_email}
        )
        
        if not user:
            return False
            
        # Check the is_admin column from the database
        return bool(user.get('is_admin', False))
        
    except Exception as e:
        print(f"Error checking admin status: {str(e)}")
        return False

def log_admin_action(admin_email, action, details):
    """Log an admin action for audit purposes"""
    try:
        return log_user_activity(
            admin_email,
            'admin_action',
            action=action,
            details=details
        )
    except Exception as e:
        print(f"Error logging admin action: {str(e)}")
        return False 