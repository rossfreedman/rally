#!/usr/bin/env python3
"""
Parallel Team Processing Enhancement for APTA Chicago Scraper
Implements safe concurrent team processing while maintaining stealth levels.

Key Safety Features:
- Individual stealth browser instances per thread
- Proxy isolation between threads  
- Controlled concurrency (2-3 max)
- Graceful fallback to sequential processing
- Same stealth level as original scraper
"""

import sys
import os
import time
import json
import hashlib
import re
import threading
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Add the parent directory to the path to access scraper modules
parent_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(parent_path)

from helpers.stealth_browser import EnhancedStealthBrowser, StealthConfig
from helpers.user_agent_manager import UserAgentManager
from helpers.proxy_manager import fetch_with_retry

# Import speed optimizations with safe fallbacks
try:
    from helpers.adaptive_pacer import pace_sleep, mark
    from helpers.stealth_browser import stop_after_selector
    SPEED_OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    try:
        from ..adaptive_pacer import pace_sleep, mark
        from ..stealth_browser import stop_after_selector
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

class ParallelTeamProcessor:
    """Safe parallel team processing with individual stealth browser instances"""
    
    def __init__(self, max_workers=2):
        self.max_workers = max_workers
        self.thread_local = threading.local()
        self.lock = threading.Lock()
        self.results = []
        
    def _get_stealth_browser(self):
        """Get or create thread-local stealth browser instance"""
        if not hasattr(self.thread_local, 'stealth_browser'):
            print(f"   🔧 Initializing stealth browser for thread {threading.current_thread().name}")
            self.thread_local.stealth_browser = self._create_stealth_browser()
        return self.thread_local.stealth_browser
    
    def _create_stealth_browser(self):
        """Create a new stealth browser instance for this thread"""
        try:
            # Create stealth config with thread-safe settings
            config = StealthConfig(
                mode='stealth',
                environment='production',
                delays=(3.0, 5.0),
                use_proxy=True,
                proxy_rotation=True
            )
            
            stealth_browser = EnhancedStealthBrowser(config)
            if stealth_browser:
                print(f"   ✅ Stealth browser initialized for thread {threading.current_thread().name}")
                return stealth_browser
            else:
                print(f"   ❌ Failed to initialize stealth browser for thread {threading.current_thread().name}")
                return None
        except Exception as e:
            print(f"   ❌ Error creating stealth browser for thread {threading.current_thread().name}: {e}")
            return None
    
    def _process_single_team(self, team_data: Tuple[int, str, str, str]) -> Dict:
        """Process a single team with thread-safe stealth browser"""
        team_index, team_name, team_url, series_identifier = team_data
        thread_name = threading.current_thread().name
        
        print(f"   🏢 [{thread_name}] Processing team {team_index}: {team_name}")
        
        try:
            # Get thread-local stealth browser
            stealth_browser = self._get_stealth_browser()
            if not stealth_browser:
                print(f"   ❌ [{thread_name}] No stealth browser available for {team_name}")
                return {
                    'team_name': team_name,
                    'players': [],
                    'success': False,
                    'error': 'No stealth browser available'
                }
            
            # Get team roster page with stealth browser
            pace_sleep()  # Adaptive pacing
            team_html = stealth_browser.get_html(team_url)
            
            if not team_html or len(team_html) < 1000:
                print(f"   ❌ [{thread_name}] Failed to load team page for {team_name}")
                return {
                    'team_name': team_name,
                    'players': [],
                    'success': False,
                    'error': 'Failed to load team page'
                }
            
            # Parse team roster (reuse existing parsing logic)
            team_players = self._parse_team_roster(team_html, team_name, series_identifier, stealth_browser)
            
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
    
    def _parse_team_roster(self, html: str, team_name: str, series_identifier: str, stealth_browser) -> List[Dict]:
        """Parse team roster (simplified version for parallel processing)"""
        # This would contain the actual parsing logic from the original scraper
        # For now, returning empty list as placeholder
        soup = BeautifulSoup(html, 'html.parser')
        players = []
        
        # Extract players from HTML (same logic as original)
        # ... parsing logic here ...
        
        return players
    
    def process_teams_parallel(self, team_links: List[Tuple[str, str]], series_identifier: str) -> List[Dict]:
        """Process multiple teams in parallel with safety controls"""
        print(f"🚀 Starting parallel team processing with {self.max_workers} workers...")
        print(f"   📊 Processing {len(team_links)} teams concurrently")
        
        all_players = []
        successful_teams = 0
        failed_teams = 0
        
        # Prepare team data with indices for tracking
        team_data_list = [
            (i+1, team_name, team_url, series_identifier) 
            for i, (team_name, team_url) in enumerate(team_links)
        ]
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all team processing tasks
                future_to_team = {
                    executor.submit(self._process_single_team, team_data): team_data[1] 
                    for team_data in team_data_list
                }
                
                # Process completed tasks as they finish
                for future in as_completed(future_to_team):
                    team_name = future_to_team[future]
                    
                    try:
                        result = future.result()
                        
                        if result['success']:
                            all_players.extend(result['players'])
                            successful_teams += 1
                            print(f"   ✅ Completed {team_name}: {len(result['players'])} players")
                        else:
                            failed_teams += 1
                            print(f"   ❌ Failed {team_name}: {result['error']}")
                            
                    except Exception as e:
                        failed_teams += 1
                        print(f"   ❌ Exception processing {team_name}: {e}")
        
        except Exception as e:
            print(f"❌ Parallel processing failed: {e}")
            print("🔄 Falling back to sequential processing...")
            return self._fallback_sequential_processing(team_links, series_identifier)
        
        print(f"🎯 Parallel processing complete:")
        print(f"   ✅ Successful teams: {successful_teams}")
        print(f"   ❌ Failed teams: {failed_teams}")
        print(f"   📊 Total players: {len(all_players)}")
        
        return all_players
    
    def _fallback_sequential_processing(self, team_links: List[Tuple[str, str]], series_identifier: str) -> List[Dict]:
        """Fallback to sequential processing if parallel fails"""
        print("🔄 Using sequential fallback processing...")
        
        all_players = []
        stealth_browser = self._create_stealth_browser()
        
        for i, (team_name, team_url) in enumerate(team_links):
            print(f"   🏢 Sequential team {i+1}/{len(team_links)}: {team_name}")
            
            try:
                pace_sleep()
                team_html = stealth_browser.get_html(team_url) if stealth_browser else None
                
                if team_html and len(team_html) > 1000:
                    team_players = self._parse_team_roster(team_html, team_name, series_identifier, stealth_browser)
                    all_players.extend(team_players)
                    print(f"      ✅ Found {len(team_players)} players")
                    _pacer_mark_ok()
                else:
                    print(f"      ❌ Failed to load team page")
                
                time.sleep(2)  # Delay between sequential requests
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
                continue
        
        return all_players
    
    def cleanup(self):
        """Clean up thread-local resources"""
        try:
            if hasattr(self.thread_local, 'stealth_browser'):
                # Close stealth browser if it has cleanup method
                if hasattr(self.thread_local.stealth_browser, 'close'):
                    self.thread_local.stealth_browser.close()
                delattr(self.thread_local, 'stealth_browser')
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")

