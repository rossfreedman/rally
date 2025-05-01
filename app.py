from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
from openai import OpenAI
import time
import pandas as pd
import random
import re

# Load environment variables
load_dotenv()

# Check for required environment variables
if not os.getenv('OPENAI_API_KEY'):
    print("Error: OPENAI_API_KEY not found in environment variables")
    exit(1)

if not os.getenv('OPENAI_ASSISTANT_ID'):
    print("Error: OPENAI_ASSISTANT_ID not found in environment variables")
    exit(1)

app = Flask(__name__)
# Configure CORS to allow requests from any origin during development
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})

# Initialize OpenAI client with API key from environment
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Get assistant ID from environment
ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')
print(f"Using assistant ID: {ASSISTANT_ID}")

def clean_assistant_message(message):
    """Clean the assistant's message by removing reference markers."""
    # Remove references like 【4:0†all_tennaqua_players.json】
    cleaned_message = re.sub(r'【[^】]*】', '', message)
    # Remove any double spaces that might be left
    cleaned_message = re.sub(r'\s+', ' ', cleaned_message)
    # Remove any lines that are now empty
    cleaned_message = '\n'.join(line for line in cleaned_message.split('\n') if line.strip())
    return cleaned_message.strip()

# Mock player data generator
def generate_mock_players(series):
    players = []
    first_names = ["John", "Mike", "Sarah", "David", "Emma", "James", "Lisa", "Robert", "Emily", "William"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    num_players = random.randint(5, 10)
    for _ in range(num_players):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        rating = round(random.uniform(3.5, 4.5), 1)
        wins = random.randint(5, 30)
        losses = random.randint(2, 15)
        win_rate = f"{(wins / (wins + losses) * 100):.1f}%"
        
        players.append({
            "series": f"Series {series}",
            "name": name,
            "rating": rating,
            "wins": wins,
            "losses": losses,
            "winRate": win_rate
        })
    
    return players

@app.route('/api/players', methods=['GET'])
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
            requested_series_num = int(series)
            
            # Extract series numbers for comparison
            df['Series_Num'] = df['Series'].str.extract(r'(\d+)').astype(int)
            
            # Filter for higher series only (higher number = higher series)
            df = df[df['Series_Num'] > requested_series_num]
            
            if len(df) == 0:
                print(f"❌ No players found in higher series than {series}")
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
                # Calculate composite score
                pti = float(row['PTI'])
                win_percent = float(row['Win %'].rstrip('%'))
                series_num = int(row['Series'].split()[-1])  # Extract number from "Chicago X"
                
                # Normalize each component (0-1 scale where 1 is better)
                pti_score = (7 - pti) / 6  # PTI range ~1-7, lower is better
                win_score = win_percent / 100  # Already 0-100%, higher is better
                series_score = (40 - series_num) / 40  # Series range ~1-40, lower is better
                
                # Apply weightings
                composite_score = (
                    0.65 * pti_score +  # 65% weight on PTI
                    0.20 * win_score +  # 20% weight on win percentage
                    0.15 * series_score # 15% weight on series level
                )
                
                player = {
                    'name': f"{row['Last Name']} {row['First Name']}",
                    'series': row['Series'],
                    'rating': str(row['PTI']),
                    'wins': str(row['Wins']),
                    'losses': str(row['Losses']),
                    'winRate': f"{win_rate:.1f}%",
                    'compositeScore': composite_score
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

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        print("\n=== New Chat Request ===")
        data = request.json
        if not data:
            print("No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
            
        message = data.get('message')
        if not message:
            print("No message provided")
            return jsonify({'error': 'No message provided'}), 400

        print(f"Processing message: {message}")

        # Create a thread
        try:
            print("Creating new thread...")
            thread = client.beta.threads.create()
            print(f"Thread created successfully: {thread.id}")
        except Exception as e:
            print(f"Error creating thread: {str(e)}")
            return jsonify({'error': f'Failed to create chat thread: {str(e)}'}), 500

        # Add message to thread
        try:
            print(f"Adding message to thread {thread.id}...")
            message_response = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            print(f"Message added successfully: {message_response.id}")
        except Exception as e:
            print(f"Error adding message to thread: {str(e)}")
            return jsonify({'error': f'Failed to add message to chat: {str(e)}'}), 500

        # Run the assistant
        try:
            print(f"Starting assistant run on thread {thread.id}...")
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )
            print(f"Assistant run created successfully: {run.id}")
        except Exception as e:
            print(f"Error creating assistant run: {str(e)}")
            return jsonify({'error': f'Failed to start assistant: {str(e)}'}), 500

        # Wait for completion with timeout
        max_retries = 30  # 30 seconds timeout
        retry_count = 0
        while retry_count < max_retries:
            try:
                print(f"Checking run status (attempt {retry_count + 1}/{max_retries})...")
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                print(f"Run status: {run_status.status}")
                
                if run_status.status == 'completed':
                    break
                elif run_status.status == 'failed':
                    error_msg = getattr(run_status, 'last_error', 'Unknown error')
                    print(f"Run failed with error: {error_msg}")
                    return jsonify({'error': f'Assistant run failed: {error_msg}'}), 500
                elif run_status.status == 'expired':
                    print("Run expired")
                    return jsonify({'error': 'Assistant run expired'}), 500
                
                time.sleep(1)
                retry_count += 1
            except Exception as e:
                print(f"Error checking run status: {str(e)}")
                return jsonify({'error': f'Failed to check assistant status: {str(e)}'}), 500

        if retry_count >= max_retries:
            print("Request timed out")
            return jsonify({'error': 'Request timed out'}), 504

        # Get messages
        try:
            print(f"Retrieving messages from thread {thread.id}...")
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            raw_message = messages.data[0].content[0].text.value
            # Clean the message before sending it back
            assistant_message = clean_assistant_message(raw_message)
            print(f"Assistant response retrieved and cleaned successfully: {assistant_message[:100]}...")
            return jsonify({'response': assistant_message})
        except Exception as e:
            print(f"Error retrieving messages: {str(e)}")
            return jsonify({'error': f'Failed to retrieve assistant response: {str(e)}'}), 500

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n=== Starting Flask Server ===")
    app.run(debug=True, port=8081, host='0.0.0.0') 