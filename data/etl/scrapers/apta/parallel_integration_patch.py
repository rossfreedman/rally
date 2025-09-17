#!/usr/bin/env python3
"""
Integration patch to add parallel team processing to existing APTA scraper
This patch modifies the existing scraper to use parallel processing safely.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

class ParallelTeamProcessor:
    """Safe parallel team processing with thread isolation"""
    
    def __init__(self, max_workers=2):
        self.max_workers = max_workers
        self.thread_local = threading.local()
        
    def _get_stealth_browser(self, original_scraper):
        """Get or create thread-local stealth browser instance"""
        if not hasattr(self.thread_local, 'stealth_browser'):
            print(f"   🔧 [{threading.current_thread().name}] Initializing thread-local stealth browser")
            
            # Create new stealth browser instance for this thread
            try:
                from helpers.stealth_browser import EnhancedStealthBrowser, StealthConfig
                
                config = StealthConfig(
                    mode='stealth',
                    environment='production',
                    delays=(3.0, 5.0),
                    use_proxy=True,
                    proxy_rotation=True
                )
                
                self.thread_local.stealth_browser = EnhancedStealthBrowser(config)
                
                if self.thread_local.stealth_browser:
                    print(f"   ✅ [{threading.current_thread().name}] Thread-local stealth browser ready")
                else:
                    print(f"   ❌ [{threading.current_thread().name}] Failed to create stealth browser")
                    
            except Exception as e:
                print(f"   ❌ [{threading.current_thread().name}] Error creating stealth browser: {e}")
                self.thread_local.stealth_browser = None
        
        return self.thread_local.stealth_browser
    
    def _process_single_team_parallel(self, team_data: Tuple, original_scraper):
        """Process single team with thread-local stealth browser"""
        team_index, team_name, team_url, series_identifier = team_data
        thread_name = threading.current_thread().name
        
        print(f"   🏢 [{thread_name}] Processing team {team_index}: {team_name}")
        
        try:
            # Get thread-local stealth browser
            stealth_browser = self._get_stealth_browser(original_scraper)
            if not stealth_browser:
                return {
                    'team_name': team_name,
                    'players': [],
                    'success': False,
                    'error': 'No stealth browser available'
                }
            
            # Use thread-local browser to get team page
            pace_sleep()  # Adaptive pacing
            team_html = stealth_browser.get_html(team_url)
            
            if not team_html or len(team_html) < 1000:
                return {
                    'team_name': team_name,
                    'players': [],
                    'success': False,
                    'error': 'Failed to load team page'
                }
            
            # Parse team roster using original scraper's method
            team_players = original_scraper._parse_team_roster(team_html, team_name, series_identifier)
            
            print(f"   ✅ [{thread_name}] Found {len(team_players)} players in {team_name}")
            _pacer_mark_ok()  # Mark successful response
            
            return {
                'team_name': team_name,
                'players': team_players,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            print(f"   ❌ [{thread_name}] Error processing {team_name}: {e}")
            return {
                'team_name': team_name,
                'players': [],
                'success': False,
                'error': str(e)
            }
    
    def process_teams_parallel(self, team_links: List[Tuple[str, str]], series_identifier: str, original_scraper) -> List[Dict]:
        """Process teams in parallel with safety controls"""
        print(f"🚀 Parallel processing {len(team_links)} teams with {self.max_workers} workers...")
        
        all_players = []
        successful_teams = 0
        failed_teams = 0
        
        # Prepare team data
        team_data_list = [
            (i+1, team_name, team_url, series_identifier) 
            for i, (team_name, team_url) in enumerate(team_links)
        ]
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_team = {
                    executor.submit(self._process_single_team_parallel, team_data, original_scraper): team_data[1] 
                    for team_data in team_data_list
                }
                
                # Process results as they complete
                for future in as_completed(future_to_team):
                    team_name = future_to_team[future]
                    
                    try:
                        result = future.result()
                        
                        if result['success']:
                            all_players.extend(result['players'])
                            successful_teams += 1
                        else:
                            failed_teams += 1
                            
                    except Exception as e:
                        failed_teams += 1
                        print(f"   ❌ Exception processing {team_name}: {e}")
        
        except Exception as e:
            print(f"❌ Parallel processing failed: {e}")
            print("🔄 Falling back to sequential processing...")
            return self._fallback_sequential(team_links, series_identifier, original_scraper)
        
        print(f"🎯 Parallel processing results:")
        print(f"   ✅ Successful: {successful_teams}")
        print(f"   ❌ Failed: {failed_teams}")
        print(f"   📊 Total players: {len(all_players)}")
        
        return all_players
    
    def _fallback_sequential(self, team_links: List[Tuple[str, str]], series_identifier: str, original_scraper) -> List[Dict]:
        """Fallback to original sequential processing"""
        print("🔄 Using sequential fallback...")
        return original_scraper.extract_players_from_team_rosters_sequential(team_links, series_identifier)

# Patch function to add parallel processing to existing scraper
def add_parallel_processing_to_scraper(scraper_class):
    """Add parallel processing methods to existing scraper class"""
    
    def extract_players_from_team_rosters_parallel(self, team_links: List[Tuple[str, str]], series_identifier: str) -> List[Dict]:
        """Enhanced team processing with parallel execution"""
        print(f"🔍 Processing {len(team_links)} team roster pages in parallel...")
        
        # Initialize parallel processor if not exists
        if not hasattr(self, '_parallel_processor'):
            max_workers = min(2, len(team_links))  # Max 2 workers for safety
            self._parallel_processor = ParallelTeamProcessor(max_workers=max_workers)
            print(f"🚀 Initialized parallel processor with {max_workers} workers")
        
        # Use parallel processing
        all_players = self._parallel_processor.process_teams_parallel(team_links, series_identifier, self)
        
        print(f"🎯 Total players extracted via parallel processing: {len(all_players)}")
        return all_players
    
    def extract_players_from_team_rosters_sequential(self, team_links: List[Tuple[str, str]], series_identifier: str) -> List[Dict]:
        """Original sequential team processing (fallback method)"""
        print(f"🔍 Sequential processing {len(team_links)} team roster pages...")
        
        all_players = []
        
        for i, (team_name, team_url) in enumerate(team_links):
            print(f"   🏢 Scraping team {i+1}/{len(team_links)}: {team_name}")
            
            try:
                # Get the team roster page
                team_html = self.get_html_content(team_url)
                if not team_html:
                    print(f"      ❌ Failed to load team page for {team_name}")
                    continue
                
                # Parse team roster
                team_players = self._parse_team_roster(team_html, team_name, series_identifier)
                if team_players:
                    all_players.extend(team_players)
                    print(f"      ✅ Found {len(team_players)} players in {team_name}")
                else:
                    print(f"      ⚠️ No players found in {team_name}")
                
                # Add delay between team requests
                if i < len(team_links) - 1:
                    time.sleep(2)
                    
            except Exception as e:
                print(f"      ❌ Error scraping {team_name}: {e}")
                continue
        
        print(f"🎯 Total players extracted from team rosters: {len(all_players)}")
        return all_players
    
    # Add methods to the class
    scraper_class.extract_players_from_team_rosters_parallel = extract_players_from_team_rosters_parallel
    scraper_class.extract_players_from_team_rosters_sequential = extract_players_from_team_rosters_sequential
    
    return scraper_class

# Usage example:
if __name__ == "__main__":
    # Import the original scraper
    from apta_scrape_players import APTAChicagoRosterScraper
    
    # Apply the parallel processing patch
    EnhancedScraper = add_parallel_processing_to_scraper(APTAChicagoRosterScraper)
    
    # Create enhanced scraper instance
    scraper = EnhancedScraper(force_restart=False, target_series=['20'])
    
    print("✅ Enhanced scraper with parallel processing ready!")
    print("🚀 Use extract_players_from_team_rosters_parallel() for parallel processing")
    print("🔄 Use extract_players_from_team_rosters_sequential() for fallback")
