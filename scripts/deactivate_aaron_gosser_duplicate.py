#!/usr/bin/env python3
"""
Deactivate Aaron Gosser's duplicate player record (Record #2).

This script deactivates the newer duplicate record that has no user associations,
keeping Record #1 which is linked to the user account.

Record #1 (KEEP): nndz-WkNDd3liZi9ndz09 (created Sept 17) - HAS user association
Record #2 (DEACTIVATE): nndz-WkNPd3g3djdoZz09 (created Oct 30) - NO user associations

Usage:
    # Dry run (local)
    DB_MODE=local python3 scripts/deactivate_aaron_gosser_duplicate.py --dry-run
    
    # Execute on local
    DB_MODE=local python3 scripts/deactivate_aaron_gosser_duplicate.py
    
    # Execute on production (requires --live flag)
    DB_MODE=production python3 scripts/deactivate_aaron_gosser_duplicate.py --live
"""

import psycopg2
from psycopg2.extras import DictCursor
import os
import sys
import argparse
from datetime import datetime

# Database URLs
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# Record to deactivate - ALL records with this player_id (multiple teams)
RECORD_TO_DEACTIVATE = {
    "tenniscores_player_id": "nndz-WkNPd3g3djdoZz09",
    "created_date": "2025-10-30",
    "description": "Record #2 (newer duplicate, no user associations) - ALL teams"
}

# Record to keep
RECORD_TO_KEEP = {
    "tenniscores_player_id": "nndz-WkNDd3liZi9ndz09",
    "created_date": "2025-09-17",
    "description": "Record #1 (original, has user association)"
}

def connect_database(database_mode):
    """Connect to database (local or production based on DB_MODE)"""
    db_url = LOCAL_DB_URL if database_mode == "local" else PRODUCTION_DB_URL
    db_name = "LOCAL" if database_mode == "local" else "PRODUCTION"
    
    try:
        conn = psycopg2.connect(db_url, cursor_factory=DictCursor)
        print(f"✅ Connected to {db_name} database")
        return conn
    except Exception as e:
        print(f"❌ Error connecting to {db_name} database: {e}")
        sys.exit(1)

def verify_record_to_deactivate(cur):
    """Verify ALL records we're about to deactivate exist and have no user associations"""
    print("\n🔍 Verifying records to deactivate...")
    print("-" * 80)
    
    # Get ALL records with this player_id (can have multiple teams)
    query = """
        SELECT 
            p.id,
            p.tenniscores_player_id,
            p.first_name,
            p.last_name,
            p.pti,
            p.is_active,
            p.team_id,
            p.series_id,
            p.club_id,
            p.created_at,
            c.name as club_name,
            t.team_name,
            s.name as series_name
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN series s ON p.series_id = s.id
        WHERE p.tenniscores_player_id = %s
        ORDER BY p.is_active DESC, p.created_at DESC
    """
    
    cur.execute(query, [RECORD_TO_DEACTIVATE["tenniscores_player_id"]])
    records = cur.fetchall()
    
    if not records:
        print(f"❌ No records found with tenniscores_player_id '{RECORD_TO_DEACTIVATE['tenniscores_player_id']}'!")
        return []
    
    print(f"✅ Found {len(records)} record(s):")
    for i, record in enumerate(records, 1):
        print(f"\n  Record #{i}:")
        print(f"   Database ID: {record['id']}")
        print(f"   Name: {record['first_name']} {record['last_name']}")
        print(f"   tenniscores_player_id: {record['tenniscores_player_id']}")
        print(f"   Club: {record['club_name']}")
        print(f"   Team: {record['team_name']} (ID: {record['team_id']})")
        print(f"   Series: {record['series_name']}")
        print(f"   PTI: {record['pti']}")
        print(f"   Currently Active: {record['is_active']}")
        print(f"   Created: {record['created_at']}")
    
    # Check for user associations
    assoc_query = """
        SELECT COUNT(*) as count
        FROM user_player_associations
        WHERE tenniscores_player_id = %s
    """
    cur.execute(assoc_query, [RECORD_TO_DEACTIVATE["tenniscores_player_id"]])
    assoc_result = cur.fetchone()
    association_count = assoc_result['count'] if assoc_result else 0
    
    print(f"\n   User Associations: {association_count}")
    
    if association_count > 0:
        print(f"   ⚠️  WARNING: This player_id has {association_count} user association(s)!")
        print(f"   Please review before deactivating.")
        
        # Show the associations
        assoc_detail_query = """
            SELECT 
                upa.user_id,
                u.email,
                u.first_name,
                u.last_name
            FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            WHERE upa.tenniscores_player_id = %s
        """
        cur.execute(assoc_detail_query, [RECORD_TO_DEACTIVATE["tenniscores_player_id"]])
        associations = cur.fetchall()
        
        for assoc in associations:
            print(f"      - User {assoc['user_id']}: {assoc['first_name']} {assoc['last_name']} ({assoc['email']})")
    else:
        print(f"   ✅ No user associations - safe to deactivate ALL records")
    
    # Return only active records
    active_records = [r for r in records if r['is_active']]
    if active_records:
        print(f"\n   {len(active_records)} active record(s) will be deactivated")
    
    return active_records

