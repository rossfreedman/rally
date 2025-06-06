import os
import json
import re
from datetime import datetime
from collections import defaultdict, Counter
import pandas as pd
from fuzzywuzzy import fuzz
from utils.match_utils import normalize_name, names_match

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
        players_path = os.path.join(app_dir, 'data', 'players.json')
        player_history_path = os.path.join(app_dir, 'data', 'player_history.json')
        
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

def find_player_in_history(user, player_history):
    """Find a player's record in the player history data"""
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