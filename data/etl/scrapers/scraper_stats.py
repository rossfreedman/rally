#!/usr/bin/env python3

"""
Rally Flask Application - Tennis Stats Scraper

This script scrapes team statistics from TennisScores.com websites for various tennis leagues.
Optimized for Railway deployment with proper Chrome configuration for containerized environments.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Import stealth browser manager for fingerprint evasion
from stealth_browser import StealthBrowserManager
from webdriver_manager.chrome import ChromeDriverManager

print("Starting tennis stats scraper...")

# ChromeManager has been replaced with StealthBrowserManager for fingerprint evasion
# See stealth_browser.py for the new implementation

import os

# Import centralized league utilities
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from utils.league_utils import standardize_league_id


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


def build_league_data_dir(league_id):
    """
    Build the dynamic data directory path based on the league ID.

    Args:
        league_id (str): The league identifier

    Returns:
        str: The data directory path (e.g., 'data/leagues/APTACHICAGO')
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))  # data/etl/scrapers/
    etl_dir = os.path.dirname(script_dir)  # data/etl/
    project_root = os.path.dirname(
        os.path.dirname(etl_dir)
    )  # rally/ (up one more level)

    league_data_dir = os.path.join(project_root, "data", "leagues", league_id)
    os.makedirs(league_data_dir, exist_ok=True)

    return league_data_dir


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

    for attempt in range(max_retries):
        try:
            print(f"Navigating to URL: {url} (attempt {attempt + 1}/{max_retries})")
            driver.get(url)
            time.sleep(2)  # Wait for page to load

            # Look for and click the "Statistics" link
            print("Looking for Statistics link...")
            try:
                stats_link = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.LINK_TEXT, "Statistics"))
                )
                print("Found Statistics link, clicking...")
                stats_link.click()
                time.sleep(2)  # Wait for navigation
            except TimeoutException:
                print("Could not find Statistics link")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print("Max retries reached, could not find Statistics link")
                    return []

            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Find the standings table - try multiple class names for flexibility
            table = soup.find("table", class_="standings-table2")
            if not table:
                # Try alternative table class names
                table = soup.find("table", class_="short-standings")
            if not table:
                # Try finding any table that might contain standings
                tables = soup.find_all("table")
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
                        print(f"   Found alternative standings table")
                        break

            if not table:
                print("Could not find standings table with any known format")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print("Max retries reached, could not find standings table")
                    return []

            # Process each team row
            for row in table.find_all("tr")[2:]:  # Skip header rows
                cols = row.find_all("td")
                # Be flexible with column count - different leagues have different table structures
                # Minimum 10 columns needed for basic team stats
                if len(cols) >= 10:  # More flexible column requirement
                    team_name = cols[0].text.strip()

                    # Skip BYE teams - they are placeholders with no actual players
                    if "BYE" in team_name.upper():
                        print(f"   Skipping BYE team: {team_name}")
                        continue

                    # Defensive programming: handle potential parsing errors and variable column counts
                    try:
                        # Helper function to safely extract column data
                        def safe_col_int(index, default=0):
                            if index < len(cols):
                                text = cols[index].text.strip()
                                return int(text) if text.isdigit() else default
                            return default

                        def safe_col_text(index, default=""):
                            if index < len(cols):
                                return cols[index].text.strip()
                            return default

                        team_stats = {
                            "series": series_name,
                            "team": team_name,
                            "league_id": league_id,
                            "points": safe_col_int(1),
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
                    except (ValueError, IndexError) as e:
                        print(
                            f"   ⚠️  Error parsing team stats for {team_name}: {str(e)}"
                        )
                        continue

            print(f"Successfully scraped stats for {len(stats)} teams in {series_name}")
            break  # Success, exit retry loop

        except Exception as e:
            print(
                f"Error scraping stats (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached, could not scrape stats")
                return []

    return stats


def scrape_with_requests_fallback(url, series_name, league_id, max_retries=3):
    """
    Fallback scraper using HTTP requests instead of Selenium.
    Less reliable but works when Chrome WebDriver fails.

    Args:
        url (str): URL to scrape
        series_name (str): Name of the series
        league_id (str): League identifier
        max_retries (int): Maximum retry attempts

    Returns:
        list: List of team statistics dictionaries
    """
    stats = []

    for attempt in range(max_retries):
        try:
            print(
                f"   📡 HTTP Fallback: Fetching {url} (attempt {attempt + 1}/{max_retries})"
            )

            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for Statistics link first
            stats_links = soup.find_all("a", string="Statistics")
            if stats_links:
                stats_url = stats_links[0].get("href", "")
                if stats_url and not stats_url.startswith("http"):
                    base_url = "/".join(url.split("/")[:3])
                    stats_url = f"{base_url}/{stats_url}"

                print(f"   📊 Found Statistics link: {stats_url}")

                # Fetch the statistics page
                stats_response = requests.get(stats_url, headers=headers, timeout=30)
                stats_response.raise_for_status()
                soup = BeautifulSoup(stats_response.content, "html.parser")

            # Find standings table (same logic as Selenium version)
            table = soup.find("table", class_="standings-table2")
            if not table:
                table = soup.find("table", class_="short-standings")
            if not table:
                tables = soup.find_all("table")
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
                        break

            if not table:
                print(f"   ⚠️  No standings table found in {series_name}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    return []

            # Process team rows (same logic as Selenium version)
            for row in table.find_all("tr")[2:]:
                cols = row.find_all("td")
                if len(cols) >= 10:
                    team_name = cols[0].text.strip()

                    if "BYE" in team_name.upper():
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

                        team_stats = {
                            "series": series_name,
                            "team": team_name,
                            "league_id": league_id,
                            "points": safe_col_int(1),
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
                    except (ValueError, IndexError) as e:
                        print(
                            f"      ⚠️  Error parsing team stats for {team_name}: {str(e)}"
                        )
                        continue

            print(
                f"   ✅ HTTP Fallback: Found stats for {len(stats)} teams in {series_name}"
            )
            break

        except Exception as e:
            print(
                f"   ❌ HTTP Fallback error (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                print(f"   💥 HTTP Fallback failed completely for {series_name}")
                return []

    return stats


def scrape_all_stats(league_subdomain, max_retries=3, retry_delay=5):
    """
    Main function to scrape and save statistics data from all discovered series.
    Handles both Chrome WebDriver and HTTP fallback approaches for Railway compatibility.

    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
        max_retries (int): Maximum retry attempts
        retry_delay (int): Delay between retries
    """
    # Record start time
    start_time = datetime.now()
    print(f"🕐 Session Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

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

        # Try Chrome WebDriver first, fall back to HTTP requests if it fails
        try:
            print("🚀 Attempting stealth Chrome WebDriver approach...")
            chrome_manager = StealthBrowserManager(headless=True)
            driver = chrome_manager.__enter__()
            print("✅ Stealth Chrome WebDriver created successfully!")
            use_fallback = False
        except Exception as chrome_error:
            print(f"❌ Stealth Chrome WebDriver failed: {chrome_error}")
            print("🔄 Switching to HTTP requests fallback method...")
            use_fallback = True
            driver = None
            chrome_manager = None

        # Create dynamic data directory based on league
        data_dir = build_league_data_dir(league_id)

        print(f"🚀 Starting {config['subdomain'].upper()} Stats Scraper")
        print(f"📊 Target: All Discovered Series")
        print(f"🎯 Method: {'HTTP Fallback' if use_fallback else 'Chrome WebDriver'}")
        print("=" * 60)

        # Discovery phase
        discovery_start_time = datetime.now()
        print(f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}")
        print(f"📄 Navigating to URL: {base_url}")

        if use_fallback:
            # HTTP-based series discovery
            print("   📡 Using HTTP requests for series discovery...")
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(base_url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
        else:
            # WebDriver-based series discovery
            print("   🚗 Using Chrome WebDriver for series discovery...")
            driver.get(base_url)
            time.sleep(retry_delay)
            soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all div_list_option elements
        series_elements = soup.find_all("div", class_="div_list_option")
        print(f"🏆 Found {len(series_elements)} series on main page")

        # Extract series URLs
        for element in series_elements:
            try:
                series_link = element.find("a")
                if series_link and series_link.text:
                    series_number = series_link.text.strip()

                    # Format the series number to auto-detect APTA vs NSTF vs CITA formats
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
                        # CITA format: descriptive names like "4.0 Singles Sun", "3.5 & Under Sat"
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

            print(f"🏆 Processing: {series_number}")
            print(f"   📄 Series URL: {series_url}")

            # Choose scraping method based on availability
            if use_fallback:
                stats = scrape_with_requests_fallback(
                    series_url, series_number, league_id, max_retries=max_retries
                )
            else:
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

            time.sleep(retry_delay)  # Add delay between series

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
            f"🎯 Scraping Method: {'HTTP Fallback' if use_fallback else 'Stealth Chrome WebDriver'}"
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

    finally:
        # Clean up Chrome WebDriver if it was created
        if chrome_manager is not None:
            try:
                chrome_manager.__exit__(None, None, None)
                print("🧹 Chrome WebDriver cleaned up successfully")
            except Exception as cleanup_error:
                print(f"⚠️  Chrome WebDriver cleanup error: {cleanup_error}")


if __name__ == "__main__":
    print("🎾 TennisScores Team Stats Scraper - Dynamic Discovery Mode")
    print("=" * 60)
    print(
        "🔍 Dynamically discovering ALL team statistics from any TennisScores website"
    )
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

    print("📊 Comprehensive team statistics scraping mode")
    print(
        "   Will collect detailed standings and performance data from all discovered series"
    )
    print()

    scrape_all_stats(league_subdomain)
    print(f"\n✅ Team statistics scraping complete for {league_subdomain.upper()}!")
