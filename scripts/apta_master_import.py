#!/usr/bin/env python3
"""
APTA Master Import Script

This script automates the complete APTA data import process:
1. End Season - Clear all existing season data
2. Start Season - Create clubs, series, teams, and players
3. Import Players - Import player data with career stats
4. Import Schedules - Import schedule data
5. Import Series History - Import player history data

Usage:
    python3 scripts/apta_master_import.py [--league APTA_CHICAGO] [--dry-run] [--skip-validation]

Options:
    --league LEAGUE_KEY    League to process (default: APTA_CHICAGO)
    --dry-run             Show what would be done without executing
    --skip-validation     Skip final validation step
    --help               Show this help message
"""

import sys
import os
import subprocess
import argparse
import time
from datetime import datetime
from typing import Optional, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

class APTAMasterImport:
    """Master script for APTA data import process."""
    
    def __init__(self, league_key: str = "APTA_CHICAGO", dry_run: bool = False, skip_validation: bool = False):
        self.league_key = league_key
        self.dry_run = dry_run
        self.skip_validation = skip_validation
        self.start_time = datetime.now()
        self.results = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_command(self, command: List[str], description: str) -> Tuple[bool, str]:
        """Run a command and return success status and output."""
        self.log(f"Running: {description}")
        
        if self.dry_run:
            self.log(f"DRY RUN: Would execute: {' '.join(command)}", "DRY")
            return True, "DRY RUN - Command not executed"
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            if result.returncode == 0:
                self.log(f"✅ {description} completed successfully")
                return True, result.stdout
            else:
                self.log(f"❌ {description} failed with return code {result.returncode}", "ERROR")
                self.log(f"Error output: {result.stderr}", "ERROR")
                return False, result.stderr
                
        except Exception as e:
            self.log(f"❌ {description} failed with exception: {str(e)}", "ERROR")
            return False, str(e)
    
    def step_1_end_season(self) -> bool:
        """Step 1: End Season - Clear all existing season data."""
        self.log("=" * 60)
        self.log("STEP 1: ENDING SEASON")
        self.log("=" * 60)
        
        success, output = self.run_command(
            ["python3", "scripts/end_season_auto.py", self.league_key],
            "End Season"
        )
        
        if success:
            self.results.append(("End Season", "✅ Success", "Cleared all season data"))
        else:
            self.results.append(("End Season", "❌ Failed", output))
            
        return success
    
    def step_2_start_season(self) -> bool:
        """Step 2: Start Season - Create clubs, series, teams, and players."""
        self.log("=" * 60)
        self.log("STEP 2: STARTING SEASON")
        self.log("=" * 60)
        
        success, output = self.run_command(
            ["python3", "data/etl/import/start_season.py", self.league_key],
            "Start Season"
        )
        
        if success:
            self.results.append(("Start Season", "✅ Success", "Created clubs, series, teams, and players"))
        else:
            self.results.append(("Start Season", "❌ Failed", output))
            
        return success
    
    def step_3_import_players(self) -> bool:
        """Step 3: Import Players - Import player data with career stats."""
        self.log("=" * 60)
        self.log("STEP 3: IMPORTING PLAYERS")
        self.log("=" * 60)
        
        success, output = self.run_command(
            ["python3", "data/etl/import/import_players.py", self.league_key],
            "Import Players"
        )
        
        if success:
            self.results.append(("Import Players", "✅ Success", "Imported players with career stats"))
        else:
            self.results.append(("Import Players", "❌ Failed", output))
            
        return success
    
    def step_4_import_schedules(self) -> bool:
        """Step 4: Import Schedules - Import schedule data."""
        self.log("=" * 60)
        self.log("STEP 4: IMPORTING SCHEDULES")
        self.log("=" * 60)
        
        success, output = self.run_command(
            ["python3", "data/etl/import/import_schedules.py", self.league_key],
            "Import Schedules"
        )
        
        if success:
            self.results.append(("Import Schedules", "✅ Success", "Imported schedule data"))
        else:
            self.results.append(("Import Schedules", "❌ Failed", output))
            
        return success
    
    def step_5_import_series_history(self) -> bool:
        """Step 5: Import Series History - Import player history data."""
        self.log("=" * 60)
        self.log("STEP 5: IMPORTING SERIES HISTORY")
        self.log("=" * 60)
        
        success, output = self.run_command(
            ["python3", "data/etl/import/import_series_history.py", self.league_key],
            "Import Series History"
        )
        
        if success:
            self.results.append(("Import Series History", "✅ Success", "Imported player history data"))
        else:
            self.results.append(("Import Series History", "❌ Failed", output))
            
        return success
    
    def step_6_validation(self) -> bool:
        """Step 6: Validation - Run comprehensive data validation."""
        self.log("=" * 60)
        self.log("STEP 6: VALIDATION")
        self.log("=" * 60)
        
        success, output = self.run_command(
            ["python3", "scripts/validate_apta_data.py"],
            "Data Validation"
        )
        
        if success:
            self.results.append(("Validation", "✅ Success", "Data validation completed"))
        else:
            self.results.append(("Validation", "⚠️ Issues Found", output))
            
        return success
    
    def print_summary(self):
        """Print a summary of all steps and their results."""
        self.log("=" * 60)
        self.log("IMPORT SUMMARY")
        self.log("=" * 60)
        
        total_time = datetime.now() - self.start_time
        
        for step, status, details in self.results:
            self.log(f"{step:20} | {status:15} | {details}")
        
        self.log("=" * 60)
        self.log(f"Total execution time: {total_time}")
        
        # Count successes and failures
        successes = sum(1 for _, status, _ in self.results if "✅" in status)
        failures = sum(1 for _, status, _ in self.results if "❌" in status)
        warnings = sum(1 for _, status, _ in self.results if "⚠️" in status)
        
        self.log(f"Results: {successes} successful, {warnings} warnings, {failures} failed")
        
        if failures == 0:
            self.log("🎉 All steps completed successfully!")
        else:
            self.log(f"⚠️ {failures} step(s) failed. Check the logs above for details.", "WARNING")
    
    def run(self) -> bool:
        """Run the complete APTA import process."""
        self.log("🚀 Starting APTA Master Import Process")
        self.log(f"League: {self.league_key}")
        self.log(f"Dry Run: {self.dry_run}")
        self.log(f"Skip Validation: {self.skip_validation}")
        
        # Run all steps
        steps = [
            self.step_1_end_season,
            self.step_2_start_season,
            self.step_3_import_players,
            self.step_4_import_schedules,
            self.step_5_import_series_history,
        ]
        
        # Add validation step if not skipped
        if not self.skip_validation:
            steps.append(self.step_6_validation)
        
        # Execute all steps
        all_success = True
        for step_func in steps:
            if not step_func():
                all_success = False
                if not self.dry_run:
                    self.log("❌ Step failed. Stopping execution.", "ERROR")
                    break
        
        # Print summary
        self.print_summary()
        
        return all_success

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="APTA Master Import Script - Automates the complete APTA data import process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scripts/apta_master_import.py
    python3 scripts/apta_master_import.py --league APTA_CHICAGO
    python3 scripts/apta_master_import.py --dry-run
    python3 scripts/apta_master_import.py --skip-validation
        """
    )
    
    parser.add_argument(
        "--league",
        default="APTA_CHICAGO",
        help="League to process (default: APTA_CHICAGO)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip final validation step"
    )
    
    args = parser.parse_args()
    
    # Create and run the import process
    import_process = APTAMasterImport(
        league_key=args.league,
        dry_run=args.dry_run,
        skip_validation=args.skip_validation
    )
    
    success = import_process.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
