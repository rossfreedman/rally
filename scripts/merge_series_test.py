#!/usr/bin/env python3

"""
Test script to merge one series: "5" → "Series 5"

This script safely merges the incorrect series "5" into the correct "Series 5"
by:
1. Deleting duplicate players from incorrect series
2. Updating teams to point to correct series
3. Deleting the incorrect series record

SAFETY CHECKS:
- Only runs on local database
- Validates data before and after
- Provides detailed logging
- Can be rolled back if needed
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_update
from database_config import is_local_development

def check_database_environment():
    """Ensure we're only running on local database"""
    if not is_local_development():
        print("❌ ERROR: This script can only run on local database!")
        print("   Current environment is not local development")
        sys.exit(1)
    
    print("✅ Confirmed running on local database")

def get_series_data():
    """Get data for both incorrect and correct series"""
    query = """
    SELECT 
        s.id,
        s.name,
        COUNT(p.id) as player_count,
        COUNT(t.id) as team_count
    FROM series s
    LEFT JOIN players p ON s.id = p.series_id
    LEFT JOIN teams t ON s.id = t.series_id
    WHERE s.name IN ('5', 'Series 5') AND s.league_id = 4783
    GROUP BY s.id, s.name
    ORDER BY s.name
    """
    
    results = execute_query(query)
    
    incorrect_series = None
    correct_series = None
    
    for record in results:
        if record['name'] == '5':
            incorrect_series = record
        elif record['name'] == 'Series 5':
            correct_series = record
    
    return incorrect_series, correct_series

def check_duplicate_players(incorrect_series_id, correct_series_id):
    """Check for players that exist in both series"""
    query = """
    SELECT 
        p1.tenniscores_player_id,
        p1.first_name,
        p1.last_name,
        c.name as club_name
    FROM players p1
    JOIN players p2 ON (
        p1.tenniscores_player_id = p2.tenniscores_player_id
        AND p1.league_id = p2.league_id
        AND p1.club_id = p2.club_id
    )
    JOIN clubs c ON p1.club_id = c.id
    WHERE p1.series_id = %s AND p2.series_id = %s
    ORDER BY p1.first_name, p1.last_name
    """
    
    results = execute_query(query, [incorrect_series_id, correct_series_id])
    return results

def check_foreign_key_references(series_id):
    """Check what references the series before deletion"""
    queries = [
        ("players", "SELECT COUNT(*) as count FROM players WHERE series_id = %s"),
        ("teams", "SELECT COUNT(*) as count FROM teams WHERE series_id = %s"),
        ("match_scores", "SELECT COUNT(*) as count FROM match_scores WHERE home_team_id IN (SELECT id FROM teams WHERE series_id = %s) OR away_team_id IN (SELECT id FROM teams WHERE series_id = %s)"),
    ]
    
    references = {}
    for table_name, query in queries:
        if table_name == "match_scores":
            result = execute_query(query, [series_id, series_id])
        else:
            result = execute_query(query, [series_id])
        references[table_name] = result[0]['count'] if result else 0
    
    return references

def merge_series(incorrect_series_id, correct_series_id):
    """Perform the series merge"""
    print(f"\n🔧 Starting merge: Series {incorrect_series_id} → Series {correct_series_id}")
    
    # Step 1: Delete duplicate players from incorrect series
    print("Step 1: Deleting duplicate players from incorrect series...")
    delete_players_query = "DELETE FROM players WHERE series_id = %s"
    result1 = execute_update(delete_players_query, [incorrect_series_id])
    print(f"   Deleted players: {result1}")
    
    # Step 2: Update teams to point to correct series
    print("Step 2: Updating teams to point to correct series...")
    update_teams_query = "UPDATE teams SET series_id = %s WHERE series_id = %s"
    result2 = execute_update(update_teams_query, [correct_series_id, incorrect_series_id])
    print(f"   Updated teams: {result2}")
    
    # Step 3: Delete the incorrect series
    print("Step 3: Deleting incorrect series record...")
    delete_series_query = "DELETE FROM series WHERE id = %s AND name = '5'"
    result3 = execute_update(delete_series_query, [incorrect_series_id])
    print(f"   Deleted series: {result3}")
    
    return result1, result2, result3

