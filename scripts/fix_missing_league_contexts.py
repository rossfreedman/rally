#!/usr/bin/env python3
"""
Fix Missing League Contexts After ETL
=====================================

This script fixes users who lost their league context after ETL by:
1. Linking them to their existing player records via user_player_associations
2. Setting appropriate league_context based on their player league
3. Ensuring they don't see the league selection modal

Target Users:
- Stephen Statkus (ID: 51) -> Player nndz-WkM2L3c3djZnQT09 in APTA Chicago (4887)
- Lisa Wagner (ID: 76) -> Player nndz-WkM2eHhybi9qUT09 in CNSWPL (4889)

Usage:
    python scripts/fix_missing_league_contexts.py --execute
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

def get_missing_league_context_fixes():
    """Define the fixes needed for users missing league context"""
    return [
        {
            'user_id': 51,
            'user_name': 'Stephen Statkus',
            'email': 'sstatkus@gmail.com',
            'player_id': 'nndz-WkM2L3c3djZnQT09',
            'expected_league_id': 4887,  # APTA Chicago
            'expected_league_name': 'APTA Chicago'
        },
        {
            'user_id': 76,
            'user_name': 'Lisa Wagner', 
            'email': 'lwagner@gmail.com',
            'player_id': 'nndz-WkM2eHhybi9qUT09',
            'expected_league_id': 4889,  # CNSWPL
            'expected_league_name': 'Chicago North Shore Women\'s Platform Tennis League'
        }
    ]

def check_current_state(cursor):
    """Check the current state of users and their associations"""
    print("🔍 Checking current state...")
    
    fixes = get_missing_league_context_fixes()
    
    for fix in fixes:
        user_id = fix['user_id']
        
        # Check user current state
        cursor.execute("""
            SELECT id, email, first_name, last_name, league_context, tenniscores_player_id
            FROM users WHERE id = %s
        """, [user_id])
        user = cursor.fetchone()
        
        if user:
            print(f"\n👤 {user[2]} {user[3]} (ID: {user[0]})")
            print(f"   Email: {user[1]}")
            print(f"   League context: {user[4]}")
            print(f"   Player ID: {user[5]}")
        
        # Check if player exists
        cursor.execute("""
            SELECT tenniscores_player_id, first_name, last_name, league_id, team_id
            FROM players WHERE tenniscores_player_id = %s
        """, [fix['player_id']])
        player = cursor.fetchone()
        
        if player:
            print(f"   🎾 Found player: {player[1]} {player[2]} in League {player[3]}, Team {player[4]}")
        else:
            print(f"   ❌ Player {fix['player_id']} not found")
        
        # Check existing associations
        cursor.execute("""
            SELECT tenniscores_player_id, created_at
            FROM user_player_associations WHERE user_id = %s
        """, [user_id])
        associations = cursor.fetchall()
        
        print(f"   🔗 Current associations: {len(associations)}")
        for assoc in associations:
            print(f"      - {assoc[0]} (created: {assoc[1]})")

def create_user_player_associations(cursor, fixes, dry_run=True):
    """Create missing user_player_associations"""
    print(f"\n{'🔍 DRY RUN:' if dry_run else '💾 EXECUTING:'} Creating user_player_associations...")
    
    created_count = 0
    
    for fix in fixes:
        user_id = fix['user_id']
        player_id = fix['player_id']
        
        # Check if association already exists
        cursor.execute("""
            SELECT COUNT(*) FROM user_player_associations 
            WHERE user_id = %s AND tenniscores_player_id = %s
        """, [user_id, player_id])
        
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            print(f"   ⏭️  Association already exists: User {user_id} -> {player_id}")
            continue
        
        if not dry_run:
            cursor.execute("""
                INSERT INTO user_player_associations (user_id, tenniscores_player_id, created_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
            """, [user_id, player_id])
            
            print(f"   ✅ Created association: {fix['user_name']} -> {player_id}")
        else:
            print(f"   📝 Would create association: {fix['user_name']} -> {player_id}")
        
        created_count += 1
    
    return created_count

def update_user_league_contexts(cursor, fixes, dry_run=True):
    """Update user league_context and tenniscores_player_id"""
    print(f"\n{'🔍 DRY RUN:' if dry_run else '💾 EXECUTING:'} Updating user league contexts...")
    
    updated_count = 0
    
    for fix in fixes:
        user_id = fix['user_id']
        league_id = fix['expected_league_id']
        player_id = fix['player_id']
        
        if not dry_run:
            cursor.execute("""
                UPDATE users 
                SET league_context = %s, tenniscores_player_id = %s
                WHERE id = %s
            """, [league_id, player_id, user_id])
            
            print(f"   ✅ Updated {fix['user_name']}: league_context = {league_id}, player_id = {player_id}")
        else:
            print(f"   📝 Would update {fix['user_name']}: league_context = {league_id}, player_id = {player_id}")
        
        updated_count += 1
    
    return updated_count

def validate_fixes(cursor, fixes):
    """Validate that the fixes were applied correctly"""
    print("\n✅ Validating fixes...")
    
    all_good = True
    
    for fix in fixes:
        user_id = fix['user_id']
        expected_league = fix['expected_league_id']
        expected_player = fix['player_id']
        
        # Check user state
        cursor.execute("""
            SELECT league_context, tenniscores_player_id
            FROM users WHERE id = %s
        """, [user_id])
        user_state = cursor.fetchone()
        
        if user_state:
            league_context, player_id = user_state
            
            if league_context == expected_league and player_id == expected_player:
                print(f"   ✅ {fix['user_name']}: League {league_context}, Player {player_id}")
            else:
                print(f"   ❌ {fix['user_name']}: Expected League {expected_league}/Player {expected_player}, got League {league_context}/Player {player_id}")
                all_good = False
        else:
            print(f"   ❌ {fix['user_name']}: User not found")
            all_good = False
        
        # Check association
        cursor.execute("""
            SELECT COUNT(*) FROM user_player_associations 
            WHERE user_id = %s AND tenniscores_player_id = %s
        """, [user_id, expected_player])
        
        assoc_exists = cursor.fetchone()[0] > 0
        
        if assoc_exists:
            print(f"   ✅ {fix['user_name']}: Association exists")
        else:
            print(f"   ❌ {fix['user_name']}: Association missing")
            all_good = False
    
    return all_good

def main():
    parser = argparse.ArgumentParser(description='Fix missing league contexts after ETL')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually execute the fixes (default is dry run)')
    
    args = parser.parse_args()
    
    print("🔧 League Context Fix Script")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print("=" * 60)
    
    fixes = get_missing_league_context_fixes()
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Step 1: Check current state
            check_current_state(cursor)
            
            # Step 2: Create user_player_associations
            assoc_count = create_user_player_associations(cursor, fixes, dry_run=not args.execute)
            
            # Step 3: Update league contexts
            update_count = update_user_league_contexts(cursor, fixes, dry_run=not args.execute)
            
            if args.execute:
                conn.commit()
                print(f"\n✅ Successfully processed {len(fixes)} users")
                print(f"   - Created {assoc_count} associations")
                print(f"   - Updated {update_count} league contexts")
                
                # Step 4: Validate
                if validate_fixes(cursor, fixes):
                    print("\n🎉 All fixes validated successfully!")
                    print("Users should no longer see the league selection modal.")
                else:
                    print("\n⚠️  Some fixes may not have applied correctly. Check the validation output above.")
            else:
                print(f"\n📝 Dry run complete. Would process {len(fixes)} users")
                print("Run with --execute to actually apply the fixes")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 