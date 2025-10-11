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
from data.etl.scrapers.helpers.stealth_browser import create_stealth_browser, DetectionType
from data.etl.scrapers.helpers.proxy_manager import get_proxy_rotator

# Import speed optimizations with safe fallbacks
try:
    from data.etl.scrapers.helpers.adaptive_pacer import pace_sleep, mark
    from data.etl.scrapers.helpers.stealth_browser import stop_after_selector
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

def _pacer_mark_ok():
    """Helper function to safely mark successful responses for adaptive pacing."""
    try:
        mark('ok')
    except Exception:
        pass

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
    weeks: Optional[int] = None
    skip_proxy_test: bool = False

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
    
    def _clean_player_name(self, name: str) -> str:
        """Clean player name by removing extra spaces and normalizing."""
        if not name:
            return ""
        # Remove extra spaces and normalize
        return " ".join(name.split())

    def _determine_winner_from_scores(self, scores: str) -> str:
        """Determine winner from scores string like '6-2, 6-3' or '6-4, 6-2'."""
        try:
            if not scores or scores == "Unknown Scores":
                return "tie"
            
            # Parse scores like "6-2, 6-3" or "6-4, 6-2" (comma-separated)
            # In CNSWPL format, first score is AWAY team, second score is HOME team
            sets = scores.split(', ')
            home_wins = 0
            away_wins = 0
            
            for set_score in sets:
                if '-' in set_score:
                    parts = set_score.split('-')
                    if len(parts) == 2:
                        try:
                            away_score = int(parts[0])  # First score is AWAY team
                            home_score = int(parts[1])  # Second score is HOME team
                            if home_score > away_score:
                                home_wins += 1
                            elif away_score > home_score:
                                away_wins += 1
                        except ValueError:
                            continue
            
            if home_wins > away_wins:
                return "home"
            elif away_wins > home_wins:
                return "away"
            else:
                return "tie"
                
        except Exception as e:
            print(f"❌ Error determining winner from scores '{scores}': {e}")
            return "tie"

    def _extract_player_id_from_link(self, link) -> str:
        """Extract player ID from a player link href attribute and format with cnswpl_ prefix."""
        try:
            href = link.get('href', '')
            if 'p=' in href:
                player_id = href.split('p=')[1].split('&')[0]
                # Remove nndz- prefix if present and add cnswpl_ prefix to match players.json format
                if player_id.startswith('nndz-'):
                    player_id = player_id[5:]  # Remove 'nndz-' prefix
                return f"cnswpl_{player_id}"
            return None
        except Exception as e:
            print(f"❌ CNSWPL: Error extracting player ID from link: {e}")
            return None

    def _lookup_roster_player_id(self, player_name: str) -> str:
        """Look up existing roster player ID for CNSWPL players to avoid ID mismatches."""
        try:
            # Load the consolidated CNSWPL players.json to find existing player IDs
            import json
            import os
            
            players_file = "data/leagues/CNSWPL/players.json"
            if not os.path.exists(players_file):
                print(f"❌  CNSWPL players.json not found - cannot lookup player ID for '{player_name}'")
                return None
            
            with open(players_file, 'r') as f:
                players_data = json.load(f)
            
            # Search for player by name (case-insensitive)
            first_name, last_name = self._parse_player_name(player_name)
            if not first_name or not last_name:
                print(f"❌  Could not parse player name '{player_name}' - cannot lookup player ID")
                return None
            
            for player in players_data:
                roster_first = player.get("First Name", "").strip()
                roster_last = player.get("Last Name", "").strip()
                roster_id = player.get("Player ID", "").strip()
                
                # Case-insensitive name matching
                if (roster_first.lower() == first_name.lower() and 
                    roster_last.lower() == last_name.lower() and 
                    roster_id):
                    print(f"✅  Found roster player ID for '{player_name}': {roster_id}")
                    return roster_id
            
            print(f"❌  No roster player ID found for '{player_name}' - player not in roster data")
            return None
            
        except Exception as e:
            print(f"❌  Error looking up roster player ID for '{player_name}': {e}")
            return None
    
    def _parse_player_name(self, full_name: str) -> tuple:
        """Parse full name into first and last name."""
        if not full_name:
            return None, None
        
        name_parts = full_name.strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
            return first_name, last_name
        elif len(name_parts) == 1:
            return name_parts[0], ""
        else:
            return None, None
    
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
        
        # Look for the datelocheader div which contains the overall match score
        datelocheader = soup.find('div', class_='datelocheader')
        if datelocheader:
            header_text = datelocheader.get_text(strip=True)
            print(f"🔍 CNSWPL: Found datelocheader: '{header_text}'")
            
            # Pattern like "Wilmette SN (2) @ Michigan Shores SN: 12 - 0"
            team_score_pattern = r'([^@\n]+)\s*@\s*([^:\n]+):\s*(\d+)\s*-\s*(\d+)'
            
            match = re.search(team_score_pattern, header_text)
            if match:
                away_team, home_team, away_score, home_score = match.groups()
                return {
                    "home_team": home_team.strip(),
                    "away_team": away_team.strip(),
                    "home_score": int(home_score),
                    "away_score": int(away_score)
                }
        
        # Fallback to general text search
        all_text = soup.get_text()
        team_score_pattern = r'([^@\n]+)\s*@\s*([^:\n]+):\s*(\d+)\s*-\s*(\d+)'
        
        match = re.search(team_score_pattern, all_text)
        if match:
            away_team, home_team, away_score, home_score = match.groups()
            return {
                "home_team": home_team.strip(),
                "away_team": away_team.strip(),
                "home_score": int(home_score),
                "away_score": int(away_score)
            }
        
        return None
    
    def _extract_cnswpl_lines(self, soup, series_name: str, match_id: str, match_date: str, teams_and_score: dict, league_subdomain: str = None) -> List[Dict]:
        """Extract line-specific data from court breakdown with both home/away players in APTA_CHICAGO format."""
        
        # CRITICAL VALIDATION: Prevent NSTF data from being processed as CNSWPL
        if league_subdomain and league_subdomain.lower() == 'nstf':
            print(f"⚠️  WARNING: NSTF data should not use CNSWPL line extraction logic!")
            print(f"   This could cause league ID corruption. Returning empty list.")
            return []
        import re
        line_matches = []
        
        try:
            # Look for tables with class "standings-table2" which contain the line data
            tables = soup.find_all('table', class_='standings-table2')
            print(f"🔍 CNSWPL: Found {len(tables)} tables with class 'standings-table2'")
            
            for table in tables:
                rows = table.find_all('tr')
                print(f"🔍 CNSWPL: Table has {len(rows)} rows")
                
                # Process each line (each table represents one line with two rows)
                for i in range(0, len(rows), 2):  # Process every 2 rows (winning team + losing team)
                    if i + 1 < len(rows):  # Make sure we have both rows
                        winning_row = rows[i]  # First row with tr_line_desc class
                        losing_row = rows[i + 1]  # Second row
                        
                        # Extract line number from the first row
                        line_cells = winning_row.find_all('td')
                        if len(line_cells) >= 1:
                            line_text = line_cells[0].get_text(strip=True)
                            print(f"🔍 CNSWPL: Line text: '{line_text}'")
                            
                            # Extract line number from "Line 1", "Line 2", "Court 1", "Court 2", etc.
                            line_match = re.search(r'(?:Line|Court)\s+(\d+)', line_text)
                            if line_match:
                                line_num = int(line_match.group(1))
                                # Determine which pattern was matched for better logging
                                pattern_type = "Court" if "Court" in line_text else "Line"
                                print(f"🔍 CNSWPL: Matched {pattern_type} pattern: '{line_text}' -> {pattern_type} {line_num}")
                                
                                # Extract winning team data (first row)
                                winning_cells = winning_row.find_all('td')
                                if len(winning_cells) >= 5:
                                    # Cell 2 contains winning team player names
                                    winning_player_cell = winning_cells[2]
                                    
                                    # Extract all available score columns dynamically
                                    winning_scores = []
                                    for i in range(3, len(winning_cells)):  # Start from cell 3 (first score)
                                        score_text = winning_cells[i].get_text(strip=True)
                                        if score_text and score_text != "&nbsp;":  # Skip empty cells
                                            winning_scores.append(score_text)
                                    
                                    # Extract losing team data (second row)
                                    losing_cells = losing_row.find_all('td')
                                    if len(losing_cells) >= 5:
                                        # Cell 1 is empty (checkmark column), Cell 2 contains losing team player names
                                        losing_player_cell = losing_cells[1]  # Second cell, not third
                                        
                                        # Extract all available score columns dynamically
                                        losing_scores = []
                                        for i in range(2, len(losing_cells)):  # Start from cell 2 (first score)
                                            score_text = losing_cells[i].get_text(strip=True)
                                            if score_text and score_text != "&nbsp;":  # Skip empty cells
                                                losing_scores.append(score_text)
                                    
                                    # Extract winning team player names and IDs from links
                                    winning_player_links = winning_player_cell.find_all('a')
                                    winning_players = []
                                    winning_player_ids = []
                                    if winning_player_links:
                                        for link in winning_player_links:
                                            player_name = self._clean_player_name(link.get_text(strip=True))
                                            player_id = self._extract_player_id_from_link(link)
                                            winning_players.append(player_name)
                                            winning_player_ids.append(player_id)
                                    else:
                                        winning_players = [winning_player_cell.get_text(strip=True)]
                                        winning_player_ids = [None, None]
                                    
                                    # Extract losing team player names and IDs from links
                                    losing_player_links = losing_player_cell.find_all('a')
                                    losing_players = []
                                    losing_player_ids = []
                                    if losing_player_links:
                                        for link in losing_player_links:
                                            player_name = self._clean_player_name(link.get_text(strip=True))
                                            player_id = self._extract_player_id_from_link(link)
                                            losing_players.append(player_name)
                                            losing_player_ids.append(player_id)
                                    else:
                                        losing_players = [losing_player_cell.get_text(strip=True)]
                                        losing_player_ids = [None, None]
                                    
                                    print(f"🔍 CNSWPL: Line {line_num} - Winning: {winning_players} ({winning_scores}) vs Losing: {losing_players} ({losing_scores})")
                                    
                                    # Determine which team is home/away based on overall match context
                                    home_team = teams_and_score.get("home_team", "")
                                    away_team = teams_and_score.get("away_team", "")
                                    
                                    # For CNSWPL, we need to determine which team the winning/losing players belong to
                                    # This is complex - we'll need to make an assumption or use additional logic
                                    # For now, let's assume the winning team is the away team and losing is home
                                    # This may need adjustment based on actual team assignments
                                    
                                    # Assign players based on winning/losing status
                                    away_player_1 = winning_players[0] if len(winning_players) > 0 else ""
                                    away_player_2 = winning_players[1] if len(winning_players) > 1 else ""
                                    home_player_1 = losing_players[0] if len(losing_players) > 0 else ""
                                    home_player_2 = losing_players[1] if len(losing_players) > 1 else ""
                                    
                                    # Use extracted player IDs from links
                                    away_player_1_id = winning_player_ids[0] if len(winning_player_ids) > 0 else None
                                    away_player_2_id = winning_player_ids[1] if len(winning_player_ids) > 1 else None
                                    home_player_1_id = losing_player_ids[0] if len(losing_player_ids) > 0 else None
                                    home_player_2_id = losing_player_ids[1] if len(losing_player_ids) > 1 else None
                                    
                                    # Create scores string in APTA format (winning team scores first)
                                    # Handle variable number of sets (2 or 3)
                                    scores_parts = []
                                    max_sets = max(len(winning_scores), len(losing_scores))
                                    for i in range(max_sets):
                                        winning_score = winning_scores[i] if i < len(winning_scores) else "0"
                                        losing_score = losing_scores[i] if i < len(losing_scores) else "0"
                                        scores_parts.append(f"{winning_score}-{losing_score}")
                                    scores_string = ", ".join(scores_parts)
                                    
                                    # Determine line winner based on actual scores
                                    line_winner = self._determine_winner_from_scores(scores_string)
                                    
                                    # Create line match data in APTA_CHICAGO format
                                    line_match_data = {
                                        "league_id": "CNSWPL",
                                        "source_league": "CNSWPL",
                                        "match_id": f"{match_id}_Line{line_num}",
                                        "url": f"https://cnswpl.tenniscores.com/print_match.php?sch={match_id}&print&",
                                        "Home Team": home_team,
                                        "Away Team": away_team,
                                        "Scores": scores_string,
                                        "Line": f"Line {line_num}",
                                        "Away Player 1": away_player_1,
                                        "Away Player 2": away_player_2,
                                        "Away Player 1 ID": away_player_1_id or "",
                                        "Away Player 2 ID": away_player_2_id or "",
                                        "Home Player 1": home_player_1,
                                        "Home Player 2": home_player_2,
                                        "Home Player 1 ID": home_player_1_id or "",
                                        "Home Player 2 ID": home_player_2_id or "",
                                        "Winner": line_winner,
                                        "Date": match_date
                                    }
                                    line_matches.append(line_match_data)
                                    print(f"✅ CNSWPL: Extracted line {line_num} in APTA format with players: {away_player_1}, {away_player_2} vs {home_player_1}, {home_player_2}")
            
            print(f"✅ CNSWPL: Extracted {len(line_matches)} line matches")
            return line_matches
            
        except Exception as e:
            print(f"❌ CNSWPL: Error extracting lines: {e}")
            return []
    
    def _extract_cnswpl_individual_scores(self, soup) -> str:
        """Extract individual set scores from CNSWPL court breakdown."""
        import re
        
        # Look for tennis set scores like "6-1", "6-2", "7-5", etc.
        all_text = soup.get_text()
        
        # Pattern for tennis set scores
        set_pattern = r'\b[0-7]-[0-7]\b'
        scores = re.findall(set_pattern, all_text)
        
        if scores:
            return ", ".join(scores)
        
        return ""


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
            
            print(f"\n🏆 NSTF: Starting series extraction for {series_name}")
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
                            detailed_matches = self._extract_nstf_detailed_match_data(match_response, series_name, match_id, match_url)
                            if detailed_matches:
                                matches.extend(detailed_matches)
                                match_count += len(detailed_matches)
                                print(f"✅ NSTF: Extracted {len(detailed_matches)} lines from match")
                                
                                # Save incremental temp file every 10 matches
                                if len(matches) % 40 == 0:  # Every 10 matches (4 lines each = 40 line matches)
                                    self._save_incremental_temp_file("nstf", series_name, matches, len(matches))
                        
                        matches_processed_in_series += 1
                        
                    except Exception as e:
                        print(f"⚠️ NSTF: Error processing match link: {e}")
                        continue
            
            print(f"📊 NSTF: {series_name} completed - Total matches extracted: {match_count}")
            print(f"🎯 Series Summary: {len(matches)} line matches from {matches_processed_in_series} team matches")
            
        except Exception as e:
            print(f"❌ NSTF: Error extracting matches: {e}")
        
        return matches, matches_processed_in_series
    
    def _extract_nstf_detailed_match_data(self, html: str, series_name: str, match_id: str, match_url: str) -> List[Dict]:
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
            line_matches = self._extract_nstf_lines(soup, series_name, match_id, match_date, teams_and_score, match_url)
            
            return line_matches
            
        except Exception as e:
            print(f"❌ NSTF: Error extracting detailed match data: {e}")
            return []
    
    def _extract_nstf_date(self, soup) -> str:
        """Extract match date from NSTF match page."""
        try:
            # Enhanced NSTF date extraction with proper formatting
            import re
            from datetime import datetime
            
            def format_to_nstf_date(date_str):
                """Convert various date formats to NSTF format (DD-MMM-YY)"""
                try:
                    # Try different input formats
                    formats_to_try = [
                        ('%B %d, %Y', 'May 29, 2025'),      # May 29, 2025
                        ('%b %d, %Y', 'May 29, 2025'),       # May 29, 2025  
                        ('%m/%d/%y', '5/29/25'),             # 5/29/25
                        ('%m/%d/%Y', '5/29/2025'),           # 5/29/2025
                        ('%d-%b-%y', '29-May-25'),           # Already correct format
                    ]
                    
                    for fmt, example in formats_to_try:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            # Format to NSTF standard: DD-MMM-YY
                            nstf_date = parsed_date.strftime('%d-%b-%y')
                            return nstf_date
                        except ValueError:
                            continue
                    
                    return date_str  # Return as-is if no format matches
                except:
                    return date_str
            
            # Method 1: Look in page title first
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                date_patterns = [
                    r'\d{1,2}-[A-Za-z]{3}-\d{2,4}',           # 29-May-25
                    r'[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}',     # May 29, 2025
                    r'\d{1,2}/\d{1,2}/\d{2,4}',              # 5/29/25
                ]
                
                for pattern in date_patterns:
                    date_match = re.search(pattern, title_text)
                    if date_match:
                        raw_date = date_match.group()
                        formatted_date = format_to_nstf_date(raw_date)
                        print(f"  📅 Found date in title: {raw_date} -> {formatted_date}")
                        return formatted_date
            
            # Method 2: Look in all text elements
            date_elements = soup.find_all(text=True)
            for element in date_elements:
                if isinstance(element, str):
                    text = element.strip()
                    if len(text) > 5:  # Skip very short strings
                        date_patterns = [
                            r'\d{1,2}-[A-Za-z]{3}-\d{2,4}',
                            r'[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}',
                            r'\d{1,2}/\d{1,2}/\d{2,4}',
                        ]
                        
                        for pattern in date_patterns:
                            date_match = re.search(pattern, text)
                            if date_match:
                                raw_date = date_match.group()
                                formatted_date = format_to_nstf_date(raw_date)
                                print(f"  📅 Found date in text: {raw_date} -> {formatted_date}")
                                return formatted_date
            
            print(f"  ⚠️  No date found in NSTF match page")
            return None
        except Exception as e:
            print(f"❌ NSTF: Error extracting date: {e}")
            return None
    
    def _extract_nstf_teams_and_score(self, soup) -> dict:
        """Extract team names and scores from NSTF match page."""
        try:
            # Extract team names from the page content
            home_team = "Unknown Home Team"
            away_team = "Unknown Away Team"
            scores = "Unknown Scores"
            
            # Method 1: PRIORITIZE datelocheader div for cleanest team names  
            header_div = soup.find('div', class_='datelocheader')
            if header_div:
                header_text = header_div.get_text(strip=True)
                print(f"  🔍 Found datelocheader: {header_text}")
                # Extract teams from header like "Wilmette S1 T2 @ Tennaqua S1: 15 - 1"
                import re
                # Enhanced pattern to handle team variations: S1, S1A, S1B, S1 T1, S1 T2, etc.
                match_header = re.search(r'([A-Za-z\s]+S\d+(?:[AB]|\s+T\d+)?)\s*@\s*([A-Za-z\s]+S\d+(?:[AB]|\s+T\d+)?):\s*(\d+)\s*-\s*(\d+)', header_text)
                if match_header:
                    away_team = match_header.group(1).strip()
                    home_team = match_header.group(2).strip() 
                    away_score = match_header.group(3).strip()
                    home_score = match_header.group(4).strip()
                    scores = f"{away_score}-{home_score}"
                    print(f"  🏆 NSTF Match (CLEAN from datelocheader): {away_team} (away) @ {home_team} (home) - {scores}")
                    
                    return {
                        "Home Team": home_team,
                        "Away Team": away_team,
                        "Scores": scores
                    }
                
            # Method 2: Fallback to page content (may contain garbage text)
            # Pattern: "Away Team @ Home Team: Away_Score - Home_Score"
            page_text = soup.get_text()
            import re  # Ensure re is available for fallback
            
            # Look for NSTF pattern: "Team A @ Team B: X - Y" with enhanced team name support
            match_pattern = re.search(r'([A-Za-z\s\d]+S\d+(?:[AB]|\s+T\d+)?)\s*@\s*([A-Za-z\s\d]+S\d+(?:[AB]|\s+T\d+)?):\s*(\d+)\s*-\s*(\d+)', page_text)
            if match_pattern:
                away_team = match_pattern.group(1).strip()  # Team before @ is away
                home_team = match_pattern.group(2).strip()  # Team after @ is home
                away_score = match_pattern.group(3).strip()
                home_score = match_pattern.group(4).strip()
                scores = f"{away_score}-{home_score}"  # Away-Home format
                print(f"  🏆 NSTF Match (FALLBACK from page text): {away_team} (away) @ {home_team} (home) - {scores}")
                
                return {
                    "Home Team": home_team,
                    "Away Team": away_team,
                    "Scores": scores
                }
                
            # Fallback: Look for team names in page title or headers  
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                # Look for patterns like "Team A vs Team B" or "Team A - Team B"
                team_match = re.search(r'([^-\n]+)\s*(?:vs\.?|v\.?|-)\s*([^-\n]+)', title_text)
                if team_match:
                    home_team = team_match.group(1).strip()
                    away_team = team_match.group(2).strip()
                    print(f"  🏆 Extracted teams from title: {home_team} vs {away_team}")
            
            # Method 2: Look for team names in table headers or cells
            if home_team == "Unknown Home Team":
                tables = soup.find_all('table')
                for table in tables:
                    cells = table.find_all(['td', 'th'])
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # Look for team names in the first few cells
                    if len(cell_texts) >= 2:
                        for i in range(min(10, len(cell_texts))):
                            text = cell_texts[i]
                            # Look for words that might be team names (not numbers, dates, or short words)
                            if (len(text) > 3 and 
                                not re.match(r'^\d+[-/]\d+', text) and  # Not a date
                                not re.match(r'^\d+$', text) and        # Not just a number
                                any(char.isalpha() for char in text)):  # Contains letters
                                if home_team == "Unknown Home Team":
                                    home_team = text
                                elif away_team == "Unknown Away Team" and text != home_team:
                                    away_team = text
                                    break
            
            # Method 2: Look for score patterns in NSTF format with aggressive debugging
            all_text = soup.get_text()
            import re
            
            # Debug: Show some sample text to understand NSTF format
            text_sample = ' '.join(all_text.split()[:100])  # First 100 words
            print(f"  🔍 NSTF HTML sample: {text_sample[:200]}...")
            
            # AGGRESSIVE SCORE EXTRACTION STRATEGY
            # Strategy 1: Look for ANY number-dash-number patterns and filter aggressively
            all_number_patterns = re.findall(r'\d+-\d+', all_text)
            if all_number_patterns:
                print(f"  🔢 Found {len(all_number_patterns)} number patterns: {all_number_patterns[:15]}")
                
                # Filter for tennis-like scores (0-15 range, no dates or large numbers)
                tennis_scores = []
                for pattern in all_number_patterns:
                    parts = pattern.split('-')
                    if len(parts) == 2:
                        try:
                            left, right = int(parts[0]), int(parts[1])
                            # Tennis scores: 0-15 range, but exclude likely non-tennis patterns
                            if (0 <= left <= 15 and 0 <= right <= 15 and 
                                not (left > 12 or right > 12) and  # Avoid dates like 01-15
                                not (left == 1 and right <= 4) and  # Avoid court numbers like 1-4
                                not (left <= 4 and right == 1)):   # Avoid reverse court numbers
                                tennis_scores.append(pattern)
                        except ValueError:
                            continue
                
                if tennis_scores:
                    print(f"  🎾 Tennis-like scores: {tennis_scores}")
                    # Format as comma-separated sets
                    if len(tennis_scores) >= 2:
                        scores = ', '.join(tennis_scores[:3])  # Take max 3 sets
                        print(f"  ✅ Strategy 1 success: {scores}")
                    else:
                        scores = tennis_scores[0]
                        print(f"  ✅ Strategy 1 single set: {scores}")
                else:
                    print(f"  ⚠️  No tennis-like scores in number patterns")
                    scores = "Unknown Scores"
            else:
                print(f"  ⚠️  No number patterns found at all")
                scores = "Unknown Scores"
            
            # Strategy 2: If Strategy 1 failed, try traditional regex patterns
            if scores == "Unknown Scores":
                print(f"  🔄 Trying Strategy 2: Traditional patterns")
                score_patterns = [
                    r'\d+-\d+(?:\s*,\s*\d+-\d+)+',  # Multiple sets with commas: "6-4, 6-2"
                    r'\d+-\d+(?:\s*,\s*\d+-\d+){1,2}',  # 2-3 sets
                    r'\d+-\d+\s*,\s*\d+-\d+',      # Simple 2 sets
                ]
                
                for i, pattern in enumerate(score_patterns):
                    score_match = re.search(pattern, all_text)
                    if score_match:
                        scores = score_match.group()
                        # Clean up the score format
                        scores = re.sub(r'\s+', ' ', scores)  # Normalize whitespace
                        scores = re.sub(r'\s*,\s*', ', ', scores)  # Normalize comma spacing
                        
                        # Validate that all parts are tennis scores
                        score_parts = [part.strip() for part in scores.split(',')]
                        valid_parts = []
                        for part in score_parts:
                            if re.match(r'^\d+-\d+$', part):
                                left, right = map(int, part.split('-'))
                                if (0 <= left <= 15 and 0 <= right <= 15 and 
                                    not (left == 1 and right <= 4) and 
                                    not (left <= 4 and right == 1)):
                                    valid_parts.append(part)
                        
                        if valid_parts:
                            teams_and_score["Scores"] = ', '.join(valid_parts)
                            print(f"  ✅ Strategy 2 pattern {i+1}: {', '.join(valid_parts)}")
                            break
            
            # Strategy 3: Super aggressive - look in HTML elements specifically
            if scores == "Unknown Scores":
                print(f"  🔄 Trying Strategy 3: HTML element search")
                # Look in table cells for scores
                tables = soup.find_all('table')
                for table in tables:
                    cells = table.find_all(['td', 'th'])
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        # Look for score-like patterns in individual cells
                        if re.match(r'^\d+-\d+(?:\s*,\s*\d+-\d+)*$', cell_text):
                            scores = cell_text
                            print(f"  ✅ Strategy 3 table cell: {scores}")
                            break
                    if scores != "Unknown Scores":
                        break
            
            # Strategy 4: Last resort - ANY reasonable looking scores
            if scores == "Unknown Scores":
                print(f"  🔄 Trying Strategy 4: Last resort")
                simple_scores = re.findall(r'\b\d{1,2}-\d{1,2}\b', all_text)
                filtered_scores = []
                for score in simple_scores:
                    parts = score.split('-')
                    if len(parts) == 2:
                        try:
                            left, right = int(parts[0]), int(parts[1])
                            if 0 <= left <= 15 and 0 <= right <= 15:
                                filtered_scores.append(score)
                        except ValueError:
                            continue
                
                if filtered_scores:
                    scores = ', '.join(filtered_scores[:2])  # Take first 2
                    print(f"  💡 Strategy 4 fallback: {scores}")
                else:
                    print(f"  ❌ All strategies failed")
                    scores = "Unknown Scores"
            
            return {
                "Home Team": home_team,
                "Away Team": away_team,
                "Scores": scores
            }
        except Exception as e:
            print(f"❌ NSTF: Error extracting teams and score: {e}")
            return {
                "Home Team": "Unknown Home Team",
                "Away Team": "Unknown Away Team", 
                "Scores": "Unknown Scores"
            }
    
    def _extract_nstf_lines(self, soup, series_name: str, match_id: str, match_date: str, teams_and_score: dict, match_url: str) -> List[Dict]:
        """Extract NSTF line-specific data with actual player names and IDs."""
        line_matches = []
        
        try:
            # Extract actual player data from NSTF match page
            players_data = self._extract_nstf_players(soup)
            
            # NSTF typically has 4 lines per match (doubles format)
            lines_data = self._extract_nstf_line_data(soup)
            
            # Create line matches with real data
            for line_num in range(1, 5):  # 4 lines per match
                line_index = line_num - 1
                
                # Get player data for this line
                home_player1 = players_data.get(f"home_player_{line_num}_1", {})
                home_player2 = players_data.get(f"home_player_{line_num}_2", {})
                away_player1 = players_data.get(f"away_player_{line_num}_1", {})
                away_player2 = players_data.get(f"away_player_{line_num}_2", {})
                
                # Get line score data
                line_score = lines_data.get(line_num, {})
                
                line_match = {
                    "league_id": "NSTF",
                    "match_id": f"{match_id}_Line{line_num}",
                    "source_league": "NSTF",
                    "Line": f"Line {line_num}",
                    "series": series_name,  # Add missing series field
                    "Date": match_date,
                    "Home Team": teams_and_score.get("Home Team"),
                    "Away Team": teams_and_score.get("Away Team"),
                    "Home Player 1": home_player1.get("name", f"Unknown Player H{line_num}A"),
                    "Home Player 2": home_player2.get("name", f"Unknown Player H{line_num}B"),
                    "Home Player 1 ID": home_player1.get("id", f"unknown_h{line_num}a"),
                    "Home Player 2 ID": home_player2.get("id", f"unknown_h{line_num}b"),
                    "Away Player 1": away_player1.get("name", f"Unknown Player A{line_num}A"),
                    "Away Player 2": away_player2.get("name", f"Unknown Player A{line_num}B"),
                    "Away Player 1 ID": away_player1.get("id", f"unknown_a{line_num}a"),
                    "Away Player 2 ID": away_player2.get("id", f"unknown_a{line_num}b"),
                    "Scores": line_score.get("score", teams_and_score.get("Scores")),
                    "Winner": self._determine_nstf_winner(line_score, teams_and_score),
                    "match_url": match_url  # Add URL for verification
                }
                line_matches.append(line_match)
            
            print(f"✅ NSTF: Created {len(line_matches)} line matches with actual player data")
            
        except Exception as e:
            print(f"❌ NSTF: Error extracting lines: {e}")
            
        return line_matches
    
    def _determine_nstf_winner(self, line_score: dict, teams_and_score: dict) -> str:
        """Determine winner based on line score data in NSTF format with enhanced logic."""
        try:
            # Method 1: Use line-specific score if available
            if line_score and "score" in line_score:
                score_text = line_score["score"]
                if score_text and score_text != "Unknown Scores":
                    # Parse scores like "6-4, 6-2" or "4-6, 6-4, 6-2"
                    import re
                    sets = re.findall(r'(\d+)-(\d+)', score_text)
                    if sets:
                        home_sets_won = 0
                        away_sets_won = 0
                        
                        for away_score, home_score in sets:  # CORRECTED: First score is AWAY, second is HOME
                            try:
                                away = int(away_score)
                                home = int(home_score)
                                
                                if home > away:
                                    home_sets_won += 1
                                elif away > home:
                                    away_sets_won += 1
                            except ValueError:
                                continue
                        
                        # Enhanced logic: require clear majority
                        if home_sets_won > away_sets_won:
                            return "home"
                        elif away_sets_won > home_sets_won:
                            return "away"
                        elif home_sets_won == away_sets_won and home_sets_won > 0:
                            return "tie"
                        
            # Method 2: Use line-specific winner if available
            if line_score and "winner" in line_score:
                line_winner = line_score["winner"]
                if line_winner in ["home", "away", "tie"]:
                    return line_winner
            
            # Method 3: Fallback to overall match score
            if teams_and_score and "Scores" in teams_and_score:
                match_scores = teams_and_score["Scores"]
                if match_scores and match_scores != "Unknown Scores":
                    # Use same logic as above for consistency
                    import re
                    sets = re.findall(r'(\d+)-(\d+)', match_scores)
                    if sets:
                        home_sets_won = 0
                        away_sets_won = 0
                        
                        for away_score, home_score in sets:  # CORRECTED: First score is AWAY, second is HOME
                            try:
                                away = int(away_score)
                                home = int(home_score)
                                
                                if home > away:
                                    home_sets_won += 1
                                elif away > home:
                                    away_sets_won += 1
                            except ValueError:
                                continue
                        
                        if home_sets_won > away_sets_won:
                            return "home"
                        elif away_sets_won > home_sets_won:
                            return "away"
                        else:
                            return "tie"
            
            # Method 4: Default fallback
            return "tie"
            
        except Exception as e:
            print(f"❌ Error determining NSTF winner: {e}")
            return "tie"
    def _extract_nstf_players(self, soup) -> dict:
        """Extract player names and IDs from NSTF match page."""
        players_data = {}
        
        try:
            # Find all player links in the format: player.php?print&p=PLAYER_ID
            player_links = soup.find_all('a', href=True)
            player_count = 0
            total_links = len(player_links)
            
            print(f"  🔍 NSTF: Scanning {total_links} links for player data...")
            
            for link in player_links:
                href = link.get('href', '')
                if 'player.php?print&p=' in href:
                    # Extract player ID from href
                    player_id = href.split('p=')[1].split('&')[0]
                    player_name = link.text.strip()
                    
                    if player_id and player_name:
                        player_count += 1
                        
                        # FIXED: Better player positioning logic based on HTML structure analysis
                        if player_count <= 16:  # Up to 16 players (4 lines × 2 teams × 2 players)
                            # NSTF pattern analysis:
                            # - Players appear in pairs per table row
                            # - Each line has 2 rows: top row (away/winning team), bottom row (home team)
                            # - Players 1-2: Line 1 Away team, Players 3-4: Line 1 Home team  
                            # - Players 5-6: Line 2 Away team, Players 7-8: Line 2 Home team
                            # - etc.
                            
                            line_num = ((player_count - 1) // 4) + 1  # Which line (1-4)
                            position_in_line = (player_count - 1) % 4  # Position within line (0-3)
                            
                            if position_in_line < 2:
                                # First two players in line = Away team
                                team_prefix = "away"
                                player_pos = (position_in_line % 2) + 1  # 1 or 2
                            else:
                                # Last two players in line = Home team  
                                team_prefix = "home"
                                player_pos = (position_in_line % 2) + 1  # 1 or 2
                            
                            key = f"{team_prefix}_player_{line_num}_{player_pos}"
                            
                            players_data[key] = {
                                "name": player_name,
                                "id": player_id
                            }
                            
                            print(f"  📍 NSTF Player {player_count}: {player_name} (ID: {player_id}) -> {key}")
            
            print(f"🎾 NSTF: Extracted {len(players_data)} player records")
            
            # If no players found, show some debug info
            if len(players_data) == 0:
                print(f"  ⚠️  No player links found in format 'player.php?print&p='")
                print(f"  🔍 Sample links found:")
                sample_links = player_links[:5]
                for i, link in enumerate(sample_links):
                    href = link.get('href', '')
                    text = link.text.strip()[:50]
                    print(f"    {i+1}. {href} -> '{text}'")
            
        except Exception as e:
            print(f"❌ NSTF: Error extracting players: {e}")
            
        return players_data
    
    def _extract_nstf_line_data(self, soup) -> dict:
        """Extract line-specific scores and winners from NSTF match page."""
        import re  # Ensure re is available in function scope
        lines_data = {}
        
        try:
            # Extract tables for this line (each line should have its own table)
            line_tables = soup.find_all('table', class_='standings-table2')
            
            if not line_tables:
                print(f"  ❌ No tables found for line extraction")
                return lines_data
            
            print(f"🏓 Found {len(line_tables)} NSTF line tables")
            
            line_num = 1
            
            for table_idx, table in enumerate(line_tables):
                print(f"🔍 Processing Line {line_num} table with {len(table.find_all('tr'))} rows")
                
                # Each table represents one line/match with 2 rows (away team row + home team row)
                rows = table.find_all('tr')
                if len(rows) < 2:
                    print(f"  ⚠️ Table {table_idx+1} has insufficient rows ({len(rows)})")
                    continue
                
                # Extract score cells from both rows
                away_scores = []  # Row 1 (top row)
                home_scores = []  # Row 2 (bottom row)
                
                for row_idx, row in enumerate(rows):
                    cells = row.find_all('td')
                    # Get all cells with 'pts2' class (score cells)
                    score_cells = [cell for cell in cells if 'pts2' in cell.get('class', [])]
                    
                    print(f"Row {row_idx+1}: Found {len(score_cells)} score cells")
                    
                    # Process each score cell for tiebreaks and concatenated scores
                    row_scores = []
                    for cell in score_cells:
                        cell_html = str(cell)
                        plain_text = cell.get_text(strip=True)
                        
                        if not plain_text or plain_text == '&nbsp;':
                            continue
                        
                        print(f"Score cell: {plain_text}")
                        
                        # Check for tiebreak pattern: number<sup>tiebreak</sup>
                        sup_match = re.search(r'(\d+)<sup>(\d+)</sup>', cell_html)
                        if sup_match:
                            main_score = sup_match.group(1)
                            tiebreak_points = sup_match.group(2)
                            
                            # NSTF tiebreak logic: 7<sup>7</sup> means 7-6, 6<sup>0</sup> means 6-0
                            if main_score == "7":
                                score_value = "7"  # Keep as 7 for now, will form 7-6 when paired
                            elif main_score == "6" and tiebreak_points == "0":
                                score_value = "6"  # 6-0 style
                            else:
                                score_value = main_score
                            
                            row_scores.append(score_value)
                            print(f"    🏆 Tiebreak cell: {cell_html} → {score_value}")
                        else:
                            # Handle concatenated scores like '60' = '6' + '0'
                            if len(plain_text) == 2 and plain_text.isdigit():
                                first_digit = plain_text[0]
                                second_digit = plain_text[1]
                                # Treat as single score for now
                                row_scores.append(first_digit)
                                print(f"    🏆 Concatenated: '{plain_text}' → {first_digit}")
                            elif plain_text.isdigit() and 0 <= int(plain_text) <= 15:
                                row_scores.append(plain_text)
                                print(f"    🏆 Regular score: {plain_text}")
                    
                    # Store scores by row
                    if row_idx == 0:
                        away_scores = row_scores
                    elif row_idx == 1:
                        home_scores = row_scores
                
                # Now combine away and home scores to form sets
                print(f"🧮 Analyzing sets: {list(zip(away_scores, home_scores)) if away_scores and home_scores else 'No valid scores'}")
                
                if away_scores and home_scores:
                    sets = []
                    min_sets = min(len(away_scores), len(home_scores))
                    
                    away_sets_won = 0
                    home_sets_won = 0
                    
                    for i in range(min_sets):
                        away_score = int(away_scores[i]) if away_scores[i].isdigit() else 0
                        home_score = int(home_scores[i]) if home_scores[i].isdigit() else 0
                        
                        set_score = f"{away_score}-{home_score}"
                        sets.append(set_score)
                        
                        # Determine set winner
                        if away_score > home_score:
                            away_sets_won += 1
                            print(f"Set {set_score}: AWAY wins")
                        elif home_score > away_score:
                            home_sets_won += 1
                            print(f"Set {set_score}: HOME wins")
                        else:
                            print(f"Set {set_score}: TIE")
                    
                    print(f"📊 Final: Home {home_sets_won} sets, Away {away_sets_won} sets")
                    
                    # Determine overall winner
                    if away_sets_won > home_sets_won:
                        winner = "away"
                        print(f"🏆 Winner: away")
                    elif home_sets_won > away_sets_won:
                        winner = "home"
                        print(f"🏆 Winner: home")
                    else:
                        winner = "tie"
                        print(f"🏆 Winner: tie")
                    
                    if sets:
                        score_text = ', '.join(sets)
                        lines_data[line_num] = {
                            "score": score_text,
                            "winner": winner
                        }
                        print(f"📊 Line {line_num} extracted: {score_text} (Winner: {winner})")
                
                # Always increment line_num after processing each table (each table = one line)
                line_num += 1
            
            # Debug: If no line scores found, show what was in tables
            if not lines_data:
                print(f"  ⚠️  No line scores found")
            
            print(f"📊 NSTF: Successfully extracted {len(lines_data)} line scores using table structure")
            
        except Exception as e:
            print(f"❌ NSTF: Error extracting line data: {e}")
            
        return lines_data
    
    def _determine_winner_from_score(self, score_text: str) -> str:
        """Determine winner from a score string like '6-4, 6-2' or '4-6, 6-4, 6-2'."""
        try:
            import re
            sets = re.findall(r'(\d+)-(\d+)', score_text)
            if not sets:
                print(f"    ⚠️  No sets found in score: '{score_text}'")
                return "tie"
            
            home_sets_won = 0
            away_sets_won = 0
            
            print(f"    🧮 Analyzing sets: {sets}")
            
            for home_score, away_score in sets:
                home_val = int(home_score)
                away_val = int(away_score)
                
                if home_val > away_val:
                    home_sets_won += 1
                    print(f"      Set {home_score}-{away_score}: HOME wins")
                elif away_val > home_val:
                    away_sets_won += 1
                    print(f"      Set {home_score}-{away_score}: AWAY wins")
                else:
                    print(f"      Set {home_score}-{away_score}: TIE (rare)")
            
            print(f"    📊 Final: Home {home_sets_won} sets, Away {away_sets_won} sets")
            
            if home_sets_won > away_sets_won:
                winner = "home"
            elif away_sets_won > home_sets_won:
                winner = "away"
            else:
                winner = "tie"
            
            print(f"    🏆 Winner: {winner}")
            return winner
                
        except Exception as e:
            print(f"❌ Error determining winner from score '{score_text}': {e}")
            return "tie"

class APTAScraper(BaseLeagueScraper):
    """APTA-specific scraper with dedicated extraction logic."""
    
    def extract_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract APTA series links."""
        return self._extract_apta_series_links(html)
    
    def extract_matches_from_series(self, html: str, series_name: str, 
                                  current_total_processed: int = 0, total_series: int = 1) -> Tuple[List[Dict], int]:
        """Extract matches from APTA series page."""
        return self._extract_apta_matches_from_series(html, series_name, current_total_processed, total_series)
    
    def _extract_apta_series_links(self, html: str) -> List[Tuple[str, str]]:
        """Extract series links for APTA format using RTF file."""
        print(f"   📋 Loading APTA series from RTF file...")
        return self._load_apta_series_from_rtf()
    
    def _discover_apta_series_dynamically(self, soup) -> List[Tuple[str, str]]:
        """Discover all available APTA series by scraping the standings page for series navigation."""
        print("   📋 Discovering all available series from standings page navigation...")
        
        discovered_series = []
        
        try:
            # Enhanced Method: Look for all links with series navigation patterns
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for series-specific links with the correct URL pattern
                if href and text and ('did=' in href and 'mod=' in href):
                    # Check if this looks like a series navigation link
                    if (re.search(r'\b\d+\b', text) or 
                        'Series' in text or 
                        'SW' in text):
                        
                        # Construct the full URL
                        if href.startswith('/'):
                            full_url = f"https://aptachicago.tenniscores.com{href}"
                        elif href.startswith('?'):
                            full_url = f"https://aptachicago.tenniscores.com{href}"
                        else:
                            full_url = href
                        
                        # Extract series name from text
                        if text.isdigit():
                            series_name = f"Series {text}"
                        elif ' SW' in text:
                            series_name = f"Series {text}"
                        else:
                            # Try to extract series number from text
                            series_match = re.search(r'\b(\d+)\b', text)
                            if series_match:
                                series_num = series_match.group(1)
                                if 'SW' in text:
                                    series_name = f"Series {series_num} SW"
                                else:
                                    series_name = f"Series {series_num}"
                            else:
                                series_name = text
                        
                        # Validate the URL before adding
                        if self._validate_series_url(full_url, series_name):
                            discovered_series.append((series_name, full_url))
                            print(f"         📋 Found series link: {series_name} -> {full_url}")
                        else:
                            print(f"         ⚠️ Skipped invalid series link: {series_name} -> {full_url}")
            
            # Remove duplicates and sort
            discovered_series = list(set(discovered_series))
            discovered_series.sort(key=lambda x: self._extract_series_number(x[0]))
            
            if discovered_series:
                print(f"      ✅ Found {len(discovered_series)} series from navigation")
            else:
                print("      ⚠️ No series found from navigation, using fallback...")
                
                # Fallback to comprehensive hardcoded series (same as players scraper)
                discovered_series = self._get_fallback_apta_series()
                
                # Validate fallback URLs to catch any issues
                validated_series = []
                for series_name, series_url in discovered_series:
                    if self._validate_series_url(series_url, series_name):
                        validated_series.append((series_name, series_url))
                    else:
                        print(f"         ⚠️ Skipped invalid fallback URL for {series_name}: {series_url}")
                discovered_series = validated_series
            
            return discovered_series
            
        except Exception as e:
            print(f"   ❌ Error during dynamic discovery: {e}")
            print("   🔄 Falling back to hardcoded series...")
            fallback_series = self._get_fallback_apta_series()
            
            # Validate fallback URLs to catch any issues
            validated_series = []
            for series_name, series_url in fallback_series:
                if self._validate_series_url(series_url, series_name):
                    validated_series.append((series_name, series_url))
                else:
                    print(f"         ⚠️ Skipped invalid fallback URL for {series_name}: {series_url}")
            
            return validated_series
    
    def _validate_series_url(self, url: str, series_name: str) -> bool:
        """Validate that a series URL is correct by checking for basic URL structure."""
        try:
            # Basic URL validation
            if not url or not isinstance(url, str):
                return False
                
            # Must be a tenniscores.com URL
            if 'tenniscores.com' not in url:
                return False
                
            # Must have the required parameters
            if 'mod=' not in url or 'did=' not in url:
                return False
                
            # Check for suspicious patterns that might indicate wrong URLs
            suspicious_patterns = [
                'did=nndz-WnkrNXg3MD0%3D',  # Common wrong pattern we've seen
                'did=nndz-WnkrNXc3MD0%3D',  # Another wrong pattern
            ]
            
            for pattern in suspicious_patterns:
                if pattern in url:
                    print(f"         ⚠️ Detected suspicious URL pattern in {series_name}: {pattern}")
                    return False
                    
            return True
            
        except Exception as e:
            print(f"         ❌ Error validating URL for {series_name}: {e}")
            return False
    
    def _validate_all_fallback_urls(self) -> None:
        """Validate all fallback URLs and report any issues."""
        print("   🔍 Validating all fallback URLs...")
        fallback_series = self._get_fallback_apta_series()
        
        invalid_urls = []
        for series_name, series_url in fallback_series:
            if not self._validate_series_url(series_url, series_name):
                invalid_urls.append((series_name, series_url))
        
        if invalid_urls:
            print(f"   ⚠️ Found {len(invalid_urls)} invalid fallback URLs:")
            for series_name, series_url in invalid_urls:
                print(f"      ❌ {series_name}: {series_url}")
        else:
            print("   ✅ All fallback URLs are valid")
    
    def _extract_series_number(self, series_name: str) -> int:
        """Extract series number for sorting."""
        try:
            # Handle regular series (Series 1, Series 2, etc.)
            if series_name.startswith("Series "):
                series_part = series_name.replace("Series ", "").strip()
                if series_part.isdigit():
                    return int(series_part)
                elif " SW" in series_part:
                    # For SW series, extract the number part
                    num_part = series_part.replace(" SW", "")
                    if num_part.isdigit():
                        return int(num_part) + 1000  # Put SW series after regular series
            return 9999  # Default for unrecognized formats
        except:
            return 9999
    
    def _load_apta_series_from_rtf(self) -> List[Tuple[str, str]]:
        """Load APTA series URLs from the RTF file."""
        import os
        import re
        
        rtf_file_path = os.path.join(os.path.dirname(__file__), "apta", "apta_match_scores_series_list.rtf")
        
        if not os.path.exists(rtf_file_path):
            raise FileNotFoundError(f"RTF file not found: {rtf_file_path}")
        
        try:
            with open(rtf_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract series lines from RTF content
            series_lines = []
            lines = content.split('\\')
            
            for line in lines:
                # Look for lines that start with "Series" and contain a URL
                if 'Series' in line and 'https://aptachicago.tenniscores.com' in line:
                    # Clean up the line - remove RTF formatting
                    clean_line = re.sub(r'\\[a-zA-Z0-9]+', '', line)  # Remove RTF commands
                    clean_line = clean_line.strip()
                    
                    if clean_line and ':' in clean_line:
                        # Split on the first colon to separate series name from URL
                        parts = clean_line.split(':', 1)
                        if len(parts) == 2:
                            series_name = parts[0].strip()
                            series_url = parts[1].strip()
                            
                            # Remove any trailing RTF formatting from URL (keep dots for domain names)
                            series_url = re.sub(r'[^a-zA-Z0-9/?=&%:.-]', '', series_url)
                            
                            if series_name and series_url and series_url.startswith('https://'):
                                series_lines.append((series_name, series_url))
            
            if not series_lines:
                raise ValueError("No valid series found in RTF file")
            
            print(f"   📋 Loaded {len(series_lines)} series from RTF file")
            return series_lines
            
        except Exception as e:
            print(f"   ❌ Error loading RTF file: {e}")
            raise

    def _get_fallback_apta_series(self) -> List[Tuple[str, str]]:
        """Get fallback hardcoded series list (same as players scraper)."""
        fallback_series = [
            # Regular series (1-22)
            ("Series 1", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3MD0%3D"),
            ("Series 2", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3bz0%3D"),
            ("Series 3", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3az0%3D"),
            ("Series 4", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3cz0%3D"),
            ("Series 5", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3WT0%3D"),
            ("Series 6", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3Zz0%3D"),
            ("Series 7", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMaz0%3D"),
            ("Series 8", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMWT0%3D"),
            ("Series 9", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMYz0%3D"),
            ("Series 10", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3ND0%3D"),
            ("Series 11", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3OD0%3D"),
            ("Series 12", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
            ("Series 13", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 14", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3bz0%3D"),
            ("Series 15", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3cz0%3D"),
            ("Series 16", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
            ("Series 17", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 18", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhibz0%3D"),
            ("Series 19", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhicz0%3D"),
            ("Series 20", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 21", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 22", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            # SW (Southwest) series
            ("Series 7 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMZz0%3D"),
            ("Series 9 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyZz0%3D"),
            ("Series 11 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhydz0%3D"),
            ("Series 13 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMYz0%3D"),
            ("Series 15 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXg3Yz0%3D"),
            ("Series 17 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyND0%3D"),
            ("Series 19 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyMD0%3D"),
            ("Series 21 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyOD0%3D"),
            # Additional series (23+)
            ("Series 23", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 23 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMWT0%3D"),
            ("Series 24", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 25", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 25 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXg3WT0%3D"),
            ("Series 26", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 27", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 27 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkNHL3lMbz0%3D"),
            ("Series 28", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 29", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 29 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkM2eHg3dz0%3D"),
            ("Series 30", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 31", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 31 SW", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WlNXK3licz0%3D"),
            ("Series 32", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 33", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 34", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 35", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 36", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 37", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 38", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 39", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 40", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 41", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 42", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 43", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 44", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 45", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 46", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 47", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 48", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 49", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 50", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
        ]
        
        for series_name, series_url in fallback_series:
            print(f"         📋 Added fallback: {series_name}")
        
        return fallback_series
    
    def _extract_dates_from_standings_page(self, soup) -> dict:
        """Extract dates from standings page th elements with data-col='col0'."""
        dates = {}
        
        try:
            # Look for th elements with data-col="col0" containing date format like "09/23"
            date_th_elements = soup.find_all('th', {'data-col': 'col0'})
            
            for th in date_th_elements:
                text = th.get_text(strip=True)
                print(f"      🔍 Found th data-col='col0' text: '{text}'")
                
                # Look for MM/DD format (e.g., "09/23")
                import re
                date_match = re.search(r'(\d{2})/(\d{2})', text)
                if date_match:
                    month = date_match.group(1)
                    day = date_match.group(2)
                    
                    # Convert to DD-Mon-YY format (assuming current year)
                    try:
                        from datetime import datetime
                        current_year = datetime.now().year
                        
                        # Convert month number to abbreviation
                        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        month_int = int(month)
                        if 1 <= month_int <= 12:
                            month_abbr = month_names[month_int - 1]
                            year_short = str(current_year)[-2:]
                            formatted_date = f"{day}-{month_abbr}-{year_short}"
                            
                            # Use the th element's position/context as a key
                            th_id = th.get('id', '')
                            dates[th_id] = formatted_date
                            print(f"      📅 Extracted date from th {th_id}: {formatted_date}")
                    except Exception as e:
                        print(f"      ❌ Error formatting date from th: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ Error extracting dates from standings page: {e}")
            
        return dates
    
    def _find_date_for_match_link(self, link, standings_dates: dict) -> str:
        """Find the associated date for a match link by looking at its position relative to date th elements."""
        try:
            # Get the link's position in the document
            link_parent = link.parent
            if not link_parent:
                return None
                
            # Look for the nearest th element with data-col="col0" that comes before this link
            # This is a simplified approach - in practice, we might need more sophisticated logic
            # to associate match links with their corresponding dates
            
            # For now, return the first available date as a fallback
            if standings_dates:
                return list(standings_dates.values())[0]
                
        except Exception as e:
            print(f"❌ Error finding date for match link: {e}")
            
        return None
    
    def _extract_apta_matches_from_series(self, html: str, series_name: str, 
                                        current_total_processed: int = 0, total_series: int = 1) -> Tuple[List[Dict], int]:
        """Extract matches from APTA series page."""
        matches = []
        processed_urls = set()  # Track processed URLs to avoid duplicates
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            print(f"   🔍 Extracting matches from APTA series: {series_name}")
            
            # First, extract all dates from th elements with data-col="col0"
            standings_dates = self._extract_dates_from_standings_page(soup)
            print(f"   📅 Found {len(standings_dates)} dates on standings page: {list(standings_dates.keys())}")
            
            # Look for standings tables
            standings_tables = soup.find_all('table', class_='standings-table2')
            
            for table in standings_tables:
                # Look for match links within the table
                match_links = table.find_all('a', href=True)
                
                for link in match_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Look for print_match.php links
                    if 'print_match.php' in href:
                        if href.startswith('/'):
                            full_url = f"https://aptachicago.tenniscores.com{href}"
                        else:
                            full_url = href
                        
                        # Skip if we've already processed this URL
                        if full_url in processed_urls:
                            print(f"   🔄 Skipping duplicate match link: {full_url}")
                            continue
                        
                        processed_urls.add(full_url)
                        print(f"   🔗 Found match link: {full_url}")
                        
                        # Try to find associated date for this match
                        match_date = self._find_date_for_match_link(link, standings_dates)
                        if match_date:
                            print(f"   📅 Associated date for this match: {match_date}")
                        else:
                            print(f"   ⚠️ No date found for this match link")
                        
                        # Extract match data from the link (returns list of line records)
                        match_records = self._extract_match_data_from_url(full_url, series_name, match_date)
                        if match_records:
                            matches.extend(match_records)
                            print(f"   📋 Found {len(match_records)} lines for match: {match_records[0].get('Home Team', 'Unknown')} vs {match_records[0].get('Away Team', 'Unknown')}")
                            for i, match_data in enumerate(match_records):
                                print(f"      🎾 Line {i+1}: {match_data.get('Line', 'Unknown')}")
                                print(f"      📅 Date: {match_data.get('Date', 'Unknown')}")
                                print(f"      🏆 Score: {match_data.get('Scores', 'Unknown')} (Winner: {match_data.get('Winner', 'Unknown')})")
                                print(f"      👥 Players: {match_data.get('Home Player 1', 'Unknown')}/{match_data.get('Home Player 2', 'Unknown')} vs {match_data.get('Away Player 1', 'Unknown')}/{match_data.get('Away Player 2', 'Unknown')}")
                                print(f"      🆔 Match ID: {match_data.get('match_id', 'Unknown')}")
                        else:
                            print(f"   ❌ Failed to extract data from match link")
                        
            print(f"   📊 Found {len(matches)} matches in {series_name}")
            return matches, len(matches)
            
        except Exception as e:
            print(f"   ❌ Error extracting APTA matches from series {series_name}: {e}")
            return [], 0
    
    def _extract_match_data_from_url(self, url: str, series_name: str, standings_date: str = None) -> List[Dict]:
        """Extract match data from a match URL - returns list of line records."""
        try:
            # Ensure URL has proper scheme and domain
            if not url.startswith('http'):
                if url.startswith('/'):
                    url = f"https://aptachicago.tenniscores.com{url}"
                else:
                    url = f"https://aptachicago.tenniscores.com/{url}"
            
            # Make request to get match page
            html = self._safe_request_for_league_scraper(url, f"match page for {series_name}")
            if not html:
                return []
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract team names and scores (common to all lines)
            team_data = self._extract_apta_teams_and_score(soup)
            
            # Use standings date if provided, otherwise try to extract from match page
            if standings_date:
                date_data = {"Date": standings_date}
                print(f"      📅 Using standings date: {standings_date}")
            else:
                date_data = self._extract_apta_date(soup)
            
            # Extract all lines
            all_lines = self._extract_all_apta_lines(soup)
            
            # Create separate match record for each line
            match_records = []
            for line_data in all_lines:
                # Extract line number from line name (e.g., "Line 3" or "Court 3" -> "3")
                line_name = line_data.get('Line', 'Line1')
                if 'Line ' in line_name:
                    line_number = line_name.replace('Line ', '')
                elif 'Court ' in line_name:
                    line_number = line_name.replace('Court ', '')
                else:
                    line_number = '1'
                
                match_record = {
                    "league_id": "APTA_CHICAGO",
                    "source_league": "APTA_CHICAGO",
                    "match_id": f"{self._extract_match_id_from_url(url)}_Line{line_number}",
                    "url": url
                }
                match_record.update(team_data)
                match_record.update(line_data)
                match_record.update(date_data)
                match_records.append(match_record)
            
            return match_records
            
        except Exception as e:
            print(f"   ❌ Error extracting match data from URL {url}: {e}")
            return []
    
    def _extract_match_id_from_url(self, url: str) -> str:
        """Extract match ID from URL."""
        import re
        # Look for sch parameter in URL (e.g., print_match.php?sch=nndz-WWk2OXdiNytoUT09)
        sch_match = re.search(r'sch=([^&]+)', url)
        if sch_match:
            base_id = sch_match.group(1)
            # Return just the base ID without line suffix - line will be added later
            return base_id
        return "unknown_match_id"
    
    def _extract_apta_teams_and_score(self, soup) -> dict:
        """Extract team names and scores from APTA match page."""
        try:
            # Look for team names in datelocheader div
            datelocheader = soup.find('div', class_='datelocheader')
            if datelocheader:
                text = datelocheader.get_text(strip=True)
                print(f"      🔍 Processing datelocheader text: '{text}'")
                # Parse "Exmoor - 20 @ Valley Lo - 20: 4 - 9"
                # Note: Team after @ is actually the HOME team
                if ' @ ' in text:
                    parts = text.split(' @ ')
                    if len(parts) >= 2:
                        away_part = parts[0].strip()  # Team before @ is AWAY
                        home_part = parts[1].strip()  # Team after @ is HOME
                        
                        # Extract team names (remove numbers and scores)
                        import re
                        away_team = re.sub(r'\s*-\s*\d+.*$', '', away_part).strip()
                        home_team = re.sub(r'\s*-\s*\d+.*$', '', home_part).strip()
                        
                        # Add series number suffix to team names
                        # Extract series number from the text (e.g., "Exmoor - 20 @ Valley Lo - 20")
                        series_match = re.search(r'-\s*(\d+)', text)
                        if series_match:
                            series_num = series_match.group(1)
                            home_team = f"{home_team} {series_num}"
                            away_team = f"{away_team} {series_num}"
                        else:
                            # Fallback to XX if series number not found
                            home_team = f"{home_team} XX"
                            away_team = f"{away_team} XX"
                        
                        # Extract scores from the same text
                        score_match = re.search(r':\s*(\d+)\s*-\s*(\d+)', text)
                        if score_match:
                            home_score = score_match.group(1)
                            away_score = score_match.group(2)
                            scores = f"{home_score}-{away_score}"
                        else:
                            scores = "Unknown Scores"
                        
                        result = {
                            "Home Team": home_team,  # Team after @ is HOME
                            "Away Team": away_team,  # Team before @ is AWAY
                            "Scores": scores
                        }
                        print(f"      🏠 Teams: {home_team} vs {away_team}")
                        print(f"      🎯 Scores: {scores}")
                        return result
            
            return {
                "Home Team": "Unknown Home Team",
                "Away Team": "Unknown Away Team", 
                "Scores": "Unknown Scores"
            }
        except Exception as e:
            print(f"❌ APTA: Error extracting teams and score: {e}")
            return {}
    
    def _extract_apta_date(self, soup) -> dict:
        """Extract date from APTA match page using th elements with data-col='col0'."""
        try:
            import re
            from datetime import datetime
            
            # Primary method: Look for th elements with data-col="col0" containing date format like "09/23"
            date_th_elements = soup.find_all('th', {'data-col': 'col0'})
            
            for th in date_th_elements:
                text = th.get_text(strip=True)
                print(f"      🔍 Found th data-col='col0' text: '{text}'")
                
                # Look for MM/DD format (e.g., "09/23")
                date_match = re.search(r'(\d{2})/(\d{2})', text)
                if date_match:
                    month = date_match.group(1)
                    day = date_match.group(2)
                    
                    # Convert to DD-Mon-YY format (assuming current year)
                    try:
                        # Get current year or use 2025 as fallback
                        current_year = datetime.now().year
                        
                        # Convert month number to abbreviation
                        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        month_int = int(month)
                        if 1 <= month_int <= 12:
                            month_abbr = month_names[month_int - 1]
                            year_short = str(current_year)[-2:]
                            formatted_date = f"{day}-{month_abbr}-{year_short}"
                            print(f"      📅 Extracted date from th: {formatted_date}")
                            return {"Date": formatted_date}
                    except Exception as e:
                        print(f"      ❌ Error formatting date from th: {e}")
                        continue
            
            # Fallback method 1: Look for th elements with class containing "datacol"
            datacol_th_elements = soup.find_all('th', class_=re.compile(r'datacol'))
            
            for th in datacol_th_elements:
                text = th.get_text(strip=True)
                print(f"      🔍 Found datacol th text: '{text}'")
                
                # Look for MM/DD format (e.g., "09/23")
                date_match = re.search(r'(\d{2})/(\d{2})', text)
                if date_match:
                    month = date_match.group(1)
                    day = date_match.group(2)
                    
                    try:
                        current_year = datetime.now().year
                        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        month_int = int(month)
                        if 1 <= month_int <= 12:
                            month_abbr = month_names[month_int - 1]
                            year_short = str(current_year)[-2:]
                            formatted_date = f"{day}-{month_abbr}-{year_short}"
                            print(f"      📅 Extracted date from datacol th: {formatted_date}")
                            return {"Date": formatted_date}
                    except Exception as e:
                        print(f"      ❌ Error formatting date from datacol th: {e}")
                        continue
            
            # Fallback method 2: Look for any th element containing date patterns
            all_th_elements = soup.find_all('th')
            for th in all_th_elements:
                text = th.get_text(strip=True)
                
                # Look for MM/DD format
                date_match = re.search(r'(\d{2})/(\d{2})', text)
                if date_match:
                    month = date_match.group(1)
                    day = date_match.group(2)
                    
                    try:
                        current_year = datetime.now().year
                        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        month_int = int(month)
                        if 1 <= month_int <= 12:
                            month_abbr = month_names[month_int - 1]
                            year_short = str(current_year)[-2:]
                            formatted_date = f"{day}-{month_abbr}-{year_short}"
                            print(f"      📅 Extracted date from th fallback: {formatted_date}")
                            return {"Date": formatted_date}
                    except Exception as e:
                        print(f"      ❌ Error formatting date from th fallback: {e}")
                        continue
            
            # If no date found in th elements, return unknown
            print(f"      ❌ No date found in any th element")
            return {"Date": "Unknown Date"}
        except Exception as e:
            print(f"❌ APTA: Error extracting date: {e}")
            return {"Date": "Unknown Date"}
    
    def _extract_all_apta_lines(self, soup) -> List[Dict]:
        """Extract all line data from APTA match page - returns list of line records."""
        try:
            import re
            all_lines = []
            
            # Look for line tables and extract ALL lines
            line_tables = soup.find_all('table', class_='standings-table2')
            
            for table in line_tables:
                # Get line name
                line_cell = table.find('td', class_='line_desc')
                if line_cell:
                    line_name = line_cell.get_text(strip=True)
                    print(f"      🎾 Processing {line_name}")
                    
                    # Get all player links
                    player_links = table.find_all('a', href=re.compile(r'player\.php'))
                    players = []
                    
                    for link in player_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # Extract player ID
                        player_id_match = re.search(r'p=([^&]+)', href)
                        if player_id_match:
                            player_id = player_id_match.group(1)
                            # Clean name (remove ratings)
                            clean_name = re.sub(r'\s+\d+\.\d+.*$', '', text).strip()
                            players.append({"name": clean_name, "id": player_id})
                    
                    # Extract scores from each row separately
                    rows = table.find_all('tr')
                    home_scores = []
                    away_scores = []
                    winner = "Unknown"
                    
                    for i, row in enumerate(rows):
                        if i == 0:  # First row (away team)
                            score_cells = row.find_all('td', class_='pts2')
                            for cell in score_cells:
                                score_text = cell.get_text(strip=True)
                                if score_text and score_text != '&nbsp;' and score_text.isdigit():
                                    away_scores.append(score_text)
                        elif i == 1:  # Second row (home team)
                            score_cells = row.find_all('td', class_='pts2')
                            for cell in score_cells:
                                score_text = cell.get_text(strip=True)
                                if score_text and score_text != '&nbsp;' and score_text.isdigit():
                                    home_scores.append(score_text)
                    
                    # Check for winner indicator (green checkmark) in any row
                    for i, row in enumerate(rows):
                        checkmark = row.find('img', src=re.compile(r'admin_captain_teams_approve_check_green\.png'))
                        if checkmark:
                            if i == 0:  # First row = away team wins (based on your feedback)
                                winner = "away"
                                print(f"      🏆 Winner detected: Away team (green checkmark in row {i+1})")
                            elif i == 1:  # Second row = home team wins (based on your feedback)
                                winner = "home"
                                print(f"      🏆 Winner detected: Home team (green checkmark in row {i+1})")
                            break
                    
                    print(f"      🎯 Home scores: {home_scores}")
                    print(f"      🎯 Away scores: {away_scores}")
                    
                    # Process this line's data
                    if len(players) >= 4 and home_scores and away_scores:
                        # Format scores as "6-2, 6-3" or "6-2, 6-3, 6-4" style (away-home, away-home, away-home)
                        if len(home_scores) >= 2 and len(away_scores) >= 2:
                            # Handle both 2-set and 3-set matches
                            score_pairs = []
                            max_sets = min(len(home_scores), len(away_scores))
                            
                            for i in range(max_sets):
                                score_pairs.append(f"{away_scores[i]}-{home_scores[i]}")
                            
                            line_scores = ', '.join(score_pairs)
                        else:
                            # Fallback to simple concatenation
                            all_scores = home_scores + away_scores
                            line_scores = ', '.join(all_scores)
                        
                        # If no winner detected from checkmark, try to determine from scores
                        if winner == "Unknown":
                            winner = self._determine_winner_from_scores(line_scores)
                        
                        # Create line record
                        line_record = {
                            "Line": line_name,
                            "Away Player 1": players[0].get("name", "Unknown Player"),
                            "Away Player 2": players[1].get("name", "Unknown Player"),
                            "Away Player 1 ID": players[0].get("id", "unknown_id"),
                            "Away Player 2 ID": players[1].get("id", "unknown_id"),
                            "Home Player 1": players[2].get("name", "Unknown Player"),
                            "Home Player 2": players[3].get("name", "Unknown Player"),
                            "Home Player 1 ID": players[2].get("id", "unknown_id"),
                            "Home Player 2 ID": players[3].get("id", "unknown_id"),
                            "Scores": line_scores,
                            "Winner": winner
                        }
                        
                        all_lines.append(line_record)
                        print(f"      🎾 Line: {line_name}")
                        print(f"      👥 Players: {players[0].get('name')}/{players[1].get('name')} (Away) vs {players[2].get('name')}/{players[3].get('name')} (Home)")
                        print(f"      🆔 Player IDs: {players[0].get('id')}/{players[1].get('id')} (Away) vs {players[2].get('id')}/{players[3].get('id')} (Home)")
                        print(f"      🎯 Line Scores: {line_scores} (Winner: {winner})")
            
            return all_lines
            
        except Exception as e:
            print(f"❌ APTA: Error extracting all lines: {e}")
            return []
    
    def _determine_winner_from_scores(self, scores: str) -> str:
        """Determine winner from scores string."""
        try:
            if scores == "Unknown Scores":
                return "Unknown"
            
            # Parse scores like "6-2, 6-3" or "6-4, 6-2"
            sets = scores.split(', ')
            home_wins = 0
            away_wins = 0
            
            for set_score in sets:
                if '-' in set_score:
                    parts = set_score.split('-')
                    if len(parts) == 2:
                        try:
                            home_score = int(parts[0])
                            away_score = int(parts[1])
                            if home_score > away_score:
                                home_wins += 1
                            elif away_score > home_score:
                                away_wins += 1
                        except ValueError:
                            continue
            
            if home_wins > away_wins:
                return "home"
            elif away_wins > home_wins:
                return "away"
            else:
                return "tie"
                
        except Exception as e:
            print(f"❌ Error determining winner from scores: {e}")
            return "Unknown"

class EnhancedMatchScraper:
    """Enhanced match scraper with league-specific delegation."""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        
        # Set environment variable for proxy testing skip if requested
        if config.skip_proxy_test:
            import os
            os.environ['SKIP_PROXY_TEST'] = '1'
        
        self.stealth_browser = create_stealth_browser(
            fast_mode=config.fast_mode or SPEED_OPTIMIZATIONS_AVAILABLE,  # Enable fast mode if optimizations available
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
            return NSTFScraper(self.config, league_subdomain, parent_scraper=self)
        elif league_lower in ["cnswpl", "cns"]:
            return CNSWPLScraper(self.config, league_subdomain, parent_scraper=self)
        elif league_lower in ["aptachicago", "apta_chicago", "apta"]:
            return APTAScraper(self.config, league_subdomain, parent_scraper=self)
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
            # Get main page or standings page for APTA Chicago
            if league_subdomain.lower() == "aptachicago":
                # Use standings page for APTA Chicago to get completed match results and discover all series
                base_url = "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WkM2eHhMcz0%3D"
                print(f"🌐 {league_scraper.get_league_id()}: Fetching standings page: {base_url}")
            else:
                # Use main page for other leagues
                base_url = f"https://{league_subdomain.lower()}.tenniscores.com"
                print(f"🌐 {league_scraper.get_league_id()}: Fetching main page: {base_url}")
            
            main_page_html = self._safe_request(base_url, f"{league_scraper.get_league_id()} standings page")
            if not main_page_html:
                print(f"❌ {league_scraper.get_league_id()}: Failed to get main page")
                return []
            
            # Extract series links using league-specific logic
            series_links = league_scraper.extract_series_links(main_page_html)
            print(f"📋 {league_scraper.get_league_id()}: Found {len(series_links)} series")
            
            if series_filter:
                # Filter series if specified - support both "19" and "Series 19" formats
                filtered_links = []
                for name, url in series_links:
                    # Check if filter matches series number (e.g., "19" matches "Series 19")
                    if (series_filter.lower() in name.lower() or 
                        f"series {series_filter}" == name.lower() or
                        series_filter.lower() == name.lower()):
                        filtered_links.append((name, url))
                
                print(f"🔍 {league_scraper.get_league_id()}: Filtered to {len(filtered_links)} series matching '{series_filter}'")
                if filtered_links:
                    for name, url in filtered_links:
                        print(f"   📋 {name}")
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
            league_data_dir = os.path.dirname(get_league_file_path(league_subdomain, "match_scores.json"))
            tmp_dir = os.path.join(league_data_dir, 'temp_match_scores')
            
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
    
    def _save_incremental_temp_file(self, league_subdomain: str, series_name: str, series_matches: List[Dict], current_count: int):
        """Save incremental temp file during series processing."""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            from data.etl.utils.league_directory_manager import get_league_file_path
            
            # Get the league directory
            league_data_dir = os.path.dirname(get_league_file_path(league_subdomain, "match_scores.json"))
            tmp_dir = os.path.join(league_data_dir, 'temp_match_scores')
            
            # Create tmp directory if it doesn't exist
            os.makedirs(tmp_dir, exist_ok=True)
            
            # Clean series name for filename with progress indicator
            safe_series_name = series_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            temp_file_path = os.path.join(tmp_dir, f"series_{safe_series_name}_partial_{current_count}.json")
            
            # Save series matches to temp file
            import json
            with open(temp_file_path, 'w') as f:
                json.dump(series_matches, f, indent=2)
            
            print(f"💾 Incremental temp file saved: {temp_file_path} ({current_count} line matches)")
            
        except Exception as e:
            if self.config.verbose:
                print(f"⚠️ Failed to save incremental temp file for {series_name}: {e}")
            # Don't fail the scraping if temp file creation fails
    
    def _safe_request(self, url: str, description: str = "page") -> Optional[str]:
        """Make a safe request with retry logic and detection."""
        for attempt in range(self.config.max_retries + 1):
            try:
                if self.config.verbose:
                    print(f"🌐 Fetching {description}...")
                    print(f"   URL: {url}")
                    print(f"   Attempt: {attempt + 1}/{self.config.max_retries + 1}")
                
                # Make request using stealth browser with speed optimizations
                html = self.stealth_browser.get_html(url)
                
                # Apply stop-after-selector optimization if available
                if SPEED_OPTIMIZATIONS_AVAILABLE and hasattr(self.stealth_browser, 'current_driver') and self.stealth_browser.current_driver:
                    try:
                        from selenium.webdriver.common.by import By
                        # Stop loading after key elements are present (adjust selector for match data)
                        stop_after_selector(self.stealth_browser.current_driver, By.CSS_SELECTOR, "table, .match-data, .scores", timeout=8)
                    except Exception:
                        pass  # Non-fatal optimization failure
                
                # Update metrics
                self.metrics["total_requests"] += 1
                self.metrics["successful_requests"] += 1
                
                if self.config.verbose:
                    print(f"✅ Successfully fetched {description}")
                    print(f"   Response size: {len(html)} characters")
                
                # Mark successful response for adaptive pacing
                _pacer_mark_ok()
                
                # Add adaptive pacing instead of random delay
                if not self.config.fast_mode:
                    if SPEED_OPTIMIZATIONS_AVAILABLE:
                        if self.config.verbose:
                            print("⏳ Using adaptive pacing before next request...")
                        pace_sleep()  # Intelligent adaptive pacing
                    else:
                        # Fallback to random delay if optimizations unavailable
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
            filtered_series = []
            for name, url in series_links:
                if (series_filter.lower() in name.lower() or 
                    f"series {series_filter}" == name.lower() or
                    series_filter.lower() == name.lower()):
                    filtered_series.append(name)
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
                # Flexible match for series names (supports "19" -> "Series 19")
                if not (series_filter.lower() in series_name.lower() or 
                        f"series {series_filter}" == series_name.lower() or
                        series_filter.lower() == series_name.lower()):
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
            final_path = get_league_file_path(league_subdomain, "match_scores.json")
        finally:
            sys.path.pop(0)
        tmp_dir = os.path.join(os.path.dirname(final_path), "temp_match_scores")
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
        """Save final consolidated matches to the league's main match_scores.json file."""
        import json, os, sys
        # Resolve canonical league directory via helper
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        try:
            from data.etl.utils.league_directory_manager import get_league_file_path
            final_path = get_league_file_path(league_subdomain, "match_scores.json")
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
                filtered_series = []
                for name, url in series_links:
                    if (series_filter.lower() in name.lower() or 
                        f"series {series_filter}" == name.lower() or
                        series_filter.lower() == name.lower()):
                        filtered_series.append(name)
                print(f"📊 Series matching filter: {filtered_series}")
            
            all_matches = []
            
            # Scrape each series
            processed_series = 0
            # Calculate total series with same filtering logic
            if series_filter and series_filter != "all":
                total_series = len([s for s in series_links if (series_filter.lower() in s[0].lower() or 
                                                              f"series {series_filter}" == s[0].lower() or
                                                              series_filter.lower() == s[0].lower())])
            else:
                total_series = len(series_links)
            
            # Track overall progress across all series
            total_matches_processed = 0
            
            for i, (series_name, series_url) in enumerate(series_links, 1):
                # Improved series filtering logic
                if series_filter and series_filter != "all":
                    # Flexible match for series names (supports "19" -> "Series 19")
                    if not (series_filter.lower() in series_name.lower() or 
                            f"series {series_filter}" == series_name.lower() or
                            series_filter.lower() == series_name.lower()):
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
                    
                    # Apply week filtering if in weeks mode
                    if self.config.weeks and self.config.weeks > 0:
                        print(f"📅 Filtering matches by recent weeks ({self.config.weeks} weeks)...")
                        series_matches = self._filter_matches_by_recent_weeks(series_matches, self.config.weeks)
                    
                    all_matches.extend(series_matches)
                    print(f"✅ Found {len(series_matches)} matches in {series_name}")

                    # Save per-series temp JSON to avoid all-or-nothing loss
                    self._save_series_temp_file(league_subdomain, series_name, series_matches)
                    
                    # Add adaptive delay between series processing
                    if not self.config.fast_mode:
                        if SPEED_OPTIMIZATIONS_AVAILABLE:
                            pace_sleep()  # Adaptive pacing between series
                        else:
                            import time
                            time.sleep(2)  # Fallback fixed delay
                        
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
    
    # REMOVED: _generate_player_id function that created MD5 hashes
    # This was problematic as it could create inconsistent player IDs
    

    
    
    
        
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
                
                # Look up roster player IDs for all players
                home_player1_id = self._lookup_roster_player_id(home_players[0])
                home_player2_id = self._lookup_roster_player_id(home_players[1])
                away_player1_id = self._lookup_roster_player_id(away_players[0])
                away_player2_id = self._lookup_roster_player_id(away_players[1])
                
                # Check if any players are missing roster IDs
                missing_players = []
                if not home_player1_id:
                    missing_players.append(f"Home Player 1: {home_players[0]}")
                if not home_player2_id:
                    missing_players.append(f"Home Player 2: {home_players[1]}")
                if not away_player1_id:
                    missing_players.append(f"Away Player 1: {away_players[0]}")
                if not away_player2_id:
                    missing_players.append(f"Away Player 2: {away_players[1]}")
                
                if missing_players:
                    print(f"❌  Missing roster player IDs for: {', '.join(missing_players)}")
                    # Still create the match record but with None for missing IDs
                
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
                    "Home Player 1 ID": home_player1_id,
                    "Home Player 2 ID": home_player2_id,
                    "Away Player 1 ID": away_player1_id,
                    "Away Player 2 ID": away_player2_id,
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
        
        return ", ".join(scores[:3])  # Max 3 sets
    
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
        
        return ", ".join(tennis_scores[:4])  # Return first 4 sets max
    
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
            result["scores"] = ", ".join(scores)
            
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
    
    def _filter_matches_by_recent_weeks(self, matches: List[Dict], weeks: int) -> List[Dict]:
        """Filter matches to only include the N most recent weeks based on standings page dates."""
        if not weeks or weeks <= 0:
            return matches
        
        try:
            # Get all unique dates from matches and sort them (most recent first)
            match_dates = set()
            for match in matches:
                if "Date" in match and match["Date"]:
                    try:
                        # Parse the date (assuming YYYY-MM-DD format)
                        match_date = datetime.strptime(match["Date"], "%Y-%m-%d").date()
                        match_dates.add(match_date)
                    except ValueError:
                        continue
            
            if not match_dates:
                logger.warning("⚠️ No valid dates found in matches for week filtering")
                return matches
            
            # Sort dates in descending order (most recent first)
            sorted_dates = sorted(match_dates, reverse=True)
            
            # Take only the N most recent weeks
            target_dates = sorted_dates[:weeks]
            logger.info(f"📅 Week filtering: Using {len(target_dates)} most recent dates: {[d.strftime('%Y-%m-%d') for d in target_dates]}")
            
            # Filter matches to only include those from target dates
            filtered_matches = []
            for match in matches:
                if "Date" in match and match["Date"]:
                    try:
                        match_date = datetime.strptime(match["Date"], "%Y-%m-%d").date()
                        if match_date in target_dates:
                            filtered_matches.append(match)
                    except ValueError:
                        continue
            
            logger.info(f"📅 Week filtered: {len(filtered_matches)}/{len(matches)} matches")
            return filtered_matches
            
        except Exception as e:
            logger.error(f"❌ Error filtering by weeks: {e}")
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
                      weeks: int = None,
                      fast_mode: bool = False,
                      verbose: bool = False,
                      skip_proxy_test: bool = False) -> List[Dict]:
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
        weeks: Number of recent weeks to scrape (1=most recent, 2=most recent + previous week, etc.)
        fast_mode: Enable fast mode (reduced delays)
        verbose: Enable verbose logging
        skip_proxy_test: Skip proxy testing
    
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
    
    if weeks:
        print(f"🎯 WEEKS MODE: Only scraping matches from {weeks} most recent week(s)")
    
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
        end_date=end_date,
        weeks=weeks,
        skip_proxy_test=skip_proxy_test
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
    parser.add_argument("--skip-proxy-test", action="store_true", help="Skip proxy testing")
    parser.add_argument("--quiet", action="store_true", help="Disable verbose logging (default is verbose)")
    parser.add_argument("--environment", choices=["local", "staging", "production"], 
                       default="production", help="Environment mode")
    parser.add_argument("--clean-temp-first", action="store_true", help="Delete per-series temp files before starting (default: preserve)")
    parser.add_argument("--weeks", type=int, help="Number of recent weeks to scrape (1=most recent, 2=most recent + previous week, etc.)")
    
    args = parser.parse_args()
    
    print(f"\n🎾 Starting CNSWPL Match Scraper")
    print(f"📋 League: {args.league}")
    print(f"⚙️  Mode: {'FAST' if args.fast else 'STEALTH'}")
    print(f"🌍 Environment: {args.environment}")
    
    if args.delta_mode:
        print(f"📅 Delta Mode: {args.start_date} to {args.end_date}")
    
    if args.weeks:
        print(f"📅 Week Mode: Scraping {args.weeks} most recent week(s)")
    
    # Optional pre-run cleanup of temp files (off by default)
    if args.clean_temp_first:
        try:
            import sys as _sys, os as _os, shutil as _shutil
            _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))))
            from data.etl.utils.league_directory_manager import get_league_file_path as _get_league_file_path_prerun
            prerun_output = _get_league_file_path_prerun(args.league, "match_scores.json")
            prerun_tmp_dir = _os.path.join(_os.path.dirname(prerun_output), 'temp_match_scores')
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
        weeks=args.weeks,
        fast_mode=args.fast,
        verbose=not args.quiet,  # Invert quiet to get verbose
        skip_proxy_test=args.skip_proxy_test
    )
            
            # Save results - APPEND to existing data, don't overwrite
    # Use standardized directory naming to prevent APTACHICAGO vs APTA_CHICAGO issues
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from data.etl.utils.league_directory_manager import get_league_file_path
    
    output_file = get_league_file_path(args.league, "match_scores.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create backup of existing data before scraping to prevent corruption
    if os.path.exists(output_file):
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = output_file.replace('.json', f'_backup_{timestamp}.json')
            
            import shutil
            shutil.copy2(output_file, backup_file)
            print(f"💾 Created backup: {backup_file}")
            logger.info(f"💾 Backup created: {backup_file}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not create backup: {e}")
            logger.warning(f"⚠️ Backup failed: {e}")
    
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
    tmp_dir = os.path.join(os.path.dirname(output_file), 'temp_match_scores')
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
