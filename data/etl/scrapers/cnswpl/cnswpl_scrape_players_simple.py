#!/usr/bin/env python3
"""
Simplified CNSWPL Player Scraper

This script scrapes current season player data from CNSWPL series (1-17 and A-K) 
directly from team roster pages. It skips season scores lookup and career stats
to focus only on basic player information for faster execution.

Usage:
    python3 cnswpl_scrape_players_simple.py
    python3 cnswpl_scrape_players_simple.py --series A,B,C
"""

import sys
import os
import time
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup

# Add the scrapers directory to the path to access helper modules
scrapers_path = os.path.join(os.path.dirname(__file__), '..')
if scrapers_path not in sys.path:
    sys.path.insert(0, scrapers_path)

# Import speed optimizations with safe fallbacks
try:
    from ..adaptive_pacer import pace_sleep, mark
    from ..stealth_browser import stop_after_selector
    SPEED_OPTIMIZATIONS_AVAILABLE = True
except ImportError:
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

# Import rally context for browser automation
try:
    from ..stealth_browser import create_stealth_browser
    RALLY_CONTEXT_AVAILABLE = True
except ImportError:
    try:
        from helpers.stealth_browser import create_stealth_browser
        RALLY_CONTEXT_AVAILABLE = True
    except ImportError:
        RALLY_CONTEXT_AVAILABLE = False
        print("⚠️ Rally context not available - using standard requests")

