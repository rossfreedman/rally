"""
Mobile service module - handles all mobile-specific business logic
This module provides functions for mobile interface data processing and user interactions.
All data is loaded from database tables instead of JSON files for improved performance and consistency.
"""

import os
import json
from datetime import datetime, timedelta
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
import traceback
from collections import defaultdict, Counter
from utils.date_utils import date_to_db_timestamp, normalize_date_string
from urllib.parse import unquote

def _load_players_data():
    """Load player data fresh from database with all statistics - no caching"""
    try:
        from database_utils import execute_query, execute_query_one
        
        # First, let's check if players table exists and what columns it has
        try:
            table_check = execute_query_one("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'players'
            """)
            
            if not table_check:
                print("❌ Players table does not exist, cannot load player data")
                return []
            
            # Get column information for players table
            columns_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'players'
                ORDER BY ordinal_position
            """
            columns_result = execute_query(columns_query)
            available_columns = [col['column_name'] for col in columns_result]
            print(f"Available columns in players table: {available_columns}")
            
        except Exception as check_error:
            print(f"Error checking players table: {check_error}")
            return []
        
        # Build query based on available columns
        base_columns = {
            'first_name': '"First Name"',
            'last_name': '"Last Name"', 
            'tenniscores_player_id': '"Player ID"'
        }
        
        optional_columns = {
            'pti': 'CASE WHEN p.pti IS NULL THEN \'N/A\' ELSE p.pti::TEXT END as "PTI"',
            'wins': 'COALESCE(p.wins, 0) as "Wins"',
            'losses': 'COALESCE(p.losses, 0) as "Losses"',
            'club_id': 'c.name as "Club"',
            'series_id': 's.name as "Series"',
            'league_id': 'COALESCE(l.league_id, \'all\') as "League"'
        }
        
        # Start with base required columns
        select_parts = []
        joins = []
        
        for col, select_expr in base_columns.items():
            if col in available_columns:
                select_parts.append(f'p.{col} as {select_expr}')
        
        # Add optional columns if they exist
        for col, select_expr in optional_columns.items():
            if col in available_columns:
                select_parts.append(select_expr)
                
                # Add necessary joins
                if col == 'club_id' and 'club_id' in available_columns:
                    joins.append('LEFT JOIN clubs c ON p.club_id = c.id')
                elif col == 'series_id' and 'series_id' in available_columns:
                    joins.append('LEFT JOIN series s ON p.series_id = s.id')
                elif col == 'league_id' and 'league_id' in available_columns:
                    joins.append('LEFT JOIN leagues l ON p.league_id = l.id')
        
        # Add calculated win percentage if we have wins/losses
        if 'wins' in available_columns and 'losses' in available_columns:
            select_parts.append('''
                CASE 
                    WHEN COALESCE(p.wins, 0) + COALESCE(p.losses, 0) > 0 
                    THEN ROUND((COALESCE(p.wins, 0)::NUMERIC / (COALESCE(p.wins, 0) + COALESCE(p.losses, 0))) * 100, 1)::TEXT || '%'
                    ELSE '0%'
                END as "Win %"
            ''')
        else:
            # Add default values if columns don't exist
            select_parts.extend([
                "'N/A' as \"PTI\"",
                "0 as \"Wins\"", 
                "0 as \"Losses\"",
                "'0%' as \"Win %\""
            ])
        
        # Add default values for missing optional fields
        if 'club_id' not in available_columns:
            select_parts.append("'Unknown Club' as \"Club\"")
        if 'series_id' not in available_columns:
            select_parts.append("'Unknown Series' as \"Series\"")
        if 'league_id' not in available_columns:
            select_parts.append("'all' as \"League\"")
        
        # Remove duplicate joins
        joins = list(set(joins))
        
        # Build final query
        players_query = f"""
            SELECT {', '.join(select_parts)}
            FROM players p
            {' '.join(joins)}
            WHERE p.tenniscores_player_id IS NOT NULL
            ORDER BY p.first_name, p.last_name
        """
        
        print(f"Executing query: {players_query}")
        players_data = execute_query(players_query)
        print(f"Loaded fresh player data ({len(players_data)} players) from database")
        return players_data
        
    except Exception as e:
        print(f"Error loading player data from database: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []

def get_career_stats_from_db(player_id):
    """
    Get career stats from player_history table by player_id.
    Returns None if no historical data is found or if data is insufficient.
    """
    try:
        # First get the player's database ID
        player_query = """
            SELECT id FROM players WHERE tenniscores_player_id = %s
        """
        player_record = execute_query_one(player_query, [player_id])
        
        if not player_record:
            print(f"[DEBUG] get_career_stats_from_db: No player found for tenniscores_player_id {player_id}")
            return None
            
        player_db_id = player_record['id']
        
        # Query player_history table to get all historical PTI data
        career_query = """
            SELECT 
                date,
                end_pti,
                series
            FROM player_history
            WHERE player_id = %s
            ORDER BY date ASC
        """
        
        career_records = execute_query(career_query, [player_db_id])
        
        if not career_records or len(career_records) < 5:
            print(f"[DEBUG] get_career_stats_from_db: Insufficient career data for player {player_id} (found {len(career_records) if career_records else 0} records, need at least 5)")
            return None
        
        # Get career stats directly from players table (imported from player_history.json)
        career_stats_query = """
            SELECT 
                career_wins,
                career_losses,
                career_matches,
                career_win_percentage,
                pti as current_pti
            FROM players
            WHERE id = %s
        """
        
        career_data = execute_query_one(career_stats_query, [player_db_id])
        
        if not career_data:
            print(f"[DEBUG] get_career_stats_from_db: No career data found for player {player_id}")
            return None
        
        # Check if player has meaningful career data
        career_matches = career_data['career_matches'] or 0
        career_wins = career_data['career_wins'] or 0
        career_losses = career_data['career_losses'] or 0
        
        if career_matches < 5:  # Require at least 5 career matches
            print(f"[DEBUG] get_career_stats_from_db: Insufficient career matches for player {player_id} (found {career_matches})")
            return None
        
        # Use the actual career data from JSON import
        total_matches = career_matches
        wins = career_wins
        losses = career_losses
        win_rate = round(career_data['career_win_percentage'] or 0, 1)
        
        # Get current PTI as career PTI
        latest_pti = career_data['current_pti'] or 'N/A'
        
        career_stats = {
            'winRate': win_rate,
            'matches': total_matches,
            'wins': wins,
            'losses': losses,
            'pti': latest_pti
        }
        
        print(f"[DEBUG] get_career_stats_from_db: Found career stats for player {player_id}: {total_matches} matches, {wins} wins, {losses} losses, {win_rate}% win rate")
        return career_stats
        
    except Exception as e:
        print(f"[ERROR] get_career_stats_from_db: Error fetching career stats for player {player_id}: {e}")
        return None

def get_player_analysis_by_name(player_name, viewing_user=None):
    """
    Returns the player analysis data for the given player name, as a dict.
    This function parses the player_name string into first and last name (if possible),
    then calls get_player_analysis with a constructed user dict.
    Handles single-word names gracefully.
    
    Args:
        player_name: Name of the player to analyze
        viewing_user: User object containing league_id for filtering data by league
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
    
    # Load player data from database based on viewing user's league for proper filtering
    try:
        # Note: execute_query and execute_query_one are already imported at module level
        
        # Get viewing user's league for filtering
        viewing_user_league = viewing_user.get('league_id', '') if viewing_user else ''
        
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(viewing_user_league, str) and viewing_user_league != '':
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", 
                    [viewing_user_league]
                )
                if league_record:
                    league_id_int = league_record['id']
                    print(f"[DEBUG] Converted viewing user league_id '{viewing_user_league}' to integer: {league_id_int}")
                else:
                    print(f"[WARNING] Viewing user league '{viewing_user_league}' not found in leagues table")
            except Exception as e:
                print(f"[DEBUG] Could not convert viewing user league ID: {e}")
        elif isinstance(viewing_user_league, int):
            league_id_int = viewing_user_league
            print(f"[DEBUG] Viewing user league_id already integer: {league_id_int}")
        
        # Query players table with league filtering
        if league_id_int:
            players_query = """
                SELECT 
                    first_name as "First Name",
                    last_name as "Last Name", 
                    tenniscores_player_id as "Player ID",
                    (SELECT name FROM clubs WHERE id = p.club_id) as "Club",
                    (SELECT name FROM series WHERE id = p.series_id) as "Series",
                    p.league_id as "League"
                FROM players p
                WHERE p.league_id = %s AND tenniscores_player_id IS NOT NULL
            """
            all_players_data = execute_query(players_query, [league_id_int])
        else:
            players_query = """
                SELECT 
                    first_name as "First Name",
                    last_name as "Last Name", 
                    tenniscores_player_id as "Player ID",
                    (SELECT name FROM clubs WHERE id = p.club_id) as "Club",
                    (SELECT name FROM series WHERE id = p.series_id) as "Series",
                    p.league_id as "League"
                FROM players p
                WHERE tenniscores_player_id IS NOT NULL
            """
            all_players_data = execute_query(players_query)
            
        print(f"[INFO] Loaded {len(all_players_data)} players from database")
        
    except Exception as e:
        print(f"[ERROR] Could not load players from database: {e}")
        all_players_data = []
        
    def normalize(name):
        return name.replace(',', '').replace('  ', ' ').strip().lower()
    
    # Try to find the exact player by name matching
    player_name_normalized = normalize(player_name)
    found_player = None
    
    for p in all_players_data:
        # Construct full name from First Name and Last Name fields
        first_name = p.get('First Name', '')
        last_name = p.get('Last Name', '')
        full_name = f"{first_name} {last_name}".strip()
        player_record_name = normalize(full_name)
        
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
            'tenniscores_player_id': found_player.get('Player ID'),  # Include player_id if available
            'league_id': found_player.get('League', 'all'),  # Use League field
            'club': found_player.get('Club', ''),
            'series': found_player.get('Series', '')
        }
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
    
    # Call get_player_analysis with constructed user dict
    result = get_player_analysis(user_dict)
    
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
    """Get player analysis data for mobile interface"""
    try:
        # Debug print to see what we're getting
        print(f"[DEBUG] get_player_analysis: User type: {type(user)}, Data: {user}")
        
        # Ensure user data is a dictionary
        if not isinstance(user, dict):
            print(f"[ERROR] get_player_analysis: User data is not a dictionary: {type(user)}")
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
                'pti_data_available': False,
                'error': 'Invalid user data format'
            }
        
        # Get player ID from user data
        player_id = user.get('tenniscores_player_id')
        if not player_id:
            print("[ERROR] get_player_analysis: No tenniscores_player_id found in user data")
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
                    'wins': 0,
                    'losses': 0,
                    'pti': 'N/A'
                },
                'player_history': {
                    'progression': '',
                    'seasons': []
                },
                'videos': {'match': [], 'practice': []},
                'trends': {},
                'career_pti_change': 'N/A',
                'current_pti': None,
                'weekly_pti_change': None,
                'pti_data_available': False,
                'error': 'Player ID not found'
            }
        
        # Get user's league for filtering
        user_league_id = user.get('league_id', '')
        print(f"[DEBUG] get_player_analysis: User league_id string: '{user_league_id}'")
        
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != '':
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", 
                    [user_league_id]
                )
                if league_record:
                    league_id_int = league_record['id']
                    print(f"[DEBUG] Converted league_id '{user_league_id}' to integer: {league_id_int}")
                else:
                    print(f"[WARNING] League '{user_league_id}' not found in leagues table")
            except Exception as e:
                print(f"[DEBUG] Could not convert league ID: {e}")
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
            print(f"[DEBUG] League_id already integer: {league_id_int}")
        
        # Query player history and match data from database
        # Note: execute_query and execute_query_one are already imported at module level
        
        # Get player history - only filter by league if we have a valid league_id
        if league_id_int:
            history_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC
            """
            player_matches = execute_query(history_query, [player_id, player_id, player_id, player_id, league_id_int])
        else:
            # No league filtering if we don't have a valid league_id
            history_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                ORDER BY match_date DESC
            """
            player_matches = execute_query(history_query, [player_id, player_id, player_id, player_id])
        
        if not player_matches:
            print(f"[DEBUG] get_player_analysis: No matches found for player {player_id} in league {league_id_int}")
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
                    'wins': 0,
                    'losses': 0,
                    'pti': 'N/A'
                },
                'player_history': {
                    'progression': '',
                    'seasons': []
                },
                'videos': {'match': [], 'practice': []},
                'trends': {},
                'career_pti_change': 'N/A',
                'current_pti': None,
                'weekly_pti_change': None,
                'pti_data_available': False,
                'error': None
            }
        
        # Get PTI data from players table and player_history table
        pti_data = {
            'current_pti': None,
            'pti_change': None,
            'pti_data_available': False
        }
        
        try:
            # Get current PTI and series info from players table
            player_pti_query = '''
                SELECT 
                    p.id,
                    p.pti as current_pti,
                    p.series_id,
                    s.name as series_name
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                WHERE p.tenniscores_player_id = %s
            '''
            player_pti_data = execute_query_one(player_pti_query, [player_id])
            
            if player_pti_data and player_pti_data['current_pti'] is not None:
                current_pti = player_pti_data['current_pti']
                series_name = player_pti_data['series_name']
                
                print(f"[DEBUG] Current PTI found: {current_pti} for series: {series_name}")
                
                # Get PTI history for this specific player using proper foreign key relationship
                pti_change = 0.0
                
                # Get player's database ID first
                player_db_id = player_pti_data['id']
                
                # Method 1: Use proper foreign key to get this player's PTI history
                player_pti_history_query = '''
                    SELECT 
                        date,
                        end_pti,
                        series,
                        TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
                    FROM player_history
                    WHERE player_id = %s
                    ORDER BY date DESC
                    LIMIT 10
                '''
                
                player_pti_records = execute_query(player_pti_history_query, [player_db_id])
                
                if player_pti_records and len(player_pti_records) >= 2:
                    # Get the most recent and previous week's PTI values for this specific player
                    most_recent_pti = player_pti_records[0]['end_pti']
                    previous_week_pti = player_pti_records[1]['end_pti']
                    pti_change = most_recent_pti - previous_week_pti
                    print(f"[DEBUG] Weekly PTI change via player FK: {pti_change:+.1f} (from {player_pti_records[1]['formatted_date']} to {player_pti_records[0]['formatted_date']})")
                    
                elif series_name:
                    # Fallback: Try series matching with flexible name patterns
                    series_patterns = [
                        series_name,                    # Exact: "Chicago 22"
                        series_name.replace(' ', ': '), # With colon: "Chicago: 22"
                        f"%{series_name}%",            # Fuzzy: "%Chicago 22%"
                        f"%{series_name.replace(' ', ': ')}%" # Fuzzy with colon: "%Chicago: 22%"
                    ]
                    
                    for pattern in series_patterns:
                        history_query = '''
                            SELECT 
                                date,
                                end_pti,
                                series,
                                TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
                            FROM player_history
                            WHERE series ILIKE %s
                            ORDER BY date DESC
                            LIMIT 10
                        '''
                        
                        history_records = execute_query(history_query, [pattern])
                        
                        if history_records and len(history_records) >= 2:
                            # Find the most recent and previous PTI values for this series
                            recent_pti = history_records[0]['end_pti']
                            previous_pti = history_records[1]['end_pti']
                            pti_change = recent_pti - previous_pti
                            print(f"[DEBUG] PTI change via series pattern '{pattern}': {pti_change:+.1f}")
                            break
                    else:
                        print(f"[DEBUG] No series history found for PTI change calculation")
                
                pti_data = {
                    'current_pti': current_pti,
                    'pti_change': pti_change,
                    'pti_data_available': True
                }
                print(f"[DEBUG] PTI data available: Current={current_pti}, Change={pti_change:+.1f}")
            else:
                print(f"[DEBUG] No current PTI found in players table for {player_id}")
                
        except Exception as pti_error:
            print(f"[DEBUG] Error fetching PTI data: {pti_error}")
            # Don't create sample data - only show PTI card if real data exists
        
        # Helper function to get player name from ID
        def get_player_name(player_id):
            if not player_id:
                return None
            try:
                # Try to get player name from database
                if league_id_int:
                    name_query = """
                        SELECT first_name, last_name FROM players 
                        WHERE tenniscores_player_id = %s AND league_id = %s
                    """
                    player_record = execute_query_one(name_query, [player_id, league_id_int])
                else:
                    name_query = """
                        SELECT first_name, last_name FROM players 
                        WHERE tenniscores_player_id = %s
                    """
                    player_record = execute_query_one(name_query, [player_id])
                
                if player_record:
                    return f"{player_record['first_name']} {player_record['last_name']}"
                else:
                    # Fallback: return truncated player ID if no name found
                    return f"Player {player_id[:8]}..."
            except Exception as e:
                print(f"[DEBUG] Error getting player name for {player_id}: {e}")
                return f"Player {player_id[:8]}..."
        
        # Calculate court analysis using CORRECT logic based on match position within team's matches on each date
        court_analysis = {}
        
        # Always show 4 courts
        max_courts = 4
        
        # Get all matches on the dates this player played to determine correct court assignments
        from datetime import datetime
        from collections import defaultdict
        
        # Initialize court stats for all 4 courts
        court_stats = {f'court{i}': {'matches': 0, 'wins': 0, 'losses': 0, 'players': defaultdict(int), 'partners': defaultdict(lambda: {'matches': 0, 'wins': 0, 'losses': 0})} for i in range(1, max_courts + 1)}
        player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0, 'courts': {}, 'partners': {}})
        
        def parse_date(date_str):
            if not date_str:
                return datetime.min
            # Handle the specific format from our database: "DD-Mon-YY"
            for fmt in ("%d-%b-%y", "%d-%B-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.min
        
        # Get player match dates
        player_dates = []
        for match in player_matches:
            date_str = match.get('Date', '')
            parsed_date = parse_date(date_str)
            if parsed_date != datetime.min:
                player_dates.append(parsed_date.date())
        
        if player_dates:
            # Get all matches on those dates to determine court positions
            all_matches_on_dates = execute_query("""
                SELECT 
                    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                    ms.match_date,
                    ms.id,
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.winner as "Winner",
                    ms.home_player_1_id as "Home Player 1",
                    ms.home_player_2_id as "Home Player 2",
                    ms.away_player_1_id as "Away Player 1",
                    ms.away_player_2_id as "Away Player 2"
                FROM match_scores ms
                WHERE ms.match_date = ANY(%s)
                ORDER BY ms.match_date ASC, ms.id ASC
            """, (player_dates,))
            
            # Group matches by date and team matchup
            matches_by_date_and_teams = defaultdict(lambda: defaultdict(list))
            for match in all_matches_on_dates:
                date = match.get('Date')
                home_team = match.get('Home Team', '')
                away_team = match.get('Away Team', '')
                team_matchup = f"{home_team} vs {away_team}"
                matches_by_date_and_teams[date][team_matchup].append(match)
            
            # Determine court assignments for player's matches
            for match in player_matches:
                match_date = match.get('Date')
                home_team = match.get('Home Team', '')
                away_team = match.get('Away Team', '')
                team_matchup = f"{home_team} vs {away_team}"
                
                # Find this specific match in the grouped data
                team_matches = matches_by_date_and_teams[match_date][team_matchup]
                
                # Find the position of this match within the team's matches
                court_num = None
                for i, team_match in enumerate(team_matches, 1):
                    # Match by checking if player is in this specific match
                    match_players = [
                        team_match.get('Home Player 1'),
                        team_match.get('Home Player 2'),
                        team_match.get('Away Player 1'),
                        team_match.get('Away Player 2')
                    ]
                    
                    if player_id in match_players:
                        court_num = min(i, max_courts)  # Cap at max_courts
                        break
                
                if court_num is None:
                    print(f"[WARNING] Could not determine court for match on {match_date}")
                    continue
                
                print(f"[DEBUG] Match {match_date}: {team_matchup} → Court {court_num}")
                
                court_key = f'court{court_num}'
                
                is_home = player_id in [match.get('Home Player 1'), match.get('Home Player 2')]
                won = (is_home and match.get('Winner', '').lower() == 'home') or (not is_home and match.get('Winner', '').lower() == 'away')
                
                court_stats[court_key]['matches'] += 1
                if won:
                    court_stats[court_key]['wins'] += 1
                else:
                    court_stats[court_key]['losses'] += 1
                
                # Track partners - convert IDs to names
                if is_home:
                    partner_id = match.get('Home Player 2') if match.get('Home Player 1') == player_id else match.get('Home Player 1')
                else:
                    partner_id = match.get('Away Player 2') if match.get('Away Player 1') == player_id else match.get('Away Player 1')
                
                if partner_id:
                    partner_name = get_player_name(partner_id)
                    if partner_name:
                        court_stats[court_key]['partners'][partner_name]['matches'] += 1
                        if won:
                            court_stats[court_key]['partners'][partner_name]['wins'] += 1
                        else:
                            court_stats[court_key]['partners'][partner_name]['losses'] += 1
        
        # Build court_analysis with expected structure
        for i in range(1, max_courts + 1):
            court_key = f'court{i}'
            stat = court_stats[court_key]
            matches = stat['matches']
            wins = stat['wins']
            losses = stat['losses']
            win_rate = round((wins / matches) * 100, 1) if matches > 0 else 0
            
            # Get top partners with match counts and win/loss records
            top_partners = []
            for partner_name, partner_stats in stat['partners'].items():
                if partner_name and partner_stats['matches'] > 0:  # Skip empty partners
                    partner_wins = partner_stats['wins']
                    partner_losses = partner_stats['losses']
                    match_count = partner_stats['matches']
                    win_rate = round((partner_wins / match_count) * 100, 1) if match_count > 0 else 0
                    
                    top_partners.append({
                        'name': partner_name,
                        'matches': match_count,
                        'wins': partner_wins,
                        'losses': partner_losses,
                        'winRate': win_rate
                    })
            
            # Sort by number of matches together (descending)
            top_partners.sort(key=lambda p: p['matches'], reverse=True)
            
            court_analysis[court_key] = {
                'winRate': win_rate,
                'record': f"{wins}-{losses}",
                'topPartners': top_partners[:3]  # Top 3 partners
            }
        
        # Calculate overall stats
        total_matches = len(player_matches)
        wins = 0
        
        for match in player_matches:
            is_home = player_id in [match.get('Home Player 1'), match.get('Home Player 2')]
            winner = match.get('Winner')
            won = (is_home and winner.lower() == 'home') or (not is_home and winner.lower() == 'away')
            
            if won:
                wins += 1
        
        losses = total_matches - wins
        win_rate = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0
        
        # Build current season stats
        # Calculate PTI change for current season (start to end of season)
        season_pti_change = 'N/A'
        if pti_data.get('pti_data_available', False):
            try:
                # Get season start and end PTI values from player_history
                current_pti = pti_data.get('current_pti')
                
                # Get player's database ID for history lookup
                player_pti_query = '''
                    SELECT 
                        p.id,
                        p.series_id,
                        s.name as series_name
                    FROM players p
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id = %s
                '''
                player_pti_data = execute_query_one(player_pti_query, [player_id])
                
                if player_pti_data:
                    player_db_id = player_pti_data['id']
                    series_name = player_pti_data['series_name']
                    
                    # Calculate current tennis season dates (Aug 1 - July 31)
                    from datetime import datetime
                    current_date = datetime.now()
                    current_year = current_date.year
                    current_month = current_date.month
                    
                    # Determine season year based on current date
                    if current_month >= 8:  # Aug-Dec: current season
                        season_start_year = current_year
                    else:  # Jan-Jul: previous season
                        season_start_year = current_year - 1
                    
                    season_start_date = f"{season_start_year}-08-01"
                    season_end_date = f"{season_start_year + 1}-07-31"
                    
                    # Get PTI values at season start and most recent
                    season_pti_query = '''
                        SELECT 
                            date,
                            end_pti,
                            ROW_NUMBER() OVER (ORDER BY date ASC) as rn_start,
                            ROW_NUMBER() OVER (ORDER BY date DESC) as rn_end
                        FROM player_history
                        WHERE player_id = %s 
                        AND date >= %s 
                        AND date <= %s
                        ORDER BY date
                    '''
                    
                    season_pti_records = execute_query(season_pti_query, [player_db_id, season_start_date, season_end_date])
                    
                    if season_pti_records and len(season_pti_records) >= 2:
                        # Get first and last PTI values of the season
                        start_pti = season_pti_records[0]['end_pti']
                        end_pti = season_pti_records[-1]['end_pti']
                        season_pti_change = round(end_pti - start_pti, 1)
                        print(f"[DEBUG] Season PTI change: {start_pti} -> {end_pti} = {season_pti_change:+.1f}")
                    elif series_name:
                        # Fallback: Use series matching for season PTI calculation
                        series_season_query = '''
                            SELECT 
                                date,
                                end_pti
                            FROM player_history
                            WHERE series ILIKE %s 
                            AND date >= %s 
                            AND date <= %s
                            ORDER BY date
                        '''
                        
                        series_pti_records = execute_query(series_season_query, [f"%{series_name}%", season_start_date, season_end_date])
                        
                        if series_pti_records and len(series_pti_records) >= 2:
                            start_pti = series_pti_records[0]['end_pti']
                            end_pti = series_pti_records[-1]['end_pti']
                            season_pti_change = round(end_pti - start_pti, 1)
                            print(f"[DEBUG] Season PTI change via series fallback: {start_pti} -> {end_pti} = {season_pti_change:+.1f}")
                            
            except Exception as pti_season_error:
                print(f"[DEBUG] Error calculating season PTI change: {pti_season_error}")
                season_pti_change = 'N/A'
        
        current_season = {
            'winRate': win_rate,
            'matches': total_matches,
            'wins': wins,
            'losses': losses,
            'ptiChange': season_pti_change
        }
        
        # Build career stats from player_history table
        career_stats = get_career_stats_from_db(player_id)
        
        # If no career stats found or they're the same as current season, set to None
        if (not career_stats or 
            (career_stats.get('matches', 0) == total_matches and 
             career_stats.get('wins', 0) == wins and 
             career_stats.get('losses', 0) == losses)):
            career_stats = None
        
        # Player history (empty for now since we don't have PTI data)
        player_history = {
            'progression': '',
            'seasons': []
        }
        
        # Return the complete data structure expected by the template
        result = {
            'current_season': current_season,
            'court_analysis': court_analysis,
            'career_stats': career_stats,
            'player_history': player_history,
            'videos': {'match': [], 'practice': []},
            'trends': {},
            'career_pti_change': 'N/A',
            'current_pti': pti_data.get('current_pti', 0.0),
            'weekly_pti_change': pti_data.get('pti_change', 0.0),
            'pti_data_available': pti_data.get('pti_data_available', False),
            'error': None
        }
        
        return result
        
    except Exception as e:
        print(f"Error getting player analysis: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
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
                'wins': 0,
                'losses': 0,
                'pti': 'N/A'
            },
            'player_history': {
                'progression': '',
                'seasons': []
            },
            'videos': {'match': [], 'practice': []},
            'trends': {},
            'career_pti_change': 'N/A',
            'current_pti': None,
            'weekly_pti_change': None,
            'pti_data_available': False,
            'error': str(e)
        }

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
        
        # Get matches from database for this club/series
        try:
            from database_utils import execute_query
            
            # Query the database for upcoming matches for this user's club and series
            all_matches = execute_query("""
                SELECT 
                    TO_CHAR(s.match_date, 'MM/DD/YYYY') as date,
                    TO_CHAR(s.match_time, 'HH12:MI AM') as time,
                    s.home_team,
                    s.away_team,
                    s.location,
                    l.league_id
                FROM schedule s
                LEFT JOIN leagues l ON s.league_id = l.id
                WHERE s.match_date >= CURRENT_DATE
                ORDER BY s.match_date, s.match_time
            """)
            
            print(f"[DEBUG] Loaded {len(all_matches)} total matches from database")
            
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
        from database_utils import execute_query
        
        # Query match history from database instead of JSON file
        all_matches = execute_query("""
            SELECT 
                TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                ms.home_team as "Home Team",
                ms.away_team as "Away Team",
                ms.scores as "Scores",
                ms.winner as "Winner",
                ms.home_player_1_id as "Home Player 1",
                ms.home_player_2_id as "Home Player 2", 
                ms.away_player_1_id as "Away Player 1",
                ms.away_player_2_id as "Away Player 2",
                l.league_id,
                '' as "Time",
                '' as "Location",
                '' as "Court",
                '' as "Series"
            FROM match_scores ms
            LEFT JOIN leagues l ON ms.league_id = l.id
            ORDER BY ms.match_date DESC
        """)
            
        if not user or not user.get('club'):
            return {}
            
        user_club = user['club']
        user_league_id = user.get('league_id', '')
        user_league_name = user.get('league_name', '')
        
        # Filter matches by user's league first
        def is_match_in_user_league(match):
            match_league_id = match.get('league_id')
            
            # Handle case where user_league_id is None but we have league_name
            if user_league_id is None or user_league_id == '':
                if 'APTA' in user_league_name:
                    # User is in APTA league, match APTA_CHICAGO records
                    return match_league_id == 'APTA_CHICAGO' or not match_league_id
                else:
                    # For other leagues, be more permissive during transition
                    return True
            
            # Normal league matching
            return match_league_id == user_league_id or (not match_league_id and str(user_league_id).startswith('APTA'))
        
        league_filtered_matches = [match for match in all_matches if is_match_in_user_league(match)]
        print(f"[DEBUG] get_recent_matches_for_user_club: Filtered from {len(all_matches)} to {len(league_filtered_matches)} matches for user's league (user_league_id: '{user_league_id}', user_league_name: '{user_league_name}')")
        
        # Filter matches where user's club is either home or away team
        # Make sure to capture ALL teams from this club across ALL series
        club_matches = []
        for match in league_filtered_matches:
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

def calculate_player_streaks(club_name, user_league_id=''):
    """Calculate winning and losing streaks for players across ALL matches for the club - only show significant streaks (+5/-5)"""
    try:
        from database_utils import execute_query
        
        # Load ALL match history data from database
        all_matches = execute_query("""
            SELECT 
                TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                ms.home_team as "Home Team",
                ms.away_team as "Away Team",
                ms.winner as "Winner",
                ms.home_player_1_id as "Home Player 1",
                ms.home_player_2_id as "Home Player 2",
                ms.away_player_1_id as "Away Player 1", 
                ms.away_player_2_id as "Away Player 2",
                l.league_id
            FROM match_scores ms
            LEFT JOIN leagues l ON ms.league_id = l.id
            ORDER BY ms.match_date DESC
        """)
        
        # Filter matches by user's league if provided
        if user_league_id:
            def is_match_in_user_league(match):
                match_league_id = match.get('league_id')
                
                # Handle case where user_league_id is None but we need to filter
                if user_league_id is None or user_league_id == '':
                    # For transition period, assume APTA_CHICAGO if not specified
                    return match_league_id == 'APTA_CHICAGO' or not match_league_id
                
                # Normal league matching
                return match_league_id == user_league_id or (not match_league_id and str(user_league_id).startswith('APTA'))
            
            league_filtered_matches = [match for match in all_matches if is_match_in_user_league(match)]
            print(f"[DEBUG] calculate_player_streaks: Filtered from {len(all_matches)} to {len(league_filtered_matches)} matches for user's league (user_league_id: '{user_league_id}')")
            all_matches = league_filtered_matches
        
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
                # Convert player ID to readable name
                player_display_name = get_player_name_from_id(player)
                significant_streaks.append({
                    'player_name': player_display_name,
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
        user_league_id = user.get('league_id', '')
        
        print(f"[DEBUG] get_mobile_club_data called with user: {user}")
        print(f"[DEBUG] club_name: '{club_name}', league_id: '{user_league_id}'")
        
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
                    
                # Resolve player IDs to readable names
                home_player_1_name = get_player_name_from_id(match['home_player_1']) if match.get('home_player_1') else 'Unknown'
                home_player_2_name = get_player_name_from_id(match['home_player_2']) if match.get('home_player_2') else 'Unknown'
                away_player_1_name = get_player_name_from_id(match['away_player_1']) if match.get('away_player_1') else 'Unknown'
                away_player_2_name = get_player_name_from_id(match['away_player_2']) if match.get('away_player_2') else 'Unknown'
                    
                team_matches[team]['matches'].append({
                    'court': court_num,
                    'home_players': f"{home_player_1_name}/{home_player_2_name}" if is_home else f"{away_player_1_name}/{away_player_2_name}",
                    'away_players': f"{away_player_1_name}/{away_player_2_name}" if is_home else f"{home_player_1_name}/{home_player_2_name}",
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
        
        # Calculate club standings (for all teams in the club across all series) - filtered by user's league
        from database_utils import execute_query
        
        # Get user league information for filtering
        user_league_name = user.get('league_name', '')
        
        tennaqua_standings = []
        try:
            # Query series_stats table from database instead of JSON file
            stats_query = """
                SELECT 
                    ss.series,
                    ss.team,
                    ss.points,
                    ss.matches_won,
                    ss.matches_lost,
                    ss.matches_tied,
                    l.league_id
                FROM series_stats ss
                LEFT JOIN leagues l ON ss.league_id = l.id
                ORDER BY ss.series, ss.points DESC
            """
            
            stats_data = execute_query(stats_query)
            print(f"[DEBUG] Loaded {len(stats_data)} team stats records from database")
            
            # Debug: Check if any Tennaqua teams exist
            tennaqua_teams = [team for team in stats_data if team.get('team', '').startswith(club_name)]
            print(f"[DEBUG] Found {len(tennaqua_teams)} teams starting with '{club_name}'")
            for team in tennaqua_teams[:3]:
                print(f"[DEBUG]   {team.get('team')} - {team.get('series')} - league: {team.get('league_id')}")
            
            # Filter stats_data by user's league
            def is_user_league(team_data):
                team_league_id = team_data.get('league_id')
                
                # Handle case where user_league_id is None but we have league_name
                if user_league_id is None or user_league_id == '':
                    if 'APTA' in user_league_name:
                        # User is in APTA league, match APTA_CHICAGO records or records without league_id
                        return team_league_id == 'APTA_CHICAGO' or not team_league_id
                    else:
                        # For other leagues, be more permissive during transition
                        return True
                
                # Normal league matching
                return team_league_id == user_league_id or (not team_league_id and str(user_league_id).startswith('APTA'))
            
            league_filtered_stats = [team for team in stats_data if is_user_league(team)]
            print(f"[DEBUG] Filtered from {len(stats_data)} total teams to {len(league_filtered_stats)} teams in user's league (user_league_id: '{user_league_id}', user_league_name: '{user_league_name}')")
                
            for team_stats in league_filtered_stats:
                if not team_stats.get('team', '').startswith(club_name):
                    continue
                    
                series = team_stats.get('series')
                if not series:
                    continue
                    
                # Get all teams in this series (from the league-filtered data)
                series_teams = [team for team in league_filtered_stats if team.get('series') == series]
                
                # Calculate average points
                for team in series_teams:
                    total_matches = team.get('matches_won', 0) + team.get('matches_lost', 0) + team.get('matches_tied', 0)
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
            print(f"Error loading series stats from database: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
        
        # Calculate head-to-head records (filtered by user's league)
        head_to_head = {}
        
        # Load ALL match history for comprehensive head-to-head records
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            match_history_path = os.path.join(project_root, 'data', 'leagues', 'all', 'match_history.json')
            
            with open(match_history_path, 'r') as f:
                all_match_history = json.load(f)
            
            # Filter match history by user's league
            def is_match_in_user_league(match):
                match_league_id = match.get('league_id')
                
                # Handle case where user_league_id is None but we have league_name
                if user_league_id is None or user_league_id == '':
                    if 'APTA' in user_league_name:
                        # User is in APTA league, match APTA_CHICAGO records
                        return match_league_id == 'APTA_CHICAGO' or not match_league_id
                    else:
                        # For other leagues, be more permissive during transition
                        return True
                
                # Normal league matching
                return match_league_id == user_league_id or (not match_league_id and str(user_league_id).startswith('APTA'))
            
            league_filtered_matches = [match for match in all_match_history if is_match_in_user_league(match)]
            print(f"[DEBUG] Filtered from {len(all_match_history)} total matches to {len(league_filtered_matches)} matches in user's league (user_league_id: '{user_league_id}', user_league_name: '{user_league_name}')")
            
            for match in league_filtered_matches:
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
        
        # Calculate player streaks (filtered by user's league)
        player_streaks = calculate_player_streaks(club_name, user_league_id)
        
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
    """Get all players at the user's club with optional filtering (filtered by user's league)"""
    try:
        # Get user's club and league from user data
        user_club = user.get('club')
        user_league_id = user.get('league_id', '')
        
        if not user_club:
            return {
                'players': [],
                'available_series': [],
                'pti_range': {'min': 0, 'max': 100},
                'error': 'User club not found'
            }

        print(f"\n=== DEBUG: get_club_players_data ===")
        print(f"User club: '{user_club}', league_id: '{user_league_id}'")
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

        # Filter players by user's league first
        def is_player_in_user_league(player):
            player_league = player.get('League')
            
            # Handle case where user_league_id is None but we have league_name
            if user_league_id is None or user_league_id == '':
                user_league_name = user.get('league_name', '')
                if 'APTA' in user_league_name:
                    # User is in APTA league, match APTA_CHICAGO records
                    return player_league == 'APTA_CHICAGO' or not player_league
                else:
                    # For other leagues, be more permissive during transition
                    return True
            
            # Normal league matching
            return player_league == user_league_id
        
        league_filtered_players = [player for player in all_players if is_player_in_user_league(player)]
        print(f"Filtered from {len(all_players)} total players to {len(league_filtered_players)} players in user's league (user_league_id: '{user_league_id}')")
        
        # Use the league-filtered players for all subsequent processing
        all_players = league_filtered_players
        
        if not all_players:
            return {
                'players': [],
                'available_series': [],
                'pti_range': {'min': 0, 'max': 100},
                'pti_filters_available': False,
                'error': 'Error loading player data'
            }

        # Check if players in this league have valid PTI values
        valid_pti_count = 0
        total_players_checked = 0
        for player in all_players:
            total_players_checked += 1
            try:
                pti_str = str(player.get('PTI', 'N/A')).strip()
                if pti_str and pti_str != 'N/A' and pti_str != '':
                    float(pti_str)  # Test if it's a valid number
                    valid_pti_count += 1
            except (ValueError, TypeError):
                continue
                
        # Determine if PTI filters should be available
        # Show PTI filters only if at least 10% of players have valid PTI values
        pti_percentage = (valid_pti_count / total_players_checked * 100) if total_players_checked > 0 else 0
        pti_filters_available = pti_percentage >= 10.0
        
        print(f"[DEBUG] PTI analysis: {valid_pti_count}/{total_players_checked} players have valid PTI ({pti_percentage:.1f}%)")
        print(f"[DEBUG] PTI filters available: {pti_filters_available}")

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

        # Load contact information from database instead of CSV files
        contact_info = {}
        try:
            # Get contact info from players table (phone and email columns if they exist)
            contact_query = """
                SELECT 
                    CONCAT(first_name, ' ', last_name) as full_name,
                    COALESCE(phone, '') as phone,
                    COALESCE(email, '') as email
                FROM players p
                WHERE p.first_name IS NOT NULL AND p.last_name IS NOT NULL
            """
            
            # Check if phone and email columns exist in players table
            try:
                contact_data = execute_query(contact_query)
                for row in contact_data:
                    full_name = row['full_name']
                    if full_name:
                        contact_info[full_name.lower()] = {
                            'phone': row.get('phone', ''),
                            'email': row.get('email', '')
                        }
                print(f"Loaded {len(contact_info)} contact records from database")
            except Exception as contact_error:
                print(f"Contact info columns may not exist in players table: {contact_error}")
                # For now, continue without contact info - this is not critical for functionality
                
        except Exception as e:
            print(f"Error loading contact info from database: {e}")
            # Continue without contact info

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
                
                if first_name_filter and first_name_filter.lower() not in player['First Name'].lower():
                    continue
                    
                if last_name_filter and last_name_filter.lower() not in player['Last Name'].lower():
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
            'pti_filters_available': pti_filters_available,
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
            'pti_filters_available': False,
            'error': str(e)
        }

def get_mobile_improve_data(user):
    """Get data for the mobile improve page including paddle tips and training guide"""
    try:
        # Load paddle tips from JSON file
        paddle_tips = []
        try:
            # Use current working directory since server.py runs from project root
            tips_path = os.path.join('data', 'leagues', 'all', 'improve_data', 'paddle_tips.json')
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
            guide_path = os.path.join('data', 'leagues', 'all', 'improve_data', 'complete_platform_tennis_training_guide.json')
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

def get_mobile_team_data(user):
    """Get team data for mobile my team page"""
    print(f"🚨 FUNCTION CALLED: get_mobile_team_data with user: {user}")
    try:
        # DEBUG: Start database debug FIRST
        print(f"[DEBUG DATABASE QUERY] Starting database debug at function start...")
        
        # Extract team name from user club and series (same logic as backup)
        club = user.get('club')
        series = user.get('series')
        
        if not club or not series:
            print(f"[DEBUG ERROR] User club or series not found: club={club}, series={series}")
            return {
                'team_data': None,
                'court_analysis': {},
                'top_players': [],
                'error': 'User club or series not found'
            }
        
        # Handle different team naming conventions based on league
        league_id = user.get('league_id', '')
        
        # Convert league_id to integer foreign key for database queries
        league_id_int = None
        if isinstance(league_id, str) and league_id != '':
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", 
                    [league_id]
                )
                if league_record:
                    league_id_int = league_record['id']
                    print(f"[DEBUG] get_mobile_team_data: Converted league_id '{league_id}' to integer: {league_id_int}")
                else:
                    print(f"[WARNING] get_mobile_team_data: League '{league_id}' not found in leagues table")
            except Exception as e:
                print(f"[DEBUG] get_mobile_team_data: Could not convert league ID: {e}")
        elif isinstance(league_id, int):
            league_id_int = league_id
            print(f"[DEBUG] get_mobile_team_data: League_id already integer: {league_id_int}")
        
        if league_id == 'NSTF':
            # NSTF format: "Tennaqua S2B" from series "Series 2B"
            import re
            # Extract the series suffix (e.g., "2B" from "Series 2B")
            series_match = re.search(r'Series\s+(.+)', series)
            if series_match:
                series_suffix = series_match.group(1)
                team = f"{club} S{series_suffix}"
            else:
                # Fallback: try to extract any suffix after "Series"
                series_suffix = series.replace('Series', '').strip()
                team = f"{club} S{series_suffix}" if series_suffix else f"{club} S1"
        else:
            # Other leagues - try multiple formats
            import re
            
            # First try: "Tennaqua - 22" format for series like "Chicago 22"
            m = re.search(r'(\d+)', series)
            series_num = m.group(1) if m else ''
            team = f"{club} - {series_num}"
            
            # If that doesn't work, try NSTF format as fallback
            # This handles cases where league_id might be wrong but team exists in NSTF format
            team_fallback = None
            if series_num:
                # Try common NSTF patterns: S1, S2A, S2B, S3, etc.
                possible_patterns = [
                    f"S{series_num}",
                    f"S{series_num}A", 
                    f"S{series_num}B",
                    f"S{series_num[0]}{series_num[1:]}A" if len(series_num) > 1 else None,
                    f"S{series_num[0]}{series_num[1:]}B" if len(series_num) > 1 else None
                ]
                # Remove None values
                possible_patterns = [p for p in possible_patterns if p]
                
                for pattern in possible_patterns:
                    team_fallback = f"{club} {pattern}"
                    # Check if this team exists in series_stats
                    test_query = "SELECT COUNT(*) as count FROM series_stats WHERE team = %s"
                    try:
                        result = execute_query_one(test_query, [team_fallback])
                        if result and result.get('count', 0) > 0:
                            team = team_fallback
                            break
                    except:
                        pass
        
        print(f"[DEBUG] get_mobile_team_data: Final team name: '{team}' for user {user.get('first_name')} {user.get('last_name')}")
        
        # MORE DEBUG: Show that we reached this point
        print(f"[DEBUG DATABASE QUERY] About to query database for team: {team}")
        
        # Query team stats and matches from database
        # Note: execute_query and execute_query_one are already imported at module level
        
        # Get team stats
        team_stats_query = """
            SELECT 
                team,
                points,
                matches_won,
                matches_lost,
                lines_won,
                lines_lost,
                sets_won,
                sets_lost,
                games_won,
                games_lost
            FROM series_stats
            WHERE team = %s
        """
        team_stats = execute_query_one(team_stats_query, [team])
        
        # Get team matches
        if league_id_int:
            matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                ORDER BY match_date DESC
            """
            team_matches = execute_query(matches_query, [team, team, league_id_int])
        else:
            matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                ORDER BY match_date DESC
            """
            team_matches = execute_query(matches_query, [team, team])
        
        # DEBUG: Raw database query to understand the data structure
        print(f"[DEBUG DATABASE QUERY] Starting database debug...")
        try:
            print(f"[DEBUG] Team: {team}, League ID Int: {league_id_int}")
            
            # Simple debug query first
            simple_query = "SELECT COUNT(*) as total FROM match_scores WHERE (home_team = %s OR away_team = %s)"
            if league_id_int:
                simple_query += " AND league_id = %s"
                total_count = execute_query_one(simple_query, [team, team, league_id_int])
            else:
                total_count = execute_query_one(simple_query, [team, team])
            
            print(f"[DEBUG] Total matches for {team}: {total_count['total']}")
            
            # Now try the detailed query
            if league_id_int:
                debug_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as formatted_date,
                        id,
                        home_team,
                        away_team,
                        winner,
                        scores
                    FROM match_scores
                    WHERE (home_team = %s OR away_team = %s)
                    AND league_id = %s
                    ORDER BY match_date DESC, id ASC
                    LIMIT 20
                """
                debug_matches = execute_query(debug_query, [team, team, league_id_int])
            else:
                debug_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as formatted_date,
                        id,
                        home_team,
                        away_team,
                        winner,
                        scores
                    FROM match_scores
                    WHERE (home_team = %s OR away_team = %s)
                    ORDER BY match_date DESC, id ASC
                    LIMIT 20
                """
                debug_matches = execute_query(debug_query, [team, team])
            
            print(f"[DEBUG] Raw matches from database (first 20):")
            for i, match in enumerate(debug_matches):
                print(f"  {i+1}. ID={match['id']}, Date={match['formatted_date']}, {match['home_team']} vs {match['away_team']}")
                print(f"      Winner={match['winner']}, Scores={match['scores']}")
            
            # Check for court columns
            print(f"[DEBUG] Checking match_scores table structure...")
            court_check_query = """
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'match_scores' 
                AND column_name ILIKE '%court%'
                ORDER BY column_name
            """
            court_columns = execute_query(court_check_query)
            
            if court_columns:
                print(f"[DEBUG] Found court columns: {[(col['column_name'], col['data_type']) for col in court_columns]}")
                
                # Sample actual court data
                court_cols = [col['column_name'] for col in court_columns]
                sample_query = f"""
                    SELECT id, TO_CHAR(match_date, 'DD-Mon-YY') as date, {', '.join(court_cols)}
                    FROM match_scores
                    WHERE (home_team = %s OR away_team = %s)
                    ORDER BY match_date DESC
                    LIMIT 5
                """
                if league_id_int:
                    sample_query = f"""
                        SELECT id, TO_CHAR(match_date, 'DD-Mon-YY') as date, {', '.join(court_cols)}
                        FROM match_scores
                        WHERE (home_team = %s OR away_team = %s) AND league_id = %s
                        ORDER BY match_date DESC
                        LIMIT 5
                    """
                    sample_data = execute_query(sample_query, [team, team, league_id_int])
                else:
                    sample_data = execute_query(sample_query, [team, team])
                
                print(f"[DEBUG] Sample court data:")
                for row in sample_data:
                    court_vals = ', '.join([f"{col}={row.get(col)}" for col in court_cols])
                    print(f"  ID={row['id']}, Date={row['date']}: {court_vals}")
            else:
                print(f"[DEBUG] No court columns found in match_scores table")
                
        except Exception as e:
            print(f"[DEBUG ERROR] Database debug failed: {str(e)}")
            import traceback
            print(f"[DEBUG ERROR] Traceback: {traceback.format_exc()}")
        
        # Calculate court analysis and top players
        court_analysis = {}
        top_players = []
        
        if team_matches:
            # DEBUG: Show what data we're working with
            print(f"[DEBUG COURT ORDER] Team: {team}")
            print(f"[DEBUG COURT ORDER] Total matches found: {len(team_matches)}")
            print(f"[DEBUG COURT ORDER] First 10 matches from database:")
            for i, match in enumerate(team_matches[:10]):
                print(f"  Match {i+1}: Date={match.get('Date')}, Home={match.get('Home Team')}, Away={match.get('Away Team')}, Winner={match.get('Winner')}")
                print(f"    Home Players: {match.get('Home Player 1')}, {match.get('Home Player 2')}")
                print(f"    Away Players: {match.get('Away Player 1')}, {match.get('Away Player 2')}")
            
                    # Initialize court stats (always 4 courts)
        from collections import defaultdict
        
        # Group by date to understand court patterns
        matches_by_date = defaultdict(list)
        for match in team_matches:
            date = match.get('Date')
            matches_by_date[date].append(match)
        
        print(f"[DEBUG COURT ORDER] Matches grouped by date:")
        for date, date_matches in sorted(matches_by_date.items()):
            print(f"  {date}: {len(date_matches)} match(es)")
            for i, match in enumerate(date_matches):
                print(f"    {i+1}. {match.get('Home Team')} vs {match.get('Away Team')} (Winner: {match.get('Winner')})")
        court_stats = {f'court{i}': {'matches': 0, 'wins': 0, 'losses': 0, 'players': defaultdict(lambda: {'matches': 0, 'wins': 0, 'losses': 0})} for i in range(1, 5)}
        player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0, 'courts': {}, 'partners': {}})
        
        # CORRECT approach: Use database order (ORDER BY id) for court assignment
        print(f"[DEBUG COURT ORDER] Using database order for court assignment:")
        
        # Get all matches on the dates this team played, ordered by database ID
        team_dates = list(set([match.get('Date') for match in team_matches]))
        
        # Convert date strings back to date objects for database query
        from datetime import datetime
        date_objects = []
        for date_str in team_dates:
            try:
                # Parse "DD-Mon-YY" format
                date_obj = datetime.strptime(date_str, '%d-%b-%y').date()
                date_objects.append(date_obj)
            except ValueError:
                print(f"[DEBUG] Could not parse date: {date_str}")
        
        # Determine maximum courts dynamically based on actual match data
        max_courts = 4  # Default fallback
        
        if date_objects:
            # Get all matches on those dates in database order
            all_matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2", 
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2",
                    winner as "Winner",
                    id
                FROM match_scores
                WHERE match_date = ANY(%s)
                ORDER BY match_date, id
            """
            all_matches = execute_query(all_matches_query, [date_objects])
            
            # Group by date and team matchup to determine max courts per team match
            matches_by_date_and_teams = defaultdict(lambda: defaultdict(list))
            for match in all_matches:
                date = match.get('Date')
                home_team = match.get('Home Team', '')
                away_team = match.get('Away Team', '')
                team_matchup = f"{home_team} vs {away_team}"
                matches_by_date_and_teams[date][team_matchup].append(match)
            
            # Calculate the maximum courts used in any single team matchup
            team_matchup_court_counts = []
            for date, team_matchups in matches_by_date_and_teams.items():
                for matchup, matchup_matches in team_matchups.items():
                    # Check if this team is involved in this matchup
                    if team in matchup:
                        team_matchup_court_counts.append(len(matchup_matches))
            
            if team_matchup_court_counts:
                max_courts = max(team_matchup_court_counts)
                print(f"[DEBUG COURT ORDER] Detected max courts for team '{team}': {max_courts} (max courts in any single team matchup)")
            else:
                print(f"[DEBUG COURT ORDER] Could not determine max courts, using default: {max_courts}")
            
            # Group by date and assign courts sequentially
            matches_by_date_ordered = defaultdict(list)
            for match in all_matches:
                date = match.get('Date')
                matches_by_date_ordered[date].append(match)
            
            # Create mapping of team matches to courts
            match_to_court = {}
            
            for date, date_matches in matches_by_date_ordered.items():
                print(f"  Date {date}: {len(date_matches)} matches in database order:")
                
                # Group matches by team matchup within this date
                team_matchup_groups = defaultdict(list)
                for match in date_matches:
                    home_team = match.get('Home Team', '')
                    away_team = match.get('Away Team', '')
                    team_matchup = f"{home_team} vs {away_team}"
                    team_matchup_groups[team_matchup].append(match)
                
                # Assign courts within each team matchup
                for team_matchup, matchup_matches in team_matchup_groups.items():
                    print(f"    Team matchup: {team_matchup} ({len(matchup_matches)} matches)")
                    
                    # Sort matches within this team matchup by database ID to ensure consistent ordering
                    matchup_matches_sorted = sorted(matchup_matches, key=lambda x: x.get('id', 0))
                    
                    # Assign courts sequentially within this team matchup (1, 2, 3, 4, 5...)
                    for court_index, match in enumerate(matchup_matches_sorted):
                        court_num = court_index + 1  # Courts 1, 2, 3, 4, 5 within this matchup
                        
                        print(f"      Court {court_num}: Match ID {match.get('id')} - Players: {match.get('Home Player 1')}, {match.get('Home Player 2')} vs {match.get('Away Player 1')}, {match.get('Away Player 2')}")
                        
                        # Find corresponding team match and assign court
                        for original_index, team_match in enumerate(team_matches):
                            if (team_match.get('Date') == date and
                                team_match.get('Home Team') == match.get('Home Team') and
                                team_match.get('Away Team') == match.get('Away Team') and
                                team_match.get('Home Player 1') == match.get('Home Player 1') and
                                team_match.get('Home Player 2') == match.get('Home Player 2') and
                                team_match.get('Away Player 1') == match.get('Away Player 1') and
                                team_match.get('Away Player 2') == match.get('Away Player 2')):
                                match_to_court[original_index] = court_num
                                break
        else:
            # Fallback: create empty mapping
            match_to_court = {}
        
        # Initialize court stats dynamically based on detected max courts
        court_stats = {f'court{i}': {'matches': 0, 'wins': 0, 'losses': 0, 'players': defaultdict(lambda: {'matches': 0, 'wins': 0, 'losses': 0})} for i in range(1, max_courts + 1)}
        
        # Now process each match with its correct court assignment
        for match_index, match in enumerate(team_matches):
            court_num = match_to_court.get(match_index, 1)  # Default to court 1 if not found
            
            print(f"  Match {match_index+1} ({match.get('Date')}): {match.get('Home Team')} vs {match.get('Away Team')} -> Court {court_num}")
            
            court_key = f'court{court_num}'
        
            is_home = match.get('Home Team') == team
            
            # Get player names for this team
            if is_home:
                players = [match.get('Home Player 1'), match.get('Home Player 2')]
            else:
                players = [match.get('Away Player 1'), match.get('Away Player 2')]
            
            # Filter out empty player names
            players = [p for p in players if p and p.strip()]
            
            # Determine win/loss
            winner = match.get('Winner', '').lower()
            won = (is_home and winner == 'home') or (not is_home and winner == 'away')
            
            court_stats[court_key]['matches'] += 1
            if won:
                court_stats[court_key]['wins'] += 1
            else:
                court_stats[court_key]['losses'] += 1
            
            for p in players:
                # Convert player ID to readable name
                player_name = get_player_name_from_id(p) if p else p
                
                court_stats[court_key]['players'][player_name]['matches'] += 1
                if won:
                    court_stats[court_key]['players'][player_name]['wins'] += 1
                else:
                    court_stats[court_key]['players'][player_name]['losses'] += 1
                
                player_stats[player_name]['matches'] += 1
                if won:
                    player_stats[player_name]['wins'] += 1
                
                # Track court performance for each player
                if court_key not in player_stats[player_name]['courts']:
                    player_stats[player_name]['courts'][court_key] = {'matches': 0, 'wins': 0}
                player_stats[player_name]['courts'][court_key]['matches'] += 1
                if won:
                    player_stats[player_name]['courts'][court_key]['wins'] += 1
        
        # Build court_analysis (dynamic courts based on detected max)
        print(f"[DEBUG COURT ORDER] Final court statistics:")
        for i in range(1, max_courts + 1):
            court_key = f'court{i}'
            stat = court_stats[court_key]
            matches = stat['matches']
            wins = stat['wins']
            losses = stat['losses']
            win_rate = round((wins / matches) * 100, 1) if matches > 0 else 0
            
            print(f"  Court {i}: {matches} matches, {wins}-{losses} record, {win_rate}% win rate")
            if stat['players']:
                top_players_list = sorted(stat['players'].items(), key=lambda x: x[1]['matches'], reverse=True)[:3]
                player_summaries = []
                for name, data in top_players_list:
                    win_pct = round((data['wins'] / data['matches']) * 100, 1) if data['matches'] > 0 else 0
                    player_summaries.append(f"{name} ({data['matches']} matches, {win_pct}%)")
                print(f"    Top players: {player_summaries}")
            
            # Top players by matches played on this court
            top_players_court = sorted(stat['players'].items(), key=lambda x: x[1]['matches'], reverse=True)[:3]
            court_analysis[court_key] = {
                'winRate': win_rate,    # camelCase to match analyze-me
                'record': f"{wins}-{losses}",
                'topPartners': [{
                    'name': player_name, 
                    'matches': player_data['matches'],
                    'wins': player_data['wins'],
                    'losses': player_data['losses'],
                    'winRate': round((player_data['wins'] / player_data['matches']) * 100, 1) if player_data['matches'] > 0 else 0
                } for player_name, player_data in top_players_court]
            }
        
        # Build top_players list
        top_players = []
        for name, stats in player_stats.items():
            # Show all players regardless of match count
            win_rate = round((stats['wins']/stats['matches'])*100, 1) if stats['matches'] > 0 else 0
            
            # Best court
            best_court = None
            best_court_rate = 0
            for court, cstats in stats['courts'].items():
                rate = round((cstats['wins']/cstats['matches'])*100, 1) if cstats['matches'] > 0 else 0
                if rate > best_court_rate or (rate == best_court_rate and cstats['matches'] > 0):
                    best_court_rate = rate
                    best_court = f"{court} ({rate}%)"
            
            # Best partner
            best_partner = None
            best_partner_rate = 0
            for partner, pstats in stats['partners'].items():
                rate = round((pstats['wins']/pstats['matches'])*100, 1) if pstats['matches'] > 0 else 0
                if rate > best_partner_rate or (rate == best_partner_rate and pstats['matches'] > 0):
                    best_partner_rate = rate
                    best_partner = partner
            
            top_players.append({
                'name': name,
                'matches': stats['matches'],
                'win_rate': win_rate,
                'best_court': best_court or 'N/A',
                'best_partner': f"{best_partner} ({best_partner_rate}%)" if best_partner else 'N/A'
            })
        
        top_players = sorted(top_players, key=lambda x: -x['win_rate'])
    
        # Build team stats
        if team_stats:
            # Calculate percentages safely
            matches_won = team_stats.get('matches_won', 0)
            matches_lost = team_stats.get('matches_lost', 0)
            matches_total = matches_won + matches_lost
            matches_pct = f"{round((matches_won / matches_total) * 100, 1)}%" if matches_total > 0 else "0%"
            
            lines_won = team_stats.get('lines_won', 0)
            lines_lost = team_stats.get('lines_lost', 0)
            lines_total = lines_won + lines_lost
            lines_pct = f"{round((lines_won / lines_total) * 100, 1)}%" if lines_total > 0 else "0%"
            
            sets_won = team_stats.get('sets_won', 0)
            sets_lost = team_stats.get('sets_lost', 0)
            sets_total = sets_won + sets_lost
            sets_pct = f"{round((sets_won / sets_total) * 100, 1)}%" if sets_total > 0 else "0%"
            
            games_won = team_stats.get('games_won', 0)
            games_lost = team_stats.get('games_lost', 0)
            games_total = games_won + games_lost
            games_pct = f"{round((games_won / games_total) * 100, 1)}%" if games_total > 0 else "0%"
            
            team_data = {
                'team': team,
                'points': team_stats.get('points', 0),
                'matches': {
                    'won': matches_won,
                    'lost': matches_lost,
                    'percentage': matches_pct
                },
                'lines': {
                    'won': lines_won,
                    'lost': lines_lost,
                    'percentage': lines_pct
                },
                'sets': {
                    'won': sets_won,
                    'lost': sets_lost,
                    'percentage': sets_pct
                },
                'games': {
                    'won': games_won,
                    'lost': games_lost,
                    'percentage': games_pct
                }
            }
        else:
            team_data = {
                'team': team,
                'points': 0,
                'matches': {'won': 0, 'lost': 0, 'percentage': '0%'},
                'lines': {'won': 0, 'lost': 0, 'percentage': '0%'},
                'sets': {'won': 0, 'lost': 0, 'percentage': '0%'},
                'games': {'won': 0, 'lost': 0, 'percentage': '0%'}
            }
        
        return {
            'team_data': team_data,
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
    """Get teams and players data for mobile interface - filtered by user's league"""
    try:
        from flask import request
        
        # Get team parameter from request
        team = request.args.get('team')
        
        # Get user's league for filtering
        user_league_id = user.get('league_id', '')
        print(f"[DEBUG] get_teams_players_data: User league_id string: '{user_league_id}'")
        
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != '':
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", 
                    [user_league_id]
                )
                if league_record:
                    league_id_int = league_record['id']
                    print(f"[DEBUG] Converted league_id '{user_league_id}' to integer: {league_id_int}")
                else:
                    print(f"[WARNING] League '{user_league_id}' not found in leagues table")
            except Exception as e:
                print(f"[DEBUG] Could not convert league ID: {e}")
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
            print(f"[DEBUG] League_id already integer: {league_id_int}")
        
        # Query team stats and matches from database
        # Note: execute_query and execute_query_one are already imported at module level
        
        # Get all teams in user's league - only filter if we have a valid league_id
        if league_id_int:
            teams_query = """
                SELECT DISTINCT team
                FROM series_stats
                WHERE league_id = %s
                ORDER BY team
            """
            all_teams = [row['team'] for row in execute_query(teams_query, [league_id_int])]
        else:
            teams_query = """
                SELECT DISTINCT team
                FROM series_stats
                ORDER BY team
            """
            all_teams = [row['team'] for row in execute_query(teams_query)]
        
        if not team or team not in all_teams:
            # No team selected or invalid team
            return {
                'team_analysis_data': None,
                'all_teams': all_teams,
                'selected_team': None
            }
        
        # Get team stats
        if league_id_int:
            team_stats_query = """
                SELECT *
                FROM series_stats
                WHERE team = %s AND league_id = %s
            """
            team_stats = execute_query_one(team_stats_query, [team, league_id_int])
        else:
            team_stats_query = """
                SELECT *
                FROM series_stats
                WHERE team = %s
            """
            team_stats = execute_query_one(team_stats_query, [team])
        
        # Get team matches
        if league_id_int:
            matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                ORDER BY match_date DESC
            """
            team_matches = execute_query(matches_query, [team, team, league_id_int])
        else:
            matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                ORDER BY match_date DESC
            """
            team_matches = execute_query(matches_query, [team, team])
        
        # Calculate team analysis
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
    if not stats:
        return {
            "points": 0,
            "match_win_rate": 0.0,
            "match_record": "0-0",
            "line_win_rate": 0.0,
            "set_win_rate": 0.0,
            "game_win_rate": 0.0
        }
    
    # Handle both nested structure (legacy) and flat structure (database)
    if "matches" in stats and isinstance(stats["matches"], dict):
        # Legacy nested structure
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
    else:
        # Flat database structure
        points = stats.get("points", 0)
        
        # Match stats
        matches_won = stats.get("matches_won", 0)
        matches_lost = stats.get("matches_lost", 0)
        matches_total = matches_won + matches_lost
        match_win_rate = round((matches_won / matches_total) * 100, 1) if matches_total > 0 else 0.0
        
        # Line stats
        lines_won = stats.get("lines_won", 0)
        lines_lost = stats.get("lines_lost", 0)
        lines_total = lines_won + lines_lost
        line_win_rate = round((lines_won / lines_total) * 100, 1) if lines_total > 0 else 0.0
        
        # Set stats
        sets_won = stats.get("sets_won", 0)
        sets_lost = stats.get("sets_lost", 0)
        sets_total = sets_won + sets_lost
        set_win_rate = round((sets_won / sets_total) * 100, 1) if sets_total > 0 else 0.0
        
        # Game stats
        games_won = stats.get("games_won", 0)
        games_lost = stats.get("games_lost", 0)
        games_total = games_won + games_lost
        game_win_rate = round((games_won / games_total) * 100, 1) if games_total > 0 else 0.0
        
        overview = {
            "points": points,
            "match_win_rate": match_win_rate,
            "match_record": f"{matches_won}-{matches_lost}",
            "line_win_rate": line_win_rate,
            "set_win_rate": set_win_rate,
            "game_win_rate": game_win_rate
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
            winner_is_home = match.get('Winner', '').lower() == 'home'
            team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
            
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
        
        # Court Analysis - Use correct assignment logic (like analyze-me page)
        from datetime import datetime
        from collections import defaultdict
        
        def parse_date(date_str):
            if not date_str:
                return datetime.min
            # Handle the specific format from our database
            for fmt in ("%d-%b-%y", "%d-%B-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(str(date_str), fmt)
                except ValueError:
                    continue
            return datetime.min
        
        # Get team match dates
        team_dates = []
        for match in team_matches:
            date_str = match.get('Date', '')
            parsed_date = parse_date(date_str)
            if parsed_date != datetime.min:
                team_dates.append(parsed_date.date())
        
        court_analysis = {}
        if team_dates:
            # Get all matches on those dates to determine correct court assignments
            all_matches_on_dates = execute_query("""
                SELECT 
                    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                    ms.match_date,
                    ms.id,
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.winner as "Winner",
                    ms.home_player_1_id as "Home Player 1",
                    ms.home_player_2_id as "Home Player 2",
                    ms.away_player_1_id as "Away Player 1",
                    ms.away_player_2_id as "Away Player 2"
                FROM match_scores ms
                WHERE ms.match_date = ANY(%s)
                ORDER BY ms.match_date ASC, ms.id ASC
            """, (team_dates,))
            
            # Group matches by date and team matchup
            matches_by_date_and_teams = defaultdict(lambda: defaultdict(list))
            for match in all_matches_on_dates:
                date = match.get('Date')
                home_team = match.get('Home Team', '')
                away_team = match.get('Away Team', '')
                team_matchup = f"{home_team} vs {away_team}"
                matches_by_date_and_teams[date][team_matchup].append(match)
            
            # Initialize court stats for 4 courts
            for i in range(1, 5):
                court_name = f'Court {i}'
                court_matches = []
                
                # Find matches for this court using correct logic
                for match in team_matches:
                    match_date = match.get('Date')
                    home_team = match.get('Home Team', '')
                    away_team = match.get('Away Team', '')
                    team_matchup = f"{home_team} vs {away_team}"
                    
                    # Find this specific match in the grouped data
                    team_day_matches = matches_by_date_and_teams[match_date][team_matchup]
                    
                    # Check if this match is assigned to court i
                    for j, team_match in enumerate(team_day_matches, 1):
                        # Match by checking if it's the same match (by players)
                        if (match.get('Home Player 1') == team_match.get('Home Player 1') and
                            match.get('Home Player 2') == team_match.get('Home Player 2') and
                            match.get('Away Player 1') == team_match.get('Away Player 1') and
                            match.get('Away Player 2') == team_match.get('Away Player 2')):
                            if j == i:  # This match belongs to court i
                                court_matches.append(match)
                            break
                
                wins = losses = 0
                player_win_counts = {}
                
                for match in court_matches:
                    is_home = match.get('Home Team') == team
                    winner_is_home = match.get('Winner', '').lower() == 'home'
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
                
                # Top players by win rate (show all players for this court)
                key_players = sorted([
                    {'name': get_player_name_from_id(p), 'win_rate': round((d['wins']/d['matches'])*100, 1), 'matches': d['matches']}
                    for p, d in player_win_counts.items()
                ], key=lambda x: -x['win_rate'])[:3]
                
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
        player_stats = defaultdict(lambda: {'matches': 0, 'wins': 0, 'courts': {}, 'partners': {}})
        
        if team_dates:
            for match in team_matches:
                is_home = match.get('Home Team') == team
                player1 = match.get('Home Player 1') if is_home else match.get('Away Player 1')
                player2 = match.get('Home Player 2') if is_home else match.get('Away Player 2')
                winner_is_home = match.get('Winner', '').lower() == 'home'
                team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
                
                # Determine correct court assignment for this match
                match_date = match.get('Date')
                home_team = match.get('Home Team', '')
                away_team = match.get('Away Team', '')
                team_matchup = f"{home_team} vs {away_team}"
                
                team_day_matches = matches_by_date_and_teams[match_date][team_matchup]
                court_num = None
                
                # Find the position of this match within the team's matches
                for i, team_match in enumerate(team_day_matches, 1):
                    if (match.get('Home Player 1') == team_match.get('Home Player 1') and
                        match.get('Home Player 2') == team_match.get('Home Player 2') and
                        match.get('Away Player 1') == team_match.get('Away Player 1') and
                        match.get('Away Player 2') == team_match.get('Away Player 2')):
                        court_num = min(i, 4)  # Cap at 4 courts
                        break
                
                if court_num is None:
                    continue  # Skip if court can't be determined
                
                for player in [player1, player2]:
                    if not player: 
                        continue
                    if player not in player_stats:
                        player_stats[player] = {'matches': 0, 'wins': 0, 'courts': {}, 'partners': {}}
                    
                    player_stats[player]['matches'] += 1
                    if team_won:
                        player_stats[player]['wins'] += 1
                    
                    # Court - Use correct court assignment
                    court = f'Court {court_num}'
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
        
        # Build top_players list from player_stats
        top_players = []
        for player_id, stats in player_stats.items():
            # Convert player ID to name
            player_name = get_player_name_from_id(player_id)
            
            # Calculate win rate
            win_rate = round((stats['wins']/stats['matches'])*100, 1) if stats['matches'] > 0 else 0
            
            # Best court
            best_court = None
            best_court_rate = 0
            for court, cstats in stats['courts'].items():
                rate = round((cstats['wins']/cstats['matches'])*100, 1) if cstats['matches'] > 0 else 0
                if rate > best_court_rate or (rate == best_court_rate and cstats['matches'] > 0):
                    best_court_rate = rate
                    best_court = f"{court} ({rate}%)"
            
            # Best partner
            best_partner = None
            best_partner_rate = 0
            for partner_id, pstats in stats['partners'].items():
                rate = round((pstats['wins']/pstats['matches'])*100, 1) if pstats['matches'] > 0 else 0
                if rate > best_partner_rate or (rate == best_partner_rate and pstats['matches'] > 0):
                    best_partner_rate = rate
                    best_partner = get_player_name_from_id(partner_id)
            
            top_players.append({
                'name': player_name,
                'matches': stats['matches'],
                'win_rate': win_rate,
                'best_court': best_court or 'N/A',
                'best_partner': f"{best_partner} ({best_partner_rate}%)" if best_partner else 'N/A'
            })
        
        # Sort players by win rate (descending)
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
    """Get player search data for mobile interface using the new database schema"""
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
        
            # Get user's leagues for filtering - handle users with multiple league associations
            user_league_id = user.get('league_id', '')
            print(f"[DEBUG] get_player_search_data: User league_id: '{user_league_id}'")
            
            # If user has no league_id or it's empty, try to get their leagues from associations
            user_league_ids = set()
            if user_league_id and user_league_id not in ['', 'None', None]:
                user_league_ids.add(user_league_id)
            else:
                # Try to get user's leagues from their player associations
                try:
                    user_email = user.get('email')
                    if user_email:
                        # Query user's associated leagues
                        from database_utils import execute_query
                        user_leagues_query = """
                            SELECT DISTINCT l.league_id
                            FROM user_player_associations upa
                            JOIN users u ON upa.user_id = u.id
                            JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id
                            JOIN leagues l ON p.league_id = l.id
                            WHERE u.email = %s
                        """
                        league_results = execute_query(user_leagues_query, [user_email])
                        for result in league_results:
                            user_league_ids.add(result['league_id'])
                        print(f"[DEBUG] Found user leagues from associations: {user_league_ids}")
                except Exception as e:
                    print(f"[DEBUG] Could not get user leagues from associations: {e}")
            
            # If still no leagues found, default to showing all leagues
            if not user_league_ids:
                user_league_ids = {'APTA_CHICAGO', 'NSTF'}  # Show all leagues
                print(f"[DEBUG] No specific leagues found, showing all: {user_league_ids}")
            
            # Load fresh player data using the same method as get_club_players_data
            all_players = _load_players_data()
            
            if not all_players:
                return {
                    'first_name': first_name,
                    'last_name': last_name,
                    'search_attempted': search_attempted,
                    'search_query': search_query,
                    'matching_players': [],
                    'error': 'Error loading player data'
                }

            # Filter players by user's leagues (multiple leagues supported)
            def is_player_in_user_leagues(player):
                player_league = player.get('League')
                return player_league in user_league_ids
            
            league_filtered_players = [player for player in all_players if is_player_in_user_leagues(player)]
            print(f"[DEBUG] Filtered from {len(all_players)} total players to {len(league_filtered_players)} players in user's leagues: {user_league_ids}")
            
            # Search within the league-filtered players
            for player in league_filtered_players:
                player_first = player.get('First Name', '').lower()
                player_last = player.get('Last Name', '').lower()
                
                # Apply search filters
                first_match = not first_name or first_name.lower() in player_first
                last_match = not last_name or last_name.lower() in player_last
                
                if first_match and last_match:
                    # Calculate total matches and win percentage
                    wins = 0
                    losses = 0
                    try:
                        wins = int(player.get('Wins', 0)) if str(player.get('Wins', '')).isdigit() else 0
                        losses = int(player.get('Losses', 0)) if str(player.get('Losses', '')).isdigit() else 0
                    except (ValueError, TypeError):
                        wins = losses = 0
                    
                    total_matches = wins + losses
                    
                    # Format PTI for display
                    pti_value = player.get('PTI', 'N/A')
                    if pti_value and pti_value != 'N/A':
                        try:
                            float(pti_value)
                            current_pti_display = str(pti_value)
                        except (ValueError, TypeError):
                            current_pti_display = 'N/A'
                    else:
                        current_pti_display = 'N/A'
                    
                    # Get club and series info
                    club = player.get('Club', 'Unknown')
                    series = player.get('Series', 'Unknown')
                    
                    matching_players.append({
                        'name': f"{player.get('First Name', '')} {player.get('Last Name', '')}".strip(),
                        'first_name': player.get('First Name', ''),
                        'last_name': player.get('Last Name', ''),
                        'player_id': player.get('Player ID', ''),
                        'current_pti': current_pti_display,
                        'total_matches': total_matches,
                        'club': club,
                        'series': series
                    })

            # Sort by name for consistent results
            matching_players.sort(key=lambda x: x['name'].lower())
            
            print(f"[DEBUG] Found {len(matching_players)} players matching search criteria")

        return {
            'first_name': first_name,
            'last_name': last_name,
            'search_attempted': search_attempted,
            'search_query': search_query,
            'matching_players': matching_players
        }
        
    except Exception as e:
        print(f"Error getting player search data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            'first_name': '',
            'last_name': '',
            'search_attempted': False,
            'search_query': None,
            'matching_players': [],
            'error': str(e)
        }

def get_player_name_from_id(player_id):
    """Get player's first and last name from their TennisScores player ID"""
    if not player_id or not player_id.strip():
        return "Unknown Player"
    
    try:
        player = execute_query_one(
            "SELECT first_name, last_name FROM players WHERE tenniscores_player_id = %s", 
            [player_id]
        )
        if player:
            return f"{player['first_name']} {player['last_name']}"
        else:
            # Fallback: show truncated ID if no name found
            return f"Player ({player_id[:8]}...)"
    except Exception as e:
        print(f"Error looking up player name for ID {player_id}: {e}")
        return "Unknown Player"