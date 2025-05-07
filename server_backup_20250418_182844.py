from flask import Flask, jsonify, request, send_from_directory, render_template, session, redirect, url_for
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

# Load environment variables
load_dotenv()

app = Flask(__name__, static_url_path='', static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')  # Change this in production
CORS(app, resources={
    r"/*": {  # Allow all routes
        "origins": [
            "http://localhost:5002",
            "http://127.0.0.1:5002"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
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
    """Get the existing assistant"""
    assistant_id = "asst_Q6GQOccbb0ymf9IpLMG1lFHe"
    
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        print("Using assistant:", assistant.name)
        return assistant
    except Exception as e:
        print(f"Error retrieving assistant: {e}")
        raise Exception("Failed to retrieve assistant. Please check the assistant ID and API configuration.")

# Get or create the assistant
assistant = get_or_create_assistant()

# Add this near the top with other global variables
selected_series = "Chicago 22"

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

@app.route('/')
@login_required
def serve_index():
    # Print current directory and list files to debug
    current_dir = os.getcwd()
    static_dir = os.path.join(current_dir, 'static')
    files = os.listdir(static_dir)
    print(f"\nCurrent directory: {current_dir}")
    print(f"Static directory: {static_dir}")
    print(f"Files in static directory: {files}")
    
    if os.path.exists(os.path.join(static_dir, 'index.html')):
        print("✅ Found index.html in static folder")
        return app.send_static_file('index.html')
    else:
        print("❌ index.html not found in static folder!")
        return "Error: index.html not found", 404

@app.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('serve_index'))
    return app.send_static_file('login.html')

@app.route('/api/login', methods=['POST'])
def handle_login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        # For now, we'll use a simple authentication
        # TODO: Implement proper authentication with a user database
        if email and password:  # Just check if both fields are provided
            # Create a simple user session
            session['user'] = {
                'email': email,
                'name': email.split('@')[0],  # Use email username as name
                'series': 'Chicago 22'  # Default series
            }
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Please provide both email and password'}), 401
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': 'An error occurred during login'}), 500

@app.route('/api/logout', methods=['POST'])
def handle_logout():
    session.pop('user', None)
    return jsonify({'status': 'success'})

# Protect all other routes
@app.route('/<path:path>')
@login_required
def serve_static(path):
    return send_from_directory('static', path)

# Protect all API routes
@app.route('/api/<path:path>', methods=['GET', 'POST'])
@login_required
def api_route(path):
    # This will be handled by the specific route handlers
    pass

@app.route('/api/set-series', methods=['POST'])
def set_series():
    global selected_series
    data = request.get_json()
    selected_series = data.get('series', "Chicago 22")
    return jsonify({'status': 'success', 'series': selected_series})

@app.route('/api/get-series')
@app.route('/get-series')
def get_series():
    try:
        # Read from all_tennaqua_players.csv in the Data directory
        file_path = os.path.join('Data', 'all_tennaqua_players.csv')
        df = pd.read_csv(file_path)
        
        # Get unique series
        series_list = df['Series'].unique().tolist()
        
        # Extract numbers from series names and create tuples for sorting
        series_with_numbers = []
        for series in series_list:
            # Extract number from series name (e.g., "Chicago 22" -> 22)
            number = int(''.join(filter(str.isdigit, series)))
            series_with_numbers.append((number, series))
        
        # Sort by the extracted number
        series_with_numbers.sort(key=lambda x: x[0])
        
        # Extract just the series names in sorted order
        sorted_series = [series for _, series in series_with_numbers]
        
        # If this is an API request, return the current selected series
        if request.path.startswith('/api/'):
            return jsonify({'series': selected_series})
        
        # Otherwise return all series for the settings page
        return jsonify({'series': sorted_series})
    except Exception as e:
        print(f"Error getting series: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-players-series-22')
def get_players_series_22():
    print("\n=== Getting Series 22 Players ===")
    try:
        print("Reading CSV file...")
        df = pd.read_csv('data/all_tennaqua_players.csv')
        print(f"CSV loaded, total rows: {len(df)}")
        
        # Print unique series to see what's actually in the data
        print("\nUnique series in CSV:")
        print(df['Series'].unique())
        
        print("\nFiltering for Series 22...")
        series_22_df = df[df['Series'] == 'Chicago 22']
        print(f"Found {len(series_22_df)} players in Series 22")
        
        # Print the actual Series 22 data
        print("\nSeries 22 data:")
        print(series_22_df)
        
        players = []
        for _, row in series_22_df.iterrows():
            player = {
                'firstName': row['First Name'],
                'lastName': row['Last Name'],
                'rating': row['PTI']
            }
            players.append(player)
            print(f"Added player: {player['firstName']} {player['lastName']}")
        
        print(f"\nReturning {len(players)} players")
        return jsonify({'players': players})
    except Exception as e:
        print(f"\nERROR getting Series 22 players: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-lineup', methods=['POST'])
@login_required
def generate_lineup():
    try:
        data = request.json
        selected_players = data.get('players', [])
        
        # Stricter prompt to enforce exact format
        prompt = f"""Create an optimal lineup for these players from {selected_series}: {', '.join([f"{p}" for p in selected_players])}

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
        
        assistant_message = messages.data[0].content[0].text.value
        
        logger.debug(f"\n=== RESPONSE ===\n{assistant_message}\n")
        
        return jsonify({
            'suggestion': assistant_message,
            'prompt': prompt
        })
        
    except Exception as e:
        logger.error(f"Error details: {str(e)}")  # Add error logging
        if 'rate_limit_exceeded' in str(e):
            return jsonify({'error': 'The AI service is currently experiencing high demand. Please try again in a few minutes.'}), 429
        elif 'authentication' in str(e).lower() or 'invalid api key' in str(e).lower():
            return jsonify({'error': 'There is an issue with the AI service configuration. Please contact the system administrator.'}), 500
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

@app.route('/update-availability')
def update_availability():
    return send_from_directory('static', 'update-availability.html')

@app.route('/api/update-availability', methods=['POST'])
def handle_availability_update():
    try:
        data = request.json
        print("\n=== AVAILABILITY UPDATE ===")
        print("Received data:", data)
        
        # TODO: Save the availability data to a database
        # For now, we'll just print it and return success
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating availability: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-settings', methods=['POST'])
def update_settings():
    try:
        data = request.json
        print("\n=== UPDATING USER SETTINGS ===")
        print("Received data:", data)
        
        # TODO: Save the settings to a database
        # For now, we'll just print it and return success
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/players')
def get_players():
    try:
        print("\n=== DEBUG START ===")
        
        # Read from all_tennaqua_players.csv in the Data directory
        file_path = os.path.join('Data', 'all_tennaqua_players.csv')
        df = pd.read_csv(file_path)
        
        # Get series parameter from request
        series = request.args.get('series')
        print(f"\nRequested series: {series}")
        
        if series:
            # Extract series number from the request
            requested_series_num = int(series.split()[-1])  # Get the number from "Chicago X"
            
            # Filter for players in the requested series
            df = df[df['Series'] == f"Chicago {requested_series_num}"]
            
            if len(df) == 0:
                print(f"❌ No players found in series {series}")
                print("=== DEBUG END ===")
                return jsonify([])
            
            # Convert Win % to float and sort
            df['Win_Rate_Float'] = df['Win %'].str.rstrip('%').astype(float)
            df = df.sort_values('Win_Rate_Float', ascending=False)
            
            print("\nSorted DataFrame:")
            print(df[['Last Name', 'First Name', 'Win %', 'Win_Rate_Float']].head(10))
            
            # Convert to list of dictionaries
            players = []
            for _, row in df.iterrows():
                win_rate = float(row['Win %'].rstrip('%'))
                player = {
                    'name': f"{row['Last Name']} {row['First Name']}",
                    'series': row['Series'],
                    'rating': str(row['PTI']),
                    'wins': str(row['Wins']),
                    'losses': str(row['Losses']),
                    'winRate': f"{win_rate:.1f}%"
                }
                players.append(player)
            
            print("\nFirst 3 players in response:")
            for i, p in enumerate(players[:3]):
                print(f"{i+1}. {p['name']}: {p['winRate']}")
            
            return jsonify(players)
            
        return jsonify([])
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("=== DEBUG END ===")
        return jsonify({'error': str(e)}), 500

@app.route('/api/lineup-instructions', methods=['GET'])
@login_required
def get_instructions():
    try:
        user_email = session['user']['email']
        instructions = get_user_instructions(user_email)
        return jsonify({'instructions': instructions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lineup-instructions', methods=['POST'])
@login_required
def add_instruction():
    try:
        data = request.json
        instruction = data.get('instruction')
        if not instruction:
            return jsonify({'error': 'Instruction is required'}), 400
            
        user_email = session['user']['email']
        add_user_instruction(user_email, instruction)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lineup-instructions/<int:instruction_id>', methods=['DELETE'])
@login_required
def delete_instruction(instruction_id):
    try:
        user_email = session['user']['email']
        instructions = get_user_instructions(user_email)
        
        # Check if the index is valid
        if instruction_id < 0 or instruction_id >= len(instructions):
            return jsonify({'error': 'Invalid instruction index'}), 400
            
        # Get the instruction text at the specified index
        instruction_text = instructions[instruction_id]
        
        # Deactivate the instruction by text and user email
        conn = sqlite3.connect('data/paddlepro.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_instructions 
            SET is_active = 0 
            WHERE instruction = ? AND user_email = ? AND is_active = 1
        ''', (instruction_text, user_email))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_user_instructions(user_email):
    """Get all active instructions for a user"""
    conn = sqlite3.connect('data/paddlepro.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT instruction 
        FROM user_instructions 
        WHERE user_email = ? AND is_active = 1
        ORDER BY created_at DESC
    ''', (user_email,))
    instructions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return instructions

def add_user_instruction(user_email, instruction):
    """Add a new instruction for a user"""
    conn = sqlite3.connect('data/paddlepro.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_instructions (user_email, instruction)
        VALUES (?, ?)
    ''', (user_email, instruction))
    conn.commit()
    conn.close()

def deactivate_instruction(user_email, instruction_id):
    """Deactivate an instruction for a user"""
    conn = sqlite3.connect('data/paddlepro.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE user_instructions 
        SET is_active = 0 
        WHERE id = ? AND user_email = ?
    ''', (instruction_id, user_email))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("\n=== STARTING PADDLEPRO SERVER ===")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print(f"Server will run at: http://localhost:5002")
    print("=== SERVER STARTING ===\n")
    
    # Run the server with debug output to terminal
    socketio.run(app, host='0.0.0.0', port=5002, debug=True, allow_unsafe_werkzeug=True)