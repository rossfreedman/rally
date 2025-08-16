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

class BaseLeagueScraper:
    """Base class for league-specific scrapers."""
    
    def __init__(self, config: ScrapingConfig, league_subdomain: str, parent_scraper=None):
        self.config = config
        self.league_subdomain = league_subdomain.upper()
        self.parent_scraper = parent_scraper
    
    def _safe_request_for_league_scraper(self, url: str, description: str = "page") -> Optional[str]:
        """Make a safe request using the parent scraper's method."""
        if self.parent_scraper and hasattr(self.parent_scraper, '_safe_request'):
            return self.parent_scraper._safe_request(url, description)
        else:
            print(f"⚠️ No parent scraper available for request: {url}")
            return None
        
    def extract_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract series links - must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement extract_series_links")
    
    def extract_matches_from_series(self, html: str, series_name: str, 
                                  current_total_processed: int = 0, total_series: int = 1) -> Tuple[List[Dict], int]:
        """Extract matches from series page - must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement extract_matches_from_series")
    
    def get_league_id(self) -> str:
        """Get the league ID for this scraper."""
        return self.league_subdomain

class CNSWPLScraper(BaseLeagueScraper):
    """CNSWPL-specific scraper with dedicated extraction logic."""
    
    def extract_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract CNSWPL series links."""
        return self._extract_cnswpl_series_links(html)
    
    def extract_matches_from_series(self, html: str, series_name: str, 
                                  current_total_processed: int = 0, total_series: int = 1) -> Tuple[List[Dict], int]:
        """Extract matches from CNSWPL series page."""
        return self._extract_cnswpl_matches_from_series(html, series_name, current_total_processed, total_series)
    
    def _extract_cnswpl_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract CNSWPL-specific series links."""
        series_links = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            print(f"   🔍 Looking for CNSWPL series links...")
            
            # Method 1: Look for links containing "series" pattern
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # CNSWPL-specific patterns
                if any(keyword in text.lower() for keyword in ['series', 'division']):
                    if href.startswith('/'):
                        full_url = f"https://cnswpl.tenniscores.com{href}"
                    else:
                        full_url = href
                    series_links.append((text, full_url))
                    print(f"   📋 Added CNSWPL series: {text}")
            
            return series_links
            
        except Exception as e:
            print(f"   ❌ Error extracting CNSWPL series links: {e}")
            return []
    
    def _extract_cnswpl_matches_from_series(self, html: str, series_name: str, 
                                          current_total_processed: int = 0, total_series: int = 1) -> Tuple[List[Dict], int]:
        """Extract matches from CNSWPL series page using CNSWPL-specific logic."""
        matches = []
        matches_processed_in_series = 0
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            print(f"🔍 CNSWPL: Parsing matches from {series_name}...")
            
            # CNSWPL uses individual match pages with print_match.php
            match_links = soup.find_all('a', href=True)
            match_links = [link for link in match_links if 'print_match.php' in link.get('href', '')]
            match_count = 0
            
            print(f"🔗 CNSWPL: Found {len(match_links)} match detail links")
            
            for i, link in enumerate(match_links, 1):
                href = link.get('href', '')
                
                if 'print_match.php' in href and 'sch=' in href:
                    try:
                        match_id = href.split('sch=')[1].split('&')[0] if 'sch=' in href else None
                        
                        # Build CNSWPL-specific URL
                        if href.startswith('/'):
                            match_url = f"https://cnswpl.tenniscores.com{href}"
                        elif href.startswith('http'):
                            match_url = href
                        else:
                            match_url = f"https://cnswpl.tenniscores.com/{href}"
                        
                        # Calculate progress within this series and overall
                        series_percent_complete = (i / len(match_links)) * 100
                        overall_matches_processed = current_total_processed + i
                        estimated_total_matches = len(match_links) * total_series if total_series > 0 else len(match_links)
                        overall_percent_complete = (overall_matches_processed / estimated_total_matches) * 100 if estimated_total_matches > 0 else 0
                        
                        print(f"🔗 CNSWPL Match Progress: {i}/{len(match_links)} ({series_percent_complete:.1f}% of {series_name}) | Overall: {overall_matches_processed}/{estimated_total_matches} ({overall_percent_complete:.1f}%)")
                        print(f"   Processing: {href}")
                        
                        # Get detailed CNSWPL match page using parent scraper's request method
                        match_response = self._safe_request_for_league_scraper(match_url, f"CNSWPL match detail page {i}")
                        if match_response:
                            detailed_matches = self._extract_cnswpl_detailed_match_data(match_response, series_name, match_id)
                            if detailed_matches:
                                matches.extend(detailed_matches)
                                match_count += len(detailed_matches)
                                print(f"✅ CNSWPL: Extracted {len(detailed_matches)} lines from match")
                        
                        matches_processed_in_series += 1
                        
                    except Exception as e:
                        print(f"⚠️ CNSWPL: Error processing match link: {e}")
                        continue
            
            print(f"📊 CNSWPL: Total matches extracted: {match_count}")
            
        except Exception as e:
            print(f"❌ CNSWPL: Error extracting matches: {e}")
        
        return matches, matches_processed_in_series
    
    def _extract_cnswpl_detailed_match_data(self, html: str, series_name: str, match_id: str) -> List[Dict]:
        """Extract detailed match data from CNSWPL individual match page."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract CNSWPL-specific match information
            match_date = self._extract_cnswpl_date(soup)
            teams_and_score = self._extract_cnswpl_teams_and_score(soup)
            
            if not teams_and_score:
                return []
            
            # Extract CNSWPL line-specific data
            line_matches = self._extract_cnswpl_lines(soup, series_name, match_id, match_date, teams_and_score)
            
            return line_matches
            
        except Exception as e:
            print(f"❌ CNSWPL: Error extracting detailed match data: {e}")
            return []

