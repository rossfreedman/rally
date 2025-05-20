from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
from database_utils import execute_query, execute_query_one
from utils.logging import log_user_activity
from routes.act.schedule import get_matches_for_user_club
from utils.auth import login_required

def get_player_availability(player_name, match_date, series):
    """Get availability for a player on a specific date"""
    try:
        print(f"\n=== GET PLAYER AVAILABILITY ===")
        print(f"Player: {player_name}")
        print(f"Date: {match_date}")
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
        
        result = execute_query_one(
            """
            SELECT availability_status 
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
        print(f"Availability lookup result: {result}")
        
        return result['availability_status'] if result else None
    except Exception as e:
        print(f"Error getting player availability: {str(e)}")
        return None

def update_player_availability(player_name, match_date, availability_status, series):
    """Update or insert availability for a player"""
    try:
        print(f"\n=== UPDATE PLAYER AVAILABILITY ===")
        print(f"Player: {player_name}")
        print(f"Date: {match_date}")
        print(f"Status: {availability_status}")
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
                (%(player_name)s, %(match_date)s, %(availability_status)s, %(series_id)s, CURRENT_TIMESTAMP)
            ON CONFLICT (player_name, match_date, series_id) 
            DO UPDATE SET 
                availability_status = %(availability_status)s,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, availability_status
            """,
            {
                'player_name': player_name,
                'match_date': match_date,
                'availability_status': availability_status,
                'series_id': series_record['id']
            }
        )
        print(f"Update result: {result}")
        
        return bool(result)
    except Exception as e:
        print(f"Error updating player availability: {str(e)}")
        return False

def get_user_availability(player_name, matches, series):
    """Get availability status for a list of matches for a specific player"""
    availability = []
    for match in matches:
        match_date = match.get('date', '')
        status = get_player_availability(player_name, match_date, series)
        if status is None:
            status = 'unknown'
        availability.append({'status': str(status)})
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

            session_data = {
                'user': user,
                'authenticated': True,
                'matches': matches,
                'availability': availability
            }
            return render_template('mobile/availability.html', session_data=session_data)

    @app.route('/api/availability', methods=['GET', 'POST'])
    @login_required
    def handle_availability():
        """Handle availability API requests"""
        if request.method == 'POST':
            try:
                data = request.json
                print(f"\n=== AVAILABILITY API POST ===")
                print(f"Raw request data: {request.get_data()}")
                print(f"Content type: {request.content_type}")
                print(f"Parsed JSON data: {data}")
                
                # Validate required fields
                required_fields = ['player_name', 'match_date', 'availability_status', 'series']
                missing_fields = [f for f in required_fields if f not in data]
                
                if missing_fields:
                    error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                    print(f"Error: {error_msg}")
                    print(f"Received fields: {list(data.keys())}")
                    return jsonify({'error': error_msg}), 400
                
                # Validate availability_status is an integer between 1 and 3
                try:
                    availability_status = int(data['availability_status'])
                    if availability_status not in [1, 2, 3]:
                        error_msg = f"Invalid availability_status value: {availability_status}"
                        print(f"Error: {error_msg}")
                        return jsonify({'error': 'availability_status must be 1, 2, or 3'}), 400
                except (ValueError, TypeError):
                    error_msg = f"Invalid availability_status type: {data['availability_status']}"
                    print(f"Error: {error_msg}")
                    return jsonify({'error': 'availability_status must be an integer'}), 400
                
                # Verify the player_name matches the logged-in user
                user = session['user']
                if data['player_name'] != f"{user['first_name']} {user['last_name']}":
                    error_msg = f"Player name mismatch: {data['player_name']} vs {user['first_name']} {user['last_name']}"
                    print(f"Error: {error_msg}")
                    return jsonify({'error': 'Can only update your own availability'}), 403
                
                # Validate date format
                try:
                    match_date = datetime.strptime(data['match_date'], '%Y-%m-%d').date()
                except ValueError:
                    error_msg = f"Invalid date format: {data['match_date']}"
                    print(f"Error: {error_msg}")
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
                
                print(f"All validation passed, updating availability...")
                success = update_player_availability(
                    data['player_name'],
                    match_date,
                    availability_status,
                    data['series']
                )
                
                if success:
                    print("Successfully updated availability")
                    return jsonify({'status': 'success'})
                
                print("Failed to update availability")
                return jsonify({'error': 'Failed to update availability'}), 500
            except Exception as e:
                print(f"Error in availability POST handler: {str(e)}")
                import traceback
                print(f"Full traceback: {traceback.format_exc()}")
                return jsonify({'error': str(e)}), 500
        else:
            try:
                player_name = request.args.get('player_name')
                match_date = request.args.get('match_date')
                series = request.args.get('series')
                
                print(f"\n=== AVAILABILITY API GET ===")
                print(f"Query params: player_name={player_name}, match_date={match_date}, series={series}")
                
                availability_status = get_player_availability(player_name, match_date, series)
                return jsonify({'availability_status': availability_status})
            except Exception as e:
                print(f"Error in availability GET handler: {str(e)}")
                return jsonify({'error': str(e)}), 500 