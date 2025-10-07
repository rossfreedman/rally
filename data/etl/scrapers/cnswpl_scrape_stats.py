#!/usr/bin/env python3

"""
Rally Flask Application - CNSWPL Stats Scraper

This script scrapes team statistics from CNSWPL (Chicago North Suburban Women's Paddle League) 
TennisScores.com website. Optimized for Railway deployment with proper Chrome configuration 
for containerized environments. Enhanced with IP validation, request volume tracking, and 
intelligent throttling.
"""

# Set environment variables BEFORE any imports to prevent proxy testing
import os
os.environ['SKIP_PROXY_TEST'] = '1'
os.environ['QUICK_TEST'] = '1'
os.environ['FAST_MODE'] = '1'

import json
import re
import time
import warnings
from datetime import datetime, timedelta
from urllib.parse import urljoin

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
from helpers.stealth_browser import EnhancedStealthBrowser, create_stealth_browser
from webdriver_manager.chrome import ChromeDriverManager

# Import speed optimizations with safe fallbacks
try:
    from helpers.adaptive_pacer import pace_sleep, mark
    from helpers.stealth_browser import stop_after_selector
    SPEED_OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    SPEED_OPTIMIZATIONS_AVAILABLE = False
    print("⚠️ Speed optimizations not available - using standard pacing")
    
    # Safe no-op fallbacks
    def pace_sleep():
        pass
        
    def mark(*args, **kwargs):
        pass
        
    def stop_after_selector(*args, **kwargs):
        pass

def _pacer_mark_ok():
    """Helper function to safely mark successful responses for adaptive pacing."""
    try:
        mark('ok')
    except Exception:
        pass

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


# CNSWPL Configuration - Hardcoded for CNSWPL only
def get_cnswpl_config():
    """Get CNSWPL-specific configuration"""
    return {
        "league_id": "CNSWPL",
        "subdomain": "cnswpl",
        "base_url": "https://cnswpl.tenniscores.com",
        "main_page": "https://cnswpl.tenniscores.com",
        "player_page_mod": "nndz-SkhmOW1PQ3V4Zz09",
        "team_page_mod": "nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D",
    }


def get_cnswpl_base_url():
    """
    Get the CNSWPL base URL.

    Returns:
        str: The complete CNSWPL base URL
    """
    return "https://cnswpl.tenniscores.com"


def extract_cnswpl_series_name_from_team(team_name):
    """
    Extract series name from CNSWPL team name.

    Args:
        team_name (str): CNSWPL team name in various formats

    Returns:
        str: Standardized series name or None if not detected

    Examples:
        CNSWPL: "Club S1" -> "Series 1"
        CNSWPL: "Club S2A" -> "Series 2A"
        CNSWPL: "Club S2B" -> "Series 2B"
    """
    if not team_name:
        return None

    team_name = team_name.strip()

    # CNSWPL format: "Club SNumber" or "Club SNumberLetter" (e.g., S1, S2A, S2B)
    if re.search(r"S(\d+[A-Z]*)", team_name):
        match = re.search(r"S(\d+[A-Z]*)", team_name)
        if match:
            series_identifier = match.group(1)
            return f"Series {series_identifier}"

    # CNSWPL Sunday formats
    elif "Sunday A" in team_name:
        return "Series A"
    elif "Sunday B" in team_name:
        return "Series B"

    # Direct series name (already formatted)
    elif team_name.startswith("Series "):
        return team_name

    return None


def format_cnswpl_series_name(series_name):
    """
    Format CNSWPL series name to match players.json format.
    
    Examples:
        "Series 1" -> "Series 1"
        "Series 2A" -> "Series 2A"
        "Series 2B" -> "Series 2B"
        "Series A" -> "Series A"
        "Series B" -> "Series B"
    """
    if not series_name:
        return series_name
    
    series_name = series_name.strip()
    
    # CNSWPL series are already in the correct format
    if series_name.startswith("Series "):
        return series_name
    
    # If it doesn't start with "Series", add the prefix
    return f"Series {series_name}"

