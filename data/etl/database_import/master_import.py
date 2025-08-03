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

def detect_environment():
    """Auto-detect the current environment."""
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return os.getenv("RAILWAY_ENVIRONMENT")
    if os.getenv("DATABASE_URL") and "railway" in os.getenv("DATABASE_URL", "").lower():
        return "production"
    if os.getenv("STAGING") or os.getenv("RAILWAY_STAGING"):
        return "staging"
    if os.path.exists("database_config.py"):
        return "local"
    return "local"

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

def parse_metrics_from_output(output: str) -> dict:
    """Parse key metrics from script output (imported, updated, errors, etc.)"""
    metrics = {}
    for line in output.splitlines():
        line = line.strip()
        if any(key in line.lower() for key in ["imported", "updated", "errors", "skipped", "new records", "players", "matches", "stats"]):
            # Try to extract key-value pairs
            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip().capitalize()
                value = parts[1].strip()
                metrics[key] = value
            elif "=" in line:
                parts = line.split("=", 1)
                key = parts[0].strip().capitalize()
                value = parts[1].strip()
                metrics[key] = value
    return metrics

class MasterImporter:
    """Master importer that orchestrates all ETL processes"""
    
    # Legacy hardcoded leagues for backward compatibility (active leagues only)
    LEGACY_LEAGUES = ["APTA_CHICAGO", "NSTF"]
    
    # League name mapping for case-insensitive input (active leagues only)
    LEAGUE_MAPPING = {
        "APTACHICAGO": "aptachicago",
        "aptachicago": "aptachicago",
        "APTA_CHICAGO": "aptachicago",
        "NSTF": "nstf",
        "nstf": "nstf"
    }
    
    def __init__(self, environment="staging", league=None, no_sms=False):
        self.environment = environment
        self.league = league
        self.no_sms = no_sms  # Flag to disable SMS notifications
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
            
            # Inactive leagues to exclude (empty data or not ready)
            inactive_leagues = {"CITA", "CNSWPL"}
            
            # Discover league directories (excluding 'all' directory and inactive leagues)
            available_leagues = []
            for item in leagues_dir.iterdir():
                if (item.is_dir() and 
                    item.name != "all" and 
                    not item.name.startswith(".") and 
                    item.name not in inactive_leagues):
                    available_leagues.append(item.name)
            
            if not available_leagues:
                logger.warning("No league directories found, falling back to legacy leagues")
                return self.LEGACY_LEAGUES
            
            # Sort for consistent ordering
            available_leagues.sort()
            logger.info(f"Discovered {len(available_leagues)} leagues: {', '.join(available_leagues)}")
            if inactive_leagues:
                logger.info(f"Excluded inactive leagues: {', '.join(sorted(inactive_leagues))}")
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
            # All leagues mode - map directory names to lowercase (active leagues only)
            league_mapping = {
                "APTA_CHICAGO": "aptachicago",
                "NSTF": "nstf",
            }
            
            for league in self.available_leagues:
                lowercase_league = league_mapping.get(league, league.lower())
                steps.append({
                    "name": f"Import Stats - {league}",
                    "script": "import_stats.py",
                    "args": [lowercase_league],
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
    
    def send_notification(self, message, is_failure=False, step_name=None, error_details=None, duration=None, metrics=None):
        """Send SMS notification to admin with enhanced error details"""
        # Skip sending SMS if disabled (when called from cronjob)
        if self.no_sms:
            logger.info(f"📱 SMS notification skipped (no-sms mode): {message[:50]}...")
            return
            
        try:
            current_time = datetime.now().strftime('%m-%d-%y @ %I:%M:%S %p')
            
            # Enhance failure messages with more context
            if is_failure and step_name and error_details:
                enhanced_message = f"🚨 Rally ETL FAILURE\n"
                enhanced_message += f"Activity: {step_name}\n"
                enhanced_message += f"Environment: {self.environment}\n"
                enhanced_message += f"Time: {current_time}\n"
                enhanced_message += f"Error: {error_details[:200]}..." if len(error_details) > 200 else f"Error: {error_details}"
                enhanced_message += f"\nImpact: {self._get_step_impact(step_name)}"
                enhanced_message += f"\nAction: Check logs and re-run if needed"
            elif is_failure:
                enhanced_message = f"🚨 Rally ETL FAILURE\n"
                enhanced_message += f"Environment: {self.environment}\n"
                enhanced_message += f"Time: {current_time}\n"
                enhanced_message += f"Error: {message}"
            else:
                # Success message with clean format
                enhanced_message = f"Rally ETL:\n"
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
                enhanced_message += f"Environment: {self.environment}\n"
                enhanced_message += f"Time: {current_time}\n"
                # Special formatting for final ETL completion
                if "ETL COMPLETE" in message:
                    enhanced_message += f"FINAL ETL STATUS: ✅"
                else:
                    enhanced_message += f"Status: ✅"
                if metrics:
                    enhanced_message += "\nMetrics:"
                    for k, v in metrics.items():
                        enhanced_message += f"\n- {k}: {v}"
            
            if send_sms:
                send_sms(ADMIN_PHONE, enhanced_message)
                logger.info(f"📱 SMS sent to admin: {enhanced_message[:100]}...")
            else:
                logger.info(f"📱 SMS notification (mock): {enhanced_message}")
        except Exception as e:
            logger.error(f"❌ Failed to send SMS: {e}")
    
    def _get_step_impact(self, step_name):
        """Get human-readable impact description for a failed step"""
        impact_map = {
            "Consolidate League JSONs": "No unified data structure available",
            "Import Stats": "Team standings and rankings unavailable",
            "Import Match Scores": "Match results and scores unavailable", 
            "Import Players": "Player data and associations unavailable"
        }
        
        for key, impact in impact_map.items():
            if key in step_name:
                return impact
        return "Data import step failed"
    
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
                
                # Parse metrics from output
                metrics = parse_metrics_from_output(result.stdout)
                # Send success notification with step number
                step_number = getattr(self, '_current_step_number', 0)
                total_steps = getattr(self, '_total_steps', 0)
                self.send_notification(f"[{step_number}/{total_steps}] {step_name}", duration=duration, metrics=metrics)
                
                self.results[step_name] = {
                    "status": "success",
                    "duration": duration,
                    "output": result.stdout,
                    "error": result.stderr,
                    "metrics": metrics
                }
                
                return True
            else:
                # Failure
                error_msg = f"❌ {step_name} failed after {duration}"
                logger.error(error_msg)
                logger.error(f"Error output: {result.stderr}")
                
                # Send immediate failure notification with step number
                step_number = getattr(self, '_current_step_number', 0)
                total_steps = getattr(self, '_total_steps', 0)
                self.send_notification("", is_failure=True, step_name=f"[{step_number}/{total_steps}] {step_name}", error_details=result.stderr)
                
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
            
            # Send timeout notification with step number
            step_number = getattr(self, '_current_step_number', 0)
            total_steps = getattr(self, '_total_steps', 0)
            self.send_notification("", is_failure=True, step_name=f"[{step_number}/{total_steps}] {step_name}", error_details="Script timed out after 1 hour")
            
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
            
            # Send exception notification with step number
            step_number = getattr(self, '_current_step_number', 0)
            total_steps = getattr(self, '_total_steps', 0)
            self.send_notification("", is_failure=True, step_name=f"[{step_number}/{total_steps}] {step_name}", error_details=str(e))
            
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
        total_steps = len(self.import_steps)
        self.send_notification(f"[1/{total_steps + 2}] Master Import Starting")
        
        # Store step numbers for notifications
        self._total_steps = total_steps + 2  # +2 for start and end notifications
        
        # Run each import step
        for i, step in enumerate(self.import_steps, 1):
            logger.info(f"\n📋 Step {i}/{len(self.import_steps)}: {step['name']}")
            logger.info("-" * 50)
            
            # Set current step number for notifications (start=1, steps=2..n+1, end=n+2)
            self._current_step_number = i + 1
            
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
            f"Start Time: {self.start_time.strftime('%m-%d-%y @ %I:%M:%S %p')}",
            f"End Time: {end_time.strftime('%m-%d-%y @ %I:%M:%S %p')}",
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
        final_step_number = getattr(self, '_total_steps', len(self.import_steps) + 2)
        if failed_steps == 0:
            final_message = f"[{final_step_number}/{final_step_number}] 🎉 ETL COMPLETE - {successful_steps}/{total_steps} steps successful"
        else:
            final_message = f"[{final_step_number}/{final_step_number}] ⚠️ ETL COMPLETE with Issues - {successful_steps}/{total_steps} steps successful"
        last_metrics = self.results[list(self.results)[-1]].get('metrics') if self.results else None
        self.send_notification(final_message, duration=total_duration, metrics=last_metrics)
        
        # Save detailed results to file
        self.save_detailed_results()
    
    def save_detailed_results(self):
        """Save detailed results to log file with comprehensive import information"""
        results_file = f"logs/master_import_results_{datetime.now().strftime('%m-%d-%y_%I-%M-%S_%p')}.txt"
        
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
        choices=["local", "staging", "production"],
        default=detect_environment(),
        help="Environment to run imports for (auto-detected)"
    )
    parser.add_argument(
        "--league",
        choices=["APTA_CHICAGO", "NSTF", "aptachicago", "nstf"],
        help="Specific league to import (if not specified, imports all leagues)"
    )
    parser.add_argument(
        "--no-sms",
        action="store_true",
        help="Disable SMS notifications for individual steps (used when called from cronjob)"
    )
    
    args = parser.parse_args()
    
    # Get league argument (normalization handled in MasterImporter class)
    league = args.league
    
    try:
        # Create and run master importer
        importer = MasterImporter(environment=args.environment, league=league, no_sms=args.no_sms)
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