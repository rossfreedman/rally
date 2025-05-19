from flask import jsonify, request, session
from datetime import datetime
import sqlite3
import os
import json
from utils.db import get_db_path
from utils.logging import log_user_activity

def get_matches_for_user_club(user):
    """Get matches for a user's club"""
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'match_history.json')
        with open(file_path, 'r') as f:
            matches = json.load(f)
            
        # Filter matches for user's club and series
        user_club = user.get('club')
        user_series = user.get('series')
        
        filtered_matches = []
        for match in matches:
            if match.get('club') == user_club and match.get('series') == user_series:
                filtered_matches.append(match)
                
        return filtered_matches
    except Exception as e:
        print(f"Error getting matches for user club: {str(e)}")
        return []

def init_schedule_routes(app):
    @app.route('/api/schedule')
    @app.route('/mobile/view-schedule')
    def serve_schedule():
        """Serve the schedule data and view"""
        try:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data', 'match_history.json')
            with open(file_path, 'r') as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            print(f"Error loading schedule: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/team-matches')
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