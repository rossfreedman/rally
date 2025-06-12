import os
import json
import re
from datetime import datetime
from collections import defaultdict, Counter
import pandas as pd
from rapidfuzz import fuzz
from utils.match_utils import normalize_name, names_match
from database_utils import execute_query, execute_query_one
from utils.logging import log_user_activity
import logging

logger = logging.getLogger(__name__)

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
            'error': 'Invalid player name.'
        }
    # Try to split into first and last name
    parts = player_name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = ' '.join(parts[1:])
    else:
        # If only one part, use as both first and last name
        first_name = parts[0]
        last_name = parts[0]
    # Call get_player_analysis with constructed user dict
    user_dict = {'first_name': first_name, 'last_name': last_name}
    return get_player_analysis(user_dict)

def get_player_analysis(user):
    """
    Returns the player analysis data for the given user, as a dict.
    Uses match_history.json for current season stats and court analysis,
    and player_history.json for career stats and player history.
    Always returns all expected keys, even if some are None or empty.
    """
    
    # For now, return a basic structure to avoid breaking the application
    # This will need to be fully implemented by moving the complex logic from server.py
    return {
        'current_season': {
            'winRate': 0,
            'matches': 0,
            'wins': 0,
            'losses': 0,
            'ptiChange': 'N/A'
        },
        'court_analysis': {
            'court1': {'winRate': 0, 'record': '0-0', 'topPartners': []},
            'court2': {'winRate': 0, 'record': '0-0', 'topPartners': []},
            'court3': {'winRate': 0, 'record': '0-0', 'topPartners': []},
            'court4': {'winRate': 0, 'record': '0-0', 'topPartners': []}
        },
        'career_stats': {
            'winRate': 0,
            'matches': 0,
            'pti': 'N/A'
        },
        'player_history': {
            'progression': '',
            'seasons': []
        },
        'videos': {'match': [], 'practice': []},
        'trends': {},
        'career_pti_change': 'N/A',
        'error': None
    }

def get_season_from_date(date_str):
    """Get season string from date"""
    try:
        if isinstance(date_str, str):
            dt = datetime.strptime(date_str, '%m/%d/%Y')
        else:
            dt = date_str
        
        if dt.month >= 8:  # August or later
            start_year = dt.year
            end_year = dt.year + 1
        else:
            start_year = dt.year - 1
            end_year = dt.year
        return f"{start_year}-{end_year}"
    except:
        return None

def build_season_history(player):
    """Build season history from player matches"""
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
        
        # Round trend to 1 decimal
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

def search_players_with_fuzzy_logic(first_name_query, last_name_query):
    """Search for players using fuzzy logic matching"""
    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Load all player data
        players_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'players.json')
        player_history_path = os.path.join(app_dir, 'data', 'leagues', 'apta', 'player_history.json')
        
        results = []
        
        # Search in players.json
        try:
            with open(players_path, 'r') as f:
                players_data = json.load(f)
                
            for player in players_data:
                first_name = player.get('First Name', '')
                last_name = player.get('Last Name', '')
                
                # Calculate fuzzy match scores
                first_score = fuzz.partial_ratio(first_name_query.lower(), first_name.lower()) if first_name_query else 100
                last_score = fuzz.partial_ratio(last_name_query.lower(), last_name.lower()) if last_name_query else 100
                
                # Only include if both scores are reasonably high
                if first_score >= 70 and last_score >= 70:
                    full_name = f"{first_name} {last_name}"
                    results.append({
                        'name': full_name,
                        'source': 'players',
                        'match_score': (first_score + last_score) / 2,
                        'series': player.get('Series', ''),
                        'club': player.get('Club', ''),
                        'pti': player.get('PTI', 'N/A')
                    })
        except Exception as e:
            print(f"Error searching players.json: {str(e)}")
        
        # Search in player_history.json
        try:
            with open(player_history_path, 'r') as f:
                history_data = json.load(f)
                
            for player in history_data:
                name = player.get('name', '')
                # Split name into parts for matching
                name_parts = name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                    
                    # Calculate fuzzy match scores
                    first_score = fuzz.partial_ratio(first_name_query.lower(), first_name.lower()) if first_name_query else 100
                    last_score = fuzz.partial_ratio(last_name_query.lower(), last_name.lower()) if last_name_query else 100
                    
                    # Only include if both scores are reasonably high and not already in results
                    if first_score >= 70 and last_score >= 70:
                        # Check if already in results from players.json
                        already_exists = any(r['name'].lower() == name.lower() for r in results)
                        if not already_exists:
                            current_pti = 'N/A'
                            if player.get('matches') and len(player['matches']) > 0:
                                # Get most recent PTI
                                sorted_matches = sorted(player['matches'], 
                                                      key=lambda x: datetime.strptime(x['date'], '%m/%d/%Y'), 
                                                      reverse=True)
                                current_pti = sorted_matches[0].get('end_pti', 'N/A')
                            
                            results.append({
                                'name': name,
                                'source': 'history',
                                'match_score': (first_score + last_score) / 2,
                                'series': '',  # Not available in history data
                                'club': '',    # Not available in history data
                                'pti': current_pti
                            })
        except Exception as e:
            print(f"Error searching player_history.json: {str(e)}")
        
        # Sort by match score (descending) and limit results
        results.sort(key=lambda x: x['match_score'], reverse=True)
        return results[:20]  # Limit to top 20 results
        
    except Exception as e:
        print(f"Error in fuzzy player search: {str(e)}")
        return []

