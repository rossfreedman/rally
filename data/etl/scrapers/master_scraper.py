#!/usr/bin/env python3
"""
Master Scraper - Unified Intelligent Scraping System
====================================================

This unified scraper intelligently determines whether to perform incremental or full scraping
based on data analysis, schedule information, and existing match data.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# Import database utilities
try:
    from database_config import get_db_engine
    # Avoid importing app.models.database_models which triggers Flask app startup
    # Instead, define the models we need directly
    from sqlalchemy import Column, Integer, String, Date, Time, Text, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    
    Base = declarative_base()
    
    # Define minimal models for scraper use only
    class Schedule(Base):
        __tablename__ = "schedule"
        id = Column(Integer, primary_key=True)
        league_id = Column(Integer, ForeignKey("leagues.id"))
        match_date = Column(Date)
        match_time = Column(Time)
        home_team = Column(Text)
        away_team = Column(Text)
        home_team_id = Column(Integer, ForeignKey("teams.id"))
        away_team_id = Column(Integer, ForeignKey("teams.id"))
        location = Column(Text)
    
    class MatchScore(Base):
        __tablename__ = "match_scores"
        id = Column(Integer, primary_key=True)
        league_id = Column(Integer, ForeignKey("leagues.id"))
        match_date = Column(Date)
        home_team = Column(Text)
        away_team = Column(Text)
        home_team_id = Column(Integer, ForeignKey("teams.id"))
        away_team_id = Column(Integer, ForeignKey("teams.id"))
        home_player_1_id = Column(Text)
        home_player_2_id = Column(Text)
        away_player_1_id = Column(Text)
        away_player_2_id = Column(Text)
        scores = Column(Text)
        winner = Column(Text)
    
    class League(Base):
        __tablename__ = "leagues"
        id = Column(Integer, primary_key=True)
        league_id = Column(String(255), nullable=False, unique=True)
        league_name = Column(String(255), nullable=False)
        league_url = Column(String(512))
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/master_scraper.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DeltaScrapingPlan:
    """Plan for delta scraping"""
    league_id: str
    league_name: str
    start_date: date
    end_date: date
    matches_to_scrape: List[Dict]
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
    
    def parse_json_date(self, date_str: str) -> date:
        """Parse JSON date format like '31-Oct-24' to date object"""
        try:
            return datetime.strptime(date_str, '%d-%b-%y').date()
        except:
            return None
    
    def get_latest_json_date(self, league_id: int) -> date:
        """Get the latest date from JSON file for a league"""
        
        json_file = self.league_json_mapping.get(league_id)
        if not json_file:
            logger.warning(f"⚠️ No JSON file mapping for league {league_id}")
            return None
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    # Find the latest date in the JSON
                    json_dates = []
                    for match in data:
                        if 'Date' in match and match['Date']:
                            parsed_date = self.parse_json_date(match['Date'])
                            if parsed_date:
                                json_dates.append(parsed_date)
                    
                    if json_dates:
                        latest_date = max(json_dates)
                        logger.info(f"📄 JSON latest date for league {league_id}: {latest_date}")
                        return latest_date
                    else:
                        logger.warning(f"⚠️ No valid dates found in JSON for league {league_id}")
                        return None
                else:
                    logger.warning(f"⚠️ Invalid JSON format for league {league_id}")
                    return None
        except FileNotFoundError:
            logger.warning(f"⚠️ JSON file not found: {json_file}")
            return None
        except Exception as e:
            logger.error(f"❌ Error reading JSON for league {league_id}: {e}")
            return None
    
    def get_latest_database_date(self, league_id: int) -> date:
        """Get the latest date from database for a league"""
        
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            # Get the latest match date from database
            latest_match = session.query(MatchScore.match_date).filter(
                MatchScore.league_id == league_id
            ).order_by(MatchScore.match_date.desc()).first()
            
            if latest_match and latest_match[0]:
                latest_date = latest_match[0]
                logger.info(f"🗄️ Database latest date for league {league_id}: {latest_date}")
                return latest_date
            else:
                logger.info(f"🗄️ No matches in database for league {league_id}")
                return None
                
        finally:
            session.close()
    
    def calculate_delta_date_range(self, league_id: int) -> Tuple[date, date]:
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
    
    def create_delta_plan(self, league_id: int) -> DeltaScrapingPlan:
        """Create a comprehensive delta plan based on JSON vs Database comparison"""
        
        # Get league info
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            league = session.query(League).filter(League.id == league_id).first()
            if not league:
                raise ValueError(f"League {league_id} not found")
            
            league_name = league.league_name
            
        finally:
            session.close()
        
        # Calculate delta date range
        start_date, end_date = self.calculate_delta_date_range(league_id)
        
        if not start_date or not end_date:
            # No delta needed
            return DeltaScrapingPlan(
                league_id=str(league_id),
                league_name=league_name,
                start_date=date.today(),
                end_date=date.today(),
                matches_to_scrape=[],
                estimated_requests=0,
                reason="No delta needed - JSON and database dates match"
            )
        
        # Get matches from JSON file in the delta range
        matches_to_scrape = self.get_matches_from_json_in_range(league_id, start_date, end_date)
        
        # Calculate estimated requests (each match might need multiple requests)
        estimated_requests = len(matches_to_scrape) * 3  # Conservative estimate
        
        logger.info(f"\n🎯 Delta Plan for {league_name}:")
        logger.info(f"   Date Range: {start_date} to {end_date}")
        logger.info(f"   Matches to Import: {len(matches_to_scrape)}")
        logger.info(f"   Estimated Requests: {estimated_requests}")
        logger.info(f"   Reason: JSON data newer than database")
        
        return DeltaScrapingPlan(
            league_id=str(league_id),
            league_name=league_name,
            start_date=start_date,
            end_date=end_date,
            matches_to_scrape=matches_to_scrape,
            estimated_requests=estimated_requests,
            reason="JSON data newer than database - need to import delta"
        )
    
    def get_matches_from_json_in_range(self, league_id: int, start_date: date, end_date: date) -> List[Dict]:
        """Get matches from JSON file within the specified date range"""
        
        json_file = self.league_json_mapping.get(league_id)
        if not json_file:
            return []
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                
                matches_in_range = []
                for match in data:
                    if 'Date' in match and match['Date']:
                        parsed_date = self.parse_json_date(match['Date'])
                        if parsed_date and start_date <= parsed_date <= end_date:
                            matches_in_range.append(match)
                
                logger.info(f"📄 Found {len(matches_in_range)} matches in JSON for date range {start_date} to {end_date}")
                return matches_in_range
                
        except Exception as e:
            logger.error(f"❌ Error reading JSON for league {league_id}: {e}")
            return []

class MasterScraper:
    """Unified intelligent scraper that determines scraping strategy"""
    
    def __init__(self):
        self.delta_manager = DeltaScrapingManager()
        self.engine = get_db_engine()
        self.failures = []  # Track failures for cron job compatibility
    
    def analyze_scraping_strategy(self, league: str = None, force_full: bool = False, force_incremental: bool = False) -> Dict:
        """
        Analyze and determine the best scraping strategy
        
        Args:
            league: Specific league to scrape (optional)
            force_full: Force full scraping regardless of analysis
            force_incremental: Force incremental scraping regardless of analysis
            
        Returns:
            Dict with strategy analysis and recommendations
        """
        
        logger.info(f"\n🔍 Analyzing scraping strategy...")
        logger.info(f"   League: {league or 'All leagues'}")
        logger.info(f"   Force Full: {force_full}")
        logger.info(f"   Force Incremental: {force_incremental}")
        
        # Get all leagues or specific league
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            if league:
                leagues = session.query(League).filter(League.league_name.ilike(f"%{league}%")).all()
            else:
                leagues = session.query(League).all()
            
            if not leagues:
                logger.error(f"❌ No leagues found matching: {league}")
                return {"error": f"No leagues found matching: {league}"}
            
            # Analyze each league
            league_plans = []
            total_matches_to_scrape = 0
            total_estimated_requests = 0
            
            for league_obj in leagues:
                try:
                    plan = self.delta_manager.create_delta_plan(league_obj.id)
                    league_plans.append(plan)
                    total_matches_to_scrape += len(plan.matches_to_scrape)
                    total_estimated_requests += plan.estimated_requests
                except Exception as e:
                    logger.error(f"❌ Error analyzing league {league_obj.league_name}: {e}")
                    continue
            
            # Determine strategy
            if force_full:
                strategy = "FORCE_FULL"
                reason = "User forced full scraping"
            elif force_incremental:
                strategy = "FORCE_INCREMENTAL"
                reason = "User forced incremental scraping"
            elif total_matches_to_scrape == 0:
                strategy = "SKIP"
                reason = "No new matches to scrape"
            elif total_estimated_requests < 1000:  # Small delta (increased from 100)
                strategy = "DELTA"
                reason = f"Small delta: {total_matches_to_scrape} matches, {total_estimated_requests} requests"
            else:
                strategy = "FULL"
                reason = f"Large delta: {total_matches_to_scrape} matches, {total_estimated_requests} requests"
            
            analysis = {
                "strategy": strategy,
                "reason": reason,
                "league_plans": league_plans,
                "total_matches_to_scrape": total_matches_to_scrape,
                "total_estimated_requests": total_estimated_requests,
                "efficiency_percentage": (total_estimated_requests / 80000) * 100 if total_estimated_requests > 0 else 0
            }
            
            logger.info(f"\n📊 Strategy Analysis:")
            logger.info(f"   Strategy: {strategy}")
            logger.info(f"   Reason: {reason}")
            logger.info(f"   Total Matches: {total_matches_to_scrape}")
            logger.info(f"   Estimated Requests: {total_estimated_requests}")
            logger.info(f"   Efficiency: {analysis['efficiency_percentage']:.1f}% of full scraping")
            
            return analysis
            
        finally:
            session.close()
    
    def run_intelligent_match_scraping(self, analysis: Dict) -> bool:
        """
        Run match scraping based on intelligent analysis
        
        Args:
            analysis: Strategy analysis from analyze_scraping_strategy
            
        Returns:
            bool: Success status
        """
        
        strategy = analysis.get("strategy")
        league_plans = analysis.get("league_plans", [])
        
        logger.info(f"\n🚀 Running intelligent match scraping...")
        logger.info(f"   Strategy: {strategy}")
        logger.info(f"   League Plans: {len(league_plans)}")
        
        if strategy == "SKIP":
            logger.info(f"✅ Skipping scraping - no new matches to scrape")
            return True
        
        try:
            if strategy in ["DELTA", "FORCE_INCREMENTAL"]:
                return self._run_delta_scraping(league_plans)
            else:
                return self._run_full_scraping(league_plans)
                
        except Exception as e:
            logger.error(f"❌ Error in intelligent match scraping: {e}")
            return False
    
    def _run_delta_scraping(self, league_plans: List[DeltaScrapingPlan]) -> bool:
        """Run delta scraping for specific matches"""
        
        logger.info(f"\n🎯 Running DELTA scraping...")
        logger.info(f"   Target: Only missing matches")
        logger.info(f"   Scope: {len(league_plans)} leagues")
        logger.info(f"   Goal: Minimize requests and processing time")
        
        total_success = 0
        total_matches = 0
        
        for plan in league_plans:
            if len(plan.matches_to_scrape) == 0:
                logger.info(f"✅ {plan.league_name}: No matches to scrape")
                continue
            
            logger.info(f"\n🏆 Scraping {plan.league_name}:")
            logger.info(f"   Matches: {len(plan.matches_to_scrape)}")
            logger.info(f"   Date Range: {plan.start_date} to {plan.end_date}")
            
            # Run scraper for this league with specific date range
            success = self._run_scraper_for_league(
                plan.league_name,
                plan.start_date,
                plan.end_date,
                plan.matches_to_scrape
            )
            
            if success:
                total_success += 1
                total_matches += len(plan.matches_to_scrape)
        
        logger.info(f"\n📊 Delta Scraping Results:")
        logger.info(f"   Successful Leagues: {total_success}/{len(league_plans)}")
        logger.info(f"   Total Matches Scraped: {total_matches}")
        
        return total_success > 0
    
    def _run_full_scraping(self, league_plans: List[DeltaScrapingPlan]) -> bool:
        """Run full scraping for all leagues"""
        
        logger.info(f"\n🎯 Running FULL scraping...")
        logger.info(f"   Target: All match scores and game data")
        logger.info(f"   Scope: All series and teams")
        logger.info(f"   Goal: Complete data refresh")
        
        # Run the original scrape_match_scores.py for full scraping
        try:
            result = subprocess.run([
                sys.executable, "data/etl/scrapers/scrape_match_scores.py"
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                logger.info(f"✅ Full scraping completed successfully")
                return True
            else:
                logger.error(f"❌ Full scraping failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error running full scraping: {e}")
            return False
    
    def _run_scraper_for_league(self, league_name: str, start_date: date, end_date: date, matches: List[Dict]) -> bool:
        """Run scraper for a specific league with date range"""
        
        logger.info(f"\n🎯 Running scraper for {league_name}")
        logger.info(f"   Date Range: {start_date} to {end_date}")
        logger.info(f"   Target Matches: {len(matches)}")
        
        # Import and run the scraper with specific parameters
        try:
            # This would need to be implemented in scrape_match_scores.py
            # For now, we'll run the full scraper but log the intent
            logger.info(f"   Note: Running full scraper for {league_name} (delta filtering to be implemented)")
            
            result = subprocess.run([
                sys.executable, "data/etl/scrapers/scrape_match_scores.py",
                league_name,  # Positional argument for league
                "--start-date", start_date.isoformat(),
                "--end-date", end_date.isoformat(),
                "--delta-mode"  # Enable delta mode
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                logger.info(f"✅ Scraping completed for {league_name}")
                return True
            else:
                logger.error(f"❌ Scraping failed for {league_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error running scraper for {league_name}: {e}")
            return False
    
    def run_scraping_step(self, league: str = None, force_full: bool = False, force_incremental: bool = False) -> bool:
        """
        Run the scraping step with intelligent strategy determination
        
        Args:
            league: Specific league to scrape (optional)
            force_full: Force full scraping
            force_incremental: Force incremental scraping
            
        Returns:
            bool: Success status
        """
        
        logger.info(f"\n🎯 Running scraping step...")
        logger.info(f"   League: {league or 'All leagues'}")
        logger.info(f"   Force Full: {force_full}")
        logger.info(f"   Force Incremental: {force_incremental}")
        
        # Analyze strategy
        analysis = self.analyze_scraping_strategy(league, force_full, force_incremental)
        
        if "error" in analysis:
            logger.error(f"❌ Strategy analysis failed: {analysis['error']}")
            return False
        
        # Run intelligent scraping
        success = self.run_intelligent_match_scraping(analysis)
        
        if success:
            logger.info(f"✅ Scraping step completed successfully")
        else:
            logger.error(f"❌ Scraping step failed")
        
        return success
    
    def save_detailed_results(self, analysis: Dict, success: bool):
        """Save detailed scraping results"""
        
        # Convert DeltaScrapingPlan objects to dicts for JSON serialization
        league_plans = analysis.get("league_plans", [])
        serializable_plans = []
        for plan in league_plans:
            serializable_plans.append({
                "league_id": plan.league_id,
                "league_name": plan.league_name,
                "start_date": plan.start_date.isoformat(),
                "end_date": plan.end_date.isoformat(),
                "matches_to_scrape": plan.matches_to_scrape,
                "estimated_requests": plan.estimated_requests,
                "reason": plan.reason
            })
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "analysis": {
                "strategy": analysis.get("strategy"),
                "reason": analysis.get("reason"),
                "total_matches_to_scrape": analysis.get("total_matches_to_scrape", 0),
                "total_estimated_requests": analysis.get("total_estimated_requests", 0),
                "efficiency_percentage": analysis.get("efficiency_percentage", 0),
                "league_plans": serializable_plans
            },
            "strategy": analysis.get("strategy"),
            "total_matches": analysis.get("total_matches_to_scrape", 0),
            "total_requests": analysis.get("total_estimated_requests", 0),
            "efficiency": analysis.get("efficiency_percentage", 0)
        }
        
        # Save to results file
        results_file = "logs/scraping_results.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        try:
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"✅ Results saved to: {results_file}")
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
    
    def generate_final_summary(self, analysis: Dict, success: bool):
        """Generate final summary of scraping operation"""
        
        logger.info(f"\n📊 Final Summary:")
        logger.info(f"   Success: {'✅' if success else '❌'}")
        logger.info(f"   Strategy: {analysis.get('strategy', 'Unknown')}")
        logger.info(f"   Total Matches: {analysis.get('total_matches_to_scrape', 0)}")
        logger.info(f"   Estimated Requests: {analysis.get('total_estimated_requests', 0)}")
        logger.info(f"   Efficiency: {analysis.get('efficiency_percentage', 0):.1f}%")
        logger.info(f"   Reason: {analysis.get('reason', 'Unknown')}")

def main():
    """Main entry point for the master scraper"""
    
    parser = argparse.ArgumentParser(description="Unified Intelligent Scraper")
    parser.add_argument("--league", help="Specific league to scrape")
    parser.add_argument("--force-full", action="store_true", help="Force full scraping")
    parser.add_argument("--force-incremental", action="store_true", help="Force incremental scraping")
    parser.add_argument("--environment", choices=["local", "staging", "production"], default="local", help="Environment")
    
    args = parser.parse_args()
    
    logger.info(f"\n🎯 Master Scraper Started")
    logger.info(f"   Time: {datetime.now()}")
    logger.info(f"   Environment: {args.environment}")
    logger.info(f"   League: {args.league or 'All leagues'}")
    logger.info(f"   Force Full: {args.force_full}")
    logger.info(f"   Force Incremental: {args.force_incremental}")
    
    # Initialize scraper
    scraper = MasterScraper()
    
    # Run scraping step
    success = scraper.run_scraping_step(
        league=args.league,
        force_full=args.force_full,
        force_incremental=args.force_incremental
    )
    
    # Generate analysis for summary
    analysis = scraper.analyze_scraping_strategy(
        league=args.league,
        force_full=args.force_full,
        force_incremental=args.force_incremental
    )
    
    # Save results and generate summary
    scraper.save_detailed_results(analysis, success)
    scraper.generate_final_summary(analysis, success)
    
    if success:
        logger.info(f"\n✅ Master scraper completed successfully")
        return 0
    else:
        logger.error(f"\n❌ Master scraper failed")
        return 1

if __name__ == "__main__":
    exit(main()) 