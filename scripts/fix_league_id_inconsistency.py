#!/usr/bin/env python3
"""
Fix League ID Inconsistency
===========================

This script fixes the inconsistency between users.league_id and users.league_context
that's causing the league selection modal to appear incorrectly.

Issue: All users have:
- league_context: pointing to valid leagues (4891, 4893, etc.) ✅
- league_id: pointing to non-existent leagues (4775, 4635, etc.) ❌

The session validation logic checks league_id, but it has wrong values.

Solution: Update users.league_id to match users.league_context

Usage:
    python scripts/fix_league_id_inconsistency.py --execute
"""

import argparse
import os
import sys
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db

def analyze_inconsistency(cursor):
    """Analyze the current inconsistency between league_id and league_context"""
    print("🔍 Analyzing league_id vs league_context inconsistency...")
    
    # Find users with inconsistent data
    cursor.execute("""
        SELECT 
            u.id,
            u.email,
            u.first_name,
            u.last_name,
            u.league_id,
            u.league_context,
            lc.league_name as context_league_name,
            li.league_name as id_league_name
        FROM users u
        LEFT JOIN leagues lc ON u.league_context = lc.id
        LEFT JOIN leagues li ON u.league_id = li.id
        WHERE u.league_context != u.league_id
           OR (u.league_context IS NOT NULL AND u.league_id IS NULL)
           OR (u.league_id IS NOT NULL AND li.id IS NULL)
        ORDER BY u.id
    """)
    
    inconsistent_users = cursor.fetchall()
    
    print(f"Found {len(inconsistent_users)} users with inconsistent league data:")
    print()
    
    # Categorize the issues
    wrong_league_id = []
    null_league_id = []
    orphaned_league_id = []
    
    for user in inconsistent_users:
        user_id, email, first_name, last_name, league_id, league_context, context_name, id_name = user
        
        if league_context and not league_id:
            null_league_id.append(user)
        elif league_id and not id_name:  # orphaned league_id
            orphaned_league_id.append(user)
        elif league_context != league_id:
            wrong_league_id.append(user)
        
        print(f"  {first_name} {last_name} (ID: {user_id}):")
        print(f"    league_context: {league_context} ({context_name})")
        print(f"    league_id: {league_id} ({id_name})")
        print()
    
    print("Summary:")
    print(f"  - Users with NULL league_id: {len(null_league_id)}")
    print(f"  - Users with orphaned league_id: {len(orphaned_league_id)}")
    print(f"  - Users with wrong league_id: {len(wrong_league_id)}")
    print(f"  - Total users needing fix: {len(inconsistent_users)}")
    
    return inconsistent_users

def fix_inconsistency(cursor, dry_run=True):
    """Fix the league_id inconsistency by updating league_id to match league_context"""
    
    action = "DRY RUN" if dry_run else "EXECUTING"
    print(f"\n🔧 {action}: Fixing league_id inconsistency...")
    
    if not dry_run:
        # Update league_id to match league_context for all users
        cursor.execute("""
            UPDATE users 
            SET league_id = league_context
            WHERE league_context IS NOT NULL
            AND (league_id != league_context OR league_id IS NULL)
        """)
        
        fixed_count = cursor.rowcount
        print(f"✅ Updated {fixed_count} users - set league_id = league_context")
        
        # Also clear league_id for users with NULL league_context
        cursor.execute("""
            UPDATE users 
            SET league_id = NULL
            WHERE league_context IS NULL AND league_id IS NOT NULL
        """)
        
        cleared_count = cursor.rowcount
        if cleared_count > 0:
            print(f"✅ Cleared league_id for {cleared_count} users with NULL league_context")
        
        return fixed_count + cleared_count
    else:
        # Count what would be fixed
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE league_context IS NOT NULL
            AND (league_id != league_context OR league_id IS NULL)
        """)
        would_fix = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE league_context IS NULL AND league_id IS NOT NULL
        """)
        would_clear = cursor.fetchone()[0]
        
        print(f"📝 Would update {would_fix} users - set league_id = league_context")
        if would_clear > 0:
            print(f"📝 Would clear league_id for {would_clear} users with NULL league_context")
        
        return would_fix + would_clear

def validate_fix(cursor):
    """Validate that the fix was successful"""
    print("\n✅ Validating fix...")
    
    # Check for remaining inconsistencies
    cursor.execute("""
        SELECT COUNT(*) FROM users u
        LEFT JOIN leagues l ON u.league_id = l.id
        WHERE u.league_id IS NOT NULL AND l.id IS NULL
    """)
    orphaned_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE league_context != league_id
    """)
    inconsistent_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE league_context IS NOT NULL AND league_id IS NOT NULL
    """)
    consistent_count = cursor.fetchone()[0]
    
    print(f"  - Users with orphaned league_id: {orphaned_count}")
    print(f"  - Users with inconsistent league_id/context: {inconsistent_count}")
    print(f"  - Users with consistent league_id/context: {consistent_count}")
    
    # Check league distribution
    cursor.execute("""
        SELECT l.league_name, COUNT(*) as user_count
        FROM users u
        JOIN leagues l ON u.league_id = l.id
        WHERE u.league_id IS NOT NULL
        GROUP BY l.league_name
        ORDER BY user_count DESC
    """)
    distribution = cursor.fetchall()
    
    print("\n  League distribution after fix:")
    for league in distribution:
        print(f"    - {league[0]}: {league[1]} users")
    
    success = orphaned_count == 0 and inconsistent_count == 0
    
    if success:
        print("\n🎉 SUCCESS: All league_id inconsistencies resolved!")
        print("   Users should no longer see the league selection modal.")
    else:
        print(f"\n⚠️  WARNING: {orphaned_count + inconsistent_count} inconsistencies remain")
    
    return success

def main():
    parser = argparse.ArgumentParser(description='Fix league_id inconsistency in users table')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually execute the fix (default is dry run)')
    
    args = parser.parse_args()
    
    print("🔧 League ID Inconsistency Fix")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print("=" * 60)
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Step 1: Analyze the problem
            inconsistent_users = analyze_inconsistency(cursor)
            
            if len(inconsistent_users) == 0:
                print("\n🎉 No inconsistencies found - system is already healthy!")
                return
            
            # Step 2: Fix the inconsistency
            fixed_count = fix_inconsistency(cursor, dry_run=not args.execute)
            
            if args.execute:
                conn.commit()
                print(f"\n✅ Successfully fixed {fixed_count} users")
                
                # Step 3: Validate the fix
                success = validate_fix(cursor)
                
                if not success:
                    print("\n⚠️  Some issues remain - check the validation output above.")
            else:
                print(f"\n📝 Dry run complete. Would fix {fixed_count} users")
                print("Run with --execute to actually apply the fixes")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 