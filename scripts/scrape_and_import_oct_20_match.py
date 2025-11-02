#!/usr/bin/env python3
"""
Scrape and Import October 20, 2025 CNSWPL Match
================================================

Focused script to scrape and import just the 10/20 match that was missing.

Usage:
    python3 scripts/scrape_and_import_oct_20_match.py
"""

import sys
import os
import subprocess
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def run_command(command, description):
    """Run a command and display output."""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"\n✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed")
        print(f"Error: {e}")
        return False

def main():
    print(f"\n{'='*60}")
    print("🎾 Scraping and Importing October 20, 2025 CNSWPL Match")
    print(f"{'='*60}\n")
    
    # Step 1: Scrape matches for October 20, 2025
    scrape_command = (
        "python3 data/etl/scrapers/cnswpl_scrape_match_scores.py cnswpl "
        "--delta-mode "
        "--start-date 2025-10-20 "
        "--end-date 2025-10-20"
    )
    
    if not run_command(scrape_command, "Scraping October 20, 2025 matches"):
        print("\n❌ Scraping failed. Aborting import.")
        sys.exit(1)
    
    # Step 2: Import the scraped matches
    import_command = "python3 data/etl/import/import_match_scores.py CNSWPL"
    
    if not run_command(import_command, "Importing October 20, 2025 matches"):
        print("\n❌ Import failed.")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("✅ SUCCESS: October 20, 2025 match scraped and imported!")
    print(f"{'='*60}\n")
    
    print("Next steps:")
    print("1. Verify the match appears in the database")
    print("2. Check that player names are displaying correctly")
    print("3. Verify team assignments are correct")

if __name__ == "__main__":
    main()

