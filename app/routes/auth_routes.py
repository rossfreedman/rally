from flask import Blueprint, jsonify, request, session, redirect, url_for, render_template
import logging
from app.services.auth_service_refactored import register_user, authenticate_user, create_session_data, get_clubs_list

# Create Blueprint
auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Serve the login page"""
    if request.method == 'GET':
        return render_template('login.html')
    return jsonify({'error': 'Method not allowed'}), 405

@auth_bp.route('/api/register', methods=['POST'])
def handle_register():
    """Handle user registration"""
    try:
        data = request.get_json()
        email = data.get('email', '').lower()
        password = data.get('password', '')
        first_name = data.get('firstName', '')
        last_name = data.get('lastName', '')
        league_id = data.get('league', '')
        club_name = data.get('club', '')
        series_name = data.get('series', '')

        # Validate required fields
        if not all([email, password, first_name, last_name, league_id, club_name, series_name]):
            missing = []
            if not email: missing.append('email')
            if not password: missing.append('password')
            if not first_name: missing.append('firstName')
            if not last_name: missing.append('lastName')
            if not league_id: missing.append('league')
            if not club_name: missing.append('club')
            if not series_name: missing.append('series')
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

        # Use service to register user with league
        result = register_user(email, password, first_name, last_name, league_id, club_name, series_name)
        
        if not result['success']:
            if 'already exists' in result['error']:
                return jsonify({'error': result['error']}), 409
            else:
                return jsonify({'error': result['error']}), 500

        # Set session data using the refactored service that handles user_player_associations
        session['user'] = create_session_data(result['user'])
        session.permanent = True
        
        logger.info(f"Registration: Session created for user {email}")
        
        return jsonify({
            'status': 'success',
            'message': result['message'],
            'redirect': '/mobile'
        }), 201

    except Exception as e:
        logger.error(f"Registration endpoint error: {str(e)}")
        return jsonify({'error': 'Registration failed - server error'}), 500

@auth_bp.route('/api/login', methods=['POST'])
def handle_login():
    """Handle user login"""
    try:
        logger.info("Login attempt started")
        
        # Check if we can get JSON data
        try:
            data = request.get_json()
            logger.info("Successfully parsed JSON data")
        except Exception as json_error:
            logger.error(f"Failed to parse JSON: {json_error}")
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data received'}), 400
            
        email = data.get('email', '').lower()
        password = data.get('password', '')
        
        logger.info(f"Login attempt for email: {email}")

        if not email or not password:
            logger.warning("Missing email or password")
            return jsonify({'error': 'Missing email or password'}), 400

        # Test database connection first
        try:
            from database_config import test_db_connection
            db_success, db_error = test_db_connection()
            if not db_success:
                logger.error(f"Database connection failed: {db_error}")
                return jsonify({'error': 'Database connection failed'}), 500
            logger.info("Database connection verified")
        except Exception as db_test_error:
            logger.error(f"Database test error: {db_test_error}")
            return jsonify({'error': 'Database test failed'}), 500

        # Use service to authenticate user
        try:
            result = authenticate_user(email, password)
            logger.info(f"Authentication result: success={result['success']}")
        except Exception as auth_error:
            logger.error(f"Authentication service error: {auth_error}")
            return jsonify({'error': 'Authentication service failed'}), 500
        
        if not result['success']:
            logger.warning(f"Authentication failed: {result['error']}")
            return jsonify({'error': result['error']}), 401

        # Set session data
        try:
            session['user'] = create_session_data(result['user'])
            session.permanent = True
            logger.info(f"Session created for user: {email}")
        except Exception as session_error:
            logger.error(f"Session creation error: {session_error}")
            return jsonify({'error': 'Session creation failed'}), 500

        # Extract club and series from primary player or session data
        user_data = result['user']
        primary_player = user_data.get('primary_player')
        session_user = session.get('user', {})
        
        # Get club and series from primary player if available, otherwise from session
        if primary_player:
            club = primary_player.get('club', {}).get('name') if isinstance(primary_player.get('club'), dict) else primary_player.get('club', '')
            series = primary_player.get('series', {}).get('name') if isinstance(primary_player.get('series'), dict) else primary_player.get('series', '')
        else:
            club = session_user.get('club', '')
            series = session_user.get('series', '')

        # Check for redirect_after_login in session
        redirect_url = session.pop('redirect_after_login', '/mobile')
        
        return jsonify({
            'status': 'success',
            'message': result['message'],
            'redirect': redirect_url,
            'user': {
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'club': club,
                'series': series
            }
        })

    except Exception as e:
        logger.error(f"Login endpoint error: {str(e)}")
        logger.error(f"Request path: {request.path}")
        logger.error(f"Request method: {request.method}")
        logger.error(f"Request headers: {dict(request.headers)}")
        return jsonify({'error': 'Login failed - server error'}), 500

@auth_bp.route('/api/logout', methods=['POST'])
def handle_logout():
    """Handle API logout"""
    try:
        session.clear()
        return jsonify({'message': 'Logout successful'})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/logout')
def logout_page():
    """Handle page logout with redirect"""
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/check-auth')
def check_auth():
    """Check if the user is authenticated"""
    try:
        if 'user' in session:
            return jsonify({
                'authenticated': True,
                'user': session['user']
            })
        return jsonify({
            'authenticated': False
        })
    except Exception as e:
        logger.error(f"Error checking authentication: {str(e)}")
        return jsonify({
            'error': str(e),
            'authenticated': False
        }), 500

@auth_bp.route('/static/js/logout.js')
def serve_logout_js():
    """Serve the logout JavaScript file"""
    try:
        logout_js_content = '''
// logout.js - Handle logout functionality
console.log("Logout.js loaded");

window.logout = function() {
    console.log("Logout function called");
    fetch('/api/logout', {
        method: 'POST',
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        console.log("Logout response:", data);
        // Redirect to login page
        window.location.href = '/login';
    })
    .catch(error => {
        console.error('Logout error:', error);
        // Still redirect to login page even if logout fails
        window.location.href = '/login';
    });
};
'''
        response = jsonify(logout_js_content)
        response.headers['Content-Type'] = 'application/javascript'
        return response
    except Exception as e:
        logger.error(f"Error serving logout.js: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/get-clubs')
def get_clubs():
    """Get list of all clubs - public endpoint for registration"""
    try:
        clubs_list = get_clubs_list()
        return jsonify({
            'clubs': clubs_list  # For login page compatibility
        })
    except Exception as e:
        logger.error(f"Error getting clubs: {str(e)}")
        return jsonify({'error': str(e)}), 500 