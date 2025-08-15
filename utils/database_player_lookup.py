"""
Database-only Player Lookup
Replaces JSON file dependency with proper database queries
"""

import logging
from typing import Any, Dict, List, Optional

from database_utils import execute_query, execute_query_one

logger = logging.getLogger(__name__)

# Common name variations mapping for better first name matching
NAME_VARIATIONS = {
    "rob": ["robert", "bob"],
    "robert": ["rob", "bob", "ross"],
    "bob": ["robert", "rob"],
    "ross": ["robert", "rob"],
    "mike": ["michael"],
    "michael": ["mike"],
    "jim": ["james"],
    "james": ["jim"],
    "bill": ["william", "will"],
    "william": ["bill", "will"],
    "will": ["william", "bill"],
    "dan": ["daniel"],
    "daniel": ["dan"],
    "dave": ["david"],
    "david": ["dave"],
    "steve": ["steven", "stephen"],
    "steven": ["steve", "stephen"],
    "stephen": ["steve", "steven"],
    "chris": ["christopher"],
    "christopher": ["chris"],
    "matt": ["matthew"],
    "matthew": ["matt"],
    "tom": ["thomas"],
    "thomas": ["tom"],
    "tony": ["anthony"],
    "anthony": ["tony"],
    "rick": ["richard"],
    "richard": ["rick"],
    "sam": ["samuel"],
    "samuel": ["sam"],
    "alex": ["alexander"],
    "alexander": ["alex"],
    "ben": ["benjamin"],
    "benjamin": ["ben"],
    "greg": ["gregory"],
    "gregory": ["greg"],
    "joe": ["joseph"],
    "joseph": ["joe"],
    "pat": ["patrick"],
    "patrick": ["pat"],
    "ed": ["edward"],
    "edward": ["ed"],
    "andy": ["andrew"],
    "andrew": ["andy"],
    "p": ["peter"],
    "peter": ["p", "pete"],
    "pete": ["peter"],
    "rj": ["ryan"],
    "ryan": ["rj"],
    "nick": ["nicholas"],
    "nicholas": ["nick"],
    "zach": ["zachary"],
    "zachary": ["zach"],
    "tim": ["timothy"],
    "timothy": ["tim"],
    "frank": ["francis"],
    "francis": ["frank"],
    "ted": ["theodore"],
    "theodore": ["ted"],
    "ken": ["kenneth"],
    "kenneth": ["ken"],
    "olg": ["olga"],  # Fix for Olg Martinsone case
    "olga": ["olg"],  # Bidirectional mapping
}


def normalize_name(name: str) -> str:
    """Normalize player name for consistent matching"""
    if not name:
        return ""
    return name.replace(",", "").replace("  ", " ").strip().lower()


def normalize_series_name(series_name: str, league_id: str = None) -> str:
    """
    Normalize series names using database mappings instead of hard-coded logic.
    
    Args:
        series_name: User-provided series name (e.g., "Series 1", "Division 1a")
        league_id: League identifier for context-specific mapping
        
    Returns:
        Database series name if mapping exists, otherwise original name
    """
    if not series_name:
        return ""
    
    series_name = series_name.strip()
    
    # If we have a league_id, try to get the database mapping
    if league_id:
        try:
            # Try to find database name using series.display_name system
            mapping_query = """
                SELECT s.name as database_name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                JOIN leagues l ON sl.league_id = l.id
                WHERE l.league_id = %s AND (s.display_name = %s OR s.name = %s)
                LIMIT 1
            """
            
            mapping_result = execute_query_one(mapping_query, [league_id, series_name, series_name])
            
            if mapping_result:
                mapped_name = mapping_result["database_name"]
                logger.info(f"Mapped series '{series_name}' -> '{mapped_name}' for league {league_id}")
                return mapped_name
                
        except Exception as e:
            logger.warning(f"Error querying series mapping for '{series_name}' in {league_id}: {e}")
    
    # If no mapping found or no league_id provided, return original
    return series_name


def get_name_variations(first_name: str) -> List[str]:
    """Get all possible variations of a first name"""
    if not first_name:
        return []

    norm_name = normalize_name(first_name)
    variations = [norm_name]

    # Add variations from mapping
    if norm_name in NAME_VARIATIONS:
        variations.extend(NAME_VARIATIONS[norm_name])

    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        if var not in seen:
            seen.add(var)
            unique_variations.append(var)

    return unique_variations


