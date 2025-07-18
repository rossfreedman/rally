#!/usr/bin/env python3
"""
Debug script to investigate why upcoming schedule notifications are missing for Ross
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_upcoming_schedule_notifications
from core.database import get_db
from datetime import datetime, timedelta

def debug_upcoming_schedule():
    print("=== Debugging Ross's Upcoming Schedule Notifications ===\n")
    
    # Ross's user info
    user_id = 43
    player_id = "nndz-WlNhd3hMYi9nQT09"
    league_id = 4775  # APTA Chicago
    team_id = 47092   # Tennaqua - 22
    
    print(f"1. Ross's user info:")
    print(f"   - User ID: {user_id}")
    print(f"   - Player ID: {player_id}")
    print(f"   - League ID: {league_id}")
    print(f"   - Team ID: {team_id}\n")
    
    print("2. Testing upcoming schedule notifications function...")
    
    try:
        # Test the function directly
        notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
        
        print(f"   Function returned {len(notifications)} notifications")
        
        if notifications:
            for i, notification in enumerate(notifications, 1):
                print(f"   {i}. {notification['title']} - {notification['message'][:100]}...")
                print(f"      Priority: {notification['priority']}")
        else:
            print("   ❌ No upcoming schedule notifications returned")
            
        print("\n3. Checking schedule data directly...")
        
        # Check schedule table directly
        with get_db() as conn:
            # Check for any schedule entries for Ross's team
            schedule_query = """
                SELECT 
                    s.id,
                    s.match_date,
                    s.match_time,
                    s.home_team_id,
                    s.away_team_id,
                    s.home_team,
                    s.away_team,
                    s.location,
                    CASE 
                        WHEN s.home_team_id = %s THEN 'practice'
                        ELSE 'match'
                    END as type
                FROM schedule s
                WHERE (s.home_team_id = %s OR s.away_team_id = %s)
                AND s.match_date >= CURRENT_DATE
                ORDER BY s.match_date ASC, s.match_time ASC
                LIMIT 10
            """
            
            cursor = conn.cursor()
            cursor.execute(schedule_query, [team_id, team_id, team_id])
            schedule_entries = cursor.fetchall()
            
            print(f"   Found {len(schedule_entries)} schedule entries for team {team_id}:")
            
            if schedule_entries:
                for entry in schedule_entries:
                    print(f"   - {entry[1]} at {entry[2]}: {entry[8]} ({entry[5]} vs {entry[6]})")
            else:
                print("   ❌ No schedule entries found for Ross's team")
                
            # Check team info
            team_query = """
                SELECT 
                    t.id,
                    t.team_name,
                    t.series_id,
                    s.name as series_name,
                    c.name as club_name
                FROM teams t
                LEFT JOIN series s ON t.series_id = s.id
                LEFT JOIN clubs c ON t.club_id = c.id
                WHERE t.id = %s
            """
            
            cursor.execute(team_query, [team_id])
            team_info = cursor.fetchone()
            
            if team_info:
                print(f"\n4. Team info for team {team_id}:")
                print(f"   - Team Name: {team_info[1]}")
                print(f"   - Series: {team_info[3]}")
                print(f"   - Club: {team_info[4]}")
            else:
                print(f"\n4. ❌ No team info found for team {team_id}")
                
            # Check if there are any schedule entries at all
            all_schedule_query = """
                SELECT COUNT(*) as total_entries
                FROM schedule
                WHERE match_date >= CURRENT_DATE
            """
            
            cursor.execute(all_schedule_query)
            total_entries = cursor.fetchone()[0]
            
            print(f"\n5. Total future schedule entries in database: {total_entries}")
            
            if total_entries == 0:
                print("   ❌ No future schedule entries in database at all")
            else:
                # Show a few sample entries
                sample_query = """
                    SELECT 
                        s.match_date,
                        s.match_time,
                        s.home_team,
                        s.away_team,
                        t.team_name,
                        c.name as club_name
                    FROM schedule s
                    LEFT JOIN teams t ON (s.home_team_id = t.id OR s.away_team_id = t.id)
                    LEFT JOIN clubs c ON t.club_id = c.id
                    WHERE s.match_date >= CURRENT_DATE
                    ORDER BY s.match_date ASC
                    LIMIT 5
                """
                
                cursor.execute(sample_query)
                sample_entries = cursor.fetchall()
                
                print("   Sample future schedule entries:")
                for entry in sample_entries:
                    print(f"   - {entry[0]} at {entry[1]}: {entry[2]} vs {entry[3]} ({entry[5]})")
        
    except Exception as e:
        print(f"   ❌ Error testing function: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Debug completed - check the summary above")

if __name__ == "__main__":
    debug_upcoming_schedule() 