class CNSWPLSimpleScraper:
    """Simplified CNSWPL player scraper that only gets current season data"""
    
    def __init__(self, force_restart=False, target_series=None):
        self.base_url = "https://cnswpl.tenniscores.com"
        self.all_players = []
        self.completed_series = set()
        self.target_series = target_series

        self.start_time = time.time()
        self.force_restart = force_restart
        
        # Progress tracking
        self.total_players_processed = 0
        self.total_players_expected = 0
        self.total_series_count = 0
        self.current_series = ""
        self.current_player = ""
        self.last_progress_update = time.time()
        
        # Initialize rally context if available
        self.rally_context = None
        if RALLY_CONTEXT_AVAILABLE:
            try:
                self.rally_context = create_stealth_browser(fast_mode=True, verbose=False)
                if self.rally_context:
                    print("✅ Rally context (stealth browser) initialized for efficient scraping")
            except Exception as e:
                print(f"⚠️ Rally context initialization failed: {e}")
                self.rally_context = None
        
        # Setup logging
        self.setup_logging()
        
        # Performance tracking
        self.request_count = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.request_times = []

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"cnswpl_simple_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_series_urls(self) -> List[Tuple[str, str]]:
        """Generate URLs for CNSWPL series (1-17 and A-K)"""
        series_urls = []
        
        series_urls_data = [
            # Numeric series (1-17)
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
            # Letter series (A-K) - these URLs need to be discovered dynamically
            ("Series A", None),
            ("Series B", None),
            ("Series C", None),
            ("Series D", None),
            ("Series E", None),
            ("Series F", None),
            ("Series G", None),
            ("Series H", None),
            ("Series I", None),
            ("Series J", None),
            ("Series K", None)
        ]
        
        # Filter series based on target_series parameter if specified
        if self.target_series:
            filtered_data = []
            for series_name, series_path in series_urls_data:
                series_id = series_name.replace('Series ', '').strip()
                if series_id in self.target_series:
                    filtered_data.append((series_name, series_path))
            series_urls_data = filtered_data
        
        # Process series URLs
        for series_name, series_path in series_urls_data:
            if series_path:
                series_url = f"{self.base_url}{series_path}"
                series_urls.append((series_name, series_url))
            else:
                series_urls.append((series_name, "DISCOVER"))
        
        return series_urls

    def get_html_with_fallback(self, url: str) -> str:
        """Get HTML content with fallback methods"""
        try:
            # Try rally context (stealth browser) first if available
            if self.rally_context:
                try:
                    # Use the stealth browser to get HTML
                    html = self.rally_context.get_html(url)
                    if html and len(html) > 1000:
                        return html
                except Exception as e:
                    print(f"   ⚠️ Rally context failed, falling back: {e}")
            
            # Fallback to requests
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
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
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            print(f"   ❌ Failed to get HTML for {url}: {e}")
            return ""

    def scrape_all_series(self):
        """Scrape all series with simplified approach"""
        if self.target_series:
            series_list = ', '.join(self.target_series)
            print(f"🚀 Starting CNSWPL targeted series scraping (simple mode)...")
            print(f"   This will scrape series: {series_list}")
        else:
            print("🚀 Starting CNSWPL comprehensive series scraping (simple mode)...")
            print("   This will scrape ALL series (1-17 and A-K) from roster pages")
        print("   ⚡ SIMPLE MODE: Current season scores + player data (no career stats)")
        print("⏱️ This should take about 8-12 minutes to complete")
        
        # Get series URLs
        series_urls = self.get_series_urls()
        
        # Filter series based on target_series parameter if specified
        if self.target_series:
            print(f"\n🎯 Filtering to target series: {', '.join(self.target_series)}")
            filtered_series = []
            for series_name, series_url in series_urls:
                series_id = series_name.replace('Series ', '').strip()
                if series_id in self.target_series:
                    filtered_series.append((series_name, series_url))
                else:
                    print(f"   ⏭️ Skipping {series_name} (not in target list)")
            series_urls = filtered_series
            print(f"✅ Filtered to {len(series_urls)} target series")
        
        print(f"\n📋 Will scrape {len(series_urls)} series:")
        for series_name, series_url in series_urls:
            status = "✅ COMPLETED" if series_name in self.completed_series else "⏳ PENDING"
            url_status = "🔍 DISCOVER" if series_url == "DISCOVER" else "✅ URL READY"
            print(f"   - {series_name} {status} ({url_status})")
        
        # Estimate total players
        estimated_players_per_series = 100  # Conservative estimate
        self.total_players_expected = len(series_urls) * estimated_players_per_series
        self.total_series_count = len(series_urls)
        
        print(f"\n🚀 Beginning scraping process...")
        print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Estimated total players: {self.total_players_expected:,}")
        print(f"{'='*60}")
        
        # Scrape each series
        successful_series = len(self.completed_series)
        failed_series = []
        
        for i, (series_name, series_url) in enumerate(series_urls, 1):
            if series_name in self.completed_series:
                print(f"\n⏭️ Skipping {series_name} (already completed)")
                continue
            
            print(f"\n🏆 Processing Series {i}/{len(series_urls)}: {series_name}")
            
            try:
                players = self.extract_players_from_series_page(series_name, series_url)
                if players:
                    self.all_players.extend(players)
                    self.completed_series.add(series_name)
                    successful_series += 1
                    print(f"✅ Successfully processed {series_name}: {len(players)} players")
                else:
                    failed_series.append(series_name)
                    print(f"⚠️ No players found for {series_name}")
                
                # Add delay between series
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error processing {series_name}: {e}")
                failed_series.append(series_name)
        
        # Save results
        self.save_results(is_final=True)
        
        print(f"\n🎉 SCRAPING COMPLETED!")
        print(f"   ✅ Successful series: {successful_series}")
        print(f"   ❌ Failed series: {len(failed_series)}")
        print(f"   👥 Total players found: {len(self.all_players)}")
        
        if failed_series:
            print(f"   Failed series: {', '.join(failed_series)}")

    def extract_players_from_series_page(self, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific series"""
        print(f"\n🎾 Scraping {series_name} from {series_url}")
        
        try:
            html_content = self.get_html_with_fallback(series_url)
            
            if not html_content:
                print(f"❌ Failed to get content for {series_name}")
                return []
            
            print(f"   ✅ Got HTML content ({len(html_content)} characters)")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            all_players = []
            
            # Find all team links on the series page
            team_links = []
            all_links = soup.find_all('a', href=True)
            
            # Extract series number/letter for filtering
            series_identifier = series_name.replace('Series ', '').strip()
            
            # Use a set to track unique team URLs to prevent duplicates
            seen_urls = set()
            
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
                        
                        # Only add if we haven't seen this URL before
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            team_links.append((text, full_url))
            
            print(f"🏢 Found {len(team_links)} team links in {series_name}")
            
            if not team_links:
                print(f"   ⚠️ No team links found - this might indicate a filtering issue")
                return []
            
            # Process each team
            for team_name, team_url in team_links:
                try:
                    players = self.extract_players_from_team_page(team_name, team_url, series_name, series_url)
                    if players:
                        all_players.extend(players)
                        print(f"     ✅ {team_name}: {len(players)} players")
                    else:
                        print(f"     ⚠️ {team_name}: No players found")
                    
                    # Add delay between teams
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"     ❌ Error processing team {team_name}: {e}")
                    continue
            
            # Final deduplication
            if all_players:
                unique_players_dict = {}
                duplicates_found = 0
                
                for player in all_players:
                    player_id = player.get('Player ID', '')
                    if player_id and player_id not in unique_players_dict:
                        unique_players_dict[player_id] = player
                    elif player_id:
                        duplicates_found += 1
                
                all_players = list(unique_players_dict.values())
                
                if duplicates_found > 0:
                    print(f"   🧹 Final deduplication: Removed {duplicates_found} duplicate players")
                    print(f"   📊 Final count: {len(all_players)} unique players")
                
                # Show series summary
                team_counts = {}
                for player in all_players:
                    team = player.get('Team', 'Unknown')
                    team_counts[team] = team_counts.get(team, 0) + 1
                
                print(f"   📊 Series {series_name} breakdown:")
                for team, count in sorted(team_counts.items()):
                    print(f"      {team}: {count} players")
            
            return all_players
            
        except Exception as e:
            print(f"❌ Error scraping {series_name}: {e}")
            return []

    def extract_players_from_team_page(self, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific team roster page"""
        try:
            html_content = self.get_html_with_fallback(team_url)
            
            if not html_content:
                print(f"     ❌ Failed to get team page for {team_name}")
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            players = []
            
            # Look for the main roster table
            roster_table = soup.find('table', class_='team_roster_table')
            
            if roster_table:
                print(f"       📋 Found team roster table, processing table structure")
                players = self._extract_players_from_table(roster_table, team_name, team_url, series_name, series_url)
            else:
                print(f"       ⚠️ No team roster table found, trying fallback method")
                players = self._extract_players_fallback(soup, team_name, team_url, series_name, series_url)
            
            print(f"     ✅ Found {len(players)} total players on {team_name} roster")
            return players
            
        except Exception as e:
            print(f"     ❌ Error scraping team {team_name}: {e}")
            return []

    def _extract_players_from_table(self, table_element, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Extract players from the CNSWPL team roster table structure - SIMPLIFIED VERSION WITH CURRENT SEASON SCORES"""
        players = []
        
        # Find all rows in the table
        rows = table_element.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:  # Need at least name, wins, and losses
                
                # Extract player name (usually in first cell)
                player_cell = cells[0]
                player_name = player_cell.get_text(strip=True)
                
                # Skip empty rows or headers
                if not player_name or player_name.lower() in ['name', 'player', '']:
                    continue
                
                # Skip sub players
                if any(sub_indicator in player_name.lower() for sub_indicator in ['sub', 'substitute', '(sub)']):
                    continue
                
                # Check for captain indicators and clean player name
                is_captain = False
                clean_player_name = player_name
                
                if '(C)' in player_name:
                    is_captain = True
                    clean_player_name = player_name.replace('(C)', '').strip()
                elif '(CC)' in player_name:
                    is_captain = True
                    clean_player_name = player_name.replace('(CC)', '').strip()
                
                # Remove checkmark from player name
                clean_player_name = clean_player_name.replace('✔', '').strip()
                
                # Extract player ID from any links
                player_id = ""
                player_link = player_cell.find('a', href=True)
                if player_link:
                    href = player_link.get('href', '')
                    # Extract player ID from URL and change prefix
                    player_id_match = re.search(r'p=([^&]+)', href)
                    if player_id_match:
                        player_id = f"cnswpl_{player_id_match.group(1)}"
                
                # Extract current season wins and losses from table cells
                current_wins = 0
                current_losses = 0
                
                if len(cells) >= 3:
                    try:
                        # Look for W and L columns (usually 2nd and 3rd columns)
                        wins_text = cells[1].get_text(strip=True) if len(cells) > 1 else "0"
                        losses_text = cells[2].get_text(strip=True) if len(cells) > 2 else "0"
                        
                        # Convert to integers, handle empty or non-numeric values
                        current_wins = int(wins_text) if wins_text.isdigit() else 0
                        current_losses = int(losses_text) if losses_text.isdigit() else 0
                    except (ValueError, IndexError):
                        current_wins = 0
                        current_losses = 0
                
                # Calculate win percentage
                total_games = current_wins + current_losses
                win_percentage = f"{(current_wins/total_games*100):.1f}%" if total_games > 0 else "0.0%"
                
                # Parse first and last name from cleaned name
                name_parts = clean_player_name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                # Create player record with current season scores (NO CAREER STATS)
                player_data = {
                    'Player ID': player_id,
                    'First Name': first_name,
                    'Last Name': last_name,
                    'Team': team_name,
                    'Series': series_name,
                    'League': 'CNSWPL',
                    'Club': self._extract_club_from_team_name(team_name),
                    'Wins': str(current_wins),
                    'Losses': str(current_losses),
                    'Win %': win_percentage,
                    'Captain': 'Yes' if is_captain else '',
                    'Source URL': team_url,
                    'source_league': 'CNSWPL',
                    'Scraped At': datetime.now().isoformat()
                }
                
                # Debug print for each player
                print(f"         🔍 SCRAPED PLAYER: {clean_player_name}")
                print(f"            Player ID: {player_id}")
                print(f"            First Name: {first_name}")
                print(f"            Last Name: {last_name}")
                print(f"            Team: {team_name}")
                print(f"            Series: {series_name}")
                print(f"            Club: {self._extract_club_from_team_name(team_name)}")
                print(f"            Captain: {'Yes' if is_captain else 'No'}")
                print(f"            Current Season: {current_wins}W-{current_losses}L ({win_percentage})")
                print(f"            ⚡ SIMPLE MODE: Current season scores included, NO career stats")
                
                players.append(player_data)
        
        return players

    def _extract_players_fallback(self, soup, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Fallback method to extract players when table structure is not found - SIMPLIFIED VERSION"""
        players = []
        
        # Look for any links that might be player links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Check if this looks like a player link
            if 'p=' in href and text and len(text.split()) >= 2:
                # Skip sub players
                if any(sub_indicator in text.lower() for sub_indicator in ['sub', 'substitute', '(sub)']):
                    continue
                
                # Extract player ID from URL and change prefix
                player_id_match = re.search(r'p=([^&]+)', href)
                player_id = f"cnswpl_{player_id_match.group(1)}" if player_id_match else ""
                
                # Check for captain indicators and clean player name
                is_captain = False
                clean_player_name = text
                
                if '(C)' in text:
                    is_captain = True
                    clean_player_name = text.replace('(C)', '').strip()
                elif '(CC)' in text:
                    is_captain = True
                    clean_player_name = text.replace('(CC)', '').strip()
                
                # Remove checkmark from player name
                clean_player_name = clean_player_name.replace('✔', '').strip()
                
                # Parse first and last name from cleaned name
                name_parts = clean_player_name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                # Create player record with current season scores (NO CAREER STATS)
                # Note: Fallback method can't extract current season scores from links alone
                player_data = {
                    'Player ID': player_id,
                    'First Name': first_name,
                    'Last Name': last_name,
                    'Team': team_name,
                    'Series': series_name,
                    'League': 'CNSWPL',
                    'Club': self._extract_club_from_team_name(team_name),
                    'Wins': '0',  # Fallback method can't extract scores
                    'Losses': '0',
                    'Win %': '0.0%',
                    'Captain': 'Yes' if is_captain else '',
                    'Source URL': team_url,
                    'source_league': 'CNSWPL',
                    'Scraped At': datetime.now().isoformat()
                }
                
                # Debug print for each player (fallback method)
                print(f"         🔍 SCRAPED PLAYER (FALLBACK): {clean_player_name}")
                print(f"            Player ID: {player_id}")
                print(f"            First Name: {first_name}")
                print(f"            Last Name: {last_name}")
                print(f"            Team: {team_name}")
                print(f"            Series: {series_name}")
                print(f"            Club: {self._extract_club_from_team_name(team_name)}")
                print(f"            Captain: {'Yes' if is_captain else 'No'}")
                print(f"            Current Season: 0W-0L (0.0%) - Fallback method")
                print(f"            ⚡ SIMPLE MODE: Current season scores included, NO career stats")
                
                players.append(player_data)
        
        return players

    def _team_belongs_to_series(self, team_name: str, series_identifier: str) -> bool:
        """Check if a team belongs to a specific series"""
        # This is a simplified version - in practice you might need more sophisticated logic
        # For now, we'll include all teams and let the series page filtering handle it
        return True

    def _extract_club_from_team_name(self, team_name: str) -> str:
        """Extract club name from team name"""
        # Simple club extraction - you might need to enhance this
        club_keywords = ['Tennaqua', 'Winter Club', 'Lake Forest', 'Evanston', 'Prairie Club', 
                        'Wilmette', 'North Shore', 'Valley Lo', 'Westmoreland', 'Indian Hill', 
                        'Birchwood', 'Exmoor', 'Glen View', 'Glenbrook', 'Park Ridge', 'Skokie', 
                        'Michigan Shores', 'Midtown', 'Hinsdale', 'Knollwood', 'Sunset Ridge', 
                        'Briarwood', 'Biltmore', 'Barrington Hills', 'Bryn Mawr', 'Saddle & Cycle', 
                        'Onwentsia', 'Lake Bluff', 'Lake Shore', 'Northmoor', 'Butterfield', 
                        'River Forest', 'LifeSport', 'Winnetka']
        
        for club in club_keywords:
            if club.lower() in team_name.lower():
                return club
        
        return team_name  # Fallback to team name if no club found

    def save_results(self, is_final: bool = False):
        """Save scraping results to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create results directory if it doesn't exist
        results_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL')
        os.makedirs(results_dir, exist_ok=True)
        
        # Save to special file for Series 17 test, otherwise use players_simple.json
        if '17' in str(self.target_series) and len(self.target_series) == 1:
            output_file = os.path.join(results_dir, 'series17_simple.json')
        else:
            output_file = os.path.join(results_dir, 'players_simple.json')
        
        # Create backup if file exists
        if os.path.exists(output_file):
            backup_file = os.path.join(results_dir, f'players_simple_backup_{timestamp}.json')
            import shutil
            shutil.copy2(output_file, backup_file)
            print(f"📁 Created backup: {backup_file}")
        
        # Prepare data for saving with metadata
        results_data = {
            'metadata': {
                'scraper': 'CNSWPL Simple Player Scraper',
                'version': '1.0',
                'scraped_at': datetime.now().isoformat(),
                'is_final': is_final,
                'total_players': len(self.all_players),
                'completed_series': list(self.completed_series),
                'target_series': self.target_series,
                'scraping_duration_minutes': (time.time() - self.start_time) / 60,
                'description': 'Simplified scraper - only current season player data (no career stats)'
            },
            'players': self.all_players
        }
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {output_file}")
        print(f"   👥 Total players: {len(self.all_players)}")
        print(f"   📊 Completed series: {len(self.completed_series)}")
        print(f"   ⚡ SIMPLE MODE: Only basic player data (no career stats)")

def main():
    """Main function"""
    import sys
    
    # Show help if requested
    if "--help" in sys.argv or "-h" in sys.argv:
        print("CNSWPL Simple Player Scraper - Usage:")
        print("  python cnswpl_scrape_players_simple.py                    # Scrape all series (1-17 and A-K)")
        print("  python cnswpl_scrape_players_simple.py --series A,B,C     # Scrape specific series (A, B, C)")
        print("  python cnswpl_scrape_players_simple.py --series=1,2,3     # Scrape specific series (1, 2, 3)")
        print("  python cnswpl_scrape_players_simple.py --help             # Show this help message")
        print("\nFEATURES:")
        print("  ⚡ SIMPLE MODE: Current season scores + player data (no career stats)")
        print("  🚀 FASTER: Skips career stats lookup for quicker execution")
        print("  📊 CURRENT SEASON: Player name, team, series, club, wins, losses")
        print("\nExamples:")
        print("  python cnswpl_scrape_players_simple.py --series A,B,C,D,E,F,G,H,I,J,K")
        print("  python cnswpl_scrape_players_simple.py --series 1,2,3")
        return
    
    # Parse command line arguments
    target_series = None
    
    # Check for series specification
    for i, arg in enumerate(sys.argv):
        if arg == "--series" and i + 1 < len(sys.argv):
            target_series = sys.argv[i + 1].split(',')
            break
        elif arg.startswith("--series="):
            target_series = arg.split("=", 1)[1].split(',')
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
        print(f"🏆 CNSWPL SIMPLE TARGETED SERIES SCRAPER")
        print(f"   Scraping specific series: {series_list}")
    else:
        print("🏆 CNSWPL SIMPLE COMPREHENSIVE ROSTER SCRAPER")
        print("   Scraping ALL series (1-17 and A-K) from roster pages")
    print("   ⚡ SIMPLE MODE: Only current season player data")
    print("============================================================")
    
    scraper = CNSWPLSimpleScraper(target_series=target_series)
    
    try:
        scraper.scrape_all_series()
        print("\n🎉 SIMPLE SCRAPING SESSION COMPLETED!")
        print("   Player data saved and ready for database import")
        
    except KeyboardInterrupt:
        print("\n⏸️ Scraping interrupted by user")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results(is_final=False)
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results(is_final=False)
    finally:
        # Clean up rally context
        if hasattr(scraper, 'rally_context') and scraper.rally_context:
            try:
                scraper.rally_context.quit()
                print("✅ Rally context (stealth browser) cleaned up")
            except:
                pass

if __name__ == "__main__":
    main()
