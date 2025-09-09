#!/usr/bin/env python3
"""
Clean Orphaned Availability Records
===================================

Remove availability records that reference non-existent players or have
series_id mismatches. This fixes incomplete end_season cleanup.

Usage: python scripts/clean_orphaned_availability_records.py [--dry-run]
"""

import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database_config import get_db_url

def clean_orphaned_availability_records(dry_run=False):
    """Clean orphaned availability records"""
    
    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("🧹 CLEANING ORPHANED AVAILABILITY RECORDS")
        print("=" * 50)
        
        # 1. Find availability records with non-existent player_ids
        print("\n1. Finding availability records with non-existent player_ids...")
        cur.execute("""
            SELECT pa.id, pa.player_name, pa.match_date, pa.series_id, pa.player_id
            FROM player_availability pa
            LEFT JOIN players p ON pa.player_id = p.id
            WHERE p.id IS NULL
            ORDER BY pa.match_date DESC
        """)
        
        orphaned_players = cur.fetchall()
        print(f"   Found {len(orphaned_players)} records with non-existent player_ids:")
        
        orphaned_ids = []
        for record in orphaned_players:
            print(f"     ID {record['id']}: {record['player_name']} ({record['match_date']}) - Player ID {record['player_id']} not found")
            orphaned_ids.append(record['id'])
        
        # 2. Find availability records with series_id mismatches
        print("\n2. Finding availability records with series_id mismatches...")
        cur.execute("""
            SELECT pa.id, pa.player_name, pa.match_date, pa.series_id, pa.player_id,
                   p.series_id as current_player_series
            FROM player_availability pa
            JOIN players p ON pa.player_id = p.id
            WHERE pa.series_id != p.series_id
            ORDER BY pa.match_date DESC
        """)
        
        mismatched_series = cur.fetchall()
        print(f"   Found {len(mismatched_series)} records with series_id mismatches:")
        
        mismatch_fixes = []
        for record in mismatched_series:
            print(f"     ID {record['id']}: {record['player_name']} - Avail series {record['series_id']} vs Player series {record['current_player_series']}")
            mismatch_fixes.append((record['id'], record['current_player_series']))
        
        # 3. Execute cleanup
        total_cleaned = 0
        
        if orphaned_ids:
            print(f"\n3. Cleaning {len(orphaned_ids)} orphaned records...")
            if not dry_run:
                placeholders = ",".join(["%s"] * len(orphaned_ids))
                cur.execute(f"DELETE FROM player_availability WHERE id IN ({placeholders})", orphaned_ids)
                deleted_orphaned = cur.rowcount
                print(f"   ✅ Deleted {deleted_orphaned} orphaned records")
                total_cleaned += deleted_orphaned
            else:
                print(f"   🔍 DRY RUN: Would delete {len(orphaned_ids)} orphaned records")
        
        if mismatch_fixes:
            print(f"\n4. Fixing {len(mismatch_fixes)} series_id mismatches...")
            if not dry_run:
                for record_id, correct_series_id in mismatch_fixes:
                    cur.execute("UPDATE player_availability SET series_id = %s WHERE id = %s", 
                              (correct_series_id, record_id))
                fixed_mismatches = cur.rowcount
                print(f"   ✅ Fixed {len(mismatch_fixes)} series_id mismatches")
                total_cleaned += len(mismatch_fixes)
            else:
                print(f"   🔍 DRY RUN: Would fix {len(mismatch_fixes)} series_id mismatches")
        
        # 4. Verify cleanup
        if not dry_run:
            conn.commit()
            
            print(f"\n5. Verifying cleanup...")
            # Recheck orphaned records
            cur.execute("""
                SELECT COUNT(*) FROM player_availability pa
                LEFT JOIN players p ON pa.player_id = p.id
                WHERE p.id IS NULL
            """)
            remaining_orphaned = cur.fetchone()['count']
            
            # Recheck mismatches
            cur.execute("""
                SELECT COUNT(*) FROM player_availability pa
                JOIN players p ON pa.player_id = p.id
                WHERE pa.series_id != p.series_id
            """)
            remaining_mismatches = cur.fetchone()['count']
            
            print(f"   Remaining orphaned records: {remaining_orphaned}")
            print(f"   Remaining series_id mismatches: {remaining_mismatches}")
            
            if remaining_orphaned == 0 and remaining_mismatches == 0:
                print("   ✅ All availability data integrity issues resolved!")
            else:
                print("   ⚠️ Some issues remain - may need additional investigation")
        
        print(f"\n🎉 CLEANUP COMPLETE")
        print(f"   Total records processed: {total_cleaned}")
        print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE CLEANUP'}")
        
        return True
        
    except Exception as e:
        if not dry_run:
            conn.rollback()
        print(f"❌ Error during cleanup: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    finally:
        cur.close()
        conn.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Clean orphaned availability records")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without making changes")
    args = parser.parse_args()
    
    success = clean_orphaned_availability_records(dry_run=args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
