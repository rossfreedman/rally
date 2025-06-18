#!/usr/bin/env python3
"""
Fix script for users who have league_name but NULL league_id
This resolves the analyze-me data display issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update

def fix_user_league_ids():
    """Fix users who have league_name but NULL league_id"""
    print("=== FIXING USER LEAGUE IDS ===")
    
    # Find users with league_name but NULL league_id
    problem_users_query = """
        SELECT id, email, first_name, last_name, league_name
        FROM users
        WHERE league_id IS NULL 
        AND league_name IS NOT NULL 
        AND league_name != ''
    """
    
    problem_users = execute_query(problem_users_query)
    
    if not problem_users:
        print("✅ No users found with NULL league_id but non-NULL league_name")
        return
    
    print(f"Found {len(problem_users)} users with NULL league_id but valid league_name:")
    
    fixed_count = 0
    for user in problem_users:
        print(f"\n👤 {user['first_name']} {user['last_name']} ({user['email']})")
        print(f"   League Name: '{user['league_name']}'")
        
        # Look up the league_id from the leagues table
        league_lookup = execute_query_one(
            "SELECT id, league_id FROM leagues WHERE league_name = %s",
            [user['league_name']]
        )
        
        if league_lookup:
            league_db_id = league_lookup['id']
            league_identifier = league_lookup['league_id']
            
            print(f"   ✅ Found matching league: {league_identifier} (DB ID: {league_db_id})")
            
            # Update the user's league_id
            update_query = """
                UPDATE users 
                SET league_id = %s
                WHERE id = %s
            """
            
            try:
                execute_update(update_query, [league_db_id, user['id']])
                print(f"   ✅ Updated user's league_id to {league_db_id}")
                fixed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to update user: {e}")
        else:
            print(f"   ❌ No matching league found for '{user['league_name']}'")
    
    print(f"\n🎉 Fixed {fixed_count} out of {len(problem_users)} users")


def verify_fixes():
    """Verify that the fixes worked"""
    print("\n=== VERIFYING FIXES ===")
    
    # Check if any users still have NULL league_id with non-NULL league_name
    remaining_query = """
        SELECT COUNT(*) as count
        FROM users
        WHERE league_id IS NULL 
        AND league_name IS NOT NULL 
        AND league_name != ''
    """
    
    remaining = execute_query_one(remaining_query)
    
    if remaining['count'] == 0:
        print("✅ All users now have proper league_id values!")
    else:
        print(f"⚠️  {remaining['count']} users still have NULL league_id")


if __name__ == "__main__":
    fix_user_league_ids()
    verify_fixes() 