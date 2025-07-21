#!/usr/bin/env python3
"""
Team ID Orphans Fix Script
==========================

This script comprehensively fixes orphaned team_id references across
the Rally database, restoring functionality for:
1. Captain notifications 
2. Practice times team references
3. Team polls

The script uses intelligent matching logic to map orphaned team_ids
to the correct current teams based on content analysis and user context.

Usage: python scripts/fix_team_id_orphans.py [--dry-run]
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from database_config import get_db
from datetime import datetime
import argparse

def find_correct_team_for_poll(cursor, created_by, question, old_team_id):
    """
    Find the correct team_id for a poll based on creator and content.
    Uses intelligent matching based on series mentions and user associations.
    """
    
    try:
        # Strategy 1: Content-based matching for series references
        question_lower = question.lower()
        
        # Check for NSTF Series 2B references (must be exact to avoid confusion with Series 22)
        if "2b" in question_lower or "series 2b" in question_lower:
            cursor.execute("""
                SELECT DISTINCT t.id, t.team_name, t.team_alias, l.league_id
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                JOIN players p ON t.id = p.team_id
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s 
                AND l.league_id = 'NSTF' 
                AND (t.team_alias LIKE %s OR t.team_name LIKE %s)
                AND p.is_active = TRUE
                LIMIT 1
            """, (created_by, '%2B%', '%2B%'))
            
            result = cursor.fetchone()
            if result:
                team_id, team_name, team_alias, league_id = result
                print(f"   🎯 Series 2B match: {team_name} ({team_alias}) | {league_id}")
                return team_id
        
        # Check for APTA Series 22 references (must be exact to avoid confusion with Series 2B)
        if ("22" in question_lower or "series 22" in question_lower) and "2b" not in question_lower:
            cursor.execute("""
                SELECT DISTINCT t.id, t.team_name, t.team_alias, l.league_id
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                JOIN players p ON t.id = p.team_id
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s 
                AND l.league_id = 'APTA_CHICAGO' 
                AND (t.team_alias LIKE %s OR t.team_name LIKE %s)
                AND p.is_active = TRUE
                LIMIT 1
            """, (created_by, '%22%', '%22%'))
            
            result = cursor.fetchone()
            if result:
                team_id, team_name, team_alias, league_id = result
                print(f"   🎯 Series 22 match: {team_name} ({team_alias}) | {league_id}")
                return team_id
        
        # Strategy 2: Find creator's primary team (APTA_CHICAGO preferred)
        cursor.execute("""
            SELECT DISTINCT t.id, t.team_name, t.team_alias, l.league_id,
                CASE WHEN l.league_id = 'APTA_CHICAGO' THEN 1 ELSE 2 END as league_priority
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s AND p.is_active = TRUE AND p.team_id IS NOT NULL
            ORDER BY league_priority, t.id
            LIMIT 1
        """, (created_by,))
        
        result = cursor.fetchone()
        if result:
            team_id, team_name, team_alias, league_id, league_priority = result
            print(f"   🎯 Primary team match: {team_name} ({team_alias}) | {league_id}")
            return team_id
        
        print(f"   ❌ No matching team found for user {created_by}")
        return None
        
    except Exception as e:
        print(f"   ❌ Error finding team for user {created_by}: {str(e)}")
        return None

def find_correct_team_for_captain_message(cursor, captain_user_id, message, old_team_id):
    """
    Find the correct team_id for a captain message based on captain and content.
    Uses similar logic to poll matching but optimized for captain messages.
    """
    
    try:
        # Strategy 1: Content-based matching for series references
        message_lower = message.lower()
        
        # Check for NSTF Series 2B references
        if "2b" in message_lower or "series 2b" in message_lower:
            cursor.execute("""
                SELECT DISTINCT t.id, t.team_name, t.team_alias, l.league_id
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                JOIN players p ON t.id = p.team_id
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s 
                AND l.league_id = 'NSTF' 
                AND (t.team_alias LIKE %s OR t.team_name LIKE %s)
                AND p.is_active = TRUE
                LIMIT 1
            """, (captain_user_id, '%2B%', '%2B%'))
            
            result = cursor.fetchone()
            if result:
                team_id, team_name, team_alias, league_id = result
                print(f"   🎯 Series 2B captain match: {team_name} ({team_alias}) | {league_id}")
                return team_id
        
        # Check for APTA Series 22 references
        if ("22" in message_lower or "series 22" in message_lower) and "2b" not in message_lower:
            cursor.execute("""
                SELECT DISTINCT t.id, t.team_name, t.team_alias, l.league_id
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                JOIN players p ON t.id = p.team_id
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s 
                AND l.league_id = 'APTA_CHICAGO' 
                AND (t.team_alias LIKE %s OR t.team_name LIKE %s)
                AND p.is_active = TRUE
                LIMIT 1
            """, (captain_user_id, '%22%', '%22%'))
            
            result = cursor.fetchone()
            if result:
                team_id, team_name, team_alias, league_id = result
                print(f"   🎯 Series 22 captain match: {team_name} ({team_alias}) | {league_id}")
                return team_id
        
        # Strategy 2: Find captain's primary team (APTA_CHICAGO preferred)
        cursor.execute("""
            SELECT DISTINCT t.id, t.team_name, t.team_alias, l.league_id,
                CASE WHEN l.league_id = 'APTA_CHICAGO' THEN 1 ELSE 2 END as league_priority
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            JOIN players p ON t.id = p.team_id
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s AND p.is_active = TRUE AND p.team_id IS NOT NULL
            ORDER BY league_priority, t.id
            LIMIT 1
        """, (captain_user_id,))
        
        result = cursor.fetchone()
        if result:
            team_id, team_name, team_alias, league_id, league_priority = result
            print(f"   🎯 Primary captain team match: {team_name} ({team_alias}) | {league_id}")
            return team_id
        
        print(f"   ❌ No matching team found for captain {captain_user_id}")
        return None
        
    except Exception as e:
        print(f"   ❌ Error finding team for captain {captain_user_id}: {str(e)}")
        return None

def fix_orphaned_polls(cursor, dry_run=False):
    """Fix orphaned team_id references in polls table"""
    print("📊 FIXING ORPHANED POLLS")
    print("-" * 40)
    
    # Find orphaned polls
    cursor.execute("""
        SELECT p.id, p.team_id, p.question, p.created_at, p.created_by, u.first_name, u.last_name
        FROM polls p
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN users u ON p.created_by = u.id
        WHERE p.team_id IS NOT NULL AND t.id IS NULL
        ORDER BY p.created_at DESC
    """)
    
    orphaned_polls = cursor.fetchall()
    
    if not orphaned_polls:
        print("   ✅ No orphaned polls found")
        return 0
    
    print(f"   Found {len(orphaned_polls)} orphaned polls to fix")
    
    fixed_count = 0
    
    for poll in orphaned_polls:
        poll_id, old_team_id, question, created_at, created_by, first_name, last_name = poll
        
        print(f"\n   🔍 Poll {poll_id}: \"{question[:50]}...\"")
        print(f"       Creator: {first_name} {last_name} | Old team_id: {old_team_id}")
        
        # Find the correct team
        new_team_id = find_correct_team_for_poll(cursor, created_by, question, old_team_id)
        
        if new_team_id:
            if not dry_run:
                cursor.execute("""
                    UPDATE polls 
                    SET team_id = %s 
                    WHERE id = %s
                """, [new_team_id, poll_id])
            
            print(f"       ✅ {'[DRY RUN] Would fix' if dry_run else 'Fixed'}: {old_team_id} → {new_team_id}")
            fixed_count += 1
        else:
            if not dry_run:
                cursor.execute("""
                    UPDATE polls 
                    SET team_id = NULL 
                    WHERE id = %s
                """, [poll_id])
            
            print(f"       ⚠️  {'[DRY RUN] Would set' if dry_run else 'Set'} team_id to NULL (no matching team)")
            fixed_count += 1
    
    print(f"\n   📊 Polls fixed: {fixed_count}")
    return fixed_count

def fix_orphaned_captain_messages(cursor, dry_run=False):
    """Fix orphaned team_id references in captain_messages table"""
    print("\n💬 FIXING ORPHANED CAPTAIN MESSAGES")
    print("-" * 40)
    
    # Find orphaned captain messages
    cursor.execute("""
        SELECT cm.id, cm.team_id, cm.message, cm.created_at, cm.captain_user_id, u.first_name, u.last_name
        FROM captain_messages cm
        LEFT JOIN teams t ON cm.team_id = t.id
        LEFT JOIN users u ON cm.captain_user_id = u.id
        WHERE cm.team_id IS NOT NULL AND t.id IS NULL
        ORDER BY cm.created_at DESC
    """)
    
    orphaned_messages = cursor.fetchall()
    
    if not orphaned_messages:
        print("   ✅ No orphaned captain messages found")
        return 0
    
    print(f"   Found {len(orphaned_messages)} orphaned captain messages to fix")
    
    fixed_count = 0
    
    for message in orphaned_messages:
        msg_id, old_team_id, msg_text, created_at, captain_user_id, first_name, last_name = message
        
        print(f"\n   🔍 Message {msg_id}: \"{msg_text[:50]}...\"")
        print(f"       Captain: {first_name} {last_name} | Old team_id: {old_team_id}")
        
        # Find the correct team
        new_team_id = find_correct_team_for_captain_message(cursor, captain_user_id, msg_text, old_team_id)
        
        if new_team_id:
            if not dry_run:
                cursor.execute("""
                    UPDATE captain_messages 
                    SET team_id = %s 
                    WHERE id = %s
                """, [new_team_id, msg_id])
            
            print(f"       ✅ {'[DRY RUN] Would fix' if dry_run else 'Fixed'}: {old_team_id} → {new_team_id}")
            fixed_count += 1
        else:
            print(f"       ❌ No matching team found - captain message will be deleted")
            if not dry_run:
                cursor.execute("""
                    DELETE FROM captain_messages 
                    WHERE id = %s
                """, [msg_id])
            
            print(f"       🗑️  {'[DRY RUN] Would delete' if dry_run else 'Deleted'} orphaned message")
            fixed_count += 1
    
    print(f"\n   📊 Captain messages fixed: {fixed_count}")
    return fixed_count

def fix_orphaned_practice_times(cursor, dry_run=False):
    """Fix orphaned team_id references in schedule table for practice times"""
    print("\n⏰ FIXING ORPHANED PRACTICE TIMES")
    print("-" * 40)
    
    # Find orphaned practice times
    cursor.execute("""
        SELECT s.id, s.home_team_id, s.home_team, s.match_date, s.match_time
        FROM schedule s
        LEFT JOIN teams t ON s.home_team_id = t.id
        WHERE (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
        AND s.home_team_id IS NOT NULL AND t.id IS NULL
        ORDER BY s.match_date DESC
    """)
    
    orphaned_practice = cursor.fetchall()
    
    if not orphaned_practice:
        print("   ✅ No orphaned practice times found")
        return 0
    
    print(f"   Found {len(orphaned_practice)} orphaned practice times to fix")
    
    fixed_count = 0
    
    for practice in orphaned_practice:
        sched_id, old_team_id, home_team, match_date, match_time = practice
        
        print(f"\n   🔍 Schedule {sched_id}: \"{home_team}\"")
        print(f"       Date: {match_date} {match_time} | Old team_id: {old_team_id}")
        
        # Try to find matching team by name
        cursor.execute("""
            SELECT t.id, t.team_name, t.team_alias
            FROM teams t
            WHERE t.team_name = %s OR t.team_alias = %s
            LIMIT 1
        """, [home_team, home_team])
        
        team_match = cursor.fetchone()
        
        if team_match:
            new_team_id, team_name, team_alias = team_match
            if not dry_run:
                cursor.execute("""
                    UPDATE schedule 
                    SET home_team_id = %s 
                    WHERE id = %s
                """, [new_team_id, sched_id])
            
            print(f"       ✅ {'[DRY RUN] Would fix' if dry_run else 'Fixed'}: {old_team_id} → {new_team_id}")
            print(f"       🎯 Matched to: {team_name} ({team_alias})")
            fixed_count += 1
        else:
            if not dry_run:
                cursor.execute("""
                    UPDATE schedule 
                    SET home_team_id = NULL 
                    WHERE id = %s
                """, [sched_id])
            
            print(f"       ⚠️  {'[DRY RUN] Would set' if dry_run else 'Set'} team_id to NULL (no matching team)")
            fixed_count += 1
    
    print(f"\n   📊 Practice times fixed: {fixed_count}")
    return fixed_count

def main():
    parser = argparse.ArgumentParser(description='Fix orphaned team_id references')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without making changes')
    args = parser.parse_args()
    
    print("🔧 TEAM ID ORPHANS FIX SCRIPT")
    print("=" * 60)
    print(f"📅 Fix run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made")
    print()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            total_fixed = 0
            
            # Fix orphaned polls
            total_fixed += fix_orphaned_polls(cursor, args.dry_run)
            
            # Fix orphaned captain messages
            total_fixed += fix_orphaned_captain_messages(cursor, args.dry_run)
            
            # Fix orphaned practice times
            total_fixed += fix_orphaned_practice_times(cursor, args.dry_run)
            
            if not args.dry_run and total_fixed > 0:
                conn.commit()
                print(f"\n✅ Successfully committed all fixes")
            
            print()
            print("📊 FIX SUMMARY")
            print("-" * 40)
            print(f"Total records fixed: {total_fixed}")
            
            if args.dry_run:
                print("🧪 This was a dry run - no changes were made")
                print("   Run without --dry-run to apply fixes")
            else:
                print("✅ All fixes have been applied to the database")
                print("   Run diagnose_team_id_orphans.py to verify")
            
            print()
            print("🔧 NEXT STEPS:")
            print("   1. Verify fix: python scripts/diagnose_team_id_orphans.py")
            print("   2. Test user functionality:")
            print("      • Check polls page: /mobile/polls")
            print("      • Check notifications: /mobile")
            print("      • Check practice times display")
            print("   3. Monitor ETL imports to prevent future orphaning")
            
        except Exception as e:
            print(f"\n❌ Error during fix: {str(e)}")
            if not args.dry_run:
                conn.rollback()
                print("🔄 Database changes rolled back")
            return 1
        
        print()
        print("=" * 60)
        print("🏁 FIX COMPLETE")
        return 0

if __name__ == "__main__":
    exit(main()) 