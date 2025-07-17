#!/usr/bin/env python3
"""
Test the refactored schedule notification function using team IDs
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_team_id_schedule():
    """Test schedule lookup using team IDs"""
    
    print("🧪 Testing Team ID-based Schedule Lookup")
    print("=" * 50)
    
    # Staging database URL
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        # Parse and connect to staging database
        parsed = urlparse(staging_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port
        )
        
        cursor = conn.cursor()
        
        # Test user data (Ross)
        user_id = 43
        player_id = "nndz-WkMrK3didjlnUT09"
        league_id = 4823
        team_id = 48003
        
        print(f"Testing with team_id: {team_id}")
        print()
        
        # Test the new team_id-based query
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
                c.club_address,
                CASE 
                    WHEN s.home_team_id = %s THEN 'practice'
                    ELSE 'match'
                END as type
            FROM schedule s
            LEFT JOIN teams t ON (s.home_team_id = t.id OR s.away_team_id = t.id)
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE (s.home_team_id = %s OR s.away_team_id = %s)
            AND s.match_date >= CURRENT_DATE
            ORDER BY s.match_date ASC, s.match_time ASC
            LIMIT 10
        """
        
        cursor.execute(schedule_query, [team_id, team_id, team_id])
        schedule_entries = cursor.fetchall()
        
        if schedule_entries:
            print(f"✅ Found {len(schedule_entries)} schedule entries using team_id {team_id}:")
            for entry in schedule_entries:
                print(f"   - {entry[9]}: {entry[5]} vs {entry[6]} on {entry[1]} at {entry[2]}")
                print(f"     Home team ID: {entry[3]}, Away team ID: {entry[4]}")
        else:
            print(f"❌ No schedule entries found for team_id: {team_id}")
            
            # Check if the team exists
            cursor.execute("SELECT id, team_name FROM teams WHERE id = %s", [team_id])
            team = cursor.fetchone()
            if team:
                print(f"   Team exists: {team[1]} (ID: {team[0]})")
            else:
                print(f"   Team ID {team_id} does not exist in teams table")
            
            # Check what schedule entries exist
            cursor.execute("SELECT DISTINCT home_team_id, away_team_id FROM schedule WHERE match_date >= CURRENT_DATE LIMIT 10")
            sample_ids = cursor.fetchall()
            print(f"   Sample team IDs in schedule: {sample_ids}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_team_id_schedule() 