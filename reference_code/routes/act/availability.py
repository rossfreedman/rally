from flask import jsonify, request, session, render_template
from datetime import datetime
import sqlite3
import os
import json
from utils.db import get_db_path
from utils.logging import log_user_activity
from routes.act.schedule import get_matches_for_user_club

def get_player_availability(player_name, match_date, series):
    """Get availability for a player on a specific date"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT is_available 
            FROM player_availability 
            WHERE player_name = ? AND match_date = ? AND series = ?
        ''', (player_name, match_date, series))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting player availability: {str(e)}")
        return None

def update_player_availability(player_name, match_date, is_available, series):
    """Update or insert availability for a player"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO player_availability 
            (player_name, match_date, is_available, series) 
            VALUES (?, ?, ?, ?)
        ''', (player_name, match_date, is_available, series))
        
        conn.commit()
        conn.close()
        return True
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
    def handle_availability():
        """Handle availability API requests"""
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
            try:
                player_name = request.args.get('player_name')
                match_date = request.args.get('match_date')
                series = request.args.get('series')
                
                is_available = get_player_availability(player_name, match_date, series)
                return jsonify({'is_available': is_available})
            except Exception as e:
                return jsonify({'error': str(e)}), 500 