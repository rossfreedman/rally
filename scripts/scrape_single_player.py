#!/usr/bin/env python3
"""
Single Player Scraper

Fetches data for a single player from APTA Chicago or CNSWPL using their player ID.
This is useful for fixing missing player records without running a full ETL.

Usage:
    python3 scrape_single_player.py nndz-WkM2eHhMZjVoZz09
    python3 scrape_single_player.py nndz-WkM2eHhMZjVoZz09 --league APTA_CHICAGO
    python3 scrape_single_player.py cnswpl_abc123 --league CNSWPL
"""

import sys
import os
import re
import argparse
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import requests for HTTP
import requests

# Try to import Rally's stealth browser
try:
    from data.etl.scrapers.helpers.stealth_browser import create_stealth_browser
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    print("⚠️ Stealth browser not available, using basic requests")

def fetch_apta_player(player_id):
    """Fetch player data from APTA Chicago website"""
    print(f"\n🎾 Fetching APTA Chicago player: {player_id}")
    
    # Construct player profile URL
    base_url = "https://aptachicago.tenniscores.com"
    player_url = f"{base_url}/?p={player_id}"
    
    print(f"   URL: {player_url}")
    
    # Fetch the page
    html_content = None
    
    if STEALTH_AVAILABLE:
        print("   Using stealth browser...")
        try:
            rally_context = create_stealth_browser(fast_mode=True, verbose=False)
            if rally_context:
                # Use the get_html method
                html_content = rally_context.get_html(player_url)
                rally_context.close()
        except Exception as e:
            print(f"   ⚠️ Stealth browser failed: {e}")
    
    if not html_content:
        print("   Using standard requests...")
        try:
            response = requests.get(player_url, timeout=30)
            if response.status_code == 200:
                html_content = response.text
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            return None
    
    if not html_content:
        print("   ❌ Failed to fetch player page")
        return None
    
    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract player information
    player_data = {
        'tenniscores_player_id': player_id,
        'league': 'APTA_CHICAGO',
        'first_name': None,
        'last_name': None,
        'team': None,
        'club': None,
        'series': None,
        'pti': None,
        'wins': None,
        'losses': None
    }
    
    # Method 1: Look for player name in page title or heading
    title = soup.find('title')
    if title:
        title_text = title.get_text(strip=True)
        print(f"   Page title: {title_text}")
        
        # Extract name from title (usually "FirstName LastName - APTA Chicago")
        name_match = re.match(r'^([^-]+)', title_text)
        if name_match:
            full_name = name_match.group(1).strip()
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                player_data['first_name'] = name_parts[0]
                player_data['last_name'] = ' '.join(name_parts[1:])
    
    # Method 2: Look for h1 or h2 headings with player name
    if not player_data['first_name']:
        for heading_tag in ['h1', 'h2', 'h3']:
            headings = soup.find_all(heading_tag)
            for heading in headings:
                text = heading.get_text(strip=True)
                # Skip common headings that aren't player names
                if text and not any(skip in text.lower() for skip in ['schedule', 'standings', 'stats', 'career', 'current season']):
                    name_parts = text.split()
                    if len(name_parts) >= 2:
                        player_data['first_name'] = name_parts[0]
                        player_data['last_name'] = ' '.join(name_parts[1:])
                        break
            if player_data['first_name']:
                break
    
    # Method 3: Look for profile/bio section
    if not player_data['first_name']:
        # Look for common profile containers
        profile_containers = soup.find_all(['div', 'section'], class_=re.compile(r'profile|player|bio', re.I))
        for container in profile_containers:
            text = container.get_text(strip=True)
            if text:
                name_parts = text.split()[:2]  # First two words
                if len(name_parts) >= 2:
                    player_data['first_name'] = name_parts[0]
                    player_data['last_name'] = name_parts[1]
                    break
    
    # Extract team/club/series information
    # Look for tables or lists containing player stats
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                
                if 'team' in label and not player_data['team']:
                    player_data['team'] = value
                elif 'club' in label and not player_data['club']:
                    player_data['club'] = value
                elif 'series' in label and not player_data['series']:
                    player_data['series'] = value
                elif 'pti' in label and not player_data['pti']:
                    try:
                        player_data['pti'] = float(value)
                    except:
                        pass
                elif 'win' in label and not player_data['wins']:
                    # Extract number from "Wins: 10" or "10-5"
                    numbers = re.findall(r'\d+', value)
                    if numbers:
                        player_data['wins'] = int(numbers[0])
                elif 'loss' in label and not player_data['losses']:
                    numbers = re.findall(r'\d+', value)
                    if numbers:
                        player_data['losses'] = int(numbers[0])
    
    # Look for series information in links
    if not player_data['series']:
        series_links = soup.find_all('a', href=re.compile(r'did='))
        for link in series_links:
            text = link.get_text(strip=True)
            if 'Series' in text or re.match(r'^\d+', text):
                player_data['series'] = text
                break
    
    # Print what we found
    print("\n   ✅ Extracted player data:")
    for key, value in player_data.items():
        if value:
            print(f"      {key}: {value}")
    
    return player_data

