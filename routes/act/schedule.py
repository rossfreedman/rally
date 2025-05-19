from flask import jsonify, request, session
from datetime import datetime
import os
import json
from utils.logging import log_user_activity
from utils.auth import login_required

def get_matches_for_user_club(user):
    """Get matches for a user's club"""
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'match_history.json')
        with open(file_path, 'r') as f:
            matches = json.load(f)
            
        # Get user's club and series
        user_club = user.get('club')
        user_series = user.get('series')
        if not user_club or not user_series:
            print("Missing club or series in user data")
            return []
            
        # Extract series number (e.g., "22" from "Series 22")
        series_num = user_series.split()[-1] if user_series else ''
        team_identifier = f"{user_club} - {series_num}"
        print(f"Looking for matches with team identifier: {team_identifier}")
        
        filtered_matches = []
        for match in matches:
            # Check if the user's team is either home or away
            if (match.get('home_team') == team_identifier or 
                match.get('away_team') == team_identifier):
                filtered_matches.append(match)
                
        print(f"Found {len(filtered_matches)} matches for team {team_identifier}")
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