from flask import jsonify, request, session, render_template
from datetime import datetime
import sqlite3
import os
import json
from utils.db import get_db_path
from utils.logging import log_user_activity

def init_find_sub_routes(app):
    @app.route('/mobile/find-subs')
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
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT first_name, last_name, email, phone
                FROM users
                ORDER BY last_name, first_name
            ''')
            
            players = []
            for row in cursor.fetchall():
                players.append({
                    'name': f"{row[0]} {row[1]}",
                    'email': row[2],
                    'phone': row[3] if row[3] else 'Not provided'
                })
            
            conn.close()
            return jsonify(players)
        except Exception as e:
            print(f"Error getting player contact info: {str(e)}")
            return jsonify({'error': str(e)}), 500 