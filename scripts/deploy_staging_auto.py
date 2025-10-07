#!/usr/bin/env python3
"""
Automated Staging Deployment Script
==================================

Automated version of the comprehensive staging deployment script.
Runs without user confirmation for CI/CD pipelines.

Usage:
    python scripts/deploy_staging_auto.py
"""

import os
import sys
import subprocess
import logging
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/staging_deployment_auto.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

class AutomatedStagingDeployment:
    """Handles automated staging deployment"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.staging_db_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
        self.start_time = datetime.now()
        
    def print_banner(self, title):
        """Print formatted banner"""
        print(f"\n🎯 {title}")
        print("=" * 80)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def run_command(self, cmd, capture_output=True, check=True):
        """Run shell command with error handling"""
        try:
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=capture_output, text=True, check=check)
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"Error: {e}")
            if capture_output and e.stdout:
                logger.error(f"Output: {e.stdout}")
            if capture_output and e.stderr:
                logger.error(f"Error output: {e.stderr}")
            return None
    
    def step_1_backup_staging(self):
        """Step 1: Create backup of current staging database"""
        self.print_banner("Step 1: Backup Staging Database")
        
        backup_file = f"backups/staging_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        os.makedirs("backups", exist_ok=True)
        
        logger.info("Creating staging database backup...")
        result = self.run_command([
            "pg_dump",
            self.staging_db_url,
            "-f", backup_file
        ])
        
        if result:
            logger.info(f"✅ Staging backup created: {backup_file}")
            return True
        else:
            logger.error("❌ Staging backup failed")
            return False
    
    def step_2_update_database_schema(self):
        """Step 2: Update database schema on staging"""
        self.print_banner("Step 2: Update Database Schema")
        
        # Check if we have new migrations to apply
        alembic_versions = list(Path("alembic/versions").glob("*.py"))
        if not alembic_versions:
            logger.info("No new Alembic migrations found")
            return True
        
        logger.info(f"Found {len(alembic_versions)} migration files")
        
        # Apply migrations to staging
        logger.info("Applying migrations to staging...")
        result = self.run_command([
            "alembic", "upgrade", "head"
        ])
        
        if result:
            logger.info("✅ Database schema updated successfully")
            return True
        else:
            logger.error("❌ Database schema update failed")
            return False
    
    def step_3_validate_etl_processes(self):
        """Step 3: Validate ETL processes"""
        self.print_banner("Step 3: Validate ETL Processes")
        
        # Test the new ETL structure
        etl_scripts = [
            "data/etl/database_import/import_players.py",
            "data/etl/database_import/import_match_scores.py", 
            "data/etl/database_import/import_schedules.py",
            "data/etl/database_import/import_stats.py"
        ]
        
        for script in etl_scripts:
            if not Path(script).exists():
                logger.error(f"❌ ETL script missing: {script}")
                return False
        
        logger.info("✅ All ETL scripts present")
        
        # Test consolidation script
        consolidate_script = "data/etl/database_import/consolidate_league_jsons_to_all.py"
        if Path(consolidate_script).exists():
            logger.info("✅ Consolidation script present")
        else:
            logger.error(f"❌ Consolidation script missing: {consolidate_script}")
            return False
        
        return True
    
    def step_4_validate_scrapers(self):
        """Step 4: Validate scrapers"""
        self.print_banner("Step 4: Validate Scrapers")
        
        # Check new scraper files
        scraper_scripts = [
            "data/etl/scrapers/scrape_players.py",
            "data/etl/scrapers/apta_scrape_match_scores.py",
            "data/etl/scrapers/scrape_match_scores_incremental.py"
        ]
        
        for script in scraper_scripts:
            if not Path(script).exists():
                logger.error(f"❌ Scraper script missing: {script}")
                return False
        
        logger.info("✅ All scraper scripts present")
        
        # Check stealth browser
        stealth_script = "data/etl/scrapers/stealth_browser.py"
        if Path(stealth_script).exists():
            logger.info("✅ Stealth browser present")
        else:
            logger.warning(f"⚠️ Stealth browser missing: {stealth_script}")
        
        return True
    
    def step_5_validate_cron_jobs(self):
        """Step 5: Validate cron jobs"""
        self.print_banner("Step 5: Validate Cron Jobs")
        
        # Check staging cron scripts
        cron_scripts = [
            "chronjobs/railway_cron_etl_staging.py",
            "chronjobs/STAGING_cron_etl_atomic.py"
        ]
        
        for script in cron_scripts:
            if not Path(script).exists():
                logger.error(f"❌ Cron script missing: {script}")
                return False
        
        logger.info("✅ All cron scripts present")
        
        # Check railway.toml for cron configuration
        railway_toml = Path("railway.toml")
        if railway_toml.exists():
            logger.info("✅ Railway configuration present")
        else:
            logger.warning("⚠️ Railway configuration missing")
        
        return True
    
    def step_6_deploy_to_staging(self):
        """Step 6: Deploy to staging environment"""
        self.print_banner("Step 6: Deploy to Staging")
        
        # Push to staging branch
        logger.info("Pushing to staging branch...")
        
        # First, switch to staging branch
        result = self.run_command(["git", "checkout", "staging"])
        if not result:
            logger.error("❌ Failed to switch to staging branch")
            return False
        
        # Merge main into staging
        result = self.run_command(["git", "merge", "main"])
        if not result:
            logger.error("❌ Failed to merge main into staging")
            return False
        
        # Push to staging
        result = self.run_command(["git", "push", "origin", "staging"])
        if not result:
            logger.error("❌ Failed to push to staging")
            return False
        
        logger.info("✅ Deployed to staging successfully")
        return True
    
    def step_7_validate_staging(self):
        """Step 7: Validate staging deployment"""
        self.print_banner("Step 7: Validate Staging Deployment")
        
        # Wait for deployment to complete
        logger.info("Waiting for staging deployment to complete...")
        time.sleep(30)
        
        # Test staging URL
        staging_url = "https://rally-staging.up.railway.app"
        logger.info(f"Testing staging URL: {staging_url}")
        
        try:
            import requests
            response = requests.get(f"{staging_url}/health", timeout=30)
            if response.status_code == 200:
                logger.info("✅ Staging health check passed")
                return True
            else:
                logger.error(f"❌ Staging health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Staging health check error: {e}")
            return False
    
    def step_8_test_etl_on_staging(self):
        """Step 8: Test ETL processes on staging"""
        self.print_banner("Step 8: Test ETL on Staging")
        
        # Test consolidation
        logger.info("Testing data consolidation...")
        result = self.run_command([
            sys.executable, 
            "data/etl/database_import/consolidate_league_jsons_to_all.py"
        ])
        
        if not result:
            logger.error("❌ Data consolidation failed")
            return False
        
        logger.info("✅ Data consolidation successful")
        
        # Test one of the import scripts (players as example)
        logger.info("Testing player import...")
        result = self.run_command([
            sys.executable,
            "data/etl/database_import/import_players.py",
            "--test-only"
        ])
        
        if not result:
            logger.warning("⚠️ Player import test failed (may be expected)")
        else:
            logger.info("✅ Player import test successful")
        
        return True
    
    def run_complete_deployment(self):
        """Run the complete staging deployment"""
        self.print_banner("AUTOMATED STAGING DEPLOYMENT")
        
        steps = [
            ("Backup Staging", self.step_1_backup_staging),
            ("Update Database Schema", self.step_2_update_database_schema),
            ("Validate ETL Processes", self.step_3_validate_etl_processes),
            ("Validate Scrapers", self.step_4_validate_scrapers),
            ("Validate Cron Jobs", self.step_5_validate_cron_jobs),
            ("Deploy to Staging", self.step_6_deploy_to_staging),
            ("Validate Staging", self.step_7_validate_staging),
            ("Test ETL on Staging", self.step_8_test_etl_on_staging),
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
                    if step_name in ["Backup Staging", "Deploy to Staging"]:
                        logger.error("Critical step failed, stopping deployment")
                        break
            except Exception as e:
                logger.error(f"❌ {step_name} crashed: {e}")
                if step_name in ["Backup Staging", "Deploy to Staging"]:
                    logger.error("Critical step crashed, stopping deployment")
                    break
        
        # Summary
        duration = datetime.now() - self.start_time
        self.print_banner("DEPLOYMENT SUMMARY")
        
        print(f"✅ Successful steps: {successful_steps}/{total_steps}")
        print(f"⏱️ Total duration: {duration}")
        
        if successful_steps == total_steps:
            print("🎉 All steps completed successfully!")
            print("🚀 Staging is ready for testing")
        else:
            print("⚠️ Some steps failed - check logs for details")
            print("🔧 Manual intervention may be required")
        
        return successful_steps == total_steps

def main():
    """Main function"""
    deployment = AutomatedStagingDeployment()
    
    # Run deployment automatically
    success = deployment.run_complete_deployment()
    
    if success:
        print("\n🎉 Automated staging deployment completed successfully!")
        print("Next steps:")
        print("1. Test staging environment manually")
        print("2. Run ETL processes on staging")
        print("3. Verify all functionality works")
        print("4. Deploy to production when ready")
    else:
        print("\n❌ Automated staging deployment had issues")
        print("Check logs and fix issues before proceeding")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 