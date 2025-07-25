import json
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs, unquote

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Import stealth browser manager for fingerprint evasion
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from stealth_browser import StealthBrowserManager

print("🎾 TennisScores Match Scraper - Best Practice Approach")
print("=" * 80)
print("✅ Only imports matches with legitimate match IDs - no synthetic IDs!")
print("✅ Ensures data integrity and best practices for all leagues")
print("=" * 80)


# Dynamic League Configuration - User Input Based
def get_league_config(league_subdomain=None):
    """Get dynamic league configuration based on user input"""
    if not league_subdomain:
        # This will be passed from the main function
        raise ValueError("League subdomain must be provided")

    base_url = f"https://{league_subdomain}.tenniscores.com"

    # Enhanced league mapping to handle different subdomain patterns
    league_mappings = {
        "aptachicago": {"league_id": "APTA_CHICAGO", "type": "apta"},
        "apta": {"league_id": "APTA", "type": "apta"},
        "nstf": {"league_id": "NSTF", "type": "nstf"},
        "cita": {"league_id": "CITA", "type": "cita"},
        "tennaqua": {
            "league_id": "CITA",
            "type": "cita",
        },  # CITA uses tennaqua subdomain
        "cnswpl": {
            "league_id": "CNSWPL",
            "type": "cnswpl",
        },  # Chicago North Shore Women's Platform Tennis League
    }

    # Get league configuration or use subdomain as fallback
    if league_subdomain.lower() in league_mappings:
        config = league_mappings[league_subdomain.lower()]
        league_id = config["league_id"]
        league_type = config["type"]
    else:
        # Fallback for unknown subdomains
        league_id = league_subdomain.upper()
        league_type = "unknown"

    return {
        "league_id": league_id,
        "subdomain": league_subdomain,
        "base_url": base_url,
        "type": league_type,
    }


