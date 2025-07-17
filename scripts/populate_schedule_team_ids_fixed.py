#!/usr/bin/env python3
"""
Populate home_team_id and away_team_id in schedule table by matching team names within the same league
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def populate_schedule_team_ids_fixed():
    """Populate team IDs in schedule table by matching team names within the same league"""
    
    print("🔧 Populating Schedule Team IDs (League-Aware)")
    print("=" * 60)
    
    # Local database URL for local testing
    local_url = "postgresql://localhost/rally"
    try:
        # Parse and connect to local database
        parsed = urlparse(local_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username if parsed.username else None,
            password=parsed.password if parsed.password else None,
            host=parsed.hostname,
            port=parsed.port if parsed.port else 5432
        )
        
        cursor = conn.cursor()
        
        # First, let's see what leagues we have in the schedule
        print("1. 📊 Leagues in Schedule Table:")
        cursor.execute("""
            SELECT DISTINCT league_id, COUNT(*) as count
            FROM schedule 
            WHERE league_id IS NOT NULL
            GROUP BY league_id
            ORDER BY league_id
        """)
        leagues = cursor.fetchall()
        for league_id, count in leagues:
            cursor.execute("SELECT league_name FROM leagues WHERE id = %s", [league_id])
            league_name = cursor.fetchone()
            print(f"   League {league_id}: {league_name[0] if league_name else 'Unknown'} ({count} entries)")
        
        print()
        
        # Get all unique team names from schedule, grouped by league
        cursor.execute("""
            SELECT DISTINCT league_id, home_team, away_team 
            FROM schedule 
            WHERE (home_team_id IS NULL OR away_team_id IS NULL)
            AND league_id IS NOT NULL
            ORDER BY league_id, home_team, away_team
        """)
        team_names = cursor.fetchall()
        
        print(f"Found {len(team_names)} unique team name pairs to process")
        
        # Create a mapping of schedule team names to team IDs, grouped by league
        team_mapping = {}
        
        for league_id, home_team, away_team in team_names:
            if home_team and (league_id, home_team) not in team_mapping:
                # Try to find a matching team in the same league
                cursor.execute("""
                    SELECT t.id, t.team_name 
                    FROM teams t
                    WHERE t.league_id = %s 
                    AND (t.team_name ILIKE %s OR t.team_name ILIKE %s)
                """, [league_id, f"%{home_team.split()[0]}%", f"%{home_team}%"])
                match = cursor.fetchone()
                if match:
                    team_mapping[(league_id, home_team)] = match[0]
                    print(f"   League {league_id}: '{home_team}' -> {match[1]} (ID: {match[0]})")
                else:
                    print(f"   League {league_id}: ❌ No match for '{home_team}'")
            
            if away_team and (league_id, away_team) not in team_mapping:
                # Try to find a matching team in the same league
                cursor.execute("""
                    SELECT t.id, t.team_name 
                    FROM teams t
                    WHERE t.league_id = %s 
                    AND (t.team_name ILIKE %s OR t.team_name ILIKE %s)
                """, [league_id, f"%{away_team.split()[0]}%", f"%{away_team}%"])
                match = cursor.fetchone()
                if match:
                    team_mapping[(league_id, away_team)] = match[0]
                    print(f"   League {league_id}: '{away_team}' -> {match[1]} (ID: {match[0]})")
                else:
                    print(f"   League {league_id}: ❌ No match for '{away_team}'")
        
        print(f"\nTeam mapping created: {len(team_mapping)} mappings")
        
        # Update schedule table with team IDs
        updated_count = 0
        for (league_id, team_name), team_id in team_mapping.items():
            cursor.execute("""
                UPDATE schedule 
                SET home_team_id = %s 
                WHERE league_id = %s AND home_team = %s AND home_team_id IS NULL
            """, [team_id, league_id, team_name])
            home_updated = cursor.rowcount
            
            cursor.execute("""
                UPDATE schedule 
                SET away_team_id = %s 
                WHERE league_id = %s AND away_team = %s AND away_team_id IS NULL
            """, [team_id, league_id, team_name])
            away_updated = cursor.rowcount
            
            updated_count += home_updated + away_updated
            if home_updated > 0 or away_updated > 0:
                print(f"   Updated {home_updated} home + {away_updated} away for League {league_id}: '{team_name}'")
        
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
    populate_schedule_team_ids_fixed() 