def find_player_by_database_lookup(
    first_name: str, last_name: str, club_name: str, series_name: str, league_id: str
) -> Optional[str]:
    """
    Find a player's tenniscores_player_id using pure database lookups.

    Enhanced strategy with name variations and improved fallbacks:
    1. Primary: name_variations + exact last_name + club + series + league
    2. Fallback 1: name_variations + last_name + series + league (drop club)
    3. Fallback 2: name_variations + last_name + club + league (drop series)
    4. Fallback 3: last_name + series + league (drop first name and club)
    5. Fallback 4: last_name + club + league (drop first name and series)
    6. Final: last_name + league only (most permissive, with warning)

    Args:
        first_name: Player's first name (now supports variations like Rob->Robert)
        last_name: Player's last name
        club_name: Club name
        series_name: Series name
        league_id: League identifier (e.g., 'NSTF', 'APTA_CHICAGO')

    Returns:
        str|None: Player's tenniscores_player_id if found, None otherwise
    """
    try:
        # Normalize inputs
        norm_last = normalize_name(last_name)
        norm_club = normalize_name(club_name)
        norm_series = normalize_series_name(series_name, league_id)

        # Get name variations for first name
        first_name_variations = get_name_variations(first_name)
        
        # Get all possible series name variations for better matching
        series_variations = get_series_name_variations(series_name, league_id)

        logger.info(
            f"Database lookup for: {first_name} {last_name} ({club_name}, {series_name}, {league_id})"
        )
        logger.info(f"First name variations: {first_name_variations}")
        logger.info(f"Series variations: {series_variations}")

        # Get league database ID
        league_record = execute_query_one(
            "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
        )

        if not league_record:
            logger.warning(f"League {league_id} not found in database")
            return None

        league_db_id = league_record["id"]

        # ===========================================
        # PRIMARY SEARCH: Name variations + exact match on other fields
        # ===========================================
        logger.info(f"PRIMARY: Name variation search for {first_name} {last_name}")

        # Build query with OR conditions for first name variations
        name_conditions = " OR ".join(
            ["LOWER(TRIM(p.first_name)) = %s"] * len(first_name_variations)
        )
        
        # Build query with OR conditions for series variations
        series_conditions = " OR ".join(
            ["LOWER(TRIM(s.name)) = %s"] * len(series_variations)
        )

        primary_query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id  
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s 
            AND p.is_active = true
            AND ({name_conditions})
            AND LOWER(TRIM(p.last_name)) = %s  
            AND LOWER(TRIM(c.name)) = %s
            AND ({series_conditions})
        """

        params = (
            [league_db_id] + first_name_variations + [norm_last, norm_club] + [var.lower() for var in series_variations]
        )
        primary_matches = execute_query(primary_query, params)

        if len(primary_matches) == 1:
            player = primary_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(
                f"✅ PRIMARY: Found exact match - {match_info}: {player['tenniscores_player_id']}"
            )
            return {
                "match_type": "exact",
                "player": player,
                "message": f"Exact match found: All details match perfectly",
            }
        elif len(primary_matches) > 1:
            player_ids = [m["tenniscores_player_id"] for m in primary_matches]
            logger.warning(f"⚠️ PRIMARY: Multiple exact matches found: {player_ids}")
            return primary_matches[0]["tenniscores_player_id"]  # Return first match
        else:
            logger.info(f"❌ PRIMARY: No exact matches found")

        # ===========================================
        # FALLBACK 1: name_variations + last_name + series + league (drop club)
        # ===========================================
        logger.info(f"FALLBACK 1: Name variations + last name + series search")

        fallback1_query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id  
            WHERE p.league_id = %s
            AND p.is_active = true
            AND ({name_conditions})
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(s.name)) = %s
        """

        params = [league_db_id] + first_name_variations + [norm_last, norm_series]
        fallback1_matches = execute_query(fallback1_query, params)

        if len(fallback1_matches) == 1:
            player = fallback1_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(
                f"✅ FALLBACK 1: Found unique match - {first_name} {last_name} → {match_info}: {player['tenniscores_player_id']}"
            )
            return {
                "match_type": "probable",
                "player": player,
                "message": f"Probable match: Name variation + exact series match",
            }
        elif len(fallback1_matches) > 1:
            match_names = [
                f"{m['first_name']} {m['last_name']} ({m['club_name']})"
                for m in fallback1_matches
            ]
            logger.info(
                f"⚠️ FALLBACK 1: Multiple matches for {first_name_variations} {last_name} + {series_name}: {match_names}"
            )
        else:
            logger.info(
                f"❌ FALLBACK 1: No matches found for {first_name_variations} {last_name} + {series_name}"
            )

        # ===========================================
        # FALLBACK 2: name_variations + last_name + club + league (drop series)
        # ===========================================
        logger.info(f"FALLBACK 2: Name variations + last name + club search")

        fallback2_query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true  
            AND ({name_conditions})
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(c.name)) = %s
        """

        params = [league_db_id] + first_name_variations + [norm_last, norm_club]
        fallback2_matches = execute_query(fallback2_query, params)

        if len(fallback2_matches) == 1:
            player = fallback2_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(
                f"✅ FALLBACK 2: Found unique match - {first_name} {last_name} → {match_info}: {player['tenniscores_player_id']}"
            )
            return {
                "match_type": "high_confidence",
                "player": player,
                "message": f"High-confidence match: Name variation + exact club match (series: {player['series_name']} vs requested {series_name})",
            }
        elif len(fallback2_matches) > 1:
            match_names = [
                f"{m['first_name']} {m['last_name']} ({m['series_name']})"
                for m in fallback2_matches
            ]
            logger.info(
                f"⚠️ FALLBACK 2: Multiple matches for {first_name_variations} {last_name} + {club_name}: {match_names}"
            )
        else:
            logger.info(
                f"❌ FALLBACK 2: No matches found for {first_name_variations} {last_name} + {club_name}"
            )

        # ===========================================
        # FALLBACK 2.5: last_name + club + series + league (drop first name only)
        # This is often the most reliable fallback - exact club and series with right last name
        # ===========================================
        logger.info(f"FALLBACK 2.5: Last name + club + series search (no first name)")

        fallback2_5_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id  
            WHERE p.league_id = %s
            AND p.is_active = true
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(c.name)) = %s
            AND LOWER(TRIM(s.name)) = %s
        """

        fallback2_5_matches = execute_query(
            fallback2_5_query, (league_db_id, norm_last, norm_club, norm_series)
        )

        if len(fallback2_5_matches) == 1:
            player = fallback2_5_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(
                f"✅ FALLBACK 2.5: Found unique match - {first_name} {last_name} → {match_info}: {player['tenniscores_player_id']}"
            )
            logger.info(
                f"✅ FALLBACK 2.5: Exact club + series + last name match (first name differs: '{first_name}' vs '{player['first_name']}')"
            )
            return {
                "match_type": "high_confidence",
                "player": player,
                "message": f"High-confidence match: Exact club, series, and last name match (first name: {player['first_name']} vs requested {first_name})",
            }
        elif len(fallback2_5_matches) > 1:
            match_names = [
                f"{m['first_name']} {m['last_name']}"
                for m in fallback2_5_matches
            ]
            logger.info(
                f"⚠️ FALLBACK 2.5: Multiple matches for {last_name} + {club_name} + {series_name}: {match_names}"
            )
            
            # CRITICAL FIX: High-confidence fallback found multiple matches
            # This is a very strong signal - same last name + club + series + league
            # Return the matches for user selection instead of continuing to weaker fallbacks
            logger.info(
                f"✅ FALLBACK 2.5: Found multiple high-confidence matches - returning for user selection"
            )
            logger.info(
                f"✅ FALLBACK 2.5: Exact club + series + last name match with multiple first names"
            )
            return {
                "match_type": "multiple_high_confidence",
                "matches": fallback2_5_matches,
                "message": f"Multiple high-confidence matches found: {match_names}. Exact club, series, and last name match with different first names.",
            }
        else:
            logger.info(
                f"❌ FALLBACK 2.5: No matches found for {last_name} + {club_name} + {series_name}"
            )

        # ===========================================
        # FALLBACK 3: last_name + series + league (drop first name and club)
        # ===========================================
        logger.info(f"FALLBACK 3: Last name + series search (no first name)")

        fallback3_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id  
            WHERE p.league_id = %s
            AND p.is_active = true
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(s.name)) = %s
        """

        fallback3_matches = execute_query(
            fallback3_query, (league_db_id, norm_last, norm_series)
        )

        if len(fallback3_matches) == 1:
            player = fallback3_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(
                f"✅ FALLBACK 3: Found unique match - {first_name} {last_name} → {match_info}: {player['tenniscores_player_id']}"
            )
            return {
                "match_type": "possible",
                "player": player,
                "message": f"Possible match: Last name + series match (different first name/club)",
            }
        elif len(fallback3_matches) > 1:
            match_names = [
                f"{m['first_name']} {m['last_name']} ({m['club_name']})"
                for m in fallback3_matches
            ]
            logger.info(
                f"⚠️ FALLBACK 3: Multiple matches for {last_name} + {series_name}: {match_names}"
            )
        else:
            logger.info(
                f"❌ FALLBACK 3: No matches found for {last_name} + {series_name}"
            )

        # ===========================================
        # FALLBACK 4: last_name + club + league (drop first name and series)
        # ===========================================
        logger.info(f"FALLBACK 4: Last name + club search (no first name)")

        fallback4_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true  
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(c.name)) = %s
        """

        fallback4_matches = execute_query(
            fallback4_query, (league_db_id, norm_last, norm_club)
        )

        if len(fallback4_matches) == 1:
            player = fallback4_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(
                f"✅ FALLBACK 4: Found unique match - {first_name} {last_name} → {match_info}: {player['tenniscores_player_id']}"
            )
            logger.info(
                f"✅ FALLBACK 4: Auto-associating based on last name + club + league match (first name/series may differ)"
            )
            return {
                "match_type": "high_confidence",
                "player": player,
                "message": f"High-confidence match: Last name + club + league match (first name: {player['first_name']} vs requested {first_name}, series: {player['series_name']} vs requested {series_name})",
            }
        elif len(fallback4_matches) > 1:
            match_names = [
                f"{m['first_name']} {m['last_name']} ({m['series_name']})"
                for m in fallback4_matches
            ]
            logger.info(
                f"⚠️ FALLBACK 4: Multiple matches for {last_name} + {club_name}: {match_names}"
            )
            
            # CONSISTENT FIX: High-confidence fallback found multiple matches  
            # Same last name + club + league is also high confidence
            # Return the matches for user selection instead of continuing to riskier fallbacks
            logger.info(
                f"✅ FALLBACK 4: Found multiple high-confidence matches - returning for user selection"
            )
            logger.info(
                f"✅ FALLBACK 4: Exact club + last name match with multiple first names/series"
            )
            return {
                "match_type": "multiple_high_confidence",
                "matches": fallback4_matches,
                "message": f"Multiple high-confidence matches found: {match_names}. Exact club and last name match with different first names/series.",
            }
        else:
            logger.info(
                f"❌ FALLBACK 4: No matches found for {last_name} + {club_name}"
            )

        # ===========================================
        # FALLBACK 5: name_variations + series + league (drop last_name and club)
        # This catches cases where user has correct first name + series but wrong last name/club
        # ===========================================
        logger.info(f"FALLBACK 5: Name variations + series search (no last name or club)")

        fallback5_query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id  
            WHERE p.league_id = %s
            AND p.is_active = true
            AND ({name_conditions})
            AND LOWER(TRIM(s.name)) = %s
        """

        params = [league_db_id] + first_name_variations + [norm_series]
        fallback5_matches = execute_query(fallback5_query, params)

        if len(fallback5_matches) == 1:
            player = fallback5_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(
                f"✅ FALLBACK 5: Found unique match - {first_name} {last_name} → {match_info}: {player['tenniscores_player_id']}"
            )
            logger.info(
                f"✅ FALLBACK 5: Name variation + series match (last name: '{player['last_name']}' vs '{last_name}', club: '{player['club_name']}' vs '{club_name}')"
            )
            return {
                "match_type": "possible",
                "player": player,
                "message": f"Possible match: Name variation + series match (last name: {player['last_name']} vs requested {last_name}, club: {player['club_name']} vs requested {club_name})",
            }
        elif len(fallback5_matches) > 1:
            match_names = [
                f"{m['first_name']} {m['last_name']} ({m['club_name']})"
                for m in fallback5_matches
            ]
            logger.info(
                f"⚠️ FALLBACK 5: Multiple matches for {first_name_variations} + {series_name}: {match_names}"
            )
            logger.info(
                f"✅ FALLBACK 5: Found multiple possible matches - returning for user selection"
            )
            return {
                "match_type": "multiple_possible",
                "matches": fallback5_matches,
                "message": f"Multiple possible matches found: {match_names}. Same first name variation and series with different last names/clubs.",
            }
        else:
            logger.info(
                f"❌ FALLBACK 5: No matches found for {first_name_variations} + {series_name}"
            )

        # ===========================================
        # FINAL FALLBACK: last_name + league only (VERY PERMISSIVE - USE WITH CAUTION)
        # ===========================================
        logger.warning(
            f"FINAL FALLBACK: Last name only search for {last_name} (RISKY - may match wrong player)"
        )

        final_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true
            AND LOWER(TRIM(p.last_name)) = %s
        """

        final_matches = execute_query(final_query, (league_db_id, norm_last))

        if len(final_matches) == 1:
            player = final_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.warning(
                f"⚠️ FINAL FALLBACK: Found unique match - {first_name} {last_name} → {match_info}: {player['tenniscores_player_id']}"
            )
            logger.warning(
                f"⚠️ WARNING: Registration data differs significantly from player record!"
            )
            logger.warning(
                f"⚠️ User registered: {first_name} {last_name} at {club_name} in {series_name}"
            )
            logger.warning(
                f"⚠️ Player found: {player['first_name']} {player['last_name']} at {player['club_name']} in {player['series_name']}"
            )
            return {
                "match_type": "risky",
                "player": player,
                "message": f"RISKY match: Only last name matches - registration data differs significantly",
            }
        elif len(final_matches) > 1:
            match_names = [
                f"{m['first_name']} {m['last_name']} ({m['club_name']}, {m['series_name']})"
                for m in final_matches
            ]
            logger.warning(
                f"⚠️ FINAL FALLBACK: Multiple matches for {last_name}: {match_names}"
            )
            logger.warning(
                f"⚠️ Cannot determine correct player - skipping association to avoid errors"
            )
        else:
            logger.info(f"❌ FINAL FALLBACK: No matches found for {last_name}")

        logger.info(f"❌ All fallback strategies failed for {first_name} {last_name}")
        return {
            "match_type": "no_match",
            "player": None,
            "message": f"No matches found for {first_name} {last_name}",
        }

    except Exception as e:
        logger.error(f"Database player lookup error: {str(e)}")
        return {
            "match_type": "error",
            "player": None,
            "message": f"Database error during lookup: {str(e)}",
        }


