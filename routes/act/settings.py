from flask import jsonify, request, session
from database_utils import execute_query_one, execute_update
import logging
import json

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to check if user is logged in"""
    from functools import wraps
    from flask import session, jsonify, redirect, url_for, request
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Not authenticated'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_routes(app):
    @app.route('/api/get-user-settings')
    @login_required
    def get_user_settings():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_email = session['user']['email']
            
            # Get user data with club and series names
            user_data = execute_query_one('''
                SELECT u.first_name, u.last_name, u.email, u.club_automation_password,
                       c.name as club, s.name as series
                FROM users u
                LEFT JOIN clubs c ON u.club_id = c.id
                LEFT JOIN series s ON u.series_id = s.id
                WHERE u.email = %(email)s
            ''', {'email': user_email})
            
            if not user_data:
                return jsonify({'error': 'User not found'}), 404
                
            response_data = {
                'first_name': user_data['first_name'] or '',
                'last_name': user_data['last_name'] or '',
                'email': user_data['email'] or '',
                'club_automation_password': user_data['club_automation_password'] or '',
                'club': user_data['club'] or '',
                'series': user_data['series'] or ''
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error getting user settings: {str(e)}")
            return jsonify({'error': 'Failed to get user settings'}), 500

    @app.route('/api/update-settings', methods=['POST'])
    @login_required
    def update_settings():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            data = request.get_json()
            user_email = session['user']['email']
            
            # Validate required fields
            if not data.get('firstName') or not data.get('lastName') or not data.get('email'):
                return jsonify({'error': 'First name, last name, and email are required'}), 400
            
            # Get club_id and series_id from names
            club_id = None
            series_id = None
            
            if data.get('club'):
                club_result = execute_query_one('SELECT id FROM clubs WHERE name = %(club)s', {'club': data['club']})
                if club_result:
                    club_id = club_result['id']
            
            if data.get('series'):
                series_result = execute_query_one('SELECT id FROM series WHERE name = %(series)s', {'series': data['series']})
                if series_result:
                    series_id = series_result['id']
            
            # Update user data
            success = execute_update('''
                UPDATE users 
                SET first_name = %(first_name)s, last_name = %(last_name)s, email = %(email)s, 
                    club_id = %(club_id)s, series_id = %(series_id)s, club_automation_password = %(club_automation_password)s
                WHERE email = %(current_email)s
            ''', {
                'first_name': data['firstName'], 
                'last_name': data['lastName'], 
                'email': data['email'],
                'club_id': club_id,
                'series_id': series_id,
                'club_automation_password': data.get('clubAutomationPassword', ''),
                'current_email': user_email
            })
            
            if not success:
                return jsonify({'error': 'Failed to update user data'}), 500
            
            # Get updated user data to return and update session
            updated_user = execute_query_one('''
                SELECT u.first_name, u.last_name, u.email, u.club_automation_password,
                       c.name as club, s.name as series, u.is_admin
                FROM users u
                LEFT JOIN clubs c ON u.club_id = c.id
                LEFT JOIN series s ON u.series_id = s.id
                WHERE u.email = %(email)s
            ''', {'email': data['email']})  # Use new email in case it was changed
            
            if updated_user:
                # Update session with new user data
                session['user'] = {
                    'email': updated_user['email'],
                    'first_name': updated_user['first_name'],
                    'last_name': updated_user['last_name'],
                    'club': updated_user['club'],
                    'series': updated_user['series'],
                    'club_automation_password': updated_user['club_automation_password'],
                    'is_admin': updated_user['is_admin']
                }
                
                return jsonify({
                    'success': True,
                    'message': 'Settings updated successfully',
                    'user': session['user']
                })
            else:
                return jsonify({'error': 'Failed to retrieve updated user data'}), 500
            
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            return jsonify({'error': 'Failed to update settings'}), 500

    @app.route('/api/set-series', methods=['POST'])
    @login_required
    def set_series():
        try:
            data = request.get_json()
            series = data.get('series')
            
            if not series:
                return jsonify({'error': 'Series not provided'}), 400
                
            user_email = session['user']['email']
            
            # Get series_id from name
            series_result = execute_query_one('SELECT id FROM series WHERE name = %(series)s', {'series': series})
            if not series_result:
                return jsonify({'error': 'Series not found'}), 404
            
            series_id = series_result['id']
            
            # Update user series
            success = execute_update('''
                UPDATE users 
                SET series_id = %(series_id)s
                WHERE email = %(email)s
            ''', {'series_id': series_id, 'email': user_email})
            
            if not success:
                return jsonify({'error': 'Failed to update series'}), 500
            
            # Update session
            session['user']['series'] = series
            
            return jsonify({'message': 'Series updated successfully'})
            
        except Exception as e:
            logger.error(f"Error updating series: {str(e)}")
            return jsonify({'error': 'Failed to update series'}), 500

    @app.route('/api/get-series')
    def get_series():
        try:
            from database_utils import execute_query
            import re
            
            # Get all available series (unsorted)
            all_series_records = execute_query("SELECT name FROM series")
            
            # Extract series names and sort them numerically
            def extract_series_number(series_name):
                """Extract the numeric part from series name for sorting"""
                # Look for the first number in the series name
                match = re.search(r'(\d+)', series_name)
                if match:
                    return int(match.group(1))
                else:
                    # If no number found, put it at the end
                    return 9999
            
            # Sort series by the extracted number
            all_series_names = [record['name'] for record in all_series_records]
            all_series_sorted = sorted(all_series_names, key=extract_series_number)
            
            # Get user's current series
            current_series = None
            if 'user' in session and 'series' in session['user']:
                current_series = session['user']['series']
            
            return jsonify({
                'series': current_series,
                'all_series': all_series_sorted
            })
            
        except Exception as e:
            logger.error(f"Error getting series: {str(e)}")
            return jsonify({'error': 'Failed to get series'}), 500

    return app 