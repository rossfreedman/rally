from flask import jsonify, request, session
from datetime import datetime
import os
import json
from utils.logging import log_user_activity
from utils.auth import login_required

def get_matches_for_user_club(user):
    """Get upcoming matches and practices for a user's club from schedules.json"""
    try:
        # Use schedules.json for upcoming matches (availability system)
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'leagues', 'all', 'schedules.json')
        print(f"Looking for schedule file at: {file_path}")
        
        with open(file_path, 'r') as f:
            all_matches = json.load(f)
            
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
        
        filtered_matches = []
        for match in all_matches:
            try:
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                practice_field = match.get('Practice', '')
                
                # Check if this is a practice entry for the user's club
                if practice_field and practice_field == user_club:
                    print(f"Found practice: {practice_field} on {match.get('date', '')}")
                    # Normalize practice data to consistent format
                    normalized_practice = {
                        'date': match.get('date', ''),
                        'time': match.get('time', ''),
                        'location': practice_field,
                        'home_team': '',
                        'away_team': '',
                        'type': 'practice',
                        'description': f"{practice_field} Practice"
                    }
                    filtered_matches.append(normalized_practice)
                # Check if either home or away team matches our team pattern (regular matches)
                elif user_team_pattern in (home_team, away_team):
                    print(f"Found match: {home_team} vs {away_team}")
                    # Normalize match data to consistent format
                    normalized_match = {
                        'date': match.get('date', ''),
                        'time': match.get('time', ''),
                        'location': match.get('location', ''),
                        'home_team': home_team,
                        'away_team': away_team,
                        'type': 'match'
                    }
                    filtered_matches.append(normalized_match)
            except Exception as e:
                print(f"Warning: Skipping invalid match record: {e}")
                continue
        
        # Sort matches and practices by date and time
        def sort_key(match):
            try:
                date_obj = datetime.strptime(match['date'], '%m/%d/%Y')
                time_obj = datetime.strptime(match['time'], '%I:%M %p')
                return (date_obj, time_obj)
            except ValueError:
                # If parsing fails, put it at the end
                return (datetime.max, datetime.max)
        
        filtered_matches.sort(key=sort_key)
        
        print(f"Found {len(filtered_matches)} matches and practices for team")
        return filtered_matches
    except Exception as e:
        print(f"Error getting matches for user club: {str(e)}")
        return []

def init_schedule_routes(app):
    @app.route('/api/schedule')
    @login_required
    def serve_schedule():
        """Serve the schedule data"""
        try:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'leagues', 'all', 'match_history.json')
            with open(file_path, 'r') as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            print(f"Error loading schedule: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/team-matches')
    @login_required
    def get_team_matches():
        """Get matches for a team"""
        try:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'leagues', 'all', 'match_history.json')
            with open(file_path, 'r') as f:
                matches = json.load(f)
            return jsonify(matches)
        except Exception as e:
            print(f"Error getting team matches: {str(e)}")
            return jsonify({'error': str(e)}), 500 