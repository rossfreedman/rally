#!/usr/bin/env python3
"""
Comprehensive CNSWPL Roster Scraper

This script systematically scrapes ALL CNSWPL series (1-17 and A-K) directly from 
team roster pages to capture every registered player, including those in missing 
series like H, I, J, K, 13, 15, etc.

Unlike the match-based scraper, this goes directly to team/roster pages to find
ALL registered players, not just those who have played matches.

Usage:
    python3 scripts/comprehensive_cnswpl_roster_scraper.py
"""

import sys
import os
import time
import json
import hashlib
import logging
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

def _pacer_mark_ok():
    """Helper function to safely mark successful responses for adaptive pacing."""
    try:
        mark('ok')
    except Exception:
        pass

# Configure logging to reduce output
logging.basicConfig(level=logging.WARNING)
logging.getLogger('selenium').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)

from helpers.stealth_browser import EnhancedStealthBrowser, StealthConfig
from helpers.user_agent_manager import UserAgentManager
from helpers.proxy_manager import fetch_with_retry
# Import the new rally runtime for efficiency upgrades
try:
    from helpers.rally_runtime import ScrapeContext
    RALLY_RUNTIME_AVAILABLE = True
except ImportError:
    RALLY_RUNTIME_AVAILABLE = False
    print("⚠️ Rally runtime not available, using traditional approach")

