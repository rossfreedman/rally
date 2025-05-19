from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
from utils.db import execute_query
from utils.logging import log_user_activity
from utils.auth import login_required

def init_find_sub_routes(app):
    @app.route('/mobile/find-subs')
    @login_required
    def serve_mobile_find_subs():
        """Serve the mobile Find Sub page"""
        try:
            session_data = {
                'user': session['user'],
                'authenticated': True
            }
            log_user_activity(session['user']['email'], 'page_visit', page='mobile_find_subs')
            return render_template('mobile/find_subs.html', session_data=session_data)
        except Exception as e:
            print(f"Error serving find subs page: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/player-contact')
    def get_player_contact():
        """Get player contact information"""
        try:
            players = execute_query(
                """
                SELECT first_name, last_name, email, phone
                FROM users
                ORDER BY last_name, first_name
                """
            )
            
            formatted_players = [{
                'name': f"{player['first_name']} {player['last_name']}",
                'email': player['email'],
                'phone': player['phone'] if player['phone'] else 'Not provided'
            } for player in players]
            
            return jsonify(formatted_players)
        except Exception as e:
            print(f"Error getting player contact info: {str(e)}")
            return jsonify({'error': str(e)}), 500 