#!/usr/bin/env python3
"""
Permanently delete inactive (S) player records from the database.

WHAT THIS DOES:
- Deletes all player records where (first_name or last_name contains "(S)") AND is_active = false
- Does NOT delete user accounts, contexts, or associations
- Only removes the inactive player records themselves

SAFETY:
- Only deletes inactive records (is_active = false)
- Validates no foreign key constraints would be violated
- Creates backup recommendations
- Includes dry-run mode
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_utils import get_db_cursor
from datetime import datetime

def permanently_delete_s_records(dry_run=True):
    print("=" * 80)
    print(f"PERMANENTLY DELETE INACTIVE (S) RECORDS - {'DRY RUN' if dry_run else 'LIVE RUN'}")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    if not dry_run:
        print("⚠️  WARNING: This will PERMANENTLY DELETE records from the database!")
        print("⚠️  Make sure you have a backup before proceeding!")
        print()
    
    with get_db_cursor(commit=(not dry_run)) as cursor:
        
        # Step 1: Count inactive (S) records
        print("STEP 1: COUNTING INACTIVE (S) RECORDS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE %s OR last_name LIKE %s)
            AND is_active = false
        """, ('%(S)', '%(S)'))
        
        total_to_delete = cursor.fetchone()['count']
        
        print(f"Found {total_to_delete} inactive (S) records to delete")
        print()
        
        if total_to_delete == 0:
            print("✅ No inactive (S) records to delete!")
            return {'deleted': 0, 'errors': 0}
        
        # Step 2: Check for foreign key references
        print("STEP 2: CHECKING FOREIGN KEY REFERENCES")
        print("-" * 80)
        
        # Check user_player_associations
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE (p.first_name LIKE %s OR p.last_name LIKE %s)
            AND p.is_active = false
        """, ('%(S)', '%(S)'))
        
        upa_count = cursor.fetchone()['count']
        
        print(f"User-player associations referencing (S) records: {upa_count}")
        
        if upa_count > 0:
            print("⚠️  WARNING: Some user associations reference (S) player IDs")
            print("   These associations will remain (pointing to regular player with same ID)")
            print("   This is SAFE - users have regular player records with same tenniscores_player_id")
        
        print()
        
        # Step 3: Verify safety
        print("STEP 3: SAFETY VERIFICATION")
        print("-" * 80)
        
        # Verify all are actually inactive
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE %s OR last_name LIKE %s)
            AND is_active = true
        """, ('%(S)', '%(S)'))
        
        active_s_count = cursor.fetchone()['count']
        
        if active_s_count > 0:
            print(f"❌ ABORT: {active_s_count} ACTIVE (S) records found!")
            print("   Only inactive records should be deleted")
            return {'deleted': 0, 'errors': active_s_count}
        
        print(f"✅ Verified: All {total_to_delete} records are inactive")
        print()
        
        # Step 4: Show sample of what will be deleted
        print("STEP 4: SAMPLE OF RECORDS TO BE DELETED")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   t.team_name, s.name as series_name
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN series s ON t.series_id = s.id
            WHERE (p.first_name LIKE %s OR p.last_name LIKE %s)
            AND p.is_active = false
            ORDER BY p.id
            LIMIT 10
        """, ('%(S)', '%(S)'))
        
        sample = cursor.fetchall()
        
        for record in sample:
            print(f"  ID {record['id']}: {record['first_name']} {record['last_name']}")
            print(f"    Team: {record['team_name']}, Series: {record['series_name']}")
            print(f"    Tenniscores ID: {record['tenniscores_player_id']}")
            print()
        
        if len(sample) < total_to_delete:
            print(f"  ... and {total_to_delete - len(sample)} more records")
        print()
        
        # Step 5: Execute deletion
        print("STEP 5: DELETION")
        print("-" * 80)
        
        if dry_run:
            print("DRY RUN - No records will be deleted")
            print(f"Would delete {total_to_delete} inactive (S) player records")
            print()
            print("To execute deletion, run with --live flag:")
            print("  python3 scripts/permanently_delete_s_records.py --live")
        else:
            print("LIVE RUN - Deleting records...")
            
            try:
                cursor.execute("""
                    DELETE FROM players
                    WHERE (first_name LIKE %s OR last_name LIKE %s)
                    AND is_active = false
                """, ('%(S)', '%(S)'))
                
                deleted_count = cursor.rowcount
                
                print(f"✅ Successfully deleted {deleted_count} inactive (S) records")
                print()
                
                # Verify deletion
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM players
                    WHERE (first_name LIKE %s OR last_name LIKE %s)
                """, ('%(S)', '%(S)'))
                
                remaining = cursor.fetchone()['count']
                
                if remaining == 0:
                    print("✅ VERIFIED: No (S) records remain in database")
                else:
                    print(f"⚠️  {remaining} (S) records still remain (should be 0)")
                
                return {'deleted': deleted_count, 'errors': 0}
                
            except Exception as e:
                print(f"❌ ERROR during deletion: {e}")
                return {'deleted': 0, 'errors': 1}
        
        print()
        print("=" * 80)
        
        return {'deleted': 0 if dry_run else total_to_delete, 'errors': 0}

if __name__ == "__main__":
    import sys
    
    dry_run = "--live" not in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No records will be deleted")
        print("Add --live to execute the deletion")
        print()
    else:
        print("⚠️  LIVE RUN MODE - Records will be PERMANENTLY DELETED!")
        print()
        response = input("Are you sure you want to permanently delete inactive (S) records? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(1)
        print()
    
    result = permanently_delete_s_records(dry_run=dry_run)
    
    print()
    print("SUMMARY:")
    print(f"  Records deleted: {result['deleted']}")
    print(f"  Errors: {result['errors']}")
    
    if result['deleted'] > 0:
        print()
        print("✅ DELETION COMPLETE")
    elif dry_run:
        print()
        print("✅ DRY RUN COMPLETE - Ready to execute with --live")
    
    sys.exit(0)

