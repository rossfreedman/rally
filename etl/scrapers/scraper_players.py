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

# Import centralized league utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.league_utils import standardize_league_id

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
    Dynamically discover all leagues, series, and teams from a TennisScores website.
    Uses comprehensive exploration to find all available data.
    
    Args:
        driver: Chrome WebDriver instance
        config: League configuration dictionary
        max_exploration_pages (int): Maximum number of additional pages to explore
        
    Returns:
        dict: Dictionary containing discovered teams, series, divisions, locations, and clubs
    """
    discovery_start_time = datetime.now()
    max_discovery_time = 120  # Maximum 2 minutes for discovery phase
    
    print(f"🔍 Discovering team IDs from {config['subdomain']} website using comprehensive discovery...")
    print(f"⏰ Maximum discovery time: {max_discovery_time}s")
    
    discovered_teams = {}
    all_series = set()
    all_divisions = {}
    all_locations = {}
    all_clubs = set()
    
    def check_discovery_timeout():
        """Check if discovery has exceeded maximum time limit"""
        elapsed = (datetime.now() - discovery_start_time).total_seconds()
        if elapsed > max_discovery_time:
            print(f"⏰ Discovery timeout reached ({elapsed:.1f}s > {max_discovery_time}s)")
            return True
        return False
    
    try:
        print(f"🔍 Starting comprehensive site discovery for {config['subdomain']} website...")
        
        # Strategy 1: Explore main page
        if check_discovery_timeout():
            return {'teams': discovered_teams, 'series': all_series, 'divisions': all_divisions, 'locations': all_locations, 'clubs': all_clubs}
            
        main_page_url = f"{config['base_url']}/?mod=nndz-TjJiOWtOR2sxTnhI"
        print(f"📄 Exploring main page: {main_page_url}")
        
        driver.get(main_page_url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract team information
        print(f"🏆 Discovering teams and extracting series information...")
        team_links = soup.find_all('a', href=re.compile(r'team='))
        
        for link in team_links:
            if check_discovery_timeout():
                break
                
            href = link.get('href', '')
            team_name = link.text.strip()
            
            team_match = re.search(r'team=([^&]+)', href)
            if team_match and team_name:
                # Skip BYE teams - they are placeholders with no actual players
                if 'BYE' in team_name.upper():
                    continue
                    
                team_id = team_match.group(1)
                discovered_teams[team_name] = team_id
                
                # Extract series name using improved helper function
                series_name = extract_series_name_from_team(team_name)
                if series_name:
                    all_series.add(series_name)
                    print(f"Found series: {series_name} (from team: {team_name})")
                
                # Extract club name
                club_name = extract_club_name_from_team(team_name)
                if club_name:
                    all_clubs.add(club_name)
        
        print(f"✅ Discovered {len(discovered_teams)} teams from main page")
        
        # Strategy 2: Explore navigation and menu links (with timeout check)
        if not check_discovery_timeout():
            print(f"🧭 Exploring navigation and menu links for additional team pages...")
            
            # Look for navigation links that might lead to more teams
            nav_links = soup.find_all('a', href=True)
            potential_team_pages = []
            
            for link in nav_links[:10]:  # Limit to first 10 links to prevent timeouts
                if check_discovery_timeout():
                    break
                    
                href = link.get('href', '')
                text = link.text.strip().lower()
                
                # Look for links that might contain team listings
                if any(keyword in text for keyword in ['standing', 'team', 'roster', 'division', 'league']):
                    if href.startswith('http') or href.startswith('/') or href.startswith('?'):
                        potential_team_pages.append((text, href))
            
            # Explore a few promising links
            for i, (text, href) in enumerate(potential_team_pages[:3]):  # Limit to 3 to prevent timeouts
                if check_discovery_timeout():
                    break
                    
                try:
                    if href.startswith('/') or href.startswith('?'):
                        full_url = f"{config['base_url']}{href}"
                    else:
                        full_url = href
                    
                    print(f"🔍 Exploring potential team page: {text} ({full_url})")
                    driver.get(full_url)
                    time.sleep(2)
                    
                    page_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    page_team_links = page_soup.find_all('a', href=re.compile(r'team='))
                    
                    new_teams_found = 0
                    for link in page_team_links:
                        href = link.get('href', '')
                        team_name = link.text.strip()
                        
                        team_match = re.search(r'team=([^&]+)', href)
                        if team_match and team_name and team_name not in discovered_teams:
                            # Skip BYE teams
                            if 'BYE' in team_name.upper():
                                continue
                                
                            team_id = team_match.group(1)
                            discovered_teams[team_name] = team_id
                            new_teams_found += 1
                            
                            # Extract series and club info
                            series_name = extract_series_name_from_team(team_name)
                            if series_name:
                                all_series.add(series_name)
                            
                            club_name = extract_club_name_from_team(team_name)
                            if club_name:
                                all_clubs.add(club_name)
                    
                    if new_teams_found == 0:
                        print(f"ℹ️ No new teams found on this page")
                    else:
                        print(f"✅ Found {new_teams_found} new teams")
                        
                except Exception as e:
                    print(f"⚠️ Error exploring {full_url}: {str(e)}")
                    continue
        
        # Strategy 3: Try common URL patterns (with timeout check)
        if not check_discovery_timeout():
            print(f"🎯 Trying common URL patterns for different series...")
            
            # Test fewer patterns to prevent timeouts
            test_patterns = [
                'mod=nndz-TjJiOWtOR2sxTnhI',
                'mod=nndz-TjJROWJOR2sxTnhI', 
                'mod=nndz-TjJqOWtOR2sxTnhI',
                'series=1',
                'series=2',
                'series=3',
                'series=4',
                'series=5',
                'division=1',
                'division=2',
            ]
            
            for i, pattern in enumerate(test_patterns):
                if check_discovery_timeout():
                    print(f"⏰ Stopping URL pattern testing due to timeout")
                    break
                    
                try:
                    test_url = f"{config['base_url']}/?{pattern}"
                    print(f"🧪 Testing URL pattern: {pattern}")
                    
                    # Wrap the driver.get call in its own try-catch
                    try:
                        driver.get(test_url)
                        time.sleep(1)  # Reduced delay
                    except Exception as driver_error:
                        print(f"⚠️ Driver error for pattern {pattern}: {str(driver_error)}")
                        continue
                    
                    # Wrap the page parsing in its own try-catch
                    try:
                        page_source = driver.page_source
                        if not page_source or len(page_source) < 100:
                            print(f"⚠️ Empty or short page source for pattern {pattern}")
                            continue
                            
                        page_soup = BeautifulSoup(page_source, 'html.parser')
                        if not page_soup:
                            print(f"⚠️ BeautifulSoup parsing failed for pattern {pattern}")
                            continue
                            
                    except Exception as parse_error:
                        print(f"⚠️ Parse error for pattern {pattern}: {str(parse_error)}")
                        continue
                    
                    # Wrap the team link extraction in its own try-catch
                    try:
                        page_team_links = page_soup.find_all('a', href=re.compile(r'team='))
                        
                        teams_found_in_pattern = 0
                        for link in page_team_links:
                            try:
                                href = link.get('href', '')
                                team_name = link.text.strip()
                                
                                team_match = re.search(r'team=([^&]+)', href)
                                if team_match and team_name and team_name not in discovered_teams:
                                    # Skip BYE teams
                                    if 'BYE' in team_name.upper():
                                        continue
                                        
                                    team_id = team_match.group(1)
                                    discovered_teams[team_name] = team_id
                                    teams_found_in_pattern += 1
                                    
                                    # Extract series and club info
                                    series_name = extract_series_name_from_team(team_name)
                                    if series_name:
                                        all_series.add(series_name)
                                    
                                    club_name = extract_club_name_from_team(team_name)
                                    if club_name:
                                        all_clubs.add(club_name)
                                        
                            except Exception as link_error:
                                print(f"⚠️ Error processing link in pattern {pattern}: {str(link_error)}")
                                continue
                        
                        if teams_found_in_pattern > 0:
                            print(f"✅ Pattern {pattern} found {teams_found_in_pattern} new teams")
                        else:
                            print(f"ℹ️ Pattern {pattern} found no new teams")
                            
                    except Exception as extraction_error:
                        print(f"⚠️ Team extraction error for pattern {pattern}: {str(extraction_error)}")
                        continue
                    
                except Exception as e:
                    print(f"⚠️ General error testing pattern {pattern}: {str(e)}")
                    continue
        
        print(f"✅ Discovered {len(discovered_teams)} teams")
        print(f"✅ Discovered {len(all_series)} series: {sorted(list(all_series))}")
        print(f"✅ Discovered {len(all_clubs)} clubs")
        
        # Deep-dive exploration (limited to prevent timeouts)
        if not check_discovery_timeout() and len(discovered_teams) > 0:
            print(f"🔬 Deep-diving into {min(3, len(discovered_teams))} team pages for additional discovery...")
            
            sample_teams = list(discovered_teams.items())[:3]  # Limit to 3 teams
            for team_name, team_id in sample_teams:
                if check_discovery_timeout():
                    break
                    
                try:
                    print(f"📊 Exploring team page: {team_name}")
                    team_url = f"{config['base_url']}/?mod={config['team_page_mod']}&team={team_id}"
                    driver.get(team_url)
                    time.sleep(2)
                    
                    team_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # Look for additional series or division information
                    # This could reveal more teams in the same series
                    
                except Exception as e:
                    print(f"⚠️ Error exploring team {team_name}: {str(e)}")
                    continue
        
        # Final summary
        elapsed_time = (datetime.now() - discovery_start_time).total_seconds()
        print(f"📊 DISCOVERY SUMMARY:")
        print(f"🏆 Teams: {len(discovered_teams)} (initial: {len(discovered_teams)}, new: 0)")
        print(f"📈 Series: {len(all_series)} - {sorted(list(all_series))}")
        print(f"🏢 Clubs: {len(all_clubs)}")
        print(f"🏛️ Divisions: {len(all_divisions)}")
        print(f"📍 Locations: {len(all_locations)}")
        print(f"⏰ Discovery completed in {elapsed_time:.1f}s")
        
        # Try to find missing teams (with timeout check)
        if not check_discovery_timeout():
            missing_series = []
            
            # For platform tennis leagues, try to find missing numbered series
            is_platform_tennis = is_platform_tennis_league(config['subdomain'])
            if is_platform_tennis:
                # Look for missing numbered series (e.g., Chicago 3, 4, 5...)
                found_numbers = set()
                for series in all_series:
                    numbers = re.findall(r'\d+', series)
                    for num in numbers:
                        found_numbers.add(int(num))
                
                if found_numbers:
                    max_found = max(found_numbers)
                    min_found = min(found_numbers)
                    
                    # Look for gaps in the series
                    for i in range(min_found, min(max_found + 5, max_found + 10)):  # Limited range
                        if i not in found_numbers:
                            missing_series.append(f"Chicago {i}")
            
            if missing_series:
                print(f"🔍 Found {len(missing_series)} potentially missing series: {missing_series[:10]}{'...' if len(missing_series) > 10 else ''}")
                
                # Try to find a few missing series (limited to prevent timeouts)
                for target_series in missing_series[:3]:  # Limit to 3 attempts
                    if check_discovery_timeout():
                        break
                        
                    print(f"🎯 Searching specifically for: {target_series}")
                    try:
                        found_teams = find_missing_teams_comprehensive(driver, config, discovered_teams, target_series)
                        if found_teams:
                            discovered_teams.update(found_teams)
                            print(f"✅ Found teams for {target_series}")
                        else:
                            print(f"ℹ️ No teams found for {target_series}")
                    except Exception as e:
                        print(f"⚠️ Error searching for {target_series}: {str(e)}")
                        continue
        
        final_elapsed = (datetime.now() - discovery_start_time).total_seconds()
        if final_elapsed > max_discovery_time:
            print(f"⏰ Discovery completed with timeout ({final_elapsed:.1f}s)")
        else:
            print(f"✅ Discovery completed successfully in {final_elapsed:.1f}s")
        
        return {
            'teams': discovered_teams,
            'series': all_series,
            'divisions': all_divisions,
            'locations': all_locations,
            'clubs': all_clubs
        }
        
    except Exception as e:
        elapsed_time = (datetime.now() - discovery_start_time).total_seconds()
        print(f"❌ Discovery failed after {elapsed_time:.1f}s: {str(e)}")
        
        # Return whatever we managed to discover
        return {
            'teams': discovered_teams,
            'series': all_series,
            'divisions': all_divisions,
            'locations': all_locations,
            'clubs': all_clubs
        }

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
        
        # Essential options for headless operation
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        
        # Additional stability options for environments where Chrome may not be fully installed
        options.add_argument('--disable-features=NetworkService')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        # Note: Not disabling JavaScript as TennisScores sites may require it
        
        # Set a user agent to avoid detection
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            # Try ChromeDriverManager first (automatic driver management)
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"      ⚠️ ChromeDriverManager failed: {e}")
            
            try:
                # Fallback: Try system Chrome installation
                return webdriver.Chrome(options=options)
            except Exception as e2:
                print(f"      ⚠️ System Chrome failed: {e2}")
                
                # Final fallback: Try with explicit Chrome binary paths
                common_chrome_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
                    "/usr/bin/google-chrome",  # Linux
                    "/usr/bin/chromium-browser",  # Linux Chromium
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",  # Windows x86
                ]
                
                for chrome_path in common_chrome_paths:
                    try:
                        if os.path.exists(chrome_path):
                            options.binary_location = chrome_path
                            print(f"      🔧 Trying Chrome at: {chrome_path}")
                            return webdriver.Chrome(options=options)
                    except Exception as e3:
                        continue
                
                # If all else fails, raise the original error
                raise Exception(f"Could not initialize Chrome WebDriver. Original error: {e}. System Chrome error: {e2}")

    def __enter__(self):
        """Create and return a Chrome WebDriver instance with retries."""
        for attempt in range(self.max_retries):
            try:
                if self.driver is not None:
                    try:
                        self.driver.quit()
                    except:
                        pass
                        
                print(f"🌐 Initializing Chrome WebDriver (attempt {attempt + 1}/{self.max_retries})...")
                self.driver = self.create_driver()
                
                # Test the driver with a simple page load
                print("🧪 Testing Chrome WebDriver...")
                self.driver.get("data:text/html,<html><body>Test</body></html>")
                
                print("✅ Chrome WebDriver initialized successfully")
                return self.driver
                
            except Exception as e:
                print(f"❌ Error creating Chrome driver (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    print("🔄 Retrying...")
                    time.sleep(5)
                else:
                    print("\n" + "="*60)
                    print("❌ CHROME DRIVER INITIALIZATION FAILED")
                    print("="*60)
                    print("🚨 Could not initialize Chrome WebDriver after maximum retries.")
                    print("💡 Possible solutions:")
                    print("   1. Install Google Chrome: brew install --cask google-chrome (macOS)")
                    print("   2. Install ChromeDriver: brew install chromedriver (macOS)")
                    print("   3. Update Chrome to latest version")
                    print("   4. Check if Chrome is blocked by security settings")
                    print("="*60)
                    raise Exception("Failed to create Chrome driver after maximum retries")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the Chrome WebDriver instance."""
        self.quit()

    def quit(self):
        """Safely quit the Chrome WebDriver instance."""
        if self.driver is not None:
            try:
                self.driver.quit()
                print("🔒 Chrome WebDriver closed successfully")
            except Exception as e:
                print(f"⚠️ Error closing Chrome driver: {str(e)}")
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
                
            print(f"         🌐 Loading player page: {full_url}")
            driver.get(full_url)
            time.sleep(retry_delay / 2)

            # Get page content and parse with BeautifulSoup with enhanced error handling
            try:
                page_source = driver.page_source
                if not page_source or len(page_source) < 100:
                    raise Exception("Page source is empty or too short")
                    
                soup = BeautifulSoup(page_source, 'html.parser')
                if not soup:
                    raise Exception("BeautifulSoup parsing failed")
                    
            except Exception as e:
                print(f"         ❌ Error parsing page source: {e}")
                raise
            
            # Use PlayerScraper for better extraction with enhanced error handling
            try:
                scraper = PlayerScraper(config)
                
                # Extract PTI only for platform tennis leagues
                pti_value = None
                if is_platform_tennis:
                    try:
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
                                            pti_candidate = float(pti_text)
                                            if 10.0 <= pti_candidate <= 100.0:
                                                pti_value = str(pti_candidate)
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
                    except Exception as e:
                        print(f"         ⚠️ Error extracting PTI: {e}")
                        pti_value = None
                
                # Extract wins and losses using the improved scraper method with enhanced error handling
                try:
                    wins, losses = scraper._extract_win_loss_stats(soup)
                except Exception as e:
                    print(f"         ⚠️ Error extracting W/L stats: {e}")
                    # Fallback to simple counting
                    wins, losses = 0, 0
                    try:
                        content = driver.find_element(By.TAG_NAME, "body").text
                        lines = content.split('\n')
                        for line in lines:
                            line_clean = line.strip()
                            if line_clean == 'W':
                                wins += 1
                            elif line_clean == 'L':
                                losses += 1
                        print(f"         ✅ Fallback W/L extraction: {wins}W, {losses}L")
                    except Exception as e2:
                        print(f"         ❌ Fallback W/L extraction also failed: {e2}")
                        wins, losses = 0, 0
                
                # Calculate win percentage safely
                try:
                    if wins + losses > 0:
                        win_percentage = f"{(wins/(wins+losses)*100):.1f}%"
                    else:
                        win_percentage = "0.0%"
                except Exception as e:
                    print(f"         ⚠️ Error calculating win percentage: {e}")
                    win_percentage = "0.0%"
                
            except Exception as e:
                print(f"         ❌ Error in PlayerScraper extraction: {e}")
                # Return default values
                return {'PTI': 'N/A', 'Wins': '0', 'Losses': '0', 'Win %': '0.0%'}

            # Build and return result safely
            try:
                result = {
                    'PTI': pti_value or 'N/A',
                    'Wins': str(wins),
                    'Losses': str(losses),
                    'Win %': win_percentage
                }
                
                print(f"         ✅ Extraction successful: PTI={result['PTI']}, W/L={result['Wins']}-{result['Losses']} ({result['Win %']})")
                return result
                
            except Exception as e:
                print(f"         ❌ Error building result: {e}")
                return {'PTI': 'N/A', 'Wins': '0', 'Losses': '0', 'Win %': '0.0%'}

        except Exception as e:
            print(f"         ❌ Error getting player stats (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"         🔄 Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"         ❌ Max retries reached, returning default stats")
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
                    
                    # Check if this is a platform tennis league for appropriate messaging
                    is_platform_tennis = is_platform_tennis_league(config['subdomain'])
                    
                    if is_platform_tennis:
                        print(f"   🏓 Platform Tennis League: Extracting PTI + Win/Loss stats")
                    else:
                        print(f"   🎾 Tennis League: Extracting Win/Loss stats only (no PTI)")
                    
                    for player_idx, player in enumerate(team_players, 1):
                        # Use the temporarily stored URL for PTI extraction
                        player_url = player.get('_temp_url')
                        if player_url:
                            try:
                                player_progress = (player_idx / len(team_players)) * 100
                                
                                # Use appropriate messaging based on league type
                                if is_platform_tennis:
                                    print(f"      🔍 [{player_idx}/{len(team_players)} - {player_progress:.1f}%] Getting PTI + stats for {player['First Name']} {player['Last Name']}")
                                else:
                                    print(f"      🔍 [{player_idx}/{len(team_players)} - {player_progress:.1f}%] Getting W/L stats for {player['First Name']} {player['Last Name']}")
                                
                                # Use optimized retry settings for tennis leagues
                                if is_platform_tennis:
                                    stats = get_player_stats(player_url, driver, config, max_retries=3, retry_delay=5)
                                else:
                                    # Tennis leagues need less time per player since no PTI extraction
                                    stats = get_player_stats(player_url, driver, config, max_retries=2, retry_delay=2)
                                
                                if stats['PTI'] != "N/A" and is_platform_tennis:
                                    player.update(stats)
                                    print(f"         ✅ Updated stats: PTI={stats['PTI']}, W/L: {stats['Wins']}-{stats['Losses']} ({stats['Win %']})")
                                else:
                                    # Update just the W/L if PTI not found or tennis league
                                    player['Wins'] = stats['Wins']
                                    player['Losses'] = stats['Losses'] 
                                    player['Win %'] = stats['Win %']
                                    
                                    if is_platform_tennis:
                                        print(f"         ⚠️  No PTI found, but got W/L: {stats['Wins']}-{stats['Losses']} ({stats['Win %']})")
                                    else:
                                        print(f"         ✅ Tennis stats: W/L: {stats['Wins']}-{stats['Losses']} ({stats['Win %']})")
                                    
                            except Exception as e:
                                print(f"         ❌ Error getting stats for {player['First Name']} {player['Last Name']}: {e}")
                                continue
                        else:
                            print(f"      ⚠️  No URL available for {player['First Name']} {player['Last Name']}")
                        
                        # Reduced rate limiting for tennis leagues
                        if is_platform_tennis:
                            time.sleep(0.5)  # Platform tennis needs more time for PTI extraction
                        else:
                            time.sleep(0.2)  # Tennis leagues can be faster
                
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
    
    # Strategy 1: Try fewer, more targeted URL structures to prevent timeouts
    url_strategies = [
        # Try different main page variations (reduced set)
        f"{base_url}/?mod=nndz-TjJiOWtOR2sxTnhI",
        f"{base_url}/?mod=nndz-TjJROWJOR2sxTnhI", 
        # Try direct access patterns (fewer attempts)
        f"{base_url}/standings",
        f"{base_url}/teams", 
        # Try current season only
        f"{base_url}/?season=2024",
    ]
    
    for i, url in enumerate(url_strategies):
        try:
            print(f"   🌐 Trying URL {i+1}/{len(url_strategies)}: {url}")
            driver.get(url)
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            team_links = soup.find_all('a', href=re.compile(r'team='))
            
            found_any = False
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
                    found_any = True
                    
                    series_name = extract_series_name_from_team(team_name)
                    if target_series and series_name == target_series:
                        print(f"      🎉 FOUND TARGET: {team_name} -> {team_id} (series: {series_name})")
                    elif series_name:
                        print(f"      ✅ Found: {team_name} -> {team_id} (series: {series_name})")
            
            if not found_any:
                print(f"      ℹ️ No new teams found on this page")
                        
        except Exception as e:
            print(f"      ❌ Error with URL {url}: {str(e)}")
            # Continue with next URL instead of stopping
            continue
    
    # Strategy 2: Only search for specific target series if provided (reduced scope)
    if target_series and len(new_teams) == 0:
        # Extract series number from target (e.g., "24" from "Chicago 24")
        series_match = re.search(r'(\d+)', target_series)
        if series_match:
            series_num = series_match.group(1)
            
            # Try only the most likely parameter combinations (reduced set)
            param_combinations = [
                {'mod': 'nndz-TjJiOWtOR2sxTnhI', 'series': series_num},
                {'series': series_num},
                {'division': series_num}, 
            ]
            
            for i, params in enumerate(param_combinations):
                try:
                    param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                    test_url = f"{base_url}/?{param_string}"
                    
                    print(f"   🧪 Testing specific params {i+1}/{len(param_combinations)}: {param_string}")
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
    
    # Skip Strategy 3 (sequential ID discovery) for tennis leagues to prevent timeouts
    is_platform_tennis = is_platform_tennis_league(config['subdomain'])
    if is_platform_tennis:
        print(f"   🔢 Trying sequential team ID discovery...")
        
        # Get known team IDs and try adjacent ones (reduced scope)
        known_team_ids = list(known_teams.values())
        numeric_ids = []
        
        for team_id in known_team_ids:
            if team_id.isdigit():
                numeric_ids.append(int(team_id))
        
        if numeric_ids:
            min_id = min(numeric_ids)
            max_id = max(numeric_ids)
            
            # Try a smaller range around known IDs to prevent timeouts
            test_range = range(max(1, min_id - 2), min(max_id + 5, max_id + 10))
            
            for test_id in test_range:
                if str(test_id) not in known_team_ids:
                    try:
                        test_url = f"{base_url}/?mod={config['team_page_mod']}&team={test_id}"
                        driver.get(test_url)
                        time.sleep(1)  # Reduced delay
                        
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        
                        # Look for team name in page title or headers
                        title = soup.find('title')
                        if title and 'team' in title.text.lower():
                            # Try to extract team name from page
                            headers = soup.find_all(['h1', 'h2', 'h3'])
                            for header in headers:
                                header_text = header.text.strip()
                                if header_text and len(header_text) > 3:
                                    if 'BYE' not in header_text.upper():
                                        new_teams[header_text] = str(test_id)
                                        print(f"      🔢 Found by ID: {header_text} -> {test_id}")
                                        break
                                    
                    except Exception as e:
                        print(f"      ⚠️ Error testing ID {test_id}: {str(e)}")
                        continue
    else:
        print(f"   ⏭️ Skipping sequential ID discovery for tennis league (prevents timeouts)")
    
    if new_teams:
        print(f"   ✅ Found {len(new_teams)} new teams via comprehensive search")
        for name, team_id in new_teams.items():
            print(f"      - {name} -> {team_id}")
    else:
        print(f"   ℹ️ No new teams found via comprehensive search")
    
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