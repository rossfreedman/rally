"""
Optimized Player History Scraper with Concurrent Processing
Performance improvements:
- Concurrent team page processing with ThreadPoolExecutor
- Batch player stats retrieval with connection pooling
- Intelligent caching to avoid redundant requests
- Reduced sleep delays with smart retry logic
- Memory-efficient data structures
Enhanced with IP validation, request volume tracking, and intelligent throttling.
"""

import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
import warnings
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from threading import Lock

# Suppress deprecation warnings - CRITICAL for production stability
warnings.filterwarnings("ignore", category=UserWarning, module="_distutils_hack")
warnings.filterwarnings("ignore", category=UserWarning, module="setuptools")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.league_utils import standardize_league_id
from utils.player_id_utils import create_player_id, extract_tenniscores_player_id

# Import enhanced stealth browser with all features
from stealth_browser import EnhancedStealthBrowser, StealthConfig, create_stealth_browser
from proxy_manager import fetch_with_retry, make_proxy_request, get_random_headers

# Import notification service
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import requests
import os

# Admin phone number for notifications
ADMIN_PHONE = "17732138911"  # Ross's phone number

# Enhanced scraper tracking
class ScraperEnhancements:
    """Enhanced scraper functionality with request tracking and session management"""
    
    def __init__(self, scraper_name: str, estimated_requests: int, cron_frequency: str):
        self.scraper_name = scraper_name
        self.estimated_requests = estimated_requests
        self.cron_frequency = cron_frequency
        self.request_count = 0
        self.start_time = datetime.now()
        self.requests_tracked = []
        
    def track_request(self, request_type: str):
        """Track a request for monitoring"""
        self.request_count += 1
        self.requests_tracked.append({
            "type": request_type,
            "timestamp": datetime.now(),
            "count": self.request_count
        })
        
    def validate_ip_region(self, driver=None):
        """Validate IP region using proxy"""
        try:
            # Use proxy manager to check IP
            response = fetch_with_retry("https://ipapi.co/json/", timeout=10)
            if response and response.status_code == 200:
                data = response.json()
                country = data.get('country_name', 'Unknown')
                return {
                    'validation_successful': True,
                    'country': country,
                    'ip': data.get('ip', 'Unknown')
                }
        except Exception as e:
            print(f"⚠️ IP validation failed: {e}")
        
        return {'validation_successful': False}
        
    def log_session_summary(self):
        """Log session summary"""
        duration = datetime.now() - self.start_time
        print(f"\n📊 {self.scraper_name} Session Summary:")
        print(f"⏱️ Duration: {duration}")
        print(f"📈 Requests tracked: {self.request_count}")
        print(f"🎯 Estimated vs Actual: {self.estimated_requests} vs {self.request_count}")

def create_enhanced_scraper(scraper_name: str, estimated_requests: int, cron_frequency: str):
    """Create enhanced scraper tracker"""
    return ScraperEnhancements(scraper_name, estimated_requests, cron_frequency)

def add_throttling_to_loop():
    """Add intelligent throttling between requests"""
    import random
    # Reduced delays for optimized scraper
    delay = random.uniform(0.5, 1.5)  # Faster than original 1.5-3.0
    time.sleep(delay)

def make_decodo_request(url: str, timeout: int = 30):
    """Make request using proxy manager (Decodo equivalent)"""
    return fetch_with_retry(url, timeout=timeout)


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


