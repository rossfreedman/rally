#!/usr/bin/env python3
"""
Enhanced Master Scraper for Rally Tennis
Unified intelligent scraper with comprehensive stealth measures, smart request pacing,
IP rotation, retry logic, CAPTCHA detection, and session fingerprinting.
"""

import argparse
import json
import logging
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# Import stealth components
from data.etl.scrapers.stealth_browser import create_stealth_browser, DetectionType, SessionMetrics
from data.etl.scrapers.proxy_manager import get_proxy_rotator
from data.etl.utils.json_backup_manager import backup_before_scraping, create_backup_manager

# Import database components
from database_config import get_db_engine
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

Base = declarative_base()

# Admin phone number for notifications
ADMIN_PHONE = "17732138911"

def send_scraper_notification(message, is_failure=False, step_name=None, error_details=None, duration=None, metrics=None):
    """Send SMS notification to admin with scraper details (mirrors import notifications)"""
    try:
        # Try importing the notification service
        from app.services.notifications_service import send_sms
        
        current_time = datetime.now().strftime('%m-%d-%y @ %I:%M:%S %p')
        
        if is_failure:
            # Failure message with error details
            enhanced_message = f"Rally Scraper:\n"
            enhanced_message += f"Step: {step_name or 'Unknown'}\n"
            enhanced_message += f"Time: {current_time}\n"
            enhanced_message += f"Status: ❌ FAILURE\n"
            if error_details:
                # Truncate long error messages
                truncated_error = error_details[:150] + "..." if len(error_details) > 150 else error_details
                enhanced_message += f"Error: {truncated_error}"
        else:
            # Success message with clean format
            enhanced_message = f"Rally Scraper:\n"
            enhanced_message += f"Activity: {message}\n"
            if duration:
                # Format duration without seconds
                if hasattr(duration, 'total_seconds'):
                    total_seconds = duration.total_seconds()
                    if total_seconds < 60:
                        formatted_duration = f"{int(total_seconds)}s"
                    else:
                        minutes = int(total_seconds // 60)
                        seconds = int(total_seconds % 60)
                        formatted_duration = f"{minutes}m {seconds}s"
                else:
                    formatted_duration = str(duration)
                enhanced_message += f"Duration: {formatted_duration}\n"
            enhanced_message += f"Time: {current_time}\n"
            # Special formatting for final scraper completion
            if "SCRAPER COMPLETE" in message:
                enhanced_message += f"FINAL SCRAPER STATUS: ✅"
            else:
                enhanced_message += f"Status: ✅"
            if metrics:
                enhanced_message += "\nMetrics:"
                for k, v in metrics.items():
                    enhanced_message += f"\n- {k}: {v}"
        
        send_sms(ADMIN_PHONE, enhanced_message)
        logger.info(f"📱 SMS sent to admin: {enhanced_message[:100]}...")
    except Exception as e:
        logger.warning(f"📱 SMS notification failed: {e}")

@dataclass
class StealthConfig:
    """Configuration for stealth behavior."""
    fast_mode: bool = False
    verbose: bool = False
    environment: str = "production"
    max_retries: int = 3
    min_delay: float = 2.0
    max_delay: float = 6.0
    timeout: int = 30
    requests_per_proxy: int = 30
    session_duration: int = 600
    # Delta mode configuration
    delta_mode: bool = False
    delta_start_date: Optional[str] = None
    delta_end_date: Optional[str] = None
    delta_config_file: str = "data/etl/scrapers/delta_scraper_config.json"

class IncrementalScrapingManager:
    """Manages intelligent incremental scraping using latest match detection"""
    
    def __init__(self):
        self.match_scores_file = "match_scores.json"
        self.backup_file = "match_scores_backup.json"
        self.overlap_days = 7  # Number of days to overlap for catching updates
    
    def load_existing_matches(self) -> Tuple[List[Dict], Set[str], Dict[str, Dict]]:
        """
        Load existing match scores from JSON file.
        
        Returns:
            Tuple of (all_matches, existing_ids, id_to_match_lookup)
        """
        if not os.path.exists(self.match_scores_file):
            logger.info(f"📄 No existing {self.match_scores_file} found, starting fresh")
            return [], set(), {}
        
        try:
            with open(self.match_scores_file, 'r') as f:
                existing_matches = json.load(f)
            
            existing_ids = set()
            id_to_match = {}
            
            for match in existing_matches:
                if 'id' in match:
                    match_id = str(match['id'])
                    existing_ids.add(match_id)
                    id_to_match[match_id] = match
            
            logger.info(f"📋 Loaded {len(existing_matches)} existing matches, {len(existing_ids)} unique IDs")
            return existing_matches, existing_ids, id_to_match
            
        except Exception as e:
            logger.error(f"❌ Error loading {self.match_scores_file}: {e}")
            return [], set(), {}
    
    def get_latest_match_date_by_league(self) -> Dict[str, Optional[datetime]]:
        """
        Find the most recent match date for each league separately.
        
        Returns:
            Dictionary mapping league names to their latest match dates
        """
        league_configs = {
            "APTA_CHICAGO": {
                "file": "data/leagues/APTA_CHICAGO/match_history.json",
                "site_id": "57043"
            },
            "NSTF": {
                "file": "data/leagues/NSTF/match_history.json", 
                "site_id": "57045"
            },


        }
        
        league_dates = {}
        
        for league_name, config in league_configs.items():
            latest_date = None
            file_path = config["file"]
            
            if os.path.exists(file_path):
                try:
                    logger.info(f"📋 Analyzing {league_name}: {file_path}...")
                    with open(file_path, 'r') as f:
                        league_matches = json.load(f)
                    
                    file_matches = len(league_matches)
                    logger.info(f"   📊 Found {file_matches:,} matches")
                    
                    # Sample recent matches for performance (last 1000 matches)
                    sample_matches = league_matches[-1000:] if len(league_matches) > 1000 else league_matches
                    
                    for match in sample_matches:
                        date_field = match.get('Date') or match.get('date')
                        if date_field:
                            try:
                                match_date = None
                                
                                # Try DD-MMM-YY format first (e.g., "11-Feb-25")
                                if '-' in date_field and len(date_field.split('-')) == 3:
                                    try:
                                        match_date = datetime.strptime(date_field, '%d-%b-%y')
                                    except ValueError:
                                        pass
                                
                                # Try YYYY-MM-DD format
                                if not match_date:
                                    try:
                                        match_date = datetime.strptime(date_field, '%Y-%m-%d')
                                    except ValueError:
                                        pass
                                
                                # Try MM/DD/YYYY format
                                if not match_date:
                                    try:
                                        match_date = datetime.strptime(date_field, '%m/%d/%Y')
                                    except ValueError:
                                        pass
                                
                                if match_date and (latest_date is None or match_date > latest_date):
                                    latest_date = match_date
                                    
                            except Exception:
                                continue
                                
                except Exception as e:
                    logger.warning(f"⚠️ Error reading {file_path}: {e}")
                    continue
            else:
                logger.info(f"📄 No file found for {league_name}: {file_path}")
            
            league_dates[league_name] = latest_date
            if latest_date:
                logger.info(f"   📅 Latest {league_name} match: {latest_date.strftime('%Y-%m-%d')}")
            else:
                logger.info(f"   📅 No valid dates found for {league_name}")
        
        return league_dates
    
    def scrape_latest_match_dates_by_league(self, stealth_config: Optional[StealthConfig] = None) -> Dict[str, Optional[datetime]]:
        """
        Get the latest match date for each league from their TennisScores standings pages.
        Uses lightweight direct HTTP requests to check recent match activity per league.
        
        Args:
            stealth_config: Optional stealth configuration
            
        Returns:
            Dictionary mapping league names to their latest site dates
        """
        logger.info("🔍 Checking latest match dates from TennisScores by league...")
        
        league_configs = {
            "APTA_CHICAGO": {
                "url": "https://www.tenniscores.com/league-standings/57043",
                "name": "APTA Chicago"
            },
            "NSTF": {
                "url": "https://www.tenniscores.com/league-standings/57045", 
                "name": "NSTF"
            },


        }
        
        league_site_dates = {}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for league_name, config in league_configs.items():
            latest_match_date = None
            url = config["url"]
            
            try:
                logger.info(f"🌐 Checking {league_name}: {url}")
                
                import requests
                import re
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Look for various date patterns in the page content
                    date_patterns = [
                        r'(\d{4}-\d{2}-\d{2})',           # 2025-07-31
                        r'(\d{1,2}/\d{1,2}/\d{4})',       # 7/31/2025 or 07/31/2025
                        r'(\d{1,2}-\d{1,2}-\d{4})',       # 7-31-2025 or 07-31-2025
                        r'(\d{1,2}/\d{1,2}/\d{2})',       # 7/31/25 or 07/31/25
                    ]
                    
                    for pattern in date_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            try:
                                # Parse different date formats
                                if '-' in match and len(match.split('-')[0]) == 4:  # YYYY-MM-DD
                                    date_obj = datetime.strptime(match, '%Y-%m-%d')
                                elif '/' in match and len(match.split('/')[2]) == 4:  # MM/DD/YYYY
                                    date_obj = datetime.strptime(match, '%m/%d/%Y')
                                elif '/' in match and len(match.split('/')[2]) == 2:  # MM/DD/YY
                                    date_obj = datetime.strptime(match, '%m/%d/%y')
                                elif '-' in match:  # MM-DD-YYYY
                                    date_obj = datetime.strptime(match, '%m-%d-%Y')
                                else:
                                    continue
                                
                                # Only consider reasonable dates (within last 90 days, not future)
                                today = datetime.now()
                                if (today - timedelta(days=90)) <= date_obj <= today:
                                    if latest_match_date is None or date_obj > latest_match_date:
                                        latest_match_date = date_obj
                            except ValueError:
                                continue
                else:
                    logger.warning(f"⚠️ Failed to fetch {league_name}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error checking {league_name}: {str(e)}")
            
            # Store result for this league
            if latest_match_date:
                logger.info(f"   ✅ Latest {league_name} site date: {latest_match_date.strftime('%Y-%m-%d')}")
            else:
                logger.warning(f"   ⚠️ No recent dates found for {league_name}")
                # Use fallback for this league
                today = datetime.now()
                latest_match_date = today - timedelta(days=3)
                logger.info(f"   📅 Using fallback for {league_name}: {latest_match_date.strftime('%Y-%m-%d')}")
            
            league_site_dates[league_name] = latest_match_date
        
        return league_site_dates
    
    def determine_league_scrape_decisions(self, existing_matches: List[Dict], stealth_config: Optional[StealthConfig] = None) -> Dict[str, Dict]:
        """
        Determine scraping decisions for each league separately using intelligent delta analysis.
        
        Args:
            existing_matches: List of existing match dictionaries (legacy parameter, ignored)
            stealth_config: Optional stealth configuration
            
        Returns:
            Dictionary mapping league names to their scraping decisions
        """
        logger.info("🧠 League-Specific Intelligent Delta Analysis Starting...")
        logger.info("=" * 70)
        
        # Step 1: Get latest match dates by league from local files
        logger.info("📋 STEP 1: Analyzing league-specific match history files...")
        local_dates_by_league = self.get_latest_match_date_by_league()
        
        # Step 2: Get latest match dates by league from site
        logger.info("🌐 STEP 2: Checking latest match dates on TennisScores by league...")
        site_dates_by_league = self.scrape_latest_match_dates_by_league(stealth_config)
        
        # Step 3: Make decisions for each league
        league_decisions = {}
        
        logger.info("🔍 STEP 3: League-by-League Analysis:")
        logger.info("=" * 70)
        
        # Determine which leagues to analyze based on specified league
        leagues_to_analyze = ["APTA_CHICAGO", "NSTF"]  # Default: analyze all
        
        # If a specific league is provided, only analyze that one
        if hasattr(self, 'target_league') and self.target_league:
            leagues_to_analyze = [self.target_league.upper()]
            logger.info(f"🎯 Analyzing only specified league: {self.target_league}")
        
        for league_name in leagues_to_analyze:
            local_date = local_dates_by_league.get(league_name)
            site_date = site_dates_by_league.get(league_name)
            
            logger.info(f"🏆 {league_name} Analysis:")
            logger.info("-" * 50)
            
            # Display current status for this league
            if local_date:
                logger.info(f"   📅 LOCAL FILE:  {local_date.strftime('%Y-%m-%d')}")
            else:
                logger.info(f"   📅 LOCAL FILE:  NO MATCHES FOUND")
                
            if site_date:
                logger.info(f"   🌐 WEBSITE:     {site_date.strftime('%Y-%m-%d')}")
            else:
                logger.info(f"   🌐 WEBSITE:     DETECTION FAILED")
            
            # Decision logic for this league
            decision = {
                "league": league_name,
                "local_date": local_date,
                "site_date": site_date,
                "should_scrape": False,
                "start_date": None,
                "end_date": None,
                "reason": "Unknown"
            }
            
            if not site_date:
                # Site detection failed - use fallback window
                logger.info("   ⚠️ DECISION: Site detection failed - using fallback window")
                today = datetime.now()
                decision.update({
                    "should_scrape": True,
                    "start_date": (today - timedelta(days=14)).strftime('%Y-%m-%d'),
                    "end_date": today.strftime('%Y-%m-%d'),
                    "reason": "Site detection failed - fallback window"
                })
                logger.info(f"   📅 Fallback range: {decision['start_date']} to {decision['end_date']}")
                
            elif not local_date:
                # No local data - perform initial scrape
                logger.info("   ✅ DECISION: No local data - performing initial scrape")
                decision.update({
                    "should_scrape": True,
                    "start_date": (site_date - timedelta(days=30)).strftime('%Y-%m-%d'),
                    "end_date": site_date.strftime('%Y-%m-%d'),
                    "reason": "No local data - initial scrape"
                })
                logger.info(f"   📅 Initial range: {decision['start_date']} to {decision['end_date']}")
                
            elif site_date <= local_date:
                # Up to date
                logger.info("   ✅ DECISION: Local data is up-to-date - SKIPPING")
                logger.info(f"   🧠 Reasoning: Site ({site_date.strftime('%Y-%m-%d')}) ≤ Local ({local_date.strftime('%Y-%m-%d')})")
                decision.update({
                    "should_scrape": False,
                    "reason": f"Up-to-date (site: {site_date.strftime('%Y-%m-%d')}, local: {local_date.strftime('%Y-%m-%d')})"
                })
                
            else:
                # New matches detected
                scrape_start_date = local_date - timedelta(days=self.overlap_days)
                scrape_end_date = site_date
                days_diff = (site_date - local_date).days
                
                logger.info("   🎯 DECISION: New matches detected - PROCEEDING WITH SCRAPE")
                logger.info(f"   🧠 Reasoning: Site ({site_date.strftime('%Y-%m-%d')}) > Local ({local_date.strftime('%Y-%m-%d')})")
                logger.info(f"   📈 Site is {days_diff} days ahead of local data")
                logger.info(f"   📅 Scrape range: {scrape_start_date.strftime('%Y-%m-%d')} to {scrape_end_date.strftime('%Y-%m-%d')}")
                logger.info(f"   🔄 Including {self.overlap_days}-day overlap to catch updates")
                
                decision.update({
                    "should_scrape": True,
                    "start_date": scrape_start_date.strftime('%Y-%m-%d'),
                    "end_date": scrape_end_date.strftime('%Y-%m-%d'),
                    "reason": f"New matches detected ({days_diff} days behind)"
                })
            
            league_decisions[league_name] = decision
            logger.info("")  # Add spacing between leagues
        
        # Summary
        scrape_count = sum(1 for d in league_decisions.values() if d["should_scrape"])
        logger.info("📊 SUMMARY:")
        logger.info("=" * 70)
        logger.info(f"   Total leagues analyzed: {len(league_decisions)}")
        logger.info(f"   Leagues requiring scraping: {scrape_count}")
        logger.info(f"   Leagues up-to-date: {len(league_decisions) - scrape_count}")
        
        return league_decisions
    
    def scrape_matches_between(self, start_date: str, end_date: str, stealth_config: Optional[StealthConfig] = None) -> List[Dict]:
        """
        Scrape matches between the specified date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            stealth_config: Optional stealth configuration
            
        Returns:
            List of match dictionaries
        """
        logger.info(f"🔍 Scraping matches between {start_date} and {end_date}...")
        
        try:
            # Build command for delta scraping
            cmd = [
                "python3", "data/etl/scrapers/scrape_match_scores.py",
                "all",  # Scrape all leagues
                "--delta-mode",
                "--start-date", start_date,
                "--end-date", end_date
            ]
            
            # Add stealth config parameters if available
            if stealth_config:
                if stealth_config.fast_mode:
                    cmd.append("--fast")
                if stealth_config.verbose:
                    cmd.append("--verbose")
            
            logger.info(f"🚀 Running: {' '.join(cmd)}")
            
            # Run the delta scraper
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0:
                logger.info(f"✅ Scraping completed successfully")
                logger.info(f"📥 Output preview: {result.stdout[:200]}...")
                
                # The scraper might have updated the file, but we need to return just the new matches
                # For now, we'll return an empty list and let the calling method handle file reading
                # This maintains compatibility with existing merge logic
                return []
            else:
                logger.error(f"❌ Scraping failed: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}")
            return []
    
    def get_scrape_window(self) -> str:
        """
        Calculate the start date for intelligent delta analysis window.
        
        Returns:
            Start date as YYYY-MM-DD string
        """
        today = datetime.today()
        start_date = today - timedelta(days=14)  # Analysis window for strategy determination
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        logger.info(f"📅 Analysis window: {start_date_str} to {today.strftime('%Y-%m-%d')} (for strategy determination)")
        return start_date_str
    
    def scrape_matches_since(self, start_date: str, stealth_config: Optional[StealthConfig] = None) -> List[Dict]:
        """
        Scrape matches since the given start date using delta mode.
        
        Args:
            start_date: Date string in YYYY-MM-DD format
            stealth_config: Optional stealth configuration for delta mode
            
        Returns:
            List of match dictionaries with 'id', 'date', 'score' fields
        """
        logger.info(f"🔍 Scraping matches since {start_date}...")
        
        # Calculate end date (today)
        end_date = datetime.today().strftime('%Y-%m-%d')
        
        try:
            # Build command for delta scraping
            cmd = [
                "python3", "data/etl/scrapers/scrape_match_scores.py",
                "all",  # Scrape all leagues
                "--delta-mode",
                "--start-date", start_date,
                "--end-date", end_date
            ]
            
            # Add stealth config parameters if available
            if stealth_config:
                if stealth_config.fast_mode:
                    cmd.append("--fast")
                if stealth_config.verbose:
                    cmd.append("--verbose")
            
            logger.info(f"🚀 Running delta scraper: {' '.join(cmd)}")
            
            # Run the delta scraper
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0:
                logger.info(f"✅ Delta scraping completed successfully")
                logger.info(f"📥 Output: {result.stdout[:200]}...")
                
                # Load the scraped results from the output file
                # The scraper should have updated the match_scores.json file
                if os.path.exists(self.match_scores_file):
                    with open(self.match_scores_file, 'r') as f:
                        scraped_matches = json.load(f)
                    logger.info(f"📥 Loaded {len(scraped_matches)} matches from scraper output")
                    return scraped_matches
                else:
                    logger.warning(f"⚠️ No output file found after scraping")
                    return []
            else:
                logger.error(f"❌ Delta scraping failed: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error during delta scraping: {e}")
            return []
    
    def compare_and_merge_matches(self, existing_matches: List[Dict], existing_ids: Set[str], 
                                id_to_match: Dict[str, Dict], scraped_matches: List[Dict]) -> Tuple[List[Dict], int, int]:
        """
        Compare scraped matches with existing ones and merge updates.
        
        Returns:
            Tuple of (updated_matches, new_count, updated_count)
        """
        new_count = 0
        updated_count = 0
        
        # Create a working copy of existing matches
        updated_matches = existing_matches.copy()
        
        for scraped_match in scraped_matches:
            if 'id' not in scraped_match:
                logger.warning("⚠️ Scraped match missing 'id' field, skipping")
                continue
            
            match_id = str(scraped_match['id'])
            
            if match_id not in existing_ids:
                # New match - append it
                updated_matches.append(scraped_match)
                existing_ids.add(match_id)
                new_count += 1
                logger.debug(f"➕ New match: {match_id}")
            
            else:
                # Existing match - check if score changed
                existing_match = id_to_match[match_id]
                existing_score = existing_match.get('score', '')
                new_score = scraped_match.get('score', '')
                
                if existing_score != new_score:
                    # Score changed - update the match
                    for i, match in enumerate(updated_matches):
                        if str(match.get('id')) == match_id:
                            updated_matches[i] = scraped_match
                            updated_count += 1
                            logger.debug(f"🔄 Updated match: {match_id} (score changed)")
                            break
                else:
                    # Score same - skip
                    logger.debug(f"✅ Match unchanged: {match_id}")
        
        return updated_matches, new_count, updated_count
    
    def deduplicate_matches(self, matches: List[Dict]) -> List[Dict]:
        """
        Deduplicate matches by ID, keeping the most recent version.
        
        Args:
            matches: List of match dictionaries
            
        Returns:
            Deduplicated list of matches
        """
        seen_ids = set()
        deduplicated = []
        
        # Process in reverse to keep the most recent version of duplicates
        for match in reversed(matches):
            match_id = str(match.get('id', ''))
            if match_id and match_id not in seen_ids:
                seen_ids.add(match_id)
                deduplicated.append(match)
        
        # Reverse back to original order
        deduplicated.reverse()
        
        logger.info(f"🔧 Deduplicated: {len(matches)} → {len(deduplicated)} matches")
        return deduplicated
    
    def save_matches(self, matches: List[Dict]) -> bool:
        """
        Save matches to JSON file with backup.
        
        Args:
            matches: List of match dictionaries to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup if file exists
            if os.path.exists(self.match_scores_file):
                import shutil
                shutil.copy2(self.match_scores_file, self.backup_file)
                logger.info(f"💾 Backup created: {self.backup_file}")
            
            # Write updated matches
            with open(self.match_scores_file, 'w') as f:
                json.dump(matches, f, indent=2)
            
            logger.info(f"💾 Saved {len(matches)} matches to {self.match_scores_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving matches: {e}")
            return False
    
    def run_incremental_scrape(self, stealth_config: Optional[StealthConfig] = None) -> Dict[str, Any]:
        """
        Run league-specific intelligent incremental scraping process.
        
        Args:
            stealth_config: Optional stealth configuration for delta mode
        
        Returns:
            Dictionary with scraping results and statistics
        """
        logger.info("🚀 Starting League-Specific Intelligent Incremental Scraping")
        logger.info("🧠 Using per-league match detection for optimal efficiency")
        
        # Step 1: Load existing matches (for legacy compatibility)
        existing_matches, existing_ids, id_to_match = self.load_existing_matches()
        
        # Step 2: Get league-specific scraping decisions
        league_decisions = self.determine_league_scrape_decisions(existing_matches, stealth_config)
        
        # Check if any leagues need scraping
        leagues_to_scrape = {name: decision for name, decision in league_decisions.items() if decision["should_scrape"]}
        
        if not leagues_to_scrape:
            # No scraping needed for any league - return current state
            logger.info("🎯 League analysis: No new matches to scrape across all leagues")
            return {
                "success": True,
                "existing_matches": len(existing_matches),
                "scraped_matches": 0,
                "new_matches": 0,
                "updated_matches": 0,
                "final_matches": len(existing_matches),
                "leagues_analyzed": len(league_decisions),
                "leagues_scraped": 0,
                "leagues_skipped": len(league_decisions),
                "scraping_skipped": True,
                "reason": "All leagues up-to-date"
            }
        
        # Step 3: Scrape each league that needs updating
        logger.info(f"🎯 Scraping {len(leagues_to_scrape)} league(s) that need updates...")
        
        total_before_scraping = len(existing_matches)
        scraped_leagues = []
        
        for league_name, decision in leagues_to_scrape.items():
            logger.info(f"🏆 Scraping {league_name}: {decision['start_date']} to {decision['end_date']}")
            
            try:
                # Scrape this specific league
                scraped_matches = self.scrape_league_matches(
                    league_name, 
                    decision['start_date'], 
                    decision['end_date'], 
                    stealth_config
                )
                
                scraped_leagues.append({
                    "league": league_name,
                    "start_date": decision['start_date'],
                    "end_date": decision['end_date'],
                    "reason": decision['reason'],
                    "success": True
                })
                
                logger.info(f"   ✅ {league_name} scraping completed")
                
            except Exception as e:
                logger.error(f"   ❌ {league_name} scraping failed: {e}")
                scraped_leagues.append({
                    "league": league_name,
                    "start_date": decision['start_date'],
                    "end_date": decision['end_date'],
                    "reason": decision['reason'],
                    "success": False,
                    "error": str(e)
                })
        
        # Step 4: Load fresh data after scraping to see total impact
        fresh_matches, fresh_ids, fresh_id_to_match = self.load_existing_matches()
        
        # Step 5: Calculate aggregate results
        total_new_matches = len(fresh_matches) - total_before_scraping
        total_updated_matches = 0  # Estimate based on overlap across all leagues
        
        # Calculate estimated updates across all scraped leagues
        for league_name, decision in leagues_to_scrape.items():
            if decision["should_scrape"]:
                # Estimate updates for this league's overlap period
                try:
                    overlap_start = datetime.strptime(decision['start_date'], '%Y-%m-%d')
                    overlap_end = datetime.strptime(decision['end_date'], '%Y-%m-%d')
                    overlap_matches = [m for m in existing_matches 
                                     if 'date' in m and overlap_start <= datetime.strptime(m['date'], '%Y-%m-%d') <= overlap_end]
                    total_updated_matches += len(overlap_matches)
                except Exception:
                    continue
        
        # Step 6: Create backup of consolidated results
        if os.path.exists(self.match_scores_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"match_scores_backup_{timestamp}.json"
            
            try:
                import shutil
                shutil.copy2(self.match_scores_file, backup_filename)
                logger.info(f"💾 Timestamped backup created: {backup_filename}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to create timestamped backup: {e}")
        
        # Results
        successful_leagues = sum(1 for sl in scraped_leagues if sl["success"])
        results = {
            "success": True,
            "existing_matches": total_before_scraping,
            "scraped_matches": 0,  # Individual scrape counts not tracked
            "new_matches": max(0, total_new_matches),
            "updated_matches": total_updated_matches,
            "final_matches": len(fresh_matches),
            "leagues_analyzed": len(league_decisions),
            "leagues_scraped": successful_leagues,
            "leagues_skipped": len(league_decisions) - len(leagues_to_scrape),
            "scraped_league_details": scraped_leagues,
            "scraping_skipped": False,
            "league_specific_mode": True
        }
        
        # Log comprehensive summary
        logger.info("📊 League-Specific Incremental Scraping Results:")
        logger.info("=" * 60)
        logger.info(f"   🏆 Leagues analyzed: {len(league_decisions)}")
        logger.info(f"   🏆 Leagues scraped: {successful_leagues}")
        logger.info(f"   🏆 Leagues skipped: {len(league_decisions) - len(leagues_to_scrape)}")
        logger.info(f"   📋 Total matches before: {total_before_scraping:,}")
        logger.info(f"   📋 Total matches after: {len(fresh_matches):,}")
        logger.info(f"   ➕ Estimated new matches: {max(0, total_new_matches):,}")
        logger.info(f"   🔄 Potential updates: {total_updated_matches:,}")
        
        for sl in scraped_leagues:
            status = "✅" if sl["success"] else "❌"
            logger.info(f"   {status} {sl['league']}: {sl['start_date']} to {sl['end_date']}")
        
        logger.info("=" * 60)
        
        return results
    
    def scrape_league_matches(self, league_name: str, start_date: str, end_date: str, stealth_config: Optional[StealthConfig] = None) -> List[Dict]:
        """
        Scrape matches for a specific league within the given date range.
        
        Args:
            league_name: Name of the league to scrape (e.g., "APTA_CHICAGO")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            stealth_config: Optional stealth configuration
        
        Returns:
            List of scraped match dictionaries
        """
        try:
            # Map directory names to scraper league arguments
            league_mapping = {
                "APTA_CHICAGO": "aptachicago",
                "NSTF": "nstf", 


            }
            
            scraper_league_name = league_mapping.get(league_name, league_name.lower())
            
            # Build command for league-specific scraping
            cmd = [
                "python3", "data/etl/scrapers/scrape_match_scores.py",
                scraper_league_name,
                "--delta-mode",
                "--start-date", start_date,
                "--end-date", end_date
            ]
            
            # Add stealth options
            if stealth_config:
                if stealth_config.fast_mode:
                    cmd.append("--fast")
                # Note: scraper is verbose by default, use --quiet to disable
                if not stealth_config.verbose:
                    cmd.append("--quiet")
            
            logger.debug(f"🚀 Running league scraper: {' '.join(cmd)}")
            logger.info(f"   🎯 Command: {scraper_league_name} from {start_date} to {end_date}")
            
            # Run the league-specific scraper
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0:
                logger.debug(f"✅ {league_name} scraping completed successfully")
                return []  # Match data is written directly to files, not returned
            else:
                logger.warning(f"⚠️ {league_name} scraping failed with return code {result.returncode}")
                if result.stderr:
                    logger.warning(f"⚠️ {league_name} stderr: {result.stderr[:200]}...")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error during {league_name} scraping: {e}")
            return []

class EnhancedMasterScraper:
    """Enhanced master scraper with comprehensive stealth measures."""
    
    def __init__(self, stealth_config: StealthConfig):
        self.config = stealth_config
        self.incremental_manager = IncrementalScrapingManager()
        self.stealth_browser = create_stealth_browser(
            fast_mode=stealth_config.fast_mode,
            verbose=stealth_config.verbose,
            environment=stealth_config.environment
        )
        self.proxy_rotator = get_proxy_rotator()
        self.failures = []
        self.backup_manager = None  # Will be initialized when needed
        
        # Metrics tracking
        self.session_metrics = SessionMetrics(
            session_id=f"master_session_{int(time.time())}",
            start_time=datetime.now()
        )
        
        logger.info(f"🚀 Enhanced Master Scraper initialized")
        logger.info(f"   Mode: {'FAST' if stealth_config.fast_mode else 'STEALTH'}")
        logger.info(f"   Environment: {stealth_config.environment}")
        logger.info(f"   Verbose: {stealth_config.verbose}")
        logger.info(f"   Delta Mode: {stealth_config.delta_mode}")
        logger.info(f"   JSON Backup: Enabled")
        if stealth_config.delta_mode and stealth_config.delta_start_date and stealth_config.delta_end_date:
            logger.info(f"   Delta Range: {stealth_config.delta_start_date} to {stealth_config.delta_end_date}")
    
    def analyze_scraping_strategy(self, league_name: str = None, force_full: bool = False, force_incremental: bool = False) -> Dict[str, Any]:
        """Analyze and determine the scraping strategy using intelligent delta analysis."""
        logger.info(f"\n🔍 Analyzing scraping strategy...")
        logger.info(f"   League: {league_name or 'All'}")
        logger.info(f"   Force Full: {force_full}")
        logger.info(f"   Force Incremental: {force_incremental}")
        
        if force_full:
            return {
                "strategy": "FULL",
                "reason": "Forced full scraping",
                "overlap_days": 0,
                "estimated_matches": "Unknown"
            }
        
        # Always use intelligent incremental scraping with delta analysis
        # This compares local vs site dates to determine optimal scrape range
        start_date = self.incremental_manager.get_scrape_window()
        
        return {
            "strategy": "INCREMENTAL",
            "reason": f"Intelligent delta analysis from {start_date}",
            "overlap_days": self.incremental_manager.overlap_days,
            "start_date": start_date,
            "estimated_matches": "Variable (determined by delta analysis)"
        }
    
    def run_intelligent_match_scraping(self, analysis: Dict[str, Any]) -> bool:
        """Run intelligent match scraping based on analysis."""
        strategy = analysis["strategy"]
        
        logger.info(f"\n🚀 Running intelligent match scraping...")
        logger.info(f"   Strategy: {strategy}")
        
        if strategy == "FULL":
            return self._run_full_scraping()
        else:
            # Use incremental scraping (default strategy)
            return self._run_incremental_scraping(analysis)
    
    def _run_incremental_scraping(self, analysis: Dict[str, Any]) -> bool:
        """Run incremental scraping using intelligent delta analysis."""
        logger.info(f"\n🎯 Running INCREMENTAL scraping...")
        logger.info(f"   Target: Latest matches via intelligent detection")
        logger.info(f"   Goal: Capture new and updated matches efficiently")
        
        try:
            # Run the incremental scraping process with stealth config
            results = self.incremental_manager.run_incremental_scrape(self.config)
            
            # Check if scraping was successful
            if results["success"]:
                logger.info(f"✅ Incremental scraping completed successfully")
                logger.info(f"   📥 Scraped: {results['scraped_matches']} recent matches")
                logger.info(f"   ➕ New: {results['new_matches']} matches added")
                logger.info(f"   🔄 Updated: {results['updated_matches']} matches updated")
                logger.info(f"   💾 Total: {results['final_matches']} matches in file")
                return True
            else:
                logger.error(f"❌ Incremental scraping failed during save")
                self.failures.append("Failed to save incremental scraping results")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error during incremental scraping: {e}")
            self.failures.append(f"Incremental scraping error: {e}")
            return False
    
    def _run_full_scraping(self) -> bool:
        """Run full scraping for all leagues."""
        logger.info(f"\n🎯 Running FULL scraping...")
        logger.info(f"   Target: All match scores and game data")
        logger.info(f"   Scope: All series and teams")
        logger.info(f"   Goal: Complete data refresh")
        
        # For full scraping, we run the scraper (with delta mode if enabled)
        try:
            cmd = [
                "python3", "data/etl/scrapers/scrape_match_scores.py",
                "all"  # Scrape all leagues
            ]
            
            # Add delta mode parameters if enabled
            if self.config.delta_mode:
                cmd.extend(["--delta-mode"])
                if self.config.delta_start_date:
                    cmd.extend(["--start-date", self.config.delta_start_date])
                if self.config.delta_end_date:
                    cmd.extend(["--end-date", self.config.delta_end_date])
            
            # Add other configuration parameters
            if self.config.fast_mode:
                cmd.append("--fast")
            # Note: scraper is verbose by default, use --quiet to disable
            if not self.config.verbose:
                cmd.append("--quiet")
            
            logger.info(f"🚀 Running full scraper: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                logger.info("✅ Full scraping completed successfully")
                return True
            else:
                logger.error(f"❌ Full scraping failed: {result.stderr}")
                self.failures.append(f"Full scraping failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ Error during full scraping: {e}")
            self.failures.append(f"Error during full scraping: {e}")
            return False
    

                
    def run_scraping_step(self, league_name: str = None, force_full: bool = False, force_incremental: bool = False) -> bool:
        """Run the complete scraping step with JSON backup protection."""
        start_time = datetime.now()
        logger.info(f"\n🎯 Running scraping step...")
        logger.info(f"   League: {league_name or 'All'}")
        logger.info(f"   Force Full: {force_full}")
        logger.info(f"   Force Incremental: {force_incremental}")
        
        # Set target league for incremental scraping
        if league_name:
            self.incremental_manager.target_league = league_name
            logger.info(f"🎯 Target league set to: {league_name}")
        
        # Send start notification
        send_scraper_notification("[1/4] Master Scraper Starting")
        
        try:
            # CRITICAL STEP: Create backup of JSON files before any scraping
            logger.info("📦 Creating backup of JSON files before scraping...")
            send_scraper_notification("[1/4] Creating JSON backup before scraping...")
            
            try:
                self.backup_manager = backup_before_scraping(league_name)
                backup_summary = self.backup_manager.get_backup_summary()
                backup_msg = f"✅ Backup completed: {backup_summary['total_files']} files ({backup_summary['total_size_mb']:.1f}MB)"
                logger.info(backup_msg)
                send_scraper_notification(f"[1/4] {backup_msg}")
            except Exception as e:
                error_msg = f"❌ Backup failed: {e}"
                logger.error(error_msg)
                logger.warning("⚠️ Proceeding without backup - MANUAL BACKUP RECOMMENDED!")
                send_scraper_notification(f"[1/4] ⚠️ Backup failed: {e} - Proceeding without backup")
            
            # Analyze strategy
            analysis = self.analyze_scraping_strategy(league_name, force_full, force_incremental)
            
            # Send strategy notification
            strategy_msg = f"[2/4] Strategy Analysis: {analysis['strategy']}"
            send_scraper_notification(strategy_msg)
            
            # Run scraping
            success = self.run_intelligent_match_scraping(analysis)
            
            # Update session metrics
            end_time = datetime.now()
            duration = end_time - start_time
            self.session_metrics.total_duration = duration.total_seconds()
            
            # Prepare metrics for notification
            metrics = {
                "Strategy": analysis['strategy'],
                "Overlap Days": analysis.get('overlap_days', 7),
                "Start Date": analysis.get('start_date', 'N/A'),
                "Estimated Matches": analysis.get('estimated_matches', 'Variable'),
                "Failures": len(self.failures)
            }
            
            if success:
                # Send success notification with backup info
                final_message = f"[4/4] 🎉 SCRAPER COMPLETE - Strategy: {analysis['strategy']}"
                if self.backup_manager:
                    backup_summary = self.backup_manager.get_backup_summary()
                    final_message += f" (Backup: {backup_summary['backup_directory']})"
                send_scraper_notification(final_message, duration=duration, metrics=metrics)
                return True
            else:
                # Send failure notification with backup info
                error_details = "; ".join(self.failures) if self.failures else "Unknown scraping error"
                failure_message = f"[4/4] ❌ SCRAPER FAILED - {error_details}"
                if self.backup_manager:
                    backup_summary = self.backup_manager.get_backup_summary()
                    failure_message += f" (Backup available: {backup_summary['backup_directory']})"
                send_scraper_notification(failure_message, is_failure=True, step_name="Master Scraper", error_details=error_details)
                return False
                
        except Exception as e:
            # Send exception notification
            logger.error(f"❌ Error in scraping step: {e}")
            self.failures.append(f"Error in scraping step: {e}")
            send_scraper_notification("", is_failure=True, step_name="Master Scraper", error_details=str(e))
            return False
    
    def save_detailed_results(self, analysis: Dict[str, Any]):
        """Save detailed results to JSON file."""
        try:
            os.makedirs("logs", exist_ok=True)
            
            results = {
                "timestamp": datetime.now().isoformat(),
                "analysis": {
                    "strategy": analysis["strategy"],
                    "reason": analysis["reason"],
                    "overlap_days": analysis.get("overlap_days", 7),
                    "start_date": analysis.get("start_date", "N/A"),
                    "estimated_matches": analysis.get("estimated_matches", "Variable")
                },
                "session_metrics": self.session_metrics.get_summary(),
                "failures": self.failures
            }
            
            with open("logs/scraping_results.json", "w") as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"✅ Results saved to: logs/scraping_results.json")
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")

def detect_environment():
    """Auto-detect the current environment."""
    # Check for Railway environment variables
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return os.getenv("RAILWAY_ENVIRONMENT")
    
    # Check for common production indicators
    if os.getenv("DATABASE_URL") and "railway" in os.getenv("DATABASE_URL", "").lower():
        return "production"
    
    # Check for staging indicators
    if os.getenv("STAGING") or os.getenv("RAILWAY_STAGING"):
        return "staging"
    
    # Check if we're running locally (default)
    if os.path.exists("database_config.py"):
        return "local"
    
    # Fallback to local
    return "local"

def main():
    """Main function with enhanced CLI arguments."""
    parser = argparse.ArgumentParser(description="Enhanced Master Scraper with Stealth Measures")
    parser.add_argument("--league", help="Specific league to scrape")
    parser.add_argument("--force-full", action="store_true", help="Force full scraping")
    parser.add_argument("--force-incremental", action="store_true", help="Force incremental scraping")
    parser.add_argument("--environment", choices=["local", "staging", "production"], 
                       default=detect_environment(), help="Environment mode (auto-detected)")
    parser.add_argument("--fast", action="store_true", help="Enable fast mode (reduced delays)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum retry attempts")
    parser.add_argument("--min-delay", type=float, default=2.0, help="Minimum delay between requests")
    parser.add_argument("--max-delay", type=float, default=6.0, help="Maximum delay between requests")
    parser.add_argument("--requests-per-proxy", type=int, default=30, help="Requests per proxy before rotation")
    parser.add_argument("--session-duration", type=int, default=600, help="Session duration in seconds")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    
    # Delta mode arguments
    parser.add_argument("--delta-mode", action="store_true", help="Enable delta scraping mode")
    parser.add_argument("--delta-start-date", help="Start date for delta scraping (YYYY-MM-DD)")
    parser.add_argument("--delta-end-date", help="End date for delta scraping (YYYY-MM-DD)")
    parser.add_argument("--delta-config", default="data/etl/scrapers/delta_scraper_config.json", 
                       help="Path to delta configuration file")
    
    args = parser.parse_args()
    
    # Create stealth configuration
    config = StealthConfig(
        fast_mode=args.fast,
        verbose=args.verbose,
        environment=args.environment,
        max_retries=args.max_retries,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        timeout=args.timeout,
        requests_per_proxy=args.requests_per_proxy,
        session_duration=args.session_duration,
        # Delta mode configuration
        delta_mode=args.delta_mode,
        delta_start_date=args.delta_start_date,
        delta_end_date=args.delta_end_date,
        delta_config_file=args.delta_config
    )
    
    # Create enhanced master scraper
    scraper = EnhancedMasterScraper(config)
    
    # Log start
    logger.info(f"\n🎯 Master Scraper Started")
    logger.info(f"   Time: {datetime.now()}")
    logger.info(f"   Environment: {args.environment}")
    logger.info(f"   League: {args.league or 'All'}")
    logger.info(f"   Force Full: {args.force_full}")
    logger.info(f"   Force Incremental: {args.force_incremental}")
    logger.info(f"   Delta Mode: {args.delta_mode}")
    if args.delta_mode and args.delta_start_date and args.delta_end_date:
        logger.info(f"   Delta Range: {args.delta_start_date} to {args.delta_end_date}")
    
    try:
        # Run scraping step
        success = scraper.run_scraping_step(
            league_name=args.league,
            force_full=args.force_full,
            force_incremental=args.force_incremental
        )
        
        # Analyze strategy for logging
        analysis = scraper.analyze_scraping_strategy(args.league, args.force_full, args.force_incremental)
        
        # Save results
        scraper.save_detailed_results(analysis)
        
        # Log final summary
        logger.info(f"\n📊 Final Summary:")
        logger.info(f"   Success: {'✅' if success else '❌'}")
        logger.info(f"   Strategy: {analysis['strategy']}")
        logger.info(f"   Overlap Days: {analysis.get('overlap_days', 7)} days")
        logger.info(f"   Start Date: {analysis.get('start_date', 'N/A')}")
        logger.info(f"   Estimated Matches: {analysis.get('estimated_matches', 'Variable')}")
        logger.info(f"   Reason: {analysis['reason']}")
        
        if scraper.failures:
            logger.info(f"   Failures: {len(scraper.failures)}")
            for failure in scraper.failures:
                logger.info(f"     - {failure}")
        
        logger.info(f"\n✅ Master scraper completed successfully")
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"❌ Master scraper failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 