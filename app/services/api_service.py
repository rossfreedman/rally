"""
API Service Module

This module contains business logic for API routes.
Functions handle data processing, database queries, and response formatting for API endpoints.
"""

import json
import os
import traceback
from flask import jsonify, request, session
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from utils.series_matcher import series_match, normalize_series_for_storage

def calculate_points_progression(series_stats, matches_path):
    """Calculate cumulative points progression over time for teams in the series"""
    try:
        if not os.path.exists(matches_path):
            return {}
            
        with open(matches_path, 'r') as f:
            all_matches = json.load(f)
        
        # Get team names from series stats
        team_names = [team['team'] for team in series_stats]
        if not team_names:
            return {}
        
        # Filter matches for teams in this series
        series_matches = []
        for match in all_matches:
            home_team = match.get('Home Team', '')
            away_team = match.get('Away Team', '')
            if home_team in team_names or away_team in team_names:
                series_matches.append(match)
        
        # Sort matches by date
        from datetime import datetime
        def parse_date(date_str):
            try:
                # Handle different date formats
                if '-' in date_str:
                    return datetime.strptime(date_str, '%d-%b-%y')
                return datetime.strptime(date_str, '%m/%d/%Y')
            except:
                return datetime.now()
        
        series_matches.sort(key=lambda m: parse_date(m.get('Date', '')))
        
        # Calculate cumulative points for each team over time
        team_progression = {}
        team_points = {}
        match_weeks = []
        
        # Initialize team points
        for team_name in team_names:
            team_progression[team_name] = []
            team_points[team_name] = 0
        
        # Group matches by week (approximate)
        current_week = 0
        last_date = None
        week_matches = 0
        
        for i, match in enumerate(series_matches):
            match_date = parse_date(match.get('Date', ''))
            
            # Check if we've moved to a new week (7+ days difference or every 12 matches)
            if (last_date and (match_date - last_date).days >= 7) or week_matches >= 12:
                current_week += 1
                week_matches = 0
                # Record current points for all teams at end of week
                if current_week <= len(match_weeks):
                    match_weeks.append(f"Week {current_week}")
                    for team_name in team_names:
                        team_progression[team_name].append(team_points[team_name])
            
            home_team = match.get('Home Team', '')
            away_team = match.get('Away Team', '')
            winner = match.get('Winner', '')
            
            # Simplified points system based on line wins
            # Each match represents one line, winner gets 1 point
            if home_team in team_names:
                if winner == 'home':
                    team_points[home_team] += 1
            
            if away_team in team_names:
                if winner == 'away':
                    team_points[away_team] += 1
            
            last_date = match_date
            week_matches += 1
        
        # Add final week if we have remaining matches
        if week_matches > 0:
            match_weeks.append(f"Week {current_week + 1}")
            for team_name in team_names:
                team_progression[team_name].append(team_points[team_name])
        
        return {
            'weeks': match_weeks,
            'teams': team_progression
        }
        
    except Exception as e:
        print(f"Error calculating points progression: {str(e)}")
        return {}

