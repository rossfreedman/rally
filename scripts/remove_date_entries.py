#!/usr/bin/env python3
"""
Remove Date Entries for Delta Intelligence Testing
=================================================

This script removes all match entries for a specific date to test
the delta intelligence system's ability to detect and fill gaps.
"""

import json
import sys
from pathlib import Path

def remove_date_entries(file_path: str, target_date: str):
    """
    Remove all entries with the specified date from the JSON file.
    
    Args:
        file_path: Path to the match_history.json file
        target_date: Date to remove (e.g., "11-Feb-25")
    """
    print(f"🎯 Testing Delta Intelligence System")
    print(f"📁 File: {file_path}")
    print(f"📅 Removing entries for date: {target_date}")
    
    # Load the JSON file
    print("📥 Loading JSON file...")
    with open(file_path, 'r') as f:
        matches = json.load(f)
    
    print(f"📊 Original total matches: {len(matches):,}")
    
    # Count matches for target date
    target_matches = [match for match in matches if match.get('Date') == target_date]
    print(f"🎯 Matches for {target_date}: {len(target_matches):,}")
    
    # Remove matches for target date
    filtered_matches = [match for match in matches if match.get('Date') != target_date]
    print(f"📊 Matches after removal: {len(filtered_matches):,}")
    print(f"❌ Removed {len(matches) - len(filtered_matches):,} matches")
    
    # Save the modified file
    print("💾 Saving modified file...")
    with open(file_path, 'w') as f:
        json.dump(filtered_matches, f, indent=2)
    
    print("✅ Date entries removed successfully!")
    print(f"📈 Gap created: {len(target_matches)} missing matches for {target_date}")
    print(f"🔍 Delta intelligence should detect this gap and rescrape the missing data")

if __name__ == "__main__":
    file_path = "data/leagues/APTA_CHICAGO/match_history.json"
    target_date = "19-Feb-25"  # Remove LATEST date to test gap detection
    
    # Verify file exists
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    # Remove the date entries
    remove_date_entries(file_path, target_date)