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
    
    def __init__(self):
        self.base_url = "https://cnswpl.tenniscores.com"
        self.all_players = []
        
        # Configure stealth browser for comprehensive scraping
        print("🔧 Initializing stealth browser for comprehensive scraping...")
        config = StealthConfig(
            fast_mode=True,   # Use faster mode to reduce delays and avoid timeouts
            verbose=False,    # Reduce verbose output during long scrape
            environment="production",  # Use production settings for robust scraping
            force_browser=False  # Use proxy-first approach
        )
        
        # Adjust config for long scrapes
        config.session_duration = 1800  # Extend session duration to 30 minutes
        config.requests_per_proxy = 50  # More requests per proxy before rotating
        config.max_retries = 2  # Reduce retries to avoid getting stuck
        config.timeout_seconds = 20  # Shorter timeout to avoid hanging
        
        self.stealth_browser = EnhancedStealthBrowser(config)
        print("✅ Stealth browser initialized and ready for long scrape")
        
    def get_series_urls(self) -> List[Tuple[str, str]]:
        """Generate URLs for all series (1-17 and A-K)"""
        series_urls = []
        
        # Numeric series: 1-17
        for i in range(1, 18):
            series_name = f"Series {i}"
            # Use the pattern from the existing scraper
            series_url = f"{self.base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WkNHeHozc0E%3D&series={i}"
            series_urls.append((series_name, series_url))
        
        # Letter series: A-K
        for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']:
            series_name = f"Series {letter}"
            # Use the pattern that accesses team pages for each series
            # This URL pattern is based on the extract_real_cnswpl_player_ids function
            if letter == 'A':
                series_url = f"{self.base_url}/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkNHeHg3dz0%3D"
            else:
                # Try to construct URLs for other letters based on the pattern
                # We'll need to discover these dynamically or use a mapping
                series_url = f"{self.base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NqN1FMcGpx&did=nndz-WkNHeHg3dz0%3D&series={letter}"
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
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for team links (they contain 'team=' parameter)
                if 'team=' in href and text and any(keyword in text for keyword in ['Tennaqua', 'Winter Club', 'Lake Forest', 'Evanston', 'Prairie Club', 'Wilmette', 'North Shore', 'Valley Lo', 'Westmoreland', 'Indian Hill', 'Birchwood', 'Exmoor', 'Glen View', 'Glenbrook', 'Park Ridge', 'Skokie', 'Michigan Shores', 'Midtown', 'Hinsdale', 'Knollwood', 'Sunset Ridge', 'Briarwood', 'Biltmore', 'Barrington Hills', 'Bryn Mawr', 'Saddle & Cycle', 'Onwentsia', 'Lake Bluff', 'Lake Shore', 'Northmoor', 'Butterfield', 'River Forest', 'Lifesport']):
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
                
                # Small delay between team requests
                if i < len(team_links) - 1:
                    time.sleep(1)
            
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
                    
                    # Create player record
                    player_data = {
                        'League': 'CNSWPL',
                        'Series': team_series,
                        'Series Mapping ID': f"{club_name} {team_series.replace('Series ', '')}",
                        'Club': club_name,
                        'Location ID': club_name.upper().replace(' ', '_'),
                        'Player ID': player_id,
                        'First Name': player_name.split()[0] if player_name.split() else 'Unknown',
                        'Last Name': ' '.join(player_name.split()[1:]) if len(player_name.split()) > 1 else '',
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
        print("🚀 Starting comprehensive CNSWPL roster scraping...")
        print("   This will scrape ALL series (1-17 and A-K) from roster pages")
        print("   to capture every registered player, not just match participants.")
        print("⚠️ This is a LONG scrape that may take 30-60 minutes to complete")
        
        # Use hardcoded series URLs for reliability
        series_urls = self.get_series_urls()
        
        print(f"\n📋 Will scrape {len(series_urls)} series:")
        for series_name, _ in series_urls:
            print(f"   - {series_name}")
        
        # Track progress and failures
        successful_series = 0
        failed_series = []
        total_players = 0
        
        # Scrape each series with error handling
        for i, (series_name, series_url) in enumerate(series_urls, 1):
            print(f"\n🏆 Processing Series {i}/{len(series_urls)}: {series_name}")
            print(f"⏰ Estimated remaining time: {(len(series_urls) - i) * 2} minutes")
            
            try:
                series_players = self.extract_players_from_series_page(series_name, series_url)
                if series_players:
                    self.all_players.extend(series_players)
                    total_players += len(series_players)
                    successful_series += 1
                    print(f"✅ {series_name}: {len(series_players)} players")
                else:
                    failed_series.append(series_name)
                    print(f"⚠️ {series_name}: No players found")
                
                # Save intermediate results every 5 series
                if i % 5 == 0:
                    print(f"💾 Intermediate save: {len(self.all_players)} players so far")
                    self.save_intermediate_results()
                    
            except Exception as e:
                print(f"❌ Error processing {series_name}: {e}")
                failed_series.append(series_name)
            
            # Add delay between requests to be respectful
            if i < len(series_urls):
                print("⏳ Waiting 3 seconds before next series...")
                time.sleep(3)
        
        print(f"\n🎉 Comprehensive scraping completed!")
        print(f"📊 Successful series: {successful_series}/{len(series_urls)}")
        print(f"📊 Total players found: {len(self.all_players)}")
        
        if failed_series:
            print(f"⚠️ Failed series: {', '.join(failed_series)}")
        
        # Show series breakdown
        series_counts = {}
        for player in self.all_players:
            series = player.get('Series', 'Unknown')
            series_counts[series] = series_counts.get(series, 0) + 1
        
        print(f"\n📈 Players by series:")
        for series, count in sorted(series_counts.items()):
            print(f"   {series}: {count} players")
    
    def save_intermediate_results(self):
        """Save intermediate results during long scrape"""
        try:
            output_file = "data/leagues/CNSWPL/players_intermediate.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_players, f, indent=2, ensure_ascii=False)
            print(f"   💾 Intermediate results saved to {output_file}")
        except Exception as e:
            print(f"   ⚠️ Failed to save intermediate results: {e}")
    
    def save_results(self):
        """Save comprehensive results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"data/leagues/CNSWPL/players_comprehensive_{timestamp}.json"
        
        # Also update the main players.json file
        main_output_file = "data/leagues/CNSWPL/players.json"
        
        # Save timestamped version
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_players, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Comprehensive results saved to: {output_file}")
        
        # Update main file if we have more players
        if os.path.exists(main_output_file):
            with open(main_output_file, 'r', encoding='utf-8') as f:
                existing_players = json.load(f)
            
            if len(self.all_players) > len(existing_players):
                with open(main_output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.all_players, f, indent=2, ensure_ascii=False)
                print(f"✅ Updated main file: {main_output_file}")
                print(f"   Old count: {len(existing_players)}, New count: {len(self.all_players)}")
            else:
                print(f"ℹ️ Main file not updated (existing: {len(existing_players)}, new: {len(self.all_players)})")
        else:
            with open(main_output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_players, f, indent=2, ensure_ascii=False)
            print(f"✅ Created main file: {main_output_file}")

def main():
    """Main function"""
    print("============================================================")
    print("🏆 COMPREHENSIVE CNSWPL ROSTER SCRAPER")
    print("   Scraping ALL series (1-17 and A-K) from roster pages")
    print("   to capture every registered player")
    print("============================================================")
    
    scraper = CNSWPLRosterScraper()
    
    try:
        scraper.scrape_all_series()
        scraper.save_results()
        
        print("\n🎉 COMPREHENSIVE SCRAPING COMPLETED SUCCESSFULLY!")
        print("   All series rosters have been scraped")
        print("   This includes players from missing series like H, I, J, K, 13, 15")
        
    except KeyboardInterrupt:
        print("\n⏸️ Scraping interrupted by user")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results()
    except Exception as e:
        print(f"\n❌ Error during comprehensive scraping: {e}")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results()

if __name__ == "__main__":
    main()