def get_series_stats_data():
    """Get series statistics data - extracted from working backup implementation"""
    try:
        # Get the project root directory for file paths
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        stats_path = os.path.join(project_root, 'data', 'leagues', 'all', 'series_stats.json')
        matches_path = os.path.join(project_root, 'data', 'leagues', 'all', 'match_history.json')
        
        if not os.path.exists(stats_path):
            return jsonify({'error': 'Stats file not found'}), 404
            
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
            
        # Get the requested team from query params
        requested_team = request.args.get('team')
        
        if requested_team:
            team_stats = next((team for team in all_stats if team['team'] == requested_team), None)
            if not team_stats:
                return jsonify({'error': 'Team not found'}), 404

            # Format the response with just the team analysis data
            stats_data = {
                'team_analysis': {
                    'overview': {
                        'points': team_stats['points'],
                        'match_record': f"{team_stats['matches']['won']}-{team_stats['matches']['lost']}",
                        'match_win_rate': team_stats['matches']['percentage'],
                        'line_win_rate': team_stats['lines']['percentage'],
                        'set_win_rate': team_stats['sets']['percentage'],
                        'game_win_rate': team_stats['games']['percentage']
                    }
                }
            }

            # Add match patterns if matches file exists
            if os.path.exists(matches_path):
                with open(matches_path, 'r') as f:
                    matches = json.load(f)
                    
                # Initialize court stats
                court_stats = {
                    'court1': {'wins': 0, 'losses': 0, 'key_players': []},
                    'court2': {'wins': 0, 'losses': 0, 'key_players': []},
                    'court3': {'wins': 0, 'losses': 0, 'key_players': []},
                    'court4': {'wins': 0, 'losses': 0, 'key_players': []}
                }
                
                player_performance = {}
                
                # Group matches by date and team
                team_matches = {}
                for match in matches:
                    if match['Home Team'] == requested_team or match['Away Team'] == requested_team:
                        date = match['Date']
                        if date not in team_matches:
                            team_matches[date] = []
                        team_matches[date].append(match)
                
                # Process each match day
                for date, day_matches in team_matches.items():
                    # Sort matches to ensure consistent court assignment
                    day_matches.sort(key=lambda x: (x['Date'], x['Home Team'], x['Away Team']))
                    
                    # Process each match with its court number
                    for court_num, match in enumerate(day_matches, 1):
                        is_home = match['Home Team'] == requested_team
                        court_key = f'court{court_num}'
                        
                        # Determine if this court was won
                        won_court = (is_home and match['Winner'] == 'home') or \
                                  (not is_home and match['Winner'] == 'away')
                        
                        # Update court stats
                        if won_court:
                            court_stats[court_key]['wins'] += 1
                        else:
                            court_stats[court_key]['losses'] += 1
                        
                        # Track player performance
                        players = []
                        if is_home:
                            players = [
                                {'name': match['Home Player 1'], 'team': 'home'},
                                {'name': match['Home Player 2'], 'team': 'home'}
                            ]
                        else:
                            players = [
                                {'name': match['Away Player 1'], 'team': 'away'},
                                {'name': match['Away Player 2'], 'team': 'away'}
                            ]
                        
                        for player in players:
                            if player['name'] not in player_performance:
                                player_performance[player['name']] = {
                                    'courts': {},
                                    'total_wins': 0,
                                    'total_matches': 0
                                }
                            
                            if court_key not in player_performance[player['name']]['courts']:
                                player_performance[player['name']]['courts'][court_key] = {
                                    'wins': 0, 'matches': 0
                                }
                            
                            player_performance[player['name']]['courts'][court_key]['matches'] += 1
                            if won_court:
                                player_performance[player['name']]['courts'][court_key]['wins'] += 1
                                player_performance[player['name']]['total_wins'] += 1
                            player_performance[player['name']]['total_matches'] += 1
                
                # Calculate various metrics
                total_matches = len([match for matches in team_matches.values() for match in matches])
                total_sets_won = 0
                total_sets_played = 0
                three_set_matches = 0
                three_set_wins = 0
                straight_set_wins = 0
                comeback_wins = 0
                
                # Process match statistics
                for matches in team_matches.values():
                    for match in matches:
                        scores = match['Scores'].split(', ')
                        is_home = match['Home Team'] == requested_team
                        won_match = (match['Winner'] == 'home' and is_home) or \
                                  (match['Winner'] == 'away' and not is_home)
                        
                        # Count sets
                        total_sets_played += len(scores)
                        for set_score in scores:
                            home_games, away_games = map(int, set_score.split('-'))
                            if (is_home and home_games > away_games) or \
                               (not is_home and away_games > home_games):
                                total_sets_won += 1
                        
                        # Analyze match patterns
                        if len(scores) == 3:
                            three_set_matches += 1
                            if won_match:
                                three_set_wins += 1
                        elif won_match:
                            straight_set_wins += 1
                        
                        # Check for comebacks
                        if won_match:
                            first_set = scores[0].split('-')
                            first_set_games = list(map(int, first_set))
                            lost_first = (is_home and first_set_games[0] < first_set_games[1]) or \
                                       (not is_home and first_set_games[0] > first_set_games[1])
                            if lost_first:
                                comeback_wins += 1
                
                # Identify key players for each court
                for court_key in court_stats:
                    court_players = []
                    for player, stats in player_performance.items():
                        if court_key in stats['courts'] and stats['courts'][court_key]['matches'] >= 2:
                            win_rate = stats['courts'][court_key]['wins'] / stats['courts'][court_key]['matches']
                            court_players.append({
                                'name': player,
                                'win_rate': win_rate,
                                'matches': stats['courts'][court_key]['matches'],
                                'wins': stats['courts'][court_key]['wins']
                            })
                    
                    # Sort by win rate and take top 2
                    court_players.sort(key=lambda x: x['win_rate'], reverse=True)
                    court_stats[court_key]['key_players'] = court_players[:2]
                
                # Calculate basic team stats
                total_matches = team_stats['matches']['won'] + team_stats['matches']['lost']
                win_rate = team_stats['matches']['won'] / total_matches if total_matches > 0 else 0
                
                # Calculate average points
                total_games = team_stats['games']['won'] + team_stats['games']['lost']
                avg_points_for = team_stats['games']['won'] / total_matches if total_matches > 0 else 0
                avg_points_against = team_stats['games']['lost'] / total_matches if total_matches > 0 else 0
                
                # Calculate consistency rating (based on standard deviation of scores)
                consistency_rating = 8.5  # Placeholder - would calculate from actual score variance
                
                # Calculate strength index (composite of win rate and point differential)
                point_differential = avg_points_for - avg_points_against
                strength_index = (win_rate * 7 + (point_differential / 10) * 3)  # Scale to 0-10
                
                # Get recent form (last 5 matches)
                recent_form = ['W', 'L', 'W', 'W', 'L']  # Placeholder - would get from actual match history
                
                # Format response
                response = {
                    'teamName': requested_team,
                    'wins': team_stats['matches']['won'],
                    'losses': team_stats['matches']['lost'],
                    'winRate': win_rate,
                    'avgPoinsftor': avg_points_for,
                    'avgPointsAgainst': avg_points_against,
                    'consistencyRating': consistency_rating,
                    'strengthIndex': strength_index,
                    'recentForm': recent_form,
                    'dates': ['2025-01-01', '2025-01-15', '2025-02-01', '2025-02-15', '2025-03-01'],  # Placeholder dates
                    'scores': [6, 8, 7, 9, 6],  # Placeholder scores
                    'courtAnalysis': court_stats
                }
                
                return jsonify(response)
            
        # If no team requested, filter stats by user's series
        user = session.get('user')
        if not user or not user.get('series'):
            return jsonify({'error': 'User series not found'}), 400
            
        # Filter stats for the user's series
        series_stats = [team for team in all_stats if team.get('series') == user['series']]
        
        # Calculate points progression over time for the series
        points_progression = calculate_points_progression(series_stats, matches_path)
        
        return jsonify({
            'teams': series_stats,
            'pointsProgression': points_progression
        })
        
    except Exception as e:
        print(f"Error reading series stats: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to read stats file'}), 500

def get_players_by_series_data():
    """Get all players for a specific series, optionally filtered by team and club"""
    try:
        from flask import request, session, jsonify
        import json
        import os
        import traceback
        from utils.series_matcher import series_match, normalize_series_for_storage
        
        # Get series and optional team from query parameters
        series = request.args.get('series')
        team_id = request.args.get('team_id')
        
        if not series:
            return jsonify({'error': 'Series parameter is required'}), 400
            
        print(f"\n=== DEBUG: get_players_by_series ===")
        print(f"Requested series: {series}")
        print(f"Requested team: {team_id}")
        print(f"User series: {session['user'].get('series')}")
        print(f"User club: {session['user'].get('club')}")
        
        # Get project root directory - fix path resolution for modular structure
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)  # app directory
        project_root = os.path.dirname(app_dir)  # rally directory
        
        # Use the user's league to determine the correct data path
        user_league = session['user'].get('league_id', 'APTA').upper()
        if user_league == 'NSTF':
            players_path = os.path.join(project_root, 'data', 'leagues', 'NSTF', 'players.json')
            matches_path = os.path.join(project_root, 'data', 'leagues', 'NSTF', 'match_history.json')
        else:
            # Default to 'all' directory which contains consolidated data
            players_path = os.path.join(project_root, 'data', 'leagues', 'all', 'players.json')
            matches_path = os.path.join(project_root, 'data', 'leagues', 'all', 'match_history.json')
        
        print(f"Players path: {players_path}")
        print(f"Matches path: {matches_path}")
        print(f"Players file exists: {os.path.exists(players_path)}")
        print(f"Matches file exists: {os.path.exists(matches_path)}")
            
        # Load player data
        with open(players_path, 'r') as f:
            all_players = json.load(f)
            
        # Load matches data if team filtering is needed
        team_players = set()
        if team_id and os.path.exists(matches_path):
            try:
                with open(matches_path, 'r') as f:
                    matches = json.load(f)
                # Get all players who have played for this team
                for match in matches:
                    if match.get('Home Team') == team_id:
                        if match.get('Home Player 1'):
                            team_players.add(match['Home Player 1'])
                        if match.get('Home Player 2'):
                            team_players.add(match['Home Player 2'])
                    elif match.get('Away Team') == team_id:
                        if match.get('Away Player 1'):
                            team_players.add(match['Away Player 1'])
                        if match.get('Away Player 2'):
                            team_players.add(match['Away Player 2'])
                print(f"Found {len(team_players)} team players for {team_id}")
            except Exception as e:
                print(f"Warning: Error loading matches data: {str(e)}")
                # Continue without team filtering if matches data can't be loaded
                team_id = None
        
        # Get user's club from session
        user_club = session['user'].get('club')
        
        # Filter players by series, team if specified, and club
        players = []
        for player in all_players:
            # Use our new series matching functionality
            if series_match(player['Series'], series):
                # Create player name in the same format as match data
                player_name = f"{player['First Name']} {player['Last Name']}"
                
                # If team_id is specified, only include players from that team
                if not team_id or player_name in team_players:
                    # Only include players from the same club as the user
                    if player['Club'] == user_club:
                        players.append({
                            'name': player_name,
                            'series': normalize_series_for_storage(player['Series']),  # Normalize series format
                            'rating': str(player['PTI']),
                            'pti': str(player['PTI']),  # Add pti field for compatibility
                            'wins': str(player['Wins']),
                            'losses': str(player['Losses']),
                            'winRate': player['Win %']
                        })
            
        print(f"Found {len(players)} players in {series}{' for team ' + team_id if team_id else ''} and club {user_club}")
        print("=== END DEBUG ===\n")
        return jsonify(players)
        
    except Exception as e:
        print(f"\nERROR getting players for series {series}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def get_team_players_data(team_id):
    """Get team players data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'team_players', 'team_id': team_id})

def test_log_data():
    """Test log data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'test_log'})

