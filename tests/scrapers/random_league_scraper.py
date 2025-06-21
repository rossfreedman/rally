"""
Rally Test Data Scraper
Automated scraper to pull real player data from TennisScores for testing purposes
Generates both valid and intentionally invalid test data
"""

import os
import sys
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Optional
import tempfile
import requests
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class TennisScoresTestDataScraper:
    """Scraper to generate test data from real TennisScores websites"""
    
    def __init__(self, max_players_per_league=20, max_invalid_players=10):
        self.max_players_per_league = max_players_per_league
        self.max_invalid_players = max_invalid_players
        self.valid_players = []
        self.invalid_players = []
        self.leagues_scraped = []
        
        # Common TennisScores league configurations
        self.league_configs = {
            'APTA_CHICAGO': {
                'base_url': 'https://aptachicago.tenniscores.com',
                'main_page_mod': 'nndz-SkhmOW1PQ3V4Zz09',
                'league_id': 'APTA_CHICAGO',
                'league_name': 'APTA Chicago'
            },
            'NSTF': {
                'base_url': 'https://nstf.tenniscores.com',
                'main_page_mod': 'nndz-QXZNKzh4N0F0QT09',
                'league_id': 'NSTF',
                'league_name': 'North Shore Tennis Foundation'
            },
            'CITA': {
                'base_url': 'https://cita.tenniscores.com',
                'main_page_mod': 'basic',
                'league_id': 'CITA',
                'league_name': 'Connecticut Indoor Tennis Association'
            }
        }
        
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        print("🚀 Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Create temporary user data directory
        user_data_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✅ Chrome WebDriver initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Chrome WebDriver: {e}")
            return False
    
    def cleanup_driver(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Chrome WebDriver cleaned up")
            except Exception as e:
                print(f"⚠️ Error cleaning up WebDriver: {e}")
    
    def scrape_league_players(self, league_key: str, sample_size: int = None) -> List[Dict]:
        """Scrape player data from a specific league"""
        if sample_size is None:
            sample_size = self.max_players_per_league
            
        config = self.league_configs.get(league_key)
        if not config:
            print(f"❌ Unknown league: {league_key}")
            return []
        
        print(f"\n🎾 Scraping {config['league_name']} ({league_key})")
        print(f"   Target: {sample_size} players")
        
        players = []
        
        try:
            # Build main URL
            main_url = f"{config['base_url']}/?mod={config['main_page_mod']}"
            print(f"   Loading: {main_url}")
            
            self.driver.get(main_url)
            time.sleep(3)  # Wait for page to load
            
            # Parse page content
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find player table(s)
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows[:sample_size]:  # Limit sample size
                    try:
                        player_data = self.extract_player_from_row(row, config)
                        if player_data:
                            players.append(player_data)
                            print(f"   ✓ {player_data['first_name']} {player_data['last_name']} | {player_data['club']} | PTI: {player_data.get('pti', 'N/A')}")
                    except Exception as e:
                        print(f"   ⚠️ Error extracting player from row: {e}")
                        continue
                
                if len(players) >= sample_size:
                    break
            
            print(f"   📊 Collected {len(players)} players from {league_key}")
            self.leagues_scraped.append(league_key)
            
        except Exception as e:
            print(f"❌ Error scraping {league_key}: {e}")
            
        return players
    
    def extract_player_from_row(self, row, config: Dict) -> Optional[Dict]:
        """Extract player information from a table row"""
        cells = row.find_all('td')
        if len(cells) < 2:
            return None
        
        try:
            # Basic player info
            first_name = cells[0].get_text(strip=True)
            last_name = cells[1].get_text(strip=True)
            
            if not first_name or not last_name:
                return None
            
            # Extract PTI/rating if available
            pti = None
            if len(cells) > 2:
                pti_text = cells[2].get_text(strip=True)
                try:
                    pti = float(pti_text) if pti_text and pti_text.replace('.', '').isdigit() else None
                except ValueError:
                    pti = None
            
            # Extract series/division from row classes
            row_classes = row.get('class', [])
            series = self.extract_series_from_classes(row_classes, config)
            
            # Extract club information (try to determine from context)
            club = self.extract_club_from_context(row, config)
            
            # Generate TennisScores player ID from link if available
            player_link = row.find('a')
            tenniscores_id = None
            if player_link:
                href = player_link.get('href', '')
                tenniscores_id = self.extract_tenniscores_id(href)
            
            # Create player record
            player_data = {
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f"{first_name} {last_name}",
                'club': club or 'Unknown Club',
                'series': series or 'Unknown Series',
                'league': config['league_id'],  
                'league_name': config['league_name'],
                'pti': pti,
                'tenniscores_player_id': tenniscores_id,
                'scraped_at': datetime.now().isoformat(),
                'valid_for_testing': True,
                'source_url': config['base_url']
            }
            
            # Add some stats simulation
            if pti:
                # Simulate wins/losses based on PTI
                total_matches = random.randint(5, 25)
                win_rate = min(0.9, max(0.1, (pti - 1000) / 1000))  # PTI-based win rate
                wins = int(total_matches * win_rate)
                losses = total_matches - wins
                
                player_data.update({
                    'wins': wins,
                    'losses': losses,
                    'win_percentage': round((wins / total_matches) * 100, 1) if total_matches > 0 else 0
                })
            
            return player_data
            
        except Exception as e:
            print(f"   ⚠️ Error extracting player data: {e}")
            return None
    
    def extract_series_from_classes(self, row_classes: List[str], config: Dict) -> Optional[str]:
        """Extract series/division information from row CSS classes"""
        # Look for division ID patterns
        for class_name in row_classes:
            if class_name.startswith('diver_'):
                div_id = class_name.replace('diver_', '')
                
                # Map division ID to series name (league-specific)
                if config['league_id'] == 'APTA_CHICAGO':
                    # Common APTA Chicago series patterns
                    series_mapping = {
                        '19048': 'Chicago 22',
                        '19047': 'Chicago 21', 
                        '19046': 'Chicago 20',
                        '19029': 'Chicago 2',
                        '19066': 'Chicago 6'
                    }
                    return series_mapping.get(div_id, f'Chicago Series {div_id}')
                elif config['league_id'] == 'NSTF':
                    return f'NSTF Series {div_id}'
                
        return None
    
    def extract_club_from_context(self, row, config: Dict) -> Optional[str]:
        """Extract club name from row context"""
        # Try to find club information in the row or nearby elements
        # This is highly dependent on the specific league's HTML structure
        
        # Look for club names in common patterns
        club_patterns = [
            'Tennaqua', 'Birchwood', 'Exmoor', 'Onwentsia', 'Knollwood',
            'Indian Hill', 'North Shore', 'Winnetka', 'Lake Forest',
            'Wilmette', 'Evanston', 'Highland Park', 'Northbrook'
        ]
        
        row_text = row.get_text()
        for club in club_patterns:
            if club.lower() in row_text.lower():
                return club
        
        # Fallback: generate a random club for testing
        return random.choice(['Test Club A', 'Test Club B', 'Test Club C'])
    
    def extract_tenniscores_id(self, href: str) -> Optional[str]:
        """Extract TennisScores player ID from URL"""
        if not href:
            return None
            
        # Common patterns for TennisScores player IDs
        patterns = ['uid=', 'player=', 'player_id=', 'id=']
        
        for pattern in patterns:
            if pattern in href:
                try:
                    id_part = href.split(pattern)[1].split('&')[0]
                    return id_part
                except IndexError:
                    continue
        
        return None
    
    def generate_invalid_players(self) -> List[Dict]:
        """Generate intentionally invalid player data for negative testing"""
        print(f"\n🔧 Generating {self.max_invalid_players} invalid players for negative testing")
        
        invalid_players = []
        
        # Pattern 1: Non-existent clubs
        for i in range(self.max_invalid_players // 3):
            invalid_players.append({
                'first_name': f'Invalid{i}',
                'last_name': 'Player',
                'full_name': f'Invalid{i} Player',
                'club': f'NonExistentClub{i}',
                'series': 'FakeSeries',
                'league': 'FAKE_LEAGUE',
                'league_name': 'Fake League',
                'pti': None,
                'tenniscores_player_id': f'FAKE_{i:03d}',
                'valid_for_testing': False,
                'invalid_reason': 'non_existent_club'
            })
        
        # Pattern 2: Malformed data
        for i in range(self.max_invalid_players // 3):
            invalid_players.append({
                'first_name': '',  # Empty name
                'last_name': 'Test',
                'full_name': ' Test',
                'club': 'ValidClub',
                'series': '',  # Empty series
                'league': 'APTA_CHICAGO',
                'league_name': 'APTA Chicago',
                'pti': -1,  # Invalid PTI
                'tenniscores_player_id': None,
                'valid_for_testing': False,
                'invalid_reason': 'malformed_data'
            })
        
        # Pattern 3: SQL injection attempts (for security testing)
        sql_payloads = ["'; DROP TABLE players; --", "Robert'); DROP TABLE students;--", "admin'--"]
        for i, payload in enumerate(sql_payloads[:self.max_invalid_players // 3]):
            invalid_players.append({
                'first_name': payload,
                'last_name': 'SecurityTest',
                'full_name': f'{payload} SecurityTest',
                'club': 'TestClub',
                'series': 'TestSeries',
                'league': 'APTA_CHICAGO',
                'league_name': 'APTA Chicago',
                'pti': 1500,
                'tenniscores_player_id': f'SEC_{i:03d}',
                'valid_for_testing': False,
                'invalid_reason': 'security_payload'
            })
        
        print(f"   ✓ Generated {len(invalid_players)} invalid test players")
        return invalid_players
    
    def scrape_all_leagues(self) -> Dict:
        """Scrape player data from all configured leagues"""
        print("🎯 Starting comprehensive test data scraping...")
        print(f"   Target: {self.max_players_per_league} players per league")
        print(f"   Leagues: {list(self.league_configs.keys())}")
        
        if not self.setup_driver():
            return {'error': 'Failed to setup WebDriver'}
        
        try:
            all_valid_players = []
            
            # Scrape each league
            for league_key in self.league_configs.keys():
                league_players = self.scrape_league_players(league_key)
                all_valid_players.extend(league_players)
                
                # Add delay between leagues to be respectful
                time.sleep(2)
            
            # Generate invalid players
            invalid_players = self.generate_invalid_players()
            
            # Prepare final dataset
            dataset = {
                'metadata': {
                    'scraped_at': datetime.now().isoformat(),
                    'leagues_scraped': self.leagues_scraped,
                    'total_valid_players': len(all_valid_players),
                    'total_invalid_players': len(invalid_players),
                    'scraper_version': '1.0',
                    'purpose': 'Rally application testing'
                },
                'valid_players': all_valid_players,
                'invalid_players': invalid_players
            }
            
            print(f"\n📊 Scraping Summary:")
            print(f"   ✅ Valid players: {len(all_valid_players)}")
            print(f"   ❌ Invalid players: {len(invalid_players)}")
            print(f"   🏆 Leagues covered: {len(self.leagues_scraped)}")
            
            return dataset
            
        finally:
            self.cleanup_driver()
    
    def save_test_data(self, dataset: Dict, output_dir: str = None) -> str:
        """Save scraped test data to JSON file"""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'fixtures')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'scraped_players_{timestamp}.json'
        filepath = os.path.join(output_dir, filename)
        
        # Also save as the default name for test fixtures
        default_filepath = os.path.join(output_dir, 'scraped_players.json')
        
        try:
            # Save timestamped version
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
            
            # Save default version for tests
            with open(default_filepath, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Test data saved to:")
            print(f"   📁 {filepath}")
            print(f"   📁 {default_filepath}")
            
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving test data: {e}")
            return None

def main():
    """Main function to run the test data scraper"""
    print("🎾 Rally Test Data Scraper")
    print("=" * 50)
    print("Scraping real player data from TennisScores for testing")
    print()
    
    # Initialize scraper
    scraper = TennisScoresTestDataScraper(
        max_players_per_league=15,  # Reasonable sample size
        max_invalid_players=10
    )
    
    try:
        # Scrape all leagues
        dataset = scraper.scrape_all_leagues()
        
        if 'error' in dataset:
            print(f"❌ Scraping failed: {dataset['error']}")
            return False
        
        # Save the data
        output_file = scraper.save_test_data(dataset)
        
        if output_file:
            print(f"\n✅ Test data scraping completed successfully!")
            print(f"📄 Use this data in your tests by loading: tests/fixtures/scraped_players.json")
            return True
        else:
            print(f"\n❌ Failed to save test data")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Scraping interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1) 