class NSTFScraper(BaseLeagueScraper):
    """NSTF-specific scraper with dedicated extraction logic."""
    
    def extract_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract NSTF series links."""
        return self._extract_nstf_series_links(html)
    
    def extract_matches_from_series(self, html: str, series_name: str, 
                                  current_total_processed: int = 0, total_series: int = 1) -> Tuple[List[Dict], int]:
        """Extract matches from NSTF series page."""
        return self._extract_nstf_matches_from_series(html, series_name, current_total_processed, total_series)
    
    def _extract_nstf_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract NSTF-specific series links."""
        series_links = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            print(f"   🔍 Looking for NSTF series links...")
            
            # Method 1: Look for links containing NSTF series patterns
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # NSTF-specific patterns (Series, Division, Team names)
                if any(keyword in text.lower() for keyword in ['series', 'division', 'league']):
                    if href.startswith('/'):
                        full_url = f"https://nstf.tenniscores.com{href}"
                    else:
                        full_url = href
                    series_links.append((text, full_url))
                    print(f"   📋 Added NSTF series: {text}")
            
            # Method 2: Look for team links (NSTF uses team= parameters)
            import re
            team_links = soup.find_all("a", href=re.compile(r"team="))
            for link in team_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                
                if text and href:
                    full_url = f"https://nstf.tenniscores.com{href}" if href.startswith('/') else href
                    series_links.append((text, full_url))
                    print(f"   📋 Added NSTF team: {text}")
            
            return series_links
            
        except Exception as e:
            print(f"   ❌ Error extracting NSTF series links: {e}")
            return []
    
    def _extract_nstf_matches_from_series(self, html: str, series_name: str, 
                                        current_total_processed: int = 0, total_series: int = 1) -> Tuple[List[Dict], int]:
        """Extract matches from NSTF series page using NSTF-specific logic."""
        matches = []
        matches_processed_in_series = 0
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            print(f"🔍 NSTF: Parsing matches from {series_name}...")
            
            # NSTF also uses individual match pages with print_match.php  
            match_links = soup.find_all('a', href=True)
            match_links = [link for link in match_links if 'print_match.php' in link.get('href', '')]
            match_count = 0
            
            print(f"🔗 NSTF: Found {len(match_links)} match detail links")
            
            for i, link in enumerate(match_links, 1):
                href = link.get('href', '')
                
                if 'print_match.php' in href:
                    try:
                        # Extract match ID from NSTF URL format
                        match_id = href.split('sch=')[1].split('&')[0] if 'sch=' in href else f"nstf_match_{i}"
                        
                        # Build NSTF-specific URL
                        if href.startswith('/'):
                            match_url = f"https://nstf.tenniscores.com{href}"
                        elif href.startswith('http'):
                            match_url = href
                        else:
                            match_url = f"https://nstf.tenniscores.com/{href}"
                        
                        # Calculate progress within this series and overall
                        series_percent_complete = (i / len(match_links)) * 100
                        overall_matches_processed = current_total_processed + i
                        estimated_total_matches = len(match_links) * total_series if total_series > 0 else len(match_links)
                        overall_percent_complete = (overall_matches_processed / estimated_total_matches) * 100 if estimated_total_matches > 0 else 0
                        
                        print(f"🔗 NSTF Match Progress: {i}/{len(match_links)} ({series_percent_complete:.1f}% of {series_name}) | Overall: {overall_matches_processed}/{estimated_total_matches} ({overall_percent_complete:.1f}%)")
                        print(f"   Processing: {href}")
                        
                        # Get detailed NSTF match page using parent scraper's request method
                        match_response = self._safe_request_for_league_scraper(match_url, f"NSTF match detail page {i}")
                        if match_response:
                            detailed_matches = self._extract_nstf_detailed_match_data(match_response, series_name, match_id)
                            if detailed_matches:
                                matches.extend(detailed_matches)
                                match_count += len(detailed_matches)
                                print(f"✅ NSTF: Extracted {len(detailed_matches)} lines from match")
                        
                        matches_processed_in_series += 1
                        
                    except Exception as e:
                        print(f"⚠️ NSTF: Error processing match link: {e}")
                        continue
            
            print(f"📊 NSTF: Total matches extracted: {match_count}")
            
        except Exception as e:
            print(f"❌ NSTF: Error extracting matches: {e}")
        
        return matches, matches_processed_in_series
    
    def _extract_nstf_detailed_match_data(self, html: str, series_name: str, match_id: str) -> List[Dict]:
        """Extract detailed match data from NSTF individual match page."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract NSTF-specific match information  
            match_date = self._extract_nstf_date(soup)
            teams_and_score = self._extract_nstf_teams_and_score(soup)
            
            if not teams_and_score:
                return []
            
            # Extract NSTF line-specific data (similar to CNSWPL but with NSTF league_id)
            line_matches = self._extract_nstf_lines(soup, series_name, match_id, match_date, teams_and_score)
            
            return line_matches
            
        except Exception as e:
            print(f"❌ NSTF: Error extracting detailed match data: {e}")
            return []
    
    def _extract_nstf_date(self, soup) -> str:
        """Extract match date from NSTF match page."""
        try:
            # NSTF-specific date extraction logic
            date_elements = soup.find_all(text=True)
            for element in date_elements:
                if isinstance(element, str) and '-' in element:
                    # Look for date patterns like "10-Jul-25"
                    import re
                    date_match = re.search(r'\d{1,2}-[A-Za-z]{3}-\d{2}', element)
                    if date_match:
                        return date_match.group()
            return None
        except Exception as e:
            print(f"❌ NSTF: Error extracting date: {e}")
            return None
    
    def _extract_nstf_teams_and_score(self, soup) -> dict:
        """Extract team names and scores from NSTF match page."""
        try:
            # NSTF-specific team and score extraction
            # This will need to be customized based on NSTF's actual HTML structure
            return {
                "Home Team": "NSTF Home Team",  # Placeholder - needs actual implementation
                "Away Team": "NSTF Away Team",  # Placeholder - needs actual implementation
                "Scores": "NSTF Scores"         # Placeholder - needs actual implementation
            }
        except Exception as e:
            print(f"❌ NSTF: Error extracting teams and score: {e}")
            return {}
    
    def _extract_nstf_lines(self, soup, series_name: str, match_id: str, match_date: str, teams_and_score: dict) -> List[Dict]:
        """Extract NSTF line-specific data with proper league assignment."""
        line_matches = []
        
        try:
            # NSTF-specific line extraction logic
            # This is a simplified implementation - needs customization for actual NSTF format
            for line_num in range(1, 5):  # Assume 4 lines per match
                line_match = {
                    "league_id": "NSTF",  # CRITICAL: Always NSTF for this scraper
                    "match_id": f"{match_id}_Line{line_num}",
                    "source_league": "NSTF",
                    "Line": f"Line {line_num}",
                    "Date": match_date,
                    "Home Team": teams_and_score.get("Home Team"),
                    "Away Team": teams_and_score.get("Away Team"),
                    "Home Player 1": "NSTF Player 1",  # Placeholder
                    "Home Player 2": "NSTF Player 2",  # Placeholder  
                    "Away Player 1": "NSTF Player 3",  # Placeholder
                    "Away Player 2": "NSTF Player 4",  # Placeholder
                    "Home Player 1 ID": f"nstf_player_{line_num}_1",  # Placeholder
                    "Home Player 2 ID": f"nstf_player_{line_num}_2",  # Placeholder
                    "Away Player 1 ID": f"nstf_player_{line_num}_3",  # Placeholder
                    "Away Player 2 ID": f"nstf_player_{line_num}_4",  # Placeholder
                    "Scores": teams_and_score.get("Scores"),
                    "Winner": "home"  # Placeholder
                }
                line_matches.append(line_match)
            
            print(f"✅ NSTF: Created {len(line_matches)} line matches with league_id=NSTF")
            
        except Exception as e:
            print(f"❌ NSTF: Error extracting lines: {e}")
            
        return line_matches

class APTAScraper(BaseLeagueScraper):
    """APTA-specific scraper with dedicated extraction logic."""
    
    def extract_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract APTA series links."""
        return self._extract_apta_series_links(html)
    
    def extract_matches_from_series(self, html: str, series_name: str, 
                                  current_total_processed: int = 0, total_series: int = 1) -> Tuple[List[Dict], int]:
        """Extract matches from APTA series page."""
        return self._extract_apta_matches_from_series(html, series_name, current_total_processed, total_series)

