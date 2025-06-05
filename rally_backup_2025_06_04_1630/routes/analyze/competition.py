from flask import jsonify, session
import pandas as pd
from database import get_db
from datetime import datetime
import logging
from ..act.auth import login_required

logger = logging.getLogger(__name__)

def get_player_court_stats(player_name):
    """Get player's performance statistics by court"""
    try:
        with get_db() as conn:
            # Get all matches for the player
            matches_df = pd.read_sql_query('''
                SELECT * FROM matches 
                WHERE player1 = %s OR player2 = %s OR player3 = %s OR player4 = %s
                ORDER BY date DESC
            ''', conn, params=[player_name] * 4)
            
            if matches_df.empty:
                return {
                    'error': 'No match data found',
                    'matches_played': 0
                }
                
            # Calculate overall stats
            total_matches = len(matches_df)
            wins = len(matches_df[
                ((matches_df['player1'] == player_name) & (matches_df['team1_won'] == 1)) |
                ((matches_df['player2'] == player_name) & (matches_df['team1_won'] == 1)) |
                ((matches_df['player3'] == player_name) & (matches_df['team2_won'] == 1)) |
                ((matches_df['player4'] == player_name) & (matches_df['team2_won'] == 1))
            ])
            
            # Calculate court-specific stats
            court_stats = {}
            for court in matches_df['court'].unique():
                court_matches = matches_df[matches_df['court'] == court]
                court_wins = len(court_matches[
                    ((court_matches['player1'] == player_name) & (court_matches['team1_won'] == 1)) |
                    ((court_matches['player2'] == player_name) & (court_matches['team1_won'] == 1)) |
                    ((court_matches['player3'] == player_name) & (court_matches['team2_won'] == 1)) |
                    ((court_matches['player4'] == player_name) & (court_matches['team2_won'] == 1))
                ])
                
                court_stats[court] = {
                    'matches': len(court_matches),
                    'wins': court_wins,
                    'losses': len(court_matches) - court_wins,
                    'win_rate': round((court_wins / len(court_matches) * 100), 1)
                }
            
            return {
                'player_name': player_name,
                'total_matches': total_matches,
                'total_wins': wins,
                'total_losses': total_matches - wins,
                'overall_win_rate': round((wins / total_matches * 100), 1),
                'court_stats': court_stats
            }
            
    except Exception as e:
        logger.error(f"Error getting player court stats: {str(e)}")
        return {'error': str(e)}

def get_team_competition_stats(team_id):
    """Get comprehensive competition statistics for a team"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get team info
            cursor.execute('SELECT * FROM teams WHERE id = %s', (team_id,))
            team = cursor.fetchone()
            
            if not team:
                return {'error': 'Team not found'}
                
            team_dict = {
                'id': team[0],
                'name': team[1],
                'club': team[2],
                'series': team[3]
            }
            
            # Get team matches
            matches_df = pd.read_sql_query('''
                SELECT * FROM matches 
                WHERE team1_id = %s OR team2_id = %s
                ORDER BY date DESC
            ''', conn, params=[team_id, team_id])
            
            if matches_df.empty:
                return {
                    'team': team_dict,
                    'error': 'No match data found',
                    'matches_played': 0
                }
                
            # Calculate overall stats
            total_matches = len(matches_df)
            wins = len(matches_df[
                ((matches_df['team1_id'] == team_id) & (matches_df['team1_won'] == 1)) |
                ((matches_df['team2_id'] == team_id) & (matches_df['team2_won'] == 1))
            ])
            
            # Calculate opponent stats
            opponent_stats = {}
            for _, match in matches_df.iterrows():
                opponent_id = match['team2_id'] if match['team1_id'] == team_id else match['team1_id']
                opponent_name = match['team2_name'] if match['team1_id'] == team_id else match['team1_name']
                won = (match['team1_id'] == team_id and match['team1_won']) or (match['team2_id'] == team_id and match['team2_won'])
                
                if opponent_id not in opponent_stats:
                    opponent_stats[opponent_id] = {
                        'name': opponent_name,
                        'matches': 0,
                        'wins': 0
                    }
                
                opponent_stats[opponent_id]['matches'] += 1
                if won:
                    opponent_stats[opponent_id]['wins'] += 1
            
            # Format opponent stats for response
            formatted_opponent_stats = []
            for stats in opponent_stats.values():
                formatted_opponent_stats.append({
                    'name': stats['name'],
                    'matches_played': stats['matches'],
                    'wins': stats['wins'],
                    'losses': stats['matches'] - stats['wins'],
                    'win_rate': round((stats['wins'] / stats['matches'] * 100), 1)
                })
            
            return {
                'team': team_dict,
                'total_matches': total_matches,
                'total_wins': wins,
                'total_losses': total_matches - wins,
                'win_rate': round((wins / total_matches * 100), 1),
                'opponent_stats': sorted(formatted_opponent_stats, key=lambda x: x['matches_played'], reverse=True)
            }
            
    except Exception as e:
        logger.error(f"Error getting team competition stats: {str(e)}")
        return {'error': str(e)}

def init_routes(app):
    @app.route('/api/player-court-stats/<player_name>')
    def player_court_stats(player_name):
        try:
            stats = get_player_court_stats(player_name)
            
            if 'error' in stats:
                return jsonify(stats), 404 if stats['error'] == 'No match data found' else 500
                
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error serving player court stats: {str(e)}")
            return jsonify({'error': 'Failed to get player court stats'}), 500

    @app.route('/api/research-team')
    @login_required
    def research_team():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            team_id = request.args.get('team_id')
            if not team_id:
                return jsonify({'error': 'Team ID is required'}), 400
                
            stats = get_team_competition_stats(team_id)
            
            if 'error' in stats:
                return jsonify(stats), 404 if stats['error'] == 'Team not found' else 500
                
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error researching team: {str(e)}")
            return jsonify({'error': 'Failed to research team'}), 500

    return app 