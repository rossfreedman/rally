"""
Mobile service module - handles all mobile-specific business logic
This module provides functions for mobile interface data processing and user interactions.
"""

import os
import json
from datetime import datetime, timedelta
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
import traceback
from collections import defaultdict, Counter
from utils.date_utils import date_to_db_timestamp, normalize_date_string

def get_player_analysis_by_name(player_name):
    """
    Returns the player analysis data for the given player name, as a dict.
    This function parses the player_name string into first and last name (if possible),
    then calls get_player_analysis with a constructed user dict.
    Handles single-word names gracefully.
    """
    # Defensive: handle empty or None
    if not player_name or not isinstance(player_name, str):
        return {
            'current_season': None,
            'court_analysis': {},
            'career_stats': None,
            'player_history': None,
            'videos': {'match': [], 'practice': []},
            'trends': {},
            'career_pti_change': 'N/A',
            'current_pti': None,
            'weekly_pti_change': None,
            'error': 'Invalid player name.'
        }
    
    # Load player history to find the exact player record first
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        player_history_path = os.path.join(project_root, 'data', 'player_history.json')
        
        with open(player_history_path, 'r') as f:
            all_players = json.load(f)
        
        def normalize(name):
            return name.replace(',', '').replace('  ', ' ').strip().lower()
        
        # Try to find the exact player by name matching
        player_name_normalized = normalize(player_name)
        found_player = None
        
        for p in all_players:
            player_record_name = normalize(p.get('name', ''))
            if player_record_name == player_name_normalized:
                found_player = p
                break
        
        if found_player:
            # If we found the player, create a better user dict with their player_id if available
            parts = player_name.strip().split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
            else:
                first_name = parts[0]
                last_name = parts[0]
            
            # Create user dict with potentially more complete information
            user_dict = {
                'first_name': first_name,
                'last_name': last_name,
                'tenniscores_player_id': found_player.get('player_id')  # Include player_id if available
            }
            
            print(f"[DEBUG] Found player record for '{player_name}': {found_player.get('name')} with ID {found_player.get('player_id')}")
            
        else:
            # Fallback to basic name parsing if no exact match found
            parts = player_name.strip().split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
            else:
                first_name = parts[0]
                last_name = parts[0]
            
            user_dict = {'first_name': first_name, 'last_name': last_name}
            print(f"[DEBUG] No exact match found for '{player_name}', using fallback user dict")
        
    except Exception as e:
        print(f"Error loading player history for better matching: {str(e)}")
        # Fallback to original logic if file loading fails
        parts = player_name.strip().split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = ' '.join(parts[1:])
        else:
            first_name = parts[0]
            last_name = parts[0]
        
        user_dict = {'first_name': first_name, 'last_name': last_name}
    
    # Call get_player_analysis with constructed user dict
    result = get_player_analysis(user_dict)
    
    # Debug output for career stats
    if result.get('career_stats'):
        print(f"[DEBUG] Career stats for {player_name}: {result['career_stats']}")
    else:
        print(f"[DEBUG] No career stats found for {player_name}")
    
    return result

def get_mobile_schedule_data(user):
    """Get schedule data for mobile view schedule page"""
    try:
        # TODO: Extract schedule logic from server.py mobile route
        return {
            'matches': [],
            'user_name': user.get('email', ''),
            'error': 'Function not yet extracted from server.py'
        }
    except Exception as e:
        print(f"Error getting mobile schedule data: {str(e)}")
        return {
            'error': str(e)
        }

