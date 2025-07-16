#!/usr/bin/env python3
"""
Check schedule data and debug schedule notification function
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from datetime import datetime, date

def check_schedule_data():
    """Check what schedule data exists"""
    
    print("Checking schedule data...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check current date
        cursor.execute("SELECT CURRENT_DATE")
        current_date = cursor.fetchone()[0]
        print(f"Current date: {current_date}")
        
        # Check all schedule entries
        cursor.execute("""
            SELECT 
                match_date,
                match_time,
                home_team,
                away_team,
                location
            FROM schedule 
            WHERE match_date >= %s
            ORDER BY match_date ASC, match_time ASC
            LIMIT 20
        """, [current_date])
        
        schedule_entries = cursor.fetchall()
        print(f"\nFound {len(schedule_entries)} upcoming schedule entries:")
        for entry in schedule_entries:
            print(f"  {entry}")
        
        # Check for practice entries specifically
        cursor.execute("""
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
            LIMIT 10
        """, [current_date])
        
        practice_entries = cursor.fetchall()
        print(f"\nFound {len(practice_entries)} practice entries:")
        for entry in practice_entries:
            print(f"  {entry}")
        
        # Check Tennaqua entries specifically
        cursor.execute("""
            SELECT 
                match_date,
                match_time,
                home_team,
                away_team,
                location
            FROM schedule 
            WHERE (home_team ILIKE '%Tennaqua%' OR away_team ILIKE '%Tennaqua%')
            AND match_date >= %s
            ORDER BY match_date ASC, match_time ASC
            LIMIT 10
        """, [current_date])
        
        tennaqua_entries = cursor.fetchall()
        print(f"\nFound {len(tennaqua_entries)} Tennaqua entries:")
        for entry in tennaqua_entries:
            print(f"  {entry}")
        
        cursor.close()

if __name__ == "__main__":
    check_schedule_data() 