#!/usr/bin/env python3
"""
Check practice entries in schedule table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database_utils import execute_query
from datetime import datetime

def check_practice_entries():
    """Check all practice entries in the schedule table"""
    
    print("Checking practice entries in schedule table...")
    
    # Check current date
    current_date_query = "SELECT CURRENT_DATE"
    current_date_result = execute_query(current_date_query)
    current_date = current_date_result[0][0] if current_date_result else datetime.now().date()
    print(f"Current date: {current_date}")
    
    # Check all practice entries
    practice_query = """
        SELECT 
            match_date,
            match_time,
            home_team,
            away_team,
            location
        FROM schedule 
        WHERE home_team ILIKE '%Practice%'
        AND match_date >= %s
        ORDER BY match_date ASC, match_time ASC
        LIMIT 20
    """
    
    practice_entries = execute_query(practice_query, [current_date])
    print(f"\nFound {len(practice_entries)} upcoming practice entries:")
    for entry in practice_entries:
        print(f"  {entry}")
    
    # Check for Tennaqua practices specifically
    tennaqua_query = """
        SELECT 
            match_date,
            match_time,
            home_team,
            away_team,
            location
        FROM schedule 
        WHERE home_team ILIKE '%Tennaqua%Practice%'
        AND match_date >= %s
        ORDER BY match_date ASC, match_time ASC
        LIMIT 10
    """
    
    tennaqua_practices = execute_query(tennaqua_query, [current_date])
    print(f"\nFound {len(tennaqua_practices)} Tennaqua practice entries:")
    for entry in tennaqua_practices:
        print(f"  {entry}")

if __name__ == "__main__":
    check_practice_entries() 