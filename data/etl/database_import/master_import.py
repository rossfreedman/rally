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

ADMIN_PHONE = "17732138911"

class MasterImporter:
    """Master importer that orchestrates all ETL processes"""
    
    # Legacy hardcoded leagues for backward compatibility
    LEGACY_LEAGUES = ["APTA_CHICAGO", "NSTF", "CNSWPL", "CITA"]
    
    # League name mapping for case-insensitive input
    LEAGUE_MAPPING = {
        "APTACHICAGO": "APTA_CHICAGO",
        "aptachicago": "APTA_CHICAGO",
        "NSTF": "NSTF",
        "nstf": "NSTF",
        "CNSWPL": "CNSWPL",
        "cnswpl": "CNSWPL",
        "CITA": "CITA",
        "cita": "CITA"
    }
    
    def __init__(self, environment="staging", league=None):
        self.environment = environment
        self.league = league
        self.start_time = datetime.now()
        self.results = {}
        self.failures = []
        
        # Discover available leagues dynamically
        self.available_leagues = self._discover_available_leagues()
        
        # Build import steps dynamically based on league parameter
        self.import_steps = self._build_import_steps()
    
    def _discover_available_leagues(self):
        """Dynamically discover available leagues from data/leagues/ directory"""
        try:
            # Get the project root directory
            project_root = Path(__file__).parent.parent.parent.parent
            leagues_dir = project_root / "data" / "leagues"
            
            if not leagues_dir.exists():
                logger.warning(f"Leagues directory not found: {leagues_dir}")
                logger.info("Falling back to legacy hardcoded leagues")
                return self.LEGACY_LEAGUES
            
            # Discover league directories (excluding 'all' directory)
            available_leagues = []
            for item in leagues_dir.iterdir():
                if item.is_dir() and item.name != "all" and not item.name.startswith("."):
                    available_leagues.append(item.name)
            
            if not available_leagues:
                logger.warning("No league directories found, falling back to legacy leagues")
                return self.LEGACY_LEAGUES
            
            # Sort for consistent ordering
            available_leagues.sort()
            logger.info(f"Discovered {len(available_leagues)} leagues: {', '.join(available_leagues)}")
            return available_leagues
            
        except Exception as e:
            logger.error(f"Error discovering leagues: {e}")
            logger.info("Falling back to legacy hardcoded leagues")
            return self.LEGACY_LEAGUES
    
    def _build_import_steps(self):
        """Build import steps based on league parameter"""
        steps = []
        
        # Always include consolidation step
        steps.append({
            "name": "Consolidate League JSONs",
            "script": "consolidate_league_jsons.py",
            "args": [],
            "description": "Consolidate all league JSON files into unified data"
        })
        
        # Add stats import steps based on league parameter
        if self.league:
            # Single league mode - normalize league name
            normalized_league = self.LEAGUE_MAPPING.get(self.league, self.league)
            if normalized_league not in self.available_leagues:
                raise ValueError(f"Invalid league: {self.league}. Available leagues: {', '.join(self.available_leagues)}")
            
            steps.append({
                "name": f"Import Stats - {normalized_league}",
                "script": "import_stats.py",
                "args": [normalized_league],
                "description": f"Import series statistics for {normalized_league}"
            })
        else:
            # All leagues mode
            for league in self.available_leagues:
                steps.append({
                    "name": f"Import Stats - {league}",
                    "script": "import_stats.py",
                    "args": [league],
                    "description": f"Import series statistics for {league}"
                })
        
        # Always include match scores and players import
        steps.extend([
            {
                "name": "Import Match Scores",
                "script": "import_match_scores.py",
                "args": [],
                "description": "Import match scores and results"
            },
            {
                "name": "Import Players",
                "script": "import_players.py",
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
        
        # Build command - handle both local and Docker environments
        if os.path.exists(script_path):
            # Script exists at the specified path (Docker environment)
            cmd = ["python3", script_path] + args
        else:
            # Try to find script in the same directory as this script (local environment)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            local_script_path = os.path.join(script_dir, os.path.basename(script_path))
            if os.path.exists(local_script_path):
                cmd = ["python3", local_script_path] + args
            else:
                raise FileNotFoundError(f"Script not found: {script_path} or {local_script_path}")
        
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
            logger.info(f"🏆 League Mode: All Leagues ({', '.join(self.available_leagues)})")
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
        """Generate and send final summary with detailed import information"""
        end_time = datetime.now()
        total_duration = end_time - self.start_time
        
        # Count results
        total_steps = len(self.import_steps)
        successful_steps = len([r for r in self.results.values() if r["status"] == "success"])
        failed_steps = len(self.failures)
        
        # Create detailed summary
        summary_lines = [
            "📊 Rally ETL Master Import Summary",
            "=" * 60,
            f"Environment: {self.environment}",
            f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {total_duration}",
            f"Steps: {successful_steps}/{total_steps} successful",
            f"Failures: {failed_steps}",
            ""
        ]
        
        # League information
        if self.league:
            summary_lines.extend([
                "🏆 LEAGUE MODE: Single League",
                f"Target League: {self.league}",
                ""
            ])
        else:
            summary_lines.extend([
                "🏆 LEAGUE MODE: All Leagues",
                f"Available Leagues: {', '.join(self.available_leagues)}",
                ""
            ])
        
        # Step-by-step results
        summary_lines.append("📋 STEP-BY-STEP RESULTS:")
        summary_lines.append("-" * 40)
        
        for i, step in enumerate(self.import_steps, 1):
            step_name = step["name"]
            result = self.results.get(step_name, {"status": "not_run"})
            
            status_emoji = {
                "success": "✅",
                "failed": "❌",
                "timeout": "⏰",
                "error": "💥",
                "not_run": "⏸️"
            }.get(result["status"], "❓")
            
            summary_lines.append(f"{i}. {status_emoji} {step_name}")
            summary_lines.append(f"   Status: {result['status'].upper()}")
            summary_lines.append(f"   Duration: {result.get('duration', 'N/A')}")
            
            # Add specific details for each step type
            if step_name.startswith("Consolidate League JSONs"):
                summary_lines.append("   Action: Merged all league JSON files into unified data structure")
            elif step_name.startswith("Import Stats"):
                league_name = step_name.replace("Import Stats - ", "")
                summary_lines.append(f"   Action: Imported series statistics for {league_name}")
                summary_lines.append("   Data: Team standings, win/loss records, series rankings")
            elif step_name == "Import Match Scores":
                summary_lines.append("   Action: Imported match results and scores")
                summary_lines.append("   Data: Match outcomes, individual set scores, player performance")
            elif step_name == "Import Players":
                summary_lines.append("   Action: Imported player data and associations")
                summary_lines.append("   Data: Player profiles, team assignments, league memberships")
            
            # Add error details if failed
            if result["status"] in ["failed", "timeout", "error"]:
                error_msg = result.get("error", "Unknown error")
                summary_lines.append(f"   Error: {error_msg[:100]}...")
            
            summary_lines.append("")
        
        # What was imported (successful steps)
        if successful_steps > 0:
            summary_lines.append("✅ SUCCESSFULLY IMPORTED:")
            summary_lines.append("-" * 30)
            
            for step_name, result in self.results.items():
                if result["status"] == "success":
                    if step_name.startswith("Consolidate League JSONs"):
                        summary_lines.append("• Unified league data structure")
                        summary_lines.append("  - Combined all league JSON files")
                        summary_lines.append("  - Created standardized data format")
                    elif step_name.startswith("Import Stats"):
                        league_name = step_name.replace("Import Stats - ", "")
                        summary_lines.append(f"• {league_name} statistics")
                        summary_lines.append(f"  - Team standings and rankings")
                        summary_lines.append(f"  - Win/loss records")
                        summary_lines.append(f"  - Series performance data")
                    elif step_name == "Import Match Scores":
                        summary_lines.append("• Match results and scores")
                        summary_lines.append("  - Individual match outcomes")
                        summary_lines.append("  - Set-by-set scores")
                        summary_lines.append("  - Player performance metrics")
                    elif step_name == "Import Players":
                        summary_lines.append("• Player data and associations")
                        summary_lines.append("  - Player profiles and contact info")
                        summary_lines.append("  - Team assignments")
                        summary_lines.append("  - League memberships")
                        summary_lines.append("  - User-player associations")
            
            summary_lines.append("")
        
        # What didn't work (failed steps)
        if failed_steps > 0:
            summary_lines.append("❌ FAILED TO IMPORT:")
            summary_lines.append("-" * 25)
            
            for step_name in self.failures:
                result = self.results.get(step_name, {})
                summary_lines.append(f"• {step_name}")
                summary_lines.append(f"  Status: {result.get('status', 'unknown')}")
                summary_lines.append(f"  Duration: {result.get('duration', 'N/A')}")
                
                if step_name.startswith("Consolidate League JSONs"):
                    summary_lines.append("  Impact: No unified data structure created")
                    summary_lines.append("  Consequence: Subsequent imports may fail")
                elif step_name.startswith("Import Stats"):
                    league_name = step_name.replace("Import Stats - ", "")
                    summary_lines.append(f"  Impact: No {league_name} statistics imported")
                    summary_lines.append(f"  Consequence: {league_name} standings unavailable")
                elif step_name == "Import Match Scores":
                    summary_lines.append("  Impact: No match results imported")
                    summary_lines.append("  Consequence: Match history and scores unavailable")
                elif step_name == "Import Players":
                    summary_lines.append("  Impact: No player data imported")
                    summary_lines.append("  Consequence: Player profiles and associations unavailable")
                
                error_msg = result.get("error", "Unknown error")
                summary_lines.append(f"  Error: {error_msg[:150]}...")
                summary_lines.append("")
        
        # Data quality and validation notes
        summary_lines.append("🔍 DATA QUALITY NOTES:")
        summary_lines.append("-" * 25)
        
        if successful_steps >= 3:  # At least consolidation + stats + one other
            summary_lines.append("• Data consolidation completed successfully")
            summary_lines.append("• League statistics imported for available leagues")
            summary_lines.append("• Database structure updated with latest data")
        else:
            summary_lines.append("• Partial import completed - some data may be missing")
            summary_lines.append("• Consider re-running failed steps individually")
        
        # Recommendations
        summary_lines.append("")
        summary_lines.append("💡 RECOMMENDATIONS:")
        summary_lines.append("-" * 20)
        
        if failed_steps == 0:
            summary_lines.append("• All imports successful - no action required")
            summary_lines.append("• Data is ready for platform use")
        else:
            summary_lines.append("• Review failed steps and error messages")
            summary_lines.append("• Consider re-running failed imports individually")
            summary_lines.append("• Check database connectivity and permissions")
            summary_lines.append("• Verify source data files are accessible")
        
        summary = "\n".join(summary_lines)
        
        # Log detailed summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 DETAILED FINAL SUMMARY")
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
        """Save detailed results to log file with comprehensive import information"""
        results_file = f"logs/master_import_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(results_file, 'w') as f:
            f.write("Rally ETL Master Import Detailed Results\n")
            f.write("=" * 60 + "\n")
            f.write(f"Environment: {self.environment}\n")
            f.write(f"Start Time: {self.start_time}\n")
            f.write(f"End Time: {datetime.now()}\n")
            f.write(f"Total Duration: {datetime.now() - self.start_time}\n")
            
            # League information
            if self.league:
                f.write(f"League Mode: Single League ({self.league})\n")
            else:
                f.write(f"League Mode: All Leagues ({', '.join(self.available_leagues)})\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("STEP-BY-STEP DETAILED RESULTS\n")
            f.write("=" * 60 + "\n\n")
            
            for step_name, result in self.results.items():
                f.write(f"STEP: {step_name}\n")
                f.write(f"Status: {result['status'].upper()}\n")
                f.write(f"Duration: {result['duration']}\n")
                
                # Add step-specific details
                if step_name.startswith("Consolidate League JSONs"):
                    f.write("Purpose: Merge all league JSON files into unified data structure\n")
                    f.write("Data Processed: All league directories and JSON files\n")
                    f.write("Output: Consolidated data in data/leagues/all/\n")
                elif step_name.startswith("Import Stats"):
                    league_name = step_name.replace("Import Stats - ", "")
                    f.write(f"Purpose: Import series statistics for {league_name}\n")
                    f.write("Data Imported: Team standings, win/loss records, series rankings\n")
                    f.write("Database Tables: series_stats, teams, leagues\n")
                elif step_name == "Import Match Scores":
                    f.write("Purpose: Import match results and scores\n")
                    f.write("Data Imported: Match outcomes, individual set scores, player performance\n")
                    f.write("Database Tables: match_scores, players\n")
                elif step_name == "Import Players":
                    f.write("Purpose: Import player data and associations\n")
                    f.write("Data Imported: Player profiles, team assignments, league memberships\n")
                    f.write("Database Tables: players, user_player_associations\n")
                
                f.write(f"Command Output: {result['output'][:1000]}...\n")
                if result['error']:
                    f.write(f"Error Details: {result['error']}\n")
                f.write("-" * 50 + "\n\n")
            
            # Summary section
            f.write("=" * 60 + "\n")
            f.write("IMPORT SUMMARY\n")
            f.write("=" * 60 + "\n")
            
            successful_steps = len([r for r in self.results.values() if r["status"] == "success"])
            failed_steps = len(self.failures)
            total_steps = len(self.import_steps)
            
            f.write(f"Total Steps: {total_steps}\n")
            f.write(f"Successful: {successful_steps}\n")
            f.write(f"Failed: {failed_steps}\n")
            f.write(f"Success Rate: {(successful_steps/total_steps)*100:.1f}%\n\n")
            
            # What was successfully imported
            if successful_steps > 0:
                f.write("SUCCESSFULLY IMPORTED:\n")
                f.write("-" * 25 + "\n")
                for step_name, result in self.results.items():
                    if result["status"] == "success":
                        if step_name.startswith("Consolidate League JSONs"):
                            f.write("✓ Unified league data structure\n")
                        elif step_name.startswith("Import Stats"):
                            league_name = step_name.replace("Import Stats - ", "")
                            f.write(f"✓ {league_name} statistics and standings\n")
                        elif step_name == "Import Match Scores":
                            f.write("✓ Match results and scores\n")
                        elif step_name == "Import Players":
                            f.write("✓ Player data and associations\n")
                f.write("\n")
            
            # What failed to import
            if failed_steps > 0:
                f.write("FAILED TO IMPORT:\n")
                f.write("-" * 20 + "\n")
                for step_name in self.failures:
                    f.write(f"✗ {step_name}\n")
                f.write("\n")
            
            # Data quality assessment
            f.write("DATA QUALITY ASSESSMENT:\n")
            f.write("-" * 25 + "\n")
            if successful_steps >= 3:
                f.write("✓ Comprehensive import completed\n")
                f.write("✓ Database updated with latest data\n")
                f.write("✓ Platform ready for use\n")
            elif successful_steps >= 1:
                f.write("⚠ Partial import completed\n")
                f.write("⚠ Some data may be missing\n")
                f.write("⚠ Consider re-running failed steps\n")
            else:
                f.write("✗ Import failed completely\n")
                f.write("✗ No data imported\n")
                f.write("✗ Manual intervention required\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("END OF REPORT\n")
            f.write("=" * 60 + "\n")
        
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
    
    # Get league argument (normalization handled in MasterImporter class)
    league = args.league
    
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