def find_player_in_history(user, player_history=None):
    """
    Find a player in the player history data based on user information.
    Enhanced to handle multiple name formats and fuzzy matching.
    """
    if player_history is None:
        # Load player history data if not provided
        try:
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            user_league_id = user.get('league_id', '')
            
            # Use dynamic path based on league
            if user_league_id and not user_league_id.startswith('APTA'):
                players_path = os.path.join(app_dir, 'data', 'leagues', user_league_id, 'player_history.json')
            else:
                players_path = os.path.join(app_dir, 'data', 'leagues', 'all', 'player_history.json')
                
            with open(players_path, 'r') as f:
                all_player_history = json.load(f)
                
            # Filter player history by league
            player_history = []
            for player in all_player_history:
                player_league = player.get('League', player.get('league_id'))
                if user_league_id.startswith('APTA'):
                    # For APTA users, only include players from the same APTA league
                    if player_league == user_league_id:
                        player_history.append(player)
                else:
                    # For other leagues, match the league_id
                    if player_league == user_league_id:
                        player_history.append(player)
                        
        except Exception as e:
            print(f"Error loading player history for find_player_in_history: {e}")
            return None
    
    try:
        # Build possible name variations for the user
        first_name = user.get('first_name', '').strip()
        last_name = user.get('last_name', '').strip()
        
        if not first_name or not last_name:
            return None
            
        # Try different name formats
        name_variations = [
            f"{first_name} {last_name}",
            f"{last_name} {first_name}",
            f"{first_name.lower()} {last_name.lower()}",
            f"{last_name.lower()} {first_name.lower()}",
        ]
        
        # Also try without middle names/initials if present
        first_parts = first_name.split()
        if len(first_parts) > 1:
            name_variations.extend([
                f"{first_parts[0]} {last_name}",
                f"{last_name} {first_parts[0]}"
            ])
        
        def normalize_for_matching(name):
            """Normalize name for fuzzy matching"""
            return re.sub(r'[^\w\s]', '', name.lower()).strip()
        
        # Try exact matches first
        for variation in name_variations:
            for player in player_history:
                if player.get('name', '').lower() == variation.lower():
                    return player
        
        # If no exact match, try fuzzy matching
        normalized_variations = [normalize_for_matching(v) for v in name_variations]
        
        for player in player_history:
            player_name_normalized = normalize_for_matching(player.get('name', ''))
            
            # Check if any variation has a high fuzzy match score
            for normalized_var in normalized_variations:
                if fuzz.ratio(normalized_var, player_name_normalized) >= 85:
                    return player
        
        return None
        
    except Exception as e:
        print(f"Error finding player in history: {str(e)}")
        return None 

def get_players_by_league_and_series(league_id, series_name, club_name=None):
    """
    Get players for a specific league and series, optionally filtered by club
    
    Args:
        league_id (str): League identifier (e.g., 'APTA_CHICAGO', 'NSTF')
        series_name (str): Series name for filtering
        club_name (str, optional): Club name for additional filtering
    
    Returns:
        list: List of player dictionaries with stats
    """
    try:
        base_query = """
            SELECT DISTINCT p.tenniscores_player_id, p.first_name, p.last_name,
                   p.club_id, p.series_id, c.name as club_name, s.name as series_name,
                   l.league_name, l.league_id, p.pti, p.wins, p.losses, p.win_percentage
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE l.league_id = %(league_id)s 
            AND p.is_active = true
        """
        
        params = {'league_id': league_id}
        
        # Add series filter if provided
        if series_name:
            base_query += " AND s.name = %(series_name)s"
            params['series_name'] = series_name
            
        # Add club filter if provided
        if club_name:
            base_query += " AND c.name = %(club_name)s"
            params['club_name'] = club_name
            
        base_query += " ORDER BY p.last_name, p.first_name"
        
        players = execute_query(base_query, params)
        
        # Format for API response
        formatted_players = []
        for player in players:
            # Calculate win rate
            wins = player.get('wins', 0) or 0
            losses = player.get('losses', 0) or 0
            total_matches = wins + losses
            win_rate = f"{(wins / total_matches * 100):.1f}%" if total_matches > 0 else "0.0%"
            
            formatted_players.append({
                'name': f"{player['first_name']} {player['last_name']}",
                'player_id': player['tenniscores_player_id'],
                'series': player['series_name'],
                'club': player['club_name'],
                'league': player['league_id'],
                'pti': player.get('pti'),
                'rating': player.get('pti'),  # Alias for pti
                'wins': wins,
                'losses': losses,
                'winRate': win_rate
            })
            
        return formatted_players
        
    except Exception as e:
        logger.error(f"Error fetching players for league {league_id}, series {series_name}: {e}")
        return []