def build_league_data_dir(league_id):
    """
    Build the dynamic data directory path based on the league ID.

    Args:
        league_id (str): The league identifier

    Returns:
        str: The data directory path (e.g., 'data/leagues/NSTF')
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))  # data/etl/scrapers/
    etl_dir = os.path.dirname(script_dir)  # data/etl/
    project_root = os.path.dirname(
        os.path.dirname(etl_dir)
    )  # rally/ (up one more level)

    league_data_dir = os.path.join(project_root, "data", "leagues", league_id)
    os.makedirs(league_data_dir, exist_ok=True)

    return league_data_dir


def deduplicate_matches(matches):
    """
    Remove duplicate matches using multiple strategies.
    
    Args:
        matches (list): List of match dictionaries
        
    Returns:
        tuple: (unique_matches, duplicates_removed, stats)
    """
    if not matches:
        return [], 0, {"exact_duplicates": 0, "match_id_duplicates": 0}
    
    print(f"🔍 Deduplicating {len(matches)} matches...")
    
    # Strategy 1: Remove exact duplicates (same JSON representation)
    seen_exact = set()
    unique_matches = []
    exact_duplicates = 0
    
    for match in matches:
        record_str = json.dumps(match, sort_keys=True)
        if record_str not in seen_exact:
            seen_exact.add(record_str)
            unique_matches.append(match)
        else:
            exact_duplicates += 1
    
    # Strategy 2: Remove duplicates based on match_id (if available)
    match_id_duplicates = 0
    if unique_matches and any(match.get('match_id') for match in unique_matches):
        seen_match_ids = set()
        final_matches = []
        
        for match in unique_matches:
            match_id = match.get('match_id')
            if match_id and match_id != 'None':
                if match_id not in seen_match_ids:
                    seen_match_ids.add(match_id)
                    final_matches.append(match)
                else:
                    match_id_duplicates += 1
            else:
                # Keep matches without match_id (they'll be handled by exact deduplication)
                final_matches.append(match)
        
        unique_matches = final_matches
    
    total_duplicates = exact_duplicates + match_id_duplicates
    
    stats = {
        "exact_duplicates": exact_duplicates,
        "match_id_duplicates": match_id_duplicates,
        "total_duplicates": total_duplicates,
        "final_count": len(unique_matches)
    }
    
    if total_duplicates > 0:
        print(f"✅ Removed {total_duplicates} duplicates:")
        print(f"   - {exact_duplicates} exact duplicates")
        print(f"   - {match_id_duplicates} match_id duplicates")
        print(f"📊 Final unique matches: {len(unique_matches)}")
    else:
        print(f"✅ No duplicates found - all {len(unique_matches)} matches are unique")
    
    return unique_matches, total_duplicates, stats


# Global variable to store players data for lookups
players_data = []

# Common nickname mappings for better name matching
NICKNAME_MAPPINGS = {
    # Common nicknames to full names
    "mike": ["michael"],
    "jim": ["james"],
    "bob": ["robert"],
    "bill": ["william"],
    "dave": ["david"],
    "steve": ["steven", "stephen"],
    "chris": ["christopher"],
    "matt": ["matthew"],
    "dan": ["daniel"],
    "tom": ["thomas"],
    "tony": ["anthony"],
    "rick": ["richard"],
    "dick": ["richard"],
    "nick": ["nicholas"],
    "ben": ["benjamin"],
    "sam": ["samuel"],
    "alex": ["alexander"],
    "brad": ["bradley"],
    "greg": ["gregory"],
    "rob": ["robert"],
    "joe": ["joseph"],
    "pat": ["patrick"],
    "ed": ["edward"],
    "ted": ["theodore", "edward"],
    "andy": ["andrew"],
    "tony": ["anthony"],
    "brian": ["bryan"],  # Common spelling variation
    "bryan": ["brian"],  # Reverse mapping
    # Full names to nicknames (reverse mappings)
    "michael": ["mike"],
    "james": ["jim", "jimmy"],
    "robert": ["bob", "rob"],
    "william": ["bill", "will"],
    "david": ["dave"],
    "steven": ["steve"],
    "stephen": ["steve"],
    "christopher": ["chris"],
    "matthew": ["matt"],
    "daniel": ["dan", "danny"],
    "thomas": ["tom"],
    "anthony": ["tony"],
    "richard": ["rick", "dick"],
    "nicholas": ["nick"],
    "benjamin": ["ben"],
    "samuel": ["sam"],
    "alexander": ["alex"],
    "bradley": ["brad"],
    "gregory": ["greg"],
    "joseph": ["joe"],
    "patrick": ["pat"],
    "edward": ["ed", "ted"],
    "theodore": ["ted"],
    "andrew": ["andy"],
}


def get_name_variations(name):
    """Get all possible variations of a name including nicknames."""
    if not name:
        return []

    name_lower = name.lower()
    variations = [name_lower]  # Always include the original

    # Add mapped variations
    if name_lower in NICKNAME_MAPPINGS:
        variations.extend(NICKNAME_MAPPINGS[name_lower])

    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        if var not in seen:
            seen.add(var)
            unique_variations.append(var)

    return unique_variations


def load_players_data(league_id):
    """Load players data from players.json for Player ID lookups."""
    global players_data
    try:
        # Build path using dynamic league directory
        league_data_dir = build_league_data_dir(league_id)
        players_path = os.path.join(league_data_dir, "players.json")

        with open(players_path, "r", encoding="utf-8") as f:
            players_data = json.load(f)
        print(
            f"📊 Loaded {len(players_data)} players for ID lookup from {players_path}"
        )
        return True
    except FileNotFoundError:
        print(
            f"⚠️  Warning: players.json not found at {players_path}. Player IDs will not be available."
        )
        return False
    except Exception as e:
        print(f"❌ Error loading players data: {str(e)}")
        return False


def extract_series_name_from_team(team_name):
    """
    Extract series name from team name, auto-detecting APTA vs NSTF vs CNSWPL format.

    Args:
        team_name (str): Team name in various formats

    Returns:
        str: Standardized series name or None if not detected

    Examples:
        APTA: "Birchwood - 6" -> "Chicago 6"
        NSTF: "Birchwood S1" -> "Series 1"
        NSTF: "Wilmette Sunday A" -> "Series A"
        CNSWPL: "Birchwood 1" -> "Series 1"
        CNSWPL: "Hinsdale PC 1a" -> "Series 1a"
    """
    if not team_name:
        return None

    team_name = team_name.strip()

    # APTA Chicago format: "Club - Number"
    if " - " in team_name:
        parts = team_name.split(" - ")
        if len(parts) > 1:
            series_num = parts[1].strip()
            return f"Chicago {series_num}"

    # NSTF format: "Club SNumber" or "Club SNumberLetter" (e.g., S1, S2A, S2B)
    elif re.search(r"S(\d+[A-Z]*)", team_name):
        match = re.search(r"S(\d+[A-Z]*)", team_name)
        if match:
            series_identifier = match.group(1)
            return f"Series {series_identifier}"

    # NSTF Sunday formats
    elif "Sunday A" in team_name:
        return "Series A"
    elif "Sunday B" in team_name:
        return "Series B"

    # CNSWPL format: "Club Number" or "Club NumberLetter" (e.g., "Birchwood 1", "Hinsdale PC 1a")
    elif re.search(r"\s(\d+[a-zA-Z]?)$", team_name):
        match = re.search(r"\s(\d+[a-zA-Z]?)$", team_name)
        if match:
            series_identifier = match.group(1)
            return f"Series {series_identifier}"

    # Direct series name (already formatted)
    elif team_name.startswith("Series ") or team_name.startswith("Chicago "):
        return team_name

    return None


def extract_club_name_from_team(team_name):
    """Extract the club name from a team name like 'Birchwood - 6' or 'Lake Forest S1' -> 'Birchwood' or 'Lake Forest'."""
    if not team_name:
        return ""

    # Handle APTA format: "Birchwood - 6" -> "Birchwood"
    if " - " in team_name:
        parts = team_name.split(" - ")
        return parts[0].strip() if parts else team_name.strip()

    # Handle NSTF format: "Lake Forest S1" or "Wilmette S1 T2" -> "Lake Forest" or "Wilmette"
    # Remove series suffixes like "S1", "S1 T2", "S2A", etc.
    import re

    # Pattern matches: S1, S1 T2, S2A, S2B, etc.
    pattern = r"\s+S\d+[A-Z]*(\s+T\d+)?$"
    cleaned = re.sub(pattern, "", team_name).strip()
    return cleaned if cleaned else team_name.strip()


def normalize_name_for_lookup(name):
    """Normalize a name for more flexible matching."""
    if not name:
        return ""
    # Convert to lowercase and strip whitespace
    normalized = name.lower().strip()

    # Remove common suffixes and patterns
    patterns_to_remove = [
        " by forfeit",
        " forfeit",
        "by forfeit",
        " jr.",
        " jr",
        " sr.",
        " sr",
        " iii",
        " iv",
        " ii",
    ]

    for pattern in patterns_to_remove:
        if normalized.endswith(pattern):
            normalized = normalized[: -len(pattern)].strip()

    # Remove periods and other punctuation
    normalized = normalized.replace(".", "").replace(",", "")

    return normalized


def levenshtein_distance(s1, s2):
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similar_strings(s1, s2, threshold=0.8):
    """Check if two strings are similar using Levenshtein distance and character overlap."""
    if not s1 or not s2:
        return False

    # Quick exact match
    if s1.lower() == s2.lower():
        return True

    # Levenshtein distance approach for short strings
    if len(s1) <= 8 and len(s2) <= 8:
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return True
        distance = levenshtein_distance(s1.lower(), s2.lower())
        similarity = 1 - (distance / max_len)
        if similarity >= threshold:
            return True

    # Character overlap method for longer strings
    set1 = set(s1.lower())
    set2 = set(s2.lower())

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    similarity = intersection / union if union > 0 else 0
    return similarity >= threshold


def lookup_player_id_enhanced(series, team_name, first_name, last_name, league_id=None):
    """Enhanced Player ID lookup with multiple strategies for better accuracy."""
    if not players_data and league_id:
        load_players_data(league_id)

    club_name = extract_club_name_from_team(team_name)

    # Normalize names for lookup
    first_name_norm = normalize_name_for_lookup(first_name)
    last_name_norm = normalize_name_for_lookup(last_name)

    if not first_name_norm or not last_name_norm:
        print(
            f"    [LOOKUP] Warning: Empty name after normalization - {first_name} {last_name}"
        )
        return None

    # Strategy 1: Exact match (Series + Club + Names)
    for player in players_data:
        if (
            player.get("Series") == series
            and player.get("Club") == club_name
            and normalize_name_for_lookup(player.get("First Name", ""))
            == first_name_norm
            and normalize_name_for_lookup(player.get("Last Name", "")) == last_name_norm
        ):
            print(
                f"    [LOOKUP] Strategy 1 (Exact): Found {first_name} {last_name} → {player.get('Player ID')}"
            )
            return player.get("Player ID")

    # Strategy 2: Series-wide matching (handles club changes)
    series_matches = []
    for player in players_data:
        if (
            player.get("Series") == series
            and normalize_name_for_lookup(player.get("First Name", ""))
            == first_name_norm
            and normalize_name_for_lookup(player.get("Last Name", "")) == last_name_norm
        ):
            series_matches.append(player)

    if len(series_matches) == 1:
        player = series_matches[0]
        print(
            f"    [LOOKUP] Strategy 2 (Series-wide): Found {first_name} {last_name} → {player.get('Player ID')} (Different club: {player.get('Club')})"
        )
        return player.get("Player ID")

    # Strategy 2.5: Nickname matching (same club)
    first_name_variations = get_name_variations(first_name_norm)
    last_name_variations = get_name_variations(last_name_norm)

    for player in players_data:
        if player.get("Series") == series and player.get("Club") == club_name:

            player_first_norm = normalize_name_for_lookup(player.get("First Name", ""))
            player_last_norm = normalize_name_for_lookup(player.get("Last Name", ""))

            # Check if any variation of the search name matches any variation of the player name
            first_match = player_first_norm in first_name_variations or any(
                var in get_name_variations(player_first_norm)
                for var in first_name_variations
            )

            last_match = player_last_norm in last_name_variations or any(
                var in get_name_variations(player_last_norm)
                for var in last_name_variations
            )

            if first_match and last_match:
                print(
                    f"    [LOOKUP] Strategy 2.5 (Nickname): Found {first_name} {last_name} → {player.get('Player ID')} (DB: {player.get('First Name')} {player.get('Last Name')})"
                )
                return player.get("Player ID")

    # Strategy 3: Fuzzy matching (same club)
    for player in players_data:
        if player.get("Series") == series and player.get("Club") == club_name:

            player_first_norm = normalize_name_for_lookup(player.get("First Name", ""))
            player_last_norm = normalize_name_for_lookup(player.get("Last Name", ""))

            # Try various fuzzy matching approaches
            first_similar = similar_strings(
                first_name_norm, player_first_norm, threshold=0.8
            )
            last_similar = similar_strings(
                last_name_norm, player_last_norm, threshold=0.8
            )

            if first_similar and last_similar:
                print(
                    f"    [LOOKUP] Strategy 3 (Fuzzy): Found {first_name} {last_name} → {player.get('Player ID')} (DB: {player.get('First Name')} {player.get('Last Name')})"
                )
                return player.get("Player ID")

    # Strategy 4: Very lenient matching (same club only, lower threshold)
    for player in players_data:
        if player.get("Series") == series and player.get("Club") == club_name:

            player_first_norm = normalize_name_for_lookup(player.get("First Name", ""))
            player_last_norm = normalize_name_for_lookup(player.get("Last Name", ""))

            # More lenient fuzzy matching
            first_similar = similar_strings(
                first_name_norm, player_first_norm, threshold=0.6
            )
            last_similar = similar_strings(
                last_name_norm, player_last_norm, threshold=0.6
            )

            if first_similar and last_similar:
                print(
                    f"    [LOOKUP] Strategy 4 (Lenient): Found {first_name} {last_name} → {player.get('Player ID')} (DB: {player.get('First Name')} {player.get('Last Name')})"
                )
                return player.get("Player ID")

    # Strategy 5: Cross-league database search (for substitute players)
    print(f"    [LOOKUP] Strategy 5: Cross-league database search for substitute player...")
    try:
        # Import database utilities (need to add this to the scraper)
        sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        from database_utils import execute_query_one
        
        # Search across ALL leagues for this player name
        cross_league_query = """
            SELECT tenniscores_player_id, first_name, last_name, league_id
            FROM players 
            WHERE LOWER(first_name) = LOWER(%s) AND LOWER(last_name) = LOWER(%s)
            AND is_active = TRUE
            ORDER BY league_id
            LIMIT 1
        """
        cross_league_result = execute_query_one(cross_league_query, [first_name, last_name])
        
        if cross_league_result:
            player_id = cross_league_result['tenniscores_player_id']
            found_league = cross_league_result['league_id']
            print(f"    [LOOKUP] Strategy 5 (Cross-league): Found {first_name} {last_name} → {player_id} (League: {found_league})")
            return player_id
        else:
            print(f"    [LOOKUP] Strategy 5: No cross-league match found in database")
    except Exception as e:
        print(f"    [LOOKUP] Strategy 5: Database search failed: {e}")

    # No match found anywhere
    print(
        f"    [LOOKUP] No match found for {first_name} {last_name} in {club_name} ({series}) - tried all strategies"
    )
    return None


def lookup_player_id(series, team_name, first_name, last_name, league_id=None):
    """
    Look up a Player ID based on Series, Club, First Name, and Last Name.

    This is a wrapper that calls the enhanced lookup function.
    """
    return lookup_player_id_enhanced(
        series, team_name, first_name, last_name, league_id
    )


def extract_match_id_from_url(url):
    """
    Extract match ID from TennisScores URL.
    Based on the birchwood scripts pattern - looks for sch= parameter.
    Handles both direct and URL-encoded formats.
    """
    try:
        # URL-decode the URL first to handle CNSWPL's encoded format
        from urllib.parse import unquote
        decoded_url = unquote(url)
        
        parsed_url = urlparse(decoded_url)
        query_params = parse_qs(parsed_url.query)
        
        # Look for sch parameter (TennisScores match ID)
        sch_param = query_params.get('sch', [None])[0]
        if sch_param:
            return sch_param
        
        # Look for other potential match ID parameters
        for param_name in ['match_id', 'id', 'match']:
            param_value = query_params.get(param_name, [None])[0]
            if param_value:
                return param_value
        
        return None
        
    except Exception as e:
        print(f"Warning: Error extracting match ID from URL {url}: {e}")
        return None


def find_match_links(soup, base_url):
    """
    Find all match links on a page and extract their IDs.
    Based on the birchwood scripts pattern.
    """
    match_links = []
    
    try:
        # Look for links containing print_match.php?sch= (both direct and URL-encoded)
        # CNSWPL uses URL-encoded format: print%5Fmatch.php?sch= (where %5F = _)
        # Other leagues use direct format: print_match.php?sch=
        match_link_elements = soup.find_all('a', href=re.compile(r'print%5F?match\.php\?sch='))
        
        for link in match_link_elements:
            href = link.get('href')
            if href:
                # Create full URL
                full_url = urljoin(base_url, href)
                
                # Extract match ID
                match_id = extract_match_id_from_url(href)
                
                if match_id:
                    # Get link text as description
                    description = link.get_text(strip=True)
                    if not description:
                        # Try to get text from parent elements
                        try:
                            parent = link.parent
                            description = parent.get_text(strip=True)
                        except:
                            description = f"Match_{match_id}"
                    
                    match_links.append({
                        'match_id': match_id,
                        'description': description,
                        'url': href,
                        'full_url': full_url
                    })
                    
                    print(f"    Found match link: {description} -> {match_id}")
        
        print(f"    Found {len(match_links)} match links")
        
    except Exception as e:
        print(f"Error finding match links: {e}")
    
    return match_links


def scrape_individual_match_page(driver, match_link, series_name, league_id):
    """
    Scrape detailed information from an individual match page.
    Each page contains 4 lines (matches), so we create separate match data for each line.
    Returns a list of match data in the exact format of match_history.json with match_id added.
    """
    match_url = match_link['full_url']
    match_id = match_link['match_id']
    
    print(f"    Scraping individual match: {match_id}")
    
    try:
        # Navigate to the match page
        driver.get(match_url)
        time.sleep(2)  # Wait for page to load
        
        # Parse the page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract date from the page
        date = extract_match_date_from_page(soup)
        
        # Extract teams from the page
        home_team, away_team = extract_teams_from_page(soup, league_id, series_name)
        
        # Extract individual line scores with set details
        line_scores = extract_line_scores_from_page(soup)
        
        if not line_scores:
            print(f"    Warning: No line scores found for match {match_id}")
            return []
        
        matches_data = []
        
        # Create a separate match for each line
        for line_data in line_scores:
            line_number = line_data.get('line_number', 1)
            
            # Create unique match_id for this specific line
            unique_match_id = f"{match_id}_Line{line_number}"
            
            # Create match data for this line
            match_data = {
                'league_id': league_id,
                'match_id': unique_match_id,  # Use unique match_id with line suffix
                'source_league': league_id,
                'Line': f"Line {line_number}"  # Add separate Line attribute
            }
            
            # Add date
            if date:
                match_data['Date'] = date
            
            # Add teams
            if home_team:
                match_data['Home Team'] = home_team
            if away_team:
                match_data['Away Team'] = away_team
            
            # Extract individual players for this line
            if len(line_data['home_players']) >= 2:
                match_data['Home Player 1'] = line_data['home_players'][0]['name']
                match_data['Home Player 2'] = line_data['home_players'][1]['name']
                # Add player IDs (will be populated by player lookup)
                match_data['Home Player 1 ID'] = line_data['home_players'][0].get('id', '')
                match_data['Home Player 2 ID'] = line_data['home_players'][1].get('id', '')
            
            if len(line_data['away_players']) >= 2:
                match_data['Away Player 1'] = line_data['away_players'][0]['name']
                match_data['Away Player 2'] = line_data['away_players'][1]['name']
                # Add player IDs (will be populated by player lookup)
                match_data['Away Player 1 ID'] = line_data['away_players'][0].get('id', '')
                match_data['Away Player 2 ID'] = line_data['away_players'][1].get('id', '')
            
            # Create legacy scores format for this specific line only
            legacy_scores = create_legacy_scores_from_line_scores([line_data], line_number)
            if legacy_scores:
                match_data['Scores'] = legacy_scores
                match_data['Winner'] = determine_winner_from_scores(legacy_scores)
            
            # Validate the match data
            if validate_match_data(match_data):
                matches_data.append(match_data)
                print(f"    ✅ Created match for Line {line_number}")
            else:
                print(f"    ⚠️ Invalid match data for Line {line_number}")
        
        return matches_data
            
    except Exception as e:
        print(f"    Error scraping individual match {match_id}: {e}")
        return []


def extract_match_date_from_page(soup):
    """Extract match date from the page."""
    
    # First try to find date in the header area (more specific)
    header_divs = soup.find_all('div', class_='datelocheader')
    for header_div in header_divs:
        header_text = header_div.get_text(strip=True)
        
        # Look for date patterns in the header
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            r'(\d{1,2}-\d{1,2}-\d{4})',  # MM-DD-YYYY
            r'([A-Za-z]+ \d{1,2}, \d{4})',  # Month DD, YYYY
            r'(\d{1,2}-[A-Za-z]+-\d{2,4})',  # DD-MMM-YY or DD-MMM-YYYY
            r'(\d{1,2}/\d{1,2}/\d{2})',  # MM/DD/YY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, header_text)
            if match:
                date_str = match.group(1)
                # Try to parse and format consistently
                try:
                    parsed_date = parse_date_string(date_str)
                    if parsed_date:
                        # Format to match APTA_CHICAGO match_history.json format: DD-MMM-YY
                        return parsed_date.strftime('%d-%b-%y')
                except:
                    pass
                return date_str
    
    # Fallback to searching entire page if not found in header
    page_text = soup.get_text()
    
    # Try different date patterns in full page text
    date_patterns = [
        r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
        r'(\d{1,2}-\d{1,2}-\d{4})',  # MM-DD-YYYY
        r'([A-Za-z]+ \d{1,2}, \d{4})',  # Month DD, YYYY
        r'(\d{1,2}-[A-Za-z]+-\d{2,4})',  # DD-MMM-YY or DD-MMM-YYYY
        r'(\d{1,2}/\d{1,2}/\d{2})',  # MM/DD/YY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, page_text)
        if match:
            date_str = match.group(1)
            # Try to parse and format consistently
            try:
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    # Format to match APTA_CHICAGO match_history.json format: DD-MMM-YY
                    return parsed_date.strftime('%d-%b-%y')
            except:
                pass
            return date_str
    
    return None


def extract_teams_from_page(soup, league_id, series_name=None):
    """Extract home and away team names from the page."""
    try:
        # Look for the header that contains team names
        # Format: "Salt Creek - 4 @ Westmoreland - 4: 4 - 10"
        header_divs = soup.find_all('div', class_='datelocheader')
        
        for header_div in header_divs:
            header_text = header_div.get_text(strip=True)
            
            # Extract team names from header
            # Pattern: "Team1 - Series @ Team2 - Series: Score1 - Score2"
            # Team1 is visiting (away), Team2 is home (after @)
            match = re.search(r'(.+?)\s*-\s*\d+\s*@\s*(.+?)\s*-\s*\d+', header_text)
            if match:
                away_team_raw = match.group(1).strip()  # Team1 is away (visiting)
                home_team_raw = match.group(2).strip()  # Team2 is home (after @)
                
                # Extract series number from series_name (e.g., "Chicago 22" -> "22")
                series_number = ""
                if series_name:
                    series_match = re.search(r'(\d+)', series_name)
                    if series_match:
                        series_number = series_match.group(1)
                
                # Add series number to team names with proper formatting (Team - Number)
                if series_number:
                    home_team = f"{home_team_raw} - {series_number}"
                    away_team = f"{away_team_raw} - {series_number}"
                else:
                    home_team = home_team_raw
                    away_team = away_team_raw
                
                return home_team, away_team
        
        return None, None
        
    except Exception as e:
        print(f"Error extracting teams: {e}")
        return None, None


def extract_line_scores_from_page(soup):
    """Extract line scores from individual match page."""
    try:
        line_scores = []
        
        # Find all tables with class "standings-table2"
        tables = soup.find_all('table', class_='standings-table2')
        
        for table in tables:
            # Extract line number from the first cell
            line_cell = table.find('td', class_='line_desc')
            if not line_cell:
                continue
                
            line_text = line_cell.get_text(strip=True)
            line_match = re.search(r'Line (\d+)', line_text)
            if not line_match:
                continue
                
            line_number = int(line_match.group(1))
            
            # Extract player data from the table
            player_cells = table.find_all('td', class_='card_names')
            
            home_players = []
            away_players = []
            
            for cell in player_cells:
                # Find player links
                player_links = cell.find_all('a', href=re.compile(r'player\.php\?print&p='))
                
                for link in player_links:
                    player_name = link.get_text(strip=True)
                    player_id = extract_player_id_from_url(link.get('href', ''))
                    
                    player_data = {
                        'name': player_name,
                        'id': player_id
                    }
                    
                    # Determine if this is home or away player based on position
                    # NOTE: Since we swapped teams in extract_teams_from_page, we need to swap here too
                    # First row is typically away team (visiting), second row is home team 
                    row = link.find_parent('tr')
                    if row and 'tr_line_desc' in row.get('class', []):
                        away_players.append(player_data)  # First row is away (swapped)
                    else:
                        home_players.append(player_data)  # Second row is home (swapped)
            
            # Extract scores from the last columns - need to get home and away scores separately
            rows = table.find_all('tr')
            home_scores = []
            away_scores = []
            
            for row in rows:
                # Look for rows with score cells
                score_cells = row.find_all('td', class_='pts2')
                if score_cells:
                    # NOTE: Since we swapped teams/players, we need to swap scores too
                    # First row with scores is away team, second is home team
                    if not away_scores:  # First row with scores is away (swapped)
                        for cell in score_cells:
                            score_text = cell.get_text(strip=True)
                            if score_text and score_text.strip() and score_text.strip() != '&nbsp;':
                                try:
                                    away_scores.append(int(score_text.strip()))
                                except ValueError:
                                    pass
                    elif not home_scores:  # Second row with scores is home (swapped)
                        for cell in score_cells:
                            score_text = cell.get_text(strip=True)
                            if score_text and score_text.strip() and score_text.strip() != '&nbsp;':
                                try:
                                    home_scores.append(int(score_text.strip()))
                                except ValueError:
                                    pass
            
            # Create line score data with separate home and away scores
            line_data = {
                'line_number': line_number,
                'home_players': home_players,
                'away_players': away_players,
                'home_scores': home_scores,
                'away_scores': away_scores
            }
            
            line_scores.append(line_data)
        
        return line_scores
        
    except Exception as e:
        print(f"Error extracting line scores: {e}")
        return []


def extract_player_id_from_url(url):
    """Extract player ID from player.php URL."""
    try:
        match = re.search(r'p=([^&]+)', url)
        if match:
            return match.group(1)
    except:
        pass
    return None


def generate_player_id(player_name):
    """Generate a placeholder player ID for testing purposes."""
    # This is a placeholder - in real implementation, this would look up the actual player ID
    # The format appears to be base64-encoded strings like "WkNDOHlMdjZqUT09"
    import base64
    import hashlib
    
    # Create a hash of the player name
    name_hash = hashlib.md5(player_name.encode()).hexdigest()[:12]
    
    # Convert to base64-like format (this is a simplified version)
    # In real implementation, this would be the actual player ID from the database
    encoded = base64.b64encode(name_hash.encode()).decode()
    
    # Remove padding and ensure it matches the pattern
    encoded = encoded.replace('=', '')
    
    return encoded


def create_legacy_scores_from_line_scores(line_scores, target_line_number=1):
    """
    Create legacy scores format from individual line scores.
    Only use scores from the specified line number (default: 1 for first line).
    """
    if not line_scores:
        return None
    
    # Find the target line
    target_line = None
    for line in line_scores:
        if line.get('line_number') == target_line_number:
            target_line = line
            break
    
    if not target_line:
        print(f"    Warning: Could not find line {target_line_number} in scores")
        return None
    
    # Extract scores only from the target line
    set_scores = []
    
    # Use the new home_scores and away_scores format
    if 'home_scores' in target_line and 'away_scores' in target_line:
        home_scores = target_line['home_scores']
        away_scores = target_line['away_scores']
        
        # Pair up home and away scores for each set
        for i in range(min(len(home_scores), len(away_scores))):
            home_score = home_scores[i]
            away_score = away_scores[i]
            set_scores.append(f"{home_score}-{away_score}")
    
    # Fallback to old structure if needed
    elif 'scores' in target_line and target_line['scores']:
        # The scores array contains individual set scores
        # We need to pair them up as home-away
        scores = target_line['scores']
        for i in range(0, len(scores), 2):
            if i + 1 < len(scores):
                home_score = scores[i]
                away_score = scores[i + 1]
                set_scores.append(f"{home_score}-{away_score}")
    
    # Handle old structure with separate home/away set scores
    elif 'home_set_scores' in target_line and 'away_set_scores' in target_line:
        for i, home_score in enumerate(target_line['home_set_scores']):
            away_score = target_line['away_set_scores'][i] if i < len(target_line['away_set_scores']) else 0
            set_scores.append(f"{home_score}-{away_score}")
    
    if set_scores:
        return ", ".join(set_scores)
    
    return None


def determine_winner_from_scores(scores):
    """Determine winner from scores."""
    if not scores:
        return "unknown"
    
    try:
        # Parse set scores
        sets = scores.split(", ")
        home_sets_won = 0
        away_sets_won = 0
        
        for set_score in sets:
            if "-" in set_score:
                home_score, away_score = map(int, set_score.split("-"))
                if home_score > away_score:
                    home_sets_won += 1
                else:
                    away_sets_won += 1
        
        if home_sets_won > away_sets_won:
            return "home"
        elif away_sets_won > home_sets_won:
            return "away"
        else:
            return "tie"
    except:
        return "unknown"


def validate_match_data(match_data):
    """Validate that match data has required fields."""
    required_fields = [
        'Date', 'Home Team', 'Away Team', 
        'Home Player 1', 'Home Player 1 ID', 'Home Player 2', 'Home Player 2 ID',
        'Away Player 1', 'Away Player 1 ID', 'Away Player 2', 'Away Player 2 ID',
        'Scores', 'Winner', 'source_league', 'match_id'
    ]
    
    for field in required_fields:
        if field not in match_data or not match_data[field]:
            print(f"    Missing required field: {field}")
            return False
    
    return True


def parse_date_string(date_str):
    """Parse date string in various formats."""
    date_formats = [
        '%m/%d/%Y',    # MM/DD/YYYY
        '%m-%d-%Y',    # MM-DD-YYYY
        '%B %d, %Y',   # Month DD, YYYY
        '%d-%b-%Y',    # DD-MMM-YYYY
        '%d-%b-%y',    # DD-MMM-YY
        '%m/%d/%y',    # MM/DD/YY
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None





# ChromeManager has been replaced with StealthBrowserManager for fingerprint evasion
# See stealth_browser.py for the new implementation


def clean_player_name(name):
    """Clean player name from HTML artifacts"""
    if not name:
        return ""

    # Remove HTML entities and extra whitespace
    name = re.sub(r"&nbsp;", " ", name)
    name = re.sub(r"\s+", " ", name)
    name = name.strip()

    # Remove common suffixes like "(S)", "(S↑)", etc.
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)

    return name


def split_player_name_for_lookup(full_name):
    """Split player name into first and last name for ID lookup"""
    if not full_name:
        return "", ""

    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    elif len(parts) == 1:
        return parts[0], ""
    return "", ""


def scrape_apta_chicago_standings(driver, url, series_name, league_id):
    """Scrape match data from APTA Chicago standings page with individual match page extraction."""
    matches_data = []
    
    try:
        print(f"🎯 APTA Chicago detected - working directly with standings page")
        print(f"Navigating to URL: {url}")
        driver.get(url)
        time.sleep(2)  # Wait for page to load
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Look for match links directly on the standings page
        print("🔍 Looking for match links on standings page...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        base_url = driver.current_url.split('?')[0]  # Get base URL without query params
        match_links = find_match_links(soup, base_url)
        
        if match_links:
            print(f"🎯 Found {len(match_links)} individual match links with IDs")
            print("📋 Scraping individual match pages for detailed data with match IDs...")
            
            # Scrape each individual match page
            for i, match_link in enumerate(match_links, 1):
                try:
                    print(f"    [{i}/{len(match_links)}] Scraping match {match_link['match_id']}...")
                    individual_matches_data = scrape_individual_match_page(driver, match_link, series_name, league_id)
                    if individual_matches_data:
                        # Add all matches from this page to the main list
                        matches_data.extend(individual_matches_data)
                        print(f"    ✅ Successfully scraped {len(individual_matches_data)} matches from {match_link['match_id']}")
                    else:
                        print(f"    ⚠️ Failed to scrape match {match_link['match_id']}")
                except Exception as e:
                    print(f"    ❌ Error scraping match {match_link['match_id']}: {e}")
            
            print(f"🎯 Completed individual match page scraping: {len(matches_data)} matches with IDs")
            return matches_data
        else:
            print("⚠️ No individual match links found on standings page")
            return []
            
    except Exception as e:
        print(f"❌ Error in APTA Chicago standings scraping: {e}")
        return []


def scrape_matches(driver, url, series_name, league_id, max_retries=3, retry_delay=5):
    """Scrape match data from a single series URL with retries, including individual match pages for match IDs."""
    
    # For APTA Chicago, use the standings page approach
    if league_id == "APTA_CHICAGO":
        return scrape_apta_chicago_standings(driver, url, series_name, league_id)
    
    matches_data = []

    for attempt in range(max_retries):
        try:
            print(f"Navigating to URL: {url} (attempt {attempt + 1}/{max_retries})")
            driver.get(url)
            time.sleep(2)  # Wait for page to load

            # Look for and click the "Matches" link - enhanced for multiple league formats
            print("Looking for Matches link...")
            matches_link = None

            # Try multiple strategies to find the matches link
            try:
                # Strategy 1: Direct "Matches" link (NSTF/APTA format)
                try:
                    matches_link = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.LINK_TEXT, "Matches"))
                    )
                    print("Found 'Matches' link using Strategy 1")
                except TimeoutException:
                    pass

                # Strategy 2: Case-insensitive matches link
                if not matches_link:
                    try:
                        matches_link = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//a[contains(translate(text(), 'MATCHES', 'matches'), 'matches')]",
                                )
                            )
                        )
                        print("Found matches link using Strategy 2 (case-insensitive)")
                    except TimeoutException:
                        pass

                # Strategy 3: Look for "Results" link (CITA might use this)
                if not matches_link:
                    try:
                        matches_link = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.LINK_TEXT, "Results"))
                        )
                        print("Found 'Results' link using Strategy 3")
                    except TimeoutException:
                        pass

                # Strategy 4: Look for "Match Results" or similar
                if not matches_link:
                    try:
                        matches_link = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//a[contains(text(), 'Match') or contains(text(), 'Result')]",
                                )
                            )
                        )
                        print("Found match/result link using Strategy 4")
                    except TimeoutException:
                        pass

                # Strategy 5: Look for any link that might contain match data
                if not matches_link:
                    try:
                        # Look for links with href containing "match" or "result"
                        matches_link = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//a[contains(@href, 'match') or contains(@href, 'result')]",
                                )
                            )
                        )
                        print("Found match/result link using Strategy 5 (href-based)")
                    except TimeoutException:
                        pass

                # Strategy 6: NSTF-specific navigation attempts
                if not matches_link and league_id == "NSTF":
                    try:
                        # For NSTF, try looking for navigation tabs or buttons
                        nstf_navigation_patterns = [
                            "//a[contains(text(), 'Match')]",
                            "//button[contains(text(), 'Match')]",
                            "//div[contains(@class, 'tab') and contains(text(), 'Match')]",
                            "//a[contains(@class, 'nav') and contains(text(), 'Match')]",
                            "//a[contains(text(), 'Result')]",
                            "//button[contains(text(), 'Result')]",
                        ]

                        for pattern in nstf_navigation_patterns:
                            try:
                                matches_link = WebDriverWait(driver, 3).until(
                                    EC.presence_of_element_located((By.XPATH, pattern))
                                )
                                print(
                                    f"Found matches link using NSTF pattern: {pattern}"
                                )
                                break
                            except TimeoutException:
                                continue
                    except Exception as e:
                        print(f"Error in NSTF navigation attempts: {e}")

                # Strategy 7: Try direct URL modification for series overview
                if not matches_link and league_id == "NSTF":
                    try:
                        current_url = driver.current_url
                        print(f"Current URL: {current_url}")

                        # If we're on a team page, try to navigate to series overview
                        if "team=" in current_url:
                            # Extract team ID and try series overview URL
                            team_match = re.search(r"team=([^&]+)", current_url)
                            if team_match:
                                team_id = team_match.group(1)
                                overview_url = f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did={team_id}"
                                print(f"Trying series overview URL: {overview_url}")
                                driver.get(overview_url)
                                time.sleep(3)

                                # Now try to find matches link again
                                try:
                                    matches_link = WebDriverWait(driver, 5).until(
                                        EC.presence_of_element_located(
                                            (By.LINK_TEXT, "Matches")
                                        )
                                    )
                                    print(
                                        "Found matches link after navigating to series overview"
                                    )
                                except TimeoutException:
                                    print(
                                        "Still no matches link found after series overview attempt"
                                    )
                    except Exception as e:
                        print(f"Error in direct URL modification: {e}")

                # If we found a matches link, click it
                if matches_link:
                    print(f"Clicking matches link: {matches_link.text}")
                    matches_link.click()
                    time.sleep(2)  # Wait for navigation
                else:
                    print("Could not find any matches/results link")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print("Max retries reached, could not find matches link")
                        return []

            except Exception as e:
                print(f"Error finding matches link: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print("Max retries reached, could not find matches link")
                    return []

            print("Waiting for match results to load...")
            results_container_found = False

            # Try multiple strategies to find the match results container
            try:
                # Strategy 1: Standard match_results_container (NSTF/APTA format)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.ID, "match_results_container")
                        )
                    )
                    print("Match results loaded successfully using Strategy 1")
                    results_container_found = True
                except TimeoutException:
                    pass

                # Strategy 2: Look for any element with "match" or "result" in the ID
                if not results_container_found:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//*[contains(@id, 'match') or contains(@id, 'result')]",
                                )
                            )
                        )
                        print("Match results loaded successfully using Strategy 2")
                        results_container_found = True
                    except TimeoutException:
                        pass

                # Strategy 3: Look for common table structures
                if not results_container_found:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//table[contains(@class, 'match') or contains(@class, 'result')]",
                                )
                            )
                        )
                        print("Match results loaded successfully using Strategy 3")
                        results_container_found = True
                    except TimeoutException:
                        pass

                # Strategy 4: Wait for any substantial content to load
                if not results_container_found:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, "//div[count(descendant::*) > 10]")
                            )
                        )
                        print("Page content loaded successfully using Strategy 4")
                        results_container_found = True
                    except TimeoutException:
                        pass

                if not results_container_found:
                    print(
                        f"Timeout waiting for match results to load (attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print("Max retries reached, could not load match results")
                        return []

            except Exception as e:
                print(f"Error waiting for match results: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print("Max retries reached, could not load match results")
                    return []

            # Find all match result tables - enhanced for multiple league formats
            match_tables = []

            # Strategy 1: Standard match_results_table class (NSTF/APTA format)
            print(
                "Looking for match tables using Strategy 1: match_results_table class"
            )
            tables_strategy1 = driver.find_elements(
                By.CLASS_NAME, "match_results_table"
            )
            if tables_strategy1:
                match_tables.extend(tables_strategy1)
                print(f"Found {len(tables_strategy1)} tables using Strategy 1")

            # Strategy 2: Look for any table with "match" or "result" in the class name
            if not match_tables:
                print(
                    "Looking for match tables using Strategy 2: match/result class patterns"
                )
                tables_strategy2 = driver.find_elements(
                    By.XPATH,
                    "//table[contains(@class, 'match') or contains(@class, 'result')]",
                )
                if tables_strategy2:
                    match_tables.extend(tables_strategy2)
                    print(f"Found {len(tables_strategy2)} tables using Strategy 2")

            # Strategy 3: Look for div containers that might contain match data
            if not match_tables:
                print("Looking for match tables using Strategy 3: div containers")
                tables_strategy3 = driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'match') or contains(@class, 'result')]",
                )
                if tables_strategy3:
                    match_tables.extend(tables_strategy3)
                    print(f"Found {len(tables_strategy3)} containers using Strategy 3")

            # Strategy 4: Look for any table elements on the page
            if not match_tables:
                print("Looking for match tables using Strategy 4: all table elements")
                all_tables = driver.find_elements(By.TAG_NAME, "table")
                # Filter for tables that likely contain match data
                for table in all_tables:
                    try:
                        # Check if table has substantial content
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        if len(rows) > 2:  # At least header + some data rows
                            match_tables.append(table)
                    except:
                        continue
                if match_tables:
                    print(f"Found {len(match_tables)} tables using Strategy 4")

            # Strategy 5: Look for structured div layouts (General fallback)
            if not match_tables:
                print(
                    "Looking for match tables using Strategy 5: structured div layouts"
                )
                div_containers = driver.find_elements(
                    By.XPATH, "//div[count(./div) > 5]"
                )  # Divs with multiple child divs
                if div_containers:
                    match_tables.extend(div_containers)
                    print(
                        f"Found {len(div_containers)} structured divs using Strategy 6"
                    )

            if not match_tables:
                print("No match tables found with any strategy")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print("Max retries reached, no match tables found")
                    return []

            print(f"Found {len(match_tables)} match tables/containers to process")

            # NEW: Look for individual match links on the page for match ID extraction
            print("🔍 Looking for individual match links to extract match IDs...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            base_url = driver.current_url.split('?')[0]  # Get base URL without query params
            match_links = find_match_links(soup, base_url)
            
            if match_links:
                print(f"🎯 Found {len(match_links)} individual match links with IDs")
                print("📋 Scraping individual match pages for detailed data with match IDs...")
                
                # Scrape each individual match page
                for match_link in match_links:
                    try:
                        individual_match_data = scrape_individual_match_page(driver, match_link, series_name, league_id)
                        if individual_match_data:
                            matches_data.append(individual_match_data)
                            print(f"    ✅ Successfully scraped match {match_link['match_id']}")
                        else:
                            print(f"    ⚠️ Failed to scrape match {match_link['match_id']}")
                    except Exception as e:
                        print(f"    ❌ Error scraping match {match_link['match_id']}: {e}")
                
                print(f"🎯 Completed individual match page scraping: {len(matches_data)} matches with IDs")
                
                # If we successfully scraped individual match pages, skip the table parsing
                if matches_data:
                    break  # Exit the retry loop since we have data
            else:
                print("⚠️ No individual match links found - skipping this series")
                print("   Only matches with legitimate match IDs will be imported")
                print("   This ensures data integrity and best practices")

            # If we successfully processed the page, break the retry loop
            break

        except TimeoutException:
            print(
                f"Timeout waiting for page to load (attempt {attempt + 1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached, could not load page")
                return []
        except Exception as e:
            print(f"Error loading page (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached, could not process page")
                return []

    return matches_data


# Removed load_active_series function - now uses dynamic discovery to process all series


def scrape_all_matches(league_subdomain, series_filter=None, max_retries=3, retry_delay=5):
    """Main function to scrape and save match data from all series."""
    # Record start time
    start_time = datetime.now()
    print(f"🕐 Session Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize timing variables
    discovery_start_time = None
    discovery_duration = None

    try:
        # Load league configuration from user input
        config = get_league_config(league_subdomain)
        league_id = config["league_id"]

        if series_filter and series_filter != "all":
            print(f"🌟 Processing filtered series: {series_filter} from {config['subdomain']}")
            print(f"🔍 Filtering for series containing: '{series_filter}'")
        else:
            print(f"🌟 Processing ALL discovered series from {config['subdomain']} dynamically")
            print("🔍 No filtering - comprehensive discovery and processing of all series")

        # Load players data for Player ID lookups
        players_loaded = load_players_data(league_id)
        if not players_loaded:
            print("⚠️  Warning: Player ID lookups will not be available")

        # Use stealth browser manager to avoid bot detection
        with StealthBrowserManager(headless=True) as driver:
            # Use dynamic base URL from config
            base_url = config["base_url"]
            print(f"🌐 Target League: {league_id} ({config['subdomain']})")
            print(f"🔗 Base URL: {base_url}")

            # Create league-specific directory
            data_dir = build_league_data_dir(league_id)

            print(f"Navigating to URL: {base_url}")
            driver.get(base_url)
            time.sleep(retry_delay)

            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Import comprehensive discovery from players scraper
            series_urls = []
            comprehensive_discovery_success = False

            try:
                # Import the comprehensive discovery function from players scraper
                import os
                import sys

                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from scraper_players import discover_all_leagues_and_series

                print("🔍 Using comprehensive discovery from players scraper...")
                discovery_results = discover_all_leagues_and_series(driver, config)

                # Extract series information from discovery results
                discovered_teams = discovery_results["teams"]
                all_series = discovery_results["series"]

                # Dynamically extract correct series URLs from the main page
                print("🔍 Dynamically discovering series overview URLs...")

                # Parse the main page to find the correct series navigation links
                soup = BeautifulSoup(driver.page_source, "html.parser")
                all_links = soup.find_all("a", href=True)

                for link in all_links:
                    href = link.get("href", "")
                    text = link.text.strip()

                    # Strategy A: APTA Chicago format - numbered series with specific mod
                    if (
                        text.isdigit()
                        or (text.endswith(" SW") and text.replace(" SW", "").isdigit())
                        or text in ["Legends"]
                    ):

                        # Check if this uses the correct mod parameter for series overview (not team pages)
                        if (
                            "mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx" in href
                            and "did=" in href
                        ):
                            full_url = (
                                f"{base_url}{href}"
                                if href.startswith("/")
                                else f"{base_url}/{href}"
                            )

                            # Format series name consistently
                            if text.isdigit():
                                series_name = f"Chicago {text}"
                            elif text.endswith(" SW"):
                                series_name = f"Chicago {text}"
                            elif text == "Legends":
                                series_name = "Chicago Legends"
                            else:
                                series_name = f"Chicago {text}"

                            # Only add if this series was discovered in our comprehensive search
                            if series_name in all_series:
                                series_urls.append((series_name, full_url))
                                print(f"📈 Found series: {series_name}")

                    # Strategy B: NSTF format - try to find series overview pages with different patterns
                    elif config["league_id"] == "NSTF" and (
                        text.startswith("Series ")
                        or text.startswith("S")
                        or text in ["1", "2A", "2B", "3", "A"]
                    ):

                        # For NSTF, try multiple URL patterns that might lead to series overview
                        potential_patterns = [
                            "mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx",  # Standard series overview
                            "mod=nndz-TjJSOWJOR2sxTnhI",  # Alternative series pattern
                            "mod=nndz-TjJqOWtOR2sxTnhI",  # Another alternative
                        ]

                        for pattern in potential_patterns:
                            if pattern in href:
                                full_url = (
                                    f"{base_url}{href}"
                                    if href.startswith("/")
                                    else f"{base_url}/{href}"
                                )

                                # Map text to series name
                                if text.startswith("Series "):
                                    series_name = text
                                elif text.startswith("S"):
                                    series_name = f"Series {text[1:]}"
                                elif text in ["1", "2A", "2B", "3", "A"]:
                                    series_name = f"Series {text}"
                                else:
                                    series_name = text

                                # Only add if this series was discovered
                                if series_name in all_series:
                                    series_urls.append((series_name, full_url))
                                    print(f"📈 Found NSTF series: {series_name}")
                                break

                    # Strategy C: CNSWPL format - look for series links
                    elif config["league_id"] == "CNSWPL" and (
                        text.startswith("Series ")
                        or re.match(r"^Series\s+\d+[a-zA-Z]*$", text)
                    ):

                        # CNSWPL uses specific mod parameters for series pages
                        if (
                            "mod=nndz-TjJiOWtOR3QzTU4yakRrY1NqN1FMcGpx" in href
                            or "mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx" in href
                        ):
                            full_url = (
                                f"{base_url}{href}"
                                if href.startswith("/")
                                else f"{base_url}/{href}"
                            )

                            # Map the text directly as series name
                            series_name = text.strip()

                            # Only add if this series was discovered
                            if series_name in all_series:
                                series_urls.append((series_name, full_url))
                                print(f"📈 Found CNSWPL series: {series_name}")

                    # Strategy D: Generic approach - look for any link that might contain series results
                    elif (
                        any(
                            keyword in text.lower()
                            for keyword in ["result", "match", "score", "standing"]
                        )
                        and len(text) < 50
                    ):
                        # This might be a results/matches page
                        if (
                            "mod=" in href and "team=" not in href
                        ):  # Series level, not team level
                            full_url = (
                                f"{base_url}{href}"
                                if href.startswith("/")
                                else f"{base_url}/{href}"
                            )

                            # Try to match this to one of our discovered series
                            for discovered_series in all_series:
                                if discovered_series.lower() in text.lower() or any(
                                    part in text.lower()
                                    for part in discovered_series.lower().split()
                                ):
                                    series_urls.append((discovered_series, full_url))
                                    print(
                                        f"📈 Found series via generic match: {discovered_series}"
                                    )
                                    break

                if not series_urls:
                    print("⚠️  No series overview URLs found using dynamic discovery")
                    print(
                        "🔍 Falling back to team-based URLs (may not have match results)"
                    )
                    # Fallback to original method if dynamic discovery fails
                    for series_name in sorted(all_series):
                        series_team = None
                        for team_name, team_id in discovered_teams.items():
                            # CNSWPL-specific matching: "Series 12" matches "Tennaqua 12"
                            if config[
                                "league_id"
                            ] == "CNSWPL" and series_name.startswith("Series "):
                                series_number = series_name.replace(
                                    "Series ", ""
                                ).strip()
                                if team_name.endswith(f" {series_number}"):
                                    series_team = team_id
                                    break
                            # Original matching logic for other leagues
                            elif (
                                series_name in team_name
                                or (
                                    series_name.startswith("Chicago ")
                                    and f" - {series_name.split()[1]}" in team_name
                                )
                                or (
                                    series_name.startswith("Series ")
                                    and f" S{series_name.split()[1]}" in team_name
                                )
                            ):
                                series_team = team_id
                                break

                        if series_team:
                            # Try different URL patterns based on league
                            if config["league_id"] == "NSTF":
                                # For NSTF, try multiple mod parameters that might contain series overview/matches
                                nstf_patterns = [
                                    f"/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did={series_team}",  # Series overview
                                    f"/?mod=nndz-TjJSOWJOR2sxTnhI&did={series_team}",  # Alternative overview
                                    f"/?mod=nndz-TjJqOWtOR2sxTnhI&did={series_team}",  # Another alternative
                                    f"/?mod=nndz-TjJiOWtOR2sxTnhI&team={series_team}",  # Team page fallback
                                ]

                                # Try each pattern to see which one works
                                for i, pattern in enumerate(nstf_patterns):
                                    test_url = f"{base_url}{pattern}"
                                    if i < 3:  # First 3 are series overview attempts
                                        series_urls.append((series_name, test_url))
                                        print(
                                            f"📈 Found series (NSTF pattern {i+1}): {series_name}"
                                        )
                                        break  # Only add the first working pattern

                                # If no series overview patterns worked, fall back to team page
                                if not any(
                                    series_name in url[0] for url in series_urls
                                ):
                                    series_url = f"{base_url}/?mod=nndz-TjJiOWtOR2sxTnhI&team={series_team}"
                                    series_urls.append((series_name, series_url))
                                    print(f"📈 Found series (fallback): {series_name}")
                            elif config["league_id"] == "CNSWPL":
                                # For CNSWPL, use specific mod parameters for series pages
                                cnswpl_patterns = [
                                    f"/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did={series_team}",  # Series overview
                                    f"/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NqN1FMcGpx&did={series_team}",  # Alternative mod
                                    f"/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&tid={series_team}",  # Team standings
                                ]

                                # Try each pattern to see which one works
                                for i, pattern in enumerate(cnswpl_patterns):
                                    test_url = f"{base_url}{pattern}"
                                    series_urls.append((series_name, test_url))
                                    print(
                                        f"📈 Found series (CNSWPL pattern {i+1}): {series_name}"
                                    )
                                    break  # Only add the first pattern for now
                            else:
                                # Original fallback for other leagues
                                series_url = f"{base_url}/?mod=nndz-TjJiOWtOR2sxTnhI&team={series_team}"
                                series_urls.append((series_name, series_url))
                                print(f"📈 Found series (fallback): {series_name}")
                else:
                    print(
                        f"✅ Successfully discovered {len(series_urls)} series overview URLs dynamically"
                    )

                print(f"✅ Comprehensive discovery found {len(series_urls)} series")
                comprehensive_discovery_success = True

            except ImportError as e:
                print(f"⚠️  Could not import comprehensive discovery: {e}")
                print("🔍 Falling back to basic discovery strategies...")
                comprehensive_discovery_success = False
            except Exception as e:
                print(f"⚠️  Comprehensive discovery failed: {e}")
                print("🔍 Falling back to basic discovery strategies...")
                comprehensive_discovery_success = False

            # Only run basic discovery strategies if comprehensive discovery failed
            if not comprehensive_discovery_success:
                # Fallback to original basic discovery
                discovery_start_time = datetime.now()
                print(
                    f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}"
                )

                # Strategy 1: NSTF/APTA_CHICAGO format - div_list_option
                print(
                    "🔍 Trying Strategy 1: div_list_option (NSTF/APTA_CHICAGO format)"
                )
                series_elements = soup.find_all("div", class_="div_list_option")

                if series_elements:
                    print(f"✅ Found {len(series_elements)} series using Strategy 1")
                for element in series_elements:
                    try:
                        series_link = element.find("a")
                        if series_link and series_link.text:
                            series_number = series_link.text.strip()

                            # Auto-detect and format series based on content
                            if "Series" in series_number or series_number.startswith(
                                "S"
                            ):
                                # NSTF format: "Series 1", "S1", "S2A", etc.
                                if series_number.startswith("Series "):
                                    formatted_series = (
                                        series_number  # Already properly formatted
                                    )
                                else:
                                    formatted_series = f"Series {series_number}"
                            elif series_number.isdigit():
                                # APTA format: "1", "2", "25", etc. -> "Chicago X"
                                formatted_series = f"Chicago {series_number}"
                            elif "SW" in series_number:
                                # Handle SW series: "23 SW" -> "Chicago 23 SW"
                                formatted_series = f"Chicago {series_number}"
                            else:
                                # Other formats - use as-is
                                formatted_series = series_number

                            series_url = series_link.get("href", "")
                            full_url = f"{base_url}{series_url}" if series_url else ""
                            if full_url:
                                series_urls.append((formatted_series, full_url))
                                print(f"📈 Found series: {formatted_series}")
                                print(f"    URL: {full_url}")
                    except Exception as e:
                        print(f"❌ Error extracting series URL: {str(e)}")

                # Strategy 2: CITA format - look for different patterns
                if not series_urls:
                    print(
                        "🔍 Trying Strategy 2: CITA format - searching for series links"
                    )

                    # Look for any links that might contain series information
                    all_links = soup.find_all("a", href=True)

                    for link in all_links:
                        try:
                            href = link.get("href", "")
                            text = link.text.strip()

                            # Look for patterns that might indicate series
                            if text and (
                                text.replace(" ", "")
                                .replace("&", "")
                                .replace("Under", "")
                                .replace(".", "")
                                .replace("0", "")
                                .isdigit()
                                or "series" in text.lower()
                                or "division" in text.lower()
                                or "level" in text.lower()
                                or "flight" in text.lower()
                                or re.match(
                                    r"^\d+(\.\d+)?\s*(&\s*Under|&\s*Over|Over|Under|\+)?$",
                                    text.replace(" ", ""),
                                )
                                or re.match(
                                    r"^\d+(\.\d+)?\s*(Men|Women|Mixed|Open)?\s*(Doubles?|Singles?)?$",
                                    text,
                                    re.IGNORECASE,
                                )
                            ):

                                # Format the series name
                                if (
                                    text.replace(" ", "")
                                    .replace("&", "")
                                    .replace("Under", "")
                                    .replace(".", "")
                                    .replace("0", "")
                                    .isdigit()
                                ):
                                    # Numeric series like "4.5", "3.5 & Under", etc.
                                    formatted_series = text
                                elif "series" in text.lower():
                                    formatted_series = text
                                else:
                                    # Use the text as-is for other patterns
                                    formatted_series = text

                                full_url = (
                                    f"{base_url}{href}"
                                    if href.startswith("/")
                                    else href
                                )

                                # Filter out library documents and PDFs
                                if (
                                    full_url
                                    and (formatted_series, full_url) not in series_urls
                                    and "library" not in href.lower()
                                    and not href.lower().endswith(".pdf")
                                    and not href.lower().endswith(".doc")
                                    and not href.lower().endswith(".docx")
                                ):
                                    series_urls.append((formatted_series, full_url))
                                    print(f"📈 Found series: {formatted_series}")
                                    print(f"    URL: {full_url}")
                                elif "library" in href.lower() or href.lower().endswith(
                                    (".pdf", ".doc", ".docx")
                                ):
                                    print(
                                        f"⏸️ Skipping library/document: {formatted_series} -> {href}"
                                    )
                        except Exception as e:
                            print(f"❌ Error processing link: {str(e)}")

                    if series_urls:
                        print(f"✅ Found {len(series_urls)} series using Strategy 2")

                # Strategy 3: Generic fallback - look for any structured navigation
                if not series_urls:
                    print(
                        "🔍 Trying Strategy 3: Generic fallback - looking for navigation patterns"
                    )

                    # Look for common navigation patterns
                    nav_patterns = [
                        ("ul", "nav"),
                        ("div", "navigation"),
                        ("div", "menu"),
                        ("div", "list"),
                        ("table", None),
                        ("tbody", None),
                    ]

                    for tag, class_name in nav_patterns:
                        elements = (
                            soup.find_all(tag, class_=class_name)
                            if class_name
                            else soup.find_all(tag)
                        )

                        for element in elements:
                            links = element.find_all("a", href=True)

                            for link in links:
                                try:
                                    href = link.get("href", "")
                                    text = link.text.strip()

                                    # Look for numeric or series-like patterns
                                    if (
                                        text
                                        and len(text) < 50  # Reasonable length
                                        and (
                                            text.replace(" ", "")
                                            .replace("&", "")
                                            .isdigit()
                                            or "series" in text.lower()
                                            or re.match(r"^\d+(\.\d+)?.*$", text)
                                            or re.match(r"^[A-Z]\d+.*$", text)
                                        )
                                    ):

                                        formatted_series = text
                                        full_url = (
                                            f"{base_url}{href}"
                                            if href.startswith("/")
                                            else href
                                        )

                                        if (
                                            full_url
                                            and (formatted_series, full_url)
                                            not in series_urls
                                        ):
                                            series_urls.append(
                                                (formatted_series, full_url)
                                            )
                                            print(
                                                f"📈 Found series: {formatted_series}"
                                            )
                                            print(f"    URL: {full_url}")
                                except Exception as e:
                                    continue

                    if series_urls:
                        print(f"✅ Found {len(series_urls)} series using Strategy 3")

                # Debug: If still no series found, show detailed page structure
                if not series_urls:
                    print(
                        "🔍 No series found with any strategy. Analyzing page structure..."
                    )

                    # Show some debug info about the page structure
                    all_divs = soup.find_all("div")
                    classes_found = set()

                    for div in all_divs[:50]:  # Limit to first 50 for performance
                        if div.get("class"):
                            classes_found.update(div.get("class"))

                    print(f"📊 Found {len(all_divs)} div elements")
                    print(
                        f"📊 Common classes: {list(classes_found)[:20]}"
                    )  # Show first 20 classes

                    # Look for any links with text
                    all_links = soup.find_all("a", href=True)
                    print(f"📊 Found {len(all_links)} total links")

                    # Show all link texts for debugging
                    link_texts = []
                    for link in all_links:
                        text = link.text.strip()
                        href = link.get("href", "")
                        if text and len(text) < 100:  # Reasonable length
                            link_texts.append(f"'{text}' -> {href}")

                    if link_texts:
                        print(f"📊 All links found:")
                        for i, link_text in enumerate(link_texts[:20]):  # Show first 20
                            print(f"  {i+1}. {link_text}")
                        if len(link_texts) > 20:
                            print(f"  ... and {len(link_texts) - 20} more links")

                    # Look for dropdowns, menus, or navigation elements
                    nav_elements = soup.find_all(["nav", "ul", "ol"])
                    print(f"📊 Found {len(nav_elements)} navigation elements")

                    for i, nav in enumerate(nav_elements[:5]):  # Show first 5
                        nav_links = nav.find_all("a")
                        if nav_links:
                            print(f"  Nav {i+1}: {len(nav_links)} links")
                            for link in nav_links[:3]:  # Show first 3 links in each nav
                                print(
                                    f"    - '{link.text.strip()}' -> {link.get('href', '')}"
                                )

                    # Look for form elements or buttons that might trigger navigation
                    forms = soup.find_all("form")
                    buttons = soup.find_all(["button", "input"])
                    selects = soup.find_all("select")

                    print(
                        f"📊 Found {len(forms)} forms, {len(buttons)} buttons/inputs, {len(selects)} select elements"
                    )

                    # Look for JavaScript-loaded content indicators
                    scripts = soup.find_all("script")
                    print(
                        f"📊 Found {len(scripts)} script tags (may indicate dynamic content)"
                    )

                    # Check for common league/series keywords in the page content
                    page_text = soup.get_text().lower()
                    league_keywords = [
                        "series",
                        "division",
                        "level",
                        "flight",
                        "league",
                        "tournament",
                        "bracket",
                        "draw",
                    ]
                    found_keywords = [kw for kw in league_keywords if kw in page_text]
                    if found_keywords:
                        print(f"📊 Found league keywords in page: {found_keywords}")

                    # Try to find any numeric patterns in the page text
                    numeric_patterns = re.findall(r"\b\d+(?:\.\d+)?\b", page_text)
                    unique_numbers = list(set(numeric_patterns))[
                        :10
                    ]  # Get unique numbers, limit to 10
                    if unique_numbers:
                        print(f"📊 Found numeric patterns: {unique_numbers}")

                    # Strategy 6: Try to find series through JavaScript interaction
                    print(
                        "🔍 Trying Strategy 6: JavaScript interaction and dynamic content"
                    )

                    # Wait a bit more for potential JavaScript to load
                    time.sleep(3)

                    # Re-parse the page after waiting
                    updated_soup = BeautifulSoup(driver.page_source, "html.parser")
                    updated_links = updated_soup.find_all("a", href=True)

                    print(f"📊 After waiting: Found {len(updated_links)} links")

                    # Try clicking on potential navigation elements
                    try:
                        # Look for menu toggles or dropdowns
                        menu_toggles = driver.find_elements(
                            By.XPATH,
                            "//button[contains(@class, 'toggle') or contains(@class, 'menu') or contains(@class, 'nav')]",
                        )
                        dropdown_toggles = driver.find_elements(
                            By.XPATH,
                            "//a[contains(@class, 'dropdown') or contains(@data-toggle, 'dropdown')]",
                        )

                        for toggle in menu_toggles + dropdown_toggles:
                            try:
                                print(
                                    f"📋 Clicking potential menu toggle: {toggle.text.strip()}"
                                )
                                toggle.click()
                                time.sleep(2)

                                # Re-check for series after clicking
                                updated_soup = BeautifulSoup(
                                    driver.page_source, "html.parser"
                                )
                                new_links = updated_soup.find_all("a", href=True)

                                for link in new_links:
                                    text = link.text.strip()
                                    href = link.get("href", "")

                                    # Check if this looks like a series link
                                    if text and (
                                        re.match(r"^\d+(\.\d+)?", text)
                                        or "series" in text.lower()
                                        or "division" in text.lower()
                                        or "level" in text.lower()
                                    ):

                                        formatted_series = text
                                        full_url = (
                                            f"{base_url}{href}"
                                            if href.startswith("/")
                                            else href
                                        )

                                        if (
                                            formatted_series,
                                            full_url,
                                        ) not in series_urls:
                                            series_urls.append(
                                                (formatted_series, full_url)
                                            )
                                            print(
                                                f"📈 Found series after menu interaction: {formatted_series}"
                                            )
                                            print(f"    URL: {full_url}")

                                if series_urls:
                                    break

                            except Exception as e:
                                print(f"📋 Error clicking toggle: {e}")
                                continue

                    except Exception as e:
                        print(f"📋 Error with JavaScript interaction: {e}")

                    if series_urls:
                        print(
                            f"✅ Found {len(series_urls)} series using Strategy 6 (JavaScript interaction)"
                        )

                discovery_end_time = datetime.now()
                discovery_duration = discovery_end_time - discovery_start_time
                print(
                    f"✅ Discovery Phase Complete: {discovery_duration.total_seconds():.1f} seconds"
                )
                print(f"📊 Discovered {len(series_urls)} series total")

            # Common processing regardless of discovery method
            if not series_urls:
                print("❌ No series found!")
                return

            # Sort series by number for organized processing
            def sort_key(item):
                # Extract number from series name
                try:
                    series_name = item[0]

                    # APTA_CHICAGO format: "Chicago 1", "Chicago 25", etc.
                    if "Chicago" in series_name:
                        num = float(
                            series_name.split()[1]
                        )  # Get the number after "Chicago "

                    # NSTF format: "Series 1", "Series 2A", etc.
                    elif "Series" in series_name:
                        parts = series_name.split()[1:]
                        if parts:
                            # Extract numeric part
                            match = re.search(r"(\d+)", parts[0])
                            if match:
                                num = float(match.group(1))
                            else:
                                num = float("inf")
                        else:
                            num = float("inf")

                    # CITA format: "4.5", "3.5 & Under", "5.0 Open", etc.
                    elif re.match(r"^\d+(\.\d+)?", series_name):
                        # Extract the numeric part at the beginning
                        match = re.match(r"^(\d+(?:\.\d+)?)", series_name)
                        if match:
                            num = float(match.group(1))
                        else:
                            num = float("inf")

                    # Numeric series: "1", "2", "25", etc.
                    elif (
                        series_name.replace(" ", "")
                        .replace("&", "")
                        .replace("Under", "")
                        .replace(".", "")
                        .replace("0", "")
                        .isdigit()
                    ):
                        # Try to extract just the numeric part
                        numeric_part = re.search(r"(\d+(?:\.\d+)?)", series_name)
                        if numeric_part:
                            num = float(numeric_part.group(1))
                        else:
                            num = float("inf")

                    # Fallback: try to find any number in the series name
                    else:
                        numeric_match = re.search(r"(\d+(?:\.\d+)?)", series_name)
                        if numeric_match:
                            num = float(numeric_match.group(1))
                        else:
                            num = float("inf")

                    return (num, True)
                except (IndexError, ValueError):
                    return (float("inf"), False)

            series_urls.sort(key=sort_key)

            # Apply series filtering if specified
            original_count = len(series_urls)
            if series_filter and series_filter != "all":
                print(f"\n🔍 Applying series filter: '{series_filter}'")
                print(f"📊 Before filtering: {original_count} series found")
                
                filtered_series = []
                for series_name, series_url in series_urls:
                    # Check if the series filter matches the series name
                    if series_filter.lower() in series_name.lower():
                        filtered_series.append((series_name, series_url))
                        print(f"  ✅ Included: {series_name}")
                    else:
                        print(f"  ❌ Excluded: {series_name}")
                
                series_urls = filtered_series
                print(f"📊 After filtering: {len(series_urls)} series to process")
                
                if not series_urls:
                    print(f"⚠️ No series found matching filter '{series_filter}'")
                    print("Available series were:")
                    for series_name, _ in filtered_series:
                        print(f"  • {series_name}")
                    return
            else:
                print(f"📊 Processing all {original_count} discovered series")

            # Initialize tracking
            all_matches = []
            total_matches = 0
            scraping_start_time = datetime.now()
            print(
                f"\n⚡ Scraping Phase Start: {scraping_start_time.strftime('%H:%M:%S')}"
            )
            print(f"📋 Processing {len(series_urls)} series...")

            # Process each series
            for series_num, (series_number, series_url) in enumerate(series_urls, 1):
                series_start_time = datetime.now()
                progress_percent = (series_num / len(series_urls)) * 100
                elapsed = series_start_time - start_time

                print(
                    f"\n=== Series {series_num}/{len(series_urls)} ({progress_percent:.1f}%) | Elapsed: {elapsed} ==="
                )
                print(f"🏆 Processing: {series_number}")

                matches = scrape_matches(
                    driver,
                    series_url,
                    series_number,
                    league_id,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                )

                series_end_time = datetime.now()
                series_duration = series_end_time - series_start_time

                if not matches:
                    print(f"⚠️  No matches found for series {series_number}")
                else:
                    # Add matches directly to the flat array
                    all_matches.extend(matches)
                    total_matches += len(matches)
                    print(
                        f"✅ Series completed in {series_duration.total_seconds():.1f}s | Found {len(matches)} matches"
                    )

                # Progress update with ETA
                remaining_series = len(series_urls) - series_num
                avg_time_per_series = (
                    (series_start_time - scraping_start_time).total_seconds()
                    / series_num
                    if series_num > 0
                    else 0
                )
                estimated_remaining = (
                    remaining_series * avg_time_per_series
                    if avg_time_per_series > 0
                    else 0
                )
                eta = (
                    series_end_time + timedelta(seconds=estimated_remaining)
                    if estimated_remaining > 0
                    else None
                )

                print(
                    f"📊 Progress: {series_num}/{len(series_urls)} series, {total_matches} total matches"
                )
                if eta:
                    print(
                        f"⏰ ETA: {eta.strftime('%H:%M:%S')} (est. {estimated_remaining/60:.1f} min remaining)"
                    )

                time.sleep(retry_delay)  # Add delay between series

            # Save all matches to league-specific JSON file
            json_filename = "match_history.json"
            json_path = os.path.join(data_dir, json_filename)

            # Load existing data if it exists
            existing_matches = []
            existing_league_ids = set()

            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as jsonfile:
                        existing_matches = json.load(jsonfile)
                        # Extract league IDs from existing data
                        for match in existing_matches:
                            if "league_id" in match:
                                existing_league_ids.add(match["league_id"])
                    print(f"Found existing data with {len(existing_matches)} matches")
                    print(f"Existing league IDs: {existing_league_ids}")
                except Exception as e:
                    print(f"Error loading existing data: {str(e)}")
                    existing_matches = []
                    existing_league_ids = set()

            # Deduplicate matches before saving to prevent duplication issues
            unique_matches, duplicates_removed, dedup_stats = deduplicate_matches(all_matches)
            
            # Save deduplicated matches (always overwrite for current league)
            with open(json_path, "w", encoding="utf-8") as jsonfile:
                json.dump(unique_matches, jsonfile, indent=2)

            # For CNSWPL league, automatically fix player IDs after saving matches
            if league_id == "CNSWPL" and total_matches > 0:
                print(f"\n🔧 Auto-fixing CNSWPL player IDs...")
                try:
                    # Import the fix function - use absolute path approach
                    import os
                    import sys

                    # Get the project root directory (rally/)
                    current_file = os.path.abspath(
                        __file__
                    )  # data/etl/scrapers/scraper_match_scores.py
                    scrapers_dir = os.path.dirname(current_file)  # data/etl/scrapers/
                    etl_dir = os.path.dirname(scrapers_dir)  # data/etl/
                    data_dir_parent = os.path.dirname(etl_dir)  # data/
                    project_root = os.path.dirname(data_dir_parent)  # rally/
                    scripts_dir = os.path.join(project_root, "scripts")

                    # Add the scripts directory to Python path
                    if scripts_dir not in sys.path:
                        sys.path.insert(0, scripts_dir)

                    from fix_cnswpl_match_player_ids import fix_cnswpl_match_player_ids

                    # Run the fix with minimal output
                    fix_stats = fix_cnswpl_match_player_ids(
                        league_data_dir=data_dir, verbose=False
                    )

                    if fix_stats and isinstance(fix_stats, dict):
                        fixed_count = fix_stats.get("fixed_players", 0)
                        null_count = fix_stats.get("still_null", 0)
                        if fixed_count > 0:
                            print(f"✅ Auto-fixed {fixed_count} player IDs")
                        if null_count > 0:
                            print(
                                f"⚠️  {null_count} player IDs still null (may need manual review)"
                            )
                    else:
                        print(f"⚠️  Player ID auto-fix encountered an issue")

                except Exception as e:
                    print(f"⚠️  Could not auto-fix player IDs: {str(e)}")
                    print(
                        "💡 You can manually run: python scripts/fix_cnswpl_match_player_ids.py"
                    )

            # Calculate final timing
            end_time = datetime.now()
            total_duration = end_time - start_time
            scraping_duration = (
                end_time - scraping_start_time
                if scraping_start_time
                else total_duration
            )

            print(f"\n🎉 SCRAPING COMPLETE!")
            print("=" * 70)

            # Detailed timing summary
            print(f"📅 SESSION SUMMARY - {end_time.strftime('%Y-%m-%d')}")
            print(f"🕐 Session Start:     {start_time.strftime('%H:%M:%S')}")
            if discovery_start_time and discovery_duration:
                print(
                    f"🔍 Discovery Start:   {discovery_start_time.strftime('%H:%M:%S')} (Duration: {discovery_duration.total_seconds():.1f}s)"
                )
            if scraping_start_time:
                print(
                    f"⚡ Scraping Start:    {scraping_start_time.strftime('%H:%M:%S')} (Duration: {scraping_duration.total_seconds():.1f}s)"
                )
            print(f"🏁 Session End:       {end_time.strftime('%H:%M:%S')}")
            print(f"⏱️  TOTAL DURATION:    {total_duration}")
            print()

            # Performance metrics
            total_seconds = total_duration.total_seconds()
            series_per_minute = (
                (len(series_urls) / total_seconds * 60) if total_seconds > 0 else 0
            )
            matches_per_minute = (
                (total_matches / total_seconds * 60) if total_seconds > 0 else 0
            )

            print(f"📊 PERFORMANCE METRICS")
            print(f"🏆 Total series processed: {len(series_urls)}")
            print(f"📈 Total matches scraped: {total_matches}")
            if duplicates_removed > 0:
                print(f"🔍 Duplicates removed: {duplicates_removed}")
                if dedup_stats["exact_duplicates"] > 0:
                    print(f"   - {dedup_stats['exact_duplicates']} exact duplicates")
                if dedup_stats["match_id_duplicates"] > 0:
                    print(f"   - {dedup_stats['match_id_duplicates']} match_id duplicates")
                print(f"📈 Final unique matches: {len(unique_matches)}")
            print(f"📈 Series per minute: {series_per_minute:.1f}")
            print(f"⚡ Matches per minute: {matches_per_minute:.1f}")
            print(
                f"⚡ Average time per series: {total_seconds/len(series_urls):.1f}s"
                if len(series_urls) > 0
                else "⚡ Average time per series: N/A"
            )
            print(
                f"⚡ Average time per match: {total_seconds/total_matches:.1f}s"
                if total_matches > 0
                else "⚡ Average time per match: N/A"
            )
            print()

            print(f"💾 Data saved to: {json_path}")
            print(f"🌐 League: {league_id} ({config['subdomain']})")
            if league_id == "CNSWPL":
                print(f"🔧 CNSWPL Player IDs automatically processed")
            print("=" * 70)

    except Exception as e:
        error_time = datetime.now()
        elapsed_time = error_time - start_time
        print(f"\n❌ ERROR OCCURRED!")
        print("=" * 50)
        print(f"🕐 Session Start: {start_time.strftime('%H:%M:%S')}")
        print(f"❌ Error Time:    {error_time.strftime('%H:%M:%S')}")
        print(f"⏱️  Elapsed Time:  {elapsed_time}")
        print(f"🚨 Error Details: {str(e)}")
        print("=" * 50)
        import traceback

        traceback.print_exc()


# Removed load_league_id function - now uses dynamic user input

if __name__ == "__main__":
    import sys

    print("🔍 Dynamically discovering ALL series from any TennisScores website")
    print("📊 No more hardcoded values - everything is discovered automatically!")
    print()

    # Check if league was provided as command line argument
    if len(sys.argv) > 1:
        league_subdomain = sys.argv[1].strip().lower()
        print(f"📋 Using league from command line: {league_subdomain}")
    else:
        # Get league input from user interactively
        print("Available league options:")
        print("  • aptachicago - APTA Chicago league")
        print("  • nstf - NSTF league")
        print("  • cita - CITA league")
        print("  • cnswpl - CNSWPL league")
        print("  • all - Process all known leagues")
        print()
        league_subdomain = (
            input("Enter league subdomain (e.g., 'aptachicago', 'nstf', 'all'): ")
            .strip()
            .lower()
        )

    # Strip quotes if they were included in the input
    league_subdomain = league_subdomain.strip('"').strip("'")

    if not league_subdomain:
        print("❌ No league subdomain provided. Exiting.")
        exit(1)

    # Get series filter input from user
    series_filter = None
    if league_subdomain != "all":
        print()
        print("Series filtering options:")
        print("  • Enter a number (e.g., '22') to scrape only series containing that number")
        print("  • Enter 'all' to scrape all series for the selected league")
        print("  • Examples: '22' for Chicago 22, '2A' for Series 2A, etc.")
        print()
        series_input = input("Enter series filter (number or 'all'): ").strip()
        
        if series_input and series_input.lower() != "all":
            series_filter = series_input
            print(f"🎯 Will filter for series containing: '{series_filter}'")
        else:
            series_filter = "all"
            print("🌟 Will process all series for the selected league")

    # Handle 'all' option to process multiple leagues
    if league_subdomain == "all":
        known_leagues = ["aptachicago", "nstf", "cita", "cnswpl"]
        print(f"🌟 Processing all known leagues: {', '.join(known_leagues)}")

        for league in known_leagues:
            print(f"\n{'='*60}")
            print(f"🏆 PROCESSING LEAGUE: {league.upper()}")
            print(f"{'='*60}")

            try:
                scrape_all_matches(league, "all")  # Process all series for each league
                print(f"✅ Successfully completed {league}")
            except Exception as e:
                print(f"❌ Error processing {league}: {str(e)}")
                continue

        print(f"\n🎉 All leagues processing complete!")
    else:
        # Process single league
        target_url = f"https://{league_subdomain}.tenniscores.com"
        print(f"🌐 Target URL: {target_url}")
        print()

        scrape_all_matches(league_subdomain, series_filter)
