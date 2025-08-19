#!/usr/bin/env python3
"""
Simple CNSWPL Roster Scraper
Bypasses heavy proxy system for faster, more reliable scraping of team rosters.
"""

import sys
import os
import json
import requests
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class SimpleCNSWPLScraper:
    def __init__(self):
        self.base_url = "https://cnswpl.tenniscores.com"
        self.all_players = []
        
        # Simple session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def get_series_urls(self) -> List[Tuple[str, str]]:
        """Get all series URLs to scrape"""
        series_urls = []
        
        # Numeric series 1-17
        for num in range(1, 18):
            series_name = f"Series {num}"
            series_url = f"{self.base_url}/?mod=nndz-TjJiOWtORzQzTU4rakRrY1NqN1FMcGp4&did=nndz-WkNHeHg3dz0%3D&series={num}"
            series_urls.append((series_name, series_url))
        
        # Letter series A-K
        for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']:
            series_name = f"Series {letter}"
            series_url = f"{self.base_url}/?mod=nndz-TjJiOWtORzQzTU4rakRrY1NqN1FMcGp4&did=nndz-WkNHeHg3dz0%3D&series={letter}"
            series_urls.append((series_name, series_url))
        
        return series_urls
    
    def get_html(self, url: str) -> str:
        """Simple HTTP request with basic retry logic"""
        for attempt in range(3):
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    return response.text
                else:
                    print(f"     ⚠️ HTTP {response.status_code} for {url}")
            except Exception as e:
                print(f"     ⚠️ Request failed (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(2)
        
        return ""
    
    def extract_players_from_series_page(self, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific series by finding team links and scraping their rosters"""
        print(f"\n🎾 Scraping {series_name} from {series_url}")
        
        try:
            html_content = self.get_html(series_url)
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
                
                # Look for team links (they contain 'team=' parameter and club names)
                if 'team=' in href and text and any(keyword in text for keyword in [
                    'Tennaqua', 'Winter Club', 'Lake Forest', 'Evanston', 'Prairie Club', 
                    'Wilmette', 'North Shore', 'Valley Lo', 'Westmoreland', 'Indian Hill', 
                    'Birchwood', 'Exmoor', 'Glen View', 'Glenbrook', 'Park Ridge', 'Skokie', 
                    'Michigan Shores', 'Midtown', 'Hinsdale', 'Knollwood', 'Sunset Ridge', 
                    'Briarwood', 'Biltmore', 'Barrington Hills', 'Bryn Mawr', 'Saddle & Cycle', 
                    'Onwentsia', 'Lake Bluff', 'Lake Shore', 'Northmoor', 'Butterfield', 
                    'River Forest', 'Lifesport'
                ]):
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
                    time.sleep(0.5)  # Reduced delay for faster scraping
            
            print(f"✅ Extracted {len(all_players)} total players from {series_name}")
            return all_players
            
        except Exception as e:
            print(f"❌ Error scraping {series_name}: {e}")
            return []
    
    def extract_players_from_team_page(self, team_name: str, team_url: str, series_name: str) -> List[Dict]:
        """Extract all players from a specific team roster page"""
        try:
            html_content = self.get_html(team_url)
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
    
    def save_players_to_json(self):
        """Save all scraped players to the CNSWPL players.json file"""
        output_file = "data/leagues/CNSWPL/players.json"
        
        # Load existing players to merge
        existing_players = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_players = json.load(f)
                print(f"📁 Loaded {len(existing_players)} existing players")
            except Exception as e:
                print(f"⚠️ Could not load existing players: {e}")
        
        # Merge new players (avoid duplicates by Player ID)
        existing_ids = {player.get('Player ID') for player in existing_players}
        new_players = [p for p in self.all_players if p.get('Player ID') not in existing_ids]
        
        # Combine all players
        all_players = existing_players + new_players
        
        print(f"💾 Saving {len(all_players)} total players ({len(new_players)} new) to {output_file}")
        
        # Save to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_players, f, indent=2, ensure_ascii=False)
            print(f"✅ Successfully saved players to {output_file}")
        except Exception as e:
            print(f"❌ Error saving players: {e}")
    
    def run_comprehensive_scrape(self):
        """Run comprehensive scrape of all CNSWPL series"""
        print("🚀 Starting comprehensive CNSWPL roster scraping...")
        
        series_urls = self.get_series_urls()
        print(f"📋 Found {len(series_urls)} series to scrape")
        
        total_players = 0
        for i, (series_name, series_url) in enumerate(series_urls):
            print(f"\n📊 Progress: {i+1}/{len(series_urls)} series")
            series_players = self.extract_players_from_series_page(series_name, series_url)
            self.all_players.extend(series_players)
            total_players += len(series_players)
            
            # Small delay between series
            if i < len(series_urls) - 1:
                time.sleep(1)
        
        print(f"\n🎯 SCRAPING COMPLETE!")
        print(f"📊 Total players scraped: {total_players}")
        print(f"📊 Total unique players: {len(self.all_players)}")
        
        # Save results
        self.save_players_to_json()

def main():
    scraper = SimpleCNSWPLScraper()
    scraper.run_comprehensive_scrape()

if __name__ == "__main__":
    main()
