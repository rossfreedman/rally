import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import platform
from contextlib import contextmanager
import json
import re
import hashlib
from urllib.parse import urljoin, parse_qs, urlparse
import sys
# Navigate up three levels: etl/scrapers -> etl -> project_root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.player_id_utils import extract_tenniscores_player_id, create_player_id

def standardize_league_id(subdomain):
    """
    Standardize league ID format to match database expectations.
    
    Args:
        subdomain (str): The subdomain (e.g., 'aptachicago', 'nstf')
        
    Returns:
        str: Standardized league ID (e.g., 'APTA_CHICAGO', 'NSTF')
    """
    subdomain_lower = subdomain.lower()
    
    # Map subdomains to standardized league IDs
    mapping = {
        'aptachicago': 'APTA_CHICAGO',
        'aptanational': 'APTA_NATIONAL', 
        'nstf': 'NSTF'
    }
    
    return mapping.get(subdomain_lower, subdomain.upper())

def is_platform_tennis_league(subdomain):
    """
    Determine if a league is a platform tennis league (has PTI) or regular tennis league (no PTI).
    
    Args:
        subdomain (str): The subdomain (e.g., 'aptachicago', 'nstf', 'cita')
        
    Returns:
        bool: True if platform tennis league (has PTI), False if tennis league (no PTI)
    """
    subdomain_lower = subdomain.lower()
    
    # Platform tennis leagues that have PTI
    platform_tennis_leagues = {
        'aptachicago',
        'aptanational', 
        'nstf'
    }
    
    return subdomain_lower in platform_tennis_leagues

# Dynamic League Configuration - User Input Based
def get_league_config(league_subdomain=None):
    """Get dynamic league configuration based on user input"""
    if not league_subdomain:
        # This will be passed from the main function
        raise ValueError("League subdomain must be provided")
    
    base_url = build_base_url(league_subdomain)
    
    return {
        'league_id': standardize_league_id(league_subdomain),
        'subdomain': league_subdomain,
        'base_url': base_url,
        'main_page': f'{base_url}/?mod=nndz-TjJiOWtOR2sxTnhI',
        'player_page_mod': 'nndz-SkhmOW1PQ3V4Zz09',
        'team_page_mod': 'nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D'
    }

# Note: Hardcoded division and location lookups have been removed
# All leagues/series/divisions are now discovered dynamically from the site

# Removed file-based configuration functions - now using user input

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
    # Navigate up two levels: etl/scrapers -> etl -> project_root
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    league_data_dir = os.path.join(project_root, 'data', 'leagues', league_id)
    os.makedirs(league_data_dir, exist_ok=True)
    
    return league_data_dir

# Removed active_series functionality - now processes all discovered series

