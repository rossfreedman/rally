#!/usr/bin/env python3

"""
Quick incremental check - determines if new matches are likely available
without running the full scraper
"""

import sys
import os
import json
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_consolidated_match_history_path():
    """Get the path to the consolidated match history file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))  # scripts/
    project_root = os.path.dirname(script_dir)  # rally/
    
    return os.path.join(project_root, "data", "leagues", "all", "match_history.json")

def check_incremental_status():
    """Check if new matches are likely available"""
    
    print("🔍 Quick Incremental Match Check")
    print("=" * 40)
    
    # Load existing data
    json_path = get_consolidated_match_history_path()
    
    if not os.path.exists(json_path):
        print("❌ No existing match history found")
        print("💡 Run the full scraper first to create initial data")
        return
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        if not matches:
            print("❌ Existing match history is empty")
            return
        
        print(f"📄 Found {len(matches):,} existing matches")
        
        # Find the most recent date
        most_recent_date = None
        date_formats = [
            "%d-%b-%y",  # 09-Jan-25
            "%m/%d/%Y",  # 01/15/2025
            "%Y-%m-%d",  # 2025-01-15
        ]
        
        for match in matches:
            date_str = match.get("Date", "")
            if not date_str:
                continue
                
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    if most_recent_date is None or parsed_date > most_recent_date:
                        most_recent_date = parsed_date
                    break
                except ValueError:
                    continue
        
        if most_recent_date:
            print(f"📅 Most recent match date: {most_recent_date}")
            
            # Check if it's been more than a week since last scrape
            days_since_last = (datetime.now().date() - most_recent_date).days
            print(f"⏰ Days since last match: {days_since_last}")
            
            if days_since_last > 7:
                print("🆕 New matches likely available!")
                print("💡 Consider running the full scraper")
                return True
            else:
                print("✅ Recent data available, no new matches expected")
                return False
        else:
            print("❌ Could not determine most recent date")
            return False
            
    except Exception as e:
        print(f"❌ Error reading match history: {e}")
        return False

if __name__ == "__main__":
    check_incremental_status() 