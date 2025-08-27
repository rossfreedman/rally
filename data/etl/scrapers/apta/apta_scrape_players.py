#!/usr/bin/env python3
"""
Comprehensive APTA Chicago Roster Scraper

This script systematically scrapes ALL APTA Chicago series (1-22) directly from 
team roster pages to capture every registered player, including those in missing 
series.

Unlike the match-based scraper, this goes directly to team/roster pages to find
ALL registered players, not just those who have played matches.

Usage:
    python3 apta_scrape_players.py [--series 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22] [--force-restart]
"""

import sys
import os
import time
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup

# Add the parent directory to the path to access scraper modules
print(f"🔍 Debug: __file__ = {__file__}")
print(f"🔍 Debug: os.path.dirname(__file__) = {os.path.dirname(__file__)}")
parent_path = os.path.join(os.path.dirname(__file__), '..')
print(f"🔍 Debug: parent_path = {parent_path}")
print(f"🔍 Debug: absolute parent_path = {os.path.abspath(parent_path)}")
sys.path.append(parent_path)
print(f"🔍 Debug: sys.path now contains: {sys.path[-3:]}")

from stealth_browser import EnhancedStealthBrowser, StealthConfig
from user_agent_manager import UserAgentManager

class APTAChicagoRosterScraper:
    """Comprehensive APTA Chicago roster scraper that hits all series pages"""
    
    def __init__(self, force_restart=False, target_series=None):
        self.base_url = "https://aptachicago.tenniscores.com"
        self.all_players = []
        self.completed_series = set()  # Track completed series for resumption
        self.target_series = target_series  # Specific series to scrape (e.g., ['1', '2', '3'])

        self.start_time = time.time()
        self.force_restart = force_restart
        
        # Force stealth browser usage instead of curl
        print("🔧 Forcing stealth browser usage...")
        print("💡 Using enhanced stealth browser for maximum anti-detection!")
        
        # Initialize stealth browser with better error handling
        self.stealth_browser = self._initialize_stealth_browser()
        
        if self.stealth_browser:
            print("✅ Stealth browser initialized successfully")
        else:
            print("⚠️ Stealth browser failed - using curl fallback for all requests")
        
        # Load existing progress if not forcing restart
        self.load_existing_progress()
    
    def _initialize_stealth_browser(self) -> Optional[EnhancedStealthBrowser]:
        """
        Initialize stealth browser with enhanced error handling and proxy management.
        
        Returns:
            EnhancedStealthBrowser instance if successful, None if failed
        """
        try:
            print("🔧 Initializing stealth browser...")
            
            # Initialize user agent manager
            user_agent_manager = UserAgentManager()
            current_user_agent = user_agent_manager.get_user_agent_for_site("https://apta.tenniscores.com")
            print(f"   🎭 Using User-Agent: {current_user_agent[:50]}...")
            
            # Direct access test is now done upfront in __init__
            print("   🧪 Initializing stealth browser for fallback use...")
            
            # Enhanced stealth configuration matching our successful test
            stealth_config = StealthConfig(
                fast_mode=False,        # Use stealth mode for better success rate
                verbose=True,           # Enable verbose logging for debugging
                environment="production",  # Use production delays
                headless=False,         # Disable headless mode for APTA (they detect it)
                min_delay=3.0,         # Shorter delays like our working test
                max_delay=5.0,         # Shorter delays like our working test
                max_retries=3,         # Fewer retries like our working test
                base_backoff=1.0,      # Shorter backoff like our working test
                max_backoff=5.0        # Shorter backoff like our working test
            )
            
            # Initialize stealth browser with enhanced config
            stealth_browser = EnhancedStealthBrowser(stealth_config)
            
            # Test the browser with a Series page (which we know works) instead of root URL
            print("   🧪 Testing stealth browser on Series page...")
            test_url = "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3Zz0%3D"
            
            # Try multiple test attempts with different approaches
            max_test_attempts = 5  # More attempts for APTA
            for attempt in range(max_test_attempts):
                try:
                    print(f"   🧪 Test attempt {attempt + 1}/{max_test_attempts}...")
                    
                    # Add longer delay between test attempts for APTA
                    if attempt > 0:
                        delay = 10 + (attempt * 5)  # 15s, 20s, 25s, 30s delays
                        print(f"   ⏳ Waiting {delay}s before retry...")
                        time.sleep(delay)
                    
                    # Try to get a working proxy first
                    if hasattr(stealth_browser, 'rotate_proxy'):
                        print("   🔄 Rotating proxy before test...")
                        stealth_browser.rotate_proxy()
                    
                    test_response = stealth_browser.get_html(test_url)
                    
                    if test_response and len(test_response) > 100000:  # Series pages should be ~179K chars
                        print("   ✅ Stealth browser test successful - got full Series page")
                        return stealth_browser
                    elif test_response and len(test_response) > 50000:  # Partial but usable
                        print("   ⚠️ Stealth browser test partial - response usable")
                        return stealth_browser
                    else:
                        print(f"   ❌ Test attempt {attempt + 1} failed - response too short")
                        # Try proxy rotation
                        if hasattr(stealth_browser, 'rotate_proxy'):
                            print("   🔄 Rotating proxy and retrying...")
                            stealth_browser.rotate_proxy()
                        
                except Exception as e:
                    print(f"   ❌ Test attempt {attempt + 1} failed: {e}")
                    # Try proxy rotation on error
                    if hasattr(stealth_browser, 'rotate_proxy'):
                        print("   🔄 Rotating proxy after error...")
                        stealth_browser.rotate_proxy()
                    continue
            
            print("   ❌ All stealth browser tests failed")
            print("   🔄 APTA Chicago has sophisticated detection - using direct curl approach")
            return None
                
        except Exception as e:
            print(f"   ❌ Failed to initialize stealth browser: {e}")
            print("   🔄 Falling back to direct curl approach")
            return None

    def _test_direct_access(self, url: str) -> bool:
        """
        Test direct access to APTA Chicago without proxies.
        
        Args:
            url: URL to test
            
        Returns:
            bool: True if direct access successful, False otherwise
        """
        try:
            import subprocess
            
            print(f"   🌐 Testing direct access to: {url}")
            
            # Simple curl command without proxies
            curl_cmd = [
                'curl', '-s', '-L',  # Silent, follow redirects
                '--max-time', '15',   # 15 second timeout
                '--retry', '1',       # Retry once on failure
                '--retry-delay', '1', # 1 second between retries
                '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                '-H', 'Accept-Language: en-US,en;q=0.5',
                '-H', 'Connection: keep-alive',
                url
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0 and result.stdout:
                content = result.stdout
                if len(content) > 1000:
                    print(f"   ✅ Direct access successful: {len(content)} characters")
                    # Check if it's actually blocked (more accurate detection)
                    if self._is_actually_blocked(content):
                        print("   🚫 Blocking detected in direct access")
                        return False
                    return True
                else:
                    print(f"   ⚠️ Direct access returned insufficient content: {len(content)} characters")
                    return False
            else:
                print(f"   ❌ Direct access failed: return code {result.returncode}")
                if result.stderr:
                    print(f"      Error: {result.stderr[:100]}...")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ Direct access timed out")
            return False
        except Exception as e:
            print(f"   ❌ Direct access error: {e}")
            return False
    
    def _is_actually_blocked(self, html: str) -> bool:
        """
        Accurate blocking detection that avoids false positives.
        
        Args:
            html: HTML content to check
            
        Returns:
            bool: True if actually blocked, False if normal content
        """
        if not html:
            return True
        
        html_lower = html.lower()
        
        # Check for actual blocking indicators (not false positives)
        blocking_indicators = [
            "access denied",
            "blocked",
            "verify you are human",
            "robot check",
            "bot check",
            "suspicious activity",
            "rate limit",
            "too many requests"
        ]
        
        # Check for actual blocking content, not CSS classes or JavaScript
        for indicator in blocking_indicators:
            if indicator in html_lower:
                # Verify it's not just in CSS or JavaScript
                if not any(context in html_lower for context in [".captcha", "#captcha", "captcha", "captcha"]):
                    return True
        
        # Check for blank or very short pages
        if len(html) < 500:
            return True
        
        # Check for error pages
        if "error" in html_lower and "page not found" in html_lower:
            return True
        
        return False

    def _handle_proxy_rotation(self, stealth_browser: EnhancedStealthBrowser) -> bool:
        """
        Handle proxy rotation with intelligent error handling to prevent infinite loops.
        
        Args:
            stealth_browser: The stealth browser instance
            
        Returns:
            bool: True if proxy rotation successful, False if should fall back to curl
        """
        try:
            # Check if proxy rotation is needed
            if not hasattr(stealth_browser, 'rotate_proxy') or not stealth_browser.rotate_proxy():
                print("   ℹ️ No proxy rotation available")
                return True
            
            # Limit proxy rotation attempts
            max_rotation_attempts = 3
            for attempt in range(max_rotation_attempts):
                try:
                    print(f"   🔄 Rotating proxy (attempt {attempt + 1}/{max_rotation_attempts})...")
                    
                    # Add delay between rotation attempts
                    if attempt > 0:
                        time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s
                    
                    # Test the new proxy with a simple request
                    test_response = stealth_browser.get_html("https://apta.tenniscores.com")
                    if test_response and len(test_response) > 100:
                        print("   ✅ Proxy rotation successful")
                        return True
                    else:
                        print(f"   ⚠️ Proxy rotation attempt {attempt + 1} failed - insufficient response")
                        
                except Exception as e:
                    print(f"   ❌ Proxy rotation attempt {attempt + 1} failed: {e}")
                    continue
            
            print("   ⚠️ Proxy rotation failed after all attempts")
            return False
            
        except Exception as e:
            print(f"   ❌ Proxy rotation error: {e}")
            return False
    
    def _add_intelligent_delay(self, request_type: str = "general"):
        """
        Add intelligent delays between requests to avoid rate limiting.
        
        Args:
            request_type: Type of request ("series", "team", "general")
        """
        if request_type == "series":
            # Longer delay between series pages
            delay = 5 + (2 * (len(self.completed_series) % 3))  # 5-9 seconds
            print(f"   ⏳ Waiting {delay}s before next series...")
            time.sleep(delay)
        elif request_type == "team":
            # Standard delay between team pages
            delay = 3
            print(f"   ⏳ Waiting {delay}s before next team...")
            time.sleep(delay)
        else:
            # General delay for other requests
            delay = 2
            print(f"   ⏳ Adding {delay}s delay...")
            time.sleep(delay)
    
    def _team_belongs_to_series(self, team_name: str, series_identifier: str) -> bool:
        """
        Determine if a team belongs to the specified series in APTA Chicago.
        APTA Chicago uses numbered series (1-22).
        """
        if not team_name or not series_identifier:
            return False
        
        # Extract series number from series identifier
        if series_identifier.startswith("Series "):
            series_value = series_identifier.replace("Series ", "")
        else:
            series_value = series_identifier
        
        # APTA Chicago team naming patterns:
        # - "Club Name Series X" (e.g., "Chicago Series 22", "Glenbrook Series 8")
        # - "Club Name X" (e.g., "Chicago 22", "Glenbrook 8")
        # - "Club Name Series X" (e.g., "Chicago Series 22", "Glenbrook Series 8")
        
        # Check if team name contains the series identifier
        if series_value.isdigit():
            # Numeric series (1-22)
            # Check for "Series X" pattern
            if f"Series {series_value}" in team_name:
                return True
            # Check for " X" pattern (space + number)
            if f" {series_value}" in team_name:
                return True
            # Check for end-of-name pattern
            if team_name.endswith(f" {series_value}"):
                return True
        
        return False

    def _parse_player_name(self, full_name: str) -> Tuple[str, str]:
        """
        Enhanced name parsing to handle compound first names and organizational suffixes.
        
        Fixes issues like:
        - "Mary Jo Lestingi" -> ("Mary Jo", "Lestingi") instead of ("Mary", "Jo Lestingi") 
        - "Peters - MSC" -> ("Peters", "") by removing organizational suffixes
        
        Preserves legitimate patterns like:
        - Hyphens: "Smith-Jones" 
        - Apostrophes: "O'Brien"
        """
        if not full_name or not full_name.strip():
            return 'Unknown', ''
        
        # Clean the name
        name = full_name.strip()
        
        # Remove organizational suffixes (like "- MSC")
        name = self._clean_organizational_suffixes(name)
        
        # Split into parts
        parts = name.split()
        if len(parts) == 0:
            return 'Unknown', ''
        elif len(parts) == 1:
            return parts[0], ''
        elif len(parts) == 2:
            return parts[0], parts[1]
        else:
            # Handle compound names intelligently
            return self._handle_compound_names(parts)
    
    def _clean_organizational_suffixes(self, name: str) -> str:
        """Remove organizational suffixes like '- MSC' from names"""
        # List of organizational suffixes to remove
        org_suffixes = [
            ' - MSC',
            ' - msc',
            ' MSC',
            ' msc'
        ]
        
        for suffix in org_suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        return name
    
    def _handle_compound_names(self, parts: List[str]) -> Tuple[str, str]:
        """
        Handle names with 3+ parts to distinguish compound first names from parsing errors.
        
        Strategy:
        1. If last part looks like a clear surname (capitalized, common pattern), use it as last name
        2. If multiple capitalized words, likely indicates first name was split incorrectly
        3. For names like "Mary Jo Lestingi", assume "Mary Jo" is first name, "Lestingi" is last
        """
        if len(parts) < 3:
            return parts[0], ' '.join(parts[1:])
        
        # Check if this looks like a compound first name case
        # Heuristic: if the middle part(s) are short and could be middle names or compound first names
        middle_parts = parts[1:-1]
        last_part = parts[-1]
        
        # If we have exactly 3 parts and middle part is short (1-2 chars or common compound names)
        if len(parts) == 3:
            middle = parts[1]
            # Common compound first name patterns
            compound_indicators = ['Jo', 'Ann', 'Anne', 'Sue', 'Lee', 'May', 'Kay', 'Beth', 'Lynn', 'Rose']
            
            if (len(middle) <= 2 or 
                middle in compound_indicators or 
                middle.lower() in [x.lower() for x in compound_indicators]):
                # Treat as compound first name: "Mary Jo" + "Lestingi"
                first_name = f"{parts[0]} {middle}"
                last_name = last_part
            else:
                # Treat as first + middle + last: "John" + "Michael Smith"
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
        else:
            # For 4+ parts, assume first part is first name, rest is last name
            # This handles cases like parsing errors where multiple words got split
            first_name = parts[0]
            last_name = ' '.join(parts[1:])
        
        return first_name, last_name

    def _convert_to_apta_format(self, nndz_player_id: str) -> str:
        """
        Convert nndz- format player ID to apta_ format using simple prefix replacement.
        
        This ensures compatibility with the ETL system which expects apta_ format IDs
        for APTA Chicago players to prevent match import failures.
        
        Args:
            nndz_player_id: Player ID in nndz-XXXXX format
            
        Returns:
            Player ID in apta_XXXXX format (simple prefix replacement)
        """
        if not nndz_player_id or not nndz_player_id.startswith('nndz-'):
            return nndz_player_id
        
        # Simple prefix replacement: nndz-XXXXX -> apta_XXXXX
        return nndz_player_id.replace('nndz-', 'apta_')

    def get_series_urls(self) -> List[Tuple[str, str]]:
        """Generate URLs for APTA Chicago series (1-22)"""
        series_urls = []
        
        # APTA Chicago uses numbered series (1-22)
        # These are the actual series URLs from the website
        series_urls_data = [
            # Numeric series (1-22)
            ("Series 1", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3MD0%3D"),
            ("Series 2", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3bz0%3D"),
            ("Series 3", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3az0%3D"),
            ("Series 4", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3cz0%3D"),
            ("Series 5", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3WT0%3D"),
            ("Series 6", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3Zz0%3D"),
            ("Series 7", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMaz0%3D"),
            ("Series 8", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMWT0%3D"),
            ("Series 9", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMYz0%3D"),
            ("Series 10", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3ND0%3D"),
            ("Series 11", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3OD0%3D"),
            ("Series 12", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
            ("Series 13", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 14", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3bz0%3D"),
            ("Series 15", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3cz0%3D"),
            ("Series 16", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
            ("Series 17", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 18", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 19", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 20", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 21", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 22", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D")
        ]
        
        # Filter series based on target_series parameter
        if self.target_series:
            filtered_data = []
            for series_name, series_path in series_urls_data:
                # Extract series identifier (number or letter)
                series_id = series_name.replace('Series ', '').strip()
                if series_id in self.target_series:
                    filtered_data.append((series_name, series_path))
            series_urls_data = filtered_data
        
        # Process series URLs
        for series_name, series_path in series_urls_data:
            # All APTA Chicago series have hardcoded URLs
            series_url = f"{self.base_url}{series_path}"
            series_urls.append((series_name, series_url))
        
        return series_urls
    
    def extract_players_from_series_page(self, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific series by finding team links and scraping their rosters"""
        print(f"\n🎾 Scraping {series_name} from {series_url}")
        
        try:
            # Use stealth browser with fallback to curl
            start_time = time.time()
            html_content = self.get_html_content(series_url)
            elapsed = time.time() - start_time
            
            # If request took too long, it might be stuck in proxy testing
            if elapsed > 120:  # 2 minutes
                print(f"⚠️ Request took {elapsed:.1f}s - possible proxy testing loop")
                
            if not html_content:
                print(f"❌ Failed to get content for {series_name}")
                print(f"   🔍 Debug: HTML content is None or empty")
                return []
            
            print(f"   ✅ Got HTML content ({len(html_content)} characters)")
            
            # Add intelligent delay after successful series page request
            self._add_intelligent_delay("series")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            all_players = []
            
            # Find all team links on the series page
            team_links = []
            all_links = soup.find_all('a', href=True)
            
            print(f"   🔍 Found {len(all_links)} total links on page")
            
            # Extract series number/letter for filtering
            series_identifier = series_name.replace('Series ', '').strip()
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for team links (they contain 'team=' parameter)
                if 'team=' in href and text and any(keyword.lower() in text.lower() for keyword in ['Tennaqua', 'Winter Club', 'Lake Forest', 'Evanston', 'Prairie Club', 'Wilmette', 'North Shore', 'Valley Lo', 'Westmoreland', 'Indian Hill', 'Birchwood', 'Exmoor', 'Glen View', 'Glenbrook', 'Park Ridge', 'Skokie', 'Michigan Shores', 'Midtown', 'Hinsdale', 'Knollwood', 'Sunset Ridge', 'Briarwood', 'Biltmore', 'Barrington Hills', 'Bryn Mawr', 'Saddle & Cycle', 'Onwentsia', 'Lake Bluff', 'Lake Shore', 'Northmoor', 'Butterfield', 'River Forest', 'LifeSport', 'Winnetka']):
                    
                    # Filter teams to only include those belonging to this specific series
                    if self._team_belongs_to_series(text, series_identifier):
                        if href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = href
                        team_links.append((text, full_url))
            
            print(f"🏢 Found {len(team_links)} team links in {series_name}")
            
            if not team_links:
                print(f"   ⚠️ No team links found - this might indicate a filtering issue")
                print(f"   🔍 Series identifier: '{series_identifier}'")
                # Show some sample links for debugging
                sample_links = [link.get_text(strip=True) for link in all_links[:10] if link.get_text(strip=True)]
                print(f"   🔍 Sample links on page: {sample_links}")
            
            # Extract players from team roster pages (simple approach)
            print("   🔄 Using team roster-based player extraction...")
            series_players = self.extract_players_from_team_rosters(team_links, series_identifier)
            all_players.extend(series_players)
            
            # Show series summary
            if series_players:
                print(f"      📊 Series {series_name}: {len(series_players)} players added")
            else:
                print(f"      ⚠️ Series {series_name}: No players found")
            
            print(f"✅ Extracted {len(all_players)} total players from {series_name}")
            
            # Show series summary with team breakdown
            if all_players:
                team_counts = {}
                for player in all_players:
                    team = player.get('scrape_team', 'Unknown')
                    team_counts[team] = team_counts.get(team, 0) + 1
                
                print(f"   📊 Series {series_name} breakdown:")
                for team, count in sorted(team_counts.items()):
                    print(f"      {team}: {count} players")
            
            return all_players
            
        except Exception as e:
            print(f"❌ Error scraping {series_name}: {e}")
            import traceback
            print(f"   🔍 Full error: {traceback.format_exc()}")
            return []
    
    def extract_players_from_team_rosters(self, team_links: List[Tuple[str, str]], series_identifier: str) -> List[Dict]:
        """Extract players from team roster pages"""
        print(f"🔍 Extracting players from {len(team_links)} team roster pages...")
        
        all_players = []
        
        for i, (team_name, team_url) in enumerate(team_links):
            print(f"   🏢 Scraping team {i+1}/{len(team_links)}: {team_name}")
            
            try:
                # Get the team roster page
                team_html = self.get_html_content(team_url)
                if not team_html:
                    print(f"      ❌ Failed to load team page for {team_name}")
                    continue
                
                # Parse team roster
                team_players = self._parse_team_roster(team_html, team_name, series_identifier)
                if team_players:
                    all_players.extend(team_players)
                    print(f"      ✅ Found {len(team_players)} players in {team_name}")
                else:
                    print(f"      ⚠️ No players found in {team_name}")
                
                # Add delay between team requests
                if i < len(team_links) - 1:
                    time.sleep(2)
                    
            except Exception as e:
                print(f"      ❌ Error scraping {team_name}: {e}")
                continue
        
        print(f"🎯 Total players extracted from team rosters: {len(all_players)}")
        return all_players

    def _parse_team_roster(self, html: str, team_name: str, series_identifier: str) -> List[Dict]:
        """Parse a team roster page to extract player information"""
        soup = BeautifulSoup(html, 'html.parser')
        players = []
        
        # Look for player tables or lists
        player_elements = soup.find_all(['tr', 'div', 'span'], class_=lambda x: x and 'player' in x.lower() if x else False)
        
        if not player_elements:
            # Try alternative selectors
            player_elements = soup.find_all('td', string=lambda x: x and len(x.strip()) > 2 and x.strip()[0].isupper())
        
        for element in player_elements:
            text = element.get_text(strip=True)
            if text and len(text) > 2 and len(text) < 50:
                # Look for name-like patterns
                if any(char.isupper() for char in text) and any(char.islower() for char in text):
                    # Parse player name into first and last
                    name_parts = text.strip().split()
                    if len(name_parts) >= 2:
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                    else:
                        first_name = text.strip()
                        last_name = ""
                    
                    # Extract club name from team name
                    club_name = team_name
                    if ' - ' in team_name:
                        parts = team_name.split(' - ')
                        if len(parts) == 2:
                            club_name = parts[0].strip()
                    
                    # Create a unique player record for THIS team appearance
                    # This allows the same player to appear on multiple teams
                    player_data = {
                        'League': 'APTA_CHICAGO',
                        'Club': club_name,
                        'Series': f'Series {series_identifier}',
                        'Team': team_name,
                        'Player ID': f'nndz-{self._generate_player_id(text)}',  # Generate unique ID for this team appearance
                        'First Name': first_name,
                        'Last Name': last_name,
                        'PTI': 'N/A',
                        'Wins': '0',
                        'Losses': '0',
                        'Win %': '0.0%',
                        'Captain': '',  # Could be enhanced to detect captain status
                        'Source URL': team_name,  # Use team name as source for now
                        'source_league': 'APTA_CHICAGO',
                        'extraction_method': 'team_roster',
                        'team_context': team_name  # Add team context to distinguish multiple appearances
                    }
                    players.append(player_data)
        
        return players
    
    def _generate_player_id(self, player_name: str) -> str:
        """Generate a unique player ID for team roster extraction"""
        # Create a hash-based ID that's unique per player+team combination
        import hashlib
        # Use player name + timestamp to ensure uniqueness
        unique_string = f"{player_name}_{int(time.time() * 1000)}"
        hash_object = hashlib.md5(unique_string.encode())
        # Take first 12 characters of hash and encode as base64
        hash_hex = hash_object.hexdigest()[:12]
        return hash_hex
    
    def _consolidate_all_temp_files(self) -> List[Dict]:
        """Consolidate all series temp files into a single player list"""
        print("🔍 Consolidating all temp series files...")
        
        temp_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'temp')
        all_players = []
        
        if not os.path.exists(temp_dir):
            print("   ⚠️ No temp directory found")
            return all_players
        
        # Find all series_*.json files
        series_files = []
        for filename in os.listdir(temp_dir):
            if filename.startswith('series_') and filename.endswith('.json'):
                series_files.append(filename)
        
        print(f"   📁 Found {len(series_files)} series temp files")
        
        for filename in sorted(series_files):
            file_path = os.path.join(temp_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    series_players = json.load(f)
                
                if isinstance(series_players, list):
                    all_players.extend(series_players)
                    print(f"   ✅ {filename}: {len(series_players)} players")
                else:
                    print(f"   ⚠️ {filename}: Invalid format (not a list)")
                    
            except Exception as e:
                print(f"   ❌ {filename}: Error reading file - {e}")
        
        print(f"   📊 Total consolidated players: {len(all_players):,}")
        return all_players
    
    def _merge_player_data(self, existing_players: List[Dict], new_players: List[Dict]) -> List[Dict]:
        """Merge existing and new player data, avoiding duplicates"""
        print("🔄 Merging existing and new player data...")
        
        # Create a lookup set for existing players to avoid duplicates
        # Use combination of name + team + series as unique identifier
        existing_lookup = set()
        for player in existing_players:
            if isinstance(player, dict):
                name = player.get('First Name', '') + ' ' + player.get('Last Name', '')
                team = player.get('Team', '')
                series = player.get('Series', '')
                key = f"{name}|{team}|{series}"
                existing_lookup.add(key)
        
        print(f"   📊 Existing players: {len(existing_players):,}")
        print(f"   📊 New players: {len(new_players):,}")
        
        # Start with existing players
        merged_players = existing_players.copy()
        added_count = 0
        
        # Add new players that don't already exist
        for player in new_players:
            if isinstance(player, dict):
                name = player.get('First Name', '') + ' ' + player.get('Last Name', '')
                team = player.get('Team', '')
                series = player.get('Series', '')
                key = f"{name}|{team}|{series}"
                
                if key not in existing_lookup:
                    merged_players.append(player)
                    added_count += 1
                    existing_lookup.add(key)  # Add to lookup to avoid duplicates within new data
        
        print(f"   ✅ Added {added_count} new unique players")
        print(f"   📊 Final merged total: {len(merged_players):,} players")
        
        return merged_players

    # Removed extract_players_from_match_history method - no longer needed
    
    # Removed _scrape_individual_player_profile method - no longer needed
    
    # Removed _extract_pti_from_profile method - no longer needed
    
    # Removed _extract_win_loss_from_profile method - no longer needed
    
    def discover_series_dynamically(self) -> List[Tuple[str, str]]:
        """Try to discover all available series by scraping the main page"""
        print("🔍 Discovering available series from main page...")
        
        try:
            main_url = f"{self.base_url}/"
            html_content = self.get_html_content(main_url)
            
            if not html_content:
                print("❌ Failed to get main page content")
                return self.get_series_urls()  # Fallback to hardcoded list
            
            soup = BeautifulSoup(html_content, 'html.parser')
            series_links = []
            
            # Look for series links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for series patterns in the link text
                if any(keyword in text.lower() for keyword in ['series', 'division']):
                    if href.startswith('/'):
                        full_url = f"{self.base_url}{href}"
                    else:
                        full_url = href
                    series_links.append((text, full_url))
                    print(f"   📋 Discovered series: {text}")
            
            if series_links:
                print(f"✅ Dynamically discovered {len(series_links)} series")
                return series_links
            else:
                print("⚠️ No series found dynamically, using hardcoded list")
                return self.get_series_urls()
                
        except Exception as e:
            print(f"❌ Error during dynamic discovery: {e}")
            return self.get_series_urls()
    
    def scrape_all_series(self):
        """Scrape all series comprehensively with progress tracking and resilience"""
        if self.target_series:
            series_list = ', '.join(self.target_series)
            print(f"🚀 Starting APTA Chicago targeted series scraping...")
            print(f"   This will scrape series: {series_list}")
        else:
            print("🚀 Starting APTA Chicago comprehensive series roster scraping...")
            print("   This will scrape ALL series (1-22) from roster pages")
            print("   to capture every registered player, not just match participants.")
        print("⏱️ This should take about 15-20 minutes to complete")
        
        # Load existing progress if available
        self.load_existing_progress()
        
        # Use hardcoded series URLs for reliability
        series_urls = self.get_series_urls()
        
        print(f"\n📋 Will scrape {len(series_urls)} series:")
        for series_name, _ in series_urls:
            status = "✅ COMPLETED" if series_name in self.completed_series else "⏳ PENDING"
            print(f"   - {series_name} {status}")
        
        # Track progress and failures
        successful_series = len(self.completed_series)
        failed_series = []
        
        # Scrape each series with error handling
        for i, (series_name, series_url) in enumerate(series_urls, 1):
            # Skip if already completed
            if series_name in self.completed_series:
                print(f"\n⏭️ Skipping {series_name} (already completed)")
                continue
                
            # Calculate progress
            progress_percent = (i - 1) / len(series_urls) * 100
            elapsed_time = time.time() - self.start_time
            
            print(f"\n🏆 Processing Series {i}/{len(series_urls)}: {series_name}")
            print(f"📊 Progress: {progress_percent:.1f}% complete")
            print(f"⏱️ Elapsed time: {elapsed_time/60:.1f} minutes")
            
            # Handle dynamic discovery for letter series
            if series_url == "DISCOVER":
                print(f"🔍 Discovering URL for {series_name} dynamically...")
                discovered_urls = self.discover_series_dynamically()
                # Find the specific series URL
                series_url = None
                for discovered_name, discovered_url in discovered_urls:
                    if discovered_name == series_name:
                        series_url = discovered_url
                        break
                
                if not series_url:
                    print(f"❌ Could not discover URL for {series_name}")
                    failed_series.append(series_name)
                    continue
                else:
                    print(f"✅ Discovered URL for {series_name}: {series_url}")
            
            print(f"🎯 Target: {series_url}")
            
            if i > 1:
                avg_time_per_series = elapsed_time / (i - 1)
                remaining_series = len(series_urls) - i + 1
                eta_minutes = (remaining_series * avg_time_per_series) / 60
                print(f"🔮 ETA: {eta_minutes:.1f} minutes remaining")
                print(f"📈 Running average: {avg_time_per_series/60:.1f} minutes per series")
            
            try:
                series_players = self.extract_players_from_series_page(series_name, series_url)
                if series_players:
                    # Mark series as completed and save individual file BEFORE adding to aggregate
                    self.completed_series.add(series_name)
                    self.save_series_completion(series_name, series_players)
                    
                    # Now add to aggregate list
                    self.all_players.extend(series_players)
                    successful_series += 1
                    print(f"✅ {series_name}: {len(series_players)} players")
                    print(f"   📊 Total players so far: {len(self.all_players)}")
                    print(f"   📁 Saved to: data/leagues/APTA_CHICAGO/temp/{series_name.replace(' ', '_').lower()}.json")
                    
                    # Show running totals and progress
                    completion_rate = (len(self.completed_series) / len(series_urls)) * 100
                    print(f"   🎯 Overall progress: {completion_rate:.1f}% ({len(self.completed_series)}/{len(series_urls)} series)")
                    print(f"   📈 Running total: {len(self.all_players)} players across all series")
                else:
                    failed_series.append(series_name)
                    print(f"⚠️ {series_name}: No players found")
                    
                    # Still mark as completed (but with empty data) to avoid re-processing
                    self.completed_series.add(series_name)
                    self.save_series_completion(series_name, [])
                    
            except Exception as e:
                print(f"❌ Error processing {series_name}: {e}")
                failed_series.append(series_name)
            
            # Add longer delay between series to avoid anti-bot detection
            if i < len(series_urls):
                print("⏳ Waiting 5 seconds before next series...")
                time.sleep(5)
        
        # Final completion status
        self.print_completion_summary(series_urls, successful_series, failed_series)
    
    def load_existing_progress(self):
        """Load existing progress and player data if available"""
        if self.force_restart:
            # Clean up any existing progress files
            try:
                progress_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'temp', 'scrape_progress.json')
                partial_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'temp', 'players_comprehensive_partial.json')
                
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                    print("🧹 Removed progress file")
                    
                if os.path.exists(partial_file):
                    os.remove(partial_file)
                    print("🧹 Removed partial results file")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up progress files: {e}")
            
            print("📂 Starting completely fresh - no previous progress loaded")
            return
            
        try:
            progress_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'tmp', 'scrape_progress.json')
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    self.completed_series = set(progress_data.get('completed_series', []))
                    print(f"📂 Loaded progress: {len(self.completed_series)} series already completed")
                    
                # Load existing player data
                output_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'tmp', 'players_comprehensive_partial.json')
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        self.all_players = json.load(f)
                        print(f"📂 Loaded {len(self.all_players)} existing players")
            else:
                print("📂 No previous progress found - starting fresh")
        except Exception as e:
            print(f"⚠️ Error loading progress: {e}")
            
    def save_series_completion(self, series_name: str, series_players: List[Dict]):
        """Save individual series file and progress after each completed series"""
        try:
            # Create data/leagues/APTA_CHICAGO/temp directory if it doesn't exist
            series_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'temp')
            os.makedirs(series_dir, exist_ok=True)
            
            # Save individual series file
            series_filename = series_name.replace(" ", "_").lower()  # "Series 1" -> "series_1"
            series_file = f"{series_dir}/{series_filename}.json"
            
            with open(series_file, 'w', encoding='utf-8') as f:
                json.dump(series_players, f, indent=2, ensure_ascii=False)
            
            print(f"📁 Saved {series_name} to: {series_file} ({len(series_players)} players)")
            
            # Save progress tracking
            progress_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'temp', 'scrape_progress.json')
            progress_data = {
                'completed_series': list(self.completed_series),
                'last_update': datetime.now().isoformat(),
                'total_players': len(self.all_players),
                'series_files_created': len(self.completed_series)
            }
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
                
            # Save current aggregate player data (only if we have aggregate data)
            output_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'temp', 'players_comprehensive_partial.json')
            if self.all_players:  # Only save if we have aggregate data
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.all_players, f, indent=2, ensure_ascii=False)
                
            print(f"💾 Progress saved: {series_name} complete - individual file + aggregate updated")
        except Exception as e:
            print(f"⚠️ Failed to save series completion: {e}")
    
    def print_completion_summary(self, series_urls: List[Tuple[str, str]], successful_series: int, failed_series: List[str]):
        """Print detailed completion summary"""
        elapsed_time = time.time() - self.start_time
        
        print(f"\n🎉 COMPREHENSIVE SCRAPING COMPLETED!")
        print(f"⏱️ Total time: {elapsed_time/60:.1f} minutes ({elapsed_time/3600:.1f} hours)")
        print(f"📊 Successful series: {successful_series}/{len(series_urls)}")
        print(f"📊 Total players found: {len(self.all_players)}")
        
        if failed_series:
            print(f"\n⚠️ Failed series ({len(failed_series)}):")
            for series in failed_series:
                print(f"   - {series}")
        
        # Show series breakdown
        series_counts = {}
        for player in self.all_players:
            series = player.get('Series', 'Unknown')
            series_counts[series] = series_counts.get(series, 0) + 1
        
        print(f"\n📈 Players by series:")
        for series, count in sorted(series_counts.items()):
            print(f"   {series}: {count} players")
            
        # Show completion percentage
        completion_rate = (successful_series / len(series_urls)) * 100
        print(f"\n🎯 Completion rate: {completion_rate:.1f}%")
        
        if completion_rate == 100:
            print("🌟 PERFECT! All series successfully scraped!")
        elif completion_rate >= 90:
            print("✨ EXCELLENT! Nearly all series scraped!")
        elif completion_rate >= 75:
            print("👍 GOOD! Most series scraped successfully!")
        else:
            print("⚠️ Some series had issues - consider retry!")
    
    def save_intermediate_results(self):
        """Save intermediate results during long scrape (legacy method)"""
        try:
            output_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'players_intermediate.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_players, f, indent=2, ensure_ascii=False)
            print(f"   💾 Intermediate results saved to {output_file}")
        except Exception as e:
            print(f"   ⚠️ Failed to save intermediate results: {e}")
    
    def save_results(self, is_final=True):
        """Save comprehensive results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if is_final:
            print(f"\n🏁 FINALIZING COMPREHENSIVE SCRAPE RESULTS...")
            
            # Show individual series files created
            series_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'temp')
            if os.path.exists(series_dir):
                series_files = [f for f in os.listdir(series_dir) if f.endswith('.json')]
                print(f"📁 Individual series files created: {len(series_files)}")
                for series_file in sorted(series_files):
                    print(f"   - {series_file}")
            
            # Clean up progress files since we're done
            try:
                progress_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'scrape_progress.json')
                partial_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'players_comprehensive_partial.json')
                
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                    print("🧹 Cleaned up progress tracking file")
                    
                if os.path.exists(partial_file):
                    os.remove(partial_file)
                    print("🧹 Cleaned up partial results file")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up temporary files: {e}")
        
        # Save timestamped version
        output_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', f"players_comprehensive_{timestamp}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_players, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Comprehensive results saved to: {output_file}")
        
        # Update main players.json file with intelligent merging
        main_output_file = os.path.join(os.path.dirname(__file__), '..', '..', 'leagues', 'APTA_CHICAGO', 'players.json')
        
        # First, consolidate all temp files to get complete picture
        consolidated_players = self._consolidate_all_temp_files()
        
        if os.path.exists(main_output_file):
            with open(main_output_file, 'r', encoding='utf-8') as f:
                existing_players = json.load(f)
            
            print(f"\n📊 COMPARISON WITH EXISTING DATA:")
            print(f"   Existing players.json: {len(existing_players):,} players")
            print(f"   New scraped data: {len(self.all_players):,} players")
            print(f"   Consolidated temp files: {len(consolidated_players):,} players")
            
            # Merge existing data with new data, avoiding duplicates
            merged_players = self._merge_player_data(existing_players, consolidated_players)
            
            print(f"   Final merged data: {len(merged_players):,} players")
            print(f"   Added: {len(merged_players) - len(existing_players):+,} players")
            
            # Update main file with merged data
            with open(main_output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_players, f, indent=2, ensure_ascii=False)
            print(f"✅ UPDATED main file: {main_output_file}")
            print(f"   📈 Preserved existing data + added new players!")
        else:
            # No existing file, use consolidated data
            with open(main_output_file, 'w', encoding='utf-8') as f:
                json.dump(consolidated_players, f, indent=2, ensure_ascii=False)
            print(f"✅ Created main file: {main_output_file}")
            print(f"   📈 Used consolidated temp file data")
            
        if is_final:
            print(f"\n🎯 FINAL COMPREHENSIVE SCRAPE COMPLETE!")
            print(f"   ✅ All {len(self.completed_series)} series processed")
            print(f"   📁 Individual series files: data/leagues/APTA_CHICAGO/temp/")
            print(f"   📁 Final aggregated data: {main_output_file}")
            print(f"   📁 Timestamped backup: {output_file}")

    def get_html_content(self, url: str, max_retries: int = 3) -> str:
        """
        Get HTML content from URL using stealth browser with curl as emergency fallback.
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
            
        Returns:
            HTML content as string
        """
        if self.stealth_browser:
            print(f"   🌐 Using stealth browser for: {url}")
            try:
                # Try stealth browser first (prioritized)
                response = self.stealth_browser.get_html(url)
                if response and len(response) > 1000:
                    print(f"   ✅ Stealth browser successful: {len(response)} characters")
                    return response
                else:
                    print("   ⚠️ Stealth browser returned insufficient content, trying again...")
                    # Give stealth browser another chance
                    time.sleep(2)
                    response = self.stealth_browser.get_html(url)
                    if response and len(response) > 1000:
                        print(f"   ✅ Stealth browser retry successful: {len(response)} characters")
                        return response
                    else:
                        print("   ❌ Stealth browser failed after retry, using curl fallback...")
            except Exception as e:
                print(f"   ❌ Stealth browser failed: {e}, using curl fallback...")
        else:
            print("   ⚠️ No stealth browser available, using curl...")
        
        # Use curl only as emergency fallback
        print(f"   🌐 Using curl fallback for: {url}")
        return self._get_html_with_curl(url, max_retries)

    def _get_html_with_curl(self, url: str, max_retries: int = 3) -> str:
        """
        Get HTML content using curl with intelligent retries and delays.
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
            
        Returns:
            HTML content as string
        """
        import subprocess
        
        for attempt in range(max_retries):
            try:
                print(f"   📡 Curl attempt {attempt + 1}/{max_retries} for {url}...")
                
                # Add delay between attempts
                if attempt > 0:
                    delay = 3 + (attempt * 2)
                    print(f"   ⏳ Waiting {delay}s before retry...")
                    time.sleep(delay)
                
                # Get user agent from manager
                try:
                    from user_agent_manager import UserAgentManager
                    ua_manager = UserAgentManager()
                    user_agent = ua_manager.get_user_agent_for_site(url)
                except:
                    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                
                # Enhanced curl command with APTA-specific headers
                curl_cmd = [
                    'curl', '-s', '-L',  # Silent, follow redirects
                    '--max-time', '30',   # 30 second timeout
                    '--retry', '2',       # Retry on failure
                    '--retry-delay', '1', # 1 second between retries
                    '--compressed',       # Handle gzip/deflate compression
                    '-H', f'User-Agent: {user_agent}',
                    '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    '-H', 'Accept-Language: en-US,en;q=0.5',
                    '-H', 'Accept-Encoding: gzip, deflate',
                    '-H', 'Connection: keep-alive',
                    '-H', 'Upgrade-Insecure-Requests: 1',
                    '-H', 'Cache-Control: no-cache',
                    '-H', 'Pragma: no-cache',
                    '--cookie-jar', '/tmp/apta_cookies.txt',  # Maintain cookies
                    '--cookie', '/tmp/apta_cookies.txt',
                    url
                ]
                
                result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=35)
                
                if result.returncode == 0 and result.stdout:
                    content = result.stdout
                    if len(content) > 1000:  # Higher threshold for APTA
                        print(f"   ✅ Curl successful: {len(content)} characters")
                        return content
                    elif len(content) > 500:
                        print(f"   ⚠️ Curl partial success: {len(content)} characters")
                        # Check if it's actually blocked (more accurate detection)
                        if self._is_actually_blocked(content):
                            print("   🚫 Blocking detected in curl response")
                            continue
                        return content
                    else:
                        print(f"   ⚠️ Curl returned insufficient content: {len(content)} characters")
                else:
                    print(f"   ❌ Curl failed: return code {result.returncode}")
                    if result.stderr:
                        print(f"      Error: {result.stderr[:100]}...")
                        
            except subprocess.TimeoutExpired:
                print(f"   ⏰ Curl attempt {attempt + 1} timed out")
            except Exception as e:
                print(f"   ❌ Curl attempt {attempt + 1} failed: {e}")
                continue
        
        print(f"   💀 All curl attempts failed for: {url}")
        return ""

def main():
    """Main function"""
    import sys
    
    # Show help if requested
    if "--help" in sys.argv or "-h" in sys.argv:
        print("APTA Chicago Roster Scraper - Usage:")
        print("  python apta_scrape_players.py                    # Scrape all series (1-22)")
        print("  python apta_scrape_players.py --series 1,2,3     # Scrape specific series (1, 2, 3)")
        print("  python apta_scrape_players.py --series=1,2,3     # Scrape specific series (1, 2, 3)")
        print("  python apta_scrape_players.py --force-restart    # Force restart ignoring progress")
        print("  python apta_scrape_players.py --fresh            # Same as --force-restart")
        print("  python apta_scrape_players.py --help             # Show this help message")
        
        print("\nExamples:")
        print("  python apta_scrape_players.py --series 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22  # Scrape all series")
        print("  python apta_scrape_players.py --series 1,2,3                   # Scrape series 1, 2, 3")
        return
    
    # Parse command line arguments
    force_restart = "--force-restart" in sys.argv or "--fresh" in sys.argv
    target_series = None
    
    # Check for series specification
    for i, arg in enumerate(sys.argv):
        if arg == "--series" and i + 1 < len(sys.argv):
            target_series = sys.argv[i + 1].split(',')
            # Remove the --series argument and its value
            sys.argv.pop(i)
            sys.argv.pop(i)
            break
        elif arg.startswith("--series="):
            target_series = arg.split("=", 1)[1].split(',')
            sys.argv.remove(arg)
            break
    
    # Validate target_series if specified
    if target_series:
        valid_series = [str(i) for i in range(1, 18)] + list('ABCDEFGHIJK')
        invalid_series = [s for s in target_series if s not in valid_series]
        if invalid_series:
            print(f"❌ Error: Invalid series specified: {', '.join(invalid_series)}")
            print(f"   Valid series are: 1-17 and A-K")
            return
        print(f"✅ Valid series specified: {', '.join(target_series)}")
    
    print("============================================================")
    if target_series:
        series_list = ', '.join(target_series)
        print(f"🏆 APTA Chicago TARGETED SERIES SCRAPER")
        print(f"   Scraping specific series: {series_list}")
    else:
        print("🏆 COMPREHENSIVE APTA Chicago ROSTER SCRAPER")
        print("   Scraping ALL series (1-22) from roster pages")
        print("   to capture every registered player")
    if force_restart:
        print("   🔄 FORCE RESTART: Ignoring any previous progress")
    print("============================================================")
    
    scraper = APTAChicagoRosterScraper(force_restart=force_restart, target_series=target_series)
    
    try:
        scraper.scrape_all_series()
        
        # Check if scrape was complete
        if target_series:
            # For targeted scraping, check if all requested series were completed
            expected_series = set([f"Series {s}" for s in target_series])
            is_complete = scraper.completed_series == expected_series
            
            if is_complete:
                print(f"\n🌟 TARGETED SCRAPE COMPLETE!")
                print(f"   All requested series ({', '.join(target_series)}) successfully processed")
                scraper.save_results(is_final=True)
            else:
                missing_series = expected_series - scraper.completed_series
                print(f"\n⚠️ PARTIAL TARGETED SCRAPE COMPLETED")
                print(f"   Missing series: {', '.join(sorted(missing_series))}")
                scraper.save_results(is_final=False)
        else:
            # For comprehensive scraping, check all series
            expected_series = set([f"Series {i}" for i in range(1, 18)] + [f"Series {letter}" for letter in 'ABCDEFGHIJK'])
            is_complete = scraper.completed_series == expected_series
            
            if is_complete:
                print("\n🌟 COMPLETE SCRAPE DETECTED!")
                print("   All series (1-17 and A-K) successfully processed")
                scraper.save_results(is_final=True)
            else:
                missing_series = expected_series - scraper.completed_series
                print(f"\n⚠️ PARTIAL SCRAPE COMPLETED")
                print(f"   Missing series: {', '.join(sorted(missing_series))}")
                scraper.save_results(is_final=False)
        
        if target_series:
            print(f"\n🎉 TARGETED SCRAPING SESSION COMPLETED!")
            print(f"   Series {', '.join(target_series)} data saved and ready for database import")
        else:
            print("\n🎉 COMPREHENSIVE SCRAPING SESSION COMPLETED!")
            print("   All series data saved and ready for database import")
        
    except KeyboardInterrupt:
        print("\n⏸️ Scraping interrupted by user")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results(is_final=False)
            print("   You can resume by running the scraper again")
    except Exception as e:
        print(f"\n❌ Error during comprehensive scraping: {e}")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results(is_final=False)

if __name__ == "__main__":
    main()
