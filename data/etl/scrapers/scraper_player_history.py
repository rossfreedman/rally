print("[DEBUG] player_scrape_history.py script started")
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import warnings
from datetime import datetime, timedelta
from io import StringIO

# Suppress deprecation warnings - CRITICAL for production stability
warnings.filterwarnings("ignore", category=UserWarning, module="_distutils_hack")
warnings.filterwarnings("ignore", category=UserWarning, module="setuptools")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import enhanced stealth browser with all features
from stealth_browser import StealthBrowserManager, create_enhanced_scraper, add_throttling_to_loop, validate_browser_ip, make_decodo_request

from utils.league_utils import standardize_league_id
from utils.player_id_utils import create_player_id, extract_tenniscores_player_id

"""
👥 Player History Scraper - Enhanced Production-Ready Approach

📊 REQUEST VOLUME ANALYSIS:
- Estimated requests per run: ~100-500 (varies by league size and player count)
- Cron frequency: daily
- Estimated daily volume: 100-500 requests
- Status: ✅ Within safe limits

🌐 IP ROTATION: Enabled via Decodo residential proxies + Selenium Wire
⏳ THROTTLING: 1.5-4.5 second delays between requests
"""

# Removed hardcoded division and location lookups - now using dynamic discovery

# Removed file-based configuration functions - now using user input