def fetch_cnswpl_player(player_id):
    """Fetch player data from CNSWPL website"""
    print(f"\n🎾 Fetching CNSWPL player: {player_id}")
    print("   ⚠️ CNSWPL scraping not yet implemented")
    return None

def save_to_database(player_data):
    """Save player data to the database"""
    from database_utils import execute_query_one, execute_query
    
    print("\n💾 Saving to database...")
    
    # Check if player already exists
    check_query = "SELECT id, first_name, last_name FROM players WHERE tenniscores_player_id = %s"
    existing = execute_query_one(check_query, [player_data['tenniscores_player_id']])
    
    if existing:
        print(f"   ⚠️ Player already exists: {existing['first_name']} {existing['last_name']} (ID: {existing['id']})")
        response = input("   Update existing player? (y/n): ")
        if response.lower() != 'y':
            print("   Aborted.")
            return False
        
        # Update existing player
        update_query = """
        UPDATE players
        SET first_name = %s,
            last_name = %s
        WHERE tenniscores_player_id = %s
        RETURNING id
        """
        result = execute_query_one(update_query, [
            player_data['first_name'],
            player_data['last_name'],
            player_data['tenniscores_player_id']
        ])
        
        if result:
            print(f"   ✅ Updated player ID {result['id']}")
            return True
        else:
            print("   ❌ Update failed")
            return False
    else:
        # Get league_id
        league_query = "SELECT id FROM leagues WHERE league_id = %s"
        league = execute_query_one(league_query, [player_data['league']])
        
        if not league:
            print(f"   ❌ League '{player_data['league']}' not found in database")
            return False
        
        league_id = league['id']
        
        # Create new player (with minimal required fields)
        # We'll need to get club_id and series_id if required
        print("   ℹ️ Creating new player with basic info (no team/club/series)")
        
        # Get or create Unknown club
        club_query = "SELECT id FROM clubs WHERE name = %s"
        club = execute_query_one(club_query, ['Unknown Club'])
        
        if not club:
            club_insert = "INSERT INTO clubs (name) VALUES (%s) RETURNING id"
            club = execute_query_one(club_insert, ['Unknown Club'])
        
        club_id = club['id']
        
        # Get or create Unknown series
        series_query = "SELECT id FROM series WHERE name = %s AND league_id = %s"
        series = execute_query_one(series_query, ['Unknown Series', league_id])
        
        if not series:
            series_insert = "INSERT INTO series (name, league_id, display_name) VALUES (%s, %s, %s) RETURNING id"
            series = execute_query_one(series_insert, ['Unknown Series', league_id, 'Unknown Series'])
        
        series_id = series['id']
        
        # Insert player
        insert_query = """
        INSERT INTO players (
            tenniscores_player_id,
            first_name,
            last_name,
            league_id,
            club_id,
            series_id,
            is_active
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        
        result = execute_query_one(insert_query, [
            player_data['tenniscores_player_id'],
            player_data['first_name'],
            player_data['last_name'],
            league_id,
            club_id,
            series_id,
            True
        ])
        
        if result:
            print(f"   ✅ Created new player ID {result['id']}")
            return True
        else:
            print("   ❌ Insert failed")
            return False

def main():
    parser = argparse.ArgumentParser(description='Scrape a single player from APTA or CNSWPL')
    parser.add_argument('player_id', help='Player ID (e.g., nndz-WkM2eHhMZjVoZz09)')
    parser.add_argument('--league', default='APTA_CHICAGO', 
                       choices=['APTA_CHICAGO', 'CNSWPL'],
                       help='League to scrape from')
    parser.add_argument('--save', action='store_true', help='Save to database')
    args = parser.parse_args()
    
    print("=" * 70)
    print("SINGLE PLAYER SCRAPER")
    print("=" * 70)
    
    # Fetch player data
    if args.league == 'APTA_CHICAGO':
        player_data = fetch_apta_player(args.player_id)
    elif args.league == 'CNSWPL':
        player_data = fetch_cnswpl_player(args.player_id)
    else:
        print(f"❌ Unknown league: {args.league}")
        return
    
    if not player_data:
        print("\n❌ Failed to fetch player data")
        return
    
    if not player_data.get('first_name') or not player_data.get('last_name'):
        print("\n❌ Could not extract player name from page")
        return
    
    # Save to database if requested
    if args.save:
        save_to_database(player_data)
    else:
        print("\n💡 Run with --save to save this player to the database")

if __name__ == "__main__":
    main()

