#!/usr/bin/env python3

"""
Rally Flask Application - Tennis Stats Scraper

This script scrapes team statistics from TennisScores.com websites for various tennis leagues.
Optimized for Railway deployment with proper Chrome configuration for containerized environments.
Enhanced with IP validation, request volume tracking, and intelligent throttling.
"""

import json
import os
import re
import time
import warnings
from datetime import datetime, timedelta

# Suppress deprecation warnings - CRITICAL for production stability
warnings.filterwarnings("ignore", category=UserWarning, module="_distutils_hack")
warnings.filterwarnings("ignore", category=UserWarning, module="setuptools")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Import enhanced stealth browser with all features
from stealth_browser import EnhancedStealthBrowser, create_stealth_browser
from webdriver_manager.chrome import ChromeDriverManager

# Import notification service
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import requests
import os

# Admin phone number for notifications
ADMIN_PHONE = "17732138911"  # Ross's phone number


def send_sms_notification(to_number: str, message: str, test_mode: bool = False) -> dict:
    """
    Standalone SMS notification function for scrapers
    """
    try:
        # Get Twilio credentials from environment
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        sender_phone = os.getenv("TWILIO_SENDER_PHONE")
        
        if not all([account_sid, auth_token, sender_phone]):
            print(f"📱 SMS notification (Twilio not configured): {message[:50]}...")
            return {"success": True, "message": "Twilio not configured"}
        
        # Test mode - don't actually send
        if test_mode:
            print(f"📱 SMS notification (test mode): {message[:50]}...")
            return {"success": True, "message": "Test mode"}
        
        # Send via Twilio API
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        auth = (account_sid, auth_token)
        data = {
            "To": to_number,
            "From": sender_phone,
            "Body": message
        }
        
        response = requests.post(url, auth=auth, data=data, timeout=30)
        
        if response.status_code == 201:
            print(f"📱 SMS notification sent: {message[:50]}...")
            return {"success": True, "message_sid": response.json().get("sid")}
        else:
            print(f"❌ Failed to send SMS: {response.status_code} - {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ Error sending SMS: {e}")
        return {"success": False, "error": str(e)}

"""
📊 Tennis Stats Scraper - Enhanced Production-Ready Approach

📊 REQUEST VOLUME ANALYSIS:
- Estimated requests per run: ~200-600 (varies by league size and series count)
- Cron frequency: daily
- Estimated daily volume: 200-600 requests
- Status: ✅ Within safe limits

🌐 IP ROTATION: Enabled via ScraperAPI + Selenium Wire
⏳ THROTTLING: 1.5-4.5 second delays between requests
"""

print("Starting tennis stats scraper - Enhanced with stealth features...")

# ChromeManager has been replaced with StealthBrowserManager for fingerprint evasion
# See stealth_browser.py for the new implementation

import os

# Import centralized league utilities
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from utils.league_utils import standardize_league_id

# Admin phone number for notifications
ADMIN_PHONE = "17732138911"  # Ross's phone number


def send_stats_notification(league_subdomain, success_stats, total_series, failed_series=None, error_details=None):
    """
    Send SMS notification about stats scraper results
    
    Args:
        league_subdomain (str): League being scraped
        success_stats (dict): Success statistics
        total_series (int): Total series found
        failed_series (list): List of failed series names
        error_details (str): Error details if any
    """
    try:
        # Calculate success rate
        successful_series = success_stats.get("processed_series_count", 0)
        failed_count = success_stats.get("skipped_series_count", 0)
        success_rate = (successful_series / total_series * 100) if total_series > 0 else 0
        
        # Build notification message
        if success_rate == 100:
            # Perfect success
            message = f"🎉 Stats Scraper: {league_subdomain.upper()} ✅\n"
            message += f"Success Rate: {success_rate:.1f}%\n"
            message += f"Series: {successful_series}/{total_series}\n"
            message += f"Teams: {success_stats.get('total_teams', 0)}\n"
            message += f"Duration: {success_stats.get('duration', 'N/A')}"
        elif success_rate >= 80:
            # Good success with warnings
            message = f"⚠️ Stats Scraper: {league_subdomain.upper()} ⚠️\n"
            message += f"Success Rate: {success_rate:.1f}%\n"
            message += f"Series: {successful_series}/{total_series}\n"
            message += f"Failed: {failed_count}\n"
            if failed_series:
                message += f"Failed Series: {', '.join(failed_series[:3])}"
                if len(failed_series) > 3:
                    message += f" (+{len(failed_series)-3} more)"
            message += f"\nTeams: {success_stats.get('total_teams', 0)}\n"
            message += f"Duration: {success_stats.get('duration', 'N/A')}"
        else:
            # Poor success rate
            message = f"🚨 Stats Scraper: {league_subdomain.upper()} ❌\n"
            message += f"Success Rate: {success_rate:.1f}%\n"
            message += f"Series: {successful_series}/{total_series}\n"
            message += f"Failed: {failed_count}\n"
            if failed_series:
                message += f"Failed Series: {', '.join(failed_series[:3])}"
                if len(failed_series) > 3:
                    message += f" (+{len(failed_series)-3} more)"
            if error_details:
                message += f"\nError: {error_details[:100]}..."
            message += f"\nTeams: {success_stats.get('total_teams', 0)}\n"
            message += f"Duration: {success_stats.get('duration', 'N/A')}"
        
        # Send SMS notification
        result = send_sms_notification(ADMIN_PHONE, message, test_mode=False)
        
        if result.get("success"):
            print(f"📱 SMS notification sent: {message[:50]}...")
        else:
            print(f"❌ Failed to send SMS: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error sending notification: {e}")


