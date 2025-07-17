#!/usr/bin/env python3
"""
Simple script to check schedule data for Ross's team
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

def check_schedule_data():
    """Check schedule data for Ross's team"""
    
    print("🔍 Checking Schedule Data for Ross's Team")
    print("=" * 50)
    
    # Ross's team ID from the debug output
    team_id = 57314
    
    with get_db() as db:
        cursor = db.cursor()
        
        # Check total schedule entries
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM schedule 
            WHERE (home_team_id = %s OR away_team_id = %s)
        """, (team_id, team_id))
        
        result = cursor.fetchone()
        total_count = result[0] if result else 0
        print(f"✅ Total schedule entries for team {team_id}: {total_count}")
        
        # Check upcoming schedule entries
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM schedule 
            WHERE (home_team_id = %s OR away_team_id = %s)
            AND match_date >= CURRENT_DATE
        """, (team_id, team_id))
        
        result = cursor.fetchone()
        upcoming_count = result[0] if result else 0
        print(f"✅ Upcoming schedule entries for team {team_id}: {upcoming_count}")
        
        if upcoming_count > 0:
            # Show the actual schedule entries
            cursor.execute("""
                SELECT 
                    match_date,
                    match_time,
                    home_team,
                    away_team,
                    location,
                    CASE 
                        WHEN home_team_id = %s THEN 'practice'
                        ELSE 'match'
                    END as type
                FROM schedule 
                WHERE (home_team_id = %s OR away_team_id = %s)
                AND match_date >= CURRENT_DATE
                ORDER BY match_date ASC, match_time ASC
                LIMIT 10
            """, (team_id, team_id, team_id))
            
            entries = cursor.fetchall()
            print(f"\n📅 Upcoming entries:")
            for entry in entries:
                print(f"   {entry[0]} {entry[1]}: {entry[2]} vs {entry[3]} ({entry[4]}) - {entry[5]}")
        else:
            print(f"\n❌ No upcoming schedule entries found")
            
            # Check if there are any past entries
            cursor.execute("""
                SELECT 
                    match_date,
                    match_time,
                    home_team,
                    away_team,
                    location
                FROM schedule 
                WHERE (home_team_id = %s OR away_team_id = %s)
                AND match_date < CURRENT_DATE
                ORDER BY match_date DESC, match_time DESC
                LIMIT 5
            """, (team_id, team_id))
            
            past_entries = cursor.fetchall()
            if past_entries:
                print(f"\n📅 Recent past entries:")
                for entry in past_entries:
                    print(f"   {entry[0]} {entry[1]}: {entry[2]} vs {entry[3]} ({entry[4]})")
            else:
                print(f"\n❌ No schedule entries at all for team {team_id}")
                
                # Check if team exists
                cursor.execute("""
                    SELECT t.id, t.name, c.name as club_name, s.name as series_name
                    FROM teams t
                    JOIN clubs c ON t.club_id = c.id
                    JOIN series s ON t.series_id = s.id
                    WHERE t.id = %s
                """, (team_id,))
                
                team_info = cursor.fetchone()
                if team_info:
                    print(f"\n✅ Team {team_id} exists: {team_info[1]} ({team_info[2]} - {team_info[3]})")
                else:
                    print(f"\n❌ Team {team_id} does not exist in database")
                    
                    # Find Tennaqua teams
                    cursor.execute("""
                        SELECT t.id, t.name, c.name as club_name, s.name as series_name
                        FROM teams t
                        JOIN clubs c ON t.club_id = c.id
                        JOIN series s ON t.series_id = s.id
                        WHERE c.name LIKE '%%Tennaqua%%'
                        ORDER BY t.id DESC
                        LIMIT 10
                    """)
                    
                    teams = cursor.fetchall()
                    print(f"\n🏢 Available Tennaqua teams:")
                    for team in teams:
                        print(f"   Team ID {team[0]}: {team[1]} ({team[2]} - {team[3]})")

if __name__ == "__main__":
    check_schedule_data() 