from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
import traceback
from database_utils import execute_query, execute_query_one
from utils.logging import log_user_activity
from routes.act.schedule import get_matches_for_user_club
from utils.auth import login_required

def get_player_availability(player_name, match_date, series):
    """Get availability for a player on a specific date"""
    try:
        print(f"\n=== GET PLAYER AVAILABILITY ===")
        print(f"Player: {player_name}")
        print(f"Original date: {match_date}")
        print(f"Series: {series}")
        
        # First get the series_id
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s",
            {'series': series}
        )
        print(f"Series lookup result: {series_record}")
        
        if not series_record:
            print(f"No series found with name: {series}")
            return None
        
        # Standardize the date format
        original_date = match_date
        if isinstance(match_date, str):
            try:
                # Convert MM/DD/YYYY to YYYY-MM-DD
                if '/' in match_date:
                    month, day, year = match_date.split('/')
                    match_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                # Try to parse the date to validate format
                match_date = datetime.strptime(match_date, '%Y-%m-%d').date()
                print(f"Standardized date: {match_date} (from {original_date})")
            except ValueError as e:
                print(f"Invalid date format: {match_date}, error: {str(e)}")
                return None
        
        print(f"Querying availability with parameters:")
        print(f"  player_name: {player_name.strip()}")
        print(f"  match_date: {match_date}")
        print(f"  series_id: {series_record['id']}")
        
        # Try both date formats in the query
        result = execute_query_one(
            """
            SELECT availability_status 
            FROM player_availability 
            WHERE player_name = %(player_name)s 
            AND (
                match_date = %(match_date)s 
                OR match_date = %(match_date_str)s::date
            )
            AND series_id = %(series_id)s
            """,
            {
                'player_name': player_name.strip(),
                'match_date': match_date,
                'match_date_str': match_date.strftime('%Y-%m-%d'),
                'series_id': series_record['id']
            }
        )
        print(f"Availability lookup result: {result}")
        
        if not result:
            print(f"No availability found for {player_name} on {match_date}")
            return None
            
        print(f"Found availability status: {result['availability_status']}")
        return result['availability_status']
            
    except Exception as e:
        print(f"Error getting player availability: {str(e)}")
        print(traceback.format_exc())  # Add full traceback
        return None  # Return None on error instead of defaulting to "not_sure"

def update_player_availability(player_name, match_date, status, series):
    """Update or insert availability for a player"""
    try:
        print(f"\n=== UPDATE PLAYER AVAILABILITY ===")
        print(f"Player: {player_name}")
        print(f"Date: {match_date}")
        print(f"Status: {status}")
        print(f"Series: {series}")
        
        # First get the series_id
        series_record = execute_query_one(
            "SELECT id, name FROM series WHERE name = %(series)s",
            {'series': series}
        )
        print(f"Series lookup result: {series_record}")
        
        if not series_record:
            print(f"No series found with name: {series}")
            return False
        
        # Standardize the date format
        if isinstance(match_date, str):
            try:
                match_date = datetime.strptime(match_date, '%Y-%m-%d').date()
            except ValueError:
                print(f"Invalid date format: {match_date}")
                return False
        
        # Check if record exists first
        existing = execute_query_one(
            """
            SELECT id, availability_status 
            FROM player_availability 
            WHERE player_name = %(player_name)s 
            AND match_date = %(match_date)s 
            AND series_id = %(series_id)s
            """,
            {
                'player_name': player_name,
                'match_date': match_date,
                'series_id': series_record['id']
            }
        )
        print(f"Existing record: {existing}")
        
        # Perform the update/insert
        result = execute_query_one(
            """
            INSERT INTO player_availability 
                (player_name, match_date, availability_status, series_id, updated_at)
            VALUES 
                (%(player_name)s, %(match_date)s, %(status)s, %(series_id)s, CURRENT_TIMESTAMP)
            ON CONFLICT (player_name, match_date, series_id) 
            DO UPDATE SET 
                availability_status = %(status)s,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, availability_status
            """,
            {
                'player_name': player_name,
                'match_date': match_date,
                'status': status,
                'series_id': series_record['id']
            }
        )
        print(f"Update result: {result}")
        
        return bool(result)
    except Exception as e:
        print(f"Error updating player availability: {str(e)}")
        return False

def get_user_availability(player_name, matches, series):
    """Get availability for a user across multiple matches"""
    availability = []
    
    # Map numeric status to string status for template
    status_map = {
        1: 'available',
        2: 'unavailable', 
        3: 'not_sure',
        None: None  # No selection made
    }
    
    for match in matches:
        match_date = match.get('date', '')
        # Get this player's availability for this specific match
        numeric_status = get_player_availability(player_name, match_date, series)
        
        # Convert numeric status to string status that template expects
        string_status = status_map.get(numeric_status)
        availability.append({'status': string_status})
        
    return availability

