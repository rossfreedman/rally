#!/usr/bin/env python3
"""
Remove Recent NSTF Data for Testing

This script removes the most recent week of NSTF match data from both:
1. The JSON file (data/leagues/NSTF/match_history.json)
2. The database (match_scores table)

This is useful for testing the scraper to ensure it can detect and re-scrape recent data.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database_config import get_db

def parse_date(date_str: str) -> datetime:
    """Parse date string in format 'DD-MMM-YY' to datetime object."""
    try:
        return datetime.strptime(date_str, "%d-%b-%y")
    except ValueError:
        # Try alternative format
        return datetime.strptime(date_str, "%d-%b-%Y")

def remove_recent_data_from_json():
    """Remove the most recent week of data from the JSON file."""
    json_file = "data/leagues/NSTF/match_history.json"
    
    print("📄 Loading NSTF JSON data...")
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Original matches: {len(data)}")
    
    # Find the most recent date
    dates = [parse_date(match['Date']) for match in data if match.get('Date')]
    if not dates:
        print("❌ No valid dates found in JSON data")
        return
    
    most_recent_date = max(dates)
    cutoff_date = most_recent_date - timedelta(days=7)
    
    print(f"📅 Most recent date: {most_recent_date.strftime('%d-%b-%y')}")
    print(f"📅 Cutoff date: {cutoff_date.strftime('%d-%b-%y')}")
    
    # Filter out matches from the last week
    original_count = len(data)
    filtered_data = []
    removed_count = 0
    
    for match in data:
        if not match.get('Date'):
            filtered_data.append(match)
            continue
            
        match_date = parse_date(match['Date'])
        if match_date <= cutoff_date:
            filtered_data.append(match)
        else:
            removed_count += 1
            print(f"🗑️ Removing match: {match['Date']} - {match.get('Home Team', 'Unknown')} vs {match.get('Away Team', 'Unknown')}")
    
    print(f"📊 Removed {removed_count} matches from JSON")
    print(f"📊 Remaining matches: {len(filtered_data)}")
    
    # Backup original file
    backup_file = f"data/leagues/NSTF/match_history_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 Backup saved to: {backup_file}")
    
    # Write filtered data
    with open(json_file, 'w') as f:
        json.dump(filtered_data, f, indent=2)
    print(f"✅ Updated JSON file: {json_file}")
    
    return removed_count

def remove_recent_data_from_database():
    """Remove the most recent week of data from the database."""
    print("\n🗄️ Removing recent data from database...")
    
    # Get database connection using context manager
    with get_db() as db:
        cursor = db.cursor()
        
        # Find the most recent date in the database
        cursor.execute("""
            SELECT MAX(match_date) 
            FROM match_scores 
            WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'NSTF')
        """)
        
        result = cursor.fetchone()
        if not result or not result[0]:
            print("❌ No NSTF matches found in database")
            return 0
        
        most_recent_date = result[0]
        cutoff_date = most_recent_date - timedelta(days=7)
        
        print(f"📅 Most recent database date: {most_recent_date}")
        print(f"📅 Database cutoff date: {cutoff_date}")
        
        # Count matches to be removed
        cursor.execute("""
            SELECT COUNT(*) 
            FROM match_scores 
            WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'NSTF')
            AND match_date > %s
        """, (cutoff_date,))
        
        matches_to_remove = cursor.fetchone()[0]
        print(f"📊 Matches to remove from database: {matches_to_remove}")
        
        if matches_to_remove == 0:
            print("ℹ️ No recent matches to remove from database")
            return 0
        
        # Remove recent matches
        cursor.execute("""
            DELETE FROM match_scores 
            WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'NSTF')
            AND match_date > %s
        """, (cutoff_date,))
        
        removed_count = cursor.rowcount
        db.commit()
        
        print(f"✅ Removed {removed_count} matches from database")
        
        # Verify removal
        cursor.execute("""
            SELECT COUNT(*) 
            FROM match_scores 
            WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'NSTF')
        """)
        
        remaining_count = cursor.fetchone()[0]
        print(f"📊 Remaining database matches: {remaining_count}")
        
        return removed_count

def main():
    """Main function to remove recent NSTF data."""
    print("🧪 REMOVE RECENT NSTF DATA FOR TESTING")
    print("=" * 50)
    
    # Remove from JSON
    json_removed = remove_recent_data_from_json()
    
    # Remove from database
    db_removed = remove_recent_data_from_database()
    
    print("\n" + "=" * 50)
    print("✅ REMOVAL COMPLETE")
    print(f"📄 JSON matches removed: {json_removed}")
    print(f"🗄️ Database matches removed: {db_removed}")
    print("\n🎯 Now you can test the scraper to see if it detects and re-scrapes the missing data!")

if __name__ == "__main__":
    main() 