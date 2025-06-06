from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for, g
from utils.auth import login_required
from utils.logging import log_user_activity
import os
import json
import traceback
import re
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import unquote
from utils.series_matcher import series_match, normalize_series_for_storage

# Create Blueprint
player_bp = Blueprint('player', __name__)

@player_bp.route('/api/players')
@login_required
def get_players_by_series():
    """Get all players for a specific series, optionally filtered by team and club"""
    try:
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
            
        # Load player data
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        players_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'players.json')
        
        with open(players_path, 'r') as f:
            all_players = json.load(f)
            
        # Load matches data if team filtering is needed
        matches_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'match_history.json')
        team_players = set()
        if team_id and os.path.exists(matches_path):
            try:
                with open(matches_path, 'r') as f:
                    matches = json.load(f)
                # Get all players who have played for this team
                for match in matches:
                    if match['Home Team'] == team_id:
                        team_players.add(match['Home Player 1'])
                        team_players.add(match['Home Player 2'])
                    elif match['Away Team'] == team_id:
                        team_players.add(match['Away Player 1'])
                        team_players.add(match['Away Player 2'])
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

@player_bp.route('/api/team-players/<team_id>')
@login_required
def get_team_players(team_id):
    """Get all players for a specific team"""
    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Load player PTI data from JSON
        players_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'players.json')
        with open(players_path, 'r') as f:
            all_players = json.load(f)
        
        pti_dict = {}
        for player in all_players:
            player_name = f"{player['Last Name']} {player['First Name']}"
            pti_dict[player_name] = float(player['PTI'])
        
        matches_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'match_history.json')
        with open(matches_path, 'r') as f:
            matches = json.load(f)
            
        # Track unique players and their stats
        players = {}
        
        # Group matches by date to determine court numbers
        date_matches = {}
        for match in matches:
            if match['Home Team'] == team_id or match['Away Team'] == team_id:
                date = match['Date']
                if date not in date_matches:
                    date_matches[date] = []
                date_matches[date].append(match)
        
        # Sort dates and assign court numbers
        sorted_dates = sorted(date_matches.keys())
        
        for date in sorted_dates:
            day_matches = date_matches[date]
            # Sort by time if available, otherwise use original order
            day_matches.sort(key=lambda m: m.get('Time', ''))
            
            for court_idx, match in enumerate(day_matches):
                court_num = (court_idx % 4) + 1  # Courts 1-4
                
                # Determine if team was home or away
                is_home = match['Home Team'] == team_id
                player1 = match['Home Player 1'] if is_home else match['Away Player 1']
                player2 = match['Home Player 2'] if is_home else match['Away Player 2']
                
                # Skip if players are missing
                if not player1 or not player2:
                    continue
                
                # Determine if team won
                winner_is_home = match.get('Winner') == 'home'
                team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
                
                # Track stats for each player
                for player_name in [player1, player2]:
                    if player_name not in players:
                        players[player_name] = {
                            'name': player_name,
                            'matches': 0,
                            'wins': 0,
                            'courts': {'Court 1': {'matches': 0, 'wins': 0},
                                     'Court 2': {'matches': 0, 'wins': 0},
                                     'Court 3': {'matches': 0, 'wins': 0},
                                     'Court 4': {'matches': 0, 'wins': 0}},
                            'partners': {},
                            'pti': pti_dict.get(player_name, 0.0)
                        }
                    
                    player_stats = players[player_name]
                    player_stats['matches'] += 1
                    
                    if team_won:
                        player_stats['wins'] += 1
                    
                    # Court stats
                    court_name = f'Court {court_num}'
                    player_stats['courts'][court_name]['matches'] += 1
                    if team_won:
                        player_stats['courts'][court_name]['wins'] += 1
                    
                    # Partner stats
                    partner = player2 if player_name == player1 else player1
                    if partner not in player_stats['partners']:
                        player_stats['partners'][partner] = {'matches': 0, 'wins': 0}
                    player_stats['partners'][partner]['matches'] += 1
                    if team_won:
                        player_stats['partners'][partner]['wins'] += 1
        
        # Convert to list and add calculated fields
        result_players = []
        for player_name, stats in players.items():
            win_rate = (stats['wins'] / stats['matches'] * 100) if stats['matches'] > 0 else 0
            
            # Find best court
            best_court = None
            best_court_rate = 0
            for court, court_stats in stats['courts'].items():
                if court_stats['matches'] >= 2:
                    court_rate = (court_stats['wins'] / court_stats['matches'] * 100)
                    if court_rate > best_court_rate:
                        best_court_rate = court_rate
                        best_court = f"{court} ({court_rate:.1f}%)"
            
            # Find best partner
            best_partner = None
            best_partner_rate = 0
            for partner, partner_stats in stats['partners'].items():
                if partner_stats['matches'] >= 2:
                    partner_rate = (partner_stats['wins'] / partner_stats['matches'] * 100)
                    if partner_rate > best_partner_rate:
                        best_partner_rate = partner_rate
                        best_partner = f"{partner} ({partner_rate:.1f}%)"
            
            result_players.append({
                'name': player_name,
                'matches': stats['matches'],
                'wins': stats['wins'],
                'losses': stats['matches'] - stats['wins'],
                'winRate': round(win_rate, 1),
                'pti': stats['pti'],
                'bestCourt': best_court or 'N/A',
                'bestPartner': best_partner or 'N/A',
                'courts': stats['courts'],
                'partners': stats['partners']
            })
        
        # Sort by matches played (desc), then by win rate (desc)
        result_players.sort(key=lambda p: (-p['matches'], -p['winRate']))
        
        return jsonify({
            'players': result_players,
            'teamId': team_id
        })
        
    except Exception as e:
        print(f"Error getting team players: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@player_bp.route('/api/player-court-stats/<player_name>')
def player_court_stats(player_name):
    """
    Returns court breakdown stats for a player using data/match_history.json.
    """
    print(f"=== /api/player-court-stats called for player: {player_name} ===")
    
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'match_history.json')
    print(f"Loading match data from: {json_path}")
    
    try:
        with open(json_path, 'r') as f:
            matches = json.load(f)
        print(f"Successfully loaded {len(matches)} matches")
    except Exception as e:
        print(f"ERROR: Failed to load match data: {e}")
        return jsonify({"error": f"Failed to load match data: {e}"}), 500

    # Helper function for case-insensitive name normalization
    def normalize_name(name):
        return name.replace(',', '').replace('  ', ' ').strip().lower()
    
    # Normalize the target player name
    player_name_normalized = normalize_name(player_name)
    
    # Helper function to check if player is in a match (case-insensitive)
    def player_in_match_players(match_players, target_normalized):
        return any(normalize_name(p) == target_normalized for p in match_players if p)

    # Group matches by date
    matches_by_date = defaultdict(list)
    for match in matches:
        matches_by_date[match['Date']].append(match)
    
    print(f"Grouped matches for {len(matches_by_date)} different dates")

    # For each date, assign court number by order
    court_matches = defaultdict(list)  # court_num (1-based) -> list of matches for this player
    player_match_count = 0
    
    for date, day_matches in matches_by_date.items():
        for i, match in enumerate(day_matches):
            court_num = i + 1
            # Check if player is in this match (case-insensitive)
            match_players = [match['Home Player 1'], match['Home Player 2'], match['Away Player 1'], match['Away Player 2']]
            if player_in_match_players(match_players, player_name_normalized):
                court_matches[court_num].append(match)
                player_match_count += 1
    
    print(f"Found {player_match_count} matches for player {player_name}")
    print(f"Matches by court: {', '.join([f'Court {k}: {len(v)}' for k, v in court_matches.items()])}")

    # For each court, calculate stats
    result = {}
    for court_num in range(1, 5):  # Courts 1-4
        matches = court_matches.get(court_num, [])
        num_matches = len(matches)
        wins = 0
        losses = 0
        partners = []
        partner_results = defaultdict(lambda: {'matches': 0, 'wins': 0})

        for match in matches:
            # Determine if player was home or away, and who was their partner (case-insensitive)
            player_position = None
            partner = None
            
            if normalize_name(match['Home Player 1']) == player_name_normalized:
                partner = match['Home Player 2']
                is_home = True
            elif normalize_name(match['Home Player 2']) == player_name_normalized:
                partner = match['Home Player 1']
                is_home = True
            elif normalize_name(match['Away Player 1']) == player_name_normalized:
                partner = match['Away Player 2']
                is_home = False
            elif normalize_name(match['Away Player 2']) == player_name_normalized:
                partner = match['Away Player 1']
                is_home = False
            else:
                continue  # Shouldn't happen
                
            partners.append(partner)
            partner_results[partner]['matches'] += 1
            # Determine win/loss
            if (is_home and match['Winner'] == 'home') or (not is_home and match['Winner'] == 'away'):
                wins += 1
                partner_results[partner]['wins'] += 1
            else:
                losses += 1
                
        # Win rate
        win_rate = (wins / num_matches * 100) if num_matches > 0 else 0.0
        # Most common partners
        partner_list = []
        for partner, stats in sorted(partner_results.items(), key=lambda x: -x[1]['matches']):
            p_matches = stats['matches']
            p_wins = stats['wins']
            p_win_rate = (p_wins / p_matches * 100) if p_matches > 0 else 0.0
            partner_list.append({
                'name': partner,
                'matches': p_matches,
                'wins': p_wins,
                'winRate': round(p_win_rate, 1)
            })
        result[f'court{court_num}'] = {
            'matches': num_matches,
            'wins': wins,
            'losses': losses,
            'winRate': round(win_rate, 1),
            'partners': partner_list
        }
    
    print(f"Returning court stats for {player_name}: {len(result)} courts")
    return jsonify(result)

