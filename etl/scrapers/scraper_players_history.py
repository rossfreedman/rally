print("[DEBUG] player_scrape_history.py script started")
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import csv
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import tempfile
import json
import hashlib
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.player_id_utils import extract_tenniscores_player_id, create_player_id

# Import enhanced discovery functions from scraper_players.py
try:
    from scrapers.scraper_players import discover_all_leagues_and_series, find_missing_teams_comprehensive
    print("[DEBUG] Successfully imported enhanced discovery functions")
except ImportError as e:
    print(f"[DEBUG] Warning: Could not import enhanced discovery functions: {e}")
    # Define a fallback function
    def discover_all_leagues_and_series(driver, config, max_exploration_pages=5):
        print("[DEBUG] Using fallback discovery - enhanced functions not available")
        return {'teams': {}, 'series': set(), 'divisions': {}, 'locations': {}, 'clubs': set()}

# Removed hardcoded division and location lookups - now using dynamic discovery

# Removed file-based configuration functions - now using user input

def get_subdomain_to_league_id_mapping():
    """
    Dynamically map subdomains to their correct database league IDs by querying the database.
    This ensures consistency with the database schema and automatically handles new leagues.
    
    Returns:
        dict: Mapping of subdomain -> league_id
    """
    try:
        import psycopg2
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        if not DATABASE_URL:
            print("[WARNING] DATABASE_URL not found, using fallback mapping")
            return _get_fallback_mapping()
        
        # Query database for league mappings
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("SELECT league_id, league_url FROM leagues WHERE league_url IS NOT NULL")
        results = cursor.fetchall()
        
        mapping = {}
        for league_id, league_url in results:
            # Extract subdomain from URL (e.g., https://aptachicago.tenniscores.com -> aptachicago)
            if league_url and 'tenniscores.com' in league_url:
                try:
                    # Parse URL to get subdomain
                    from urllib.parse import urlparse
                    parsed = urlparse(league_url)
                    hostname = parsed.hostname
                    if hostname and hostname.endswith('.tenniscores.com'):
                        subdomain = hostname.replace('.tenniscores.com', '')
                        mapping[subdomain] = league_id
                        print(f"[DEBUG] Mapped subdomain '{subdomain}' -> league_id '{league_id}'")
                except Exception as e:
                    print(f"[WARNING] Could not parse URL {league_url}: {e}")
        
        conn.close()
        
        if not mapping:
            print("[WARNING] No mappings found in database, using fallback")
            return _get_fallback_mapping()
            
        print(f"[DEBUG] Dynamic mapping loaded: {mapping}")
        return mapping
        
    except Exception as e:
        print(f"[WARNING] Database query failed: {e}, using fallback mapping")
        return _get_fallback_mapping()

def _get_fallback_mapping():
    """
    Fallback mapping in case database query fails.
    
    Returns:
        dict: Basic fallback mapping
    """
    return {
        'aptachicago': 'APTA_CHICAGO',
        'nstf': 'NSTF',
    }

def get_league_config(league_subdomain=None):
    """Get dynamic league configuration based on user input"""
    if not league_subdomain:
        raise ValueError("League subdomain must be provided")
    
    # Map subdomain to correct database league ID
    subdomain_mapping = get_subdomain_to_league_id_mapping()
    league_id = subdomain_mapping.get(league_subdomain.lower())
    
    if not league_id:
        # Fallback to uppercased subdomain if no mapping exists
        league_id = league_subdomain.upper()
        print(f"[WARNING] No league ID mapping found for '{league_subdomain}', using fallback: {league_id}")
    
    base_url = build_base_url(league_subdomain)
    
    return {
        'league_id': league_id,
        'subdomain': league_subdomain,
        'base_url': base_url,
        'main_page': f'{base_url}/?mod=nndz-TjJiOWtOR2sxTnhI',
        'player_page_mod': 'nndz-SkhmOW1PQ3V4Zz09',
        'team_page_mod': 'nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D'
    }

def build_base_url(subdomain):
    """
    Build the base URL for the league using the subdomain.
    
    Args:
        subdomain (str): The subdomain for the league (e.g., 'aptachicago', 'nstf')
    
    Returns:
        str: The complete base URL (e.g., 'https://aptachicago.tenniscores.com')
    """
    return f"https://{subdomain}.tenniscores.com"

