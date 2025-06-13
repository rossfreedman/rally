"""
Database-only Player Lookup
Replaces JSON file dependency with proper database queries
"""
import logging
from typing import Optional, List, Dict, Any
from database_utils import execute_query, execute_query_one

logger = logging.getLogger(__name__)

def normalize_name(name: str) -> str:
    """Normalize name for comparison (lowercase, stripped)"""
    if not name:
        return ""
    return name.strip().lower()

def find_player_by_database_lookup(
    first_name: str,
    last_name: str, 
    club_name: str,
    series_name: str,
    league_id: str
) -> Optional[str]:
    """
    Find a player's tenniscores_player_id using pure database lookups.
    
    Progressive fallback strategy:
    1. Primary: fuzzy first_name + exact last_name + club + series + league
    2. Fallback 1: last_name + series + league (drop club and first name)  
    3. Fallback 2: last_name + club + league (drop series and first name)
    4. Fallback 3: last_name + league (drop club, series, and first name)
    
    Args:
        first_name: Player's first name (uses fuzzy matching in primary search)
        last_name: Player's last name
        club_name: Club name
        series_name: Series name  
        league_id: League identifier (e.g., 'NSTF', 'APTA_CHICAGO')
        
    Returns:
        str|None: Player's tenniscores_player_id if found, None otherwise
    """
    try:
        # Normalize inputs
        norm_first = normalize_name(first_name)
        norm_last = normalize_name(last_name)
        norm_club = normalize_name(club_name)
        norm_series = normalize_name(series_name)
        
        logger.info(f"Database lookup for: {first_name} {last_name} ({club_name}, {series_name}, {league_id})")
        
        # Get league database ID
        league_record = execute_query_one(
            "SELECT id FROM leagues WHERE league_id = %s",
            (league_id,)
        )
        
        if not league_record:
            logger.warning(f"League {league_id} not found in database")
            return None
            
        league_db_id = league_record['id']
        
        # ===========================================
        # PRIMARY SEARCH: Fuzzy first name + exact match on other fields
        # ===========================================
        logger.info(f"PRIMARY: Fuzzy first name search for {first_name} {last_name}")
        
        primary_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id  
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s 
            AND p.is_active = true
            AND LOWER(TRIM(p.first_name)) LIKE %s
            AND LOWER(TRIM(p.last_name)) = %s  
            AND LOWER(TRIM(c.name)) = %s
            AND LOWER(TRIM(s.name)) = %s
        """
        
        primary_matches = execute_query(primary_query, (league_db_id, f"%{norm_first}%", norm_last, norm_club, norm_series))
        
        if len(primary_matches) == 1:
            player_id = primary_matches[0]['tenniscores_player_id']
            match_info = f"{primary_matches[0]['first_name']} {primary_matches[0]['last_name']} ({primary_matches[0]['club_name']}, {primary_matches[0]['series_name']})"
            logger.info(f"✅ PRIMARY: Found exact match - {match_info}: {player_id}")
            return player_id
        elif len(primary_matches) > 1:
            player_ids = [m['tenniscores_player_id'] for m in primary_matches]
            logger.warning(f"⚠️ PRIMARY: Multiple exact matches found: {player_ids}")
            return primary_matches[0]['tenniscores_player_id']  # Return first match
        else:
            logger.info(f"❌ PRIMARY: No exact matches found")
        
        # ===========================================  
        # FALLBACK 1: last_name + series + league (drop club and first name)
        # ===========================================
        logger.info(f"FALLBACK 1: Last name + series search for {last_name}")
        
        fallback1_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id  
            WHERE p.league_id = %s
            AND p.is_active = true
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(s.name)) = %s
        """
        
        fallback1_matches = execute_query(fallback1_query, (league_db_id, norm_last, norm_series))
        
        if len(fallback1_matches) == 1:
            player_id = fallback1_matches[0]['tenniscores_player_id']
            match_info = f"{fallback1_matches[0]['first_name']} {fallback1_matches[0]['last_name']} ({fallback1_matches[0]['club_name']}, {fallback1_matches[0]['series_name']})"
            logger.info(f"✅ FALLBACK 1: Found unique match - {first_name} {last_name} → {match_info}: {player_id}")
            return player_id
        elif len(fallback1_matches) > 1:
            match_names = [f"{m['first_name']} {m['last_name']} ({m['club_name']})" for m in fallback1_matches]
            logger.info(f"⚠️ FALLBACK 1: Multiple matches for {last_name} + {series_name}: {match_names}")
        else:
            logger.info(f"❌ FALLBACK 1: No matches found for {last_name} + {series_name}")
        
        # ===========================================
        # FALLBACK 2: last_name + club + league (drop series and first name)  
        # ===========================================
        logger.info(f"FALLBACK 2: Last name + club search for {last_name}")
        
        fallback2_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true  
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(c.name)) = %s
        """
        
        fallback2_matches = execute_query(fallback2_query, (league_db_id, norm_last, norm_club))
        
        if len(fallback2_matches) == 1:
            player_id = fallback2_matches[0]['tenniscores_player_id']
            match_info = f"{fallback2_matches[0]['first_name']} {fallback2_matches[0]['last_name']} ({fallback2_matches[0]['club_name']}, {fallback2_matches[0]['series_name']})"
            logger.info(f"✅ FALLBACK 2: Found unique match - {first_name} {last_name} → {match_info}: {player_id}")
            return player_id
        elif len(fallback2_matches) > 1:
            match_names = [f"{m['first_name']} {m['last_name']} ({m['series_name']})" for m in fallback2_matches]
            logger.info(f"⚠️ FALLBACK 2: Multiple matches for {last_name} + {club_name}: {match_names}")
        else:
            logger.info(f"❌ FALLBACK 2: No matches found for {last_name} + {club_name}")
        
        # ===========================================
        # FALLBACK 3: last_name + league only (drop everything else)
        # ===========================================
        logger.info(f"FALLBACK 3: Last name only search for {last_name}")
        
        fallback3_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true
            AND LOWER(TRIM(p.last_name)) = %s
        """
        
        fallback3_matches = execute_query(fallback3_query, (league_db_id, norm_last))
        
        if len(fallback3_matches) == 1:
            player_id = fallback3_matches[0]['tenniscores_player_id']
            match_info = f"{fallback3_matches[0]['first_name']} {fallback3_matches[0]['last_name']} ({fallback3_matches[0]['club_name']}, {fallback3_matches[0]['series_name']})"
            logger.info(f"✅ FALLBACK 3: Found unique match - {first_name} {last_name} → {match_info}: {player_id}")
            return player_id
        elif len(fallback3_matches) > 1:
            match_names = [f"{m['first_name']} {m['last_name']} ({m['club_name']}, {m['series_name']})" for m in fallback3_matches]
            logger.info(f"⚠️ FALLBACK 3: Multiple matches for {last_name}: {match_names}")
        else:
            logger.info(f"❌ FALLBACK 3: No matches found for {last_name}")
        
        logger.info(f"❌ All fallback strategies failed for {first_name} {last_name}")
        return None
        
    except Exception as e:
        logger.error(f"Database player lookup error: {str(e)}")
        return None

