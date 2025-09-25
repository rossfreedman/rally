#!/usr/bin/env python3
"""
APTA Chicago Scraper Sequence Cron Job
=====================================

This script runs the three APTA Chicago scrapers in sequence:
1. apta_scrape_players_simple.py - Scrapes player data
2. scrape_match_scores.py - Scrapes match scores  
3. scrape_stats.py - Scrapes team statistics

Features:
- Sequential execution with validation after each step
- SMS notifications to admin after each scraper completion
- Comprehensive error handling and logging
- Final summary with success/failure status
- Validation of scraper outputs

Usage:
    python cron/apta_chicago_scraper_sequence.py

Railway Configuration:
    [deploy.cronJobs.apta_chicago_sequence]
    schedule = "0 3 * * *"  # Daily at 3 AM
    command = "python cron/apta_chicago_scraper_sequence.py"
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import SMS notification service
from app.services.notifications_service import send_sms_notification

# Admin phone number for notifications
ADMIN_PHONE = "17732138911"

class APTAChicagoScraperSequence:
    """Manages the sequential execution of APTA Chicago scrapers"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            "players_scraper": {"success": False, "duration": 0, "error": None, "output_file": None},
            "match_scores_scraper": {"success": False, "duration": 0, "error": None, "output_file": None},
            "stats_scraper": {"success": False, "duration": 0, "error": None, "output_file": None}
        }
        self.total_duration = 0
        self.overall_success = False
        
    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def send_sms(self, message, test_mode=False):
        """Send SMS notification to admin"""
        try:
            result = send_sms_notification(
                to_number=ADMIN_PHONE,
                message=message,
                test_mode=test_mode
            )
            if result.get("success"):
                self.log(f"SMS sent: {message[:50]}...")
            else:
                self.log(f"SMS failed: {result.get('error', 'Unknown error')}", "ERROR")
        except Exception as e:
            self.log(f"SMS error: {str(e)}", "ERROR")
    
    def validate_scraper_output(self, scraper_name, expected_file_patterns):
        """Validate that scraper produced expected output files"""
        try:
            data_dir = Path(project_root) / "data" / "leagues" / "APTA_CHICAGO"
            self.log(f"Validating output for {scraper_name}")
            self.log(f"Data directory: {data_dir}")
            self.log(f"Expected patterns: {expected_file_patterns}")
            
            if not data_dir.exists():
                self.log(f"Data directory not found: {data_dir}", "ERROR")
                return False, f"Data directory not found: {data_dir}"
            
            self.log(f"Data directory exists, checking for files...")
            
            found_files = []
            missing_files = []
            
            for pattern in expected_file_patterns:
                self.log(f"Searching for pattern: {pattern}")
                matching_files = list(data_dir.glob(pattern))
                if matching_files:
                    self.log(f"Found {len(matching_files)} files matching '{pattern}': {[f.name for f in matching_files]}")
                    found_files.extend([str(f) for f in matching_files])
                else:
                    self.log(f"No files found matching pattern: {pattern}", "WARNING")
                    missing_files.append(pattern)
            
            if missing_files:
                self.log(f"Missing expected files: {missing_files}", "ERROR")
                return False, f"Missing expected files: {missing_files}"
            
            # Check if files have content
            self.log(f"Checking file sizes for {len(found_files)} files...")
            for file_path in found_files:
                file_size = os.path.getsize(file_path)
                self.log(f"File {os.path.basename(file_path)}: {file_size} bytes")
                if file_size == 0:
                    self.log(f"Empty file found: {file_path}", "ERROR")
                    return False, f"Empty file found: {file_path}"
            
            self.log(f"All {len(found_files)} files have content")
            return True, f"Found {len(found_files)} files: {[os.path.basename(f) for f in found_files]}"
            
        except Exception as e:
            self.log(f"Validation error: {str(e)}", "ERROR")
            return False, f"Validation error: {str(e)}"
    
    def run_scraper(self, scraper_name, script_path, args=None, expected_files=None):
        """Run a single scraper and validate its output"""
        self.log(f"Starting {scraper_name}...")
        self.log(f"Script path: {script_path}")
        self.log(f"Working directory: {project_root}")
        scraper_start = time.time()
        
        try:
            # Prepare command
            cmd = [sys.executable, script_path]
            if args:
                cmd.extend(args)
            
            self.log(f"Running command: {' '.join(cmd)}")
            self.log(f"Expected output files: {expected_files}")
            
            # Run scraper with real-time output
            self.log(f"Executing scraper subprocess...")
            self.log(f"Command: {' '.join(cmd)}")
            self.log(f"Working directory: {project_root}")
            
            # Use Popen for real-time output streaming
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output in real-time
            stdout_lines = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    stdout_lines.append(line)
                    # Show important lines in real-time
                    if any(keyword in line.lower() for keyword in ['error', 'failed', 'success', 'completed', 'starting', 'found', 'scraped']):
                        self.log(f"  SCRAPER: {line}")
                    sys.stdout.flush()
            
            # Get return code
            return_code = process.poll()
            stdout_content = '\n'.join(stdout_lines)
            
            # Create result object similar to subprocess.run
            class Result:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
            
            result = Result(return_code, stdout_content, "")
            
            scraper_duration = time.time() - scraper_start
            self.log(f"Scraper execution completed in {scraper_duration:.1f}s")
            self.log(f"Return code: {result.returncode}")
            
            # Log scraper output for debugging
            if result.stdout:
                self.log(f"Scraper STDOUT ({len(result.stdout)} chars):")
                # Show first 500 chars of stdout for debugging
                stdout_preview = result.stdout[:500]
                if len(result.stdout) > 500:
                    stdout_preview += "... (truncated)"
                for line in stdout_preview.split('\n'):
                    self.log(f"  {line}")
            
            if result.stderr:
                self.log(f"Scraper STDERR ({len(result.stderr)} chars):")
                # Show first 500 chars of stderr for debugging
                stderr_preview = result.stderr[:500]
                if len(result.stderr) > 500:
                    stderr_preview += "... (truncated)"
                for line in stderr_preview.split('\n'):
                    self.log(f"  {line}")
            
            if result.returncode == 0:
                self.log(f"{scraper_name} completed successfully in {scraper_duration:.1f}s")
                
                # Validate output if expected files specified
                if expected_files:
                    self.log(f"Validating output files: {expected_files}")
                    is_valid, validation_msg = self.validate_scraper_output(scraper_name, expected_files)
                    if is_valid:
                        self.log(f"Validation passed: {validation_msg}")
                        self.results[scraper_name] = {
                            "success": True,
                            "duration": scraper_duration,
                            "error": None,
                            "validation": validation_msg
                        }
                    else:
                        self.log(f"Validation failed: {validation_msg}", "ERROR")
                        self.results[scraper_name] = {
                            "success": False,
                            "duration": scraper_duration,
                            "error": f"Validation failed: {validation_msg}",
                            "validation": validation_msg
                        }
                else:
                    self.log(f"No validation specified for {scraper_name}")
                    self.results[scraper_name] = {
                        "success": True,
                        "duration": scraper_duration,
                        "error": None,
                        "validation": "No validation performed"
                    }
                
                # Send success SMS
                success_msg = f"✅ {scraper_name} completed successfully in {scraper_duration:.1f}s"
                self.log(f"Sending success SMS: {success_msg}")
                self.send_sms(success_msg)
                
                return True
                
            else:
                error_msg = f"Scraper failed with return code {result.returncode}"
                self.log(f"{scraper_name} failed: {error_msg}", "ERROR")
                self.log(f"Full STDOUT: {result.stdout}", "ERROR")
                self.log(f"Full STDERR: {result.stderr}", "ERROR")
                
                self.results[scraper_name] = {
                    "success": False,
                    "duration": scraper_duration,
                    "error": error_msg,
                    "validation": "Failed - no validation performed"
                }
                
                # Send failure SMS
                failure_msg = f"❌ {scraper_name} failed: {error_msg}"
                self.log(f"Sending failure SMS: {failure_msg}")
                self.send_sms(failure_msg)
                
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = f"Scraper timed out after 30 minutes"
            self.log(f"{scraper_name} timed out", "ERROR")
            
            self.results[scraper_name] = {
                "success": False,
                "duration": 1800,
                "error": error_msg,
                "validation": "Failed - timeout"
            }
            
            # Send timeout SMS
            timeout_msg = f"⏰ {scraper_name} timed out after 30 minutes"
            self.send_sms(timeout_msg)
            
            return False
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log(f"{scraper_name} error: {error_msg}", "ERROR")
            
            scraper_duration = time.time() - scraper_start
            self.results[scraper_name] = {
                "success": False,
                "duration": scraper_duration,
                "error": error_msg,
                "validation": "Failed - exception"
            }
            
            # Send error SMS
            error_sms = f"💥 {scraper_name} error: {str(e)[:100]}"
            self.send_sms(error_sms)
            
            return False
    
    def run_players_scraper(self):
        """Run the APTA players scraper"""
        script_path = "data/etl/scrapers/apta/apta_scrape_players_simple.py"
        expected_files = ["players.json", "players_simple_*.json"]
        
        return self.run_scraper(
            "players_scraper",
            script_path,
            args=["--force-restart"],  # Force fresh start
            expected_files=expected_files
        )
    
    def run_match_scores_scraper(self):
        """Run the match scores scraper"""
        script_path = "data/etl/scrapers/scrape_match_scores.py"
        expected_files = ["match_scores.json", "match_scores_*.json"]
        
        return self.run_scraper(
            "match_scores_scraper",
            script_path,
            args=["APTA_CHICAGO"],  # League parameter
            expected_files=expected_files
        )
    
    def run_stats_scraper(self):
        """Run the stats scraper"""
        script_path = "data/etl/scrapers/scrape_stats.py"
        expected_files = ["series_stats.json", "series_stats_*.json"]
        
        return self.run_scraper(
            "stats_scraper",
            script_path,
            args=["aptachicago"],  # League subdomain
            expected_files=expected_files
        )
    
    def generate_summary(self):
        """Generate final summary of all scrapers"""
        end_time = datetime.now()
        self.total_duration = (end_time - self.start_time).total_seconds()
        
        # Count successes and failures
        successful_scrapers = sum(1 for result in self.results.values() if result["success"])
        total_scrapers = len(self.results)
        
        self.overall_success = successful_scrapers == total_scrapers
        
        # Generate summary message
        if self.overall_success:
            summary_msg = f"🎉 APTA Chicago Scraper Sequence COMPLETED SUCCESSFULLY!\n\n"
            summary_msg += f"✅ All {total_scrapers} scrapers completed successfully\n"
            summary_msg += f"⏱️ Total duration: {self.total_duration:.1f}s\n"
            summary_msg += f"🕐 Completed at: {end_time.strftime('%m-%d-%y @ %I:%M:%S %p')}\n\n"
        else:
            summary_msg = f"⚠️ APTA Chicago Scraper Sequence COMPLETED WITH ISSUES\n\n"
            summary_msg += f"✅ Successful: {successful_scrapers}/{total_scrapers} scrapers\n"
            summary_msg += f"❌ Failed: {total_scrapers - successful_scrapers}/{total_scrapers} scrapers\n"
            summary_msg += f"⏱️ Total duration: {self.total_duration:.1f}s\n"
            summary_msg += f"🕐 Completed at: {end_time.strftime('%m-%d-%y @ %I:%M:%S %p')}\n\n"
        
        # Add detailed results
        summary_msg += "📊 Detailed Results:\n"
        for scraper_name, result in self.results.items():
            status = "✅" if result["success"] else "❌"
            duration = f"{result['duration']:.1f}s"
            summary_msg += f"  {status} {scraper_name}: {duration}"
            if not result["success"] and result["error"]:
                summary_msg += f" - {result['error'][:50]}..."
            summary_msg += "\n"
        
        return summary_msg
    
    def run_sequence(self):
        """Run the complete scraper sequence"""
        self.log("🚀 Starting APTA Chicago Scraper Sequence")
        self.log("=" * 60)
        self.log(f"Start time: {self.start_time.strftime('%m-%d-%y @ %I:%M:%S %p')}")
        self.log("Sequence: Players → Match Scores → Stats")
        self.log(f"Project root: {project_root}")
        self.log(f"Admin phone: {ADMIN_PHONE}")
        self.log("=" * 60)
        
        # Send start notification
        start_msg = f"🚀 APTA Chicago Scraper Sequence STARTING\n\n"
        start_msg += f"🕐 Start time: {self.start_time.strftime('%m-%d-%y @ %I:%M:%S %p')}\n"
        start_msg += f"📋 Sequence: Players → Match Scores → Stats\n"
        start_msg += f"⏱️ Estimated duration: 15-30 minutes"
        self.log(f"Sending start SMS: {start_msg}")
        self.send_sms(start_msg)
        
        # Step 1: Players Scraper
        self.log("\n" + "="*50)
        self.log("STEP 1: APTA Players Scraper")
        self.log("="*50)
        
        if not self.run_players_scraper():
            self.log("Players scraper failed - continuing with remaining scrapers", "WARNING")
        
        # Step 2: Match Scores Scraper
        self.log("\n" + "="*50)
        self.log("STEP 2: Match Scores Scraper")
        self.log("="*50)
        
        if not self.run_match_scores_scraper():
            self.log("Match scores scraper failed - continuing with remaining scrapers", "WARNING")
        
        # Step 3: Stats Scraper
        self.log("\n" + "="*50)
        self.log("STEP 3: Stats Scraper")
        self.log("="*50)
        
        if not self.run_stats_scraper():
            self.log("Stats scraper failed", "WARNING")
        
        # Generate and send final summary
        self.log("\n" + "="*60)
        self.log("FINAL SUMMARY")
        self.log("="*60)
        
        summary = self.generate_summary()
        self.log(summary)
        
        # Send final summary SMS
        self.send_sms(summary)
        
        # Log final status
        if self.overall_success:
            self.log("🎉 All scrapers completed successfully!")
            return True
        else:
            self.log("⚠️ Some scrapers failed - check logs for details", "WARNING")
            return False

def main():
    """Main entry point"""
    try:
        # Create and run scraper sequence
        sequence = APTAChicagoScraperSequence()
        success = sequence.run_sequence()
        
        # Exit with appropriate code
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏸️ Scraper sequence interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
