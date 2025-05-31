from flask import jsonify, request, session, render_template
from utils.auth import login_required
from database_utils import execute_query, execute_query_one
from datetime import datetime, date, timezone, timedelta
from routes.act.schedule import get_matches_for_user_club
import traceback
import pytz

# Define the application timezone
APP_TIMEZONE = pytz.timezone('America/Chicago')

# Import the correct date utility function for timezone handling
from utils.date_utils import date_to_db_timestamp, normalize_date_string

def normalize_date_for_db(date_input, target_timezone='UTC'):
    """
    DEPRECATED: Use date_to_db_timestamp from utils.date_utils instead.
    This function is kept for backward compatibility but should be replaced.
    
    Normalize date input to a consistent TIMESTAMPTZ format for database storage.
    After migration to TIMESTAMPTZ, always stores dates at midnight UTC to avoid timezone edge cases.
    
    Args:
        date_input: String date in various formats or datetime object
        target_timezone: Target timezone (defaults to 'UTC' for consistency)
    
    Returns:
        datetime: Timezone-aware datetime object at midnight UTC
    """
    print("⚠️  Warning: Using deprecated normalize_date_for_db. Use date_to_db_timestamp instead.")
    try:
        print(f"Normalizing date: {date_input} (type: {type(date_input)})")
        
        if isinstance(date_input, str):
            # Handle multiple date formats
            if '/' in date_input:
                # Handle MM/DD/YYYY format
                dt = datetime.strptime(date_input, '%m/%d/%Y')
            else:
                # Handle YYYY-MM-DD format
                dt = datetime.strptime(date_input, '%Y-%m-%d')
        elif isinstance(date_input, datetime):
            dt = date_input
        elif hasattr(date_input, 'year'):  # Handle date objects
            dt = datetime.combine(date_input, datetime.min.time())
        else:
            raise ValueError(f"Unsupported date type: {type(date_input)}")
        
        # Set time to midnight for consistency with TIMESTAMPTZ schema
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Always store as UTC timezone to avoid conversion issues
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        
        print(f"Normalized to midnight UTC: {dt}")
        return dt
        
    except Exception as e:
        print(f"Error normalizing date {date_input}: {str(e)}")
        raise

def get_player_availability(player_name, match_date, series):
    """Get a player's availability status for a specific match date and series with proper timezone handling"""
    try:
        print(f"\n=== Getting availability for {player_name} on {match_date} ===")
        
        # Get series ID
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(name)s",
            {'name': series}
        )
        
        if not series_record:
            print(f"❌ Series not found: {series}")
            return None
            
        series_id = series_record['id']
        
        # Use proper timezone handling for TIMESTAMPTZ column
        try:
            normalized_date = date_to_db_timestamp(match_date)
            print(f"Converted date for TIMESTAMPTZ query: {match_date} -> {normalized_date}")
        except Exception as e:
            print(f"❌ Error converting date {match_date}: {str(e)}")
            return None

        # Query using TIMESTAMPTZ with UTC timezone handling
        query = """
            SELECT availability_status, match_date
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
        """
        params = {
            'player': player_name.strip(),
            'series_id': series_id,
            'date': normalized_date
        }
        
        result = execute_query_one(query, params)
        
        if not result:
            print(f"No availability found for {player_name} on {match_date}")
            return None
        
        print(f"Found availability status: {result['availability_status']}")
        return result['availability_status']
        
    except Exception as e:
        print(f"❌ Error getting player availability: {str(e)}")
        print(traceback.format_exc())
        return None