def get_player_analysis(user):
    """
    Returns the player analysis data for the given user, as a dict.
    Uses match_history.json for current season stats and court analysis,
    and player_history.json for career stats and player history.
    Always returns all expected keys, even if some are None or empty.
    """
    # Use tenniscores_player_id as primary search method, fallback to name if not available
    tenniscores_player_id = user.get('tenniscores_player_id')
    player_name = f"{user['first_name']} {user['last_name']}"
    print(f"[DEBUG] Looking for player with ID: '{tenniscores_player_id}' or name: '{player_name}'")
    
    # Fix path construction to point to project root data directory
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    player_history_path = os.path.join(project_root, 'data', 'player_history.json')
    matches_path = os.path.join(project_root, 'data', 'match_history.json')
    
    print(f"[DEBUG] Looking for player_history.json at: {player_history_path}")
    print(f"[DEBUG] Looking for match_history.json at: {matches_path}")

    # --- 1. Load player history for career stats and previous seasons ---
    try:
        with open(player_history_path, 'r') as f:
            all_players = json.load(f)
    except Exception as e:
        return {
            'current_season': None,
            'court_analysis': {},
            'career_stats': None,
            'player_history': None,
            'videos': {'match': [], 'practice': []},
            'trends': {},
            'career_pti_change': 'N/A',
            'current_pti': None,
            'weekly_pti_change': None,
            'error': f'Could not load player history: {e}'
        }
    
    def normalize(name):
        return name.replace(',', '').replace('  ', ' ').strip().lower()
    
    player = None
    
    # First try to find by tenniscores_player_id (most reliable)
    if tenniscores_player_id:
        print(f"[DEBUG] Searching by player_id: '{tenniscores_player_id}'")
        player = next((p for p in all_players if p.get('player_id') == tenniscores_player_id), None)
        print(f"[DEBUG] Found player by ID: {player.get('name') if player else 'None'}")
    
    # Fallback to name matching if ID search failed
    if not player:
        print(f"[DEBUG] Player not found by ID, falling back to name search")
        # Normalize the target player name for case-insensitive matching
        player_name_normal = normalize(player_name)
        player_last_first = normalize(f"{user['last_name']}, {user['first_name']}")
        print(f"[DEBUG] Normalized search names: '{player_name_normal}', '{player_last_first}'")
        
        for p in all_players:
            n = normalize(p.get('name', ''))
            if n == player_name_normal or n == player_last_first:
                print(f"[DEBUG] Match found for player: '{p.get('name')}'")
                player = p
                break
    
    if not player:
        return {
            'current_season': None,
            'court_analysis': {},
            'career_stats': None,
            'player_history': None,
            'videos': {'match': [], 'practice': []},
            'trends': {},
            'career_pti_change': 'N/A',
            'current_pti': None,
            'weekly_pti_change': None,
            'error': 'Player not found'
        }
    
    # --- 2. Load all matches for this player ---
    try:
        with open(matches_path, 'r') as f:
            all_matches = json.load(f)
    except Exception as e:
        all_matches = []
    
    # Helper function to check if player is in a match (case-insensitive)
    def player_in_match(match, target_player_name):
        """Check if target_player_name is in the match, case-insensitive"""
        match_players = [
            match.get('Home Player 1', ''),
            match.get('Home Player 2', ''),
            match.get('Away Player 1', ''),
            match.get('Away Player 2', '')
        ]
        target_normalized = normalize(target_player_name)
        return any(normalize(p) == target_normalized for p in match_players if p)
    
    def get_player_position_in_match(match, target_player_name):
        """Get the position (home/away and 1/2) of target player in match, case-insensitive"""
        target_normalized = normalize(target_player_name)
        
        if normalize(match.get('Home Player 1', '')) == target_normalized:
            return 'Home Player 1'
        elif normalize(match.get('Home Player 2', '')) == target_normalized:
            return 'Home Player 2'
        elif normalize(match.get('Away Player 1', '')) == target_normalized:
            return 'Away Player 1'
        elif normalize(match.get('Away Player 2', '')) == target_normalized:
            return 'Away Player 2'
        return None
    
    def get_partner_for_player(match, target_player_name):
        """Get the partner of target player in the match, case-insensitive"""
        position = get_player_position_in_match(match, target_player_name)
        if position == 'Home Player 1':
            return match.get('Home Player 2', '')
        elif position == 'Home Player 2':
            return match.get('Home Player 1', '')
        elif position == 'Away Player 1':
            return match.get('Away Player 2', '')
        elif position == 'Away Player 2':
            return match.get('Away Player 1', '')
        return None
    
    # --- 3. Determine current season (latest in player history) ---
    current_season_info = None
    if player and player.get('seasons') and player['seasons']:
        current_season_info = player['seasons'][-1]
        current_series = str(current_season_info.get('series', ''))
    else:
        matches_with_series = [m for m in player.get('matches', []) if 'series' in m and 'date' in m] if player else []
        if matches_with_series:
            def parse_date(d):
                for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(d, fmt)
                    except Exception:
                        continue
                return None
            matches_with_series_sorted = sorted(matches_with_series, key=lambda m: parse_date(m['date']) or m['date'], reverse=True)
            current_series = matches_with_series_sorted[0]['series']
        else:
            current_series = None
    
    # --- 4. Filter matches for current season/series ---
    player_matches = []
    if player:
        for m in all_matches:
            if player_in_match(m, player_name):
                if current_series:
                    match_series = str(m.get('Series', ''))
                    if match_series and match_series != current_series:
                        continue
                player_matches.append(m)
    
    # --- 5. Assign matches to courts 1-4 by date and team pairing ---
    matches_by_group = defaultdict(list)
    for match in all_matches:
        date = match.get('Date') or match.get('date')
        home_team = match.get('Home Team', '')
        away_team = match.get('Away Team', '')
        group_key = (date, home_team, away_team)
        matches_by_group[group_key].append(match)

    court_stats = {f'court{i}': {'matches': 0, 'wins': 0, 'losses': 0, 'partners': Counter()} for i in range(1, 5)}
    total_matches = 0
    wins = 0
    losses = 0
    pti_start = None
    pti_end = None

    for group_key in sorted(matches_by_group.keys()):
        day_matches = matches_by_group[group_key]
        # Sort all matches for this group for deterministic court assignment
        day_matches_sorted = sorted(day_matches, key=lambda m: (m.get('Home Team', ''), m.get('Away Team', '')))
        for i, match in enumerate(day_matches_sorted):
            court_num = i + 1
            if court_num > 4:
                continue
            # Check if player is in this match (case-insensitive)
            # Use actual player name from player record instead of session name for reliable matching
            actual_player_name = player.get('name', player_name) if player else player_name
            if not player_in_match(match, actual_player_name):
                continue
            total_matches += 1
            
            # Determine if player is home team (case-insensitive)
            position = get_player_position_in_match(match, player_name)
            is_home = position and position.startswith('Home')
            
            won = (is_home and match.get('Winner') == 'home') or (not is_home and match.get('Winner') == 'away')
            if won:
                wins += 1
                court_stats[f'court{court_num}']['wins'] += 1
            else:
                losses += 1
                court_stats[f'court{court_num}']['losses'] += 1
            court_stats[f'court{court_num}']['matches'] += 1
            
            # Identify partner (case-insensitive)
            partner = get_partner_for_player(match, player_name)
            if partner:
                court_stats[f'court{court_num}']['partners'][partner] += 1
            
            if 'Rating' in match:
                if pti_start is None:
                    pti_start = match['Rating']
                pti_end = match['Rating']
    
    # --- 6. Build current season stats ---
    pti_change = 'N/A'
    if player and 'matches' in player:
        import re
        def parse_date(d):
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(d, fmt)
                except Exception:
                    continue
            return None
        def normalize_series(x):
            return ''.join(re.findall(r'\d+', x or ''))
        cs = normalize_series(current_series) if 'current_series' in locals() and current_series else ''
        season_matches = [m for m in player['matches'] if 'series' in m and normalize_series(m['series']) == cs and 'end_pti' in m and 'date' in m]
        season_window_matches = []
        if season_matches:
            season_matches_sorted = sorted(season_matches, key=lambda m: parse_date(m['date']) or m['date'])
            latest_match_date = parse_date(season_matches_sorted[-1]['date'])
            if latest_match_date:
                if latest_match_date.month < 8:
                    season_start_year = latest_match_date.year - 1
                else:
                    season_start_year = latest_match_date.year
                season_start = datetime(season_start_year, 8, 1)
                season_end = datetime(season_start_year + 1, 3, 31)
                for m in season_matches:
                    pd = parse_date(m['date'])
            season_window_matches = [m for m in season_matches if parse_date(m['date']) and season_start <= parse_date(m['date']) <= season_end]
        if len(season_window_matches) >= 2:
            matches_for_pti_sorted = sorted(season_window_matches, key=lambda m: parse_date(m['date']))
            earliest_pti = matches_for_pti_sorted[0]['end_pti']
            latest_pti = matches_for_pti_sorted[-1]['end_pti']
            pti_change = round(latest_pti - earliest_pti, 1)
    
    win_rate = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0
    current_season = {
        'winRate': win_rate,
        'matches': total_matches,
        'wins': wins,  # Added: number of wins in current season
        'losses': losses,  # Added: number of losses in current season
        'ptiChange': pti_change
    }
    
    # --- 7. Build court analysis ---
    court_analysis = {}
    for court, stats in court_stats.items():
        matches = stats['matches']
        win_rate = round((stats['wins'] / matches) * 100, 1) if matches > 0 else 0
        record = f"{stats['wins']}-{stats['losses']}"
        # Only include winRate if partner has at least one match; otherwise, omit or set to None
        top_partners = []
        for p, c in stats['partners'].most_common(3):
            partner_entry = {'name': p, 'record': f"{c} matches"}
            if c > 0:
                # If you want to show win rate for partners, you can add it here in the future
                pass  # Not adding winRate if not available
            top_partners.append(partner_entry)
        court_analysis[court] = {
            'winRate': win_rate,
            'record': record,
            'topPartners': top_partners
        }
    
    # --- 8. Career stats and player history from player history file ---
    career_stats = None
    player_history = None
    if player:
        # The player_history.json has direct wins, losses, and matches fields on each player
        total_career_wins = player.get('wins', 0)
        total_career_losses = player.get('losses', 0)
        matches_list = player.get('matches', [])
        total_career_matches = len(matches_list) if isinstance(matches_list, list) else player.get('matches', 0)
        
        # Calculate win rate
        win_rate_career = round((total_career_wins / total_career_matches) * 100, 1) if total_career_matches > 0 else 0
        current_pti = player.get('pti', 'N/A')
        
        career_stats = {
            'winRate': win_rate_career,
            'matches': total_career_matches,
            'wins': total_career_wins,
            'losses': total_career_losses,
            'pti': current_pti
        }
        
        print(f"[DEBUG] Career stats for {player.get('name', 'Unknown')}: {total_career_matches} matches, {total_career_wins} wins, {total_career_losses} losses, {win_rate_career}% win rate")
        
        progression = []
        # --- NEW: Compute seasons from matches if missing or empty ---
        seasons = player.get('seasons', [])
        if not seasons:
            seasons = build_season_history(player)
        for s in seasons:
            trend_val = s.get('trend', '')
            progression.append(f"{s.get('season', '')}: PTI {s.get('ptiStart', '')}→{s.get('ptiEnd', '')} ({trend_val})")
        player_history = {
            'progression': ' | '.join(progression),
            'seasons': seasons
        }
    
    # --- 9. Get current PTI and weekly change ---
    current_pti = None
    weekly_pti_change = None
    
    if player and player.get('matches'):
        # Sort matches by date to find most recent
        matches = sorted(player['matches'], key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y'), reverse=True)
        if matches:
            current_pti = matches[0].get('end_pti')
            
            # Calculate weekly PTI change
            if len(matches) > 1:
                current_date = datetime.strptime(matches[0]['date'], '%m/%d/%Y')
                # Find the match closest to one week ago
                prev_match = None
                for match in matches[1:]:  # Skip the first match (current)
                    match_date = datetime.strptime(match['date'], '%m/%d/%Y')
                    if (current_date - match_date).days >= 5:  # Allow some flexibility in what constitutes a "week"
                        prev_match = match
                        break
                
                if prev_match and 'end_pti' in prev_match:
                    prev_pti = prev_match['end_pti']
                    weekly_pti_change = current_pti - prev_pti  # Change calculation to current - previous

    # --- 10. Compose response ---
    career_pti_change = 'N/A'
    if player and 'matches' in player:
        def parse_date(d):
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(d, fmt)
                except Exception:
                    continue
            return None
        matches_with_pti = [m for m in player['matches'] if 'end_pti' in m and 'date' in m]
        if len(matches_with_pti) >= 2:
            matches_with_pti_sorted = sorted(matches_with_pti, key=lambda m: parse_date(m['date']))
            earliest_pti = matches_with_pti_sorted[0]['end_pti']
            latest_pti = matches_with_pti_sorted[-1]['end_pti']
            career_pti_change = round(latest_pti - earliest_pti, 1)
    
    # --- Defensive: always return all keys, even if player not found ---
    response = {
        'current_season': current_season if player else None,
        'court_analysis': court_analysis if player else {},
        'career_stats': career_stats if player else None,
        'player_history': player_history if player else None,
        'videos': {'match': [], 'practice': []},
        'trends': {},
        'career_pti_change': career_pti_change if player else 'N/A',
        'current_pti': float(current_pti) if current_pti is not None else None,
        'weekly_pti_change': float(weekly_pti_change) if weekly_pti_change is not None else None,
        'error': None if player else 'No analysis data available for this player.'
    }
    return response

def get_season_from_date(date_str):
    """
    Given a date string in MM/DD/YYYY or YYYY-MM-DD, return the season string 'YYYY-YYYY+1'.
    """
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        return None  # Invalid date format
    if dt.month >= 8:
        start_year = dt.year
        end_year = dt.year + 1
    else:
        start_year = dt.year - 1
        end_year = dt.year
    return f"{start_year}-{end_year}"

def build_season_history(player):
    from collections import defaultdict
    matches = player.get('matches', [])
    if not matches:
        return []
    # Helper to parse date robustly
    def parse_date(d):
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(d, fmt)
            except Exception:
                continue
        return d  # fallback to string if parsing fails
    # Group matches by season
    season_matches = defaultdict(list)
    for m in matches:
        season = get_season_from_date(m.get('date', ''))
        if season:
            season_matches[season].append(m)
    seasons = []
    for season, ms in season_matches.items():
        ms_sorted = sorted(ms, key=lambda x: parse_date(x.get('date', '')))
        pti_start = ms_sorted[0].get('end_pti', None)
        pti_end = ms_sorted[-1].get('end_pti', None)
        series = ms_sorted[0].get('series', '')
        trend = (pti_end - pti_start) if pti_start is not None and pti_end is not None else None
        # --- ROUND trend to 1 decimal ---
        if trend is not None:
            trend_rounded = round(trend, 1)
            trend_str = f"+{trend_rounded}" if trend_rounded >= 0 else str(trend_rounded)
        else:
            trend_str = ''
        seasons.append({
            'season': season,
            'series': series,
            'ptiStart': pti_start,
            'ptiEnd': pti_end,
            'trend': trend_str
        })
    # Sort by season (descending)
    seasons.sort(key=lambda s: s['season'], reverse=True)
    return seasons

def get_mobile_team_data(user):
    """Get team data for mobile my team page"""
    try:
        # Extract team name from user club and series (same logic as backup)
        club = user.get('club')
        series = user.get('series')
        
        if not club or not series:
            return {
                'team_data': None,
                'court_analysis': {},
                'top_players': [],
                'error': 'User club or series not found'
            }
        
        # Extract series number from series string (e.g. "Chicago 22" -> "22")
        import re
        m = re.search(r'(\d+)', series)
        series_num = m.group(1) if m else ''
        
        # Construct team name in format "Club - SeriesNum"
        team = f"{club} - {series_num}"
        
        # Load team stats and matches data
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        stats_path = os.path.join(project_root, 'data', 'series_stats.json')
        matches_path = os.path.join(project_root, 'data', 'match_history.json')
        
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
        
        # Find the team's stats
        team_stats = next((stats for stats in all_stats if stats.get('team') == team), None)
        
        print(f"[DEBUG] Looking for team: {team}")
        print(f"[DEBUG] Found team stats: {team_stats is not None}")
        
        # Compute court analysis and top players from match_history.json
        court_analysis = {}
        top_players = []
        
        if os.path.exists(matches_path):
            with open(matches_path, 'r') as f:
                matches = json.load(f)
            
            # Group matches by date for court assignment
            from collections import defaultdict, Counter
            matches_by_date = defaultdict(list)
            for match in matches:
                if match.get('Home Team') == team or match.get('Away Team') == team:
                    matches_by_date[match['Date']].append(match)
            
            # Court stats and player stats
            court_stats = {f'court{i}': {'matches': 0, 'wins': 0, 'losses': 0, 'players': Counter()} for i in range(1, 5)}
            player_stats = {}
            
            for date, day_matches in matches_by_date.items():
                # Sort matches for deterministic court assignment
                day_matches_sorted = sorted(day_matches, key=lambda m: (m.get('Home Team', ''), m.get('Away Team', '')))
                for i, match in enumerate(day_matches_sorted):
                    court_num = i + 1
                    if court_num > 4:
                        continue
                    court_key = f'court{court_num}'
                    is_home = match.get('Home Team') == team
                    
                    # Get players for this team
                    if is_home:
                        players = [match.get('Home Player 1'), match.get('Home Player 2')]
                        opp_players = [match.get('Away Player 1'), match.get('Away Player 2')]
                    else:
                        players = [match.get('Away Player 1'), match.get('Away Player 2')]
                        opp_players = [match.get('Home Player 1'), match.get('Home Player 2')]
                    
                    # Filter out empty player names
                    players = [p for p in players if p and p.strip()]
                    
                    # Determine win/loss
                    won = (is_home and match.get('Winner') == 'home') or (not is_home and match.get('Winner') == 'away')
                    
                    court_stats[court_key]['matches'] += 1
                    if won:
                        court_stats[court_key]['wins'] += 1
                    else:
                        court_stats[court_key]['losses'] += 1
                    
                    for p in players:
                        court_stats[court_key]['players'][p] += 1
                        if p not in player_stats:
                            player_stats[p] = {'matches': 0, 'wins': 0, 'courts': Counter(), 'partners': Counter()}
                        player_stats[p]['matches'] += 1
                        if won:
                            player_stats[p]['wins'] += 1
                        player_stats[p]['courts'][court_key] += 1
                    
                    # Partner tracking
                    if len(players) == 2:
                        player_stats[players[0]]['partners'][players[1]] += 1
                        player_stats[players[1]]['partners'][players[0]] += 1
            
            # Build court_analysis
            for i in range(1, 5):
                court_key = f'court{i}'
                stat = court_stats[court_key]
                matches = stat['matches']
                wins = stat['wins']
                losses = stat['losses']
                win_rate = round((wins / matches) * 100, 1) if matches > 0 else 0
                
                # Top players by matches played on this court
                top_players_court = stat['players'].most_common(2)
                court_analysis[court_key] = {
                    'matches': matches,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'top_players': [{'name': p, 'matches': c} for p, c in top_players_court]
                }
            
            # Build top_players list
            for p, stat in player_stats.items():
                matches = stat['matches']
                wins = stat['wins']
                win_rate = round((wins / matches) * 100, 1) if matches > 0 else 0
                
                # Best court
                best_court = max(stat['courts'].items(), key=lambda x: x[1])[0] if stat['courts'] else ''
                
                # Best partner
                best_partner = max(stat['partners'].items(), key=lambda x: x[1])[0] if stat['partners'] else ''
                
                top_players.append({
                    'name': p,
                    'matches': matches,
                    'win_rate': win_rate,
                    'best_court': best_court,
                    'best_partner': best_partner
                })
            
            # Sort top_players by matches played, then win rate
            top_players.sort(key=lambda x: (-x['matches'], -x['win_rate'], x['name']))
        
        if not team_stats:
            return {
                'team_data': {
                    'team': team,
                    'points': 'N/A',
                    'matches': {'won': 0, 'lost': 0, 'percentage': 'N/A'},
                    'lines': {'percentage': 'N/A'},
                    'sets': {'percentage': 'N/A'},
                    'games': {'percentage': 'N/A'}
                },
                'court_analysis': court_analysis,
                'top_players': top_players,
                'error': f'No stats found for team: {team}'
            }
        
        return {
            'team_data': team_stats,
            'court_analysis': court_analysis,
            'top_players': top_players
        }
        
    except Exception as e:
        print(f"Error getting mobile team data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'team_data': None,
            'court_analysis': {},
            'top_players': [],
            'error': str(e)
        }

def get_mobile_series_data(user):
    """Get series data for mobile my series page"""
    try:
        # The series data is now handled directly by the API endpoint
        # This function can just return session data and let the frontend handle the API call
        return {
            'user_series': user.get('series'),
            'user_club': user.get('club'),
            'success': True
        }
    except Exception as e:
        print(f"Error getting mobile series data: {str(e)}")
        return {
            'error': str(e)
        }

def get_teams_players_data(user):
    """Get teams and players data for mobile interface"""
    try:
        from flask import request
        import os
        
        # Get team parameter from request
        team = request.args.get('team')
        
        # Load data files
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        stats_path = os.path.join(project_root, 'data', 'series_stats.json')
        matches_path = os.path.join(project_root, 'data', 'match_history.json')
        
        with open(stats_path, 'r') as f:
            all_stats = json.load(f)
        with open(matches_path, 'r') as f:
            all_matches = json.load(f)
        
        # Filter out BYE teams
        all_teams = sorted({s['team'] for s in all_stats if 'BYE' not in s['team'].upper()})
        
        if not team or team not in all_teams:
            # No team selected or invalid team
            return {
                'team_analysis_data': None,
                'all_teams': all_teams,
                'selected_team': None
            }
        
        # Get team stats and matches
        team_stats = next((s for s in all_stats if s.get('team') == team), {})
        team_matches = [m for m in all_matches if m.get('Home Team') == team or m.get('Away Team') == team]
        
        # Calculate team analysis using the helper function
        team_analysis_data = calculate_team_analysis_mobile(team_stats, team_matches, team)
        
        return {
            'team_analysis_data': team_analysis_data,
            'all_teams': all_teams,
            'selected_team': team
        }
        
    except Exception as e:
        print(f"Error getting teams players data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'team_analysis_data': None,
            'all_teams': [],
            'selected_team': None,
            'error': str(e)
        }

def transform_team_stats_to_overview_mobile(stats):
    """Transform team stats to overview format for mobile use"""
    matches = stats.get("matches", {})
    lines = stats.get("lines", {})
    sets = stats.get("sets", {})
    games = stats.get("games", {})
    points = stats.get("points", 0)
    
    overview = {
        "points": points,
        "match_win_rate": float(matches.get("percentage", "0").replace("%", "")),
        "match_record": f"{matches.get('won', 0)}-{matches.get('lost', 0)}",
        "line_win_rate": float(lines.get("percentage", "0").replace("%", "")),
        "set_win_rate": float(sets.get("percentage", "0").replace("%", "")),
        "game_win_rate": float(games.get("percentage", "0").replace("%", ""))
    }
    return overview

def calculate_team_analysis_mobile(team_stats, team_matches, team):
    """Calculate comprehensive team analysis for mobile interface"""
    try:
        # Use the same transformation as desktop for correct stats
        overview = transform_team_stats_to_overview_mobile(team_stats)
        
        # Match Patterns
        total_matches = len(team_matches)
        straight_set_wins = 0
        comeback_wins = 0
        three_set_wins = 0
        three_set_losses = 0
        
        for match in team_matches:
            is_home = match.get('Home Team') == team
            winner_is_home = match.get('Winner') == 'home'
            team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
            sets = match.get('Sets', [])
            
            # Get the scores
            scores = match.get('Scores', '').split(', ')
            if len(scores) == 2 and team_won:
                straight_set_wins += 1
            if len(scores) == 3:
                if team_won:
                    three_set_wins += 1
                    # Check for comeback win - lost first set but won the match
                    if scores[0]:
                        first_set = scores[0].split('-')
                        if len(first_set) == 2:
                            try:
                                home_score, away_score = map(int, first_set)
                                if is_home and home_score < away_score:
                                    comeback_wins += 1
                                elif not is_home and away_score < home_score:
                                    comeback_wins += 1
                            except ValueError:
                                pass  # Skip if scores can't be parsed
                else:
                    three_set_losses += 1
        
        three_set_record = f"{three_set_wins}-{three_set_losses}"
        match_patterns = {
            'total_matches': total_matches,
            'set_win_rate': overview['set_win_rate'],
            'three_set_record': three_set_record,
            'straight_set_wins': straight_set_wins,
            'comeback_wins': comeback_wins
        }
        
        # Court Analysis
        court_analysis = {}
        for i in range(1, 5):
            court_name = f'Court {i}'
            court_matches = [m for idx, m in enumerate(team_matches) if (idx % 4) + 1 == i]
            wins = losses = 0
            player_win_counts = {}
            
            for match in court_matches:
                is_home = match.get('Home Team') == team
                winner_is_home = match.get('Winner') == 'home'
                team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
                
                if team_won:
                    wins += 1
                else:
                    losses += 1
                
                players = [match.get('Home Player 1'), match.get('Home Player 2')] if is_home else [match.get('Away Player 1'), match.get('Away Player 2')]
                for p in players:
                    if not p: 
                        continue
                    if p not in player_win_counts:
                        player_win_counts[p] = {'matches': 0, 'wins': 0}
                    player_win_counts[p]['matches'] += 1
                    if team_won:
                        player_win_counts[p]['wins'] += 1
            
            win_rate = round((wins / (wins + losses) * 100), 1) if (wins + losses) > 0 else 0
            record = f"{wins}-{losses} ({win_rate}%)"
            
            # Top players by win rate (min 2 matches)
            key_players = sorted([
                {'name': p, 'win_rate': round((d['wins']/d['matches'])*100, 1), 'matches': d['matches']}
                for p, d in player_win_counts.items() if d['matches'] >= 2
            ], key=lambda x: -x['win_rate'])[:2]
            
            # Summary sentence
            if win_rate >= 60:
                perf = 'strong performance'
            elif win_rate >= 45:
                perf = 'solid performance'
            else:
                perf = 'average performance'
            
            if key_players:
                contributors = ' and '.join([
                    f"{kp['name']} ({kp['win_rate']}% in {kp['matches']} matches)" for kp in key_players
                ])
                summary = f"This court has shown {perf} with a {win_rate}% win rate. Key contributors: {contributors}."
            else:
                summary = f"This court has shown {perf} with a {win_rate}% win rate."
            
            court_analysis[court_name] = {
                'record': record,
                'win_rate': win_rate,
                'key_players': key_players,
                'summary': summary
            }
        
        # Top Players Table
        player_stats = {}
        for match in team_matches:
            is_home = match.get('Home Team') == team
            player1 = match.get('Home Player 1') if is_home else match.get('Away Player 1')
            player2 = match.get('Home Player 2') if is_home else match.get('Away Player 2')
            winner_is_home = match.get('Winner') == 'home'
            team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
            
            for player in [player1, player2]:
                if not player: 
                    continue
                if player not in player_stats:
                    player_stats[player] = {'matches': 0, 'wins': 0, 'courts': {}, 'partners': {}}
                
                player_stats[player]['matches'] += 1
                if team_won:
                    player_stats[player]['wins'] += 1
                
                # Court
                court_idx = team_matches.index(match) % 4 + 1
                court = f'Court {court_idx}'
                if court not in player_stats[player]['courts']:
                    player_stats[player]['courts'][court] = {'matches': 0, 'wins': 0}
                player_stats[player]['courts'][court]['matches'] += 1
                if team_won:
                    player_stats[player]['courts'][court]['wins'] += 1
                
                # Partner
                partner = player2 if player == player1 else player1
                if partner:
                    if partner not in player_stats[player]['partners']:
                        player_stats[player]['partners'][partner] = {'matches': 0, 'wins': 0}
                    player_stats[player]['partners'][partner]['matches'] += 1
                    if team_won:
                        player_stats[player]['partners'][partner]['wins'] += 1
        
        top_players = []
        for name, stats in player_stats.items():
            if stats['matches'] < 3: 
                continue
            win_rate = round((stats['wins']/stats['matches'])*100, 1) if stats['matches'] > 0 else 0
            
            # Best court
            best_court = None
            best_court_rate = 0
            for court, cstats in stats['courts'].items():
                if cstats['matches'] >= 2:
                    rate = round((cstats['wins']/cstats['matches'])*100, 1)
                    if rate > best_court_rate:
                        best_court_rate = rate
                        best_court = f"{court} ({rate}%)"
            
            # Best partner
            best_partner = None
            best_partner_rate = 0
            for partner, pstats in stats['partners'].items():
                if pstats['matches'] >= 2:
                    rate = round((pstats['wins']/pstats['matches'])*100, 1)
                    if rate > best_partner_rate:
                        best_partner_rate = rate
                        best_partner = f"{partner} ({rate}%)"
            
            top_players.append({
                'name': name,
                'matches': stats['matches'],
                'win_rate': win_rate,
                'best_court': best_court or 'N/A',
                'best_partner': best_partner or 'N/A'
            })
        
        top_players = sorted(top_players, key=lambda x: -x['win_rate'])
        
        # Narrative summary
        summary = (
            f"{team} has accumulated {overview['points']} points this season with a "
            f"{overview['match_win_rate']}% match win rate. The team shows "
            f"strong resilience with {match_patterns['comeback_wins']} comeback victories "
            f"and has won {match_patterns['straight_set_wins']} matches in straight sets.\n"
            f"Their performance metrics show a {overview['game_win_rate']}% game win rate and "
            f"{overview['set_win_rate']}% set win rate, with particularly "
            f"{'strong' if overview['line_win_rate'] >= 50 else 'consistent'} line play at "
            f"{overview['line_win_rate']}%.\n"
            f"In three-set matches, the team has a record of {match_patterns['three_set_record']}, "
            f"demonstrating their {'strength' if three_set_wins > three_set_losses else 'areas for improvement'} in extended matches."
        )
        
        return {
            'overview': overview,
            'match_patterns': match_patterns,
            'court_analysis': court_analysis,
            'top_players': top_players,
            'summary': summary
        }
        
    except Exception as e:
        print(f"Error calculating team analysis: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'overview': {},
            'match_patterns': {},
            'court_analysis': {},
            'top_players': [],
            'summary': f"Error calculating team analysis: {str(e)}"
        }

def get_player_search_data(user):
    """Get player search data for mobile player search page"""
    try:
        from flask import request
        
        # Get search parameters from request
        first_name = request.args.get('first_name', '').strip()
        last_name = request.args.get('last_name', '').strip()
        search_attempted = bool(first_name or last_name)
        matching_players = []
        search_query = None
        
        if search_attempted:
            # Build search query description
            if first_name and last_name:
                search_query = f'"{first_name} {last_name}"'
            elif first_name:
                search_query = f'first name "{first_name}"'
            elif last_name:
                search_query = f'last name "{last_name}"'
            
            # Search for matching players using enhanced fuzzy logic
            matching_players = search_players_with_fuzzy_logic_mobile(first_name, last_name)
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'search_attempted': search_attempted,
            'matching_players': matching_players,
            'search_query': search_query
        }
        
    except Exception as e:
        print(f"Error getting player search data: {str(e)}")
        return {
            'first_name': '',
            'last_name': '',
            'search_attempted': False,
            'matching_players': [],
            'search_query': None,
            'error': str(e)
        }