def extract_series_name_from_team(team_name):
    """
    Extract series name from team name, auto-detecting APTA vs NSTF format.
    
    Args:
        team_name (str): Team name in various formats
        
    Returns:
        str: Standardized series name or None if not detected
        
    Examples:
        APTA: "Birchwood - 6" -> "Chicago 6"
        NSTF: "Birchwood S1" -> "Series 1"
        NSTF: "Wilmette Sunday A" -> "Series A"
    """
    if not team_name:
        return None
        
    team_name = team_name.strip()
    
    # APTA Chicago format: "Club - Number"
    if ' - ' in team_name:
        parts = team_name.split(' - ')
        if len(parts) > 1:
            series_num = parts[1].strip()
            return f"Chicago {series_num}"
    
    # NSTF format: "Club SNumber" or "Club SNumberLetter" (e.g., S1, S2A, S2B)
    elif re.search(r'S(\d+[A-Z]*)', team_name):
        match = re.search(r'S(\d+[A-Z]*)', team_name)
        if match:
            series_identifier = match.group(1)
            return f"Series {series_identifier}"
    
    # NSTF Sunday formats
    elif 'Sunday A' in team_name:
        return "Series A"
    elif 'Sunday B' in team_name:
        return "Series B"
    
    # Direct series name (already formatted)
    elif team_name.startswith('Series ') or team_name.startswith('Chicago '):
        return team_name
    
    return None

def extract_club_name_from_team(team_name):
    """
    Extract club name from team name, auto-detecting APTA vs NSTF format.
    
    Args:
        team_name (str): Team name in various formats
        
    Returns:
        str: Club name
        
    Examples:
        APTA: "Birchwood - 6" -> "Birchwood"
        NSTF: "Birchwood S1" -> "Birchwood"
        NSTF: "Wilmette Sunday A" -> "Wilmette"
    """
    if not team_name:
        return "Unknown"
        
    team_name = team_name.strip()
    
    # APTA format: "Club - Number"
    if ' - ' in team_name:
        return team_name.split(' - ')[0].strip()
    
    # NSTF format: "Club SNumber" or "Club SNumberLetter" (e.g., S1, S2A, S2B)
    elif re.search(r'S\d+[A-Z]*', team_name):
        return re.sub(r'\s+S\d+[A-Z]*.*$', '', team_name).strip()
    
    # NSTF Sunday format: "Club Sunday A/B"
    elif 'Sunday' in team_name:
        club_name = team_name.replace('Sunday A', '').replace('Sunday B', '').strip()
        return club_name if club_name else team_name
    
    # Fallback: use the team name as-is
    return team_name

