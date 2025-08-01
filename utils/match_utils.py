import difflib
import json
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Load nickname mappings from JSON file and build bidirectional lookup
def load_nickname_mappings():
    """Load nickname mappings from JSON file and build bidirectional lookup."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # Go up one level from utils/
    nickname_file = os.path.join(
        project_root, "data", "leagues", "apta", "nickname_mappings.json"
    )

    try:
        with open(nickname_file, "r") as f:
            NAME_GROUPS = json.load(f)

        # Build a reverse lookup for faster resolution
        NAME_TO_GROUP = {}
        for canonical, names in NAME_GROUPS.items():
            for name in names:
                NAME_TO_GROUP[name.lower()] = set(names)

        logger.info(f"Loaded {len(NAME_GROUPS)} nickname groups from {nickname_file}")
        return NAME_TO_GROUP
    except FileNotFoundError:
        logger.warning(
            f"Nickname mappings file not found: {nickname_file}, using empty mappings"
        )
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing nickname mappings JSON: {e}")
        return {}


# Load the nickname mappings once when module is imported
NAME_TO_GROUP = load_nickname_mappings()


def normalize_name(name: str) -> str:
    """
    Normalize a name for matching purposes.

    Args:
        name: The name to normalize

    Returns:
        str: Normalized name (lowercase, trimmed)
    """
    if not name:
        return ""
    return name.strip().lower()


def get_name_variations(name: str) -> List[str]:
    """
    Returns all name variations (nicknames, full names) for the given name.

    Args:
        name: The name to get variations for

    Returns:
        list: List of possible name variations
    """
    return list(NAME_TO_GROUP.get(name.strip().lower(), {name.strip().lower()}))


def names_match(name1: str, name2: str) -> bool:
    """
    Check if two names match, considering nickname variations and fuzzy matching.

    Args:
        name1: First name to compare
        name2: Second name to compare

    Returns:
        bool: True if names match (including nickname variations and fuzzy matches)
    """
    # Normalize names for comparison
    norm_name1 = normalize_name(name1)
    norm_name2 = normalize_name(name2)

    # Direct exact match
    if norm_name1 == norm_name2:
        return True

    # Check if names share any nickname group (bidirectional lookup)
    if bool(set(get_name_variations(name1)) & set(get_name_variations(name2))):
        return True

    # Fuzzy matching for typos and slight variations
    # Check if names are very similar (e.g., "jonathann" vs "jonathan")
    similarity = difflib.SequenceMatcher(None, norm_name1, norm_name2).ratio()

    # If names are at least 85% similar and at least 3 characters long, consider them a match
    if similarity >= 0.85 and len(norm_name1) >= 3 and len(norm_name2) >= 3:
        return True

    # Also check fuzzy matching between all nickname variations
    variations1 = get_name_variations(name1)
    variations2 = get_name_variations(name2)

    for var1 in variations1:
        for var2 in variations2:
            if var1 != var2:  # Skip exact matches (already checked above)
                sim = difflib.SequenceMatcher(None, var1, var2).ratio()
                if sim >= 0.85 and len(var1) >= 3 and len(var2) >= 3:
                    return True

    return False


def normalize_location_id_to_club_name(location_id: str) -> str:
    """
    Convert a Location ID from players.json to a club name for database matching.

    Args:
        location_id: Location ID like "BILTMORE_CC" or legacy "APTA_BILTMORE_CC"

    Returns:
        str: Club name like "Biltmore CC"
    """
    if not location_id:
        return ""

    # Handle legacy APTA_ prefix (for backward compatibility)
    if location_id.startswith("APTA_"):
        club_part = location_id[5:]  # Remove "APTA_"
    else:
        club_part = location_id

    # Common transformations based on the data patterns observed
    transformations = {
        "BILTMORE_CC": "Biltmore CC",
        "EVANSTON": "Evanston",
        "KNOLLWOOD": "Knollwood",
        "WILMETTE_PD_I": "Wilmette PD I",
        "WILMETTE_PD_II": "Wilmette PD II",
        "WINNETKA_I": "Winnetka I",
        "WINNETKA_II": "Winnetka II",
        "BIRCHWOOD": "Birchwood",
        "LAKE_BLUFF": "Lake Bluff",
        "LAKE_FOREST": "Lake Forest",
        "LAKE_SHORE_CC": "Lake Shore CC",
        "LAKESHORE_SANDF": "Lakeshore S&F",
        "MICHIGAN_SHORES": "Michigan Shores",
        "SADDLE_AND_CYCLE": "Saddle & Cycle",
        "VALLEY_LO": "Valley Lo",
        "MIDTOWN_CHICAGO": "Midtown - Chicago",
    }

    # Check direct transformations first
    if club_part in transformations:
        return transformations[club_part]

    # Generic transformation: replace underscores with spaces and title case
    club_name = club_part.replace("_", " ").title()

    # Handle common abbreviations
    club_name = club_name.replace(" Cc", " CC")
    club_name = club_name.replace(" Pd", " PD")
    club_name = club_name.replace(" Sandf", " S&F")

    return club_name


def load_players_data(players_json_path: str = None, league: str = None) -> List[Dict]:
    """
    Load players data from JSON file.

    Args:
        players_json_path: Path to players.json file. If None, uses default path
        league: League identifier to determine which league's data to load

    Returns:
        list: List of player dictionaries
    """
    if players_json_path is None:
        # Default path relative to project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)  # Go up one level from utils/

        # Determine league directory based on league parameter
        if league == "NSTF":
            league_dir = "NSTF"
        elif league == "APTA_CHICAGO":
            league_dir = "apta"
        elif league == "APTA_NATIONAL":
            league_dir = "apta_national"
        else:
            # Default to all leagues data if no specific league or unknown league
            league_dir = "all"

        players_json_path = os.path.join(
            project_root, "data", "leagues", league_dir, "players.json"
        )

    try:
        with open(players_json_path, "r") as f:
            raw_data = json.load(f)

        # Flatten the data structure - handle mixed list/dict structure
        players_data = []
        for item in raw_data:
            if isinstance(item, list):
                # It's a sublist, extend with all items in the sublist
                players_data.extend(item)
            elif isinstance(item, dict):
                # It's a single player record, append it directly
                players_data.append(item)
            else:
                # Skip unknown data types
                continue

        logger.info(f"Loaded {len(players_data)} players from {players_json_path}")
        return players_data
    except FileNotFoundError:
        logger.error(f"Players JSON file not found: {players_json_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing players JSON file: {e}")
        raise


def find_player_id(
    first_name: str,
    last_name: str,
    series_mapping_id: str,
    location_id: str,
    players_data: List[Dict] = None,
    league: str = None,
) -> Optional[str]:
    """
    Find a Player ID by matching first name, last name, series mapping ID, and location ID.

    This function uses deterministic matching with no confirmation step, based on the assumption
    that it's extremely unlikely for two players to have the same name AND be in the same
    club and series.

    Args:
        first_name: Player's first name
        last_name: Player's last name
        series_mapping_id: Series like "Chicago 19"
        location_id: Location ID like "APTA_BILTMORE_CC" OR club name like "Biltmore CC"
        players_data: List of player dictionaries. If None, loads from default path
        league: League identifier to determine which league's data to load

    Returns:
        str|None: Player ID if exactly one match found, None otherwise
    """
    if players_data is None:
        players_data = load_players_data(league=league)

    # Normalize inputs
    norm_first = normalize_name(first_name)
    norm_last = normalize_name(last_name)
    norm_series = series_mapping_id.strip() if series_mapping_id else ""

    # Handle location_id - it could be a Location ID or club name
    if location_id and (location_id.startswith("APTA_") or "_" in location_id):
        # It's a Location ID (legacy APTA_ or raw format), convert to club name
        target_club = normalize_location_id_to_club_name(location_id)
    else:
        # It's already a club name
        target_club = location_id.strip() if location_id else ""

    norm_club = normalize_name(target_club)

    matches = []

    for player in players_data:
        # Skip non-dictionary items (defensive programming)
        if not isinstance(player, dict):
            continue

        # Normalize player data
        player_first = player.get("First Name", "")
        player_last = normalize_name(player.get("Last Name", ""))
        player_series = player.get("Series Mapping ID", "").strip()
        player_club = normalize_name(player.get("Club", ""))

        # Check all four fields for match (with nickname support for first name)
        if (
            names_match(first_name, player_first)
            and player_last == norm_last
            and player_series == norm_series
            and player_club == norm_club
        ):

            matches.append(player)

    if len(matches) == 1:
        player_id = matches[0].get("Player ID")
        logger.info(
            f"Found unique match for {first_name} {last_name} ({target_club}, {series_mapping_id}): {player_id}"
        )
        return player_id
    elif len(matches) == 0:
        logger.warning(
            f"No match found for {first_name} {last_name} ({target_club}, {series_mapping_id})"
        )
        return None
    else:
        # Multiple matches - log for review
        player_ids = [m.get("Player ID") for m in matches]
        logger.warning(
            f"Multiple matches found for {first_name} {last_name} ({target_club}, {series_mapping_id}): {player_ids}"
        )
        return None


def find_player_id_by_club_name(
    first_name: str,
    last_name: str,
    series_mapping_id: str,
    club_name: str,
    players_data: List[Dict] = None,
    league: str = None,
) -> Optional[str]:
    """
    Enhanced multi-tier player ID lookup with progressive fallback strategy.

    Search Strategy:
    1. Primary: first name (with nicknames/fuzzy) + last name + series + club + league
    2. Fallback 1: last name + series + league (drop club and first name)
    3. Fallback 2: last name + series + club + league (drop first name only)
    4. Fallback 3: last name + club + league (drop series and first name)

    Args:
        first_name: Player's first name
        last_name: Player's last name
        series_mapping_id: Series like "Chicago 19" or "Tennaqua - 6"
        club_name: Club name like "Biltmore CC"
        players_data: List of player dictionaries. If None, loads from default path
        league: League identifier like "APTA_CHICAGO" or "NSTF" to disambiguate multi-league players

    Returns:
        str|None: Player ID if exactly one match found, None otherwise
    """
    # Load players data if not provided
    if players_data is None:
        players_data = load_players_data(league=league)

    # Filter by league first if provided (to handle multi-league players)
    if league:
        league_filtered_data = [
            p for p in players_data if isinstance(p, dict) and p.get("League") == league
        ]
        if league_filtered_data:
            logger.info(
                f"Filtering {len(players_data)} players to {len(league_filtered_data)} for league {league}"
            )
            players_data = league_filtered_data
        else:
            logger.warning(
                f"No players found for league {league}. Available leagues: {set(p.get('League', 'None') for p in players_data if isinstance(p, dict))}"
            )

    # ==========================================
    # PRIMARY SEARCH: All fields with first name matching
    # ==========================================
    logger.info(
        f"Starting primary search for {first_name} {last_name} ({club_name}, {series_mapping_id}, {league})"
    )
    player_id = find_player_id(
        first_name, last_name, series_mapping_id, club_name, players_data, league
    )

    if player_id:
        logger.info(f"✅ PRIMARY: Found match using full search: {player_id}")
        return player_id

    # Normalize inputs for fallback searches
    norm_last = normalize_name(last_name)
    norm_series = series_mapping_id.strip() if series_mapping_id else ""
    norm_club = normalize_name(club_name)

    # ==========================================
    # FALLBACK 1: last name + series + league (drop club and first name)
    # ==========================================
    logger.info(
        f"PRIMARY failed, trying FALLBACK 1: last name + series + league for {first_name} {last_name}"
    )

    fallback1_matches = []
    for player in players_data:
        if not isinstance(player, dict):
            continue

        player_last = normalize_name(player.get("Last Name", ""))
        player_series = player.get("Series Mapping ID", "").strip()

        # Match: last name + series (ignore club and first name)
        if player_last == norm_last and player_series == norm_series:
            fallback1_matches.append(player)

    if len(fallback1_matches) == 1:
        player_id = fallback1_matches[0].get("Player ID")
        player_first = fallback1_matches[0].get("First Name", "")
        player_club = fallback1_matches[0].get("Club", "")
        logger.info(
            f"✅ FALLBACK 1: Found unique match {first_name} {last_name} → {player_first} {last_name} ({player_club}, {series_mapping_id}): {player_id}"
        )
        return player_id
    elif len(fallback1_matches) > 1:
        player_names = [
            f"{m.get('First Name', '')} {m.get('Last Name', '')} ({m.get('Club', '')})"
            for m in fallback1_matches
        ]
        logger.info(
            f"⚠️ FALLBACK 1: Multiple matches found for {last_name} + {series_mapping_id}: {player_names}"
        )
    else:
        logger.info(
            f"❌ FALLBACK 1: No matches found for {last_name} + {series_mapping_id}"
        )

    # ==========================================
    # FALLBACK 2: last name + series + club + league (drop first name only)
    # ==========================================
    logger.info(
        f"FALLBACK 1 failed, trying FALLBACK 2: last name + series + club + league for {first_name} {last_name}"
    )

    fallback2_matches = []
    for player in players_data:
        if not isinstance(player, dict):
            continue

        player_last = normalize_name(player.get("Last Name", ""))
        player_series = player.get("Series Mapping ID", "").strip()
        player_club = normalize_name(player.get("Club", ""))

        # Match: last name + series + club (ignore first name)
        if (
            player_last == norm_last
            and player_series == norm_series
            and player_club == norm_club
        ):
            fallback2_matches.append(player)

    if len(fallback2_matches) == 1:
        player_id = fallback2_matches[0].get("Player ID")
        player_first = fallback2_matches[0].get("First Name", "")
        logger.info(
            f"✅ FALLBACK 2: Found unique match {first_name} {last_name} → {player_first} {last_name} ({club_name}, {series_mapping_id}): {player_id}"
        )
        return player_id
    elif len(fallback2_matches) > 1:
        player_names = [
            f"{m.get('First Name', '')} {m.get('Last Name', '')}"
            for m in fallback2_matches
        ]
        player_ids = [m.get("Player ID") for m in fallback2_matches]
        logger.info(
            f"⚠️ FALLBACK 2: Multiple matches found for {last_name} ({club_name}, {series_mapping_id}): {player_names} → {player_ids}"
        )
    else:
        logger.info(
            f"❌ FALLBACK 2: No matches found for {last_name} ({club_name}, {series_mapping_id})"
        )

    # ==========================================
    # FALLBACK 3: last name + club + league (drop series and first name)
    # ==========================================
    logger.info(
        f"FALLBACK 2 failed, trying FALLBACK 3: last name + club + league for {first_name} {last_name}"
    )

    fallback3_matches = []
    for player in players_data:
        if not isinstance(player, dict):
            continue

        player_last = normalize_name(player.get("Last Name", ""))
        player_club = normalize_name(player.get("Club", ""))

        # Match: last name + club (ignore series and first name)
        if player_last == norm_last and player_club == norm_club:
            fallback3_matches.append(player)

    if len(fallback3_matches) == 1:
        player_id = fallback3_matches[0].get("Player ID")
        player_first = fallback3_matches[0].get("First Name", "")
        player_series = fallback3_matches[0].get("Series Mapping ID", "")
        logger.info(
            f"✅ FALLBACK 3: Found unique match {first_name} {last_name} → {player_first} {last_name} ({club_name}, {player_series}): {player_id}"
        )
        return player_id
    elif len(fallback3_matches) > 1:
        player_names = [
            f"{m.get('First Name', '')} {m.get('Last Name', '')} ({m.get('Series Mapping ID', '')})"
            for m in fallback3_matches
        ]
        player_ids = [m.get("Player ID") for m in fallback3_matches]
        logger.info(
            f"⚠️ FALLBACK 3: Multiple matches found for {last_name} ({club_name}): {player_names} → {player_ids}"
        )
    else:
        logger.info(f"❌ FALLBACK 3: No matches found for {last_name} ({club_name})")

    # ==========================================
    # ALL FALLBACKS EXHAUSTED
    # ==========================================
    logger.warning(
        f"❌ ALL SEARCHES FAILED: No unique player ID found for {first_name} {last_name} ({club_name}, {series_mapping_id}, {league})"
    )
    return None


def find_player_id_by_location_id(
    first_name: str,
    last_name: str,
    series_mapping_id: str,
    location_id: str,
    players_data: List[Dict] = None,
) -> Optional[str]:
    """
    Convenience function to find Player ID using Location ID directly.

    Args:
        first_name: Player's first name
        last_name: Player's last name
        series_mapping_id: Series like "Chicago 19"
        location_id: Location ID like "BILTMORE_CC" or legacy "APTA_BILTMORE_CC"
        players_data: List of player dictionaries. If None, loads from default path

    Returns:
        str|None: Player ID if exactly one match found, None otherwise
    """
    return find_player_id(
        first_name, last_name, series_mapping_id, location_id, players_data
    )