def get_player_by_tenniscores_id(tenniscores_player_id, league_id=None):
    """
    Get player information by Tenniscores Player ID
    
    Args:
        tenniscores_player_id (str): Tenniscores Player ID
        league_id (str, optional): League to filter by for multi-league players
    
    Returns:
        dict|None: Player information or None if not found
    """
    try:
        query = """
            SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
                   p.club_id, p.series_id, c.name as club_name, 
                   s.name as series_name, l.league_name, l.league_id
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %(player_id)s
            AND p.is_active = true
        """
        
        params = {'player_id': tenniscores_player_id}
        
        if league_id:
            query += " AND l.league_id = %(league_id)s"
            params['league_id'] = league_id
            
        result = execute_query_one(query, params)
        
        if result:
            return {
                'id': result['id'],
                'tenniscores_player_id': result['tenniscores_player_id'],
                'first_name': result['first_name'],
                'last_name': result['last_name'],
                'club_name': result['club_name'],
                'series_name': result['series_name'],
                'league_id': result['league_id'],
                'league_name': result['league_name']
            }
        return None
        
    except Exception as e:
        logger.error(f"Error fetching player {tenniscores_player_id}: {e}")
        return None

def find_player_in_history(user, player_history_data):
    """
    Find a user's player record in the player history data
    
    Args:
        user (dict): User session data with first_name, last_name, league_id
        player_history_data (list): List of player history records
    
    Returns:
        dict|None: Player history record or None if not found
    """
    user_name = f"{user['first_name']} {user['last_name']}"
    user_league_id = user.get('league_id')
    
    # Helper function to normalize names for comparison
    def normalize(name):
        return name.lower().strip().replace(',', '').replace('.', '')
    
    target_normalized = normalize(user_name)
    
    for player in player_history_data:
        # Check league match first
        player_league = player.get('League', player.get('league_id'))
        if user_league_id and player_league != user_league_id:
            continue
            
        # Check name match
        if normalize(player.get('name', '')) == target_normalized:
            return player
    
    return None

def get_team_players_by_team_id(team_id, user_league_id):
    """
    Get all players for a specific team using match history and database
    
    Args:
        team_id (str): Team identifier
        user_league_id (str): User's league for filtering
    
    Returns:
        list: List of team players with stats
    """
    # This would require loading match history to find team players
    # For now, return empty list - this needs match history integration
    logger.warning(f"get_team_players_by_team_id not fully implemented for team {team_id}")
    return []

def search_players_by_name(search_term, league_id=None, limit=20):
    """
    Search players by name across leagues
    
    Args:
        search_term (str): Name search term
        league_id (str, optional): Limit to specific league
        limit (int): Maximum number of results
    
    Returns:
        list: Matching players
    """
    try:
        query = """
            SELECT DISTINCT p.tenniscores_player_id, p.first_name, p.last_name,
                   c.name as club_name, s.name as series_name, l.league_id
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.is_active = true
            AND (LOWER(p.first_name || ' ' || p.last_name) LIKE LOWER(%(search)s)
                 OR LOWER(p.last_name || ' ' || p.first_name) LIKE LOWER(%(search)s))
        """
        
        params = {'search': f'%{search_term}%'}
        
        if league_id:
            query += " AND l.league_id = %(league_id)s"
            params['league_id'] = league_id
            
        query += " ORDER BY p.last_name, p.first_name LIMIT %(limit)s"
        params['limit'] = limit
        
        results = execute_query(query, params)
        
        return [{
            'name': f"{r['first_name']} {r['last_name']}",
            'player_id': r['tenniscores_player_id'],
            'club': r['club_name'],
            'series': r['series_name'],
            'league': r['league_id']
        } for r in results]
        
    except Exception as e:
        logger.error(f"Error searching players: {e}")
        return [] 