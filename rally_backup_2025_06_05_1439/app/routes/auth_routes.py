from flask import Blueprint, jsonify, request, session, redirect, url_for, render_template
import logging
from app.services.auth_service import register_user, authenticate_user, create_session_data, get_clubs_list

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
        club_name = data.get('club', '')
        series_name = data.get('series', '')

        # Validate required fields
        if not all([email, password, first_name, last_name, club_name, series_name]):
            missing = []
            if not email: missing.append('email')
            if not password: missing.append('password')
            if not first_name: missing.append('firstName')
            if not last_name: missing.append('lastName')
            if not club_name: missing.append('club')
            if not series_name: missing.append('series')
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

        # Use service to register user
        result = register_user(email, password, first_name, last_name, club_name, series_name)
        
        if not result['success']:
            if 'already exists' in result['error']:
                return jsonify({'error': result['error']}), 409
            else:
                return jsonify({'error': result['error']}), 500

        # Set session data to automatically log in the user
        session['user'] = create_session_data(result['user'])
        session.permanent = True
        
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
        data = request.get_json()
        email = data.get('email', '').lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Missing email or password'}), 400

        # Use service to authenticate user
        result = authenticate_user(email, password)
        
        if not result['success']:
            return jsonify({'error': result['error']}), 401

        # Set session data
        session['user'] = create_session_data(result['user'])
        session.permanent = True

        return jsonify({
            'status': 'success',
            'message': result['message'],
            'redirect': '/mobile',
            'user': {
                'email': result['user']['email'],
                'first_name': result['user']['first_name'],
                'last_name': result['user']['last_name'],
                'club': result['user']['club_name'],
                'series': result['user']['series_name']
            }
        })

    except Exception as e:
        logger.error(f"Login endpoint error: {str(e)}")
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