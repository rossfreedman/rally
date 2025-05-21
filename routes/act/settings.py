from flask import jsonify, request, session
from database import get_db
import logging
import json
from .auth import login_required

logger = logging.getLogger(__name__)

def init_routes(app):
    @app.route('/api/get-user-settings')
    @login_required
    def get_user_settings():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_email = session['user']['email']
            
            # Connect to database
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Get user settings
                cursor.execute('''
                    SELECT settings
                    FROM users 
                    WHERE email = %s
                ''', (user_email,))
                
                result = cursor.fetchone()
            
            if not result:
                return jsonify({'error': 'User not found'}), 404
                
            settings = result[0] if result[0] else '{}'
            return jsonify({'settings': json.loads(settings)})
            
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
            
            # Validate settings data
            if not isinstance(data, dict):
                return jsonify({'error': 'Invalid settings format'}), 400
            
            # Connect to database
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Update user settings
                cursor.execute('''
                    UPDATE users 
                    SET settings = %s
                    WHERE email = %s
                ''', (json.dumps(data), user_email))
                
                conn.commit()
            
            # Update session
            session['user']['settings'] = json.dumps(data)
            
            return jsonify({'message': 'Settings updated successfully'})
            
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
            
            # Connect to database
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Update user series
                cursor.execute('''
                    UPDATE users 
                    SET series = %s
                    WHERE email = %s
                ''', (series, user_email))
                
                conn.commit()
            
            # Update session
            session['user']['series'] = series
            
            return jsonify({'message': 'Series updated successfully'})
            
        except Exception as e:
            logger.error(f"Error updating series: {str(e)}")
            return jsonify({'error': 'Failed to update series'}), 500

    @app.route('/api/get-series')
    def get_series():
        try:
            if 'user' in session and 'series' in session['user']:
                return jsonify({'series': session['user']['series']})
            return jsonify({'error': 'Series not set'}), 404
            
        except Exception as e:
            logger.error(f"Error getting series: {str(e)}")
            return jsonify({'error': 'Failed to get series'}), 500

    return app 