from flask import Flask, jsonify, request, send_from_directory, render_template, session, redirect, url_for, make_response
from flask_socketio import SocketIO, emit
import pandas as pd
from flask_cors import CORS
import os
from datetime import datetime
import traceback
import openai
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
from database import get_db

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

# Initialize OpenAI client with organization if provided and disable audio features
client_kwargs = {
    'api_key': openai_api_key,
    'base_url': os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'),  # Use default base URL if not set
}
if openai_org_id:
    client_kwargs['organization'] = openai_org_id
    logger.info(f"Using OpenAI organization: {openai_org_id}")

# Disable audio features by setting the environment variable
os.environ['OPENAI_ENABLE_AUDIO'] = 'false'

try:
    client = openai.OpenAI(**client_kwargs)
except Exception as e:
    logger.error(f"ERROR: Failed to initialize OpenAI client: {str(e)}")
    sys.exit(1)

# Store active threads
active_threads = {}

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')  # Change this in production

# Configure session settings
app.config.update(
    SESSION_COOKIE_SECURE=True,  # Set to True for production with HTTPS
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
            "https://*.up.railway.app"  # Railway domain
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True   # Important for session cookies
    }
})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
        file_path = os.path.join('Data', 'all_tennaqua_players.csv')
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"Successfully loaded {len(df)} player records")
            return df
        else:
            print(f"Warning: Player data file not found at {file_path}")
        return pd.DataFrame()
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
        except openai.NotFoundError:
            print(f"Assistant {assistant_id} not found, creating new one...")
        except Exception as e:
            if "No access to organization" in str(e):
                print(f"ERROR: No access to organization. Please check OPENAI_ORG_ID if using a shared assistant.")
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
    # Set up logging to both console and file
    log_file = 'server.log'
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))
    console_handler.setLevel(logging.DEBUG)
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Suppress OpenAI client logging
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    return logger

# Initialize logging
logger = setup_logging()

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
    """Serve the index page with session data"""
    print("\n=== Serving Index Page ===")
    
    # If user is not authenticated, redirect to login
    if 'user' not in session:
        print("User not authenticated, redirecting to login")
        return redirect(url_for('login'))
    
    print(f"User in session: {session['user']['email']}")
    
    # Log page visit
    try:
        log_user_activity(
            session['user']['email'], 
            'page_visit', 
            page='home',
            details='Accessed home page'
        )
        print("Successfully logged home page visit")
    except Exception as e:
        print(f"Error logging home page visit: {str(e)}")
        print(traceback.format_exc())
    
    # Read the index.html file
    try:
        static_dir = os.path.join(app.root_path, 'static')
        with open(os.path.join(static_dir, 'index.html'), 'r') as f:
            html_content = f.read()
            
        # Create session data script
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        session_script = f'<script>window.sessionData = {json.dumps(session_data)};</script>'
        
        # Insert the session data script before the closing </head> tag
        html_with_session = html_content.replace('</head>', f'{session_script}</head>')
        
        return html_with_session
        
    except Exception as e:
        print(f"Error serving index page: {str(e)}")
        print(traceback.format_exc())
        return "Error: Could not serve index page", 500

@app.route('/login')
def login():
    """Serve the login page"""
    # If user is already authenticated, redirect to home
    if 'user' in session:
        return redirect(url_for('serve_index'))
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
        
        conn = sqlite3.connect('data/paddlepro.db')
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
            
            return jsonify({'status': 'success'})
            
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
            
        conn = sqlite3.connect('data/paddlepro.db')
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
            
            # Create response with session cookie settings
            response = jsonify({'status': 'success'})
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
        conn = sqlite3.connect('data/paddlepro.db')
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

# Protect all API routes except check-auth and login
@app.route('/api/<path:path>', methods=['GET', 'POST'])
def api_route(path):
    """Handle API routes and log access"""
    print(f"\n=== API Route Access ===")
    print(f"Path: {path}")
    print(f"Method: {request.method}")
    print(f"User in session: {'user' in session}")
    
    # List of routes that don't require authentication
    public_routes = ['check-auth', 'login', 'register']
    
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
    return None

