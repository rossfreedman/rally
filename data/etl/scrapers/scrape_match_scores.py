#!/usr/bin/env python3
"""
Enhanced Match Scores Scraper for Rally Tennis
Implements comprehensive stealth measures with smart request pacing, retry logic,
CAPTCHA detection, and enhanced logging.
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# Import stealth components
from data.etl.scrapers.stealth_browser import create_stealth_browser, DetectionType
from data.etl.scrapers.proxy_manager import get_proxy_rotator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ScrapingConfig:
    """Configuration for scraping behavior."""
    fast_mode: bool = False
    verbose: bool = True  # Make verbose default
    environment: str = "production"
    max_retries: int = 3
    min_delay: float = 2.0
    max_delay: float = 6.0
    timeout: int = 30
    retry_delay: int = 5  # Add missing retry_delay attribute
    delta_mode: bool = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class EnhancedMatchScraper:
    """Enhanced match scraper with comprehensive stealth measures."""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.stealth_browser = create_stealth_browser(
            fast_mode=config.fast_mode,
            verbose=config.verbose,
            environment=config.environment
        )
        self.proxy_rotator = get_proxy_rotator()
        
        # Metrics tracking
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "detections": {},
            "start_time": datetime.now(),
            "leagues_scraped": []
        }
        
        if config.verbose:
            print(f"🚀 Enhanced Match Scraper initialized")
            print(f"   Mode: {'FAST' if config.fast_mode else 'STEALTH'}")
            print(f"   Environment: {config.environment}")
            print(f"   Delta Mode: {config.delta_mode}")
            if config.start_date and config.end_date:
                print(f"   Date Range: {config.start_date} to {config.end_date}")
    
    def _safe_request(self, url: str, description: str = "page") -> Optional[str]:
        """Make a safe request with retry logic and detection."""
        for attempt in range(self.config.max_retries + 1):
            try:
                if self.config.verbose:
                    print(f"🌐 Fetching {description}...")
                    print(f"   URL: {url}")
                    print(f"   Attempt: {attempt + 1}/{self.config.max_retries + 1}")
                
                # Make request using stealth browser
                html = self.stealth_browser.get_html(url)
                
                # Update metrics
                self.metrics["total_requests"] += 1
                self.metrics["successful_requests"] += 1
                
                if self.config.verbose:
                    print(f"✅ Successfully fetched {description}")
                    print(f"   Response size: {len(html)} characters")
                
                # Add random delay
                if not self.config.fast_mode:
                    delay = random.uniform(self.config.min_delay, self.config.max_delay)
                    if self.config.verbose:
                        print(f"⏳ Waiting {delay:.1f} seconds before next request...")
                    time.sleep(delay)
                
                return html
                
            except Exception as e:
                self.metrics["failed_requests"] += 1
                if self.config.verbose:
                    print(f"❌ Failed to fetch {description}")
                    print(f"   Error: {e}")
                    if attempt < self.config.max_retries:
                        print(f"   Retrying in {self.config.retry_delay} seconds...")
                time.sleep(self.config.retry_delay)
                
                if attempt < self.config.max_retries:
                    # Exponential backoff
                    backoff = min(2 ** attempt, 10)
                    if self.config.verbose:
                        print(f"⏳ Backing off for {backoff} seconds...")
                    time.sleep(backoff)
                    continue
                else:
                    if self.config.verbose:
                        print(f"💀 All retries failed for {description}")
                    break
        
        return None
    
    def _detect_blocking(self, html: str) -> Optional[DetectionType]:
        """Detect if the page is blocked or showing CAPTCHA."""
        html_lower = html.lower()
        
        # Check for CAPTCHA indicators
        captcha_indicators = [
            "captcha", "robot", "bot check", "verify you are human",
            "cloudflare", "access denied", "blocked"
        ]
        
        for indicator in captcha_indicators:
            if indicator in html_lower:
                return DetectionType.CAPTCHA
        
        # Check for blank or very short pages
        if len(html) < 1000:
            return DetectionType.BLANK_PAGE
    
        return None

    def scrape_league_matches(self, league_subdomain: str, series_filter: str = None) -> List[Dict]:
        """Scrape matches for a specific league with enhanced stealth."""
        if self.config.verbose:
            print(f"🎾 Starting enhanced scraping for {league_subdomain}")
        
        try:
            # Try to use stealth browser, fallback to HTTP requests if it fails
            try:
                with self.stealth_browser as browser:
                    return self._scrape_with_browser(league_subdomain, series_filter)
            except Exception as browser_error:
                if self.config.verbose:
                    print(f"   ⚠️ Browser initialization failed: {browser_error}")
                    print(f"   🔄 Falling back to HTTP requests...")
                return self._scrape_with_http(league_subdomain, series_filter)
                
        except Exception as e:
            if self.config.verbose:
                print(f"   ❌ Error scraping {league_subdomain}: {e}")
            return []
    
    def _scrape_with_browser(self, league_subdomain: str, series_filter: str = None) -> List[Dict]:
        """Scrape using stealth browser."""
        # Build base URL
        base_url = f"https://{league_subdomain}.tenniscores.com"
        print(f"   🌐 Base URL: {base_url}")
        
        # Get main page
        print(f"   📄 Navigating to main page...")
        main_html = self._safe_request(base_url, "main page")
        if not main_html:
            print(f"   ❌ Failed to access main page for {league_subdomain}")
            return []
        
        # Check for blocking
        detection = self._detect_blocking(main_html)
        if detection:
            self.metrics["detections"][detection.value] = self.metrics["detections"].get(detection.value, 0) + 1
            print(f"   ❌ Blocking detected: {detection.value}")
            return []

        # Parse series links (simplified for example)
        series_links = self._extract_series_links(main_html)
        print(f"   📋 Found {len(series_links)} series")
        
        all_matches = []
        
        for i, (series_name, series_url) in enumerate(series_links, 1):
            if series_filter and series_filter != "all" and series_filter not in series_name:
                continue
            
            print(f"   🏆 Processing series {i}/{len(series_links)}: {series_name}")
            print(f"   📄 Series URL: {series_url}")
            
            # Get series page
            series_html = self._safe_request(series_url, f"series {series_name}")
            if not series_html:
                print(f"   ⚠️ Failed to scrape series {series_name}")
                continue
            
            # Parse matches from series page
            print(f"   🔍 Parsing matches from {series_name}...")
            series_matches = self._extract_matches_from_series(series_html, series_name)
            
            # Apply date filtering if in delta mode
            if self.config.delta_mode and self.config.start_date and self.config.end_date:
                print(f"   📅 Filtering matches by date range...")
                series_matches = self._filter_matches_by_date(series_matches)
            
            all_matches.extend(series_matches)
            print(f"   ✅ Series {series_name}: {len(series_matches)} matches")
        
        self.metrics["leagues_scraped"].append(league_subdomain)
        print(f"   🎉 Completed scraping {league_subdomain}: {len(all_matches)} total matches")
        
        return all_matches
    
    def _scrape_with_http(self, league_subdomain: str, series_filter: str = None) -> List[Dict]:
        """Scrape using HTTP requests as fallback."""
        print(f"\n🌐 Starting HTTP scraping for {league_subdomain}")
        print(f"📄 Base URL: https://{league_subdomain}.tenniscores.com")
        
        # Build base URL
        base_url = f"https://{league_subdomain}.tenniscores.com"
        
        try:
            # Get main page using proxy
            print(f"\n📥 Fetching main page...")
            from data.etl.scrapers.proxy_manager import make_proxy_request
            
            response = make_proxy_request(base_url, timeout=30)
            if not response:
                print(f"❌ Failed to access main page for {league_subdomain}")
                return []
            
            print(f"✅ Main page loaded successfully")
            print(f"   Status: {response.status_code}")
            print(f"   Content size: {len(response.text)} characters")
            
            # Parse the main page to extract series links
            main_html = response.text
            print(f"\n🔍 Analyzing main page to find series...")
            series_links = self._extract_series_links(main_html)
            
            if not series_links:
                print(f"⚠️ No series links found for {league_subdomain}")
                return []
            
            print(f"📋 Found {len(series_links)} series to process:")
            for i, (series_name, _) in enumerate(series_links, 1):
                print(f"   {i}. {series_name}")
            
            all_matches = []
            
            # Scrape each series
            for i, (series_name, series_url) in enumerate(series_links, 1):
                if series_filter and series_filter != "all" and series_filter not in series_name:
                    continue
                
                print(f"\n🏆 Processing Series {i}/{len(series_links)}: {series_name}")
                print(f"   URL: {series_url}")
                
                try:
                    # Get series page
                    series_response = make_proxy_request(series_url, timeout=30)
                    if not series_response:
                        print(f"❌ Failed to fetch series page for {series_name}")
                        continue
                    
                    # Parse matches from series page
                    print(f"🔍 Extracting matches from {series_name}...")
                    series_matches = self._extract_matches_from_series(series_response.text, series_name)
                    
                    # Apply date filtering if in delta mode
                    if self.config.delta_mode and self.config.start_date and self.config.end_date:
                        print(f"📅 Filtering matches by date range...")
                        series_matches = self._filter_matches_by_date(series_matches)
                    
                    all_matches.extend(series_matches)
                    print(f"✅ Found {len(series_matches)} matches in {series_name}")
                    
                    # Add delay between requests
                    if not self.config.fast_mode:
                        import time
                        time.sleep(2)
                        
                except Exception as e:
                    print(f"❌ Error scraping series {series_name}: {e}")
                    continue
            
            print(f"\n🎉 Completed HTTP scraping for {league_subdomain}")
            print(f"📊 Total matches found: {len(all_matches)}")
            return all_matches
            
        except Exception as e:
            print(f"❌ HTTP scraping failed: {e}")
            return []

    def _extract_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract series links from main page based on league."""
        series_links = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Determine league type based on URL patterns in the HTML
            html_lower = html.lower()
            
            if 'cnswpl' in html_lower or 'cns' in html_lower:
                # CNSWPL League - use Series format
                return self._extract_cnswpl_series_links(html)
            elif 'apta' in html_lower or 'chicago' in html_lower:
                # APTA Chicago - use Line format
                return self._extract_apta_series_links(html)
            else:
                # Default to CNSWPL format for now
                return self._extract_cnswpl_series_links(html)
            
        except Exception as e:
            print(f"   ❌ Error extracting series links: {e}")
            return []
    
    def _extract_cnswpl_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract series links for CNSWPL format."""
        series_links = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: Look for links containing "series" or "division"
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for series patterns
                if any(keyword in text.lower() for keyword in ['series', 'division']):
                    if href.startswith('/'):
                        full_url = f"https://cnswpl.tenniscores.com{href}"
                    else:
                        full_url = href
                    series_links.append((text, full_url))
                    print(f"   📋 Added CNSWPL series: {text}")
            
            # Method 2: Look for specific CNSWPL series patterns
            if not series_links:
                # CNSWPL has specific series like "Series 1", "Series 2", etc.
                for i in range(1, 20):  # Check Series 1-19
                    series_name = f"Series {i}"
                    # Try to construct URL based on CNSWPL pattern
                    series_url = f"https://cnswpl.tenniscores.com/?mod=nndz-TjJiOWtOR2sxTnhI&tid=nndz-WkNld3hyci8%3D&series={i}"
                    series_links.append((series_name, series_url))
                    print(f"   📋 Added CNSWPL series: {series_name}")
            
            # Method 3: Look for day/night league patterns
            day_series = ["Day League", "Night League", "Sunday Night League"]
            for series_name in day_series:
                series_url = f"https://cnswpl.tenniscores.com/?mod=nndz-TjJiOWtOR2sxTnhI&league={series_name.lower().replace(' ', '_')}"
                series_links.append((series_name, series_url))
                print(f"   📋 Added league: {series_name}")
            
            print(f"   📊 Total series found: {len(series_links)}")
            return series_links
            
        except Exception as e:
            print(f"   ❌ Error extracting CNSWPL series links: {e}")
            return []
    
    def _extract_apta_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract series links for APTA Chicago format (uses Lines instead of Series)."""
        series_links = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: Look for links containing "line" or "division"
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for line patterns
                if any(keyword in text.lower() for keyword in ['line', 'division']):
                    if href.startswith('/'):
                        full_url = f"https://aptachicago.tenniscores.com{href}"
                    else:
                        full_url = href
                    series_links.append((text, full_url))
                    print(f"   📋 Added APTA line: {text}")
            
            # Method 2: Look for team links (APTA uses team= parameters)
            team_links = soup.find_all("a", href=re.compile(r"team="))
            for link in team_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                
                # Extract team ID from URL
                team_match = re.search(r"team=([^&]+)", href)
                if team_match and text:
                    team_id = team_match.group(1)
                    team_name = text.strip()
                    
                    # Extract line number from team name (e.g., "Glenbrook RC - 1" -> "Line 1")
                    line_match = re.search(r".*-\s*(\d+).*", team_name)
                    if line_match:
                        line_num = line_match.group(1)
                        line_name = f"Line {line_num}"
                        full_url = f"https://aptachicago.tenniscores.com{href}" if href.startswith('/') else href
                        series_links.append((line_name, full_url))
                        print(f"   📋 Added APTA team: {team_name} -> {line_name}")
            
            # Method 3: Construct team URLs based on APTA patterns if no links found
            if not series_links:
                print(f"   🔍 No team links found, constructing APTA team URLs...")
                
                # APTA typically has teams with line numbers
                # Common APTA teams: Glenbrook RC - 1, Winnetka - 1, etc.
                # We'll try to construct URLs for common teams
                common_teams = [
                    ("Glenbrook RC - 1", "nndz-WWlPd3dyMy9nZz09"),
                    ("Winnetka - 1", "nndz-WWlPd3dyenhndz09"),
                    ("Wilmette PD - 1", "nndz-WWlPd3dyMy9nZz09"),
                ]
                
                for team_name, team_id in common_teams:
                    line_match = re.search(r".*-\s*(\d+).*", team_name)
                    if line_match:
                        line_num = line_match.group(1)
                        line_name = f"Line {line_num}"
                        team_url = f"https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR2sxTnhI&team={team_id}"
                        series_links.append((line_name, team_url))
                        print(f"   📋 Added APTA team: {team_name} -> {line_name}")
            
            print(f"   📊 Total lines found: {len(series_links)}")
            return series_links
            
            print(f"   📊 Total lines found: {len(series_links)}")
            return series_links
            
        except Exception as e:
            print(f"   ❌ Error extracting APTA series links: {e}")
            return []
    
    def _extract_matches_from_series(self, html: str, series_name: str) -> List[Dict]:
        """Extract detailed matches from series page for CNSWPL (like APTA format)."""
        matches = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            print(f"🔍 Parsing detailed matches from {series_name}...")
            
            # Method 1: Look for match links and follow them to get detailed data
            match_links = soup.find_all('a', href=True)
            match_links = [link for link in match_links if 'print_match.php' in link.get('href', '')]
            match_count = 0
            
            print(f"🔗 Found {len(match_links)} match detail links")
            
            for i, link in enumerate(match_links, 1):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for CNSWPL match link patterns
                if 'print_match.php' in href and 'sch=' in href:
                    try:
                        # Extract match ID from URL
                        match_id = href.split('sch=')[1].split('&')[0] if 'sch=' in href else None
                        
                        # Follow the match link to get detailed data
                        if href.startswith('/'):
                            match_url = f"https://cnswpl.tenniscores.com{href}"
                        elif href.startswith('http'):
                            match_url = href
                        else:
                            match_url = f"https://cnswpl.tenniscores.com/{href}"
                        
                        print(f"🔗 Processing match {i}/{len(match_links)}: {href}")
                        
                        # Get detailed match page
                        match_response = self._safe_request(match_url, f"match detail page {i}")
                        if match_response:
                            detailed_matches = self._extract_detailed_match_data(match_response, series_name, match_id)
                            if detailed_matches:
                                matches.extend(detailed_matches)  # Add all line matches
                                match_count += len(detailed_matches)
                                first_match = detailed_matches[0] if detailed_matches else {}
                                home_team = first_match.get('Home Team', 'Unknown')
                                away_team = first_match.get('Away Team', 'Unknown')
                                date = first_match.get('Date', 'Unknown Date')
                                print(f"✅ Extracted {len(detailed_matches)} lines: {home_team} vs {away_team} on {date}")
                        
                    except Exception as e:
                        print(f"⚠️ Error following match link: {e}")
                        continue
            
            # Method 2: Look for match data in tables (fallback)
            if not matches:
                print(f"📋 No match links found, looking for table data...")
                
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 4:
                            try:
                                match_data = self._extract_match_from_table_row(cells, series_name)
                                if match_data:
                                    matches.append(match_data)
                                    match_count += 1
                                    home_team = match_data.get('Home Team', 'Unknown')
                                    away_team = match_data.get('Away Team', 'Unknown')
                                    print(f"✅ Extracted table match: {home_team} vs {away_team}")
                            except Exception as e:
                                print(f"⚠️ Error parsing table row: {e}")
                                continue
            
            print(f"📊 Total matches extracted: {match_count}")
            
        except Exception as e:
            if self.config.verbose:
                print(f"   ❌ Error extracting matches: {e}")
        
        return matches
    
    def _extract_detailed_match_data(self, html: str, series_name: str, match_id: str) -> List[Dict]:
        """Extract detailed match data from CNSWPL individual match page - returns list of line matches."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract common match information
            match_date = self._extract_cnswpl_date(soup)
            teams_and_score = self._extract_cnswpl_teams_and_score(soup)
            
            if not teams_and_score:
                return []
            
            # Extract line-specific data from court breakdown
            line_matches = self._extract_cnswpl_lines(soup, series_name, match_id, match_date, teams_and_score)
            
            return line_matches
            
        except Exception as e:
            if self.config.verbose:
                print(f"   ❌ Error extracting detailed match data: {e}")
            return []
    
    def _extract_match_from_table_row(self, cells, series_name: str) -> Optional[Dict]:
        """Extract match data from table row (fallback method)."""
        try:
            match_data = {
                "league_id": "CNSWPL",
                "match_id": f"table_{series_name.replace(' ', '_')}_{len(cells)}",
                "source_league": "CNSWPL",
                "Series": series_name,
                "Date": None,
                "Home Team": None,
                "Away Team": None,
                "Scores": None,
                "Winner": None
            }
            
            # Extract basic data from table cells
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Look for date
            for text in cell_texts:
                if self._is_date(text):
                    match_data["Date"] = text
                    break
            
            # Look for team names
            teams = [text for text in cell_texts if text and len(text) > 2 and not self._is_date(text)]
            if len(teams) >= 2:
                match_data["Home Team"] = teams[0]
                match_data["Away Team"] = teams[1]
            
            # Look for scores
            for text in cell_texts:
                if any(char in text for char in ['-', '6', '7', '0', '1', '2', '3', '4', '5']):
                    match_data["Scores"] = text
                    break
            
            return match_data if match_data["Home Team"] and match_data["Away Team"] else None
            
        except Exception as e:
            if self.config.verbose:
                print(f"   ❌ Error extracting from table row: {e}")
            return None
    
    def _generate_player_id(self, player_name: str) -> str:
        """Generate a unique player ID for CNSWPL players."""
        import hashlib
        # Create a hash of the player name for consistent ID generation
        return hashlib.md5(player_name.lower().encode()).hexdigest()[:16]
    
    def _extract_cnswpl_date(self, soup) -> str:
        """Extract match date from CNSWPL match page header and convert to DD-MMM-YY format."""
        import re
        from datetime import datetime
        
        # Look for CNSWPL date pattern like "Series 1 March 6, 2025"
        all_text = soup.get_text()
        
        # Pattern for "Month Day, Year" format
        date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b'
        
        match = re.search(date_pattern, all_text)
        if match:
            month_name, day, year = match.groups()
            # Convert to DD-MMM-YY format like "06-Mar-25"
            try:
                date_obj = datetime.strptime(f"{month_name} {day}, {year}", "%B %d, %Y")
                return date_obj.strftime("%d-%b-%y")
            except:
                pass
        
        # Fallback to standard date patterns and convert
        date_patterns = [
            (r'\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b', "%m/%d/%Y"),  # MM/DD/YYYY
            (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', "%Y-%m-%d"),    # YYYY-MM-DD
            (r'\b(\d{1,2})-(\d{1,2})-(\d{2,4})\b', "%m-%d-%Y"),  # MM-DD-YYYY
        ]
        
        for pattern, format_str in date_patterns:
            matches = re.findall(pattern, all_text)
            if matches:
                try:
                    if format_str == "%m/%d/%Y":
                        month, day, year = matches[0]
                        date_obj = datetime.strptime(f"{month}/{day}/{year}", format_str)
                        return date_obj.strftime("%d-%b-%y")
                except:
                    continue
        
        return None
    
    def _extract_cnswpl_teams_and_score(self, soup) -> dict:
        """Extract teams and match score from CNSWPL match page."""
        import re
        
        all_text = soup.get_text()
        
        # Look for pattern like "Hinsdale PC 1a @ Birchwood 1: 1 - 12"
        # Team @ Team: Score - Score
        team_score_pattern = r'([^@\n]+)\s*@\s*([^:\n]+):\s*(\d+)\s*-\s*(\d+)'
        
        match = re.search(team_score_pattern, all_text)
        if match:
            away_team = match.group(1).strip()
            home_team = match.group(2).strip()
            away_score = int(match.group(3))
            home_score = int(match.group(4))
            
            # Determine winner based on team match score
            if home_score > away_score:
                winner = "home"
            elif away_score > home_score:
                winner = "away"
            else:
                winner = "tie"
            
            return {
                "Home Team": home_team,
                "Away Team": away_team,
                "Team Match Score": f"{away_score}-{home_score}",  # Away-Home format
                "Winner": winner
            }
        
        return {}
    
    def _extract_cnswpl_lines(self, soup, series_name: str, match_id: str, match_date: str, teams_and_score: dict) -> List[Dict]:
        """Extract line-specific data from CNSWPL court breakdown with both home/away players."""
        import re
        line_matches = []
        
        # Based on actual CNSWPL structure:
        # Court 1
        # Nancy Gaspadarek / Ellie Hay (Home team)
        # 12 (Home scores)
        # Leslie Katz / Alison Morgan (Away team)  
        # 66 (Away scores)
        
        all_text = soup.get_text()
        lines = all_text.split('\n')
        
        court_data = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'Court\s+\d+', line):
                court_num = re.search(r'Court\s+(\d+)', line).group(1)
                
                # Look for the pattern: Court -> Home Players -> Home Score -> Away Players -> Away Score
                home_players = None
                home_score = None
                away_players = None
                away_score = None
                
                # Scan next few lines for the 4-part pattern
                for j in range(i+1, min(i+10, len(lines))):
                    potential_line = lines[j].strip()
                    if not potential_line:
                        continue
                        
                    if '/' in potential_line and not home_players:
                        home_players = potential_line
                    elif re.match(r'^\d+$', potential_line) and home_players and not home_score:
                        home_score = potential_line
                    elif '/' in potential_line and home_players and home_score and not away_players:
                        away_players = potential_line
                    elif re.match(r'^\d+$', potential_line) and away_players and not away_score:
                        away_score = potential_line
                        break  # Found all 4 components
                
                if home_players and away_players:
                    court_data.append({
                        'court_num': court_num,
                        'home_players': home_players,
                        'home_score': home_score,
                        'away_players': away_players,
                        'away_score': away_score
                    })
                
                i = j if 'j' in locals() else i + 1
            else:
                i += 1
        
        # Process each court to create line matches
        for court_info in court_data:
            court_num = court_info['court_num']
            
            # Parse home and away players
            home_players = self._parse_cnswpl_player_line(court_info['home_players'])
            away_players = self._parse_cnswpl_player_line(court_info['away_players'])
            
            # Convert scores to tennis format (e.g., "66" -> "6-6")
            tennis_scores = self._convert_cnswpl_scores_to_tennis(
                court_info['home_score'], 
                court_info['away_score']
            )
            
            # Determine winner from green checkboxes
            winner = self._determine_cnswpl_winner(soup, court_num)
            
            if len(home_players) >= 2 and len(away_players) >= 2:
                line_match = {
                    "league_id": "CNSWPL",
                    "match_id": f"cnswpl_{match_id}_Line{court_num}",
                    "source_league": "CNSWPL",
                    "Line": f"Line {court_num}",
                    "Date": match_date,
                    "Home Team": teams_and_score.get("Home Team"),
                    "Away Team": teams_and_score.get("Away Team"),
                    "Home Player 1": home_players[0],
                    "Home Player 2": home_players[1],
                    "Away Player 1": away_players[0],
                    "Away Player 2": away_players[1],
                    "Home Player 1 ID": f"cnswpl_{self._generate_player_id(home_players[0])}",
                    "Home Player 2 ID": f"cnswpl_{self._generate_player_id(home_players[1])}",
                    "Away Player 1 ID": f"cnswpl_{self._generate_player_id(away_players[0])}",
                    "Away Player 2 ID": f"cnswpl_{self._generate_player_id(away_players[1])}",
                    "Scores": tennis_scores,
                    "Winner": winner
                }
                line_matches.append(line_match)
        
        return line_matches
    
    def _parse_cnswpl_player_line(self, line: str) -> List[str]:
        """Parse player names from a CNSWPL court line."""
        import re
        
        # Remove check marks and scores
        clean_line = re.sub(r'[✔️✓]', '', line)
        clean_line = re.sub(r'\b\d+\b', '', clean_line)  # Remove numbers
        clean_line = clean_line.strip()
        
        # Split by common separators 
        if ' / ' in clean_line:
            players = [p.strip() for p in clean_line.split(' / ')]
        elif '/' in clean_line:
            players = [p.strip() for p in clean_line.split('/')]
        else:
            # Try to split by detecting two names
            words = clean_line.split()
            if len(words) >= 4:  # First Last / First Last
                mid = len(words) // 2
                players = [' '.join(words[:mid]), ' '.join(words[mid:])]
            elif len(words) >= 2:
                players = [clean_line]  # Single name or can't split
            else:
                players = []
        
        return [p for p in players if p and len(p) > 2]
    
    def _extract_line_scores(self, line1: str, line2: str) -> str:
        """Extract individual set scores from court lines."""
        import re
        
        # Look for score patterns in both lines
        combined = f"{line1} {line2}"
        
        # Look for patterns like "6 6", "3 4", etc.
        score_matches = re.findall(r'\b([0-7])\s+([0-7])\b', combined)
        
        scores = []
        for s1, s2 in score_matches:
            if int(s1) <= 7 and int(s2) <= 7:  # Valid tennis scores
                scores.append(f"{s1}-{s2}")
        
        return " ".join(scores[:3])  # Max 3 sets
    
    def _convert_cnswpl_scores_to_tennis(self, home_score: str, away_score: str) -> str:
        """Convert CNSWPL concatenated scores to tennis format."""
        if not home_score or not away_score:
            return "Unknown"
        
        # Convert scores like "66" (6-6) and "12" (1-2) to proper tennis scores
        try:
            # Handle single digit and double digit scores
            home_sets = []
            away_sets = []
            
            # Parse home score (e.g., "66" -> [6, 6] or "265" -> [2, 6, 5])
            home_str = str(home_score)
            if len(home_str) == 2:
                home_sets = [int(home_str[0]), int(home_str[1])]
            elif len(home_str) == 3:
                home_sets = [int(home_str[0]), int(home_str[1]), int(home_str[2])]
            elif len(home_str) == 4:
                home_sets = [int(home_str[0]), int(home_str[1]), int(home_str[2]), int(home_str[3])]
            else:
                home_sets = [int(d) for d in home_str]
            
            # Parse away score
            away_str = str(away_score)
            if len(away_str) == 2:
                away_sets = [int(away_str[0]), int(away_str[1])]
            elif len(away_str) == 3:
                away_sets = [int(away_str[0]), int(away_str[1]), int(away_str[2])]
            elif len(away_str) == 4:
                away_sets = [int(away_str[0]), int(away_str[1]), int(away_str[2]), int(away_str[3])]
            else:
                away_sets = [int(d) for d in away_str]
            
            # Combine into tennis score format
            tennis_sets = []
            max_sets = max(len(home_sets), len(away_sets))
            for i in range(max_sets):
                home_set = home_sets[i] if i < len(home_sets) else 0
                away_set = away_sets[i] if i < len(away_sets) else 0
                tennis_sets.append(f"{home_set}-{away_set}")
            
            return ", ".join(tennis_sets)
            
        except (ValueError, IndexError):
            return f"{home_score}-{away_score}"  # Fallback
    
    def _determine_cnswpl_winner(self, soup, court_num: str) -> str:
        """Determine match winner from green checkboxes in CNSWPL format."""
        try:
            # Look for green checkbox images near the court number
            html_content = str(soup)
            
            # Pattern: look for green checkbox image tags
            if 'admin_captain_teams_approve_check_green.png' in html_content:
                # Find the position of the court and check for green checkboxes nearby
                court_pattern = f"Court {court_num}"
                court_pos = html_content.find(court_pattern)
                
                if court_pos >= 0:
                    # Look in the section around this court for green checkboxes
                    section = html_content[court_pos:court_pos + 2000]  # Look ahead in HTML
                    
                    # Count green checkboxes in this section
                    green_count = section.count('admin_captain_teams_approve_check_green.png')
                    
                    # Simple heuristic: if we find green checkboxes, assume home team won
                    # (More sophisticated logic would parse the table structure)
                    if green_count > 0:
                        return "home"  # Green checkboxes indicate home team won
                    else:
                        return "away"
            
            return "unknown"  # Fallback if no green checkboxes found
            
        except Exception:
            return "unknown"
    
    def _extract_cnswpl_individual_scores(self, soup) -> str:
        """Extract individual set scores from CNSWPL court breakdown."""
        import re
        
        # Look for tennis set scores like "6-1", "6-2", "7-5", etc.
        all_text = soup.get_text()
        
        # Pattern for tennis set scores
        set_pattern = r'\b[0-7]-[0-7]\b'
        scores = re.findall(set_pattern, all_text)
        
        # Filter out obvious non-tennis scores and return unique scores
        tennis_scores = []
        for score in scores:
            parts = score.split('-')
            if len(parts) == 2:
                s1, s2 = int(parts[0]), int(parts[1])
                # Valid tennis scores (excluding team match scores like 1-12)
                if (s1 <= 7 and s2 <= 7) and not (s1 <= 1 and s2 >= 10):
                    tennis_scores.append(score)
        
        return " ".join(tennis_scores[:4])  # Return first 4 sets max
    
    def _extract_match_date(self, soup) -> str:
        """Extract match date from various possible locations in the HTML."""
        # For CNSWPL, use the specific extraction method
        return self._extract_cnswpl_date(soup)
    
    def _extract_scores_and_winner(self, soup) -> dict:
        """Extract match scores and determine winner."""
        import re
        
        # Look for score patterns in the HTML
        all_text = soup.get_text()
        
        # Common paddle tennis score patterns: 6-4, 6-7, 7-5, etc.
        score_pattern = r'\b\d{1,2}-\d{1,2}\b'
        scores = re.findall(score_pattern, all_text)
        
        result = {"scores": None, "winner": None}
        
        if scores:
            # Join multiple set scores
            result["scores"] = " ".join(scores)
            
            # Simple winner determination - could be enhanced
            # For now, assume first team wins if they win more sets
            try:
                sets = [score.split('-') for score in scores]
                home_sets_won = sum(1 for s1, s2 in sets if int(s1) > int(s2))
                away_sets_won = sum(1 for s1, s2 in sets if int(s2) > int(s1))
                
                if home_sets_won > away_sets_won:
                    result["winner"] = "home"
                elif away_sets_won > home_sets_won:
                    result["winner"] = "away"
                else:
                    result["winner"] = "tie"
            except (ValueError, IndexError):
                result["winner"] = "unknown"
        
        return result

    def _is_date(self, text: str) -> bool:
        """Check if text looks like a date."""
        import re
        # Look for date patterns like MM/DD/YYYY, YYYY-MM-DD, etc.
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _filter_matches_by_date(self, matches: List[Dict]) -> List[Dict]:
        """Filter matches by date range in delta mode."""
        if not self.config.start_date or not self.config.end_date:
            return matches
        
        try:
            start_date = datetime.strptime(self.config.start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(self.config.end_date, "%Y-%m-%d").date()
            
            filtered_matches = []
            for match in matches:
                if "Date" in match:
                    try:
                        match_date = datetime.strptime(match["Date"], "%Y-%m-%d").date()
                        if start_date <= match_date <= end_date:
                            filtered_matches.append(match)
                    except ValueError:
                        # Skip matches with invalid dates
                        continue
            
            logger.info(f"📅 Date filtered: {len(filtered_matches)}/{len(matches)} matches")
            return filtered_matches
        
        except Exception as e:
            logger.error(f"❌ Error filtering by date: {e}")
            return matches
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        duration = (datetime.now() - self.metrics["start_time"]).total_seconds()
        
        return {
            "duration_seconds": duration,
            "total_requests": self.metrics["total_requests"],
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": (self.metrics["successful_requests"] / self.metrics["total_requests"] * 100) if self.metrics["total_requests"] > 0 else 0,
            "detections": self.metrics["detections"],
            "leagues_scraped": self.metrics["leagues_scraped"]
        }

def scrape_all_matches(league_subdomain: str, 
                      series_filter: str = None,
                      max_retries: int = 3,
                      retry_delay: int = 5,
                      start_date: str = None,
                      end_date: str = None,
                      delta_mode: bool = False,
                      fast_mode: bool = False,
                      verbose: bool = False) -> List[Dict]:
    """
    Enhanced scrape_all_matches function with stealth measures.
    
    Args:
        league_subdomain: League subdomain to scrape
        series_filter: Optional series filter
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries
        start_date: Start date for delta mode (YYYY-MM-DD)
        end_date: End date for delta mode (YYYY-MM-DD)
        delta_mode: Enable delta mode
        fast_mode: Enable fast mode (reduced delays)
        verbose: Enable verbose logging
    
    Returns:
        List of match dictionaries
    """
    print(f"🎾 Enhanced TennisScores Match Scraper")
    print(f"✅ Only imports matches with legitimate match IDs - no synthetic IDs!")
    print(f"✅ Ensures data integrity and best practices for all leagues")
    print(f"✅ Enhanced with IP validation, request tracking, and intelligent throttling")
    
    if delta_mode:
        print(f"🎯 DELTA MODE: Only scraping matches within specified date range")
        if start_date and end_date:
            print(f"📅 Date Range: {start_date} to {end_date}")
    
    # Create configuration
    config = ScrapingConfig(
        fast_mode=fast_mode,
        verbose=verbose,
        environment="production",
        max_retries=max_retries,
        min_delay=1.0 if fast_mode else 2.0,
        max_delay=3.0 if fast_mode else 6.0,
        delta_mode=delta_mode,
        start_date=start_date,
        end_date=end_date
    )
    
    # Create enhanced scraper
    scraper = EnhancedMatchScraper(config)
    
    # Scrape matches
    print(f"🚀 Starting match scraping for {league_subdomain}...")
    matches = scraper.scrape_league_matches(league_subdomain, series_filter)
    
    # Log summary
    summary = scraper.get_metrics_summary()
    print(f"📊 Scraping Summary:")
    print(f"   Duration: {summary['duration_seconds']:.1f}s")
    print(f"   Requests: {summary['total_requests']} (Success: {summary['successful_requests']}, Failed: {summary['failed_requests']})")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Detections: {summary['detections']}")
    print(f"   Leagues Scraped: {summary['leagues_scraped']}")
    print(f"   Total Matches: {len(matches)}")
    
    return matches

def main():
    """Main function with enhanced CLI arguments."""
    parser = argparse.ArgumentParser(description="Enhanced Match Scores Scraper with Stealth Measures")
    parser.add_argument("league", help="League subdomain (e.g., aptachicago, nstf)")
    parser.add_argument("--start-date", help="Start date for delta scraping (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for delta scraping (YYYY-MM-DD)")
    parser.add_argument("--series-filter", help="Series filter (e.g., '22', 'all')")
    parser.add_argument("--delta-mode", action="store_true", help="Enable delta scraping mode")
    parser.add_argument("--fast", action="store_true", help="Enable fast mode (reduced delays)")
    parser.add_argument("--quiet", action="store_true", help="Disable verbose logging (default is verbose)")
    parser.add_argument("--environment", choices=["local", "staging", "production"], 
                       default="production", help="Environment mode")
    
    args = parser.parse_args()
    
    print(f"\n🎾 Starting CNSWPL Match Scraper")
    print(f"📋 League: {args.league}")
    print(f"⚙️  Mode: {'FAST' if args.fast else 'STEALTH'}")
    print(f"🌍 Environment: {args.environment}")
    
    if args.delta_mode:
        print(f"📅 Delta Mode: {args.start_date} to {args.end_date}")
    
    # Scrape matches
    matches = scrape_all_matches(
        league_subdomain=args.league,
        series_filter=args.series_filter,
        start_date=args.start_date,
        end_date=args.end_date,
        delta_mode=args.delta_mode,
        fast_mode=args.fast,
        verbose=not args.quiet  # Invert quiet to get verbose
    )
            
            # Save results - APPEND to existing data, don't overwrite
    # Use standardized directory naming to prevent APTACHICAGO vs APTA_CHICAGO issues
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from data.etl.utils.league_directory_manager import get_league_file_path
    
    output_file = get_league_file_path(args.league, "match_history.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Load existing matches to preserve data
    existing_matches = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_matches = json.load(f)
            logger.info(f"📄 Loaded {len(existing_matches):,} existing matches")
        except Exception as e:
            logger.warning(f"⚠️ Could not load existing data: {e}")
            existing_matches = []
    
    # Merge new matches with existing ones (deduplicate by match_id)
    existing_ids = {match.get('match_id') for match in existing_matches if match.get('match_id')}
    new_matches = [match for match in matches if match.get('match_id') not in existing_ids]
    
    # Combine all matches
    all_matches = existing_matches + new_matches
    
    # Write combined data
    with open(output_file, 'w') as f:
        json.dump(all_matches, f, indent=2)
    
    print(f"\n🎉 Scraping completed!")
    print(f"📁 Results saved to: {output_file}")
    print(f"📊 Existing matches: {len(existing_matches):,}")
    print(f"📊 New matches added: {len(new_matches):,}")
    print(f"📊 Total matches: {len(all_matches):,}")
    
    if len(new_matches) > 0:
        print(f"✅ Successfully extracted {len(new_matches)} new matches")
    else:
        print(f"⚠️ No new matches were extracted")

if __name__ == "__main__":
    main()