def format_cnswpl_team_name_for_output(team_name, series_name):
    """
    Format CNSWPL team name to match players.json format.
    
    Examples:
        "Club S1" -> "Club S1"
        "Club S2A" -> "Club S2A"
        "Club S2B" -> "Club S2B"
    """
    if not team_name:
        return team_name
    
    team_name = team_name.strip()
    
    # CNSWPL team names are typically already in the correct format
    # Just ensure they're clean
    return team_name


def get_cnswpl_data_dir():
    """
    Get the CNSWPL data directory path.

    Returns:
        str: The CNSWPL data directory path
    """
    # Import the standardized directory manager
    script_dir = os.path.dirname(os.path.abspath(__file__))  # data/etl/scrapers/
    etl_dir = os.path.dirname(script_dir)  # data/etl/
    project_root = os.path.dirname(os.path.dirname(etl_dir))  # rally/
    
    import sys
    sys.path.insert(0, project_root)
    
    from data.etl.utils.league_directory_manager import get_league_directory_path
    return get_league_directory_path("CNSWPL")


def scrape_cnswpl_series_stats(
    driver, url, series_name, max_retries=3, retry_delay=5
):
    """Scrape CNSWPL statistics data from a single series URL with retries."""

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
            pace_sleep()  # Adaptive pacing before navigation
            driver.get(url)
            
            # Use stop-after-selector for faster page ready detection
            if SPEED_OPTIMIZATIONS_AVAILABLE:
                try:
                    from selenium.webdriver.common.by import By
                    stop_after_selector(driver, By.CSS_SELECTOR, "table, .standings, .stats", timeout=8)
                except Exception:
                    time.sleep(1)  # Fallback delay if optimization fails
            else:
                time.sleep(2)  # Original delay as fallback
                
            _pacer_mark_ok()  # Mark successful page load
            print(f"   ✅ Page loaded successfully")

            # Look for and click the "Statistics" link
            print(f"   🔍 Looking for Statistics link on {series_name} page...")
            try:
                stats_link = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.LINK_TEXT, "Statistics"))
                )
                print(f"   ✅ Found Statistics link, clicking...")
                stats_link.click()
                
                # Use intelligent wait for navigation
                if SPEED_OPTIMIZATIONS_AVAILABLE:
                    try:
                        from selenium.webdriver.common.by import By
                        stop_after_selector(driver, By.CSS_SELECTOR, "table.standings, .stats-table, table", timeout=10)
                    except Exception:
                        time.sleep(2)  # Fallback delay
                else:
                    time.sleep(2)  # Original delay as fallback
                    
                _pacer_mark_ok()  # Mark successful navigation
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
            
            # Handle different header structures - most leagues have 2 header rows
            start_row = 2  # Standard: skip 2 header rows (grouping + column headers)
            all_rows = table.find_all("tr")
            
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
                                print(f"   [DEBUG] Column {index}: '{text}' (len={len(text)})")
                                
                                # Handle both integers and decimal numbers (e.g., "98" and "98.0")
                                try:
                                    # Convert to float first to handle decimals, then to int
                                    result = int(float(text))
                                    if index == 1:  # Points column
                                        print(f"   [DEBUG] Points extracted: {result}")
                                    return result
                                except (ValueError, TypeError):
                                    if index == 1:
                                        print(f"   [DEBUG] Failed to parse points: '{text}'")
                                    return default
                            else:
                                if index == 1:
                                    print(f"   [DEBUG] Column {index} not found, cols length: {len(cols)}")
                            return default

                        # Special function for CNSWPL points extraction using class selector
                        def get_cnswpl_points():
                            # CNSWPL-specific logic
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
                        return safe_col_int(1)  # Fallback to column index
                        
                        # Extract points using the appropriate method
                        points_value = get_cnswpl_points()

                        def safe_col_text(index, default=""):
                            if index < len(cols):
                                return cols[index].text.strip()
                            return default

                        team_stats = {
                            "series": series_name,
                            "team": format_cnswpl_team_name_for_output(team_name, series_name),
                            "league_id": "CNSWPL",
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


def scrape_cnswpl_with_stealth_browser(stealth_browser, url, series_name, max_retries=3):
    """
    Scrape CNSWPL statistics using Enhanced Stealth Browser with all stealth features.
    
    Args:
        stealth_browser: EnhancedStealthBrowser instance
        url (str): URL to scrape
        series_name (str): Name of the series
        max_retries (int): Maximum retry attempts

    Returns:
        list: List of team statistics dictionaries
    """
    stats = []
    print(f"   🛡️ Starting stealth browser scraping for {series_name}")

    for attempt in range(max_retries):
        try:
            print(f"   📡 Stealth Browser: Fetching {url} (attempt {attempt + 1}/{max_retries})")
            
            # Use stealth browser's get_html() method
            html_content = stealth_browser.get_html(url)
            if not html_content:
                raise Exception("Stealth browser returned empty content")
            
            print(f"   ✅ Stealth browser request successful for {series_name}")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Look for Statistics link
            print(f"   🔍 Looking for Statistics link in {series_name}...")
            stats_link = soup.find("a", href=True, string=lambda text: text and "Statistics" in text)
            
            if not stats_link:
                print(f"   ❌ No Statistics link found for {series_name}")
                return []
            
            stats_url = stats_link["href"]
            if not stats_url.startswith("http"):
                stats_url = urljoin(url, stats_url)
            
            print(f"   ✅ Found Statistics link: {stats_url}")
            
            # Fetch the statistics page using stealth browser
            print(f"   📡 Fetching statistics page for {series_name}...")
            stats_html = stealth_browser.get_html(stats_url)
            if not stats_html:
                raise Exception("Stealth browser returned empty content for statistics page")
            
            print(f"   ✅ Stealth browser request successful for statistics page")
            
            # Parse statistics page
            soup = BeautifulSoup(stats_html, "html.parser")
            
            # Find the standings table
            print(f"   📊 Looking for standings table in {series_name}...")
            table = soup.find("table", class_="standings-table2")
            if not table:
                table = soup.find("table", class_="short-standings")
            if not table:
                # Try finding any table with standings data
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
                            "w",
                            "l",
                            "pct",
                            "percentage",
                        ]
                    ):
                        table = t
                        print(f"   ✅ Found alternative standings table with headers: {header_text[:50]}...")
                        break
            
            if not table:
                print(f"   ❌ No standings table found for {series_name}")
                return []
            
            # Process team rows
            print(f"   📊 Processing team rows in {series_name} standings table...")
            rows = table.find_all("tr")
            team_count = 0
            
            for row in rows[2:]:  # Skip 2 header rows (grouping + column headers)
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:
                    continue
                
                team_name = cells[0].get_text().strip()
                if not team_name or team_name.upper() == "TEAM":
                    continue
                
                # Skip BYE teams
                if "BYE" in team_name.upper():
                    print(f"   ⏸️  Skipping BYE team: {team_name}")
                    continue
                
                # Helper function to safely extract column data
                def safe_col_int(index, default=0):
                    if index < len(cells):
                        text = cells[index].get_text().strip()
                        try:
                            return int(float(text))
                        except (ValueError, TypeError):
                            return default
                    return default

                def safe_col_text(index, default=""):
                    if index < len(cells):
                        return cells[index].get_text().strip()
                    return default

                # Extract points
                points = safe_col_int(1)
                
                # Format series name to match players.json format
                series_name_formatted = format_cnswpl_series_name(series_name)
                
                # Format team name to match players.json format
                team_name_formatted = format_cnswpl_team_name_for_output(team_name, series_name_formatted)
                
                team_stats = {
                    "series": series_name_formatted,
                    "team": team_name_formatted,
                    "league_id": "CNSWPL",
                    "points": points,
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
                print(f"   ✅ Processed team {team_count}: {team_name_formatted} (Points: {points}, W/L: {safe_col_int(2)}/{safe_col_int(3)})")
            
            print(f"   🎉 Stealth Browser: Successfully scraped stats for {team_count} teams in {series_name}")
            return stats
            
        except Exception as e:
            print(f"   ❌ Stealth browser attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"   🚨 All stealth browser attempts failed for {series_name}")
                return []

    return stats


def scrape_cnswpl_with_requests_fallback(url, series_name, max_retries=3):
    """
    CNSWPL fallback scraper using direct HTTP requests with retry logic.
    Uses same pattern as APTA simple scraper for reliability.

    Args:
        url (str): URL to scrape
        series_name (str): Name of the series
        max_retries (int): Maximum retry attempts

    Returns:
        list: List of team statistics dictionaries
    """
    stats = []
    print(f"   🌐 Starting direct HTTP scraping for {series_name}")

    # Use direct HTTP requests with retry logic (same as APTA simple scraper)
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    for attempt in range(max_retries):
        try:
            print(
                f"   📡 HTTP API: Fetching {url} (attempt {attempt + 1}/{max_retries})"
            )

            # Use direct HTTP requests with retry logic
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = session.get(url, headers=headers, timeout=30)
            print(f"   ✅ Direct HTTP request successful for {series_name}")
            
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

                # Fetch the statistics page using direct HTTP
                print(f"   📡 Fetching statistics page for {series_name}...")
                stats_response = session.get(stats_url, headers=headers, timeout=30)
                print(f"   ✅ Direct HTTP request successful for statistics page")
                
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
                                try:
                                    # Handle float values like "12.0" by converting to int
                                    return int(float(text)) if text.replace('.', '').isdigit() else default
                                except (ValueError, TypeError):
                                    return default
                            return default

                        def safe_col_text(index, default=""):
                            if index < len(cols):
                                return cols[index].text.strip()
                            return default

                        # Extract points from column 1 (index 1) - this is where points are in CNSWPL tables
                        points_value = safe_col_int(1)

                        team_stats = {
                            "series": series_name,
                            "team": format_cnswpl_team_name_for_output(team_name, series_name),
                            "league_id": "CNSWPL",
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


def check_cnswpl_stats_delta():
    """
    Check if CNSWPL stats need to be updated based on updated_at date in series_stats table.
    
    PERMANENTLY DISABLED - Always returns True to force fresh scraping.
    This ensures we always get the most current data from the website.
        
    Returns:
        bool: True if stats need to be updated, False otherwise
    """
    print("🚫 Delta check PERMANENTLY DISABLED - will always scrape fresh data")
    return True  # Always scrape fresh data

def scrape_cnswpl_all_stats(max_retries=3, retry_delay=5):
    """
    Main function to scrape and save CNSWPL statistics data from all discovered series.
    Handles both Chrome WebDriver and HTTP fallback approaches for Railway compatibility.
    Always scrapes fresh data (delta checking permanently disabled).

    Args:
        max_retries (int): Maximum retry attempts
        retry_delay (int): Delay between retries
    """
    print("[Scraper] Starting scrape: scrape_stats")
    
    # Check if stats need to be updated
    print("🔍 Checking if stats need to be updated...")
    needs_update = check_cnswpl_stats_delta()
    
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
        # Load CNSWPL configuration
        config = get_cnswpl_config()
        league_id = config["league_id"]
        base_url = config["base_url"]

        print(
            f"🌟 Processing ALL discovered series from {config['subdomain']} dynamically"
        )
        print(
            "No filtering - comprehensive discovery and processing of all team statistics"
        )

        # Use stealth browser for both discovery and stats scraping
        print("🛡️ Using Enhanced Stealth Browser for discovery and stats scraping...")
        
        print("✅ Proceeding with stealth browser (proxy testing disabled)")
        use_fallback = False  # Use stealth browser as primary method
        driver = None
        chrome_manager = None

        # Create CNSWPL data directory
        data_dir = get_cnswpl_data_dir()

        print(f"🚀 Starting {config['subdomain'].upper()} Stats Scraper")
        print(f"📊 Target: All Discovered Series")
        print(f"🎯 Method: {'ScraperAPI HTTP API' if use_fallback else 'Enhanced Stealth Browser'}")
        print("=" * 60)

        # CNSWPL Stats Scraper: Force direct HTTP requests to avoid CAPTCHA loops
        print("🌐 CNSWPL Stats Scraper: Using direct HTTP requests (stealth browser disabled due to CAPTCHA issues)")
        use_fallback = True  # Force direct HTTP requests
        chrome_manager = None
        driver = None
        print("✅ Direct HTTP mode enabled - bypassing stealth browser to avoid CAPTCHA loops")

        # Discovery phase
        discovery_start_time = datetime.now()
        print(f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}")
        print(f"📄 Navigating to URL: {base_url}")

        # CNSWPL Stats Scraper: Use hardcoded series URLs that work (same as player scraper)
        print("   🎯 Using hardcoded CNSWPL series URLs (same as player scraper)")
        
        # Use the same hardcoded URLs that the CNSWPL player scraper uses successfully
        # CRITICAL: Include Series SN which has actual stats data (season has started)
        series_urls = [
            # Series SN - HAS ACTUAL STATS DATA (season started)
            ("Series SN", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WlNlN3lMcz0%3D"),
            # Numeric series (1-17) - these have zero stats (season hasn't started)
            ("Series 1", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3MD0%3D"),
            ("Series 2", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3bz0%3D"),
            ("Series 3", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3az0%3D"),
            ("Series 4", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3cz0%3D"),
            ("Series 5", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3WT0%3D"),
            ("Series 6", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3Zz0%3D"),
            ("Series 7", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMaz0%3D"),
            ("Series 8", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMWT0%3D"),
            ("Series 9", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMYz0%3D"),
            ("Series 10", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3ND0%3D"),
            ("Series 11", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3OD0%3D"),
            ("Series 12", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
            ("Series 13", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 14", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3bz0%3D"),
            ("Series 15", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3cz0%3D"),
            # FIXED: Series 16 and 17 were using duplicate URLs (same as Series 12 and 13)
            # This caused Series 16 to show Series 12 data and Series 17 to show Series 13 data
            ("Series 16", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3ez0%3D"),
            ("Series 17", f"{base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3ND0%3D"),
        ]
        
        print(f"🏆 Using {len(series_urls)} hardcoded CNSWPL series URLs")
        
        # Skip the discovery phase and go directly to scraping
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

            # Track request and add intelligent pacing before series processing
            print(f"   ⏳ Adding adaptive delay before processing {series_number}...")
            pace_sleep()  # Adaptive pacing instead of fixed delay

            print(f"🏆 Processing: {series_number}")
            print(f"   📄 Series URL: {series_url}")
            print(f"   🔄 Scraping method: {'Direct HTTP API' if use_fallback else 'Enhanced Stealth Browser'}")

            # Choose scraping method based on availability
            if use_fallback:
                print(f"   🌐 Using Direct HTTP API for {series_number}...")
                stats = scrape_cnswpl_with_requests_fallback(
                    series_url, series_number, max_retries=max_retries
                )
            else:
                print(f"   🛡️ Using Enhanced Stealth Browser for {series_number}...")
                stats = scrape_cnswpl_with_stealth_browser(
                    chrome_manager,
                    series_url,
                    series_number,
                    max_retries=max_retries,
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

            # Mark successful completion and add minimal delay
            _pacer_mark_ok()  # Mark successful series processing
            time.sleep(0.5)  # Minimal delay between series

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
            f"🎯 Scraping Method: {'Direct HTTP API' if use_fallback else 'Enhanced Stealth Browser'}"
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
            league_subdomain="cnswpl",
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
            league_subdomain="cnswpl",
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
    print("🎾 CNSWPL Team Stats Scraper")
    print("=" * 60)
    print("🔍 Scraping team statistics from CNSWPL TennisScores website")
    print("📊 Chicago North Suburban Women's Paddle League")
    print()

    target_url = "https://cnswpl.tenniscores.com"
    print(f"🌐 Target URL: {target_url}")
    print()

    print("📊 Comprehensive team statistics scraping mode")
    print(
        "   Will collect detailed standings and performance data from all discovered series"
    )
    print()

    scrape_cnswpl_all_stats(retry_delay=1)
    print(f"\n✅ Team statistics scraping complete for CNSWPL!")