class OptimizedStealthManager:
    """Optimized stealth browser manager with connection pooling and proxy support."""

    def __init__(self, pool_size=3, max_retries=3, use_stealth=True):
        """Initialize with a pool of stealth browsers for concurrent access."""
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.use_stealth = use_stealth
        self.browser_pool = []
        self.pool_lock = Lock()
        self.active_browsers = set()
        
        # Create stealth config optimized for performance
        self.stealth_config = StealthConfig(
            fast_mode=True,  # Enable fast mode for better performance
            verbose=False,   # Reduce logging for performance
            environment="production",  # Production environment settings
            force_browser=False  # Allow fallback to HTTP requests
        )

    def create_browser(self):
        """Create a stealth browser optimized for scraping."""
        if self.use_stealth:
            try:
                return create_stealth_browser(
                    fast_mode=True,  # Enable fast mode
                    verbose=False,   # Reduce logging
                    environment="production"  # Production optimizations
                )
            except Exception as e:
                print(f"⚠️ Failed to create stealth browser, falling back to regular: {e}")
                return self._create_fallback_driver()
        else:
            return self._create_fallback_driver()

    def _create_fallback_driver(self):
        """Create fallback regular Chrome driver."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-images")  # Don't load images
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1280x720")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        # Stealth-like arguments
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        # Execute stealth script
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def get_browser(self):
        """Get a browser from the pool or create a new one."""
        with self.pool_lock:
            if self.browser_pool:
                browser = self.browser_pool.pop()
                self.active_browsers.add(browser)
                return browser
            elif len(self.active_browsers) < self.pool_size:
                browser = self.create_browser()
                if browser:
                    self.active_browsers.add(browser)
                    return browser
                return None
            else:
                # Wait for a browser to become available
                return None

    def return_browser(self, browser):
        """Return a browser to the pool."""
        with self.pool_lock:
            if browser in self.active_browsers:
                self.active_browsers.remove(browser)
                # Check if browser is still healthy
                try:
                    if hasattr(browser, 'current_url'):
                        browser.current_url  # Test browser health
                        self.browser_pool.append(browser)
                    elif hasattr(browser, 'driver') and browser.driver:
                        browser.driver.current_url  # Test stealth browser health
                        self.browser_pool.append(browser)
                except:
                    # Browser is dead, clean it up
                    try:
                        if hasattr(browser, 'quit'):
                            browser.quit()
                        elif hasattr(browser, 'driver') and browser.driver:
                            browser.driver.quit()
                    except:
                        pass

    def get_html_with_proxy(self, url: str):
        """Get HTML using proxy-first approach for maximum stealth."""
        try:
            # Try proxy request first (fastest and most stealthy)
            response = fetch_with_retry(url, timeout=15)
            if response and response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"⚠️ Proxy request failed for {url}: {e}")
        
        # Fallback to browser
        browser = self.get_browser()
        if browser:
            try:
                if hasattr(browser, 'get_html'):
                    # Stealth browser
                    return browser.get_html(url)
                else:
                    # Regular driver
                    browser.get(url)
                    time.sleep(0.5)
                    return browser.page_source
            finally:
                self.return_browser(browser)
        
        return None

    def cleanup(self):
        """Clean up all browsers."""
        with self.pool_lock:
            for browser in list(self.browser_pool) + list(self.active_browsers):
                try:
                    if hasattr(browser, 'quit'):
                        browser.quit()
                    elif hasattr(browser, 'driver') and browser.driver:
                        browser.driver.quit()
                except:
                    pass
            self.browser_pool.clear()
            self.active_browsers.clear()


class PlayerDataCache:
    """Intelligent caching system to avoid redundant requests."""

    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or tempfile.mkdtemp()
        self.cache_file = os.path.join(self.cache_dir, "player_cache.json")
        self.cache = self.load_cache()
        self.cache_lock = Lock()

    def load_cache(self):
        """Load existing cache from disk."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r") as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_cache(self):
        """Save cache to disk."""
        with self.cache_lock:
            try:
                with open(self.cache_file, "w") as f:
                    json.dump(self.cache, f, indent=2)
            except:
                pass

    def get_cache_key(self, player_url, last_modified=None):
        """Generate a cache key for a player URL."""
        key_data = f"{player_url}_{last_modified}" if last_modified else player_url
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_cached_stats(self, player_url, max_age_days=1):
        """Get cached player stats if they're recent enough."""
        cache_key = self.get_cache_key(player_url)

        with self.cache_lock:
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                cache_time = datetime.fromisoformat(
                    cached_data.get("timestamp", "2000-01-01")
                )

                if datetime.now() - cache_time < timedelta(days=max_age_days):
                    return cached_data.get("stats")

        return None

    def cache_stats(self, player_url, stats):
        """Cache player stats with timestamp."""
        cache_key = self.get_cache_key(player_url)

        with self.cache_lock:
            self.cache[cache_key] = {
                "stats": stats,
                "timestamp": datetime.now().isoformat(),
            }