def search_players_by_name(
    first_name: str = None,
    last_name: str = None,
    league_id: str = None,
    club_name: str = None,
    series_name: str = None,
    limit: int = 20,
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
            league_record = execute_query_one(
                "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
            )
            if league_record:
                conditions.append("p.league_id = %s")
                params.append(league_record["id"])

        if club_name:
            conditions.append("LOWER(TRIM(c.name)) LIKE %s")
            params.append(f"%{normalize_name(club_name)}%")

        if series_name:
            conditions.append("LOWER(TRIM(s.name)) LIKE %s")
            params.append(f"%{normalize_series_name(series_name, league_id)}%")

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

        return [
            {
                "tenniscores_player_id": r["tenniscores_player_id"],
                "name": f"{r['first_name']} {r['last_name']}",
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "club": r["club_name"],
                "series": r["series_name"],
                "league": r["league_name"],
                "pti": r["pti"],
                "wins": r["wins"],
                "losses": r["losses"],
                "win_percentage": r["win_percentage"],
            }
            for r in results
        ]

    except Exception as e:
        logger.error(f"Player search error: {str(e)}")
        return []


def find_player_by_database_lookup_id(
    first_name: str, last_name: str, club_name: str, series_id: int, league_id: str
) -> Optional[Dict[str, Any]]:
    """
    BULLETPROOF: Find player using series_id instead of name matching.
    No transformations, no fallbacks needed - just exact matching.
    
    Args:
        first_name: Player's first name (supports variations like Rob->Robert)
        last_name: Player's last name
        club_name: Club name
        series_id: Series database ID (stable, unique identifier)
        league_id: League identifier (e.g., 'NSTF', 'APTA_CHICAGO')
    
    Returns:
        Dict with match result or None if no match found
    """
    try:
        # Normalize inputs
        norm_last = normalize_name(last_name)
        norm_club = normalize_name(club_name)
        
        # Get name variations for first name (keep this flexibility)
        first_name_variations = get_name_variations(first_name)
        
        logger.info(
            f"ID-based lookup for: {first_name} {last_name} ({club_name}, series_id={series_id}, {league_id})"
        )
        logger.info(f"First name variations: {first_name_variations}")
        
        # Get league database ID
        league_record = execute_query_one(
            "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
        )
        
        if not league_record:
            logger.warning(f"League {league_id} not found in database")
            return {
                "match_type": "error",
                "player": None,
                "message": f"League {league_id} not found in database",
            }
        
        league_db_id = league_record["id"]
        
        # Build name conditions for flexible first name matching
        name_conditions = " OR ".join(
            ["LOWER(TRIM(p.first_name)) = %s"] * len(first_name_variations)
        )
        
        # BULLETPROOF PRIMARY QUERY: Use series_id for exact matching
        primary_query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, 
                   c.name as club_name, s.name as series_name, s.id as series_id
            FROM players p
            JOIN clubs c ON p.club_id = c.id  
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s 
            AND p.is_active = true
            AND ({name_conditions})
            AND LOWER(TRIM(p.last_name)) = %s  
            AND LOWER(TRIM(c.name)) = %s
            AND p.series_id = %s
        """
        
        params = (
            [league_db_id] + first_name_variations + 
            [norm_last, norm_club, series_id]
        )
        
        primary_matches = execute_query(primary_query, params)
        
        if len(primary_matches) == 1:
            player = primary_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(f"✅ ID-BASED PRIMARY: Perfect match - {match_info}: {player['tenniscores_player_id']}")
            return {
                "match_type": "exact",
                "player": player,
                "message": f"Perfect match using series ID {series_id}",
            }
        elif len(primary_matches) > 1:
            player_ids = [m["tenniscores_player_id"] for m in primary_matches]
            logger.warning(f"⚠️ ID-BASED PRIMARY: Multiple exact matches found: {player_ids}")
            return {
                "match_type": "multiple",
                "players": primary_matches,
                "message": f"Multiple players found with same details (series_id={series_id})",
            }
        else:
            logger.info(f"❌ ID-BASED PRIMARY: No exact matches found for series_id={series_id}")
        
        # FALLBACK 1: Drop club requirement but keep series_id (series is more specific than club)
        logger.info(f"ID-BASED FALLBACK 1: Drop club, keep series_id={series_id}")
        
        fallback1_query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, 
                   c.name as club_name, s.name as series_name, s.id as series_id
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true
            AND ({name_conditions})
            AND LOWER(TRIM(p.last_name)) = %s
            AND p.series_id = %s
        """
        
        fallback1_params = [league_db_id] + first_name_variations + [norm_last, series_id]
        fallback1_matches = execute_query(fallback1_query, fallback1_params)
        
        if len(fallback1_matches) == 1:
            player = fallback1_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(f"✅ ID-BASED FALLBACK 1: Found match (different club) - {match_info}: {player['tenniscores_player_id']}")
            return {
                "match_type": "high_confidence",
                "player": player,
                "message": f"High-confidence match: Name + series match (series_id={series_id}, club: {player['club_name']} vs requested {club_name})",
            }
        elif len(fallback1_matches) > 1:
            logger.warning(f"⚠️ ID-BASED FALLBACK 1: Multiple matches found")
            return {
                "match_type": "multiple_high_confidence",
                "players": fallback1_matches,
                "message": f"Multiple high-confidence matches found (series_id={series_id})",
            }
        else:
            logger.info(f"❌ ID-BASED FALLBACK 1: No matches for series_id={series_id}")
        
        # FALLBACK 2: Drop series requirement, keep club (for cases where user selected wrong series)
        logger.info(f"ID-BASED FALLBACK 2: Drop series_id, keep club")
        
        fallback2_query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, 
                   c.name as club_name, s.name as series_name, s.id as series_id
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true
            AND ({name_conditions})
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(c.name)) = %s
        """
        
        fallback2_params = [league_db_id] + first_name_variations + [norm_last, norm_club]
        fallback2_matches = execute_query(fallback2_query, fallback2_params)
        
        if len(fallback2_matches) == 1:
            player = fallback2_matches[0]
            match_info = f"{player['first_name']} {player['last_name']} ({player['club_name']}, {player['series_name']})"
            logger.info(f"✅ ID-BASED FALLBACK 2: Found match (different series) - {match_info}: {player['tenniscores_player_id']}")
            return {
                "match_type": "medium_confidence",
                "player": player,
                "message": f"Medium-confidence match: Name + club match (series: {player['series_name']} vs requested series_id={series_id})",
            }
        elif len(fallback2_matches) > 1:
            logger.warning(f"⚠️ ID-BASED FALLBACK 2: Multiple matches found")
            return {
                "match_type": "multiple_medium_confidence", 
                "players": fallback2_matches,
                "message": f"Multiple medium-confidence matches found (club: {club_name})",
            }
        else:
            logger.info(f"❌ ID-BASED FALLBACK 2: No matches for club {club_name}")
        
        # No matches found
        logger.warning(f"❌ ID-BASED: No matches found for {first_name} {last_name} (series_id={series_id}, club={club_name})")
        return {
            "match_type": "no_match",
            "player": None,
            "message": f"No player found matching the provided details (series_id={series_id})",
        }
        
    except Exception as e:
        logger.error(f"ID-based player lookup error: {str(e)}")
        return {
            "match_type": "error",
            "player": None,
            "message": f"Database error during lookup: {str(e)}",
        }


def find_potential_player_matches(
    first_name: str,
    last_name: str,
    club_name: str,
    series_name: str,
    league_id: str,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Find potential player matches and categorize them by confidence level.
    Used for registration when we want user confirmation for questionable matches.

    Returns:
        Dict with:
        - exact_matches: Perfect matches (all fields)
        - probable_matches: High confidence (name variations + 2 other fields)
        - possible_matches: Lower confidence (name variations + 1 field)
        - risky_matches: Last name only matches
        - no_matches: True if no matches found at all
    """
    try:
        # Normalize inputs
        norm_last = normalize_name(last_name)
        norm_club = normalize_name(club_name)
        norm_series = normalize_series_name(series_name, league_id)

        # Get name variations for first name
        first_name_variations = get_name_variations(first_name)

        logger.info(
            f"Finding potential matches for: {first_name} {last_name} ({club_name}, {series_name}, {league_id})"
        )

        # Get league database ID
        league_record = execute_query_one(
            "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
        )

        if not league_record:
            logger.warning(f"League {league_id} not found in database")
            return {"no_matches": True}

        league_db_id = league_record["id"]

        result = {
            "exact_matches": [],
            "probable_matches": [],
            "possible_matches": [],
            "risky_matches": [],
            "no_matches": False,
        }

        # Helper function to format player data
        def format_player(player_row):
            return {
                "tenniscores_player_id": player_row["tenniscores_player_id"],
                "first_name": player_row["first_name"],
                "last_name": player_row["last_name"],
                "club_name": player_row["club_name"],
                "series_name": player_row["series_name"],
                "full_name": f"{player_row['first_name']} {player_row['last_name']}",
                "display_text": f"{player_row['first_name']} {player_row['last_name']} ({player_row['club_name']}, {player_row['series_name']})",
            }

        # ===========================================
        # EXACT MATCHES: Name variations + exact club + series + league
        # ===========================================
        name_conditions = " OR ".join(
            ["LOWER(TRIM(p.first_name)) = %s"] * len(first_name_variations)
        )

        exact_query = f"""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id  
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s 
            AND p.is_active = true
            AND ({name_conditions})
            AND LOWER(TRIM(p.last_name)) = %s  
            AND LOWER(TRIM(c.name)) = %s
            AND LOWER(TRIM(s.name)) = %s
            LIMIT %s
        """

        params = (
            [league_db_id]
            + first_name_variations
            + [norm_last, norm_club, norm_series, max_results]
        )
        exact_matches = execute_query(exact_query, params)
        result["exact_matches"] = [format_player(p) for p in exact_matches]

        # ===========================================
        # HIGH-CONFIDENCE MATCHES: Name variations + exact club + league (wrong series)
        # These should be treated as exact matches for auto-association purposes
        # since it's very common for users to get series wrong but club right
        # ===========================================
        if not result["exact_matches"]:
            high_confidence_query = f"""
                SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
                FROM players p
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                WHERE p.league_id = %s
                AND p.is_active = true  
                AND ({name_conditions})
                AND LOWER(TRIM(p.last_name)) = %s
                AND LOWER(TRIM(c.name)) = %s
                LIMIT %s
            """

            params = (
                [league_db_id]
                + first_name_variations
                + [norm_last, norm_club, max_results]
            )
            high_confidence_matches = execute_query(high_confidence_query, params)

            if len(high_confidence_matches) == 1:
                # Single match with name variation + exact club = treat as exact match
                logger.info(
                    f"High-confidence match: Name variation + exact club match (series differs)"
                )
                result["exact_matches"] = [format_player(high_confidence_matches[0])]
            elif len(high_confidence_matches) > 1:
                # Multiple matches at same club - let user choose
                result["probable_matches"] = [
                    format_player(p) for p in high_confidence_matches
                ]

        # ===========================================
        # PROBABLE MATCHES: Name variations + last_name + (series OR club)
        # Only if we haven't already found exact/high-confidence matches
        # ===========================================
        if not result["exact_matches"]:

            # Series match (drop club)
            probable_series_query = f"""
                SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
                FROM players p
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id  
                WHERE p.league_id = %s
                AND p.is_active = true
                AND ({name_conditions})
                AND LOWER(TRIM(p.last_name)) = %s
                AND LOWER(TRIM(s.name)) = %s
                LIMIT %s
            """

            params = (
                [league_db_id]
                + first_name_variations
                + [norm_last, norm_series, max_results]
            )
            probable_series = execute_query(probable_series_query, params)

            # Club match (drop series) - but only for clubs we haven't already processed as high-confidence
            probable_club_query = f"""
                SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
                FROM players p
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                WHERE p.league_id = %s
                AND p.is_active = true  
                AND ({name_conditions})
                AND LOWER(TRIM(p.last_name)) = %s
                AND LOWER(TRIM(c.name)) = %s
                LIMIT %s
            """

            params_club = (
                [league_db_id]
                + first_name_variations
                + [norm_last, norm_club, max_results]
            )
            probable_club = execute_query(probable_club_query, params_club)

            # Only add to probable_matches if not already handled by high-confidence logic above
            if not result["probable_matches"]:
                # Combine and deduplicate probable matches (excluding high-confidence ones)
                probable_combined = list(probable_series) + list(probable_club)
                seen_ids = set()
                for p in probable_combined:
                    if p["tenniscores_player_id"] not in seen_ids:
                        seen_ids.add(p["tenniscores_player_id"])
                        result["probable_matches"].append(format_player(p))

        # ===========================================
        # POSSIBLE MATCHES: Last name + (series OR club), no first name constraint
        # ===========================================

        # Last name + series (no first name)
        possible_series_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id  
            WHERE p.league_id = %s
            AND p.is_active = true
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(s.name)) = %s
            LIMIT %s
        """

        possible_series = execute_query(
            possible_series_query, (league_db_id, norm_last, norm_series, max_results)
        )

        # Last name + club (no first name)
        possible_club_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true  
            AND LOWER(TRIM(p.last_name)) = %s
            AND LOWER(TRIM(c.name)) = %s
            LIMIT %s
        """

        possible_club = execute_query(
            possible_club_query, (league_db_id, norm_last, norm_club, max_results)
        )

        # Combine and deduplicate possible matches
        possible_combined = list(possible_series) + list(possible_club)
        seen_ids = set()
        for p in possible_combined:
            if p["tenniscores_player_id"] not in seen_ids:
                seen_ids.add(p["tenniscores_player_id"])
                result["possible_matches"].append(format_player(p))

        # ===========================================
        # RISKY MATCHES: Last name only
        # ===========================================
        risky_query = """
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
            AND p.is_active = true
            AND LOWER(TRIM(p.last_name)) = %s
            LIMIT %s
        """

        risky_matches = execute_query(
            risky_query, (league_db_id, norm_last, max_results)
        )
        result["risky_matches"] = [format_player(p) for p in risky_matches]

        # Check if we found any matches at all
        total_matches = (
            len(result["exact_matches"])
            + len(result["probable_matches"])
            + len(result["possible_matches"])
            + len(result["risky_matches"])
        )

        if total_matches == 0:
            result["no_matches"] = True

        logger.info(
            f"Potential matches found: exact={len(result['exact_matches'])}, probable={len(result['probable_matches'])}, possible={len(result['possible_matches'])}, risky={len(result['risky_matches'])}"
        )

        return result

    except Exception as e:
        logger.error(f"Error finding potential player matches: {str(e)}")
        return {"no_matches": True}


