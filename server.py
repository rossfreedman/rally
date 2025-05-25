from flask import Flask, jsonify, request, send_from_directory, render_template, session, redirect, url_for, make_response, g, flash
from flask_socketio import SocketIO, emit
import pandas as pd
from flask_cors import CORS
import os
from datetime import datetime, timedelta, date
import traceback
from openai import OpenAI
from dotenv import load_dotenv
import time
from functools import wraps
import sys
import re
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
from werkzeug.security import generate_password_hash, check_password_hash
from database_utils import get_db_cursor as get_db, execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from routes.analyze import init_analyze_routes
from routes.act import init_act_routes
from routes.admin import admin_bp
from routes.act.availability import update_player_availability as act_update_player_availability

def is_public_file(path):
    """Check if a file should be publicly accessible without authentication"""
    # List of files that should be publicly accessible
    public_files = [
        'login.html',
        'register.html',
        'favicon.ico',
        'robots.txt',
        'js/logout.js',  # Make logout.js always accessible
        'mobile/css/tailwind.css',
        'mobile/css/style.css',
        'images/rallylogo.png',
        'images/rally_favicon.png'
    ]
    
    # List of directories that should be publicly accessible
    public_dirs = [
        'css/',
        'fonts/',
        'images/'
    ]
    
    # Check if the file is in the public list
    if any(path.endswith(f) for f in public_files):
        return True
        
    # Check if the file is in a public directory
    if any(path.startswith(d) for d in public_dirs):
        return True
        
    return False

# Test database connection
print("\n=== Testing Database Connection ===")
try:
    result = execute_query_one('SELECT 1 as test')
    if result and result['test'] == 1:
        print("Database connection successful!")
        
        # Check if tables exist and initialize if needed
        print("\n=== Checking Database Tables ===")
        tables_result = execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        existing_tables = [row['table_name'] for row in tables_result]
        
        if 'clubs' not in existing_tables or 'series' not in existing_tables:
            print("Tables missing, initializing database...")
            from init_db import init_db
            init_db()
        else:
            print("Database tables exist")
            
            # Check if clubs and series have data
            clubs_count = execute_query_one("SELECT COUNT(*) as count FROM clubs")
            series_count = execute_query_one("SELECT COUNT(*) as count FROM series")
            
            if clubs_count['count'] == 0 or series_count['count'] == 0:
                print("Tables empty, initializing with default data...")
                from init_db import init_db
                init_db()
            else:
                print(f"Found {clubs_count['count']} clubs and {series_count['count']} series")
    else:
        print("Database connection test failed!")
        sys.exit(1)
except Exception as e:
    print(f"Error connecting to database: {str(e)}")
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
    api_key=openai_api_key
)

# Store active threads
active_threads = {}

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Determine environment
is_development = os.environ.get('FLASK_ENV') == 'development'

# Register blueprints
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# Register training data API blueprint
from api.training_data import training_data_bp
app.register_blueprint(training_data_bp)

# Initialize ACT routes
init_act_routes(app)

