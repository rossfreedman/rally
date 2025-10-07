#!/usr/bin/env python3

"""
Remove unique_team_club_series_league constraint from local database only.

This script safely removes the constraint that prevents multiple teams
from existing in the same club/series/league combination, which is needed
for APTA teams like "Wilmette PD I 11" and "Wilmette PD II 11".

SAFETY CHECKS:
- Only runs on local database (localhost)
- Validates constraint exists before removal
- Provides rollback instructions
- Logs all operations
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_update
from database_config import get_db_url, is_local_development

def check_database_environment():
    """Ensure we're only running on local database"""
    if not is_local_development():
        print("❌ ERROR: This script can only run on local database!")
        print("   Current environment is not local development")
        sys.exit(1)
    
    db_url = get_db_url()
    print(f"✅ Confirmed running on local database: {db_url}")

def check_constraint_exists():
    """Check if the constraint exists before attempting removal"""
    query = """
    SELECT 
        conname as constraint_name,
        pg_get_constraintdef(oid) as constraint_definition
    FROM pg_constraint 
    WHERE conrelid = 'teams'::regclass
    AND conname = 'unique_team_club_series_league'
    """
    
    results = execute_query(query)
    
    if not results:
        print("❌ Constraint 'unique_team_club_series_league' not found!")
        print("   It may have already been removed.")
        return False
    
    constraint = results[0]
    print(f"✅ Found constraint: {constraint['constraint_name']}")
    print(f"   Definition: {constraint['constraint_definition']}")
    return True

def check_current_violations():
    """Check for any current constraint violations"""
    query = """
    SELECT 
        t.club_id,
        c.name as club_name,
        t.series_id,
        s.name as series_name,
        t.league_id,
        l.league_id as league_code,
        COUNT(*) as team_count,
        STRING_AGG(t.team_name, ', ') as team_names
    FROM teams t
    JOIN clubs c ON t.club_id = c.id
    JOIN series s ON t.series_id = s.id
    JOIN leagues l ON t.league_id = l.id
    GROUP BY t.club_id, c.name, t.series_id, s.name, t.league_id, l.league_id
    HAVING COUNT(*) > 1
    ORDER BY team_count DESC
    """
    
    results = execute_query(query)
    
    if results:
        print(f"⚠️  Found {len(results)} club/series/league combinations with multiple teams:")
        for record in results:
            print(f"   {record['club_name']} - {record['series_name']} ({record['league_code']}): {record['team_count']} teams")
            print(f"     Teams: {record['team_names']}")
        return True
    else:
        print("✅ No current violations found")
        return False

def remove_constraint():
    """Remove the unique_team_club_series_league constraint"""
    print("\n🔧 Removing constraint 'unique_team_club_series_league'...")
    
    drop_query = """
    ALTER TABLE teams 
    DROP CONSTRAINT IF EXISTS unique_team_club_series_league
    """
    
    try:
        result = execute_update(drop_query)
        print("✅ Constraint removed successfully!")
        return True
    except Exception as e:
        print(f"❌ Error removing constraint: {str(e)}")
        return False

def verify_constraint_removed():
    """Verify the constraint was actually removed"""
    query = """
    SELECT 
        conname as constraint_name
    FROM pg_constraint 
    WHERE conrelid = 'teams'::regclass
    AND conname = 'unique_team_club_series_league'
    """
    
    results = execute_query(query)
    
    if not results:
        print("✅ Constraint successfully removed!")
        return True
    else:
        print("❌ Constraint still exists!")
        return False

def test_apta_scenario():
    """Test if we can now create multiple APTA teams in same club/series"""
    print("\n🧪 Testing APTA scenario...")
    
    # Check if we can now have multiple teams in same club/series/league
    query = """
    SELECT 
        t1.id as team1_id,
        t1.team_name as team1_name,
        t2.id as team2_id,
        t2.team_name as team2_name,
        c.name as club_name,
        s.name as series_name,
        l.league_id
    FROM teams t1
    JOIN teams t2 ON t1.club_id = t2.club_id 
        AND t1.series_id = t2.series_id 
        AND t1.league_id = t2.league_id
        AND t1.id != t2.id
    JOIN clubs c ON t1.club_id = c.id
    JOIN series s ON t1.series_id = s.id
    JOIN leagues l ON t1.league_id = l.id
    WHERE l.league_id = 'APTA_CHICAGO'
    ORDER BY t1.team_name, t1.id
    """
    
    results = execute_query(query)
    
    if results:
        print(f"✅ Found {len(results)} APTA teams in same club/series combinations:")
        for record in results:
            print(f"   {record['team1_name']} (ID: {record['team1_id']})")
            print(f"   {record['team2_name']} (ID: {record['team2_id']})")
            print(f"   Club: {record['club_name']}, Series: {record['series_name']}")
            print()
    else:
        print("ℹ️  No APTA teams found in same club/series combinations yet")
        print("   This is expected - the constraint prevented them from being created")

def provide_rollback_instructions():
    """Provide instructions for rolling back the change"""
    print("\n📋 ROLLBACK INSTRUCTIONS:")
    print("If you need to restore the constraint, run:")
    print()
    print("ALTER TABLE teams")
    print("ADD CONSTRAINT unique_team_club_series_league")
    print("UNIQUE (club_id, series_id, league_id);")
    print()
    print("Note: This will fail if there are existing violations!")

def main():
    """Main execution function"""
    print("=" * 60)
    print("REMOVE UNIQUE_TEAM_CLUB_SERIES_LEAGUE CONSTRAINT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Safety checks
    check_database_environment()
    
    # Check if constraint exists
    if not check_constraint_exists():
        print("\n❌ Cannot proceed - constraint not found")
        sys.exit(1)
    
    # Check for current violations
    has_violations = check_current_violations()
    
    if has_violations:
        print("\n⚠️  WARNING: Found existing violations!")
        print("   The constraint is currently preventing data issues.")
        print("   Removing it may cause data inconsistency.")
        
        response = input("\nDo you want to continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Operation cancelled by user")
            sys.exit(1)
    
    # Remove the constraint
    if not remove_constraint():
        print("\n❌ Failed to remove constraint")
        sys.exit(1)
    
    # Verify removal
    if not verify_constraint_removed():
        print("\n❌ Constraint removal verification failed")
        sys.exit(1)
    
    # Test APTA scenario
    test_apta_scenario()
    
    # Provide rollback instructions
    provide_rollback_instructions()
    
    print("\n" + "=" * 60)
    print("✅ CONSTRAINT REMOVAL COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Next steps:")
    print("1. Test the APTA import process")
    print("2. Verify Chris Tag duplicate issue is resolved")
    print("3. Monitor for any data integrity issues")

if __name__ == "__main__":
    main()
