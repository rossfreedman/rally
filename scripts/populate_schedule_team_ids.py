#!/usr/bin/env python3
"""
Populate home_team_id and away_team_id in schedule table by matching team names
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def populate_schedule_team_ids():
    """Populate team IDs in schedule table by matching team names"""
    
    print("🔧 Populating Schedule Team IDs")
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
        
        # Get all unique team names from schedule
        cursor.execute("""
            SELECT DISTINCT home_team, away_team 
            FROM schedule 
            WHERE home_team_id IS NULL OR away_team_id IS NULL
        """)
        team_names = cursor.fetchall()
        
        print(f"Found {len(team_names)} unique team name pairs to process")
        
        # Create a mapping of schedule team names to team IDs
        team_mapping = {}
        
        for home_team, away_team in team_names:
            if home_team and home_team not in team_mapping:
                # Try to find a matching team
                cursor.execute("""
                    SELECT id, team_name FROM teams 
                    WHERE team_name ILIKE %s OR team_name ILIKE %s
                """, [f"%{home_team.split()[0]}%", f"%{home_team}%"])
                match = cursor.fetchone()
                if match:
                    team_mapping[home_team] = match[0]
                    print(f"   '{home_team}' -> {match[1]} (ID: {match[0]})")
                else:
                    print(f"   ❌ No match for '{home_team}'")
            
            if away_team and away_team not in team_mapping:
                # Try to find a matching team
                cursor.execute("""
                    SELECT id, team_name FROM teams 
                    WHERE team_name ILIKE %s OR team_name ILIKE %s
                """, [f"%{away_team.split()[0]}%", f"%{away_team}%"])
                match = cursor.fetchone()
                if match:
                    team_mapping[away_team] = match[0]
                    print(f"   '{away_team}' -> {match[1]} (ID: {match[0]})")
                else:
                    print(f"   ❌ No match for '{away_team}'")
        
        print(f"\nTeam mapping created: {len(team_mapping)} mappings")
        
        # Update schedule table with team IDs
        updated_count = 0
        for team_name, team_id in team_mapping.items():
            cursor.execute("""
                UPDATE schedule 
                SET home_team_id = %s 
                WHERE home_team = %s AND home_team_id IS NULL
            """, [team_id, team_name])
            home_updated = cursor.rowcount
            
            cursor.execute("""
                UPDATE schedule 
                SET away_team_id = %s 
                WHERE away_team = %s AND away_team_id IS NULL
            """, [team_id, team_name])
            away_updated = cursor.rowcount
            
            updated_count += home_updated + away_updated
            if home_updated > 0 or away_updated > 0:
                print(f"   Updated {home_updated} home + {away_updated} away for '{team_name}'")
        
        conn.commit()
        print(f"\n✅ Updated {updated_count} schedule entries with team IDs")
        
        # Verify the update
        cursor.execute("""
            SELECT COUNT(*) FROM schedule 
            WHERE home_team_id IS NOT NULL OR away_team_id IS NOT NULL
        """)
        with_ids = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM schedule")
        total = cursor.fetchone()[0]
        
        print(f"Schedule entries with team IDs: {with_ids}/{total}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    populate_schedule_team_ids() 