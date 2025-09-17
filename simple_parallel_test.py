#!/usr/bin/env python3
"""
Simple parallel processing test for APTA scraper
Tests basic parallel team processing with minimal complexity
"""

import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

# Add the scraper path
sys.path.append('/Users/rossfreedman/dev/rally/data/etl/scrapers/apta')

def test_simple_parallel():
    """Test simple parallel processing approach"""
    print("🧪 Simple Parallel APTA Team Processing Test")
    print("=" * 60)
    
    # Import the original scraper
    from apta_scrape_players import APTAChicagoRosterScraper
    
    # Create scraper instance
    print("🚀 Initializing scraper...")
    scraper = APTAChicagoRosterScraper(force_restart=False, target_series=['20'])
    
    # Test teams
    test_teams = [
        ("Evanston - 20", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&team=nndz-WkNLd3c3Lzg%3D"),
        ("Exmoor - 20", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&team=nndz-WkNld3lMNys%3D"),
        ("Indian Hill - 20", "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&team=nndz-WkNLd3c3LzY%3D")
    ]
    
    print(f"🎯 Testing with {len(test_teams)} teams")
    
    # Test 1: Sequential processing (baseline)
    print("\n🔄 Testing Sequential Processing...")
    start_time = time.time()
    
    sequential_results = []
    for team_name, team_url in test_teams:
        print(f"   🏢 Processing {team_name}...")
        try:
            team_html = scraper.get_html_content(team_url)
            if team_html:
                team_players = scraper._parse_team_roster(team_html, team_name, "20")
                sequential_results.extend(team_players)
                print(f"      ✅ Found {len(team_players)} players")
            else:
                print(f"      ❌ Failed to load team page")
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    sequential_time = time.time() - start_time
    print(f"✅ Sequential completed: {sequential_time:.1f}s, {len(sequential_results)} players")
    
    # Test 2: Simple parallel processing
    print("\n🚀 Testing Simple Parallel Processing...")
    start_time = time.time()
    
    def process_single_team(team_data):
        """Process a single team with thread-safe approach"""
        team_name, team_url = team_data
        thread_name = threading.current_thread().name
        
        print(f"   🏢 [{thread_name}] Processing {team_name}...")
        
        try:
            # Create a new stealth browser instance for this thread
            from helpers.stealth_browser import EnhancedStealthBrowser, StealthConfig
            
            config = StealthConfig(
                fast_mode=False,
                verbose=False,
                environment='production',
                force_browser=False,
                headless=True,
                min_delay=3.0,
                max_delay=5.0
            )
            
            stealth_browser = EnhancedStealthBrowser(config)
            if not stealth_browser:
                return {
                    'team_name': team_name,
                    'players': [],
                    'success': False,
                    'error': 'Failed to create stealth browser'
                }
            
            # Get team page
            team_html = stealth_browser.get_html(team_url)
            if not team_html or len(team_html) < 1000:
                return {
                    'team_name': team_name,
                    'players': [],
                    'success': False,
                    'error': 'Failed to load team page'
                }
            
            # Parse team roster
            team_players = scraper._parse_team_roster(team_html, team_name, "20")
            
            print(f"      ✅ [{thread_name}] Found {len(team_players)} players in {team_name}")
            
            # Cleanup
            if hasattr(stealth_browser, 'close'):
                stealth_browser.close()
            
            return {
                'team_name': team_name,
                'players': team_players,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            print(f"      ❌ [{thread_name}] Error processing {team_name}: {e}")
            return {
                'team_name': team_name,
                'players': [],
                'success': False,
                'error': str(e)
            }
    
    # Execute parallel processing
    parallel_results = []
    successful_teams = 0
    failed_teams = 0
    
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all tasks
            future_to_team = {
                executor.submit(process_single_team, team_data): team_data[0] 
                for team_data in test_teams
            }
            
            # Process results as they complete
            for future in as_completed(future_to_team):
                team_name = future_to_team[future]
                
                try:
                    result = future.result()
                    
                    if result['success']:
                        parallel_results.extend(result['players'])
                        successful_teams += 1
                    else:
                        failed_teams += 1
                        print(f"   ❌ Failed {team_name}: {result['error']}")
                        
                except Exception as e:
                    failed_teams += 1
                    print(f"   ❌ Exception processing {team_name}: {e}")
    
    except Exception as e:
        print(f"❌ Parallel processing failed: {e}")
        parallel_results = []
    
    parallel_time = time.time() - start_time
    
    # Results comparison
    print(f"\n📈 Performance Comparison:")
    print("=" * 40)
    print(f"Sequential Processing: {sequential_time:.1f}s, {len(sequential_results)} players")
    print(f"Parallel Processing:   {parallel_time:.1f}s, {len(parallel_results)} players")
    print(f"Successful Teams:      {successful_teams}/{len(test_teams)}")
    print(f"Failed Teams:          {failed_teams}/{len(test_teams)}")
    
    if parallel_time > 0 and sequential_time > 0:
        speedup = sequential_time / parallel_time
        print(f"Speed Improvement:     {speedup:.1f}x faster")
    
    if len(parallel_results) == len(sequential_results):
        print("✅ Both methods extracted the same number of players")
    else:
        print(f"⚠️ Different player counts: Parallel={len(parallel_results)}, Sequential={len(sequential_results)}")
    
    print("\n🎯 Simple parallel test completed!")
    return parallel_results, sequential_results

if __name__ == "__main__":
    test_simple_parallel()