def suggest_registration_corrections(
    first_name: str, last_name: str, club_name: str, series_name: str, league_id: str
) -> Dict[str, Any]:
    """
    Suggest corrections to registration data based on what's actually in the database.
    Useful for helping users understand why exact matches weren't found.

    Returns suggestions for club and series based on available players with similar names.
    """
    try:
        potential_matches = find_potential_player_matches(
            first_name, last_name, club_name, series_name, league_id, max_results=5
        )

        suggestions = {
            "has_suggestions": False,
            "name_matches": [],
            "club_suggestions": set(),
            "series_suggestions": set(),
            "message": "",
        }

        # Collect all non-exact matches for analysis
        all_matches = []
        all_matches.extend(potential_matches.get("probable_matches", []))
        all_matches.extend(potential_matches.get("possible_matches", []))
        all_matches.extend(potential_matches.get("risky_matches", []))

        if not all_matches:
            suggestions["message"] = (
                f"No players found with last name '{last_name}' in {league_id}"
            )
            return suggestions

        # Look for players with exact or similar first names
        first_name_variations = get_name_variations(first_name)
        name_matches = []

        for match in all_matches:
            match_first_norm = normalize_name(match["first_name"])
            if match_first_norm in first_name_variations:
                name_matches.append(match)
                suggestions["club_suggestions"].add(match["club_name"])
                suggestions["series_suggestions"].add(match["series_name"])

        if name_matches:
            suggestions["has_suggestions"] = True
            suggestions["name_matches"] = name_matches

            # Create helpful message
            if len(name_matches) == 1:
                match = name_matches[0]
                suggestions["message"] = (
                    f"Found '{match['first_name']} {match['last_name']}' at "
                    f"'{match['club_name']}' in '{match['series_name']}'. "
                    f"You registered for '{club_name}' in '{series_name}'. "
                    f"Please verify your club and series information."
                )
            else:
                suggestions["message"] = (
                    f"Found {len(name_matches)} players with similar names. "
                    f"Please check if your club and series information is correct."
                )
        else:
            # No name matches - might be wrong first name too
            suggestions["message"] = (
                f"Found players with last name '{last_name}' but different first names. "
                f"Please verify your first name, club, and series information."
            )

        return suggestions

    except Exception as e:
        logger.error(f"Error generating registration suggestions: {str(e)}")
        return {"has_suggestions": False, "message": "Unable to generate suggestions"}