def verify_record_to_keep(cur):
    """Verify the record we're keeping still exists and is active"""
    print("\n🔍 Verifying record to keep...")
    print("-" * 80)
    
    query = """
        SELECT 
            p.id,
            p.tenniscores_player_id,
            p.first_name,
            p.last_name,
            p.is_active,
            COUNT(upa.user_id) as user_association_count
        FROM players p
        LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
        WHERE p.tenniscores_player_id = %s
        GROUP BY p.id, p.tenniscores_player_id, p.first_name, p.last_name, p.is_active
    """
    
    cur.execute(query, [RECORD_TO_KEEP["tenniscores_player_id"]])
    record = cur.fetchone()
    
    if not record:
        print(f"❌ Record with tenniscores_player_id '{RECORD_TO_KEEP['tenniscores_player_id']}' not found!")
        return None
    
    print(f"✅ Record to keep is present:")
    print(f"   Database ID: {record['id']}")
    print(f"   Name: {record['first_name']} {record['last_name']}")
    print(f"   tenniscores_player_id: {record['tenniscores_player_id']}")
    print(f"   Active: {record['is_active']}")
    print(f"   User Associations: {record['user_association_count']}")
    
    if not record['is_active']:
        print(f"   ⚠️  WARNING: Record to keep is not active!")
    
    if record['user_association_count'] == 0:
        print(f"   ⚠️  WARNING: Record to keep has no user associations!")
    
    return record

def deactivate_records(cur, records, dry_run=False):
    """Deactivate all specified records"""
    if not records:
        print(f"\n✅ No active records to deactivate")
        return 0
    
    if dry_run:
        print(f"\n🔍 DRY RUN: Would deactivate {len(records)} record(s)")
        for record in records:
            print(f"   Would deactivate record {record['id']}: {record['first_name']} {record['last_name']} - {record['team_name']} ({record['club_name']})")
        return len(records)
    
    print(f"\n🔄 Deactivating {len(records)} record(s)...")
    
    updated_count = 0
    for record in records:
        update_query = """
            UPDATE players
            SET is_active = false,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, first_name, last_name, is_active, updated_at
        """
        
        cur.execute(update_query, [record['id']])
        result = cur.fetchone()
        
        if result:
            updated_count += 1
            print(f"✅ Deactivated record {result['id']}: {result['first_name']} {result['last_name']} - Team ID {record['team_id']}")
        else:
            print(f"❌ Failed to deactivate record {record['id']}")
    
    return updated_count

def main():
    parser = argparse.ArgumentParser(description="Deactivate Aaron Gosser duplicate record")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--live", action="store_true", help="Required flag for production database")
    parser.add_argument("--yes", action="store_true", help="Auto-confirm without prompting (use with caution)")
    
    args = parser.parse_args()
    
    # Get database mode
    database_mode = os.getenv("DB_MODE", "local").lower()
    
    if database_mode == "production" and not args.live:
        print("❌ ERROR: Production database requires --live flag for safety")
        print("   Usage: DB_MODE=production python3 scripts/deactivate_aaron_gosser_duplicate.py --live")
        sys.exit(1)
    
    print("=" * 80)
    print("DEACTIVATE AARON GOSSER DUPLICATE RECORD")
    print("=" * 80)
    print()
    print(f"Database: {database_mode.upper()}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    print("Record to KEEP:")
    print(f"  {RECORD_TO_KEEP['description']}")
    print(f"  ID: {RECORD_TO_KEEP['tenniscores_player_id']}")
    print()
    print("Record to DEACTIVATE:")
    print(f"  {RECORD_TO_DEACTIVATE['description']}")
    print(f"  ID: {RECORD_TO_DEACTIVATE['tenniscores_player_id']}")
    print()
    
    # Connect to database
    conn = connect_database(database_mode)
    cur = conn.cursor()
    
    try:
        # Verify both records
        records_to_deactivate = verify_record_to_deactivate(cur)
        if not records_to_deactivate:
            print("\n✅ No active records to deactivate (all are already deactivated)")
            return
        
        record_to_keep = verify_record_to_keep(cur)
        if not record_to_keep:
            print("\n❌ Cannot proceed - record to keep not found")
            sys.exit(1)
        
        # Final confirmation for production
        if database_mode == "production" and not args.dry_run and not args.yes:
            print("\n" + "=" * 80)
            print("⚠️  PRODUCTION DATABASE - FINAL CONFIRMATION")
            print("=" * 80)
            print()
            print(f"This will deactivate {len(records_to_deactivate)} player record(s):")
            for record in records_to_deactivate:
                print(f"  • ID: {record['id']}, Team: {record['team_name']} ({record['club_name']})")
            print(f"\n  tenniscores_player_id: {RECORD_TO_DEACTIVATE['tenniscores_player_id']}")
            print()
            print("Type 'yes' to confirm: ", end='')
            confirmation = input().strip().lower()
            
            if confirmation != 'yes':
                print("❌ Cancelled - no changes made")
                return
        elif database_mode == "production" and not args.dry_run and args.yes:
            print("\n⚠️  PRODUCTION DATABASE - AUTO-CONFIRMED (--yes flag used)")
            print(f"Will deactivate {len(records_to_deactivate)} player record(s)")
        
        # Deactivate all records
        updated_count = deactivate_records(cur, records_to_deactivate, dry_run=args.dry_run)
        
        if updated_count > 0:
            if not args.dry_run:
                conn.commit()
                print(f"\n✅ Successfully deactivated {updated_count} record(s)")
                print("✅ Changes committed to database")
            else:
                print(f"\n✅ Dry run complete - would deactivate {updated_count} record(s)")
        else:
            if not args.dry_run:
                conn.rollback()
                print("\n❌ No records were updated")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        if not args.dry_run:
            conn.rollback()
        sys.exit(1)
    
    finally:
        cur.close()
        conn.close()
    
    print("\n✅ Operation complete!")

if __name__ == "__main__":
    main()

