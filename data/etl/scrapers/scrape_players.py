#!/usr/bin/env python3
"""
Incremental Player Scraper

This script scrapes player data for specific tenniscores_player_ids only.
It's designed to be efficient and incremental - only scraping players who appeared in newly scraped matches.

Usage:
    python3 data/etl/scrapers/scrape_players.py <league_subdomain> <player_ids_file>
    python3 data/etl/scrapers/scrape_players.py aptachicago player_ids.txt

The script:
1. Reads a list of tenniscores_player_ids from a file or accepts them as input
2. For each ID, scrapes the player's profile page
3. Extracts: tenniscores_player_id, name, team_name, league_id, series, current_pti
4. Saves the data to a JSON file for import
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Import stealth browser manager for fingerprint evasion
from stealth_browser import StealthBrowserManager
from utils.league_utils import standardize_league_id


class IncrementalPlayerScraper:
    """Scraper for specific player IDs only"""
    
    def __init__(self, league_subdomain: str):
        self.league_subdomain = league_subdomain.lower()
        self.league_id = standardize_league_id(league_subdomain)
        self.base_url = f"https://{league_subdomain}.tenniscores.com"
        self.chrome_manager = None
        self.driver = None
        
        # Statistics
        self.stats = {
            'total_players': 0,
            'scraped': 0,
            'errors': 0,
            'not_found': 0
        }
        
        print(f"🎾 Incremental Player Scraper for {self.league_subdomain}")
        print(f"📊 League ID: {self.league_id}")
        print(f"🌐 Base URL: {self.base_url}")
    
    def setup_browser(self):
        """Set up the Chrome browser with stealth settings"""
        try:
            self.chrome_manager = StealthBrowserManager()
            self.driver = self.chrome_manager.create_driver()
            print("✅ Browser setup complete")
            return True
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            return False
    
    def cleanup_browser(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                print("🧹 Browser cleaned up")
            except Exception as e:
                print(f"⚠️ Browser cleanup warning: {e}")
    
    def build_player_url(self, player_id: str) -> str:
        """Build the player profile URL"""
        return f"{self.base_url}/player/view?id={player_id}"
    
    def extract_player_data(self, player_id: str) -> Optional[Dict]:
        """Extract player data from the profile page"""
        url = self.build_player_url(player_id)
        
        try:
            print(f"🔍 Scraping player: {player_id}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Add a small delay to ensure dynamic content loads
            time.sleep(2)
            
            # Parse the page
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract player data
            player_data = self._parse_player_page(soup, player_id)
            
            if player_data:
                print(f"✅ Successfully scraped: {player_data.get('name', 'Unknown')}")
                return player_data
            else:
                print(f"⚠️ No data found for player: {player_id}")
                return None
                
        except TimeoutException:
            print(f"❌ Timeout scraping player: {player_id}")
            self.stats['errors'] += 1
            return None
        except Exception as e:
            print(f"❌ Error scraping player {player_id}: {e}")
            self.stats['errors'] += 1
            return None
    
    def _parse_player_page(self, soup: BeautifulSoup, player_id: str) -> Optional[Dict]:
        """Parse the player profile page and extract data with enhanced validation"""
        try:
            # Parse player name
            first_name, last_name = self._extract_player_name(soup)
            
            # Extract team and series information
            team_info = self._extract_team_info(soup)
            
            # Extract PTI (Performance Tracking Index)
            pti = self._extract_pti(soup)
            
            # Extract win/loss statistics
            wins, losses, win_percentage = self._extract_win_loss_stats(soup)
            
            # Extract captain status
            captain_status = self._extract_captain_status(soup)
            
            # Enhanced validation and fallback logic
            validation_issues = []
            
            # Name validation
            if not first_name and not last_name:
                validation_issues.append("No player name found")
                # Try to extract from page title or other sources
                page_title = soup.find('title')
                if page_title:
                    title_text = page_title.get_text(strip=True)
                    if title_text and len(title_text) > 3:
                        # Extract name from title (e.g., "John Doe - Player Profile")
                        name_part = title_text.split('-')[0].strip()
                        if name_part:
                            name_parts = name_part.split()
                            if len(name_parts) >= 2:
                                first_name = name_parts[0]
                                last_name = ' '.join(name_parts[1:])
                            else:
                                first_name = name_part
                                last_name = ""
            
            # Team info validation with fallbacks
            if not team_info:
                validation_issues.append("No team info found")
                # Create minimal team info
                team_info = {
                    'team_name': 'Unknown',
                    'series': '',
                    'club_name': 'Unknown'
                }
            else:
                # Validate team info components
                if not team_info.get('team_name'):
                    team_info['team_name'] = 'Unknown'
                    validation_issues.append("No team name found")
                
                if not team_info.get('club_name'):
                    team_info['club_name'] = team_info.get('team_name', 'Unknown')
                
                if not team_info.get('series'):
                    # Try to extract series from page content
                    page_text = soup.get_text()
                    series_patterns = [
                        r'Series\s+(\d+|[A-Z]+)',
                        r'Division\s+(\d+|[A-Z]+)',
                        r'(\d+|[A-Z]+)\s+Series',
                        r'(\d+|[A-Z]+)\s+Division'
                    ]
                    
                    for pattern in series_patterns:
                        import re
                        series_match = re.search(pattern, page_text, re.IGNORECASE)
                        if series_match:
                            team_info['series'] = series_match.group(1)
                            break
            
            # PTI validation
            if pti is None:
                validation_issues.append("No PTI found")
            
            # Win/loss validation
            if wins is None and losses is None:
                validation_issues.append("No win/loss stats found")
            
            # Build player data with validation info
            player_data = {
                "League": self.league_id,
                "Series": team_info.get('series', ''),
                "Series Mapping ID": team_info.get('team_name', ''),
                "Club": team_info.get('club_name', ''),
                "Location ID": self._generate_location_id(team_info.get('club_name', '')),
                "Player ID": player_id,
                "First Name": first_name or "Unknown",
                "Last Name": last_name or "",
                "PTI": str(pti) if pti is not None else "N/A",
                "Wins": str(wins) if wins is not None else "0",
                "Losses": str(losses) if losses is not None else "0",
                "Win %": f"{win_percentage:.1f}%" if win_percentage is not None else "0.0%",
                "Captain": captain_status,
                "source_league": self.league_id,
                "validation_issues": validation_issues if validation_issues else []
            }
            
            # Log validation issues if any
            if validation_issues:
                print(f"⚠️ Player {player_id} has validation issues: {', '.join(validation_issues)}")
                print(f"   Using fallback data where possible")
            
            return player_data
            
        except Exception as e:
            print(f"❌ Error parsing player page for {player_id}: {e}")
            return None
    
    def _extract_team_info(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract team and series information with enhanced parsing"""
        try:
            team_info = {'team_name': '', 'series': '', 'club_name': ''}
            
            # Strategy 1: Look for team information in various HTML elements
            team_selectors = [
                '.team-info', '.player-team', '.current-team', '.team-name',
                'td:contains("Team")', 'td:contains("Club")', '.team', '.club',
                'span:contains("Team")', 'span:contains("Club")', '.player-club',
                '.current-club', '.team-details', '.club-info'
            ]
            
            for selector in team_selectors:
                try:
                    team_elem = soup.select_one(selector)
                    if team_elem:
                        text = team_elem.get_text(strip=True)
                        if text and len(text) > 2:
                            team_info = self._parse_team_text(text)
                            if team_info['team_name']:
                                break
                except:
                    continue
            
            # Strategy 2: Look for team info in table rows
            if not team_info['team_name']:
                table_rows = soup.find_all('tr')
                for row in table_rows:
                    cells = row.find_all(['td', 'th'])
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True).lower()
                        if 'team' in cell_text or 'club' in cell_text:
                            if i + 1 < len(cells):
                                next_cell_text = cells[i + 1].get_text(strip=True)
                                if next_cell_text and len(next_cell_text) > 2:
                                    team_info = self._parse_team_text(next_cell_text)
                                    if team_info['team_name']:
                                        break
                    if team_info['team_name']:
                        break
            
            # Strategy 3: Look for patterns in page content
            if not team_info['team_name']:
                page_text = soup.get_text()
                team_patterns = [
                    r'Team:\s*([^\n\r]+)',
                    r'Club:\s*([^\n\r]+)',
                    r'Current Team:\s*([^\n\r]+)',
                    r'Current Club:\s*([^\n\r]+)',
                    r'Playing for:\s*([^\n\r]+)',
                    r'Member of:\s*([^\n\r]+)'
                ]
                
                for pattern in team_patterns:
                    import re
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        team_text = match.group(1).strip()
                        team_info = self._parse_team_text(team_text)
                        if team_info['team_name']:
                            break
            
            # Strategy 4: Look for known club names in page content
            if not team_info['team_name']:
                page_text = soup.get_text()
                known_clubs = {
                    'birchwood': 'Birchwood',
                    'lake bluff': 'Lake Bluff', 
                    'glenbrook': 'Glenbrook',
                    'tennaqua': 'Tennaqua',
                    'exmoor': 'Exmoor',
                    'westmoreland': 'Westmoreland',
                    'prairie club': 'Prairie Club',
                    'sunset ridge': 'Sunset Ridge',
                    'ruth lake': 'Ruth Lake',
                    'hinsdale': 'Hinsdale',
                    'valley lo': 'Valley Lo',
                    'lakeshore': 'Lakeshore',
                    'barrington hills': 'Barrington Hills',
                    'glenbrook rc': 'Glenbrook RC',
                    'glenbrook racquet': 'Glenbrook RC'
                }
                
                for club_key, club_name in known_clubs.items():
                    if club_key in page_text.lower():
                        team_info['team_name'] = club_name
                        team_info['club_name'] = club_name
                        
                        # Try to extract series from context
                        series_patterns = [
                            rf'{club_key}\s+(\d+|[A-Z]+)',
                            rf'{club_key}.*?(\d+|[A-Z]+)',
                            rf'Series\s+(\d+|[A-Z]+)',
                            rf'Division\s+(\d+|[A-Z]+)'
                        ]
                        
                        for pattern in series_patterns:
                            import re
                            series_match = re.search(pattern, page_text, re.IGNORECASE)
                            if series_match:
                                team_info['series'] = series_match.group(1)
                                break
                        break
            
            # Strategy 5: Look for series information in isolation
            if not team_info['series']:
                page_text = soup.get_text()
                series_patterns = [
                    r'Series\s+(\d+|[A-Z]+)',
                    r'Division\s+(\d+|[A-Z]+)',
                    r'(\d+|[A-Z]+)\s+Series',
                    r'(\d+|[A-Z]+)\s+Division'
                ]
                
                for pattern in series_patterns:
                    import re
                    series_match = re.search(pattern, page_text, re.IGNORECASE)
                    if series_match:
                        team_info['series'] = series_match.group(1)
                        break
            
            # Return team info if we found at least a team name
            return team_info if team_info['team_name'] else None
            
        except Exception as e:
            print(f"⚠️ Error extracting team info: {e}")
            return None
    
    def _parse_team_text(self, text: str) -> Dict:
        """Parse team text to extract team name, club name, and series"""
        team_info = {'team_name': '', 'series': '', 'club_name': ''}
        
        if not text or len(text) < 2:
            return team_info
        
        # Clean the text
        text = text.strip()
        
        # Handle common patterns
        if ' - ' in text:
            parts = text.split(' - ')
            if len(parts) >= 2:
                team_info['team_name'] = parts[0].strip()
                team_info['series'] = parts[1].strip()
                team_info['club_name'] = parts[0].strip()
        elif ' vs ' in text:
            # This might be a match description, not team info
            return team_info
        else:
            # Split by spaces and analyze
            parts = text.split()
            
            if len(parts) == 1:
                # Single word - likely just team name
                team_info['team_name'] = parts[0]
                team_info['club_name'] = parts[0]
            elif len(parts) == 2:
                # Two words - could be "Team Series" or "Club Name"
                # Check if second part looks like a series
                if self._is_series_indicator(parts[1]):
                    team_info['team_name'] = parts[0]
                    team_info['series'] = parts[1]
                    team_info['club_name'] = parts[0]
                else:
                    # Assume it's a two-word team name
                    team_info['team_name'] = text
                    team_info['club_name'] = text
            elif len(parts) == 3:
                # Three words - could be "Club Series Number" like "Tennaqua Series 22"
                if parts[1].lower() == 'series' and self._is_series_indicator(parts[2]):
                    team_info['team_name'] = parts[0]
                    team_info['series'] = f"{parts[1]} {parts[2]}"
                    team_info['club_name'] = parts[0]
                else:
                    # Check if any part looks like a series
                    series_found = False
                    for i, part in enumerate(parts):
                        if self._is_series_indicator(part):
                            team_info['series'] = part
                            team_info['team_name'] = ' '.join(parts[:i] + parts[i+1:])
                            team_info['club_name'] = ' '.join(parts[:i] + parts[i+1:])
                            series_found = True
                            break
                    
                    if not series_found:
                        # No clear series indicator, treat as team name
                        team_info['team_name'] = text
                        team_info['club_name'] = text
            else:
                # Multiple words - try to identify series at the end
                if self._is_series_indicator(parts[-1]):
                    team_info['series'] = parts[-1]
                    team_info['team_name'] = ' '.join(parts[:-1])
                    team_info['club_name'] = ' '.join(parts[:-1])
                else:
                    # Check if any part looks like a series
                    series_found = False
                    for i, part in enumerate(parts):
                        if self._is_series_indicator(part):
                            team_info['series'] = part
                            team_info['team_name'] = ' '.join(parts[:i] + parts[i+1:])
                            team_info['club_name'] = ' '.join(parts[:i] + parts[i+1:])
                            series_found = True
                            break
                    
                    if not series_found:
                        # No clear series indicator, treat as team name
                        team_info['team_name'] = text
                        team_info['club_name'] = text
        
        return team_info
    
    def _is_series_indicator(self, text: str) -> bool:
        """Check if text looks like a series indicator"""
        if not text:
            return False
        
        text = text.strip().upper()
        
        # Series patterns
        series_patterns = [
            r'^\d+$',  # Just numbers
            r'^S\d+$',  # S1, S2, etc.
            r'^SERIES\s+\d+$',  # SERIES 1, SERIES 2, etc.
            r'^DIVISION\s+\d+$',  # DIVISION 1, DIVISION 2, etc.
            r'^DIV\s+\d+$',  # DIV 1, DIV 2, etc.
            r'^\d+[A-Z]$',  # 1A, 2B, etc.
            r'^[A-Z]\d+$',  # A1, B2, etc.
        ]
        
        import re
        for pattern in series_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _extract_player_name(self, soup: BeautifulSoup) -> tuple:
        """Extract first and last name from the player page with enhanced parsing"""
        try:
            # Strategy 1: Look for player name in various HTML elements
            name_selectors = [
                'h1', 'h2', 'h3', 'h4',
                '.player-name', '.player-title', '.profile-name',
                'h1.player-name', '.name', '.player-info .name',
                '.profile-header h1', '.player-header h1',
                'title', '.page-title', '.main-title'
            ]
            
            full_name = ""
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    text = name_elem.get_text(strip=True)
                    if text and len(text) > 2 and self._is_valid_name(text):
                        full_name = text
                        break
            
            # Strategy 2: Look for name in table cells
            if not full_name:
                table_rows = soup.find_all('tr')
                for row in table_rows:
                    cells = row.find_all(['td', 'th'])
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text(strip=True).lower()
                        if 'name' in cell_text or 'player' in cell_text:
                            if i + 1 < len(cells):
                                next_cell_text = cells[i + 1].get_text(strip=True)
                                if next_cell_text and self._is_valid_name(next_cell_text):
                                    full_name = next_cell_text
                                    break
                    if full_name:
                        break
            
            # Strategy 3: Look for name patterns in page content
            if not full_name:
                page_text = soup.get_text()
                name_patterns = [
                    r'Name:\s*([^\n\r]+)',
                    r'Player:\s*([^\n\r]+)',
                    r'Player Name:\s*([^\n\r]+)'
                ]
                
                for pattern in name_patterns:
                    import re
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        potential_name = match.group(1).strip()
                        if self._is_valid_name(potential_name):
                            full_name = potential_name
                            break
            
            if not full_name:
                return "", ""
            
            # Clean and parse the name
            full_name = self._clean_name(full_name)
            
            # Split into first and last name
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                first_name = full_name
                last_name = ""
            
            return first_name, last_name
            
        except Exception as e:
            print(f"⚠️ Error extracting player name: {e}")
            return "", ""
    
    def _is_valid_name(self, text: str) -> bool:
        """Check if text looks like a valid player name"""
        if not text or len(text) < 2:
            return False
        
        # Clean the text
        text = text.strip()
        
        # Must contain at least one letter
        import re
        if not re.search(r'[a-zA-Z]', text):
            return False
        
        # Check for common non-name patterns
        invalid_patterns = [
            r'^\d+$',  # Just numbers
            r'^player$', r'^profile$', r'^team$', r'^club$',  # Exact matches for common words
            r'^tennis$', r'^scores$', r'^league$', r'^match$'
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
        
        # Check for reasonable name characteristics
        if len(text.split()) > 5:  # Too many words for a name
            return False
        
        return True
    
    def _clean_name(self, name: str) -> str:
        """Clean and normalize a player name"""
        if not name:
            return ""
        
        # Remove common prefixes/suffixes
        name = name.strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            'Player:', 'Name:', 'Player Name:', 'Profile:', 'Member:'
        ]
        for prefix in prefixes_to_remove:
            if name.lower().startswith(prefix.lower()):
                name = name[len(prefix):].strip()
        
        # Remove common suffixes
        suffixes_to_remove = [
            ' - Player Profile', ' - Profile', ' - Tennis Player',
            ' (Player)', ' (Member)', ' - Member'
        ]
        for suffix in suffixes_to_remove:
            if name.lower().endswith(suffix.lower()):
                name = name[:-len(suffix)].strip()
        
        # Normalize whitespace
        name = ' '.join(name.split())
        
        return name

    def _extract_pti(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract PTI (Performance Tracking Index)"""
        try:
            # Look for PTI in various formats
            pti_patterns = [
                r'PTI:\s*([\d.]+)',
                r'Performance Tracking Index:\s*([\d.]+)',
                r'Rating:\s*([\d.]+)',
                r'Current PTI:\s*([\d.]+)'
            ]
            
            page_text = soup.get_text()
            
            for pattern in pti_patterns:
                import re
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        pti_value = float(match.group(1))
                        return pti_value
                    except ValueError:
                        continue
            
            # Try to find PTI in table cells
            pti_selectors = [
                'td:contains("PTI")',
                'td:contains("Rating")',
                '.pti-value',
                '.rating-value'
            ]
            
            for selector in pti_selectors:
                try:
                    pti_elem = soup.select_one(selector)
                    if pti_elem:
                        # Get the next sibling or parent for the value
                        value_elem = pti_elem.find_next_sibling() or pti_elem.parent
                        if value_elem:
                            text = value_elem.get_text(strip=True)
                            try:
                                pti_value = float(text)
                                return pti_value
                            except ValueError:
                                continue
                except:
                    continue
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error extracting PTI: {e}")
            return None

    def _extract_win_loss_stats(self, soup: BeautifulSoup) -> tuple:
        """Extract win/loss statistics"""
        try:
            wins, losses = None, None
            
            # Look for win/loss patterns in the page
            page_text = soup.get_text()
            
            # Common patterns for win/loss stats
            win_loss_patterns = [
                r'(\d+)\s*wins?\s*[,\s]\s*(\d+)\s*losses?',
                r'Wins:\s*(\d+).*?Losses:\s*(\d+)',
                r'Record:\s*(\d+)-(\d+)',
                r'(\d+)-(\d+)',
            ]
            
            for pattern in win_loss_patterns:
                import re
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        wins = int(match.group(1))
                        losses = int(match.group(2))
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Calculate win percentage
            win_percentage = None
            if wins is not None and losses is not None and (wins + losses) > 0:
                win_percentage = (wins / (wins + losses)) * 100
            
            return wins, losses, win_percentage
            
        except Exception as e:
            print(f"⚠️ Error extracting win/loss stats: {e}")
            return None, None, None

    def _extract_captain_status(self, soup: BeautifulSoup) -> str:
        """Extract captain status"""
        try:
            page_text = soup.get_text()
            
            # Look for captain indicators
            captain_patterns = [
                r'Captain',
                r'C\b',
                r'Team Captain',
                r'Co-Captain'
            ]
            
            for pattern in captain_patterns:
                import re
                if re.search(pattern, page_text, re.IGNORECASE):
                    if 'co-captain' in page_text.lower():
                        return "CC"
                    elif 'captain' in page_text.lower():
                        return "C"
            
            return ""
            
        except Exception as e:
            print(f"⚠️ Error extracting captain status: {e}")
            return ""

    def _generate_location_id(self, club_name: str) -> str:
        """Generate location ID from club name"""
        if not club_name:
            return ""
        
        # Convert club name to location ID format
        # e.g., "Birchwood" -> "BIRCHWOOD", "Lake Bluff" -> "LAKE_BLUFF"
        location_id = club_name.upper().replace(" ", "_").replace("-", "_")
        return location_id
    
    def scrape_players(self, player_ids: List[str]) -> List[Dict]:
        """Scrape data for the specified player IDs"""
        if not self.setup_browser():
            return []
        
        self.stats['total_players'] = len(player_ids)
        scraped_players = []
        
        try:
            for i, player_id in enumerate(player_ids, 1):
                print(f"\n📊 Progress: {i}/{len(player_ids)} ({i/len(player_ids)*100:.1f}%)")
                
                player_data = self.extract_player_data(player_id)
                
                if player_data:
                    scraped_players.append(player_data)
                    self.stats['scraped'] += 1
                else:
                    self.stats['not_found'] += 1
                
                # Add delay between requests to be respectful
                time.sleep(1)
                
        finally:
            self.cleanup_browser()
        
        return scraped_players
    
    def save_players_data(self, players: List[Dict], output_file: str = None):
        """Save scraped player data to JSON file"""
        if not output_file:
            # Create default output file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/leagues/all/players_incremental_{timestamp}.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(players, f, indent=2)
            
            print(f"💾 Saved {len(players)} players to: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Error saving player data: {e}")
            return None
    
    def print_summary(self):
        """Print scraping summary"""
        print("\n" + "=" * 60)
        print("📊 PLAYER SCRAPING SUMMARY")
        print("=" * 60)
        print(f"📄 Total players requested: {self.stats['total_players']:,}")
        print(f"✅ Successfully scraped: {self.stats['scraped']:,}")
        print(f"❌ Errors: {self.stats['errors']}")
        print(f"⚠️ Not found: {self.stats['not_found']}")
        
        if self.stats['total_players'] > 0:
            success_rate = (self.stats['scraped'] / self.stats['total_players']) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")
        
        print("=" * 60)





def extract_player_ids_from_match_history(match_history_file: str) -> Set[str]:
    """Extract unique player IDs from match history JSON"""
    try:
        with open(match_history_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        player_ids = set()
        
        for match in matches:
            # Extract player IDs from all player fields
            player_fields = [
                'Home Player 1 ID', 'Home Player 2 ID',
                'Away Player 1 ID', 'Away Player 2 ID'
            ]
            
            for field in player_fields:
                player_id = match.get(field)
                if player_id and isinstance(player_id, str):
                    player_id = player_id.strip()
                    if player_id:
                        player_ids.add(player_id)
        
        print(f"🎾 Extracted {len(player_ids)} unique player IDs from match history")
        return player_ids
        
    except Exception as e:
        print(f"❌ Error extracting player IDs from match history: {e}")
        return set()


def extract_active_player_ids(scraped_matches):
    """
    Extract unique player IDs from recently scraped matches.
    
    Args:
        scraped_matches (list): List of match dictionaries containing player data
        
    Returns:
        set: Set of unique tenniscores_player_ids to scrape
    """
    recent_players = set()

    for match in scraped_matches:
        # Extract player IDs from all player fields in the match
        player_fields = [
            'Home Player 1 ID', 'Home Player 2 ID',
            'Away Player 1 ID', 'Away Player 2 ID'
        ]
        
        for field in player_fields:
            player_id = match.get(field, '').strip()
            if player_id:
                recent_players.add(player_id)

    print(f"🎾 Extracted {len(recent_players)} unique player IDs from {len(scraped_matches)} matches")
    return recent_players


def extract_active_player_ids_from_team_players(scraped_matches):
    """
    Extract unique player IDs from matches with team1_players and team2_players structure.
    
    Args:
        scraped_matches (list): List of match dictionaries with team1_players and team2_players
        
    Returns:
        set: Set of unique tenniscores_player_ids to scrape
    """
    recent_players = set()

    for match in scraped_matches:
        team1 = match.get("team1_players", [])
        team2 = match.get("team2_players", [])

        for player in team1 + team2:
            pid = player.get("tenniscores_player_id")
            if pid:
                recent_players.add(pid)

    print(f"🎾 Extracted {len(recent_players)} unique player IDs from {len(scraped_matches)} matches")
    return recent_players





def main():
    """Main function"""
    print("🎾 Incremental Player Scraper")
    print("=" * 60)
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_players.py <league_subdomain>")
        print("Examples:")
        print("  python3 scrape_players.py aptachicago")
        print("  python3 scrape_players.py nstf")
        sys.exit(1)
    
    league_subdomain = sys.argv[1]
    
    # Always extract player IDs from match history
    match_history_file = "data/leagues/all/match_history.json"
    if not os.path.exists(match_history_file):
        print(f"❌ Match history file not found: {match_history_file}")
        print("Please run match scraping first to generate match_history.json")
        sys.exit(1)
    
    # Extract player IDs from match history
    player_ids = list(extract_player_ids_from_match_history(match_history_file))
    
    if not player_ids:
        print("❌ No player IDs found in match history")
        print("No matches have been scraped yet or no player IDs in matches")
        sys.exit(1)
    
    print(f"🎾 Found {len(player_ids)} unique player IDs in match history")
    
    # Create scraper and run
    scraper = IncrementalPlayerScraper(league_subdomain)
    scraped_players = scraper.scrape_players(player_ids)
    
    # Save results
    if scraped_players:
        output_file = scraper.save_players_data(scraped_players)
        if output_file:
            print(f"✅ Player scraping completed! Data saved to: {output_file}")
        else:
            print("❌ Failed to save player data")
    else:
        print("❌ No players were successfully scraped")
    
    # Print summary
    scraper.print_summary()


if __name__ == "__main__":
    main() 