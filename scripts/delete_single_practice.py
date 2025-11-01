#!/usr/bin/env python3
"""
Surgical deletion of a single practice for APTA Series 18 on Saturday 11/8.

This script:
1. Finds the APTA league
2. Finds Series 18
3. Identifies the practice on 11/8 for Series 18 teams
4. Shows the practice details before deletion
5. Safely deletes only that specific practice
"""

import sys
import os
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import execute_query, execute_query_one, get_db


def find_practice_to_delete(league_name="APTA Chicago", series_name="Series 18", practice_date_str="2025-11-08"):
    """
    Find the practice to delete based on league, series, and date.
    
    Args:
        league_name: Name of the league (default: "APTA Chicago")
        series_name: Name of the series (default: "Series 18")
        practice_date_str: Date in YYYY-MM-DD format (default: "2025-11-08")
    """
    print(f"\n🔍 Searching for practice:")
    print(f"   League: {league_name}")
    print(f"   Series: {series_name}")
    print(f"   Date: {practice_date_str}")
    print(f"   Day: Saturday\n")
    
    # Parse the date
    try:
        practice_date = datetime.strptime(practice_date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"❌ Error: Invalid date format. Expected YYYY-MM-DD, got {practice_date_str}")
        return None
    
    # Step 1: Find APTA league
    league_query = """
        SELECT id, league_name, league_id 
        FROM leagues 
        WHERE league_name ILIKE %s OR league_id ILIKE %s
    """
    league = execute_query_one(league_query, [f"%{league_name}%", f"%{league_name.split()[0]}%"])
    
    if not league:
        print(f"❌ Error: League '{league_name}' not found")
        return None
    
    print(f"✅ Found league: {league['league_name']} (ID: {league['id']})")
    
    # Step 2: Find Series 18
    series_query = """
        SELECT id, name 
        FROM series 
        WHERE league_id = %s AND (name ILIKE %s OR name = %s)
    """
    series = execute_query_one(
        series_query, 
        [league['id'], f"%{series_name}%", series_name]
    )
    
    if not series:
        print(f"❌ Error: Series '{series_name}' not found in {league['league_name']}")
        return None
    
    print(f"✅ Found series: {series['name']} (ID: {series['id']})")
    
    # Step 3: Find practices on the specified date for Series 18 teams
    # Match practices by either:
    # 1. Team's series_id matches Series 18
    # 2. Practice description contains "Series 18"
    practice_query = """
        SELECT 
            s.id,
            s.match_date,
            s.match_time,
            s.home_team,
            s.away_team,
            s.home_team_id,
            s.away_team_id,
            s.location,
            s.league_id,
            t.team_name,
            t.id as team_db_id,
            t.series_id,
            ser.name as series_name,
            c.name as club_name
        FROM schedule s
        LEFT JOIN teams t ON s.home_team_id = t.id
        LEFT JOIN series ser ON t.series_id = ser.id
        LEFT JOIN clubs c ON t.club_id = c.id
        WHERE s.match_date = %s
        AND s.home_team ILIKE '%%Practice%%'
        AND (s.league_id = %s OR s.league_id IS NULL)
        AND (t.series_id = %s OR s.home_team ILIKE %s)
        ORDER BY s.match_time, s.id
    """
    
    # Create pattern for Series 18 practice
    practice_pattern = f"%Series 18%"
    
    practices = execute_query(
        practice_query,
        [
            practice_date,
            league['id'],
            series['id'],
            practice_pattern
        ]
    )
    
    if not practices:
        print(f"❌ No practices found for {series_name} on {practice_date_str}")
        
        # Let's check what practices exist on that date anyway
        debug_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team,
                s.home_team_id,
                t.team_name,
                t.series_id,
                ser.name as series_name
            FROM schedule s
            LEFT JOIN teams t ON s.home_team_id = t.id
            LEFT JOIN series ser ON t.series_id = ser.id
            WHERE s.match_date = %s
            AND s.home_team ILIKE '%%Practice%%'
            AND s.league_id = %s
            ORDER BY s.match_time
        """
        all_practices = execute_query(debug_query, [practice_date, league['id']])
        if all_practices:
            print(f"\n   Found {len(all_practices)} practice(s) on that date:")
            for p in all_practices:
                print(f"   - ID {p['id']}: {p['home_team']} (Team: {p.get('team_name', 'N/A')}, Series: {p.get('series_name', 'N/A')})")
        return None
    
    if len(practices) > 1:
        print(f"\n⚠️  Warning: Found {len(practices)} practices matching the criteria:")
        for i, p in enumerate(practices, 1):
            print(f"\n   Practice {i}:")
            print(f"   - ID: {p['id']}")
            print(f"   - Date: {p['match_date']}")
            print(f"   - Time: {p['match_time']}")
            print(f"   - Description: {p['home_team']}")
            print(f"   - Team: {p.get('team_name', 'N/A')}")
            print(f"   - Club: {p.get('club_name', 'N/A')}")
            print(f"   - Location: {p.get('location', 'N/A')}")
        
        print(f"\n⚠️  Multiple practices found. Please specify which one to delete.")
        return None
    
    # Single practice found
    practice = practices[0]
    print(f"\n✅ Found practice:")
    print(f"   - ID: {practice['id']}")
    print(f"   - Date: {practice['match_date']}")
    print(f"   - Time: {practice['match_time']}")
    print(f"   - Description: {practice['home_team']}")
    print(f"   - Team: {practice.get('team_name', 'N/A')}")
    print(f"   - Club: {practice.get('club_name', 'N/A')}")
    print(f"   - Location: {practice.get('location', 'N/A')}")
    
    return practice


def delete_practice(practice_id):
    """
    Safely delete a practice from the schedule table.
    
    Args:
        practice_id: The ID of the practice to delete
    """
    if not practice_id:
        print("❌ Error: No practice ID provided")
        return False
    
    # First, verify it's still a practice (safety check)
    verify_query = """
        SELECT id, home_team, match_date, match_time
        FROM schedule
        WHERE id = %s AND home_team ILIKE '%%Practice%%'
    """
    practice = execute_query_one(verify_query, [practice_id])
    
    if not practice:
        print(f"❌ Error: Practice with ID {practice_id} not found or is not a practice")
        return False
    
    print(f"\n🗑️  Deleting practice:")
    print(f"   - ID: {practice['id']}")
    print(f"   - Date: {practice['match_date']}")
    print(f"   - Time: {practice['match_time']}")
    print(f"   - Description: {practice['home_team']}")
    
    # Delete the practice
    delete_query = "DELETE FROM schedule WHERE id = %s"
    
    # Use direct database connection for DELETE operation
    with get_db() as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(delete_query, [practice_id])
                rows_deleted = cursor.rowcount
                conn.commit()
                
                if rows_deleted == 0:
                    print("❌ Error: No rows deleted. Practice may not exist.")
                    return False
                
                # Verify deletion
                verify = execute_query_one(
                    "SELECT id FROM schedule WHERE id = %s",
                    [practice_id]
                )
                
                if verify:
                    print("❌ Error: Practice still exists after deletion attempt")
                    return False
                
                print(f"\n✅ Successfully deleted practice ID {practice_id}")
                return True
                
        except Exception as e:
            conn.rollback()
            print(f"❌ Error deleting practice: {str(e)}")
            return False


def main():
    """Main execution function"""
    print("=" * 60)
    print("SURGICAL PRACTICE DELETION TOOL")
    print("=" * 60)
    
    # Configuration - can be modified via command line args
    league_name = "APTA Chicago"
    series_name = "Series 18"
    practice_date = "2025-11-08"  # November 8, 2025 (Saturday)
    
    # Allow override via command line
    if len(sys.argv) > 1:
        practice_date = sys.argv[1]
    if len(sys.argv) > 2:
        series_name = sys.argv[2]
    
    # Find the practice
    practice = find_practice_to_delete(league_name, series_name, practice_date)
    
    if not practice:
        print("\n❌ No practice found to delete")
        return
    
    # Confirm deletion
    print("\n" + "=" * 60)
    response = input(f"\n⚠️  Are you sure you want to delete this practice? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("\n❌ Deletion cancelled")
        return
    
    # Delete the practice
    success = delete_practice(practice['id'])
    
    if success:
        print("\n✅ Practice deletion completed successfully")
    else:
        print("\n❌ Practice deletion failed")


if __name__ == "__main__":
    main()

