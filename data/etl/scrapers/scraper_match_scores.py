from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import re
import time
import os
from datetime import datetime, timedelta

print("🎾 TennisScores Match Scraper - Dynamic Discovery Mode")
print("=" * 60)

# Dynamic League Configuration - User Input Based
def get_league_config(league_subdomain=None):
    """Get dynamic league configuration based on user input"""
    if not league_subdomain:
        # This will be passed from the main function
        raise ValueError("League subdomain must be provided")
    
    base_url = f"https://{league_subdomain}.tenniscores.com"
    
    # Enhanced league mapping to handle different subdomain patterns
    league_mappings = {
        'aptachicago': {'league_id': 'APTA_CHICAGO', 'type': 'apta'},
        'apta': {'league_id': 'APTA', 'type': 'apta'},
        'nstf': {'league_id': 'NSTF', 'type': 'nstf'},
        'cita': {'league_id': 'CITA', 'type': 'cita'},
        'tennaqua': {'league_id': 'CITA', 'type': 'cita'},  # CITA uses tennaqua subdomain
    }
    
    # Get league configuration or use subdomain as fallback
    if league_subdomain.lower() in league_mappings:
        config = league_mappings[league_subdomain.lower()]
        league_id = config['league_id']
        league_type = config['type']
    else:
        # Fallback for unknown subdomains
        league_id = league_subdomain.upper()
        league_type = 'unknown'
    
    return {
        'league_id': league_id,
        'subdomain': league_subdomain,
        'base_url': base_url,
        'type': league_type,
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
    etl_dir = os.path.dirname(script_dir)                    # data/etl/
    project_root = os.path.dirname(os.path.dirname(etl_dir))  # rally/ (up one more level)
    
    league_data_dir = os.path.join(project_root, 'data', 'leagues', league_id)
    os.makedirs(league_data_dir, exist_ok=True)
    
    return league_data_dir

# Global variable to store players data for lookups
players_data = []

# Common nickname mappings for better name matching
NICKNAME_MAPPINGS = {
    # Common nicknames to full names
    'mike': ['michael'],
    'jim': ['james'],
    'bob': ['robert'],
    'bill': ['william'],
    'dave': ['david'],
    'steve': ['steven', 'stephen'],
    'chris': ['christopher'],
    'matt': ['matthew'],
    'dan': ['daniel'],
    'tom': ['thomas'],
    'tony': ['anthony'],
    'rick': ['richard'],
    'dick': ['richard'],
    'nick': ['nicholas'],
    'ben': ['benjamin'],
    'sam': ['samuel'],
    'alex': ['alexander'],
    'brad': ['bradley'],
    'greg': ['gregory'],
    'rob': ['robert'],
    'joe': ['joseph'],
    'pat': ['patrick'],
    'ed': ['edward'],
    'ted': ['theodore', 'edward'],
    'andy': ['andrew'],
    'tony': ['anthony'],
    'brian': ['bryan'],  # Common spelling variation
    'bryan': ['brian'],  # Reverse mapping
    
    # Full names to nicknames (reverse mappings)
    'michael': ['mike'],
    'james': ['jim', 'jimmy'],
    'robert': ['bob', 'rob'],
    'william': ['bill', 'will'],
    'david': ['dave'],
    'steven': ['steve'],
    'stephen': ['steve'],
    'christopher': ['chris'],
    'matthew': ['matt'],
    'daniel': ['dan', 'danny'],
    'thomas': ['tom'],
    'anthony': ['tony'],
    'richard': ['rick', 'dick'],
    'nicholas': ['nick'],
    'benjamin': ['ben'],
    'samuel': ['sam'],
    'alexander': ['alex'],
    'bradley': ['brad'],
    'gregory': ['greg'],
    'joseph': ['joe'],
    'patrick': ['pat'],
    'edward': ['ed', 'ted'],
    'theodore': ['ted'],
    'andrew': ['andy'],
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
        players_path = os.path.join(league_data_dir, 'players.json')
        
        with open(players_path, 'r', encoding='utf-8') as f:
            players_data = json.load(f)
        print(f"📊 Loaded {len(players_data)} players for ID lookup from {players_path}")
        return True
    except FileNotFoundError:
        print(f"⚠️  Warning: players.json not found at {players_path}. Player IDs will not be available.")
        return False
    except Exception as e:
        print(f"❌ Error loading players data: {str(e)}")
        return False

def extract_club_name_from_team(team_name):
    """Extract the club name from a team name like 'Birchwood - 6' or 'Lake Forest S1' -> 'Birchwood' or 'Lake Forest'."""
    if not team_name:
        return ""
    
    # Handle APTA format: "Birchwood - 6" -> "Birchwood"
    if ' - ' in team_name:
        parts = team_name.split(' - ')
        return parts[0].strip() if parts else team_name.strip()
    
    # Handle NSTF format: "Lake Forest S1" or "Wilmette S1 T2" -> "Lake Forest" or "Wilmette"
    # Remove series suffixes like "S1", "S1 T2", "S2A", etc.
    import re
    # Pattern matches: S1, S1 T2, S2A, S2B, etc.
    pattern = r'\s+S\d+[A-Z]*(\s+T\d+)?$'
    cleaned = re.sub(pattern, '', team_name).strip()
    return cleaned if cleaned else team_name.strip()

def normalize_name_for_lookup(name):
    """Normalize a name for more flexible matching."""
    if not name:
        return ""
    # Convert to lowercase and strip whitespace
    normalized = name.lower().strip()
    
    # Remove common suffixes and patterns
    patterns_to_remove = [
        ' by forfeit',
        ' forfeit',
        'by forfeit',
        ' jr.',
        ' jr',
        ' sr.',
        ' sr',
        ' iii',
        ' iv',
        ' ii'
    ]
    
    for pattern in patterns_to_remove:
        if normalized.endswith(pattern):
            normalized = normalized[:-len(pattern)].strip()
    
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
        print(f"    [LOOKUP] Warning: Empty name after normalization - {first_name} {last_name}")
        return None
    
    # Strategy 1: Exact match (Series + Club + Names)
    for player in players_data:
        if (player.get('Series') == series and 
            player.get('Club') == club_name and
            normalize_name_for_lookup(player.get('First Name', '')) == first_name_norm and
            normalize_name_for_lookup(player.get('Last Name', '')) == last_name_norm):
            print(f"    [LOOKUP] Strategy 1 (Exact): Found {first_name} {last_name} → {player.get('Player ID')}")
            return player.get('Player ID')
    
    # Strategy 2: Series-wide matching (handles club changes)
    series_matches = []
    for player in players_data:
        if (player.get('Series') == series and
            normalize_name_for_lookup(player.get('First Name', '')) == first_name_norm and
            normalize_name_for_lookup(player.get('Last Name', '')) == last_name_norm):
            series_matches.append(player)
    
    if len(series_matches) == 1:
        player = series_matches[0]
        print(f"    [LOOKUP] Strategy 2 (Series-wide): Found {first_name} {last_name} → {player.get('Player ID')} (Different club: {player.get('Club')})")
        return player.get('Player ID')
    
    # Strategy 2.5: Nickname matching (same club)
    first_name_variations = get_name_variations(first_name_norm)
    last_name_variations = get_name_variations(last_name_norm)
    
    for player in players_data:
        if (player.get('Series') == series and 
            player.get('Club') == club_name):
            
            player_first_norm = normalize_name_for_lookup(player.get('First Name', ''))
            player_last_norm = normalize_name_for_lookup(player.get('Last Name', ''))
            
            # Check if any variation of the search name matches any variation of the player name
            first_match = (player_first_norm in first_name_variations or 
                          any(var in get_name_variations(player_first_norm) for var in first_name_variations))
            
            last_match = (player_last_norm in last_name_variations or
                         any(var in get_name_variations(player_last_norm) for var in last_name_variations))
            
            if first_match and last_match:
                print(f"    [LOOKUP] Strategy 2.5 (Nickname): Found {first_name} {last_name} → {player.get('Player ID')} (DB: {player.get('First Name')} {player.get('Last Name')})")
                return player.get('Player ID')
    
    # Strategy 3: Fuzzy matching (same club)
    for player in players_data:
        if (player.get('Series') == series and 
            player.get('Club') == club_name):
            
            player_first_norm = normalize_name_for_lookup(player.get('First Name', ''))
            player_last_norm = normalize_name_for_lookup(player.get('Last Name', ''))
            
            # Try various fuzzy matching approaches
            first_similar = similar_strings(first_name_norm, player_first_norm, threshold=0.8)
            last_similar = similar_strings(last_name_norm, player_last_norm, threshold=0.8)
            
            if first_similar and last_similar:
                print(f"    [LOOKUP] Strategy 3 (Fuzzy): Found {first_name} {last_name} → {player.get('Player ID')} (DB: {player.get('First Name')} {player.get('Last Name')})")
                return player.get('Player ID')
    
    # Strategy 4: Very lenient matching (same club only, lower threshold)
    for player in players_data:
        if (player.get('Series') == series and 
            player.get('Club') == club_name):
            
            player_first_norm = normalize_name_for_lookup(player.get('First Name', ''))
            player_last_norm = normalize_name_for_lookup(player.get('Last Name', ''))
            
            # More lenient fuzzy matching
            first_similar = similar_strings(first_name_norm, player_first_norm, threshold=0.6)
            last_similar = similar_strings(last_name_norm, player_last_norm, threshold=0.6)
            
            if first_similar and last_similar:
                print(f"    [LOOKUP] Strategy 4 (Lenient): Found {first_name} {last_name} → {player.get('Player ID')} (DB: {player.get('First Name')} {player.get('Last Name')})")
                return player.get('Player ID')
    
    # No match found
    print(f"    [LOOKUP] No match found for {first_name} {last_name} in {club_name} ({series})")
    return None

def lookup_player_id(series, team_name, first_name, last_name, league_id=None):
    """
    Look up a Player ID based on Series, Club, First Name, and Last Name.
    
    This is a wrapper that calls the enhanced lookup function.
    """
    return lookup_player_id_enhanced(series, team_name, first_name, last_name, league_id)

class ChromeManager:
    """Context manager for handling Chrome WebDriver sessions."""
    
    def __init__(self, max_retries=3):
        """Initialize the Chrome WebDriver manager.
        
        Args:
            max_retries (int): Maximum number of retries for creating a new driver
        """
        self.driver = None
        self.max_retries = max_retries
        
    def create_driver(self):
        """Create and configure a new Chrome WebDriver instance."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--disable-features=NetworkService')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        return webdriver.Chrome(options=options)

    def __enter__(self):
        """Create and return a Chrome WebDriver instance with retries."""
        for attempt in range(self.max_retries):
            try:
                if self.driver is not None:
                    try:
                        self.driver.quit()
                    except:
                        pass
                self.driver = self.create_driver()
                return self.driver
            except Exception as e:
                print(f"Error creating Chrome driver (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    print("Retrying...")
                    time.sleep(5)
                else:
                    raise Exception("Failed to create Chrome driver after maximum retries")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the Chrome WebDriver instance."""
        self.quit()

    def quit(self):
        """Safely quit the Chrome WebDriver instance."""
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error closing Chrome driver: {str(e)}")
            finally:
                self.driver = None

def scrape_matches(driver, url, series_name, league_id, max_retries=3, retry_delay=5):
    """Scrape match data from a single series URL with retries."""
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
                            EC.presence_of_element_located((By.XPATH, "//a[contains(translate(text(), 'MATCHES', 'matches'), 'matches')]"))
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
                            EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Match') or contains(text(), 'Result')]"))
                        )
                        print("Found match/result link using Strategy 4")
                    except TimeoutException:
                        pass
                
                # Strategy 5: Look for any link that might contain match data
                if not matches_link:
                    try:
                        # Look for links with href containing "match" or "result"
                        matches_link = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'match') or contains(@href, 'result')]"))
                        )
                        print("Found match/result link using Strategy 5 (href-based)")
                    except TimeoutException:
                        pass
                
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
                        EC.presence_of_element_located((By.ID, "match_results_container"))
                    )
                    print("Match results loaded successfully using Strategy 1")
                    results_container_found = True
                except TimeoutException:
                    pass
                
                # Strategy 2: Look for any element with "match" or "result" in the ID
                if not results_container_found:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'match') or contains(@id, 'result')]"))
                        )
                        print("Match results loaded successfully using Strategy 2")
                        results_container_found = True
                    except TimeoutException:
                        pass
                
                # Strategy 3: Look for common table structures
                if not results_container_found:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'match') or contains(@class, 'result')]"))
                        )
                        print("Match results loaded successfully using Strategy 3")
                        results_container_found = True
                    except TimeoutException:
                        pass
                
                # Strategy 4: Wait for any substantial content to load
                if not results_container_found:
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//div[count(descendant::*) > 10]"))
                        )
                        print("Page content loaded successfully using Strategy 4")
                        results_container_found = True
                    except TimeoutException:
                        pass
                
                if not results_container_found:
                    print(f"Timeout waiting for match results to load (attempt {attempt + 1}/{max_retries})")
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
            print("Looking for match tables using Strategy 1: match_results_table class")
            tables_strategy1 = driver.find_elements(By.CLASS_NAME, "match_results_table")
            if tables_strategy1:
                match_tables.extend(tables_strategy1)
                print(f"Found {len(tables_strategy1)} tables using Strategy 1")
            
            # Strategy 2: Look for any table with "match" or "result" in the class name
            if not match_tables:
                print("Looking for match tables using Strategy 2: match/result class patterns")
                tables_strategy2 = driver.find_elements(By.XPATH, "//table[contains(@class, 'match') or contains(@class, 'result')]")
                if tables_strategy2:
                    match_tables.extend(tables_strategy2)
                    print(f"Found {len(tables_strategy2)} tables using Strategy 2")
            
            # Strategy 3: Look for div containers that might contain match data
            if not match_tables:
                print("Looking for match tables using Strategy 3: div containers")
                tables_strategy3 = driver.find_elements(By.XPATH, "//div[contains(@class, 'match') or contains(@class, 'result')]")
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
            
            # Strategy 5: Look for structured div layouts (CITA might use this)
            if not match_tables:
                print("Looking for match tables using Strategy 5: structured div layouts")
                div_containers = driver.find_elements(By.XPATH, "//div[count(./div) > 5]")  # Divs with multiple child divs
                if div_containers:
                    match_tables.extend(div_containers)
                    print(f"Found {len(div_containers)} structured divs using Strategy 5")
            
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
            
            for table_index, table in enumerate(match_tables, 1):
                try:
                    print(f"\nProcessing match table {table_index} of {len(match_tables)}")
                    # Find the match header (contains date and club names)
                    header_row = table.find_element(By.CSS_SELECTOR, "div[style*='background-color: #dcdcdc;']")
                    
                    # Extract date from the header
                    date_element = header_row.find_element(By.CLASS_NAME, "match_rest")
                    date_text = date_element.text
                    match_date = re.search(r'(\w+ \d+, \d{4})', date_text)
                    if match_date:
                        date_str = match_date.group(1)
                        date_obj = datetime.strptime(date_str, '%B %d, %Y')
                        date = date_obj.strftime('%d-%b-%y')
                    else:
                        date = "Unknown"
                    
                    # Extract club names from the header
                    home_club_element = header_row.find_element(By.CLASS_NAME, "team_name")
                    away_club_element = header_row.find_element(By.CLASS_NAME, "team_name2")
                    
                    # Get the full team names including the "- 22" suffix
                    home_club_full = home_club_element.text.strip()
                    away_club_full = away_club_element.text.strip()
                    
                    # Skip matches involving BYE teams - they are placeholders with no actual players
                    if 'BYE' in home_club_full.upper() or 'BYE' in away_club_full.upper():
                        print(f"   Skipping BYE match: {home_club_full} vs {away_club_full}")
                        continue
                    
                    print(f"Processing matches for {home_club_full} vs {away_club_full} on {date}")
                    
                    # Find all player rows in this table
                    player_divs = table.find_elements(By.XPATH, ".//div[not(contains(@style, 'background-color')) and not(contains(@class, 'clear clearfix'))]")
                    
                    i = 0
                    while i < len(player_divs) - 4:  # Need at least 5 elements for a complete match row
                        try:
                            # Check if this is a player match row
                            if ("points" in player_divs[i].get_attribute("class") and 
                                "team_name" in player_divs[i+1].get_attribute("class") and 
                                "match_rest" in player_divs[i+2].get_attribute("class") and 
                                "team_name2" in player_divs[i+3].get_attribute("class")):
                                
                                # Extract data
                                home_text = player_divs[i+1].text.strip()
                                score = player_divs[i+2].text.strip()
                                away_text = player_divs[i+3].text.strip()
                                
                                # Skip if this is not a match
                                if not score or re.search(r'\d{1,2}:\d{2}', score) or "Date" in score:
                                    i += 5
                                    continue
                                
                                # Determine winner
                                winner_img_home = player_divs[i].find_elements(By.TAG_NAME, "img")
                                winner_img_away = player_divs[i+4].find_elements(By.TAG_NAME, "img") if i+4 < len(player_divs) else []
                                
                                if winner_img_home:
                                    winner = "home"
                                elif winner_img_away:
                                    winner = "away"
                                else:
                                    winner = "unknown"
                                
                                # Split player names
                                home_players = home_text.split("/")
                                away_players = away_text.split("/")
                                
                                home_player1 = home_players[0].strip() if len(home_players) > 0 else ""
                                home_player2 = home_players[1].strip() if len(home_players) > 1 else ""
                                away_player1 = away_players[0].strip() if len(away_players) > 0 else ""
                                away_player2 = away_players[1].strip() if len(away_players) > 1 else ""
                                
                                # Split player names into first and last names for lookup
                                def split_player_name(full_name):
                                    if not full_name:
                                        return "", ""
                                    
                                    # Handle "By Forfeit" cases
                                    clean_name = full_name.strip()
                                    if "by forfeit" in clean_name.lower():
                                        # Extract the name before "By Forfeit"
                                        clean_name = clean_name.lower().split("by forfeit")[0].strip()
                                    elif "forfeit" in clean_name.lower():
                                        # Handle just "Forfeit" cases
                                        clean_name = clean_name.lower().split("forfeit")[0].strip()
                                    
                                    parts = clean_name.strip().split()
                                    if len(parts) >= 2:
                                        return parts[0], " ".join(parts[1:])
                                    elif len(parts) == 1:
                                        return parts[0], ""
                                    return "", ""
                                
                                # Split names and lookup Player IDs
                                home_p1_first, home_p1_last = split_player_name(home_player1)
                                home_p2_first, home_p2_last = split_player_name(home_player2)
                                away_p1_first, away_p1_last = split_player_name(away_player1)
                                away_p2_first, away_p2_last = split_player_name(away_player2)
                                
                                # Lookup Player IDs using the enhanced lookup function
                                home_p1_id = lookup_player_id_enhanced(series_name, home_club_full, home_p1_first, home_p1_last, league_id)
                                home_p2_id = lookup_player_id_enhanced(series_name, home_club_full, home_p2_first, home_p2_last, league_id)
                                away_p1_id = lookup_player_id_enhanced(series_name, away_club_full, away_p1_first, away_p1_last, league_id)
                                away_p2_id = lookup_player_id_enhanced(series_name, away_club_full, away_p2_first, away_p2_last, league_id)
                                
                                # Store match data with Player IDs included
                                match_data = {
                                    "league_id": league_id,
                                    "Date": date,
                                    "Home Team": home_club_full,
                                    "Away Team": away_club_full,
                                    "Home Player 1": home_player1,
                                    "Home Player 1 ID": home_p1_id,
                                    "Home Player 2": home_player2,
                                    "Home Player 2 ID": home_p2_id,
                                    "Away Player 1": away_player1,
                                    "Away Player 1 ID": away_p1_id,
                                    "Away Player 2": away_player2,
                                    "Away Player 2 ID": away_p2_id,
                                    "Scores": score,
                                    "Winner": winner
                                }
                                matches_data.append(match_data)
                                
                                # Log the match with ID lookup results
                                id_status = []
                                if home_p1_id: id_status.append(f"H1✓")
                                else: id_status.append(f"H1✗")
                                if home_p2_id: id_status.append(f"H2✓")
                                else: id_status.append(f"H2✗")
                                if away_p1_id: id_status.append(f"A1✓")
                                else: id_status.append(f"A1✗")
                                if away_p2_id: id_status.append(f"A2✓")
                                else: id_status.append(f"A2✗")
                                
                                print(f"  Processed match: {home_player1}/{home_player2} vs {away_player1}/{away_player2} - Score: {score} [IDs: {' '.join(id_status)}]")
                                
                                i += 5  # Move to the next potential match row
                            else:
                                i += 1  # Move to the next div
                        except Exception as e:
                            print(f"  Error processing match row: {str(e)}")
                            i += 1  # Skip this div if there's an error
                    
                    print(f"Completed table {table_index}")
                
                except Exception as e:
                    print(f"Error processing match table {table_index}: {str(e)}")
            
            # If we successfully processed the page, break the retry loop
            break
            
        except TimeoutException:
            print(f"Timeout waiting for page to load (attempt {attempt + 1}/{max_retries})")
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

