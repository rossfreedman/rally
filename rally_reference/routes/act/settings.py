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
    # Route moved to api_routes.py blueprint

    # Route moved to api_routes.py blueprint

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