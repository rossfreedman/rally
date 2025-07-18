#!/usr/bin/env python3
"""
Script to check if there are any Chicago 22 schedule entries
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db

def check_chicago_schedule():
    print("=== Checking for Chicago 22 Schedule Entries ===\n")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check for any Chicago 22 schedule entries
        chicago_schedule_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team,
                s.away_team,
                s.home_team_id,
                s.away_team_id,
                t.team_name,
                s2.name as series_name
            FROM schedule s
            LEFT JOIN teams t ON (s.home_team_id = t.id OR s.away_team_id = t.id)
            LEFT JOIN series s2 ON t.series_id = s2.id
            WHERE s2.name LIKE '%Chicago%'
            AND s.match_date >= CURRENT_DATE
            ORDER BY s.match_date ASC
            LIMIT 20
        """
        
        cursor.execute(chicago_schedule_query)
        chicago_entries = cursor.fetchall()
        
        print(f"1. Chicago schedule entries:")
        print(f"   Found {len(chicago_entries)} entries")
        
        if chicago_entries:
            for entry in chicago_entries:
                print(f"   - {entry[1]} at {entry[2]}: {entry[3]} vs {entry[4]}")
                print(f"     Home Team ID: {entry[5]}, Away Team ID: {entry[6]}")
                print(f"     Team Name: {entry[7]}, Series: {entry[8]}")
        else:
            print("   ❌ No Chicago schedule entries found")
        
        # Check what teams exist for Chicago series
        chicago_teams_query = """
            SELECT 
                t.id,
                t.team_name,
                s.name as series_name,
                c.name as club_name
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE s.name LIKE '%Chicago%'
            ORDER BY s.name, t.team_name
        """
        
        cursor.execute(chicago_teams_query)
        chicago_teams = cursor.fetchall()
        
        print(f"\n2. Chicago teams:")
        for team in chicago_teams:
            print(f"   - Team ID: {team[0]}, Name: {team[1]}, Series: {team[2]}, Club: {team[3]}")
        
        # Check total schedule entries
        total_schedule_query = """
            SELECT COUNT(*) as total_entries
            FROM schedule
            WHERE match_date >= CURRENT_DATE
        """
        
        cursor.execute(total_schedule_query)
        total_entries = cursor.fetchone()[0]
        
        print(f"\n3. Total future schedule entries: {total_entries}")
    
    print("\n✅ Analysis completed")

if __name__ == "__main__":
    check_chicago_schedule() 