#!/usr/bin/env python3
"""
Reverse the Aaron Gosser fix: Reactivate Record #2, deactivate Record #1, and move user associations.

Record #1 (DEACTIVATE): nndz-WkNDd3liZi9ndz09 (created Sept 17) - HAS user association (OLD ID)
Record #2 (REACTIVATE): nndz-WkNPd3g3djdoZz09 (created Oct 30) - NO user associations (CURRENT ID on source website)

This script will:
1. Find and move user associations from Record #1 to Record #2
2. Reactivate Record #2
3. Deactivate Record #1
4. Reverse match ID reassignments (move matches back from Record #1 to Record #2)

Usage:
    # Dry run (local)
    DB_MODE=local python3 scripts/reverse_aaron_gosser_fix.py --dry-run
    
    # Execute on local
    DB_MODE=local python3 scripts/reverse_aaron_gosser_fix.py
    
    # Execute on production (requires --live flag)
    DB_MODE=production python3 scripts/reverse_aaron_gosser_fix.py --live
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

# Record #1 (to deactivate) - OLD ID with user associations
RECORD_TO_DEACTIVATE = {
    "tenniscores_player_id": "nndz-WkNDd3liZi9ndz09",
    "created_date": "2025-09-17",
    "description": "Record #1 (older ID, has user associations - OLD/DEPRECATED)"
}

# Record #2 (to reactivate) - CURRENT ID on source website
RECORD_TO_REACTIVATE = {
    "tenniscores_player_id": "nndz-WkNPd3g3djdoZz09",
    "created_date": "2025-10-30",
    "description": "Record #2 (newer ID, current on source website - CORRECT)"
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

def verify_current_state(cur):
    """Verify current state of both records"""
    print("\n🔍 Verifying current state...")
    print("=" * 80)
    
    # Check Record #1 (to deactivate)
    query1 = """
        SELECT 
            p.id,
            p.tenniscores_player_id,
            p.first_name,
            p.last_name,
            p.is_active,
            p.team_id,
            p.club_id,
            c.name as club_name,
            t.team_name,
            COUNT(DISTINCT upa.user_id) as user_association_count
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
        WHERE p.tenniscores_player_id = %s
        GROUP BY p.id, p.tenniscores_player_id, p.first_name, p.last_name, p.is_active, 
                 p.team_id, p.club_id, c.name, t.team_name
        ORDER BY p.is_active DESC, p.created_at DESC
    """
    
    cur.execute(query1, [RECORD_TO_DEACTIVATE["tenniscores_player_id"]])
    records1 = cur.fetchall()
    
    print(f"\n📋 Record #1 ({RECORD_TO_DEACTIVATE['tenniscores_player_id']}):")
    if records1:
        for record in records1:
            print(f"   ID: {record['id']}, Name: {record['first_name']} {record['last_name']}")
            print(f"   Team: {record['team_name']} ({record['club_name']})")
            print(f"   Active: {record['is_active']}")
            print(f"   User Associations: {record['user_association_count']}")
    else:
        print("   ❌ No records found")
    
    # Check Record #2 (to reactivate)
    query2 = """
        SELECT 
            p.id,
            p.tenniscores_player_id,
            p.first_name,
            p.last_name,
            p.is_active,
            p.team_id,
            p.club_id,
            c.name as club_name,
            t.team_name,
            COUNT(DISTINCT upa.user_id) as user_association_count
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
        WHERE p.tenniscores_player_id = %s
        GROUP BY p.id, p.tenniscores_player_id, p.first_name, p.last_name, p.is_active, 
                 p.team_id, p.club_id, c.name, t.team_name
        ORDER BY p.is_active DESC, p.created_at DESC
    """
    
    cur.execute(query2, [RECORD_TO_REACTIVATE["tenniscores_player_id"]])
    records2 = cur.fetchall()
    
    print(f"\n📋 Record #2 ({RECORD_TO_REACTIVATE['tenniscores_player_id']}):")
    if records2:
        for record in records2:
            print(f"   ID: {record['id']}, Name: {record['first_name']} {record['last_name']}")
            print(f"   Team: {record['team_name']} ({record['club_name']})")
            print(f"   Active: {record['is_active']}")
            print(f"   User Associations: {record['user_association_count']}")
    else:
        print("   ❌ No records found")
    
    # Get user associations for Record #1
    print(f"\n👤 User Associations for Record #1:")
    assoc_query = """
        SELECT 
            upa.user_id,
            u.email,
            u.first_name,
            u.last_name,
            upa.created_at
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        WHERE upa.tenniscores_player_id = %s
    """
    cur.execute(assoc_query, [RECORD_TO_DEACTIVATE["tenniscores_player_id"]])
    associations = cur.fetchall()
    
    if associations:
        for assoc in associations:
            print(f"   User {assoc['user_id']}: {assoc['first_name']} {assoc['last_name']} ({assoc['email']})")
    else:
        print("   No user associations found")
    
    return records1, records2, associations

def move_user_associations(cur, associations, dry_run=False):
    """Move user associations from Record #1 to Record #2"""
    if not associations:
        print("\n✅ No user associations to move")
        return 0
    
    print(f"\n{'🔍 DRY RUN: Would move' if dry_run else '🔄 Moving'} {len(associations)} user association(s)...")
    print("-" * 80)
    
    moved_count = 0
    
    for assoc in associations:
        user_id = assoc['user_id']
        old_id = RECORD_TO_DEACTIVATE["tenniscores_player_id"]
        new_id = RECORD_TO_REACTIVATE["tenniscores_player_id"]
        
        # Check if association already exists for Record #2
        check_query = """
            SELECT COUNT(*) as count
            FROM user_player_associations
            WHERE user_id = %s AND tenniscores_player_id = %s
        """
        cur.execute(check_query, [user_id, new_id])
        exists = cur.fetchone()['count'] > 0
        
        if exists:
            print(f"   ⚠️  User {user_id} already has association with Record #2 - skipping")
            # Still delete the old one
            if not dry_run:
                delete_query = """
                    DELETE FROM user_player_associations
                    WHERE user_id = %s AND tenniscores_player_id = %s
                """
                cur.execute(delete_query, [user_id, old_id])
                print(f"   ✅ Deleted old association for user {user_id}")
        else:
            if dry_run:
                print(f"   Would move association: User {user_id} ({assoc['email']}) from {old_id} to {new_id}")
            else:
                # Delete old association
                delete_query = """
                    DELETE FROM user_player_associations
                    WHERE user_id = %s AND tenniscores_player_id = %s
                """
                cur.execute(delete_query, [user_id, old_id])
                
                # Create new association
                insert_query = """
                    INSERT INTO user_player_associations (user_id, tenniscores_player_id, created_at)
                    VALUES (%s, %s, %s)
                """
                cur.execute(insert_query, [user_id, new_id, assoc['created_at'] or datetime.now()])
                
                print(f"   ✅ Moved association: User {user_id} ({assoc['email']}) from {old_id} to {new_id}")
                moved_count += 1
    
    return moved_count

