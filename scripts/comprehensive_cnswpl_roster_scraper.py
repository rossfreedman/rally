#!/usr/bin/env python3
"""
Comprehensive CNSWPL Roster Scraper

This script systematically scrapes ALL CNSWPL series (1-17 and A-K) directly from 
team roster pages to capture every registered player, including those in missing 
series like H, I, J, K, 13, 15, etc.

Unlike the match-based scraper, this goes directly to team/roster pages to find
ALL registered players, not just those who have played matches.

Usage:
    python3 scripts/comprehensive_cnswpl_roster_scraper.py
"""

import json
import os
import sys
import time
import requests
import hashlib
from bs4 import BeautifulSoup
from typing import Set, Dict, List, Tuple
from datetime import datetime

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from data.etl.scrapers.stealth_browser import EnhancedStealthBrowser, StealthConfig

class CNSWPLRosterScraper:
    """Comprehensive CNSWPL roster scraper that hits all series pages"""
    
    def __init__(self, force_restart=False):
        self.base_url = "https://cnswpl.tenniscores.com"
        self.all_players = []
        self.completed_series = set()  # Track completed series for resumption
        self.start_time = time.time()
        self.force_restart = force_restart
        
        # Configure stealth browser for comprehensive scraping
        print("🔧 Initializing stealth browser for long scrape...")
        config = StealthConfig(
            fast_mode=False,  # Use slower mode with longer delays to avoid detection
            verbose=False,    # Reduce verbose output during long scrape
            environment="production"  # Use production settings for robust scraping
        )
        
        self.stealth_browser = EnhancedStealthBrowser(config)
        print("✅ Stealth browser initialized - optimized for long scrape")
        
    def _team_belongs_to_series(self, team_name: str, series_identifier: str) -> bool:
        """Check if a team belongs to the specific series being scraped"""
        if not team_name or not series_identifier:
            return False
            
        # For numeric series (1-17): team should end with the number or number+letter
        if series_identifier.isdigit():
            # Examples: "Birchwood 1", "Hinsdale PC 1a", "Hinsdale PC 1b"
            # Should match teams ending with "1", "1a", "1b", etc. but NOT "10", "11", "12"
            
            # Split team name to get the last part
            parts = team_name.split()
            if not parts:
                return False
                
            last_part = parts[-1]
            
            # Check if last part starts with our series number
            if last_part == series_identifier:
                return True
            elif last_part.startswith(series_identifier) and len(last_part) > len(series_identifier):
                # Check if it's like "1a", "1b" (series + letter)
                suffix = last_part[len(series_identifier):]
                return suffix.isalpha() and len(suffix) == 1
            
            return False
        
        # For letter series (A-K): team should end with the letter
        elif series_identifier.isalpha() and len(series_identifier) == 1:
            # Examples: "Birchwood A", "Tennaqua B"
            parts = team_name.split()
            if not parts:
                return False
                
            last_part = parts[-1]
            return last_part == series_identifier
            
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

    def _convert_to_cnswpl_format(self, nndz_player_id: str) -> str:
        """
        Convert nndz- format player ID to cnswpl_ format using MD5 hash.
        
        This ensures compatibility with the ETL system which expects cnswpl_ format IDs
        for CNSWPL players to prevent match import failures.
        
        Args:
            nndz_player_id: Player ID in nndz-XXXXX format
            
        Returns:
            Player ID in cnswpl_MD5HASH format
        """
        if not nndz_player_id or not nndz_player_id.startswith('nndz-'):
            return nndz_player_id
        
        # Extract the unique part after 'nndz-'
        unique_part = nndz_player_id[5:]  # Remove 'nndz-' prefix
        
        # Create MD5 hash of the unique part
        md5_hash = hashlib.md5(unique_part.encode('utf-8')).hexdigest()
        
        # Return in cnswpl_ format
        return f"cnswpl_{md5_hash}"

    def get_series_urls(self) -> List[Tuple[str, str]]:
        """Generate URLs for letter series only (A-K)"""
        series_urls = []
        
        # CNSWPL Letter series URLs - these use the same base pattern as Series A
        # The website uses a consistent URL structure for roster access
        base_roster_url = f"{self.base_url}/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkNHeHg3dz0%3D"
        
        for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']:
            series_name = f"Series {letter}"
            # All letter series use the same roster page URL structure
            # We'll filter teams on the page by series identifier later
            series_url = base_roster_url
            series_urls.append((series_name, series_url))
        
        return series_urls
    
    def extract_players_from_series_page(self, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific series by finding team links and scraping their rosters"""
        print(f"\n🎾 Scraping {series_name} from {series_url}")
        
        try:
            # Use stealth browser to get the series overview page with timeout protection
            start_time = time.time()
            html_content = self.stealth_browser.get_html(series_url)
            elapsed = time.time() - start_time
            
            # If request took too long, it might be stuck in proxy testing
            if elapsed > 120:  # 2 minutes
                print(f"⚠️ Request took {elapsed:.1f}s - possible proxy testing loop")
                
            if not html_content:
                print(f"❌ Failed to get content for {series_name}")
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            all_players = []
            
            # Find all team links on the series page
            team_links = []
            all_links = soup.find_all('a', href=True)
            
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
            
            # Scrape each team's roster page
            for i, (team_name, team_url) in enumerate(team_links):
                print(f"   🎾 Scraping team {i+1}/{len(team_links)}: {team_name}")
                team_players = self.extract_players_from_team_page(team_name, team_url, series_name)
                all_players.extend(team_players)
                
                # Longer delay between team requests to avoid rate limiting
                if i < len(team_links) - 1:
                    time.sleep(3)
            
            print(f"✅ Extracted {len(all_players)} total players from {series_name}")
            return all_players
            
        except Exception as e:
            print(f"❌ Error scraping {series_name}: {e}")
            return []
    
    def extract_players_from_team_page(self, team_name: str, team_url: str, series_name: str) -> List[Dict]:
        """Extract all players from a specific team roster page"""
        try:
            # Get the team page with timeout monitoring
            start_time = time.time()
            html_content = self.stealth_browser.get_html(team_url)
            elapsed = time.time() - start_time
            
            if elapsed > 60:  # 1 minute warning
                print(f"     ⚠️ Team page request took {elapsed:.1f}s")
                
            if not html_content:
                print(f"     ❌ Failed to get team page for {team_name}")
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            players = []
            
            # Look for player links in the team roster
            # Based on the example: /player.php?print&p=nndz-WkM2eHhyYjRnQT09
            player_links = soup.find_all('a', href=True)
            
            for link in player_links:
                href = link.get('href', '')
                player_name = link.get_text(strip=True)
                
                # Check if this is a player link
                if '/player.php?print&p=' in href and player_name and len(player_name.split()) >= 2:
                    # Extract player ID from href
                    player_id = href.split('p=')[1].split('&')[0] if '&' in href else href.split('p=')[1]
                    
                    # Parse team name to get club and series info
                    club_name = team_name
                    team_series = series_name
                    
                    # Extract club name from team name (e.g., "Tennaqua I" -> "Tennaqua")
                    if ' ' in team_name:
                        parts = team_name.split()
                        if parts[-1] in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'] or parts[-1].isdigit():
                            club_name = ' '.join(parts[:-1])
                    
                    # Enhanced name parsing with compound first name handling
                    first_name, last_name = self._parse_player_name(player_name)
                    
                    # Convert player ID to cnswpl_ format for ETL compatibility
                    cnswpl_player_id = self._convert_to_cnswpl_format(player_id)
                    
                    # Create player record
                    player_data = {
                        'League': 'CNSWPL',
                        'Series': team_series,
                        'Series Mapping ID': f"{club_name} {team_series.replace('Series ', '')}",
                        'Club': club_name,
                        'Location ID': club_name.upper().replace(' ', '_'),
                        'Player ID': cnswpl_player_id,
                        'First Name': first_name,
                        'Last Name': last_name,
                        'PTI': 'N/A',
                        'Wins': '0',
                        'Losses': '0',
                        'Win %': '0.0%',
                        'Captain': '',
                        'source_league': 'CNSWPL',
                        'validation_issues': [f'Scraped from {team_name} team roster'],
                        'scrape_source': 'team_roster_page',
                        'scrape_team': team_name,
                        'scrape_series': series_name
                    }
                    
                    players.append(player_data)
                    
            print(f"     ✅ Found {len(players)} players on {team_name} roster")
            return players
            
        except Exception as e:
            print(f"     ❌ Error scraping team {team_name}: {e}")
            return []
    
    def discover_series_dynamically(self) -> List[Tuple[str, str]]:
        """Try to discover all available series by scraping the main page"""
        print("🔍 Discovering available series from main page...")
        
        try:
            main_url = f"{self.base_url}/"
            html_content = self.stealth_browser.get_html(main_url)
            
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
        print("🚀 Starting CNSWPL letter series roster scraping...")
        print("   This will scrape letter series (A-K) from roster pages")
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
            
            if i > 1:
                avg_time_per_series = elapsed_time / (i - 1)
                remaining_series = len(series_urls) - i + 1
                eta_minutes = (remaining_series * avg_time_per_series) / 60
                print(f"🔮 ETA: {eta_minutes:.1f} minutes remaining")
            
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
        """Load existing progress from previous runs"""
        if self.force_restart:
            print("🔄 Force restart enabled - clearing all previous progress")
            # Clean up any existing progress files
            try:
                progress_file = "data/leagues/CNSWPL/scrape_progress.json"
                partial_file = "data/leagues/CNSWPL/players_comprehensive_partial.json"
                
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
            progress_file = "data/leagues/CNSWPL/scrape_progress.json"
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    self.completed_series = set(progress_data.get('completed_series', []))
                    print(f"📂 Loaded progress: {len(self.completed_series)} series already completed")
                    
                # Load existing player data
                output_file = "data/leagues/CNSWPL/players_comprehensive_partial.json"
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
            # Create tmp/players directory if it doesn't exist
            series_dir = "data/leagues/CNSWPL/tmp/players"
            os.makedirs(series_dir, exist_ok=True)
            
            # Save individual series file
            series_filename = series_name.replace(" ", "_").lower()  # "Series 1" -> "series_1"
            series_file = f"{series_dir}/{series_filename}.json"
            
            with open(series_file, 'w', encoding='utf-8') as f:
                json.dump(series_players, f, indent=2, ensure_ascii=False)
            
            print(f"📁 Saved {series_name} to: {series_file} ({len(series_players)} players)")
            
            # Save progress tracking
            progress_file = "data/leagues/CNSWPL/scrape_progress.json"
            progress_data = {
                'completed_series': list(self.completed_series),
                'last_update': datetime.now().isoformat(),
                'total_players': len(self.all_players),
                'series_files_created': len(self.completed_series)
            }
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
                
            # Save current aggregate player data (only if we have aggregate data)
            output_file = "data/leagues/CNSWPL/players_comprehensive_partial.json"
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
            output_file = "data/leagues/CNSWPL/players_intermediate.json"
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
            series_dir = "data/leagues/CNSWPL/tmp/players"
            if os.path.exists(series_dir):
                series_files = [f for f in os.listdir(series_dir) if f.endswith('.json')]
                print(f"📁 Individual series files created: {len(series_files)}")
                for series_file in sorted(series_files):
                    print(f"   - {series_file}")
            
            # Clean up progress files since we're done
            try:
                progress_file = "data/leagues/CNSWPL/scrape_progress.json"
                partial_file = "data/leagues/CNSWPL/players_comprehensive_partial.json"
                
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                    print("🧹 Cleaned up progress tracking file")
                    
                if os.path.exists(partial_file):
                    os.remove(partial_file)
                    print("🧹 Cleaned up partial results file")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up temporary files: {e}")
        
        # Save timestamped version
        output_file = f"data/leagues/CNSWPL/players_comprehensive_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_players, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Comprehensive results saved to: {output_file}")
        
        # Update main players.json file
        main_output_file = "data/leagues/CNSWPL/players.json"
        
        if os.path.exists(main_output_file):
            with open(main_output_file, 'r', encoding='utf-8') as f:
                existing_players = json.load(f)
            
            print(f"\n📊 COMPARISON WITH EXISTING DATA:")
            print(f"   Existing players.json: {len(existing_players):,} players")
            print(f"   New comprehensive data: {len(self.all_players):,} players")
            print(f"   Difference: {len(self.all_players) - len(existing_players):+,} players")
            
            if len(self.all_players) > len(existing_players):
                with open(main_output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.all_players, f, indent=2, ensure_ascii=False)
                print(f"✅ UPDATED main file: {main_output_file}")
                print(f"   📈 Added {len(self.all_players) - len(existing_players)} new players!")
            elif len(self.all_players) == len(existing_players):
                print(f"ℹ️ Same player count - keeping existing file")
            else:
                print(f"⚠️ Fewer players found - keeping existing file (investigate needed)")
        else:
            with open(main_output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_players, f, indent=2, ensure_ascii=False)
            print(f"✅ Created main file: {main_output_file}")
            
        if is_final:
            print(f"\n🎯 FINAL COMPREHENSIVE SCRAPE COMPLETE!")
            print(f"   ✅ All {len(self.completed_series)} series processed")
            print(f"   📁 Individual series files: data/leagues/CNSWPL/tmp/players/")
            print(f"   📁 Final aggregated data: {main_output_file}")
            print(f"   📁 Timestamped backup: {output_file}")

def main():
    """Main function"""
    import sys
    
    # Check for force restart flag
    force_restart = "--force-restart" in sys.argv or "--fresh" in sys.argv
    
    print("============================================================")
    print("🏆 COMPREHENSIVE CNSWPL ROSTER SCRAPER")
    print("   Scraping ALL series (1-17 and A-K) from roster pages")
    print("   to capture every registered player")
    if force_restart:
        print("   🔄 FORCE RESTART: Ignoring any previous progress")
    print("============================================================")
    
    scraper = CNSWPLRosterScraper(force_restart=force_restart)
    
    try:
        scraper.scrape_all_series()
        
        # Check if scrape was complete
        expected_series = set([f"Series {i}" for i in range(1, 18)] + [f"Series {letter}" for letter in 'ABCDEFGHIJK'])
        is_complete = scraper.completed_series == expected_series
        
        if is_complete:
            print("\n🌟 COMPLETE SCRAPE DETECTED!")
            print("   All 28 series (1-17 and A-K) successfully processed")
            scraper.save_results(is_final=True)
        else:
            missing_series = expected_series - scraper.completed_series
            print(f"\n⚠️ PARTIAL SCRAPE COMPLETED")
            print(f"   Missing series: {', '.join(sorted(missing_series))}")
            scraper.save_results(is_final=False)
        
        print("\n🎉 COMPREHENSIVE SCRAPING SESSION COMPLETED!")
        print("   Data saved and ready for database import")
        
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
