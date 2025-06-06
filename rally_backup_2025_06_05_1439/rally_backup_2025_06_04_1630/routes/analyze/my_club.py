from flask import jsonify, session
import pandas as pd
from database import get_db
from datetime import datetime
import logging
from ..act.auth import login_required

logger = logging.getLogger(__name__)

def get_recent_matches_for_user_club(user):
    """Get recent matches for the user's club"""
    try:
        with get_db() as conn:
            matches_df = pd.read_sql_query('''
                SELECT * FROM matches 
                WHERE club = %s
                ORDER BY date DESC, time DESC
                LIMIT 50
            ''', conn, params=[user['club']])
            
            if matches_df.empty:
                return []
                
            recent_matches = []
            for _, match in matches_df.iterrows():
                recent_matches.append({
                    'date': match['date'],
                    'time': match['time'],
                    'court': match['court'],
                    'team1': {
                        'name': match['team1_name'],
                        'players': [match['player1'], match['player2']],
                        'score': match['team1_score']
                    },
                    'team2': {
                        'name': match['team2_name'],
                        'players': [match['player3'], match['player4']],
                        'score': match['team2_score']
                    },
                    'winner': 'team1' if match['team1_won'] else 'team2'
                })
                
            return recent_matches
            
    except Exception as e:
        logger.error(f"Error getting recent club matches: {str(e)}")
        return []

def calculate_player_streaks(matches, club_name):
    """Calculate winning and losing streaks for players"""
    try:
        player_matches = {}
        
        for _, match in matches.iterrows():
            players = [match['player1'], match['player2'], match['player3'], match['player4']]
            
            for player in players:
                if player not in player_matches:
                    player_matches[player] = []
                    
                is_team1 = player in [match['player1'], match['player2']]
                won = (is_team1 and match['team1_won']) or (not is_team1 and match['team2_won'])
                
                player_matches[player].append({
                    'date': match['date'],
                    'won': won
                })
                
        streaks = []
        for player, matches in player_matches.items():
            if len(matches) < 3:  # Require at least 3 matches for a streak
                continue
                
            current_streak = 1
            max_win_streak = 1
            max_loss_streak = 1
            
            for i in range(1, len(matches)):
                if matches[i]['won'] == matches[i-1]['won']:
                    current_streak += 1
                    if matches[i]['won']:
                        max_win_streak = max(max_win_streak, current_streak)
                    else:
                        max_loss_streak = max(max_loss_streak, current_streak)
                else:
                    current_streak = 1
                    
            streaks.append({
                'player': player,
                'max_win_streak': max_win_streak,
                'max_loss_streak': max_loss_streak,
                'current_streak': current_streak,
                'current_streak_type': 'win' if matches[-1]['won'] else 'loss'
            })
            
        return sorted(streaks, key=lambda x: (x['max_win_streak'], -x['max_loss_streak']), reverse=True)
        
    except Exception as e:
        logger.error(f"Error calculating player streaks: {str(e)}")
        return []

def get_club_analysis(user):
    """Get comprehensive club analysis"""
    try:
        with get_db() as conn:
            # Get all matches for the club
            matches_df = pd.read_sql_query('''
                SELECT * FROM matches 
                WHERE club = %s
                ORDER BY date DESC
            ''', conn, params=[user['club']])
            
            # Get all teams in the club
            teams_df = pd.read_sql_query('''
                SELECT * FROM teams 
                WHERE club = %s
            ''', conn, params=[user['club']])

        if matches_df.empty:
            return {
                'error': 'No match data found',
                'matches_played': 0,
                'teams': 0
            }

        # Basic stats
        total_matches = len(matches_df)
        total_teams = len(teams_df)
        
        # Court usage
        court_stats = matches_df['court'].value_counts().to_dict()
        
        # Time of day stats
        matches_df['hour'] = pd.to_datetime(matches_df['time']).dt.hour
        time_stats = {
            'morning': len(matches_df[matches_df['hour'] < 12]),
            'afternoon': len(matches_df[(matches_df['hour'] >= 12) & (matches_df['hour'] < 17)]),
            'evening': len(matches_df[matches_df['hour'] >= 17])
        }
        
        # Player streaks
        streaks = calculate_player_streaks(matches_df, user['club'])
        
        # Recent matches
        recent_matches = get_recent_matches_for_user_club(user)

        return {
            'club_name': user['club'],
            'total_matches': total_matches,
            'total_teams': total_teams,
            'court_stats': court_stats,
            'time_stats': time_stats,
            'player_streaks': streaks[:10],  # Top 10 streaks
            'recent_matches': recent_matches[:5]  # Last 5 matches
        }
    except Exception as e:
        logger.error(f"Error in club analysis: {str(e)}")
        return {'error': 'Failed to analyze club data'}

def init_routes(app):
    @app.route('/mobile/my-club')
    @login_required
    def my_club():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user = session['user']
            analysis = get_club_analysis(user)
            
            if 'error' in analysis:
                return jsonify(analysis), 404 if analysis['error'] == 'No match data found' else 500
                
            return jsonify({
                'user': user,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Error serving club analysis: {str(e)}")
            return jsonify({'error': 'Failed to serve club analysis'}), 500

    @app.route('/api/win-streaks')
    @login_required
    def get_win_streaks():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user = session['user']
            
            # Get matches for the club
            with get_db() as conn:
                matches_df = pd.read_sql_query('''
                    SELECT * FROM matches 
                    WHERE club = %s
                    ORDER BY date DESC
                ''', conn, params=[user['club']])
            
            if matches_df.empty:
                return jsonify({'streaks': []})
                
            streaks = calculate_player_streaks(matches_df, user['club'])
            return jsonify({'streaks': streaks})
            
        except Exception as e:
            logger.error(f"Error getting win streaks: {str(e)}")
            return jsonify({'error': 'Failed to get win streaks'}), 500

    return app 