def verify_logging_data():
    """Verify logging data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'verify_logging'})

def log_click_data():
    """Log click data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'log_click'})

def research_team_data():
    """Research team data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'research_team'})

def get_player_court_stats_data(player_name):
    """Get player court statistics data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'player_court_stats', 'player_name': player_name})

def research_my_team_data():
    """Research my team data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'research_my_team'})

def research_me_data():
    """Research me data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'research_me'})

def get_win_streaks_data():
    """Get win streaks data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'win_streaks'})

def get_player_streaks_data():
    """Get player streaks data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'player_streaks'})

def get_enhanced_streaks_data():
    """Get enhanced streaks data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({'placeholder': 'enhanced_streaks'})

def find_training_video_data():
    """Find relevant training videos based on user prompt"""
    try:
        from flask import request, jsonify
        import os
        import json
        
        data = request.get_json()
        if not data:
            return jsonify({'videos': [], 'error': 'No data provided'})
            
        user_prompt = data.get('content', '').lower().strip()
        
        if not user_prompt:
            return jsonify({'videos': [], 'video': None})
        
        # Load training guide data
        try:
            # Use current working directory since server.py runs from project root
            guide_path = os.path.join('data', 'leagues', 'apta', 'improve_data', 'complete_platform_tennis_training_guide.json')
            with open(guide_path, 'r', encoding='utf-8') as f:
                training_guide = json.load(f)
        except Exception as e:
            print(f"Error loading training guide: {str(e)}")
            return jsonify({'videos': [], 'video': None, 'error': 'Could not load training guide'})
        
        # Search through training guide sections
        matching_sections = []
        
        def search_sections(data):
            """Search through the training guide sections"""
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and 'Reference Videos' in value:
                        # Calculate relevance based on section title
                        relevance_score = calculate_video_relevance(user_prompt, key.lower())
                        
                        if relevance_score > 0:
                            # Get all videos from Reference Videos
                            videos = value.get('Reference Videos', [])
                            if videos and len(videos) > 0:
                                # Add each video with the section info
                                for video in videos:
                                    matching_sections.append({
                                        'title': key.replace('_', ' ').title(),
                                        'video': video,
                                        'relevance_score': relevance_score
                                    })
        
        def calculate_video_relevance(query, section_title):
            """Calculate relevance score for video matching"""
            score = 0
            query_words = query.split()
            
            # Exact match in section title gets highest score
            if query == section_title:
                score += 200
            
            # Query appears as a word in the section title
            if query in section_title.split():
                score += 150
            
            # Query appears anywhere in section title
            if query in section_title:
                score += 100
            
            # Partial word matches in section title
            for word in query_words:
                if word in section_title:
                    score += 50
            
            return score
        
        # Perform the search
        search_sections(training_guide)
        
        # Sort by relevance score and return all relevant matches
        if matching_sections:
            matching_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Filter to only include videos with sufficient relevance
            relevant_videos = []
            for match in matching_sections:
                if match['relevance_score'] >= 50:  # Minimum threshold for relevance
                    relevant_videos.append({
                        'title': match['video']['title'],
                        'url': match['video']['url'],
                        'topic': match['title'],
                        'relevance_score': match['relevance_score']
                    })
            
            # Return both formats for backward compatibility
            response = {'videos': relevant_videos}
            
            # Include the best video as 'video' for backward compatibility
            if relevant_videos:
                response['video'] = relevant_videos[0]  # Best match (highest relevance)
            
            return jsonify(response)
        
        return jsonify({'videos': [], 'video': None})
        
    except Exception as e:
        print(f"Error finding training video: {str(e)}")
        return jsonify({'videos': [], 'video': None, 'error': str(e)})

def remove_practice_times_data():
    """API endpoint to remove practice times for the user's series from the schedule"""
    try:
        from flask import session, jsonify
        import json
        import os
        from utils.logging import log_user_activity
        
        # Get user's club and series to determine which practice times to remove
        user = session['user']
        user_club = user.get('club', '')
        user_series = user.get('series', '')
        
        if not user_club:
            return jsonify({
                'success': False, 
                'message': 'User club not found'
            }), 400
            
        if not user_series:
            return jsonify({
                'success': False, 
                'message': 'User series not found'
            }), 400
        
        # Load the current schedule (use the same file as the availability system)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        schedule_file = os.path.join(project_root, "data", "leagues", "all", "schedules.json")
        try:
            with open(schedule_file, 'r') as f:
                schedule = json.load(f)
        except FileNotFoundError:
            return jsonify({
                'success': False, 
                'message': 'Schedule file not found'
            }), 500
        except json.JSONDecodeError:
            return jsonify({
                'success': False, 
                'message': 'Invalid schedule file format'
            }), 500
        
        print(f'Original schedule has {len(schedule)} entries')
        
        # Count practice entries before removal
        practice_count = sum(1 for entry in schedule 
                           if 'Practice' in entry 
                           and entry.get('Practice') == user_club 
                           and entry.get('Series') == user_series)
        print(f'Found {practice_count} practice entries for {user_club} - {user_series} to remove')
        
        # Filter out practice entries that match the user's club and series
        filtered_schedule = [entry for entry in schedule 
                           if not ('Practice' in entry 
                                 and entry.get('Practice') == user_club 
                                 and entry.get('Series') == user_series)]
        
        print(f'After removal: {len(filtered_schedule)} entries remaining')
        
        # Save the updated schedule
        try:
            with open(schedule_file, 'w') as f:
                json.dump(filtered_schedule, f, indent=4)
        except Exception as e:
            return jsonify({
                'success': False, 
                'message': f'Failed to save schedule: {str(e)}'
            }), 500
        
        # Log the activity
        log_user_activity(
            user['email'], 
            'practice_times_removed',
            details=f'Removed {practice_count} practice times for {user_series} at {user_club}'
        )
        
        return jsonify({
            'success': True, 
            'message': f'Successfully removed {practice_count} practice times from the schedule!',
            'count': practice_count,
            'series': user_series,
            'club': user_club
        })
        
    except Exception as e:
        print(f"Error removing practice times: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'An unexpected error occurred'
        }), 500

