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

class IncrementalScrapingManager:
    """Manages incremental scraping using 10-day sliding window approach"""
    
    def __init__(self):
        self.match_scores_file = "match_scores.json"
        self.backup_file = "match_scores_backup.json"
        self.sliding_window_days = 10
    
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
    
    def get_scrape_window(self) -> str:
        """
        Calculate the start date for sliding window (10 days ago).
        
        Returns:
            Start date as YYYY-MM-DD string
        """
        today = datetime.today()
        start_date = today - timedelta(days=self.sliding_window_days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        logger.info(f"📅 Scrape window: {start_date_str} to {today.strftime('%Y-%m-%d')} ({self.sliding_window_days} days)")
        return start_date_str
    
    def scrape_matches_since(self, start_date: str) -> List[Dict]:
        """
        Scrape matches since the given start date.
        
        Args:
            start_date: Date string in YYYY-MM-DD format
            
        Returns:
            List of match dictionaries with 'id', 'date', 'score' fields
        """
        # TODO: This is a placeholder - implement actual scraping logic
        # This should call your existing scraping functions with date filtering
        logger.info(f"🔍 Scraping matches since {start_date}...")
        
        # For now, return empty list - this needs to be implemented with actual scraper
        scraped_matches = []
        
        logger.info(f"📥 Scraped {len(scraped_matches)} matches since {start_date}")
        return scraped_matches
    
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
    
    def run_incremental_scrape(self) -> Dict[str, Any]:
        """
        Run the complete incremental scraping process.
        
        Returns:
            Dictionary with scraping results and statistics
        """
        logger.info("🚀 Starting incremental scraping with 10-day sliding window")
        
        # Step 1: Load existing matches
        existing_matches, existing_ids, id_to_match = self.load_existing_matches()
        
        # Step 2: Define scrape window
        start_date = self.get_scrape_window()
        
        # Step 3: Scrape recent matches
        scraped_matches = self.scrape_matches_since(start_date)
        
        # Step 4: Compare and merge
        updated_matches, new_count, updated_count = self.compare_and_merge_matches(
            existing_matches, existing_ids, id_to_match, scraped_matches
        )
        
        # Step 5: Deduplicate
        final_matches = self.deduplicate_matches(updated_matches)
        
        # Step 6: Save to file
        save_success = self.save_matches(final_matches)
        
        # Results
        results = {
            "success": save_success,
            "existing_matches": len(existing_matches),
            "scraped_matches": len(scraped_matches),
            "new_matches": new_count,
            "updated_matches": updated_count,
            "final_matches": len(final_matches),
            "start_date": start_date,
            "sliding_window_days": self.sliding_window_days
        }
        
        # Log summary
        logger.info("📊 Incremental Scraping Results:")
        logger.info(f"   📥 Scraped: {len(scraped_matches)} matches since {start_date}")
        logger.info(f"   ➕ New: {new_count} matches")
        logger.info(f"   🔄 Updated: {updated_count} matches")
        logger.info(f"   💾 Final: {len(final_matches)} total matches")
        
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
    
    def analyze_scraping_strategy(self, league_name: str = None, force_full: bool = False, force_incremental: bool = False) -> Dict[str, Any]:
        """Analyze and determine the scraping strategy using 10-day sliding window."""
        logger.info(f"\n🔍 Analyzing scraping strategy...")
        logger.info(f"   League: {league_name or 'All'}")
        logger.info(f"   Force Full: {force_full}")
        logger.info(f"   Force Incremental: {force_incremental}")
        
        if force_full:
            return {
                "strategy": "FULL",
                "reason": "Forced full scraping",
                "sliding_window_days": 0,
                "estimated_matches": "Unknown"
            }
        
        # Always use incremental scraping with 10-day sliding window
        # This captures both new matches and retroactively edited ones
        start_date = self.incremental_manager.get_scrape_window()
        
        return {
            "strategy": "INCREMENTAL",
            "reason": f"10-day sliding window from {start_date}",
            "sliding_window_days": self.incremental_manager.sliding_window_days,
            "start_date": start_date,
            "estimated_matches": "Variable (recent matches only)"
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
        """Run incremental scraping using 10-day sliding window."""
        logger.info(f"\n🎯 Running INCREMENTAL scraping...")
        logger.info(f"   Target: Last {analysis.get('sliding_window_days', 10)} days")
        logger.info(f"   Goal: Capture new and updated matches efficiently")
        
        try:
            # Run the incremental scraping process
            results = self.incremental_manager.run_incremental_scrape()
            
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
        
        # For full scraping, we run the scraper without date restrictions
        try:
            result = subprocess.run([
                "python3", "data/etl/scrapers/scrape_match_scores.py",
                "all",  # Scrape all leagues
                "--fast" if self.config.fast_mode else "",
                "--verbose" if self.config.verbose else ""
            ], capture_output=True, text=True, timeout=3600)
            
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
                "Sliding Window Days": analysis.get('sliding_window_days', 10),
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
                    "sliding_window_days": analysis.get("sliding_window_days", 10),
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
        session_duration=args.session_duration
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
        logger.info(f"   Sliding Window: {analysis.get('sliding_window_days', 10)} days")
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