class CNSWPLRosterScraper:
    """Comprehensive CNSWPL roster scraper that hits all series pages"""
    
    def __init__(self, force_restart=False, target_series=None):
        self.base_url = "https://cnswpl.tenniscores.com"
        self.all_players = []
        self.completed_series = set()  # Track completed series for resumption
        self.target_series = target_series  # Specific series to scrape (e.g., ['A', 'B', 'C'] or ['1', '2', '3'])

        self.start_time = time.time()
        self.force_restart = force_restart
        
        # Progress tracking
        self.total_players_processed = 0
        self.total_players_expected = 0
        self.total_series_count = 0
        self.current_series = ""
        self.current_player = ""
        self.last_progress_update = time.time()
        
        # Speed optimizations flag
        self.SPEED_OPTIMIZATIONS_AVAILABLE = SPEED_OPTIMIZATIONS_AVAILABLE
        
        # Try to initialize rally runtime context for efficiency
        self.rally_context = self._initialize_rally_context()
        
        # Initialize stealth browser with better error handling
        self.stealth_browser = self._initialize_stealth_browser()
        
        if self.rally_context:
            print("✅ Rally runtime context initialized - using efficient driver reuse")
        elif self.stealth_browser:
            print("✅ Stealth browser initialized successfully")
        else:
            print("⚠️ Stealth browser failed - using curl fallback for all requests")
        
        # Load existing progress if not forcing restart
        self.load_existing_progress()
        
        # Use enhanced series discovery for better coverage
        print("\n🔍 Discovering available series...")
        discovered_series = self.discover_series_dynamically()
        
        # Fallback to hardcoded URLs if dynamic discovery fails
        if not discovered_series or all(url == "DISCOVER" for _, url in discovered_series):
            print("⚠️ Dynamic discovery incomplete, using hardcoded series URLs")
            series_urls = self.get_series_urls()
        else:
            series_urls = discovered_series
        
        print(f"\n📋 Will scrape {len(series_urls)} series:")
        for series_name, series_url in series_urls:
            status = "✅ COMPLETED" if series_name in self.completed_series else "⏳ PENDING"
            url_status = "🔍 DISCOVER" if series_url == "DISCOVER" else "✅ URL READY"
            print(f"   - {series_name} {status} ({url_status})")
    
    def _initialize_rally_context(self) -> Optional['ScrapeContext']:
        """Initialize rally runtime context for efficient scraping."""
        if not RALLY_RUNTIME_AVAILABLE:
            return None
            
        try:
            context = ScrapeContext(
                series_id="cnswpl_players",
                site_hint="https://cnswpl.tenniscores.com/"
            )
            print("✅ Rally runtime context initialized")
            return context
        except Exception as e:
            print(f"⚠️ Failed to initialize rally context: {e}")
            return None

    def _initialize_stealth_browser(self) -> Optional[EnhancedStealthBrowser]:
        """
        Initialize stealth browser with enhanced error handling and proxy management.
        
        Returns:
            EnhancedStealthBrowser instance if successful, None if failed
        """
        try:
            print("🔧 Initializing stealth browser...")
            
            # Initialize user agent manager (will auto-detect config path)
            user_agent_manager = UserAgentManager()
            current_user_agent = user_agent_manager.get_user_agent_for_site("https://cnswpl.tenniscores.com")
            print(f"   🎭 Using User-Agent: {current_user_agent[:50]}...")
            
            # Enhanced stealth configuration with better error handling
            stealth_config = StealthConfig(
                fast_mode=False,        # Use stealth mode for better success rate
                verbose=True,           # Enable verbose logging for debugging
                environment="production"  # Use production delays
            )
            
            # Initialize stealth browser with enhanced config
            stealth_browser = EnhancedStealthBrowser(stealth_config)
            
            # Test the browser with a working deep link instead of blocked root URL
            print("   🧪 Testing stealth browser...")
            test_url = "https://cnswpl.tenniscores.com/?mod=nndz-TjJiOWtOR2sxTnhI"  # Use series page instead of root
            
            try:
                pace_sleep()  # Adaptive pacing before network request
                test_response = stealth_browser.get_html(test_url)
                
                if test_response and len(test_response) > 100:
                    mark('ok')  # Mark successful response
                    print("   ✅ Stealth browser test successful")
                    return stealth_browser
                else:
                    print("   ❌ Stealth browser test failed - response too short")
                    return None
            except Exception as e:
                if "522" in str(e) or "Cloudflare" in str(e):
                    print("   ⚠️ CNSWPL site returned 522/Cloudflare error - this may be temporary")
                    print("   🔄 Will retry with different proxy on actual requests")
                    return stealth_browser  # Return browser anyway, let it handle retries
                else:
                    print(f"   ❌ Stealth browser test failed: {e}")
                    return None
                
        except Exception as e:
            print(f"   ❌ Failed to initialize stealth browser: {e}")
            print("   🔄 Falling back to curl-based requests")
            return None
    
    def _handle_proxy_rotation(self, stealth_browser: EnhancedStealthBrowser) -> bool:
        """
        Handle proxy rotation with intelligent error handling to prevent infinite loops.
        
        Args:
            stealth_browser: The stealth browser instance
            
        Returns:
            bool: True if proxy rotation successful, False if should fall back to curl
        """
        try:
            # Check if proxy rotation is needed
            if not hasattr(stealth_browser, 'rotate_proxy') or not stealth_browser.rotate_proxy():
                print("   ℹ️ No proxy rotation available")
                return True
            
            # Limit proxy rotation attempts
            max_rotation_attempts = 3
            for attempt in range(max_rotation_attempts):
                try:
                    print(f"   🔄 Rotating proxy (attempt {attempt + 1}/{max_rotation_attempts})...")
                    
                    # Add delay between rotation attempts
                    if attempt > 0:
                        time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s
                    
                    # Test the new proxy with a simple request
                    pace_sleep()  # Adaptive pacing before network request
                    test_response = stealth_browser.get_html("https://tennisscores.com")
                    if test_response and len(test_response) > 100:
                        mark('ok')  # Mark successful response
                        print("   ✅ Proxy rotation successful")
                        return True
                    else:
                        print(f"   ⚠️ Proxy rotation attempt {attempt + 1} failed - insufficient response")
                        
                except Exception as e:
                    print(f"   ❌ Proxy rotation attempt {attempt + 1} failed: {e}")
                    continue
            
            print("   ⚠️ Proxy rotation failed after all attempts")
            return False
            
        except Exception as e:
            print(f"   ❌ Proxy rotation error: {e}")
            return False
    
    def _check_proxy_health(self) -> bool:
        """
        Check if proxy pool is healthy and suggest fallback if needed.
        
        Returns:
            bool: True if proxy pool is healthy, False if should use fallback
        """
        try:
            from helpers.proxy_manager import rotator
            if hasattr(rotator, 'session_metrics'):
                total_requests = rotator.session_metrics.get('total_requests', 0)
                failed_requests = rotator.session_metrics.get('failed_requests', 0)
                dead_proxies = rotator.session_metrics.get('dead_proxies_detected', 0)
                
                if total_requests > 0:
                    failure_rate = (failed_requests / total_requests) * 100
                    if failure_rate > 60 or dead_proxies > 5:
                        print(f"   ⚠️ Proxy pool health: {failure_rate:.1f}% failure rate, {dead_proxies} dead proxies")
                        print(f"   🔄 Consider using browser fallback for better reliability")
                        return False
        except Exception as e:
            print(f"   ⚠️ Could not check proxy health: {e}")
        
        return True

    def _format_time(self, seconds):
        """Format seconds into human-readable time string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def _format_completion_time(self, completion_timestamp):
        """Format completion time in a user-friendly way."""
        if completion_timestamp <= 0:
            return "Calculating..."
        
        # Get current time and completion time
        now = time.time()
        completion_time = time.localtime(completion_timestamp)
        current_time = time.localtime(now)
        
        # Calculate time difference
        time_diff = completion_timestamp - now
        
        # If completion is today
        if completion_time.tm_yday == current_time.tm_yday:
            if time_diff < 3600:  # Less than 1 hour
                return f"in {self._format_time(time_diff)}"
            else:  # More than 1 hour today
                hour = completion_time.tm_hour
                minute = completion_time.tm_min
                am_pm = "AM" if hour < 12 else "PM"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                return f"today at {display_hour}:{minute:02d} {am_pm}"
        else:  # Different day
            days_diff = completion_time.tm_yday - current_time.tm_yday
            if days_diff == 1:
                return "tomorrow"
            elif days_diff <= 7:
                return f"in {days_diff} days"
            else:
                return f"in {days_diff} days"
    
    def _create_progress_bar(self, percent_complete, width=20):
        """Create a visual progress bar."""
        # Ensure percentage is within 0-100 range for display
        display_percent = max(0, min(percent_complete, 100))
        
        filled = int((display_percent / 100) * width)
        empty = width - filled
        
        # Create progress bar with different characters for different completion levels
        if display_percent < 25:
            fill_char = "░"  # Light fill
        elif display_percent < 50:
            fill_char = "▒"  # Medium fill
        elif display_percent < 75:
            fill_char = "▓"  # Dark fill
        else:
            fill_char = "█"  # Full fill
        
        bar = fill_char * filled + "░" * empty
        return f"[{bar}] {display_percent:.1f}%"

    def _update_progress(self, series_name="", player_name="", players_processed=0, total_players=0, player_stats=None):
        """Update and display comprehensive progress information with player details."""
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        # Update counters
        if players_processed > 0:
            self.total_players_processed = players_processed
        if total_players > 0:
            self.total_players_expected = total_players
        if series_name:
            self.current_series = series_name
        if player_name:
            self.current_player = player_name
        
        # Calculate progress metrics - dynamically adjust expected total based on actual discoveries
        if hasattr(self, 'total_series_count') and self.total_series_count > 0:
            # Use actual series count and realistic estimates for better progress tracking
            if self.total_players_processed > self.total_players_expected:
                # We've discovered more players than initially estimated
                # Recalculate based on current average and remaining series
                completed_series_count = len(self.completed_series) if hasattr(self, 'completed_series') else 1
                if completed_series_count > 0:
                    avg_players_per_series = self.total_players_processed / completed_series_count
                    remaining_series = self.total_series_count - completed_series_count
                    self.total_players_expected = self.total_players_processed + (remaining_series * avg_players_per_series)
                else:
                    # Fallback: add buffer for remaining players
                    self.total_players_expected = self.total_players_processed + 100
        
        if self.total_players_expected > 0:
            percent_complete = (self.total_players_processed / self.total_players_expected) * 100
            # Cap percentage at 100% for display purposes
            percent_complete = min(percent_complete, 100.0)
        else:
            percent_complete = 0
        
        # Calculate estimated time remaining
        if self.total_players_processed > 0 and elapsed_time > 0:
            avg_time_per_player = elapsed_time / self.total_players_processed
            remaining_players = max(0, self.total_players_expected - self.total_players_processed)
            estimated_remaining_time = remaining_players * avg_time_per_player
            estimated_completion_time = time.time() + estimated_remaining_time
            
            # If we've exceeded our estimate, show minimal remaining time
            if remaining_players == 0:
                estimated_remaining_time = 60  # Show 1 minute remaining when near completion
        else:
            estimated_remaining_time = 0
            estimated_completion_time = 0
        
        # Calculate processing rate
        if elapsed_time > 0:
            players_per_hour = (self.total_players_processed / elapsed_time) * 3600
        else:
            players_per_hour = 0
        
        # Display progress (only update every 5 seconds to avoid spam, or when processing new players)
        if current_time - self.last_progress_update >= 5 or players_processed > 0:
            print(f"\n{'='*80}")
            print(f"📊 SCRAPING PROGRESS UPDATE")
            print(f"{'='*80}")
            print(f"🎯 Current Series: {self.current_series}")
            print(f"👤 Current Player: {self.current_player}")
            
            # Show player stats if available
            if player_stats:
                self._display_player_stats(player_stats)
            
            # Show progress with prominent percentage and progress bar
            print(f"📈 Progress: {self.total_players_processed:,} / {self.total_players_expected:,} players")
            print(f"🎯 TOTAL COMPLETE: {percent_complete:.1f}%")
            print(f"📊 Progress Bar: {self._create_progress_bar(percent_complete)}")
            print(f"⏱️  Elapsed Time: {self._format_time(elapsed_time)}")
            print(f"⏳ Estimated Remaining: {self._format_time(estimated_remaining_time)}")
            print(f"🏁 Estimated Completion: {self._format_completion_time(estimated_completion_time)}")
            print(f"🚀 Processing Rate: {players_per_hour:.1f} players/hour")
            print(f"{'='*80}")
            self.last_progress_update = current_time
    
    def _display_player_stats(self, player_stats):
        """Display player statistics in a formatted way."""
        if not player_stats:
            return
        
        print(f"📊 Player Stats:")
        
        # Season stats
        season_wins = player_stats.get('Season Wins', 0)
        season_losses = player_stats.get('Season Losses', 0)
        season_win_pct = player_stats.get('Season Win %', '0.0%')
        print(f"   🏆 Season: {season_wins}W/{season_losses}L ({season_win_pct})")
        
        # Career stats
        career_wins = player_stats.get('Career Wins', 0)
        career_losses = player_stats.get('Career Losses', 0)
        career_win_pct = player_stats.get('Career Win %', '0.0%')
        print(f"   🎯 Career: {career_wins}W/{career_losses}L ({career_win_pct})")
        
        # Additional info
        club = player_stats.get('Club', 'Unknown')
        series = player_stats.get('Series', 'Unknown')
        print(f"   🏢 Club: {club} | Series: {series}")

    def _get_recent_success_rate(self) -> float:
        """Calculate recent success rate for adaptive delays."""
        if not hasattr(self, 'recent_requests'):
            self.recent_requests = []
        
        # Keep only last 20 requests for recent success rate
        if len(self.recent_requests) > 20:
            self.recent_requests = self.recent_requests[-20:]
        
        if not self.recent_requests:
            return 1.0  # Assume success if no history
        
        return sum(self.recent_requests) / len(self.recent_requests)
    
    def _get_delay_multiplier(self, success_rate: float, very_fast: float, fast: float, moderate: float, conservative: float) -> float:
        """Get delay multiplier based on success rate."""
        if success_rate >= 0.98:
            return very_fast
        elif success_rate >= 0.95:
            return fast
        elif success_rate >= 0.90:
            return moderate
        else:
            return conservative
    
    def _record_request_result(self, success: bool):
        """Record request result for success rate tracking."""
        if not hasattr(self, 'recent_requests'):
            self.recent_requests = []
        
        self.recent_requests.append(success)
        
        # Track recent errors for adaptive pacing
        if not hasattr(self, 'recent_errors'):
            self.recent_errors = 0
        
        if not success:
            self.recent_errors += 1
        else:
            # Decay error count on success
            self.recent_errors = max(0, self.recent_errors - 0.1)
    
    def _process_teams_parallel(self, team_links: List[Tuple[str, str]], series_name: str, series_url: str) -> List[Dict]:
        """Process teams in parallel for massive speed improvement."""
        try:
            from .settings_stealth import (
                ENABLE_PARALLEL_PROCESSING, PARALLEL_WORKERS, PARALLEL_BATCH_SIZE,
                PARALLEL_BATCH_DELAY, PARALLEL_MAX_RETRIES, PARALLEL_TIMEOUT
            )
        except ImportError:
            # Fallback to sequential processing
            return self._process_teams_sequential(team_links, series_name, series_url)
        
        if not ENABLE_PARALLEL_PROCESSING:
            return self._process_teams_sequential(team_links, series_name, series_url)
        
        print(f"   🚀 Processing {len(team_links)} teams in parallel ({PARALLEL_WORKERS} workers)")
        
        all_players = []
        seen_player_ids = set()
        
        # Process teams in batches
        for i in range(0, len(team_links), PARALLEL_BATCH_SIZE):
            batch = team_links[i:i + PARALLEL_BATCH_SIZE]
            batch_num = (i // PARALLEL_BATCH_SIZE) + 1
            total_batches = (len(team_links) + PARALLEL_BATCH_SIZE - 1) // PARALLEL_BATCH_SIZE
            
            print(f"   📦 Processing batch {batch_num}/{total_batches} ({len(batch)} teams)")
            
            # Process batch in parallel
            batch_players = self._process_team_batch_parallel(batch, series_name, series_url)
            
            # Filter duplicates and add to results
            for player in batch_players:
                player_id = player.get('Player ID', '')
                if player_id and player_id not in seen_player_ids:
                    seen_player_ids.add(player_id)
                    all_players.append(player)
                elif player_id:
                    print(f"      ⚠️ Skipping duplicate player: {player.get('First Name', '')} {player.get('Last Name', '')} (ID: {player_id})")
            
            # Add delay between batches
            if i + PARALLEL_BATCH_SIZE < len(team_links):
                time.sleep(PARALLEL_BATCH_DELAY)
        
        print(f"   ✅ Parallel processing complete: {len(all_players)} unique players from {len(team_links)} teams")
        return all_players
    
    def _process_team_batch_parallel(self, team_batch: List[Tuple[str, str]], series_name: str, series_url: str) -> List[Dict]:
        """Process a batch of teams in parallel using ThreadPoolExecutor."""
        try:
            from .settings_stealth import PARALLEL_WORKERS, PARALLEL_TIMEOUT
        except ImportError:
            PARALLEL_WORKERS = 4
            PARALLEL_TIMEOUT = 30
        
        batch_players = []
        
        with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
            # Submit all team processing tasks
            future_to_team = {
                executor.submit(self._extract_players_from_team_page_safe, team_name, team_url, series_name, series_url): 
                (team_name, team_url) for team_name, team_url in team_batch
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_team, timeout=PARALLEL_TIMEOUT * len(team_batch)):
                team_name, team_url = future_to_team[future]
                try:
                    team_players = future.result(timeout=PARALLEL_TIMEOUT)
                    if team_players:
                        batch_players.extend(team_players)
                        print(f"      ✅ {team_name}: {len(team_players)} players")
                    else:
                        print(f"      ⚠️ {team_name}: No players found")
                except Exception as e:
                    print(f"      ❌ {team_name}: Error - {e}")
                    # Record failure for success rate tracking
                    self._record_request_result(False)
        
        return batch_players
    
    def _extract_players_from_team_page_safe(self, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Thread-safe version of extract_players_from_team_page for parallel processing."""
        try:
            # Get the team page with timeout monitoring using fallback method
            start_time = time.time()
            html_content = self.get_html_with_fallback(team_url)
            elapsed = time.time() - start_time
            
            if elapsed > 60:  # 1 minute warning
                print(f"        ⚠️ {team_name} request took {elapsed:.1f}s")
                
            if not html_content:
                print(f"        ❌ Failed to get team page for {team_name}")
                self._record_request_result(False)
                return []
            
            print(f"        ✅ Got team page for {team_name} ({len(html_content)} characters)")
            self._record_request_result(True)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            players = []
            
            # CNSWPL uses a table-based structure with class 'team_roster_table'
            roster_table = soup.find('table', class_='team_roster_table')
            
            if roster_table:
                players = self._extract_players_from_table(roster_table, team_name, team_url, series_name, series_url)
            else:
                # Fall back to the old method but with sub filtering
                players = self._extract_players_fallback_with_sub_filtering(soup, team_name, team_url, series_name, series_url)
            
            return players
            
        except Exception as e:
            print(f"        ❌ Error scraping team {team_name}: {e}")
            self._record_request_result(False)
            return []
    
    def _process_teams_sequential(self, team_links: List[Tuple[str, str]], series_name: str, series_url: str) -> List[Dict]:
        """Fallback sequential processing for teams."""
        print(f"   📝 Processing {len(team_links)} teams sequentially")
        
        all_players = []
        seen_player_ids = set()
        
        for i, (team_name, team_url) in enumerate(team_links):
            print(f"   🎾 Scraping team {i+1}/{len(team_links)}: {team_name}")
            print(f"      🌐 URL: {team_url}")
            team_players = self.extract_players_from_team_page(team_name, team_url, series_name, series_url)
            
            # Filter out duplicate players based on Player ID
            unique_team_players = []
            for player in team_players:
                player_id = player.get('Player ID', '')
                if player_id and player_id not in seen_player_ids:
                    seen_player_ids.add(player_id)
                    unique_team_players.append(player)
                elif player_id:
                    print(f"         ⚠️ Skipping duplicate player: {player.get('First Name', '')} {player.get('Last Name', '')} (ID: {player_id})")
            
            all_players.extend(unique_team_players)
            
            # Show team summary
            if unique_team_players:
                print(f"      📊 Team {team_name}: {len(unique_team_players)} unique players added (filtered from {len(team_players)} total)")
            else:
                print(f"      ⚠️ Team {team_name}: No unique players found")
            
            # Add delay between team requests
            if i < len(team_links) - 1:
                self._add_intelligent_delay("team")
        
        return all_players

    def _add_intelligent_delay(self, request_type: str = "general"):
        """
        Add intelligent, randomized delays between requests to mimic human behavior.
        Uses adaptive pacing when available for speed optimization.
        
        Args:
            request_type: Type of request ("series", "team", "general")
        """
        import random
        
        # Use adaptive pacing if available
        if SPEED_OPTIMIZATIONS_AVAILABLE:
            try:
                pace_sleep()
                return
            except Exception as e:
                print(f"⚠️ Adaptive pacing failed, using optimized delay: {e}")
        
        # Get optimized delay settings
        try:
            from .settings_stealth import (
                TEAM_DELAY_MIN, TEAM_DELAY_MAX, SERIES_DELAY_MIN, SERIES_DELAY_MAX,
                HIGH_SUCCESS_THRESHOLD, GOOD_SUCCESS_THRESHOLD, MODERATE_SUCCESS_THRESHOLD,
                VERY_FAST_MULTIPLIER, FAST_MULTIPLIER, MODERATE_MULTIPLIER, CONSERVATIVE_MULTIPLIER
            )
        except ImportError:
            # Fallback to conservative settings
            TEAM_DELAY_MIN, TEAM_DELAY_MAX = 0.8, 2.0
            SERIES_DELAY_MIN, SERIES_DELAY_MAX = 2.0, 4.0
            HIGH_SUCCESS_THRESHOLD, GOOD_SUCCESS_THRESHOLD, MODERATE_SUCCESS_THRESHOLD = 0.98, 0.95, 0.90
            VERY_FAST_MULTIPLIER, FAST_MULTIPLIER, MODERATE_MULTIPLIER, CONSERVATIVE_MULTIPLIER = 0.3, 0.6, 0.8, 1.2
        
        # Calculate success rate for adaptive delays
        success_rate = self._get_recent_success_rate()
        
        if request_type == "series":
            # Use adaptive pacing for series delays
            try:
                from .adaptive_pacer import next_delay
                recent_errors = getattr(self, 'recent_errors', 0)
                delay = next_delay(success_rate, recent_errors)
                print(f"   ⏳ Adaptive series delay: {delay:.1f}s (success rate: {success_rate:.1%})")
                time.sleep(delay)
            except ImportError:
                # Fallback to optimized delays
                base_delay = random.uniform(SERIES_DELAY_MIN, SERIES_DELAY_MAX)
                multiplier = self._get_delay_multiplier(success_rate, VERY_FAST_MULTIPLIER, FAST_MULTIPLIER, MODERATE_MULTIPLIER, CONSERVATIVE_MULTIPLIER)
                delay = round(base_delay * multiplier, 1)
                print(f"   ⏳ Waiting {delay:.1f}s before next series... (success rate: {success_rate:.1%})")
                time.sleep(delay)
            
        elif request_type == "team":
            # Use adaptive pacing for team delays
            try:
                from .adaptive_pacer import next_delay
                recent_errors = getattr(self, 'recent_errors', 0)
                delay = next_delay(success_rate, recent_errors)
                
                # Add occasional human-like variation (10% chance)
                if random.random() < 0.10:
                    variation = random.uniform(0.2, 0.5)
                    delay += variation
                    print(f"   🤔 Human variation... (+{variation:.1f}s)")
                
                print(f"   ⏳ Adaptive team delay: {delay:.1f}s (success rate: {success_rate:.1%})")
                time.sleep(delay)
            except ImportError:
                # Fallback to optimized delays
                base_delay = random.uniform(TEAM_DELAY_MIN, TEAM_DELAY_MAX)
                multiplier = self._get_delay_multiplier(success_rate, VERY_FAST_MULTIPLIER, FAST_MULTIPLIER, MODERATE_MULTIPLIER, CONSERVATIVE_MULTIPLIER)
                delay = round(base_delay * multiplier, 1)
                
                # Add occasional human-like variation (10% chance)
                if random.random() < 0.10:
                    variation = random.uniform(0.2, 0.8)
                    delay += variation
                    print(f"   🤔 Human variation... (+{variation:.1f}s)")
                
                print(f"   ⏳ Waiting {delay:.1f}s before next team... (success rate: {success_rate:.1%})")
                time.sleep(delay)
            
        else:
            # General delay with natural variation
            base_delay = random.uniform(1.8, 2.8)  # 1.8-2.8 seconds
            jitter = random.uniform(0.85, 1.15)  # ±15% variation
            delay = round(base_delay * jitter, 1)
            
            print(f"   ⏳ Adding {delay:.1f}s delay...")
            time.sleep(delay)
    
    def _team_belongs_to_series(self, team_name: str, series_identifier: str) -> bool:
        """
        Determine if a team belongs to the specified series in CNSWPL.
        CNSWPL uses both numeric series (1-17) and letter series (A-K).
        """
        if not team_name or not series_identifier:
            return False
        
        # Extract series number from series identifier
        if series_identifier.startswith("Series "):
            series_value = series_identifier.replace("Series ", "")
        else:
            series_value = series_identifier
        
        # CNSWPL team naming patterns:
        # - "Club Name X" (e.g., "Birchwood 1", "Tennaqua 22")
        # - "Club Name Xa/Xb" (e.g., "Tennaqua 22a", "Tennaqua 22b")
        # - "Club Name X" (e.g., "Birchwood A", "Tennaqua B") for letter series
        
        # Check if team name contains the series identifier
        if series_value.isdigit():
            # Numeric series (1-17) - use word boundaries to avoid partial matches
            # " 1 " or " 1" at end or " 1a" or " 1b"
            if (f" {series_value} " in team_name or 
                team_name.endswith(f" {series_value}") or
                f" {series_value}a" in team_name or 
                f" {series_value}b" in team_name):
                return True
        elif series_value.isalpha() and series_value in 'ABCDEFGHIJK':
            # Letter series (A-K)
            # Check for exact letter match (e.g., "Birchwood A", "Tennaqua B")
            if (f" {series_value} " in team_name or 
                team_name.endswith(f" {series_value}") or
                f" {series_value}1" in team_name or 
                f" {series_value}2" in team_name):
                return True
        elif series_value == 'SN':
            # Special case for Series SN (Sunday Night League)
            # Teams have "SN" suffix (e.g., "Michigan Shores SN", "Prairie Club SN (3)")
            if team_name.endswith(' SN') or ' SN (' in team_name:
                return True
        
        return False

    def _construct_team_name(self, club_name: str, team_series: str) -> str:
        """
        Construct team name, avoiding duplicate series suffixes.
        
        For Series SN teams that already have 'SN' in their name,
        don't add it again.
        """
        series_suffix = team_series.replace('Series ', '')
        
        # Special handling for Series SN - don't add SN if already present
        if series_suffix == 'SN' and (' SN' in club_name or club_name.endswith('SN')):
            return club_name
        
        # For other series, add the suffix
        return f"{club_name} {series_suffix}"

    def _parse_player_name(self, full_name: str) -> Tuple[str, str]:
        """
        Enhanced name parsing to handle compound first names and organizational suffixes.
        
        Fixes issues like:
        - "Mary Jo Lestingi" -> ("Mary Jo", "Lestingi") instead of ("Mary", "Jo Lestingi") 
        - "Peters - MSC" -> ("Peters", "") by removing organizational suffixes
        
        Preserves legitimate patterns like:
        - Hyphens: "Smith-Jones" 
        - Apostrophes: "O'Brien"
        """
        if not full_name or not full_name.strip():
            return 'Unknown', ''
        
        # Clean the name
        name = full_name.strip()
        
        # Remove organizational suffixes (like "- MSC")
        name = self._clean_organizational_suffixes(name)
        
        # Split into parts
        parts = name.split()
        if len(parts) == 0:
            return 'Unknown', ''
        elif len(parts) == 1:
            return parts[0], ''
        elif len(parts) == 2:
            return parts[0], parts[1]
        else:
            # Handle compound names intelligently
            return self._handle_compound_names(parts)
    
    def _clean_organizational_suffixes(self, name: str) -> str:
        """Remove organizational suffixes like '- MSC' from names"""
        # List of organizational suffixes to remove
        org_suffixes = [
            ' - MSC',
            ' - msc',
            ' MSC',
            ' msc'
        ]
        
        for suffix in org_suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        return name
    
    def _handle_compound_names(self, parts: List[str]) -> Tuple[str, str]:
        """
        Handle names with 3+ parts to distinguish compound first names from parsing errors.
        
        Strategy:
        1. If last part looks like a clear surname (capitalized, common pattern), use it as last name
        2. If multiple capitalized words, likely indicates first name was split incorrectly
        3. For names like "Mary Jo Lestingi", assume "Mary Jo" is first name, "Lestingi" is last
        """
        if len(parts) < 3:
            return parts[0], ' '.join(parts[1:])
        
        # Check if this looks like a compound first name case
        # Heuristic: if the middle part(s) are short and could be middle names or compound first names
        middle_parts = parts[1:-1]
        last_part = parts[-1]
        
        # If we have exactly 3 parts and middle part is short (1-2 chars or common compound names)
        if len(parts) == 3:
            middle = parts[1]
            # Common compound first name patterns
            compound_indicators = ['Jo', 'Ann', 'Anne', 'Sue', 'Lee', 'May', 'Kay', 'Beth', 'Lynn', 'Rose']
            
            if (len(middle) <= 2 or 
                middle in compound_indicators or 
                middle.lower() in [x.lower() for x in compound_indicators]):
                # Treat as compound first name: "Mary Jo" + "Lestingi"
                first_name = f"{parts[0]} {middle}"
                last_name = last_part
            else:
                # Treat as first + middle + last: "John" + "Michael Smith"
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
        else:
            # For 4+ parts, assume first part is first name, rest is last name
            # This handles cases like parsing errors where multiple words got split
            first_name = parts[0]
            last_name = ' '.join(parts[1:])
        
        return first_name, last_name

    def _convert_to_cnswpl_format(self, nndz_player_id: str) -> str:
        """
        Convert nndz- format player ID to cnswpl_ format using simple prefix replacement.
        
        This ensures compatibility with the ETL system which expects cnswpl_ format IDs
        for CNSWPL players to prevent match import failures.
        
        Args:
            nndz_player_id: Player ID in nndz-XXXXX format
            
        Returns:
            Player ID in cnswpl_XXXXX format (simple prefix replacement)
        """
        if not nndz_player_id or not nndz_player_id.startswith('nndz-'):
            return nndz_player_id
        
        # Simple prefix replacement: nndz-XXXXX -> cnswpl_XXXXX
        return nndz_player_id.replace('nndz-', 'cnswpl_')

    def get_series_urls(self) -> List[Tuple[str, str]]:
        """Generate URLs for CNSWPL series (1-17 and A-K)"""
        series_urls = []
        
        # CNSWPL uses both numeric series (1-17) and letter series (A-K) in the Day League
        # These are the actual series URLs from the website
        series_urls_data = [
            # Numeric series (1-17)
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
            # Letter series (A-K) - these URLs need to be discovered or provided
            # For now, we'll use placeholder URLs that the scraper will need to discover
            ("Series A", None),  # Will be discovered dynamically
            ("Series B", None),  # Will be discovered dynamically
            ("Series C", None),  # Will be discovered dynamically
            ("Series D", None),  # Will be discovered dynamically
            ("Series E", None),  # Will be discovered dynamically
            ("Series F", None),  # Will be discovered dynamically
            ("Series G", None),  # Will be discovered dynamically
            ("Series H", None),  # Will be discovered dynamically
            ("Series I", None),  # Will be discovered dynamically
            ("Series J", None),  # Will be discovered dynamically
            ("Series K", None),  # Will be discovered dynamically
            # Special series
            ("Series SN", "/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WlNlN3lMcz0%3D")
        ]
        
        # Filter series based on target_series parameter
        if self.target_series:
            filtered_data = []
            for series_name, series_path in series_urls_data:
                # Extract series identifier (number or letter)
                series_id = series_name.replace('Series ', '').strip()
                if series_id in self.target_series:
                    filtered_data.append((series_name, series_path))
            series_urls_data = filtered_data
        
        # Process series URLs
        for series_name, series_path in series_urls_data:
            if series_path:
                # Use hardcoded URL
                series_url = f"{self.base_url}{series_path}"
                series_urls.append((series_name, series_url))
            else:
                # For letter series, we'll need to discover the URL dynamically
                # For now, add a placeholder that will trigger dynamic discovery
                series_urls.append((series_name, "DISCOVER"))
        
        return series_urls
    
    def extract_players_from_series_page(self, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific series by finding team links and scraping their rosters"""
        print(f"\n🎾 Scraping {series_name} from {series_url}")
        
        try:
            # Use stealth browser with fallback to curl
            start_time = time.time()
            html_content = self.get_html_with_fallback(series_url)
            elapsed = time.time() - start_time
            
            # If request took too long, it might be stuck in proxy testing
            if elapsed > 120:  # 2 minutes
                print(f"⚠️ Request took {elapsed:.1f}s - possible proxy testing loop")
                
            if not html_content:
                print(f"❌ Failed to get content for {series_name}")
                self._record_request_result(False)
                return []
            
            print(f"   ✅ Got HTML content ({len(html_content)} characters)")
            self._record_request_result(True)
            
            # Add intelligent delay after successful series page request
            self._add_intelligent_delay("series")
            
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
                if 'team=' in href and text and any(keyword.lower() in text.lower() for keyword in ['Tennaqua', 'Winter Club', 'Lake Forest', 'Evanston', 'Prairie Club', 'Prarie Club', 'Wilmette', 'North Shore', 'Valley Lo', 'Westmoreland', 'Indian Hill', 'Birchwood', 'Exmoor', 'Glen View', 'Glenbrook', 'Park Ridge', 'Skokie', 'Michigan Shores', 'Midtown', 'Hinsdale', 'Knollwood', 'Sunset Ridge', 'Briarwood', 'Biltmore', 'Barrington Hills', 'Bryn Mawr', 'Saddle & Cycle', 'Onwentsia', 'Lake Bluff', 'Lake Shore', 'Northmoor', 'Butterfield', 'River Forest', 'LifeSport', 'Winnetka']):
                    
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
                        else:
                            print(f"      ⚠️ Skipping duplicate team URL: {text} ({full_url})")
            

            print(f"🏢 Found {len(team_links)} team links in {series_name}")
            
            # Log the team links for debugging
            for i, (team_name, team_url) in enumerate(team_links):
                print(f"      {i+1}. {team_name} -> {team_url}")
            
            if not team_links:
                print(f"   ⚠️ No team links found - this might indicate a filtering issue")
            
            # Process teams using parallel or sequential processing
            all_players = self._process_teams_parallel(team_links, series_name, series_url)
            
            print(f"✅ Extracted {len(all_players)} total players from {series_name}")
            
            # Final deduplication step to ensure no duplicates made it through
            if all_players:
                # Create a dictionary to keep only the first occurrence of each player ID
                unique_players_dict = {}
                duplicates_found = 0
                
                for player in all_players:
                    player_id = player.get('Player ID', '')
                    if player_id and player_id not in unique_players_dict:
                        unique_players_dict[player_id] = player
                    elif player_id:
                        duplicates_found += 1
                
                # Convert back to list
                all_players = list(unique_players_dict.values())
                
                if duplicates_found > 0:
                    print(f"   🧹 Final deduplication: Removed {duplicates_found} duplicate players")
                    print(f"   📊 Final count: {len(all_players)} unique players")
                
                # Show series summary with team breakdown
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
    
    def extract_players_from_team_page_with_rally_context(self, team_name: str, team_url: str, series_name: str, series_url: str, player_index: int = 0) -> List[Dict]:
        """
        Extract players using rally runtime context for efficiency.
        This demonstrates the new stealth & efficiency approach.
        """
        if not self.rally_context:
            # Fallback to traditional method
            return self.extract_players_from_team_page(team_name, team_url, series_name, series_url)
        
        try:
            # Start driver if not already started (reuses existing driver)
            driver = self.rally_context.start_driver()
            if not driver:
                # Fallback to traditional method
                return self.extract_players_from_team_page(team_name, team_url, series_name, series_url)
            
            # Get HTML using the rally context
            html = self.rally_context.get_html_with_driver(team_url)
            
            # Validate the HTML
            success = len(html) > 1000 and "player" in html.lower()
            
            # Maybe save debug HTML (respects settings_stealth.py configuration)
            def save_html_debug(content, filename):
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            self.rally_context.maybe_save_debug(html, success, save_html_debug, f"team_{team_name}", player_index)
            
            if not success:
                print(f"     ❌ Invalid HTML received for team {team_name}")
                return []
            
            # Parse the HTML (same logic as original)
            soup = BeautifulSoup(html, 'html.parser')
            # Add human-like pause after successful extraction
            self.rally_context.pause_between_players(player_index)
            
            return self._extract_players_from_soup(soup, team_name, team_url, series_name, series_url)
            
        except Exception as e:
            print(f"     ❌ Rally context error for team {team_name}: {e}")
            # Fallback to traditional method
            return self.extract_players_from_team_page(team_name, team_url, series_name, series_url)

    def extract_players_from_team_page(self, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Extract all players from a specific team roster page, excluding sub players"""
        try:
            # Get the team page with timeout monitoring using fallback method
            start_time = time.time()
            html_content = self.get_html_with_fallback(team_url)
            elapsed = time.time() - start_time
            
            if elapsed > 60:  # 1 minute warning
                print(f"     ⚠️ Team page request took {elapsed:.1f}s")
                
            if not html_content:
                print(f"     ❌ Failed to get team page for {team_name}")
                self._record_request_result(False)
                return []
            
            print(f"     ✅ Got team page for {team_name} ({len(html_content)} characters)")
            self._record_request_result(True)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            players = []
            
            # CNSWPL uses a table-based structure with class 'team_roster_table'
            # Look for the main roster table first
            roster_table = soup.find('table', class_='team_roster_table')
            
            if roster_table:
                print(f"       📋 Found team roster table, processing table structure")
                players = self._extract_players_from_table(roster_table, team_name, team_url, series_name, series_url)
            else:
                print(f"       ⚠️ No team roster table found, trying fallback method")
                # Fall back to the old method but with sub filtering
                return self._extract_players_fallback_with_sub_filtering(soup, team_name, team_url, series_name, series_url)
            
            print(f"     ✅ Found {len(players)} total players on {team_name} roster (excluding subs)")
            return players
            
        except Exception as e:
            print(f"     ❌ Error scraping team {team_name}: {e}")
            return []
    
    def _extract_players_from_table(self, table_element, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Extract players from the CNSWPL team roster table structure"""
        players = []
        
        # Find all table rows
        all_rows = table_element.find_all('tr')
        
        print(f"         🔍 Found {len(all_rows)} total rows")
        
        # Track current section
        current_section = None
        
        # Process each row
        for row_idx, row in enumerate(all_rows):
            cells = row.find_all(['td', 'th'])
            
            if not cells:
                continue
            
            # Check if this is a section header (has colspan attribute)
            first_cell = cells[0]
            colspan = first_cell.get('colspan', '1')
            
            if colspan != '1':
                # This is a section header
                section_text = first_cell.get_text(strip=True).lower()
                
                if 'captains' in section_text:
                    current_section = 'captains'
                    print(f"         📋 Found Captains section at row {row_idx + 1}")
                elif 'players' in section_text and 'subbing' not in section_text:
                    current_section = 'players'
                    print(f"         📋 Found Players section at row {row_idx + 1}")
                elif 'subbing' in section_text:
                    current_section = 'subbing'
                    print(f"         ⚠️ Skipping subbing section at row {row_idx + 1}")
                else:
                    current_section = None
                    print(f"         ⚠️ Unknown section: {section_text}")
                
                # Skip section header rows
                continue
            
            # This is a data row (should have 4 cells: player, empty, wins, losses)
            if len(cells) == 4 and current_section in ['captains', 'players']:
                # First cell contains player info
                player_cell = cells[0]
                
                # Look for player links in this cell
                player_links = player_cell.find_all('a', href=True)
                
                for link in player_links:
                    href = link.get('href', '')
                    if '/player.php?print&p=' not in href:
                        continue
                    
                    # Convert print URL to individual player page URL for career stats
                    # Print URL: /player.php?print&p=PLAYER_ID
                    # Individual URL: /player.php?p=PLAYER_ID
                    if 'print&p=' in href:
                        player_id = href.split('p=')[1].split('&')[0] if '&' in href else href.split('p=')[1]
                        href = f"/player.php?p={player_id}"
                        print(f"           🔗 Converted print URL to individual page: {href}")
                    
                    # Get the player name from the link
                    player_name = link.get_text(strip=True)
                    
                    # Get the full cell text to check for captain indicators
                    cell_text = player_cell.get_text(strip=True)
                    
                    # Check for captain indicators in the cell text
                    is_captain = False
                    clean_player_name = player_name
                    
                    if '(C)' in cell_text:
                        is_captain = True
                        print(f"           🎯 CAPTAIN DETECTED: {player_name}")
                    elif '(CC)' in cell_text:
                        is_captain = True
                        print(f"           🎯 CO-CAPTAIN DETECTED: {player_name}")
                    
                    # Extract player ID from href
                    player_id = href.split('p=')[1].split('&')[0] if '&' in href else href.split('p=')[1]
                    
                    # Parse team name to get club and series info
                    club_name = team_name
                    team_series = series_name
                    
                    # Extract club name from team name (e.g., "Tennaqua I" -> "Tennaqua")
                    if ' ' in team_name:
                        parts = team_name.split()
                        if parts[-1] in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'] or parts[-1].isdigit():
                            club_name = ' '.join(parts[:-1])
                    
                    # Enhanced name parsing with compound first name handling
                    first_name, last_name = self._parse_player_name(clean_player_name)
                    
                    # Convert player ID to cnswpl_ format for ETL compatibility
                    cnswpl_player_id = self._convert_to_cnswpl_format(player_id)
                    
                    # Get player stats from individual player page
                    print(f"           📊 Getting current season stats for {player_name}...")
                    stats = self.get_player_stats_from_individual_page(href)
                    
                    # Get career stats from individual player page
                    print(f"           📊 Getting career stats for {player_name}...")
                    career_stats = self.get_career_stats_from_individual_page(href)
                    
                    # Create player record
                    player_data = {
                        'League': 'CNSWPL',
                        'Club': club_name,
                        'Series': team_series,
                        'Team': self._construct_team_name(club_name, team_series),
                        'Player ID': cnswpl_player_id,
                        'First Name': first_name,
                        'Last Name': last_name,
                        'PTI': 'N/A',
                        'Wins': str(stats['Wins']),  # Current season wins
                        'Losses': str(stats['Losses']),  # Current season losses
                        'Win %': stats['Win %'],  # Current season win percentage
                        'Career Wins': career_stats["wins"],  # Career wins from player page
                        'Career Losses': career_stats["losses"],  # Career losses from player page
                        'Career Win %': career_stats["win_percentage"],  # Career win percentage
                        'Captain': 'Yes' if is_captain else '',
                        'Source URL': team_url,
                        'source_league': 'CNSWPL'
                    }
                    
                    players.append(player_data)
                    
                    # Update progress tracking with player stats
                    self._update_progress(
                        player_name=player_name, 
                        players_processed=len(self.all_players) + len(players),
                        player_stats=player_data
                    )
                    
                    print(f"           🎾 Added player: {player_name} (section: {current_section}, Season W: {stats['Wins']}, Season L: {stats['Losses']}, Career W: {career_stats['wins']}, Career L: {career_stats['losses']})")
            
            elif len(cells) != 4:
                # Skip rows that don't have the expected 4-cell structure
                print(f"         ⚠️ Row {row_idx + 1} has {len(cells)} cells, skipping")
        
        print(f"         ✅ Total players extracted: {len(players)}")
        
        return players
    
    def _extract_players_fallback_with_sub_filtering(self, soup, team_name: str, team_url: str, series_name: str, series_url: str) -> List[Dict]:
        """Fallback method that extracts all players but filters out sub players"""
        players = []
        
        # Look for player links in the team roster
        player_links = soup.find_all('a', href=True)
        
        for link in player_links:
            href = link.get('href', '')
            player_name = link.get_text(strip=True)
            
            # Check if this is a player link
            if '/player.php?print&p=' in href and player_name and len(player_name.split()) >= 2:
                # FILTER OUT SUB PLAYERS - this is the key fix
                if '(S↑)' in player_name or '(S)' in player_name:
                    print(f"         ⚠️ Skipping sub player: {player_name}")
                    continue
                
                # Convert print URL to individual player page URL for career stats
                if 'print&p=' in href:
                    player_id = href.split('p=')[1].split('&')[0] if '&' in href else href.split('p=')[1]
                    href = f"/player.php?p={player_id}"
                    print(f"           🔗 Converted print URL to individual page: {href}")
                else:
                    # Extract player ID from href
                    player_id = href.split('p=')[1].split('&')[0] if '&' in href else href.split('p=')[1]
                
                # Check for captain indicators and clean player name
                is_captain = False
                clean_player_name = player_name
                
                if '(C)' in player_name:
                    is_captain = True
                    clean_player_name = player_name.replace('(C)', '').strip()
                    print(f"         🎯 CAPTAIN DETECTED: {player_name} -> {clean_player_name}")
                elif '(CC)' in player_name:
                    is_captain = True
                    clean_player_name = player_name.replace('(CC)', '').strip()
                    print(f"         🎯 CO-CAPTAIN DETECTED: {player_name} -> {clean_player_name}")
                
                # Parse team name to get club and series info
                club_name = team_name
                team_series = series_name
                
                # Extract club name from team name (e.g., "Tennaqua I" -> "Tennaqua")
                if ' ' in team_name:
                    parts = team_name.split()
                    if parts[-1] in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'] or parts[-1].isdigit():
                        club_name = ' '.join(parts[:-1])
                
                # Enhanced name parsing with compound first name handling (use clean name)
                first_name, last_name = self._parse_player_name(clean_player_name)
                
                # Convert player ID to cnswpl_ format for ETL compatibility
                cnswpl_player_id = self._convert_to_cnswpl_format(player_id)
                
                # Get player stats first
                
                # Get player stats from individual player page
                print(f"           📊 Getting current season stats for {player_name}...")
                stats = self.get_player_stats_from_individual_page(href)
                
                # Get career stats from individual player page
                print(f"           📊 Getting career stats for {player_name}...")
                career_stats = self.get_career_stats_from_individual_page(href)
                
                # Create player record
                player_data = {
                    'League': 'CNSWPL',
                    'Club': club_name,
                    'Series': team_series,
                    'Team': self._construct_team_name(club_name, team_series),
                    'Player ID': cnswpl_player_id,
                    'First Name': first_name,
                    'Last Name': last_name,
                    'PTI': 'N/A',
                    'Wins': str(stats['Wins']),  # Current season wins
                    'Losses': str(stats['Losses']),  # Current season losses
                    'Win %': stats['Win %'],  # Current season win percentage
                    'Career Wins': career_stats["wins"],  # Career wins from player page
                    'Career Losses': career_stats["losses"],  # Career losses from player page
                    'Career Win %': career_stats["win_percentage"],  # Career win percentage
                    'Captain': 'Yes' if is_captain else '',
                    'Source URL': team_url,
                    'source_league': 'CNSWPL'
                }
                
                players.append(player_data)
                
                # Update progress tracking with player stats
                self._update_progress(
                    player_name=player_name, 
                    players_processed=len(self.all_players) + len(players),
                    player_stats=player_data
                )
        
        return players
    
    def discover_series_dynamically(self) -> List[Tuple[str, str]]:
        """Try to discover all available series by scraping the main page and navigation"""
        
        try:
            main_url = f"{self.base_url}/"
            html_content = self.get_html_with_fallback(main_url)
            
            if not html_content:
                print("❌ Failed to get main page content")
                return self.get_series_urls()  # Fallback to hardcoded list
            
            soup = BeautifulSoup(html_content, 'html.parser')
            series_links = []
            
            # Look for series links in navigation and content
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for series patterns in the link text
                if any(keyword in text.lower() for keyword in ['series', 'division']):
                    if href.startswith('/'):
                        full_url = f"{self.base_url}{href}"
                    else:
                        full_url = href
                    series_links.append((text, full_url))
                    print(f"   📋 Discovered series: {text}")
            
            # Also look for series patterns in text content
            text_content = soup.get_text()
            
            # Find numeric series patterns (Series 1, Series 2, etc.)
            import re
            numeric_series = re.findall(r'\bSeries\s+(\d+)\b', text_content)
            for series_num in numeric_series:
                series_name = f"Series {series_num}"
                if not any(name == series_name for name, _ in series_links):
                    # Try to construct URL or mark for discovery
                    series_links.append((series_name, "DISCOVER"))
                    print(f"   📋 Discovered numeric series: {series_name}")
            
            # Find letter series patterns (Series A, Series B, etc.)
            letter_series = re.findall(r'\bSeries\s+([A-K])\b', text_content)
            for series_letter in letter_series:
                series_name = f"Series {series_letter}"
                if not any(name == series_name for name, _ in series_links):
                    series_links.append((series_name, "DISCOVER"))
                    print(f"   📋 Discovered letter series: {series_name}")
            
            # Special handling for Series SN - override any existing URL with correct one
            series_name = "Series SN"
            correct_sn_url = f"{self.base_url}/?mod=nndz-TjJiOWtORzkwTlJFb0NVU1NzOD0%3D&did=nndz-WlNlN3lMcz0%3D"
            
            # Remove any existing Series SN entries
            series_links = [(name, url) for name, url in series_links if name != series_name]
            
            # Add Series SN with correct URL
            series_links.append((series_name, correct_sn_url))
            print(f"   📋 Discovered special series: {series_name} (with correct URL)")
            
            if series_links:
                print(f"✅ Dynamically discovered {len(series_links)} series")
                # Sort series for consistent ordering
                series_links.sort(key=lambda x: self._sort_series_key(x[0]))
                return series_links
            else:
                print("⚠️ No series found dynamically, using hardcoded list")
                return self.get_series_urls()
                
        except Exception as e:
            print(f"❌ Error during dynamic discovery: {e}")
            return self.get_series_urls()
    
    def _sort_series_key(self, series_name: str) -> float:
        """Sort series by numeric value or letter position"""
        series_id = series_name.replace('Series ', '').strip()
        
        if series_id.isdigit():
            return float(series_id)
        elif series_id.isalpha() and series_id in 'ABCDEFGHIJK':
            # Convert letters to numbers for sorting (A=1, B=2, etc.)
            return ord(series_id) - ord('A') + 1
        else:
            return float('inf')  # Put unknown series at the end
    
    def scrape_all_series(self):
        """Scrape all series comprehensively with progress tracking and resilience"""
        if self.target_series:
            series_list = ', '.join(self.target_series)
            print(f"🚀 Starting CNSWPL targeted series scraping...")
            print(f"   This will scrape series: {series_list}")
        else:
            print("🚀 Starting CNSWPL comprehensive series roster scraping...")
            print("   This will scrape ALL series (1-17 and A-K) from roster pages")
        print("   to capture every registered player, not just match participants.")
        print("⏱️ This should take about 15-20 minutes to complete")
        
        # Load existing progress if available
        self.load_existing_progress()
        
        # Use enhanced series discovery for better coverage
        print("\n🔍 Discovering available series...")
        discovered_series = self.discover_series_dynamically()
        
        # Fallback to hardcoded URLs if dynamic discovery fails
        if not discovered_series or all(url == "DISCOVER" for _, url in discovered_series):
            print("⚠️ Dynamic discovery incomplete, using hardcoded series URLs")
            series_urls = self.get_series_urls()
        else:
            series_urls = discovered_series
        
        # Filter series based on target_series parameter if specified
        if self.target_series:
            print(f"\n🎯 Filtering to target series: {', '.join(self.target_series)}")
            filtered_series = []
            for series_name, series_url in series_urls:
                # Extract series identifier (number or letter) from series name
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
            url_status = "🔍 DISCOVER" if series_url == "DISCOVER" else "✅ URL READY"
            print(f"   - {series_name} {status} ({url_status})")
        
        # Estimate total players for progress tracking using realistic assumptions
        # Average players per team: 10, Average teams per series: 10
        estimated_players_per_series = 10 * 10  # 10 teams × 10 players = 100 players per series
        self.total_players_expected = len(series_urls) * estimated_players_per_series
        self.total_series_count = len(series_urls)
        
        print(f"\n🚀 Beginning scraping process...")
        print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Force restart: {'Yes' if self.force_restart else 'No'}")
        print(f"🎯 Target series: {self.target_series if self.target_series else 'All series'}")
        print(f"📊 Estimated total players: {self.total_players_expected:,}")
        print(f"{'='*60}")
        
        # Track progress and failures
        successful_series = len(self.completed_series)
        failed_series = []
        
        # Initialize human-like behavior patterns
        import random
        from datetime import datetime
        
        self.attention_span = random.uniform(0.8, 1.2)  # Some people are faster/slower
        self.energy_level = random.uniform(0.9, 1.1)    # Energy affects speed
        
        # Time-of-day effects (people are slower in early morning and late night)
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 9:  # Early morning
            self.energy_level *= 0.8
            print("   🌅 Early morning - moving a bit slower...")
        elif 22 <= current_hour or current_hour <= 2:  # Late night
            self.energy_level *= 0.7
            print("   🌙 Late night - getting tired...")
        elif 14 <= current_hour <= 16:  # Afternoon slump
            self.energy_level *= 0.9
            print("   😴 Afternoon slump - need coffee...")
        
        # Weekend effects (people are more relaxed on weekends)
        if datetime.now().weekday() >= 5:  # Saturday = 5, Sunday = 6
            self.energy_level *= 0.9
            print("   🎉 Weekend mode - taking it easy...")
        
        # Scrape each series with error handling
        for i, (series_name, series_url) in enumerate(series_urls, 1):
            # Skip if already completed
            if series_name in self.completed_series:
                print(f"\n⏭️ Skipping {series_name} (already completed)")
                continue
            
            # Update progress tracking
            self._update_progress(series_name=series_name)
            
            print(f"\n🏆 Processing Series {i}/{len(series_urls)}: {series_name}")
            
            # Handle dynamic discovery for letter series
            if series_url == "DISCOVER":

                discovered_urls = self.discover_series_dynamically()
                # Find the specific series URL
                series_url = None
                for discovered_name, discovered_url in discovered_urls:
                    if discovered_name == series_name:
                        series_url = discovered_url
                        break
                
                if not series_url:
                    print(f"❌ Could not discover URL for {series_name}")
                    failed_series.append(series_name)
                    continue
                else:
                    print(f"✅ Discovered URL for {series_name}: {series_url}")
            
            print(f"🎯 Target: {series_url}")
            
            if i > 1:
                elapsed_time = time.time() - self.start_time  # Calculate elapsed time
                avg_time_per_series = elapsed_time / (i - 1)
                remaining_series = len(series_urls) - i + 1
                eta_minutes = (remaining_series * avg_time_per_series) / 60
                print(f"🔮 ETA: {eta_minutes:.1f} minutes remaining")
                print(f"📈 Running average: {avg_time_per_series/60:.1f} minutes per series")
            
            try:
                series_players = self.extract_players_from_series_page(series_name, series_url)
                if series_players:
                    # Mark series as completed and save individual file BEFORE adding to aggregate
                    self.completed_series.add(series_name)
                    self.save_series_completion(series_name, series_players)
                    
                    # Now add to aggregate list with deduplication
                    # Check for duplicates before adding
                    new_players = []
                    existing_player_ids = {p.get('Player ID', '') for p in self.all_players}
                    duplicates_in_series = 0
                    
                    for player in series_players:
                        player_id = player.get('Player ID', '')
                        if player_id and player_id not in existing_player_ids:
                            new_players.append(player)
                            existing_player_ids.add(player_id)
                        else:
                            duplicates_in_series += 1
                    
                    self.all_players.extend(new_players)
                    successful_series += 1
                    
                    if duplicates_in_series > 0:
                        print(f"✅ {series_name}: {len(new_players)} new players added, {duplicates_in_series} duplicates skipped")
                    else:
                        print(f"✅ {series_name}: {len(new_players)} players")
                    
                    print(f"   📊 Total players so far: {len(self.all_players)}")
                    print(f"   📁 Saved to: data/leagues/CNSWPL/temp/{series_name.replace(' ', '_').lower()}.json")
                    
                    # Show running totals and progress
                    completion_rate = (len(self.completed_series) / len(series_urls)) * 100
                    print(f"   🎯 Overall progress: {completion_rate:.1f}% ({len(self.completed_series)}/{len(series_urls)} series)")
                    print(f"   📈 Running total: {len(self.all_players)} players across all series")
                else:
                    failed_series.append(series_name)
                    print(f"⚠️ {series_name}: No players found")
                    
                    # Still mark as completed (but with empty data) to avoid re-processing
                    self.completed_series.add(series_name)
                    self.save_series_completion(series_name, [])
                    
            except Exception as e:
                print(f"❌ Error processing {series_name}: {e}")
                failed_series.append(series_name)
            
            # Add longer delay between series to avoid anti-bot detection
            if i < len(series_urls):
                # Human-like delay between series with natural variation
                base_delay = random.uniform(4.5, 7.5)  # 4.5-7.5 seconds base
                
                # Add "coffee break" effect (longer delays occasionally)
                if random.random() < 0.2:  # 20% chance
                    coffee_break = random.uniform(3, 8)
                    base_delay += coffee_break
                    print(f"☕ Taking a coffee break... (+{coffee_break:.1f}s)")
                
                # Add natural jitter
                jitter = random.uniform(0.85, 1.15)
                final_delay = round(base_delay * jitter, 1)
                
                print(f"⏳ Waiting {final_delay:.1f}s before next series...")
                time.sleep(final_delay)
        
        # Final completion status
        self.print_completion_summary(series_urls, successful_series, failed_series)
    
    def load_existing_progress(self):
        """Load existing progress and player data if available"""
        if self.force_restart:
            # Clean up any existing progress files
            try:
                progress_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'temp', 'scrape_progress.json')
                partial_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'temp', 'players_comprehensive_partial.json')
                
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                    print("🧹 Removed progress file")
                    
                if os.path.exists(partial_file):
                    os.remove(partial_file)
                    print("🧹 Removed partial results file")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up progress files: {e}")
            
            print("📂 Starting completely fresh - no previous progress loaded")
            print("   💡 This is the DEFAULT behavior - use --continue to resume from progress")
            return
            
        try:
            progress_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'temp', 'scrape_progress.json')
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    self.completed_series = set(progress_data.get('completed_series', []))
                    print(f"📂 Loaded progress: {len(self.completed_series)} series already completed")
                    
                # Load existing player data
                output_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'temp', 'players_comprehensive_partial.json')
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        self.all_players = json.load(f)
                        print(f"📂 Loaded {len(self.all_players)} existing players")
            else:
                print("📂 No previous progress found - starting fresh")
                print("   💡 This is the DEFAULT behavior - use --continue to resume from progress")
        except Exception as e:
            print(f"⚠️ Error loading progress: {e}")
            
    def save_series_completion(self, series_name: str, series_players: List[Dict]):
        """Save individual series file and progress after each completed series"""
        try:
            # Create data/leagues/CNSWPL/temp directory if it doesn't exist
            series_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'temp')
            os.makedirs(series_dir, exist_ok=True)
            
            # Save individual series file
            series_filename = series_name.replace(" ", "_").lower()  # "Series 1" -> "series_1"
            series_file = f"{series_dir}/{series_filename}.json"
            
            with open(series_file, 'w', encoding='utf-8') as f:
                json.dump(series_players, f, indent=2, ensure_ascii=False)
            
            print(f"📁 Saved {series_name} to: {series_file} ({len(series_players)} players)")
            
            # Save progress tracking
            progress_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'temp', 'scrape_progress.json')
            progress_data = {
                'completed_series': list(self.completed_series),
                'last_update': datetime.now().isoformat(),
                'total_players': len(self.all_players),
                'series_files_created': len(self.completed_series)
            }
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
                
            # Save current aggregate player data (only if we have aggregate data)
            output_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'temp', 'players_comprehensive_partial.json')
            if self.all_players:  # Only save if we have aggregate data
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.all_players, f, indent=2, ensure_ascii=False)
                
            print(f"💾 Progress saved: {series_name} complete - individual file + aggregate updated")
        except Exception as e:
            print(f"⚠️ Failed to save series completion: {e}")
    
    def print_completion_summary(self, series_urls: List[Tuple[str, str]], successful_series: int, failed_series: List[str]):
        """Print detailed completion summary"""
        elapsed_time = time.time() - self.start_time
        
        # Final progress update
        self._update_progress(players_processed=len(self.all_players))
        
        print(f"\n🎉 COMPREHENSIVE SCRAPING COMPLETED!")
        print(f"⏱️ Total time: {self._format_time(elapsed_time)}")
        print(f"📊 Successful series: {successful_series}/{len(series_urls)}")
        print(f"📊 Total players found: {len(self.all_players):,}")
        
        # Calculate final performance metrics
        if len(self.all_players) > 0 and elapsed_time > 0:
            players_per_hour = (len(self.all_players) / elapsed_time) * 3600
            avg_time_per_player = elapsed_time / len(self.all_players)
            print(f"🚀 Final processing rate: {players_per_hour:.1f} players/hour")
            print(f"⏱️ Average time per player: {avg_time_per_player:.1f} seconds")
        
        if failed_series:
            print(f"\n⚠️ Failed series ({len(failed_series)}):")
            for series in failed_series:
                print(f"   - {series}")
        
        # Show series breakdown
        series_counts = {}
        for player in self.all_players:
            series = player.get('Series', 'Unknown')
            series_counts[series] = series_counts.get(series, 0) + 1
        
        print(f"\n📈 Players by series:")
        for series, count in sorted(series_counts.items()):
            print(f"   {series}: {count} players")
            
        # Show completion percentage
        completion_rate = (successful_series / len(series_urls)) * 100
        print(f"\n🎯 Completion rate: {completion_rate:.1f}%")
        
        if completion_rate == 100:
            print("🌟 PERFECT! All series successfully scraped!")
        elif completion_rate >= 90:
            print("✨ EXCELLENT! Nearly all series scraped!")
        elif completion_rate >= 75:
            print("👍 GOOD! Most series scraped successfully!")
        else:
            print("⚠️ Some series had issues - consider retry!")
    
    def save_intermediate_results(self):
        """Save intermediate results during long scrape (legacy method)"""
        try:
            output_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'players_intermediate.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_players, f, indent=2, ensure_ascii=False)
            print(f"   💾 Intermediate results saved to {output_file}")
        except Exception as e:
            print(f"   ⚠️ Failed to save intermediate results: {e}")
    
    def save_results(self, is_final=True):
        """Save comprehensive results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if is_final:
            print(f"\n🏁 FINALIZING COMPREHENSIVE SCRAPE RESULTS...")
            
            # Show individual series files created
            series_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'temp')
            if os.path.exists(series_dir):
                series_files = [f for f in os.listdir(series_dir) if f.endswith('.json')]
                print(f"📁 Individual series files created: {len(series_files)}")
                for series_file in sorted(series_files):
                    print(f"   - {series_file}")
            
            # Clean up progress files since we're done
            try:
                progress_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'scrape_progress.json')
                partial_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'players_comprehensive_partial.json')
                
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                    print("🧹 Cleaned up progress tracking file")
                    
                if os.path.exists(partial_file):
                    os.remove(partial_file)
                    print("🧹 Cleaned up partial results file")
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not clean up temporary files: {e}")
        
        # Update main players.json file directly
        main_output_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'players.json')
        
        if os.path.exists(main_output_file):
            # BACKUP EXISTING players.json BEFORE OVERWRITING
            try:
                backup_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'leagues', 'CNSWPL', 'backup')
                os.makedirs(backup_dir, exist_ok=True)
                
                backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"players_backup_{backup_timestamp}.json"
                backup_file = os.path.join(backup_dir, backup_filename)
                
                # Copy existing players.json to backup
                with open(main_output_file, 'r', encoding='utf-8') as source:
                    with open(backup_file, 'w', encoding='utf-8') as dest:
                        dest.write(source.read())
                
                print(f"🛡️ BACKUP CREATED: {backup_file}")
                
                # Get existing player count for backup message
                with open(main_output_file, 'r', encoding='utf-8') as f:
                    existing_players = json.load(f)
                print(f"   📁 Protected {len(existing_players):,} existing players")
                
            except Exception as e:
                print(f"⚠️ WARNING: Failed to create backup: {e}")
                print(f"   ⚠️ Existing players.json may be lost if update proceeds!")
                existing_players = []
            
            print(f"\n📊 COMPARISON WITH EXISTING DATA:")
            print(f"   Existing players.json: {len(existing_players):,} players")
            print(f"   New comprehensive data: {len(self.all_players):,} players")
            print(f"   Difference: {len(self.all_players) - len(existing_players):+,} players")
            
            # Always update with new data (since we're doing comprehensive scrapes)
            with open(main_output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_players, f, indent=2, ensure_ascii=False)
            print(f"✅ UPDATED main file: {main_output_file}")
            print(f"   📈 Replaced with {len(self.all_players)} current season players!")
        else:
            with open(main_output_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_players, f, indent=2, ensure_ascii=False)
            print(f"✅ Created main file: {main_output_file}")
            
        if is_final:
            print(f"\n🎯 FINAL COMPREHENSIVE SCRAPE COMPLETE!")
            print(f"   ✅ All {len(self.completed_series)} series processed")
            print(f"   📁 Individual series files: data/leagues/CNSWPL/temp/")
            print(f"   📁 Final aggregated data: {main_output_file}")
            print(f"   🛡️ Safety backup: data/leagues/CNSWPL/backup/")

    def get_html_with_fallback(self, url: str) -> str:
        """
        Get HTML content with intelligent fallback strategy.
        
        Strategy:
        1. Try stealth browser first (if available)
        2. If stealth fails, retry with exponential backoff
        3. Fall back to curl if stealth continues to fail
        4. Add delays between requests to avoid rate limiting
        """
        # Try stealth browser first if available
        if self.stealth_browser:
            print(f"   🕵️ Using stealth browser for request...")
            
            # Try stealth browser with retries
            for attempt in range(3):  # Max 3 attempts
                try:
                    if attempt > 0:
                        delay = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                        print(f"   ⏳ Retry attempt {attempt + 1}/3, waiting {delay}s...")
                        time.sleep(delay)
                    
                    pace_sleep()  # Adaptive pacing before network request
                    html = self.stealth_browser.get_html(url)
                    
                    # Add early stop optimization if available
                    if SPEED_OPTIMIZATIONS_AVAILABLE and hasattr(self.stealth_browser, 'current_driver') and self.stealth_browser.current_driver:
                        try:
                            from selenium.webdriver.common.by import By
                            # Stop loading after key elements are present (adjust selector as needed)
                            stop_after_selector(self.stealth_browser.current_driver, By.CSS_SELECTOR, "table, .roster, .team", timeout=8)
                        except Exception as e:
                            print(f"   ⚠️ Early stop optimization failed: {e}")
                    
                    if html and len(html) > 100:
                        print(f"   ✅ Stealth browser successful - got {len(html)} characters")
                        # Mark success for adaptive pacing
                        if SPEED_OPTIMIZATIONS_AVAILABLE:
                            try:
                                mark("ok")
                            except Exception:
                                pass
                        return html
                    else:
                        print(f"   ⚠️ Stealth browser returned insufficient data (attempt {attempt + 1})")
                        
                except Exception as e:
                    print(f"   ❌ Stealth browser error (attempt {attempt + 1}): {e}")
                    # Mark failure for adaptive pacing
                    if SPEED_OPTIMIZATIONS_AVAILABLE:
                        try:
                            if "429" in str(e) or "rate limit" in str(e).lower():
                                mark("429")
                            elif "javascript" in str(e).lower() or "js" in str(e).lower():
                                mark("js")
                            else:
                                mark("ok")  # Mark as ok for other errors to avoid over-slowing
                        except Exception:
                            pass
                    continue
            
            print(f"   🔄 Stealth browser failed after 3 attempts, falling back to curl...")
        
        # Fall back to curl with enhanced error handling
        print(f"   📡 Using curl fallback...")
        try:
            import subprocess
            
            # Add a small delay before curl to avoid overwhelming the server
            time.sleep(1)
            
            # Enhanced curl command with better headers, timeout, compression handling, and redirect following
            curl_cmd = [
                'curl', '-s', '-L', '--max-time', '30', '--retry', '2', '--retry-delay', '3',
                '--compressed',  # Handle gzip/deflate compression automatically
                '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                '-H', 'Accept-Language: en-US,en;q=0.5',
                '-H', 'Accept-Encoding: gzip, deflate',
                '-H', 'Connection: keep-alive',
                '-H', 'Upgrade-Insecure-Requests: 1',
                url
            ]
            
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=45)
            
            if result.returncode == 0 and result.stdout and len(result.stdout) > 100:
                print(f"   ✅ Curl successful - got {len(result.stdout)} characters")
                return result.stdout
            else:
                print(f"   ❌ Curl failed: return code {result.returncode}")
                if result.stderr:
                    print(f"      Error: {result.stderr.strip()}")
                return ""
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ Curl timeout after 45 seconds")
            return ""
        except Exception as e:
            print(f"   ❌ Curl error: {e}")
            return ""

    def get_player_stats_from_individual_page(self, player_url: str, max_retries: int = 2) -> Dict[str, any]:
        """
        Get player stats (wins/losses) from individual player page using the same logic as scraper_player_history.py
        
        Args:
            player_url: URL to the individual player page
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with wins, losses, and win percentage
        """
        for attempt in range(max_retries):
            try:
                # Construct full URL if needed
                if not player_url.startswith("http"):
                    full_url = f"{self.base_url}{player_url}"
                else:
                    full_url = player_url
                
                # Use browser-first approach for better reliability during long scrapes
                print(f"   🌐 Using browser automation for reliable data extraction...")
                html_content = self.get_html_with_fallback(full_url)
                
                if not html_content:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        return {"Wins": 0, "Losses": 0, "Win %": "0.0%"}
                
                wins = 0
                losses = 0
                
                # Count wins and losses from HTML content using the same logic as scraper_player_history.py
                if "W" in html_content or "L" in html_content:
                    # Simple pattern matching for wins/losses
                    w_matches = re.findall(r'\bW\b', html_content)
                    l_matches = re.findall(r'\bL\b', html_content)
                    wins = len(w_matches)
                    losses = len(l_matches)
                
                stats = {
                    "Wins": wins,
                    "Losses": losses,
                    "Win %": (
                        f"{(wins/(wins+losses)*100):.1f}%" if wins + losses > 0 else "0.0%"
                    ),
                }
                
                return stats
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ Error getting stats for {player_url}, retrying: {e}")
                    time.sleep(0.5)
                else:
                    print(f"   ❌ Failed to get stats for {player_url} after {max_retries} attempts: {e}")
        
        # Return default stats if all retries failed
        return {"Wins": 0, "Losses": 0, "Win %": "0.0%"}

    def get_career_stats_from_individual_page(self, player_url: str, max_retries: int = 2) -> Dict[str, any]:
        """
        Get career wins and losses from individual player page - RESTORED WORKING VERSION.
        Uses the exact same approach that was working earlier today.
        
        Args:
            player_url: URL to the individual player page
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with career wins, losses, and win_percentage
        """
        for attempt in range(max_retries):
            try:
                print(f"   📊 Getting career stats from individual player page (attempt {attempt + 1})...")
                
                # Construct full URL if needed
                if not player_url.startswith("http"):
                    full_url = f"{self.base_url}{player_url}"
                else:
                    full_url = player_url
                
                # Extract player ID from the player URL
                player_id = self._extract_player_id_from_url(player_url)
                if not player_id:
                    print(f"   ❌ Could not extract player ID from URL: {player_url}")
                    continue
                
                # Build the direct chronological URL (discovered from JavaScript analysis)
                chronological_url = f"{self.base_url}/?print&mod=nndz-Sm5yb2lPdTcxdFJibXc9PQ%3D%3D&all&p={player_id}"
                print(f"   🔗 Chronological URL: {chronological_url}")
                
                # Use existing stealth infrastructure for consistency (maintains proxy/UA)
                html_content = self.get_html_with_fallback(chronological_url)
                
                if not html_content:
                    print(f"   ❌ Failed to get chronological HTML content")
                    continue
                
                print(f"   ✅ Chronological content retrieved: {len(html_content)} characters")
                
                # Extract career stats from div elements (not tables)
                return self._extract_career_from_result_divs(html_content)
                
            except Exception as e:
                print(f"   ❌ Error getting career stats (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    print(f"   ⚠️ All attempts failed for career stats")
                    return {"wins": "0", "losses": "0", "win_percentage": "0.0%"}
        
        return {"wins": "0", "losses": "0", "win_percentage": "0.0%"}
    
    def _extract_player_id_from_url(self, player_url: str) -> str:
        """Extract player ID from player URL."""
        try:
            if 'p=' in player_url:
                player_id = player_url.split('p=')[1].split('&')[0] if '&' in player_url else player_url.split('p=')[1]
                return player_id
            else:
                print(f"   ⚠️ No player ID found in URL: {player_url}")
                return ""
        except Exception as e:
            print(f"   ❌ Error extracting player ID: {e}")
            return ""
    
    def _extract_career_from_result_divs(self, html_content: str) -> Dict[str, str]:
        """
        Extract career stats from result divs using the working chronological URL approach.
        Looks for divs with specific styling that contain W/L results.
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        wins = 0
        losses = 0
        
        # Method 1: Look for result divs with the specific style (width: 57px, text-align: right)
        result_divs = soup.find_all('div', style=re.compile(r'width:\s*57px.*text-align:\s*right'))
        
        for div in result_divs:
            result_text = div.get_text().strip()
            if result_text == 'W':
                wins += 1
            elif result_text == 'L':
                losses += 1
        
        print(f"   📊 Method 1 (Result divs): {wins}W/{losses}L")
        
        # Method 2: If no specific divs found, look for any right-aligned divs with W/L
        if wins == 0 and losses == 0:
            right_aligned_divs = soup.find_all('div', style=re.compile(r'text-align:\s*right'))
            
            for div in right_aligned_divs:
                text = div.get_text().strip()
                if text == 'W':
                    wins += 1
                elif text == 'L':
                    losses += 1
            
            print(f"   📊 Method 2 (Right-aligned): {wins}W/{losses}L")
        
        # Method 3: Conservative fallback if still no results
        if wins == 0 and losses == 0:
            all_w = len(re.findall(r'\bW\b', html_content))
            all_l = len(re.findall(r'\bL\b', html_content))
            
            # Filter out navigation/UI W/L (conservative)
            wins = max(0, all_w - 5)  # Subtract likely navigation
            losses = max(0, all_l - 2)  # Subtract likely navigation
            
            print(f"   📊 Method 3 (Conservative): {wins}W/{losses}L (filtered from {all_w}W/{all_l}L)")
        
        # Calculate win percentage
        if wins + losses > 0:
            win_percentage = f"{(wins / (wins + losses) * 100):.1f}%"
        else:
            win_percentage = "0.0%"
        
        career_stats = {
            "wins": str(wins),
            "losses": str(losses),
            "win_percentage": win_percentage
        }
        
        print(f"   ✅ Career stats extracted: {wins} wins, {losses} losses, {win_percentage}")
        return career_stats
    
    def _has_career_stats_in_html(self, html_content: str) -> bool:
        """
        Quick check if HTML contains career stats without full parsing.
        """
        # Look for common career stats patterns
        career_patterns = [
            r'\b\d+W\b',  # XW pattern
            r'\b\d+L\b',  # XL pattern
            r'Career.*\d+.*\d+',  # Career X Y pattern
            r'Total.*\d+.*\d+',   # Total X Y pattern
        ]
        
        for pattern in career_patterns:
            if re.search(pattern, html_content, re.IGNORECASE):
                return True
        return False
    
    def _extract_career_stats_from_tables(self, html_content: str) -> Dict[str, str]:
        """
        Extract career stats from match history tables - FIXED VERSION from backup.
        Only counts W/L from actual match results in Date/Result tables.
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        total_wins = 0
        total_losses = 0
        
        # Look for match history tables (tables with Date, Match, Line, Result columns)
        tables = soup.find_all('table')
        print(f"   🔍 Found {len(tables)} tables, analyzing for match history...")
        
        for i, table in enumerate(tables):
            table_text = table.get_text()
            
            # Look for tables that contain match history
            if 'Date' in table_text and 'Result' in table_text:
                print(f"   📊 Found match history table {i+1}, analyzing results...")
                
                # Count W's and L's only in the Result column
                rows = table.find_all('tr')
                table_wins = 0
                table_losses = 0
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:  # Date, Match, Line, Result
                        result_cell = cells[-1]  # Last cell should be Result
                        result_text = result_cell.get_text().strip()
                        
                        if result_text == 'W':
                            table_wins += 1
                        elif result_text == 'L':
                            table_losses += 1
                
                if table_wins > 0 or table_losses > 0:
                    total_wins += table_wins
                    total_losses += table_losses
                    print(f"   📊 Table {i+1}: {table_wins}W/{table_losses}L")
        
        # If no match history tables found, try conservative pattern matching
        if total_wins == 0 and total_losses == 0:
            print(f"   🔍 No match history tables found, trying conservative patterns...")
            
            # Look for W/L in any table, but be very conservative
            for i, table in enumerate(tables):
                table_text = table.get_text()
                w_count = len(re.findall(r'\bW\b', table_text))
                l_count = len(re.findall(r'\bL\b', table_text))
                
                # Only count if it looks reasonable (not too many W's from team names like "Wilmette")
                if w_count <= 15 and l_count <= 15 and (w_count > 0 or l_count > 0):
                    total_wins += w_count
                    total_losses += l_count
                    print(f"   📊 Conservative table {i+1}: {w_count}W/{l_count}L")
        
        # Calculate win percentage
        if total_wins + total_losses > 0:
            win_percentage = f"{(total_wins / (total_wins + total_losses) * 100):.1f}%"
        else:
            win_percentage = "0.0%"
        
        career_stats = {
            "wins": str(total_wins),
            "losses": str(total_losses),
            "win_percentage": win_percentage
        }
        
        print(f"   ✅ Career stats extracted: {total_wins} wins, {total_losses} losses, {win_percentage}")
        return career_stats

def main():
    """Main function"""
    import sys
    
    # Show help if requested
    if "--help" in sys.argv or "-h" in sys.argv:
        print("CNSWPL Roster Scraper - Usage:")
        print("  python cnswpl_scrape_players.py                    # Scrape all series (1-17 and A-K) - FRESH START")
        print("  python cnswpl_scrape_players.py --series A,B,C     # Scrape specific series (A, B, C) - FRESH START")
        print("  python cnswpl_scrape_players.py --series=1,2,3     # Scrape specific series (1, 2, 3) - FRESH START")
        print("  python cnswpl_scrape_players.py --continue         # Continue from previous progress")
        print("  python cnswpl_scrape_players.py --resume           # Same as --continue")
        print("  python cnswpl_scrape_players.py --force-restart    # Explicitly force restart (default behavior)")
        print("  python cnswpl_scrape_players.py --fresh            # Same as --force-restart")
        print("  python cnswpl_scrape_players.py --help             # Show this help message")
        print("\nDEFAULT BEHAVIOR:")
        print("  🆕 Always starts fresh (ignores previous progress)")
        print("  🔄 Use --continue or --resume to resume from where you left off")
        print("\nExamples:")
        print("  python cnswpl_scrape_players.py --series A,B,C,D,E,F,G,H,I,J,K  # Scrape all letter series (fresh)")
        print("  python cnswpl_scrape_players.py --series 1,2,3                   # Scrape series 1, 2, 3 (fresh)")
        print("  python cnswpl_scrape_players.py --continue                       # Resume from previous progress")
        return
    
    # Parse command line arguments
    # DEFAULT: Force restart (start fresh) - requires explicit permission to continue
    force_restart = True  # Default to fresh start
    
    # Check for continue/resume flags
    if "--continue" in sys.argv or "--resume" in sys.argv:
        force_restart = False
        print("🔄 CONTINUE MODE: Resuming from previous progress")
    
    # Override with explicit force restart flags
    if "--force-restart" in sys.argv or "--fresh" in sys.argv:
        force_restart = True
        print("🔄 FORCE RESTART: Ignoring any previous progress")
    
    target_series = None
    
    # Check for series specification
    for i, arg in enumerate(sys.argv):
        if arg == "--series" and i + 1 < len(sys.argv):
            target_series = sys.argv[i + 1].split(',')
            # Remove the --series argument and its value
            sys.argv.pop(i)
            sys.argv.pop(i)
            break
        elif arg.startswith("--series="):
            target_series = arg.split("=", 1)[1].split(',')
            sys.argv.remove(arg)
            break
    
    # Validate target_series if specified
    if target_series:
        valid_series = [str(i) for i in range(1, 18)] + list('ABCDEFGHIJK') + ['SN']
        invalid_series = [s for s in target_series if s not in valid_series]
        if invalid_series:
            print(f"❌ Error: Invalid series specified: {', '.join(invalid_series)}")
            print(f"   Valid series are: 1-17, A-K, and SN")
            return
        print(f"✅ Valid series specified: {', '.join(target_series)}")
    
    print("============================================================")
    if target_series:
        series_list = ', '.join(target_series)
        print(f"🏆 CNSWPL TARGETED SERIES SCRAPER")
        print(f"   Scraping specific series: {series_list}")
    else:
        print("🏆 COMPREHENSIVE CNSWPL ROSTER SCRAPER")
        print("   Scraping ALL series (1-17 and A-K) from roster pages")
    print("   to capture every registered player")
    
    if force_restart:
        print("   🆕 FRESH START: Ignoring any previous progress (default behavior)")
    else:
        print("   🔄 CONTINUE MODE: Resuming from previous progress")
    print("============================================================")
    
    scraper = CNSWPLRosterScraper(force_restart=force_restart, target_series=target_series)
    
    try:
        scraper.scrape_all_series()
        
        # Check if scrape was complete
        if target_series:
            # For targeted scraping, check if all requested series were completed
            expected_series = set([f"Series {s}" for s in target_series])
            is_complete = scraper.completed_series == expected_series
            
            if is_complete:
                print(f"\n🌟 TARGETED SCRAPE COMPLETE!")
                print(f"   All requested series ({', '.join(target_series)}) successfully processed")
                scraper.save_results(is_final=True)
            else:
                missing_series = expected_series - scraper.completed_series
                print(f"\n⚠️ PARTIAL TARGETED SCRAPE COMPLETED")
                print(f"   Missing series: {', '.join(sorted(missing_series))}")
                scraper.save_results(is_final=False)
        else:
            # For comprehensive scraping, check all series
            expected_series = set([f"Series {i}" for i in range(1, 18)] + [f"Series {letter}" for letter in 'ABCDEFGHIJK'])
            is_complete = scraper.completed_series == expected_series
            
            if is_complete:
                print("\n🌟 COMPLETE SCRAPE DETECTED!")
                print("   All series (1-17 and A-K) successfully processed")
                scraper.save_results(is_final=True)
            else:
                missing_series = expected_series - scraper.completed_series
                print(f"\n⚠️ PARTIAL SCRAPE COMPLETED")
                print(f"   Missing series: {', '.join(sorted(missing_series))}")
                scraper.save_results(is_final=False)
        
        if target_series:
            print(f"\n🎉 TARGETED SCRAPING SESSION COMPLETED!")
            print(f"   Series {', '.join(target_series)} data saved and ready for database import")
        else:
            print("\n🎉 COMPREHENSIVE SCRAPING SESSION COMPLETED!")
            print("   All series data saved and ready for database import")
        
    except KeyboardInterrupt:
        print("\n⏸️ Scraping interrupted by user")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results(is_final=False)
            print("   You can resume by running the scraper again")
    except Exception as e:
        print(f"\n❌ Error during comprehensive scraping: {e}")
        if scraper.all_players:
            print("💾 Saving partial results...")
            scraper.save_results(is_final=False)
    finally:
        # Clean up rally context (driver reuse) for efficiency
        if hasattr(scraper, 'rally_context') and scraper.rally_context:
            try:
                scraper.rally_context.stop_driver()
                print("✅ Rally context cleaned up")
            except:
                pass

if __name__ == "__main__":
    main()