def build_league_data_dir(league_id):
    """Build the dynamic data directory path based on the league ID."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up three levels: scrapers -> etl -> data -> project_root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    league_data_dir = os.path.join(project_root, "data", "leagues", league_id)
    os.makedirs(league_data_dir, exist_ok=True)
    return league_data_dir


def convert_date_format(date_str):
    """Convert date from DD-MMM-YY format to MM/DD/YYYY format to match expected output."""
    if not date_str:
        return date_str
    
    try:
        # Handle various input formats
        if "/" in date_str and len(date_str) >= 8:
            # Already in MM/DD/YYYY format
            return date_str
        elif "-" in date_str:
            # Convert DD-MMM-YY to MM/DD/YYYY
            from datetime import datetime
            # Parse DD-MMM-YY format (e.g., "15-Jan-25")
            dt = datetime.strptime(date_str, "%d-%b-%y")
            # Convert to MM/DD/YYYY format (e.g., "01/15/2025")
            return dt.strftime("%m/%d/%Y")
        else:
            return date_str
    except:
        # If conversion fails, return original
        return date_str


def get_league_config(league_subdomain):
    """Get dynamic league configuration."""
    if not league_subdomain:
        raise ValueError("League subdomain must be provided")

    base_url = f"https://{league_subdomain}.tenniscores.com"

    return {
        "league_id": standardize_league_id(league_subdomain),
        "subdomain": league_subdomain,
        "base_url": base_url,
        "main_page": f"{base_url}/?mod=nndz-TjJiOWtOR2sxTnhI",
        "player_page_mod": "nndz-SkhmOW1PQ3V4Zz09",
        "team_page_mod": "nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D",
    }


def extract_series_name_from_team(team_name):
    """Extract series name from team name."""
    if not team_name:
        return None

    team_name = team_name.strip()

    # APTA Chicago format: "Club - Number"
    if " - " in team_name:
        parts = team_name.split(" - ")
        if len(parts) > 1:
            series_num = parts[1].strip()
            return f"Chicago {series_num}"

    # NSTF format: "Club SNumber" or "Club SNumberLetter"
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

    elif team_name.startswith("Series ") or team_name.startswith("Chicago "):
        return team_name

    return None


def extract_club_name_from_team(team_name):
    """Extract club name from team name."""
    if not team_name:
        return "Unknown"

    team_name = team_name.strip()

    # APTA format: "Club - Number"
    if " - " in team_name:
        return team_name.split(" - ")[0].strip()

    # NSTF format: Remove series identifiers
    if re.search(r"S\d+[A-Z]*", team_name):
        return re.sub(r"\s*S\d+[A-Z]*\s*", "", team_name).strip()

    # Remove Sunday identifiers
    team_name = re.sub(r"\s*Sunday\s*[AB]?\s*$", "", team_name).strip()

    return team_name if team_name else "Unknown"


def process_team_page_concurrent(team_info, config, stealth_manager):
    """Process a single team page to extract player mappings - optimized for concurrent execution."""
    team_name, team_id = team_info
    driver = None

    try:
        series_name = extract_series_name_from_team(team_name)
        club_name = extract_club_name_from_team(team_name)

        if not series_name or not club_name:
            return team_name, {}

        # Visit team page using proxy-first approach
        team_url = f"{config['base_url']}/?mod={config['team_page_mod']}&team={team_id}"
        
        # Try proxy request first (faster and more stealthy)
        html_content = stealth_manager.get_html_with_proxy(team_url)
        if not html_content:
            return team_name, {}

        team_soup = BeautifulSoup(html_content, "html.parser")
        player_mappings = {}

        # Extract player names from various elements
        # Method 1: Links
        for link in team_soup.find_all("a", href=True):
            href = link.get("href", "")
            if any(
                pattern in href
                for pattern in ["player.php", "uid=", "player=", "player_id="]
            ):
                player_name = link.get_text(strip=True)
                if player_name and len(player_name.split()) >= 2:
                    player_mappings[player_name] = {
                        "team_name": team_name,
                        "series": series_name,
                        "club": club_name,
                    }

        # Method 2: Table cells (backup)
        for table in team_soup.find_all("table"):
            for row in table.find_all("tr"):
                for cell in row.find_all(["td", "th"]):
                    cell_text = cell.get_text(strip=True)
                    if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+", cell_text):
                        player_mappings[cell_text] = {
                            "team_name": team_name,
                            "series": series_name,
                            "club": club_name,
                        }

        return team_name, player_mappings

    except Exception as e:
        print(f"   ❌ Error processing team {team_name}: {e}")
        return team_name, {}

    finally:
        # No cleanup needed for proxy requests
        pass


def get_player_stats_optimized(
    player_url, config, stealth_manager, cache, max_retries=2
):
    """Optimized player stats retrieval with caching and reduced retries."""
    # Check cache first
    if cache:
        cached_stats = cache.get_cached_stats(player_url)
        if cached_stats:
            return cached_stats

    for attempt in range(max_retries):
        try:
            base_url = config["base_url"]
            full_url = (
                f"{base_url}{player_url}"
                if not player_url.startswith("http")
                else player_url
            )

            # Use proxy-first approach for maximum stealth
            html_content = stealth_manager.get_html_with_proxy(full_url)
            if not html_content:
                time.sleep(0.5)
                continue

            wins = 0
            losses = 0
            match_details = []

            soup = BeautifulSoup(html_content, "html.parser")

            # Extract match info from rbox_top divs
            for rbox in soup.find_all("div", class_="rbox_top"):
                date_div = rbox.find("div", class_="rbox_inner")
                match_date = None
                if date_div:
                    date_text = date_div.get_text(strip=True)
                    match_date = date_text.split()[0] if date_text else None

                series_div = rbox.find_all("div", class_="rbox_inner")
                match_series = None
                if len(series_div) > 1:
                    match_series = series_div[1].get_text(strip=True)
                    if " - " in match_series:
                        match_series = match_series.split(" - ")[0]

                end_pti = None
                for pti_div in rbox.find_all("div", class_="rbox3top"):
                    if "End" in pti_div.get_text():
                        span = pti_div.find("span", class_="demi")
                        if span:
                            end_pti = span.get_text(strip=True)

                if match_date and end_pti and match_series:
                    # Convert date to MM/DD/YYYY format to match expected output
                    formatted_date = convert_date_format(match_date)
                    match_details.append(
                        {"date": formatted_date, "end_pti": end_pti, "series": match_series}
                    )

            # Count wins and losses from HTML content
            # Extract text content for win/loss counting
            if "W" in html_content or "L" in html_content:
                # Simple pattern matching for wins/losses
                import re
                w_matches = re.findall(r'\bW\b', html_content)
                l_matches = re.findall(r'\bL\b', html_content)
                wins = len(w_matches)
                losses = len(l_matches)

            stats = {
                "Wins": wins,
                "Losses": losses,
                "Win %": (
                    f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%"
                ),
                "match_details": match_details,
            }

            # Cache the results
            if cache:
                cache.cache_stats(player_url, stats)

            return stats

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)

        finally:
            # No cleanup needed for proxy requests
            pass

    # Return default stats if all retries failed
    return {"Wins": 0, "Losses": 0, "Win %": "0.0%", "match_details": []}


def discover_teams_optimized(browser, config):
    """Optimized team discovery with minimal page visits."""
    print(f"🔍 Starting optimized team discovery...")

    discovery_results = {"teams": {}, "series": set(), "clubs": set()}

    try:
        # Use proxy-first approach for discovery
        if hasattr(browser, 'get_html'):
            # Stealth browser
            html_content = browser.get_html(config["main_page"])
        else:
            # Regular browser fallback
            browser.get(config["main_page"])
            time.sleep(1)
            html_content = browser.page_source

        soup = BeautifulSoup(html_content, "html.parser")

        # Discover teams
        team_links = soup.find_all("a", href=re.compile(r"team="))

        for link in team_links:
            href = link.get("href", "")
            team_name = link.text.strip()

            team_match = re.search(r"team=([^&]+)", href)
            if team_match and team_name:
                team_id = team_match.group(1)
                discovery_results["teams"][team_name] = team_id

                series_name = extract_series_name_from_team(team_name)
                if series_name:
                    discovery_results["series"].add(series_name)

                club_name = extract_club_name_from_team(team_name)
                if club_name and club_name != "Unknown":
                    discovery_results["clubs"].add(club_name)

        print(f"✅ Discovered {len(discovery_results['teams'])} teams")
        print(f"✅ Discovered {len(discovery_results['series'])} series")
        print(f"✅ Discovered {len(discovery_results['clubs'])} clubs")

        return discovery_results

    except Exception as e:
        print(f"❌ Error during team discovery: {str(e)}")
        return discovery_results


def scrape_player_history_optimized(league_subdomain, max_workers=4, use_cache=True, test_mode=False, max_players=None):
    """
    Optimized main function with concurrent processing and intelligent caching.

    Args:
        league_subdomain (str): League subdomain
        max_workers (int): Number of concurrent workers for team processing
        use_cache (bool): Whether to use intelligent caching
        test_mode (bool): Enable test mode for limited scraping
        max_players (int): Maximum number of players to scrape (for testing)
    """
    start_time = datetime.now()
    mode_text = f" (TEST MODE - {max_players} players)" if test_mode else ""
    print(
        f"🚀 OPTIMIZED Player History Scraper Started{mode_text}: {start_time.strftime('%m-%d-%y @ %I:%M:%S %p')}"
    )
    
    # Initialize enhanced scraper with request volume tracking
    estimated_requests = 300  # Conservative estimate for optimized scraper
    scraper_enhancements = create_enhanced_scraper(
        scraper_name="Optimized Player History Scraper",
        estimated_requests=estimated_requests,
        cron_frequency="daily"
    )
    
    # Initialize components
    config = get_league_config(league_subdomain)
    league_id = config["league_id"]
    data_dir = build_league_data_dir(league_id)

    stealth_manager = OptimizedStealthManager(pool_size=max_workers, use_stealth=True)
    cache = PlayerDataCache() if use_cache else None

    try:
        # Get initial browser for discovery  
        discovery_browser = stealth_manager.get_browser()
        
        if not discovery_browser:
            raise Exception("Failed to create discovery browser")

        try:
            # Phase 1: Optimized Discovery
            print("\n🔍 PHASE 1: Optimized Team Discovery")
            discovery_start = datetime.now()

            # Track request and add throttling before discovery
            scraper_enhancements.track_request("discovery_phase")
            add_throttling_to_loop()

            discovery_results = discover_teams_optimized(discovery_browser, config)

            discovery_duration = datetime.now() - discovery_start
            print(
                f"✅ Discovery completed in {discovery_duration.total_seconds():.1f}s"
            )

            # Phase 2: Concurrent Team Processing
            print(f"\n⚡ PHASE 2: Concurrent Team Processing ({max_workers} workers)")
            mapping_start = datetime.now()

            # Track request and add throttling before team processing
            scraper_enhancements.track_request("team_processing_phase")
            add_throttling_to_loop()

            player_to_team_map = {}
            teams_list = list(discovery_results["teams"].items())

            # Process teams concurrently
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_team = {
                    executor.submit(
                        process_team_page_concurrent, team_info, config, stealth_manager
                    ): team_info[0]
                    for team_info in teams_list
                }

                completed = 0
                for future in as_completed(future_to_team):
                    completed += 1
                    team_name, team_mappings = future.result()
                    player_to_team_map.update(team_mappings)

                    if completed % 10 == 0 or completed == len(teams_list):
                        progress = (completed / len(teams_list)) * 100
                        print(
                            f"   📊 Team processing: {completed}/{len(teams_list)} ({progress:.1f}%)"
                        )

            mapping_duration = datetime.now() - mapping_start
            print(
                f"✅ Team mapping completed in {mapping_duration.total_seconds():.1f}s"
            )
            print(f"🔗 Mapped {len(player_to_team_map)} players to teams")

            # Phase 3: Player Data Collection
            print(f"\n👥 PHASE 3: Player Data Collection")

            # Get player page using proxy-first approach
            player_page_url = f"{config['base_url']}/?mod={config['player_page_mod']}"
            
            # Use proxy request for faster loading
            html_content = stealth_manager.get_html_with_proxy(player_page_url)
            if not html_content:
                raise Exception("Failed to load player page")

            soup = BeautifulSoup(html_content, "html.parser")

            # Find all player rows
            all_rows = []
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        all_rows.append(row)

            total_players = len(all_rows)
            if test_mode and max_players:
                all_rows = all_rows[:max_players]
                print(f"📋 Found {total_players} total players, limiting to {len(all_rows)} for testing")
            else:
                print(f"📋 Found {len(all_rows)} players to process")

            # Process players with reduced delays and batching
            all_players_json = []
            processing_start = datetime.now()

            for row_idx, row in enumerate(all_rows, 1):
                if row_idx % 50 == 0:  # Progress update every 50 players
                    elapsed = datetime.now() - processing_start
                    progress = (row_idx / len(all_rows)) * 100
                    avg_time = elapsed.total_seconds() / row_idx
                    remaining = (len(all_rows) - row_idx) * avg_time
                    eta = datetime.now() + timedelta(seconds=remaining)
                    print(
                        f"📊 Progress: {row_idx}/{len(all_rows)} ({progress:.1f}%) | ETA: {eta.strftime('%H:%M:%S')}"
                    )

                cells = row.find_all("td")

                # Extract basic info
                first_name = cells[0].text.strip() if len(cells) > 0 else "Unknown"
                last_name = cells[1].text.strip() if len(cells) > 1 else "Unknown"
                rating = cells[2].text.strip() if len(cells) > 2 else "N/A"

                # Get team mapping
                full_player_name = f"{first_name} {last_name}".strip()
                series_name = "Unknown"
                club_name = "Unknown"

                if full_player_name in player_to_team_map:
                    team_info = player_to_team_map[full_player_name]
                    series_name = team_info["series"]
                    club_name = team_info["club"]

                # Get stats with caching
                link = row.find("a")
                stats = {"Wins": 0, "Losses": 0, "Win %": "0.0%", "match_details": []}

                if link:
                    href = link.get("href", "")
                    tenniscores_id = extract_tenniscores_player_id(href)
                    player_id = create_player_id(
                        tenniscores_id, first_name, last_name, club_name
                    )

                    try:
                        stats = get_player_stats_optimized(
                            href, config, stealth_manager, cache
                        )
                    except Exception as e:
                        print(
                            f"   ❌ Error getting stats for {first_name} {last_name}: {e}"
                        )
                else:
                    player_id = create_player_id(None, first_name, last_name, club_name)

                # Create player JSON in exact format expected
                player_json = {
                    "league_id": league_id,
                    "player_id": player_id,
                    "name": f"{first_name} {last_name}",
                    "first_name": first_name,
                    "last_name": last_name,
                    "series": series_name,
                    "club": club_name,
                    "rating": str(rating) if rating else "0.0",  # Always string format
                    "wins": stats["Wins"],
                    "losses": stats["Losses"],
                    "matches": [
                        {
                            "date": m["date"],
                            "end_pti": str(m["end_pti"]) if m["end_pti"] else "0.0",  # Always string format
                            "series": m["series"],
                        }
                        for m in stats.get("match_details", [])
                    ],
                }
                all_players_json.append(player_json)

            # Save results
            if test_mode:
                filename = os.path.join(data_dir, f"player_history_test_{max_players}_players.json")
            else:
                filename = os.path.join(data_dir, "player_history.json")
            
            with open(filename, "w", encoding="utf-8") as jsonfile:
                json.dump(all_players_json, jsonfile, indent=2)

            # Save cache
            if cache:
                cache.save_cache()

            # Final timing
            end_time = datetime.now()
            total_duration = end_time - start_time

            print(f"\n🎉 OPTIMIZED SCRAPING COMPLETE!")
            print("=" * 70)
            print(f"⏱️  TOTAL DURATION: {total_duration}")
            print(f"📈 Total players: {len(all_players_json)}")
            print(
                f"⚡ Players per minute: {(len(all_players_json) / total_duration.total_seconds() * 60):.1f}"
            )
            print(f"💾 Data saved to: {filename}")
            
            # Log enhanced session summary
            scraper_enhancements.log_session_summary()
        
        finally:
            # Return discovery browser
            stealth_manager.return_browser(discovery_browser)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        stealth_manager.cleanup()


if __name__ == "__main__":
    print("🚀 OPTIMIZED TennisScores Player History Scraper")
    print("=" * 60)

    league_subdomain = input("Enter league subdomain: ").strip().lower()
    if not league_subdomain:
        print("❌ No league subdomain provided. Exiting.")
        exit(1)

    # Configuration options
    max_workers = int(
        input("Enter number of concurrent workers (default 4): ").strip() or 4
    )
    use_cache = input("Use intelligent caching? (Y/n): ").strip().lower() != "n"
    
    # Test mode option
    test_mode_input = input("Enable test mode? (y/N): ").strip().lower()
    test_mode = test_mode_input == "y"
    max_players = None
    
    if test_mode:
        max_players = int(input("Enter max players for testing (default 10): ").strip() or 10)

    print(f"🌐 Target: https://{league_subdomain}.tenniscores.com")
    print(f"⚡ Workers: {max_workers}")
    print(f"💾 Caching: {'Enabled' if use_cache else 'Disabled'}")
    if test_mode:
        print(f"🧪 Test Mode: {max_players} players")
    print()

    scrape_player_history_optimized(league_subdomain, max_workers, use_cache, test_mode, max_players)