def get_series_name_variations(series_name: str, league_id: str = None) -> List[str]:
    """
    Get all possible variations of a series name using database mappings.
    
    Args:
        series_name: User-provided series name
        league_id: League identifier for context-specific mapping
        
    Returns:
        List of all possible variations to check against database
    """
    if not series_name:
        return []
    
    variations = [series_name.strip()]  # Always include original
    
    # If we have a league_id, get all mapped variations from database using series.display_name
    if league_id:
        try:
            # Get all series for this league that might match
            mappings_query = """
                SELECT s.name as database_name, s.display_name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                JOIN leagues l ON sl.league_id = l.id
                WHERE l.league_id = %s 
                AND (s.display_name = %s OR s.name = %s)
            """
            
            mappings = execute_query(mappings_query, [league_id, series_name, series_name])
            
            for mapping in mappings:
                db_name = mapping["database_name"]
                display_name = mapping["display_name"]
                
                # Add both directions of the mapping
                if db_name not in variations:
                    variations.append(db_name)
                if display_name and display_name not in variations:
                    variations.append(display_name)
                    
            logger.info(f"Found {len(variations)} series variations for '{series_name}' in {league_id}: {variations}")
            
        except Exception as e:
            logger.warning(f"Error getting series variations for '{series_name}' in {league_id}: {e}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for variation in variations:
        if variation and variation not in seen:
            seen.add(variation)
            unique_variations.append(variation)
    
    return unique_variations
