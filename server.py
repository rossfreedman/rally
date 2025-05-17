from flask import Flask, jsonify, request, send_from_directory, render_template, session, redirect, url_for, make_response, g
from flask_socketio import SocketIO, emit
import pandas as pd
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import traceback
from openai import OpenAI
from dotenv import load_dotenv
import time
from functools import wraps
import sys
import re
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
import json
import hashlib
import secrets
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from utils.series_matcher import series_match, normalize_series_for_storage, normalize_series_for_display
from collections import defaultdict

# Initialize database
print("\n=== Initializing Database ===")
try:
    # Import the init_db function
    from init_db import init_db
    
    # Check if database exists
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}, initializing now...")
        init_db()
    else:
        print(f"Database file already exists at {db_path}")
    
    print("Database initialized successfully!")
except Exception as e:
    print(f"Error initializing database: {str(e)}")
    print(traceback.format_exc())
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to console
        logging.FileHandler('server.log')   # Log to file
    ]
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for required environment variables
openai_api_key = os.getenv('OPENAI_API_KEY')
openai_org_id = os.getenv('OPENAI_ORG_ID')  # Optional organization ID
assistant_id = os.getenv('OPENAI_ASSISTANT_ID', 'asst_Q6GQOccbb0ymf9IpLMG1lFHe')  # Default to known ID

if not openai_api_key:
    logger.error("ERROR: OPENAI_API_KEY environment variable is not set!")
    logger.error("Please set your OpenAI API key in the environment variables.")
    sys.exit(1)

# Initialize OpenAI client
client = OpenAI(
    api_key=openai_api_key,
    base_url="https://api.openai.com/v1"  # Explicitly set the base URL
)

# Store active threads
active_threads = {}

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')  # Change this in production

# Session config for development
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Set to False for development without HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1 hour
)

CORS(app, resources={
    r"/*": {  # Allow all routes
        "origins": [
            "http://localhost:5002",
            "http://127.0.0.1:5002",
            "http://localhost:3000",  # Development port
            "http://127.0.0.1:3000",  # Development port
            "https://*.up.railway.app",  # Railway domain
            "https://www.lovetorally.com",  # Production domain
            "https://lovetorally.com",  # Production domain without www
            "*"  # Allow all origins in development/testing
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,   # Important for session cookies
        "max_age": 86400
    }
})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active threads
active_threads = {}

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Not authenticated'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def read_all_player_data():
    """Read and return all player data from the CSV file"""
    try:
        import os
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'all_tennaqua_players.csv')
        df = pd.read_csv(csv_path)
        print(f"Successfully loaded {len(df)} player records")
        return df
    except Exception as e:
        print(f"Error reading player data: {str(e)}")
        return pd.DataFrame()

def get_or_create_assistant():
    """Get or create the paddle tennis assistant"""
    try:
        # First try to retrieve the existing assistant
        try:
            assistant = client.beta.assistants.retrieve(assistant_id)
            print(f"Successfully retrieved existing assistant with ID: {assistant.id}")
            return assistant
        except Exception as e:
            if "No assistant found" in str(e):
                print(f"Assistant {assistant_id} not found, creating new one...")
            else:
                raise
            print(f"Error retrieving assistant: {str(e)}")
            print("Attempting to create new assistant...")

        # Create new assistant if retrieval failed
        assistant = client.beta.assistants.create(
            name="PaddlePro Assistant",
            instructions="""You are a paddle tennis assistant. Help users with:
            1. Generating optimal lineups based on player statistics
            2. Analyzing match patterns and team performance
            3. Providing strategic advice for upcoming matches
            4. Answering questions about paddle tennis rules and strategy""",
            model="gpt-4-turbo-preview"
        )
        print(f"Successfully created new assistant with ID: {assistant.id}")
        print("\nIMPORTANT: Save this assistant ID in your environment variables:")
        print(f"OPENAI_ASSISTANT_ID={assistant.id}")
        return assistant
    except Exception as e:
        error_msg = str(e)
        print(f"Error with assistant: {error_msg}")
        print("Full error details:", traceback.format_exc())
        
        if "No access to organization" in error_msg:
            print("\nTROUBLESHOOTING STEPS:")
            print("1. Verify your OPENAI_ORG_ID is correct")
            print("2. Ensure your API key has access to the organization")
            print("3. Check if the assistant ID belongs to the correct organization")
        elif "Rate limit" in error_msg:
            print("\nTROUBLESHOOTING STEPS:")
            print("1. Check your API usage and limits")
            print("2. Implement rate limiting or retry logic if needed")
        elif "Invalid authentication" in error_msg:
            print("\nTROUBLESHOOTING STEPS:")
            print("1. Verify your OPENAI_API_KEY is correct and active")
            print("2. Check if your API key has the necessary permissions")
        
        raise Exception("Failed to initialize assistant. Please check the error messages above.")

try:
    # Initialize the assistant
    print("\nInitializing OpenAI Assistant...")
    assistant = get_or_create_assistant()
    print("Assistant initialization complete.")
except Exception as e:
    print(f"Failed to initialize assistant: {str(e)}")
    sys.exit(1)

# Add this near the top with other global variables
selected_series = "Chicago 22"
selected_club = f"Tennaqua - {selected_series.split()[-1]}"

# Configure logging
def setup_logging():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set up logging to both console and file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    app.logger.setLevel(logging.INFO)

@app.before_request
def log_request_info():
    """Log information about each request"""
    print(f"\n=== Request Info ===")
    print(f"Path: {request.path}")
    print(f"Method: {request.method}")
    print(f"User in session: {'user' in session}")
    if 'user' in session:
        print(f"User email: {session['user']['email']}")
    print("===================\n")

@app.route('/')
def serve_index():
    """Redirect all desktop index requests to the mobile version."""
    print("\n=== Serving Index Page ===")
    # If user is not authenticated, redirect to login
    if 'user' not in session:
        print("User not authenticated, redirecting to login")
        return redirect(url_for('login'))
    # Always redirect authenticated users to mobile
    print(f"User in session: {session['user']['email']}")
    print("Redirecting to /mobile")
    return redirect(url_for('serve_mobile'))

@app.route('/index.html')
def redirect_index_html():
    """Redirect /index.html to the mobile version."""
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('serve_mobile'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Serve the login page"""
    # If user is already authenticated, redirect to mobile interface
    if 'user' in session:
        return redirect(url_for('serve_mobile'))
    return app.send_static_file('login.html')

def hash_password(password):
    """Hash a password using SHA-256 and a random salt"""
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.sha256((salt + password).encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a password against a stored hash"""
    salt, hash_value = stored_password.split(':')
    return hash_value == hashlib.sha256((salt + provided_password).encode()).hexdigest()

@app.route('/api/register', methods=['POST'])
def handle_register():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        club = data.get('club')
        series = data.get('series')
        
        if not all([email, password, first_name, last_name, club, series]):
            return jsonify({'error': 'All fields are required'}), 400
            
        # Hash the password
        password_hash = hash_password(password)
        
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get club_id
            cursor.execute('SELECT id FROM clubs WHERE name = ?', (club,))
            club_result = cursor.fetchone()
            if not club_result:
                return jsonify({'error': 'Invalid club'}), 400
            club_id = club_result[0]
            
            # Get series_id
            cursor.execute('SELECT id FROM series WHERE name = ?', (series,))
            series_result = cursor.fetchone()
            if not series_result:
                return jsonify({'error': 'Invalid series'}), 400
            series_id = series_result[0]
            
            # Insert new user
            cursor.execute('''
                INSERT INTO users (email, password_hash, first_name, last_name, club_id, series_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (email, password_hash, first_name, last_name, club_id, series_id))
            
            conn.commit()
            
            # Create session for the new user
            session['user'] = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'club': club,
                'series': series
            }
            
            # Redirect to mobile interface after registration
            return jsonify({'status': 'success', 'redirect': '/mobile'})
            
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Email already registered'}), 400
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': 'An error occurred during registration'}), 500

@app.route('/api/login', methods=['POST'])
def handle_login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Please provide both email and password'}), 401
            
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get user with club and series info
            cursor.execute('''
                SELECT u.id, u.email, u.password_hash, u.first_name, u.last_name,
                       c.name as club_name, s.name as series_name
                FROM users u
                JOIN clubs c ON u.club_id = c.id
                JOIN series s ON u.series_id = s.id
                WHERE u.email = ?
            ''', (email,))
            
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'Invalid email or password'}), 401
                
            # Verify password
            if not verify_password(user[2], password):
                return jsonify({'error': 'Invalid email or password'}), 401
                
            # Update last login
            cursor.execute('''
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user[0],))
            conn.commit()
            
            # Create session with all user information
            session.permanent = True  # Use the permanent session lifetime
            session['user'] = {
                'id': user[0],
                'email': user[1],
                'first_name': user[3],
                'last_name': user[4],
                'club': user[5],
                'series': user[6]
            }
            
            # Log successful login
            log_user_activity(email, 'auth', action='login', details='Successful login')
            
            # Create response with session cookie settings and redirect to mobile
            response = jsonify({'status': 'success', 'redirect': '/mobile'})
            return response
            
        finally:
            conn.close()
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'An error occurred during login'}), 500

@app.route('/api/logout', methods=['POST'])
def handle_logout():
    """Handle user logout"""
    try:
        if 'user' in session:
            # Log logout
            log_user_activity(session['user']['email'], 'auth', action='logout')
            
        # Clear the session
        session.clear()
        return jsonify({'status': 'success', 'redirect': '/login'})
    except Exception as e:
        print(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

# Admin routes
@app.route('/admin')
@login_required
def serve_admin():
    """Serve the admin dashboard page"""
    try:
        # Log admin page visit
        log_user_activity(session['user']['email'], 'page_visit', page='admin')
        
        admin_path = os.path.join(app.static_folder, 'admin.html')
        if not os.path.exists(admin_path):
            print(f"Admin file not found at: {admin_path}")
            return "Error: Admin page not found", 404
        return send_from_directory(app.static_folder, 'admin.html')
    except Exception as e:
        print(f"Error serving admin page: {str(e)}")
        return "Error: Admin page not found", 404

@app.route('/api/admin/users')
@login_required
def get_admin_users():
    """Get all registered users with their club and series information"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.first_name, u.last_name, u.email, u.last_login,
                   c.name as club_name, s.name as series_name
            FROM users u
            JOIN clubs c ON u.club_id = c.id
            JOIN series s ON u.series_id = s.id
            ORDER BY u.last_login DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'first_name': row[0],
                'last_name': row[1],
                'email': row[2],
                'last_login': row[3],
                'club_name': row[4],
                'series_name': row[5]
            })
        
        conn.close()
        return jsonify(users)
    except Exception as e:
        print(f"Error getting admin users: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Protect all other routes
@app.route('/<path:path>')
@login_required
def serve_static(path):
    """Serve static files and log page visits"""
    print(f"\n=== Serving Static File ===")
    print(f"Path: {path}")
    print(f"User: {session.get('user', {}).get('email')}")
    print(f"Path ends with .html: {path.endswith('.html')}")
    print(f"User in session: {'user' in session}")
    print(f"Session contents: {session}")
    
    if 'user' in session:
        try:
            # Extract page name without extension and any directory path
            page_name = os.path.splitext(os.path.basename(path))[0]
            
            # Determine activity type and details based on path
            if path.endswith('.html'):
                activity_type = 'page_visit'
                details = f"Accessed page: {path}"
            elif path.startswith('components/'):
                activity_type = 'component_load'
                details = f"Loaded component: {path}"
            else:
                # For other static assets (css, js, images)
                activity_type = 'static_asset'
                details = f"Accessed static asset: {path}"
            
            print(f"About to log activity for: {path}")
            log_user_activity(
                session['user']['email'], 
                activity_type, 
                page=page_name,
                details=details
            )
            print("Successfully logged access")
        except Exception as e:
            print(f"Error logging access: {str(e)}")
            print(traceback.format_exc())
    
    return send_from_directory('static', path)

@app.route('/api/player-history')
def get_player_history():
    """Get player history data"""
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'player_history.json')
        with open(file_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"Error loading player history: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Protect all API routes except check-auth and login
@app.route('/api/<path:path>', methods=['GET', 'POST'])
def api_route(path):
    """Handle API routes and log access"""
    print(f"\n=== API Route Access ===")
    print(f"Path: {path}")
    print(f"Method: {request.method}")
    print(f"User in session: {'user' in session}")
    
    # List of routes that don't require authentication
    public_routes = ['check-auth', 'login', 'register', 'log-click']
    
    if path not in public_routes:
        if 'user' not in session:
            print("Authentication required but user not in session")
            return jsonify({'error': 'Not authenticated'}), 401
        print(f"Authenticated user: {session['user']['email']}")
        
        # Log API access for authenticated routes
        try:
            log_user_activity(
                session['user']['email'],
                'api_access',
                action=f'api_{path}',
                details=f"Method: {request.method}"
            )
            print("Successfully logged API access")
        except Exception as e:
            print(f"Error logging API access: {str(e)}")
            print(traceback.format_exc())
    
    # Let the route continue to the specific handler
    # If no specific handler matched, return a 404 error
    return jsonify({'error': 'API endpoint not found'}), 404

@app.route('/api/set-series', methods=['POST'])
def set_series():
    """Set the series for the current session"""
    try:
        data = request.get_json()
        series = data.get('series')
        if not series:
            return jsonify({'error': 'Series is required'}), 400
        session['series'] = series
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-series')
@app.route('/get-series')
def get_series():
    """Get the current series and all available series"""
    try:
        print("\n=== GET SERIES REQUEST ===")
        print("Connecting to database...")
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all series from the database
        print("Executing SQL query...")
        cursor.execute('SELECT name FROM series ORDER BY name')
        all_series = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Get the user's current series from their session
        user_series = session.get('user', {}).get('series', '')
        print(f"\nUser series from session: {user_series}")
        print(f"Available series: {all_series}")
        print(f"Number of series: {len(all_series)}")
        
        # Log each series with its extracted number
        print("\nSeries with extracted numbers:")
        for series in all_series:
            num = ''.join(filter(str.isdigit, series))
            print(f"Series: {series}, Number: {num}")
        
        response_data = {
            'series': user_series,
            'all_series': all_series
        }
        
        print(f"\nReturning response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        print(f"\nError getting series: {str(e)}")
        print("Full error:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/get-players-series-22', methods=['GET'])
def get_players_series_22():
    """Get all players for series 22"""
    try:
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'all_tennaqua_players.csv')
        df = pd.read_csv(csv_path)

        # Filter for Series 22
        series_22_df = df[df['Series'] == 'Chicago 22']  # Changed from 'Series 22' to 'Chicago 22'
        print(f"Found {len(series_22_df)} players in Series 22")
        
        # Track unique players
        unique_players = set()
        players = []
        
        for _, row in series_22_df.iterrows():
            player_name = f"{row['First Name']} {row['Last Name']}"  # Format as First Name Last Name
            
            if player_name not in unique_players:
                unique_players.add(player_name)
                player = {
                    'name': player_name,
                    'series': row['Series'],
                    'rating': str(row['PTI']),
                    'wins': str(row['Wins']),
                    'losses': str(row['Losses']),
                    'winRate': row['Win %']
                }
                players.append(player)
        
        print(f"Returning {len(players)} unique players")
        return jsonify({'players': players})  # Wrap players array in an object with 'players' key
        
    except Exception as e:
        print(f"\nERROR getting Series 22 players: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-lineup', methods=['POST'])
@login_required
def generate_lineup():
    try:
        data = request.json
        selected_players = data.get('players', [])
        
        # Get the user's current series and normalize it for display
        user_series = session['user'].get('series', '')
        display_series = normalize_series_for_display(user_series)
        
        # Stricter prompt to enforce exact format
        prompt = f"""Create an optimal lineup for these players from {display_series}: {', '.join([f"{p}" for p in selected_players])}

Provide detailed lineup recommendations based on player stats, match history, and team dynamics. Each recommendation should include:

Player Pairings: List the players paired for each court as follows:

Court 1: Player1/Player2
Court 2: Player3/Player4
Court 3: Player5/Player6
Court 4: Player7/Player8

Strategic Explanation: For each court, provide a brief explanation of the strategic reasoning behind the player pairings, highlighting player strengths, intended roles within the pairing, and any specific matchup considerations.
"""

        logger.debug(f"\n=== PROMPT ===\n{prompt}\n")
        
        # Create a new thread
        thread = client.beta.threads.create()
        
        # Add the message to the thread
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )
        
        # Create and run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Wait for the run to complete
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == 'completed':
                break
            elif run_status.status == 'failed':
                raise Exception(f"Run failed: {run_status.last_error}")
            time.sleep(1)
        
        # Get the assistant's response
        messages = client.beta.threads.messages.list(
            thread_id=thread.id,
            order="desc",
            limit=1
        )
        
        # Return the response
        return jsonify({
            'prompt': prompt,
            'suggestion': messages.data[0].content[0].text.value
        })
        
    except Exception as e:
        print(f"Error generating lineup: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/create-lineup')
@app.route('/create-lineup.html')
def create_lineup():
    print("\n=== Serving Create Lineup Page ===")
    return send_from_directory('static', 'create-lineup.html')

@socketio.on('connect')
def handle_connect():
    # Create a new thread for this session
    thread = client.beta.threads.create()
    active_threads[request.sid] = thread.id
    print(f"New client connected. Thread ID: {thread.id}")

@socketio.on('disconnect')
def handle_disconnect():
    # Clean up the thread
    thread_id = active_threads.pop(request.sid, None)
    if thread_id:
        print(f"Client disconnected. Thread ID: {thread_id}")

@socketio.on('send_message')
def handle_message(data):
    thread_id = active_threads.get(request.sid)
    if not thread_id:
        return
    
    try:
        # Add the user message to the thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=data['message']
        )

        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant.id
        )

        # Wait for the response
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if run_status.status == 'completed':
                break
            socketio.sleep(1)

        # Get the assistant's response
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        assistant_message = messages.data[0].content[0].text.value

        # Send the response back to the client
        emit('receive_message', {'message': assistant_message})

    except Exception as e:
        print(f"Error: {str(e)}")
        emit('receive_message', {'message': f"Error: {str(e)}"})

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        print("\n=== CHAT REQUEST ===")
        print(f"Message: {message}")
        print(f"Current series: {selected_series}")
        print("=== END REQUEST ===\n")
        
        # Create a new thread for this request
        thread = client.beta.threads.create()
        
        # Add context message first
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""You are a paddle tennis assistant. The current series is {selected_series}.
            Base your responses on player statistics and paddle tennis knowledge.
            Be specific and data-driven in your responses."""
        )
        
        # Add the user's message
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Wait for completion with timeout
        timeout = 30  # seconds
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError("Assistant response timed out")
                
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            
            if run_status.status == 'failed':
                print("\n=== CHAT ERROR ===")
                print(f"Run failed: {run_status.last_error}")
                print("=== END ERROR ===\n")
                if 'rate_limit_exceeded' in str(run_status.last_error):
                    return jsonify({'error': 'The AI service is currently experiencing high demand. Please try again in a few minutes.'}), 429
                raise Exception(f"Assistant run failed: {run_status.last_error}")
            elif run_status.status == 'completed':
                break
                
            time.sleep(1)
        
        # Get the messages
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        if not messages.data:
            raise Exception("No response received from assistant")
            
        assistant_message = messages.data[0].content[0].text.value
        
        print("\n=== CHAT RESPONSE ===")
        print(f"Response: {assistant_message}")
        print("=== END RESPONSE ===\n")
        
        return jsonify({'message': assistant_message})
        
    except Exception as e:
        print(f"\n=== CHAT ERROR ===")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print("=== END ERROR ===\n")
        
        if 'rate_limit_exceeded' in str(e):
            return jsonify({'error': 'The AI service is currently experiencing high demand. Please try again in a few minutes.'}), 429
        return jsonify({'error': str(e)}), 500