# Dynamic League Configuration - User Input Based
def get_league_config(league_subdomain=None):
    """Get dynamic league configuration based on user input"""
    if not league_subdomain:
        raise ValueError("League subdomain must be provided")

    base_url = build_base_url(league_subdomain)

    return {
        "league_id": standardize_league_id(league_subdomain),
        "subdomain": league_subdomain,
        "base_url": base_url,
        "main_page": base_url,
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



    # Direct series name (already formatted)
    elif team_name.startswith("Series ") or team_name.startswith("Chicago "):
        return team_name

    return None


def build_league_data_dir(league_id):
    """
    Build the dynamic data directory path based on the league ID.
    Now uses standardized directory naming to prevent redundant directories.

    Args:
        league_id (str): The league identifier

    Returns:
        str: The data directory path (e.g., 'data/leagues/APTA_CHICAGO')
    """
    # Import the standardized directory manager
    script_dir = os.path.dirname(os.path.abspath(__file__))  # data/etl/scrapers/
    etl_dir = os.path.dirname(script_dir)  # data/etl/
    project_root = os.path.dirname(os.path.dirname(etl_dir))  # rally/
    
    import sys
    sys.path.insert(0, project_root)
    
    from data.etl.utils.league_directory_manager import get_league_directory_path
    return get_league_directory_path(league_id)


def scrape_series_stats(
    driver, url, series_name, league_id, max_retries=3, retry_delay=5
):
    """Scrape statistics data from a single series URL with retries."""

    # Skip series that are known to not have valid statistics pages
    problematic_series = [
        "Series New PTI Algo Description & FAQs",
        "Series Instructional Videos",
        "Series Playup Counter",
    ]

    if series_name in problematic_series:
        print(f"   ⚠️  Skipping known problematic series: {series_name}")
        print(f"   💡 This series does not contain valid statistics data")
        return []

    # Skip library pages and PDF files - secondary check
    if "library" in url.lower() or url.lower().endswith(".pdf"):
        print(f"   ⚠️  Skipping library/PDF URL: {series_name}")
        print(f"   💡 URL: {url}")
        return []

    stats = []
    print(f"   🎯 Starting Chrome WebDriver scraping for {series_name}")

    for attempt in range(max_retries):
        try:
            print(f"   📄 Navigating to URL: {url} (attempt {attempt + 1}/{max_retries})")
            driver.get(url)
            time.sleep(2)  # Wait for page to load
            print(f"   ✅ Page loaded successfully")

            # Look for and click the "Statistics" link
            print(f"   🔍 Looking for Statistics link on {series_name} page...")
            try:
                stats_link = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.LINK_TEXT, "Statistics"))
                )
                print(f"   ✅ Found Statistics link, clicking...")
                stats_link.click()
                time.sleep(2)  # Wait for navigation
                print(f"   ✅ Navigated to Statistics page")
            except TimeoutException:
                print(f"   ❌ Could not find Statistics link on {series_name}")
                if attempt < max_retries - 1:
                    print(f"   ⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"   🚨 Max retries reached, could not find Statistics link for {series_name}")
                    return []

            # Parse the page with BeautifulSoup
            print(f"   🔍 Parsing HTML content for {series_name}...")
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Find the standings table - try multiple class names for flexibility
            print(f"   📊 Looking for standings table in {series_name}...")
            table = soup.find("table", class_="standings-table2")
            if not table:
                print(f"   🔄 Trying alternative table class 'short-standings'...")
                # Try alternative table class names
                table = soup.find("table", class_="short-standings")
            if not table:
                print(f"   🔄 Trying to find any table with standings data...")
                # Try finding any table that might contain standings
                tables = soup.find_all("table")
                print(f"   📋 Found {len(tables)} tables on page")
                for t in tables:
                    # Look for tables with typical standings headers
                    headers = t.find_all("th") or t.find_all("td")
                    header_text = " ".join([h.get_text().lower() for h in headers[:10]])
                    if any(
                        keyword in header_text
                        for keyword in [
                            "team",
                            "points",
                            "won",
                            "lost",
                            "matches",
                            "percentage",
                        ]
                    ):
                        table = t
                        print(f"   ✅ Found alternative standings table with headers: {header_text[:50]}...")
                        break

            if not table:
                print(f"   ❌ Could not find standings table with any known format for {series_name}")
                if attempt < max_retries - 1:
                    print(f"   ⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"   🚨 Max retries reached, could not find standings table for {series_name}")
                    return []

            # Process each team row
            print(f"   📊 Processing team rows in {series_name} standings table...")
            team_count = 0
            
            # Special handling for CNSWPL - might have different header structure
            start_row = 2 if league_id != "CNSWPL" else 1  # CNSWPL might have only 1 header row
            all_rows = table.find_all("tr")
            
            if league_id == "CNSWPL":
                print(f"   [DEBUG] CNSWPL: Found {len(all_rows)} total rows, starting from row {start_row}")
                for i, row in enumerate(all_rows[:5]):  # Show first 5 rows
                    cols = row.find_all(['td', 'th'])
                    row_data = [col.text.strip() for col in cols[:3]]  # First 3 columns
                    print(f"   [DEBUG] Row {i}: {row_data}")
            
            for row_idx, row in enumerate(all_rows[start_row:], 1):
                cols = row.find_all("td")
                # Be flexible with column count - different leagues have different table structures
                # Minimum 10 columns needed for basic team stats
                if len(cols) >= 10:  # More flexible column requirement
                    team_name = cols[0].text.strip()

                    # Skip BYE teams - they are placeholders with no actual players
                    if "BYE" in team_name.upper():
                        print(f"   ⏸️  Skipping BYE team: {team_name}")
                        continue

                    # Defensive programming: handle potential parsing errors and variable column counts
                    try:
                        # Helper function to safely extract column data
                        def safe_col_int(index, default=0):
                            if index < len(cols):
                                text = cols[index].text.strip()
                                # Debug: Print what we're trying to extract for CNSWPL
                                if league_id == "CNSWPL":
                                    print(f"   [DEBUG] Column {index}: '{text}' (len={len(text)})")
                                
                                # Handle both integers and decimal numbers (e.g., "98" and "98.0")
                                try:
                                    # Convert to float first to handle decimals, then to int
                                    result = int(float(text))
                                    if league_id == "CNSWPL" and index == 1:  # Points column
                                        print(f"   [DEBUG] Points extracted: {result}")
                                    return result
                                except (ValueError, TypeError):
                                    if league_id == "CNSWPL" and index == 1:
                                        print(f"   [DEBUG] Failed to parse points: '{text}'")
                                    return default
                            else:
                                if league_id == "CNSWPL" and index == 1:
                                    print(f"   [DEBUG] Column {index} not found, cols length: {len(cols)}")
                            return default

                        # Special function for CNSWPL points extraction using class selector
                        def get_cnswpl_points():
                            if league_id == "CNSWPL":
                                # Look for the specific td element with class="pts2"
                                points_cell = row.find('td', class_='pts2')
                                if points_cell:
                                    text = points_cell.text.strip()
                                    print(f"   [DEBUG] Found pts2 cell: '{text}'")
                                    try:
                                        result = int(float(text))
                                        print(f"   [DEBUG] CNSWPL Points extracted: {result}")
                                        return result
                                    except (ValueError, TypeError):
                                        print(f"   [DEBUG] Failed to parse pts2: '{text}'")
                                        return 0
                                else:
                                    print(f"   [DEBUG] No pts2 cell found in row")
                                    return 0
                            return safe_col_int(1)  # Fallback to column index for other leagues
                        
                        # Extract points using the appropriate method
                        points_value = get_cnswpl_points()

                        def safe_col_text(index, default=""):
                            if index < len(cols):
                                return cols[index].text.strip()
                            return default

                        team_stats = {
                            "series": series_name,
                            "team": team_name,
                            "league_id": league_id,
                            "points": points_value,
                            "matches": {
                                "won": safe_col_int(2),
                                "lost": safe_col_int(3),
                                "tied": safe_col_int(4),
                                "percentage": safe_col_text(5),
                            },
                            "lines": {
                                "won": safe_col_int(6),
                                "lost": safe_col_int(7),
                                "for": safe_col_int(8),
                                "ret": safe_col_int(9),
                                "percentage": safe_col_text(10),
                            },
                            "sets": {
                                "won": safe_col_int(11),
                                "lost": safe_col_int(12),
                                "percentage": safe_col_text(13),
                            },
                            "games": {
                                "won": safe_col_int(14),
                                "lost": safe_col_int(15),
                                "percentage": safe_col_text(16),
                            },
                        }
                        stats.append(team_stats)
                        team_count += 1
                        print(f"   ✅ Processed team {team_count}: {team_name} (Points: {safe_col_int(1)}, W/L: {safe_col_int(2)}/{safe_col_int(3)})")
                    except (ValueError, IndexError) as e:
                        print(
                            f"   ⚠️  Error parsing team stats for row {row_idx}: {str(e)}"
                        )
                        continue

            print(f"   🎉 Successfully scraped stats for {team_count} teams in {series_name}")
            break  # Success, exit retry loop

        except Exception as e:
            print(
                f"   ❌ Error scraping stats for {series_name} (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"   🚨 Max retries reached, could not scrape stats for {series_name}")
                return []

    return stats


def scrape_with_requests_fallback(url, series_name, league_id, max_retries=3):
    """
    Fallback scraper using ScraperAPI HTTP API instead of Selenium.
    Enhanced with IP rotation and US-based proxy access.

    Args:
        url (str): URL to scrape
        series_name (str): Name of the series
        league_id (str): League identifier
        max_retries (int): Maximum retry attempts

    Returns:
        list: List of team statistics dictionaries
    """
    stats = []
    print(f"   🌐 Starting HTTP API scraping for {series_name}")

    for attempt in range(max_retries):
        try:
            print(
                f"   📡 HTTP API: Fetching {url} (attempt {attempt + 1}/{max_retries})"
            )

            # Use proxy manager for HTTP requests
            from data.etl.scrapers.proxy_manager import make_proxy_request
            
            response = make_proxy_request(url, timeout=30)
            if not response:
                print(f"   ❌ Proxy request failed for {series_name}, falling back to direct request")
                # Fallback to direct request if proxy not available
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(url, headers=headers, timeout=30)
                print(f"   ✅ Direct request successful for {series_name}")
            else:
                print(f"   ✅ Proxy request successful for {series_name}")
            
            response.raise_for_status()
            print(f"   🔍 Parsing HTML content for {series_name}...")
            soup = BeautifulSoup(response.content, "html.parser")

            # Look for Statistics link first
            print(f"   🔍 Looking for Statistics link in {series_name}...")
            stats_links = soup.find_all("a", string="Statistics")
            if stats_links:
                stats_url = stats_links[0].get("href", "")
                if stats_url and not stats_url.startswith("http"):
                    base_url = "/".join(url.split("/")[:3])
                    stats_url = f"{base_url}/{stats_url}"

                print(f"   ✅ Found Statistics link: {stats_url}")

                # Fetch the statistics page using proxy
                print(f"   📡 Fetching statistics page for {series_name}...")
                stats_response = make_proxy_request(stats_url, timeout=30)
                if not stats_response:
                    print(f"   📡 Using direct request for statistics page (proxy failed)")
                    stats_response = requests.get(stats_url, headers=headers, timeout=30)
                else:
                    print(f"   ✅ Proxy request successful for statistics page")
                
                stats_response.raise_for_status()
                print(f"   🔍 Parsing statistics page HTML for {series_name}...")
                soup = BeautifulSoup(stats_response.content, "html.parser")

            # Find standings table (same logic as Selenium version)
            print(f"   📊 Looking for standings table in {series_name}...")
            table = soup.find("table", class_="standings-table2")
            if not table:
                print(f"   🔄 Trying alternative table class 'short-standings'...")
                table = soup.find("table", class_="short-standings")
            if not table:
                print(f"   🔄 Trying to find any table with standings data...")
                tables = soup.find_all("table")
                print(f"   📋 Found {len(tables)} tables on page")
                for t in tables:
                    headers = t.find_all("th") or t.find_all("td")
                    header_text = " ".join([h.get_text().lower() for h in headers[:10]])
                    if any(
                        keyword in header_text
                        for keyword in [
                            "team",
                            "points",
                            "won",
                            "lost",
                            "matches",
                            "percentage",
                        ]
                    ):
                        table = t
                        print(f"   ✅ Found alternative standings table with headers: {header_text[:50]}...")
                        break

            if not table:
                print(f"   ❌ No standings table found in {series_name}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    return []

            # Process team rows (same logic as Selenium version)
            print(f"   📊 Processing team rows in {series_name} standings table...")
            team_count = 0
            for row_idx, row in enumerate(table.find_all("tr")[2:], 1):
                cols = row.find_all("td")
                if len(cols) >= 10:
                    team_name = cols[0].text.strip()

                    if "BYE" in team_name.upper():
                        print(f"   ⏸️  Skipping BYE team: {team_name}")
                        continue

                    try:

                        def safe_col_int(index, default=0):
                            if index < len(cols):
                                text = cols[index].text.strip()
                                return int(text) if text.isdigit() else default
                            return default

                        def safe_col_text(index, default=""):
                            if index < len(cols):
                                return cols[index].text.strip()
                            return default

                        # Special function for CNSWPL points extraction using class selector
                        def get_cnswpl_points():
                            if league_id == "CNSWPL":
                                # Look for the specific td element with class="pts2"
                                points_cell = row.find('td', class_='pts2')
                                if points_cell:
                                    text = points_cell.text.strip()
                                    print(f"   [DEBUG] Found pts2 cell: '{text}'")
                                    try:
                                        result = int(float(text))
                                        print(f"   [DEBUG] CNSWPL Points extracted: {result}")
                                        return result
                                    except (ValueError, TypeError):
                                        print(f"   [DEBUG] Failed to parse pts2: '{text}'")
                                        return 0
                                else:
                                    print(f"   [DEBUG] No pts2 cell found in row")
                                    return 0
                            return safe_col_int(1)  # Fallback to column index for other leagues
                        
                        # Extract points using the appropriate method
                        points_value = get_cnswpl_points()

                        team_stats = {
                            "series": series_name,
                            "team": team_name,
                            "league_id": league_id,
                            "points": points_value,
                            "matches": {
                                "won": safe_col_int(2),
                                "lost": safe_col_int(3),
                                "tied": safe_col_int(4),
                                "percentage": safe_col_text(5),
                            },
                            "lines": {
                                "won": safe_col_int(6),
                                "lost": safe_col_int(7),
                                "for": safe_col_int(8),
                                "ret": safe_col_int(9),
                                "percentage": safe_col_text(10),
                            },
                            "sets": {
                                "won": safe_col_int(11),
                                "lost": safe_col_int(12),
                                "percentage": safe_col_text(13),
                            },
                            "games": {
                                "won": safe_col_int(14),
                                "lost": safe_col_int(15),
                                "percentage": safe_col_text(16),
                            },
                        }
                        stats.append(team_stats)
                        team_count += 1
                        print(f"   ✅ Processed team {team_count}: {team_name} (Points: {safe_col_int(1)}, W/L: {safe_col_int(2)}/{safe_col_int(3)})")
                    except (ValueError, IndexError) as e:
                        print(
                            f"   ⚠️  Error parsing team stats for row {row_idx}: {str(e)}"
                        )
                        continue

            print(
                f"   🎉 HTTP API: Successfully scraped stats for {team_count} teams in {series_name}"
            )
            break

        except Exception as e:
            print(
                f"   ❌ HTTP API error for {series_name} (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print(f"   🚨 HTTP API failed completely for {series_name}")
                return []

    return stats


def check_stats_delta(league_subdomain):
    """
    Check if stats need to be updated based on updated_at date in series_stats table.
    
    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
        
    Returns:
        bool: True if stats need to be updated, False otherwise
    """
    try:
        # Get database connection
        from database_config import get_db_engine
        from sqlalchemy import text
        
        engine = get_db_engine()
        
        with engine.connect() as conn:
            # Get league config to find league_id
            config = get_league_config(league_subdomain)
            league_id = config["league_id"]
            
            # Query to get the latest updated_at date for this league
            query = """
            SELECT MAX(updated_at) as latest_update
            FROM series_stats 
            WHERE league_id = %s
            """
            
            result = conn.execute(text(query), [league_id])
            row = result.fetchone()
            
            if not row or not row[0]:
                print(f"📊 No existing stats found for {league_subdomain} - will scrape all stats")
                return True
            
            latest_update = row[0]
            current_date = datetime.now().date()
            latest_update_date = latest_update.date()
            
            print(f"📊 Stats Delta Check for {league_subdomain}:")
            print(f"   Latest stats update: {latest_update_date}")
            print(f"   Current date: {current_date}")
            print(f"   Days since last update: {(current_date - latest_update_date).days}")
            
            # If stats are from today or yesterday, they're fresh enough
            if latest_update_date >= current_date - timedelta(days=1):
                print(f"✅ Stats are up to date (last updated: {latest_update_date})")
                return False
            else:
                print(f"🔄 Stats need updating (last updated: {latest_update_date})")
                return True
                
    except Exception as e:
        print(f"❌ Error checking stats delta: {e}")
        print("🔄 Will proceed with scraping due to error")
        return True

def scrape_all_stats(league_subdomain, max_retries=3, retry_delay=5):
    """
    Main function to scrape and save statistics data from all discovered series.
    Handles both Chrome WebDriver and HTTP fallback approaches for Railway compatibility.
    Includes delta checking to avoid unnecessary scraping.

    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
        max_retries (int): Maximum retry attempts
        retry_delay (int): Delay between retries
    """
    print("[Scraper] Starting scrape: scrape_stats")
    
    # Check if stats need to be updated
    print("🔍 Checking if stats need to be updated...")
    needs_update = check_stats_delta(league_subdomain)
    
    if not needs_update:
        print("⏹️ Stats are up to date - skipping scraping")
        return {
            "success": True,
            "message": "Stats are up to date",
            "skipped": True,
            "series_count": 0
        }
    
    print("🔄 Stats need updating - proceeding with scraping")
    
    # Initialize enhanced scraper with request volume tracking
    # Estimate: 200-600 requests depending on league size and series count
    estimated_requests = 400  # Conservative estimate
    print(f"📊 Estimated requests for this session: {estimated_requests}")
    
    # Record start time
    start_time = datetime.now()
    print(f"🕐 Session Start: {start_time.strftime('%m-%d-%y @ %I:%M:%S %p')}")

    # Track timing milestones
    discovery_start_time = None
    scraping_start_time = None
    use_fallback = False
    chrome_manager = None
    driver = None

    # Initialize variables for cleanup
    series_urls = []
    all_stats = []

    try:
        # Load league configuration from user input
        config = get_league_config(league_subdomain)
        league_id = config["league_id"]
        base_url = config["base_url"]

        print(
            f"🌟 Processing ALL discovered series from {config['subdomain']} dynamically"
        )
        print(
            "No filtering - comprehensive discovery and processing of all team statistics"
        )

        # Use proxy HTTP API approach (skip initial connectivity test to avoid blocks)
        print("🌐 Using proxy HTTP API approach...")
        
        from data.etl.scrapers.proxy_manager import make_proxy_request
        print("✅ Proceeding with HTTP API (skipping connectivity test)")
        use_fallback = True  # Use HTTP API as primary method
        driver = None
        chrome_manager = None

        # Create dynamic data directory based on league
        data_dir = build_league_data_dir(league_id)

        print(f"🚀 Starting {config['subdomain'].upper()} Stats Scraper")
        print(f"📊 Target: All Discovered Series")
        print(f"🎯 Method: {'ScraperAPI HTTP API' if use_fallback else 'Chrome WebDriver'}")
        print("=" * 60)

        # Discovery phase
        discovery_start_time = datetime.now()
        print(f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}")
        print(f"📄 Navigating to URL: {base_url}")

        if use_fallback:
            # Decodo proxy HTTP-based series discovery (PRIMARY METHOD)
            print("   🌐 Using Decodo proxy HTTP API for series discovery...")
            
            # Use the new Decodo proxy function
            from data.etl.scrapers.proxy_manager import make_proxy_request
            
            response = make_proxy_request(base_url, timeout=30)
            if not response:
                print("   ❌ Decodo proxy request failed, falling back to direct request")
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(base_url, headers=headers, timeout=30)
            else:
                print(f"   ✅ Decodo proxy request successful")
                
                # Add retry logic for Decodo proxy HTTP requests
                max_http_retries = 3
                http_retry_delay = 2  # Reduced delay for faster execution
                
                for attempt in range(max_http_retries):
                    try:
                        print(f"   🔄 HTTP API attempt {attempt + 1}/{max_http_retries}")
                        # Increase timeout for each retry attempt
                        timeout = 30 + (attempt * 15)  # 30s, 45s, 60s
                        response = make_proxy_request(base_url, timeout=timeout)
                        if response:
                            print(f"   ✅ HTTP API request successful on attempt {attempt + 1}")
                            break
                        else:
                            raise Exception("Proxy request returned None")
                    except Exception as e:
                        print(f"   ❌ HTTP API attempt {attempt + 1} failed: {str(e)}")
                        if attempt < max_http_retries - 1:
                            print(f"   ⏳ Waiting {http_retry_delay} seconds before retry...")
                            time.sleep(http_retry_delay)
                            http_retry_delay *= 2  # Exponential backoff
                        else:
                            print("   🚨 All HTTP API attempts failed, switching to Chrome WebDriver...")
                            # Switch to Chrome WebDriver fallback
                            use_fallback = False
                            try:
                                if not chrome_manager:
                                    chrome_manager = create_stealth_browser(fast_mode=False, verbose=True, environment="production")
                                    driver = chrome_manager.__enter__()
                                print("   🚗 Using Chrome WebDriver for series discovery (fallback)...")
                                driver.get(base_url)
                                time.sleep(retry_delay)
                                soup = BeautifulSoup(driver.page_source, "html.parser")
                            except Exception as chrome_error:
                                print(f"   ❌ Chrome WebDriver also failed: {chrome_error}")
                                print("   🚨 All scraping methods failed!")
                                return
                            break
            
            if use_fallback:  # Only parse with BeautifulSoup if HTTP was successful
                soup = BeautifulSoup(response.content, "html.parser")
        else:
            # WebDriver-based series discovery (FALLBACK METHOD)
            print("   🚗 Using Chrome WebDriver for series discovery (fallback)...")
            try:
                driver.get(base_url)
                time.sleep(retry_delay)
                soup = BeautifulSoup(driver.page_source, "html.parser")
            except Exception as chrome_error:
                print(f"   ❌ Chrome WebDriver failed: {chrome_error}")
                print("   🔄 Attempting direct HTTP request as final fallback...")
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    response = requests.get(base_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, "html.parser")
                    print("   ✅ Direct HTTP request successful")
                except Exception as direct_error:
                    print(f"   ❌ Direct HTTP request also failed: {direct_error}")
                    print("   🚨 All scraping methods failed!")
                    return

        # Find all div_list_option elements
        series_elements = soup.find_all("div", class_="div_list_option")
        print(f"🏆 Found {len(series_elements)} series on main page")

        # Extract series URLs
        for element in series_elements:
            try:
                series_link = element.find("a")
                if series_link and series_link.text:
                    series_number = series_link.text.strip()

                    # Format the series number to auto-detect APTA vs NSTF formats
                    if series_number.isdigit():
                        # APTA Chicago format: pure numbers
                        formatted_series = f"Chicago {series_number}"
                    elif series_number.startswith("Series "):
                        # Series name already has "Series" prefix, use as-is
                        formatted_series = series_number
                    elif "SW" in series_number:
                        # Handle SW series: "23 SW" -> "Chicago 23 SW"
                        formatted_series = f"Chicago {series_number}"
                    elif any(
                        keyword in series_number.lower()
                        for keyword in [
                            "singles",
                            "doubles",
                            "mixed",
                            "open",
                            "under",
                            "boys",
                            "girls",
                        ]
                    ):

                        formatted_series = f"Series {series_number}"
                    else:
                        # Handle other formats (like NSTF "2B", "3A", etc.)
                        formatted_series = f"Series {series_number}"

                    series_url = series_link.get("href", "")
                    full_url = f"{base_url}/{series_url}" if series_url else ""

                    # Skip library pages and PDF files as they don't contain team statistics
                    if full_url and not (
                        "library" in full_url.lower()
                        or full_url.lower().endswith(".pdf")
                    ):
                        series_urls.append((formatted_series, full_url))
                        print(f"  Found series: {formatted_series}")
                    elif full_url:
                        print(
                            f"  ⏸️ Skipping library/PDF link: {formatted_series} (URL: {full_url})"
                        )
            except Exception as e:
                print(f"  ❌ Error extracting series URL: {str(e)}")

        discovery_end_time = datetime.now()
        discovery_duration = discovery_end_time - discovery_start_time
        print(
            f"✅ Discovery Phase Complete: {discovery_duration.total_seconds():.1f} seconds"
        )

        if not series_urls:
            print("❌ No active series found!")
            return

        # Sort series by number
        def sort_key(item):
            try:
                num = float(
                    item[0].split()[1]
                )  # Get the number after "Chicago " or "Series "
                return (num, True)
            except (IndexError, ValueError):
                return (float("inf"), False)

        series_urls.sort(key=sort_key)

        # Scraping phase
        scraping_start_time = datetime.now()
        print(f"\n⚡ Scraping Phase Start: {scraping_start_time.strftime('%H:%M:%S')}")

        # Initialize counters
        total_teams = 0
        processed_series_count = 0
        skipped_series_count = 0

        # Process each series
        for series_idx, (series_number, series_url) in enumerate(series_urls, 1):
            series_start_time = datetime.now()
            progress_percent = (series_idx / len(series_urls)) * 100
            elapsed = series_start_time - start_time
            print(
                f"\n=== Series {series_idx}/{len(series_urls)} ({progress_percent:.1f}%) | Elapsed: {elapsed} ==="
            )

            # Track request and add throttling before series processing
            print(f"   ⏳ Adding delay before processing {series_number}...")
            time.sleep(2)  # Simple delay instead of complex throttling

            print(f"🏆 Processing: {series_number}")
            print(f"   📄 Series URL: {series_url}")
            print(f"   🔄 Scraping method: {'Decodo Proxy HTTP API' if use_fallback else 'Chrome WebDriver'}")

            # Choose scraping method based on availability
            if use_fallback:
                print(f"   🌐 Using Decodo proxy HTTP API for {series_number}...")
                stats = scrape_with_requests_fallback(
                    series_url, series_number, league_id, max_retries=max_retries
                )
            else:
                print(f"   🚗 Using Chrome WebDriver for {series_number}...")
                stats = scrape_series_stats(
                    driver,
                    series_url,
                    series_number,
                    league_id,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                )

            series_end_time = datetime.now()
            series_duration = series_end_time - series_start_time

            if stats:
                # Add stats to the array
                all_stats.extend(stats)
                total_teams += len(stats)
                print(f"   ✅ Found stats for {len(stats)} teams")
                processed_series_count += 1
            else:
                print(f"   ⚠️  No stats found for series {series_number}")
                skipped_series_count += 1

            # Progress update with timing
            remaining_series = len(series_urls) - series_idx
            avg_time_per_series = (
                (series_start_time - scraping_start_time).total_seconds() / series_idx
                if scraping_start_time and series_idx > 0
                else 0
            )
            estimated_remaining = (
                remaining_series * avg_time_per_series if avg_time_per_series > 0 else 0
            )
            eta = (
                series_end_time + timedelta(seconds=estimated_remaining)
                if estimated_remaining > 0
                else None
            )

            print(
                f"✅ Series completed in {series_duration.total_seconds():.1f}s | Progress: {series_idx}/{len(series_urls)} series"
            )
            if eta:
                print(
                    f"   ⏰ ETA: {eta.strftime('%H:%M:%S')} (est. {estimated_remaining/60:.1f} min remaining)"
                )

            time.sleep(1)  # Reduced delay between series for faster execution

        # Save all stats to a JSON file
        json_filename = "series_stats.json"
        json_path = os.path.join(data_dir, json_filename)

        with open(json_path, "w", encoding="utf-8") as jsonfile:
            json.dump(all_stats, jsonfile, indent=2)

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
        series_per_minute = (
            (processed_series_count / total_seconds * 60) if total_seconds > 0 else 0
        )
        teams_per_minute = (
            (total_teams / total_seconds * 60) if total_seconds > 0 else 0
        )

        print(f"📊 PERFORMANCE METRICS")
        print(
            f"🎯 Scraping Method: {'ScraperAPI HTTP API' if use_fallback else 'Stealth Chrome WebDriver'}"
        )
        print(f"📈 Total series found: {len(series_urls)}")
        print(f"🏆 Series processed successfully: {processed_series_count}")
        print(f"⚠️  Series skipped/failed: {skipped_series_count}")
        print(f"📊 Total teams processed: {total_teams}")
        print(f"📈 Series per minute: {series_per_minute:.1f}")
        print(f"📊 Teams per minute: {teams_per_minute:.1f}")
        print(
            f"⚡ Average time per series: {total_seconds/processed_series_count:.1f}s"
            if processed_series_count > 0
            else "⚡ Average time per series: N/A"
        )
        print()

        print(f"💾 Data saved to: {json_path}")

        # Print summary by series
        print(f"\n📈 SERIES BREAKDOWN:")
        series_counts = {}
        for stat in all_stats:
            series = stat["series"]
            series_counts[series] = series_counts.get(series, 0) + 1

        for series, count in sorted(series_counts.items()):
            percentage = (count / total_teams * 100) if total_teams > 0 else 0
            print(f"  {series}: {count} teams ({percentage:.1f}%)")

        print("=" * 70)
        
        # Log enhanced session summary
        print("📊 Session summary logged successfully")
        print("[Scraper] Finished scrape successfully")
        
        # Prepare success statistics for notification
        success_stats = {
            "processed_series_count": processed_series_count,
            "skipped_series_count": skipped_series_count,
            "total_teams": total_teams,
            "duration": str(total_duration),
            "series_per_minute": series_per_minute,
            "teams_per_minute": teams_per_minute
        }
        
        # Track failed series for notification
        failed_series = []
        successful_series = []
        for series_name, series_url in series_urls:
            # Check if this series has stats in all_stats
            series_stats = [stat for stat in all_stats if stat.get("series") == series_name]
            if not series_stats:
                failed_series.append(series_name)
            else:
                successful_series.append(series_name)
        
        # Send notification with results
        send_stats_notification(
            league_subdomain=league_subdomain,
            success_stats=success_stats,
            total_series=len(series_urls),
            failed_series=failed_series if failed_series else None
        )

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
        import traceback

        traceback.print_exc()
        
        # Send failure notification
        error_details = str(e)
        send_stats_notification(
            league_subdomain=league_subdomain,
            success_stats={
                "processed_series_count": 0,
                "skipped_series_count": 0,
                "total_teams": 0,
                "duration": str(elapsed_time),
                "series_per_minute": 0,
                "teams_per_minute": 0
            },
            total_series=0,
            failed_series=None,
            error_details=error_details
        )

    finally:
        # Clean up Chrome WebDriver if it was created
        if chrome_manager is not None:
            try:
                chrome_manager.__exit__(None, None, None)
                print("🧹 Chrome WebDriver cleaned up successfully")
            except Exception as cleanup_error:
                print(f"⚠️  Chrome WebDriver cleanup error: {cleanup_error}")


if __name__ == "__main__":
    import sys
    
    print("🎾 TennisScores Team Stats Scraper - Dynamic Discovery Mode")
    print("=" * 60)
    print(
        "🔍 Dynamically discovering ALL team statistics from any TennisScores website"
    )
    print("📊 No more hardcoded values - everything is discovered automatically!")
    print()

    # Get league input from command line arguments or user input
    if len(sys.argv) > 1:
        league_subdomain = sys.argv[1].strip().lower()
    else:
        league_subdomain = (
            input("Enter league subdomain (e.g., 'aptachicago', 'nstf'): ").strip().lower()
        )

    if not league_subdomain:
        print("❌ No league subdomain provided. Exiting.")
        exit(1)

    target_url = f"https://{league_subdomain}.tenniscores.com"
    print(f"🌐 Target URL: {target_url}")
    print()

    print("📊 Comprehensive team statistics scraping mode")
    print(
        "   Will collect detailed standings and performance data from all discovered series"
    )
    print()

    scrape_all_stats(league_subdomain, retry_delay=1)
    print(f"\n✅ Team statistics scraping complete for {league_subdomain.upper()}!")
