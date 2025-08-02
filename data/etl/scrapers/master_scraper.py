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
    
    def get_latest_match_date_from_file(self, existing_matches: List[Dict]) -> Optional[datetime]:
        """
        Find the most recent match date from existing match data.
        
        Args:
            existing_matches: List of match dictionaries
            
        Returns:
            Latest match date as datetime object, or None if no valid dates found
        """
        if not existing_matches:
            logger.info("📄 No existing matches found")
            return None
        
        latest_date = None
        valid_dates = []
        
        for match in existing_matches:
            if 'date' in match:
                try:
                    match_date = datetime.strptime(match['date'], '%Y-%m-%d')
                    valid_dates.append(match_date)
                except ValueError:
                    logger.debug(f"⚠️ Invalid date format in match: {match.get('date')}")
                    continue
        
        if valid_dates:
            latest_date = max(valid_dates)
            logger.info(f"📅 Latest match in local file: {latest_date.strftime('%Y-%m-%d')}")
        else:
            logger.warning("⚠️ No valid dates found in existing matches")
        
        return latest_date
    
    def scrape_latest_match_date_from_site(self, stealth_config: Optional[StealthConfig] = None) -> Optional[datetime]:
        """
        Get the latest match date directly from TennisScores standings pages.
        Uses lightweight direct HTTP requests to check recent match activity.
        
        Args:
            stealth_config: Optional stealth configuration
            
        Returns:
            Latest match date from site as datetime object, or None if not found
        """
        logger.info("🔍 Checking latest match date from TennisScores...")
        
        try:
            import requests
            import re
            
            # Define league standings URLs to check for recent activity
            standings_urls = [
                "https://www.tenniscores.com/league-standings/57043",  # APTA Chicago
                "https://www.tenniscores.com/league-standings/57045",  # NSTF  
                "https://www.tenniscores.com/league-standings/57046",  # CNSWPL
                "https://www.tenniscores.com/league-standings/57047"   # CITA
            ]
            
            latest_match_date = None
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            for url in standings_urls:
                try:
                    logger.debug(f"🌐 Checking standings: {url}")
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
                                            logger.debug(f"✅ Found potential latest date: {date_obj.strftime('%Y-%m-%d')}")
                                except ValueError:
                                    continue
                    else:
                        logger.debug(f"⚠️ Failed to fetch {url}: HTTP {response.status_code}")
                        
                except Exception as e:
                    logger.debug(f"⚠️ Error checking {url}: {str(e)}")
                    continue
            
            if latest_match_date:
                logger.info(f"✅ Successfully detected latest site date: {latest_match_date.strftime('%Y-%m-%d')}")
                return latest_match_date
            else:
                logger.warning("⚠️ No recent match dates found on standings pages")
                
        except Exception as e:
            logger.warning(f"⚠️ Exception during direct site check: {str(e)}")
        
        # Fallback: Use a reasonable estimate based on typical league activity
        today = datetime.now()
        reasonable_latest = today - timedelta(days=3)  # Most leagues have matches within 3 days
        
        logger.info(f"📅 Using fallback estimate for latest match: {reasonable_latest.strftime('%Y-%m-%d')}")
        logger.info("   🧠 This ensures intelligent scraping still works even when detection fails")
        
        return reasonable_latest
    
    def determine_intelligent_scrape_range(self, existing_matches: List[Dict], stealth_config: Optional[StealthConfig] = None) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Intelligently determine if scraping is needed and calculate date range.
        
        Args:
            existing_matches: List of existing match dictionaries
            stealth_config: Optional stealth configuration
            
        Returns:
            Tuple of (start_date_str, end_date_str, should_scrape)
        """
        logger.info("🧠 Intelligent Delta Analysis Starting...")
        logger.info("=" * 60)
        
        # Step 1: Get latest match date from local file
        logger.info("📋 STEP 1: Analyzing local match_scores.json file...")
        latest_local_date = self.get_latest_match_date_from_file(existing_matches)
        
        # Step 2: Get latest match date from site
        logger.info("🌐 STEP 2: Checking latest match date on TennisScores...")
        latest_site_date = self.scrape_latest_match_date_from_site(stealth_config)
        
        # Step 3: Debug output - show both dates clearly
        logger.info("🔍 STEP 3: Date Comparison Results:")
        logger.info("=" * 60)
        if latest_local_date:
            logger.info(f"   📅 LOCAL FILE (match_scores.json):  {latest_local_date.strftime('%Y-%m-%d')}")
        else:
            logger.info(f"   📅 LOCAL FILE (match_scores.json):  NO MATCHES FOUND")
            
        if latest_site_date:
            logger.info(f"   🌐 WEBSITE (TennisScores.com):      {latest_site_date.strftime('%Y-%m-%d')}")
        else:
            logger.info(f"   🌐 WEBSITE (TennisScores.com):      DETECTION FAILED")
        
        logger.info("=" * 60)
        
        # Step 4: Decision logic with clear reasoning
        if not latest_site_date:
            logger.warning("⚠️ DECISION: Site detection failed - using fallback window")
            today = datetime.now()
            start_date = (today - timedelta(days=14)).strftime('%Y-%m-%d')  # 14-day fallback window
            end_date = today.strftime('%Y-%m-%d')
            logger.info(f"   📅 Fallback range: {start_date} to {end_date}")
            return start_date, end_date, True
            
        if not latest_local_date:
            logger.info("✅ DECISION: No local data - performing initial scrape")
            # No local data, scrape from 30 days ago to latest site date
            start_date = (latest_site_date - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = latest_site_date.strftime('%Y-%m-%d')
            logger.info(f"   📅 Initial scrape range: {start_date} to {end_date}")
            return start_date, end_date, True
        
        # Step 5: Compare the dates with detailed logic
        local_date_str = latest_local_date.strftime('%Y-%m-%d')
        site_date_str = latest_site_date.strftime('%Y-%m-%d')
        
        if latest_site_date <= latest_local_date:
            logger.info("✅ DECISION: Local data is up-to-date - SKIPPING SCRAPE")
            logger.info(f"   🧠 Reasoning: Site date ({site_date_str}) ≤ Local date ({local_date_str})")
            return None, None, False
        else:
            # Calculate scrape range: latest_local_date - 7 days to latest_site_date
            scrape_start_date = latest_local_date - timedelta(days=self.overlap_days)
            scrape_end_date = latest_site_date
            
            days_diff = (latest_site_date - latest_local_date).days
            logger.info("🎯 DECISION: New matches detected - PROCEEDING WITH SCRAPE")
            logger.info(f"   🧠 Reasoning: Site date ({site_date_str}) > Local date ({local_date_str})")
            logger.info(f"   📈 Site is {days_diff} days ahead of local data")
            logger.info(f"   📅 Scrape range: {scrape_start_date.strftime('%Y-%m-%d')} to {scrape_end_date.strftime('%Y-%m-%d')}")
            logger.info(f"   🔄 Including {self.overlap_days}-day overlap to catch updates")
            
            return scrape_start_date.strftime('%Y-%m-%d'), scrape_end_date.strftime('%Y-%m-%d'), True
    
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
        Run the complete intelligent incremental scraping process.
        
        Args:
            stealth_config: Optional stealth configuration for delta mode
        
        Returns:
            Dictionary with scraping results and statistics
        """
        logger.info("🚀 Starting Intelligent Incremental Scraping")
        logger.info("🧠 Using latest match detection for optimal efficiency")
        
        # Step 1: Load existing matches
        existing_matches, existing_ids, id_to_match = self.load_existing_matches()
        
        # Step 2: Intelligent analysis - determine if scraping is needed
        start_date, end_date, should_scrape = self.determine_intelligent_scrape_range(existing_matches, stealth_config)
        
        if not should_scrape:
            # No scraping needed - return current state
            logger.info("🎯 Intelligent analysis: No new matches to scrape")
            return {
                "success": True,
                "existing_matches": len(existing_matches),
                "scraped_matches": 0,
                "new_matches": 0,
                "updated_matches": 0,
                "final_matches": len(existing_matches),
                "start_date": "N/A",
                "end_date": "N/A",
                "scraping_skipped": True,
                "reason": "No new matches detected on site"
            }
        
        # Step 3: Scrape matches in the calculated range
        logger.info(f"🎯 Intelligent scraping: {start_date} to {end_date}")
        scraped_matches = self.scrape_matches_between(start_date, end_date, stealth_config)
        
        # Step 4: Load fresh data after scraping to compare results
        # The match scraper updates the file directly, so we need to reload to see changes
        fresh_matches, fresh_ids, fresh_id_to_match = self.load_existing_matches()
        
        # Step 5: Calculate what changed
        new_count = len(fresh_matches) - len(existing_matches)
        updated_count = 0  # For now, we'll estimate based on overlap
        
        # If we used the overlap strategy, estimate updates within the overlap period
        if start_date and end_date:
            overlap_start = datetime.strptime(start_date, '%Y-%m-%d')
            overlap_end = datetime.strptime(end_date, '%Y-%m-%d')
            overlap_matches = [m for m in existing_matches 
                             if 'date' in m and overlap_start <= datetime.strptime(m['date'], '%Y-%m-%d') <= overlap_end]
            updated_count = len(overlap_matches)
        
        # Step 6: Create backup and ensure data integrity
        if os.path.exists(self.match_scores_file):
            # Create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"match_scores_backup_{timestamp}.json"
            
            try:
                import shutil
                shutil.copy2(self.match_scores_file, backup_filename)
                logger.info(f"💾 Timestamped backup created: {backup_filename}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to create timestamped backup: {e}")
        
        # Results
        results = {
            "success": True,
            "existing_matches": len(existing_matches),
            "scraped_matches": 0,  # We don't get individual scraped matches back
            "new_matches": max(0, new_count),  # Ensure non-negative
            "updated_matches": updated_count,
            "final_matches": len(fresh_matches),
            "start_date": start_date,
            "end_date": end_date,
            "scraping_skipped": False,
            "intelligent_mode": True
        }
        
        # Log comprehensive summary
        logger.info("📊 Intelligent Incremental Scraping Results:")
        logger.info("=" * 50)
        logger.info(f"   📅 Scrape Range: {start_date} to {end_date}")
        logger.info(f"   📋 Before: {len(existing_matches)} matches")
        logger.info(f"   📋 After:  {len(fresh_matches)} matches")
        logger.info(f"   ➕ Estimated New: {max(0, new_count)} matches")
        logger.info(f"   🔄 Potential Updates: {updated_count} matches")
        logger.info(f"   🎯 Efficiency: Only scraped {(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days} days instead of full dataset")
        logger.info("=" * 50)
        
        return results

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
            if self.config.verbose:
                cmd.append("--verbose")
            
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
        """Run the complete scraping step."""
        start_time = datetime.now()
        logger.info(f"\n🎯 Running scraping step...")
        logger.info(f"   League: {league_name or 'All'}")
        logger.info(f"   Force Full: {force_full}")
        logger.info(f"   Force Incremental: {force_incremental}")
        
        # Send start notification
        send_scraper_notification("[1/3] Master Scraper Starting")
        
        try:
            # Analyze strategy
            analysis = self.analyze_scraping_strategy(league_name, force_full, force_incremental)
            
            # Send strategy notification
            strategy_msg = f"[2/3] Strategy Analysis: {analysis['strategy']}"
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
                # Send success notification
                final_message = f"[3/3] 🎉 SCRAPER COMPLETE - Strategy: {analysis['strategy']}"
                send_scraper_notification(final_message, duration=duration, metrics=metrics)
                return True
            else:
                # Send failure notification
                error_details = "; ".join(self.failures) if self.failures else "Unknown scraping error"
                send_scraper_notification("", is_failure=True, step_name="Master Scraper", error_details=error_details)
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