def init_availability_routes(app):
    @app.route('/mobile/availability', methods=['GET', 'POST'])
    @login_required
    def mobile_availability():
        """Handle mobile availability page and updates"""
        if request.method == 'POST':
            try:
                data = request.json
                player_name = data.get('player_name')
                match_date = data.get('match_date')
                availability_status = data.get('availability_status')
                series = data.get('series')
                
                # Validate required fields
                required_fields = ['player_name', 'match_date', 'availability_status', 'series']
                if not all(field in data for field in required_fields):
                    missing = [f for f in required_fields if f not in data]
                    print(f"Missing required fields: {missing}")
                    return jsonify({'error': 'Missing required fields'}), 400
                
                # Validate availability_status is in valid range
                if availability_status not in [1, 2, 3]:
                    return jsonify({'error': 'Invalid availability status'}), 400
                
                success = update_player_availability(player_name, match_date, availability_status, series)
                if success:
                    return jsonify({'status': 'success'})
                return jsonify({'error': 'Failed to update availability'}), 500
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        else:
            user = session.get('user')
            player_name = f"{user['first_name']} {user['last_name']}"
            series = user['series']

            # Get matches for the user's club/series
            matches = get_matches_for_user_club(user)
            
            # Get this user's availability for each match
            availability = get_user_availability(player_name, matches, series)

            # Create match-availability pairs
            match_avail_pairs = list(zip(matches, availability))

            session_data = {
                'user': user,
                'authenticated': True,
                'matches': matches,
                'availability': availability,
                'players': [{'name': player_name}]  # Add player name to context
            }
            return render_template('mobile/availability.html', 
                                 session_data=session_data,
                                 match_avail_pairs=match_avail_pairs,
                                 players=[{'name': player_name}]  # Also pass directly to template
                                 )

    @app.route('/api/availability', methods=['GET', 'POST'])
    @login_required
    def handle_availability():
        """Handle availability API requests"""
        if request.method == 'POST':
            try:
                print(f"\n=== AVAILABILITY API POST ===")
                print(f"Request Content-Type: {request.content_type}")
                print(f"Request headers: {dict(request.headers)}")
                
                # Try to get data from various sources
                data = None
                error_details = []
                
                # Try JSON first
                if request.is_json:
                    try:
                        data = request.get_json()
                        print("Got JSON data")
                    except Exception as e:
                        error_msg = f"Error parsing JSON: {str(e)}"
                        print(error_msg)
                        error_details.append(error_msg)
                
                # Try form data if JSON failed
                if not data and request.form:
                    data = request.form.to_dict()
                    print("Got form data")
                
                # Try raw data if both failed
                if not data:
                    try:
                        raw_data = request.get_data(as_text=True)
                        print(f"Raw request data: {raw_data}")
                        data = json.loads(raw_data)
                        print("Parsed raw data as JSON")
                    except Exception as e:
                        error_msg = f"Error parsing raw data: {str(e)}"
                        print(error_msg)
                        error_details.append(error_msg)
                
                if not data:
                    error_msg = "No data received from any source"
                    if error_details:
                        error_msg += f". Errors: {', '.join(error_details)}"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                print(f"Final parsed data: {data}")
                print(f"Data type: {type(data)}")
                print(f"Keys in data: {list(data.keys())}")
                
                # Validate required fields
                required_fields = ['player_name', 'match_date', 'availability_status', 'series']
                missing = [f for f in required_fields if f not in data]
                print(f"Required fields: {required_fields}")
                print(f"Missing fields: {missing}")
                
                if missing:
                    error_msg = f"Missing required fields: {missing}"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                # Convert availability_status to int if it's a string
                try:
                    status = int(data['availability_status'])
                    data['availability_status'] = status
                except (ValueError, TypeError) as e:
                    error_msg = f"Error converting availability_status to int: {str(e)}"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                # Verify the player_name matches the logged-in user
                user = session['user']
                if data['player_name'] != f"{user['first_name']} {user['last_name']}":
                    error_msg = f"Player name mismatch: {data['player_name']} vs {user['first_name']} {user['last_name']}"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 403
                
                # Validate availability_status is in valid range
                if status not in [1, 2, 3]:
                    error_msg = f"Invalid availability status: {status}"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                success = update_player_availability(
                    data['player_name'],
                    data['match_date'],
                    status,  # Pass status directly
                    data['series']
                )
                
                if success:
                    return jsonify({'status': 'success'})
                return jsonify({'error': 'Failed to update availability'}), 500
            except Exception as e:
                error_msg = f"Error in availability POST handler: {str(e)}"
                print(error_msg)
                print(f"Full traceback: {traceback.format_exc()}")
                return jsonify({'error': error_msg}), 500
        else:
            try:
                player_name = request.args.get('player_name')
                match_date = request.args.get('match_date')
                series = request.args.get('series')
                
                print(f"\n=== AVAILABILITY API GET ===")
                print(f"Query params: player_name={player_name}, match_date={match_date}, series={series}")
                
                is_available = get_player_availability(player_name, match_date, series)
                return jsonify({'is_available': is_available})
            except Exception as e:
                print(f"Error in availability GET handler: {str(e)}")
                return jsonify({'error': str(e)}), 500 