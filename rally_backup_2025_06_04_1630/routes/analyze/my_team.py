from flask import jsonify, session
import pandas as pd
from database import get_db
import logging
from ..act.auth import login_required

logger = logging.getLogger(__name__)

def calculate_team_analysis(team_stats, team_matches, team):
    """Calculate comprehensive team analysis"""
    try:
        # Basic team stats
        total_matches = len(team_matches)
        wins = len(team_matches[team_matches['team1_won'] == 1])
        losses = total_matches - wins
        
        # Calculate court preferences
        court_stats = team_matches['court'].value_counts().to_dict()
        preferred_court = max(court_stats.items(), key=lambda x: x[1])[0] if court_stats else 'Unknown'
        
        # Calculate time of day preferences
        team_matches['hour'] = pd.to_datetime(team_matches['time']).dt.hour
        time_stats = {
            'morning': len(team_matches[team_matches['hour'] < 12]),
            'afternoon': len(team_matches[(team_matches['hour'] >= 12) & (team_matches['hour'] < 17)]),
            'evening': len(team_matches[team_matches['hour'] >= 17])
        }
        preferred_time = max(time_stats.items(), key=lambda x: x[1])[0]
        
        # Calculate player combinations
        player_combinations = []
        for _, match in team_matches.iterrows():
            combo = sorted([match['player1'], match['player2']])
            player_combinations.append(tuple(combo))
        
        combo_stats = pd.Series(player_combinations).value_counts().head(3).to_dict()
        top_combinations = [
            {'players': list(combo), 'matches': count}
            for combo, count in combo_stats.items()
        ]
        
        # Calculate recent form (last 5 matches)
        recent_matches = team_matches.sort_values('date', ascending=False).head(5)
        recent_form = []
        
        for _, match in recent_matches.iterrows():
            recent_form.append({
                'date': match['date'],
                'result': 'W' if match['team1_won'] else 'L',
                'score': f"{match['team1_score']}-{match['team2_score']}",
                'opponent': match['team2_name']
            })

        return {
            'team_name': team['name'],
            'matches_played': total_matches,
            'wins': wins,
            'losses': losses,
            'win_rate': round((wins / total_matches) * 100, 1) if total_matches > 0 else 0,
            'court_stats': court_stats,
            'preferred_court': preferred_court,
            'time_stats': time_stats,
            'preferred_time': preferred_time,
            'top_combinations': top_combinations,
            'recent_form': recent_form
        }
    except Exception as e:
        logger.error(f"Error in team analysis calculation: {str(e)}")
        return {'error': 'Failed to calculate team analysis'}

def get_team_matches(team_id):
    """Get all matches for a team"""
    try:
        with get_db() as conn:
            matches_df = pd.read_sql_query('''
                SELECT * FROM matches 
                WHERE team1_id = %s OR team2_id = %s
                ORDER BY date DESC
            ''', conn, params=[team_id, team_id])
            return matches_df
    except Exception as e:
        logger.error(f"Error getting team matches: {str(e)}")
        return pd.DataFrame()

def get_team_stats(team_id):
    """Get team statistics"""
    try:
        with get_db() as conn:
            stats_df = pd.read_sql_query('''
                SELECT * FROM team_stats 
                WHERE team_id = %s
            ''', conn, params=[team_id])
            return stats_df
    except Exception as e:
        logger.error(f"Error getting team stats: {str(e)}")
        return pd.DataFrame()

def init_routes(app):
    @app.route('/api/research-my-team')
    @login_required
    def research_my_team():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            # Get user's team
            with get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT t.* FROM teams t
                    JOIN team_players tp ON t.id = tp.team_id
                    WHERE tp.player_email = %s
                ''', (session['user']['email'],))
                
                team = cursor.fetchone()
            
            if not team:
                return jsonify({'error': 'No team found'}), 404
                
            team_dict = {
                'id': team[0],
                'name': team[1],
                'club': team[2],
                'series': team[3]
            }
            
            # Get team matches and stats
            team_matches = get_team_matches(team_dict['id'])
            team_stats = get_team_stats(team_dict['id'])
            
            if team_matches.empty:
                return jsonify({
                    'team': team_dict,
                    'matches_played': 0,
                    'win_rate': 0,
                    'recent_form': []
                })
            
            # Calculate analysis
            analysis = calculate_team_analysis(team_stats, team_matches, team_dict)
            
            return jsonify({
                'team': team_dict,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Error researching team: {str(e)}")
            return jsonify({'error': 'Failed to research team'}), 500

    @app.route('/mobile/my-team')
    @login_required
    def serve_mobile_my_team():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            # Get user's team
            with get_db() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT t.* FROM teams t
                    JOIN team_players tp ON t.id = tp.team_id
                    WHERE tp.player_email = %s
                ''', (session['user']['email'],))
                
                team = cursor.fetchone()
            
            if not team:
                return jsonify({'error': 'No team found'}), 404
                
            team_dict = {
                'id': team[0],
                'name': team[1],
                'club': team[2],
                'series': team[3]
            }
            
            # Get team matches and stats
            team_matches = get_team_matches(team_dict['id'])
            team_stats = get_team_stats(team_dict['id'])
            
            # Calculate analysis
            analysis = calculate_team_analysis(team_stats, team_matches, team_dict)
            
            return jsonify({
                'team': team_dict,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Error serving mobile team analysis: {str(e)}")
            return jsonify({'error': 'Failed to serve mobile team analysis'}), 500

    return app 