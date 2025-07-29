#!/usr/bin/env python3
"""
Master ETL Script for Rally Platform
====================================

Orchestrates the complete ETL process using the new modular structure:
1. Data consolidation
2. Player import
3. Match scores import
4. Schedules import
5. Stats import

Usage:
    python data/etl/database_import/master_etl.py [--environment staging|production] [--full-import]
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/master_etl.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

class MasterETL:
    """Master ETL orchestrator"""
    
    def __init__(self, environment="staging", full_import=False):
        self.environment = environment
        self.full_import = full_import
        self.start_time = datetime.now()
        self.project_root = Path(__file__).parent.parent.parent.parent
        
        # Set environment variables
        if environment == "staging":
            os.environ["RAILWAY_ENVIRONMENT"] = "staging"
            os.environ["DATABASE_URL"] = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
        elif environment == "production":
            os.environ["RAILWAY_ENVIRONMENT"] = "production"
            os.environ["DATABASE_URL"] = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        
        logger.info(f"🎯 Master ETL initialized for {environment} environment")
        logger.info(f"📊 Full import mode: {full_import}")
    
    def print_banner(self, title):
        """Print formatted banner"""
        print(f"\n🎯 {title}")
        print("=" * 60)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def step_1_consolidate_data(self):
        """Step 1: Consolidate league data"""
        self.print_banner("Step 1: Consolidate League Data")
        
        consolidate_script = self.project_root / "data" / "etl" / "database_import" / "consolidate_league_jsons_to_all.py"
        
        if not consolidate_script.exists():
            logger.error(f"❌ Consolidation script not found: {consolidate_script}")
            return False
        
        logger.info("Running data consolidation...")
        
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, str(consolidate_script)
            ], capture_output=True, text=True, check=True)
            
            logger.info("✅ Data consolidation completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Data consolidation failed: {e}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            return False
    
    def step_2_import_players(self):
        """Step 2: Import player data"""
        self.print_banner("Step 2: Import Player Data")
        
        import_script = self.project_root / "data" / "etl" / "database_import" / "import_players.py"
        
        if not import_script.exists():
            logger.error(f"❌ Player import script not found: {import_script}")
            return False
        
        logger.info("Running player import...")
        
        try:
            import subprocess
            cmd = [sys.executable, str(import_script)]
            if self.full_import:
                cmd.append("--full-import")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info("✅ Player import completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Player import failed: {e}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            return False
    
    def step_3_import_match_scores(self):
        """Step 3: Import match scores"""
        self.print_banner("Step 3: Import Match Scores")
        
        import_script = self.project_root / "data" / "etl" / "database_import" / "import_match_scores.py"
        
        if not import_script.exists():
            logger.error(f"❌ Match scores import script not found: {import_script}")
            return False
        
        logger.info("Running match scores import...")
        
        try:
            import subprocess
            cmd = [sys.executable, str(import_script)]
            if self.full_import:
                cmd.append("--full-import")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info("✅ Match scores import completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Match scores import failed: {e}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            return False
    
    def step_4_import_schedules(self):
        """Step 4: Import schedules"""
        self.print_banner("Step 4: Import Schedules")
        
        import_script = self.project_root / "data" / "etl" / "database_import" / "import_schedules.py"
        
        if not import_script.exists():
            logger.error(f"❌ Schedules import script not found: {import_script}")
            return False
        
        logger.info("Running schedules import...")
        
        try:
            import subprocess
            cmd = [sys.executable, str(import_script)]
            if self.full_import:
                cmd.append("--full-import")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info("✅ Schedules import completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Schedules import failed: {e}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            return False
    
    def step_5_import_stats(self):
        """Step 5: Import statistics"""
        self.print_banner("Step 5: Import Statistics")
        
        import_script = self.project_root / "data" / "etl" / "database_import" / "import_stats.py"
        
        if not import_script.exists():
            logger.error(f"❌ Stats import script not found: {import_script}")
            return False
        
        logger.info("Running statistics import...")
        
        try:
            import subprocess
            cmd = [sys.executable, str(import_script)]
            if self.full_import:
                cmd.append("--full-import")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info("✅ Statistics import completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Statistics import failed: {e}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            return False
    
    def step_6_validate_import(self):
        """Step 6: Validate import results"""
        self.print_banner("Step 6: Validate Import Results")
        
        try:
            # Import database utilities
            sys.path.append(str(self.project_root))
            from database_config import get_db
            
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Check table counts
                tables = ["players", "match_scores", "schedule", "series_stats"]
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    logger.info(f"📊 {table}: {count:,} records")
                
                # Check for any obvious issues
                cursor.execute("SELECT COUNT(*) FROM players WHERE tenniscores_player_id IS NULL")
                null_players = cursor.fetchone()[0]
                if null_players > 0:
                    logger.warning(f"⚠️ Found {null_players} players with null tenniscores_player_id")
                
                cursor.execute("SELECT COUNT(*) FROM match_scores WHERE home_team_id IS NULL OR away_team_id IS NULL")
                null_teams = cursor.fetchone()[0]
                if null_teams > 0:
                    logger.warning(f"⚠️ Found {null_teams} matches with null team IDs")
                
                logger.info("✅ Import validation completed")
                return True
                
        except Exception as e:
            logger.error(f"❌ Import validation failed: {e}")
            return False
    
    def run_complete_etl(self):
        """Run the complete ETL process"""
        self.print_banner("MASTER ETL PROCESS")
        
        steps = [
            ("Consolidate Data", self.step_1_consolidate_data),
            ("Import Players", self.step_2_import_players),
            ("Import Match Scores", self.step_3_import_match_scores),
            ("Import Schedules", self.step_4_import_schedules),
            ("Import Statistics", self.step_5_import_stats),
            ("Validate Import", self.step_6_validate_import),
        ]
        
        successful_steps = 0
        total_steps = len(steps)
        
        for step_name, step_func in steps:
            logger.info(f"\n🔄 Running: {step_name}")
            try:
                if step_func():
                    successful_steps += 1
                    logger.info(f"✅ {step_name} completed successfully")
                else:
                    logger.error(f"❌ {step_name} failed")
                    # Continue with other steps unless it's critical
                    if step_name in ["Consolidate Data"]:
                        logger.error("Critical step failed, stopping ETL")
                        break
            except Exception as e:
                logger.error(f"❌ {step_name} crashed: {e}")
                if step_name in ["Consolidate Data"]:
                    logger.error("Critical step crashed, stopping ETL")
                    break
        
        # Summary
        duration = datetime.now() - self.start_time
        self.print_banner("ETL SUMMARY")
        
        print(f"✅ Successful steps: {successful_steps}/{total_steps}")
        print(f"⏱️ Total duration: {duration}")
        print(f"🌍 Environment: {self.environment}")
        print(f"📊 Full import: {self.full_import}")
        
        if successful_steps == total_steps:
            print("🎉 All ETL steps completed successfully!")
            print("🚀 Data is ready for use")
        else:
            print("⚠️ Some ETL steps failed - check logs for details")
            print("🔧 Manual intervention may be required")
        
        return successful_steps == total_steps

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Master ETL for Rally Platform")
    parser.add_argument(
        "--environment", 
        choices=["staging", "production"], 
        default="staging",
        help="Target environment (default: staging)"
    )
    parser.add_argument(
        "--full-import",
        action="store_true",
        help="Perform full import (clear existing data)"
    )
    
    args = parser.parse_args()
    
    # Confirm for production
    if args.environment == "production":
        print("🚨 PRODUCTION ETL WARNING")
        print("This will modify the production database.")
        response = input("Continue with production ETL? (y/n): ")
        if response.lower() != 'y':
            print("Production ETL cancelled")
            return
    
    # Run ETL
    etl = MasterETL(environment=args.environment, full_import=args.full_import)
    success = etl.run_complete_etl()
    
    if success:
        print(f"\n🎉 {args.environment.title()} ETL completed successfully!")
        print("Next steps:")
        print("1. Verify data integrity")
        print("2. Test application functionality")
        print("3. Monitor for any issues")
    else:
        print(f"\n❌ {args.environment.title()} ETL had issues")
        print("Check logs and fix issues before proceeding")

if __name__ == "__main__":
    main() 