def search_players_by_name(
    first_name: str = None,
    last_name: str = None, 
    league_id: str = None,
    club_name: str = None,
    series_name: str = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search for players by name and optional filters.
    Used for user selection when multiple matches are found.
    
    Returns:
        List of player dictionaries with basic info
    """
    try:
        conditions = ["p.is_active = true"]
        params = []
        
        if first_name:
            conditions.append("LOWER(TRIM(p.first_name)) LIKE %s")
            params.append(f"%{normalize_name(first_name)}%")
            
        if last_name:
            conditions.append("LOWER(TRIM(p.last_name)) LIKE %s") 
            params.append(f"%{normalize_name(last_name)}%")
            
        if league_id:
            league_record = execute_query_one("SELECT id FROM leagues WHERE league_id = %s", (league_id,))
            if league_record:
                conditions.append("p.league_id = %s")
                params.append(league_record['id'])
                
        if club_name:
            conditions.append("LOWER(TRIM(c.name)) LIKE %s")
            params.append(f"%{normalize_name(club_name)}%")
            
        if series_name:
            conditions.append("LOWER(TRIM(s.name)) LIKE %s")
            params.append(f"%{normalize_name(series_name)}%")
        
        query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, 
                   c.name as club_name, s.name as series_name, l.league_name,
                   p.pti, p.wins, p.losses, p.win_percentage
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id  
            JOIN leagues l ON p.league_id = l.id
            WHERE {' AND '.join(conditions)}
            ORDER BY p.last_name, p.first_name
            LIMIT %s
        """
        
        params.append(limit)
        results = execute_query(query, params)
        
        return [{
            'tenniscores_player_id': r['tenniscores_player_id'],
            'name': f"{r['first_name']} {r['last_name']}",
            'first_name': r['first_name'],
            'last_name': r['last_name'],
            'club': r['club_name'],
            'series': r['series_name'],
            'league': r['league_name'],
            'pti': r['pti'],
            'wins': r['wins'],
            'losses': r['losses'],
            'win_percentage': r['win_percentage']
        } for r in results]
        
    except Exception as e:
        logger.error(f"Player search error: {str(e)}")
        return [] 