from flask import jsonify, session
import pandas as pd
import sqlite3
from datetime import datetime
import logging
from ..act.auth import login_required

logger = logging.getLogger(__name__)

def get_player_court_stats(player_name):
    """Get player's performance statistics by court"""
    try:
        conn = sqlite3.connect('data/paddlepro.db')
        
        # Get all matches for the player
        matches_df = pd.read_sql_query('''
            SELECT * FROM matches 
            WHERE player1 = ? OR player2 = ? OR player3 = ? OR player4 = ?
            ORDER BY date DESC
        ''', conn, params=[player_name] * 4)
        conn.close()
        
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
            court_total = len(court_matches)
            court_wins = len(court_matches[
                ((court_matches['player1'] == player_name) & (court_matches['team1_won'] == 1)) |
                ((court_matches['player2'] == player_name) & (court_matches['team1_won'] == 1)) |
                ((court_matches['player3'] == player_name) & (court_matches['team2_won'] == 1)) |
                ((court_matches['player4'] == player_name) & (court_matches['team2_won'] == 1))
            ])
            
            court_stats[court] = {
                'matches': court_total,
                'wins': court_wins,
                'losses': court_total - court_wins,
                'win_rate': round((court_wins / court_total * 100), 1) if court_total > 0 else 0
            }
            
        # Calculate partner stats
        partner_stats = {}
        for _, match in matches_df.iterrows():
            is_team1 = player_name in [match['player1'], match['player2']]
            partner = match['player2'] if player_name == match['player1'] else \
                     match['player1'] if player_name == match['player2'] else \
                     match['player4'] if player_name == match['player3'] else \
                     match['player3']
                     
            if partner not in partner_stats:
                partner_stats[partner] = {
                    'matches': 0,
                    'wins': 0
                }
                
            partner_stats[partner]['matches'] += 1
            if (is_team1 and match['team1_won']) or (not is_team1 and match['team2_won']):
                partner_stats[partner]['wins'] += 1
                
        # Calculate win rates and sort partners
        for stats in partner_stats.values():
            stats['win_rate'] = round((stats['wins'] / stats['matches'] * 100), 1)
            
        sorted_partners = sorted(
            partner_stats.items(),
            key=lambda x: (x[1]['win_rate'], x[1]['matches']),
            reverse=True
        )
        
        # Get recent matches
        recent_matches = []
        for _, match in matches_df.head(5).iterrows():
            is_team1 = player_name in [match['player1'], match['player2']]
            won = (is_team1 and match['team1_won']) or (not is_team1 and match['team2_won'])
            
            recent_matches.append({
                'date': match['date'],
                'court': match['court'],
                'partner': match['player2'] if player_name == match['player1'] else \
                          match['player1'] if player_name == match['player2'] else \
                          match['player4'] if player_name == match['player3'] else \
                          match['player3'],
                'opponents': [
                    match['player3'] if is_team1 else match['player1'],
                    match['player4'] if is_team1 else match['player2']
                ],
                'result': 'W' if won else 'L',
                'score': f"{match['team1_score']}-{match['team2_score']}"
            })

        return {
            'player_name': player_name,
            'total_matches': total_matches,
            'total_wins': wins,
            'total_losses': total_matches - wins,
            'overall_win_rate': round((wins / total_matches * 100), 1) if total_matches > 0 else 0,
            'court_stats': court_stats,
            'partner_stats': [
                {
                    'partner': partner,
                    'stats': stats
                }
                for partner, stats in sorted_partners[:5]  # Top 5 partners
            ],
            'recent_matches': recent_matches
        }
    except Exception as e:
        logger.error(f"Error getting player court stats: {str(e)}")
        return {'error': 'Failed to get player statistics'}

def get_team_competition_stats(team_id):
    """Get comprehensive competition statistics for a team"""
    try:
        conn = sqlite3.connect('data/paddlepro.db')
        
        # Get team info
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM teams WHERE id = ?', (team_id,))
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
            WHERE team1_id = ? OR team2_id = ?
            ORDER BY date DESC
        ''', conn, params=[team_id, team_id])
        
        conn.close()
        
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
            is_team1 = match['team1_id'] == team_id
            opponent_id = match['team2_id'] if is_team1 else match['team1_id']
            opponent_name = match['team2_name'] if is_team1 else match['team1_name']
            won = (is_team1 and match['team1_won']) or (not is_team1 and match['team2_won'])
            
            if opponent_id not in opponent_stats:
                opponent_stats[opponent_id] = {
                    'name': opponent_name,
                    'matches': 0,
                    'wins': 0
                }
                
            opponent_stats[opponent_id]['matches'] += 1
            if won:
                opponent_stats[opponent_id]['wins'] += 1
                
        # Calculate win rates and sort opponents
        for stats in opponent_stats.values():
            stats['win_rate'] = round((stats['wins'] / stats['matches'] * 100), 1)
            
        sorted_opponents = sorted(
            opponent_stats.items(),
            key=lambda x: (x[1]['win_rate'], x[1]['matches']),
            reverse=True
        )
        
        # Get recent matches
        recent_matches = []
        for _, match in matches_df.head(5).iterrows():
            is_team1 = match['team1_id'] == team_id
            won = (is_team1 and match['team1_won']) or (not is_team1 and match['team2_won'])
            
            recent_matches.append({
                'date': match['date'],
                'court': match['court'],
                'opponent': match['team2_name'] if is_team1 else match['team1_name'],
                'result': 'W' if won else 'L',
                'score': f"{match['team1_score']}-{match['team2_score']}"
            })

        return {
            'team': team_dict,
            'total_matches': total_matches,
            'total_wins': wins,
            'total_losses': total_matches - wins,
            'overall_win_rate': round((wins / total_matches * 100), 1) if total_matches > 0 else 0,
            'opponent_stats': [
                {
                    'opponent_id': opponent_id,
                    'stats': stats
                }
                for opponent_id, stats in sorted_opponents
            ],
            'recent_matches': recent_matches
        }
    except Exception as e:
        logger.error(f"Error getting team competition stats: {str(e)}")
        return {'error': 'Failed to get team statistics'}

def init_routes(app):
    @app.route('/api/player-court-stats/<player_name>')
    @login_required
    def player_court_stats(player_name):
        try:
            stats = get_player_court_stats(player_name)
            
            if 'error' in stats:
                return jsonify(stats), 404 if stats['error'] == 'No match data found' else 500
                
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error serving player court stats: {str(e)}")
            return jsonify({'error': 'Failed to get player statistics'}), 500

    @app.route('/api/team-stats/<team_id>')
    @login_required
    def get_team_stats(team_id):
        try:
            stats = get_team_competition_stats(team_id)
            
            if 'error' in stats:
                return jsonify(stats), 404 if stats['error'] in ['Team not found', 'No match data found'] else 500
                
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error serving team stats: {str(e)}")
            return jsonify({'error': 'Failed to get team statistics'}), 500

    return app 