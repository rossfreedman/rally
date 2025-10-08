#!/usr/bin/env python3
"""
Quick SW Series Scraper - Bypasses proxy testing for faster execution
"""

import sys
import os
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Add the scrapers directory to the path
scrapers_path = os.path.join(os.path.dirname(__file__), 'data/etl/scrapers')
if scrapers_path not in sys.path:
    sys.path.insert(0, scrapers_path)

def scrape_sw_series():
    """Scrape only the missing SW series quickly"""
    
    # SW series URLs with correct paths
    sw_series = [
        ("Series 7 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMZz0%3D"),
        ("Series 9 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyZz0%3D"),
        ("Series 11 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhydz0%3D"),
        ("Series 13 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMYz0%3D"),
        ("Series 15 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXg3Yz0%3D"),
        ("Series 17 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyND0%3D"),
        ("Series 19 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyMD0%3D"),
        ("Series 21 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyOD0%3D"),
        ("Series 23 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMWT0%3D"),
        ("Series 25 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXg3WT0%3D"),
        ("Series 27 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkNHL3lMbz0%3D"),
        ("Series 29 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkM2eHg3dz0%3D"),
        ("Series 31 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WlNXK3licz0%3D"),
    ]
    
    print("🚀 Quick SW Series Scraper")
    print("=" * 50)
    print(f"📋 Scraping {len(sw_series)} SW series...")
    print()
    
    all_players = []
    
    # Load existing players
    players_file = "data/leagues/APTA_CHICAGO/players.json"
    if os.path.exists(players_file):
        with open(players_file, 'r') as f:
            all_players = json.load(f)
        print(f"📂 Loaded {len(all_players)} existing players")
    
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    for i, (series_name, url) in enumerate(sw_series, 1):
        print(f"🏆 Processing {i}/{len(sw_series)}: {series_name}")
        print(f"   URL: {url}")
        
        try:
            # Make request
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find team links
            team_links = soup.find_all('a', href=lambda x: x and 'team=' in x)
            print(f"   ✅ Found {len(team_links)} team links")
            
            series_players = []
            
            for team_link in team_links:
                team_name = team_link.get_text(strip=True)
                team_url = "https://aptachicago.tenniscores.com" + team_link['href']
                
                print(f"   📋 Processing team: {team_name}")
                
                try:
                    # Get team page
                    team_response = requests.get(team_url, headers=headers, timeout=30)
                    team_response.raise_for_status()
                    
                    team_soup = BeautifulSoup(team_response.content, 'html.parser')
                    
                    # Find player table
                    player_table = team_soup.find('table')
                    if not player_table:
                        print(f"     ❌ No player table found for {team_name}")
                        continue
                    
                    # Extract players
                    rows = player_table.find_all('tr')[1:]  # Skip header
                    team_players = []
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            # Extract player info
                            player_link = cells[0].find('a')
                            if player_link:
                                player_id = player_link['href'].split('p=')[-1] if 'p=' in player_link['href'] else ""
                                name_parts = player_link.get_text(strip=True).split()
                                first_name = name_parts[0] if name_parts else ""
                                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                                
                                # Extract PTI if available
                                pti = ""
                                if len(cells) > 1:
                                    pti_text = cells[1].get_text(strip=True)
                                    if pti_text and pti_text != "N/A":
                                        pti = pti_text
                                
                                # Check if captain
                                captain = "Yes" if "✔" in cells[0].get_text() else "No"
                                
                                player_data = {
                                    "Player ID": player_id,
                                    "First Name": first_name,
                                    "Last Name": last_name,
                                    "Team": team_name,
                                    "Series": series_name,
                                    "League": "APTA_CHICAGO",
                                    "Club": team_name.split(' - ')[0] if ' - ' in team_name else team_name,
                                    "PTI": pti,
                                    "Wins": "0",
                                    "Losses": "0",
                                    "Win %": "0.0%",
                                    "Captain": captain,
                                    "Source URL": team_url,
                                    "source_league": "APTA_CHICAGO",
                                    "Scraped At": datetime.now().isoformat()
                                }
                                
                                team_players.append(player_data)
                                print(f"     🔍 {first_name} {last_name} (PTI: {pti})")
                    
                    series_players.extend(team_players)
                    print(f"     ✅ Found {len(team_players)} players in {team_name}")
                    
                except Exception as e:
                    print(f"     ❌ Error processing team {team_name}: {e}")
                    continue
            
            all_players.extend(series_players)
            print(f"   ✅ {series_name}: {len(series_players)} players total")
            print()
            
        except Exception as e:
            print(f"   ❌ Error processing {series_name}: {e}")
            print()
            continue
    
    # Save updated players file
    with open(players_file, 'w') as f:
        json.dump(all_players, f, indent=2)
    
    print("🎉 SW Series Scraping Complete!")
    print(f"📊 Total players: {len(all_players)}")
    print(f"📁 Saved to: {players_file}")
    
    # Show summary
    sw_series_found = set()
    for player in all_players:
        if 'SW' in player['Series']:
            sw_series_found.add(player['Series'])
    
    print(f"\n🏆 SW Series Summary:")
    for series in sorted(sw_series_found):
        count = len([p for p in all_players if p['Series'] == series])
        print(f"  {series}: {count} players")

if __name__ == "__main__":
    scrape_sw_series()