def build_league_data_dir(league_id):
    """
    Build the dynamic data directory path based on the league ID.
    
    Args:
        league_id (str): The league identifier
        
    Returns:
        str: The data directory path (e.g., 'data/leagues/APTACHICAGO')
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up two levels: scrapers -> etl -> project_root
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    league_data_dir = os.path.join(project_root, 'data', 'leagues', league_id)
    os.makedirs(league_data_dir, exist_ok=True)
    
    return league_data_dir

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

# Removed active_series functionality - now processes all discovered series

def get_player_stats(player_url, driver, config, max_retries=3, retry_delay=2):
    """Get detailed player statistics including match history."""
    for attempt in range(max_retries):
        try:
            # Use dynamic league configuration
            base_url = config['base_url']
            full_url = f"{base_url}{player_url}" if not player_url.startswith('http') else player_url
            
            # Verify driver health before making request
            try:
                driver.current_url
            except Exception:
                raise Exception("Driver session is invalid")
                
            driver.get(full_url)
            time.sleep(retry_delay)

            wins = 0
            losses = 0
            match_details = []  # List of dicts: {date, end_pti, series}

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Extract match info from rbox_top divs
            for rbox in soup.find_all('div', class_='rbox_top'):
                # Date
                date_div = rbox.find('div', class_='rbox_inner')
                match_date = None
                if date_div:
                    date_text = date_div.get_text(strip=True)
                    match_date = date_text.split()[0] if date_text else None

                # Series
                series_div = rbox.find_all('div', class_='rbox_inner')
                match_series = None
                if len(series_div) > 1:
                    match_series = series_div[1].get_text(strip=True)
                    if ' - ' in match_series:
                        match_series = match_series.split(' - ')[0]

                # End PTI
                end_pti = None
                for pti_div in rbox.find_all('div', class_='rbox3top'):
                    if 'End' in pti_div.get_text():
                        span = pti_div.find('span', class_='demi')
                        if span:
                            end_pti = span.get_text(strip=True)

                if match_date and end_pti and match_series:
                    match_details.append({
                        'date': match_date,
                        'end_pti': end_pti,
                        'series': match_series
                    })

            # Count wins and losses
            content = driver.find_element(By.TAG_NAME, "body").text
            matches = content.split('\n')
            for line in matches:
                if line.strip() == 'W':
                    wins += 1
                elif line.strip() == 'L':
                    losses += 1

            return {
                'Wins': wins,
                'Losses': losses,
                'Win %': f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%",
                'match_details': match_details
            }

        except Exception as e:
            print(f"Error getting player stats (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached, returning default stats")
                return {'Wins': 0, 'Losses': 0, 'Win %': '0.0%', 'match_details': []}

def scrape_player_history(league_subdomain):
    """
    Main function to scrape and save player history data using dynamic discovery.
    
    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
    """
    # Record start time
    start_time = datetime.now()
    print(f"🕐 Session Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track timing milestones
    discovery_start_time = None
    scraping_start_time = None
    
    try:
        # Load league configuration from user input
        config = get_league_config(league_subdomain)
        league_id = config['league_id']
        
        print(f"🌟 Processing ALL discovered series from {config['subdomain']} dynamically")
        print("No filtering - comprehensive discovery and processing of all players")

        # Use context manager to ensure Chrome driver is properly closed
        with ChromeManager() as driver:
            
            # Create dynamic data directory based on league
            data_dir = build_league_data_dir(league_id)
            
            print(f"🚀 Starting {config['subdomain'].upper()} Player History Scraper")
            print(f"📊 Target: All Discovered Players")
            print("=" * 60)
            
            # Discover all available data dynamically
            discovery_start_time = datetime.now()
            print(f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}")
            discovery_results = discover_all_leagues_and_series(driver, config)
            discovery_end_time = datetime.now()
            discovery_duration = discovery_end_time - discovery_start_time
            print(f"✅ Discovery Phase Complete: {discovery_duration.total_seconds():.1f} seconds")
            
            # Navigate to player page with dynamic URL
            player_page_url = f"{config['base_url']}/?mod={config['player_page_mod']}"
            print(f"\n📄 Navigating to player page: {player_page_url}")
            driver.get(player_page_url)
            time.sleep(3)
            
            # Get the page source after JavaScript has run
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all player rows
            all_rows = []
            for table in soup.find_all('table'):
                for row in table.find_all('tr')[1:]:  # Skip header row
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        all_rows.append(row)
            
            print(f"📋 Found {len(all_rows)} total players to process")
            
            # Initialize tracking variables
            all_players_json = []
            processed_series = set()
            
            scraping_start_time = datetime.now()
            print(f"⚡ Scraping Phase Start: {scraping_start_time.strftime('%H:%M:%S')}")
            
            # Process each player row
            for row_idx, row in enumerate(all_rows, 1):
                player_start_time = datetime.now()
                progress_percent = (row_idx / len(all_rows)) * 100
                elapsed = player_start_time - start_time
                print(f"\n=== Player {row_idx}/{len(all_rows)} ({progress_percent:.1f}%) | Elapsed: {elapsed} ===")
                
                cells = row.find_all('td')
                
                # Extract basic player information
                first_name = cells[0].text.strip() if len(cells) > 0 else "Unknown"
                last_name = cells[1].text.strip() if len(cells) > 1 else "Unknown"
                rating = cells[2].text.strip() if len(cells) > 2 else "N/A"
                
                # Skip players with BYE in their name (placeholder players)
                if 'BYE' in first_name.upper() or 'BYE' in last_name.upper():
                    print(f"   Skipping BYE player: {first_name} {last_name}")
                    continue
                
                # Extract series and club information from row classes or data
                series_name = "Unknown"
                club_name = "Unknown"
                
                # Try to extract series from class names or other attributes
                row_classes = row.get('class', [])
                for cls in row_classes:
                    if cls.startswith('diver_'):
                        # This might be a division ID, we can use it to determine series
                        division_id = cls.replace('diver_', '')
                        # For now, we'll just use "Series" + ID as a fallback
                        series_name = f"Series {division_id}"
                        break
                    elif cls.startswith('loc_'):
                        # This might be a location/club ID
                        location_id = cls.replace('loc_', '')
                        club_name = f"Club {location_id}"
                        break
                
                # Get link for detailed stats and extract native TennisScores ID
                link = row.find('a')
                stats = {'Wins': 0, 'Losses': 0, 'Win %': '0.0%', 'match_details': []}
                
                if link:
                    href = link.get('href', '')
                    # Extract native TennisScores player ID from URL
                    tenniscores_id = extract_tenniscores_player_id(href)
                    # Generate Player ID using TennisScores native ID (preferred) or fallback
                    player_id = create_player_id(tenniscores_id, first_name, last_name, club_name)
                    
                    try:
                        print(f"   🔍 Getting detailed stats for {first_name} {last_name}")
                        stats = get_player_stats(href, driver, config)
                        print(f"   ✅ Stats: W/L: {stats['Wins']}-{stats['Losses']} ({stats['Win %']})")
                    except Exception as e:
                        print(f"   ❌ Error getting stats: {e}")
                else:
                    # Fallback ID generation when no link available
                    player_id = create_player_id(None, first_name, last_name, club_name)
                
                # Create player info for JSON
                player_json = {
                    "league_id": league_id,
                    "player_id": player_id,
                    "name": f"{first_name} {last_name}",
                    "first_name": first_name,
                    "last_name": last_name,
                    "series": series_name,
                    "club": club_name,
                    "rating": float(rating) if rating.replace('.', '', 1).isdigit() else rating,
                    "wins": stats['Wins'],
                    "losses": stats['Losses'],
                    "matches": [
                        {
                            "date": m['date'],
                            "end_pti": float(m['end_pti']) if str(m['end_pti']).replace('.', '', 1).isdigit() else m['end_pti'],
                            "series": m['series']
                        } for m in stats.get('match_details', [])
                    ]
                }
                all_players_json.append(player_json)
                
                processed_series.add(series_name)
                
                player_end_time = datetime.now()
                player_duration = player_end_time - player_start_time
                
                # Progress update with timing
                remaining_players = len(all_rows) - row_idx
                avg_time_per_player = (player_start_time - scraping_start_time).total_seconds() / row_idx if scraping_start_time and row_idx > 0 else 0
                estimated_remaining = remaining_players * avg_time_per_player if avg_time_per_player > 0 else 0
                eta = player_end_time + timedelta(seconds=estimated_remaining) if estimated_remaining > 0 else None
                
                print(f"✅ Player completed in {player_duration.total_seconds():.1f}s | Progress: {row_idx}/{len(all_rows)} players")
                if eta:
                    print(f"   ⏰ ETA: {eta.strftime('%H:%M:%S')} (est. {estimated_remaining/60:.1f} min remaining)")
                
                # Small delay between players
                time.sleep(1)
            
            # Save all players to JSON
            filename = os.path.join(data_dir, 'player_history.json')
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(all_players_json, jsonfile, indent=2)
            
            # Calculate end time and duration
            end_time = datetime.now()
            total_duration = end_time - start_time
            scraping_end_time = end_time
            scraping_duration = scraping_end_time - scraping_start_time if scraping_start_time else total_duration
            
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
            players_per_minute = (len(all_players_json) / total_seconds * 60) if total_seconds > 0 else 0
            
            print(f"📊 PERFORMANCE METRICS")
            print(f"📈 Total players scraped: {len(all_players_json)}")
            print(f"👥 Players per minute: {players_per_minute:.1f}")
            print(f"⚡ Average time per player: {total_seconds/len(all_players_json):.1f}s" if len(all_players_json) > 0 else "⚡ Average time per player: N/A")
            print()
            
            print(f"💾 Data saved to: {filename}")
            print(f"📈 Processed series: {', '.join(sorted(processed_series))}")
            
            # Print summary by series
            print(f"\n📈 SERIES BREAKDOWN:")
            series_counts = {}
            for player in all_players_json:
                series = player['series']
                series_counts[series] = series_counts.get(series, 0) + 1
            
            for series, count in sorted(series_counts.items()):
                percentage = (count / len(all_players_json) * 100) if len(all_players_json) > 0 else 0
                print(f"  {series}: {count} players ({percentage:.1f}%)")
            
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

if __name__ == "__main__":
    print("🎾 TennisScores Player History Scraper - Dynamic Discovery Mode")
    print("=" * 60)
    print("🔍 Dynamically discovering ALL players from any TennisScores website")
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
    
    print("📈 Comprehensive player history scraping mode")
    print("   Will collect detailed match history and statistics for all players")
    print()
    
    scrape_player_history(league_subdomain)
    print(f"\n✅ Player history scraping complete for {league_subdomain.upper()}!")
