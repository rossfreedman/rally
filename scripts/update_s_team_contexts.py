#!/usr/bin/env python3
"""
Update user contexts that point to (S) teams to point to the user's correct active team.

This script:
1. Identifies users with contexts pointing to teams containing inactive (S) players
2. Finds each user's correct active team (from their active player record)
3. Updates user_contexts to point to the correct team
4. Validates the changes
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_utils import get_db_cursor
from datetime import datetime

def update_s_team_contexts(dry_run=True):
    print("=" * 80)
    print(f"UPDATE USER CONTEXTS - {'DRY RUN' if dry_run else 'LIVE RUN'}")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    with get_db_cursor(commit=(not dry_run)) as cursor:
        
        # Step 1: Identify affected users
        print("STEP 1: IDENTIFYING AFFECTED USERS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT DISTINCT
                u.id as user_id,
                u.email,
                uc.team_id as current_context_team_id,
                t.team_name as current_team_name,
                s.name as current_series_name
            FROM user_contexts uc
            JOIN users u ON uc.user_id = u.id
            JOIN teams t ON uc.team_id = t.id
            JOIN series s ON t.series_id = s.id
            JOIN players p_s ON t.id = p_s.team_id
            WHERE (p_s.first_name LIKE %s OR p_s.last_name LIKE %s)
            AND p_s.is_active = false
            ORDER BY u.email
        """, ('%(S)', '%(S)'))
        
        affected_users = cursor.fetchall()
        
        print(f"Found {len(affected_users)} users with contexts pointing to (S) teams")
        print()
        
        # Step 2: Find correct team for each user
        print("STEP 2: FINDING CORRECT TEAMS FOR EACH USER")
        print("-" * 80)
        
        updates_needed = []
        no_change_needed = []
        errors = []
        
        for user in affected_users:
            # Find user's active regular player record
            cursor.execute("""
                SELECT p.team_id, t.team_name, s.name as series_name
                FROM players p
                JOIN teams t ON p.team_id = t.id
                JOIN series s ON t.series_id = s.id
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s
                AND p.is_active = true
                AND p.first_name NOT LIKE %s
                AND p.last_name NOT LIKE %s
                ORDER BY upa.is_primary DESC, p.id DESC
                LIMIT 1
            """, (user['user_id'], '%(S)', '%(S)'))
            
            correct_team = cursor.fetchone()
            
            if correct_team:
                if correct_team['team_id'] == user['current_context_team_id']:
                    # Already pointing to correct team (same team, just has inactive S players)
                    no_change_needed.append({
                        'user_id': user['user_id'],
                        'email': user['email'],
                        'team': correct_team['team_name']
                    })
                else:
                    # Needs update
                    updates_needed.append({
                        'user_id': user['user_id'],
                        'email': user['email'],
                        'current_team_id': user['current_context_team_id'],
                        'current_team_name': user['current_team_name'],
                        'correct_team_id': correct_team['team_id'],
                        'correct_team_name': correct_team['team_name'],
                        'correct_series': correct_team['series_name']
                    })
            else:
                errors.append({
                    'user_id': user['user_id'],
                    'email': user['email'],
                    'error': 'No active regular player record found'
                })
        
        print(f"Analysis complete:")
        print(f"  ✅ No change needed: {len(no_change_needed)} (contexts already correct)")
        print(f"  🔧 Updates needed: {len(updates_needed)}")
        print(f"  ❌ Errors: {len(errors)}")
        print()
        
        # Show no-change cases
        if no_change_needed:
            print("USERS WITH CORRECT CONTEXTS (no change needed):")
            print("-" * 80)
            for user in no_change_needed[:5]:
                print(f"  ✅ {user['email']} → {user['team']} (already correct)")
            if len(no_change_needed) > 5:
                print(f"  ... and {len(no_change_needed) - 5} more")
            print()
        
        # Show updates needed
        if updates_needed:
            print("USERS NEEDING CONTEXT UPDATES:")
            print("-" * 80)
            for update in updates_needed:
                print(f"  {update['email']}:")
                print(f"    Current: {update['current_team_name']} (ID: {update['current_team_id']})")
                print(f"    Correct: {update['correct_team_name']} (ID: {update['correct_team_id']}) - {update['correct_series']}")
                print()
        
        # Show errors
        if errors:
            print("ERRORS (CANNOT UPDATE):")
            print("-" * 80)
            for error in errors:
                print(f"  ❌ {error['email']}: {error['error']}")
            print()
        
        # Step 3: Execute updates
        if updates_needed:
            print("STEP 3: EXECUTING UPDATES")
            print("-" * 80)
            
            if dry_run:
                print("DRY RUN - No changes will be made")
                print(f"Would update {len(updates_needed)} user contexts")
            else:
                print("LIVE RUN - Updating user contexts...")
                
                success_count = 0
                fail_count = 0
                
                for update in updates_needed:
                    try:
                        cursor.execute("""
                            UPDATE user_contexts
                            SET team_id = %s
                            WHERE user_id = %s
                        """, (update['correct_team_id'], update['user_id']))
                        
                        success_count += 1
                        print(f"  ✅ Updated {update['email']}")
                    except Exception as e:
                        fail_count += 1
                        print(f"  ❌ Failed {update['email']}: {e}")
                
                print()
                print(f"Results: {success_count} succeeded, {fail_count} failed")
        else:
            print("STEP 3: NO UPDATES NEEDED")
            print("-" * 80)
            print("All user contexts are already pointing to correct teams!")
        
        print()
        
        # Step 4: Validation
        print("STEP 4: VALIDATION")
        print("-" * 80)
        
        if dry_run:
            print("Skipping validation (dry run)")
        else:
            # Re-run the check to see how many are left
            cursor.execute("""
                SELECT COUNT(DISTINCT u.id) as count
                FROM user_contexts uc
                JOIN users u ON uc.user_id = u.id
                JOIN teams t ON uc.team_id = t.id
                JOIN players p_s ON t.id = p_s.team_id
                WHERE (p_s.first_name LIKE %s OR p_s.last_name LIKE %s)
                AND p_s.is_active = false
            """, ('%(S)', '%(S)'))
            
            remaining = cursor.fetchone()['count']
            
            if remaining == 0:
                print("✅ SUCCESS: No users have contexts pointing to (S) teams!")
            elif remaining < len(affected_users):
                print(f"⚠️  PARTIAL: Reduced from {len(affected_users)} to {remaining}")
            else:
                print(f"❌ FAILED: Still {remaining} users with (S) team contexts")
        
        print()
        print("=" * 80)
        
        return {
            'total_affected': len(affected_users),
            'no_change_needed': len(no_change_needed),
            'updates_needed': len(updates_needed),
            'errors': len(errors)
        }

if __name__ == "__main__":
    import sys
    
    dry_run = "--live" not in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("Add --live to execute the updates")
        print()
    else:
        print("⚠️  LIVE RUN MODE - Changes will be applied!")
        print()
    
    result = update_s_team_contexts(dry_run=dry_run)
    
    print()
    print("SUMMARY:")
    print(f"  Total affected users: {result['total_affected']}")
    print(f"  No change needed: {result['no_change_needed']}")
    print(f"  Updates needed: {result['updates_needed']}")
    print(f"  Errors: {result['errors']}")
    
    if result['updates_needed'] == 0 and result['errors'] == 0:
        print()
        print("✅ All user contexts are already correct!")
        sys.exit(0)
    elif result['errors'] > 0:
        print()
        print("⚠️  Some users have errors - review above")
        sys.exit(1)
    else:
        if dry_run:
            print()
            print("✅ DRY RUN COMPLETE - Ready to execute with --live")
        else:
            print()
            print("✅ UPDATES COMPLETE")
        sys.exit(0)



