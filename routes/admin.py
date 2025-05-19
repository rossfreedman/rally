from flask import Blueprint, jsonify, request, session
from functools import wraps
from utils.db import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from utils.auth import login_required

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to check if user is an admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            print("No user in session")
            return jsonify({'error': 'Not authenticated'}), 401
        
        # For now, we'll consider the first user (ID 1) as admin
        # TODO: Implement proper admin roles
        try:
            user = execute_query_one(
                "SELECT id, email FROM users WHERE email = %(email)s",
                {'email': session['user']['email']}
            )
            print(f"Admin check for user: {user}")
            
            if not user:
                print(f"No user found in database for email: {session['user']['email']}")
                return jsonify({'error': 'User not found'}), 404
                
            if user['id'] != 1:
                print(f"Non-admin user {user['email']} (ID: {user['id']}) attempted to access admin endpoint")
                return jsonify({'error': 'Unauthorized'}), 403
                
            print(f"Admin access granted to user {user['email']} (ID: {user['id']})")
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error checking admin status: {str(e)}")
            return jsonify({'error': 'Server error'}), 500
    return decorated_function

@admin_bp.route('/users')
@login_required
def get_users():
    """Get all users with their information"""
    try:
        users = execute_query("""
            SELECT u.id, u.email, u.first_name, u.last_name, 
                   u.last_login, c.name as club_name, s.name as series_name,
                   c.id as club_id, s.id as series_id
            FROM users u
            LEFT JOIN clubs c ON u.club_id = c.id
            LEFT JOIN series s ON u.series_id = s.id
            ORDER BY u.last_login DESC NULLS LAST
        """)
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/user-activity/<email>')
@login_required
def get_user_activity(email):
    """Get activity logs for a specific user"""
    try:
        logs = execute_query("""
            SELECT activity_type, page, action, details, 
                   ip_address, timestamp
            FROM user_activity_logs
            WHERE user_email = %(email)s
            ORDER BY timestamp DESC
            LIMIT 100
        """, {'email': email})
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/update-user', methods=['POST'])
@login_required
def update_user():
    """Update user information"""
    try:
        data = request.json
        result = execute_update("""
            UPDATE users 
            SET first_name = %(first_name)s,
                last_name = %(last_name)s,
                club_id = %(club_id)s,
                series_id = %(series_id)s
            WHERE id = %(id)s
            RETURNING id
        """, data)
        
        if result:
            log_user_activity(
                session['user']['email'],
                'admin_action',
                action='update_user',
                details=f"Updated user {data['email']}"
            )
            return jsonify({'status': 'success'})
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/clubs')
@login_required
def get_clubs():
    """Get all clubs"""
    try:
        clubs = execute_query("SELECT * FROM clubs ORDER BY name")
        return jsonify(clubs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/save-club', methods=['POST'])
@login_required
def save_club():
    """Add or update a club"""
    try:
        data = request.json
        if data.get('id'):
            result = execute_update("""
                UPDATE clubs 
                SET name = %(name)s
                WHERE id = %(id)s
                RETURNING id
            """, data)
        else:
            result = execute_update("""
                INSERT INTO clubs (name)
                VALUES (%(name)s)
                RETURNING id
            """, data)
        
        if result:
            log_user_activity(
                session['user']['email'],
                'admin_action',
                action='save_club',
                details=f"{'Updated' if data.get('id') else 'Added'} club {data['name']}"
            )
            return jsonify({'status': 'success', 'id': result[0]['id']})
        return jsonify({'error': 'Operation failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/delete-club/<int:club_id>', methods=['DELETE'])
@login_required
def delete_club(club_id):
    """Delete a club"""
    try:
        # Check if club is being used by any users
        users = execute_query(
            "SELECT COUNT(*) as count FROM users WHERE club_id = %(club_id)s",
            {'club_id': club_id}
        )
        if users[0]['count'] > 0:
            return jsonify({'error': 'Cannot delete club that has users assigned'}), 400

        result = execute_update(
            "DELETE FROM clubs WHERE id = %(club_id)s RETURNING id",
            {'club_id': club_id}
        )
        
        if result:
            log_user_activity(
                session['user']['email'],
                'admin_action',
                action='delete_club',
                details=f"Deleted club ID {club_id}"
            )
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Club not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/series')
@login_required
def get_series():
    """Get all series"""
    try:
        series = execute_query("SELECT * FROM series ORDER BY name")
        return jsonify(series)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/save-series', methods=['POST'])
@login_required
def save_series():
    """Add or update a series"""
    try:
        data = request.json
        if data.get('id'):
            result = execute_update("""
                UPDATE series 
                SET name = %(name)s
                WHERE id = %(id)s
                RETURNING id
            """, data)
        else:
            result = execute_update("""
                INSERT INTO series (name)
                VALUES (%(name)s)
                RETURNING id
            """, data)
        
        if result:
            log_user_activity(
                session['user']['email'],
                'admin_action',
                action='save_series',
                details=f"{'Updated' if data.get('id') else 'Added'} series {data['name']}"
            )
            return jsonify({'status': 'success', 'id': result[0]['id']})
        return jsonify({'error': 'Operation failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/delete-series/<int:series_id>', methods=['DELETE'])
@login_required
def delete_series(series_id):
    """Delete a series"""
    try:
        # Check if series is being used by any users
        users = execute_query(
            "SELECT COUNT(*) as count FROM users WHERE series_id = %(series_id)s",
            {'series_id': series_id}
        )
        if users[0]['count'] > 0:
            return jsonify({'error': 'Cannot delete series that has users assigned'}), 400

        result = execute_update(
            "DELETE FROM series WHERE id = %(series_id)s RETURNING id",
            {'series_id': series_id}
        )
        
        if result:
            log_user_activity(
                session['user']['email'],
                'admin_action',
                action='delete_series',
                details=f"Deleted series ID {series_id}"
            )
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Series not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500 