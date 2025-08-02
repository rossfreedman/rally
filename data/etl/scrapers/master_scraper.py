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
from typing import Dict, List, Optional, Any, Tuple
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

@dataclass
class DeltaScrapingPlan:
    """Plan for delta scraping."""
    league_id: int
    league_name: str
    start_date: str
    end_date: str
    matches_to_scrape: int
    estimated_requests: int
    reason: str

class DeltaScrapingManager:
    """Manages delta scraping by comparing JSON files vs database imports"""
    
    def __init__(self):
        self.engine = get_db_engine()
        # Map league IDs to their JSON file paths
        self.league_json_mapping = {
            4930: "data/leagues/APTA_CHICAGO/match_history.json",  # APTA Chicago
            4931: "data/leagues/CITA/match_history.json",           # CITA
            4932: "data/leagues/CNSWPL/match_history.json",         # CNSWPL
            4933: "data/leagues/NSTF/match_history.json"            # NSTF
        }
    
    def parse_json_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse JSON date format like '31-Oct-24' to date object"""
        try:
            return datetime.strptime(date_str, '%d-%b-%y').date()
        except:
            return None
    
    def get_latest_json_date(self, league_id: int) -> Optional[datetime.date]:
        """Get the latest date from JSON file for a league."""
        json_file = self.league_json_mapping.get(league_id)
        if not json_file or not os.path.exists(json_file):
            return None
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            latest_date = None
            for match in data:
                if 'Date' in match:
                    date_obj = self.parse_json_date(match['Date'])
                    if date_obj and (latest_date is None or date_obj > latest_date):
                        latest_date = date_obj
            
            return latest_date
        except Exception as e:
            logger.error(f"❌ Error reading JSON file {json_file}: {e}")
            return None
    
    def get_latest_database_date(self, league_id: int) -> Optional[datetime.date]:
        """Get the latest date from database for a league."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text('''
                    SELECT MAX(match_date) as latest_date
                    FROM match_scores
                    WHERE league_id = :league_id
                '''), {"league_id": league_id})
                
                row = result.fetchone()
                if row and row[0]:
                    # Handle both datetime and date objects
                    if hasattr(row[0], 'date'):
                        return row[0].date()
                    else:
                        return row[0]
                return None
        except Exception as e:
            logger.error(f"❌ Error querying database for league {league_id}: {e}")
            return None
    
    def calculate_delta_date_range(self, league_id: int) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
        """Calculate date range for delta based on JSON vs Database comparison"""
        
        json_latest = self.get_latest_json_date(league_id)
        db_latest = self.get_latest_database_date(league_id)
        
        if not json_latest:
            logger.warning(f"⚠️ No JSON data available for league {league_id}")
            return None, None
        
        if not db_latest:
            # No database data, import everything from JSON
            logger.info(f"📥 No database data for league {league_id}, will import all JSON data")
            return json_latest, json_latest  # Import just the latest date
        
        if json_latest > db_latest:
            # JSON is newer than database, need to import delta
            delta_days = (json_latest - db_latest).days
            logger.info(f"🎯 DELTA: JSON is {delta_days} days newer than database")
            logger.info(f"📅 Need to import from: {db_latest + timedelta(days=1)} to {json_latest}")
            return db_latest + timedelta(days=1), json_latest
        elif json_latest < db_latest:
            # Database is newer than JSON (shouldn't happen normally)
            logger.warning(f"⚠️ Database is newer than JSON for league {league_id}")
            return None, None
        else:
            # Dates match, no delta needed
            logger.info(f"✅ DATES MATCH: No delta needed for league {league_id}")
            return None, None
    
    def get_matches_from_json_in_range(self, league_id: int, start_date: datetime.date, end_date: datetime.date) -> List[Dict]:
        """Get matches from JSON file within the specified date range."""
        json_file = self.league_json_mapping.get(league_id)
        if not json_file or not os.path.exists(json_file):
            return []
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            matches_in_range = []
            for match in data:
                if 'Date' in match:
                    match_date = self.parse_json_date(match['Date'])
                    if match_date and start_date <= match_date <= end_date:
                        matches_in_range.append(match)
            
            return matches_in_range
        except Exception as e:
            logger.error(f"❌ Error reading JSON file {json_file}: {e}")
            return []
    
    def create_delta_plan(self, league_id: int, league_name: str) -> Optional[DeltaScrapingPlan]:
        """Create a delta scraping plan for a league."""
        start_date, end_date = self.calculate_delta_date_range(league_id)
        
        if not start_date or not end_date:
            return None
        
        # Get matches in range
        matches = self.get_matches_from_json_in_range(league_id, start_date, end_date)
        
        # Estimate requests (3 requests per match for detailed scraping)
        estimated_requests = len(matches) * 3
        
        return DeltaScrapingPlan(
            league_id=league_id,
            league_name=league_name,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            matches_to_scrape=len(matches),
            estimated_requests=estimated_requests,
            reason="JSON data newer than database"
        )

class EnhancedMasterScraper:
    """Enhanced master scraper with comprehensive stealth measures."""
    
    def __init__(self, stealth_config: StealthConfig):
        self.config = stealth_config
        self.delta_manager = DeltaScrapingManager()
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
        """Analyze and determine the best scraping strategy."""
        logger.info(f"\n🔍 Analyzing scraping strategy...")
        logger.info(f"   League: {league_name or 'All'}")
        logger.info(f"   Force Full: {force_full}")
        logger.info(f"   Force Incremental: {force_incremental}")
        
        if force_full:
            return {
                "strategy": "FULL",
                "reason": "Forced full scraping",
                "league_plans": []
            }
        
        if force_incremental:
            return {
                "strategy": "DELTA",
                "reason": "Forced incremental scraping",
                "league_plans": []
            }
        
        # Get league plans for delta scraping
        league_plans = []
        total_matches_to_scrape = 0
        total_estimated_requests = 0
        
        # Map league names to IDs
        league_mapping = {
            "APTA Chicago": 4930,
            "CITA": 4931,
            "CNSWPL": 4932,
            "North Shore Tennis Foundation": 4933,
            "NSTF": 4933
        }
        
        if league_name:
            # Single league
            league_id = league_mapping.get(league_name)
            if league_id:
                plan = self.delta_manager.create_delta_plan(league_id, league_name)
                if plan:
                    league_plans.append(plan)
                    total_matches_to_scrape += plan.matches_to_scrape
                    total_estimated_requests += plan.estimated_requests
        else:
            # All leagues
            for name, league_id in league_mapping.items():
                plan = self.delta_manager.create_delta_plan(league_id, name)
                if plan:
                    league_plans.append(plan)
                    total_matches_to_scrape += plan.matches_to_scrape
                    total_estimated_requests += plan.estimated_requests
        
        # Determine strategy based on request volume
        if total_estimated_requests < 1000:  # Small delta
            strategy = "DELTA"
            reason = f"Small delta: {total_matches_to_scrape} matches, {total_estimated_requests} requests"
        else:
            strategy = "FULL"
            reason = f"Large delta: {total_matches_to_scrape} matches, {total_estimated_requests} requests"
        
        return {
            "strategy": strategy,
            "reason": reason,
            "league_plans": league_plans,
            "total_matches": total_matches_to_scrape,
            "total_requests": total_estimated_requests
        }
    
    def run_intelligent_match_scraping(self, analysis: Dict[str, Any]) -> bool:
        """Run intelligent match scraping based on analysis."""
        strategy = analysis["strategy"]
        league_plans = analysis["league_plans"]
        
        logger.info(f"\n🚀 Running intelligent match scraping...")
        logger.info(f"   Strategy: {strategy}")
        logger.info(f"   League Plans: {len(league_plans)}")
        
        if strategy == "DELTA":
            return self._run_delta_scraping(league_plans)
        else:
            return self._run_full_scraping(league_plans)
    
    def _run_delta_scraping(self, league_plans: List[DeltaScrapingPlan]) -> bool:
        """Run delta scraping for specific leagues."""
        logger.info(f"\n🎯 Running DELTA scraping...")
        logger.info(f"   Target: Only missing matches")
        logger.info(f"   Scope: {len(league_plans)} leagues")
        logger.info(f"   Goal: Minimize requests and processing time")
        
        successful_leagues = 0
        total_matches_scraped = 0
        
        for plan in league_plans:
            logger.info(f"\n🏆 Scraping {plan.league_name}:")
            logger.info(f"   Matches: {plan.matches_to_scrape}")
            logger.info(f"   Date Range: {plan.start_date} to {plan.end_date}")
            
            try:
                # Run the scraper with date range
                result = self._run_scraper_with_dates(plan)
                if result:
                    successful_leagues += 1
                    total_matches_scraped += plan.matches_to_scrape
                    logger.info(f"✅ Scraping completed for {plan.league_name}")
                else:
                    logger.error(f"❌ Scraping failed for {plan.league_name}")
                    self.failures.append(f"Failed to scrape {plan.league_name}")
            except Exception as e:
                logger.error(f"❌ Error scraping {plan.league_name}: {e}")
                self.failures.append(f"Error scraping {plan.league_name}: {e}")
        
        logger.info(f"\n📊 Delta Scraping Results:")
        logger.info(f"   Successful Leagues: {successful_leagues}/{len(league_plans)}")
        logger.info(f"   Total Matches Scraped: {total_matches_scraped}")
        
        return successful_leagues == len(league_plans)
    
    def _run_full_scraping(self, league_plans: List[DeltaScrapingPlan]) -> bool:
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
    
    def _run_scraper_with_dates(self, plan: DeltaScrapingPlan) -> bool:
        """Run scraper with specific date range."""
        logger.info(f"\n🎯 Running scraper for {plan.league_name}")
        logger.info(f"   Date Range: {plan.start_date} to {plan.end_date}")
        logger.info(f"   Target Matches: {plan.matches_to_scrape}")
        
        # Map league names to subdomains
        league_subdomain_mapping = {
            "APTA Chicago": "aptachicago",
            "CITA": "cita",
            "CNSWPL": "cnswpl",
            "North Shore Tennis Foundation": "nstf",
            "NSTF": "nstf"
        }
        
        subdomain = league_subdomain_mapping.get(plan.league_name)
        if not subdomain:
            logger.error(f"❌ Unknown league: {plan.league_name}")
            return False
        
        try:
            # Run the enhanced scraper
            result = subprocess.run([
                "python3", "data/etl/scrapers/scrape_match_scores.py",
                subdomain,
                "--start-date", plan.start_date,
                "--end-date", plan.end_date,
                "--delta-mode",
                "--fast" if self.config.fast_mode else "",
                "--verbose" if self.config.verbose else ""
            ], capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0:
                logger.info(f"✅ Scraping completed for {plan.league_name}")
                return True
            else:
                logger.error(f"❌ Scraping failed for {plan.league_name}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ Error running scraper for {plan.league_name}: {e}")
            return False
    
    def run_scraping_step(self, league_name: str = None, force_full: bool = False, force_incremental: bool = False) -> bool:
        """Run the complete scraping step."""
        logger.info(f"\n🎯 Running scraping step...")
        logger.info(f"   League: {league_name or 'All'}")
        logger.info(f"   Force Full: {force_full}")
        logger.info(f"   Force Incremental: {force_incremental}")
        
        try:
            # Analyze strategy
            analysis = self.analyze_scraping_strategy(league_name, force_full, force_incremental)
            
            # Run scraping
            success = self.run_intelligent_match_scraping(analysis)
            
            # Update session metrics
            self.session_metrics.total_duration = (datetime.now() - self.session_metrics.start_time).total_seconds()
            
            return success
        except Exception as e:
            logger.error(f"❌ Error in scraping step: {e}")
            self.failures.append(f"Error in scraping step: {e}")
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
                    "total_matches": analysis.get("total_matches", 0),
                    "total_requests": analysis.get("total_requests", 0),
                    "league_plans": [
                        {
                            "league_id": plan.league_id,
                            "league_name": plan.league_name,
                            "start_date": plan.start_date,
                            "end_date": plan.end_date,
                            "matches_to_scrape": plan.matches_to_scrape,
                            "estimated_requests": plan.estimated_requests,
                            "reason": plan.reason
                        }
                        for plan in analysis.get("league_plans", [])
                    ]
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
        logger.info(f"   Total Matches: {analysis.get('total_matches', 0)}")
        logger.info(f"   Estimated Requests: {analysis.get('total_requests', 0)}")
        logger.info(f"   Efficiency: {analysis.get('total_requests', 0) / 10000 * 100:.1f}% of full scraping")
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