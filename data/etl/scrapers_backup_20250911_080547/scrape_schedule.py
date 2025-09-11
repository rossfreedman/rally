import json
import os
import re
import time
import random
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# Import enhanced scraping utilities
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from stealth_browser import EnhancedStealthBrowser, create_stealth_browser
try:
    from data.etl.scrapers.proxy_manager import make_proxy_request
except ImportError:
    from proxy_manager import make_proxy_request

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
📅 Tennis Schedule Scraper - HTTP API Approach

📊 REQUEST VOLUME ANALYSIS:
- Estimated requests per run: ~100-500 (varies by league size)
- Cron frequency: daily
- Estimated daily volume: 100-500 requests
- Status: ✅ Within safe limits

🌐 IP ROTATION: Enabled via Decodo residential proxies
⏳ THROTTLING: 2.0-6.0 second delays between requests
"""


def normalize_league_id(league_subdomain):
    """
    Normalize league subdomain input to prevent duplicate directories.
    
    Args:
        league_subdomain (str): Raw user input (e.g., 'aptachicago', 'apta_chicago')
    
    Returns:
        str: Standardized league ID (e.g., 'APTA_CHICAGO')
    """
    # Convert to lowercase and handle common variations
    normalized = league_subdomain.lower().strip()
    
    # Define mapping for known league variations
    league_mappings = {
        'aptachicago': 'APTA_CHICAGO',
        'apta_chicago': 'APTA_CHICAGO', 
        'apta-chicago': 'APTA_CHICAGO',
        'chicago': 'APTA_CHICAGO',
        'nstf': 'NSTF',
        'cnswpl': 'CNSWPL',
        'cnswp': 'CNSWPL',
    }
    
    return league_mappings.get(normalized, normalized.upper())


# Dynamic League Configuration - User Input Based
def get_league_config(league_subdomain=None):
    """Get dynamic league configuration based on user input"""
    if not league_subdomain:
        raise ValueError("League subdomain must be provided")

    base_url = build_base_url(league_subdomain)
    
    # Normalize the league ID to prevent duplicate directories
    normalized_league_id = normalize_league_id(league_subdomain)

    return {
        "league_id": normalized_league_id,
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


def send_schedule_notification(league_subdomain, success_stats, total_series, failed_series=None, error_details=None):
    """
    Send SMS notification about schedule scraper results
    
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
            message = f"📅 Schedule Scraper: {league_subdomain.upper()} ✅\n"
            message += f"Success Rate: {success_rate:.1f}%\n"
            message += f"Series: {successful_series}/{total_series}\n"
            message += f"Matches: {success_stats.get('total_matches', 0)}\n"
            message += f"Duration: {success_stats.get('duration', 'N/A')}"
        elif success_rate >= 80:
            # Good success with warnings
            message = f"⚠️ Schedule Scraper: {league_subdomain.upper()} ⚠️\n"
            message += f"Success Rate: {success_rate:.1f}%\n"
            message += f"Series: {successful_series}/{total_series}\n"
            message += f"Failed: {failed_count}\n"
            if failed_series:
                message += f"Failed Series: {', '.join(failed_series[:3])}"
                if len(failed_series) > 3:
                    message += f" (+{len(failed_series)-3} more)"
            message += f"\nMatches: {success_stats.get('total_matches', 0)}\n"
            message += f"Duration: {success_stats.get('duration', 'N/A')}"
        else:
            # Poor success rate
            message = f"🚨 Schedule Scraper: {league_subdomain.upper()} ❌\n"
            message += f"Success Rate: {success_rate:.1f}%\n"
            message += f"Series: {successful_series}/{total_series}\n"
            message += f"Failed: {failed_count}\n"
            if failed_series:
                message += f"Failed Series: {', '.join(failed_series[:3])}"
                if len(failed_series) > 3:
                    message += f" (+{len(failed_series)-3} more)"
            if error_details:
                message += f"\nError: {error_details[:100]}..."
            message += f"\nMatches: {success_stats.get('total_matches', 0)}\n"
            message += f"Duration: {success_stats.get('duration', 'N/A')}"
        
        # Send SMS notification
        result = send_sms_notification(ADMIN_PHONE, message, test_mode=False)
        
        if result.get("success"):
            print(f"📱 SMS notification sent: {message[:50]}...")
        else:
            print(f"❌ Failed to send SMS: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error sending notification: {e}")


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


