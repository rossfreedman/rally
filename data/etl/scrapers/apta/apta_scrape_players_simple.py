#!/usr/bin/env python3
"""
Simplified APTA Chicago Player Scraper

This script scrapes current season player data from APTA Chicago series (1-22 and SW variants) 
directly from team roster pages. It skips career stats lookup to focus only on basic player 
information for faster execution.

Usage:
    python3 apta_scrape_players_simple.py
    python3 apta_scrape_players_simple.py --series 1,2,3
"""

import sys
import os
import time
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup

# Add the scrapers directory to the path to access helper modules
scrapers_path = os.path.join(os.path.dirname(__file__), '..')
if scrapers_path not in sys.path:
    sys.path.insert(0, scrapers_path)

# Import speed optimizations with safe fallbacks
try:
    from ..adaptive_pacer import pace_sleep, mark
    from ..stealth_browser import stop_after_selector
    SPEED_OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    try:
        from helpers.adaptive_pacer import pace_sleep, mark
        from helpers.stealth_browser import stop_after_selector
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

# Import rally context for browser automation
try:
    from ..stealth_browser import create_stealth_browser
    RALLY_CONTEXT_AVAILABLE = True
except ImportError:
    try:
        from helpers.stealth_browser import create_stealth_browser
        RALLY_CONTEXT_AVAILABLE = True
    except ImportError:
        RALLY_CONTEXT_AVAILABLE = False
        print("⚠️ Rally context not available - using standard requests")

