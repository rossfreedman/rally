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

def _load_players_data():
    """Load player data fresh from JSON file - no caching"""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        players_path = os.path.join(project_root, 'data', 'players.json')
        
        # Always load fresh data
        with open(players_path, 'r') as f:
            players_data = json.load(f)
        
        print(f"Loaded fresh player data ({len(players_data)} players)")
        return players_data
        
    except Exception as e:
        print(f"Error loading player data: {e}")
        return []

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
    # Use tenniscores_player_id as primary search method
    tenniscores_player_id = user.get('tenniscores_player_id')
    session_player_name = f"{user['first_name']} {user['last_name']}"
    print(f"[DEBUG] Looking for player with ID: '{tenniscores_player_id}' (session name: '{session_player_name}')")
    
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
    actual_player_name = None  # This will store the actual name from the player record
    
    # Search by tenniscores_player_id (most reliable)
    if tenniscores_player_id:
        print(f"[DEBUG] Searching by player_id: '{tenniscores_player_id}'")
        
        # Debug: Print first few player records to see what IDs are available
        print(f"[DEBUG] Sample player IDs in data: {[p.get('player_id', 'None') for p in all_players[:5]]}")
        
        player = next((p for p in all_players if p.get('player_id') == tenniscores_player_id), None)
        if player:
            actual_player_name = player.get('name', session_player_name)
            print(f"[DEBUG] Found player by ID: '{actual_player_name}' (ID: {tenniscores_player_id})")
        else:
            print(f"[DEBUG] No player found with ID: '{tenniscores_player_id}'")
            # Debug: Check if any players have similar IDs
            similar_ids = [p.get('player_id') for p in all_players if p.get('player_id') and tenniscores_player_id.lower() in p.get('player_id', '').lower()]
            print(f"[DEBUG] Similar player IDs found: {similar_ids[:5]}")
    else:
        print(f"[DEBUG] No tenniscores_player_id provided in user session")
    
    # If we don't have a player ID or it failed, return error instead of falling back to name matching
    if not player:
        print(f"[DEBUG] Player not found by reliable ID lookup - no fallback to name matching")
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
            'error': f'Player not found with ID: {tenniscores_player_id}' if tenniscores_player_id else 'No player ID available'
        }
    
    # --- 2. Load all matches for this player ---
    try:
        with open(matches_path, 'r') as f:
            all_matches = json.load(f)
    except Exception as e:
        all_matches = []
    
    # --- 2.5. Create name-to-ID mapping from player data for match filtering ---
    name_to_id_mapping = {}
    for p in all_players:
        player_name = p.get('name', '')
        player_id = p.get('player_id', '')
        if player_name and player_id:
            name_to_id_mapping[normalize(player_name)] = player_id
    
    print(f"[DEBUG] Created name-to-ID mapping for {len(name_to_id_mapping)} players")

    # Helper function to check if target player ID is in a match
    def player_id_in_match(match, target_player_id):
        """Check if target_player_id is in the match by converting player names to IDs"""
        match_players = [
            match.get('Home Player 1', ''),
            match.get('Home Player 2', ''),
            match.get('Away Player 1', ''),
            match.get('Away Player 2', '')
        ]
        
        # Convert match player names to IDs and check if target ID is present
        for match_player_name in match_players:
            if match_player_name:
                normalized_name = normalize(match_player_name)
                match_player_id = name_to_id_mapping.get(normalized_name)
                if match_player_id == target_player_id:
                    return True
        return False
    
    def get_player_position_in_match_by_id(match, target_player_id):
        """Get the position (home/away and 1/2) of target player in match using ID"""
        match_players = [
            ('Home Player 1', match.get('Home Player 1', '')),
            ('Home Player 2', match.get('Home Player 2', '')),
            ('Away Player 1', match.get('Away Player 1', '')),
            ('Away Player 2', match.get('Away Player 2', ''))
        ]
        
        for position, match_player_name in match_players:
            if match_player_name:
                normalized_name = normalize(match_player_name)
                match_player_id = name_to_id_mapping.get(normalized_name)
                if match_player_id == target_player_id:
                    return position
        return None
    
    def get_partner_for_player_by_id(match, target_player_id):
        """Get the partner of target player in the match using ID"""
        position = get_player_position_in_match_by_id(match, target_player_id)
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
    
    # --- 4. Filter matches for current season/series using ACTUAL player name ---
    player_matches = []
    if player and actual_player_name:
        print(f"[DEBUG] Filtering matches for actual player name: '{actual_player_name}'")
        for m in all_matches:
            # Use actual_player_name instead of session-constructed name
            if player_id_in_match(m, tenniscores_player_id):
                if current_series:
                    match_series = str(m.get('Series', ''))
                    if match_series and match_series != current_series:
                        continue
                player_matches.append(m)
        print(f"[DEBUG] Found {len(player_matches)} matches for player using actual name")
    
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
            # Check if player is in this match using ACTUAL player name
            if not player_id_in_match(match, tenniscores_player_id):
                continue
            total_matches += 1
            
            # Determine if player is home team (using actual player name)
            position = get_player_position_in_match_by_id(match, tenniscores_player_id)
            is_home = position and position.startswith('Home')
            
            won = (is_home and match.get('Winner') == 'home') or (not is_home and match.get('Winner') == 'away')
            if won:
                wins += 1
                court_stats[f'court{court_num}']['wins'] += 1
            else:
                losses += 1
                court_stats[f'court{court_num}']['losses'] += 1
            court_stats[f'court{court_num}']['matches'] += 1
            
            # Identify partner (using actual player name)
            partner = get_partner_for_player_by_id(match, tenniscores_player_id)
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