# Configure CORS for admin routes
CORS(app, resources={
    r"/admin/*": {
        "origins": ["*"] if is_development else [
            "https://*.up.railway.app",
            "https://*.railway.app",
            "https://lovetorally.com",
            "https://www.lovetorally.com"
        ],
        "supports_credentials": True,
        "allow_headers": ["Content-Type", "X-Requested-With", "Authorization"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }
})

# Set secret key
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Session config
app.config.update(
    SESSION_COOKIE_SECURE=not is_development,  # True in production, False in development
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    SESSION_COOKIE_NAME='rally_session',
    SESSION_COOKIE_PATH='/',
    SESSION_REFRESH_EACH_REQUEST=True
)

# Configure CORS
CORS(app, 
     resources={
         r"/api/*": {
             "origins": ["*"] if is_development else [
                 "https://*.up.railway.app",
                 "https://*.railway.app",
                 "https://lovetorally.com",
                 "https://www.lovetorally.com"
             ],
             "supports_credentials": True,
             "allow_headers": ["Content-Type", "X-Requested-With", "Authorization"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
         }
     },
     expose_headers=["Set-Cookie"])

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active threads
active_threads = {}

# Login required decorator
from utils.auth import login_required

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
            model="gpt-4"  # Match the UI model
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
    """Serve the index page"""
    print(f"Session at index: {session}")
    if 'user' not in session:
        print("No user in session, redirecting to login")
        return redirect('/login')
        
    print("User in session, redirecting to mobile")
    return redirect('/mobile')

@app.route('/index.html')
def redirect_index_html():
    return redirect('/mobile')

# Authentication routes and functions moved to routes/act/auth.py

# All authentication routes moved to routes/act/auth.py

# Admin routes
def admin_required(f):
    """Decorator to check if user is an admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"=== ADMIN_REQUIRED CHECK ===")
        print(f"User in session: {'user' in session}")
        if 'user' in session:
            print(f"User email: {session['user']['email']}")
        
        if 'user' not in session:
            print("No user in session, redirecting to login")
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        
        try:
            print(f"Checking admin status for: {session['user']['email']}")
            user = execute_query_one(
                "SELECT id, email FROM users WHERE email = %(email)s",
                {'email': session['user']['email']}
            )
            print(f"Database user result: {user}")
            
            if not user:
                print("User not found in database, redirecting to index")
                flash('User not found.', 'error')
                return redirect(url_for('serve_index'))
                
            if user['id'] not in [1, 7]:  # TODO: Implement proper admin roles
                print(f"User ID {user['id']} is not admin (allowed IDs: 1, 7), redirecting to index")
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('serve_index'))
                
            print("Admin check passed, proceeding to admin function")
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error checking admin status: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            flash('An error occurred while checking permissions.', 'error')
            return redirect(url_for('serve_index'))
            
    return decorated_function

@app.route('/admin')
@login_required
@admin_required
def serve_admin():
    """Serve the admin dashboard"""
    print(f"=== SERVE_ADMIN FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"User in session: {session.get('user', 'No user')}")
    
    log_user_activity(session['user']['email'], 'page_visit', page='admin')
    
    # Check if request is from mobile but ALWAYS use admin template
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad'])
    
    print(f"Is mobile: {is_mobile}")
    print(f"About to render template...")
    
    if is_mobile:
        print("Rendering mobile admin template")
        return render_template('mobile/admin.html', session_data={'user': session['user']})
    
    print("Rendering desktop admin template")
    return render_template('admin/index.html', session_data={'user': session['user']})

@app.route('/contact-sub')
@login_required
def serve_contact_sub():
    """Serve the contact sub page"""
    return send_from_directory('static/components', 'contact-sub.html')

@app.route('/<path:path>')
@login_required
def serve_static(path):
    """Serve static files with proper access control"""
    print(f"\n=== Serving Static File ===")
    print(f"Path: {path}")
    print(f"Is public: {is_public_file(path)}")
    print(f"User in session: {'user' in session}")
    
    # Special handling for favicon.ico
    if path == 'favicon.ico':
        try:
            return send_from_directory('static/images', 'rally_favicon.png', mimetype='image/x-icon')
        except Exception as e:
            print(f"Error serving favicon: {str(e)}")
            return '', 404
    
    # Allow access to public files without authentication
    if is_public_file(path):
        print("Serving public file")
        try:
            response = send_from_directory('static', path)
            print(f"Successfully served {path}")
            return response
        except Exception as e:
            print(f"Error serving {path}: {str(e)}")
            return str(e), 500
    
    # Require authentication for all other files
    if 'user' not in session:
        print("Access denied - no user in session")
        if path.startswith('api/'):
            return jsonify({'error': 'Not authenticated'}), 401
        return redirect(url_for('login'))
    
            # Serve the file if authenticated
    try:
        response = send_from_directory('static', path)
        print(f"Successfully served {path}")
        return response
    except Exception as e:
        print(f"Error serving {path}: {str(e)}")
        return str(e), 500

@app.route('/api/admin/users')
@login_required
def get_admin_users():
    """Get all registered users with their club and series information"""
    try:
        users = execute_query('''
            SELECT u.id, u.first_name, u.last_name, u.email, u.last_login,
                   c.name as club_name, s.name as series_name
            FROM users u
            LEFT JOIN clubs c ON u.club_id = c.id
            LEFT JOIN series s ON u.series_id = s.id
            ORDER BY u.last_name, u.first_name
        ''')
        return jsonify(users)
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

# Reserve court route moved to routes/act/court.py

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
                                    'wins': 0, 'matches': 0
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

# Player contact route moved to routes/act/find_sub.py

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

# Update settings route moved to routes/act/settings.py

@app.route('/test-static')
def test_static():
    """Test route to verify static file serving"""
    try:
        return send_from_directory('static', 'rallylogo.png')
    except Exception as e:
        return str(e), 500

@app.route('/test-video')
def test_video():
    """Test route for video embedding"""
    try:
        return render_template('test_video.html')
    except Exception as e:
        print(f"Error serving test video page: {str(e)}")
        return str(e), 500

@app.route('/api/admin/delete-user', methods=['POST'])
@login_required
@admin_required
def delete_user():
    """Delete a user from the database"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Get user details for logging before deletion
        user = execute_query_one(
            "SELECT first_name, last_name FROM users WHERE email = %(email)s",
            {'email': email}
        )
        
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Delete user and related data
        execute_update("""
            DELETE FROM user_activity_logs WHERE user_email = %(email)s;
            DELETE FROM user_instructions WHERE user_email = %(email)s;
            DELETE FROM player_availability WHERE player_name = %(email)s;
            DELETE FROM users WHERE email = %(email)s;
        """, {'email': email})
        
        # Log the deletion
        log_user_activity(
            session['user']['email'],
            'admin_action',
            action='delete_user',
            details=f"Deleted user: {user['first_name']} {user['last_name']} ({email})"
        )
        
        return jsonify({
            'status': 'success',
            'message': 'User deleted successfully'
        })
            
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/user-activity/<email>')
@login_required
def get_user_activity(email):
    """Get activity logs for a specific user"""
    try:
        print(f"\n=== Getting Activity for User: {email} ===")
        
        # Get user details first
        print("Fetching user details...")
        user = execute_query_one(
            """
            SELECT first_name, last_name, email, last_login
            FROM users
            WHERE email = %(email)s
            """,
            {'email': email}
        )
        
        if not user:
            print(f"User not found: {email}")
            return jsonify({'error': 'User not found'}), 404
            
        print(f"Found user: {user['first_name']} {user['last_name']}")
            
        # Get activity logs with explicit timestamp ordering
        print("Fetching activity logs...")
        logs = execute_query(
            """
            SELECT id, activity_type, page, action, details, ip_address, 
                   timezone('America/Chicago', timestamp) as central_time
            FROM user_activity_logs
            WHERE user_email = %(email)s
            ORDER BY timestamp DESC, id DESC
            LIMIT 1000
            """,
            {'email': email}
        )
        
        print("\nMost recent activities:")
        for idx, log in enumerate(logs[:5]):  # Print details of 5 most recent activities
            print(f"ID: {log['id']}, Type: {log['activity_type']}, Time: {log['central_time']}")
        
        formatted_logs = [{
            'id': log['id'],
            'activity_type': log['activity_type'],
            'page': log['page'],
            'action': log['action'],
            'details': log['details'],
            'ip_address': log['ip_address'],
            'timestamp': log['central_time'].isoformat()  # Format timestamp as ISO string
        } for log in logs]
        
        print(f"\nFound {len(formatted_logs)} activity logs")
        if formatted_logs:
            print(f"Most recent log ID: {formatted_logs[0]['id']}")
            print(f"Most recent timestamp: {formatted_logs[0]['timestamp']}")
        
        response_data = {
            'user': {
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'email': user['email'],
                'last_login': user['last_login']
            },
            'activities': formatted_logs
        }
        
        print("Returning response data")
        print("=== End Activity Request ===\n")
        
        # Create response with cache-busting headers
        response = jsonify(response_data)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
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
        success = log_user_activity(
            user_email,
            'test',
            page='test_page',
            action='test_action',
            details='Testing activity logging'
        )
        
        if not success:
            return jsonify({'error': 'Failed to log activity'}), 500
        
        # Try to read back the test activity
        last_log = execute_query_one(
            """
            SELECT * FROM user_activity_logs 
            WHERE user_email = %(email)s 
            ORDER BY timestamp DESC 
            LIMIT 1
            """,
            {'email': user_email}
        )
        
        if last_log:
            return jsonify({
                'status': 'success',
                'last_log': {
                    'id': last_log['id'],
                    'activity_type': last_log['activity_type'],
                    'page': last_log['page'],
                    'action': last_log['action'],
                    'details': last_log['details'],
                    'timestamp': last_log['timestamp'].isoformat()
                }
            })
        else:
            return jsonify({'error': 'Activity log not found after insert'}), 500
            
    except Exception as e:
        print(f"Error testing activity logging: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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
        last_log = execute_query_one('''
            SELECT * FROM user_activity_logs 
            WHERE user_email = %(email)s 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', {'email': user_email})
        
        if last_log:
            return jsonify({
                'status': 'success',
                'message': 'Activity logged successfully',
                'log': {
                    'id': last_log['id'],
                    'email': last_log['user_email'],
                    'type': last_log['activity_type'],
                    'page': last_log['page'],
                    'action': last_log['action'],
                    'details': last_log['details'],
                    'ip': last_log['ip_address'],
                    'timestamp': last_log['timestamp'].isoformat() if isinstance(last_log['timestamp'], datetime) else last_log['timestamp']
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Activity was not logged'
            }), 500
            
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
        last_log = execute_query_one('''
            SELECT * FROM user_activity_logs 
            WHERE user_email = %(email)s AND activity_type = 'test'
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', {'email': user_email})
        
        if last_log:
            return jsonify({
                'status': 'success',
                'message': 'Logging system verified',
                'log': {
                    'id': last_log['id'],
                    'email': last_log['user_email'],
                    'type': last_log['activity_type'],
                    'page': last_log['page'],
                    'action': last_log['action'],
                    'details': last_log['details'],
                    'timestamp': last_log['timestamp'].isoformat() if isinstance(last_log['timestamp'], datetime) else last_log['timestamp']
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Log entry not found after writing'
            }), 500
            
    except Exception as e:
        print(f"Error in verify logging: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/log-click', methods=['POST'])
def log_click():
    """Handle click tracking - DISABLED"""
    return jsonify({'status': 'tracking disabled'}), 200

# Add a basic healthcheck endpoint
@app.route('/health')
def healthcheck():
    """Basic healthcheck endpoint that also verifies database connection"""
    try:
        # Test database connection
        result = execute_query_one('SELECT 1 as test')
        
        if result and result['test'] == 1:
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

# Team matches route moved to routes/act/schedule.py

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
    print(f"=== SERVE_MOBILE FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    
    # Don't handle admin routes
    if '/admin' in request.path:
        print("Admin route detected in mobile, redirecting to serve_admin")
        return redirect(url_for('serve_admin'))
        
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
            page='mobile_home'
        )
    except Exception as e:
        print(f"Error logging mobile access: {str(e)}")
    
    return render_template('mobile/index.html', session_data=session_data)

@app.route('/mobile/rally')
@login_required
def serve_rally_mobile():
    """Redirect from old mobile interface to new one"""
    try:
        # Log the redirect
        log_user_activity(
            session['user']['email'], 
            'redirect',
            page='rally_mobile_to_new',
            details='Redirected from old mobile interface to new one'
        )
    except Exception as e:
        print(f"Error logging rally mobile redirect: {str(e)}")
    
    return redirect(url_for('serve_mobile_index'))

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

# Lineup routes moved to routes/act/lineup.py

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
    """Get availability for a user across multiple matches"""
    # First get the series_id
    series_record = execute_query_one(
        "SELECT id FROM series WHERE name = %(series)s",
        {'series': series}
    )
    
    if not series_record:
        return []
        
    availability = []
    for match in matches:
        match_date = match.get('date', '')
        # Pass all required arguments: player_name, match_date, and series
        avail_status = get_player_availability(player_name, match_date, series)
        
        if avail_status is None:
            availability.append({'availability_status': 0})  # Default to "not set"
        else:
            availability.append({'availability_status': avail_status})
        
    return availability

# Mobile availability route moved to routes/act/availability.py

# Mobile find-subs route moved to routes/act/find_sub.py

@app.route('/mobile/view-schedule')
@login_required
def serve_mobile_view_schedule():
    """Serve the mobile View Schedule page with the user's schedule."""
    try:
        print("\n=== VIEW SCHEDULE REQUEST ===")
        user = session.get('user')
        print(f"User from session: {user}")
        
        if not user:
            print("❌ No user in session")
            return redirect(url_for('login'))
            
        matches = get_matches_for_user_club(user)
        print(f"Found {len(matches)} matches for user")
        
        # Sort matches by date
        from datetime import datetime
        try:
            # First try MM/DD/YYYY format (from schedules.json)
            matches = sorted(matches, key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y'))
            print("Sorted matches using MM/DD/YYYY format")
        except Exception as e:
            print(f"Error sorting matches with MM/DD/YYYY format: {e}")
            try:
                # Try DD-Mon-YY format
                matches = sorted(matches, key=lambda x: datetime.strptime(x['date'], '%d-%b-%y'))
                print("Sorted matches using DD-Mon-YY format")
            except Exception as e2:
                print(f"Error sorting matches with DD-Mon-YY format: {e2}")
                try:
                    # Try YYYY-MM-DD format
                    matches = sorted(matches, key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
                    print("Sorted matches using YYYY-MM-DD format")
                except Exception as e3:
                    print(f"Error sorting matches with any format, using string sort: {e3}")
                    matches = sorted(matches, key=lambda x: x['date'])
        
        # Add formatted_date to each match
        for match in matches:
            try:
                # Try different date formats
                dt = None
                date_formats = ['%m/%d/%Y', '%d-%b-%y', '%Y-%m-%d']
                date_str = match['date']
                
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if dt:
                    # Format for display
                    match['formatted_date'] = f"{dt.strftime('%A')} {dt.month}/{dt.day}/{dt.strftime('%y')}"
                    # Also store the raw datetime for template use
                    match['datetime'] = dt
                else:
                    print(f"Could not parse date: {date_str}")
                    match['formatted_date'] = date_str
                    match['datetime'] = None
            except Exception as e:
                print(f"Error formatting date {match.get('date')}: {e}")
                match['formatted_date'] = match.get('date', '')
                match['datetime'] = None
            
            # Ensure all required fields exist
            match.setdefault('time', '')
            match.setdefault('location', '')
            match.setdefault('home_team', '')
            match.setdefault('away_team', '')
            match.setdefault('type', 'match')
            
            # Add practice flag if needed
            match['is_practice'] = match.get('type', '') == 'Practice'
            
            # Clean up time format if needed
            if match['time']:
                try:
                    # Parse and reformat time to ensure consistency
                    time_obj = datetime.strptime(match['time'], '%I:%M %p')
                    match['time'] = time_obj.strftime('%I:%M %p').lstrip('0')
                except ValueError:
                    # If parsing fails, just use the original time
                    match['time'] = match['time'].lstrip('0')

        session_data = {
            'user': user,
            'authenticated': True
        }
        
        # Log the page visit
        log_user_activity(
            user['email'],
            'page_visit',
            page='mobile_view_schedule',
            details='Viewed schedule'
        )
        
        print(f"Rendering template with {len(matches)} matches")
        # Pass user directly to the template in addition to session_data
        return render_template('mobile/view_schedule.html', 
                             session_data=session_data,
                             matches=matches,
                             user=user)  # Add user object here
                             
    except Exception as e:
        print(f"❌ Error in view schedule: {str(e)}")
        print(traceback.format_exc())  # Print full traceback for debugging
        return redirect(url_for('login'))

# Mobile ask-ai route moved to routes/act/rally_ai.py

@app.template_filter('parse_date')
def parse_date(value):
    """
    Jinja2 filter to parse a date string or datetime.date into a datetime object.
    Handles multiple date formats.
    """
    from datetime import datetime, date
    
    if not value:
        return None
    
    # If already a datetime.date, convert to datetime with default time
    if isinstance(value, date):
        return datetime.combine(value, datetime.strptime('6:30 PM', '%I:%M %p').time())
    
    # If already a datetime, return as is
    if isinstance(value, datetime):
        return value
    
    # Try different date formats for strings
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d-%b-%y"
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(str(value), fmt)
            # Add default time of 6:30 PM if not specified
            if dt.hour == 0 and dt.minute == 0:
                dt = dt.replace(hour=18, minute=30)
            return dt
        except ValueError:
            continue
    
    return None

@app.template_filter('pretty_date')
def pretty_date(value):
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%y']
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value
            
        # Format with day of week followed by date
        day_of_week = date_obj.strftime('%A')
        date_str = date_obj.strftime('%-m/%-d/%y')
        return f"{day_of_week} {date_str}"
    except Exception as e:
        print(f"Error formatting date: {e}")
        return value

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
        
        # Get current PTI from player history
        try:
            player_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'player_history.json')
            print(f"Loading player history from: {player_history_path}")
            
            with open(player_history_path, 'r') as f:
                player_history = json.load(f)
                print(f"Loaded {len(player_history)} player records")
                
            # Build full name for comparison
            full_name = f"{user['first_name']} {user['last_name']}"
            print(f"Looking for player with name: {full_name}")
            
            # Find the player's record by matching first and last name
            player_record = next((p for p in player_history if p.get('name', '').lower() == full_name.lower()), None)
            print(f"Found player record: {player_record is not None}")
            
            if player_record and player_record.get('matches'):
                print(f"Found {len(player_record['matches'])} matches for player")
                # Sort matches by date to find most recent
                matches = sorted(player_record['matches'], key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y'), reverse=True)
                if matches:
                    print(f"Most recent match date: {matches[0]['date']}")
                    current_pti = matches[0].get('end_pti')
                    print(f"Current PTI from most recent match: {current_pti}")
                    
                    # Calculate weekly PTI change
                    weekly_pti_change = None
                    if len(matches) > 1:
                        current_date = datetime.strptime(matches[0]['date'], '%m/%d/%Y')
                        # Find the match closest to one week ago
                        prev_match = None
                        for match in matches[1:]:  # Skip the first match (current)
                            match_date = datetime.strptime(match['date'], '%m/%d/%Y')
                            if (current_date - match_date).days >= 5:  # Allow some flexibility in what constitutes a "week"
                                prev_match = match
                                break
                        
                        if prev_match and 'end_pti' in prev_match:
                            prev_pti = prev_match['end_pti']
                            weekly_pti_change = current_pti - prev_pti  # Change calculation to current - previous
                            print(f"Weekly PTI change: {weekly_pti_change} (Previous: {prev_pti}, Current: {current_pti})")
                    
                    if current_pti is not None:
                        analyze_data['current_pti'] = float(current_pti)
                        analyze_data['weekly_pti_change'] = float(weekly_pti_change) if weekly_pti_change is not None else None
                    else:
                        print("No end_pti found in most recent match")
                        analyze_data['current_pti'] = None
                        analyze_data['weekly_pti_change'] = None
                else:
                    print("No matches found after sorting")
                    analyze_data['current_pti'] = None
                    analyze_data['weekly_pti_change'] = None
            else:
                if not player_record:
                    print("No player record found")
                elif not player_record.get('matches'):
                    print("Player record found but no matches")
                analyze_data['current_pti'] = None
                analyze_data['weekly_pti_change'] = None
                
        except Exception as e:
            print(f"Error getting current PTI: {str(e)}")
            analyze_data['current_pti'] = None
            analyze_data['weekly_pti_change'] = None
        
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
        # Get the scores
        scores = match.get('Scores', '').split(', ')
        if len(scores) == 2 and team_won:
            straight_set_wins += 1
        if len(scores) == 3:
            if team_won:
                three_set_wins += 1
                # Check for comeback win - lost first set but won the match
                first_set = scores[0].split('-')
                home_score, away_score = map(int, first_set)
                if is_home and home_score < away_score:
                    comeback_wins += 1
                elif not is_home and away_score < home_score:
                    comeback_wins += 1
            else:
                three_set_losses += 1
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
                    
        # Sort standings by place (ascending)
        tennaqua_standings.sort(key=lambda x: x['place'])
        
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
        List of match dictionaries from schedules.json filtered for the user's club and series
    """
    try:
        schedule_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'schedules.json')
        print(f"\n=== Getting matches for user club ===")
        print(f"Looking for schedule file at: {schedule_path}")
        
        with open(schedule_path, 'r') as f:
            all_matches = json.load(f)
            
        if not user or not user.get('club') or not user.get('series'):
            print("❌ Missing user data:", user)
            return []
            
        user_club = user['club']
        # Handle different series formats (e.g. "Chicago 22" or just "22")
        user_series = user['series'].split()[-1]  # Get the last part which should be the number
        print(f"Looking for matches for club: {user_club}, series: {user_series}")
        
        # The team name in schedules.json could be in multiple formats:
        # 1. "Club - Series - Series" (e.g. "Tennaqua - 22 - 22")
        # 2. "Club - Chicago - Series - Series" (e.g. "Midtown - Chicago - 6 - 6")
        possible_team_formats = [
            f"{user_club} - {user_series} - {user_series}",  # Format 1
            f"{user_club} - Chicago - {user_series} - {user_series}",  # Format 2
            f"{user_club} - {user_series}"  # Legacy format
        ]
        
        # Filter matches where user's team is either home or away team
        club_matches = []
        for match in all_matches:
            try:
                # Check if it's a practice record
                if 'Practice' in match:
                    # For practices, add them all since they're at the user's club
                    normalized_match = {
                        'id': f"practice-{match.get('date', '')}-{user_club}",  # Add unique ID
                        'date': match.get('date', ''),
                        'time': match.get('time', ''),
                        'location': match.get('location', user_club),
                        'Practice': True,
                        'type': 'Practice'
                    }
                    club_matches.append(normalized_match)
                    continue
                
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                
                # Check if either home or away team matches any of our possible formats
                is_user_team = any(fmt in (home_team, away_team) for fmt in possible_team_formats)
                
                if is_user_team:
                    print(f"Found match: {home_team} vs {away_team}")
                    # Create a unique ID for the match
                    match_id = f"{match.get('date', '')}-{home_team}-{away_team}"
                    # Normalize keys to snake_case and ensure all required fields exist
                    normalized_match = {
                        'id': match_id,  # Add unique ID
                        'date': match.get('date', ''),
                        'time': match.get('time', ''),
                        'location': match.get('location', ''),
                        'home_team': home_team,
                        'away_team': away_team,
                        'winner': match.get('winner', ''),
                        'scores': match.get('scores', ''),
                        'home_player_1': match.get('home_player_1', ''),
                        'home_player_2': match.get('home_player_2', ''),
                        'away_player_1': match.get('away_player_1', ''),
                        'away_player_2': match.get('away_player_2', ''),
                        'type': 'match'
                    }
                    club_matches.append(normalized_match)
            except KeyError as e:
                print(f"Warning: Skipping invalid match record: {e}")
                continue
        
        print(f"Found {len(club_matches)} matches for club")
        print("=== End getting matches for user club ===\n")
        return club_matches
    except Exception as e:
        print(f"Error getting matches for user club: {e}")
        print(traceback.format_exc())  # Print full traceback for debugging
        return []

@app.route('/mobile/improve')
@login_required
def serve_mobile_improve():
    """Serve the mobile improve page with paddle tips"""
    try:
        user = session.get('user')
        if not user:
            return redirect(url_for('login'))
            
        session_data = {
            'user': user,
            'authenticated': True
        }
        
        # Load paddle tips from JSON file
        paddle_tips = []
        try:
            tips_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'paddle_tips.json')
            with open(tips_path, 'r', encoding='utf-8') as f:
                tips_data = json.load(f)
                paddle_tips = tips_data.get('paddle_tips', [])
        except Exception as tips_error:
            print(f"Error loading paddle tips: {str(tips_error)}")
            # Continue without tips if file can't be loaded
        
        # Load training guide data for video references
        training_guide = {}
        try:
            guide_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'complete_platform_tennis_training_guide.json')
            with open(guide_path, 'r', encoding='utf-8') as f:
                training_guide = json.load(f)
        except Exception as guide_error:
            print(f"Error loading training guide: {str(guide_error)}")
            # Continue without training guide if file can't be loaded
        
        log_user_activity(
            user['email'], 
            'page_visit', 
            page='mobile_improve',
            details='Accessed improve page'
        )
        
        return render_template('mobile/improve.html', 
                              session_data=session_data, 
                              paddle_tips=paddle_tips,
                              training_guide=training_guide)
        
    except Exception as e:
        print(f"Error serving improve page: {str(e)}")
        return redirect(url_for('login'))

def find_training_video_direct(user_prompt):
    """Find relevant training videos based on user prompt - direct function call version"""
    try:
        if not user_prompt:
            return {'videos': [], 'video': None}
        
        user_prompt = user_prompt.lower().strip()
        
        # Load training guide data
        try:
            guide_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'complete_platform_tennis_training_guide.json')
            with open(guide_path, 'r', encoding='utf-8') as f:
                training_guide = json.load(f)
        except Exception as e:
            print(f"Error loading training guide: {str(e)}")
            return {'videos': [], 'video': None, 'error': 'Could not load training guide'}
        
        # Search through training guide sections
        matching_sections = []
        
        def search_sections(data):
            """Search through the training guide sections"""
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and 'Reference Videos' in value:
                        # Calculate relevance based on section title
                        relevance_score = calculate_video_relevance(user_prompt, key.lower())
                        
                        if relevance_score > 0:
                            # Get all videos from Reference Videos
                            videos = value.get('Reference Videos', [])
                            if videos and len(videos) > 0:
                                # Add each video with the section info
                                for video in videos:
                                    matching_sections.append({
                                        'title': key.replace('_', ' ').title(),
                                        'video': video,
                                        'relevance_score': relevance_score
                                    })
        
        def calculate_video_relevance(query, section_title):
            """Calculate relevance score for video matching"""
            score = 0
            query_words = query.split()
            
            # Exact match in section title gets highest score
            if query == section_title:
                score += 200
            
            # Query appears as a word in the section title
            if query in section_title.split():
                score += 150
            
            # Query appears anywhere in section title
            if query in section_title:
                score += 100
            
            # Partial word matches in section title
            for word in query_words:
                if word in section_title:
                    score += 50
            
            return score
        
        # Perform the search
        search_sections(training_guide)
        
        # Sort by relevance score and return all relevant matches
        if matching_sections:
            matching_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Filter to only include videos with sufficient relevance
            relevant_videos = []
            for match in matching_sections:
                if match['relevance_score'] >= 50:  # Minimum threshold for relevance
                    relevant_videos.append({
                        'title': match['video']['title'],
                        'url': match['video']['url'],
                        'topic': match['title'],
                        'relevance_score': match['relevance_score']
                    })
            
            # Return both formats for backward compatibility
            response = {'videos': relevant_videos}
            
            # Include the best video as 'video' for backward compatibility
            if relevant_videos:
                response['video'] = relevant_videos[0]  # Best match (highest relevance)
            
            return response
        
        return {'videos': [], 'video': None}
        
    except Exception as e:
        print(f"Error finding training video: {str(e)}")
        return {'videos': [], 'video': None, 'error': str(e)}

@app.route('/api/find-training-video', methods=['POST'])
def find_training_video():
    """Find relevant training videos based on user prompt"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'videos': [], 'error': 'No data provided'})
            
        user_prompt = data.get('content', '').lower().strip()
        
        # Use the direct function
        result = find_training_video_direct(user_prompt)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error finding training video: {str(e)}")
        return jsonify({'videos': [], 'video': None, 'error': str(e)})

@app.route('/mobile/email-team')
@login_required
def serve_mobile_email_team():
    """Serve the email team page"""
    return render_template('mobile/email_team.html', show_back_arrow=True)

def get_user_by_id(user_id):
    """Get user by ID from database"""
    user = execute_query_one(
        "SELECT * FROM users WHERE id = %(user_id)s",
        {'user_id': user_id}
    )
    return user if user else None

def get_user_by_email(email):
    """Get user by email from database"""
    user = execute_query_one(
        "SELECT * FROM users WHERE email = %(email)s",
        {'email': email}
    )
    return user if user else None

def get_club_by_id(club_id):
    """Get club by ID from database"""
    club = execute_query_one(
        "SELECT * FROM clubs WHERE id = %(club_id)s",
        {'club_id': club_id}
    )
    return club if club else None

def get_series_by_id(series_id):
    """Get series by ID from database"""
    series = execute_query_one(
        "SELECT * FROM series WHERE id = %(series_id)s",
        {'series_id': series_id}
    )
    return series if series else None

# Serve logout.js without requiring login
@app.route('/static/js/logout.js')
def serve_logout_js():
    """Serve the logout.js file with proper headers"""
    try:
        response = send_from_directory('static/js', 'logout.js')
        
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        # Add cache control headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print("Successfully served logout.js")
        return response
    except Exception as e:
        print(f"Error serving logout.js: {str(e)}")
        return str(e), 500

@app.route('/mobile/team-schedule')
@login_required
def serve_mobile_team_schedule():
    """Serve the team schedule page showing all players and their schedules"""
    try:
        print("\n=== TEAM SCHEDULE PAGE REQUEST ===")
        # Get the team from user's session data
        user = session.get('user')
        if not user:
            print("❌ No user in session")
            flash('Please log in first', 'error')
            return redirect(url_for('login'))
            
        club_name = user.get('club')
        series = user.get('series')
        print(f"User: {user.get('email')}")
        print(f"Club: {club_name}")
        print(f"Series: {series}")
        
        if not club_name or not series:
            print("❌ Missing club or series")
            flash('Please set your club and series in your profile settings', 'error')
            return redirect(url_for('serve_mobile_view_schedule'))

        # Get series ID first since we want all players in the series
        series_query = "SELECT id, name FROM series WHERE name = %(name)s"
        print(f"Executing series query: {series_query}")
        print(f"Query params: {{'name': {series}}}")
        
        series_record = execute_query(series_query, {'name': series})
        print(f"Series query result: {series_record}")
        
        if not series_record:
            print(f"❌ Series not found: {series}")
            flash(f'Series "{series}" not found in database', 'error')
            return redirect(url_for('serve_mobile_view_schedule'))
            
        series_record = series_record[0]
        print(f"✓ Found series: {series_record}")

        # Load all players from players.json
        try:
            with open('data/players.json', 'r') as f:
                all_players = json.load(f)
            
            # Filter players for this series and club
            team_players = []
            for player in all_players:
                if (player.get('Series') == series and 
                    player.get('Club') == club_name):
                    full_name = f"{player['First Name']} {player['Last Name']}"
                    team_players.append({
                        'player_name': full_name,
                        'club_name': club_name
                    })
            
            print(f"✓ Found {len(team_players)} players in players.json for {club_name} - {series}")
            
            if not team_players:
                print("❌ No players found in players.json")
                flash('No players found for your team', 'warning')
                return redirect(url_for('serve_mobile_view_schedule'))
                
        except Exception as e:
            print(f"❌ Error reading players.json: {e}")
            print(traceback.format_exc())
            flash('Error loading player data', 'error')
            return redirect(url_for('serve_mobile_view_schedule'))

        # Get match dates from schedules.json
        try:
            matches_path = os.path.join('data', 'schedules.json')
            print(f"\nReading matches from: {matches_path}")
            
            if not os.path.exists(matches_path):
                print(f"❌ Schedules file not found: {matches_path}")
                flash('Match schedule file not found', 'error')
                return redirect(url_for('serve_mobile_view_schedule'))
                
            with open(matches_path, 'r') as f:
                all_matches = json.load(f)
                
            # Filter matches for this series
            series_number = series.split()[-1]  # Get the number part (e.g. "22" from "Chicago 22")
            match_dates = []
            
            print(f"Looking for matches with series number: {series_number}")
            for match in all_matches:
                # Check if either team is in this series
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                match_date = match.get('date')
                
                if (f" - {series_number} - " in home_team or 
                    f" - {series_number} - " in away_team):
                    if match_date:
                        try:
                            # Convert from MM/DD/YYYY to YYYY-MM-DD
                            date_obj = datetime.strptime(match_date, '%m/%d/%Y')
                            match_dates.append(date_obj.strftime('%Y-%m-%d'))
                        except ValueError as e:
                            print(f"Invalid date format: {match_date}, error: {e}")
                            continue
            
            match_dates = sorted(list(set(match_dates)))  # Remove duplicates and sort
            print(f"✓ Found {len(match_dates)} match dates")
            
            if not match_dates:
                print("❌ No match dates found for series")
                flash('No matches found for your series', 'warning')
                return redirect(url_for('serve_mobile_view_schedule'))
            
        except Exception as e:
            print(f"❌ Error reading schedules.json: {e}")
            print(traceback.format_exc())
            flash('Error loading match schedule', 'error')
            return redirect(url_for('serve_mobile_view_schedule'))

        players_schedule = {}
        print("\nProcessing player availability:")
        for player in team_players:
            availability = []
            player_name = player['player_name']
            print(f"\nChecking availability for {player_name}")
            
            for match_date in match_dates:
                try:
                    # Convert match_date string to datetime.date object
                    match_date_obj = datetime.strptime(match_date, '%Y-%m-%d').date()
                    
                    # Get availability status for this player and date
                    avail_query = """
                        SELECT availability_status
                        FROM player_availability 
                        WHERE player_name = %(player)s 
                        AND series_id = %(series_id)s 
                        AND match_date = %(date)s::date
                    """
                    avail_params = {
                        'player': player_name,
                        'series_id': series_record['id'],
                        'date': match_date_obj
                    }
                    
                    avail_record = execute_query(avail_query, avail_params)
                    status = avail_record[0]['availability_status'] if avail_record and avail_record[0]['availability_status'] is not None else 0
                    
                    availability.append({
                        'date': match_date,
                        'availability_status': status
                    })
                except Exception as e:
                    print(f"Error processing availability for {player_name} on {match_date}: {e}")
                    # Skip this date if there's an error
                    continue
            
            # Store both player name and club name in the schedule
            display_name = player_name
            players_schedule[display_name] = availability
            print(f"✓ Added {display_name} with {len(availability)} dates")

        if not players_schedule:
            print("❌ No player schedules created")
            flash('No player schedules found for your series', 'warning')
            return redirect(url_for('serve_mobile_view_schedule'))
            
        print(f"\n✓ Final players_schedule has {len(players_schedule)} players")
            
        # Create a clean team name string for the title
        team_name = f"{club_name} - {series}"
        print(f"\nRendering template with team: {team_name}")
        
        return render_template(
            'mobile/team_schedule.html',
            team=team_name,
            players_schedule=players_schedule,
            session_data={'user': user},
            match_dates=match_dates  # Add match_dates to the template context
        )
        
    except Exception as e:
        print(f"❌ Error in serve_mobile_team_schedule: {str(e)}")
        print(traceback.format_exc())
        flash('An error occurred while loading the team schedule', 'error')
        return redirect(url_for('serve_mobile_view_schedule'))

@app.route('/mobile/reserve-court')
@login_required
def serve_mobile_reserve_court():
    return render_template('mobile/reserve-court.html')

@app.route('/submit_availability', methods=['POST'])
@login_required
def submit_availability():
    """Handle availability submission from HTMX"""
    try:
        # Get data from form
        player_name = request.form.get('player_name')
        match_date = request.form.get('match_date')
        status = request.form.get('status')
        series = request.form.get('series')
        match_id = request.form.get('match_id')  # This is now a safe ID
        user = session['user']

        print(f"\n=== SUBMIT AVAILABILITY ===")
        print(f"Player: {player_name}")
        print(f"Date: {match_date}")
        print(f"Status: {status}")
        print(f"Series: {series}")
        print(f"Match ID: {match_id}")

        # Validate required fields
        if not all([player_name, match_date, status, series]):
            print("Missing required fields")
            return 'Missing required fields', 400

        # Map status strings to numeric values
        status_map = {
            'available': 1,
            'unavailable': 2,
            'not_sure': 3
        }
        numeric_status = status_map.get(status)
        if numeric_status is None:
            print(f"Invalid status: {status}")
            return 'Invalid status', 400

        # Get series ID from the database
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s",
            {'series': series}
        )
        
        if not series_record:
            # Try with "Chicago " prefix if not found
            series_with_prefix = f"Chicago {series.split()[-1]}"
            series_record = execute_query_one(
                "SELECT id FROM series WHERE name = %(series)s",
                {'series': series_with_prefix}
            )
            if not series_record:
                print(f"Series not found: {series}")
                return 'Series not found', 404

        # Update availability using the existing function
        success = update_player_availability(
            series_record['id'],  # Pass series ID instead of name
            match_date.strip(),
            player_name.strip(),
            numeric_status,
            series  # Keep series name for logging
        )

        if not success:
            print("Failed to update availability")
            return 'Failed to update availability', 500

        # For HTMX response, render the button group with updated status
        match = {
            'date': match_date,
            'home_team': match_id.split('-')[1] if len(match_id.split('-')) > 1 else '',
            'away_team': match_id.split('-')[2] if len(match_id.split('-')) > 2 else ''
        }
        avail = {'status': status}  # Use string status for template
        players = [{'name': player_name}]
        session_data = {'user': user}

        return render_template(
            'partials/button_group.html',
            match=match,
            avail=avail,
            players=players,
            session_data=session_data
        )

    except Exception as e:
        print(f"Error in submit_availability: {str(e)}")
        print(traceback.format_exc())  # Add full traceback for debugging
        return str(e), 500

@app.route('/mobile/all-team-availability')
@login_required
def serve_all_team_availability():
    """Serve the all team availability page showing all players' availability for a specific date"""
    try:
        print("\n=== ALL TEAM AVAILABILITY PAGE REQUEST ===")
        # Get the selected date from query parameter
        selected_date = request.args.get('date')
        if not selected_date:
            flash('No date selected', 'error')
            return redirect(url_for('mobile_availability'))

        # Get the team from user's session data
        user = session.get('user')
        if not user:
            print("❌ No user in session")
            flash('Please log in first', 'error')
            return redirect(url_for('login'))
            
        club_name = user.get('club')
        series = user.get('series')
        print(f"User: {user.get('email')}")
        print(f"Club: {club_name}")
        print(f"Series: {series}")
        print(f"Selected Date: {selected_date}")
        
        if not club_name or not series:
            print("❌ Missing club or series")
            flash('Please set your club and series in your profile settings', 'error')
            return redirect(url_for('mobile_availability'))

        # Get series ID
        series_record = execute_query("SELECT id, name FROM series WHERE name = %(name)s", {'name': series})
        if not series_record:
            print(f"❌ Series not found: {series}")
            flash(f'Series "{series}" not found in database', 'error')
            return redirect(url_for('mobile_availability'))
            
        series_record = series_record[0]

        # Load all players from players.json
        try:
            with open('data/players.json', 'r') as f:
                all_players = json.load(f)
            
            # Filter players for this series and club
            team_players = []
            for player in all_players:
                if (player.get('Series') == series and 
                    player.get('Club') == club_name):
                    full_name = f"{player['First Name']} {player['Last Name']}"
                    team_players.append({
                        'player_name': full_name,
                        'club_name': club_name
                    })
            
            if not team_players:
                print("❌ No players found in players.json")
                flash('No players found for your team', 'warning')
                return redirect(url_for('mobile_availability'))
                
        except Exception as e:
            print(f"❌ Error reading players.json: {e}")
            print(traceback.format_exc())
            flash('Error loading player data', 'error')
            return redirect(url_for('mobile_availability'))

        players_schedule = {}
        for player in team_players:
            availability = []
            player_name = player['player_name']
            
            try:
                # Convert selected_date string to datetime.date object if needed
                if '/' in selected_date:
                    selected_date_obj = datetime.strptime(selected_date, '%m/%d/%Y').date()
                else:
                    selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                
                # Get availability status for this player and date
                avail_query = """
                    SELECT availability_status
                    FROM player_availability 
                    WHERE player_name = %(player)s 
                    AND series_id = %(series_id)s 
                    AND match_date = %(date)s::date
                """
                avail_params = {
                    'player': player_name,
                    'series_id': series_record['id'],
                    'date': selected_date_obj
                }
                
                avail_record = execute_query(avail_query, avail_params)
                status = avail_record[0]['availability_status'] if avail_record and avail_record[0]['availability_status'] is not None else 0
                
                availability.append({
                    'date': selected_date,
                    'availability_status': status
                })
            except Exception as e:
                print(f"Error processing availability for {player_name} on {selected_date}: {e}")
                continue
            
            # Store both player name and club name in the schedule
            display_name = f"{player_name} ({player['club_name']})"
            players_schedule[display_name] = availability

        if not players_schedule:
            print("❌ No player schedules created")
            flash('No player schedules found for your series', 'warning')
            return redirect(url_for('mobile_availability'))
            
        # Create a clean team name string for the title
        team_name = f"{club_name} - {series}"
        
        return render_template(
            'mobile/all_team_availability.html',
            team=team_name,
            players_schedule=players_schedule,
            session_data={'user': user},
            selected_date=selected_date
        )
        
    except Exception as e:
        print(f"❌ Error in serve_all_team_availability: {str(e)}")
        print(traceback.format_exc())
        flash('An error occurred while loading the team availability', 'error')
        return redirect(url_for('mobile_availability'))

@app.route('/api/check-auth')
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
        print(f"Error checking authentication: {str(e)}")
        return jsonify({
            'error': str(e),
            'authenticated': False
        }), 500

def get_player_availability(player_name, match_date, series):
    """Get a player's availability status for a specific match date and series"""
    try:
        print(f"\n=== Getting availability for {player_name} on {match_date} ===")
        
        # Get series ID
        series_record = execute_query(
            "SELECT id FROM series WHERE name = %(name)s",
            {'name': series}
        )
        
        if not series_record:
            print(f"❌ Series not found: {series}")
            return {'availability_status': 0}  # Default to not set
            
        series_id = series_record[0]['id']
        
        # Convert match_date to datetime if it's a string
        if isinstance(match_date, str):
            if '/' in match_date:  # Handle MM/DD/YYYY format
                match_date = datetime.strptime(match_date, '%m/%d/%Y').date()
            else:  # Handle YYYY-MM-DD format
                match_date = datetime.strptime(match_date, '%Y-%m-%d').date()
        elif isinstance(match_date, dict) and 'date' in match_date:
            # Handle case where match_date is a dictionary containing date
            date_str = match_date['date']
            if '/' in date_str:
                match_date = datetime.strptime(date_str, '%m/%d/%Y').date()
            else:
                match_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Query the database for availability
        query = """
            SELECT availability_status
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s 
            AND match_date = %(date)s::date
        """
        params = {
            'player': player_name,
            'series_id': series_id,
            'date': match_date
        }
        
        result = execute_query(query, params)
        
        if result and result[0]['availability_status'] is not None:
            status = result[0]['availability_status']
            print(f"✓ Found availability status: {status}")
            return {'availability_status': status}
        
        print("✓ No availability set, returning default status")
        return {'availability_status': 0}  # Default to not set
        
    except Exception as e:
        print(f"❌ Error getting player availability: {str(e)}")
        print(traceback.format_exc())
        return {'availability_status': 0}  # Default to not set on error

def get_user_availability(player_name, matches, series):
    """Get a user's availability for multiple matches"""
    try:
        print(f"\n=== Getting availability for {player_name} ===")
        availability = []
        
        for match in matches:
            match_date = match.get('date')
            if not match_date:
                print(f"❌ No date in match: {match}")
                continue
                
            avail_status = get_player_availability(player_name, match_date, series)
            availability.append(avail_status)
            
        print(f"✓ Retrieved {len(availability)} availability records")
        return availability
        
    except Exception as e:
        print(f"❌ Error getting user availability: {str(e)}")
        print(traceback.format_exc())
        return []

# API availability route moved to routes/act/availability.py

# Get user settings route moved to routes/act/settings.py

@app.route('/api/get-clubs')
def get_clubs():
    """Get list of all clubs - public endpoint for registration"""
    try:
        clubs_data = execute_query("SELECT name FROM clubs ORDER BY name")
        clubs_list = [club['name'] for club in clubs_data]
        return jsonify({
            'clubs': clubs_list  # For login page compatibility
        })
    except Exception as e:
        print(f"Error getting clubs: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Get series route moved to routes/act/settings.py

@app.route('/api/player-history')
@login_required
def get_player_history():
    """Return the player history data for PTI history chart"""
    try:
        # Get user info from session
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Build player name
        player_name = f"{user['first_name']} {user['last_name']}"
        
        # Load player history data
        player_history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'player_history.json')
        
        with open(player_history_path, 'r') as f:
            all_players = json.load(f)
            
        # Find the player's record
        def normalize(name):
            return name.replace(',', '').replace('  ', ' ').strip().lower()
            
        player_name_normal = normalize(player_name)
        player_last_first = normalize(f"{user['last_name']}, {user['first_name']}")
        
        player = None
        for p in all_players:
            n = normalize(p.get('name', ''))
            if n == player_name_normal or n == player_last_first:
                player = p
                break
                
        if not player or not player.get('matches'):
            return jsonify({'error': 'No match history found', 'data': []}), 404
            
        # Extract matches with PTI data
        matches_with_pti = [
            {
                'date': m['date'],
                'end_pti': m['end_pti']
            }
            for m in player['matches'] 
            if 'end_pti' in m and 'date' in m
        ]
        
        # Sort matches by date
        matches_with_pti.sort(key=lambda m: datetime.strptime(m['date'], '%m/%d/%Y'))
        
        return jsonify({
            'data': matches_with_pti
        })
        
    except Exception as e:
        print(f"Error getting player history: {str(e)}")
        return jsonify({'error': str(e), 'data': []}), 500

@app.route('/api/paddle-insights', methods=['POST'])
@login_required
def get_paddle_insights():
    """Search paddle insights based on user query"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
            
        data = request.get_json()
        query = data.get('query', '').lower().strip()
        
        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400
            
        # Load paddle insights from JSON file
        insights_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'complete_platform_tennis_training_guide.json')
        with open(insights_path, 'r', encoding='utf-8') as f:
            insights_data = json.load(f)
        
        # Search through insights
        matching_insights = []
        
        def search_insights(data, path=""):
            """Recursively search through the insights data structure"""
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}/{key}" if path else key
                    
                    if isinstance(value, dict):
                        # Check if this is a training section with Reference Videos
                        if 'Reference Videos' in value:
                            # Calculate relevance based on section title
                            relevance_score = calculate_relevance(query, key.lower(), [])
                            
                            if relevance_score > 0:
                                # Extract rich content from the training guide
                                formatted_text = format_training_content(key, value)
                                
                                # Get the first video from Reference Videos
                                videos = value.get('Reference Videos', [])
                                first_video = videos[0] if videos and len(videos) > 0 else None
                                
                                matching_insights.append({
                                    'title': key.replace('_', ' ').title(),
                                    'category': 'Training Guide',
                                    'text': formatted_text,
                                    'tags': [key.lower()],
                                    'linked_videos': [first_video] if first_video else [],
                                    'relevance_score': relevance_score
                                })
                        else:
                            # Continue searching deeper
                            search_insights(value, current_path)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                search_insights(item, current_path)
        
        def format_training_content(technique_name, content):
            """Format the training content into a nicely structured HTML text"""
            formatted_parts = []
            
            # Add technique title
            title = technique_name.replace('_', ' ').title()
            formatted_parts.append(f"<div class='technique-title'><strong>{title} – Step-by-Step Technique</strong></div>")
            
            # Add recommendations
            recommendations = content.get('Recommendation', [])
            if recommendations:
                formatted_parts.append("<div class='section-header'><strong>Recommendation:</strong></div>")
                formatted_parts.append("<div class='section-content'>")
                for rec in recommendations:
                    rec_title = rec.get('title', '')
                    details = rec.get('details', [])
                    if rec_title:
                        formatted_parts.append(f"<div class='bullet-item'>• <strong>{rec_title}</strong></div>")
                        for detail in details:
                            formatted_parts.append(f"<div class='sub-item'>- {detail}</div>")
                    else:
                        # Handle simple string recommendations
                        if isinstance(rec, str):
                            formatted_parts.append(f"<div class='bullet-item'>• {rec}</div>")
                formatted_parts.append("</div>")
            
            # Add drills
            drills = content.get('Drills to Improve', [])
            if drills:
                formatted_parts.append("<div class='section-header'><strong>Drills to Improve:</strong></div>")
                formatted_parts.append("<div class='section-content'>")
                for drill in drills:
                    drill_title = drill.get('title', '')
                    steps = drill.get('steps', [])
                    if drill_title:
                        formatted_parts.append(f"<div class='bullet-item'>• <strong>{drill_title}</strong></div>")
                        for step in steps:
                            formatted_parts.append(f"<div class='sub-item'>- {step}</div>")
                    else:
                        # Handle simple string drills
                        if isinstance(drill, str):
                            formatted_parts.append(f"<div class='bullet-item'>• {drill}</div>")
                formatted_parts.append("</div>")
            
            # Add common mistakes
            mistakes = content.get('Common Mistakes & Fixes', [])
            if mistakes:
                formatted_parts.append("<div class='section-header'><strong>Common Mistakes & Fixes:</strong></div>")
                formatted_parts.append("<div class='section-content'>")
                for mistake in mistakes:
                    mistake_text = mistake.get('Mistake', '')
                    why = mistake.get('Why it happens', '')
                    fix = mistake.get('Fix', '')
                    if mistake_text:
                        formatted_parts.append(f"<div class='mistake-item'><strong>Mistake:</strong> {mistake_text}</div>")
                        if why:
                            formatted_parts.append(f"<div class='why-item'><strong>Why it happens:</strong> {why}</div>")
                        if fix:
                            formatted_parts.append(f"<div class='fix-item'><strong>Fix:</strong> {fix}</div>")
                formatted_parts.append("</div>")
            
            # Add coach's cues
            cues = content.get("Coach's Cues", [])
            if cues:
                formatted_parts.append("<div class='section-header'><strong>Coach's Cues:</strong></div>")
                formatted_parts.append("<div class='section-content'>")
                for cue in cues:
                    formatted_parts.append(f"<div class='cue-item'>• {cue}</div>")
                formatted_parts.append("</div>")
            
            return "".join(formatted_parts).strip()
        
        def calculate_relevance(query, text, tags):
            """Calculate relevance score based on how well the query matches"""
            score = 0
            query_words = query.split()
            
            # Exact match in section title gets highest score
            if query == text:
                score += 200
            
            # Query appears as a word in the section title
            if query in text.split():
                score += 150
            
            # Query appears anywhere in section title
            if query in text:
                score += 100
            
            # Partial word matches in section title
            for word in query_words:
                if word in text:
                    score += 50
            
            # Exact tag match gets high score
            if query in [tag.lower() for tag in tags]:
                score += 100
            
            # Partial tag matches
            for tag in tags:
                if query in tag.lower():
                    score += 50
                for word in query_words:
                    if word in tag.lower():
                        score += 25
            
            return score
        
        # Perform the search
        search_insights(insights_data)
        
        # If no results found, return appropriate message
        if not matching_insights:
            return jsonify({
                'query': query,
                'result': None,
                'message': f'No specific insights found for "{query}". Try searching for terms like "serve", "volley", "overhead", "backhand", or "beginner tips".'
            })
        
        # Sort by relevance score and get the BEST match
        matching_insights.sort(key=lambda x: x['relevance_score'], reverse=True)
        best_match = matching_insights[0]  # Take only the top result
        
        log_user_activity(
            user['email'], 
            'paddle_insight_search', 
            details=f'Searched for: {query}, found best match: {best_match["title"]}'
        )
        
        return jsonify({
            'query': query,
            'result': best_match,
            'message': f'Here\'s the most relevant advice for improving your {query}:'
        })
        
    except FileNotFoundError:
        return jsonify({'error': 'Paddle insights data not found'}), 404
    except Exception as e:
        print(f"Error searching paddle insights: {str(e)}")
        return jsonify({'error': 'An error occurred while searching insights'}), 500

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