class APTAChicagoSimpleScraper:
    """Simplified APTA Chicago player scraper that only gets current season data"""
    
    def __init__(self, force_restart=False, target_series=None):
        self.base_url = "https://aptachicago.tenniscores.com"
        self.all_players = []
        self.completed_series = set()
        self.target_series = target_series

        self.start_time = time.time()
        self.force_restart = force_restart
        
        # Progress tracking
        self.total_players_processed = 0
        self.total_players_expected = 0
        self.total_series_count = 0
        self.current_series = ""
        self.current_player = ""
        self.last_progress_update = time.time()
        
        # Initialize rally context if available
        self.rally_context = None
        if RALLY_CONTEXT_AVAILABLE:
            try:
                self.rally_context = create_stealth_browser(fast_mode=True, verbose=False)
                if self.rally_context:
                    print("✅ Rally context (stealth browser) initialized for efficient scraping")
            except Exception as e:
                print(f"⚠️ Rally context initialization failed: {e}")
                self.rally_context = None
        
        # Setup logging
        self.setup_logging()
        
        # Performance tracking
        self.request_count = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.request_times = []
        
        # Load existing progress if not forcing restart
        self.load_existing_progress()

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"apta_simple_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_existing_progress(self):
        """Load existing progress and player data if available"""
        if self.force_restart:
            # Clean up any existing progress files
            try:
                progress_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp', 'scrape_progress.json')
                partial_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp', 'players_comprehensive_partial.json')
                
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                    print("🧹 Removed progress file")
                    
                if os.path.exists(partial_file):
                    os.remove(partial_file)
                    print("🧹 Removed partial results file")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up progress files: {e}")
            
            print("📂 Starting completely fresh - no previous progress loaded")
            return
            
        try:
            progress_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp', 'scrape_progress.json')
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    self.completed_series = set(progress_data.get('completed_series', []))
                    print(f"📂 Loaded progress: {len(self.completed_series)} series already completed")
                    
                # Load existing player data
                output_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp', 'players_comprehensive_partial.json')
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        self.all_players = json.load(f)
                        print(f"📂 Loaded {len(self.all_players)} existing players")
            else:
                print("📂 No previous progress found - starting fresh")
        except Exception as e:
            print(f"⚠️ Error loading progress: {e}")

    def get_series_urls(self) -> List[Tuple[str, str]]:
        """Generate URLs for APTA Chicago series using dynamic discovery"""
        print("🔍 Using dynamic discovery to find all available series...")
        
        # Use dynamic discovery to find all series
        series_urls = self.discover_series_dynamically()
        
        # Filter series based on target_series parameter if specified
        if self.target_series:
            print(f"\n🎯 Filtering to target series: {', '.join(self.target_series)}")
            filtered_series = []
            for series_name, series_url in series_urls:
                series_id = series_name.replace('Series ', '').strip()
                if series_id in self.target_series:
                    filtered_series.append((series_name, series_url))
                    print(f"   ✅ Including: {series_name}")
                else:
                    print(f"   ⏭️ Skipping: {series_name} (not in target list)")
            series_urls = filtered_series
            print(f"✅ Filtered to {len(series_urls)} target series")
        
        return series_urls

    def discover_series_dynamically(self) -> List[Tuple[str, str]]:
        """Discover all available series by scraping any series page for the series navigation"""
        print("🔍 Discovering all available series from series page navigation...")
        
        discovered_series = []
        
        try:
            # Method 1: Scrape any series page to get the series navigation
            print("   📋 Method 1: Scraping series page for navigation...")
            
            # Use a known working series URL to get the navigation
            series_url = "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WkM2eHhMcz0%3D"
            print(f"      🔍 Using series page: {series_url}")
            
            html_content = self.get_html_with_fallback(series_url)
            
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Method 1a: Look for links with the specific pattern
                series_links = soup.find_all('a', href=True, id=lambda x: x and x.startswith('dividdrop_'))
                
                for link in series_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    link_id = link.get('id', '')
                    
                    # Extract the series number from the link text
                    if text.isdigit():
                        # Regular series (e.g., "1", "2", "3")
                        series_num = text
                        series_name = f"Series {series_num}"
                        
                        # Construct the full URL
                        if href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = href
                        
                        discovered_series.append((series_name, full_url))
                        print(f"         📋 Found series link: {series_name} -> {full_url} (ID: {link_id})")
                    elif ' SW' in text and any(char.isdigit() for char in text):
                        # SW series (e.g., "7 SW", "9 SW", "11 SW")
                        series_name = f"Series {text}"
                        
                        # Construct the full URL
                        if href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = href
                        
                        discovered_series.append((series_name, full_url))
                        print(f"         📋 Found SW series link: {series_name} -> {full_url} (ID: {link_id})")
                
                # Method 1b: Look for the series navigation text pattern
                if not discovered_series:
                    print("      📋 Method 1b: Looking for series navigation text pattern...")
                    
                    text_elements = soup.find_all(text=True)
                    for element in text_elements:
                        text = element.strip()
                        if 'Chicago' in text and any(char.isdigit() for char in text):
                            print(f"         📋 Found navigation text: {text}")
                            
                            # Extract series numbers from the text
                            series_numbers = re.findall(r'\b(\d+)\b', text)
                            
                            # Add regular series
                            for series_num in series_numbers:
                                series_name = f"Series {series_num}"
                                series_url = f"{self.base_url}/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WkM2eHhMcz0%3D"
                                discovered_series.append((series_name, series_url))
                                print(f"            📋 Extracted: {series_name}")
                
                if discovered_series:
                    print(f"      ✅ Found {len(discovered_series)} series from navigation")
                else:
                    print("      ⚠️ No series found from navigation, using fallback...")
                    
                    # Fallback to comprehensive hardcoded series (including SW and 23+)
                    fallback_series = [
                        # Regular series (1-22)
            ("Series 1", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3MD0%3D"),
            ("Series 2", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3bz0%3D"),
            ("Series 3", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3az0%3D"),
            ("Series 4", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3cz0%3D"),
            ("Series 5", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3WT0%3D"),
            ("Series 6", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3Zz0%3D"),
            ("Series 7", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMaz0%3D"),
            ("Series 8", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMWT0%3D"),
            ("Series 9", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMYz0%3D"),
            ("Series 10", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3ND0%3D"),
            ("Series 11", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3OD0%3D"),
            ("Series 12", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
            ("Series 13", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 14", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3bz0%3D"),
            ("Series 15", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3cz0%3D"),
            ("Series 16", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
            ("Series 17", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 18", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 19", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 20", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 21", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 22", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                        # SW (Southwest) series
                        ("Series 7 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMZz0%3D"),
                        ("Series 9 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyZz0%3D"),
                        ("Series 11 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhydz0%3D"),
                        ("Series 13 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMYz0%3D"),
                        ("Series 15 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXg3Yz0%3D"),
                        ("Series 17 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyND0%3D"),
                        ("Series 19 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyMD0%3D"),
                        ("Series 21 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyOD0%3D"),
            # Additional series (23+)
            ("Series 23", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 23 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMWT0%3D"),
            ("Series 24", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 25", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 25 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXg3WT0%3D"),
            ("Series 26", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 27", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 27 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkNHL3lMbz0%3D"),
            ("Series 28", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 29", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 29 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkM2eHg3dz0%3D"),
            ("Series 30", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 31", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 31 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WlNXK3licz0%3D"),
            ("Series 32", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 33", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 34", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 35", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 36", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 37", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 38", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 39", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 40", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 41", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 42", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 43", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 44", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 45", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 46", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 47", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 48", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ("Series 49", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                        ("Series 50", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                    ]
                    
                    for series_name, series_path in fallback_series:
                        series_url = f"{self.base_url}{series_path}"
                        discovered_series.append((series_name, series_url))
                        print(f"         📋 Added fallback: {series_name}")
            
            # Keep all series (including SW variants and series 23+)
            print(f"\n🎯 Dynamic discovery complete!")
            print(f"   📊 Total series discovered: {len(discovered_series)}")
            print(f"   🏆 All series included: {len(discovered_series)}")
            
            return discovered_series
            
        except Exception as e:
            print(f"❌ Error during dynamic discovery: {e}")
            print("   🔄 Falling back to hardcoded series...")
            
            # Fallback to comprehensive hardcoded series (including SW and 23+)
            fallback_series = [
                # Regular series (1-22)
                ("Series 1", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3MD0%3D"),
                ("Series 2", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3bz0%3D"),
                ("Series 3", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3az0%3D"),
                ("Series 4", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3cz0%3D"),
                ("Series 5", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3WT0%3D"),
                ("Series 6", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXc3Zz0%3D"),
                ("Series 7", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMaz0%3D"),
                ("Series 8", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMWT0%3D"),
                ("Series 9", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXhMYz0%3D"),
                ("Series 10", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3ND0%3D"),
                ("Series 11", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3OD0%3D"),
                ("Series 12", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
                ("Series 13", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 14", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3bz0%3D"),
                ("Series 15", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3cz0%3D"),
                ("Series 16", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3dz0%3D"),
                ("Series 17", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 18", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 19", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 20", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 21", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 22", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                # SW (Southwest) series
                ("Series 7 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMZz0%3D"),
                ("Series 9 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyZz0%3D"),
                ("Series 11 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhydz0%3D"),
                ("Series 13 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMYz0%3D"),
                ("Series 15 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXg3Yz0%3D"),
                ("Series 17 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyND0%3D"),
                ("Series 19 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyMD0%3D"),
                ("Series 21 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXhyOD0%3D"),
                # Additional series (23+)
                ("Series 23", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 23 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrOHhMWT0%3D"),
                ("Series 24", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 25", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 25 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WnkrNXg3WT0%3D"),
                ("Series 26", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 27", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 27 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkNHL3lMbz0%3D"),
                ("Series 28", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 29", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 29 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WkM2eHg3dz0%3D"),
                ("Series 30", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 31", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 31 SW", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WlNXK3licz0%3D"),
                ("Series 32", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 33", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 34", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 35", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 36", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 37", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 38", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 39", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 40", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 41", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 42", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 43", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 44", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 45", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 46", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 47", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 48", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 49", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
                ("Series 50", "/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1NjN1FMcGpx&did=nndz-WnkrNXg3MD0%3D"),
            ]
            
            fallback_urls = []
            for series_name, series_path in fallback_series:
                series_url = f"{self.base_url}{series_path}"
                fallback_urls.append((series_name, series_url))
        
            return fallback_urls

    def get_html_with_fallback(self, url: str) -> str:
        """Get HTML content with fallback methods"""
        try:
            # Try rally context (stealth browser) first if available
            if self.rally_context:
                try:
                    # Use the stealth browser to get HTML
                    html = self.rally_context.get_html(url)
                    if html and len(html) > 1000:
                        return html
                except Exception as e:
                    print(f"   ⚠️ Rally context failed, falling back: {e}")
            
            # Fallback to requests
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            print(f"   ❌ Failed to get HTML for {url}: {e}")
            return ""

    def scrape_all_series(self):
        """Scrape all series with simplified approach"""
        if self.target_series:
            series_list = ', '.join(self.target_series)
            print(f"🚀 Starting APTA Chicago targeted series scraping (simple mode)...")
            print(f"   This will scrape series: {series_list}")
        else:
            print("🚀 Starting APTA Chicago comprehensive series scraping (simple mode)...")
            print("   This will scrape ALL series (1-50 and SW variants) from roster pages")
        print("   ⚡ SIMPLE MODE: Current season scores + player data (no career stats)")
        print("⏱️ This should take about 8-12 minutes to complete")
        
        # Get series URLs
        series_urls = self.get_series_urls()
        
        # Filter series based on target_series parameter if specified
        if self.target_series:
            print(f"\n🎯 Filtering to target series: {', '.join(self.target_series)}")
            filtered_series = []
            for series_name, series_url in series_urls:
                series_id = series_name.replace('Series ', '').strip()
                if series_id in self.target_series:
                    filtered_series.append((series_name, series_url))
                else:
                    print(f"   ⏭️ Skipping {series_name} (not in target list)")
            series_urls = filtered_series
            print(f"✅ Filtered to {len(series_urls)} target series")
        
        print(f"\n📋 Will scrape {len(series_urls)} series:")
        for series_name, series_url in series_urls:
            status = "✅ COMPLETED" if series_name in self.completed_series else "⏳ PENDING"
            print(f"   - {series_name} {status}")
        
        # Estimate total players
        estimated_players_per_series = 150  # Conservative estimate for APTA
        self.total_players_expected = len(series_urls) * estimated_players_per_series
        self.total_series_count = len(series_urls)
        
        print(f"\n🚀 Beginning scraping process...")
        print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Estimated total players: {self.total_players_expected:,}")
        print(f"{'='*60}")
        
        # Scrape each series
        successful_series = len(self.completed_series)
        failed_series = []
        
        for i, (series_name, series_url) in enumerate(series_urls, 1):
            if series_name in self.completed_series:
                print(f"\n⏭️ Skipping {series_name} (already completed)")
                continue
            
            print(f"\n🏆 Processing Series {i}/{len(series_urls)}: {series_name}")
            
            try:
                players = self.extract_players_from_series_page(series_name, series_url)
                if players:
                    # Mark series as completed and save individual file BEFORE adding to aggregate
                    self.completed_series.add(series_name)
                    self.save_series_completion(series_name, players)
                    
                    # Now add to aggregate list
                    self.all_players.extend(players)
                    successful_series += 1
                    print(f"✅ Successfully processed {series_name}: {len(players)} players")
                    print(f"   📁 Saved to: data/leagues/APTA_CHICAGO/temp/{series_name.replace(' ', '_').lower()}.json")
                else:
                    failed_series.append(series_name)
                    print(f"⚠️ No players found for {series_name}")
                    
                    # Still mark as completed (but with empty data) to avoid re-processing
                    self.completed_series.add(series_name)
                    self.save_series_completion(series_name, [])
                
                # Add delay between series
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error processing {series_name}: {e}")
                failed_series.append(series_name)
        
        # Save results
        self.save_results(is_final=True)
        
        print(f"\n🎉 SCRAPING COMPLETED!")
        print(f"   ✅ Successful series: {successful_series}")
        print(f"   ❌ Failed series: {len(failed_series)}")
        print(f"   👥 Total players found: {len(self.all_players)}")
        
        if failed_series:
            print(f"   Failed series: {', '.join(failed_series)}")

    def extract_players_from_series_page(self, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific series"""
        print(f"\n🎾 Scraping {series_name} from {series_url}")
        
        try:
            html_content = self.get_html_with_fallback(series_url)
            
            if not html_content:
                print(f"❌ Failed to get content for {series_name}")
                return []
            
            print(f"   ✅ Got HTML content ({len(html_content)} characters)")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            all_players = []
            
            # Find all team links on the series page
            team_links = []
            all_links = soup.find_all('a', href=True)
            
            # Extract series number/letter for filtering
            series_identifier = series_name.replace('Series ', '').strip()
            
            # Use a set to track unique team URLs to prevent duplicates
            seen_urls = set()
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for team links (they contain 'team=' parameter)
                if 'team=' in href and text:
                    # Filter teams to only include those belonging to this specific series
                    if self._team_belongs_to_series(text, series_identifier):
                        if href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = href
                        
                        # Only add if we haven't seen this URL before
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            team_links.append((text, full_url))
            
            print(f"🏢 Found {len(team_links)} team links in {series_name}")
            
            if not team_links:
                print(f"   ⚠️ No team links found - this might indicate a filtering issue")
                return []
            
            # Process each team
            for team_name, team_url in team_links:
                try:
                    players = self.extract_players_from_team_page(team_name, team_url, series_name, series_url)
                    if players:
                        all_players.extend(players)
                        print(f"     ✅ {team_name}: {len(players)} players")
                    else:
                        print(f"     ⚠️ {team_name}: No players found")
                    
                    # Add delay between teams
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"     ❌ Error processing team {team_name}: {e}")
                    continue
            
            # Final deduplication
            if all_players:
                unique_players_dict = {}
                duplicates_found = 0
                
                for player in all_players:
                    player_id = player.get('Player ID', '')
                    if player_id and player_id not in unique_players_dict:
                        unique_players_dict[player_id] = player
                    elif player_id:
                        duplicates_found += 1
                
                all_players = list(unique_players_dict.values())
                
                if duplicates_found > 0:
                    print(f"   🧹 Final deduplication: Removed {duplicates_found} duplicate players")
                    print(f"   📊 Final count: {len(all_players)} unique players")
                
                # Show series summary
                team_counts = {}
                for player in all_players:
                    team = player.get('Team', 'Unknown')
                    team_counts[team] = team_counts.get(team, 0) + 1
                
                print(f"   📊 Series {series_name} breakdown:")
                for team, count in sorted(team_counts.items()):
                    print(f"      {team}: {count} players")
            
            return all_players
            
        except Exception as e:
            print(f"❌ Error scraping {series_name}: {e}")
            return []

    def extract_players_from_team_page(self, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific team roster page"""
        try:
            html_content = self.get_html_with_fallback(team_url)
            
            if not html_content:
                print(f"     ❌ Failed to get team page for {team_name}")
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            players = []
            
            # Look for the main roster table
            roster_table = soup.find('table', class_='team_roster_table')
            
            if roster_table:
                print(f"       📋 Found team roster table, processing table structure")
                players = self._extract_players_from_table(roster_table, team_name, team_url, series_name, series_url)
            else:
                print(f"       ⚠️ No team roster table found, trying fallback method")
                players = self._extract_players_fallback(soup, team_name, team_url, series_name, series_url)
            
            print(f"     ✅ Found {len(players)} total players on {team_name} roster")
            return players
            
        except Exception as e:
            print(f"     ❌ Error scraping team {team_name}: {e}")
            return []

    def _extract_players_from_table(self, table_element, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Extract players from the APTA team roster table structure - SIMPLIFIED VERSION WITH CURRENT SEASON SCORES"""
        players = []
        
        # Find all rows in the table
        rows = table_element.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 4:  # Need at least name, PTI, wins, and losses
                
                # Extract player name (usually in first cell)
                player_cell = cells[0]
                player_link = player_cell.find('a', class_='lightbox-auto iframe link')
                
                if player_link:
                    # Get the full cell content to check for captain indicators outside the link
                    full_cell_text = player_cell.get_text(strip=True)
                    player_name = player_link.get_text(strip=True)
                    
                    # Skip empty rows or headers
                    if not player_name or player_name.lower() in ['name', 'player', '']:
                        continue
                    
                    # Skip sub players
                    if any(sub_indicator in player_name.lower() for sub_indicator in ['sub', 'substitute', '(sub)']):
                        continue
                    
                    # Check for captain indicators in the full cell content (not just the link text)
                    is_captain = False
                    clean_player_name = player_name
                    
                    if '(C)' in full_cell_text:
                        is_captain = True
                        clean_player_name = player_name  # Keep original name, don't modify it
                    elif '(CC)' in full_cell_text:
                        is_captain = True
                        clean_player_name = player_name  # Keep original name, don't modify it
                    
                    # Remove checkmark from player name
                    clean_player_name = clean_player_name.replace('✔', '').strip()
                    
                    # Extract player ID from any links
                    player_id = ""
                    if player_link:
                        href = player_link.get('href', '')
                        # Extract player ID from URL and change prefix
                        player_id_match = re.search(r'p=([^&]+)', href)
                        if player_id_match:
                            player_id = player_id_match.group(1)
                    
                    # Extract PTI from second cell
                    pti_cell = cells[1] if len(cells) > 1 else None
                    pti_raw = pti_cell.get_text(strip=True) if pti_cell else ''
                    
                    # Clean PTI value - remove checkmarks, captain indicators, and extra text
                    pti_value = re.sub(r'[✔✓☑☒☓]', '', pti_raw)  # Remove checkmarks
                    pti_value = re.sub(r'\s*\(C\)\s*', '', pti_value)  # Remove (C)
                    pti_value = re.sub(r'^[A-Za-z\s]+', '', pti_value)  # Remove leading text
                    pti_value = pti_value.strip()
                    
                    # If PTI is empty after cleaning, try to find numeric value
                    if not pti_value or pti_value == '':
                        # Look for any numeric value in the PTI cell
                        numbers = re.findall(r'\d+\.?\d*', pti_raw)
                        if numbers:
                            pti_value = numbers[0]
                        else:
                            pti_value = 'N/A'
                    
                    # Extract current season wins and losses from table cells
                    current_wins = 0
                    current_losses = 0
                    
                    if len(cells) >= 3:
                        try:
                            # Look for W and L columns (usually 3rd and 4th columns)
                            wins_text = cells[2].get_text(strip=True) if len(cells) > 2 else "0"
                            losses_text = cells[3].get_text(strip=True) if len(cells) > 3 else "0"
                            
                            # Convert to integers, handle empty or non-numeric values
                            current_wins = int(wins_text) if wins_text.isdigit() else 0
                            current_losses = int(losses_text) if losses_text.isdigit() else 0
                        except (ValueError, IndexError):
                            current_wins = 0
                            current_losses = 0
                    
                    # Calculate win percentage
                    total_games = current_wins + current_losses
                    win_percentage = f"{(current_wins/total_games*100):.1f}%" if total_games > 0 else "0.0%"
                    
                    # Parse first and last name from cleaned name
                    name_parts = clean_player_name.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                    
                    # Extract club name from team name
                    club_name = team_name
                    if ' - ' in team_name:
                        parts = team_name.split(' - ')
                        if len(parts) == 2:
                            club_name = parts[0].strip()
                    
                    # Remove dash from team name for display
                    team_name = team_name.replace(' - ', ' ')
                    
                    # Create player record with current season scores (NO CAREER STATS)
                    player_data = {
                        'Player ID': player_id,
                        'First Name': first_name,
                        'Last Name': last_name,
                        'Team': team_name,
                        'Series': series_name,
                        'League': 'APTA_CHICAGO',
                        'Club': club_name,
                        'PTI': pti_value,
                        'Wins': str(current_wins),
                        'Losses': str(current_losses),
                        'Win %': win_percentage,
                        'Captain': 'Yes' if is_captain else 'No',
                        'Source URL': team_url,
                        'source_league': 'APTA_CHICAGO',
                        'Scraped At': datetime.now().isoformat()
                    }
                    
                    # Debug print for each player
                    print(f"         🔍 SCRAPED PLAYER: {clean_player_name}")
                    print(f"            Player ID: {player_id}")
                    print(f"            First Name: {first_name}")
                    print(f"            Last Name: {last_name}")
                    print(f"            Team: {team_name}")
                    print(f"            Series: {series_name}")
                    print(f"            Club: {club_name}")
                    print(f"            PTI: {pti_value}")
                    print(f"            Captain: {'Yes' if is_captain else 'No'}")
                    print(f"            Current Season: {current_wins}W-{current_losses}L ({win_percentage})")
                    print(f"            ⚡ SIMPLE MODE: Current season scores included, NO career stats")
                    
                    players.append(player_data)
        
        return players

    def _extract_players_fallback(self, soup, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Fallback method to extract players when table structure is not found - SIMPLIFIED VERSION"""
        players = []
        
        # Look for any links that might be player links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Check if this looks like a player link
            if 'p=' in href and text and len(text.split()) >= 2:
                # Skip sub players
                if any(sub_indicator in text.lower() for sub_indicator in ['sub', 'substitute', '(sub)']):
                    continue
                
                # Extract player ID from URL and change prefix
                player_id_match = re.search(r'p=([^&]+)', href)
                player_id = player_id_match.group(1) if player_id_match else ""
                
                # Check for captain indicators in the parent element (like the main method)
                parent_text = link.parent.get_text(strip=True) if link.parent else text
                is_captain = False
                clean_player_name = text
                
                if '(C)' in parent_text:
                    is_captain = True
                    clean_player_name = text  # Keep original name, don't modify it
                elif '(CC)' in parent_text:
                    is_captain = True
                    clean_player_name = text  # Keep original name, don't modify it
                
                # Remove checkmark from player name
                clean_player_name = clean_player_name.replace('✔', '').strip()
                
                # Parse first and last name from cleaned name
                name_parts = clean_player_name.split()
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                
                # Extract club name from team name
                club_name = team_name
                if ' - ' in team_name:
                    parts = team_name.split(' - ')
                    if len(parts) == 2:
                        club_name = parts[0].strip()
                
                # Remove dash from team name for display
                team_name = team_name.replace(' - ', ' ')
                
                # Create player record with current season scores (NO CAREER STATS)
                # Note: Fallback method can't extract current season scores from links alone
                player_data = {
                    'Player ID': player_id,
                    'First Name': first_name,
                    'Last Name': last_name,
                    'Team': team_name,
                    'Series': series_name,
                    'League': 'APTA_CHICAGO',
                    'Club': club_name,
                    'PTI': 'N/A',  # Fallback method can't extract PTI
                    'Wins': '0',  # Fallback method can't extract scores
                    'Losses': '0',
                    'Win %': '0.0%',
                    'Captain': 'Yes' if is_captain else 'No',
                    'Source URL': team_url,
                    'source_league': 'APTA_CHICAGO',
                    'Scraped At': datetime.now().isoformat()
                }
                
                # Debug print for each player (fallback method)
                print(f"         🔍 SCRAPED PLAYER (FALLBACK): {clean_player_name}")
                print(f"            Player ID: {player_id}")
                print(f"            First Name: {first_name}")
                print(f"            Last Name: {last_name}")
                print(f"            Team: {team_name}")
                print(f"            Series: {series_name}")
                print(f"            Club: {club_name}")
                print(f"            PTI: N/A (Fallback method)")
                print(f"            Captain: {'Yes' if is_captain else 'No'}")
                print(f"            Current Season: 0W-0L (0.0%) - Fallback method")
                print(f"            ⚡ SIMPLE MODE: Current season scores included, NO career stats")
                
                players.append(player_data)
        
        return players

    def _team_belongs_to_series(self, team_name: str, series_identifier: str) -> bool:
        """
        Determine if a team belongs to the specified series in APTA Chicago.
        This method must be STRICT to prevent cross-series contamination.
        """
        if not team_name or not series_identifier:
            return False
        
        # Extract series number from series identifier
        if series_identifier.startswith("Series "):
            # Extract just the number part, not the SW suffix
            series_value = series_identifier.replace("Series ", "").replace(" SW", "")
        else:
            series_value = series_identifier.replace(" SW", "")
        
        # Check SW status FIRST before any pattern matching
        is_sw_series = ' SW' in series_identifier
        is_sw_team = ' SW' in team_name
        
        # SW teams must match SW series, regular teams must match regular series
        if is_sw_series != is_sw_team:
            return False  # Mismatch between SW status
        
        # SPECIAL CASE: Series 1 is actually a combined division that includes Series 1 and Series 2
        if series_value == "1":
            # Series 1 division includes teams ending with " - 1" or " - 2"
            if team_name.endswith(" - 1") or team_name.endswith(" - 2"):
                return True
            return False
        
        # Use word boundary matching to prevent partial matches
        import re
        
        # Create word boundary patterns to ensure exact series matching
        if is_sw_series:
            # SW series - only match SW patterns
            word_boundary_patterns = [
                rf'\b{re.escape(series_value)} SW\b',             # " 9 SW" (word boundary)
                rf'\bSeries {re.escape(series_value)} SW\b',      # "Series 9 SW" (word boundary)
            ]
        else:
            # Regular series - only match regular patterns
            word_boundary_patterns = [
                rf'\b{re.escape(series_value)}\b',                # " 9 " (word boundary)
                rf'\bSeries {re.escape(series_value)}\b',         # "Series 9" (word boundary)
            ]
        
        # Check for word boundary matches
        for pattern in word_boundary_patterns:
            if re.search(pattern, team_name):
                return True
        
        # Fallback to end-of-name patterns if word boundary patterns don't match
        if is_sw_series:
            # SW series - only match SW teams
            if team_name.endswith(f" {series_value} SW"):
                return True
            if team_name.endswith(f" - {series_value} SW"):
                return True
        else:
            # Regular series - only match regular teams
            if team_name.endswith(f" {series_value}"):
                return True
            if team_name.endswith(f" - {series_value}"):
                return True
        
        return False

    def save_series_completion(self, series_name: str, series_players: List[Dict]):
        """Save individual series file and progress after each completed series"""
        try:
            # Create data/leagues/APTA_CHICAGO/temp directory if it doesn't exist
            series_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp')
            os.makedirs(series_dir, exist_ok=True)
            
            # Save individual series file
            series_filename = series_name.replace(" ", "_").lower()  # "Series 20" -> "series_20"
            series_file = f"{series_dir}/{series_filename}.json"
            
            with open(series_file, 'w', encoding='utf-8') as f:
                json.dump(series_players, f, indent=2, ensure_ascii=False)
            
            print(f"📁 Saved {series_name} to: {series_file} ({len(series_players)} players)")
            
            # Save progress tracking
            progress_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp', 'scrape_progress.json')
            progress_data = {
                'completed_series': list(self.completed_series),
                'last_update': datetime.now().isoformat(),
                'total_players': len(self.all_players),
                'series_files_created': len(self.completed_series)
            }
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
                
            # Save current aggregate player data (only if we have aggregate data)
            output_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp', 'players_comprehensive_partial.json')
            if self.all_players:  # Only save if we have aggregate data
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.all_players, f, indent=2, ensure_ascii=False)
                
            print(f"💾 Progress saved: {series_name} complete - individual file + aggregate updated")
        except Exception as e:
            print(f"⚠️ Failed to save series completion: {e}")

    def _consolidate_all_temp_files(self) -> List[Dict]:
        """Consolidate all series temp files into a single player list"""
        print("🔍 Consolidating all temp series files...")
        
        temp_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp')
        all_players = []
        
        if not os.path.exists(temp_dir):
            print("   ⚠️ No temp directory found")
            return all_players
        
        # Find all series_*.json files
        series_files = []
        for filename in os.listdir(temp_dir):
            if filename.startswith('series_') and filename.endswith('.json'):
                series_files.append(filename)
        
        print(f"   📁 Found {len(series_files)} series temp files")
        
        for filename in sorted(series_files):
            file_path = os.path.join(temp_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    series_players = json.load(f)
                
                if isinstance(series_players, list):
                    all_players.extend(series_players)
                    print(f"   ✅ {filename}: {len(series_players)} players")
                else:
                    print(f"   ⚠️ {filename}: Invalid format (not a list)")
                    
            except Exception as e:
                print(f"   ❌ {filename}: Error reading file - {e}")
        
        print(f"   📊 Total consolidated players: {len(all_players):,}")
        return all_players
    
    def _merge_player_data(self, existing_players: List[Dict], new_players: List[Dict]) -> List[Dict]:
        """Merge existing and new player data, updating existing players with new data"""
        print("🔄 Merging existing and new player data...")
        
        # Create a lookup dictionary for existing players to enable updates
        # Use combination of name + team + series as unique identifier
        existing_lookup = {}
        for i, player in enumerate(existing_players):
            if isinstance(player, dict):
                name = player.get('First Name', '') + ' ' + player.get('Last Name', '')
                team = player.get('Team', '')
                series = player.get('Series', '')
                key = f"{name}|{team}|{series}"
                existing_lookup[key] = i  # Store index for updates
        
        print(f"   📊 Existing players: {len(existing_players):,}")
        print(f"   📊 New players: {len(new_players):,}")
        
        # Start with existing players
        merged_players = existing_players.copy()
        added_count = 0
        updated_count = 0
        
        # Process new players - either add new ones or update existing ones
        for player in new_players:
            if isinstance(player, dict):
                name = player.get('First Name', '') + ' ' + player.get('Last Name', '')
                team = player.get('Team', '')
                series = player.get('Series', '')
                key = f"{name}|{team}|{series}"
                
                if key in existing_lookup:
                    # Update existing player with new data
                    existing_index = existing_lookup[key]
                    existing_player = merged_players[existing_index]
                    
                    # Update all fields with new data
                    for field, value in player.items():
                        if field != 'Scraped At':  # Don't update timestamp
                            existing_player[field] = value
                    
                    updated_count += 1
                else:
                    # Add new player
                    merged_players.append(player)
                    added_count += 1
                    existing_lookup[key] = len(merged_players) - 1  # Add to lookup for future updates
        
        print(f"   ✅ Added {added_count} new unique players")
        print(f"   🔄 Updated {updated_count} existing players with new data")
        print(f"   📊 Final merged total: {len(merged_players):,} players")
        
        return merged_players

    def save_results(self, is_final: bool = False):
        """Save comprehensive results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if is_final:
            print(f"\n🏁 FINALIZING COMPREHENSIVE SCRAPE RESULTS...")
            
            # Show individual series files created
            series_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp')
            if os.path.exists(series_dir):
                series_files = [f for f in os.listdir(series_dir) if f.endswith('.json') and f.startswith('series_')]
                print(f"📁 Individual series files created: {len(series_files)}")
                for series_file in sorted(series_files):
                    print(f"   - {series_file}")
            
            # Clean up progress files since we're done
            try:
                progress_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp', 'scrape_progress.json')
                partial_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'temp', 'players_comprehensive_partial.json')
                
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                    print("🧹 Cleaned up progress tracking file")
                    
                if os.path.exists(partial_file):
                    os.remove(partial_file)
                    print("🧹 Cleaned up partial results file")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up temporary files: {e}")
        
        # Save timestamped version
        output_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', f"players_simple_{timestamp}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_players, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Simple results saved to: {output_file}")
        
        # Update main players.json file with intelligent merging
        main_output_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'APTA_CHICAGO', 'players.json')
        
        # First, consolidate all temp files to get complete picture
        consolidated_players = self._consolidate_all_temp_files()
        
        if os.path.exists(main_output_file):
            # Check if file is empty or contains only whitespace
            with open(main_output_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    existing_players = []
                else:
                    existing_players = json.loads(content)
            
            print(f"\n📊 COMPARISON WITH EXISTING DATA:")
            print(f"   Existing players.json: {len(existing_players):,} players")
            print(f"   New scraped data: {len(self.all_players):,} players")
            print(f"   Consolidated temp files: {len(consolidated_players):,} players")
            
            # Merge existing data with new data, avoiding duplicates
            merged_players = self._merge_player_data(existing_players, consolidated_players)
            
            print(f"   Final merged data: {len(merged_players):,} players")
            print(f"   Added: {len(merged_players) - len(existing_players):+,} players")
            
            # Update main file with merged data
            with open(main_output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_players, f, indent=2, ensure_ascii=False)
            print(f"✅ UPDATED main file: {main_output_file}")
            print(f"   📈 Preserved existing data + added new players!")
        else:
            # No existing file, use consolidated data
            with open(main_output_file, 'w', encoding='utf-8') as f:
                json.dump(consolidated_players, f, indent=2, ensure_ascii=False)
            print(f"✅ Created main file: {main_output_file}")
            print(f"   📈 Used consolidated temp file data")
            
        if is_final:
            print(f"\n🎯 FINAL SIMPLE SCRAPE COMPLETE!")
            print(f"   ✅ All {len(self.completed_series)} series processed")
            print(f"   📁 Individual series files: data/leagues/APTA_CHICAGO/temp/")
            print(f"   📁 Final aggregated data: {main_output_file}")
            print(f"   📁 Timestamped backup: {output_file}")

def main():
    """Main function"""
    import sys
    
    # Show help if requested
    if "--help" in sys.argv or "-h" in sys.argv:
        print("APTA Chicago Simple Player Scraper - Usage:")
        print("  python apta_scrape_players_simple.py                    # Scrape all series (1-50 and SW variants)")
        print("  python apta_scrape_players_simple.py --series 1,2,3     # Scrape specific series (1, 2, 3)")
        print("  python apta_scrape_players_simple.py --series=1,2,3     # Scrape specific series (1, 2, 3)")
        print("  python apta_scrape_players_simple.py --force-restart    # Force restart ignoring progress")
        print("  python apta_scrape_players_simple.py --fresh            # Same as --force-restart")
        print("  python apta_scrape_players_simple.py --help             # Show this help message")
        print("\nFEATURES:")
        print("  ⚡ SIMPLE MODE: Current season scores + player data (no career stats)")
        print("  🚀 FASTER: Skips career stats lookup for quicker execution")
        print("  📊 CURRENT SEASON: Player name, team, series, club, PTI, wins, losses")
        print("\nExamples:")
        print("  python apta_scrape_players_simple.py --series 1,2,3,7,9")
        print("  python apta_scrape_players_simple.py --series 7,9,11,13")
        return
    
    # Parse command line arguments
    force_restart = "--force-restart" in sys.argv or "--fresh" in sys.argv
    target_series = None
    
    # Check for series specification
    for i, arg in enumerate(sys.argv):
        if arg == "--series" and i + 1 < len(sys.argv):
            target_series = sys.argv[i + 1].split(',')
            break
        elif arg.startswith("--series="):
            target_series = arg.split("=", 1)[1].split(',')
            break
    
    # Validate target_series if specified
    if target_series:
        valid_series = [str(i) for i in range(1, 51)] + [f"{i} SW" for i in [7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31]]
        invalid_series = [s for s in target_series if s not in valid_series]
        if invalid_series:
            print(f"❌ Error: Invalid series specified: {', '.join(invalid_series)}")
            print(f"   Valid series are: 1-50 and 7 SW, 9 SW, 11 SW, 13 SW, 15 SW, 17 SW, 19 SW, 21 SW, 23 SW, 25 SW, 27 SW, 29 SW, 31 SW")
            return
        print(f"✅ Valid series specified: {', '.join(target_series)}")
    
    print("============================================================")
    if target_series:
        series_list = ', '.join(target_series)
        print(f"🏆 APTA CHICAGO SIMPLE TARGETED SERIES SCRAPER")
        print(f"   Scraping specific series: {series_list}")
    else:
        print("🏆 APTA CHICAGO SIMPLE COMPREHENSIVE ROSTER SCRAPER")
        print("   Scraping ALL series (1-50 and SW variants) from roster pages")
    print("   ⚡ SIMPLE MODE: Only current season player data")
    print("============================================================")
    
    scraper = APTAChicagoSimpleScraper(force_restart=force_restart, target_series=target_series)
    
    try:
        scraper.scrape_all_series()
        print("\n🎉 SIMPLE SCRAPING SESSION COMPLETED!")
        print("   Player data saved and ready for database import")
        
    except KeyboardInterrupt:
        print("\n⏸️ Scraping interrupted by user")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results(is_final=False)
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results(is_final=False)
    finally:
        # Clean up rally context
        if hasattr(scraper, 'rally_context') and scraper.rally_context:
            try:
                scraper.rally_context.quit()
                print("✅ Rally context (stealth browser) cleaned up")
            except:
                pass

if __name__ == "__main__":
    main()