@app.route('/api/set-series', methods=['POST'])
def set_series():
    global selected_series, selected_club
    data = request.get_json()
    selected_series = data.get('series', "Chicago 22")
    selected_club = f"Tennaqua - {selected_series.split()[-1]}"
    return jsonify({'status': 'success', 'series': selected_series})

@app.route('/api/get-series')
@app.route('/get-series')
def get_series():
    try:
        print("\n=== GET SERIES REQUEST ===")
        print("Connecting to database...")
        conn = sqlite3.connect('data/paddlepro.db')
        cursor = conn.cursor()
        
        # Get all series from the database
        print("Executing SQL query...")
        cursor.execute('SELECT name FROM series ORDER BY name')
        series_list = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"\nCurrent series: {selected_series}")
        print(f"Available series: {series_list}")
        print(f"Number of series: {len(series_list)}")
        
        # Log each series with its extracted number
        print("\nSeries with extracted numbers:")
        for series in series_list:
            num = ''.join(filter(str.isdigit, series))
            print(f"Series: {series}, Number: {num}")
        
        # Always return the current series and all available series
        response_data = {
            'series': selected_series,
            'club': selected_club,
            'all_series': series_list
        }
        
        print(f"\nReturning response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        print(f"\nError getting series: {str(e)}")
        print("Full error:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/get-players-series-22', methods=['GET'])
def get_players_series_22():
    """Get all players in Series 22"""
    print("\n=== Getting Players for Series 22 ===")
    try:
        df = pd.read_csv('data/all_tennaqua_players.csv')
        
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
        data = request.get_json()
        players = data.get('players', [])
        instructions = data.get('instructions', [])
        
        if not players:
            logger.error("No players selected for lineup generation")
            return jsonify({'error': 'No players selected'}), 400
            
        # Log lineup generation with more details
        log_user_activity(
            session['user']['email'], 
            'feature_use', 
            action='generate_lineup',
            details=f"Players: {', '.join(players)}. Instructions: {len(instructions)} provided."
        )

        # Create a new thread
        thread = client.beta.threads.create()
        logger.debug(f"Created new thread with ID: {thread.id}")
        
        # Format the instructions for the prompt
        instructions_text = ""
        if instructions:
            instructions_text = "\n".join([f"- {instruction}" for instruction in instructions])
        
        # Create a clean prompt
        prompt_text = f"""Generate an optimal lineup for the following AVAILABLE players: {', '.join(players)}

Additional Instructions to be followed as secondary. Only include the specific AVAILABLE players above.
{instructions_text}

Above all else, only include AVAILABLE players, even if a player is mentioned in the additional instructions.

Format the lineup exactly like this example:
Court 1: Player1/Player2
Court 2: Player3/Player4
Court 3: Player5/Player6
Court 4: Player7/Player8

Add a 3-5 sentence explanation after you list the lineup: [Your explanation here]"""
        
        # Add a message to the thread
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt_text
        )
        
        # Print the prompt to terminal
        print("\n=== PROMPT ===")
        print(prompt_text)
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Wait for the run to complete
        while True:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run.status == 'completed':
                break
            elif run.status in ['failed', 'cancelled', 'expired']:
                error_msg = f'Run failed with status: {run.status}'
                logger.error(error_msg)
                return jsonify({'error': error_msg}), 500
            time.sleep(1)
        
        # Get the assistant's response
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )
        
        # Get the most recent message from the assistant
        assistant_message = next((msg for msg in messages.data if msg.role == 'assistant'), None)
        if not assistant_message:
            error_msg = 'No response from assistant'
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 500
            
        # Clean up the response by removing asterisks
        response_text = assistant_message.content[0].text.value.replace('**', '')
            
        # Print the response to terminal
        print("\n=== RESPONSE ===")
        print(response_text)
        
        return jsonify({'suggestion': response_text})
        
    except Exception as e:
        error_msg = f"Error in generate_lineup: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())  # Log full traceback
        print(error_msg)  # Also print to terminal
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
        schedule_path = os.path.join('data', 'Series_22_schedule.json')
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
        stats_path = os.path.join('data', 'Chicago_22_stats_20250425.json')
        matches_path = os.path.join('data', 'tennis_matches_20250416.json')
        
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
                
            conn = sqlite3.connect('data/paddlepro.db')
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE user_instructions
            SET is_active = 0
            WHERE instruction = ? AND user_email = ? AND team_id = ?
            ''', (instruction, user_email, team_id))
            
            conn.commit()
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
        with get_db() as conn:
            with conn.cursor() as cursor:
                query = '''
                SELECT id, instruction, team_id, created_at
                FROM user_instructions
                WHERE user_email = %s AND is_active = true
                '''
                params = [user_email]
                
                if team_id:
                    query += ' AND team_id = %s'
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
                    
                return result
    except Exception as e:
        logger.error(f"Error getting user instructions: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def add_user_instruction(user_email, instruction, team_id=None):
    """Add a new instruction for a user, optionally associated with a team"""
    logger.info(f"Adding instruction for user: {user_email}, team_id: {team_id}")
    logger.debug(f"Instruction text: {instruction}")
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                query = '''
                INSERT INTO user_instructions (user_email, instruction, team_id)
                VALUES (%s, %s, %s)
                '''
                params = (user_email, instruction, team_id)
                logger.debug(f"Executing query: {query} with params: {params}")
                cursor.execute(query, params)
                conn.commit()
                logger.info("Successfully added instruction")
                return True
    except Exception as e:
        logger.error(f"Error adding user instruction: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def deactivate_instruction(user_email, instruction_id):
    """Deactivate an instruction for a user"""
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                UPDATE user_instructions 
                SET is_active = false 
                WHERE id = %s AND user_email = %s
            ''', (instruction_id, user_email))
            conn.commit()

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
        with open('data/Series_22_schedule.json', 'r') as f:
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
        # The schedule uses format "Club Name - 22" while we store it as "Club Name"
        club_name = f"{user_club} - 22"
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
        print(f"❌ Schedule file not found at data/Series_22_schedule.json")
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
        conn = sqlite3.connect('data/paddlepro.db')
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
            conn = sqlite3.connect('data/paddlepro.db')
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
            conn = sqlite3.connect('data/paddlepro.db')
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
        conn = sqlite3.connect('data/paddlepro.db')
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
        conn = sqlite3.connect('data/paddlepro.db')
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
        return jsonify({
            'authenticated': True,
            'user': session['user']
        })
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
        
        conn = sqlite3.connect('data/paddlepro.db')
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
        conn = sqlite3.connect('data/paddlepro.db')
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
        conn = sqlite3.connect('data/paddlepro.db')
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
            
        conn = sqlite3.connect('data/paddlepro.db')
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
            
        conn = sqlite3.connect('data/paddlepro.db')
        cursor = conn.cursor()
        
        # Update club name
        cursor.execute('UPDATE clubs SET name = %s WHERE name = %s', (new_name, old_name))
        
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
            
        conn = sqlite3.connect('data/paddlepro.db')
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
            conn = sqlite3.connect('data/paddlepro.db')
            cursor = conn.cursor()
            cursor.execute('SELECT club_automation_password FROM users WHERE email = %s', (user_email,))
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
    """Return the series stats JSON file for Chicago 22"""
    try:
        # Read the stats file
        stats_path = os.path.join('data', 'Chicago_22_stats_20250425.json')
        matches_path = os.path.join('data', 'tennis_matches_20250416.json')
        
        if not os.path.exists(stats_path):
            return jsonify({'error': 'Stats file not found'}), 404
        with open(stats_path, 'r') as f:
            stats = json.load(f)
            
        # Get the requested team from query params
        requested_team = request.args.get('team')
        
        if requested_team:
            team_stats = next((team for team in stats if team['team'] == requested_team), None)
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
                        
                        # Analyze match patterns
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
            
        # If no team requested, return all stats
        return jsonify({'teams': stats})
        
    except Exception as e:
        print(f"Error reading series stats: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to read stats file'}), 500

@app.route('/api/player-contact')
def get_player_contact():
    first_name = request.args.get('firstName')
    last_name = request.args.get('lastName')
    
    if not first_name or not last_name:
        return jsonify({'error': 'Missing first or last name parameter'}), 400
        
    try:
        # Query the database for player contact info
        player = db.session.query(Player).filter(
            Player.first_name == first_name,
            Player.last_name == last_name
        ).first()
        
        if not player:
            return jsonify({'error': 'Player not found'}), 404
            
        return jsonify({
            'phone': player.phone,
            'email': player.email
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching player contact info: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/players')
@login_required
def get_players_by_series():
    """Get players for a specific series"""
    try:
        series = request.args.get('series')
        if not series:
            return jsonify({'error': 'Series parameter is required'}), 400
            
        print(f"\n=== Getting Players for {series} ===")
        df = pd.read_csv('data/all_tennaqua_players.csv')
        
        # Filter for the requested series
        series_df = df[df['Series'] == series]
        print(f"Found {len(series_df)} players in {series}")
        
        players = []
        for _, row in series_df.iterrows():
            player = {
                'name': f"{row['First Name']} {row['Last Name']}",  # Already in First Name Last Name format
                'series': row['Series'],
                'rating': str(row['PTI']),
                'wins': str(row['Wins']),
                'losses': str(row['Losses']),
                'winRate': row['Win %']
            }
            players.append(player)
            
        return jsonify(players)
        
    except Exception as e:
        print(f"\nERROR getting players for {series}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/team-players/<team_id>')
@login_required
def get_team_players(team_id):
    """Get all players who have played for a specific team"""
    try:
        matches_path = os.path.join('data', 'tennis_matches_20250416.json')
        players_path = os.path.join('data', 'all_tennaqua_players.csv')  # Changed from 'Data' to 'data'
        
        if not os.path.exists(matches_path):
            return jsonify({'error': 'Match data not found'}), 404
            
        # Read the players CSV file to get PTI ratings
        df = pd.read_csv(players_path)
        pti_dict = {}
        for _, row in df.iterrows():
            player_name = f"{row['Last Name']} {row['First Name']}"
            pti_dict[player_name] = float(row['PTI'])
            
        with open(matches_path, 'r') as f:
            matches = json.load(f)
            
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
        print("\n=== UPDATING USER SETTINGS ===")
        print("Received data:", data)
        print("clubAutomationPassword received:", data.get('clubAutomationPassword', '[not present]'))
        
        if not all(key in data for key in ['firstName', 'lastName', 'email', 'series', 'club']):
            print("Missing required fields in request data")
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        current_email = session['user']['email']
        print(f"Updating settings for user: {current_email}")
        
        conn = sqlite3.connect('data/paddlepro.db')
        cursor = conn.cursor()
        
        try:
            # Get series ID
            cursor.execute('SELECT id FROM series WHERE name = ?', (data['series'],))
            series_result = cursor.fetchone()
            if not series_result:
                print(f"Series not found: {data['series']}")
                return jsonify({'success': False, 'message': 'Invalid series selected'}), 400
            series_id = series_result[0]
            
            # Get club ID
            cursor.execute('SELECT id FROM clubs WHERE name = ?', (data['club'],))
            club_result = cursor.fetchone()
            if not club_result:
                print(f"Club not found: {data['club']}")
                return jsonify({'success': False, 'message': 'Invalid club selected'}), 400
            club_id = club_result[0]
            
            # Optionally update club_automation_password if provided
            if 'clubAutomationPassword' in data and data['clubAutomationPassword'] is not None:
                print("Updating club_automation_password to:", data.get('clubAutomationPassword', ''))
                print("[DEBUG] SQL UPDATE with club_automation_password:")
                print("SQL:", '''UPDATE users SET first_name = ?, last_name = ?, email = ?, series_id = ?, club_id = ?, club_automation_password = ? WHERE email = ?''')
                print("Values:", data['firstName'], data['lastName'], data['email'], series_id, club_id, data.get('clubAutomationPassword', ''), current_email)
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
                print("[DEBUG] SQL UPDATE without club_automation_password:")
                print("SQL:", '''UPDATE users SET first_name = ?, last_name = ?, email = ?, series_id = ?, club_id = ? WHERE email = ?''')
                print("Values:", data['firstName'], data['lastName'], data['email'], series_id, club_id, current_email)
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
                print("No rows were updated - user not found")
                return jsonify({'success': False, 'message': 'User not found'}), 404
            
            conn.commit()
            print("Settings updated successfully")
            
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
            print(f"Database error: {str(e)}")
            conn.rollback()
            return jsonify({'success': False, 'message': 'Database error occurred'}), 500
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        import traceback
        print("Full error:", traceback.format_exc())
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
            
        conn = sqlite3.connect('data/paddlepro.db')
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
    print(f"\n=== LOGGING USER ACTIVITY ===")
    print(f"User: {user_email}")
    print(f"Type: {activity_type}")
    print(f"Page: {page}")
    print(f"Action: {action}")
    print(f"Details: {details}")
    
    try:
        conn = sqlite3.connect('data/paddlepro.db')
        cursor = conn.cursor()
        try:
            # Get IP address from request if available
            ip_address = request.remote_addr if request else None
            print(f"IP Address: {ip_address}")
            
            # Insert the activity log
            print("Inserting activity log...")
            insert_query = '''
                INSERT INTO user_activity_logs 
                (user_email, activity_type, page, action, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            params = (user_email, activity_type, page, action, details, ip_address)
            print(f"Query: {insert_query}")
            print(f"Parameters: {params}")
            
            cursor.execute(insert_query, params)
            conn.commit()
            print("Activity logged successfully")
            
            # Verify the log was written
            print("Verifying log entry...")
            cursor.execute('''
                SELECT * FROM user_activity_logs 
                WHERE user_email = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (user_email,))
            last_log = cursor.fetchone()
            if last_log:
                print(f"Last log entry: {last_log}")
            else:
                print("WARNING: Log entry not found after insert!")
        finally:
            conn.close()
                    
    except Exception as e:
        print(f"Database error during transaction: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Full error details: {traceback.format_exc()}")
        raise

@app.route('/api/admin/user-activity/<email>')
@login_required
def get_user_activity(email):
    """Get activity logs for a specific user"""
    try:
        print(f"\n=== Getting Activity for User: {email} ===")
        conn = sqlite3.connect('data/paddlepro.db')
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
                       datetime(timestamp, 'localtime') as local_time,
                       timestamp as utc_time
                FROM user_activity_logs
                WHERE user_email = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1000
            ''', (email,))
            
            logs = []
            print("\nMost recent activities:")
            for idx, row in enumerate(cursor.fetchall()):
                if idx < 5:  # Print details of 5 most recent activities
                    print(f"ID: {row[0]}, Type: {row[1]}, Time (Local): {row[6]}, Time (UTC): {row[7]}")
                
                logs.append({
                    'id': row[0],
                    'activity_type': row[1],
                    'page': row[2],
                    'action': row[3],
                    'details': row[4],
                    'ip_address': row[5],
                    'timestamp': row[7]  # Use UTC time
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
        conn = sqlite3.connect('data/paddlepro.db')
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
        conn = sqlite3.connect('data/paddlepro.db')
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
        conn = sqlite3.connect('data/paddlepro.db')
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
@login_required
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
    """Basic healthcheck endpoint"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", os.environ.get("RAILWAY_PORT", 3000)))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info("=== SERVER STARTING ===")
    logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    logger.info(f"Port: {port}")
    logger.info(f"Host: {host}")
    
    try:
        # Initialize eventlet
        import eventlet
        eventlet.monkey_patch()
        
        # Configure SocketIO
        socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='eventlet',
            logger=True,
            engineio_logger=True,
            ping_timeout=60,
            ping_interval=25
        )
        
        # Run the server
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            log_output=True
        )
        logger.info("Server started successfully")
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)