def update_player_availability(player_name, match_date, availability_status, series):
    """
    Update player availability with proper timezone handling.
    """
    try:
        print(f"\n=== UPDATE PLAYER AVAILABILITY ===")
        print(f"Input - Player: {player_name}, Date: {match_date}, Status: {availability_status}, Series: {series}")
        
        # Get series ID
        series_record = execute_query_one(
            "SELECT id FROM series WHERE name = %(series)s",
            {'series': series}
        )
        
        if not series_record:
            print(f"❌ Series not found: {series}")
            return False
        
        series_id = series_record['id']
        
        # Convert date to datetime object for database storage
        try:
            date_obj = date_to_db_timestamp(match_date)
            print(f"Converted date for TIMESTAMPTZ storage: {match_date} -> {date_obj}")
        except Exception as e:
            print(f"❌ Error converting date: {e}")
            return False
        
        # Check if record exists using timezone-aware date comparison
        existing_record = execute_query_one(
            """
            SELECT id, availability_status, match_date
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
            """,
            {
                'player': player_name.strip(),
                'series_id': series_id,
                'date': date_obj
            }
        )
        
        if existing_record:
            # Update existing record
            print(f"Updating existing record (ID: {existing_record['id']})")
            print(f"Old status: {existing_record['availability_status']} -> New status: {availability_status}")
            
            result = execute_query(
                """
                UPDATE player_availability 
                SET availability_status = %(status)s, updated_at = NOW()
                WHERE id = %(id)s
                """,
                {
                    'status': availability_status,
                    'id': existing_record['id']
                }
            )
        else:
            # Before creating a new record, check for discrepant dates (timezone issues)
            print("No record found with intended date. Checking for date discrepancies...")
            
            # Check one day earlier (most common timezone issue)
            one_day_earlier = date_obj - timedelta(days=1)
            earlier_record = execute_query_one(
                """
                SELECT id, match_date, availability_status 
                FROM player_availability 
                WHERE player_name = %(player)s 
                AND series_id = %(series_id)s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
                """,
                {
                    'player': player_name.strip(),
                    'series_id': series_id,
                    'date': one_day_earlier
                }
            )
            
            # Check one day later (less common but possible)
            one_day_later = date_obj + timedelta(days=1)
            later_record = execute_query_one(
                """
                SELECT id, match_date, availability_status 
                FROM player_availability 
                WHERE player_name = %(player)s 
                AND series_id = %(series_id)s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
                """,
                {
                    'player': player_name.strip(),
                    'series_id': series_id,
                    'date': one_day_later
                }
            )
            
            # If we find a discrepant record, correct it instead of creating a new one
            if earlier_record:
                print(f"🔧 Found timezone discrepancy: record exists one day earlier")
                print(f"   Correcting record ID {earlier_record['id']} from {one_day_earlier} to {date_obj}")
                
                # Update both the date and status of the discrepant record
                result = execute_query(
                    """
                    UPDATE player_availability 
                    SET match_date = %(correct_date)s, availability_status = %(status)s, updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {
                        'correct_date': date_obj,
                        'status': availability_status,
                        'id': earlier_record['id']
                    }
                )
                
            elif later_record:
                print(f"🔧 Found record one day later: {one_day_later} (should be {date_obj})")
                print(f"   Correcting record ID {later_record['id']} date and status")
                
                # Update both the date and status of the discrepant record
                result = execute_query(
                    """
                    UPDATE player_availability 
                    SET match_date = %(correct_date)s, availability_status = %(status)s, updated_at = NOW()
                    WHERE id = %(id)s
                    """,
                    {
                        'correct_date': date_obj,
                        'status': availability_status,
                        'id': later_record['id']
                    }
                )
                
            else:
                # Create new record
                print("Creating new availability record")
                print(f"Inserting: player={player_name.strip()}, date={date_obj}, status={availability_status}, series_id={series_id}")
                
                result = execute_query(
                    """
                    INSERT INTO player_availability (player_name, match_date, availability_status, series_id, updated_at)
                    VALUES (%(player)s, %(date)s, %(status)s, %(series_id)s, NOW())
                    """,
                    {
                        'player': player_name.strip(),
                        'date': date_obj,
                        'status': availability_status,
                        'series_id': series_id
                    }
                )
        
        # Verify the record was stored correctly
        verification_record = execute_query_one(
            """
            SELECT availability_status, match_date
            FROM player_availability 
            WHERE player_name = %(player)s 
            AND series_id = %(series_id)s 
            AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
            """,
            {
                'player': player_name.strip(),
                'series_id': series_id,
                'date': date_obj
            }
        )
        
        if verification_record:
            print(f"✅ Verification successful: Status={verification_record['availability_status']}, Date={verification_record['match_date']}")
            return True
        else:
            print("❌ Verification failed: Record not found after insert/update")
            return False
        
    except Exception as e:
        print(f"❌ Error updating player availability: {str(e)}")
        print(traceback.format_exc())
        return False

def get_user_availability(player_name, matches, series):
    """Get availability for a user across multiple matches"""
    # First get the series_id
    series_record = execute_query_one(
        "SELECT id FROM series WHERE name = %(series)s",
        {'series': series}
    )
    
    if not series_record:
        return []
    
    # Map numeric status to string status for template
    status_map = {
        1: 'available',
        2: 'unavailable', 
        3: 'not_sure',
        None: None  # No selection made
    }
    
    availability = []
    for match in matches:
        match_date = match.get('date', '')
        # Get this player's availability for this specific match
        numeric_status = get_player_availability(player_name, match_date, series)
        
        # Convert numeric status to string status that template expects
        string_status = status_map.get(numeric_status)
        availability.append({'status': string_status})
        
    return availability

def init_availability_routes(app):
    @app.route('/debug/availability')
    def debug_availability():
        """Debug route to test availability functionality"""
        return f"<h1>Debug Availability</h1><p>This route works!</p><p>Session keys: {list(session.keys()) if session else 'No session'}</p>"

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
            try:
                user = session.get('user')
                if not user:
                    return jsonify({'error': 'No user in session'}), 400
                
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
                    'players': [{'name': player_name}]
                }
                
                return render_template('mobile/availability.html', 
                                     session_data=session_data,
                                     match_avail_pairs=match_avail_pairs,
                                     players=[{'name': player_name}]
                                     )
                
            except Exception as e:
                print(f"ERROR in mobile_availability: {str(e)}")
                print(traceback.format_exc())
                return f"Error: {str(e)}", 500

    @app.route('/api/availability', methods=['GET', 'POST'])
    @login_required
    def handle_availability():
        """Handle availability API requests"""
        if request.method == 'POST':
            try:
                print(f"\n=== AVAILABILITY API POST START ===")
                print(f"Request Content-Type: {request.content_type}")
                print(f"Request headers: {dict(request.headers)}")
                print(f"Session user: {session.get('user', {})}")
                
                # Parse request data with detailed error logging
                data = None
                
                if request.is_json:
                    try:
                        data = request.get_json()
                        print(f"✅ Successfully parsed JSON data: {data}")
                    except Exception as e:
                        error_msg = f"❌ Error parsing JSON: {str(e)}"
                        print(error_msg)
                        return jsonify({'error': error_msg}), 400
                elif request.form:
                    data = request.form.to_dict()
                    print(f"✅ Successfully parsed form data: {data}")
                else:
                    error_msg = "❌ No JSON or form data found"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                # Validate data is not None
                if not data:
                    error_msg = "❌ Parsed data is empty or None"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                print(f"✅ Final parsed data: {data}")
                print(f"✅ Data type: {type(data)}")
                print(f"✅ Keys in data: {list(data.keys())}")
                
                # Extract and validate required fields with detailed logging
                player_name = data.get('player_name')
                match_date = data.get('match_date')
                availability_status = data.get('availability_status')
                series = data.get('series')
                
                print(f"✅ Extracted fields:")
                print(f"  - player_name: '{player_name}' (type: {type(player_name)})")
                print(f"  - match_date: '{match_date}' (type: {type(match_date)})")
                print(f"  - availability_status: '{availability_status}' (type: {type(availability_status)})")
                print(f"  - series: '{series}' (type: {type(series)})")
                
                # Validate required fields
                required_fields = ['player_name', 'match_date', 'availability_status', 'series']
                missing_fields = [field for field in required_fields if field not in data or data[field] is None or data[field] == '']
                
                if missing_fields:
                    error_msg = f"❌ Missing or empty required fields: {missing_fields}"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                # Convert and validate availability_status
                try:
                    status = int(availability_status)
                    print(f"✅ Converted availability_status to int: {status}")
                except (ValueError, TypeError) as e:
                    error_msg = f"❌ Error converting availability_status '{availability_status}' to int: {str(e)}"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                # Validate status range
                if status not in [1, 2, 3]:
                    error_msg = f"❌ Invalid availability status: {status} (must be 1, 2, or 3)"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 400
                
                # Verify user session
                user = session.get('user')
                if not user:
                    error_msg = "❌ No user found in session"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 401
                
                expected_player_name = f"{user['first_name']} {user['last_name']}"
                if player_name != expected_player_name:
                    error_msg = f"❌ Player name mismatch: received '{player_name}' vs expected '{expected_player_name}'"
                    print(error_msg)
                    return jsonify({'error': error_msg}), 403
                
                print(f"✅ All validations passed. Calling update_player_availability...")
                
                # Call the update function
                success = update_player_availability(player_name, match_date, status, series)
                
                if success:
                    print(f"✅ Successfully updated availability")
                    return jsonify({'status': 'success'})
                else:
                    error_msg = "❌ update_player_availability returned False"
                    print(error_msg)
                    return jsonify({'error': 'Failed to update availability - database operation failed'}), 500
                    
            except Exception as e:
                error_msg = f"❌ Unhandled exception in availability POST handler: {str(e)}"
                print(error_msg)
                print(f"❌ Full traceback:\n{traceback.format_exc()}")
                return jsonify({'error': f'Server error: {str(e)}'}), 500
        else:
            # GET request handling
            try:
                player_name = request.args.get('player_name')
                match_date = request.args.get('match_date')
                series = request.args.get('series')
                
                print(f"\n=== AVAILABILITY API GET ===")
                print(f"Query params: player_name={player_name}, match_date={match_date}, series={series}")
                
                is_available = get_player_availability(player_name, match_date, series)
                return jsonify({'is_available': is_available})
            except Exception as e:
                error_msg = f"❌ Error in availability GET handler: {str(e)}"
                print(error_msg)
                return jsonify({'error': error_msg}), 500 