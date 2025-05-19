from flask import jsonify, session
import pandas as pd
import sqlite3
from datetime import datetime
import logging
from ..act.auth import login_required

logger = logging.getLogger(__name__)

def normalize(name):
    """Normalize player name for consistent matching"""
    return name.lower().strip()

def parse_date(date_str):
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        try:
            return datetime.strptime(date_str, '%m/%d/%Y')
        except:
            return None

def get_player_analysis(user):
    """Get comprehensive analysis of a player's performance"""
    try:
        # Read player data
        df = pd.read_csv('data/all_tennaqua_players.csv')
        
        # Get matches for the player
        conn = sqlite3.connect('data/paddlepro.db')
        matches_df = pd.read_sql_query('''
            SELECT * FROM matches 
            WHERE player1 = ? OR player2 = ? OR player3 = ? OR player4 = ?
        ''', conn, params=[user['name']] * 4)
        conn.close()

        if matches_df.empty:
            return {
                'error': 'No match data found',
                'matches_played': 0,
                'win_rate': 0,
                'preferred_position': 'Unknown',
                'recent_form': []
            }

        # Calculate basic stats
        total_matches = len(matches_df)
        wins = len(matches_df[
            ((matches_df['player1'] == user['name']) & (matches_df['team1_won'] == 1)) |
            ((matches_df['player2'] == user['name']) & (matches_df['team1_won'] == 1)) |
            ((matches_df['player3'] == user['name']) & (matches_df['team2_won'] == 1)) |
            ((matches_df['player4'] == user['name']) & (matches_df['team2_won'] == 1))
        ])
        
        # Calculate position preferences
        position_counts = {
            'forehand': len(matches_df[
                (matches_df['player1'] == user['name']) |
                (matches_df['player3'] == user['name'])
            ]),
            'backhand': len(matches_df[
                (matches_df['player2'] == user['name']) |
                (matches_df['player4'] == user['name'])
            ])
        }
        
        # Get recent form (last 5 matches)
        recent_matches = matches_df.sort_values('date', ascending=False).head(5)
        recent_form = []
        
        for _, match in recent_matches.iterrows():
            is_team1 = match['player1'] == user['name'] or match['player2'] == user['name']
            won = (is_team1 and match['team1_won']) or (not is_team1 and match['team2_won'])
            recent_form.append({
                'date': match['date'],
                'result': 'W' if won else 'L',
                'score': f"{match['team1_score']}-{match['team2_score']}"
            })

        return {
            'matches_played': total_matches,
            'wins': wins,
            'losses': total_matches - wins,
            'win_rate': round((wins / total_matches) * 100, 1) if total_matches > 0 else 0,
            'preferred_position': 'Forehand' if position_counts['forehand'] > position_counts['backhand'] else 'Backhand',
            'position_stats': position_counts,
            'recent_form': recent_form
        }
    except Exception as e:
        logger.error(f"Error in player analysis: {str(e)}")
        return {'error': 'Failed to analyze player data'}

def init_routes(app):
    @app.route('/api/research-me')
    @login_required
    def research_me():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user = session['user']
            analysis = get_player_analysis(user)
            
            if 'error' in analysis:
                return jsonify(analysis), 404 if analysis['error'] == 'No match data found' else 500
                
            return jsonify(analysis)
            
        except Exception as e:
            logger.error(f"Error researching player: {str(e)}")
            return jsonify({'error': 'Failed to research player'}), 500

    @app.route('/mobile/analyze-me')
    @login_required
    def serve_mobile_analyze_me():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user = session['user']
            analysis = get_player_analysis(user)
            
            return jsonify({
                'user': user,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Error serving mobile analysis: {str(e)}")
            return jsonify({'error': 'Failed to serve mobile analysis'}), 500

    return app 