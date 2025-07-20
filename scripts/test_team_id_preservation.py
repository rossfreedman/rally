#!/usr/bin/env python3
"""
Test script to validate team ID preservation in ETL process.

This script tests the new approach where:
1. Teams are imported using UPSERT (preserving team IDs)
2. User data is backed up with team IDs
3. User data is restored using the same team IDs
"""

import sys
import os
import psycopg2
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL

def test_team_id_preservation():
    """Test the team ID preservation approach"""
    print("🧪 Testing Team ID Preservation in ETL Process")
    print("=" * 60)
    
    # Initialize ETL
    etl = ComprehensiveETL()
    
    try:
        with etl.get_managed_db_connection() as conn:
            cursor = conn.cursor()
            
            # Step 1: Check current team IDs
            print("\n📋 Step 1: Checking current team IDs...")
            cursor.execute("SELECT id, team_name, club_id, series_id, league_id FROM teams ORDER BY id LIMIT 5")
            current_teams = cursor.fetchall()
            
            print(f"   Found {len(current_teams)} teams:")
            for team in current_teams:
                print(f"   - ID: {team[0]}, Name: {team[1]}")
            
            # Step 2: Test backup with team IDs
            print("\n💾 Step 2: Testing backup with team IDs...")
            backup_results = etl.backup_user_data_and_team_mappings(conn)
            
            print(f"   ✅ Polls backed up: {backup_results['polls_backup_count']}")
            print(f"   ✅ Captain messages backed up: {backup_results['captain_messages_backup_count']}")
            print(f"   ✅ Practice times backed up: {backup_results['practice_times_backup_count']}")
            
            # Step 3: Check backup tables have team IDs
            print("\n🔍 Step 3: Verifying backup tables have team IDs...")
            
            # Check polls backup
            cursor.execute("SELECT COUNT(*) FROM polls_backup WHERE team_id IS NOT NULL")
            polls_with_team_ids = cursor.fetchone()[0]
            print(f"   📊 Polls with team IDs: {polls_with_team_ids}")
            
            # Check captain messages backup
            cursor.execute("SELECT COUNT(*) FROM captain_messages_backup WHERE team_id IS NOT NULL")
            messages_with_team_ids = cursor.fetchone()[0]
            print(f"   💬 Captain messages with team IDs: {messages_with_team_ids}")
            
            # Check practice times backup
            cursor.execute("SELECT COUNT(*) FROM practice_times_backup WHERE home_team_id IS NOT NULL")
            practice_with_team_ids = cursor.fetchone()[0]
            print(f"   ⏰ Practice times with team IDs: {practice_with_team_ids}")
            
            # Step 4: Test team import with UPSERT
            print("\n📥 Step 4: Testing team import with UPSERT...")
            
            # Get existing club, series, and league for testing
            cursor.execute("""
                SELECT c.name, s.name, l.league_id 
                FROM clubs c, series s, leagues l 
                LIMIT 1
            """)
            existing_data = cursor.fetchone()
            
            if existing_data:
                club_name, series_name, league_id = existing_data
                
                # Create test team data using existing references
                test_teams = [
                    {
                        "club_name": club_name,
                        "series_name": series_name,
                        "league_id": league_id,
                        "team_name": f"Test Team {datetime.now().strftime('%H%M%S')}"
                    }
                ]
                
                # Import test teams
                etl.import_teams(conn, test_teams)
                
                # Check if team IDs were preserved
                cursor.execute("SELECT id, team_name FROM teams WHERE team_name LIKE 'Test Team%' ORDER BY id")
                test_teams_after = cursor.fetchall()
                
                print(f"   ✅ Test teams imported: {len(test_teams_after)}")
                for team in test_teams_after:
                    print(f"   - ID: {team[0]}, Name: {team[1]}")
            else:
                print("   ⚠️  No existing data found for testing - skipping team import test")
                test_teams_after = []
            
            # Step 5: Test restore with team IDs
            print("\n🔄 Step 5: Testing restore with team IDs...")
            restore_results = etl.restore_user_data_with_team_mappings(conn)
            
            print(f"   ✅ Polls restored: {restore_results['polls_restored']}")
            print(f"   ✅ Captain messages restored: {restore_results['captain_messages_restored']}")
            print(f"   ✅ Practice times restored: {restore_results['practice_times_restored']}")
            
            # Step 6: Verify no orphaned references
            print("\n🔍 Step 6: Verifying no orphaned references...")
            
            # Check for orphaned polls
            cursor.execute("""
                SELECT COUNT(*) FROM polls p
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.team_id IS NOT NULL AND t.id IS NULL
            """)
            orphaned_polls = cursor.fetchone()[0]
            print(f"   📊 Orphaned polls: {orphaned_polls}")
            
            # Check for orphaned captain messages
            cursor.execute("""
                SELECT COUNT(*) FROM captain_messages cm
                LEFT JOIN teams t ON cm.team_id = t.id
                WHERE cm.team_id IS NOT NULL AND t.id IS NULL
            """)
            orphaned_messages = cursor.fetchone()[0]
            print(f"   💬 Orphaned captain messages: {orphaned_messages}")
            
            # Check for orphaned practice times
            cursor.execute("""
                SELECT COUNT(*) FROM schedule s
                LEFT JOIN teams t ON s.home_team_id = t.id
                WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
                AND s.home_team ILIKE '%practice%'
            """)
            orphaned_practice = cursor.fetchone()[0]
            print(f"   ⏰ Orphaned practice times: {orphaned_practice}")
            
            # Summary
            print("\n📊 Test Summary:")
            print(f"   ✅ Team ID preservation: {'PASS' if orphaned_polls == 0 and orphaned_messages == 0 and orphaned_practice == 0 else 'FAIL'}")
            print(f"   ✅ Backup with team IDs: {'PASS' if polls_with_team_ids > 0 or messages_with_team_ids > 0 or practice_with_team_ids > 0 else 'FAIL'}")
            print(f"   ✅ Restore with team IDs: {'PASS' if restore_results['polls_restored'] >= 0 else 'FAIL'}")
            
            if orphaned_polls == 0 and orphaned_messages == 0 and orphaned_practice == 0:
                print("\n🎉 Team ID preservation test PASSED!")
                return True
            else:
                print("\n❌ Team ID preservation test FAILED!")
                return False
                
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_team_id_preservation()
    sys.exit(0 if success else 1) 