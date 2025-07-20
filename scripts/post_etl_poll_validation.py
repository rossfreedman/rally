#!/usr/bin/env python3
"""
Post-ETL poll validation and fixing script
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from database_config import get_db

def post_etl_poll_validation():
    """Comprehensive post-ETL poll validation and fixing"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        print("🔍 Post-ETL Poll Validation and Fixing")
        print("=" * 60)
        
        # Step 1: Check for orphaned polls
        print("Step 1: Checking for orphaned polls...")
        cursor.execute("""
            SELECT p.id, p.team_id, p.question, p.created_at, p.created_by
            FROM polls p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.team_id IS NOT NULL AND t.id IS NULL
            ORDER BY p.created_at DESC
        """)
        
        orphaned_polls = cursor.fetchall()
        
        if not orphaned_polls:
            print("✅ No orphaned polls found")
            return True
        
        print(f"❌ Found {len(orphaned_polls)} orphaned polls")
        
        # Step 2: Fix orphaned polls
        print("\nStep 2: Fixing orphaned polls...")
        fixed_count = 0
        
        for poll in orphaned_polls:
            poll_id, old_team_id, question, created_at, created_by = poll
            print(f"\n🔍 Processing poll {poll_id}: {question[:50]}...")
            print(f"   Old team_id: {old_team_id}")
            
            # Try to find the correct team
            new_team_id = find_correct_team_for_poll(cursor, created_by, question, old_team_id)
            
            if new_team_id:
                # Update the poll to reference the correct team
                cursor.execute("""
                    UPDATE polls 
                    SET team_id = %s 
                    WHERE id = %s
                """, [new_team_id, poll_id])
                
                print(f"   ✅ Fixed poll {poll_id}: {old_team_id} → {new_team_id}")
                fixed_count += 1
            else:
                # If no correct team found, set to NULL
                cursor.execute("""
                    UPDATE polls 
                    SET team_id = NULL 
                    WHERE id = %s
                """, [poll_id])
                
                print(f"   ⚠️  Set poll {poll_id} team_id to NULL (no matching team found)")
                fixed_count += 1
        
        conn.commit()
        print(f"\n✅ Fixed {fixed_count} orphaned poll references")
        
        # Step 3: Verify fix
        print("\nStep 3: Verifying fix...")
        cursor.execute("""
            SELECT COUNT(*)
            FROM polls p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.team_id IS NOT NULL AND t.id IS NULL
        """)
        
        remaining_orphaned = cursor.fetchone()[0]
        if remaining_orphaned == 0:
            print("✅ All orphaned polls have been fixed")
            return True
        else:
            print(f"❌ {remaining_orphaned} orphaned polls still remain")
            return False

def find_correct_team_for_poll(cursor, created_by, question, old_team_id):
    """Find the correct team_id for a poll based on creator and content"""
    
    print(f"   Looking for correct team for creator {created_by}...")
    
    # Strategy 1: Find creator's team based on question content (e.g., "Series 22")
    if "22" in question or "Series 22" in question:
        print(f"   Strategy 1: Looking for Series 22 team...")
        cursor.execute("""
            SELECT p.team_id, t.team_name, t.team_alias
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN teams t ON p.team_id = t.id
            WHERE upa.user_id = %s AND (t.team_name LIKE '%%22%%' OR t.team_alias LIKE '%%22%%')
            LIMIT 1
        """, [created_by])
        
        result = cursor.fetchone()
        if result:
            team_id, team_name, team_alias = result
            print(f"   ✅ Found Series 22 team: {team_id} ({team_name})")
            return team_id
        else:
            print(f"   ❌ No Series 22 team found for creator")
    
    # Strategy 2: Find creator's primary team (APTA_CHICAGO preferred)
    print(f"   Strategy 2: Looking for primary team...")
    cursor.execute("""
        SELECT p.team_id, t.team_name, t.team_alias, l.league_id
        FROM players p
        JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
        JOIN teams t ON p.team_id = t.id
        JOIN leagues l ON p.league_id = l.id
        WHERE upa.user_id = %s AND p.is_active = TRUE AND p.team_id IS NOT NULL
        ORDER BY 
            CASE WHEN l.league_id = 'APTA_CHICAGO' THEN 1 ELSE 2 END,
            p.id
        LIMIT 1
    """, [created_by])
    
    result = cursor.fetchone()
    if result:
        team_id, team_name, team_alias, league_id = result
        print(f"   ✅ Found primary team: {team_id} ({team_name}) - {league_id}")
        return team_id
    else:
        print(f"   ❌ No primary team found for creator")
    
    return None

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Post-ETL Poll Validation and Fixing')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check for orphaned polls, do not fix')
    parser.add_argument('--fix-only', action='store_true',
                       help='Only fix orphaned polls, skip validation')
    
    args = parser.parse_args()
    
    if args.check_only:
        # Only check for orphaned polls
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM polls p
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.team_id IS NOT NULL AND t.id IS NULL
            """)
            orphaned_count = cursor.fetchone()[0]
            print(f"Found {orphaned_count} orphaned polls")
            return 0 if orphaned_count == 0 else 1
    elif args.fix_only:
        # Only fix orphaned polls
        success = post_etl_poll_validation()
        return 0 if success else 1
    else:
        # Full validation and fixing
        success = post_etl_poll_validation()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 