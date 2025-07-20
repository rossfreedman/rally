#!/usr/bin/env python3
"""
Create missing NSTF teams from schedule data
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database_utils import execute_query, execute_query_one
from database_config import get_db

def create_nstf_missing_teams():
    """Create missing NSTF teams from schedule data"""
    print("🔧 Creating Missing NSTF Teams")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    try:
        # Get all unique NSTF team names from schedule that don't exist in teams table
        missing_teams_query = """
            SELECT DISTINCT 
                s.home_team as team_name,
                s.league_id
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'NSTF'
            AND s.home_team != 'BYE'
            AND s.home_team != ''
            AND NOT EXISTS (
                SELECT 1 FROM teams t 
                WHERE t.team_name = s.home_team 
                AND t.league_id = s.league_id
            )
            
            UNION
            
            SELECT DISTINCT 
                s.away_team as team_name,
                s.league_id
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'NSTF'
            AND s.away_team != 'BYE'
            AND s.away_team != ''
            AND NOT EXISTS (
                SELECT 1 FROM teams t 
                WHERE t.team_name = s.away_team 
                AND t.league_id = s.league_id
            )
        """
        
        missing_teams = execute_query(missing_teams_query)
        
        if not missing_teams:
            print("✅ No missing NSTF teams found")
            return 0
        
        print(f"📊 Found {len(missing_teams)} missing NSTF teams to create")
        
        teams_created = 0
        
        for team_record in missing_teams:
            team_name = team_record["team_name"]
            league_db_id = team_record["league_id"]
            
            try:
                # Parse team name to extract club and series
                # For NSTF: "Birchwood S3 - Series 3" -> club="Birchwood", series="Series 3"
                if " - Series " in team_name:
                    team_part = team_name.split(" - Series ")[0].strip()
                    series_name = f"Series {team_name.split(' - Series ')[1].strip()}"
                    
                    # Extract club name (everything before the first space + letter/number)
                    import re
                    club_match = re.match(r'^([A-Za-z\s]+?)(?:\s+[A-Za-z0-9]+)?$', team_part)
                    if club_match:
                        club_name = club_match.group(1).strip()
                    else:
                        print(f"⚠️  Could not extract club from: {team_part}")
                        continue
                else:
                    print(f"⚠️  Could not parse team name: {team_name}")
                    continue
                
                # Get club_id
                club_result = execute_query_one(
                    "SELECT id FROM clubs WHERE name = %s",
                    (club_name,)
                )
                
                if not club_result:
                    print(f"⚠️  Club not found: {club_name}")
                    continue
                
                club_id = club_result["id"]
                
                # Get series_id
                series_result = execute_query_one(
                    "SELECT id FROM series WHERE name = %s",
                    (series_name,)
                )
                
                if not series_result:
                    print(f"⚠️  Series not found: {series_name}")
                    continue
                
                series_id = series_result["id"]
                
                # Create the team
                execute_query(
                    """
                    INSERT INTO teams (team_name, display_name, club_id, series_id, league_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    (team_name, team_name, club_id, series_id, league_db_id)
                )
                
                teams_created += 1
                print(f"✅ Created team: {team_name}")
                
            except Exception as e:
                print(f"❌ Error creating team {team_name}: {str(e)}")
                continue
        
        print(f"\n✅ NSTF teams creation complete!")
        print(f"📊 Created {teams_created} NSTF teams")
        
        # Check the results
        null_count_query = """
            SELECT COUNT(*) as null_count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'NSTF'
            AND (s.home_team_id IS NULL OR s.away_team_id IS NULL)
        """
        null_result = execute_query_one(null_count_query)
        remaining_null = null_result["null_count"]
        
        print(f"📊 Remaining NSTF schedule entries with NULL team_ids: {remaining_null}")
        
        if remaining_null == 0:
            print("🎉 All NSTF schedule entries now have valid team mappings!")
        else:
            print(f"⚠️  {remaining_null} NSTF schedule entries still have NULL team_ids")
        
        return teams_created
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    create_nstf_missing_teams() 