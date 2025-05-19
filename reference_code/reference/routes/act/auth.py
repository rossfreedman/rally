from flask import jsonify, request, session, redirect, url_for, render_template
from functools import wraps
import hashlib
import sqlite3
import logging
import os

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
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a password against its hash"""
    return stored_password == hash_password(provided_password)

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
            name = data.get('name', '')
            club = data.get('club', '')
            series = data.get('series', '')

            if not all([email, password, name, club, series]):
                return jsonify({'error': 'Missing required fields'}), 400

            # Hash the password
            hashed_password = hash_password(password)

            # Connect to database
            conn = sqlite3.connect('data/paddlepro.db')
            cursor = conn.cursor()

            # Check if user already exists
            cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                return jsonify({'error': 'User already exists'}), 409

            # Insert new user
            cursor.execute('''
                INSERT INTO users (email, password, name, club, series)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, hashed_password, name, club, series))
            
            conn.commit()
            conn.close()

            return jsonify({'message': 'Registration successful'}), 201

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return jsonify({'error': 'Registration failed'}), 500

    @app.route('/api/login', methods=['POST'])
    def handle_login():
        try:
            data = request.get_json()
            email = data.get('email', '').lower()
            password = data.get('password', '')

            if not email or not password:
                return jsonify({'error': 'Missing email or password'}), 400

            # Connect to database
            conn = sqlite3.connect('data/paddlepro.db')
            cursor = conn.cursor()

            # Get user
            cursor.execute('''
                SELECT email, password, name, club, series, settings
                FROM users 
                WHERE email = ?
            ''', (email,))
            
            user = cursor.fetchone()
            conn.close()

            if not user or not verify_password(user[1], password):
                return jsonify({'error': 'Invalid email or password'}), 401

            # Set session data
            session['user'] = {
                'email': user[0],
                'name': user[2],
                'club': user[3],
                'series': user[4],
                'settings': user[5] if user[5] else '{}'
            }
            session.permanent = True

            return jsonify({
                'message': 'Login successful',
                'user': {
                    'email': user[0],
                    'name': user[2],
                    'club': user[3],
                    'series': user[4]
                }
            })

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({'error': 'Login failed'}), 500

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

    @app.route('/api/check-auth')
    def check_auth():
        if 'user' in session:
            return jsonify({
                'authenticated': True,
                'user': session['user']
            })
        return jsonify({'authenticated': False}), 401

    return app 