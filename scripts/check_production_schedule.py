#!/usr/bin/env python3
"""
Check Production Schedule Data
"""

import os
import sys
import psycopg2

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_production_schedule():
    """Check production schedule data"""
    
    # Production database connection
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found")
        return
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("🔍 Checking Production Schedule Data")
        print("=" * 50)
        
        # Check team 49865
        cursor.execute("SELECT id, team_name, display_name FROM teams WHERE id = 49865")
        team_result = cursor.fetchone()
        print(f"Team 49865: {team_result}")
        
        # Check Tennaqua 22 teams
        cursor.execute("SELECT id, team_name, display_name FROM teams WHERE team_name LIKE '%Tennaqua%22%' OR display_name LIKE '%Tennaqua%22%'")
        tennaqua_teams = cursor.fetchall()
        print(f"\nTennaqua 22 teams:")
        for team in tennaqua_teams:
            print(f"  {team}")
        
        # Check schedule for team 49865
        if team_result:
            cursor.execute("""
                SELECT 
                    s.id,
                    s.match_date,
                    s.match_time,
                    s.home_team_id,
                    s.away_team_id,
                    s.home_team,
                    s.away_team,
                    s.location
                FROM schedule s
                WHERE (s.home_team_id = 49865 OR s.away_team_id = 49865)
                AND s.match_date >= CURRENT_DATE
                ORDER BY s.match_date ASC, s.match_time ASC
                LIMIT 10
            """)
            schedule_entries = cursor.fetchall()
            
            print(f"\nSchedule entries for team 49865:")
            for entry in schedule_entries:
                entry_id, match_date, match_time, home_team_id, away_team_id, home_team, away_team, location = entry
                print(f"  {match_date} {match_time}: {home_team} vs {away_team} ({location})")
                print(f"    home_team_id: {home_team_id}, away_team_id: {away_team_id}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_production_schedule() 