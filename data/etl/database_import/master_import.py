#!/usr/bin/env python3
"""
Master Import Script for Rally Platform
=======================================

Runs all ETL imports in the correct order with SMS notifications:
1. Consolidate league JSONs to all
2. Import stats
3. Import match scores
4. Import players

Sends detailed status messages to admin (7732138911) after each step.
Sends immediate failure notifications if any import fails.

Usage:
    python data/etl/database_import/master_import.py [--environment staging|production]
"""

import argparse
import logging
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/master_import.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

# Import SMS notification service
try:
    from app.services.notifications_service import send_sms
except ImportError:
    logger.warning("SMS service not available, notifications will be logged only")
    send_sms = None

ADMIN_PHONE = "17736121115"

class MasterImporter:
    """Master importer that orchestrates all ETL processes"""
    
    # Available leagues
    AVAILABLE_LEAGUES = ["APTA_CHICAGO", "NSTF", "CNSWPL", "CITA"]
    
    def __init__(self, environment="staging", league=None):
        self.environment = environment
        self.league = league
        self.start_time = datetime.now()
        self.results = {}
        self.failures = []
        
        # Build import steps dynamically based on league parameter
        self.import_steps = self._build_import_steps()
    
    def _build_import_steps(self):
        """Build import steps based on league parameter"""
        steps = []
        
        # Always include consolidation step
        steps.append({
            "name": "Consolidate League JSONs",
            "script": "data/etl/database_import/consolidate_league_jsons_to_all.py",
            "args": [],
            "description": "Consolidate all league JSON files into unified data"
        })
        
        # Add stats import steps based on league parameter
        if self.league:
            # Single league mode
            if self.league.upper() not in self.AVAILABLE_LEAGUES:
                raise ValueError(f"Invalid league: {self.league}. Available leagues: {', '.join(self.AVAILABLE_LEAGUES)}")
            
            steps.append({
                "name": f"Import Stats - {self.league.upper()}",
                "script": "data/etl/database_import/import_stats.py",
                "args": [self.league.upper()],
                "description": f"Import series statistics for {self.league.upper()}"
            })
        else:
            # All leagues mode
            for league in self.AVAILABLE_LEAGUES:
                steps.append({
                    "name": f"Import Stats - {league}",
                    "script": "data/etl/database_import/import_stats.py",
                    "args": [league],
                    "description": f"Import series statistics for {league}"
                })
        
        # Always include match scores and players import
        steps.extend([
            {
                "name": "Import Match Scores",
                "script": "data/etl/database_import/import_match_scores.py",
                "args": [],
                "description": "Import match scores and results"
            },
            {
                "name": "Import Players",
                "script": "data/etl/database_import/import_players.py",
                "args": [],
                "description": "Import player data and associations"
            }
        ])
        
        return steps
    
    def send_notification(self, message, is_failure=False):
        """Send SMS notification to admin"""
        try:
            if send_sms:
                send_sms(ADMIN_PHONE, message)
                logger.info(f"📱 SMS sent to admin: {message[:100]}...")
            else:
                logger.info(f"📱 SMS notification (mock): {message}")
        except Exception as e:
            logger.error(f"❌ Failed to send SMS: {e}")
    
    def run_import_step(self, step):
        """Run a single import step"""
        step_name = step["name"]
        script_path = step["script"]
        args = step["args"]
        description = step["description"]
        
        logger.info(f"🚀 Starting: {step_name}")
        logger.info(f"📝 Description: {description}")
        logger.info(f"🔧 Script: {script_path}")
        logger.info(f"⚙️ Arguments: {args}")
        
        # Build command
        cmd = ["python3", script_path] + args
        
        start_time = datetime.now()
        
        try:
            # Run the import script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            if result.returncode == 0:
                # Success
                success_msg = f"✅ {step_name} completed successfully in {duration}"
                logger.info(success_msg)
                
                # Send success notification
                notification = f"Rally ETL: {step_name} ✅\nDuration: {duration}\nEnvironment: {self.environment}"
                self.send_notification(notification)
                
                self.results[step_name] = {
                    "status": "success",
                    "duration": duration,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
                return True
            else:
                # Failure
                error_msg = f"❌ {step_name} failed after {duration}"
                logger.error(error_msg)
                logger.error(f"Error output: {result.stderr}")
                
                # Send immediate failure notification
                failure_notification = f"🚨 Rally ETL FAILURE: {step_name}\nError: {result.stderr[:200]}...\nEnvironment: {self.environment}"
                self.send_notification(failure_notification, is_failure=True)
                
                self.results[step_name] = {
                    "status": "failed",
                    "duration": duration,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
                self.failures.append(step_name)
                return False
                
        except subprocess.TimeoutExpired:
            # Timeout
            timeout_msg = f"⏰ {step_name} timed out after 1 hour"
            logger.error(timeout_msg)
            
            timeout_notification = f"⏰ Rally ETL TIMEOUT: {step_name}\nEnvironment: {self.environment}"
            self.send_notification(timeout_notification, is_failure=True)
            
            self.results[step_name] = {
                "status": "timeout",
                "duration": "1 hour+",
                "output": "",
                "error": "Script timed out after 1 hour"
            }
            
            self.failures.append(step_name)
            return False
            
        except Exception as e:
            # Unexpected error
            error_msg = f"💥 {step_name} failed with unexpected error: {e}"
            logger.error(error_msg)
            
            error_notification = f"💥 Rally ETL ERROR: {step_name}\nError: {str(e)}\nEnvironment: {self.environment}"
            self.send_notification(error_notification, is_failure=True)
            
            self.results[step_name] = {
                "status": "error",
                "duration": "unknown",
                "output": "",
                "error": str(e)
            }
            
            self.failures.append(step_name)
            return False
    
    def run_all_imports(self):
        """Run all import steps in order"""
        logger.info("🎯 Master Import Script Starting")
        logger.info("=" * 60)
        logger.info(f"🌍 Environment: {self.environment}")
        if self.league:
            logger.info(f"🏆 League Mode: Single League ({self.league})")
        else:
            logger.info(f"🏆 League Mode: All Leagues ({', '.join(self.AVAILABLE_LEAGUES)})")
        logger.info(f"📱 Admin Phone: {ADMIN_PHONE}")
        logger.info(f"🕐 Start Time: {self.start_time}")
        logger.info("=" * 60)
        
        # Send start notification
        start_notification = f"🚀 Rally ETL Master Import Starting\nEnvironment: {self.environment}\nTime: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_notification(start_notification)
        
        # Run each import step
        for i, step in enumerate(self.import_steps, 1):
            logger.info(f"\n📋 Step {i}/{len(self.import_steps)}: {step['name']}")
            logger.info("-" * 50)
            
            success = self.run_import_step(step)
            
            if not success:
                logger.warning(f"⚠️ {step['name']} failed, but continuing with next step...")
            
            # Brief pause between steps
            if i < len(self.import_steps):
                logger.info("⏳ Pausing 5 seconds before next step...")
                time.sleep(5)
        
        # Generate final summary
        self.generate_final_summary()
    
    def generate_final_summary(self):
        """Generate and send final summary"""
        end_time = datetime.now()
        total_duration = end_time - self.start_time
        
        # Count results
        total_steps = len(self.import_steps)
        successful_steps = len([r for r in self.results.values() if r["status"] == "success"])
        failed_steps = len(self.failures)
        
        # Create summary
        summary_lines = [
            "📊 Rally ETL Master Import Summary",
            f"Environment: {self.environment}",
            f"Total Duration: {total_duration}",
            f"Steps: {successful_steps}/{total_steps} successful",
            f"Failures: {failed_steps}"
        ]
        
        if self.failures:
            summary_lines.append(f"Failed Steps: {', '.join(self.failures)}")
        
        summary = "\n".join(summary_lines)
        
        # Log summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 60)
        logger.info(summary)
        
        # Send final notification
        if failed_steps == 0:
            final_notification = f"🎉 Rally ETL Complete!\n{successful_steps}/{total_steps} steps successful\nDuration: {total_duration}\nEnvironment: {self.environment}"
        else:
            final_notification = f"⚠️ Rally ETL Complete with Issues\n{successful_steps}/{total_steps} steps successful\nFailures: {', '.join(self.failures)}\nDuration: {total_duration}\nEnvironment: {self.environment}"
        
        self.send_notification(final_notification)
        
        # Save detailed results to file
        self.save_detailed_results()
    
    def save_detailed_results(self):
        """Save detailed results to log file"""
        results_file = f"logs/master_import_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(results_file, 'w') as f:
            f.write("Rally ETL Master Import Detailed Results\n")
            f.write(f"Environment: {self.environment}\n")
            f.write(f"Start Time: {self.start_time}\n")
            f.write(f"End Time: {datetime.now()}\n")
            f.write(f"Total Duration: {datetime.now() - self.start_time}\n\n")
            
            for step_name, result in self.results.items():
                f.write(f"Step: {step_name}\n")
                f.write(f"Status: {result['status']}\n")
                f.write(f"Duration: {result['duration']}\n")
                f.write(f"Output: {result['output'][:500]}...\n")
                if result['error']:
                    f.write(f"Error: {result['error']}\n")
                f.write("-" * 30 + "\n")
        
        logger.info(f"📄 Detailed results saved to: {results_file}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Master ETL Import Script")
    parser.add_argument(
        "--environment",
        choices=["staging", "production"],
        default="staging",
        help="Environment to run imports for"
    )
    parser.add_argument(
        "--league",
        choices=["APTA_CHICAGO", "NSTF", "CNSWPL", "CITA", "aptachicago", "nstf", "cnswpl", "cita"],
        help="Specific league to import (if not specified, imports all leagues)"
    )
    
    args = parser.parse_args()
    
    # Normalize league argument
    league = None
    if args.league:
        league = args.league.upper()
    
    try:
        # Create and run master importer
        importer = MasterImporter(environment=args.environment, league=league)
        importer.run_all_imports()
        
        # Exit with appropriate code
        if importer.failures:
            logger.error(f"❌ Master import completed with {len(importer.failures)} failures")
            sys.exit(1)
        else:
            logger.info("✅ Master import completed successfully")
            sys.exit(0)
            
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 