@app.route('/contact-sub')
@login_required
def contact_sub():
    """Serve the contact sub page"""
    return send_from_directory('static', 'contact-sub.html')

@app.route('/find-subs')
@login_required
def find_subs():
    """Serve the find subs page"""
    return send_from_directory('static', 'find-subs.html')

@app.route('/api/teams')
@login_required
def get_teams():
    """Return a list of all teams from the schedule"""
    try:
        # Read the schedule file
        schedule_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'schedules.json')
        if not os.path.exists(schedule_path):
            return jsonify({'error': 'Schedule file not found'}), 404
            
        with open(schedule_path, 'r') as f:
            schedule = json.load(f)
            
        # Extract unique team names from home_team and away_team fields
        teams = set()
        for match in schedule:
            # Skip practice records
            if 'Practice' in match:
                continue
            if 'home_team' in match:
                teams.add(match['home_team'])
            if 'away_team' in match:
                teams.add(match['away_team'])
                
        # Convert to sorted list
        teams_list = sorted(list(teams))
        
        return jsonify({'teams': teams_list})
        
    except Exception as e:
        print(f"Error getting teams: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/team-stats/<team_id>')
@login_required
def get_team_stats(team_id):
    """Return detailed statistics for a specific team"""
    try:
        # Read the series stats file
        stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'series_stats.json')
        matches_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_history.json')
        
        if not os.path.exists(stats_path):
            return jsonify({'error': 'Stats file not found'}), 404
            
        with open(stats_path, 'r') as f:
            stats = json.load(f)
            
        # Find the team's stats
        team_stats = next((team for team in stats if team['team'] == team_id), None)
        if not team_stats:
            return jsonify({'error': 'Team not found'}), 404
            
        # Read match data for court analysis
        court_stats = {
            'court1': {'wins': 0, 'losses': 0, 'key_players': set()},
            'court2': {'wins': 0, 'losses': 0, 'key_players': set()},
            'court3': {'wins': 0, 'losses': 0, 'key_players': set()},
            'court4': {'wins': 0, 'losses': 0, 'key_players': set()}
        }
        
        player_performance = {}  # Track individual player performance by court
        
        if os.path.exists(matches_path):
            with open(matches_path, 'r') as f:
                matches = json.load(f)
                
            # Analyze matches for court performance
            for match in matches:
                if match['Home Team'] == team_id or match['Away Team'] == team_id:
                    is_home = match['Home Team'] == team_id
                    
                    # Process each court's results
                    for court_num in range(1, 5):
                        court_key = f'court{court_num}'
                        court_result = match.get(f'Court {court_num}', {})
                        
                        if court_result:
                            # Determine if this court was won
                            won_court = (is_home and court_result.get('winner') == 'home') or \
                                      (not is_home and court_result.get('winner') == 'away')
                            
                            # Update court stats
                            if won_court:
                                court_stats[court_key]['wins'] += 1
                            else:
                                court_stats[court_key]['losses'] += 1
                                
                            # Track players for this court
                            players = court_result.get('players', [])
                            for player in players:
                                if (is_home and player['team'] == 'home') or \
                                   (not is_home and player['team'] == 'away'):
                                    # Initialize player stats if needed
                                    if player['name'] not in player_performance:
                                        player_performance[player['name']] = {
                                            'courts': {},
                                            'total_wins': 0,
                                            'total_matches': 0
                                        }
                                    
                                    # Update player's court performance
                                    if court_key not in player_performance[player['name']]['courts']:
                                        player_performance[player['name']]['courts'][court_key] = {
                                            'wins': 0, 'matches': 0
                                        }
                                    
                                    player_performance[player['name']]['courts'][court_key]['matches'] += 1
                                    if won_court:
                                        player_performance[player['name']]['courts'][court_key]['wins'] += 1
                                        player_performance[player['name']]['total_wins'] += 1
                                    player_performance[player['name']]['total_matches'] += 1
        
        # Identify key players for each court
        for court_key in court_stats:
            # Find players with best win rate on this court (minimum 3 matches)
            court_players = []
            for player, stats in player_performance.items():
                if court_key in stats['courts'] and stats['courts'][court_key]['matches'] >= 3:
                    win_rate = stats['courts'][court_key]['wins'] / stats['courts'][court_key]['matches']
                    court_players.append({
                        'name': player,
                        'win_rate': win_rate,
                        'matches': stats['courts'][court_key]['matches'],
                        'wins': stats['courts'][court_key]['wins']
                    })
            
            # Sort by win rate and take top 2
            court_players.sort(key=lambda x: x['win_rate'], reverse=True)
            court_stats[court_key]['key_players'] = court_players[:2]
        
        # Calculate basic team stats
        total_matches = team_stats['matches']['won'] + team_stats['matches']['lost']
        win_rate = team_stats['matches']['won'] / total_matches if total_matches > 0 else 0
        
        # Calculate average points
        total_games = team_stats['games']['won'] + team_stats['games']['lost']
        avg_points_for = team_stats['games']['won'] / total_matches if total_matches > 0 else 0
        avg_points_against = team_stats['games']['lost'] / total_matches if total_matches > 0 else 0
        
        # Calculate consistency rating (based on standard deviation of scores)
        consistency_rating = 8.5  # Placeholder - would calculate from actual score variance
        
        # Calculate strength index (composite of win rate and point differential)
        point_differential = avg_points_for - avg_points_against
        strength_index = (win_rate * 7 + (point_differential / 10) * 3)  # Scale to 0-10
        
        # Get recent form (last 5 matches)
        recent_form = ['W', 'L', 'W', 'W', 'L']  # Placeholder - would get from actual match history
        
        # Format response
        response = {
            'teamName': team_id,
            'wins': team_stats['matches']['won'],
            'losses': team_stats['matches']['lost'],
            'winRate': win_rate,
            'avgPointsFor': avg_points_for,
            'avgPointsAgainst': avg_points_against,
            'consistencyRating': consistency_rating,
            'strengthIndex': strength_index,
            'recentForm': recent_form,
            'dates': ['2025-01-01', '2025-01-15', '2025-02-01', '2025-02-15', '2025-03-01'],  # Placeholder dates
            'scores': [6, 8, 7, 9, 6],  # Placeholder scores
            'courtAnalysis': court_stats
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error getting team stats: {str(e)}")
        print(traceback.format_exc())  # Print full traceback for debugging
        return jsonify({'error': str(e)}), 500

@app.route('/api/lineup-instructions', methods=['GET', 'POST', 'DELETE'])
@login_required
def lineup_instructions():
    if request.method == 'GET':
        try:
            user_email = session['user']['email']
            team_id = request.args.get('team_id')
            
            if not team_id:
                return jsonify({'error': 'Team ID is required'}), 400
                
            instructions = get_user_instructions(user_email, team_id=team_id)
            return jsonify({'instructions': [i['instruction'] for i in instructions]})
        except Exception as e:
            print(f"Error getting lineup instructions: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    elif request.method == 'POST':
        try:
            user_email = session['user']['email']
            data = request.get_json()
            instruction = data.get('instruction')
            team_id = data.get('team_id')
            
            if not instruction:
                return jsonify({'error': 'Instruction is required'}), 400
            if not team_id:
                return jsonify({'error': 'Team ID is required'}), 400
                
            success = add_user_instruction(user_email, instruction, team_id=team_id)
            if not success:
                return jsonify({'error': 'Failed to add instruction'}), 500
                
            return jsonify({'status': 'success'})
        except Exception as e:
            print(f"Error adding lineup instruction: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    elif request.method == 'DELETE':
        try:
            user_email = session['user']['email']
            data = request.get_json()
            instruction = data.get('instruction')
            team_id = data.get('team_id')
            
            if not instruction:
                return jsonify({'error': 'Instruction is required'}), 400
            if not team_id:
                return jsonify({'error': 'Team ID is required'}), 400
                
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE user_instructions
            SET is_active = 0
            WHERE instruction = ? AND user_email = ? AND team_id = ?
            ''', (instruction, user_email, team_id))
            
            conn.commit()
            conn.close()
            return jsonify({'status': 'success'})
        except Exception as e:
            print(f"Error deleting lineup instruction: {str(e)}")
            return jsonify({'error': str(e)}), 500
        finally:
            if 'conn' in locals():
                conn.close()

def get_user_instructions(user_email, team_id=None):
    """Get all active instructions for a user, optionally filtered by team"""
    logger.info(f"Getting instructions for user: {user_email}, team_id: {team_id}")
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT id, instruction, team_id, created_at
        FROM user_instructions
        WHERE user_email = ? AND is_active = 1
        '''
        params = [user_email]
        
        if team_id:
            query += ' AND team_id = ?'
            params.append(team_id)
            
        query += ' ORDER BY created_at DESC'
        
        logger.debug(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        instructions = cursor.fetchall()
        logger.debug(f"Found {len(instructions)} instructions")
        
        # Convert to list of dictionaries
        result = []
        for row in instructions:
            result.append({
                'id': row[0],
                'instruction': row[1],
                'team_id': row[2],
                'created_at': row[3]
            })
        
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error getting user instructions: {str(e)}")
        logger.error(traceback.format_exc())
        if 'conn' in locals():
            conn.close()
        return []

def add_user_instruction(user_email, instruction, team_id=None):
    """Add a new instruction for a user, optionally associated with a team"""
    logger.info(f"Adding instruction for user: {user_email}, team_id: {team_id}")
    logger.debug(f"Instruction text: {instruction}")
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = '''
        INSERT INTO user_instructions (user_email, instruction, team_id)
        VALUES (?, ?, ?)
        '''
        params = (user_email, instruction, team_id)
        logger.debug(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        conn.commit()
        logger.info("Successfully added instruction")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error adding user instruction: {str(e)}")
        logger.error(traceback.format_exc())
        if 'conn' in locals():
            conn.close()
        return False

def deactivate_instruction(user_email, instruction_id):
    """Deactivate an instruction for a user"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_instructions 
            SET is_active = 0 
            WHERE id = ? AND user_email = ?
        ''', (instruction_id, user_email))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error deactivating instruction: {str(e)}")
        logger.error(traceback.format_exc())
        if 'conn' in locals():
            conn.close()
        raise

@app.route('/api/schedule')
@login_required
def serve_schedule():
    try:
        print("\n=== SCHEDULE REQUEST ===")
        print(f"Session data: {session.get('user')}")
        
        # Log schedule access
        log_user_activity(
            session['user']['email'], 
            'feature_use', 
            action='view_schedule'
        )
        
        # Read the schedule file
        schedule_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'schedules.json')
        with open(schedule_path, 'r') as f:
            schedule_data = json.load(f)

        # Get the current series and club from the session
        if 'user' not in session:
            print("❌ No user in session")
            return jsonify({'error': 'Not authenticated'}), 401
            
        user_club = session['user'].get('club')
        if not user_club:
            print("❌ No club found in user session")
            return jsonify({'error': 'Club information not found'}), 400
            
        print(f"User club from session: {user_club}")
        
        # Format the club name to match the schedule format
        # The schedule uses format "Club Name - Series - Series"
        series = session['user'].get('series', '')
        series_num = series.split()[-1] if series else ''
        club_name = f"{user_club} - {series_num} - {series_num}"
        print(f"Formatted club name for filtering: {club_name}")
        
        # Filter matches based on the club
        filtered_matches = []
        for match in schedule_data:
            try:
                # Check if it's a practice record
                if 'Practice' in match:
                    # For practices, add them all since they're at the user's club
                    filtered_matches.append(match)
                    continue
                    
                # For regular matches, check if the club is either home or away team
                if match.get('home_team') == club_name or match.get('away_team') == club_name:
                    filtered_matches.append(match)
            except KeyError as e:
                print(f"Warning: Skipping invalid match record: {e}")
                continue
        
        print(f"Found {len(filtered_matches)} matches for club {club_name}")
        print("=== END SCHEDULE REQUEST ===\n")
        return jsonify(filtered_matches)
    except FileNotFoundError:
        print(f"❌ Schedule file not found at {schedule_path}")
        return jsonify({'error': 'Schedule file not found'}), 404
    except json.JSONDecodeError:
        print(f"❌ Error parsing schedule file: Invalid JSON format")
        return jsonify({'error': 'Invalid schedule file format'}), 500
    except Exception as e:
        print(f"❌ Error serving schedule file: {str(e)}")
        print(traceback.format_exc())  # Print full traceback for debugging
        return jsonify({'error': 'Internal server error'}), 500

def get_player_availability(player_name, match_date, series):
    """Get a player's availability for a specific match date and series."""
    conn = None
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT is_available 
            FROM player_availability 
            WHERE player_name = ? AND match_date = ? AND series = ?
        ''', (player_name, match_date, series))
        result = cursor.fetchone()
        return result[0] if result else None  # Returns None if not updated
    finally:
        if conn:
            conn.close()

def update_player_availability(player_name, match_date, is_available, series):
    """Update or insert a player's availability for a specific match date and series."""
    try:
        print(f"\n=== UPDATING AVAILABILITY ===")
        print(f"Player: {player_name}")
        print(f"Date: {match_date}")
        print(f"Available: {is_available}")
        print(f"Series: {series}")
        
        conn = None
        try:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # First, check if the record exists
            cursor.execute('''
                SELECT is_available 
                FROM player_availability 
                WHERE player_name = ? AND match_date = ? AND series = ?
            ''', (player_name, match_date, series))
            existing = cursor.fetchone()
            
            if existing:
                print(f"Updating existing record: {existing[0]} -> {is_available}")
                cursor.execute('''
                    UPDATE player_availability 
                    SET is_available = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE player_name = ? AND match_date = ? AND series = ?
                ''', (is_available, player_name, match_date, series))
            else:
                print("Creating new record")
                cursor.execute('''
                    INSERT INTO player_availability 
                    (player_name, match_date, is_available, series)
                    VALUES (?, ?, ?, ?)
                ''', (player_name, match_date, is_available, series))
            
            conn.commit()
            print("Successfully saved to database")
            
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        print(f"Error saving to database: {str(e)}")
        print("Full error:", traceback.format_exc())
        raise

@app.route('/api/availability', methods=['GET', 'POST'])
def handle_availability():
    if request.method == 'GET':
        player_name = request.args.get('player_name')
        match_date = request.args.get('match_date')
        series = request.args.get('series')
        if not all([player_name, match_date, series]):
            return jsonify({'error': 'Missing required parameters'}), 400
        availability = get_player_availability(player_name, match_date, series)
        return jsonify({'is_available': availability})  # Returns None if not updated
    
    elif request.method == 'POST':
        data = request.get_json()
        print("\n=== AVAILABILITY UPDATE ===")
        print("Received data:", data)
        
        if not all(k in data for k in ['player_name', 'match_date', 'is_available', 'series']):
            print("Missing required fields:", data)
            return jsonify({'error': 'Missing required fields'}), 400
        
        try:
            # Log availability update
            log_user_activity(
                session['user']['email'], 
                'feature_use', 
                action='update_availability',
                details=f"Player: {data['player_name']}, Date: {data['match_date']}, Available: {data['is_available']}"
            )
            
            # The date is already in the correct format from the frontend
            match_date = data['match_date']
            print("Updating availability for:", data['player_name'], "on", match_date, "in series", data['series'])
            
            # Update the availability in the database
            update_player_availability(
                data['player_name'],
                match_date,
                data['is_available'],
                data['series']
            )
            
            print("Successfully updated availability")
            return jsonify({'status': 'success'})
        except Exception as e:
            print(f"Error updating availability: {str(e)}")
            print("Full error:", traceback.format_exc())
            return jsonify({'error': str(e)}), 500

@app.route('/api/get-availability', methods=['GET'])
def get_availability():
    try:
        print("\n=== GET AVAILABILITY REQUEST ===")
        # Get current series
        series_response = get_series()
        if not series_response:
            print("❌ Failed to get current series")
            return jsonify({'error': 'Failed to get current series'}), 500
            
        # Parse the JSON response
        series_data = series_response.get_json()
        if not series_data:
            print("❌ Failed to parse series data")
            return jsonify({'error': 'Failed to parse series data'}), 500
            
        series = series_data['series']
        print(f"Getting availability for series: {series}")
        
        # Get all availability data for the current series
        conn = None
        try:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT player_name, match_date, is_available
                FROM player_availability
                WHERE series = ?
            ''', (series,))
            
            availability_data = {}
            for row in cursor.fetchall():
                player_name, match_date, is_available = row
                if player_name not in availability_data:
                    availability_data[player_name] = {}
                availability_data[player_name][match_date] = is_available
                
            print(f"Found availability data for {len(availability_data)} players")
            return jsonify(availability_data)
            
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        print(f"Error getting availability: {str(e)}")
        print("Full error:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-clubs', methods=['GET'])
def get_clubs():
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM clubs ORDER BY name')
        clubs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({'clubs': clubs})
    except Exception as e:
        print(f"Error getting clubs: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching clubs'}), 500

@app.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated"""
    try:
        print("\n=== CHECK AUTH REQUEST ===")
        print(f"Origin: {request.headers.get('Origin', 'No origin header')}")
        print(f"Referer: {request.headers.get('Referer', 'No referer header')}")
        
        if 'user' not in session:
            print("❌ No user in session")
            return jsonify({
                'authenticated': False,
                'error': 'Not authenticated'
            })
            
        # Get user details from session
        user = session['user']
        print(f"User from session: {user}")
        
        if not all(key in user for key in ['email', 'first_name', 'last_name']):
            print("❌ Invalid session data")
            session.clear()
            return jsonify({
                'authenticated': False,
                'error': 'Invalid session data'
            })
            
        # Get additional user info from database
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            print(f"Querying database for user: {user['email']}")
            cursor.execute('''
                SELECT u.first_name, u.last_name, u.email, c.name as club_name, 
                       s.name as series_name, u.club_automation_password
                FROM users u
                JOIN clubs c ON u.club_id = c.id
                JOIN series s ON u.series_id = s.id
                WHERE u.email = ?
            ''', (user['email'],))
            
            db_user = cursor.fetchone()
            if db_user:
                print(f"Found user in database: {db_user}")
                # Update session with complete user information
                session['user'] = {
                    'email': db_user[2],
                    'first_name': db_user[0],
                    'last_name': db_user[1],
                    'club': db_user[3],
                    'series': db_user[4],
                    'has_club_automation_password': bool(db_user[5])
                }
                print(f"Updated session data: {session['user']}")
            else:
                print("❌ User not found in database")
                return jsonify({
                    'authenticated': False,
                    'error': 'User not found in database'
                })
            
        finally:
            conn.close()
            
        print(f"✅ User authenticated: {user['email']}")
        print("=== END CHECK AUTH ===")
        
        # Create response with appropriate headers
        response = jsonify({
            'authenticated': True,
            'user': session['user']
        })
        
        return response
        
    except Exception as e:
        print(f"❌ Auth check error: {str(e)}")
        print("Full error:", traceback.format_exc())
        # Clear session on error to prevent infinite loops
        session.clear()
        return jsonify({
            'authenticated': False,
            'error': 'Authentication check failed'
        }), 401

@app.route('/api/get-user-settings')
@login_required
def get_user_settings():
    """Get the current user's settings"""
    try:
        print("\n=== GETTING USER SETTINGS ===")
        user = session['user']
        print(f"User from session: {user}")
        
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get user details from database
            cursor.execute('''
                SELECT u.first_name, u.last_name, u.email, c.name as club_name, s.name as series_name, u.club_automation_password
                FROM users u
                JOIN clubs c ON u.club_id = c.id
                JOIN series s ON u.series_id = s.id
                WHERE u.email = ?
            ''', (user['email'],))
            
            user_data = cursor.fetchone()
            print(f"User data from database: {user_data}")
            
            if not user_data:
                print("No user data found in database")
                return jsonify({'error': 'User not found'}), 404
                
            has_club_automation_password = bool(user_data[5])
            return jsonify({
                'first_name': user_data[0],
                'last_name': user_data[1],
                'email': user_data[2],
                'club': user_data[3],
                'series': user_data[4],
                'has_club_automation_password': has_club_automation_password,
                'club_automation_password': user_data[5] or ''
            })
            
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            conn.rollback()
            return jsonify({'error': 'Database error occurred'}), 500
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error getting user settings: {str(e)}")
        print("Full error:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/clubs')
@login_required
def get_admin_clubs():
    """Get all active clubs with member counts and active series"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get clubs with member counts
        cursor.execute('''
            SELECT c.name, COUNT(u.id) as member_count,
                   GROUP_CONCAT(DISTINCT s.name) as active_series
            FROM clubs c
            LEFT JOIN users u ON c.id = u.club_id
            LEFT JOIN series s ON u.series_id = s.id
            GROUP BY c.id
            ORDER BY member_count DESC
        ''')
        
        clubs = []
        for row in cursor.fetchall():
            clubs.append({
                'name': row[0],
                'member_count': row[1],
                'active_series': row[2] or 'None'
            })
        
        conn.close()
        return jsonify(clubs)
    except Exception as e:
        print(f"Error getting admin clubs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/series')
@login_required
def get_admin_series():
    """Get all active series with player counts and active clubs"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
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
        return jsonify(series)
    except Exception as e:
        print(f"Error getting admin series: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-user', methods=['POST'])
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
            
        # Log admin action
        log_user_activity(
            session['user']['email'], 
            'admin_action', 
            action='update_user',
            details=f"Updated user: {email}"
        )
            
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get club and series IDs
            cursor.execute('SELECT id FROM clubs WHERE name = ?', (club_name,))
            club_result = cursor.fetchone()
            if not club_result:
                return jsonify({'error': 'Invalid club'}), 400
            club_id = club_result[0]
            
            cursor.execute('SELECT id FROM series WHERE name = ?', (series_name,))
            series_result = cursor.fetchone()
            if not series_result:
                return jsonify({'error': 'Invalid series'}), 400
            series_id = series_result[0]
            
            # Update user
            cursor.execute('''
                UPDATE users 
                SET first_name = ?, last_name = ?, club_id = ?, series_id = ?
                WHERE email = ?
            ''', (first_name, last_name, club_id, series_id, email))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'User not found'}), 404
                
            conn.commit()
            return jsonify({'status': 'success'})
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-club', methods=['POST'])
@login_required
def update_club():
    """Update a club's information"""
    try:
        data = request.json
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        if not all([old_name, new_name]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update club name - using ? instead of %s for SQLite
        cursor.execute('UPDATE clubs SET name = ? WHERE name = ?', (new_name, old_name))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating club: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/update-series', methods=['POST'])
@login_required
def update_series():
    """Update a series' information"""
    try:
        data = request.json
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        if not all([old_name, new_name]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update series name
        cursor.execute('UPDATE series SET name = %s WHERE name = %s', (new_name, old_name))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating series: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/static/components/<path:filename>')
def serve_component(filename):
    return send_from_directory('static/components', filename)

# Conditionally import and initialize Selenium
SELENIUM_ENABLED = not os.environ.get('DISABLE_SELENIUM', 'false').lower() == 'true'

if SELENIUM_ENABLED:
    try:
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        print("Selenium imports successful")
    except Exception as e:
        print(f"Warning: Selenium imports failed: {e}")
        SELENIUM_ENABLED = False

def get_chrome_options():
    if not SELENIUM_ENABLED:
        return None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--remote-debugging-port=9222')  # Add this line
        options.add_argument('--window-size=1920,1080')      # Add this line
        if os.environ.get('CHROME_BIN'):
            options.binary_location = os.environ['CHROME_BIN']
        return options
    except Exception as e:
        print(f"Warning: Failed to create Chrome options: {e}")
        return None

@app.route('/api/reserve-court', methods=['POST'])
@login_required
def reserve_court():
    if not SELENIUM_ENABLED:
        return jsonify({
            'error': 'SELENIUM_DISABLED',
            'message': 'Court reservation is temporarily disabled'
        }), 503
        
    logger = logging.getLogger(__name__)
    logger.debug("Starting court reservation process")
    
    try:
        # Get the current user's email from the session
        user_email = session['user']['email']
        logger.debug(f"Attempting to reserve court for user: {user_email}")
        
        # Get credentials from database
        try:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT club_automation_password FROM users WHERE email = ?', (user_email,))
            result = cursor.fetchone()
            if not result or not result[0]:
                logger.error(f"No Club Automation password found for user {user_email}")
                return jsonify({'error': 'NO_CLUB_AUTOMATION_PASSWORD', 'message': 'No Club Automation password found for this user.'}), 400
            password = result[0]
        finally:
            conn.close()

        # Initialize Chrome webdriver with options
        options = get_chrome_options()
        if not options:
            return jsonify({'error': 'Failed to create Chrome options'}), 500
        
        driver = webdriver.Chrome(options=options)
        
        try:
            # Navigate to login page with retry
            logger.debug("Navigating to login page...")
            navigate_with_retry(driver, "https://tennaqua.clubautomation.com")
            
            # Login using the enhanced element interaction methods
            logger.debug("Attempting login...")
            username_field = wait_for_element(driver, "input[name='login']")
            username_field.send_keys(user_email)
            
            password_field = wait_for_element(driver, "input[name='password']")
            password_field.send_keys(password)
            
            wait_and_click(driver, "#loginButton")
            
            # Wait for successful login
            WebDriverWait(driver, 15).until(lambda d: "member" in d.current_url.lower())
            logger.debug("Successfully logged in")
            
            # Navigate to court reservation
            logger.debug("Navigating to court reservation page...")
            navigate_with_retry(driver, "https://tennaqua.clubautomation.com/event/reserve-court")
            
            # Wait for profile tabs and try to find Paddle Tennis tab using multiple methods
            logger.debug("Looking for Paddle Tennis tab...")
            paddle_tennis_selectors = [
                (By.CSS_SELECTOR, "#tab_27.profileTabButton"),
                (By.XPATH, "//div[contains(@class, 'profileTabButton') and contains(text(), 'Paddle Tennis')]"),
                (By.LINK_TEXT, "Paddle Tennis")
            ]
            
            paddle_tennis_tab = find_element_by_multiple_selectors(driver, paddle_tennis_selectors)
            logger.debug("Found Paddle Tennis tab")
            
            # Try to click the tab using our safe click method
            safe_click(driver, paddle_tennis_tab)
            logger.debug("Clicked Paddle Tennis tab")
            
            # Wait for the content to load
            wait_for_element(driver, "#component_paddletennis_location_id")
            logger.debug("Paddle Tennis content loaded")
            
            # Take a screenshot for verification
            driver.save_screenshot("paddle_tennis_page.png")
            logger.debug("Saved screenshot of the page")
            
            # Wait for specific element to appear
            wait_for_element(driver, ".new-page-element")
            
            return '', 200
            
        except Exception as e:
            logger.error(f"Error during navigation: {str(e)}")
            if driver:
                driver.save_screenshot("error_screenshot.png")
            raise
            
    except Exception as e:
        logger.error(f"Error during court reservation: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add these helper functions after the imports
def wait_and_click(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    """Wait for an element to be clickable and click it"""
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(0.5)
    element.click()
    return element

def wait_for_element(driver, selector, by=By.CSS_SELECTOR, timeout=10):
    """Wait for an element to be present and return it"""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )

def safe_click(driver, element):
    """Try multiple click methods until one works"""
    try:
        element.click()
    except:
        try:
            driver.execute_script("arguments[0].click();", element)
        except:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).move_to_element(element).click().perform()

def find_element_by_multiple_selectors(driver, selectors):
    """Try multiple selectors to find an element"""
    for selector_type, selector in selectors:
        try:
            element = driver.find_element(selector_type, selector)
            if element.is_displayed():
                return element
        except:
            continue
    raise Exception(f"Could not find element with any of these selectors: {selectors}")

def navigate_with_retry(driver, url, max_retries=3):
    """Navigate to a URL with retry logic"""
    for attempt in range(max_retries):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

@app.route('/api/series-stats')
def get_series_stats():
    """Return the series stats for the user's series"""
    try:
        # Read the stats file
        stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'series_stats.json')
        matches_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_history.json')
        
        if not os.path.exists(stats_path):
            return jsonify({'error': 'Stats file not found'}), 404
            
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
            
        # Get the requested team from query params
        requested_team = request.args.get('team')
        
        if requested_team:
            team_stats = next((team for team in all_stats if team['team'] == requested_team), None)
            if not team_stats:
                return jsonify({'error': 'Team not found'}), 404

            # Format the response with just the team analysis data
            stats_data = {
                'team_analysis': {
                    'overview': {
                        'points': team_stats['points'],
                        'match_record': f"{team_stats['matches']['won']}-{team_stats['matches']['lost']}",
                        'match_win_rate': team_stats['matches']['percentage'],
                        'line_win_rate': team_stats['lines']['percentage'],
                        'set_win_rate': team_stats['sets']['percentage'],
                        'game_win_rate': team_stats['games']['percentage']
                    }
                }
            }

            # Add match patterns if matches file exists
            if os.path.exists(matches_path):
                with open(matches_path, 'r') as f:
                    matches = json.load(f)
                    
                # Initialize court stats
                court_stats = {
                    'court1': {'wins': 0, 'losses': 0, 'key_players': []},
                    'court2': {'wins': 0, 'losses': 0, 'key_players': []},
                    'court3': {'wins': 0, 'losses': 0, 'key_players': []},
                    'court4': {'wins': 0, 'losses': 0, 'key_players': []}
                }
                
                player_performance = {}
                
                # Group matches by date and team
                team_matches = {}
                for match in matches:
                    if match['Home Team'] == requested_team or match['Away Team'] == requested_team:
                        date = match['Date']
                        if date not in team_matches:
                            team_matches[date] = []
                        team_matches[date].append(match)
                
                # Process each match day
                for date, day_matches in team_matches.items():
                    # Sort matches to ensure consistent court assignment
                    day_matches.sort(key=lambda x: (x['Date'], x['Home Team'], x['Away Team']))
                    
                    # Process each match with its court number
                    for court_num, match in enumerate(day_matches, 1):
                        is_home = match['Home Team'] == requested_team
                        court_key = f'court{court_num}'
                        
                        # Determine if this court was won
                        won_court = (is_home and match['Winner'] == 'home') or \
                                  (not is_home and match['Winner'] == 'away')
                        
                        # Update court stats
                        if won_court:
                            court_stats[court_key]['wins'] += 1
                        else:
                            court_stats[court_key]['losses'] += 1
                        
                        # Track player performance
                        players = []
                        if is_home:
                            players = [
                                {'name': match['Home Player 1'], 'team': 'home'},
                                {'name': match['Home Player 2'], 'team': 'home'}
                            ]
                        else:
                            players = [
                                {'name': match['Away Player 1'], 'team': 'away'},
                                {'name': match['Away Player 2'], 'team': 'away'}
                            ]
                        
                        for player in players:
                            if player['name'] not in player_performance:
                                player_performance[player['name']] = {
                                    'courts': {},
                                    'total_wins': 0,
                                    'total_matches': 0
                                }
                            
                            if court_key not in player_performance[player['name']]['courts']:
                                player_performance[player['name']]['courts'][court_key] = {
                                    'wins': 0,
                                    'matches': 0
                                }
                            
                            player_performance[player['name']]['courts'][court_key]['matches'] += 1
                            if won_court:
                                player_performance[player['name']]['courts'][court_key]['wins'] += 1
                                player_performance[player['name']]['total_wins'] += 1
                            player_performance[player['name']]['total_matches'] += 1
                
                # Calculate various metrics
                total_matches = len([match for matches in team_matches.values() for match in matches])
                total_sets_won = 0
                total_sets_played = 0
                three_set_matches = 0
                three_set_wins = 0
                straight_set_wins = 0
                comeback_wins = 0
                
                # Process match statistics
                for matches in team_matches.values():
                    for match in matches:
                        scores = match['Scores'].split(', ')
                        is_home = match['Home Team'] == requested_team
                        won_match = (match['Winner'] == 'home' and is_home) or \
                                  (match['Winner'] == 'away' and not is_home)
                        
                        # Count sets
                        total_sets_played += len(scores)
                        for set_score in scores:
                            home_games, away_games = map(int, set_score.split('-'))
                            if (is_home and home_games > away_games) or \
                               (not is_home and away_games > home_games):
                                total_sets_won += 1
                        
                        #    match patterns
                        if len(scores) == 3:
                            three_set_matches += 1
                            if won_match:
                                three_set_wins += 1
                        elif won_match:
                            straight_set_wins += 1
                        
                        # Check for comebacks
                        if won_match:
                            first_set = scores[0].split('-')
                            first_set_games = list(map(int, first_set))
                            lost_first = (is_home and first_set_games[0] < first_set_games[1]) or \
                                       (not is_home and first_set_games[0] > first_set_games[1])
                            if lost_first:
                                comeback_wins += 1
                
                # Identify key players for each court
                for court_key in court_stats:
                    court_players = []
                    for player, stats in player_performance.items():
                        if court_key in stats['courts'] and stats['courts'][court_key]['matches'] >= 2:
                            win_rate = stats['courts'][court_key]['wins'] / stats['courts'][court_key]['matches']
                            court_players.append({
                                'name': player,
                                'win_rate': win_rate,
                                'matches': stats['courts'][court_key]['matches'],
                                'wins': stats['courts'][court_key]['wins']
                            })
                    
                    # Sort by win rate and take top 2
                    court_players.sort(key=lambda x: x['win_rate'], reverse=True)
                    court_stats[court_key]['key_players'] = court_players[:2]
                
                # Add match patterns to the response
                stats_data['team_analysis']['match_patterns'] = {
                    'total_matches': total_matches,
                    'set_win_rate': round(total_sets_won / total_sets_played * 100, 1) if total_sets_played > 0 else 0,
                    'three_set_record': f"{three_set_wins}-{three_set_matches - three_set_wins}",
                    'straight_set_wins': straight_set_wins,
                    'comeback_wins': comeback_wins,
                    'court_analysis': {
                        str(court_num): {
                            'wins': court_stats[f'court{court_num}']['wins'],
                            'losses': court_stats[f'court{court_num}']['losses'],
                            'win_rate': round(court_stats[f'court{court_num}']['wins'] / 
                                            (court_stats[f'court{court_num}']['wins'] + court_stats[f'court{court_num}']['losses']) * 100, 1)
                                            if (court_stats[f'court{court_num}']['wins'] + court_stats[f'court{court_num}']['losses']) > 0 else 0,
                            'key_players': [
                                {
                                    'name': player['name'],
                                    'win_rate': round(player['win_rate'] * 100, 1),
                                    'matches': player['matches']
                                }
                                for player in court_stats[f'court{court_num}']['key_players']
                            ]
                        }
                        for court_num in range(1, 5)
                    }
                }
            
            return jsonify(stats_data)
            
        # If no team requested, filter stats by user's series
        user = session.get('user')
        if not user or not user.get('series'):
            return jsonify({'error': 'User series not found'}), 400
            
        # Filter stats for the user's series
        series_stats = [team for team in all_stats if team.get('series') == user['series']]
        return jsonify({'teams': series_stats})
        
    except Exception as e:
        print(f"Error reading series stats: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to read stats file'}), 500

@app.route('/api/player-contact')
@login_required  # Add login requirement for security
def get_player_contact():
    first_name = request.args.get('firstName')
    last_name = request.args.get('lastName')
    
    print(f"\n=== Getting Contact Info ===")
    print(f"First Name: {first_name}")
    print(f"Last Name: {last_name}")
    
    if not first_name or not last_name:
        return jsonify({'error': 'Missing first or last name parameter'}), 400
        
    try:
        # Search the club directory CSV for the player
        import pandas as pd
        directory_path = os.path.join('data', 'club_directories', 'directory_tennaqua.csv')
        df = pd.read_csv(directory_path)
        # The columns are: Series,Last Name,First,Email,Phone
        player = df[
            (df['First'].str.lower() == first_name.lower()) & \
            (df['Last Name'].str.lower() == last_name.lower())
        ]
        if not player.empty:
            email = player.iloc[0]['Email'] if pd.notnull(player.iloc[0]['Email']) else 'Not available'
            phone = player.iloc[0]['Phone'] if pd.notnull(player.iloc[0]['Phone']) else 'Not available'
            return jsonify({
                'email': email,
                'phone': phone
            })
        else:
            print(f"Player not found in directory: {first_name} {last_name}")
            return jsonify({'error': 'Player not found in the club directory'}), 404
    except Exception as e:
        print(f"Error fetching player contact info: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

# Initialize paths
app_dir = os.path.dirname(os.path.abspath(__file__))
matches_path = os.path.join(app_dir, 'data', 'match_history.json')
players_path = os.path.join(app_dir, 'data', 'players.json')

@app.route('/api/players')
@login_required
def get_players_by_series():
    """Get all players for a specific series, optionally filtered by team and club"""
    try:
        # Get series and optional team from query parameters
        series = request.args.get('series')
        team_id = request.args.get('team_id')
        
        if not series:
            return jsonify({'error': 'Series parameter is required'}), 400
            
        print(f"\n=== DEBUG: get_players_by_series ===")
        print(f"Requested series: {series}")
        print(f"Requested team: {team_id}")
        print(f"User series: {session['user'].get('series')}")
        print(f"User club: {session['user'].get('club')}")
            
        # Load player data
        with open(players_path, 'r') as f:
            all_players = json.load(f)
            
        # Load matches data if team filtering is needed
        team_players = set()
        if team_id and os.path.exists(matches_path):
            try:
                with open(matches_path, 'r') as f:
                    matches = json.load(f)
                # Get all players who have played for this team
                for match in matches:
                    if match['Home Team'] == team_id:
                        team_players.add(match['Home Player 1'])
                        team_players.add(match['Home Player 2'])
                    elif match['Away Team'] == team_id:
                        team_players.add(match['Away Player 1'])
                        team_players.add(match['Away Player 2'])
            except Exception as e:
                print(f"Warning: Error loading matches data: {str(e)}")
                # Continue without team filtering if matches data can't be loaded
                team_id = None
        
        # Get user's club from session
        user_club = session['user'].get('club')
        
        # Filter players by series, team if specified, and club
        players = []
        for player in all_players:
            # Use our new series matching functionality
            if series_match(player['Series'], series):
                # Create player name in the same format as match data
                player_name = f"{player['First Name']} {player['Last Name']}"
                
                # If team_id is specified, only include players from that team
                if not team_id or player_name in team_players:
                    # Only include players from the same club as the user
                    if player['Club'] == user_club:
                        players.append({
                            'name': player_name,
                            'series': normalize_series_for_storage(player['Series']),  # Normalize series format
                            'rating': str(player['PTI']),
                            'wins': str(player['Wins']),
                            'losses': str(player['Losses']),
                            'winRate': player['Win %']
                        })
            
        print(f"Found {len(players)} players in {series}{' for team ' + team_id if team_id else ''} and club {user_club}")
        print("=== END DEBUG ===\n")
        return jsonify(players)
        
    except Exception as e:
        print(f"\nERROR getting players for series {series}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/team-players/<team_id>')
@login_required
def get_team_players(team_id):
    """Get all players for a specific team"""
    try:
        # Load player PTI data from JSON
        players_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'players.json')
        with open(players_path, 'r') as f:
            all_players = json.load(f)
        
        pti_dict = {}
        for player in all_players:
            player_name = f"{player['Last Name']} {player['First Name']}"
            pti_dict[player_name] = float(player['PTI'])
            
        with open(matches_path, 'r') as f:
            matches = json.load(f)
            
        # Rest of the function remains the same...
        # Track unique players and their stats
        players = {}
        
        # Group matches by date to determine court numbers
        date_matches = {}
        for match in matches:
            if match['Home Team'] == team_id or match['Away Team'] == team_id:
                date = match['Date']
                if date not in date_matches:
                    date_matches[date] = []
                date_matches[date].append(match)
        
        # Process each match day
        for date, day_matches in date_matches.items():
            # Sort matches to ensure consistent court assignment
            day_matches.sort(key=lambda x: (x['Date'], x['Home Team'], x['Away Team']))
            
            # Process each match with its court number
            for court_num, match in enumerate(day_matches, 1):
                is_home = match['Home Team'] == team_id
                
                # Get players from this match
                if is_home:
                    match_players = [
                        {'name': match['Home Player 1'], 'team': 'home', 'partner': match['Home Player 2']},
                        {'name': match['Home Player 2'], 'team': 'home', 'partner': match['Home Player 1']}
                    ]
                else:
                    match_players = [
                        {'name': match['Away Player 1'], 'team': 'away', 'partner': match['Away Player 2']},
                        {'name': match['Away Player 2'], 'team': 'away', 'partner': match['Away Player 1']}
                    ]
                
                # Determine if this court was won
                won_match = (is_home and match['Winner'] == 'home') or \
                           (not is_home and match['Winner'] == 'away')
                
                # Update player stats
                for player in match_players:
                    name = player['name']
                    partner = player['partner']
                    if name not in players:
                        players[name] = {
                            'name': name,
                            'matches': 0,
                            'wins': 0,
                            'pti': pti_dict.get(name, 'N/A'),
                            'courts': {
                                'court1': {'matches': 0, 'wins': 0, 'partners': {}},
                                'court2': {'matches': 0, 'wins': 0, 'partners': {}},
                                'court3': {'matches': 0, 'wins': 0, 'partners': {}},
                                'court4': {'matches': 0, 'wins': 0, 'partners': {}}
                            }
                        }
                    
                    # Update overall stats
                    players[name]['matches'] += 1
                    if won_match:
                        players[name]['wins'] += 1
                    
                    # Update court-specific stats and partner tracking
                    court_key = f'court{court_num}'
                    court_stats = players[name]['courts'][court_key]
                    court_stats['matches'] += 1
                    if won_match:
                        court_stats['wins'] += 1
                    
                    # Update partner stats
                    if partner not in court_stats['partners']:
                        court_stats['partners'][partner] = {
                            'matches': 0,
                            'wins': 0
                        }
                    court_stats['partners'][partner]['matches'] += 1
                    if won_match:
                        court_stats['partners'][partner]['wins'] += 1
        
        # Convert to list and calculate win rates
        players_list = []
        for player_stats in players.values():
            # Calculate overall win rate
            win_rate = player_stats['wins'] / player_stats['matches'] if player_stats['matches'] > 0 else 0
            
            # Calculate court-specific win rates and process partner stats
            court_stats = {}
            for court_key, stats in player_stats['courts'].items():
                if stats['matches'] > 0:
                    # Sort partners by number of matches played together
                    partners_list = []
                    for partner, partner_stats in stats['partners'].items():
                        partner_win_rate = partner_stats['wins'] / partner_stats['matches'] if partner_stats['matches'] > 0 else 0
                        partners_list.append({
                            'name': partner,
                            'matches': partner_stats['matches'],
                            'wins': partner_stats['wins'],
                            'winRate': round(partner_win_rate * 100, 1)
                        })
                    
                    # Sort partners by matches played (descending)
                    partners_list.sort(key=lambda x: x['matches'], reverse=True)
                    
                    court_stats[court_key] = {
                        'matches': stats['matches'],
                        'wins': stats['wins'],
                        'winRate': round(stats['wins'] / stats['matches'] * 100, 1),
                        'partners': partners_list[:3]  # Return top 3 most common partners
                    }
                else:
                    court_stats[court_key] = {
                        'matches': 0,
                        'wins': 0,
                        'winRate': 0,
                        'partners': []
                    }
            
            players_list.append({
                'name': player_stats['name'],
                'matches': player_stats['matches'],
                'wins': player_stats['wins'],
                'winRate': round(win_rate * 100, 1),
                'pti': player_stats['pti'],
                'courts': court_stats
            })
        
        # Sort by matches played (descending) and then name
        players_list.sort(key=lambda x: (-x['matches'], x['name']))
        
        return jsonify({'players': players_list})
        
    except Exception as e:
        print(f"Error getting team players: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-settings', methods=['POST'])
@login_required
def update_settings():
    try:
        data = request.get_json()
        # print("\n=== UPDATING USER SETTINGS ===")
        # print("Received data:", data)
        # print("clubAutomationPassword received:", data.get('clubAutomationPassword', '[not present]'))
        
        if not all(key in data for key in ['firstName', 'lastName', 'email', 'series', 'club']):
            # print("Missing required fields in request data")
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        current_email = session['user']['email']
        # print(f"Updating settings for user: {current_email}")
        
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get series ID
            cursor.execute('SELECT id FROM series WHERE name = ?', (data['series'],))
            series_result = cursor.fetchone()
            if not series_result:
                # print(f"Series not found: {data['series']}")
                return jsonify({'success': False, 'message': 'Invalid series selected'}), 400
            series_id = series_result[0]
            
            # Get club ID
            cursor.execute('SELECT id FROM clubs WHERE name = ?', (data['club'],))
            club_result = cursor.fetchone()
            if not club_result:
                # print(f"Club not found: {data['club']}")
                return jsonify({'success': False, 'message': 'Invalid club selected'}), 400
            club_id = club_result[0]
            
            # Optionally update club_automation_password if provided
            if 'clubAutomationPassword' in data and data['clubAutomationPassword'] is not None:
                # print("Updating club_automation_password to:", data.get('clubAutomationPassword', ''))
                # print("[DEBUG] SQL UPDATE with club_automation_password:")
                # print("SQL:", '''UPDATE users SET first_name = ?, last_name = ?, email = ?, series_id = ?, club_id = ?, club_automation_password = ? WHERE email = ?''')
                # print("Values:", data['firstName'], data['lastName'], data['email'], series_id, club_id, data.get('clubAutomationPassword', ''), current_email)
                cursor.execute('''
                    UPDATE users 
                    SET first_name = ?, last_name = ?, email = ?, series_id = ?, club_id = ?, club_automation_password = ?
                    WHERE email = ?
                ''', (
                    data['firstName'],
                    data['lastName'],
                    data['email'],
                    series_id,
                    club_id,
                    data.get('clubAutomationPassword', ''),
                    current_email
                ))
            else:
                # print("[DEBUG] SQL UPDATE without club_automation_password:")
                # print("SQL:", '''UPDATE users SET first_name = ?, last_name = ?, email = ?, series_id = ?, club_id = ? WHERE email = ?''')
                # print("Values:", data['firstName'], data['lastName'], data['email'], series_id, club_id, current_email)
                cursor.execute('''
                    UPDATE users 
                    SET first_name = ?, last_name = ?, email = ?, series_id = ?, club_id = ?
                    WHERE email = ?
                ''', (
                    data['firstName'],
                    data['lastName'],
                    data['email'],
                    series_id,
                    club_id,
                    current_email
                ))
            
            if cursor.rowcount == 0:
                # print("No rows were updated - user not found")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            conn.commit()
            # print("Settings updated successfully")
            
            # Update session data
            session['user'] = {
                'email': data['email'],
                'first_name': data['firstName'],
                'last_name': data['lastName'],
                'club': data['club'],
                'series': data['series']
            }
            
            # Get updated user data
            cursor.execute('''
                SELECT u.first_name, u.last_name, u.email, c.name as club_name, s.name as series_name
                FROM users u
                JOIN clubs c ON u.club_id = c.id
                JOIN series s ON u.series_id = s.id
                WHERE u.email = ?
            ''', (data['email'],))
            
            updated_user = cursor.fetchone()
            if updated_user:
                return jsonify({
                    'success': True,
                    'message': 'Settings updated successfully',
                    'user': {
                        'first_name': updated_user[0],
                        'last_name': updated_user[1],
                        'email': updated_user[2],
                        'club': updated_user[3],
                        'series': updated_user[4]
                    }
                })
            else:
                return jsonify({'success': True, 'message': 'Settings updated successfully'})
            
        except sqlite3.Error as e:
            # print(f"Database error: {str(e)}")
            conn.rollback()
            return jsonify({'success': False, 'message': 'Database error occurred'}), 500
            
        finally:
            conn.close()
            
    except Exception as e:
        # print(f"Error updating settings: {str(e)}")
        # import traceback
        # print("Full error:", traceback.format_exc())
        return jsonify({'success': False, 'message': 'Failed to update settings'}), 500

@app.route('/test-static')
def test_static():
    """Test route to verify static file serving"""
    try:
        return send_from_directory('static', 'rallylogo.png')
    except Exception as e:
        return str(e), 500

@app.route('/api/admin/delete-user', methods=['POST'])
@login_required
def delete_user():
    """Delete a user from the database"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
            
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Delete user
            cursor.execute('DELETE FROM users WHERE email = ?', (email,))
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'User not found'}), 404
                
            # Also delete any related data
            cursor.execute('DELETE FROM user_instructions WHERE user_email = ?', (email,))
            cursor.execute('DELETE FROM player_availability WHERE player_name = ?', (email,))
            
            conn.commit()
            return jsonify({'status': 'success', 'message': 'User deleted successfully'})
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

def log_user_activity(user_email, activity_type, page=None, action=None, details=None):
    """Log user activity to the database"""
    # print(f"\n=== LOGGING USER ACTIVITY ===")
    # print(f"User: {user_email}")
    # print(f"Type: {activity_type}")
    # print(f"Page: {page}")
    # print(f"Action: {action}")
    # print(f"Details: {details}")
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            # Get IP address from request if available
            ip_address = request.remote_addr if request else None
            # print(f"IP Address: {ip_address}")
            # Insert the activity log with UTC timestamp
            # print("Inserting activity log...")
            insert_query = '''
                INSERT INTO user_activity_logs 
                (user_email, activity_type, page, action, details, ip_address, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            '''
            params = (user_email, activity_type, page, action, details, ip_address)
            # print(f"Query: {insert_query}")
            # print(f"Parameters: {params}")
            
            cursor.execute(insert_query, params)
            conn.commit()
            # print("Activity logged successfully")
            
            # Verify the log was written
            # print("Verifying log entry...")
            cursor.execute('''
                SELECT * FROM user_activity_logs 
                WHERE user_email = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (user_email,))
            last_log = cursor.fetchone()
            if last_log:
                # print(f"Last log entry: {last_log}")
                pass
            else:
                # print("WARNING: Log entry not found after insert!")
                pass
        finally:
            conn.close()
                    
    except Exception as e:
        # print(f"Database error during transaction: {str(e)}")
        # print(f"Error type: {type(e).__name__}")
        # print(f"Full error details: {traceback.format_exc()}")
        raise

@app.route('/api/admin/user-activity/<email>')
@login_required
def get_user_activity(email):
    """Get activity logs for a specific user"""
    try:
        print(f"\n=== Getting Activity for User: {email} ===")
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get user details first
            print("Fetching user details...")
            cursor.execute('''
                SELECT first_name, last_name, email, last_login
                FROM users
                WHERE email = ?
            ''', (email,))
            user = cursor.fetchone()
            
            if not user:
                print(f"User not found: {email}")
                return jsonify({'error': 'User not found'}), 404
                
            print(f"Found user: {user[0]} {user[1]}")
                
            # Get activity logs with explicit timestamp ordering
            print("Fetching activity logs...")
            cursor.execute('''
                SELECT id, activity_type, page, action, details, ip_address, 
                       datetime(timestamp, '-5 hours') || '.000-05:00' as central_time
                FROM user_activity_logs
                WHERE user_email = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1000
            ''', (email,))
            
            logs = []
            print("\nMost recent activities:")
            for idx, row in enumerate(cursor.fetchall()):
                if idx < 5:  # Print details of 5 most recent activities
                    print(f"ID: {row[0]}, Type: {row[1]}, Time: {row[6]}")
                
                logs.append({
                    'id': row[0],
                    'activity_type': row[1],
                    'page': row[2],
                    'action': row[3],
                    'details': row[4],
                    'ip_address': row[5],
                    'timestamp': row[6]  # Send UTC time to frontend
                })
            
            print(f"\nFound {len(logs)} activity logs")
            if logs:
                print(f"Most recent log ID: {logs[0]['id']}")
                print(f"Most recent timestamp: {logs[0]['timestamp']}")
            
            response_data = {
                'user': {
                    'first_name': user[0],
                    'last_name': user[1],
                    'email': user[2],
                    'last_login': user[3]
                },
                'activities': logs
            }
            
            print("Returning response data")
            print("=== End Activity Request ===\n")
            
            # Create response with cache-busting headers
            response = jsonify(response_data)
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error getting user activity: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/user-activity')
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

@app.route('/test-activity')
@login_required
def test_activity():
    """Test route to verify activity logging"""
    try:
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
            
        user_email = session['user']['email']
        log_user_activity(
            user_email,
            'test',
            page='test_page',
            action='test_action',
            details='Testing activity logging'
        )
        
        # Try to read back the test activity
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM user_activity_logs 
                WHERE user_email = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (user_email,))
            
            last_log = cursor.fetchone()
            
            if last_log:
                return jsonify({
                    'status': 'success',
                    'message': 'Activity logged successfully',
                    'last_log': {
                        'id': last_log[0],
                        'user_email': last_log[1],
                        'activity_type': last_log[2],
                        'page': last_log[3],
                        'action': last_log[4],
                        'details': last_log[5],
                        'ip_address': last_log[6],
                        'timestamp': last_log[7]
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Activity was not logged'
                }), 500
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error in test route: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/test-log', methods=['GET'])
@login_required
def test_log():
    """Test endpoint to verify activity logging"""
    try:
        user_email = session['user']['email']
        print(f"\n=== Testing Activity Log ===")
        print(f"User: {user_email}")
        
        # Try to log a test activity
        log_user_activity(
            user_email,
            'test',
            page='test_page',
            action='test_action',
            details='Manual test of activity logging'
        )
        
        # Verify the log was written
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM user_activity_logs 
                WHERE user_email = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (user_email,))
            
            last_log = cursor.fetchone()
            
            if last_log:
                return jsonify({
                    'status': 'success',
                    'message': 'Activity logged successfully',
                    'log': {
                        'id': last_log[0],
                        'email': last_log[1],
                        'type': last_log[2],
                        'page': last_log[3],
                        'action': last_log[4],
                        'details': last_log[5],
                        'ip': last_log[6],
                        'timestamp': last_log[7]
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Activity was not logged'
                }), 500
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error in test endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/verify-logging')
@login_required
def verify_logging():
    """Test endpoint to verify logging system"""
    try:
        user_email = session['user']['email']
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n=== Testing Logging System ===")
        print(f"User: {user_email}")
        print(f"Timestamp: {timestamp}")
        
        # Try to log a test activity
        log_user_activity(
            user_email,
            'test',
            page='verify_logging',
            action='test_logging',
            details=f'Verifying logging system at {timestamp}'
        )
        
        # Verify the log was written
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM user_activity_logs 
                WHERE user_email = ? AND activity_type = 'test'
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (user_email,))
            
            last_log = cursor.fetchone()
            
            if last_log:
                return jsonify({
                    'status': 'success',
                    'message': 'Logging system verified',
                    'log': {
                        'id': last_log[0],
                        'email': last_log[1],
                        'type': last_log[2],
                        'page': last_log[3],
                        'action': last_log[4],
                        'details': last_log[5],
                        'timestamp': last_log[7]
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Log entry not found after writing'
                }), 500
                
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error in verify logging: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/log-click', methods=['POST'])
def log_click():
    """Log a user's click on the page"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        element_id = data.get('elementId')
        element_text = data.get('elementText')
        element_type = data.get('elementType', 'button')
        page_url = data.get('pageUrl')
        
        # Extract page name from URL
        page_name = os.path.splitext(os.path.basename(page_url))[0] if page_url else None
        
        # Create descriptive details
        details = f"Clicked {element_type}"
        if element_id:
            details += f" with id '{element_id}'"
        if element_text:
            details += f" containing text '{element_text}'"
        
        # Only log if user is in session
        if 'user' in session:
            log_user_activity(
                session['user']['email'],
                'click',
                page=page_name,
                action='click',
                details=details
            )
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error logging click: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Add a basic healthcheck endpoint
@app.route('/health')
def healthcheck():
    """Basic healthcheck endpoint that also verifies database connection"""
    try:
        # Test database connection
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddlepro.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Try to execute a simple query
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] == 1:
            # Database connection successful
            return jsonify({
                'status': 'ok',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Database query failed',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        print(f"Healthcheck error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/team-matches')
@login_required
def get_team_matches():
    """Return matches for a specific team"""
    try:
        team = request.args.get('team')
        if not team:
            return jsonify({'error': 'Team parameter is required'}), 400
        
        # Log the request
        print(f"Fetching matches for team: {team}")
        log_user_activity(
            session['user']['email'], 
            'feature_use', 
            action='view_team_matches',
            details=f"Team: {team}"
        )
        
        # Read the matches file
        matches_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_history.json')
        with open(matches_path, 'r') as f:
            all_matches = json.load(f)
        
        # Filter matches for the specific team
        team_matches = [match for match in all_matches if match.get('Home Team') == team or match.get('Away Team') == team]
        
        return jsonify(team_matches)
    except Exception as e:
        print(f"Error fetching team matches: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/data/<path:filename>')
def serve_data_file(filename):
    """Serve files from the data directory"""
    print(f"=== /data/{filename} requested ===")
    
    # Restrict to only serving .json files for security
    if not filename.endswith('.json'):
        print(f"Request rejected - not a JSON file: {filename}")
        return "Not found", 404
    
    # Create the full path
    data_path = os.path.join(app.root_path, 'data')
    full_path = os.path.join(data_path, filename)
    
    # Check if the file exists
    if not os.path.exists(full_path):
        print(f"ERROR: File does not exist: {full_path}")
        # List available files for debugging
        try:
            available_files = [f for f in os.listdir(data_path) if f.endswith('.json')]
            print(f"Available JSON files in data directory: {available_files}")
        except Exception as e:
            print(f"Error listing data directory: {e}")
        return "File not found", 404
    
    # Log the access
    if 'user' in session:
        log_user_activity(
            session['user']['email'], 
            'data_access', 
            action='view_data_file',
            details=f"File: {filename}"
        )
    
    print(f"Serving data file: {filename}")
    # Return the file from the data directory
    return send_from_directory(os.path.join(app.root_path, 'data'), filename)

def transform_team_stats_to_overview(stats):
    matches = stats.get("matches", {})
    lines = stats.get("lines", {})
    sets = stats.get("sets", {})
    games = stats.get("games", {})
    points = stats.get("points", 0)
    overview = {
        "points": points,
        "match_win_rate": float(matches.get("percentage", "0").replace("%", "")),
        "match_record": f"{matches.get('won', 0)}-{matches.get('lost', 0)}",
        "line_win_rate": float(lines.get("percentage", "0").replace("%", "")),
        "set_win_rate": float(sets.get("percentage", "0").replace("%", "")),
        "game_win_rate": float(games.get("percentage", "0").replace("%", ""))
    }
    return overview

@app.route('/api/research-team')
@login_required
def research_team():
    """Return stats for a specific team (for research team page)"""
    try:
        team = request.args.get('team')
        if not team:
            return jsonify({'error': 'Team parameter is required'}), 400
        # Log the request
        print(f"Fetching stats for team: {team}")
        log_user_activity(
            session['user']['email'], 
            'feature_use', 
            action='view_team_stats',
            details=f"Team: {team}"
        )
        # Read the stats file
        stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'series_stats.json')
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
        # Find stats for the specific team
        team_stats = next((stats for stats in all_stats if stats.get('team') == team), None)
        if not team_stats:
            return jsonify({'error': f'No stats found for team: {team}'}), 404
        # Transform to nested format for My Team page
        response = {
            "overview": transform_team_stats_to_overview(team_stats),
            "match_patterns": {}  # You can fill this in later if you want
        }
        return jsonify(response)
    except Exception as e:
        print(f"Error fetching team stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

# --- New endpoint: Player Court Stats from JSON ---
@app.route('/api/player-court-stats/<player_name>')
def player_court_stats(player_name):
    """
    Returns court breakdown stats for a player using data/match_history.json.
    """
    import os
    import json
    from collections import defaultdict, Counter
    
    print(f"=== /api/player-court-stats called for player: {player_name} ===")
    
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_history.json')
    print(f"Loading match data from: {json_path}")
    
    try:
        with open(json_path, 'r') as f:
            matches = json.load(f)
        print(f"Successfully loaded {len(matches)} matches")
    except Exception as e:
        print(f"ERROR: Failed to load match data: {e}")
        return jsonify({"error": f"Failed to load match data: {e}"}), 500

    # Group matches by date
    matches_by_date = defaultdict(list)
    for match in matches:
        matches_by_date[match['Date']].append(match)
    
    print(f"Grouped matches for {len(matches_by_date)} different dates")

    # For each date, assign court number by order
    court_matches = defaultdict(list)  # court_num (1-based) -> list of matches for this player
    player_match_count = 0
    
    for date, day_matches in matches_by_date.items():
        for i, match in enumerate(day_matches):
            court_num = i + 1
            # Check if player is in this match
            if player_name in [match['Home Player 1'], match['Home Player 2'], match['Away Player 1'], match['Away Player 2']]:
                court_matches[court_num].append(match)
                player_match_count += 1
    
    print(f"Found {player_match_count} matches for player {player_name}")
    print(f"Matches by court: {', '.join([f'Court {k}: {len(v)}' for k, v in court_matches.items()])}")

    # For each court, calculate stats
    result = {}
    for court_num in range(1, 5):  # Courts 1-4
        matches = court_matches.get(court_num, [])
        num_matches = len(matches)
        wins = 0
        losses = 0
        partners = []
        partner_results = defaultdict(lambda: {'matches': 0, 'wins': 0})

        for match in matches:
            # Determine if player was home or away, and who was their partner
            if player_name == match['Home Player 1']:
                partner = match['Home Player 2']
                is_home = True
            elif player_name == match['Home Player 2']:
                partner = match['Home Player 1']
                is_home = True
            elif player_name == match['Away Player 1']:
                partner = match['Away Player 2']
                is_home = False
            elif player_name == match['Away Player 2']:
                partner = match['Away Player 1']
                is_home = False
            else:
                continue  # Shouldn't happen
            partners.append(partner)
            partner_results[partner]['matches'] += 1
            # Determine win/loss
            if (is_home and match['Winner'] == 'home') or (not is_home and match['Winner'] == 'away'):
                wins += 1
                partner_results[partner]['wins'] += 1
            else:
                losses += 1
                
        # Win rate
        win_rate = (wins / num_matches * 100) if num_matches > 0 else 0.0
        # Most common partners
        partner_list = []
        for partner, stats in sorted(partner_results.items(), key=lambda x: -x[1]['matches']):
            p_matches = stats['matches']
            p_wins = stats['wins']
            p_win_rate = (p_wins / p_matches * 100) if p_matches > 0 else 0.0
            partner_list.append({
                'name': partner,
                'matches': p_matches,
                'wins': p_wins,
                'winRate': round(p_win_rate, 1)
            })
        result[f'court{court_num}'] = {
            'matches': num_matches,
            'wins': wins,
            'losses': losses,
            'winRate': round(win_rate, 1),
            'partners': partner_list
        }
    
    print(f"Returning court stats for {player_name}: {len(result)} courts")
    return jsonify(result)

@app.route('/api/research-my-team')
@login_required
def research_my_team():
    print("=== /api/research-my-team called ===")
    user = None
    if hasattr(g, 'user') and g.user:
        user = g.user
    else:
        from flask import session
        user = session.get('user')
        print("Session user:", user)
        if not user:
            print("No user in session, trying /api/check-auth")
            from flask import request
            import requests
            try:
                resp = requests.get(request.host_url.rstrip('/') + '/api/check-auth', cookies=request.cookies)
                if resp.ok:
                    user = resp.json().get('user')
            except Exception as e:
                print("Exception fetching /api/check-auth:", e)
                user = None
    print("User:", user)
    if not user:
        print("Not authenticated")
        return jsonify({'error': 'Not authenticated'}), 401
    team = user.get('team')
    print("Team from user:", team)
    if not team:
        club = user.get('club')
        series = user.get('series')
        print("Club:", club, "Series:", series)
        if club and series:
            m = re.search(r'(\d+)', series)
            series_num = m.group(1) if m else ''
            team = f"{club} - {series_num}"
        else:
            print("No team info for user")
            return jsonify({'error': 'No team info for user'}), 400
    print("Final team:", team)
    # Fetch stats for this team (same as /api/research-team)
    try:
        stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'series_stats.json')
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
        team_stats = next((stats for stats in all_stats if stats.get('team') == team), None)
        if not team_stats:
            print(f"No stats found for team: {team}")
            return jsonify({'error': f'No stats found for team: {team}'}), 404
        response = {
            "overview": transform_team_stats_to_overview(team_stats),
            "match_patterns": {}  # You can fill this in later if you want
        }
        print("Returning response for /api/research-my-team:", response)
        return jsonify(response)
    except Exception as e:
        print(f"Error fetching team stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/mobile')
@login_required
def serve_mobile():
    """Serve the mobile version of the application"""
    # Create session data script
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    # Log mobile access
    try:
        log_user_activity(
            session['user']['email'], 
            'page_visit', 
            page='mobile_home',
            details='Accessed mobile home page'
        )
    except Exception as e:
        print(f"Error logging mobile home page visit: {str(e)}")
    
    return render_template('mobile/index.html', session_data=session_data)

@app.route('/mobile/rally')
@login_required
def serve_rally_mobile():
    """Serve the new rally mobile interface"""
    # Create session data script
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    # Log mobile access
    try:
        log_user_activity(
            session['user']['email'], 
            'page_visit', 
            page='rally_mobile',
            details='Accessed new rally mobile interface'
        )
    except Exception as e:
        print(f"Error logging rally mobile page visit: {str(e)}")
    
    return render_template('rally_mobile.html', session_data=session_data)

@app.route('/mobile/matches')
@login_required
def serve_mobile_matches():
    """Serve the mobile matches page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_matches')
    return render_template('mobile/matches.html', session_data=session_data)

@app.route('/mobile/rankings')
@login_required
def serve_mobile_rankings():
    """Serve the mobile rankings page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_rankings')
    return render_template('mobile/rankings.html', session_data=session_data)

@app.route('/mobile/profile')
@login_required
def serve_mobile_profile():
    """Serve the mobile profile page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_profile')
    return render_template('mobile/profile.html', session_data=session_data)

@app.route('/mobile/lineup')
@login_required
def serve_mobile_lineup():
    """Serve the mobile lineup page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_lineup')
    return render_template('mobile/lineup.html', session_data=session_data)

@app.route('/mobile/lineup-escrow')
@login_required
def serve_mobile_lineup_escrow():
    """Serve the mobile Lineup Escrow page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    log_user_activity(
        session['user']['email'],
        'page_visit',
        page='mobile_lineup_escrow',
        details='Accessed mobile lineup escrow page'
    )
    return render_template('mobile/lineup_escrow.html', session_data=session_data)

@app.route('/mobile/player-detail/<player_id>')
@login_required
def serve_mobile_player_detail(player_id):
    """Serve the mobile player detail page (server-rendered, consistent with other mobile pages)"""
    from urllib.parse import unquote
    player_name = unquote(player_id)
    analyze_data = get_player_analysis_by_name(player_name)
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    log_user_activity(
        session['user']['email'], 
        'page_visit', 
        page='mobile_player_detail',
        details=f'Viewed player {player_name}'
    )
    return render_template('mobile/player_detail.html', 
                          session_data=session_data, 
                          analyze_data=analyze_data,
                          player_name=player_name)

@app.route('/white-text-fix.html')
def serve_white_text_fix():
    return send_from_directory('.', 'white-text-fix.html')



def get_user_availability(player_name, matches, series):
    availability = []
    for match in matches:
        match_date = match.get('date', '')
        is_available = get_player_availability(player_name, match_date, series)
        if is_available is None:
            status = 'unknown'
        elif is_available:
            status = 'available'
        else:
            status = 'unavailable'
        availability.append({'status': status})
    return availability

@app.route('/mobile/availability', methods=['GET', 'POST'])
@login_required
def mobile_availability():
    user = session.get('user')
    player_name = f"{user['first_name']} {user['last_name']}"
    series = user['series']

    # 1. Get matches for the user's club/series
    matches = get_matches_for_user_club(user)

    # 2. Get this user's availability for each match
    player_availability = get_user_availability(player_name, matches, series)

    # 3. Prepare data for the template
    players = [{
        'name': player_name,
        'availability': player_availability
    }]
    match_objs = [
        {
            'date': m.get('date', ''),
            'time': m.get('time', ''),
            'location': m.get('location', m.get('home_team', '')),
            'home_team': m.get('home_team', ''),
            'away_team': m.get('away_team', '')
        }
        for m in matches
    ]
    # Zip matches and availability for template
    match_avail_pairs = list(zip(match_objs, player_availability))

    return render_template(
        'mobile/availability.html',
        players=players,
        matches=match_objs,
        match_avail_pairs=match_avail_pairs,
        session_data={'user': user},
        user=user,  # Add user to the template context
        zip=zip
    )

@app.route('/mobile/find-subs')
@login_required
def serve_mobile_find_subs():
    """Serve the mobile Find Sub page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_find_subs')
    return render_template('mobile/find_subs.html', session_data=session_data)

@app.route('/mobile/view-schedule')
@login_required
def mobile_view_schedule():
    """Serve the mobile View Schedule page with the user's schedule."""
    from datetime import datetime
    user = session['user']
    matches = get_matches_for_user_club(user)
    
    # Sort matches by date
    try:
        matches = sorted(matches, key=lambda x: datetime.strptime(x['date'], '%d-%b-%y'))
    except Exception as e:
        print(f"Error sorting matches: {e}")
        matches = sorted(matches, key=lambda x: x['date'])
    
    # Add formatted_date to each match
    for match in matches:
        try:
            # Convert date to datetime object
            dt = datetime.strptime(match['date'], '%d-%b-%y')
            # Format for display
            match['formatted_date'] = f"{dt.strftime('%A')} {dt.month}/{dt.day}/{dt.strftime('%y')}"
        except Exception as e:
            print(f"Error formatting date {match.get('date')}: {e}")
            match['formatted_date'] = match.get('date', '')
            
        # Ensure all required fields exist
        match.setdefault('time', '')
        match.setdefault('location', '')
        match.setdefault('home_team', '')
        match.setdefault('away_team', '')
        
        # Add practice flag if needed
        match['is_practice'] = 'Practice' in match.get('type', '')
    
    return render_template(
        'mobile/view_schedule.html',
        matches=matches,
        user=user,
        session_data={'user': user}
    )

@app.route('/mobile/ask-ai')
@login_required
def mobile_ask_ai():
    user = session['user']
    return render_template('mobile/ask_ai.html', user=user, session_data={'user': user})

@app.template_filter('pretty_date')
def pretty_date(value):
    """
    Jinja2 filter to format a date string (YYYY-MM-DD or MM/DD/YYYY) as 'Tuesday 9/24/24'.
    """
    from datetime import datetime
    if not value:
        return ''
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            dt = datetime.strptime(value, fmt)
            return f"{dt.strftime('%A')} {dt.month}/{dt.day}/{dt.strftime('%y')}"
        except Exception:
            continue
    return value  # fallback if parsing fails

def get_player_analysis(user):
    """
    Returns the player analysis data for the given user, as a dict.
    Uses match_history.json for current season stats and court analysis,
    and series_22_player_history.json for career stats and player history.
    Always returns all expected keys, even if some are None or empty.
    """
    import os, json
    from collections import defaultdict, Counter
    player_name = f"{user['first_name']} {user['last_name']}"
    print(f"[DEBUG] Looking for player: '{player_name}'")  # Debug print
    player_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'player_history.json')
    matches_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_history.json')

    # --- 1. Load player history for career stats and previous seasons ---
    try:
        with open(player_history_path, 'r') as f:
            all_players = json.load(f)
    except Exception as e:
        return {
            'current_season': None,
            'court_analysis': {},
            'career_stats': None,
            'player_history': None,
            'videos': {'match': [], 'practice': []},
            'trends': {},
            'career_pti_change': 'N/A',
            'error': f'Could not load player history: {e}'
        }
    def normalize(name):
        return name.replace(',', '').replace('  ', ' ').strip().lower()
    player_name_normal = normalize(player_name)
    player_last_first = normalize(f"{user['last_name']}, {user['first_name']}")
    print(f"[DEBUG] Normalized search names: '{player_name_normal}', '{player_last_first}'")  # Debug print
    player = None
    for p in all_players:
        n = normalize(p.get('name', ''))
        print(f"[DEBUG] Player in file: '{n}' (original: '{p.get('name', '')}')")  # Debug print
        if n == player_name_normal or n == player_last_first:
            print(f"[DEBUG] Match found for player: '{n}'")  # Debug print
            player = p
            break
    # --- 2. Load all matches for this player ---
    try:
        with open(matches_path, 'r') as f:
            all_matches = json.load(f)
    except Exception as e:
        all_matches = []
    # --- 3. Determine current season (latest in player history) ---
    current_season_info = None
    if player and player.get('seasons') and player['seasons']:
        current_season_info = player['seasons'][-1]
        current_series = str(current_season_info.get('series', ''))
    else:
        matches_with_series = [m for m in player.get('matches', []) if 'series' in m and 'date' in m] if player else []
        if matches_with_series:
            import datetime
            def parse_date(d):
                for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                    try:
                        return datetime.datetime.strptime(d, fmt)
                    except Exception:
                        continue
                return None
            matches_with_series_sorted = sorted(matches_with_series, key=lambda m: parse_date(m['date']) or m['date'], reverse=True)
            current_series = matches_with_series_sorted[0]['series']
        else:
            current_series = None
    # --- 4. Filter matches for current season/series ---
    player_matches = []
    if player:
        for m in all_matches:
            if player_name in [m.get('Home Player 1'), m.get('Home Player 2'), m.get('Away Player 1'), m.get('Away Player 2')]:
                if current_series:
                    match_series = str(m.get('Series', ''))
                    if match_series and match_series != current_series:
                        continue
                player_matches.append(m)
    # --- 5. Assign matches to courts 1-4 by date and team pairing (CORRECTED LOGIC) ---
    matches_by_group = defaultdict(list)
    for match in all_matches:
        date = match.get('Date') or match.get('date')
        home_team = match.get('Home Team', '')
        away_team = match.get('Away Team', '')
        group_key = (date, home_team, away_team)
        matches_by_group[group_key].append(match)

    court_stats = {f'court{i}': {'matches': 0, 'wins': 0, 'losses': 0, 'partners': Counter()} for i in range(1, 5)}
    total_matches = 0
    wins = 0
    losses = 0
    pti_start = None
    pti_end = None

    for group_key in sorted(matches_by_group.keys()):
        day_matches = matches_by_group[group_key]
        # Sort all matches for this group for deterministic court assignment
        day_matches_sorted = sorted(day_matches, key=lambda m: (m.get('Home Team', ''), m.get('Away Team', '')))
        for i, match in enumerate(day_matches_sorted):
            court_num = i + 1
            if court_num > 4:
                continue
            # Check if player is in this match
            if player_name not in [match.get('Home Player 1'), match.get('Home Player 2'), match.get('Away Player 1'), match.get('Away Player 2')]:
                continue
            total_matches += 1
            is_home = player_name in [match.get('Home Player 1'), match.get('Home Player 2')]
            won = (is_home and match.get('Winner') == 'home') or (not is_home and match.get('Winner') == 'away')
            if won:
                wins += 1
                court_stats[f'court{court_num}']['wins'] += 1
            else:
                losses += 1
                court_stats[f'court{court_num}']['losses'] += 1
            court_stats[f'court{court_num}']['matches'] += 1
            # Identify partner
            if player_name == match.get('Home Player 1'):
                partner = match.get('Home Player 2')
            elif player_name == match.get('Home Player 2'):
                partner = match.get('Home Player 1')
            elif player_name == match.get('Away Player 1'):
                partner = match.get('Away Player 2')
            elif player_name == match.get('Away Player 2'):
                partner = match.get('Away Player 1')
            else:
                partner = None
            if partner:
                court_stats[f'court{court_num}']['partners'][partner] += 1
            if 'Rating' in match:
                if pti_start is None:
                    pti_start = match['Rating']
                pti_end = match['Rating']
    # --- 6. Build current season stats ---
    pti_change = 'N/A'
    if player and 'matches' in player:
        import datetime
        import re
        def parse_date(d):
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    return datetime.datetime.strptime(d, fmt)
                except Exception:
                    continue
            return None
        def normalize_series(x):
            return ''.join(re.findall(r'\d+', x or ''))
        cs = normalize_series(current_series) if 'current_series' in locals() and current_series else ''
        season_matches = [m for m in player['matches'] if 'series' in m and normalize_series(m['series']) == cs and 'end_pti' in m and 'date' in m]
        season_window_matches = []
        if season_matches:
            season_matches_sorted = sorted(season_matches, key=lambda m: parse_date(m['date']) or m['date'])
            latest_match_date = parse_date(season_matches_sorted[-1]['date'])
            if latest_match_date:
                if latest_match_date.month < 8:
                    season_start_year = latest_match_date.year - 1
                else:
                    season_start_year = latest_match_date.year
                season_start = datetime.datetime(season_start_year, 8, 1)
                season_end = datetime.datetime(season_start_year + 1, 3, 31)
                for m in season_matches:
                    pd = parse_date(m['date'])
                season_window_matches = [m for m in season_matches if parse_date(m['date']) and season_start <= parse_date(m['date']) <= season_end]
        if len(season_window_matches) >= 2:
            matches_for_pti_sorted = sorted(season_window_matches, key=lambda m: parse_date(m['date']))
            earliest_pti = matches_for_pti_sorted[0]['end_pti']
            latest_pti = matches_for_pti_sorted[-1]['end_pti']
            pti_change = round(latest_pti - earliest_pti, 1)
    win_rate = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0
    current_season = {
        'winRate': win_rate,
        'matches': total_matches,
        'wins': wins,  # Added: number of wins in current season
        'losses': losses,  # Added: number of losses in current season
        'ptiChange': pti_change
    }
    # --- 7. Build court analysis ---
    court_analysis = {}
    for court, stats in court_stats.items():
        matches = stats['matches']
        win_rate = round((stats['wins'] / matches) * 100, 1) if matches > 0 else 0
        record = f"{stats['wins']}-{stats['losses']}"
        # Only include winRate if partner has at least one match; otherwise, omit or set to None
        top_partners = []
        for p, c in stats['partners'].most_common(3):
            partner_entry = {'name': p, 'record': f"{c} matches"}
            if c > 0:
                # If you want to show win rate for partners, you can add it here in the future
                pass  # Not adding winRate if not available
            top_partners.append(partner_entry)
        court_analysis[court] = {
            'winRate': win_rate,
            'record': record,
            'topPartners': top_partners
        }
    # --- 8. Career stats and player history from player history file ---
    career_stats = None
    player_history = None
    if player:
        matches_val = player.get('matches', 0)
        wins_val = player.get('wins', 0)
        if isinstance(matches_val, list):
            total_career_matches = len(matches_val)
        else:
            total_career_matches = matches_val
        if isinstance(wins_val, list):
            total_career_wins = len(wins_val)
        else:
            total_career_wins = wins_val
        win_rate_career = round((total_career_wins / total_career_matches) * 100, 1) if total_career_matches > 0 else 0
        current_pti = player.get('pti', 'N/A')
        career_stats = {
            'winRate': win_rate_career,
            'matches': total_career_matches,
            'pti': current_pti
        }
        progression = []
        # --- NEW: Compute seasons from matches if missing or empty ---
        seasons = player.get('seasons', [])
        if not seasons:
            seasons = build_season_history(player)
        for s in seasons:
            trend_val = s.get('trend', '')
            progression.append(f"{s.get('season', '')}: PTI {s.get('ptiStart', '')}→{s.get('ptiEnd', '')} ({trend_val})")
        player_history = {
            'progression': ' | '.join(progression),
            'seasons': seasons
        }
    # --- 9. Compose response ---
    career_pti_change = 'N/A'
    if player and 'matches' in player:
        import datetime
        def parse_date(d):
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    return datetime.datetime.strptime(d, fmt)
                except Exception:
                    continue
            return None
        matches_with_pti = [m for m in player['matches'] if 'end_pti' in m and 'date' in m]
        if len(matches_with_pti) >= 2:
            matches_with_pti_sorted = sorted(matches_with_pti, key=lambda m: parse_date(m['date']))
            earliest_pti = matches_with_pti_sorted[0]['end_pti']
            latest_pti = matches_with_pti_sorted[-1]['end_pti']
            career_pti_change = round(latest_pti - earliest_pti, 1)
    # --- Defensive: always return all keys, even if player not found ---
    response = {
        'current_season': current_season if player else None,
        'court_analysis': court_analysis if player else {},
        'career_stats': career_stats if player else None,
        'player_history': player_history if player else None,
        'videos': {'match': [], 'practice': []},
        'trends': {},
        'career_pti_change': career_pti_change if player else 'N/A',
        'error': None if player else 'No analysis data available for this player.'
    }
    return response

@app.route('/mobile/analyze-me')
@login_required
def serve_mobile_analyze_me():
    try:
        # Get user info from session
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Get analysis data for the user
        analyze_data = get_player_analysis(user)
        
        # Prepare session data
        session_data = {
            'user': user,
            'authenticated': True
        }
        
        # Log the page visit
        log_user_activity(user['email'], 'page_visit', page='mobile_analyze_me')
        
        # Return the rendered template
        return render_template('mobile/analyze_me.html', session_data=session_data, analyze_data=analyze_data)
        
    except Exception as e:
        print(f"Error in serve_mobile_analyze_me: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/research-me')
@login_required
def research_me():
    """
    Unified player analysis endpoint for the logged-in user. Returns all data needed for the mobile and desktop 'Me' (player analysis) page.
    """
    import os, json
    from collections import defaultdict, Counter
    user = session['user']      # <-- Add this line
    player_name = f"{user['first_name']} {user['last_name']}"
    # Load player history
    player_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'player_history.json')
    try:
        with open(player_history_path, 'r') as f:
            all_players = json.load(f)
    except Exception as e:
        # Always return all keys, even if error
        return jsonify({
            'current_season': None,
            'court_analysis': {},
            'career_stats': None,
            'player_history': None,
            'videos': {'match': [], 'practice': []},
            'trends': {},
            'error': f'Could not load player history: {e}'
        })
    player = None
    # Try to match both 'First Last' and 'Last, First' formats, ignoring case and extra spaces
    def normalize(name):
        return name.replace(',', '').replace('  ', ' ').strip().lower()
    player_name_normal = normalize(player_name)
    player_last_first = normalize(f"{user['last_name']}, {user['first_name']}")
    for p in all_players:
        n = normalize(p.get('name', ''))
        if n == player_name_normal or n == player_last_first:
            player = p
            break
    # Fallback: try to build player from matches file if not found in player history
    if not player:
        matches_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_history.json')
        try:
            with open(matches_path, 'r') as f:
                all_matches = json.load(f)
        except Exception as e:
            all_matches = []
        def match_player_name(name):
            name = name.lower()
            return name == player_name_normal or name == player_last_first or player_name_normal in name or player_last_first in name
        player_matches = [m for m in all_matches if any(
            match_player_name((m.get(f'{side} Player {num}') or '').replace(',', '').replace('  ', ' ').strip().lower())
            for side in ['Home', 'Away'] for num in [1,2])]
        if player_matches:
            # Calculate wins/losses
            wins = 0
            for match in player_matches:
                is_home = (match.get('Home Player 1','').lower() == player_name_normal or match.get('Home Player 2','').lower() == player_name_normal or match.get('Home Player 1','').lower() == player_last_first or match.get('Home Player 2','').lower() == player_last_first)
                winner = match.get('Winner','').lower()
                if (is_home and winner == 'home') or (not is_home and winner == 'away'):
                    wins += 1
            total_matches = len(player_matches)
            losses = total_matches - wins
            # Get most recent PTI if available
            sorted_matches = sorted(player_matches, key=lambda m: m.get('Date','') or m.get('date',''))
            pti = sorted_matches[-1].get('Rating') if sorted_matches and 'Rating' in sorted_matches[-1] else 50
            # Build fallback player object
            player = {
                'name': player_name,
                'matches': player_matches,
                'wins': wins,
                'losses': losses,
                'pti': pti
            }
        else:
            # Always return all keys, even if player not found
            return jsonify({
                'current_season': None,
                'court_analysis': {},
                'career_stats': None,
                'player_history': None,
                'videos': {'match': [], 'practice': []},
                'trends': {},
                'error': 'No analysis data available for this player.'
            })
    # Load match data for advanced trends and court breakdown
    matches_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_history.json')
    try:
        with open(matches_path, 'r') as f:
            all_matches = json.load(f)
    except Exception as e:
        all_matches = []
    # Optionally, load video data if available
    video_data = {'match': [], 'practice': []}
    video_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'player_videos.json')
    if os.path.exists(video_path):
        try:
            with open(video_path, 'r') as f:
                all_videos = json.load(f)
                v = all_videos.get(player_name, {})
                video_data['match'] = v.get('match', [])
                video_data['practice'] = v.get('practice', [])
        except Exception:
            video_data = {'match': [], 'practice': []}
    # --- Compute current season stats ---
    current_season = None
    if 'seasons' in player and player['seasons']:
        # Assume last season is current
        last_season = player['seasons'][-1]
        current_season = {
            'winRate': last_season.get('winRate', 0),
            'matches': last_season.get('matches', 0),
            'ptiChange': last_season.get('ptiEnd', 0) - last_season.get('ptiStart', 0)
        }
    # --- Compute court analysis (NEW LOGIC) ---
    from collections import defaultdict, Counter
    court_analysis = {str(i): {'winRate': 0, 'record': '0-0', 'topPartners': []} for i in range(1, 5)}
    # Step 1: Group matches by (date, series)
    matches_by_date_series = defaultdict(list)
    for match in all_matches:
        date = match.get('Date')
        home_team = match.get('Home Team', '')
        away_team = match.get('Away Team', '')
        series = ''
        if ' - ' in home_team:
            series = home_team.split(' - ')[-1]
        elif ' - ' in away_team:
            series = away_team.split(' - ')[-1]
        key = (date, series)
        matches_by_date_series[key].append(match)
    print("\n[DEBUG] Grouped matches by (date, series):")
    for key, matches in matches_by_date_series.items():
        print(f"  {key}: {len(matches)} matches")
        for idx, m in enumerate(matches):
            print(f"    Court {idx+1}: {m.get('Home Team')} vs {m.get('Away Team')} | Players: {m.get('Home Player 1')}, {m.get('Home Player 2')} vs {m.get('Away Player 1')}, {m.get('Away Player 2')}")
    # Step 2: Assign courts and collect player's matches by court
    player_court_matches = defaultdict(list)
    print(f"\n[DEBUG] Checking matches for player: {player_name}")
    for (date, series), matches in matches_by_date_series.items():
        # Sort matches for deterministic court assignment
        matches_sorted = sorted(matches, key=lambda m: (m.get('Home Team', ''), m.get('Away Team', '')))
        for idx, match in enumerate(matches_sorted):
            court_num = str(idx + 1)
            match['court_num'] = court_num  # Assign court number to all matches
            players = [
                match.get('Home Player 1', ''),
                match.get('Home Player 2', ''),
                match.get('Away Player 1', ''),
                match.get('Away Player 2', '')
            ]
            if any(p and p.strip().lower() == player_name.lower() for p in players):
                player_court_matches[court_num].append(match)
                print(f"  [DEBUG] Player found on {date} series {series} court {court_num}: {players}")
    # Step 3: For each court, calculate stats
    for court_num in ['1', '2', '3', '4']:
        matches = player_court_matches.get(court_num, [])
        if not matches:
            continue
        print(f"\n[DEBUG] Court {court_num} - {len(matches)} matches for player {player_name}")
        wins = 0
        losses = 0
        partner_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'matches': 0})
        for match in matches:
            is_home = player_name in [match.get('Home Player 1'), match.get('Home Player 2')]
            won = (is_home and match.get('Winner') == 'home') or (not is_home and match.get('Winner') == 'away')
            if won:
                wins += 1
            else:
                losses += 1
            # Identify partner
            if is_home:
                partner = match.get('Home Player 2') if match.get('Home Player 1') == player_name else match.get('Home Player 1')
            else:
                partner = match.get('Away Player 2') if match.get('Away Player 1') == player_name else match.get('Away Player 1')
            if partner:
                partner_stats[partner]['matches'] += 1
                if won:
                    partner_stats[partner]['wins'] += 1
                else:
                    partner_stats[partner]['losses'] += 1
            print(f"    [DEBUG] Match: {match.get('Date')} {match.get('Home Team')} vs {match.get('Away Team')} | Partner: {partner} | Win: {won}")
        total_matches = wins + losses
        win_rate = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0
        record = f"{wins}-{losses}"
        # Top partners by matches played
        sorted_partners = sorted(partner_stats.items(), key=lambda x: -x[1]['matches'])[:3]
        top_partners = []
        for partner, stats in sorted_partners:
            p_win_rate = round((stats['wins'] / stats['matches']) * 100, 1) if stats['matches'] > 0 else 0
            p_record = f"{stats['wins']}-{stats['losses']}"
            top_partners.append({
                'name': partner,
                'winRate': p_win_rate,
                'record': p_record,
                'matches': stats['matches']
            })
        court_analysis[court_num] = {
            'winRate': win_rate,
            'record': record,
            'topPartners': top_partners
        }
    # --- Compute career stats ---
    career_stats = None
    if player.get('matches') is not None and player.get('wins') is not None:
        # Fix: handle if matches/wins are lists
        matches_val = player['matches']
        wins_val = player['wins']
        total_matches = len(matches_val) if isinstance(matches_val, list) else matches_val
        wins = len(wins_val) if isinstance(wins_val, list) else wins_val
        win_rate = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0
        career_stats = {
            'winRate': win_rate,
            'matches': total_matches,
            'pti': player.get('pti', 'N/A')
        }
    # --- Player history ---
    player_history = None
    if 'seasons' in player and player['seasons']:
        progression = []
        for s in player['seasons']:
            trend = s.get('ptiEnd', 0) - s.get('ptiStart', 0)
            progression.append(f"{s.get('season', '')}: PTI {s.get('ptiStart', '')}→{s.get('ptiEnd', '')} ({'+' if trend >= 0 else ''}{trend})")
        player_history = {
            'progression': ' | '.join(progression),
            'seasons': [
                {
                    'season': s.get('season', ''),
                    'series': s.get('series', ''),
                    'ptiStart': s.get('ptiStart', ''),
                    'ptiEnd': s.get('ptiEnd', ''),
                    'trend': ('+' if (s.get('ptiEnd', 0) - s.get('ptiStart', 0)) >= 0 else '') + str(s.get('ptiEnd', 0) - s.get('ptiStart', 0))
                } for s in player['seasons']
            ]
        }
    # --- Trends (win/loss streaks, etc.) ---
    trends = {}
    player_matches = [m for m in all_matches if player_name in [m.get('Home Player 1'), m.get('Home Player 2'), m.get('Away Player 1'), m.get('Away Player 2')]]
    streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    last_result = None
    for match in sorted(player_matches, key=lambda x: x.get('Date', '')):
        is_home = player_name in [match.get('Home Player 1'), match.get('Home Player 2')]
        won = (is_home and match.get('Winner') == 'home') or (not is_home and match.get('Winner') == 'away')
        if won:
            if last_result == 'W':
                streak += 1
            else:
                streak = 1
            max_win_streak = max(max_win_streak, streak)
            last_result = 'W'
        else:
            if last_result == 'L':
                streak += 1
            else:
                streak = 1
            max_loss_streak = max(max_loss_streak, streak)
            last_result = 'L'
    trends['max_win_streak'] = max_win_streak
    trends['max_loss_streak'] = max_loss_streak
    # --- Career PTI Change (all-time) ---
    career_pti_change = 'N/A'
    if player and 'matches' in player:
        import datetime
        def parse_date(d):
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    return datetime.datetime.strptime(d, fmt)
                except Exception:
                    continue
            return None
        matches_with_pti = [m for m in player['matches'] if 'end_pti' in m and 'date' in m]
        if len(matches_with_pti) >= 2:
            matches_with_pti_sorted = sorted(matches_with_pti, key=lambda m: parse_date(m['date']))
            career_pti_change = round(matches_with_pti_sorted[-1]['end_pti'] - matches_with_pti_sorted[0]['end_pti'], 1)
            print(f"DEBUG: Career PTI change calculation: start={matches_with_pti_sorted[0]['end_pti']} → end={matches_with_pti_sorted[-1]['end_pti']}, career_pti_change={career_pti_change}")
    # --- Compose response ---
    response = {
        'current_season': current_season if current_season is not None else {'winRate': 'N/A', 'matches': 'N/A', 'ptiChange': 'N/A'},
        'court_analysis': court_analysis if court_analysis else {},
        'career_stats': career_stats if career_stats is not None else {'winRate': 'N/A', 'matches': 'N/A', 'pti': 'N/A'},
        'career_pti_change': career_pti_change,
        'player_history': player_history if player_history is not None else {'progression': '', 'seasons': []},
        'videos': video_data if video_data else {'match': [], 'practice': []},
        'trends': trends if trends else {'max_win_streak': 0, 'max_loss_streak': 0}
    }
    return jsonify(response)

def get_season_from_date(date_str):
    """
    Given a date string in MM/DD/YYYY or YYYY-MM-DD, return the season string 'YYYY-YYYY+1'.
    """
    from datetime import datetime
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        return None  # Invalid date format
    if dt.month >= 8:
        start_year = dt.year
        end_year = dt.year + 1
    else:
        start_year = dt.year - 1
        end_year = dt.year
    return f"{start_year}-{end_year}"

def build_season_history(player):
    from collections import defaultdict
    from datetime import datetime
    matches = player.get('matches', [])
    if not matches:
        return []
    # Helper to parse date robustly
    def parse_date(d):
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(d, fmt)
            except Exception:
                continue
        return d  # fallback to string if parsing fails
    # Group matches by season
    season_matches = defaultdict(list)
    for m in matches:
        season = get_season_from_date(m.get('date', ''))
        if season:
            season_matches[season].append(m)
    seasons = []
    for season, ms in season_matches.items():
        ms_sorted = sorted(ms, key=lambda x: parse_date(x.get('date', '')))
        pti_start = ms_sorted[0].get('end_pti', None)
        pti_end = ms_sorted[-1].get('end_pti', None)
        series = ms_sorted[0].get('series', '')
        trend = (pti_end - pti_start) if pti_start is not None and pti_end is not None else None
        # --- ROUND trend to 1 decimal ---
        if trend is not None:
            trend_rounded = round(trend, 1)
            trend_str = f"+{trend_rounded}" if trend_rounded >= 0 else str(trend_rounded)
        else:
            trend_str = ''
        seasons.append({
            'season': season,
            'series': series,
            'ptiStart': pti_start,
            'ptiEnd': pti_end,
            'trend': trend_str
        })
    # Sort by season (descending)
    seasons.sort(key=lambda s: s['season'], reverse=True)
    return seasons

@app.route('/mobile/my-team')
@login_required
def serve_mobile_my_team():
    """
    Serve the mobile My Team analysis page.
    """
    user = session['user']
    # Determine the user's team (same logic as /api/research-my-team)
    club = user.get('club')
    series = user.get('series')
    import re
    m = re.search(r'(\d+)', series)
    series_num = m.group(1) if m else ''
    team = f"{club} - {series_num}"
    stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'series_stats.json')
    try:
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
        team_stats = next((stats for stats in all_stats if stats.get('team') == team), None)
        # Defensive: always pass a dict, even if not found
        return render_template('mobile/my_team.html', team_data=team_stats or {}, session_data={'user': user})
    except Exception as e:
        print(f"Error fetching team stats: {str(e)}")
        return render_template('mobile/my_team.html', team_data={}, session_data={'user': user}, error=str(e))

@app.route('/mobile/myteam')
@login_required
def serve_mobile_myteam():
    """
    Serve the mobile My Team analysis page.
    """
    user = session['user']
    club = user.get('club')
    series = user.get('series')
    import re
    m = re.search(r'(\d+)', series)
    series_num = m.group(1) if m else ''
    team = f"{club} - {series_num}"
    stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'series_stats.json')
    matches_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'match_history.json')
    try:
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
        print("DEBUG: club =", club)
        print("DEBUG: series =", series)
        print("DEBUG: series_num =", series_num)
        print("DEBUG: team =", team)
        print("DEBUG: Available teams:", [t.get('team') for t in all_stats])
        team_stats = next((stats for stats in all_stats if stats.get('team') == team), None)
        # Compute court analysis and top players
        court_analysis = {}
        top_players = []
        if os.path.exists(matches_path):
            with open(matches_path, 'r') as f:
                matches = json.load(f)
            # Group matches by date for court assignment
            from collections import defaultdict, Counter
            matches_by_date = defaultdict(list)
            for match in matches:
                if match.get('Home Team') == team or match.get('Away Team') == team:
                    matches_by_date[match['Date']].append(match)
            # Court stats and player stats
            court_stats = {f'court{i}': {'matches': 0, 'wins': 0, 'losses': 0, 'players': Counter()} for i in range(1, 5)}
            player_stats = {}
            for date, day_matches in matches_by_date.items():
                # Sort matches for deterministic court assignment
                day_matches_sorted = sorted(day_matches, key=lambda m: (m.get('Home Team', ''), m.get('Away Team', '')))
                for i, match in enumerate(day_matches_sorted):
                    court_num = i + 1
                    court_key = f'court{court_num}'
                    is_home = match.get('Home Team') == team
                    # Get players for this team
                    if is_home:
                        players = [match.get('Home Player 1'), match.get('Home Player 2')]
                        opp_players = [match.get('Away Player 1'), match.get('Away Player 2')]
                    else:
                        players = [match.get('Away Player 1'), match.get('Away Player 2')]
                        opp_players = [match.get('Home Player 1'), match.get('Home Player 2')]
                    # Determine win/loss
                    won = (is_home and match.get('Winner') == 'home') or (not is_home and match.get('Winner') == 'away')
                    court_stats[court_key]['matches'] += 1
                    if won:
                        court_stats[court_key]['wins'] += 1
                    else:
                        court_stats[court_key]['losses'] += 1
                    for p in players:
                        court_stats[court_key]['players'][p] += 1
                        if p not in player_stats:
                            player_stats[p] = {'matches': 0, 'wins': 0, 'courts': Counter(), 'partners': Counter()}
                        player_stats[p]['matches'] += 1
                        if won:
                            player_stats[p]['wins'] += 1
                        player_stats[p]['courts'][court_key] += 1
                    # Partner tracking
                    if len(players) == 2:
                        player_stats[players[0]]['partners'][players[1]] += 1
                        player_stats[players[1]]['partners'][players[0]] += 1
            # Build court_analysis
            for i in range(1, 5):
                court_key = f'court{i}'
                stat = court_stats[court_key]
                matches = stat['matches']
                wins = stat['wins']
                losses = stat['losses']
                win_rate = round((wins / matches) * 100, 1) if matches > 0 else 0
                # Top players by matches played on this court
                top_players_court = stat['players'].most_common(2)
                court_analysis[court_key] = {
                    'matches': matches,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'top_players': [{'name': p, 'matches': c} for p, c in top_players_court]
                }
            # Build top_players list
            for p, stat in player_stats.items():
                matches = stat['matches']
                wins = stat['wins']
                win_rate = round((wins / matches) * 100, 1) if matches > 0 else 0
                # Best court
                best_court = max(stat['courts'].items(), key=lambda x: x[1])[0] if stat['courts'] else ''
                # Best partner
                best_partner = max(stat['partners'].items(), key=lambda x: x[1])[0] if stat['partners'] else ''
                top_players.append({
                    'name': p,
                    'matches': matches,
                    'win_rate': win_rate,
                    'best_court': best_court,
                    'best_partner': best_partner
                })
            # Sort top_players by matches played, then win rate
            top_players.sort(key=lambda x: (-x['matches'], -x['win_rate'], x['name']))
        return render_template('mobile/my_team.html', team_data=team_stats or {}, session_data={'user': user}, court_analysis=court_analysis, top_players=top_players)
    except Exception as e:
        print(f"Error fetching team stats: {str(e)}")
        return render_template('mobile/my_team.html', team_data={}, session_data={'user': user}, error=str(e))
    

# Backward-compatible alias (redirect)
@app.route('/mobile/my-team')
def redirect_my_team():
    from flask import redirect, url_for
    return redirect(url_for('serve_mobile_myteam'))

@app.route('/mobile/settings')
@login_required
def serve_mobile_settings():
    """Serve the mobile user settings page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    return render_template('mobile/user_settings.html', session_data=session_data)

@app.route('/mobile/my-series')
@login_required
def serve_mobile_my_series():
    """Serve the mobile My Series (series stats) page"""
    user = session['user']
    session_data = {
        'user': user,
        'authenticated': True
    }
    # Log mobile access
    try:
        log_user_activity(
            user['email'],
            'page_visit',
            page='mobile_my_series',
            details='Accessed mobile my series page'
        )
    except Exception as e:
        print(f"Error logging my series mobile page visit: {str(e)}")
    return render_template('mobile/my_series.html', session_data=session_data)

@app.route('/mobile/myseries')
@login_required
def redirect_myseries():
    from flask import redirect, url_for
    return redirect(url_for('serve_mobile_my_series'))



@app.route('/mobile/teams-players', methods=['GET'])
@login_required
def mobile_teams_players():
    team = request.args.get('team')
    stats_path = 'data/series_stats.json'
    matches_path = 'data/match_history.json'
    import json
    with open(stats_path) as f:
        all_stats = json.load(f)
    with open(matches_path) as f:
        all_matches = json.load(f)
    # Filter out BYE teams
    all_teams = sorted({s['team'] for s in all_stats if 'BYE' not in s['team'].upper()})
    if not team or team not in all_teams:
        # No team selected or invalid team
        return render_template(
            'mobile/teams_players.html',
            team_analysis_data=None,
            all_teams=all_teams,
            selected_team=None
        )
    team_stats = next((s for s in all_stats if s.get('team') == team), {})
    team_matches = [m for m in all_matches if m.get('Home Team') == team or m.get('Away Team') == team]
    team_analysis_data = calculate_team_analysis(team_stats, team_matches, team)
    return render_template(
        'mobile/teams_players.html',
        team_analysis_data=team_analysis_data,
        all_teams=all_teams,
        selected_team=team
    )

def calculate_team_analysis(team_stats, team_matches, team):
    # Use the same transformation as desktop for correct stats
    overview = transform_team_stats_to_overview(team_stats)
    # Match Patterns
    total_matches = len(team_matches)
    straight_set_wins = 0
    comeback_wins = 0
    three_set_wins = 0
    three_set_losses = 0
    for match in team_matches:
        is_home = match.get('Home Team') == team
        winner_is_home = match.get('Winner') == 'home'
        team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
        sets = match.get('Sets', [])
        if len(sets) == 2 and team_won:
            straight_set_wins += 1
        if len(sets) == 3:
            if team_won:
                three_set_wins += 1
            else:
                three_set_losses += 1
            # Comeback win: lost first set, won next two
            if team_won and sets and sets[0][('away' if is_home else 'home')] > sets[0][('home' if is_home else 'away')]:
                comeback_wins += 1
    three_set_record = f"{three_set_wins}-{three_set_losses}"
    match_patterns = {
        'total_matches': total_matches,
        'set_win_rate': overview['set_win_rate'],
        'three_set_record': three_set_record,
        'straight_set_wins': straight_set_wins,
        'comeback_wins': comeback_wins
    }
    # Court Analysis (desktop logic)
    court_analysis = {}
    for i in range(1, 5):
        court_name = f'Court {i}'
        court_matches = [m for idx, m in enumerate(team_matches) if (idx % 4) + 1 == i]
        wins = losses = 0
        player_win_counts = {}
        for match in court_matches:
            is_home = match.get('Home Team') == team
            winner_is_home = match.get('Winner') == 'home'
            team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
            if team_won:
                wins += 1
            else:
                losses += 1
            players = [match.get('Home Player 1'), match.get('Home Player 2')] if is_home else [match.get('Away Player 1'), match.get('Away Player 2')]
            for p in players:
                if not p: continue
                if p not in player_win_counts:
                    player_win_counts[p] = {'matches': 0, 'wins': 0}
                player_win_counts[p]['matches'] += 1
                if team_won:
                    player_win_counts[p]['wins'] += 1
        win_rate = round((wins / (wins + losses) * 100), 1) if (wins + losses) > 0 else 0
        record = f"{wins}-{losses} ({win_rate}%)"
        # Top players by win rate (min 2 matches)
        key_players = sorted([
            {'name': p, 'win_rate': round((d['wins']/d['matches'])*100, 1), 'matches': d['matches']}
            for p, d in player_win_counts.items() if d['matches'] >= 2
        ], key=lambda x: -x['win_rate'])[:2]
        # Summary sentence
        if win_rate >= 60:
            perf = 'strong performance'
        elif win_rate >= 45:
            perf = 'solid performance'
        else:
            perf = 'average performance'
        if key_players:
            contributors = ' and '.join([
                f"{kp['name']} ({kp['win_rate']}% in {kp['matches']} matches)" for kp in key_players
            ])
            summary = f"This court has shown {perf} with a {win_rate}% win rate. Key contributors: {contributors}."
        else:
            summary = f"This court has shown {perf} with a {win_rate}% win rate."
        court_analysis[court_name] = {
            'record': record,
            'win_rate': win_rate,
            'key_players': key_players,
            'summary': summary
        }
    # Top Players Table (unchanged)
    player_stats = {}
    for match in team_matches:
        is_home = match.get('Home Team') == team
        player1 = match.get('Home Player 1') if is_home else match.get('Away Player 1')
        player2 = match.get('Home Player 2') if is_home else match.get('Away Player 2')
        winner_is_home = match.get('Winner') == 'home'
        team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
        for player in [player1, player2]:
            if not player: continue
            if player not in player_stats:
                player_stats[player] = {'matches': 0, 'wins': 0, 'courts': {}, 'partners': {}}
            player_stats[player]['matches'] += 1
            if team_won:
                player_stats[player]['wins'] += 1
            # Court
            court_idx = team_matches.index(match) % 4 + 1
            court = f'Court {court_idx}'
            if court not in player_stats[player]['courts']:
                player_stats[player]['courts'][court] = {'matches': 0, 'wins': 0}
            player_stats[player]['courts'][court]['matches'] += 1
            if team_won:
                player_stats[player]['courts'][court]['wins'] += 1
            # Partner
            partner = player2 if player == player1 else player1
            if partner:
                if partner not in player_stats[player]['partners']:
                    player_stats[player]['partners'][partner] = {'matches': 0, 'wins': 0}
                player_stats[player]['partners'][partner]['matches'] += 1
                if team_won:
                    player_stats[player]['partners'][partner]['wins'] += 1
    top_players = []
    for name, stats in player_stats.items():
        if stats['matches'] < 3: continue
        win_rate = round((stats['wins']/stats['matches'])*100, 1) if stats['matches'] > 0 else 0
        # Best court
        best_court = None
        best_court_rate = 0
        for court, cstats in stats['courts'].items():
            if cstats['matches'] >= 2:
                rate = round((cstats['wins']/cstats['matches'])*100, 1)
                if rate > best_court_rate:
                    best_court_rate = rate
                    best_court = f"{court} ({rate}%)"
        # Best partner
        best_partner = None
        best_partner_rate = 0
        for partner, pstats in stats['partners'].items():
            if pstats['matches'] >= 2:
                rate = round((pstats['wins']/pstats['matches'])*100, 1)
                if rate > best_partner_rate:
                    best_partner_rate = rate
                    best_partner = f"{partner} ({rate}%)"
        top_players.append({
            'name': name,
            'matches': stats['matches'],
            'win_rate': win_rate,
            'best_court': best_court or 'N/A',
            'best_partner': best_partner or 'N/A'
        })
    top_players = sorted(top_players, key=lambda x: -x['win_rate'])
    # Narrative summary (copied/adapted from research-team)
    summary = (
        f"{team} has accumulated {overview['points']} points this season with a "
        f"{overview['match_win_rate']}% match win rate. The team shows "
        f"strong resilience with {match_patterns['comeback_wins']} comeback victories "
        f"and has won {match_patterns['straight_set_wins']} matches in straight sets.\n"
        f"Their performance metrics show a {overview['game_win_rate']}% game win rate and "
        f"{overview['set_win_rate']}% set win rate, with particularly "
        f"{'strong' if overview['line_win_rate'] >= 50 else 'consistent'} line play at "
        f"{overview['line_win_rate']}%.\n"
        f"In three-set matches, the team has a record of {match_patterns['three_set_record']}, "
        f"demonstrating their {'strength' if three_set_wins > three_set_losses else 'areas for improvement'} in extended matches."
    )
    return {
        'overview': overview,
        'match_patterns': match_patterns,
        'court_analysis': court_analysis,
        'top_players': top_players,
        'summary': summary
    }

def get_player_analysis_by_name(player_name):
    """
    Returns the player analysis data for the given player name, as a dict.
    This function parses the player_name string into first and last name (if possible),
    then calls get_player_analysis with a constructed user dict.
    Handles single-word names gracefully.
    """
    # Defensive: handle empty or None
    if not player_name or not isinstance(player_name, str):
        return {
            'current_season': None,
            'court_analysis': {},
            'career_stats': None,
            'player_history': None,
            'videos': {'match': [], 'practice': []},
            'trends': {},
            'career_pti_change': 'N/A',
            'error': 'Invalid player name.'
        }
    # Try to split into first and last name
    parts = player_name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
    else:
        # If only one part, use as both first and last name
        first_name = parts[0]
        last_name = parts[0]
    # Call get_player_analysis with constructed user dict
    user_dict = {'first_name': first_name, 'last_name': last_name}
    return get_player_analysis(user_dict)

@app.route('/player-detail/<player_name>')
@login_required
def serve_player_detail(player_name):
    """Serve the player detail page for any player (desktop version)"""
    from urllib.parse import unquote
    player_name = unquote(player_name)
    analyze_data = get_player_analysis_by_name(player_name)
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    log_user_activity(
        session['user']['email'],
        'page_visit',
        page='player_detail',
        details=f'Viewed player {player_name}'
    )
    return render_template('player_detail.html', session_data=session_data, analyze_data=analyze_data, player_name=player_name)

def parse_date(date_str):
    """Parse a date string into a datetime object."""
    if not date_str:
        return None
    try:
        # Try DD-Mon-YY format first (e.g. '25-Sep-24')
        return datetime.strptime(date_str, '%d-%b-%y')
    except ValueError:
        try:
            # Try standard format (e.g. '2024-01-15')
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            try:
                # Try alternative format (e.g. '1/15/24')
                return datetime.strptime(date_str, '%m/%d/%y')
            except ValueError:
                return None

def calculate_player_streaks(matches, club_name):
    player_stats = {}
    
    # Sort matches by date, handling None values
    def sort_key(x):
        date = parse_date(x.get('Date', ''))
        # Return a far future date for None to put them at the end
        return date or datetime(9999, 12, 31)
    
    sorted_matches = sorted(matches, key=sort_key)
    
    for match in sorted_matches:
        if match.get('Home Team', '').startswith(club_name) or match.get('Away Team', '').startswith(club_name):
            # Process each player in the match
            for court in ['Court 1', 'Court 2', 'Court 3', 'Court 4']:
                for team in ['Home', 'Away']:
                    players = match.get(f'{team} {court}', '').split('/')
                    for player in players:
                        player = player.strip()
                        if not player or player.lower() == 'bye':
                            continue
                            
                        if player not in player_stats:
                            player_stats[player] = {
                                'current_streak': 0,
                                'best_streak': 0,
                                'last_match_date': None,
                                'series': match.get(f'{team} Series', ''),
                            }
                        
                        # Determine if player won
                        court_result = match.get(f'{court} Result', '')
                        won = (team == 'Home' and court_result == 'Home') or (team == 'Away' and court_result == 'Away')
                        
                        # Update streaks
                        if won:
                            if player_stats[player]['current_streak'] >= 0:
                                player_stats[player]['current_streak'] += 1
                            else:
                                player_stats[player]['current_streak'] = 1
                        else:
                            if player_stats[player]['current_streak'] <= 0:
                                player_stats[player]['current_streak'] -= 1
                            else:
                                player_stats[player]['current_streak'] = -1
                        
                        # Update best streak
                        player_stats[player]['best_streak'] = max(
                            player_stats[player]['best_streak'],
                            player_stats[player]['current_streak']
                        )
                        
                        # Update last match date
                        player_stats[player]['last_match_date'] = match.get('Date', '')
    
    # Convert to list and format for template
    streaks_list = [
        {
            'player_name': player,
            'current_streak': stats['current_streak'],
            'best_streak': stats['best_streak'],
            'last_match_date': stats['last_match_date'],
            'series': stats['series']
        }
        for player, stats in player_stats.items()
    ]
    
    # Sort by current streak (absolute value) descending, then best streak
    return sorted(
        streaks_list,
        key=lambda x: (abs(x['current_streak']), x['best_streak']),
        reverse=True
    )

@app.route('/mobile/my-club')
@login_required
def my_club():
    try:
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401

        club = user.get('club')
        matches_data = get_recent_matches_for_user_club(user)
        
        if not matches_data:
            return render_template(
                'mobile/my_club.html',
                team_name=club,
                this_week_results=[],
                tennaqua_standings=[],
                head_to_head=[],
                player_streaks=[]
            )
            
        # Group matches by team
        team_matches = {}
        for match in matches_data:
            home_team = match['home_team']
            away_team = match['away_team']
            
            if club in home_team:
                team = home_team
                opponent = away_team.split(' - ')[0]
                is_home = True
            elif club in away_team:
                team = away_team
                opponent = home_team.split(' - ')[0]
                is_home = False
            else:
                continue
                
            if team not in team_matches:
                team_matches[team] = {
                    'opponent': opponent,
                    'matches': [],
                    'team_points': 0,
                    'opponent_points': 0,
                    'series': team.split(' - ')[1] if ' - ' in team else team
                }
            
            # Calculate points for this match
            scores = match['scores'].split(', ')
            match_team_points = 0
            match_opponent_points = 0
            
            # Points for each set
            for set_score in scores:
                our_score, their_score = map(int, set_score.split('-'))
                if not is_home:
                    our_score, their_score = their_score, our_score
                    
                if our_score > their_score:
                    match_team_points += 1
                else:
                    match_opponent_points += 1
                    
            # Bonus point for match win
            if (is_home and match['winner'] == 'home') or (not is_home and match['winner'] == 'away'):
                match_team_points += 1
            else:
                match_opponent_points += 1
                
            # Update total points
            team_matches[team]['team_points'] += match_team_points
            team_matches[team]['opponent_points'] += match_opponent_points
            
            # Add match details
            court = match.get('court', '')
            try:
                court_num = int(court) if court and court.strip() else len(team_matches[team]['matches']) + 1
            except (ValueError, TypeError):
                court_num = len(team_matches[team]['matches']) + 1
                
            team_matches[team]['matches'].append({
                'court': court_num,
                'home_players': f"{match['home_player_1']}/{match['home_player_2']}" if is_home else f"{match['away_player_1']}/{match['away_player_2']}",
                'away_players': f"{match['away_player_1']}/{match['away_player_2']}" if is_home else f"{match['home_player_1']}/{match['home_player_2']}",
                'scores': match['scores'],
                'won': (is_home and match['winner'] == 'home') or (not is_home and match['winner'] == 'away')
            })
            
        # Convert to list format for template
        this_week_results = []
        for team_data in team_matches.values():
            this_week_results.append({
                'series': f"Series {team_data['series']}" if team_data['series'].isdigit() else team_data['series'],
                'opponent': team_data['opponent'],
                'score': f"{team_data['team_points']}-{team_data['opponent_points']}",
                'won': team_data['team_points'] > team_data['opponent_points'],
                'match_details': sorted(team_data['matches'], key=lambda x: x['court']),
                'date': matches_data[0]['date']  # All matches are from the same date
            })
            
        # Sort results by opponent name
        this_week_results.sort(key=lambda x: x['opponent'])
        
        # Calculate Tennaqua standings
        stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'series_stats.json')
        with open(stats_path, 'r') as f:
            stats_data = json.load(f)
            
        tennaqua_standings = []
        for team_stats in stats_data:
            if not team_stats.get('team', '').startswith('Tennaqua'):
                continue
                
            series = team_stats.get('series')
            if not series:
                continue
                
            # Get all teams in this series
            series_teams = [team for team in stats_data if team.get('series') == series]
            
            # Calculate average points
            for team in series_teams:
                total_matches = sum(team.get('matches', {}).get(k, 0) for k in ['won', 'lost', 'tied'])
                total_points = float(team.get('points', 0))
                team['avg_points'] = round(total_points / total_matches, 1) if total_matches > 0 else 0
            
            # Sort by average points
            series_teams.sort(key=lambda x: x.get('avg_points', 0), reverse=True)
            
            # Find Tennaqua's position
            for i, team in enumerate(series_teams, 1):
                if team.get('team', '').startswith('Tennaqua'):
                    tennaqua_standings.append({
                        'series': series,
                        'place': i,
                        'total_points': team.get('points', 0),
                        'avg_points': team.get('avg_points', 0),
                        'playoff_contention': i <= 8
                    })
                    break
                    
        # Sort standings by series
        tennaqua_standings.sort(key=lambda x: x['series'])
        
        # Calculate head-to-head records
        head_to_head = {}
        for match in matches_data:
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            winner = match.get('winner', '')
            
            if not all([home_team, away_team, winner]):
                continue
                
            if club in home_team:
                opponent = away_team.split(' - ')[0]
                won = winner == 'home'
            elif club in away_team:
                opponent = home_team.split(' - ')[0]
                won = winner == 'away'
            else:
                continue
                
            if opponent not in head_to_head:
                head_to_head[opponent] = {'wins': 0, 'losses': 0, 'total': 0}
                
            head_to_head[opponent]['total'] += 1
            if won:
                head_to_head[opponent]['wins'] += 1
            else:
                head_to_head[opponent]['losses'] += 1
                
        # Convert head-to-head to list
        head_to_head = [
            {
                'opponent': opponent,
                'wins': stats['wins'],
                'losses': stats['losses'],
                'total': stats['total']
            }
            for opponent, stats in head_to_head.items()
        ]
        
        # Sort by total matches
        head_to_head.sort(key=lambda x: x['total'], reverse=True)
        
        # Calculate player streaks
        player_streaks = calculate_player_streaks(matches_data, club)
        
        return render_template(
            'mobile/my_club.html',
            team_name=club,
            this_week_results=this_week_results,
            tennaqua_standings=tennaqua_standings,
            head_to_head=head_to_head,
            player_streaks=player_streaks
        )
        
    except Exception as e:
        print(f"Error in my_club: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.template_filter('strip_leading_zero')
def strip_leading_zero(value):
    """
    Removes leading zero from hour in a time string like '06:30 pm' -> '6:30 pm'
    """
    import re
    return re.sub(r'^0', '', value) if isinstance(value, str) else value

@app.route('/api/win-streaks')
@login_required
def get_win_streaks():
    try:
        print("Starting win streaks calculation...")  # Debug print
        app.logger.info("Starting win streaks calculation...")
        
        # Read match history
        with open('data/match_history.json', 'r') as f:
            matches = json.load(f)
        
        print(f"Loaded {len(matches)} matches")  # Debug print
        app.logger.info(f"Loaded {len(matches)} matches")
        
        # Sort matches by date
        matches.sort(key=lambda x: datetime.strptime(x['Date'], '%d-%b-%y'))
        
        # Track streaks for each player
        player_streaks = {}
        current_streaks = {}
        
        for match in matches:
            # Get all players from the match
            home_players = [match['Home Player 1'], match['Home Player 2']]
            away_players = [match['Away Player 1'], match['Away Player 2']]
            
            # Determine winning and losing players
            winning_players = home_players if match['Winner'] == 'home' else away_players
            losing_players = away_players if match['Winner'] == 'home' else home_players
            
            # Update streaks for winning players
            for player in winning_players:
                if player not in current_streaks:
                    current_streaks[player] = 0
                current_streaks[player] += 1
                
                # Update max streak if current streak is longer
                if player not in player_streaks or current_streaks[player] > player_streaks[player]['count']:
                    player_streaks[player] = {
                        'count': current_streaks[player],
                        'end_date': match['Date']
                    }
            
            # Reset streaks for losing players
            for player in losing_players:
                if player in current_streaks:
                    current_streaks[player] = 0
        
        # Convert to sorted list
        streak_list = [
            {
                'player': player,
                'streak': data['count'],
                'end_date': data['end_date']
            }
            for player, data in player_streaks.items()
        ]
        
        # Sort by streak length (descending) and take top 20
        streak_list.sort(key=lambda x: (-x['streak'], x['end_date']))
        top_streaks = streak_list[:20]
        
        print(f"Found {len(top_streaks)} top streaks")  # Debug print
        app.logger.info(f"Found {len(top_streaks)} top streaks")
        
        return jsonify({
            'success': True,
            'streaks': top_streaks
        })
        
    except Exception as e:
        print(f"Error calculating win streaks: {str(e)}")  # Debug print
        app.logger.error(f"Error calculating win streaks: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/player-streaks')
def get_player_streaks():
    try:
        # Read match history and player data
        with open('data/match_history.json', 'r') as f:
            matches_data = json.load(f)
        with open('data/players.json', 'r') as f:
            players_data = json.load(f)
        
        # Build player info lookup
        player_info = {}
        for player in players_data:
            name = f"{player['First Name']} {player['Last Name']}".strip()
            if name not in player_info:
                player_info[name] = {
                    'club': player.get('Club', ''),
                    'series': player.get('Series', ''),
                    'wins': int(player.get('Wins', 0)),
                    'losses': int(player.get('Losses', 0))
                }
        
        # Build a mapping of player name to their matches
        player_matches = defaultdict(list)
        for match in matches_data:
            for side in ['Home', 'Away']:
                for num in [1, 2]:
                    player = match.get(f'{side} Player {num}')
                    if player:
                        player_matches[player].append(match)
        
        # Calculate streaks for each player
        player_streaks = {}
        for player, matches in player_matches.items():
            # Sort matches by date
            def parse_date(d):
                for fmt in ("%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                    try:
                        return datetime.strptime(d, fmt)
                    except Exception:
                        continue
                return None
            
            # Sort matches by date
            matches_sorted = sorted(matches, key=lambda m: parse_date(m.get('Date', '')) or datetime.min)
            
            # Calculate current and best streaks
            current_streak = 0
            current_streak_type = None
            max_win_streak = 0
            max_streak_end_date = None
            current_streak_start_date = None
            
            # Calculate overall stats
            total_matches = len(matches)
            total_wins = 0
            
            for match in matches_sorted:
                # Determine if player won
                player_side = None
                if player in [match['Home Player 1'], match['Home Player 2']]:
                    player_side = 'home'
                else:
                    player_side = 'away'
                
                won = (player_side == match['Winner'])
                if won:
                    total_wins += 1
                    
                    if current_streak_type == 'W' or current_streak_type is None:
                        current_streak += 1
                        current_streak_type = 'W'
                        if current_streak_start_date is None:
                            current_streak_start_date = match['Date']
                        if current_streak > max_win_streak:
                            max_win_streak = current_streak
                            max_streak_end_date = match['Date']
                    else:
                        current_streak = 1
                        current_streak_type = 'W'
                        current_streak_start_date = match['Date']
                else:
                    if current_streak_type == 'W' and current_streak > max_win_streak:
                        max_win_streak = current_streak
                        max_streak_end_date = matches_sorted[matches_sorted.index(match) - 1]['Date']
                    current_streak = 0
                    current_streak_type = None
                    current_streak_start_date = None
            
            # Check if final streak is the best
            if current_streak_type == 'W' and current_streak > max_win_streak:
                max_win_streak = current_streak
                max_streak_end_date = matches_sorted[-1]['Date'] if matches_sorted else None
            
            # Only include players with streaks
            if max_win_streak > 0:
                # Get player info
                info = player_info.get(player, {})
                win_percentage = (total_wins / total_matches * 100) if total_matches > 0 else 0
                
                player_streaks[player] = {
                    'player': player,
                    'club': info.get('club', 'Unknown'),
                    'series': info.get('series', '').replace('Chicago ', 'Series '),
                    'streak': max_win_streak,
                    'end_date': max_streak_end_date,
                    'total_matches': total_matches,
                    'total_wins': total_wins,
                    'win_percentage': round(win_percentage, 1),
                    'current_streak': current_streak if current_streak_type == 'W' else 0,
                    'current_streak_start': current_streak_start_date
                }
        
        # Convert to sorted list
        streak_list = list(player_streaks.values())
        
        # Sort by streak length (descending) and take top 20
        streak_list.sort(key=lambda x: (-x['streak'], -x['win_percentage'], x['end_date']))
        top_streaks = streak_list[:20]
        
        app.logger.info(f"Found {len(top_streaks)} top win streaks")
        
        return jsonify({
            'success': True,
            'streaks': top_streaks
        })
        
    except Exception as e:
        app.logger.error(f"Error calculating win streaks: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/enhanced-streaks')
@login_required
def get_enhanced_streaks():
    try:
        # Read match history and player data
        with open('data/match_history.json', 'r') as f:
            matches_data = json.load(f)
        with open('data/players.json', 'r') as f:
            players_data = json.load(f)
        
        # Build player info lookup
        player_info = {}
        for player in players_data:
            name = f"{player['First Name']} {player['Last Name']}".strip()
            if name not in player_info:
                player_info[name] = {
                    'club': player.get('Club', ''),
                    'series': player.get('Series', ''),
                    'wins': int(player.get('Wins', 0)),
                    'losses': int(player.get('Losses', 0))
                }
        
        # Build a mapping of player name to their matches
        player_matches = defaultdict(list)
        for match in matches_data:
            for side in ['Home', 'Away']:
                for num in [1, 2]:
                    player = match.get(f'{side} Player {num}')
                    if player:
                        player_matches[player].append(match)
        
        # Calculate comprehensive stats for each player
        player_stats = {}
        for player, matches in player_matches.items():
            # Sort matches by date
            def parse_date(d):
                for fmt in ("%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                    try:
                        return datetime.strptime(d, fmt)
                    except Exception:
                        continue
                return None
            
            matches_sorted = sorted(matches, key=lambda m: parse_date(m.get('Date', '')) or datetime.min)
            
            # Initialize stats
            current_streak = {'type': None, 'count': 0, 'start_date': None}
            best_win_streak = {'count': 0, 'start_date': None, 'end_date': None}
            best_loss_streak = {'count': 0, 'start_date': None, 'end_date': None}
            total_matches = len(matches)
            total_wins = 0
            total_losses = 0
            court_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'matches': 0})
            partner_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'matches': 0})
            
            # Track streaks and stats
            temp_streak = {'type': None, 'count': 0, 'start_date': None}
            
            for match in matches_sorted:
                # Determine if player won
                is_home = player in [match['Home Player 1'], match['Home Player 2']]
                won = (is_home and match['Winner'] == 'home') or (not is_home and match['Winner'] == 'away')
                
                # Update total stats
                if won:
                    total_wins += 1
                else:
                    total_losses += 1
                
                # Update court stats
                court_num = matches_sorted.index(match) % 4 + 1
                court_key = f'Court {court_num}'
                court_stats[court_key]['matches'] += 1
                if won:
                    court_stats[court_key]['wins'] += 1
                else:
                    court_stats[court_key]['losses'] += 1
                
                # Update partner stats
                partner = None
                if is_home:
                    partner = match['Home Player 1'] if player == match['Home Player 2'] else match['Home Player 2']
                else:
                    partner = match['Away Player 1'] if player == match['Away Player 2'] else match['Away Player 2']
                
                if partner:
                    partner_stats[partner]['matches'] += 1
                    if won:
                        partner_stats[partner]['wins'] += 1
                    else:
                        partner_stats[partner]['losses'] += 1
                
                # Update streak tracking
                if temp_streak['type'] is None:
                    temp_streak = {
                        'type': 'W' if won else 'L',
                        'count': 1,
                        'start_date': match['Date']
                    }
                elif (won and temp_streak['type'] == 'W') or (not won and temp_streak['type'] == 'L'):
                    temp_streak['count'] += 1
                else:
                    # Streak ended, check if it was a best streak
                    if temp_streak['type'] == 'W' and temp_streak['count'] > best_win_streak['count']:
                        best_win_streak = {
                            'count': temp_streak['count'],
                            'start_date': temp_streak['start_date'],
                            'end_date': matches_sorted[matches_sorted.index(match) - 1]['Date']
                        }
                    elif temp_streak['type'] == 'L' and temp_streak['count'] > best_loss_streak['count']:
                        best_loss_streak = {
                            'count': temp_streak['count'],
                            'start_date': temp_streak['start_date'],
                            'end_date': matches_sorted[matches_sorted.index(match) - 1]['Date']
                        }
                    # Start new streak
                    temp_streak = {
                        'type': 'W' if won else 'L',
                        'count': 1,
                        'start_date': match['Date']
                    }
            
            # Check final streak
            current_streak = temp_streak
            if temp_streak['type'] == 'W' and temp_streak['count'] > best_win_streak['count']:
                best_win_streak = {
                    'count': temp_streak['count'],
                    'start_date': temp_streak['start_date'],
                    'end_date': matches_sorted[-1]['Date']
                }
            elif temp_streak['type'] == 'L' and temp_streak['count'] > best_loss_streak['count']:
                best_loss_streak = {
                    'count': temp_streak['count'],
                    'start_date': temp_streak['start_date'],
                    'end_date': matches_sorted[-1]['Date']
                }
            
            # Calculate win rates and best courts/partners
            win_rate = (total_wins / total_matches * 100) if total_matches > 0 else 0
            
            # Process court stats
            for court, stats in court_stats.items():
                stats['win_rate'] = (stats['wins'] / stats['matches'] * 100) if stats['matches'] > 0 else 0
            
            # Find best court
            best_court = max(court_stats.items(), key=lambda x: (x[1]['win_rate'], x[1]['matches']))
            
            # Process partner stats
            for partner, stats in partner_stats.items():
                stats['win_rate'] = (stats['wins'] / stats['matches'] * 100) if stats['matches'] > 0 else 0
            
            # Find best partner
            best_partner = max(partner_stats.items(), key=lambda x: (x[1]['win_rate'], x[1]['matches']))
            
            # Get player info
            info = player_info.get(player, {})
            
            # Store comprehensive player stats
            player_stats[player] = {
                'player': player,
                'club': info.get('club', 'Unknown'),
                'series': info.get('series', '').replace('Chicago ', 'Series '),
                'current_streak': {
                    'type': current_streak['type'],
                    'count': current_streak['count'],
                    'start_date': current_streak['start_date']
                },
                'best_win_streak': best_win_streak,
                'best_loss_streak': best_loss_streak,
                'total_matches': total_matches,
                'total_wins': total_wins,
                'total_losses': total_losses,
                'win_rate': round(win_rate, 1),
                'court_stats': court_stats,
                'best_court': {
                    'name': best_court[0],
                    'stats': best_court[1]
                },
                'partner_stats': partner_stats,
                'best_partner': {
                    'name': best_partner[0],
                    'stats': best_partner[1]
                }
            }
        
        # Convert to sorted list for different rankings
        players_list = list(player_stats.values())
        
        # Different sorting criteria
        best_current_streaks = sorted(
            [p for p in players_list if p['current_streak']['type'] == 'W'],
            key=lambda x: (-x['current_streak']['count'], -x['win_rate'])
        )[:10]
        
        best_all_time_streaks = sorted(
            players_list,
            key=lambda x: (-x['best_win_streak']['count'], -x['win_rate'])
        )[:10]
        
        highest_win_rates = sorted(
            [p for p in players_list if p['total_matches'] >= 5],  # Minimum 5 matches
            key=lambda x: (-x['win_rate'], -x['total_matches'])
        )[:10]
        
        return jsonify({
            'success': True,
            'current_streaks': best_current_streaks,
            'all_time_streaks': best_all_time_streaks,
            'win_rates': highest_win_rates
        })
        
    except Exception as e:
        app.logger.error(f"Error calculating enhanced streaks: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/mobile/player-stats')
@login_required
def serve_mobile_player_stats():
    try:
        # Get user info from session
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Get player stats data
        current_streaks = get_current_streaks()
        all_time_streaks = get_all_time_streaks()
        win_rates = get_player_win_rates()
        
        # Log the page visit
        log_user_activity(user['email'], 'page_visit', page='mobile_player_stats')
        
        # Return the rendered template with all the data
        return render_template(
            'mobile/player-stats.html',
            player_name=f"{user['first_name']} {user['last_name']}",
            current_streaks=current_streaks,
            all_time_streaks=all_time_streaks,
            win_rates=win_rates
        )
        
    except Exception as e:
        print(f"Error in serve_mobile_player_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_recent_matches_for_user_club(user):
    """
    Get the most recent matches for a user's club, including all courts.
    
    Args:
        user: User object containing club information
        
    Returns:
        List of match dictionaries from match_history.json filtered for the user's club,
        only including matches from the most recent date
    """
    try:
        with open('data/match_history.json', 'r') as f:
            all_matches = json.load(f)
            
        if not user or not user.get('club'):
            return []
            
        user_club = user['club']
        # Filter matches where user's club is either home or away team
        club_matches = []
        for match in all_matches:
            if user_club in match.get('Home Team', '') or user_club in match.get('Away Team', ''):
                # Normalize keys to snake_case
                normalized_match = {
                    'date': match.get('Date', ''),
                    'time': match.get('Time', ''),
                    'location': match.get('Location', ''),
                    'home_team': match.get('Home Team', ''),
                    'away_team': match.get('Away Team', ''),
                    'winner': match.get('Winner', ''),
                    'scores': match.get('Scores', ''),
                    'home_player_1': match.get('Home Player 1', ''),
                    'home_player_2': match.get('Home Player 2', ''),
                    'away_player_1': match.get('Away Player 1', ''),
                    'away_player_2': match.get('Away Player 2', ''),
                    'court': match.get('Court', '')
                }
                club_matches.append(normalized_match)
        
        # Sort matches by date to find the most recent
        from datetime import datetime
        sorted_matches = sorted(club_matches, key=lambda x: datetime.strptime(x['date'], '%d-%b-%y'), reverse=True)
        
        if not sorted_matches:
            return []
            
        # Get only matches from the most recent date
        most_recent_date = sorted_matches[0]['date']
        recent_matches = [m for m in sorted_matches if m['date'] == most_recent_date]
        
        # Sort by court number if available, handling empty strings and non-numeric values
        def court_sort_key(match):
            court = match.get('court', '')
            if not court or not str(court).strip():
                return float('inf')  # Put empty courts at the end
            try:
                return int(court)
            except (ValueError, TypeError):
                return float('inf')  # Put non-numeric courts at the end
        
        recent_matches.sort(key=court_sort_key)
        return recent_matches
        
    except Exception as e:
        print(f"Error getting recent matches for user club: {e}")
        return []

def get_matches_for_user_club(user):
    """
    Get all matches for a user's club and series.
    
    Args:
        user: User object containing club and series information
        
    Returns:
        List of match dictionaries from match_history.json filtered for the user's club and series
    """
    try:
        with open('data/match_history.json', 'r') as f:
            all_matches = json.load(f)
            
        if not user or not user.get('club') or not user.get('series'):
            return []
            
        user_club = user['club']
        user_series = user['series'].split()[-1]  # Get the series number (e.g., "22" from "Series 22")
        user_team = f"{user_club} - {user_series}"  # Full team name (e.g., "Tennaqua - 22")
        
        # Filter matches where user's team is either home or away team
        club_matches = []
        for match in all_matches:
            home_team = match.get('Home Team', '')
            away_team = match.get('Away Team', '')
            
            # Only include matches where the exact team name matches
            if user_team == home_team or user_team == away_team:
                # Normalize keys to snake_case
                normalized_match = {
                    'date': match.get('Date', ''),
                    'time': match.get('Time', ''),
                    'location': match.get('Location', ''),
                    'home_team': home_team,
                    'away_team': away_team,
                    'winner': match.get('Winner', ''),
                    'scores': match.get('Scores', ''),
                    'home_player_1': match.get('Home Player 1', ''),
                    'home_player_2': match.get('Home Player 2', ''),
                    'away_player_1': match.get('Away Player 1', ''),
                    'away_player_2': match.get('Away Player 2', '')
                }
                club_matches.append(normalized_match)
        
        return club_matches
    except Exception as e:
        print(f"Error getting matches for user club: {e}")
        return []

if __name__ == '__main__':
        # Get port from environment variable or use default
        port = int(os.environ.get("PORT", os.environ.get("RAILWAY_PORT", 8080)))
        host = os.environ.get("HOST", "0.0.0.0")
        
        logger.info("=== SERVER STARTING ===")
        logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
        logger.info(f"Port: {port}")
        logger.info(f"Host: {host}")
        
        try:
            # Configure SocketIO
            socketio = SocketIO(
                app,
                cors_allowed_origins="*",
                async_mode='threading',  # Change to threading mode
                logger=True,
                engineio_logger=True,
                ping_timeout=30,
                ping_interval=15,
                max_http_buffer_size=1024 * 1024,  # 1MB buffer size
                async_handlers=True,
                manage_session=False  # Let Flask handle sessions
            )
            
            # Add error handlers
            @app.errorhandler(500)
            def internal_error(error):
                logger.error(f"Internal Server Error: {error}")
                return jsonify({'error': 'Internal Server Error'}), 500

            @app.errorhandler(502)
            def bad_gateway_error(error):
                logger.error(f"Bad Gateway Error: {error}")
                return jsonify({'error': 'Bad Gateway'}), 502

            # Run the server
            app.run(
                host=host,
                port=port,
                debug=False
            )
            logger.info("Server started successfully")
        except Exception as e:
            logger.error(f"Failed to start server: {str(e)}")
            logger.error(traceback.format_exc())
            sys.exit(1)