def reverse_match_reassignments(cur, dry_run=False):
    """Reverse match ID reassignments: move matches back from Record #1 to Record #2"""
    print(f"\n{'🔍 DRY RUN: Would reverse' if dry_run else '🔄 Reversing'} match ID reassignments...")
    print("-" * 80)
    
    # Find matches currently linked to Record #1 (should be moved back to Record #2)
    query = """
        SELECT 
            id,
            match_date,
            home_team,
            away_team,
            home_player_1_id,
            home_player_2_id,
            away_player_1_id,
            away_player_2_id
        FROM match_scores
        WHERE (
            home_player_1_id = %s OR 
            home_player_2_id = %s OR
            away_player_1_id = %s OR
            away_player_2_id = %s
        )
        ORDER BY match_date DESC
    """
    
    cur.execute(query, [RECORD_TO_DEACTIVATE["tenniscores_player_id"]] * 4)
    matches = cur.fetchall()
    
    if not matches:
        print("✅ No matches found linked to Record #1 (already correct)")
        return 0
    
    print(f"✅ Found {len(matches)} match(es) to reverse:")
    for match in matches[:5]:
        print(f"   Match {match['id']}: {match['match_date']} - {match['home_team']} vs {match['away_team']}")
    
    if len(matches) > 5:
        print(f"   ... and {len(matches) - 5} more matches")
    
    updated_count = 0
    
    for match in matches:
        match_id = match['id']
        updates = []
        
        old_id = RECORD_TO_DEACTIVATE["tenniscores_player_id"]
        new_id = RECORD_TO_REACTIVATE["tenniscores_player_id"]
        
        # Check which fields need updating
        if match['home_player_1_id'] == old_id:
            updates.append("home_player_1_id")
        if match['home_player_2_id'] == old_id:
            updates.append("home_player_2_id")
        if match['away_player_1_id'] == old_id:
            updates.append("away_player_1_id")
        if match['away_player_2_id'] == old_id:
            updates.append("away_player_2_id")
        
        if not updates:
            continue
        
        # Build update query
        set_clauses = []
        params = []
        
        for field in updates:
            set_clauses.append(f"{field} = %s")
            params.append(new_id)
        
        params.append(match_id)
        
        update_query = f"""
            UPDATE match_scores
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """
        
        if dry_run:
            print(f"   Would update match {match_id}: {', '.join(updates)} from {old_id} to {new_id}")
        else:
            cur.execute(update_query, params)
            updated_count += 1
            if updated_count <= 5:
                print(f"   ✅ Updated match {match_id}: {', '.join(updates)}")
    
    if not dry_run and updated_count > 5:
        print(f"   ✅ Updated {updated_count - 5} more matches")
    
    return updated_count

