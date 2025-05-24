from flask import jsonify, request, session, redirect, url_for, render_template
from functools import wraps
import hashlib
import logging
import os
from werkzeug.security import generate_password_hash, check_password_hash
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity

logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Not authenticated'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    """Hash a password using Werkzeug's secure method"""
    return generate_password_hash(password, method='pbkdf2:sha256')

def verify_password(stored_password, provided_password):
    """Verify a password against its hash"""
    # Handle old-style hash (format: plain SHA-256)
    if len(stored_password) == 64:  # SHA-256 hash length
        old_hash = hashlib.sha256(provided_password.encode()).hexdigest()
        return stored_password == old_hash
    # Handle new-style Werkzeug hash
    return check_password_hash(stored_password, provided_password)

def init_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('login.html')
        return jsonify({'error': 'Method not allowed'}), 405

    @app.route('/api/register', methods=['POST'])
    def handle_register():
        try:
            data = request.get_json()
            email = data.get('email', '').lower()
            password = data.get('password', '')
            first_name = data.get('firstName', '')
            last_name = data.get('lastName', '')
            club_name = data.get('club', '')
            series_name = data.get('series', '')

            if not all([email, password, first_name, last_name, club_name, series_name]):
                missing = []
                if not email: missing.append('email')
                if not password: missing.append('password')
                if not first_name: missing.append('firstName')
                if not last_name: missing.append('lastName')
                if not club_name: missing.append('club')
                if not series_name: missing.append('series')
                return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

            # Hash the password using the new secure method
            hashed_password = hash_password(password)

            try:
                # Get club and series IDs
                club_id = execute_query_one(
                    "SELECT id FROM clubs WHERE name = %(club)s",
                    {'club': club_name}
                )['id']
                
                series_id = execute_query_one(
                    "SELECT id FROM series WHERE name = %(series)s",
                    {'series': series_name}
                )['id']

                # Check if user already exists
                existing_user = execute_query_one(
                    "SELECT id FROM users WHERE LOWER(email) = LOWER(%(email)s)",
                    {'email': email}
                )
                
                if existing_user:
                    return jsonify({'error': 'User already exists'}), 409

                # Insert new user
                success = execute_update(
                    """
                    INSERT INTO users (email, password_hash, first_name, last_name, club_id, series_id)
                    VALUES (%(email)s, %(password_hash)s, %(first_name)s, %(last_name)s, %(club_id)s, %(series_id)s)
                    """,
                    {
                        'email': email,
                        'password_hash': hashed_password,
                        'first_name': first_name,
                        'last_name': last_name,
                        'club_id': club_id,
                        'series_id': series_id
                    }
                )

                if not success:
                    logger.error("Failed to insert new user")
                    return jsonify({'error': 'Registration failed'}), 500

                # Get the newly created user with club and series info for session
                user = execute_query_one(
                    """
                    SELECT u.id, u.email, u.first_name, u.last_name,
                           c.name as club_name, s.name as series_name
                    FROM users u
                    JOIN clubs c ON u.club_id = c.id
                    JOIN series s ON u.series_id = s.id
                    WHERE LOWER(u.email) = LOWER(%(email)s)
                    """,
                    {'email': email}
                )

                # Set session data to automatically log in the user
                session['user'] = {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'club': user['club_name'],
                    'series': user['series_name'],
                    'settings': '{}'  # Default empty settings
                }
                session.permanent = True

                # Log successful registration
                log_user_activity(email, 'auth', action='register', details='Registration successful')
                
                return jsonify({
                    'status': 'success',
                    'message': 'Registration successful',
                    'redirect': '/mobile'
                }), 201

            except Exception as db_error:
                logger.error(f"Database error during registration: {str(db_error)}")
                return jsonify({'error': 'Registration failed - database error'}), 500

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return jsonify({'error': 'Registration failed - server error'}), 500

    @app.route('/api/login', methods=['POST'])
    def handle_login():
        try:
            data = request.get_json()
            email = data.get('email', '').lower()
            password = data.get('password', '')

            if not email or not password:
                return jsonify({'error': 'Missing email or password'}), 400

            try:
                # Get user with club and series info
                user = execute_query_one(
                    """
                    SELECT u.id, u.email, u.password_hash, u.first_name, u.last_name,
                           c.name as club_name, s.name as series_name
                    FROM users u
                    JOIN clubs c ON u.club_id = c.id
                    JOIN series s ON u.series_id = s.id
                    WHERE LOWER(u.email) = LOWER(%(email)s)
                    """,
                    {'email': email}
                )

                if not user:
                    logger.warning(f"Login attempt failed - user not found: {email}")
                    return jsonify({'error': 'Invalid email or password'}), 401

                if not verify_password(user['password_hash'], password):
                    logger.warning(f"Login attempt failed - invalid password: {email}")
                    return jsonify({'error': 'Invalid email or password'}), 401

                # Set session data
                session['user'] = {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'club': user['club_name'],
                    'series': user['series_name'],
                    'settings': '{}'  # Default empty settings
                }
                session.permanent = True

                # Log successful login
                log_user_activity(email, 'auth', action='login', details='Login successful')

                return jsonify({
                    'status': 'success',
                    'message': 'Login successful',
                    'redirect': '/mobile',
                    'user': {
                        'email': user['email'],
                        'first_name': user['first_name'],
                        'last_name': user['last_name'],
                        'club': user['club_name'],
                        'series': user['series_name']
                    }
                })

            except Exception as db_error:
                logger.error(f"Database error during login: {str(db_error)}")
                return jsonify({'error': 'Login failed - database error'}), 500

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({'error': 'Login failed - server error'}), 500

    @app.route('/api/logout', methods=['POST'])
    def handle_logout():
        try:
            session.clear()
            return jsonify({'message': 'Logout successful'})
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return jsonify({'error': 'Logout failed'}), 500

    @app.route('/logout')
    def logout_page():
        session.clear()
        return redirect(url_for('login'))

    return app 