def build_league_data_dir(league_id):
    """
    Build the dynamic data directory path based on the league ID.

    Args:
        league_id (str): The league identifier

    Returns:
        str: The data directory path (e.g., 'data/leagues/APTACHICAGO')
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up three levels: scrapers -> etl -> data -> project_root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

    league_data_dir = os.path.join(project_root, "data", "leagues", league_id)
    os.makedirs(league_data_dir, exist_ok=True)

    return league_data_dir


# ChromeManager has been replaced with StealthBrowserManager for fingerprint evasion
# See stealth_browser.py for the new implementation

# Removed active_series functionality - now processes all discovered series


def get_league_config(league_subdomain=None):
    """Get dynamic league configuration based on user input"""
    if not league_subdomain:
        raise ValueError("League subdomain must be provided")

    base_url = build_base_url(league_subdomain)

    return {
        "league_id": standardize_league_id(league_subdomain),
        "subdomain": league_subdomain,
        "base_url": base_url,
        "main_page": f"{base_url}/?mod=nndz-TjJiOWtOR2sxTnhI",
        "player_page_mod": "nndz-SkhmOW1PQ3V4Zz09",
        "team_page_mod": "nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D",
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
    if " - " in team_name:
        return team_name.split(" - ")[0].strip()

    # NSTF format: "Club SNumber" or "Club SNumberLetter" (e.g., S1, S2A, S2B)
    elif re.search(r"S\d+[A-Z]*", team_name):
        return re.sub(r"\s+S\d+[A-Z]*.*$", "", team_name).strip()

    # NSTF Sunday format: "Club Sunday A/B"
    elif "Sunday" in team_name:
        club_name = team_name.replace("Sunday A", "").replace("Sunday B", "").strip()
        return club_name if club_name else team_name

    # Fallback: use the team name as-is
    return team_name


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
    print(
        f"🔍 Starting comprehensive site discovery for {config['subdomain']} website..."
    )

    discovery_results = {
        "teams": {},
        "series": set(),
        "divisions": {},
        "locations": {},
        "clubs": set(),
    }

    try:
        # Start with the main league page
        print(f"📄 Exploring main page: {config['main_page']}")
        driver.get(config["main_page"])
        time.sleep(3)

        # Get page source and parse
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Discover teams and extract series/clubs from team names
        print("🏆 Discovering teams and extracting series information...")
        team_links = soup.find_all("a", href=re.compile(r"team="))

        for link in team_links:
            href = link.get("href", "")
            team_name = link.text.strip()

            # Extract team ID from URL
            team_match = re.search(r"team=([^&]+)", href)
            if team_match and team_name:
                team_id = team_match.group(1)

                # Store team mapping
                discovery_results["teams"][team_name] = team_id

                # Extract series name using existing helper function
                series_name = extract_series_name_from_team(team_name)
                if series_name:
                    discovery_results["series"].add(series_name)
                    print(f"  Found series: {series_name} (from team: {team_name})")

                # Extract club name
                club_name = extract_club_name_from_team(team_name)
                if club_name and club_name != "Unknown":
                    discovery_results["clubs"].add(club_name)

        print(f"✅ Discovered {len(discovery_results['teams'])} teams")
        print(
            f"✅ Discovered {len(discovery_results['series'])} series: {sorted(discovery_results['series'])}"
        )
        print(f"✅ Discovered {len(discovery_results['clubs'])} clubs")

        return discovery_results

    except Exception as e:
        print(f"❌ Error during site discovery: {str(e)}")
        return discovery_results


def get_player_stats(player_url, driver, config, max_retries=3, retry_delay=2):
    """Get detailed player statistics including match history using Decodo residential proxy or Chrome WebDriver."""
    for attempt in range(max_retries):
        try:
            # Use dynamic league configuration
            base_url = config["base_url"]
            full_url = (
                f"{base_url}{player_url}"
                if not player_url.startswith("http")
                else player_url
            )

            # Try Decodo residential proxy first, fall back to Chrome WebDriver
            try:
                print(f"   🌐 Using Decodo residential proxy for player stats")
                response = make_decodo_request(full_url, timeout=30)
                soup = BeautifulSoup(response.content, "html.parser")
            except Exception as e:
                print(f"   🚗 Decodo failed, using Chrome WebDriver for player stats: {e}")
                # Verify driver health before making request
                try:
                    driver.current_url
                except Exception:
                    raise Exception("Driver session is invalid")

                driver.get(full_url)
                time.sleep(retry_delay)
                soup = BeautifulSoup(driver.page_source, "html.parser")

            wins = 0
            losses = 0
            match_details = []  # List of dicts: {date, end_pti, series}

            # Extract match info from rbox_top divs
            for rbox in soup.find_all("div", class_="rbox_top"):
                # Date
                date_div = rbox.find("div", class_="rbox_inner")
                match_date = None
                if date_div:
                    date_text = date_div.get_text(strip=True)
                    match_date = date_text.split()[0] if date_text else None

                # Series
                series_div = rbox.find_all("div", class_="rbox_inner")
                match_series = None
                if len(series_div) > 1:
                    match_series = series_div[1].get_text(strip=True)
                    if " - " in match_series:
                        match_series = match_series.split(" - ")[0]

                # End PTI
                end_pti = None
                for pti_div in rbox.find_all("div", class_="rbox3top"):
                    if "End" in pti_div.get_text():
                        span = pti_div.find("span", class_="demi")
                        if span:
                            end_pti = span.get_text(strip=True)

                if match_date and end_pti and match_series:
                    match_details.append(
                        {"date": match_date, "end_pti": end_pti, "series": match_series}
                    )

            # Count wins and losses
            content = driver.find_element(By.TAG_NAME, "body").text
            matches = content.split("\n")
            for line in matches:
                if line.strip() == "W":
                    wins += 1
                elif line.strip() == "L":
                    losses += 1

            return {
                "Wins": wins,
                "Losses": losses,
                "Win %": (
                    f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%"
                ),
                "match_details": match_details,
            }

        except Exception as e:
            print(
                f"Error getting player stats (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached, returning default stats")
                return {"Wins": 0, "Losses": 0, "Win %": "0.0%", "match_details": []}


def scrape_player_history(league_subdomain):
    """
    Main function to scrape and save player history data using dynamic discovery.

    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
    """
    print("[Scraper] Starting scrape: scraper_player_history")
    
    # Initialize enhanced scraper with request volume tracking
    # Estimate: 100-500 requests depending on league size and player count
    estimated_requests = 300  # Conservative estimate
    scraper_enhancements = create_enhanced_scraper(
        scraper_name="Player History Scraper",
        estimated_requests=estimated_requests,
        cron_frequency="daily"
    )
    
    # Record start time
    start_time = datetime.now()
    print(f"🕐 Session Start: {start_time.strftime('%m-%d-%y @ %I:%M:%S %p')}")

    # Track timing milestones
    discovery_start_time = None
    scraping_start_time = None

    try:
        # Load league configuration from user input
        config = get_league_config(league_subdomain)
        league_id = config["league_id"]

        print(
            f"🌟 Processing ALL discovered series from {config['subdomain']} dynamically"
        )
        print("No filtering - comprehensive discovery and processing of all players")

        # Use stealth browser manager to avoid bot detection
        with StealthBrowserManager(headless=True) as driver:
            # Validate IP region after browser launch
            print("🌐 Validating IP region for ScraperAPI proxy...")
            ip_validation = scraper_enhancements.validate_ip_region(driver)
            if not ip_validation.get('validation_successful', False):
                print("⚠️ IP validation failed, but continuing with scraping...")

            # Create dynamic data directory based on league
            data_dir = build_league_data_dir(league_id)

            print(f"🚀 Starting {config['subdomain'].upper()} Player History Scraper")
            print(f"📊 Target: All Discovered Players")
            print("=" * 60)

            # Discover all available data dynamically
            discovery_start_time = datetime.now()
            print(
                f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}"
            )
            discovery_results = discover_all_leagues_and_series(driver, config)

            # Create a comprehensive player-to-team mapping by visiting each team page
            print("🔗 Building player-to-team mapping...")
            player_to_team_map = (
                {}
            )  # Maps "First Last" -> {"team_name": "...", "series": "...", "club": "..."}

            team_count = 0
            for team_name, team_id in discovery_results["teams"].items():
                team_count += 1

                # Extract series and club names from team name using the correct helper functions
                series_name = extract_series_name_from_team(team_name)
                club_name = extract_club_name_from_team(team_name)

                if not series_name or not club_name:
                    print(f"   ⚠️ Could not extract series/club from team: {team_name}")
                    continue

                try:
                    # Visit team page to get player list
                    team_url = f"{config['base_url']}/?mod={config['team_page_mod']}&team={team_id}"
                    print(
                        f"   📋 Processing team {team_count}/{len(discovery_results['teams'])}: {team_name}"
                    )

                    # Track request and add throttling before team page load
                    scraper_enhancements.track_request(f"team_{team_count}_load")
                    add_throttling_to_loop()

                    driver.get(team_url)
                    time.sleep(2)

                    team_soup = BeautifulSoup(driver.page_source, "html.parser")

                    # Find all player links on this team page
                    player_links = team_soup.find_all("a", href=True)

                    for link in player_links:
                        href = link.get("href", "")
                        # Look for player links (similar patterns as in the correct scraper)
                        if any(
                            pattern in href
                            for pattern in [
                                "player.php",
                                "uid=",
                                "player=",
                                "player_id=",
                            ]
                        ):
                            player_name = link.get_text(strip=True)

                            if player_name and len(player_name.split()) >= 2:
                                # Store mapping from player name to team info
                                player_to_team_map[player_name] = {
                                    "team_name": team_name,
                                    "series": series_name,
                                    "club": club_name,
                                }

                    # Also look for player names in table cells (backup method)
                    for table in team_soup.find_all("table"):
                        for row in table.find_all("tr"):
                            for cell in row.find_all(["td", "th"]):
                                cell_text = cell.get_text(strip=True)
                                # Look for name patterns (First Last)
                                if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+", cell_text):
                                    player_to_team_map[cell_text] = {
                                        "team_name": team_name,
                                        "series": series_name,
                                        "club": club_name,
                                    }

                except Exception as e:
                    print(f"   ❌ Error processing team {team_name}: {e}")
                    continue

            print(
                f"✅ Built player mapping: {len(player_to_team_map)} players mapped to teams"
            )

            discovery_end_time = datetime.now()
            discovery_duration = discovery_end_time - discovery_start_time
            print(
                f"✅ Discovery Phase Complete: {discovery_duration.total_seconds():.1f} seconds"
            )

            # Navigate to player page with dynamic URL
            player_page_url = f"{config['base_url']}/?mod={config['player_page_mod']}"
            print(f"\n📄 Navigating to player page: {player_page_url}")
            driver.get(player_page_url)
            time.sleep(3)

            # Get the page source after JavaScript has run
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Find all player rows
            all_rows = []
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:  # Skip header row
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        all_rows.append(row)

            print(f"📋 Found {len(all_rows)} total players to process")

            # Initialize tracking variables
            all_players_json = []
            processed_series = set()

            scraping_start_time = datetime.now()
            print(
                f"⚡ Scraping Phase Start: {scraping_start_time.strftime('%H:%M:%S')}"
            )

            # Process each player row
            for row_idx, row in enumerate(all_rows, 1):
                player_start_time = datetime.now()
                progress_percent = (row_idx / len(all_rows)) * 100
                elapsed = player_start_time - start_time
                print(
                    f"\n=== Player {row_idx}/{len(all_rows)} ({progress_percent:.1f}%) | Elapsed: {elapsed} ==="
                )

                cells = row.find_all("td")

                # Extract basic player information
                first_name = cells[0].text.strip() if len(cells) > 0 else "Unknown"
                last_name = cells[1].text.strip() if len(cells) > 1 else "Unknown"
                rating = cells[2].text.strip() if len(cells) > 2 else "N/A"

                # Extract series and club information using player-to-team mapping
                series_name = "Unknown"
                club_name = "Unknown"

                # Create full player name and look it up in our mapping
                full_player_name = f"{first_name} {last_name}".strip()

                if full_player_name in player_to_team_map:
                    team_info = player_to_team_map[full_player_name]
                    series_name = team_info["series"]
                    club_name = team_info["club"]
                    print(
                        f"   📍 Mapped {full_player_name} -> {club_name} | {series_name}"
                    )
                else:
                    print(f"   ⚠️ No team mapping found for {full_player_name}")

                # Get link for detailed stats and extract native TennisScores ID
                link = row.find("a")
                stats = {"Wins": 0, "Losses": 0, "Win %": "0.0%", "match_details": []}

                if link:
                    href = link.get("href", "")
                    # Extract native TennisScores player ID from URL
                    tenniscores_id = extract_tenniscores_player_id(href)
                    # Generate Player ID using TennisScores native ID (preferred) or fallback
                    player_id = create_player_id(
                        tenniscores_id, first_name, last_name, club_name
                    )

                    try:
                        print(
                            f"   🔍 Getting detailed stats for {first_name} {last_name}"
                        )
                        stats = get_player_stats(href, driver, config)
                        print(
                            f"   ✅ Stats: W/L: {stats['Wins']}-{stats['Losses']} ({stats['Win %']})"
                        )
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
                    "rating": (
                        float(rating)
                        if rating.replace(".", "", 1).isdigit()
                        else rating
                    ),
                    "wins": stats["Wins"],
                    "losses": stats["Losses"],
                    "matches": [
                        {
                            "date": m["date"],
                            "end_pti": (
                                float(m["end_pti"])
                                if str(m["end_pti"]).replace(".", "", 1).isdigit()
                                else m["end_pti"]
                            ),
                            "series": m["series"],
                        }
                        for m in stats.get("match_details", [])
                    ],
                }
                all_players_json.append(player_json)

                processed_series.add(series_name)

                player_end_time = datetime.now()
                player_duration = player_end_time - player_start_time

                # Progress update with timing
                remaining_players = len(all_rows) - row_idx
                avg_time_per_player = (
                    (player_start_time - scraping_start_time).total_seconds() / row_idx
                    if scraping_start_time and row_idx > 0
                    else 0
                )
                estimated_remaining = (
                    remaining_players * avg_time_per_player
                    if avg_time_per_player > 0
                    else 0
                )
                eta = (
                    player_end_time + timedelta(seconds=estimated_remaining)
                    if estimated_remaining > 0
                    else None
                )

                print(
                    f"✅ Player completed in {player_duration.total_seconds():.1f}s | Progress: {row_idx}/{len(all_rows)} players"
                )
                if eta:
                    print(
                        f"   ⏰ ETA: {eta.strftime('%H:%M:%S')} (est. {estimated_remaining/60:.1f} min remaining)"
                    )

                # Small delay between players
                time.sleep(1)

            # Save all players to JSON
            filename = os.path.join(data_dir, "player_history.json")
            with open(filename, "w", encoding="utf-8") as jsonfile:
                json.dump(all_players_json, jsonfile, indent=2)

            # Calculate end time and duration
            end_time = datetime.now()
            total_duration = end_time - start_time
            scraping_end_time = end_time
            scraping_duration = (
                scraping_end_time - scraping_start_time
                if scraping_start_time
                else total_duration
            )

            print(f"\n🎉 SCRAPING COMPLETE!")
            print("=" * 70)

            # Detailed timing summary
            print(f"📅 SESSION SUMMARY - {end_time.strftime('%Y-%m-%d')}")
            print(f"🕐 Session Start:     {start_time.strftime('%H:%M:%S')}")
            if discovery_start_time:
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
            players_per_minute = (
                (len(all_players_json) / total_seconds * 60) if total_seconds > 0 else 0
            )

            print(f"📊 PERFORMANCE METRICS")
            print(f"📈 Total players scraped: {len(all_players_json)}")
            print(f"👥 Players per minute: {players_per_minute:.1f}")
            print(
                f"⚡ Average time per player: {total_seconds/len(all_players_json):.1f}s"
                if len(all_players_json) > 0
                else "⚡ Average time per player: N/A"
            )
            print()

            print(f"💾 Data saved to: {filename}")
            print(f"📈 Processed series: {', '.join(sorted(processed_series))}")

            # Print summary by series
            print(f"\n📈 SERIES BREAKDOWN:")
            series_counts = {}
            for player in all_players_json:
                series = player["series"]
                series_counts[series] = series_counts.get(series, 0) + 1

            for series, count in sorted(series_counts.items()):
                percentage = (
                    (count / len(all_players_json) * 100)
                    if len(all_players_json) > 0
                    else 0
                )
                print(f"  {series}: {count} players ({percentage:.1f}%)")

            print("=" * 70)
            
                    # Log enhanced session summary
        scraper_enhancements.log_session_summary()
        print("[Scraper] Finished scrape successfully")

    except Exception as e:
        print("[Scraper] Scrape failed with an exception")
        import traceback
        traceback.print_exc()
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
    league_subdomain = (
        input("Enter league subdomain (e.g., 'aptachicago', 'nstf'): ").strip().lower()
    )

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