@player_bp.route('/player-detail/<player_name>')
@login_required
def serve_player_detail(player_name):
    """Serve the desktop player detail page"""
    from app.services.player_service import get_player_analysis_by_name
    
    analyze_data = get_player_analysis_by_name(player_name)
    
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='player_detail', details=f'Viewed player {player_name}')
    return render_template('player_detail.html', 
                          session_data=session_data, 
                          analyze_data=analyze_data,
                          player_name=player_name)

@player_bp.route('/api/player-streaks')
def get_player_streaks():
    """Get current win/loss streaks for all players"""
    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        matches_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'match_history.json')
        
        with open(matches_path, 'r') as f:
            matches = json.load(f)
            
        # Track streaks for each player
        player_streaks = {}
        
        # Helper function to parse dates
        def parse_date(d):
            try:
                if isinstance(d, str):
                    # Try multiple date formats
                    for fmt in ['%m/%d/%Y', '%d-%b-%y', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(d, fmt)
                        except ValueError:
                            continue
                    return datetime.min  # If no format works
                return d
            except:
                return datetime.min
        
        # Sort matches by date (oldest first)
        sorted_matches = sorted(matches, key=lambda x: parse_date(x.get('Date', '')))
        
        for match in sorted_matches:
            # Process all players in the match
            players_and_results = []
            
            # Home team players
            home_won = match.get('Winner') == 'home'
            if match.get('Home Player 1'):
                players_and_results.append((match['Home Player 1'], home_won))
            if match.get('Home Player 2'):
                players_and_results.append((match['Home Player 2'], home_won))
                
            # Away team players
            away_won = match.get('Winner') == 'away'
            if match.get('Away Player 1'):
                players_and_results.append((match['Away Player 1'], away_won))
            if match.get('Away Player 2'):
                players_and_results.append((match['Away Player 2'], away_won))
            
            # Update streaks for each player
            for player_name, won in players_and_results:
                if not player_name or player_name.strip() == '':
                    continue
                    
                if player_name not in player_streaks:
                    player_streaks[player_name] = {
                        'current_streak': 0,
                        'streak_type': 'none',  # 'win', 'loss', or 'none'
                        'last_match_date': parse_date(match.get('Date', ''))
                    }
                
                streak_info = player_streaks[player_name]
                
                if won:
                    if streak_info['streak_type'] == 'win':
                        streak_info['current_streak'] += 1
                    else:
                        streak_info['current_streak'] = 1
                        streak_info['streak_type'] = 'win'
                else:
                    if streak_info['streak_type'] == 'loss':
                        streak_info['current_streak'] += 1
                    else:
                        streak_info['current_streak'] = 1
                        streak_info['streak_type'] = 'loss'
                
                streak_info['last_match_date'] = parse_date(match.get('Date', ''))
        
        # Convert to response format
        result = []
        for player_name, streak_info in player_streaks.items():
            if streak_info['current_streak'] > 0:  # Only include players with active streaks
                result.append({
                    'player_name': player_name,
                    'streak_length': streak_info['current_streak'],
                    'streak_type': streak_info['streak_type'],
                    'last_match_date': streak_info['last_match_date'].strftime('%m/%d/%Y') if streak_info['last_match_date'] != datetime.min else 'Unknown'
                })
        
        # Sort by streak length (descending)
        result.sort(key=lambda x: x['streak_length'], reverse=True)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error getting player streaks: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@player_bp.route('/mobile/player-stats')
@login_required
def serve_mobile_player_stats():
    """Serve the mobile player stats page"""
    session_data = {
        'user': session['user'],
        'authenticated': True
    }
    
    log_user_activity(session['user']['email'], 'page_visit', page='mobile_player_stats')
    return render_template('mobile/player_stats.html', session_data=session_data)

@player_bp.route('/api/player-history')
@login_required
def get_player_history():
    """Get player history from match data"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'error': 'Not authenticated'}), 401
            
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        player_history_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'player_history.json')
        
        # Check if file exists before trying to open it
        if not os.path.exists(player_history_path):
            return jsonify({'error': 'Player history data not available'}), 404
        
        with open(player_history_path, 'r') as f:
            player_history = json.load(f)
            
        # Find the current user's player record
        user_name = f"{user['first_name']} {user['last_name']}"
        
        from app.services.player_service import find_player_in_history
        player_record = find_player_in_history(user, player_history)
        
        if not player_record:
            return jsonify({'error': f'No history found for player: {user_name}'}), 404
            
        return jsonify(player_record)
        
    except FileNotFoundError:
        return jsonify({'error': 'Player history data not available'}), 404
    except Exception as e:
        print(f"Error getting player history: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@player_bp.route('/api/player-history/<player_name>')
@login_required
def get_specific_player_history(player_name):
    """Get history for a specific player"""
    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        player_history_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'player_history.json')
        
        with open(player_history_path, 'r') as f:
            player_history = json.load(f)
            
        # Helper function to normalize names for comparison
        def normalize(name):
            return name.lower().strip().replace(',', '').replace('.', '')
        
        # Find the player's record by matching name (case-insensitive)
        target_normalized = normalize(player_name)
        player_record = None
        
        for player in player_history:
            if normalize(player.get('name', '')) == target_normalized:
                player_record = player
                break
        
        if not player_record:
            return jsonify({'error': f'No history found for player: {player_name}'}), 404
            
        return jsonify(player_record)
        
    except Exception as e:
        print(f"Error getting player history for {player_name}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500 