# Enhanced APTA scraper with parallel processing
class APTAChicagoRosterScraperParallel:
    """Enhanced APTA Chicago scraper with safe parallel team processing"""
    
    def __init__(self, force_restart=False, target_series=None, max_parallel_workers=2):
        self.base_url = "https://aptachicago.tenniscores.com"
        self.all_players = []
        self.target_series = target_series
        self.max_parallel_workers = max_parallel_workers
        
        # Initialize parallel processor
        self.parallel_processor = ParallelTeamProcessor(max_workers=max_parallel_workers)
        
        print(f"🚀 Initialized parallel APTA scraper with {max_parallel_workers} workers")
    
    def extract_players_from_team_rosters_parallel(self, team_links: List[Tuple[str, str]], series_identifier: str) -> List[Dict]:
        """Enhanced team processing with parallel execution"""
        print(f"🔍 Parallel processing {len(team_links)} team roster pages...")
        
        # Use parallel processing
        all_players = self.parallel_processor.process_teams_parallel(team_links, series_identifier)
        
        print(f"🎯 Total players extracted via parallel processing: {len(all_players)}")
        return all_players
    
    def __del__(self):
        """Cleanup parallel processor resources"""
        if hasattr(self, 'parallel_processor'):
            self.parallel_processor.cleanup()

if __name__ == "__main__":
    # Test parallel processing
    print("🧪 Testing parallel team processing...")
    
    # Sample team data
    test_teams = [
        ("Evanston - 20", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&team=nndz-WkNLd3c3Lzg%3D"),
        ("Exmoor - 20", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&team=nndz-WkNld3lMNys%3D"),
        ("Indian Hill - 20", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&team=nndz-WkNLd3c3LzY%3D")
    ]
    
    scraper = APTAChicagoRosterScraperParallel(max_parallel_workers=2)
    results = scraper.extract_players_from_team_rosters_parallel(test_teams, "20")
    
    print(f"✅ Test completed: {len(results)} players extracted")
