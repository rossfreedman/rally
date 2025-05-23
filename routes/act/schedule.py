from flask import jsonify, request, session
from datetime import datetime
import os
import json
from utils.logging import log_user_activity
from utils.auth import login_required

def get_matches_for_user_club(user):
    """Get upcoming matches for a user's club from schedules.json"""
    try:
        # Use schedules.json for upcoming matches (availability system)
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'schedules.json')
        print(f"Looking for schedule file at: {file_path}")
        
        with open(file_path, 'r') as f:
            all_matches = json.load(f)
            
        # Get user's club and series
        user_club = user.get('club')
        user_series = user.get('series')
        if not user_club or not user_series:
            print("Missing club or series in user data")
            return []
            
        # Extract series number (e.g., "22" from "Series 22")
        series_num = user_series.split()[-1] if user_series else ''
        print(f"Looking for matches for club: {user_club}, series: {series_num}")
        
        # The team name in schedules.json uses multiple formats:
        # 1. "Club - Series - Series" (e.g. "Tennaqua - 22 - 22")
        # 2. "Club - Chicago - Series - Series" (e.g. "Midtown - Chicago - 6 - 6") 
        # 3. "Club - Series" (legacy format)
        possible_team_formats = [
            f"{user_club} - {series_num} - {series_num}",  # Format 1
            f"{user_club} - Chicago - {series_num} - {series_num}",  # Format 2
            f"{user_club} - {series_num}"  # Legacy format
        ]
        
        print(f"Looking for matches with team identifiers: {possible_team_formats}")
        
        filtered_matches = []
        for match in all_matches:
            try:
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                
                # Check if either home or away team matches any of our possible formats
                is_user_team = any(fmt in (home_team, away_team) for fmt in possible_team_formats)
                
                if is_user_team:
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
                
        print(f"Found {len(filtered_matches)} matches for team")
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
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'match_history.json')
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
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'match_history.json')
            with open(file_path, 'r') as f:
                matches = json.load(f)
            return jsonify(matches)
        except Exception as e:
            print(f"Error getting team matches: {str(e)}")
            return jsonify({'error': str(e)}), 500 