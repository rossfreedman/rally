#!/usr/bin/env python3
"""
Master ETL Script: Run All Data Imports

This script runs all ETL processes in the correct order to populate the Rally database
with data from scraped JSON files.

Usage:
    python etl/run_all_etl.py [--dry-run]
"""

import argparse
import os
import sys
import subprocess
from datetime import datetime

def run_script(script_path, args=None, description=""):
    """Run an ETL script and handle errors"""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    print(f"\n🔄 {description}")
    print(f"   Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print("   Output:", result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Error: {e}")
        if e.stdout:
            print(f"   Stdout: {e.stdout}")
        if e.stderr:
            print(f"   Stderr: {e.stderr}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run all ETL processes")
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Run all scripts in dry-run mode'
    )
    
    args = parser.parse_args()
    
    print(f"🏓 Rally ETL Pipeline")
    print(f"   Started: {datetime.now()}")
    print(f"   Dry run: {'Yes' if args.dry_run else 'No'}")
    
    # Get current directory for script paths
    etl_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define ETL scripts in order of execution
    etl_scripts = [
        {
            'script': os.path.join(etl_dir, 'import_players.py'),
            'description': 'Import Players & League Associations',
            'args': ['--dry-run'] if args.dry_run else []
        },
        {
            'script': os.path.join(etl_dir, 'import_career_stats.py'),
            'description': 'Import Career Stats from Player History JSON',
            'args': ['--dry-run'] if args.dry_run else []
        },
        {
            'script': os.path.join(etl_dir, 'import_player_history.py'),
            'description': 'Import Player History with Enhanced Player Linking',
            'args': []  # No dry-run option for this script
        }
        # Additional scripts will be added here as they are created
    ]
    
    # Track results
    success_count = 0
    total_count = len(etl_scripts)
    
    # Run each script
    for script_info in etl_scripts:
        success = run_script(
            script_info['script'], 
            script_info['args'], 
            script_info['description']
        )
        
        if success:
            success_count += 1
        else:
            print(f"\n❌ ETL pipeline failed at: {script_info['description']}")
            if not args.dry_run:
                response = input("Continue with remaining scripts? (y/N): ")
                if response.lower() != 'y':
                    break
    
    # Print summary
    print(f"\n📊 ETL Pipeline Summary")
    print(f"   Total scripts: {total_count}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {total_count - success_count}")
    print(f"   Completed: {datetime.now()}")
    
    # Exit with appropriate code
    sys.exit(0 if success_count == total_count else 1)

if __name__ == "__main__":
    main() 