#!/usr/bin/env python3
"""
Test Master Import Script for Rally Platform
============================================

Test version that validates the import flow without running actual imports.
Useful for testing the notification system and script structure.

Usage:
    python data/etl/database_import/master_import_test.py [--environment staging|production]
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/master_import_test.log"),
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

ADMIN_PHONE = "7732138911"

class TestMasterImporter:
    """Test master importer that simulates the import process"""

    # Available leagues
    AVAILABLE_LEAGUES = ["APTA_CHICAGO", "NSTF", "CNSWPL", "CITA"]

    def __init__(self, environment="staging", league=None):
        self.environment = environment
        self.league = league
        self.start_time = datetime.now()
        self.results = {}
        self.failures = []

        # Build test import steps dynamically
        self.import_steps = self._build_test_steps()

    def _build_test_steps(self):
        """Build test import steps based on league parameter"""
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
            # All leagues mode (limited to 2 for testing)
            for league in self.AVAILABLE_LEAGUES[:2]:  # Only test first 2 leagues
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
    
    def test_import_step(self, step):
        """Test a single import step (simulated)"""
        step_name = step["name"]
        script_path = step["script"]
        args = step["args"]
        description = step["description"]
        
        logger.info(f"🧪 Testing: {step_name}")
        logger.info(f"📝 Description: {description}")
        logger.info(f"🔧 Script: {script_path}")
        logger.info(f"⚙️ Arguments: {args}")
        
        start_time = datetime.now()
        
        # Simulate script execution
        time.sleep(2)  # Simulate processing time
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Simulate success/failure (alternate for testing)
        step_index = self.import_steps.index(step)
        success = step_index != 1  # Make step 2 fail for testing
        
        if success:
            # Success
            success_msg = f"✅ {step_name} test completed successfully in {duration}"
            logger.info(success_msg)
            
            # Send success notification
            notification = f"🧪 Rally ETL Test: {step_name} ✅\nDuration: {duration}\nEnvironment: {self.environment}"
            self.send_notification(notification)
            
            self.results[step_name] = {
                "status": "success",
                "duration": duration,
                "output": f"Test output for {step_name}",
                "error": ""
            }
            
            return True
        else:
            # Failure (simulated)
            error_msg = f"❌ {step_name} test failed after {duration}"
            logger.error(error_msg)
            
            # Send immediate failure notification
            failure_notification = f"🚨 Rally ETL Test FAILURE: {step_name}\nError: Simulated test failure\nEnvironment: {self.environment}"
            self.send_notification(failure_notification, is_failure=True)
            
            self.results[step_name] = {
                "status": "failed",
                "duration": duration,
                "output": "",
                "error": "Simulated test failure"
            }
            
            self.failures.append(step_name)
            return False
    
    def run_test_imports(self):
        """Run all test import steps"""
        logger.info("🧪 Master Import Test Script Starting")
        logger.info("=" * 60)
        logger.info(f"🌍 Environment: {self.environment}")
        if self.league:
            logger.info(f"🏆 League Mode: Single League ({self.league})")
        else:
            logger.info(f"🏆 League Mode: All Leagues (Testing first 2: {', '.join(self.AVAILABLE_LEAGUES[:2])})")
        logger.info(f"📱 Admin Phone: {ADMIN_PHONE}")
        logger.info(f"🕐 Start Time: {self.start_time}")
        logger.info("=" * 60)
        
        # Send start notification
        start_notification = f"🧪 Rally ETL Master Import Test Starting\nEnvironment: {self.environment}\nTime: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_notification(start_notification)
        
        # Run each test step
        for i, step in enumerate(self.import_steps, 1):
            logger.info(f"\n📋 Test Step {i}/{len(self.import_steps)}: {step['name']}")
            logger.info("-" * 50)
            
            success = self.test_import_step(step)
            
            if not success:
                logger.warning(f"⚠️ {step['name']} test failed, but continuing with next step...")
            
            # Brief pause between steps
            if i < len(self.import_steps):
                logger.info("⏳ Pausing 2 seconds before next test step...")
                time.sleep(2)
        
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
            "📊 Rally ETL Master Import Test Summary",
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
        logger.info("📊 FINAL TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(summary)
        
        # Send final notification
        if failed_steps == 0:
            final_notification = f"🎉 Rally ETL Test Complete!\n{successful_steps}/{total_steps} steps successful\nDuration: {total_duration}\nEnvironment: {self.environment}"
        else:
            final_notification = f"⚠️ Rally ETL Test Complete with Issues\n{successful_steps}/{total_steps} steps successful\nFailures: {', '.join(self.failures)}\nDuration: {total_duration}\nEnvironment: {self.environment}"
        
        self.send_notification(final_notification)
        
        # Save detailed results to file
        self.save_detailed_results()
    
    def save_detailed_results(self):
        """Save detailed results to log file"""
        results_file = f"logs/master_import_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(results_file, 'w') as f:
            f.write("Rally ETL Master Import Test Detailed Results\n")
            f.write("=" * 50 + "\n")
            f.write(f"Environment: {self.environment}\n")
            f.write(f"Start Time: {self.start_time}\n")
            f.write(f"End Time: {datetime.now()}\n")
            f.write(f"Total Duration: {datetime.now() - self.start_time}\n\n")
            
            for step_name, result in self.results.items():
                f.write(f"Step: {step_name}\n")
                f.write(f"Status: {result['status']}\n")
                f.write(f"Duration: {result['duration']}\n")
                f.write(f"Output: {result['output']}\n")
                if result['error']:
                    f.write(f"Error: {result['error']}\n")
                f.write("-" * 30 + "\n")
        
        logger.info(f"📄 Detailed test results saved to: {results_file}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test Master ETL Import Script")
    parser.add_argument(
        "--environment",
        choices=["staging", "production"],
        default="staging",
        help="Environment to test imports for"
    )
    parser.add_argument(
        "--league",
        choices=["APTA_CHICAGO", "NSTF", "CNSWPL", "CITA", "aptachicago", "nstf", "cnswpl", "cita"],
        help="Specific league to test (if not specified, tests first 2 leagues)"
    )

    args = parser.parse_args()

    # Normalize league argument
    league = None
    if args.league:
        league = args.league.upper()

    try:
        # Create and run test master importer
        importer = TestMasterImporter(environment=args.environment, league=league)
        importer.run_test_imports()

        # Exit with appropriate code
        if importer.failures:
            logger.error(f"❌ Master import test completed with {len(importer.failures)} failures")
            sys.exit(1)
        else:
            logger.info("✅ Master import test completed successfully")
            sys.exit(0)
            
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 