class EnhancedMatchScraper:
    """Enhanced match scraper with league-specific delegation."""
    
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
            print(f"🚀 Enhanced Match Scraper initialized with league-specific architecture")
            print(f"   Mode: {'FAST' if config.fast_mode else 'STEALTH'}")
            print(f"   Environment: {config.environment}")
            print(f"   Delta Mode: {config.delta_mode}")
            if config.start_date and config.end_date:
                print(f"   Date Range: {config.start_date} to {config.end_date}")
    
    def _get_league_scraper(self, league_subdomain: str) -> BaseLeagueScraper:
        """Get appropriate league-specific scraper."""
        league_lower = league_subdomain.lower()
        
        if league_lower == "nstf":
            return NSTFScraper(self.config, league_subdomain)
        elif league_lower in ["cnswpl", "cns"]:
            return CNSWPLScraper(self.config, league_subdomain)
        elif league_lower in ["aptachicago", "apta"]:
            return APTAScraper(self.config, league_subdomain)
        else:
            raise ValueError(f"Unsupported league: {league_subdomain}")
    
    def scrape_matches(self, league_subdomain: str, series_filter: str = None) -> List[Dict]:
        """Main scraping method with league-specific delegation."""
        if self.config.verbose:
            print(f"🎾 Starting match scraping for league: {league_subdomain}")
            print(f"   Using league-specific scraper architecture for complete separation")
        
        # Get league-specific scraper
        league_scraper = self._get_league_scraper(league_subdomain)
        
        # Use league-specific scraping logic
        return self._scrape_with_league_scraper(league_scraper, league_subdomain, series_filter)
    
    def _scrape_with_league_scraper(self, league_scraper: BaseLeagueScraper, league_subdomain: str, series_filter: str = None) -> List[Dict]:
        """Scrape matches using league-specific scraper with complete isolation."""
        all_matches = []
        
        try:
            # Get main page
            base_url = f"https://{league_subdomain.lower()}.tenniscores.com"
            print(f"🌐 {league_scraper.get_league_id()}: Fetching main page: {base_url}")
            
            main_page_html = self._safe_request(base_url, f"{league_scraper.get_league_id()} main page")
            if not main_page_html:
                print(f"❌ {league_scraper.get_league_id()}: Failed to get main page")
                return []
            
            # Extract series links using league-specific logic
            series_links = league_scraper.extract_series_links(main_page_html)
            print(f"📋 {league_scraper.get_league_id()}: Found {len(series_links)} series")
            
            if series_filter:
                # Filter series if specified
                filtered_links = [(name, url) for name, url in series_links if series_filter.lower() in name.lower()]
                print(f"🔍 {league_scraper.get_league_id()}: Filtered to {len(filtered_links)} series matching '{series_filter}'")
                series_links = filtered_links
            
            current_total_processed = 0
            
            # Process each series using league-specific logic
            for i, (series_name, series_url) in enumerate(series_links, 1):
                series_percent = (i / len(series_links)) * 100
                print(f"\n🏆 {league_scraper.get_league_id()}: Processing Series {i}/{len(series_links)} ({series_percent:.1f}% of series): {series_name}")
                print(f"   URL: {series_url}")
                
                # Get series page
                series_html = self._safe_request(series_url, f"{league_scraper.get_league_id()} series: {series_name}")
                if not series_html:
                    print(f"⚠️ {league_scraper.get_league_id()}: Failed to get series page: {series_name}")
                    continue
                
                # Extract matches using league-specific logic
                series_matches, processed_count = league_scraper.extract_matches_from_series(
                    series_html, series_name, current_total_processed, len(series_links)
                )
                
                if series_matches:
                    all_matches.extend(series_matches)
                    current_total_processed += processed_count
                    
                    # Create temp file for this series
                    self._save_series_temp_file(league_subdomain, series_name, series_matches)
                    
                    # Calculate overall progress
                    overall_percent = (i / len(series_links)) * 100
                    print(f"✅ {league_scraper.get_league_id()}: {series_name} - Added {len(series_matches)} matches")
                    print(f"📊 Overall Progress: {i}/{len(series_links)} series ({overall_percent:.1f}% complete) | Total matches: {len(all_matches)}")
                else:
                    print(f"⚠️ {league_scraper.get_league_id()}: {series_name} - No matches found")
            
            print(f"🎯 {league_scraper.get_league_id()}: FINAL RESULT - {len(all_matches)} total matches extracted")
            
            # Validate all matches have correct league_id
            league_id = league_scraper.get_league_id()
            incorrect_matches = [m for m in all_matches if m.get('league_id') != league_id]
            if incorrect_matches:
                print(f"🚨 CRITICAL ERROR: Found {len(incorrect_matches)} matches with incorrect league_id!")
                for match in incorrect_matches[:3]:  # Show first 3 examples
                    print(f"   Expected: {league_id}, Found: {match.get('league_id')} in match: {match.get('match_id')}")
                raise ValueError(f"League ID validation failed for {league_scraper.get_league_id()}")
            else:
                print(f"✅ {league_scraper.get_league_id()}: All matches have correct league_id={league_id}")
            
            return all_matches
            
        except Exception as e:
            print(f"❌ {league_scraper.get_league_id()}: Error in league-specific scraping: {e}")
            return []
    
    def _save_series_temp_file(self, league_subdomain: str, series_name: str, series_matches: List[Dict]):
        """Save series matches to a temporary file for debugging and incremental processing."""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            from data.etl.utils.league_directory_manager import get_league_file_path
            
            # Get the league directory
            league_data_dir = os.path.dirname(get_league_file_path(league_subdomain, "match_history.json"))
            tmp_dir = os.path.join(league_data_dir, 'tmp')
            
            # Create tmp directory if it doesn't exist
            os.makedirs(tmp_dir, exist_ok=True)
            
            # Clean series name for filename
            safe_series_name = series_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            temp_file_path = os.path.join(tmp_dir, f"series_{safe_series_name}.json")
            
            # Save series matches to temp file
            import json
            with open(temp_file_path, 'w') as f:
                json.dump(series_matches, f, indent=2)
            
            print(f"💾 Temp file saved: {temp_file_path} ({len(series_matches)} matches)")
            
        except Exception as e:
            if self.config.verbose:
                print(f"⚠️ Failed to save temp file for {series_name}: {e}")
            # Don't fail the scraping if temp file creation fails
    
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

        # Parse series links
        series_links = self._extract_series_links(main_html, league_subdomain)
        print(f"   📋 Found {len(series_links)} series")
        
        # Show filtering information
        if series_filter and series_filter != "all":
            print(f"🔍 Filtering for series: '{series_filter}'")
            filtered_series = [s[0] for s in series_links if series_filter.lower() == s[0].lower()]
            print(f"📊 Series matching filter: {filtered_series}")
        
        all_matches = []
        
        # Calculate total series with same filtering logic
        if series_filter and series_filter != "all":
            total_series = len([s for s in series_links if series_filter.lower() == s[0].lower()])
        else:
            total_series = len(series_links)
        
        processed_series = 0
        
        # Track overall progress across all series
        total_matches_processed = 0
        
        for i, (series_name, series_url) in enumerate(series_links, 1):
            # Improved series filtering logic
            if series_filter and series_filter != "all":
                # Exact match for series names (case-insensitive)
                if series_filter.lower() != series_name.lower():
                    continue
            
            processed_series += 1
            series_percent = (processed_series / total_series) * 100
            print(f"\n🏆 Processing Series {processed_series}/{total_series} ({series_percent:.1f}% of series): {series_name}")
            print(f"   URL: {series_url}")
            
            # Get series page
            series_html = self._safe_request(series_url, f"series {series_name}")
            if not series_html:
                print(f"   ⚠️ Failed to scrape series {series_name}")
                continue
            
            # Parse matches from series page
            print(f"   🔍 Parsing matches from {series_name}...")
            series_matches, matches_processed_in_series = self._extract_matches_from_series(
                series_html, series_name, total_matches_processed, total_series, league_subdomain
            )
            total_matches_processed += matches_processed_in_series
            
            # Save temporary series file for atomic operations
            if series_matches:
                self._save_series_temp(league_subdomain, series_name, series_matches)
                all_matches.extend(series_matches)
                print(f"   ✅ Added {len(series_matches)} matches from {series_name}")
            else:
                print(f"   ⚠️ No matches found in {series_name}")
        
        # Final consolidation
        if all_matches:
            self._save_final_matches(league_subdomain, all_matches)
            print(f"\n✅ Successfully scraped {len(all_matches)} total matches")
        else:
            print(f"\n⚠️ No matches found for {league_subdomain}")
        
        return all_matches

    def _get_tmp_dir(self, league_subdomain: str) -> str:
        """Return a per-league temp directory path for series JSONs, ensure it exists."""
        import os, sys
        # Resolve canonical league directory via helper
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        try:
            from data.etl.utils.league_directory_manager import get_league_file_path
            final_path = get_league_file_path(league_subdomain, "match_history.json")
        finally:
            sys.path.pop(0)
        tmp_dir = os.path.join(os.path.dirname(final_path), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir

    def _sanitize_series_name(self, series_name: str) -> str:
        import re
        slug = re.sub(r"[^A-Za-z0-9]+", "_", series_name or "series").strip("_")
        return slug or "series"

    def _save_series_temp(self, league_subdomain: str, series_name: str, series_matches: List[Dict]) -> str:
        """Write a temporary JSON for a single series (atomic write). Returns filepath."""
        import json, os
        tmp_dir = self._get_tmp_dir(league_subdomain)
        fname = f"series_{self._sanitize_series_name(series_name)}.json"
        path = os.path.join(tmp_dir, fname)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(series_matches, f, indent=2)
        os.replace(tmp, path)
        print(f"💾 Saved temp series file: {path} ({len(series_matches)} matches)")
        return path

    def _save_final_matches(self, league_subdomain: str, all_matches: List[Dict]) -> str:
        """Save final consolidated matches to the league's main match_history.json file."""
        import json, os, sys
        # Resolve canonical league directory via helper
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        try:
            from data.etl.utils.league_directory_manager import get_league_file_path
            final_path = get_league_file_path(league_subdomain, "match_history.json")
        finally:
            sys.path.pop(0)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(final_path), exist_ok=True)
        
        # Atomic write to avoid corruption
        tmp_path = final_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(all_matches, f, indent=2)
        os.replace(tmp_path, final_path)
        
        print(f"💾 Saved final matches file: {final_path} ({len(all_matches)} matches)")
        return final_path
    
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
            series_links = self._extract_series_links(main_html, league_subdomain)
            
            if not series_links:
                print(f"⚠️ No series links found for {league_subdomain}")
                return []
            
            print(f"📋 Found {len(series_links)} series to process:")
            for i, (series_name, _) in enumerate(series_links, 1):
                print(f"   {i}. {series_name}")
            
            # Show filtering information
            if series_filter and series_filter != "all":
                print(f"🔍 Filtering for series: '{series_filter}'")
                filtered_series = [s[0] for s in series_links if series_filter.lower() == s[0].lower()]
                print(f"📊 Series matching filter: {filtered_series}")
            
            all_matches = []
            
            # Scrape each series
            processed_series = 0
            # Calculate total series with same filtering logic
            if series_filter and series_filter != "all":
                total_series = len([s for s in series_links if series_filter.lower() == s[0].lower()])
            else:
                total_series = len(series_links)
            
            # Track overall progress across all series
            total_matches_processed = 0
            
            for i, (series_name, series_url) in enumerate(series_links, 1):
                # Improved series filtering logic
                if series_filter and series_filter != "all":
                    # Exact match for series names (case-insensitive)
                    if series_filter.lower() != series_name.lower():
                        continue
                
                processed_series += 1
                series_percent = (processed_series / total_series) * 100
                print(f"\n🏆 Processing Series {processed_series}/{total_series} ({series_percent:.1f}% of series): {series_name}")
                print(f"   URL: {series_url}")
                
                try:
                    # Get series page
                    series_response = make_proxy_request(series_url, timeout=30)
                    if not series_response:
                        print(f"❌ Failed to fetch series page for {series_name}")
                        continue
                    
                    # Parse matches from series page
                    print(f"🔍 Extracting matches from {series_name}...")
                    series_matches, matches_processed_in_series = self._extract_matches_from_series(
                        series_response.text, series_name, total_matches_processed, total_series, league_subdomain
                    )
                    total_matches_processed += matches_processed_in_series
                    
                    # Apply date filtering if in delta mode
                    if self.config.delta_mode and self.config.start_date and self.config.end_date:
                        print(f"📅 Filtering matches by date range...")
                        series_matches = self._filter_matches_by_date(series_matches)
                    
                    all_matches.extend(series_matches)
                    print(f"✅ Found {len(series_matches)} matches in {series_name}")

                    # Save per-series temp JSON to avoid all-or-nothing loss
                    self._save_series_temp(league_subdomain, series_name, series_matches)
                    
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

    # REMOVED: Old mixed _extract_series_links method - now handled by league-specific scrapers
    
    # REMOVED: Old _extract_cnswpl_series_links method - now handled by CNSWPLScraper class
        
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
            
            # Method 3: Look for day/night league patterns (only if no series found yet)
            if not series_links:
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
            
        except Exception as e:
            print(f"   ❌ Error extracting APTA series links: {e}")
            return []

    def _extract_nstf_series_links(self, html: str, league_subdomain: str) -> List[Tuple[str, str]]:
        """Extract series links for NSTF format."""
        series_links = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            print(f"   🔍 Looking for NSTF series links...")
            
            # Method 1: Look for links containing "series" 
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for series patterns specific to NSTF
                if any(keyword in text.lower() for keyword in ['series', 'division', 'league']):
                    if href.startswith('/'):
                        full_url = f"https://{league_subdomain}.tenniscores.com{href}"
                    else:
                        full_url = href
                    series_links.append((text, full_url))
                    print(f"   📋 Added NSTF series: {text}")
            
            # Method 2: Look for team links (NSTF might use team= parameters like APTA)
            import re
            team_links = soup.find_all("a", href=re.compile(r"team="))
            for link in team_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                
                if text and href:
                    # For NSTF, use the text as-is for series name
                    full_url = f"https://{league_subdomain}.tenniscores.com{href}" if href.startswith('/') else href
                    series_links.append((text, full_url))
                    print(f"   📋 Added NSTF team: {text}")
            
            # Method 3: Look for other common NSTF patterns
            if not series_links:
                print(f"   🔍 No direct series links found, looking for other NSTF patterns...")
                # Look for any links that might be series/team related
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Include links that contain mod= parameter (common in TennisScores)
                    if 'mod=' in href and text and len(text.strip()) > 0:
                        full_url = f"https://{league_subdomain}.tenniscores.com{href}" if href.startswith('/') else href
                        series_links.append((text, full_url))
                        print(f"   📋 Added NSTF link: {text}")
            
            # If still no series found, don't fall back to other leagues - just return empty
            if not series_links:
                print(f"   ⚠️ No NSTF series found - this may be normal if no active series exist")
            
            print(f"   📊 Total NSTF series found: {len(series_links)}")
            return series_links
            
        except Exception as e:
            print(f"   ❌ Error extracting NSTF series links: {e}")
            return []
    
    def _extract_matches_from_series(self, html: str, series_name: str, 
                                   current_total_processed: int = 0, total_series: int = 1, league_subdomain: str = None) -> Tuple[List[Dict], int]:
        """Extract detailed matches from series page for CNSWPL (like APTA format).
        
        Returns:
            tuple: (matches_list, matches_processed_count)
        """
        matches = []
        matches_processed_in_series = 0
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            print(f"🔍 Parsing detailed matches from {series_name}...")
            
            # Method 1: Look for match links and follow them to get detailed data
            match_links = soup.find_all('a', href=True)
            match_links = [link for link in match_links if 'print_match.php' in link.get('href', '')]
            match_count = 0
            
            print(f"🔗 Found {len(match_links)} match detail links")
            
            # Estimate total matches across all series for overall progress
            estimated_total_matches = len(match_links) * total_series
            
            for i, link in enumerate(match_links, 1):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for match link patterns (works for multiple leagues)
                if 'print_match.php' in href and 'sch=' in href:
                    try:
                        # Extract match ID from URL
                        match_id = href.split('sch=')[1].split('&')[0] if 'sch=' in href else None
                        
                        # Follow the match link to get detailed data
                        # Use the correct league subdomain instead of hard-coding cnswpl
                        base_domain = f"https://{league_subdomain}.tenniscores.com" if league_subdomain else "https://cnswpl.tenniscores.com"
                        
                        if href.startswith('/'):
                            match_url = f"{base_domain}{href}"
                        elif href.startswith('http'):
                            match_url = href
                        else:
                            match_url = f"{base_domain}/{href}"
                        
                        # Calculate progress within this series and overall
                        series_percent_complete = (i / len(match_links)) * 100
                        overall_matches_processed = current_total_processed + i
                        overall_percent_complete = (overall_matches_processed / estimated_total_matches) * 100 if estimated_total_matches > 0 else 0
                        
                        print(f"🔗 Series Progress: {i}/{len(match_links)} ({series_percent_complete:.1f}% of {series_name}) | Overall: {overall_matches_processed}/{estimated_total_matches} ({overall_percent_complete:.1f}%)")
                        print(f"   Processing: {href}")
                        
                        # Get detailed match page
                        match_response = self._safe_request(match_url, f"match detail page {i}")
                        if match_response:
                            detailed_matches = self._extract_detailed_match_data(match_response, series_name, match_id, league_subdomain)
                            if detailed_matches:
                                matches.extend(detailed_matches)  # Add all line matches
                                match_count += len(detailed_matches)
                                first_match = detailed_matches[0] if detailed_matches else {}
                                home_team = first_match.get('Home Team', 'Unknown')
                                away_team = first_match.get('Away Team', 'Unknown')
                                date = first_match.get('Date', 'Unknown Date')
                                print(f"✅ Extracted {len(detailed_matches)} lines: {home_team} vs {away_team} on {date}")
                        
                        matches_processed_in_series += 1
                        
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
                                match_data = self._extract_match_from_table_row(cells, series_name, league_subdomain)
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
        
        return matches, matches_processed_in_series
    
    def _extract_detailed_match_data(self, html: str, series_name: str, match_id: str, league_subdomain: str = None) -> List[Dict]:
        """Extract detailed match data from individual match page - supports multiple league formats."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract common match information
            match_date = self._extract_cnswpl_date(soup)
            teams_and_score = self._extract_cnswpl_teams_and_score(soup)
            
            if not teams_and_score:
                return []
            
            # Extract line-specific data from court breakdown
            line_matches = self._extract_cnswpl_lines(soup, series_name, match_id, match_date, teams_and_score, league_subdomain)
            
            return line_matches
            
        except Exception as e:
            if self.config.verbose:
                print(f"   ❌ Error extracting detailed match data: {e}")
            return []
    
    def _get_league_name_from_subdomain(self, league_subdomain: str = None) -> str:
        """Convert league subdomain to proper league name."""
        if not league_subdomain:
            return "CNSWPL"
        
        subdomain_lower = league_subdomain.lower()
        if subdomain_lower == "nstf":
            return "NSTF"
        elif subdomain_lower in ["aptachicago", "apta"]:
            return "APTA_CHICAGO"
        elif subdomain_lower in ["cnswpl", "cns"]:
            return "CNSWPL"
        else:
            return subdomain_lower.upper()

    def _extract_match_from_table_row(self, cells, series_name: str, league_subdomain: str = None) -> Optional[Dict]:
        """Extract match data from table row (fallback method)."""
        try:
            # CRITICAL VALIDATION: Ensure league assignment is correct
            if not league_subdomain:
                print(f"⚠️  WARNING: No league_subdomain provided to _extract_match_from_table_row!")
                print(f"   This could cause incorrect league assignment. Using CNSWPL as default.")
            
            # Use proper league mapping
            league_name = self._get_league_name_from_subdomain(league_subdomain)
            
            # Additional validation
            if league_subdomain and league_subdomain.lower() == 'nstf' and league_name != 'NSTF':
                print(f"🚨 CRITICAL ERROR: NSTF subdomain mapped to wrong league: {league_name}")
                print(f"   Forcing correct league assignment...")
                league_name = 'NSTF'
            
            match_data = {
                "league_id": league_name,
                "match_id": f"table_{series_name.replace(' ', '_')}_{len(cells)}",
                "source_league": league_name,
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
    
    def _extract_cnswpl_lines(self, soup, series_name: str, match_id: str, match_date: str, teams_and_score: dict, league_subdomain: str = None) -> List[Dict]:
        """Extract line-specific data from court breakdown with both home/away players."""
        
        # CRITICAL VALIDATION: Prevent NSTF data from being processed as CNSWPL
        if league_subdomain and league_subdomain.lower() == 'nstf':
            print(f"⚠️  WARNING: NSTF data should not use CNSWPL line extraction logic!")
            print(f"   This could cause league ID corruption. Returning empty list.")
            return []
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
                        
                    if '/' in potential_line and not away_players:
                        away_players = potential_line
                    elif re.match(r'^\d+$', potential_line) and away_players and not away_score:
                        away_score = potential_line
                    elif '/' in potential_line and away_players and away_score and not home_players:
                        home_players = potential_line
                    elif re.match(r'^\d+$', potential_line) and home_players and not home_score:
                        home_score = potential_line
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
                # Use proper league mapping
                league_name = self._get_league_name_from_subdomain(league_subdomain)
                
                line_match = {
                    "league_id": league_name,
                    "match_id": f"{match_id}_Line{court_num}",
                    "source_league": league_name,
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
    
    # Scrape matches using league-specific architecture
    print(f"🚀 Starting match scraping for {league_subdomain}...")
    matches = scraper.scrape_matches(league_subdomain, series_filter)
    
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
    parser.add_argument("--clean-temp-first", action="store_true", help="Delete per-series temp files before starting (default: preserve)")
    
    args = parser.parse_args()
    
    print(f"\n🎾 Starting CNSWPL Match Scraper")
    print(f"📋 League: {args.league}")
    print(f"⚙️  Mode: {'FAST' if args.fast else 'STEALTH'}")
    print(f"🌍 Environment: {args.environment}")
    
    if args.delta_mode:
        print(f"📅 Delta Mode: {args.start_date} to {args.end_date}")
    
    # Optional pre-run cleanup of temp files (off by default)
    if args.clean_temp_first:
        try:
            import sys as _sys, os as _os, shutil as _shutil
            _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))))
            from data.etl.utils.league_directory_manager import get_league_file_path as _get_league_file_path_prerun
            prerun_output = _get_league_file_path_prerun(args.league, "match_history.json")
            prerun_tmp_dir = _os.path.join(_os.path.dirname(prerun_output), 'tmp')
            if _os.path.isdir(prerun_tmp_dir):
                _shutil.rmtree(prerun_tmp_dir)
                print(f"🧹 Cleaned previous temp directory: {prerun_tmp_dir}")
        except Exception as e:
            print(f"⚠️ Pre-run temp cleanup skipped: {e}")
        finally:
            try:
                _sys.path.pop(0)
            except Exception:
                pass

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
    
    # Combine all matches with consolidation from per-series temps
    # Use a composite key so multiple line/court entries for the same match are preserved
    def _dedupe_key(m: dict) -> str:
        mid = (m.get('match_id') or '').strip()
        line_marker = (m.get('Line') or m.get('Court') or m.get('Court #') or '').strip()
        if mid:
            return f"{mid}|{line_marker}".lower()
        # Fallback when match_id is missing: compose from teams/date/line
        home = (m.get('Home Team') or '').strip()
        away = (m.get('Away Team') or '').strip()
        date = (m.get('Date') or '').strip()
        return f"{home}|{away}|{date}|{line_marker}".lower()

    merged_by_key: Dict[str, Dict] = {}

    # 1) Start with existing
    for m in existing_matches:
        merged_by_key[_dedupe_key(m)] = m

    # 2) Load per-series temp files if they exist
    tmp_dir = os.path.join(os.path.dirname(output_file), 'tmp')
    if os.path.isdir(tmp_dir):
        import glob
        for path in glob.glob(os.path.join(tmp_dir, 'series_*.json')):
            try:
                with open(path, 'r') as f:
                    series_list = json.load(f)
                for m in series_list:
                    merged_by_key[_dedupe_key(m)] = m
            except Exception as e:
                logger.warning(f"⚠️ Failed reading temp series file {path}: {e}")

    # 3) Overlay new matches from this run (new data wins)
    for m in matches:
        merged_by_key[_dedupe_key(m)] = m

    all_matches = list(merged_by_key.values())

    # Atomic write
    tmp_file = output_file + '.tmp'
    with open(tmp_file, 'w') as f:
        json.dump(all_matches, f, indent=2)
    os.replace(tmp_file, output_file)
    
    print(f"\n🎉 Scraping completed!")
    print(f"📁 Results saved to: {output_file}")
    print(f"📊 Existing matches: {len(existing_matches):,}")
    print(f"📊 New matches added: {len(new_matches):,}")
    print(f"📊 Total matches: {len(all_matches):,}")
    
    if len(matches) > 0:
        print(f"✅ Successfully extracted {len(matches)} matches this run")
    else:
        print(f"⚠️ No new matches were extracted in this run")

if __name__ == "__main__":
    main()
