import json
import os
import re
import time
import random
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
    Remove duplicate matches using multiple strategies for maximum data quality.
    
    Args:
        matches (list): List of match dictionaries
        
    Returns:
        tuple: (unique_matches, duplicates_removed, stats)
    """
    if not matches:
        return [], 0, {"exact_duplicates": 0, "match_id_duplicates": 0, "similar_duplicates": 0}
    
    print(f"🔍 Deduplicating {len(matches)} matches...")
    
    # Strategy 1: Exact duplicates (complete JSON match)
    exact_duplicates = 0
    unique_matches = []
    seen_exact = set()
    
    for match in matches:
        # Create a normalized representation for exact matching
        match_key = json.dumps(match, sort_keys=True, default=str)
        if match_key not in seen_exact:
            seen_exact.add(match_key)
            unique_matches.append(match)
        else:
            exact_duplicates += 1
    
    print(f"   - {exact_duplicates} exact duplicates removed")
    
    # Strategy 2: Match ID duplicates (same match_id, keep first occurrence)
    match_id_duplicates = 0
    seen_match_ids = set()
    final_matches = []
    
    for match in unique_matches:
        match_id = match.get('match_id')
        if match_id:
            if match_id not in seen_match_ids:
                seen_match_ids.add(match_id)
                final_matches.append(match)
            else:
                match_id_duplicates += 1
        else:
            # If no match_id, keep the match
            final_matches.append(match)
    
    print(f"   - {match_id_duplicates} match_id duplicates removed")
    
    # Strategy 3: Similar matches (same teams, date, and score)
    similar_duplicates = 0
    seen_similar = set()
    final_unique_matches = []
    
    for match in final_matches:
        # Create a similarity key based on core match data
        home_team = match.get('home_team', '').strip().lower()
        away_team = match.get('away_team', '').strip().lower()
        match_date = match.get('match_date', '')
        home_score = match.get('home_score', '')
        away_score = match.get('away_score', '')
        
        if home_team and away_team and match_date:
            # Create similarity key (teams + date + score)
            similarity_key = f"{home_team}|{away_team}|{match_date}|{home_score}|{away_score}"
            
            if similarity_key not in seen_similar:
                seen_similar.add(similarity_key)
                final_unique_matches.append(match)
            else:
                similar_duplicates += 1
        else:
            # If missing core data, keep the match
            final_unique_matches.append(match)
    
    print(f"   - {similar_duplicates} similar duplicates removed")
    
    # Calculate total duplicates removed
    total_duplicates = exact_duplicates + match_id_duplicates + similar_duplicates
    
    # Quality validation
    quality_issues = []
    for match in final_unique_matches:
        # Check for required fields
        required_fields = ['home_team', 'away_team', 'match_date']
        missing_fields = [field for field in required_fields if not match.get(field)]
        if missing_fields:
            quality_issues.append(f"Match missing fields: {missing_fields}")
        
        # Check for valid scores
        home_score = match.get('home_score', '')
        away_score = match.get('away_score', '')
        if not home_score or not away_score:
            quality_issues.append("Match missing scores")
    
    if quality_issues:
        print(f"⚠️  Quality issues detected: {len(quality_issues)} matches with missing data")
    
    stats = {
        "exact_duplicates": exact_duplicates,
        "match_id_duplicates": match_id_duplicates,
        "similar_duplicates": similar_duplicates,
        "total_duplicates": total_duplicates,
        "quality_issues": len(quality_issues),
        "final_count": len(final_unique_matches)
    }
    
    print(f"✅ Removed {total_duplicates} duplicates:")
    print(f"   - {exact_duplicates} exact duplicates")
    print(f"   - {match_id_duplicates} match_id duplicates")
    print(f"   - {similar_duplicates} similar duplicates")
    print(f"📊 Final unique matches: {len(final_unique_matches)}")
    
    return final_unique_matches, total_duplicates, stats


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
        
        # Also look for the direct format without URL encoding
        if not match_link_elements:
            match_link_elements = soup.find_all('a', href=re.compile(r'print_match\.php\?sch='))
        
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
    
    print(f"    Scraping individual match: {match_url}")
    
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
        print(f"      🏠 Home Team: {home_team}")
        print(f"      🚌 Away Team: {away_team}")
        
        # Extract individual line scores with set details
        line_scores = extract_line_scores_from_page(soup)
        
        if not line_scores:
            print(f"    Warning: No line scores found for match {match_url}")
            return []
        
        print(f"      📊 Found {len(line_scores)} lines to process")
        
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
                
                # Show detailed line information
                home_p1 = match_data.get('Home Player 1', 'Unknown')
                home_p2 = match_data.get('Home Player 2', 'Unknown')
                away_p1 = match_data.get('Away Player 1', 'Unknown')
                away_p2 = match_data.get('Away Player 2', 'Unknown')
                scores = match_data.get('Scores', 'No scores')
                winner = match_data.get('Winner', 'Unknown')
                
                print(f"    ✅ Line {line_number}: {home_p1}/{home_p2} vs {away_p1}/{away_p2} - {scores} (Winner: {winner})")
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
            # Series can be "7", "7 SW", "22", etc.
            match = re.search(r'(.+?)\s*-\s*[\w\s]+\s*@\s*(.+?)\s*-\s*[\w\s]+', header_text)
            if match:
                away_team_raw = match.group(1).strip()  # Team1 is away (visiting)
                home_team_raw = match.group(2).strip()  # Team2 is home (after @)
                
                # Extract series identifier from series_name (e.g., "Chicago 22" -> "22", "Chicago 7 SW" -> "7 SW")
                series_identifier = ""
                if series_name:
                    # Extract the series part after "Chicago " (e.g., "22", "7 SW")
                    series_match = re.search(r'Chicago\s+(.+)$', series_name)
                    if series_match:
                        series_identifier = series_match.group(1).strip()
                    else:
                        # Fallback: try to extract just the number
                        series_match = re.search(r'(\d+(?:\s+[A-Z]+)?)', series_name)
                        if series_match:
                            series_identifier = series_match.group(1).strip()
                
                # Add series identifier to team names with proper formatting (Team - Series)
                if series_identifier:
                    home_team = f"{home_team_raw} - {series_identifier}"
                    away_team = f"{away_team_raw} - {series_identifier}"
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
    # Required fields (must be present for a valid match)
    required_fields = [
        'Date', 'Home Team', 'Away Team', 'Scores', 'Winner', 'source_league', 'match_id'
    ]
    
    # Optional fields (player names can be missing for substitutes/incomplete data)
    optional_fields = [
        'Home Player 1', 'Home Player 1 ID', 'Home Player 2', 'Home Player 2 ID',
        'Away Player 1', 'Away Player 1 ID', 'Away Player 2', 'Away Player 2 ID'
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in match_data or not match_data[field]:
            print(f"    Missing required field: {field}")
            return False
    
    # Check optional fields and provide warnings
    missing_optional = []
    for field in optional_fields:
        if field not in match_data or not match_data[field]:
            missing_optional.append(field)
    
    if missing_optional:
        print(f"    ⚠️ Missing optional fields (player data): {', '.join(missing_optional)}")
        # Don't fail validation for missing player names - just warn
    
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
        
        # FIXED: Use the series URL that was passed in (not hardcoded)
        print(f"🎯 Navigating to series standings page: {url}")
        driver.get(url)
        time.sleep(3)  # Wait for page to load
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Now look for match links on the standings page
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
                    # Calculate match progress percentage
                    match_progress_percent = (i / len(match_links)) * 100
                    print(f"    [{i}/{len(match_links)}] ({match_progress_percent:.1f}%) Scraping match {match_link['match_id']}...")
                    individual_matches_data = scrape_individual_match_page(driver, match_link, series_name, league_id)
                    if individual_matches_data:
                        # Add all matches from this page to the main list
                        matches_data.extend(individual_matches_data)
                        
                        # Show detailed match information
                        for match in individual_matches_data:
                            home_team = match.get('Home Team', 'Unknown')
                            away_team = match.get('Away Team', 'Unknown')
                            line = match.get('Line', 'Unknown')
                            date = match.get('Date', 'Unknown')
                            print(f"      📋 {line}: {home_team} vs {away_team} ({date})")
                        
                        print(f"    ✅ Successfully scraped {len(individual_matches_data)} matches from {match_link['full_url']}")
                    else:
                        print(f"    ⚠️ Failed to scrape match {match_link['full_url']}")
                except Exception as e:
                    print(f"    ❌ Error scraping match {match_link['full_url']}: {e}")
            
            print(f"🎯 Completed individual match page scraping: {len(matches_data)} matches with IDs")
            return matches_data
        else:
            print("⚠️ No individual match links found on standings page")
            return []
            
    except Exception as e:
        print(f"❌ Error in APTA Chicago standings scraping: {e}")
        return []


def extract_matches_from_table(table, series_name, league_id):
    """Extract matches from a table element."""
    # This is a placeholder - in a real implementation, this would parse table data
    # For now, return empty list to avoid errors
    return []


def extract_matches_from_link(link, series_name, league_id):
    """Extract matches from a link element."""
    # This is a placeholder - in a real implementation, this would parse link data
    # For now, return empty list to avoid errors
    return []


def extract_matches_from_element(element, series_name, league_id):
    """Extract matches from a generic element."""
    # This is a placeholder - in a real implementation, this would parse element data
    # For now, return empty list to avoid errors
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
            
            # Enhanced stealth-preserving retry logic
            try:
                driver.get(url)
                time.sleep(2)  # Wait for page to load
            except Exception as nav_error:
                if "timeout" in str(nav_error).lower() or "connection" in str(nav_error).lower():
                    print(f"⚠️ Connection timeout detected (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        # Exponential backoff with stealth-preserving delays
                        backoff_time = retry_delay * (2 ** attempt) + random.uniform(1, 3)
                        print(f"🔄 Retrying in {backoff_time:.1f} seconds (stealth delay)...")
                        time.sleep(backoff_time)
                        continue
                    else:
                        print("❌ Max retries reached for connection timeout")
                        return []
                else:
                    raise nav_error

            # Look for and click the "Matches" link - enhanced for multiple league formats
            print("Looking for Matches link...")
            matches_link = None

            # Try multiple strategies to find the matches link
            try:
                # Strategy 1: Look for exact "Matches" text
                matches_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Matches"))
                )
                print("✅ Found 'Matches' link (Strategy 1)")
            except TimeoutException:
                try:
                    # Strategy 2: Look for partial text match
                    matches_link = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Matches"))
                    )
                    print("✅ Found 'Matches' link (Strategy 2)")
                except TimeoutException:
                    try:
                        # Strategy 3: Look for any link containing "match" (case insensitive)
                        matches_links = driver.find_elements(By.TAG_NAME, "a")
                        for link in matches_links:
                            if link.text.lower().find("match") != -1:
                                matches_link = link
                                print(f"✅ Found matches link: '{link.text}' (Strategy 3)")
                                break
                    except Exception:
                        pass

            if matches_link:
                try:
                    # Scroll to element and click with stealth delay
                    driver.execute_script("arguments[0].scrollIntoView(true);", matches_link)
                    time.sleep(random.uniform(0.5, 1.5))  # Random stealth delay
                    matches_link.click()
                    print("✅ Clicked on Matches link")
                    time.sleep(3)  # Wait for page to load
                except Exception as click_error:
                    print(f"⚠️ Error clicking matches link: {click_error}")
                    # Try JavaScript click as fallback
                    try:
                        driver.execute_script("arguments[0].click();", matches_link)
                        print("✅ Used JavaScript click fallback")
                        time.sleep(3)
                    except Exception as js_error:
                        print(f"❌ JavaScript click also failed: {js_error}")
                        return []
            else:
                print("⚠️ No matches link found, trying to scrape current page...")

            # Parse the page content
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # Look for match data in various formats
            matches_found = False
            
            # Strategy 1: Look for match tables
            match_tables = soup.find_all("table", class_=re.compile(r"match|score", re.I))
            if match_tables:
                print(f"Found {len(match_tables)} potential match tables")
                for table in match_tables:
                    table_matches = extract_matches_from_table(table, series_name, league_id)
                    if table_matches:
                        matches_data.extend(table_matches)
                        matches_found = True
                        print(f"✅ Extracted {len(table_matches)} matches from table")

            # Strategy 2: Look for match links
            if not matches_found:
                match_links = soup.find_all("a", href=re.compile(r"match|score", re.I))
                if match_links:
                    print(f"Found {len(match_links)} potential match links")
                    for link in match_links:
                        link_matches = extract_matches_from_link(link, series_name, league_id)
                        if link_matches:
                            matches_data.extend(link_matches)
                            matches_found = True

            # Strategy 3: Look for any structured data
            if not matches_found:
                # Look for any divs or spans that might contain match information
                match_elements = soup.find_all(["div", "span"], class_=re.compile(r"match|score|result", re.I))
                if match_elements:
                    print(f"Found {len(match_elements)} potential match elements")
                    for element in match_elements:
                        element_matches = extract_matches_from_element(element, series_name, league_id)
                        if element_matches:
                            matches_data.extend(element_matches)
                            matches_found = True

            if matches_found:
                print(f"✅ Successfully extracted {len(matches_data)} matches from {series_name}")
                break  # Success, exit retry loop
            else:
                print(f"⚠️ No matches found on page for {series_name}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Max retries reached, no matches found")
                    return []

        except TimeoutException:
            print(
                f"Timeout waiting for page to load (attempt {attempt + 1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                # Enhanced backoff for timeouts
                backoff_time = retry_delay * (2 ** attempt) + random.uniform(2, 5)
                print(f"🔄 Retrying in {backoff_time:.1f} seconds...")
                time.sleep(backoff_time)
            else:
                print("Max retries reached, could not load page")
                return []
        except Exception as e:
            print(f"Error loading page (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                # Enhanced backoff for general errors
                backoff_time = retry_delay * (2 ** attempt) + random.uniform(1, 3)
                print(f"🔄 Retrying in {backoff_time:.1f} seconds...")
                time.sleep(backoff_time)
            else:
                print("Max retries reached, could not process page")
                return []

    return matches_data


# Removed load_active_series function - now uses dynamic discovery to process all series

def save_progress(league_id, series_urls, completed_series, all_matches, data_dir):
    """
    Save scraping progress to allow recovery from failures.
    
    Args:
        league_id (str): League identifier
        series_urls (list): List of series URLs to process
        completed_series (list): List of completed series names
        all_matches (list): All matches scraped so far
        data_dir (str): Data directory path
    """
    progress_data = {
        "league_id": league_id,
        "timestamp": datetime.now().isoformat(),
        "total_series": len(series_urls),
        "completed_series": completed_series,
        "remaining_series": [s["name"] for s in series_urls if s["name"] not in completed_series],
        "matches_count": len(all_matches),
        "series_urls": series_urls
    }
    
    progress_file = os.path.join(data_dir, "scraping_progress.json")
    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress_data, f, indent=2)
        print(f"💾 Progress saved: {len(completed_series)}/{len(series_urls)} series completed")
    except Exception as e:
        print(f"⚠️ Could not save progress: {e}")


def load_progress(league_id, data_dir):
    """
    Load previous scraping progress if available.
    
    Args:
        league_id (str): League identifier
        data_dir (str): Data directory path
        
    Returns:
        tuple: (series_urls, completed_series, all_matches) or (None, None, None) if no progress
    """
    progress_file = os.path.join(data_dir, "scraping_progress.json")
    
    if not os.path.exists(progress_file):
        return None, None, None
    
    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            progress_data = json.load(f)
        
        # Check if this is recent progress (within last 24 hours)
        timestamp = datetime.fromisoformat(progress_data["timestamp"])
        if datetime.now() - timestamp > timedelta(hours=24):
            print("⚠️ Progress file is older than 24 hours, starting fresh")
            return None, None, None
        
        # Check if it's for the same league
        if progress_data.get("league_id") != league_id:
            print("⚠️ Progress file is for different league, starting fresh")
            return None, None, None
        
        series_urls = progress_data.get("series_urls", [])
        completed_series = progress_data.get("completed_series", [])
        
        # Load existing matches if available
        all_matches = []
        match_file = os.path.join(data_dir, "match_history.json")
        if os.path.exists(match_file):
            try:
                with open(match_file, "r", encoding="utf-8") as f:
                    all_matches = json.load(f)
                print(f"📊 Loaded {len(all_matches)} existing matches")
            except Exception as e:
                print(f"⚠️ Could not load existing matches: {e}")
        
        print(f"🔄 Resuming from progress: {len(completed_series)}/{len(series_urls)} series completed")
        return series_urls, completed_series, all_matches
        
    except Exception as e:
        print(f"⚠️ Could not load progress: {e}")
        return None, None, None


def cleanup_progress(data_dir):
    """
    Clean up progress file after successful completion.
    
    Args:
        data_dir (str): Data directory path
    """
    progress_file = os.path.join(data_dir, "scraping_progress.json")
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
            print("🧹 Progress file cleaned up")
    except Exception as e:
        print(f"⚠️ Could not cleanup progress file: {e}")


def scrape_all_matches(league_subdomain, series_filter=None, max_retries=3, retry_delay=5):
    """
    Scrape all matches from a league with enhanced stealth and session management.
    
    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
        series_filter (str, optional): Specific series to scrape. Can be:
            - Single series: '22' for Chicago 22
            - Multiple series: '19,22,24SW' for multiple series
            - All series: 'all' or None
        max_retries (int): Maximum retry attempts per series
        retry_delay (int): Base delay between retries
    
    Returns:
        list: List of all scraped matches
    """
    
    # Get league configuration
    config = get_league_config(league_subdomain)
    league_id = config["league_id"]

    print(f"🎾 Starting comprehensive match scraping for {league_id}")
    print(f"🔧 Stealth mode: ENABLED (prioritizing undetection)")
    print(f"📊 Data quality: MAXIMUM (ensuring completeness)")
    print(f"⏱️ Performance: SECONDARY (stealth over speed)")
    print("=" * 80)

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

        # FIXED: Discover all series and scrape ONE standings page per series
        print("🎯 FIXED: Discovering all series to scrape ONE standings page per series")
        print("📊 Each standings page contains ALL matches for that series - no duplicates!")
        
        # For APTA Chicago, discover all series from the main page
        if league_id == "APTA_CHICAGO":
            print("🎯 APTA Chicago: Discovering all series...")
            
            # Look for series links on the main page
            series_links = []
            
            # Find all links that contain series numbers
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for series links (they contain mod= and did= parameters)
                if 'mod=' in href and 'did=' in href:
                    # Extract series name from the link text or href
                    series_name = text if text else f"Series {len(series_links) + 1}"
                    series_url = urljoin(base_url, href)
                    series_links.append({
                        'name': series_name,
                        'url': series_url,
                        'href': href
                    })
            
            print(f"🏆 Found {len(series_links)} series to scrape")
            
            # Show all discovered series names for debugging
            print("📋 Discovered series:")
            for i, series in enumerate(series_links[:10], 1):  # Show first 10
                print(f"   {i}. {series['name']}")
            if len(series_links) > 10:
                print(f"   ... and {len(series_links) - 10} more series")
            
            # Filter series if specified
            if series_filter and series_filter.lower() != "all":
                # Handle multiple series numbers separated by commas
                if ',' in series_filter:
                    # Split by commas and clean up each filter
                    series_filters = [f.strip() for f in series_filter.split(',') if f.strip()]
                    print(f"🔍 Multiple series filters detected: {series_filters}")
                    
                    # Filter series that match ANY of the specified filters
                    filtered_series = []
                    for series in series_links:
                        series_name_lower = series['name'].lower()
                        for filter_term in series_filters:
                            if filter_term.lower() in series_name_lower:
                                filtered_series.append(series)
                                break  # Found a match, no need to check other filters
                    
                    if filtered_series:
                        series_links = filtered_series
                        print(f"🔍 Filtered to {len(series_links)} series matching any of: {series_filters}")
                        print("📋 Filtered series:")
                        for i, series in enumerate(series_links, 1):
                            print(f"   {i}. {series['name']}")
                    else:
                        print(f"⚠️ No series found matching any of the filters: {series_filters}")
                        print(f"🔍 Available series names: {[s['name'] for s in series_links[:5]]}...")
                        return []
                else:
                    # Single filter (original logic)
                    filtered_series = [s for s in series_links if series_filter.lower() in s['name'].lower()]
                    if filtered_series:
                        series_links = filtered_series
                        print(f"🔍 Filtered to {len(series_links)} series matching '{series_filter}'")
                        print("📋 Filtered series:")
                        for i, series in enumerate(series_links, 1):
                            print(f"   {i}. {series['name']}")
                    else:
                        print(f"⚠️ No series found matching filter '{series_filter}'")
                        print(f"🔍 Available series names: {[s['name'] for s in series_links[:5]]}...")
                        return []
            
            # Scrape ONE standings page per series
            all_matches = []
            successful_series = 0
            failed_series = 0
            
            for i, series_info in enumerate(series_links, 1):
                series_name = series_info['name']
                series_url = series_info['url']
                
                # Calculate progress percentage
                progress_percent = (i / len(series_links)) * 100
                
                print(f"\n{'='*60}")
                print(f"🏆 Processing Series {i}/{len(series_links)} ({progress_percent:.1f}%): {series_name}")
                print(f"🔗 URL: {series_url}")
                print(f"📊 Progress: {i}/{len(series_links)} series, {len(all_matches)} total matches")
                
                try:
                    # Scrape matches for this series (ONE standings page only)
                    series_matches = scrape_apta_chicago_standings(
                        driver,
                        series_url,
                        series_name, 
                        league_id
                    )
                    
                    if series_matches:
                        all_matches.extend(series_matches)
                        successful_series += 1
                        
                        # Show series summary with team breakdown
                        teams_in_series = set()
                        for match in series_matches:
                            teams_in_series.add(match.get('Home Team', 'Unknown'))
                            teams_in_series.add(match.get('Away Team', 'Unknown'))
                        
                        print(f"✅ Successfully scraped {len(series_matches)} matches from {series_name}")
                        print(f"   📋 Teams in series: {', '.join(sorted(teams_in_series))}")
                        print(f"   📊 Series completion: {len(series_matches)} matches processed")
                    else:
                        failed_series += 1
                        print(f"⚠️ No matches found for {series_name}")
                    
                    # Stealth delay between series
                    if i < len(series_links):
                        stealth_delay = random.uniform(2, 5)  # Random delay between series
                        print(f"⏳ Stealth delay: {stealth_delay:.1f}s before next series...")
                        time.sleep(stealth_delay)
                    
                except Exception as e:
                    failed_series += 1
                    print(f"❌ Error scraping {series_name}: {str(e)}")
                    continue
            
            print(f"\n{'='*80}")
            print(f"🎉 SCRAPING COMPLETE!")
            print(f"📊 SUMMARY:")
            print(f"  ✅ Successful series: {successful_series}")
            print(f"  ❌ Failed series: {failed_series}")
            print(f"  📈 Total matches: {len(all_matches)}")
            print(f"  🥷 Stealth mode: ACTIVE")
            print(f"  📊 Data quality: MAXIMIZED")
            print(f"  🔧 FIXED: ONE standings page per series - no duplicates!")
            
            # Save results
            if all_matches:
                json_path = os.path.join(data_dir, "match_history.json")
                
                # Enhanced deduplication before saving (should be minimal now)
                unique_matches, duplicates_removed, dedup_stats = deduplicate_matches(all_matches)
                
                # Save deduplicated matches
                with open(json_path, "w", encoding="utf-8") as jsonfile:
                    json.dump(unique_matches, jsonfile, indent=2)

                print(f"💾 Data saved to: {json_path}")
                print(f"🔍 Deduplication: {duplicates_removed} duplicates removed (should be minimal)")
                print(f"📊 Final unique matches: {len(unique_matches)}")
            
            return all_matches
            
        else:
            # For other leagues, use the existing approach
            print("🔍 Looking for main standings/matches page...")
            
            # Try to find the main standings or matches page
            standings_url = None
            
            # Strategy 1: Look for "Standings" link
            standings_links = soup.find_all("a", href=True)
            for link in standings_links:
                text = link.get_text(strip=True).lower()
                href = link.get("href", "")
                if "standings" in text or "standings" in href.lower():
                    standings_url = urljoin(base_url, href)
                    print(f"✅ Found standings page: {standings_url}")
                    break
            
            # Strategy 2: Look for "Matches" link if no standings found
            if not standings_url:
                for link in standings_links:
                    text = link.get_text(strip=True).lower()
                    href = link.get("href", "")
                    if "matches" in text or "matches" in href.lower():
                        standings_url = urljoin(base_url, href)
                        print(f"✅ Found matches page: {standings_url}")
                        break
            
            # Strategy 3: Use base URL if no specific page found
            if not standings_url:
                standings_url = base_url
                print(f"⚠️ No specific standings/matches page found, using base URL: {standings_url}")
            
            # Scrape the single standings/matches page
            all_matches = scrape_matches(
                driver,
                standings_url,
                "All Series", 
                league_id,
                max_retries=max_retries,
                retry_delay=retry_delay
            )

        # Final summary
        print(f"\n{'='*80}")
        print(f"🎉 SCRAPING COMPLETE!")
        print(f"📊 SUMMARY:")
        print(f"  📈 Total matches scraped: {len(all_matches)}")
        print(f"  🥷 Stealth mode: ACTIVE")
        print(f"  📊 Data quality: MAXIMIZED")
        print(f"  🔧 FIXED: No duplicates - single standings page approach")
        
        # Save results
        if all_matches:
            json_path = os.path.join(data_dir, "match_history.json")
            
            # Enhanced deduplication before saving (should be minimal now)
            unique_matches, duplicates_removed, dedup_stats = deduplicate_matches(all_matches)
            
            # Save deduplicated matches
            with open(json_path, "w", encoding="utf-8") as jsonfile:
                json.dump(unique_matches, jsonfile, indent=2)

            print(f"💾 Data saved to: {json_path}")
            print(f"🔍 Deduplication: {duplicates_removed} duplicates removed (should be minimal)")
            print(f"📊 Final unique matches: {len(unique_matches)}")
        
        return all_matches


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
        print("  • Enter a single number (e.g., '22') to scrape only series containing that number")
        print("  • Enter multiple numbers separated by commas (e.g., '19,22,24SW') to scrape specific series")
        print("  • Enter 'all' to scrape all series for the selected league")
        print("  • Examples: '22' for Chicago 22, '2A' for Series 2A, '19,22,24SW' for multiple series")
        print()
        series_input = input("Enter series filter (number, comma-separated numbers, or 'all'): ").strip()
        
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