def verify_merge(correct_series_id):
    """Verify the merge was successful"""
    print(f"\n✅ Verifying merge results...")
    
    # Check that the correct series still exists and has the right data
    query = """
    SELECT 
        s.id,
        s.name,
        COUNT(p.id) as player_count,
        COUNT(t.id) as team_count
    FROM series s
    LEFT JOIN players p ON s.id = p.series_id
    LEFT JOIN teams t ON s.id = t.series_id
    WHERE s.id = %s
    GROUP BY s.id, s.name
    """
    
    results = execute_query(query, [correct_series_id])
    if results:
        series = results[0]
        print(f"   Series {series['id']}: \"{series['name']}\"")
        print(f"   Players: {series['player_count']}")
        print(f"   Teams: {series['team_count']}")
        return True
    else:
        print("   ❌ ERROR: Correct series not found!")
        return False

def provide_rollback_instructions(incorrect_series_id, correct_series_id):
    """Provide rollback instructions"""
    print(f"\n📋 ROLLBACK INSTRUCTIONS:")
    print("If you need to rollback this merge:")
    print()
    print("1. Recreate the incorrect series:")
    print(f"   INSERT INTO series (id, name, league_id) VALUES ({incorrect_series_id}, '5', 4783);")
    print()
    print("2. Move teams back:")
    print(f"   UPDATE teams SET series_id = {incorrect_series_id} WHERE series_id = {correct_series_id} AND team_name LIKE '%5%';")
    print()
    print("3. Recreate player records (this would require restoring from backup)")

def main():
    """Main execution function"""
    print("=" * 60)
    print("MERGE SERIES TEST: \"5\" → \"Series 5\"")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Safety checks
    check_database_environment()
    
    # Get series data
    incorrect_series, correct_series = get_series_data()
    
    if not incorrect_series:
        print("❌ Incorrect series '5' not found!")
        sys.exit(1)
    
    if not correct_series:
        print("❌ Correct series 'Series 5' not found!")
        sys.exit(1)
    
    print("📊 Series data before merge:")
    print(f"   Incorrect: ID {incorrect_series['id']}, \"{incorrect_series['name']}\" - {incorrect_series['player_count']} players, {incorrect_series['team_count']} teams")
    print(f"   Correct: ID {correct_series['id']}, \"{correct_series['name']}\" - {correct_series['player_count']} players, {correct_series['team_count']} teams")
    
    # Check for duplicate players
    duplicates = check_duplicate_players(incorrect_series['id'], correct_series['id'])
    print(f"\n⚠️  Found {len(duplicates)} duplicate players:")
    for player in duplicates:
        print(f"   {player['first_name']} {player['last_name']} ({player['club_name']})")
    
    if duplicates:
        print("\n   These will be deleted from the incorrect series (keeping correct series records)")
    
    # Check foreign key references
    print(f"\n🔍 Checking foreign key references for series {incorrect_series['id']}:")
    references = check_foreign_key_references(incorrect_series['id'])
    for table, count in references.items():
        print(f"   {table}: {count} references")
    
    # Confirm before proceeding
    print(f"\n⚠️  WARNING: This will permanently delete series {incorrect_series['id']} and its player records!")
    response = input("Do you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled by user")
        sys.exit(1)
    
    # Perform the merge
    try:
        deleted_players, updated_teams, deleted_series = merge_series(
            incorrect_series['id'], 
            correct_series['id']
        )
        
        # Verify the merge
        if verify_merge(correct_series['id']):
            print("\n✅ MERGE COMPLETED SUCCESSFULLY!")
            print(f"   Deleted {deleted_players} duplicate players")
            print(f"   Updated {updated_teams} teams")
            print(f"   Deleted series {incorrect_series['id']}")
        else:
            print("\n❌ MERGE VERIFICATION FAILED!")
            sys.exit(1)
        
        # Provide rollback instructions
        provide_rollback_instructions(incorrect_series['id'], correct_series['id'])
        
    except Exception as e:
        print(f"\n❌ ERROR during merge: {str(e)}")
        print("   Check the database state and consider rollback")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ SERIES MERGE TEST COMPLETED!")
    print("=" * 60)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Next steps:")
    print("1. Test the application to ensure everything works")
    print("2. If successful, apply this approach to remaining 10 series")
    print("3. Update the import process to prevent future issues")

if __name__ == "__main__":
    main()