def search_players_with_fuzzy_logic_mobile(first_name_query, last_name_query):
    """
    Search for players using enhanced fuzzy logic from the backup implementation.
    This is the mobile-specific version that returns data in the format expected by the template.
    
    Args:
        first_name_query: First name to search for (can be empty)
        last_name_query: Last name to search for (can be empty)
        
    Returns:
        list: List of matching player dictionaries with name and basic info
    """
    try:
        # Load player history data
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        player_history_path = os.path.join(project_root, 'data', 'player_history.json')
        
        with open(player_history_path, 'r') as f:
            all_players = json.load(f)
            
        from utils.match_utils import names_match, normalize_name
        
        matching_players = []
        
        for player in all_players:
            player_name = player.get('name', '')
            if not player_name:
                continue
                
            # Parse player name - handle both "First Last" and "Last, First" formats
            if ',' in player_name:
                # Format: "Last, First"
                p_last, p_first = [part.strip() for part in player_name.split(',', 1)]
            else:
                # Format: "First Last"
                parts = player_name.strip().split()
                if len(parts) >= 2:
                    p_first = parts[0]
                    p_last = ' '.join(parts[1:])
                else:
                    # Single name - treat as last name
                    p_first = ''
                    p_last = player_name.strip()
            
            # Determine if this player matches the search criteria
            matches = False
            
            if first_name_query and last_name_query:
                # Both names provided - check both with fuzzy matching
                first_match = names_match(first_name_query, p_first) if p_first else False
                last_match = normalize_name(last_name_query) == normalize_name(p_last)
                matches = first_match and last_match
                
            elif first_name_query and not last_name_query:
                # Only first name provided - fuzzy match on first name
                matches = names_match(first_name_query, p_first) if p_first else False
                
            elif last_name_query and not first_name_query:
                # Only last name provided - fuzzy match on last name
                matches = (normalize_name(last_name_query) == normalize_name(p_last) or
                          last_name_query.lower() in p_last.lower())
            
            if matches:
                # Get additional player info
                latest_match = player.get('matches', [])[-1] if player.get('matches') else {}
                current_pti = latest_match.get('end_pti') if latest_match else player.get('pti', 'N/A')
                
                # Format current_pti for display
                if current_pti == 'N/A' or current_pti is None:
                    current_pti_display = 'N/A'
                else:
                    try:
                        current_pti_display = f"{float(current_pti):.1f}"
                    except (ValueError, TypeError):
                        current_pti_display = 'N/A'
                
                matching_players.append({
                    'name': player_name,
                    'first_name': p_first,
                    'last_name': p_last,
                    'player_id': player.get('player_id', ''),
                    'current_pti': current_pti_display,
                    'total_matches': len(player.get('matches', [])),
                    'club': latest_match.get('club') if latest_match else 'Unknown',
                    'series': latest_match.get('series') if latest_match else 'Unknown'
                })
        
        # Sort by name for consistent results
        matching_players.sort(key=lambda x: x['name'].lower())
        
        return matching_players
        
    except Exception as e:
        print(f"Error in fuzzy player search: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []

def get_mobile_availability_data(user):
    """Get availability data for mobile availability page"""
    try:
        # Get matches and practices for the user's series
        user_email = user.get('email', '')
        
        print(f"Getting availability data for user: {user_email}")
        
        # Get user's club and series from database
        user_query = """
            SELECT u.email, c.name as club_name, s.name as series_name
            FROM users u 
            LEFT JOIN clubs c ON u.club_id = c.id 
            LEFT JOIN series s ON u.series_id = s.id 
            WHERE u.email = %s
        """
        
        user_result = execute_query_one(user_query, (user_email,))
        
        if not user_result:
            print(f"No user found for email: {user_email}")
            return {
                'match_avail_pairs': [],
                'players': [{'name': user_email}],
                'error': 'User not found in database'
            }
        
        club_name = user_result.get('club_name', '')
        series_name = user_result.get('series_name', '')
        
        print(f"User club: {club_name}, series: {series_name}")
        
        # Get matches from schedules.json for this club/series
        try:
            # Fix path construction to use project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            schedules_path = os.path.join(project_root, 'data', 'schedules.json')
            
            with open(schedules_path, 'r') as f:
                all_matches = json.load(f)
            
            print(f"[DEBUG] Loaded {len(all_matches)} total matches from schedules.json")
            
            # Filter matches for this user's club
            user_matches = []
            for match in all_matches:
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                practice_field = match.get('Practice', '')
                
                # Extract series number from series name (e.g., "Chicago 22" -> "22")
                series_number = None
                if series_name:
                    # Handle different series name formats
                    if 'Chicago' in series_name:
                        # Extract number from "Chicago 22" format
                        parts = series_name.split()
                        if len(parts) >= 2 and parts[-1].isdigit():
                            series_number = parts[-1]
                    else:
                        # If series name is just a number or different format
                        import re
                        number_match = re.search(r'\d+', series_name)
                        if number_match:
                            series_number = number_match.group()
                
                print(f"Looking for club '{club_name}' with series number '{series_number}'")
                
                # Check if this match involves the user's club AND series
                def team_matches_user(team_name):
                    if not team_name or not club_name:
                        return False
                    
                    # Check if club name is in team name
                    if club_name not in team_name:
                        return False
                    
                    # If we have a series number, check that it matches
                    if series_number:
                        # Team format is like "Tennaqua - 22" (updated format)
                        # Look for the series number in the team name
                        team_parts = team_name.split(' - ')
                        if len(team_parts) >= 2:
                            # Check if the last part matches our series number
                            team_series = team_parts[-1].strip()
                            if team_series != series_number:
                                return False
                        else:
                            # If team name doesn't have the expected format, be more flexible
                            # but still try to match series number
                            import re
                            team_numbers = re.findall(r'\b\d+\b', team_name)
                            if team_numbers and series_number not in team_numbers:
                                return False
                    
                    return True
                
                # Check home team, away team, and practice field
                if (team_matches_user(home_team) or team_matches_user(away_team) or 
                    (practice_field and team_matches_user(practice_field))):
                    user_matches.append(match)
                    print(f"  ✓ Match found: {home_team} vs {away_team}")
            
            print(f"Found {len(user_matches)} matches for user's club '{club_name}' in series '{series_name}'")
            
            # For now, return basic structure
            return {
                'match_avail_pairs': [(match, {'status': None}) for match in user_matches],
                'players': [{'name': user_email}]
            }
        
        except Exception as e:
            print(f"Error loading schedules: {str(e)}")
            return {
                'match_avail_pairs': [],
                'players': [{'name': user_email}],
                'error': f'Error loading schedules: {str(e)}'
            }
        
    except Exception as e:
        print(f"Error getting mobile availability data: {str(e)}")
        return {
            'error': str(e)
        }

def get_mobile_club_data(user):
    """Get club data for mobile my club page"""
    try:
        club_name = user.get('club', '')
        series = user.get('series', '')
        
        print(f"[DEBUG] get_mobile_club_data called with user: {user}")
        print(f"[DEBUG] club_name: '{club_name}', series: '{series}'")
        
        if not club_name:
            print(f"[DEBUG] No club name found, returning error")
            return {
                'team_name': 'Unknown',
                'this_week_results': [],
                'tennaqua_standings': [],
                'head_to_head': [],
                'player_streaks': [],
                'error': 'No club information found in user profile'
            }
        
        # Extract series number from series string (e.g. "Chicago 22" -> "22")
        series_number = None
        if series:
            import re
            match = re.search(r'\d+', series)
            if match:
                series_number = match.group()
        
        print(f"[DEBUG] Extracted series number: '{series_number}' from series: '{series}'")
        
        # Construct expected team name format: "Club - SeriesNumber"
        if series_number:
            expected_team_name = f"{club_name} - {series_number}"
        else:
            expected_team_name = club_name
        
        print(f"[DEBUG] Looking for team: '{expected_team_name}'")
        
        # Load match history data
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        schedules_path = os.path.join(project_root, 'data', 'schedules.json')
        series_stats_path = os.path.join(project_root, 'data', 'series_stats.json')
        
        print(f"[DEBUG] schedules_path: {schedules_path}")
        print(f"[DEBUG] series_stats_path: {series_stats_path}")
        print(f"[DEBUG] schedules exists: {os.path.exists(schedules_path)}")
        print(f"[DEBUG] series_stats exists: {os.path.exists(series_stats_path)}")
        
        # Initialize return data
        this_week_results = []
        tennaqua_standings = []
        head_to_head = []
        player_streaks = []
        
        # Get recent match results from schedules (these are scheduled matches, not completed ones)
        try:
            with open(schedules_path, 'r') as f:
                matches_data = json.load(f)
            
            print(f"[DEBUG] Loaded {len(matches_data)} total matches from schedules.json")
            
            # Filter matches for this specific team (club + series)
            club_matches = []
            for match in matches_data:
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                
                # Check if our specific team is in this match
                if expected_team_name == home_team or expected_team_name == away_team:
                    club_matches.append(match)
                # Also check broader club name for backwards compatibility
                elif club_name in home_team or club_name in away_team:
                    # Only include if series number matches (to avoid mixing series)
                    if series_number:
                        if (series_number in home_team and club_name in home_team) or \
                           (series_number in away_team and club_name in away_team):
                            club_matches.append(match)
                    else:
                        club_matches.append(match)
            
            print(f"[DEBUG] Found {len(club_matches)} matches for team '{expected_team_name}'")
            if club_matches:
                print(f"[DEBUG] Sample match: {club_matches[0]}")
            
            # Note: schedules.json contains future/scheduled matches, not completed matches with results
            # So we'll show recent scheduled matches instead of completed results
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            week_ahead = datetime.now() + timedelta(days=7)
            
            for match in club_matches:
                match_date_str = match.get('date', '')
                if match_date_str:
                    try:
                        # Try different date formats
                        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d-%b-%y']:
                            try:
                                match_date = datetime.strptime(match_date_str, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            continue
                        
                        # Include matches from this week (past or upcoming)
                        if week_ago <= match_date <= week_ahead:
                            is_home = match.get('home_team') == expected_team_name
                            opponent = match.get('away_team') if is_home else match.get('home_team')
                            
                            result = {
                                'date': match_date_str,
                                'opponent': opponent,
                                'home_team': match.get('home_team', ''),
                                'away_team': match.get('away_team', ''),
                                'location': match.get('location', ''),
                                'time': match.get('time', ''),
                                'is_home': is_home
                            }
                            this_week_results.append(result)
                    except Exception as e:
                        continue
            
            # Sort by date (most recent first)
            this_week_results.sort(key=lambda x: x.get('date', ''), reverse=True)
            
        except Exception as e:
            print(f"Error loading matches data: {str(e)}")
        
        # Get series standings if Tennaqua
        if 'tennaqua' in club_name.lower():
            try:
                with open(series_stats_path, 'r') as f:
                    stats_data = json.load(f)
                
                print(f"[DEBUG] Loaded {len(stats_data)} team stats from series_stats.json")
                
                # Find teams in the same series as the user
                user_team_stats = None
                for team_stats in stats_data:
                    if team_stats.get('team') == expected_team_name:
                        user_team_stats = team_stats
                        break
                
                if user_team_stats:
                    user_series = user_team_stats.get('series', '')
                    print(f"[DEBUG] Found user team stats, series: '{user_series}'")
                    
                    # Get all Tennaqua teams in the same series
                    series_teams = []
                    for team_stats in stats_data:
                        if team_stats.get('series') == user_series and \
                           team_stats.get('team', '').lower().startswith('tennaqua'):
                            series_teams.append(team_stats)
                    
                    print(f"[DEBUG] Found {len(series_teams)} Tennaqua teams in series '{user_series}'")
                    
                    # Calculate average points for ranking
                    for team in series_teams:
                        matches = team.get('matches', {})
                        total_matches = sum(matches.get(k, 0) for k in ['won', 'lost', 'tied'])
                        total_points = float(team.get('points', 0))
                        team['avg_points'] = round(total_points / total_matches, 1) if total_matches > 0 else 0
                    
                    # Sort by points (highest first)
                    series_teams.sort(key=lambda x: float(x.get('points', 0)), reverse=True)
                    
                    # Add standings for each Tennaqua team
                    for i, team in enumerate(series_teams, 1):
                        tennaqua_standings.append({
                            'series': team.get('series', ''),
                            'team_name': team.get('team', ''),
                            'place': i,
                            'total_points': team.get('points', 0),
                            'avg_points': team.get('avg_points', 0),
                            'playoff_contention': i <= 8
                        })
                else:
                    print(f"[DEBUG] No team stats found for '{expected_team_name}'")
                
            except Exception as e:
                print(f"Error loading series stats: {str(e)}")
                import traceback
                print(f"Full traceback: {traceback.format_exc()}")
        
        # Calculate head-to-head records (simplified since schedules.json doesn't have results)
        # We can show opponents we've played against
        try:
            opponent_counts = {}
            for match in club_matches:
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                
                if expected_team_name == home_team:
                    opponent = away_team.split(' - ')[0] if ' - ' in away_team else away_team
                elif expected_team_name == away_team:
                    opponent = home_team.split(' - ')[0] if ' - ' in home_team else home_team
                else:
                    continue
                
                if opponent not in opponent_counts:
                    opponent_counts[opponent] = 0
                opponent_counts[opponent] += 1
            
            # Convert to list showing number of matches scheduled
            head_to_head = [
                {
                    'opponent': opponent,
                    'matches_scheduled': count,
                    'wins': 'TBD',  # To be determined from actual results
                    'losses': 'TBD',
                    'win_rate': 'TBD'
                }
                for opponent, count in opponent_counts.items()
            ]
            head_to_head.sort(key=lambda x: x['matches_scheduled'], reverse=True)
            
        except Exception as e:
            print(f"Error calculating head-to-head: {str(e)}")
        
        # Player streaks would need actual match results, so skip for now
        # This would require a different data source with completed matches
        
        return {
            'team_name': expected_team_name,
            'this_week_results': this_week_results,
            'tennaqua_standings': tennaqua_standings,
            'head_to_head': head_to_head,
            'player_streaks': player_streaks
        }
        
    except Exception as e:
        print(f"Error getting mobile club data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'team_name': user.get('club', 'Unknown'),
            'this_week_results': [],
            'tennaqua_standings': [],
            'head_to_head': [],
            'player_streaks': [],
            'error': str(e)
        }

def get_mobile_player_stats(user):
    """Get player stats for mobile player stats page"""
    try:
        # TODO: Extract player stats logic from server.py
        return {
            'player_stats': {},
            'recent_matches': [],
            'error': 'Function not yet extracted from server.py'
        }
    except Exception as e:
        print(f"Error getting mobile player stats: {str(e)}")
        return {
            'error': str(e)
        }

def get_practice_times_data(user):
    """Get practice times data for mobile practice times page"""
    try:
        # Get user's club and series information for context
        user_club = user.get('club', '')
        user_series = user.get('series', '')
        
        # For now, this just returns context data for the form
        # The actual logic is in the API endpoints for add/remove
        return {
            'user_club': user_club,
            'user_series': user_series,
            'practice_times': [],
            'user_preferences': {},
        }
    except Exception as e:
        print(f"Error getting practice times data: {str(e)}")
        return {
            'user_club': user.get('club', ''),
            'user_series': user.get('series', ''),
            'practice_times': [],
            'user_preferences': {},
            'error': str(e)
        }

def get_all_team_availability_data(user, selected_date=None):
    """Get all team availability data for mobile page"""
    try:
        # TODO: Extract all team availability logic from server.py
        return {
            'players_schedule': {},
            'selected_date': selected_date or 'today',
            'error': 'Function not yet extracted from server.py'
        }
    except Exception as e:
        print(f"Error getting all team availability data: {str(e)}")
        return {
            'players_schedule': {},
            'selected_date': selected_date or 'today',
            'error': str(e)
        }

def get_club_players_data(user, series_filter=None, first_name_filter=None, last_name_filter=None, pti_min=None, pti_max=None):
    """Get all players at the user's club with optional filtering"""
    try:
        # TODO: Extract club players logic from server.py
        return {
            'players': [],
            'available_series': [],
            'pti_range': {'min': 0, 'max': 100},
            'error': 'Function not yet extracted from server.py'
        }
    except Exception as e:
        print(f"Error getting club players data: {str(e)}")
        return {
            'players': [],
            'available_series': [],
            'pti_range': {'min': 0, 'max': 100},
            'error': str(e)
        }

def get_mobile_improve_data(user):
    """Get data for the mobile improve page including paddle tips and training guide"""
    try:
        # Load paddle tips from JSON file
        paddle_tips = []
        try:
            # Use current working directory since server.py runs from project root
            tips_path = os.path.join('data', 'improve_data', 'paddle_tips.json')
            with open(tips_path, 'r', encoding='utf-8') as f:
                tips_data = json.load(f)
                paddle_tips = tips_data.get('paddle_tips', [])
        except Exception as tips_error:
            print(f"Error loading paddle tips: {str(tips_error)}")
            # Continue without tips if file can't be loaded
        
        # Load training guide data for video references
        training_guide = {}
        try:
            # Use current working directory since server.py runs from project root
            guide_path = os.path.join('data', 'improve_data', 'complete_platform_tennis_training_guide.json')
            with open(guide_path, 'r', encoding='utf-8') as f:
                training_guide = json.load(f)
        except Exception as guide_error:
            print(f"Error loading training guide: {str(guide_error)}")
            # Continue without training guide if file can't be loaded
        
        return {
            'paddle_tips': paddle_tips,
            'training_guide': training_guide
        }
        
    except Exception as e:
        print(f"Error getting mobile improve data: {str(e)}")
        return {
            'paddle_tips': [],
            'training_guide': {},
            'error': str(e)
        } 