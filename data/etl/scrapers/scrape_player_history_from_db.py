#!/usr/bin/env python3
"""
Database-Driven Player History Scraper
=======================================
Uses existing player IDs from database to build deep link URLs.
Avoids listing page captchas by scraping individual player pages directly.

Key Features:
- Queries database for player IDs (tenniscores_player_id)
- Builds deep link URLs: ?mod=nndz-SkhmOW1PQ3V4dXBjakNnUA%3D%3D&uid={player_id}
- Uses proxy/stealth management for individual page scraping
- Updates player history without needing listing page access
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional
import warnings

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="_distutils_hack")
warnings.filterwarnings("ignore", category=UserWarning, module="setuptools")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

from bs4 import BeautifulSoup

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.etl.scrapers.helpers.proxy_manager import fetch_with_retry
from data.etl.scrapers.helpers.stealth_browser import create_stealth_browser
from utils.league_utils import standardize_league_id

# Database imports
try:
    from database import get_db
except ImportError:
    # Fallback for when running from different contexts
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from database import get_db


def get_players_from_database(league_subdomain: str) -> List[Dict]:
    """
    Query database for all players with tenniscores_player_id for a given league.
    
    Args:
        league_subdomain: League subdomain (e.g., 'apta', 'nstf')
    
    Returns:
        List of player dictionaries with ID and metadata
    """
    league_id = standardize_league_id(league_subdomain)
    
    print(f"📊 Querying database for {league_id} players...")
    
    with get_db() as conn:
        cur = conn.cursor()
        
        # First, get the numeric league_id from leagues table
        league_lookup_query = """
            SELECT id FROM leagues WHERE LOWER(league_id) = %s OR LOWER(league_name) LIKE %s LIMIT 1
        """
        cur.execute(league_lookup_query, (league_id.lower(), f"%{league_subdomain.lower()}%"))
        league_row = cur.fetchone()
        
        if not league_row:
            print(f"❌ League '{league_subdomain}' not found in database")
            cur.close()
            return []
        
        league_db_id = league_row[0]
        print(f"   League ID in database: {league_db_id}")
        
        # Query players with tenniscores_player_id
        query = """
            SELECT 
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                c.name AS club_name,
                s.name AS series_name,
                p.pti
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.league_id = %s
                AND p.tenniscores_player_id IS NOT NULL
                AND p.tenniscores_player_id != ''
                AND p.tenniscores_player_id LIKE 'nndz-%%'
            ORDER BY p.first_name, p.last_name
        """
        
        cur.execute(query, (league_db_id,))
        rows = cur.fetchall()
        
        players = []
        for row in rows:
            first_name = row[1] or ''
            last_name = row[2] or ''
            full_name = f"{first_name} {last_name}".strip()
            
            players.append({
                'tenniscores_player_id': row[0],
                'name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'club': row[3] or 'Unknown',
                'series': row[4] or 'Unknown',
                'rating': str(row[5]) if row[5] else '0.0'
            })
        
        cur.close()
        
        print(f"✅ Found {len(players)} players with tenniscores IDs")
        return players


def build_player_url(base_url: str, player_id: str) -> str:
    """
    Build deep link URL for individual player page.
    
    Args:
        base_url: League base URL (e.g., https://aptachicago.tenniscores.com)
        player_id: Player's tenniscores ID (e.g., nndz-WkNHNXc3ajdodz09)
    
    Returns:
        Full player page URL
    """
    # Player page module ID (same for all leagues)
    player_mod = "nndz-SkhmOW1PQ3V4dXBjakNnUA%3D%3D"
    return f"{base_url}/?mod={player_mod}&uid={player_id}"


def scrape_player_page(player_url: str, use_stealth: bool = False) -> Optional[Dict]:
    """
    Scrape individual player page for match history.
    
    Args:
        player_url: Full URL to player page
        use_stealth: Whether to use stealth browser (fallback if proxy fails)
    
    Returns:
        Dictionary with player stats and match history, or None if failed
    """
    try:
        if use_stealth:
            # Use stealth browser
            browser = create_stealth_browser(
                fast_mode=True,
                verbose=False,
                environment="production"
            )
            
            if not browser:
                return None
            
            try:
                html = browser.get_html(player_url)
            finally:
                browser.quit()
        else:
            # Use proxy request (faster)
            response = fetch_with_retry(player_url, timeout=15)
            if not response or response.status_code != 200:
                return None
            html = response.text
        
        if not html or len(html) < 1000:
            return None
        
        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract match records
        match_details = []
        for rbox in soup.find_all('div', class_='rbox_top'):
            # Extract date
            date_div = rbox.find('div', class_='rbox_inner')
            match_date = None
            if date_div:
                date_text = date_div.get_text(strip=True)
                match_date = date_text.split()[0] if date_text else None
            
            # Extract series
            series_divs = rbox.find_all('div', class_='rbox_inner')
            match_series = None
            if len(series_divs) > 1:
                match_series = series_divs[1].get_text(strip=True)
                if " - " in match_series:
                    match_series = match_series.split(" - ")[0]
            
            # Extract PTI (end rating)
            end_pti = None
            for pti_div in rbox.find_all('div', class_='rbox3top'):
                if "End" in pti_div.get_text():
                    span = pti_div.find('span', class_='demi')
                    if span:
                        end_pti = span.get_text(strip=True)
            
            if match_date and end_pti and match_series:
                # Convert date format if needed (DD-MMM-YY -> MM/DD/YYYY)
                formatted_date = convert_date_format(match_date)
                match_details.append({
                    "date": formatted_date,
                    "end_pti": str(end_pti),
                    "series": match_series
                })
        
        # Count wins/losses (simple pattern matching)
        import re
        wins = len(re.findall(r'\bW\b', html))
        losses = len(re.findall(r'\bL\b', html))
        
        return {
            "wins": wins,
            "losses": losses,
            "matches": match_details
        }
        
    except Exception as e:
        print(f"   ❌ Error scraping {player_url}: {e}")
        return None


def convert_date_format(date_str: str) -> str:
    """Convert date from DD-MMM-YY to MM/DD/YYYY format."""
    if not date_str:
        return date_str
    
    try:
        # Already in MM/DD/YYYY format
        if "/" in date_str and len(date_str) >= 8:
            return date_str
        # Convert DD-MMM-YY to MM/DD/YYYY
        elif "-" in date_str:
            from datetime import datetime
            dt = datetime.strptime(date_str, "%d-%b-%y")
            return dt.strftime("%m/%d/%Y")
        else:
            return date_str
    except:
        return date_str


def scrape_players_from_database(league_subdomain: str, max_players: int = None, test_mode: bool = False):
    """
    Main function: Scrape player history using database player IDs.
    
    Args:
        league_subdomain: League subdomain (e.g., 'apta', 'nstf')
        max_players: Maximum players to scrape (for testing)
        test_mode: Enable test mode
    """
    start_time = datetime.now()
    mode_text = f" (TEST MODE - {max_players} players)" if test_mode else ""
    
    print("\n" + "=" * 80)
    print(f"🚀 DATABASE-DRIVEN Player History Scraper{mode_text}")
    print("=" * 80)
    print(f"⏰ Started: {start_time.strftime('%m-%d-%y @ %I:%M:%S %p')}")
    print(f"🎯 League: {league_subdomain}")
    print()
    
    # Get league config
    league_id = standardize_league_id(league_subdomain)
    base_url = f"https://{league_subdomain}.tenniscores.com"
    
    # Build data directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    data_dir = os.path.join(project_root, "data", "leagues", league_id)
    os.makedirs(data_dir, exist_ok=True)
    
    try:
        # Phase 1: Get players from database
        print("📊 PHASE 1: Database Query")
        print("-" * 80)
        players = get_players_from_database(league_subdomain)
        
        if not players:
            print("❌ No players found in database with tenniscores IDs")
            return
        
        if test_mode and max_players:
            players = players[:max_players]
            print(f"🧪 Test mode: Limited to {len(players)} players")
        
        # Phase 2: Scrape individual player pages
        print(f"\n🎯 PHASE 2: Scraping {len(players)} Player Pages")
        print("-" * 80)
        
        all_players_data = []
        success_count = 0
        fail_count = 0
        
        for idx, player in enumerate(players, 1):
            player_id = player['tenniscores_player_id']
            player_name = player['name']
            
            # Build player URL
            player_url = build_player_url(base_url, player_id)
            
            # Progress update
            if idx % 10 == 0 or idx == 1:
                progress = (idx / len(players)) * 100
                print(f"   📊 Progress: {idx}/{len(players)} ({progress:.1f}%) - {player_name}")
            
            # Scrape player page (try proxy first, fallback to stealth)
            stats = scrape_player_page(player_url, use_stealth=False)
            
            if not stats:
                # Fallback to stealth browser
                stats = scrape_player_page(player_url, use_stealth=True)
            
            if stats:
                # Create player JSON
                player_json = {
                    "league_id": league_id,
                    "player_id": player_id,
                    "name": player_name,
                    "first_name": player['first_name'],
                    "last_name": player['last_name'],
                    "series": player['series'],
                    "club": player['club'],
                    "rating": player['rating'],
                    "wins": stats['wins'],
                    "losses": stats['losses'],
                    "matches": stats['matches']
                }
                all_players_data.append(player_json)
                success_count += 1
            else:
                fail_count += 1
                print(f"   ⚠️ Failed to scrape: {player_name}")
            
            # Small delay between requests
            time.sleep(0.3)
        
        # Phase 3: Save results
        print(f"\n💾 PHASE 3: Saving Results")
        print("-" * 80)
        
        if test_mode:
            filename = os.path.join(data_dir, f"player_history_db_test_{len(all_players_data)}_players.json")
        else:
            filename = os.path.join(data_dir, "player_history.json")
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_players_data, f, indent=2)
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        print("🎉 SCRAPING COMPLETE!")
        print("=" * 80)
        print(f"⏱️  Duration: {duration}")
        print(f"✅ Successful: {success_count}/{len(players)} ({(success_count/len(players)*100):.1f}%)")
        print(f"❌ Failed: {fail_count}/{len(players)} ({(fail_count/len(players)*100):.1f}%)")
        print(f"💾 Data saved to: {filename}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Database-Driven Player History Scraper")
    print("=" * 80)
    
    league = input("Enter league subdomain (e.g., apta, nstf): ").strip().lower()
    if not league:
        print("❌ No league subdomain provided. Exiting.")
        exit(1)
    
    # Test mode option
    test_mode_input = input("Enable test mode? (y/N): ").strip().lower()
    test_mode = test_mode_input == "y"
    max_players = None
    
    if test_mode:
        max_players = int(input("Enter max players for testing (default 10): ").strip() or 10)
    
    print(f"\n🌐 League: {league}")
    if test_mode:
        print(f"🧪 Test Mode: {max_players} players")
    print()
    
    scrape_players_from_database(league, max_players, test_mode)