# Removed file-based configuration functions - now using user input
# Removed active_series functionality - now processes all discovered series


def scrape_tennis_schedule(league_subdomain):
    """
    Main function to scrape tennis schedules using dynamic discovery.

    Args:
        league_subdomain (str): League subdomain (e.g., 'aptachicago', 'nstf')
    """
    print("[Scraper] Starting scrape: scraper_schedule")
    
    # Record start time
    start_time = datetime.now()
    print(f"🕐 Session Start: {start_time.strftime('%m-%d-%y @ %I:%M:%S %p')}")
    print(f"📊 Estimated requests for this session: 300")

    # Track timing milestones
    discovery_start_time = None
    scraping_start_time = None

    try:
        # Load league configuration from user input
        config = get_league_config(league_subdomain)
        league_id = config["league_id"]
        base_url = config["base_url"]

        print(
            f"🌟 Processing ALL discovered series from {config['subdomain']} dynamically"
        )
        print("No filtering - comprehensive discovery and processing of all schedules")

        # Create dynamic data directory based on league
        data_dir = build_league_data_dir(league_id)

        print(f"🚀 Starting {config['subdomain'].upper()} Schedule Scraper")
        print(f"📊 Target: All Discovered Series")
        print("=" * 60)

        # Discovery phase
        discovery_start_time = datetime.now()
        print(f"🔍 Discovery Phase Start: {discovery_start_time.strftime('%H:%M:%S')}")
        print(f"📄 Accessing main page: {base_url}")

        # Use proxy for the main page request
        print("🌐 Using proxy for US-based access...")
        
        # Use the new proxy request function
        try:
            from data.etl.scrapers.proxy_manager import make_proxy_request
        except ImportError:
            from proxy_manager import make_proxy_request
        
        print(f"   📡 Fetching main page: {base_url}")
        try:
            response = make_proxy_request(base_url, timeout=60)
            if not response:
                print("   ❌ Proxy request failed")
                return
        except Exception as e:
            print(f"   ❌ Proxy request failed: {e}")
            return
        
        response_text = response.text
        print(f"   ✅ Main page loaded successfully via HTTP API")
        print(f"   📄 Response status: {response.status_code}")
        print(f"   📄 Content length: {len(response_text)} characters")

        # Parse the HTML content
        soup = BeautifulSoup(response_text, "html.parser")

        # Debug: Print page title and some content
        print(f"📄 Page Title: {soup.find('title').get_text() if soup.find('title') else 'No title found'}")
        print(f"📄 Page Length: {len(response_text)} characters")
        
        # Debug: Show the actual page content (first 1000 chars)
        print(f"📄 Page Content Preview:")
        print(response_text[:1000])
        print("..." if len(response_text) > 1000 else "")
        
        # Debug: Check for error messages or blocking
        if "interstitial" in response_text.lower() or "error" in response_text.lower():
            print("🚨 DETECTED: Site is showing interstitial/error page!")
            print("🔍 Looking for error messages...")
            
            # Find error messages
            error_elements = soup.find_all(text=lambda text: text and any(word in text.lower() for word in ['error', 'blocked', 'access denied', 'unavailable']))
            if error_elements:
                print("🚨 Error messages found:")
                for error in error_elements[:5]:
                    print(f"   - {error.strip()}")
        
        # Find all series elements
        series_elements = soup.find_all("div", class_="div_list_option")
        print(f"🏆 Found {len(series_elements)} total series on main page")
        
        # Debug: Show what elements we're finding
        all_divs = soup.find_all("div")
        print(f"🔍 Total div elements found: {len(all_divs)}")
        
        # Show first few div classes for debugging
        div_classes = [div.get('class', ['no-class']) for div in all_divs[:10]]
        print(f"🔍 First 10 div classes: {div_classes}")
        
        # Debug: Look for any links or navigation
        all_links = soup.find_all("a")
        print(f"🔗 Total links found: {len(all_links)}")
        if all_links:
            print("🔗 First 5 links:")
            for link in all_links[:5]:
                href = link.get('href', 'no-href')
                text = link.get_text().strip()[:50]
                print(f"   - {text} -> {href}")

        discovery_end_time = datetime.now()
        discovery_duration = discovery_end_time - discovery_start_time
        print(
            f"✅ Discovery Phase Complete: {discovery_duration.total_seconds():.1f} seconds"
        )

        # Scraping phase
        scraping_start_time = datetime.now()
        print(f"\n⚡ Scraping Phase Start: {scraping_start_time.strftime('%H:%M:%S')}")

        all_schedule_data = []
        processed_series_count = 0
        skipped_series_count = 0

        # Process each series
        for series_idx, element in enumerate(series_elements, 1):
            series_start_time = datetime.now()
            progress_percent = (series_idx / len(series_elements)) * 100
            elapsed = series_start_time - start_time
            print(
                f"\n=== Series {series_idx}/{len(series_elements)} ({progress_percent:.1f}%) | Elapsed: {elapsed} ==="
            )

            try:
                series_link = element.find("a")
                if series_link and series_link.text:
                    series_number = series_link.text.strip()

                    # Format the series number to auto-detect APTA vs NSTF format
                    if series_number.isdigit():
                        formatted_series = f"Chicago {series_number}"
                    elif series_number.startswith("Series "):
                        # Series name already has "Series" prefix, use as-is
                        formatted_series = series_number
                    elif "SW" in series_number:
                        # Handle SW series: "23 SW" -> "Chicago 23 SW"
                        formatted_series = f"Chicago {series_number}"
                    else:
                        # Handle non-numeric series (like "2B", "3A", etc.)
                        formatted_series = f"Series {series_number}"

                    # Add delay before series processing
                    print(f"   ⏳ Adding delay before processing {formatted_series}...")
                    time.sleep(2)

                    series_url = series_link.get("href", "")
                    full_url = f"{base_url}/{series_url}" if series_url else ""

                    if not full_url:
                        print(
                            f"⚠️  Skipping series {formatted_series} - No valid URL found"
                        )
                        skipped_series_count += 1
                        continue

                    print(f"🏆 Processing: {formatted_series}")
                    print(f"   📄 Series URL: {full_url}")

                    # Get the series page with HTTP API
                    print(f"   📡 Fetching series page: {full_url}")
                    
                    # Add retry logic for timeout resilience
                    max_retries = 3
                    retry_delay = 5  # seconds
                    
                    for attempt in range(max_retries):
                        try:
                            print(f"   📡 HTTP API: Fetching {full_url} (attempt {attempt + 1}/{max_retries})")
                            series_response = make_proxy_request(full_url, timeout=30)
                            series_response_text = series_response.text
                            print(f"   ✅ Proxy request successful for {formatted_series}")
                            break  # Success, exit retry loop
                            
                        except requests.exceptions.Timeout:
                            if attempt < max_retries - 1:
                                print(f"   ⏰ Timeout on attempt {attempt + 1}/{max_retries}, retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                print(f"   ❌ Failed after {max_retries} attempts due to timeout")
                                raise
                                
                        except requests.exceptions.RequestException as e:
                            if attempt < max_retries - 1:
                                print(f"   ⚠️ Request failed on attempt {attempt + 1}/{max_retries}: {e}")
                                print(f"   🔄 Retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                print(f"   ❌ Failed after {max_retries} attempts: {e}")
                                raise
                    
                    series_soup = BeautifulSoup(series_response_text, "html.parser")

                    # Find the Schedule link
                    print("   📅 Looking for schedule link...")
                    schedule_link = series_soup.find("a", text="Schedule")
                    if not schedule_link:
                        print(
                            f"   ⚠️  No schedule link found for series {formatted_series}"
                        )
                        skipped_series_count += 1
                        continue

                    schedule_url = f"{base_url}/{schedule_link['href']}"
                    print(f"   📅 Schedule URL: {schedule_url}")

                    # Get the schedule page with HTTP API
                    print("   📊 Accessing schedule page...")
                    print(f"   [Scraper] Visiting: {schedule_url}")
                    
                    # Add retry logic for timeout resilience
                    max_retries = 3
                    retry_delay = 5  # seconds
                    
                    for attempt in range(max_retries):
                        try:
                            schedule_response = make_proxy_request(schedule_url, timeout=30)
                            schedule_response_text = schedule_response.text
                            break  # Success, exit retry loop
                            
                        except requests.exceptions.Timeout:
                            if attempt < max_retries - 1:
                                print(f"   ⏰ Timeout on attempt {attempt + 1}/{max_retries}, retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                print(f"   ❌ Failed after {max_retries} attempts due to timeout")
                                raise
                                
                        except requests.exceptions.RequestException as e:
                            if attempt < max_retries - 1:
                                print(f"   ⚠️ Request failed on attempt {attempt + 1}/{max_retries}: {e}")
                                print(f"   🔄 Retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                print(f"   ❌ Failed after {max_retries} attempts: {e}")
                                raise
                    
                    schedule_soup = BeautifulSoup(schedule_response_text, "html.parser")
                    
                    # Add throttling after schedule page load
                    time.sleep(random.uniform(2.0, 4.0))

                    # Find all schedule entries
                    schedule_entries = schedule_soup.find_all("div", class_="row_cont")
                    print(
                        f"   📋 Found {len(schedule_entries)} potential schedule entries"
                    )

                    entries_added = 0
                    # Process each schedule entry
                    for entry in schedule_entries:
                        # Get all the fields for this entry
                        date = entry.find("div", class_="week_date")
                        match_time = entry.find("div", class_="week_time")
                        home = entry.find("div", class_="week_home")
                        away = entry.find("div", class_="week_away")
                        location = entry.find("div", class_="week_loc")

                        # Some sites use different class names for location field
                        if not location:
                            location = entry.find("div", class_="week_print")
                        if not location:
                            location = entry.find("div", class_="week_location")

                        if all([date, match_time, home, away]):  # Only require core fields
                            # Fix team name formatting - don't add series number if already present
                            raw_home = home.text.strip()
                            raw_away = away.text.strip()

                            # Skip schedule entries involving BYE teams - they are placeholders with no actual players
                            if "BYE" in raw_home.upper() or "BYE" in raw_away.upper():
                                print(
                                    f"       Skipping BYE schedule entry: {raw_home} vs {raw_away}"
                                )
                                continue

                            # Check if team name already ends with the series number
                            if raw_home.endswith(f" - {series_number}"):
                                formatted_home = raw_home
                            else:
                                formatted_home = f"{raw_home} - {series_number}"

                            if raw_away.endswith(f" - {series_number}"):
                                formatted_away = raw_away
                            else:
                                formatted_away = f"{raw_away} - {series_number}"

                            # Extract location text, handling different formats
                            location_text = ""
                            if location:
                                location_text = location.text.strip()
                                # If location contains "Details" or similar, it's not a real location
                                if location_text.lower() in ["details", "print", ""]:
                                    location_text = "TBD"
                            else:
                                location_text = "TBD"

                            schedule_item = {
                                "date": date.text.strip(),
                                "time": match_time.text.strip(),
                                "home_team": formatted_home,
                                "away_team": formatted_away,
                                "location": location_text,
                                "series": formatted_series,
                                "League": league_id,
                            }
                            all_schedule_data.append(schedule_item)
                            entries_added += 1

                    series_end_time = datetime.now()
                    series_duration = series_end_time - series_start_time

                    print(
                        f"   ✅ Added {entries_added} schedule entries for {formatted_series}"
                    )
                    processed_series_count += 1

                    # Progress update with timing
                    remaining_series = len(series_elements) - series_idx
                    avg_time_per_series = (
                        (series_start_time - scraping_start_time).total_seconds()
                        / series_idx
                        if scraping_start_time and series_idx > 0
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
                        f"✅ Series completed in {series_duration.total_seconds():.1f}s | Progress: {series_idx}/{len(series_elements)} series"
                    )
                    if eta:
                        print(
                            f"   ⏰ ETA: {eta.strftime('%H:%M:%S')} (est. {estimated_remaining/60:.1f} min remaining)"
                        )

            except Exception as e:
                print(f"   ❌ Error processing series: {str(e)}")
                skipped_series_count += 1
                continue

        # Save schedule data
        output_filename = os.path.join(data_dir, "schedules.json")
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(all_schedule_data, f, indent=4, ensure_ascii=False)

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
        entries_per_minute = (
            (len(all_schedule_data) / total_seconds * 60) if total_seconds > 0 else 0
        )

        print(f"📊 PERFORMANCE METRICS")
        print(f"📈 Total series found: {len(series_elements)}")
        print(f"🏆 Series processed successfully: {processed_series_count}")
        print(f"⚠️  Series skipped/failed: {skipped_series_count}")
        print(f"📅 Total schedule entries: {len(all_schedule_data)}")
        print(f"📈 Series per minute: {series_per_minute:.1f}")
        print(f"📅 Entries per minute: {entries_per_minute:.1f}")
        print(
            f"⚡ Average time per series: {total_seconds/processed_series_count:.1f}s"
            if processed_series_count > 0
            else "⚡ Average time per series: N/A"
        )
        print()

        print(f"💾 Data saved to: {output_filename}")

        # Print summary by series
        print(f"\n📈 SERIES BREAKDOWN:")
        series_counts = {}
        for entry in all_schedule_data:
            series = entry["series"]
            series_counts[series] = series_counts.get(series, 0) + 1

        for series, count in sorted(series_counts.items()):
            percentage = (
                (count / len(all_schedule_data) * 100)
                if len(all_schedule_data) > 0
                else 0
            )
            print(f"  {series}: {count} entries ({percentage:.1f}%)")

        print("=" * 70)
        
        print("[Scraper] Finished scrape successfully")
        
        # Prepare success statistics for notification
        success_stats = {
            "processed_series_count": processed_series_count,
            "skipped_series_count": skipped_series_count,
            "total_matches": len(all_schedule_data),
            "duration": str(total_duration),
            "series_per_minute": series_per_minute,
            "entries_per_minute": entries_per_minute
        }
        
        # Track failed series for notification
        failed_series = []
        successful_series = []
        for series_name in series_elements:
            # Check if this series has schedule data
            series_data = [entry for entry in all_schedule_data if entry.get("series") == series_name]
            if not series_data:
                failed_series.append(series_name)
            else:
                successful_series.append(series_name)
        
        # Send notification with results
        send_schedule_notification(
            league_subdomain=league_subdomain,
            success_stats=success_stats,
            total_series=len(series_elements),
            failed_series=failed_series if failed_series else None
        )

    except requests.RequestException as e:
        print("[Scraper] Scrape failed with an exception")
        import traceback
        traceback.print_exc()
        error_time = datetime.now()
        elapsed_time = error_time - start_time
        print(f"\n❌ NETWORK ERROR OCCURRED!")
        print("=" * 50)
        print(f"🕐 Session Start: {start_time.strftime('%H:%M:%S')}")
        print(f"❌ Error Time:    {error_time.strftime('%H:%M:%S')}")
        print(f"⏱️  Elapsed Time:  {elapsed_time}")
        print(f"🚨 Error Details: {str(e)}")
        print("=" * 50)
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
    import sys
    
    print("🎾 TennisScores Schedule Scraper - Dynamic Discovery Mode")
    print("=" * 60)
    print("🔍 Dynamically discovering ALL schedules from any TennisScores website")
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

    print("📅 Comprehensive schedule scraping mode")
    print("   Will collect all schedule data from all discovered series")
    print()

    scrape_tennis_schedule(league_subdomain)
    print(f"\n✅ Schedule scraping complete for {league_subdomain.upper()}!")
