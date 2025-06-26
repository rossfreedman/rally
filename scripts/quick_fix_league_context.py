#!/usr/bin/env python3
"""
Quick Fix for League Context on Railway
=======================================
Direct fix for the league_context NULL issue causing yellow alert banners.
"""

import os
import sys

# Force Railway environment BEFORE importing database modules
os.environ['RAILWAY_ENVIRONMENT'] = 'production'
os.environ['DATABASE_PUBLIC_URL'] = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

# Add the parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update


def fix_all_league_contexts():
    """Fix league_context for all users who need it"""
    print("🔧 FIXING LEAGUE CONTEXT FOR ALL USERS")
    print("=" * 50)
    
    # Update all users to have a valid league_context based on their player associations
    # This query sets league_context to the league of their first active player
    update_query = """
        UPDATE users 
        SET league_context = (
            SELECT p.league_id
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE upa.user_id = users.id 
              AND p.is_active = TRUE
            ORDER BY 
                CASE WHEN p.league_id IN (
                    SELECT id FROM leagues WHERE league_name LIKE '%APTA%'
                ) THEN 1 ELSE 2 END,
                p.league_id
            LIMIT 1
        )
        WHERE users.id IN (
            SELECT DISTINCT u.id
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE p.is_active = TRUE
              AND (u.league_context IS NULL OR u.league_context NOT IN (
                  SELECT DISTINCT p2.league_id
                  FROM players p2
                  JOIN user_player_associations upa2 ON p2.tenniscores_player_id = upa2.tenniscores_player_id
                  WHERE upa2.user_id = u.id AND p2.is_active = TRUE
              ))
        )
    """
    
    result = execute_update(update_query)
    print(f"   ✅ Updated league_context for {result} users")
    
    return result


def verify_fixes():
    """Verify that the fixes worked"""
    print(f"\n🔍 VERIFYING FIXES")
    print("=" * 30)
    
    # Test the session query for a few users
    test_users = execute_query("""
        SELECT email, first_name, last_name, league_context
        FROM users
        ORDER BY email
        LIMIT 5
    """)
    
    for user in test_users:
        print(f"\n   Testing {user['first_name']} {user['last_name']} ({user['email']})")
        print(f"   League context: {user['league_context']}")
        
        # Test session query
        session_result = execute_query_one("""
            SELECT u.league_context, p.tenniscores_player_id, c.name as club, l.league_name
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                AND p.league_id = u.league_context 
                AND p.is_active = TRUE
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE u.email = %s
            LIMIT 1
        """, [user['email']])
        
        if session_result and session_result['tenniscores_player_id']:
            print(f"   ✅ Session query returns valid player ID")
            print(f"   League: {session_result['league_name']}, Club: {session_result['club']}")
        else:
            print(f"   ❌ Session query still returns NULL player ID")


def main():
    """Main execution function"""
    print("🔧 QUICK FIX FOR LEAGUE CONTEXT ON RAILWAY")
    print("=" * 50)
    
    try:
        print("✅ Using Railway database connection")
        
        # Fix all league contexts
        fixed_count = fix_all_league_contexts()
        
        if fixed_count > 0:
            # Verify the fixes
            verify_fixes()
            print(f"\n✅ SUCCESS! Fixed league_context for {fixed_count} users.")
            print(f"   The yellow alert banner should disappear on next login.")
        else:
            print(f"\n✅ No users needed fixing.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main() 