def scrape_all_matches(league_subdomain, max_retries=3, retry_delay=5):
    """Main function to scrape and save match data from all series."""
    # Record start time
    start_time = datetime.now()
    print(f"🕐 Session Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Load league configuration from user input
        config = get_league_config(league_subdomain)
        league_id = config['league_id']
        
        print(f"🌟 Processing ALL discovered series from {config['subdomain']} dynamically")
        print("🔍 No filtering - comprehensive discovery and processing of all series")
        
        # Load players data for Player ID lookups
        players_loaded = load_players_data(league_id)
        if not players_loaded:
            print("⚠️  Warning: Player ID lookups will not be available")
        
        # Use context manager to ensure Chrome driver is properly closed
        with ChromeManager() as driver:
            # Use dynamic base URL from config
            base_url = config['base_url']
            print(f"🌐 Target League: {league_id} ({config['subdomain']})")
            print(f"🔗 Base URL: {base_url}")
            
            # Create league-specific directory
            data_dir = build_league_data_dir(league_id)
            
            print(f"Navigating to URL: {base_url}")
            driver.get(base_url)
            time.sleep(retry_delay)
            
            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Multi-strategy series discovery to handle different website structures
            series_urls = []
            discovery_start_time = datetime.now()
            print(f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}")
            
            # Strategy 1: NSTF/APTA_CHICAGO format - div_list_option
            print("🔍 Trying Strategy 1: div_list_option (NSTF/APTA_CHICAGO format)")
            series_elements = soup.find_all('div', class_='div_list_option')
            
            if series_elements:
                print(f"✅ Found {len(series_elements)} series using Strategy 1")
                for element in series_elements:
                    try:
                        series_link = element.find('a')
                        if series_link and series_link.text:
                            series_number = series_link.text.strip()
                            
                            # Auto-detect and format series based on content
                            if 'Series' in series_number or series_number.startswith('S'):
                                # NSTF format: "Series 1", "S1", "S2A", etc.
                                if series_number.startswith('Series '):
                                    formatted_series = series_number  # Already properly formatted
                                else:
                                    formatted_series = f"Series {series_number}"
                            elif series_number.isdigit():
                                # APTA format: "1", "2", "25", etc. -> "Chicago X"
                                formatted_series = f"Chicago {series_number}"
                            else:
                                # Other formats - use as-is
                                formatted_series = series_number
                                
                            series_url = series_link.get('href', '')
                            full_url = f"{base_url}{series_url}" if series_url else ''
                            if full_url:
                                series_urls.append((formatted_series, full_url))
                                print(f"📈 Found series: {formatted_series}")
                                print(f"    URL: {full_url}")
                    except Exception as e:
                        print(f"❌ Error extracting series URL: {str(e)}")
            
            # Strategy 2: CITA format - look for different patterns
            if not series_urls:
                print("🔍 Trying Strategy 2: CITA format - searching for series links")
                
                # Look for any links that might contain series information
                all_links = soup.find_all('a', href=True)
                
                for link in all_links:
                    try:
                        href = link.get('href', '')
                        text = link.text.strip()
                        
                        # Look for patterns that might indicate series
                        if (text and 
                            (text.replace(' ', '').replace('&', '').replace('Under', '').replace('.', '').replace('0', '').isdigit() or
                             'series' in text.lower() or
                             'division' in text.lower() or
                             'level' in text.lower() or
                             'flight' in text.lower() or
                             re.match(r'^\d+(\.\d+)?\s*(&\s*Under|&\s*Over|Over|Under|\+)?$', text.replace(' ', '')) or
                             re.match(r'^\d+(\.\d+)?\s*(Men|Women|Mixed|Open)?\s*(Doubles?|Singles?)?$', text, re.IGNORECASE))):
                            
                            # Format the series name
                            if text.replace(' ', '').replace('&', '').replace('Under', '').replace('.', '').replace('0', '').isdigit():
                                # Numeric series like "4.5", "3.5 & Under", etc.
                                formatted_series = text
                            elif 'series' in text.lower():
                                formatted_series = text
                            else:
                                # Use the text as-is for other patterns
                                formatted_series = text
                                
                            full_url = f"{base_url}{href}" if href.startswith('/') else href
                            
                            # Filter out library documents and PDFs
                            if (full_url and 
                                (formatted_series, full_url) not in series_urls and
                                'library' not in href.lower() and
                                not href.lower().endswith('.pdf') and
                                not href.lower().endswith('.doc') and
                                not href.lower().endswith('.docx')):
                                series_urls.append((formatted_series, full_url))
                                print(f"📈 Found series: {formatted_series}")
                                print(f"    URL: {full_url}")
                            elif 'library' in href.lower() or href.lower().endswith(('.pdf', '.doc', '.docx')):
                                print(f"⏸️ Skipping library/document: {formatted_series} -> {href}")
                    except Exception as e:
                        print(f"❌ Error processing link: {str(e)}")
                
                if series_urls:
                    print(f"✅ Found {len(series_urls)} series using Strategy 2")
            
            # Strategy 3: Generic fallback - look for any structured navigation
            if not series_urls:
                print("🔍 Trying Strategy 3: Generic fallback - looking for navigation patterns")
                
                # Look for common navigation patterns
                nav_patterns = [
                    ('ul', 'nav'),
                    ('div', 'navigation'),
                    ('div', 'menu'),
                    ('div', 'list'),
                    ('table', None),
                    ('tbody', None)
                ]
                
                for tag, class_name in nav_patterns:
                    elements = soup.find_all(tag, class_=class_name) if class_name else soup.find_all(tag)
                    
                    for element in elements:
                        links = element.find_all('a', href=True)
                        
                        for link in links:
                            try:
                                href = link.get('href', '')
                                text = link.text.strip()
                                
                                # Look for numeric or series-like patterns
                                if (text and len(text) < 50 and  # Reasonable length
                                    (text.replace(' ', '').replace('&', '').isdigit() or
                                     'series' in text.lower() or
                                     re.match(r'^\d+(\.\d+)?.*$', text) or
                                     re.match(r'^[A-Z]\d+.*$', text))):
                                    
                                    formatted_series = text
                                    full_url = f"{base_url}{href}" if href.startswith('/') else href
                                    
                                    if full_url and (formatted_series, full_url) not in series_urls:
                                        series_urls.append((formatted_series, full_url))
                                        print(f"📈 Found series: {formatted_series}")
                                        print(f"    URL: {full_url}")
                            except Exception as e:
                                continue
                
                if series_urls:
                    print(f"✅ Found {len(series_urls)} series using Strategy 3")
            
            # Debug: If still no series found, show detailed page structure
            if not series_urls:
                print("🔍 No series found with any strategy. Analyzing page structure...")
                
                # Show some debug info about the page structure
                all_divs = soup.find_all('div')
                classes_found = set()
                
                for div in all_divs[:50]:  # Limit to first 50 for performance
                    if div.get('class'):
                        classes_found.update(div.get('class'))
                
                print(f"📊 Found {len(all_divs)} div elements")
                print(f"📊 Common classes: {list(classes_found)[:20]}")  # Show first 20 classes
                
                # Look for any links with text
                all_links = soup.find_all('a', href=True)
                print(f"📊 Found {len(all_links)} total links")
                
                # Show all link texts for debugging
                link_texts = []
                for link in all_links:
                    text = link.text.strip()
                    href = link.get('href', '')
                    if text and len(text) < 100:  # Reasonable length
                        link_texts.append(f"'{text}' -> {href}")
                
                if link_texts:
                    print(f"📊 All links found:")
                    for i, link_text in enumerate(link_texts[:20]):  # Show first 20
                        print(f"  {i+1}. {link_text}")
                    if len(link_texts) > 20:
                        print(f"  ... and {len(link_texts) - 20} more links")
                
                # Look for dropdowns, menus, or navigation elements
                nav_elements = soup.find_all(['nav', 'ul', 'ol'])
                print(f"📊 Found {len(nav_elements)} navigation elements")
                
                for i, nav in enumerate(nav_elements[:5]):  # Show first 5
                    nav_links = nav.find_all('a')
                    if nav_links:
                        print(f"  Nav {i+1}: {len(nav_links)} links")
                        for link in nav_links[:3]:  # Show first 3 links in each nav
                            print(f"    - '{link.text.strip()}' -> {link.get('href', '')}")
                
                # Look for form elements or buttons that might trigger navigation
                forms = soup.find_all('form')
                buttons = soup.find_all(['button', 'input'])
                selects = soup.find_all('select')
                
                print(f"📊 Found {len(forms)} forms, {len(buttons)} buttons/inputs, {len(selects)} select elements")
                
                # Look for JavaScript-loaded content indicators
                scripts = soup.find_all('script')
                print(f"📊 Found {len(scripts)} script tags (may indicate dynamic content)")
                
                # Check for common league/series keywords in the page content
                page_text = soup.get_text().lower()
                league_keywords = ['series', 'division', 'level', 'flight', 'league', 'tournament', 'bracket', 'draw']
                found_keywords = [kw for kw in league_keywords if kw in page_text]
                if found_keywords:
                    print(f"📊 Found league keywords in page: {found_keywords}")
                
                # Try to find any numeric patterns in the page text
                numeric_patterns = re.findall(r'\b\d+(?:\.\d+)?\b', page_text)
                unique_numbers = list(set(numeric_patterns))[:10]  # Get unique numbers, limit to 10
                if unique_numbers:
                    print(f"📊 Found numeric patterns: {unique_numbers}")
                
                # Strategy 6: Try to find series through JavaScript interaction
                print("🔍 Trying Strategy 6: JavaScript interaction and dynamic content")
                
                # Wait a bit more for potential JavaScript to load
                time.sleep(3)
                
                # Re-parse the page after waiting
                updated_soup = BeautifulSoup(driver.page_source, 'html.parser')
                updated_links = updated_soup.find_all('a', href=True)
                
                print(f"📊 After waiting: Found {len(updated_links)} links")
                
                # Try clicking on potential navigation elements
                try:
                    # Look for menu toggles or dropdowns
                    menu_toggles = driver.find_elements(By.XPATH, "//button[contains(@class, 'toggle') or contains(@class, 'menu') or contains(@class, 'nav')]")
                    dropdown_toggles = driver.find_elements(By.XPATH, "//a[contains(@class, 'dropdown') or contains(@data-toggle, 'dropdown')]")
                    
                    for toggle in menu_toggles + dropdown_toggles:
                        try:
                            print(f"📋 Clicking potential menu toggle: {toggle.text.strip()}")
                            toggle.click()
                            time.sleep(2)
                            
                            # Re-check for series after clicking
                            updated_soup = BeautifulSoup(driver.page_source, 'html.parser')
                            new_links = updated_soup.find_all('a', href=True)
                            
                            for link in new_links:
                                text = link.text.strip()
                                href = link.get('href', '')
                                
                                # Check if this looks like a series link
                                if (text and 
                                    (re.match(r'^\d+(\.\d+)?', text) or
                                     'series' in text.lower() or
                                     'division' in text.lower() or
                                     'level' in text.lower())):
                                    
                                    formatted_series = text
                                    full_url = f"{base_url}{href}" if href.startswith('/') else href
                                    
                                    if (formatted_series, full_url) not in series_urls:
                                        series_urls.append((formatted_series, full_url))
                                        print(f"📈 Found series after menu interaction: {formatted_series}")
                                        print(f"    URL: {full_url}")
                            
                            if series_urls:
                                break
                                
                        except Exception as e:
                            print(f"📋 Error clicking toggle: {e}")
                            continue
                            
                except Exception as e:
                    print(f"📋 Error with JavaScript interaction: {e}")
                
                if series_urls:
                    print(f"✅ Found {len(series_urls)} series using Strategy 6 (JavaScript interaction)")
            
            discovery_end_time = datetime.now()
            discovery_duration = discovery_end_time - discovery_start_time
            print(f"✅ Discovery Phase Complete: {discovery_duration.total_seconds():.1f} seconds")
            print(f"📊 Discovered {len(series_urls)} series total")
            
            if not series_urls:
                print("❌ No series found!")
                return
            
            # Sort series by number for organized processing
            def sort_key(item):
                # Extract number from series name
                try:
                    series_name = item[0]
                    
                    # APTA_CHICAGO format: "Chicago 1", "Chicago 25", etc.
                    if 'Chicago' in series_name:
                        num = float(series_name.split()[1])  # Get the number after "Chicago "
                    
                    # NSTF format: "Series 1", "Series 2A", etc.
                    elif 'Series' in series_name:
                        parts = series_name.split()[1:]
                        if parts:
                            # Extract numeric part
                            match = re.search(r'(\d+)', parts[0])
                            if match:
                                num = float(match.group(1))
                            else:
                                num = float('inf')
                        else:
                            num = float('inf')
                    
                    # CITA format: "4.5", "3.5 & Under", "5.0 Open", etc.
                    elif re.match(r'^\d+(\.\d+)?', series_name):
                        # Extract the numeric part at the beginning
                        match = re.match(r'^(\d+(?:\.\d+)?)', series_name)
                        if match:
                            num = float(match.group(1))
                        else:
                            num = float('inf')
                    
                    # Numeric series: "1", "2", "25", etc.
                    elif series_name.replace(' ', '').replace('&', '').replace('Under', '').replace('.', '').replace('0', '').isdigit():
                        # Try to extract just the numeric part
                        numeric_part = re.search(r'(\d+(?:\.\d+)?)', series_name)
                        if numeric_part:
                            num = float(numeric_part.group(1))
                        else:
                            num = float('inf')
                    
                    # Fallback: try to find any number in the series name
                    else:
                        numeric_match = re.search(r'(\d+(?:\.\d+)?)', series_name)
                        if numeric_match:
                            num = float(numeric_match.group(1))
                        else:
                            num = float('inf')
                    
                    return (num, True)
                except (IndexError, ValueError):
                    return (float('inf'), False)
            
            series_urls.sort(key=sort_key)
            
            # Initialize tracking
            all_matches = []
            total_matches = 0
            scraping_start_time = datetime.now()
            print(f"\n⚡ Scraping Phase Start: {scraping_start_time.strftime('%H:%M:%S')}")
            print(f"📋 Processing {len(series_urls)} series...")
            
            # Process each series
            for series_num, (series_number, series_url) in enumerate(series_urls, 1):
                series_start_time = datetime.now()
                progress_percent = (series_num / len(series_urls)) * 100
                elapsed = series_start_time - start_time
                
                print(f"\n=== Series {series_num}/{len(series_urls)} ({progress_percent:.1f}%) | Elapsed: {elapsed} ===")
                print(f"🏆 Processing: {series_number}")
                
                matches = scrape_matches(driver, series_url, series_number, league_id, max_retries=max_retries, retry_delay=retry_delay)
                
                series_end_time = datetime.now()
                series_duration = series_end_time - series_start_time
                
                if not matches:
                    print(f"⚠️  No matches found for series {series_number}")
                else:
                    # Add matches directly to the flat array
                    all_matches.extend(matches)
                    total_matches += len(matches)
                    print(f"✅ Series completed in {series_duration.total_seconds():.1f}s | Found {len(matches)} matches")
                
                # Progress update with ETA
                remaining_series = len(series_urls) - series_num
                avg_time_per_series = (series_start_time - scraping_start_time).total_seconds() / series_num if series_num > 0 else 0
                estimated_remaining = remaining_series * avg_time_per_series if avg_time_per_series > 0 else 0
                eta = series_end_time + timedelta(seconds=estimated_remaining) if estimated_remaining > 0 else None
                
                print(f"📊 Progress: {series_num}/{len(series_urls)} series, {total_matches} total matches")
                if eta:
                    print(f"⏰ ETA: {eta.strftime('%H:%M:%S')} (est. {estimated_remaining/60:.1f} min remaining)")
                
                time.sleep(retry_delay)  # Add delay between series
            
            # Save all matches to league-specific JSON file
            json_filename = "match_history.json"
            json_path = os.path.join(data_dir, json_filename)
            
            # Load existing data if it exists
            existing_matches = []
            existing_league_ids = set()
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as jsonfile:
                        existing_matches = json.load(jsonfile)
                        # Extract league IDs from existing data
                        for match in existing_matches:
                            if 'league_id' in match:
                                existing_league_ids.add(match['league_id'])
                    print(f"Found existing data with {len(existing_matches)} matches")
                    print(f"Existing league IDs: {existing_league_ids}")
                except Exception as e:
                    print(f"Error loading existing data: {str(e)}")
                    existing_matches = []
                    existing_league_ids = set()
            
            # Save new matches (always overwrite for current league)
            with open(json_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(all_matches, jsonfile, indent=2)
            
            # Calculate final timing
            end_time = datetime.now()
            total_duration = end_time - start_time
            scraping_duration = end_time - scraping_start_time if scraping_start_time else total_duration
            
            print(f"\n🎉 SCRAPING COMPLETE!")
            print("=" * 70)
            
            # Detailed timing summary
            print(f"📅 SESSION SUMMARY - {end_time.strftime('%Y-%m-%d')}")
            print(f"🕐 Session Start:     {start_time.strftime('%H:%M:%S')}")
            if discovery_start_time:
                print(f"🔍 Discovery Start:   {discovery_start_time.strftime('%H:%M:%S')} (Duration: {discovery_duration.total_seconds():.1f}s)")
            if scraping_start_time:
                print(f"⚡ Scraping Start:    {scraping_start_time.strftime('%H:%M:%S')} (Duration: {scraping_duration.total_seconds():.1f}s)")
            print(f"🏁 Session End:       {end_time.strftime('%H:%M:%S')}")
            print(f"⏱️  TOTAL DURATION:    {total_duration}")
            print()
            
            # Performance metrics
            total_seconds = total_duration.total_seconds()
            series_per_minute = (len(series_urls) / total_seconds * 60) if total_seconds > 0 else 0
            matches_per_minute = (total_matches / total_seconds * 60) if total_seconds > 0 else 0
            
            print(f"📊 PERFORMANCE METRICS")
            print(f"🏆 Total series processed: {len(series_urls)}")
            print(f"📈 Total matches scraped: {total_matches}")
            print(f"📈 Series per minute: {series_per_minute:.1f}")
            print(f"⚡ Matches per minute: {matches_per_minute:.1f}")
            print(f"⚡ Average time per series: {total_seconds/len(series_urls):.1f}s" if len(series_urls) > 0 else "⚡ Average time per series: N/A")
            print(f"⚡ Average time per match: {total_seconds/total_matches:.1f}s" if total_matches > 0 else "⚡ Average time per match: N/A")
            print()
            
            print(f"💾 Data saved to: {json_path}")
            print(f"🌐 League: {league_id} ({config['subdomain']})")
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
    print("🔍 Dynamically discovering ALL series from any TennisScores website")
    print("📊 No more hardcoded values - everything is discovered automatically!")
    print()
    
    # Get league input from user
    league_subdomain = input("Enter league subdomain (e.g., 'aptachicago', 'nstf'): ").strip().lower()
    
    if not league_subdomain:
        print("❌ No league subdomain provided. Exiting.")
        exit(1)
    
    target_url = f"https://{league_subdomain}.tenniscores.com"
    print(f"🌐 Target URL: {target_url}")
    print()
    
    scrape_all_matches(league_subdomain)