def discover_all_leagues_and_series(driver, config, max_exploration_pages=5):
    """
    Comprehensively discover all leagues, series, divisions, and locations 
    dynamically from the target website without relying on hardcoded values.
    
    Args:
        driver: Chrome WebDriver instance
        config: League configuration dictionary
        max_exploration_pages (int): Maximum number of pages to explore for discovery
        
    Returns:
        dict: Comprehensive discovery results containing:
            - 'teams': mapping of team names to team IDs
            - 'series': set of all discovered series names
            - 'divisions': mapping of division IDs to division names (if found)
            - 'locations': mapping of location IDs to location names (if found)
            - 'clubs': set of all discovered club names
    """
    print(f"🔍 Starting comprehensive site discovery for {config['subdomain']} website...")
    
    discovery_results = {
        'teams': {},
        'series': set(),
        'divisions': {},
        'locations': {},
        'clubs': set()
    }
    
    visited_urls = set()
    
    try:
        # Start with the main league page
        print(f"📄 Exploring main page: {config['main_page']}")
        driver.get(config['main_page'])
        time.sleep(3)
        
        # Get page source and parse
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 1. Discover teams and extract series/clubs from team names
        print("🏆 Discovering teams and extracting series information...")
        team_links = soup.find_all('a', href=re.compile(r'team='))
        
        for link in team_links:
            href = link.get('href', '')
            team_name = link.text.strip()
            
            # Extract team ID from URL
            team_match = re.search(r'team=([^&]+)', href)
            if team_match and team_name:
                # Skip BYE teams - they are placeholders with no actual players
                if 'BYE' in team_name.upper():
                    print(f"  Skipping BYE team: {team_name}")
                    continue
                    
                team_id = team_match.group(1)
                
                # Store team mapping
                discovery_results['teams'][team_name] = team_id
                
                # Extract series name using existing helper function
                series_name = extract_series_name_from_team(team_name)
                if series_name:
                    discovery_results['series'].add(series_name)
                    print(f"  Found series: {series_name} (from team: {team_name})")
                
                # Extract club name using existing helper function
                club_name = extract_club_name_from_team(team_name)
                if club_name and club_name != "Unknown":
                    discovery_results['clubs'].add(club_name)
        
        initial_teams_found = len(discovery_results['teams'])
        print(f"✅ Discovered {initial_teams_found} teams from main page")
        
        # 2. NEW: Explore navigation links to find series/division pages
        print("\n🧭 Exploring navigation and menu links for additional team pages...")
        nav_links = soup.find_all('a', href=True)
        division_links = []
        location_links = []
        potential_team_pages = []
        
        for link in nav_links:
            href = link.get('href', '')
            link_text = link.text.strip().lower()
            
            # Look for division/series related links
            if any(keyword in href.lower() for keyword in ['division', 'league', 'standings', 'series']):
                division_links.append((href, link_text))
            
            # Look for location-related links  
            if any(keyword in href.lower() for keyword in ['location', 'venue', 'club']):
                location_links.append((href, link_text))
            
            # Look for links that might contain more teams
            if any(keyword in link_text for keyword in ['standings', 'teams', 'series', 'division', 'schedule']):
                full_url = urljoin(config['base_url'], href) if not href.startswith('http') else href
                if full_url not in visited_urls:
                    potential_team_pages.append((full_url, link_text))
        
        # 3. NEW: Explore potential team pages
        explored_pages = 0
        for page_url, page_description in potential_team_pages[:max_exploration_pages]:
            if explored_pages >= max_exploration_pages:
                break
                
            try:
                print(f"  🔍 Exploring potential team page: {page_description} ({page_url})")
                driver.get(page_url)
                time.sleep(2)
                visited_urls.add(page_url)
                explored_pages += 1
                
                page_soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Look for team links on this page
                page_team_links = page_soup.find_all('a', href=re.compile(r'team='))
                teams_found_on_page = 0
                
                for link in page_team_links:
                    href = link.get('href', '')
                    team_name = link.text.strip()
                    
                    # Extract team ID from URL
                    team_match = re.search(r'team=([^&]+)', href)
                    if team_match and team_name and team_name not in discovery_results['teams']:
                        # Skip BYE teams - they are placeholders with no actual players
                        if 'BYE' in team_name.upper():
                            print(f"    Skipping BYE team: {team_name}")
                            continue
                            
                        team_id = team_match.group(1)
                        
                        # Store team mapping
                        discovery_results['teams'][team_name] = team_id
                        teams_found_on_page += 1
                        
                        # Extract series name using existing helper function
                        series_name = extract_series_name_from_team(team_name)
                        if series_name:
                            discovery_results['series'].add(series_name)
                            print(f"    Found NEW series: {series_name} (from team: {team_name})")
                        
                        # Extract club name using existing helper function
                        club_name = extract_club_name_from_team(team_name)
                        if club_name and club_name != "Unknown":
                            discovery_results['clubs'].add(club_name)
                
                if teams_found_on_page > 0:
                    print(f"    ✅ Found {teams_found_on_page} new teams on this page")
                else:
                    print(f"    ℹ️ No new teams found on this page")
                    
            except Exception as e:
                print(f"    ❌ Error exploring page {page_description}: {str(e)}")
                continue
        
        # 4. NEW: Try common URL patterns for different series
        print(f"\n🎯 Trying common URL patterns for different series...")
        
        # Try to access different series directly by modifying URL parameters
        base_url_parts = urlparse(config['main_page'])
        query_params = parse_qs(base_url_parts.query)
        
        # Common patterns to try
        patterns_to_try = [
            # Try different mod parameters that might show different series
            {'mod': ['nndz-TjJiOWtOR2sxTnhI', 'nndz-TjJROWJOR2sxTnhI', 'nndz-TjJqOWtOR2sxTnhI']},
            # Try adding series/division parameters
            {'series': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25']},
            {'division': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']},
        ]
        
        pattern_urls_tried = 0
        max_pattern_attempts = 10  # Limit pattern attempts to avoid infinite loops
        
        for pattern_dict in patterns_to_try:
            if pattern_urls_tried >= max_pattern_attempts:
                break
                
            for param_name, param_values in pattern_dict.items():
                for param_value in param_values[:5]:  # Limit to 5 values per parameter
                    if pattern_urls_tried >= max_pattern_attempts:
                        break
                        
                    try:
                        # Build URL with this parameter
                        test_params = query_params.copy()
                        test_params[param_name] = [param_value]
                        
                        # Construct URL
                        new_query = '&'.join([f"{k}={v[0]}" for k, v in test_params.items()])
                        test_url = f"{config['base_url']}/?{new_query}"
                        
                        if test_url not in visited_urls:
                            print(f"  🧪 Testing URL pattern: {param_name}={param_value}")
                            driver.get(test_url)
                            time.sleep(1)
                            visited_urls.add(test_url)
                            pattern_urls_tried += 1
                            
                            pattern_soup = BeautifulSoup(driver.page_source, 'html.parser')
                            pattern_team_links = pattern_soup.find_all('a', href=re.compile(r'team='))
                            
                            new_teams_from_pattern = 0
                            for link in pattern_team_links:
                                href = link.get('href', '')
                                team_name = link.text.strip()
                                
                                team_match = re.search(r'team=([^&]+)', href)
                                if team_match and team_name and team_name not in discovery_results['teams']:
                                    # Skip BYE teams - they are placeholders with no actual players
                                    if 'BYE' in team_name.upper():
                                        print(f"      Skipping BYE team: {team_name}")
                                        continue
                                        
                                    team_id = team_match.group(1)
                                    discovery_results['teams'][team_name] = team_id
                                    new_teams_from_pattern += 1
                                    
                                    series_name = extract_series_name_from_team(team_name)
                                    if series_name:
                                        discovery_results['series'].add(series_name)
                                        print(f"      🎉 Pattern found NEW series: {series_name} (team: {team_name})")
                            
                            if new_teams_from_pattern > 0:
                                print(f"      ✅ Pattern yielded {new_teams_from_pattern} new teams")
                                
                    except Exception as e:
                        print(f"      ❌ Error testing pattern {param_name}={param_value}: {str(e)}")
                        continue
        
        print(f"✅ Discovered {len(discovery_results['teams'])} teams")
        print(f"✅ Discovered {len(discovery_results['series'])} series: {sorted(discovery_results['series'])}")
        print(f"✅ Discovered {len(discovery_results['clubs'])} clubs")
        
        # 5. Explore a few team pages to discover additional structure (existing logic)
        print(f"\n🔬 Deep-diving into {min(3, len(discovery_results['teams']))} team pages for additional discovery...")
        sample_teams = list(discovery_results['teams'].items())[:3]
        
        for team_name, team_id in sample_teams:
            try:
                team_url = f"{config['base_url']}/?mod={config['team_page_mod']}&team={team_id}"
                print(f"  📊 Exploring team page: {team_name}")
                
                driver.get(team_url)
                time.sleep(2)
                
                team_soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Look for additional structural information in team pages
                # This might include division info, location details, etc.
                
                # Extract any ID mappings that might be present
                all_links_on_page = team_soup.find_all('a', href=True)
                for link in all_links_on_page:
                    href = link.get('href', '')
                    
                    # Look for division IDs in URLs
                    division_match = re.search(r'division=([^&]+)', href)
                    if division_match:
                        div_id = division_match.group(1)
                        div_name = link.text.strip()
                        if div_name and div_id not in discovery_results['divisions']:
                            discovery_results['divisions'][div_id] = div_name
                            print(f"    Found division: {div_id} -> {div_name}")
                    
                    # Look for location IDs in URLs
                    location_match = re.search(r'location=([^&]+)', href)
                    if location_match:
                        loc_id = location_match.group(1)
                        loc_name = link.text.strip()
                        if loc_name and loc_id not in discovery_results['locations']:
                            discovery_results['locations'][loc_id] = loc_name
                            print(f"    Found location: {loc_id} -> {loc_name}")
                
            except Exception as e:
                print(f"    ❌ Error exploring team {team_name}: {str(e)}")
                continue
        
        # 6. Summary of discovery
        total_teams_discovered = len(discovery_results['teams'])
        new_teams_from_exploration = total_teams_discovered - initial_teams_found
        
        print(f"\n📊 DISCOVERY SUMMARY:")
        print(f"  🏆 Teams: {total_teams_discovered} (initial: {initial_teams_found}, new: {new_teams_from_exploration})")
        print(f"  📈 Series: {len(discovery_results['series'])} - {sorted(discovery_results['series'])}")
        print(f"  🏢 Clubs: {len(discovery_results['clubs'])}")
        print(f"  🏛️  Divisions: {len(discovery_results['divisions'])}")
        print(f"  📍 Locations: {len(discovery_results['locations'])}")
        
        # 7. NEW: Run comprehensive missing team search for known missing series
        print(f"\n🎯 Running comprehensive search for potentially missing teams...")
        
        # Common series that should exist but might be missing
        expected_series = [f"Chicago {i}" for i in range(1, 26)]  # Chicago 1-25
        missing_series = [series for series in expected_series if series not in discovery_results['series']]
        
        if missing_series:
            print(f"   🔍 Found {len(missing_series)} potentially missing series: {missing_series[:10]}{'...' if len(missing_series) > 10 else ''}")
            
            # Try to find missing series (limit to first 5 to avoid excessive time)
            for missing_series_name in missing_series[:5]:
                print(f"   🎯 Searching specifically for: {missing_series_name}")
                new_teams = find_missing_teams_comprehensive(driver, config, discovery_results['teams'], missing_series_name)
                
                # Add newly found teams to discovery results
                for team_name, team_id in new_teams.items():
                    discovery_results['teams'][team_name] = team_id
                    series_name = extract_series_name_from_team(team_name)
                    if series_name:
                        discovery_results['series'].add(series_name)
                        print(f"      🎉 ADDED MISSING SERIES: {series_name} (team: {team_name})")
                    
                    club_name = extract_club_name_from_team(team_name)
                    if club_name and club_name != "Unknown":
                        discovery_results['clubs'].add(club_name)
                
                if new_teams:
                    print(f"      ✅ Found {len(new_teams)} teams for {missing_series_name}")
                else:
                    print(f"      ❌ No teams found for {missing_series_name}")
        else:
            print(f"   ✅ All expected series found, no missing series search needed")
        
        # Final summary after comprehensive search
        final_teams_discovered = len(discovery_results['teams'])
        teams_from_missing_search = final_teams_discovered - total_teams_discovered
        
        print(f"\n📊 FINAL DISCOVERY SUMMARY:")
        print(f"  🏆 Teams: {final_teams_discovered} (missing search added: {teams_from_missing_search})")
        print(f"  📈 Series: {len(discovery_results['series'])} - {sorted(discovery_results['series'])}")
        print(f"  🏢 Clubs: {len(discovery_results['clubs'])}")
        print(f"  🏛️  Divisions: {len(discovery_results['divisions'])}")
        print(f"  📍 Locations: {len(discovery_results['locations'])}")
        
        return discovery_results
        
    except Exception as e:
        print(f"❌ Error during site discovery: {str(e)}")
        return discovery_results

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


def get_player_stats(player_url, driver, config, max_retries=3, retry_delay=5):
    """
    Get player statistics using the provided driver instance.
    
    Args:
        player_url (str): URL to the player's stats page
        driver (webdriver): Chrome WebDriver instance
        config: League configuration dictionary
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay in seconds between retries
    
    Returns:
        dict: Player statistics including PTI, wins, losses, and win percentage
    """
    # Check if this is a platform tennis league (has PTI)
    is_platform_tennis = is_platform_tennis_league(config['subdomain'])
    
    for attempt in range(max_retries):
        try:
            base_url = config['base_url']
            full_url = f"{base_url}{player_url}" if not player_url.startswith('http') else player_url
            
            # Verify driver health before making request
            try:
                driver.current_url
            except Exception:
                raise Exception("Driver session is invalid")
                
            driver.get(full_url)
            time.sleep(retry_delay / 2)

            # Get page content and parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Use PlayerScraper for better extraction
            scraper = PlayerScraper(config)
            
            # Extract PTI only for platform tennis leagues
            pti_value = None
            if is_platform_tennis:
                # Method 1: Look for PTI in the main display area
                pti_spans = soup.find_all('span', class_='demi')
                for span in pti_spans:
                    style = span.get('style', '')
                    if 'font-size: 30px' in style or 'font-size:30px' in style:
                        parent = span.parent
                        if parent:
                            parent_text = parent.get_text()
                            if 'Paddle Tennis Index' in parent_text:
                                pti_text = span.get_text(strip=True)
                                try:
                                    pti_value = float(pti_text)
                                    if 10.0 <= pti_value <= 100.0:
                                        pti_value = str(pti_value)
                                        break
                                except ValueError:
                                    continue
                
                # Method 2: Look for PTI in match history tables
                if not pti_value:
                    tables = soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            for cell in cells:
                                text = cell.get_text(strip=True)
                                if 'Player End' in text:
                                    numbers = re.findall(r'\d+\.?\d*', text)
                                    if numbers:
                                        pti = float(numbers[0])
                                        if 10.0 <= pti <= 100.0:
                                            pti_value = str(pti)
                                            break
                                end_match = re.search(r'End(\d+\.?\d*)', text)
                                if end_match:
                                    pti = float(end_match.group(1))
                                    if 10.0 <= pti <= 100.0:
                                        pti_value = str(pti)
                                        break
                            if pti_value:
                                break
                        if pti_value:
                            break
            
            # Extract wins and losses using the improved scraper method
            wins, losses = scraper._extract_win_loss_stats(soup)
            
            # Calculate win percentage
            win_percentage = f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%"

            return {
                'PTI': pti_value or 'N/A',
                'Wins': str(wins),
                'Losses': str(losses),
                'Win %': win_percentage
            }

        except Exception as e:
            print(f"         Error getting player stats (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"         Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("         Max retries reached, returning default stats")
                return {'PTI': 'N/A', 'Wins': '0', 'Losses': '0', 'Win %': '0.0%'}


def discover_league_teams(driver, config):
    """
    Discover team IDs dynamically from the league main page.
    Now uses the comprehensive discovery function for better results.
    
    Args:
        driver: Chrome WebDriver instance
        config: League configuration dictionary
        
    Returns:
        dict: Mapping of team names to team IDs
    """
    print(f"🔍 Discovering team IDs from {config['subdomain']} website using comprehensive discovery...")
    
    try:
        # Use the comprehensive discovery function
        discovery_results = discover_all_leagues_and_series(driver, config)
        
        # Extract just the team mapping for backward compatibility
        team_mapping = discovery_results['teams']
        
        # Filter teams to only include those that look like series teams
        # This maintains the same filtering logic as before
        filtered_teams = {}
        for team_name, team_id in team_mapping.items():
            if team_name and (
                ' - ' in team_name or  # APTA Chicago format: "Birchwood - 6"
                'Chicago' in team_name or  # APTA Chicago format
                re.search(r'S\d+', team_name) or  # NSTF format: "Birchwood S1"
                'Series' in team_name or  # NSTF format: "Series 1"
                'Sunday' in team_name  # NSTF format: "Wilmette Sunday A"
            ):
                # Skip BYE teams - they are placeholders with no actual players
                if 'BYE' in team_name.upper():
                    print(f"  Skipping BYE team: {team_name}")
                    continue
                    
                filtered_teams[team_name] = team_id
                print(f"  Found: {team_name} -> {team_id}")
        
        print(f"✅ Discovered {len(filtered_teams)} teams (filtered from {len(team_mapping)} total)")
        return filtered_teams
        
    except Exception as e:
        print(f"❌ Error discovering team IDs: {str(e)}")
        return {}

def scrape_team_players(team_id, driver, team_name, league_id, config):
    """
    Scrape players for a specific team using the NSTF-inspired approach.
    
    Args:
        team_id (str): Team ID for the URL
        team_name (str): Team name for display
        driver: Chrome WebDriver instance
        league_id (str): League identifier
        config: League configuration dictionary
    
    Returns:
        list: List of player dictionaries
    """
    scraped_players = []
    
    try:
        # Build team URL from team ID using dynamic configuration
        team_url = f"{config['base_url']}/?mod={config['team_page_mod']}&team={team_id}"
        print(f"\n🏆 Scraping team: {team_name}")
        print(f"   URL: {team_url}")
        
        # Use the driver to get the page
        driver.get(team_url)
        time.sleep(3)  # Wait for page to load
        
        # Get page source and parse
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract series name using helper function (auto-detects APTA vs NSTF format)
        series_name = extract_series_name_from_team(team_name)
        
        if not series_name:
            print(f"   ⚠️ Could not determine series from team name: {team_name}")
            return scraped_players
        
        # Find all player links - look for various patterns similar to NSTF
        player_link_patterns = [
            r'player\.php',    # Standard player.php links
            r'uid=',           # UID-based links
            r'player=',        # Player parameter
            r'player_id=',     # Player ID parameter
        ]
        
        all_links = soup.find_all('a', href=True)
        player_links = []
        
        for link in all_links:
            href = link.get('href', '')
            for pattern in player_link_patterns:
                if re.search(pattern, href):
                    player_links.append(link)
                    break
        
        print(f"   Found {len(player_links)} player links")
        
        # If no player links found, try to find player names in tables
        if not player_links:
            print("   🔍 No player links found, searching for player names in tables...")
            
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        # Look for name patterns (First Last)
                        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', cell_text):
                            # Create a fake link object for consistency
                            class FakeLink:
                                def __init__(self, text, parent_cell):
                                    self.text = text
                                    self.parent = parent_cell
                                
                                def get_text(self, strip=False):
                                    return self.text.strip() if strip else self.text
                                
                                def get(self, attr, default=None):
                                    return default
                            
                            fake_link = FakeLink(cell_text, cell)
                            player_links.append(fake_link)
        
        # Process each player link
        for i, link in enumerate(player_links):
            try:
                # Get player name from link text
                player_name = link.get_text(strip=True) if hasattr(link, 'get_text') else str(link)
                
                if not player_name or len(player_name) < 2:
                    continue
                
                # Split name into first and last
                name_parts = player_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                else:
                    first_name = player_name
                    last_name = ""
                
                # Extract player ID using TennisScores native ID
                href = link.get('href', '') if hasattr(link, 'get') else ''
                player_url = None  # Store the URL temporarily for PTI extraction
                
                # Extract native TennisScores player ID
                tenniscores_id = extract_tenniscores_player_id(href)
                
                # Create player ID using native TennisScores ID (preferred) or fallback
                club_name = extract_club_name_from_team(team_name)
                player_id = create_player_id(tenniscores_id, first_name, last_name, club_name)
                
                # Store the full URL for PTI extraction
                if href:
                    if href.startswith('http'):
                        player_url = href
                    else:
                        player_url = f"{config['base_url']}{href}" if href.startswith('/') else f"{config['base_url']}/{href}"
                
                # Look for captain designation
                parent_text = ""
                if hasattr(link, 'parent') and link.parent:
                    parent_text = link.parent.get_text()
                
                is_captain = "(C)" in parent_text
                is_co_captain = "(CC)" in parent_text
                
                # Extract club name using helper function (auto-detects APTA vs NSTF format)
                club_name = extract_club_name_from_team(team_name)
                
                # Create player info matching NSTF format
                player_info = {
                    'League': league_id,
                    'Series': series_name,
                    'Series Mapping ID': team_name,  # Full team name like "Birchwood - 6"
                    'Club': club_name,
                    'Location ID': f'{club_name.upper().replace(" ", "_").replace("-", "_").replace("&", "AND")}',
                    'Player ID': player_id,
                    'First Name': first_name,
                    'Last Name': last_name,
                    'PTI': 'N/A',  # Will be updated if detailed stats requested
                    'Wins': '0',
                    'Losses': '0',
                    'Win %': '0.0%',
                    'Captain': '',  # Default to empty, will be updated below if applicable
                    '_temp_url': player_url  # Temporary field for PTI extraction, will be removed later
                }
                
                # Add captain info if present
                if is_captain or is_co_captain:
                    player_info['Captain'] = 'C' if is_captain else 'CC'
                
                # Add to scraped players list
                scraped_players.append(player_info)
                
                print(f"    Player {i+1}: {first_name} {last_name} | {club_name} | ID: {player_id} | {'Captain' if is_captain else 'Co-Captain' if is_co_captain else 'Player'}")
                
            except Exception as e:
                print(f"    ❌ Error processing player {i+1}: {str(e)}")
                continue
        
        print(f"✅ Completed {team_name}: {len(scraped_players)} players")
        
    except Exception as e:
        print(f"❌ Error scraping team {team_name}: {str(e)}")
    
    return scraped_players

def scrape_league_players(league_subdomain, get_detailed_stats=False):
    """
    Main function to scrape league players using team-by-team approach.
    Works with any TennisScores league by subdomain.
    
    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
        get_detailed_stats (bool): Whether to scrape detailed player statistics
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
        print("No filtering - comprehensive discovery and processing of all teams/series")

        # Use context manager to ensure Chrome driver is properly closed
        with ChromeManager() as driver:
            
            # Create dynamic data directory based on league
            data_dir = build_league_data_dir(league_id)
            
            print(f"🚀 Starting {config['subdomain'].upper()} Player Scraper (Team-by-Team Mode)")
            print(f"📊 Target Series: All Discovered Series")
            print(f"📈 Detailed Stats: {'Yes' if get_detailed_stats else 'No (faster)'}")
            print("=" * 60)
            
            # Discover team IDs dynamically
            discovery_start_time = datetime.now()
            print(f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}")
            team_mapping = discover_league_teams(driver, config)
            discovery_end_time = datetime.now()
            discovery_duration = discovery_end_time - discovery_start_time
            print(f"✅ Discovery Phase Complete: {discovery_duration.total_seconds():.1f} seconds")
            
            if not team_mapping:
                print("❌ Could not discover team IDs. Exiting.")
                return []
            
            # Process ALL discovered teams (no filtering)
            print(f"\n🌟 Processing ALL discovered teams")
            teams_to_scrape = team_mapping
            
            # Show what series will be processed
            all_series = set()
            for team_name in team_mapping.keys():
                series_name = extract_series_name_from_team(team_name)
                if series_name:
                    all_series.add(series_name)
            print(f"📈 Will process {len(all_series)} series: {sorted(all_series)}")
            
            print(f"\n📋 Teams to scrape: {len(teams_to_scrape)}")
            for team_name in sorted(teams_to_scrape.keys()):
                print(f"  - {team_name}")
            
            # Initialize tracking variables
            all_players = []
            total_teams = len(teams_to_scrape)
            processed_series = set()
            
            print(f"\n📋 Scraping {total_teams} teams...")
            scraping_start_time = datetime.now()
            print(f"⚡ Scraping Phase Start: {scraping_start_time.strftime('%H:%M:%S')}")
            
            # Scrape each team
            for team_num, (team_name, team_id) in enumerate(teams_to_scrape.items(), 1):
                team_start_time = datetime.now()
                progress_percent = (team_num / total_teams) * 100
                elapsed = team_start_time - start_time
                print(f"\n=== Team {team_num}/{total_teams} ({progress_percent:.1f}%) | Elapsed: {elapsed} ===")
                
                team_players = scrape_team_players(team_id, driver, team_name, league_id, config)
                
                team_end_time = datetime.now()
                team_duration = team_end_time - team_start_time
                
                # Add PTI extraction if detailed stats requested
                if get_detailed_stats and team_players:
                    print(f"   🔍 Extracting detailed stats for {len(team_players)} players...")
                    
                    for player_idx, player in enumerate(team_players, 1):
                        # Use the temporarily stored URL for PTI extraction
                        player_url = player.get('_temp_url')
                        if player_url:
                            try:
                                player_progress = (player_idx / len(team_players)) * 100
                                print(f"      🔍 [{player_idx}/{len(team_players)} - {player_progress:.1f}%] Getting PTI for {player['First Name']} {player['Last Name']}")
                                # Use the WebDriver to get player stats instead of requests
                                stats = get_player_stats(player_url, driver, config)
                                if stats['PTI'] != "N/A":
                                    player.update(stats)
                                    print(f"         ✅ Updated stats: PTI={stats['PTI']}, W/L: {stats['Wins']}-{stats['Losses']} ({stats['Win %']})")
                                else:
                                    # Update just the W/L if PTI not found
                                    player['Wins'] = stats['Wins']
                                    player['Losses'] = stats['Losses'] 
                                    player['Win %'] = stats['Win %']
                                    print(f"         ⚠️  No PTI found, but got W/L: {stats['Wins']}-{stats['Losses']} ({stats['Win %']})")
                                    
                            except Exception as e:
                                print(f"         ❌ Error getting stats for {player['First Name']} {player['Last Name']}: {e}")
                                continue
                        else:
                            print(f"      ⚠️  No URL available for {player['First Name']} {player['Last Name']}")
                        
                        # Rate limiting
                        time.sleep(0.5)
                
                all_players.extend(team_players)
                
                # Track processed series
                for player in team_players:
                    processed_series.add(player['Series'])
                
                # Progress update with timing
                remaining_teams = total_teams - team_num
                avg_time_per_team = (team_start_time - scraping_start_time).total_seconds() / team_num if scraping_start_time and team_num > 0 else 0
                estimated_remaining = remaining_teams * avg_time_per_team if avg_time_per_team > 0 else 0
                eta = team_end_time + timedelta(seconds=estimated_remaining) if estimated_remaining > 0 else None
                
                print(f"✅ Team completed in {team_duration.total_seconds():.1f}s | Progress: {team_num}/{total_teams} teams, {len(all_players)} players")
                if eta:
                    print(f"   ⏰ ETA: {eta.strftime('%H:%M:%S')} (est. {estimated_remaining/60:.1f} min remaining)")
                
                # Small delay between teams
                time.sleep(2)
            
            # Remove temporary URLs from all players before saving
            for player in all_players:
                if '_temp_url' in player:
                    del player['_temp_url']
            
            # Save all players to JSON with same filename
            filename = os.path.join(data_dir, 'players.json')
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(all_players, jsonfile, indent=2)
            
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
            teams_per_minute = (total_teams / total_seconds * 60) if total_seconds > 0 else 0
            players_per_minute = (len(all_players) / total_seconds * 60) if total_seconds > 0 else 0
            
            print(f"📊 PERFORMANCE METRICS")
            print(f"📈 Total players scraped: {len(all_players)}")
            print(f"🏆 Total teams processed: {total_teams}")
            print(f"📈 Teams per minute: {teams_per_minute:.1f}")
            print(f"👥 Players per minute: {players_per_minute:.1f}")
            print(f"⚡ Average time per team: {total_seconds/total_teams:.1f}s" if total_teams > 0 else "⚡ Average time per team: N/A")
            print(f"⚡ Average time per player: {total_seconds/len(all_players):.1f}s" if len(all_players) > 0 else "⚡ Average time per player: N/A")
            print()
            
            print(f"💾 Data saved to: {filename}")
            print(f"📈 Processed series: {', '.join(sorted(processed_series))}")
            
            # Print summary by series
            print(f"\n📈 SERIES BREAKDOWN:")
            series_counts = {}
            for player in all_players:
                series = player['Series']
                series_counts[series] = series_counts.get(series, 0) + 1
            
            for series, count in sorted(series_counts.items()):
                percentage = (count / len(all_players) * 100) if len(all_players) > 0 else 0
                print(f"  {series}: {count} players ({percentage:.1f}%)")
            
            print("=" * 70)
            
            return all_players

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
        return []


class PlayerScraper:
    def __init__(self, config):
        self.base_url = config['base_url']
        self.subdomain = config['subdomain']
        self.is_platform_tennis = is_platform_tennis_league(self.subdomain)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.players_data = []
        self.failed_pti_extractions = []
        self.successful_pti_extractions = 0

    def extract_player_stats(self, player_url, retries=3):
        """Extract detailed stats including current PTI, wins, losses from individual player page"""
        for attempt in range(retries):
            try:
                print(f"         🔍 Extracting stats from: {player_url} (Attempt {attempt + 1})")
                
                response = self.session.get(player_url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract PTI only for platform tennis leagues
                pti_value = None
                if self.is_platform_tennis:
                    pti_value = self._extract_pti_from_matches(soup)
                    if not pti_value:
                        pti_value = self._extract_pti_from_summary(soup)
                    if not pti_value:
                        pti_value = self._extract_pti_patterns(soup)
                
                # Extract wins/losses from the page
                wins, losses = self._extract_win_loss_stats(soup)
                win_percentage = f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%"
                
                stats = {
                    'PTI': pti_value if pti_value else "N/A",
                    'Wins': str(wins),
                    'Losses': str(losses),
                    'Win %': win_percentage
                }
                
                if self.is_platform_tennis:
                    if pti_value:
                        print(f"         ✅ Found PTI: {pti_value}, W/L: {wins}-{losses} ({win_percentage})")
                        self.successful_pti_extractions += 1
                    else:
                        print(f"         ⚠️ No PTI found, but got W/L: {wins}-{losses} ({win_percentage})")
                        self.failed_pti_extractions.append(player_url)
                else:
                    print(f"         ✅ Tennis league - skipping PTI, got W/L: {wins}-{losses} ({win_percentage})")
                
                return stats
                
            except requests.exceptions.RequestException as e:
                print(f"         ❌ Request error (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    if self.is_platform_tennis:
                        self.failed_pti_extractions.append(player_url)
                    return {'PTI': "N/A", 'Wins': "0", 'Losses': "0", 'Win %': "0.0%"}
            except Exception as e:
                print(f"         ❌ Unexpected error: {e}")
                if self.is_platform_tennis:
                    self.failed_pti_extractions.append(player_url)
                return {'PTI': "N/A", 'Wins': "0", 'Losses': "0", 'Win %': "0.0%"}

    def _extract_pti_from_matches(self, soup):
        """Extract PTI from the most recent match in match history"""
        try:
            # Method 1: Look for the main PTI display at the top of the page
            # Look for span with class "demi" and large font-size that contains PTI
            pti_spans = soup.find_all('span', class_='demi')
            for span in pti_spans:
                style = span.get('style', '')
                if 'font-size: 30px' in style or 'font-size:30px' in style:
                    # Check if this is followed by "Paddle Tennis Index"
                    next_elements = span.find_next_siblings()
                    parent = span.parent
                    if parent:
                        parent_text = parent.get_text()
                        if 'Paddle Tennis Index' in parent_text:
                            pti_text = span.get_text(strip=True)
                            try:
                                pti_value = float(pti_text)
                                if 10.0 <= pti_value <= 100.0:  # Reasonable PTI range
                                    return str(pti_value)
                            except ValueError:
                                continue
            
            # Method 2: Look for PTI in match history table - most recent match
            tables = soup.find_all('table')
            
            for table in tables:
                # Look for rows with "Player Start" and "Player End"
                rows = table.find_all('tr')
                
                for i, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        
                        # Look for "Player End" followed by a numeric value
                        if 'Player End' in text:
                            # Try to extract number from same cell or next cell
                            numbers = re.findall(r'\d+\.?\d*', text)
                            if numbers:
                                pti = float(numbers[0])
                                if 10.0 <= pti <= 100.0:  # Reasonable PTI range
                                    return str(pti)
                        
                        # Look for patterns like "End38.8" or "Start36.8"
                        end_match = re.search(r'End(\d+\.?\d*)', text)
                        if end_match:
                            pti = float(end_match.group(1))
                            if 10.0 <= pti <= 100.0:
                                return str(pti)
            
            return None
            
        except Exception as e:
            print(f"Error extracting PTI from matches: {e}")
            return None

    def _extract_pti_from_summary(self, soup):
        """Extract PTI from player summary/profile section"""
        try:
            # Look for divs or sections that might contain player ratings
            for element in soup.find_all(['div', 'span', 'p']):
                text = element.get_text(strip=True)
                
                # Look for patterns like "Rating: 38.8" or "PTI: 38.8"
                rating_patterns = [
                    r'(?:Rating|PTI|Index):\s*(\d+\.?\d*)',
                    r'Current.*?(\d+\.?\d*)',
                    r'(\d+\.?\d*)\s*(?:Rating|PTI|Index)'
                ]
                
                for pattern in rating_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        pti = float(match.group(1))
                        if 10.0 <= pti <= 100.0:
                            return str(pti)
            
            return None
            
        except Exception as e:
            print(f"Error extracting PTI from summary: {e}")
            return None

    def _extract_pti_patterns(self, soup):
        """Extract PTI using various text patterns"""
        try:
            # Get all text content and look for numeric patterns
            all_text = soup.get_text()
            
            # Look for standalone numbers that could be PTI
            # Focus on areas near player names or match data
            lines = all_text.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Look for lines with just a number in reasonable PTI range
                if re.match(r'^\d+\.?\d*$', line):
                    pti = float(line)
                    if 10.0 <= pti <= 100.0:
                        # Check context - look at surrounding lines for confirmation
                        context_lines = lines[max(0, i-2):i+3]
                        context = ' '.join(context_lines)
                        
                        # If context suggests this is player-related, use it
                        if any(keyword in context.lower() for keyword in 
                               ['player', 'start', 'end', 'rating', 'match']):
                            return str(pti)
            
            return None
            
        except Exception as e:
            print(f"Error extracting PTI patterns: {e}")
            return None

    def _extract_win_loss_stats(self, soup):
        """Extract win/loss statistics from player page"""
        try:
            import re
            
            wins = 0
            losses = 0
            
            # Get all text content
            page_text = soup.get_text()
            lines = page_text.split('\n')
            
            # Method 1: Look for season summary lines like "Chicago: 22 (7 Wins, 5 Losses)"           
            for line in lines:
                line = line.strip()
                
                # Look for season summary pattern: "Chicago: X (Y Wins, Z Losses)"
                season_pattern = r'Chicago:\s*\d+\s*\((\d+)\s*Wins?,\s*(\d+)\s*Losses?\)'
                match = re.search(season_pattern, line)
                if match:
                    season_wins = int(match.group(1))
                    season_losses = int(match.group(2))
                    wins += season_wins
                    losses += season_losses
                    print(f"         Found season: {line} -> +{season_wins}W, +{season_losses}L")
            
            # If we found season summaries, use those (they're more reliable)
            if wins > 0 or losses > 0:
                print(f"         Season summary totals: {wins}W, {losses}L")
                return wins, losses
            
            # Method 2: Fallback - count individual match results if no season summaries found
            print("         No season summaries found, counting individual match results...")
            
            # Count individual W/L results
            for line in lines:
                line = line.strip()
                if line == 'W':
                    wins += 1
                elif line == 'L':
                    losses += 1
            
            print(f"         Individual match totals: {wins}W, {losses}L")
            return wins, losses
            
        except Exception as e:
            print(f"         Error extracting win/loss stats: {e}")
            return 0, 0


def find_missing_teams_comprehensive(driver, config, known_teams, target_series=None):
    """
    Comprehensive search for missing teams using multiple strategies.
    
    Args:
        driver: Chrome WebDriver instance
        config: League configuration dictionary  
        known_teams: Dict of already discovered teams
        target_series: Optional specific series to search for (e.g., "Chicago 24")
        
    Returns:
        dict: Newly discovered teams
    """
    print(f"🔍 Comprehensive search for missing teams...")
    if target_series:
        print(f"   🎯 Specifically looking for: {target_series}")
    
    new_teams = {}
    base_url = config['base_url']
    
    # Strategy 1: Try different URL structures
    url_strategies = [
        # Try different main page variations
        f"{base_url}/?mod=nndz-TjJiOWtOR2sxTnhI",
        f"{base_url}/?mod=nndz-TjJROWJOR2sxTnhI", 
        f"{base_url}/?mod=nndz-TjJqOWtOR2sxTnhI",
        # Try direct access patterns
        f"{base_url}/standings",
        f"{base_url}/teams", 
        f"{base_url}/series",
        f"{base_url}/divisions",
        # Try season variations
        f"{base_url}/?season=2024",
        f"{base_url}/?season=2023",
        f"{base_url}/?year=2024",
    ]
    
    for url in url_strategies:
        try:
            print(f"   🌐 Trying URL: {url}")
            driver.get(url)
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            team_links = soup.find_all('a', href=re.compile(r'team='))
            
            for link in team_links:
                href = link.get('href', '')
                team_name = link.text.strip()
                
                team_match = re.search(r'team=([^&]+)', href)
                if team_match and team_name and team_name not in known_teams:
                    # Skip BYE teams - they are placeholders with no actual players
                    if 'BYE' in team_name.upper():
                        print(f"      Skipping BYE team: {team_name}")
                        continue
                        
                    team_id = team_match.group(1)
                    new_teams[team_name] = team_id
                    
                    series_name = extract_series_name_from_team(team_name)
                    if target_series and series_name == target_series:
                        print(f"      🎉 FOUND TARGET: {team_name} -> {team_id} (series: {series_name})")
                    elif series_name:
                        print(f"      ✅ Found: {team_name} -> {team_id} (series: {series_name})")
                        
        except Exception as e:
            print(f"      ❌ Error with URL {url}: {str(e)}")
            continue
    
    # Strategy 2: Search for specific club/series combinations
    if target_series:
        # Extract series number from target (e.g., "24" from "Chicago 24")
        series_match = re.search(r'(\d+)', target_series)
        if series_match:
            series_num = series_match.group(1)
            
            # Try different parameter combinations
            param_combinations = [
                {'mod': 'nndz-TjJiOWtOR2sxTnhI', 'series': series_num},
                {'mod': 'nndz-TjJiOWtOR2sxTnhI', 'division': series_num},
                {'mod': 'nndz-TjJiOWtOR2sxTnhI', 'league': series_num},
                {'series': series_num},
                {'division': series_num}, 
            ]
            
            for params in param_combinations:
                try:
                    param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                    test_url = f"{base_url}/?{param_string}"
                    
                    print(f"   🧪 Testing specific params: {param_string}")
                    driver.get(test_url)
                    time.sleep(2)
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    team_links = soup.find_all('a', href=re.compile(r'team='))
                    
                    for link in team_links:
                        href = link.get('href', '')
                        team_name = link.text.strip()
                        
                        team_match = re.search(r'team=([^&]+)', href)
                        if team_match and team_name and team_name not in known_teams:
                            # Skip BYE teams - they are placeholders with no actual players
                            if 'BYE' in team_name.upper():
                                print(f"      Skipping BYE team: {team_name}")
                                continue
                                
                            team_id = team_match.group(1)
                            series_name = extract_series_name_from_team(team_name)
                            
                            if series_name == target_series:
                                new_teams[team_name] = team_id
                                print(f"      🎯 FOUND TARGET SERIES TEAM: {team_name} -> {team_id}")
                                
                except Exception as e:
                    print(f"      ❌ Error with params {params}: {str(e)}")
                    continue
    
    # Strategy 3: Try accessing team IDs directly by incrementing known IDs
    print(f"   🔢 Trying sequential team ID discovery...")
    
    # Get known team IDs and try adjacent ones
    known_team_ids = list(known_teams.values())
    numeric_ids = []
    
    for team_id in known_team_ids:
        if team_id.isdigit():
            numeric_ids.append(int(team_id))
    
    if numeric_ids:
        min_id = min(numeric_ids)
        max_id = max(numeric_ids)
        
        # Try a range around the known IDs
        for test_id in range(max(1, min_id - 10), max_id + 50):
            if str(test_id) not in known_team_ids:
                try:
                    team_url = f"{base_url}/?mod={config['team_page_mod']}&team={test_id}"
                    driver.get(team_url)
                    time.sleep(1)
                    
                    # Check if this is a valid team page
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Look for team name in page title or headers
                    title = soup.find('title')
                    if title and any(word in title.text.lower() for word in ['team', 'roster', 'players']):
                        # Try to extract team name from page content
                        headers = soup.find_all(['h1', 'h2', 'h3'])
                        for header in headers:
                            header_text = header.text.strip()
                            # Look for team name patterns
                            if ' - ' in header_text and any(char.isdigit() for char in header_text):
                                series_name = extract_series_name_from_team(header_text)
                                if target_series and series_name == target_series:
                                    new_teams[header_text] = str(test_id)
                                    print(f"      🎯 FOUND BY ID SCAN: {header_text} -> {test_id} (TARGET SERIES!)")
                                    break
                                elif series_name and header_text not in known_teams:
                                    new_teams[header_text] = str(test_id)
                                    print(f"      ✅ Found by ID scan: {header_text} -> {test_id}")
                        
                except Exception as e:
                    # Expected for invalid team IDs
                    continue
    
    print(f"   📊 Comprehensive search complete: {len(new_teams)} new teams found")
    return new_teams


if __name__ == "__main__":
    print("🎾 TennisScores Player Scraper - Dynamic Discovery Mode")
    print("=" * 55)
    print("🔍 Dynamically discovering ALL leagues/series from any TennisScores website")
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
    
    # Use detailed stats mode for comprehensive data collection
    get_stats = True
    print("📈 Detailed stats mode: Collecting comprehensive player statistics")
    print("   Will take longer but provides complete data including PTI, wins, losses")
    print()
    
    players = scrape_league_players(league_subdomain, get_detailed_stats=get_stats)
    print(f"\n✅ Final result: {len(players)} players scraped from {league_subdomain.upper()} using dynamic discovery.") 