def get_recent_matches_for_user_club(user):
    """
    Get the last 10 weeks of matches for a user's club, grouped by date.
    
    Args:
        user: User object containing club information
        
    Returns:
        Dict with matches grouped by date for the last 10 weeks
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        match_history_path = os.path.join(project_root, 'data', 'match_history.json')
        
        with open(match_history_path, 'r') as f:
            all_matches = json.load(f)
            
        if not user or not user.get('club'):
            return {}
            
        user_club = user['club']
        # Filter matches where user's club is either home or away team
        # Make sure to capture ALL teams from this club across ALL series
        club_matches = []
        for match in all_matches:
            home_team = match.get('Home Team', '')
            away_team = match.get('Away Team', '')
            
            # Check if either team belongs to the user's club
            # Use more flexible matching to catch all team variations
            home_club_match = (user_club in home_team) if home_team else False
            away_club_match = (user_club in away_team) if away_team else False
            
            if home_club_match or away_club_match:
                # Normalize keys to snake_case
                normalized_match = {
                    'date': match.get('Date', ''),
                    'time': match.get('Time', ''),
                    'location': match.get('Location', ''),
                    'home_team': home_team,
                    'away_team': away_team,
                    'winner': match.get('Winner', ''),
                    'scores': match.get('Scores', ''),
                    'home_player_1': match.get('Home Player 1', ''),
                    'home_player_2': match.get('Home Player 2', ''),
                    'away_player_1': match.get('Away Player 1', ''),
                    'away_player_2': match.get('Away Player 2', ''),
                    'court': match.get('Court', ''),
                    'series': match.get('Series', '')
                }
                club_matches.append(normalized_match)
        
        print(f"[DEBUG] Found {len(club_matches)} total matches for club '{user_club}' across all series")
        
        # Sort matches by date to get chronological order
        def parse_date(date_str):
            for fmt in ("%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.min
        
        sorted_matches = sorted(club_matches, key=lambda x: parse_date(x['date']), reverse=True)
        
        if not sorted_matches:
            return {}
        
        # Group matches by date and get the last 10 unique dates
        matches_by_date = {}
        for match in sorted_matches:
            date = match['date']
            if date not in matches_by_date:
                matches_by_date[date] = []
            matches_by_date[date].append(match)
        
        print(f"[DEBUG] Matches grouped by date:")
        for date, date_matches in matches_by_date.items():
            print(f"  {date}: {len(date_matches)} matches")
        
        # Get the 10 most recent dates
        recent_dates = sorted(matches_by_date.keys(), key=parse_date, reverse=True)[:10]
        print(f"[DEBUG] Selected {len(recent_dates)} most recent dates: {recent_dates}")
        
        # Build the result with only the recent dates
        recent_matches_by_date = {}
        for date in recent_dates:
            # Sort matches for this date by court number
            def court_sort_key(match):
                court = match.get('court', '')
                if not court or not str(court).strip():
                    return float('inf')  # Put empty courts at the end
                try:
                    return int(court)
                except (ValueError, TypeError):
                    return float('inf')  # Put non-numeric courts at the end
            
            sorted_date_matches = sorted(matches_by_date[date], key=court_sort_key)
            recent_matches_by_date[date] = sorted_date_matches
            print(f"[DEBUG] Date {date}: Including {len(sorted_date_matches)} matches")
        
        return recent_matches_by_date
        
    except Exception as e:
        print(f"Error getting recent matches for user club: {e}")
        return {}

def calculate_player_streaks(club_name):
    """Calculate winning and losing streaks for players across ALL matches for the club - only show significant streaks (+5/-5)"""
    try:
        # Load ALL match history data
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        match_history_path = os.path.join(project_root, 'data', 'match_history.json')
        
        with open(match_history_path, 'r') as f:
            all_matches = json.load(f)
        
        player_stats = {}
        
        # Sort matches by date, handling None values
        def parse_date(date_str):
            for fmt in ("%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.min
        
        def sort_key(x):
            date = parse_date(x.get('Date', ''))
            return date or datetime(9999, 12, 31)
        
        # Filter and normalize all matches for the club
        club_matches = []
        for match in all_matches:
            home_team = match.get('Home Team', '')
            away_team = match.get('Away Team', '')
            
            if not (home_team.startswith(club_name) or away_team.startswith(club_name)):
                continue
                
            # Normalize match data
            normalized_match = {
                'date': match.get('Date', ''),
                'home_team': home_team,
                'away_team': away_team,
                'winner': match.get('Winner', ''),
                'home_player_1': match.get('Home Player 1', ''),
                'home_player_2': match.get('Home Player 2', ''),
                'away_player_1': match.get('Away Player 1', ''),
                'away_player_2': match.get('Away Player 2', '')
            }
            club_matches.append(normalized_match)
        
        sorted_matches = sorted(club_matches, key=sort_key)
        
        print(f"[DEBUG] Found {len(sorted_matches)} total matches for club '{club_name}' across all time")
        
        for match in sorted_matches:
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            
            # Get all players from the match
            players = [
                match.get('home_player_1', ''),
                match.get('home_player_2', ''),
                match.get('away_player_1', ''),
                match.get('away_player_2', '')
            ]
            
            for player in players:
                player = player.strip()
                if not player or player.lower() == 'bye':
                    continue
                    
                if player not in player_stats:
                    player_stats[player] = {
                        'matches': [],  # Store all match results for this player
                        'series': home_team.split(' - ')[1] if ' - ' in home_team and home_team.startswith(club_name) else away_team.split(' - ')[1] if ' - ' in away_team and away_team.startswith(club_name) else '',
                    }
                
                # Determine if player won
                is_home_player = player in [match.get('home_player_1', ''), match.get('home_player_2', '')]
                won = (is_home_player and match.get('winner') == 'home') or (not is_home_player and match.get('winner') == 'away')
                
                # Store match result
                player_stats[player]['matches'].append({
                    'date': match.get('date', ''),
                    'won': won
                })
        
        # Calculate streaks for each player
        significant_streaks = []
        
        for player, stats in player_stats.items():
            if len(stats['matches']) < 5:  # Need at least 5 matches to have a significant streak
                continue
                
            matches = sorted(stats['matches'], key=lambda x: parse_date(x['date']))
            
            current_streak = 0
            best_win_streak = 0
            best_loss_streak = 0
            last_match_date = matches[-1]['date'] if matches else ''
            
            # Calculate current streak and best streaks
            for i, match in enumerate(matches):
                if i == 0:
                    current_streak = 1 if match['won'] else -1
                    best_win_streak = 1 if match['won'] else 0
                    best_loss_streak = 1 if not match['won'] else 0
                else:
                    prev_match = matches[i-1]
                    if match['won'] == prev_match['won']:
                        # Streak continues
                        if match['won']:
                            current_streak = current_streak + 1 if current_streak > 0 else 1
                            best_win_streak = max(best_win_streak, current_streak)
                        else:
                            current_streak = current_streak - 1 if current_streak < 0 else -1
                            best_loss_streak = max(best_loss_streak, abs(current_streak))
                    else:
                        # Streak broken
                        current_streak = 1 if match['won'] else -1
                        if match['won']:
                            best_win_streak = max(best_win_streak, 1)
                        else:
                            best_loss_streak = max(best_loss_streak, 1)
            
            # Only include players with significant streaks (current +5/-5 or best +5/-5)
            has_significant_current = abs(current_streak) >= 5
            has_significant_best = best_win_streak >= 5 or best_loss_streak >= 5
            
            if has_significant_current or has_significant_best:
                best_streak = max(best_win_streak, best_loss_streak)
                significant_streaks.append({
                    'player_name': player,
                    'current_streak': current_streak,
                    'best_streak': best_streak,
                    'last_match_date': last_match_date,
                    'series': stats['series'],
                    'total_matches': len(matches)
                })
        
        # Sort by current streak (win streaks highest to lowest, then loss streaks)
        significant_streaks.sort(key=lambda x: (-x['current_streak'], -x['best_streak']))
        
        print(f"[DEBUG] Found {len(significant_streaks)} players with significant streaks (+5/-5)")
        
        return significant_streaks
        
    except Exception as e:
        print(f"Error calculating player streaks: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []

def get_mobile_club_data(user):
    """Get comprehensive club data for mobile my club page - using match_history.json for completed matches"""
    try:
        club_name = user.get('club', '')
        
        print(f"[DEBUG] get_mobile_club_data called with user: {user}")
        print(f"[DEBUG] club_name: '{club_name}'")
        
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
        
        print(f"[DEBUG] Looking for matches from club: '{club_name}'")
        
        # Get recent matches from match_history.json (completed matches with results) - now grouped by date
        matches_by_date = get_recent_matches_for_user_club(user)
        
        if not matches_by_date:
            print(f"[DEBUG] No recent matches found")
            return {
                'team_name': club_name,
                'weekly_results': [],
                'tennaqua_standings': [],
                'head_to_head': [],
                'player_streaks': []
            }
        
        print(f"[DEBUG] Found matches for {len(matches_by_date)} different dates")
        
        # Process each date's matches into weekly results
        weekly_results = []
        for date, matches_data in matches_by_date.items():
            print(f"[DEBUG] Processing date {date} with {len(matches_data)} matches")
            
            # Group matches by team for this date
            team_matches = {}
            matches_processed = 0
            matches_skipped = 0
            
            for match in matches_data:
                home_team = match['home_team']
                away_team = match['away_team']
                
                if club_name in home_team:
                    team = home_team
                    opponent = away_team.split(' - ')[0] if ' - ' in away_team else away_team
                    is_home = True
                    matches_processed += 1
                elif club_name in away_team:
                    team = away_team
                    opponent = home_team.split(' - ')[0] if ' - ' in home_team else home_team
                    is_home = False
                    matches_processed += 1
                else:
                    matches_skipped += 1
                    print(f"[DEBUG] Skipping match - home: '{home_team}', away: '{away_team}' (club '{club_name}' not found)")
                    continue
                    
                if team not in team_matches:
                    team_matches[team] = {
                        'opponent': opponent,
                        'matches': [],
                        'team_points': 0,
                        'opponent_points': 0,
                        'series': team.split(' - ')[1] if ' - ' in team else team
                    }
                
                # Calculate points for this match based on set scores
                scores = match['scores'].split(', ') if match['scores'] else []
                match_team_points = 0
                match_opponent_points = 0
                
                # Points for each set
                for set_score in scores:
                    if '-' in set_score:
                        try:
                            our_score, their_score = map(int, set_score.split('-'))
                            if not is_home:
                                our_score, their_score = their_score, our_score
                                
                            if our_score > their_score:
                                match_team_points += 1
                            else:
                                match_opponent_points += 1
                        except (ValueError, IndexError):
                            continue
                            
                # Bonus point for match win
                if (is_home and match['winner'] == 'home') or (not is_home and match['winner'] == 'away'):
                    match_team_points += 1
                else:
                    match_opponent_points += 1
                    
                # Update total points
                team_matches[team]['team_points'] += match_team_points
                team_matches[team]['opponent_points'] += match_opponent_points
                
                # Add match details
                court = match.get('court', '')
                try:
                    court_num = int(court) if court and court.strip() else len(team_matches[team]['matches']) + 1
                except (ValueError, TypeError):
                    court_num = len(team_matches[team]['matches']) + 1
                    
                team_matches[team]['matches'].append({
                    'court': court_num,
                    'home_players': f"{match['home_player_1']}/{match['home_player_2']}" if is_home else f"{match['away_player_1']}/{match['away_player_2']}",
                    'away_players': f"{match['away_player_1']}/{match['away_player_2']}" if is_home else f"{match['home_player_1']}/{match['home_player_2']}",
                    'scores': match['scores'],
                    'won': (is_home and match['winner'] == 'home') or (not is_home and match['winner'] == 'away')
                })
            
            print(f"[DEBUG] Date {date}: Processed {matches_processed} matches, skipped {matches_skipped}, found {len(team_matches)} teams")
            for team, data in team_matches.items():
                print(f"  Team '{team}': {len(data['matches'])} matches vs {data['opponent']}")
            
            # Convert this date's matches to results format
            date_results = []
            for team_data in team_matches.values():
                date_results.append({
                    'series': f"Series {team_data['series']}" if team_data['series'].isdigit() else team_data['series'],
                    'opponent': team_data['opponent'],
                    'score': f"{team_data['team_points']}-{team_data['opponent_points']}",
                    'won': team_data['team_points'] > team_data['opponent_points'],
                    'match_details': sorted(team_data['matches'], key=lambda x: x['court'])
                })
                
            # Sort results by opponent name
            date_results.sort(key=lambda x: x['opponent'])
            
            # Add this week's results to the weekly results
            weekly_results.append({
                'date': date,
                'results': date_results
            })
        
        # Sort weekly results by date (most recent first)
        def parse_date(date_str):
            for fmt in ("%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.min
        
        weekly_results.sort(key=lambda x: parse_date(x['date']), reverse=True)
        
        # Calculate club standings (for all teams in the club across all series)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        stats_path = os.path.join(project_root, 'data', 'series_stats.json')
        
        tennaqua_standings = []
        try:
            with open(stats_path, 'r') as f:
                stats_data = json.load(f)
                
            for team_stats in stats_data:
                if not team_stats.get('team', '').startswith(club_name):
                    continue
                    
                series = team_stats.get('series')
                if not series:
                    continue
                    
                # Get all teams in this series
                series_teams = [team for team in stats_data if team.get('series') == series]
                
                # Calculate average points
                for team in series_teams:
                    total_matches = sum(team.get('matches', {}).get(k, 0) for k in ['won', 'lost', 'tied'])
                    total_points = float(team.get('points', 0))
                    team['avg_points'] = round(total_points / total_matches, 1) if total_matches > 0 else 0
                
                # Sort by average points
                series_teams.sort(key=lambda x: x.get('avg_points', 0), reverse=True)
                
                # Find our team's position in the series
                for i, team in enumerate(series_teams, 1):
                    if team.get('team', '').startswith(club_name) and team.get('team') == team_stats.get('team'):
                        tennaqua_standings.append({
                            'series': series,
                            'team_name': team.get('team', ''),
                            'place': i,
                            'total_points': team.get('points', 0),
                            'avg_points': team.get('avg_points', 0),
                            'playoff_contention': i <= 8,
                            'total_teams_in_series': len(series_teams)
                        })
                        break
                        
            # Sort standings by place (ascending)
            tennaqua_standings.sort(key=lambda x: x['place'])
            
        except Exception as e:
            print(f"Error loading series stats: {str(e)}")
        
        # Calculate head-to-head records
        head_to_head = {}
        
        # Load ALL match history for comprehensive head-to-head records
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            match_history_path = os.path.join(project_root, 'data', 'match_history.json')
            
            with open(match_history_path, 'r') as f:
                all_match_history = json.load(f)
            
            print(f"[DEBUG] Loading ALL match history for head-to-head: {len(all_match_history)} total matches")
            
            for match in all_match_history:
                home_team = match.get('Home Team', '')
                away_team = match.get('Away Team', '')
                winner = match.get('Winner', '')
                
                if not all([home_team, away_team, winner]):
                    continue
                    
                # Check if this match involves our club
                if club_name in home_team:
                    opponent = away_team.split(' - ')[0] if ' - ' in away_team else away_team
                    won = winner == 'home'
                elif club_name in away_team:
                    opponent = home_team.split(' - ')[0] if ' - ' in home_team else home_team
                    won = winner == 'away'
                else:
                    continue
                    
                if opponent not in head_to_head:
                    head_to_head[opponent] = {'wins': 0, 'losses': 0, 'total': 0}
                    
                head_to_head[opponent]['total'] += 1
                if won:
                    head_to_head[opponent]['wins'] += 1
                else:
                    head_to_head[opponent]['losses'] += 1
            
            print(f"[DEBUG] Found head-to-head records against {len(head_to_head)} different clubs")
            
        except Exception as e:
            print(f"Error loading all match history for head-to-head: {str(e)}")
            # Fallback to recent matches if all match history fails
            for date, matches_data in matches_by_date.items():
                for match in matches_data:
                    home_team = match.get('home_team', '')
                    away_team = match.get('away_team', '')
                    winner = match.get('winner', '')
                    
                    if not all([home_team, away_team, winner]):
                        continue
                        
                    if club_name in home_team:
                        opponent = away_team.split(' - ')[0] if ' - ' in away_team else away_team
                        won = winner == 'home'
                    elif club_name in away_team:
                        opponent = home_team.split(' - ')[0] if ' - ' in home_team else home_team
                        won = winner == 'away'
                    else:
                        continue
                        
                    if opponent not in head_to_head:
                        head_to_head[opponent] = {'wins': 0, 'losses': 0, 'total': 0}
                        
                    head_to_head[opponent]['total'] += 1
                    if won:
                        head_to_head[opponent]['wins'] += 1
                    else:
                        head_to_head[opponent]['losses'] += 1
        
        # Convert head-to-head to list
        head_to_head = [
            {
                'opponent': opponent,
                'wins': stats['wins'],
                'losses': stats['losses'],
                'total': stats['total'],
                'matches_scheduled': stats['total']  # For template compatibility
            }
            for opponent, stats in head_to_head.items()
        ]
        
        # Sort by win percentage (highest to lowest), then by total matches as tiebreaker
        head_to_head.sort(key=lambda x: (x['wins'] / x['total'] if x['total'] > 0 else 0, x['total']), reverse=True)
        
        # Calculate player streaks
        player_streaks = calculate_player_streaks(club_name)
        
        return {
            'team_name': club_name,
            'weekly_results': weekly_results,
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
            'weekly_results': [],
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
    """
    Get all team availability data for mobile page - optimized for performance
    
    PERFORMANCE OPTIMIZATIONS IMPLEMENTED:
    1. **Single Bulk Database Query**: Instead of N individual queries (one per player), 
       we now use a single query with IN clause to fetch all availability data at once.
       This reduces database round-trips from ~10 to 1, significantly improving performance.
       
    2. **Early Data Filtering**: We filter players by club/series before any database operations,
       reducing the dataset size early in the process.
       
    3. **Optimized Data Structures**: Using dictionaries for fast O(1) lookups instead of 
       iterating through lists.
       
    4. **Single Date Conversion**: The date is converted once and reused, rather than 
       converting it for each player.
    
    RECOMMENDED DATABASE OPTIMIZATION:
    For even better performance, ensure this index exists in PostgreSQL:
    CREATE INDEX IF NOT EXISTS idx_player_availability_lookup 
    ON player_availability (series_id, match_date, player_name);
    
    This index supports the bulk query's WHERE clause for optimal performance.
    """
    try:
        # Handle missing parameters
        if not selected_date:
            return {
                'players_schedule': {},
                'selected_date': 'today',
                'error': 'No date selected'
            }

        # Get user information
        if not user:
            return {
                'players_schedule': {},
                'selected_date': selected_date,
                'error': 'User not found in session'
            }
            
        club_name = user.get('club')
        series = user.get('series')
        
        print(f"\n=== ALL TEAM AVAILABILITY DATA REQUEST (OPTIMIZED) ===")
        print(f"User: {user.get('email')}")
        print(f"Club: {club_name}")
        print(f"Series: {series}")
        print(f"Selected Date: {selected_date}")
        
        if not club_name or not series:
            return {
                'players_schedule': {},
                'selected_date': selected_date,
                'error': 'Please verify your club (Tennaqua) and series (Chicago 22) are correct in your profile settings'
            }

        # Get series ID from database
        from database_utils import execute_query
        from utils.date_utils import date_to_db_timestamp
        
        series_record = execute_query("SELECT id, name FROM series WHERE name = %s", (series,))
        if not series_record:
            print(f"❌ Series not found: {series}")
            return {
                'players_schedule': {},
                'selected_date': selected_date,
                'error': f'Series "{series}" not found in database'
            }
            
        series_record = series_record[0]

        # Convert selected_date once for all queries
        try:
            if '/' in selected_date:
                # Convert MM/DD/YYYY to proper UTC timestamp
                selected_date_utc = date_to_db_timestamp(selected_date)
            else:
                # Convert YYYY-MM-DD to proper UTC timestamp  
                selected_date_utc = date_to_db_timestamp(selected_date)
            
            print(f"Converted selected_date {selected_date} to UTC timestamp: {selected_date_utc}")
        except Exception as e:
            print(f"❌ Error converting selected_date {selected_date}: {e}")
            return {
                'players_schedule': {},
                'selected_date': selected_date,
                'error': f'Invalid date format: {selected_date}'
            }

        # Load and filter players from JSON
        try:
            # Load fresh player data
            all_players = _load_players_data()
            
            if not all_players:
                return {
                    'players_schedule': {},
                    'selected_date': selected_date,
                    'error': 'Error loading player data'
                }
            
            # Filter players for this series and club - more efficient filtering
            team_player_names = []
            team_players_display = {}
            
            for player in all_players:
                if (player.get('Series') == series and 
                    player.get('Club') == club_name):
                    full_name = f"{player['First Name']} {player['Last Name']}"
                    team_player_names.append(full_name)
                    # Store display name mapping
                    team_players_display[full_name] = f"{full_name} ({club_name})"
            
            print(f"Found {len(team_player_names)} players for {club_name} - {series}")
            
            if not team_player_names:
                print("❌ No players found in players.json")
                return {
                    'players_schedule': {},
                    'selected_date': selected_date,
                    'error': 'No players found for your team'
                }
                
        except Exception as e:
            print(f"❌ Error processing player data: {e}")
            import traceback
            print(traceback.format_exc())
            return {
                'players_schedule': {},
                'selected_date': selected_date,
                'error': 'Error loading player data'
            }

        # OPTIMIZATION: Single bulk database query instead of N individual queries
        try:
            # Create a single query to get all availability data at once
            placeholders = ','.join(['%s'] * len(team_player_names))
            bulk_query = f"""
                SELECT player_name, availability_status
                FROM player_availability 
                WHERE player_name IN ({placeholders})
                AND series_id = %s 
                AND DATE(match_date AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
            """
            
            # Parameters: all player names + series_id + date
            bulk_params = tuple(team_player_names) + (series_record['id'], selected_date_utc)
            
            print(f"Executing bulk availability query for {len(team_player_names)} players...")
            availability_results = execute_query(bulk_query, bulk_params)
            
            # Convert results to dictionary for fast lookup
            availability_lookup = {}
            for result in availability_results:
                availability_lookup[result['player_name']] = result['availability_status']
            
            print(f"Found availability data for {len(availability_lookup)} players")
            
        except Exception as e:
            print(f"❌ Error in bulk availability query: {e}")
            import traceback
            print(traceback.format_exc())
            return {
                'players_schedule': {},
                'selected_date': selected_date,
                'error': 'Error querying availability data'
            }

        # Build players_schedule efficiently
        players_schedule = {}
        for player_name in team_player_names:
            # Get availability status from lookup (default to 0 if not found)
            status = availability_lookup.get(player_name, 0)
            
            # Create availability record
            availability = [{
                'date': selected_date,
                'availability_status': status
            }]
            
            # Store with display name
            display_name = team_players_display[player_name]
            players_schedule[display_name] = availability

        if not players_schedule:
            print("❌ No player schedules created")
            return {
                'players_schedule': {},
                'selected_date': selected_date,
                'error': 'No player schedules found for your series'
            }
            
        print(f"✅ Successfully created availability schedule for {len(players_schedule)} players with optimized queries")
        
        return {
            'players_schedule': players_schedule,
            'selected_date': selected_date
        }
        
    except Exception as e:
        print(f"Error getting all team availability data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'players_schedule': {},
            'selected_date': selected_date or 'today',
            'error': str(e)
        }

def get_club_players_data(user, series_filter=None, first_name_filter=None, last_name_filter=None, pti_min=None, pti_max=None):
    """Get all players at the user's club with optional filtering"""
    try:
        # Get user's club from user data
        user_club = user.get('club')
        if not user_club:
            return {
                'players': [],
                'available_series': [],
                'pti_range': {'min': 0, 'max': 100},
                'error': 'User club not found'
            }

        print(f"\n=== DEBUG: get_club_players_data ===")
        print(f"User club: '{user_club}'")
        print(f"User club type: {type(user_club)}")
        print(f"Filters - Series: {series_filter}, First: {first_name_filter}, Last: {last_name_filter}, PTI: {pti_min}-{pti_max}")

        # Load fresh player data
        all_players = _load_players_data()
        
        if not all_players:
            return {
                'players': [],
                'available_series': [],
                'pti_range': {'min': 0, 'max': 100},
                'error': 'Error loading player data'
            }

        # Debug: Show unique clubs in data and check counts
        clubs_in_data = set()
        user_club_count = 0
        for player in all_players:
            clubs_in_data.add(player['Club'])
            if player['Club'] == user_club:
                user_club_count += 1
        
        print(f"Total players in file: {len(all_players)}")
        print(f"Players with user's club '{user_club}': {user_club_count}")
        print(f"All clubs in data: {sorted(list(clubs_in_data))}")

        # Load real contact information from CSV
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(project_root, 'data', 'club_directories', 'directory_tennaqua.csv')
        contact_info = {}
        
        if os.path.exists(csv_path):
            import csv
            with open(csv_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['First'] and row['Last Name']:  # Skip empty rows
                        full_name = f"{row['First'].strip()} {row['Last Name'].strip()}"
                        contact_info[full_name.lower()] = {
                            'phone': row['Phone'].strip(),
                            'email': row['Email'].strip()
                        }
            print(f"Loaded {len(contact_info)} contact records from CSV")
        else:
            print(f"CSV file not found at: {csv_path}")

        # Calculate PTI range from ALL players in the file (for slider bounds)
        all_pti_values = []
        for player in all_players:
            try:
                pti_value = float(player['PTI'])
                all_pti_values.append(pti_value)
            except (ValueError, TypeError):
                continue
        
        # Set PTI range based on all players in the system
        pti_range = {'min': 0, 'max': 100}
        if all_pti_values:
            pti_range = {
                'min': min(all_pti_values),
                'max': max(all_pti_values)
            }

        # Filter players by club and other criteria
        filtered_players = []
        club_series = set()  # Track all series at this club

        for player in all_players:
            # Debug: Log first few club comparisons
            if len(filtered_players) < 3:
                print(f"Comparing: player['Club']='{player['Club']}' == user_club='{user_club}' ? {player['Club'] == user_club}")
            
            # Only include players from the same club as the user (exact match)
            if player['Club'] == user_club:
                club_series.add(player['Series'])
                
                # Handle PTI values - allow "N/A" and non-numeric values
                try:
                    pti_value = float(player['PTI'])
                except (ValueError, TypeError):
                    # For "N/A" or non-numeric PTI, set a default value that won't be filtered out
                    pti_value = 50.0  # Use middle value so it passes most PTI filters
                    print(f"Player {player['First Name']} {player['Last Name']} has non-numeric PTI '{player['PTI']}', using default value 50.0")

                # Apply filters
                if series_filter and player['Series'] != series_filter:
                    continue
                
                if first_name_filter and first_name_filter not in player['First Name'].lower():
                    continue
                    
                if last_name_filter and last_name_filter not in player['Last Name'].lower():
                    continue
                    
                if pti_min is not None and pti_value < pti_min:
                    continue
                    
                if pti_max is not None and pti_value > pti_max:
                    continue

                # Get real contact info from CSV
                player_name = f"{player['First Name']} {player['Last Name']}"
                player_contact = contact_info.get(player_name.lower(), {})
                
                # Add player to results
                filtered_players.append({
                    'name': player_name,
                    'firstName': player['First Name'],
                    'lastName': player['Last Name'],
                    'series': player['Series'],
                    'pti': player['PTI'],  # Keep original PTI value for display
                    'wins': player['Wins'],
                    'losses': player['Losses'],
                    'winRate': player['Win %'],
                    'phone': player_contact.get('phone', ''),
                    'email': player_contact.get('email', '')
                })

        # Sort players by PTI (ascending - lower PTI is better)
        # Handle "N/A" PTI values by treating them as a high number for sorting
        def get_sort_pti(player):
            try:
                return float(player['pti'])
            except (ValueError, TypeError):
                return 999.0  # Put "N/A" values at the end
        
        filtered_players.sort(key=get_sort_pti)

        print(f"Found {len(filtered_players)} players at {user_club}")
        print(f"Available series: {sorted(club_series)}")
        print(f"PTI range (from all players): {pti_range}")
        print("=== END DEBUG ===\n")

        return {
            'players': filtered_players,
            'available_series': sorted(club_series, key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 999),
            'pti_range': pti_range,
            'debug': {
                'user_club': user_club,
                'total_players_in_file': len(all_players),
                'players_at_user_club': user_club_count,
                'all_clubs': sorted(list(clubs_in_data))
            }
        }
        
    except Exception as e:
        print(f"Error getting club players data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
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