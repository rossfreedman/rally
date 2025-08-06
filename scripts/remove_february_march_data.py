#!/usr/bin/env python3
"""
Script to remove February and March data from APTA_CHICAGO match_history.json
for testing the delta scraping pipeline.
"""

import json
import os
from datetime import datetime

def parse_date(date_str):
    """Parse date string in format 'DD-MMM-YY' to datetime object."""
    try:
        return datetime.strptime(date_str, "%d-%b-%y")
    except ValueError:
        return None

def remove_february_march_data():
    """Remove all February and March 2025 data from match_history.json."""
    
    # File paths
    match_history_path = "data/leagues/APTA_CHICAGO/match_history.json"
    
    # Backup original file
    backup_path = f"{match_history_path}.backup"
    if not os.path.exists(backup_path):
        print(f"Creating backup: {backup_path}")
        os.system(f"cp {match_history_path} {backup_path}")
    
    # Load the match history data
    print("Loading match history data...")
    with open(match_history_path, 'r') as f:
        data = json.load(f)
    
    print(f"Original data has {len(data)} matches")
    
    # Filter out February and March 2025 data
    filtered_data = []
    removed_count = 0
    
    for match in data:
        date_str = match.get("Date", "")
        if not date_str:
            filtered_data.append(match)
            continue
            
        parsed_date = parse_date(date_str)
        if parsed_date is None:
            filtered_data.append(match)
            continue
            
        # Keep only non-February/March 2025 data
        if parsed_date.year == 2025 and parsed_date.month in [2, 3]:  # February = 2, March = 3
            removed_count += 1
            print(f"Removing match from {date_str}")
        else:
            filtered_data.append(match)
    
    print(f"Removed {removed_count} February/March 2025 matches")
    print(f"Remaining data has {len(filtered_data)} matches")
    
    # Write the filtered data back
    print("Writing filtered data...")
    with open(match_history_path, 'w') as f:
        json.dump(filtered_data, f, indent=2)
    
    print("✅ Successfully removed February and March 2025 data from match_history.json")
    print(f"Backup saved as: {backup_path}")

if __name__ == "__main__":
    remove_february_march_data() 