def get_team_schedule_data_data():
    """Get team schedule data - implementation from working backup"""
    try:
        from flask import session, jsonify
        import json
        import os
        import traceback
        from datetime import datetime
        from database_utils import execute_query
        
        # Import the get_matches_for_user_club function
        from routes.act.schedule import get_matches_for_user_club
        
        print("\n=== TEAM SCHEDULE DATA API REQUEST ===")
        # Get the team from user's session data
        user = session.get('user')
        if not user:
            print("❌ No user in session")
            return jsonify({'error': 'Not authenticated'}), 401
            
        club_name = user.get('club')
        series = user.get('series')
        print(f"User: {user.get('email')}")
        print(f"Club: {club_name}")
        print(f"Series: {series}")
        
        if not club_name or not series:
            print("❌ Missing club or series")
            return jsonify({'error': 'Club or series not set in profile'}), 400

        # Get series ID first since we want all players in the series
        series_query = "SELECT id, name FROM series WHERE name = %(name)s"
        print(f"Executing series query: {series_query}")
        
        try:
            series_record = execute_query(series_query, {'name': series})
        except Exception as e:
            print(f"❌ Database error querying series: {e}")
            # Continue without database series ID - we can still show the schedule
            series_record = [{'id': None, 'name': series}]
        
        if not series_record:
            print(f"❌ Series not found: {series}")
            # Continue without database series ID - we can still show the schedule
            series_record = [{'id': None, 'name': series}]
            
        series_record = series_record[0]
        print(f"✓ Using series: {series_record}")

        # Load all players from players.json
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            players_path = os.path.join(project_root, 'data', 'leagues', 'apta', 'players.json')
            with open(players_path, 'r') as f:
                all_players = json.load(f)
            
            # Filter players for this series and club
            team_players = []
            for player in all_players:
                if (player.get('Series') == series and 
                    player.get('Club') == club_name):
                    full_name = f"{player['First Name']} {player['Last Name']}"
                    team_players.append({
                        'player_name': full_name,
                        'club_name': club_name,
                        'player_id': player.get('Player ID')  # Include Player ID for better matching
                    })
            
            print(f"✓ Found {len(team_players)} players in players.json for {club_name} - {series}")
            
            if not team_players:
                print("❌ No players found in players.json")
                return jsonify({'error': f'No players found for {club_name} - {series}'}), 404
                
        except Exception as e:
            print(f"❌ Error reading players.json: {e}")
            return jsonify({'error': 'Error loading player data'}), 500

        # Use the same logic as get_matches_for_user_club to get matches
        print("\n=== Getting matches using same logic as availability page ===")
        matches = get_matches_for_user_club(user)
        
        if not matches:
            print("❌ No matches found")
            return jsonify({'error': 'No matches or practices found for your team'}), 404
        
        print(f"✓ Found {len(matches)} matches/practices")

        # Convert matches to the format expected by team schedule page
        event_dates = []
        event_details = {}
        
        for match in matches:
            match_date = match.get('date', '')
            if not match_date:
                continue
                
            try:
                # Convert from MM/DD/YYYY to YYYY-MM-DD
                date_obj = datetime.strptime(match_date, '%m/%d/%Y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
                
                event_dates.append(formatted_date)
                
                # Determine event details based on match type
                if match.get('type') == 'practice':
                    event_details[formatted_date] = {
                        'type': 'Practice',
                        'description': match.get('description', 'Team Practice'),
                        'location': match.get('location', club_name),
                        'time': match.get('time', '')
                    }
                    print(f"✓ Added practice date: {match_date}")
                else:
                    # It's a match
                    home_team = match.get('home_team', '')
                    away_team = match.get('away_team', '')
                    
                    # Determine opponent
                    # Extract the number from the series name and use it directly for the team suffix
                    # E.g., "Chicago 22" -> "22", "Chicago 6" -> "6"
                    series_number = series.split()[-1] if ' ' in series else series
                    team_suffix = series_number
                    user_team_pattern = f"{club_name} - {team_suffix}"
                    print(f"Using team pattern: {user_team_pattern} (series: {series} -> suffix: {team_suffix})")
                    
                    opponent = ''
                    if home_team == user_team_pattern:
                        opponent = away_team.replace(f' - {team_suffix}', '').strip()
                    elif away_team == user_team_pattern:
                        opponent = home_team.replace(f' - {team_suffix}', '').strip()
                    
                    event_details[formatted_date] = {
                        'type': 'Match',
                        'opponent': opponent,
                        'home_team': home_team,
                        'away_team': away_team,
                        'location': match.get('location', ''),
                        'time': match.get('time', '')
                    }
                    print(f"✓ Added match date: {match_date} - {user_team_pattern} vs {opponent}")
                    
            except ValueError as e:
                print(f"Invalid date format: {match_date}, error: {e}")
                continue

        event_dates = sorted(list(set(event_dates)))  # Remove duplicates and sort
        print(f"✓ Found {len(event_dates)} total event dates (matches + practices)")

        players_schedule = {}
        print("\nProcessing player availability:")
        for player in team_players:
            availability = []
            player_name = player['player_name']
            player_id = player.get('player_id')
            print(f"\nChecking availability for {player_name} (ID: {player_id})")
            
            for event_date in event_dates:
                try:
                    # Convert event_date string to datetime.date object
                    event_date_obj = datetime.strptime(event_date, '%Y-%m-%d').date()
                    
                    # Get availability status for this player and date
                    status = 0  # Default to unavailable
                    
                    if series_record['id'] is not None:
                        try:
                            # Try player ID first, then fallback to name
                            avail_record = None
                            
                            if player_id:
                                # Primary search: Use tenniscores_player_id
                                avail_query = """
                                    SELECT availability_status
                                    FROM player_availability 
                                    WHERE tenniscores_player_id = %(player_id)s 
                                    AND series_id = %(series_id)s 
                                    AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
                                """
                                avail_params = {
                                    'player_id': player_id,
                                    'series_id': series_record['id'],
                                    'date': event_date_obj
                                }
                                avail_record = execute_query(avail_query, avail_params)
                                
                            if not avail_record and player_name:
                                # Fallback search: Use player_name
                                print(f"No availability found with player ID {player_id}, falling back to name search for {player_name}")
                                avail_query = """
                                    SELECT availability_status
                                    FROM player_availability 
                                    WHERE player_name = %(player)s 
                                    AND series_id = %(series_id)s 
                                    AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%(date)s AT TIME ZONE 'UTC')
                                """
                                avail_params = {
                                    'player': player_name,
                                    'series_id': series_record['id'],
                                    'date': event_date_obj
                                }
                                avail_record = execute_query(avail_query, avail_params)
                            
                            status = avail_record[0]['availability_status'] if avail_record and avail_record[0]['availability_status'] is not None else 0
                        except Exception as e:
                            print(f"Error querying availability for {player_name}: {e}")
                            status = 0
                    
                    # Get event details for this date
                    event_info = event_details.get(event_date, {})
                    
                    availability.append({
                        'date': event_date,
                        'availability_status': status,
                        'event_type': event_info.get('type', 'Unknown'),
                        'opponent': event_info.get('opponent', ''),
                        'description': event_info.get('description', ''),
                        'location': event_info.get('location', ''),
                        'time': event_info.get('time', '')
                    })
                except Exception as e:
                    print(f"Error processing availability for {player_name} on {event_date}: {e}")
                    # Skip this date if there's an error
                    continue
            
            # Store both player name and club name in the schedule
            display_name = player_name
            players_schedule[display_name] = availability
            print(f"✓ Added {display_name} with {len(availability)} dates")

        if not players_schedule:
            print("❌ No player schedules created")
            return jsonify({'error': 'No player schedules found for your series'}), 404
            
        print(f"\n✓ Final players_schedule has {len(players_schedule)} players")
        print(f"✓ Event details for {len(event_details)} dates")
        
        # Return JSON response
        return jsonify({
            'players_schedule': players_schedule,
            'match_dates': event_dates,
            'event_details': event_details
        })
        
    except Exception as e:
        print(f"❌ Error in get_team_schedule_data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500 