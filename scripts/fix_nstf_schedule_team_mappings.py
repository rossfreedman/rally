#!/usr/bin/env python3
"""
Fix NSTF Schedule Team Mappings
===============================

This script specifically fixes NSTF schedule data by properly mapping team_ids
for matches that were imported with NULL team_ids due to NSTF team name format mismatches.

The issue: NSTF schedule data has team names like "Wilmette S1 T1 - Series 1" 
but teams table has "Wilmette S1 T1", causing NULL team_id mappings.
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database_utils import execute_query, execute_query_one

def normalize_nstf_team_name_for_matching(team_name: str) -> str:
    """Normalize NSTF team name by removing ' - Series X' suffix for matching"""
    if " - Series " in team_name:
        return team_name.split(" - Series ")[0]
    return team_name

def fix_nstf_schedule_team_mappings():
    """Fix team_id mappings in schedule table for NSTF league"""
    print("🔧 Fixing NSTF Schedule Team Mappings")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    try:
        # Find all NSTF schedule entries with NULL team_ids
        null_team_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team,
                s.away_team,
                s.location,
                s.league_id
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE (s.home_team_id IS NULL OR s.away_team_id IS NULL)
            AND l.league_id = 'NSTF'
            AND (s.home_team != 'BYE' AND s.away_team != 'BYE')
            ORDER BY s.match_date ASC
        """
        
        null_team_schedules = execute_query(null_team_query)
        print(f"Found {len(null_team_schedules)} NSTF schedule entries with NULL team_ids")
        
        if not null_team_schedules:
            print("✅ No NSTF schedule entries need fixing!")
            return True
        
        fixed_count = 0
        error_count = 0
        
        for schedule in null_team_schedules:
            try:
                schedule_id = schedule['id']
                home_team = schedule['home_team']
                away_team = schedule['away_team']
                
                # Try to find team IDs
                home_team_id = None
                away_team_id = None
                
                # Try exact match first, then normalized match
                if home_team and home_team != "BYE":
                    # Exact match
                    home_result = execute_query_one(
                        """
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = 'NSTF' AND t.team_name = %s
                        """,
                        (home_team,)
                    )
                    
                    if not home_result:
                        # Normalized match (remove " - Series X" suffix)
                        normalized_home = normalize_nstf_team_name_for_matching(home_team)
                        home_result = execute_query_one(
                            """
                            SELECT t.id FROM teams t
                            JOIN leagues l ON t.league_id = l.id
                            WHERE l.league_id = 'NSTF' AND t.team_name = %s
                            """,
                            (normalized_home,)
                        )
                    
                    home_team_id = home_result['id'] if home_result else None
                
                if away_team and away_team != "BYE":
                    # Exact match
                    away_result = execute_query_one(
                        """
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = 'NSTF' AND t.team_name = %s
                        """,
                        (away_team,)
                    )
                    
                    if not away_result:
                        # Normalized match (remove " - Series X" suffix)
                        normalized_away = normalize_nstf_team_name_for_matching(away_team)
                        away_result = execute_query_one(
                            """
                            SELECT t.id FROM teams t
                            JOIN leagues l ON t.league_id = l.id
                            WHERE l.league_id = 'NSTF' AND t.team_name = %s
                            """,
                            (normalized_away,)
                        )
                    
                    away_team_id = away_result['id'] if away_result else None
                
                # Update the schedule entry
                if home_team_id is not None or away_team_id is not None:
                    update_query = """
                        UPDATE schedule 
                        SET home_team_id = %s, away_team_id = %s
                        WHERE id = %s
                    """
                    execute_query(update_query, (home_team_id, away_team_id, schedule_id))
                    fixed_count += 1
                    
                    if fixed_count % 10 == 0:
                        print(f"   ✅ Fixed {fixed_count} NSTF schedule entries...")
                else:
                    print(f"⚠️  Schedule {schedule_id}: Could not find team IDs for '{home_team}' vs '{away_team}'")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ Error fixing schedule {schedule.get('id', 'unknown')}: {str(e)}")
                error_count += 1
        
        print(f"\n✅ NSTF Fix complete!")
        print(f"📊 Fixed: {fixed_count} NSTF schedule entries")
        print(f"❌ Errors: {error_count} entries")
        
        # Verify the fix
        remaining_null_query = """
            SELECT COUNT(*) as count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE (s.home_team_id IS NULL OR s.away_team_id IS NULL)
            AND l.league_id = 'NSTF'
            AND (s.home_team != 'BYE' AND s.away_team != 'BYE')
        """
        remaining_result = execute_query_one(remaining_null_query)
        remaining_count = remaining_result['count']
        
        print(f"📊 Remaining NSTF NULL team_ids: {remaining_count}")
        
        if remaining_count == 0:
            print("🎉 All NSTF schedule team mappings fixed!")
        else:
            print(f"⚠️  {remaining_count} NSTF schedule entries still have NULL team_ids")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    success = fix_nstf_schedule_team_mappings()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 