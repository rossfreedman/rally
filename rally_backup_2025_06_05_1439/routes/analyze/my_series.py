from flask import jsonify, session
import pandas as pd
from database import get_db
from datetime import datetime
import logging
from ..act.auth import login_required

logger = logging.getLogger(__name__)

def get_series_stats(series_name):
    """Get comprehensive statistics for a series"""
    try:
        # Connect to database
        with get_db() as conn:
            # Get all matches in the series
            matches_df = pd.read_sql_query('''
                SELECT * FROM matches 
                WHERE series = %s
                ORDER BY date DESC
            ''', conn, params=[series_name])
            
            # Get all teams in the series
            teams_df = pd.read_sql_query('''
                SELECT * FROM teams 
                WHERE series = %s
            ''', conn, params=[series_name])

        if matches_df.empty or teams_df.empty:
            return {
                'error': 'No data found for series',
                'matches_played': 0,
                'teams': 0
            }

        # Calculate series stats
        total_matches = len(matches_df)
        total_teams = len(teams_df)
        
        # Calculate team rankings
        team_stats = {}
        for _, team in teams_df.iterrows():
            team_matches = matches_df[
                (matches_df['team1_id'] == team['id']) |
                (matches_df['team2_id'] == team['id'])
            ]
            
            wins = len(team_matches[
                ((team_matches['team1_id'] == team['id']) & (team_matches['team1_won'] == 1)) |
                ((team_matches['team2_id'] == team['id']) & (team_matches['team2_won'] == 1))
            ])
            
            team_stats[team['name']] = {
                'matches_played': len(team_matches),
                'wins': wins,
                'losses': len(team_matches) - wins,
                'win_rate': round((wins / len(team_matches) * 100), 1) if len(team_matches) > 0 else 0
            }
        
        # Sort teams by win rate
        sorted_teams = sorted(
            team_stats.items(),
            key=lambda x: (x[1]['win_rate'], x[1]['matches_played']),
            reverse=True
        )
        
        # Calculate court usage
        court_stats = matches_df['court'].value_counts().to_dict()
        
        # Calculate time of day stats
        matches_df['hour'] = pd.to_datetime(matches_df['time']).dt.hour
        time_stats = {
            'morning': len(matches_df[matches_df['hour'] < 12]),
            'afternoon': len(matches_df[(matches_df['hour'] >= 12) & (matches_df['hour'] < 17)]),
            'evening': len(matches_df[matches_df['hour'] >= 17])
        }
        
        # Get recent matches
        recent_matches = matches_df.head(5).apply(lambda x: {
            'date': x['date'],
            'team1': x['team1_name'],
            'team2': x['team2_name'],
            'score': f"{x['team1_score']}-{x['team2_score']}"
        }, axis=1).tolist()

        return {
            'series_name': series_name,
            'total_matches': total_matches,
            'total_teams': total_teams,
            'team_rankings': [
                {
                    'team_name': team_name,
                    'stats': stats
                }
                for team, stats in rankings
            ],
            'court_stats': court_stats,
            'time_stats': time_stats,
            'recent_matches': recent_matches
        }
    except Exception as e:
        logger.error(f"Error in series analysis: {str(e)}")
        return {'error': 'Failed to analyze series data'}

def init_routes(app):
    @app.route('/api/series-stats')
    @login_required
    def get_series_statistics():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            series = session['user'].get('series')
            if not series:
                return jsonify({'error': 'No series selected'}), 400
                
            stats = get_series_stats(series)
            
            if 'error' in stats:
                return jsonify(stats), 404 if stats['error'] == 'No data found for series' else 500
                
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"Error getting series stats: {str(e)}")
            return jsonify({'error': 'Failed to get series stats'}), 500

    @app.route('/mobile/my-series')
    @login_required
    def serve_mobile_my_series():
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            series = session['user'].get('series')
            if not series:
                return jsonify({'error': 'No series selected'}), 400
                
            stats = get_series_stats(series)
            
            return jsonify({
                'user': session['user'],
                'series_stats': stats
            })
            
        except Exception as e:
            logger.error(f"Error serving mobile series analysis: {str(e)}")
            return jsonify({'error': 'Failed to serve mobile series analysis'}), 500

    return app