def reactivate_record(cur, records, dry_run=False):
    """Reactivate Record #2"""
    if not records:
        print("\n❌ No records found to reactivate")
        return 0
    
    active_records = [r for r in records if r['is_active']]
    inactive_records = [r for r in records if not r['is_active']]
    
    if not inactive_records:
        print("\n✅ Record #2 is already active")
        return 0
    
    print(f"\n{'🔍 DRY RUN: Would reactivate' if dry_run else '🔄 Reactivating'} {len(inactive_records)} record(s)...")
    print("-" * 80)
    
    updated_count = 0
    for record in inactive_records:
        if dry_run:
            print(f"   Would reactivate record {record['id']}: {record['first_name']} {record['last_name']} - {record['team_name']}")
        else:
            update_query = """
                UPDATE players
                SET is_active = true,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, first_name, last_name, is_active
            """
            
            cur.execute(update_query, [record['id']])
            result = cur.fetchone()
            
            if result:
                updated_count += 1
                print(f"   ✅ Reactivated record {result['id']}: {result['first_name']} {result['last_name']} - {record['team_name']}")
    
    return updated_count

def deactivate_record(cur, records, dry_run=False):
    """Deactivate Record #1"""
    if not records:
        print("\n❌ No records found to deactivate")
        return 0
    
    active_records = [r for r in records if r['is_active']]
    
    if not active_records:
        print("\n✅ Record #1 is already deactivated")
        return 0
    
    print(f"\n{'🔍 DRY RUN: Would deactivate' if dry_run else '🔄 Deactivating'} {len(active_records)} record(s)...")
    print("-" * 80)
    
    updated_count = 0
    for record in active_records:
        if dry_run:
            print(f"   Would deactivate record {record['id']}: {record['first_name']} {record['last_name']} - {record['team_name']}")
        else:
            update_query = """
                UPDATE players
                SET is_active = false,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, first_name, last_name, is_active
            """
            
            cur.execute(update_query, [record['id']])
            result = cur.fetchone()
            
            if result:
                updated_count += 1
                print(f"   ✅ Deactivated record {result['id']}: {result['first_name']} {result['last_name']} - {record['team_name']}")
    
    return updated_count

