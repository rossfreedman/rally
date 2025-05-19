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
            SELECT is_available 
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
        
        return result['is_available'] if result else None
    except Exception as e:
        print(f"Error getting player availability: {str(e)}")
        return None

def update_player_availability(player_name, match_date, is_available, series):
    """Update or insert availability for a player"""
    try:
        print(f"\n=== UPDATE PLAYER AVAILABILITY ===")
        print(f"Player: {player_name}")
        print(f"Date: {match_date}")
        print(f"Available: {is_available}")
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
            SELECT id, is_available 
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
                (player_name, match_date, is_available, series_id, updated_at)
            VALUES 
                (%(player_name)s, %(match_date)s, %(is_available)s, %(series_id)s, CURRENT_TIMESTAMP)
            ON CONFLICT (player_name, match_date, series_id) 
            DO UPDATE SET 
                is_available = %(is_available)s,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, is_available
            """,
            {
                'player_name': player_name,
                'match_date': match_date,
                'is_available': is_available,
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
        is_available = get_player_availability(player_name, match_date, series)
        if is_available is None:
            status = 'unknown'
        elif is_available:
            status = 'available'
        else:
            status = 'unavailable'
        availability.append({'status': status})
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
                is_available = data.get('is_available')
                series = data.get('series')
                
                success = update_player_availability(player_name, match_date, is_available, series)
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
                print(f"Received data: {data}")
                
                # Validate required fields
                required_fields = ['player_name', 'match_date', 'is_available', 'series']
                if not all(field in data for field in required_fields):
                    missing = [f for f in required_fields if f not in data]
                    print(f"Missing required fields: {missing}")
                    return jsonify({'error': 'Missing required fields'}), 400
                
                # Verify the player_name matches the logged-in user
                user = session['user']
                if data['player_name'] != f"{user['first_name']} {user['last_name']}":
                    print(f"Player name mismatch: {data['player_name']} vs {user['first_name']} {user['last_name']}")
                    return jsonify({'error': 'Can only update your own availability'}), 403
                
                success = update_player_availability(
                    data['player_name'],
                    data['match_date'],
                    data['is_available'],
                    data['series']
                )
                
                if success:
                    return jsonify({'status': 'success'})
                return jsonify({'error': 'Failed to update availability'}), 500
            except Exception as e:
                print(f"Error in availability POST handler: {str(e)}")
                return jsonify({'error': str(e)}), 500
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