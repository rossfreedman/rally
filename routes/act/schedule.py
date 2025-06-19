from flask import jsonify, request, session
from datetime import datetime
from utils.logging import log_user_activity
from utils.auth import login_required
from database_utils import execute_query, execute_query_one

def get_matches_for_user_club(user):
    """Get upcoming matches and practices for a user's club from the database"""
    try:
        # Get user's club and series
        user_club = user.get('club')
        user_series = user.get('series')
        if not user_club or not user_series:
            print("Missing club or series in user data")
            return []
        
        print(f"Looking for matches for club: {user_club}, series: {user_series}")
        
        # Handle different series name formats
        # For NSTF: "Series 2B" -> "Tennaqua S2B - Series 2B"
        # For APTA: "Chicago 22" -> "Tennaqua - 22"
        
        if 'Series' in user_series:
            # NSTF format: "Series 2B" -> "S2B"
            series_code = user_series.replace('Series ', 'S')
            user_team_pattern = f"{user_club} {series_code} - {user_series}"
        else:
            # APTA format: "Chicago 22" -> extract number
            series_num = user_series.split()[-1] if user_series else ''
            user_team_pattern = f"{user_club} - {series_num}"
        
        print(f"Looking for team pattern: {user_team_pattern}")
        
        # Create practice pattern for this user's club and series
        practice_pattern = f"{user_club} Practice - {user_series}"
        print(f"Looking for practice pattern: {practice_pattern}")
        
        # Query the database for matches where user's team is playing
        # Include both regular matches and practice entries
        # JOIN with clubs table to get club address for Google Maps links
        matches_query = """
            SELECT 
                s.match_date,
                s.match_time,
                s.home_team,
                s.away_team,
                s.location,
                c.club_address,
                l.league_id,
                CASE 
                    WHEN s.home_team ILIKE %s THEN 'practice'
                    ELSE 'match'
                END as type
            FROM schedule s
            LEFT JOIN leagues l ON s.league_id = l.id
            LEFT JOIN clubs c ON s.location = c.name
            WHERE (s.home_team ILIKE %s OR s.away_team ILIKE %s OR s.home_team ILIKE %s)
            ORDER BY s.match_date, s.match_time
        """
        
        # Search patterns:
        # 1. Practice pattern: "Tennaqua Practice - Chicago 22"
        # 2. Team pattern for regular matches: "Tennaqua - 22"
        practice_search = f'%{practice_pattern}%'
        team_search = f'%{user_team_pattern}%'
        
        matches = execute_query(matches_query, [practice_search, practice_search, team_search, team_search])
        
        filtered_matches = []
        for match in matches:
            try:
                # Format date and time to match the original JSON format
                match_date = match['match_date'].strftime('%m/%d/%Y') if match['match_date'] else ''
                match_time = match['match_time'].strftime('%I:%M %p').lstrip('0') if match['match_time'] else ''
                
                # Determine if this is a practice or match
                is_practice = 'Practice' in (match['home_team'] or '')
                
                # Normalize match data to consistent format
                normalized_match = {
                    'date': match_date,
                    'time': match_time,
                    'location': match['location'] or '',
                    'club_address': match['club_address'] or '',  # Include club address
                    'home_team': match['home_team'] or '',
                    'away_team': match['away_team'] or '',
                    'type': 'practice' if is_practice else 'match'
                }
                
                # Add practice-specific fields
                if is_practice:
                    normalized_match['description'] = match['home_team']
                
                filtered_matches.append(normalized_match)
                
                if is_practice:
                    print(f"Found practice: {match['home_team']} on {match_date} at {match_time}")
                else:
                    print(f"Found match: {match['home_team']} vs {match['away_team']} on {match_date}")
                
            except Exception as e:
                print(f"Warning: Skipping invalid match record: {e}")
                continue
        
        # Sort matches by date and time (same logic as reference)
        def sort_key(match):
            try:
                date_obj = datetime.strptime(match['date'], '%m/%d/%Y')
                time_obj = datetime.strptime(match['time'], '%I:%M %p')
                return (date_obj, time_obj)
            except ValueError:
                # If parsing fails, put it at the end
                return (datetime.max, datetime.max)
        
        filtered_matches.sort(key=sort_key)
        
        print(f"Found {len(filtered_matches)} total entries (matches + practices) for team")
        return filtered_matches
        
    except Exception as e:
        print(f"Error getting matches for user club: {str(e)}")
        return []

def init_schedule_routes(app):
    @app.route('/api/schedule')
    @login_required
    def serve_schedule():
        """Serve the schedule data from database"""
        try:
            # Query match history from the database instead of JSON file
            query = """
                SELECT 
                    ms.match_date as "Date",
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team", 
                    ms.home_player_1_id as "Home Player 1 ID",
                    ms.home_player_2_id as "Home Player 2 ID",
                    ms.away_player_1_id as "Away Player 1 ID",
                    ms.away_player_2_id as "Away Player 2 ID",
                    ms.scores as "Scores",
                    ms.winner as "Winner",
                    l.league_id
                FROM match_scores ms
                LEFT JOIN leagues l ON ms.league_id = l.id
                ORDER BY ms.match_date DESC
            """
            data = execute_query(query)
            
            # Convert date objects to strings for JSON serialization
            for row in data:
                if row.get('Date'):
                    row['Date'] = row['Date'].strftime('%d-%b-%y')
            
            return jsonify(data)
        except Exception as e:
            print(f"Error loading schedule from database: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/team-matches')
    @login_required
    def get_team_matches():
        """Get matches for a team from database"""
        try:
            # Query match history from the database instead of JSON file
            query = """
                SELECT 
                    ms.match_date as "Date",
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.home_player_1_id as "Home Player 1 ID",
                    ms.home_player_2_id as "Home Player 2 ID", 
                    ms.away_player_1_id as "Away Player 1 ID",
                    ms.away_player_2_id as "Away Player 2 ID",
                    ms.scores as "Scores",
                    ms.winner as "Winner",
                    l.league_id
                FROM match_scores ms
                LEFT JOIN leagues l ON ms.league_id = l.id
                ORDER BY ms.match_date DESC
            """
            matches = execute_query(query)
            
            # Convert date objects to strings for JSON serialization
            for match in matches:
                if match.get('Date'):
                    match['Date'] = match['Date'].strftime('%d-%b-%y')
            
            return jsonify(matches)
        except Exception as e:
            print(f"Error getting team matches from database: {str(e)}")
            return jsonify({'error': str(e)}), 500 