def main():
    parser = argparse.ArgumentParser(description="Reverse Aaron Gosser fix")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--live", action="store_true", help="Required flag for production database")
    parser.add_argument("--yes", action="store_true", help="Auto-confirm without prompting (use with caution)")
    
    args = parser.parse_args()
    
    # Get database mode
    database_mode = os.getenv("DB_MODE", "local").lower()
    
    if database_mode == "production" and not args.live:
        print("❌ ERROR: Production database requires --live flag for safety")
        print("   Usage: DB_MODE=production python3 scripts/reverse_aaron_gosser_fix.py --live")
        sys.exit(1)
    
    print("=" * 80)
    print("REVERSE AARON GOSSER FIX")
    print("=" * 80)
    print()
    print(f"Database: {database_mode.upper()}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    print("This will:")
    print("  1. Move user associations from Record #1 to Record #2")
    print("  2. Reactivate Record #2 (current ID on source website)")
    print("  3. Deactivate Record #1 (old/deprecated ID)")
    print("  4. Reverse match ID reassignments")
    print()
    print("Record #1 (DEACTIVATE):")
    print(f"  {RECORD_TO_DEACTIVATE['description']}")
    print(f"  ID: {RECORD_TO_DEACTIVATE['tenniscores_player_id']}")
    print()
    print("Record #2 (REACTIVATE):")
    print(f"  {RECORD_TO_REACTIVATE['description']}")
    print(f"  ID: {RECORD_TO_REACTIVATE['tenniscores_player_id']}")
    print()
    
    # Connect to database
    conn = connect_database(database_mode)
    cur = conn.cursor()
    
    try:
        # Verify current state
        records1, records2, associations = verify_current_state(cur)
        
        if not records1:
            print("\n❌ Record #1 not found - cannot proceed")
            sys.exit(1)
        
        if not records2:
            print("\n❌ Record #2 not found - cannot proceed")
            sys.exit(1)
        
        # Final confirmation for production
        if database_mode == "production" and not args.dry_run and not args.yes:
            print("\n" + "=" * 80)
            print("⚠️  PRODUCTION DATABASE - FINAL CONFIRMATION")
            print("=" * 80)
            print()
            print("This will:")
            print(f"  • Move {len(associations)} user association(s) from Record #1 to Record #2")
            print(f"  • Reactivate {len([r for r in records2 if not r['is_active']])} Record #2 record(s)")
            print(f"  • Deactivate {len([r for r in records1 if r['is_active']])} Record #1 record(s)")
            print(f"  • Reverse match ID reassignments")
            print()
            print("Type 'yes' to confirm: ", end='')
            confirmation = input().strip().lower()
            
            if confirmation != 'yes':
                print("❌ Cancelled - no changes made")
                return
        elif database_mode == "production" and not args.dry_run and args.yes:
            print("\n⚠️  PRODUCTION DATABASE - AUTO-CONFIRMED (--yes flag used)")
        
        # Step 1: Move user associations
        moved_associations = move_user_associations(cur, associations, dry_run=args.dry_run)
        
        # Step 2: Reverse match reassignments
        reversed_matches = reverse_match_reassignments(cur, dry_run=args.dry_run)
        
        # Step 3: Reactivate Record #2
        reactivated_count = reactivate_record(cur, records2, dry_run=args.dry_run)
        
        # Step 4: Deactivate Record #1
        deactivated_count = deactivate_record(cur, records1, dry_run=args.dry_run)
        
        # Commit or rollback
        if not args.dry_run:
            if moved_associations > 0 or reversed_matches > 0 or reactivated_count > 0 or deactivated_count > 0:
                conn.commit()
                print("\n" + "=" * 80)
                print("✅ SUCCESS - All changes committed")
                print("=" * 80)
                print(f"   • Moved {moved_associations} user association(s)")
                print(f"   • Reversed {reversed_matches} match reassignment(s)")
                print(f"   • Reactivated {reactivated_count} Record #2 record(s)")
                print(f"   • Deactivated {deactivated_count} Record #1 record(s)")
            else:
                conn.rollback()
                print("\n✅ No changes needed - all records already in correct state")
        else:
            print("\n" + "=" * 80)
            print("✅ DRY RUN COMPLETE")
            print("=" * 80)
            print("No actual changes were made")
    
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




