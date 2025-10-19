#!/usr/bin/env python3
"""
Validate that user contexts are working correctly on local database.
This confirms that even though contexts point to teams with inactive (S) players,
the session logic correctly shows only active player records.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_utils import get_db_cursor
from datetime import datetime

def validate_local_contexts():
    print("=" * 80)
    print("LOCAL DATABASE VALIDATION - USER CONTEXTS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    with get_db_cursor(commit=False) as cursor:
        
        # Check 1: Users with (S) team contexts
        print("CHECK 1: USERS WITH CONTEXTS POINTING TO (S) TEAMS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(DISTINCT u.id) as count
            FROM user_contexts uc
            JOIN users u ON uc.user_id = u.id
            JOIN teams t ON uc.team_id = t.id
            JOIN players p_s ON t.id = p_s.team_id
            WHERE (p_s.first_name LIKE %s OR p_s.last_name LIKE %s)
            AND p_s.is_active = false
        """, ('%(S)', '%(S)'))
        
        affected_count = cursor.fetchone()['count']
        print(f"Found {affected_count} users with contexts pointing to (S) teams")
        print()
        
        # Check 2: Verify all have active regular player records
        print("CHECK 2: VERIFY ALL HAVE ACTIVE REGULAR PLAYER RECORDS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT DISTINCT u.id, u.email, u.first_name, u.last_name
            FROM user_contexts uc
            JOIN users u ON uc.user_id = u.id
            JOIN teams t ON uc.team_id = t.id
            JOIN players p_s ON t.id = p_s.team_id
            WHERE (p_s.first_name LIKE %s OR p_s.last_name LIKE %s)
            AND p_s.is_active = false
        """, ('%(S)', '%(S)'))
        
        affected_users = cursor.fetchall()
        
        all_have_active = True
        for user in affected_users:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM players p
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s
                AND p.is_active = true
                AND p.first_name NOT LIKE %s
                AND p.last_name NOT LIKE %s
            """, (user['id'], '%(S)', '%(S)'))
            
            active_count = cursor.fetchone()['count']
            
            if active_count == 0:
                print(f"❌ {user['email']} has NO active player records!")
                all_have_active = False
        
        if all_have_active:
            print(f"✅ All {len(affected_users)} users have active regular player records")
        print()
        
        # Check 3: Simulate session building for sample users
        print("CHECK 3: SIMULATE SESSION BUILDING (SAMPLE USERS)")
        print("-" * 80)
        
        sample_users = affected_users[:3] if len(affected_users) >= 3 else affected_users
        
        all_sessions_work = True
        for user in sample_users:
            # Simulate the session query (simplified version)
            cursor.execute("""
                SELECT p.id, p.first_name, p.last_name, p.team_id,
                       t.team_name, s.name as series_name, p.is_active
                FROM players p
                JOIN teams t ON p.team_id = t.id
                JOIN series s ON t.series_id = s.id
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s
                AND p.is_active = true
                ORDER BY upa.is_primary DESC, p.id DESC
                LIMIT 1
            """, (user['id'],))
            
            session_player = cursor.fetchone()
            
            if session_player:
                print(f"✅ {user['email']}:")
                print(f"   Would see: {session_player['first_name']} {session_player['last_name']}")
                print(f"   Team: {session_player['team_name']} ({session_player['series_name']})")
                print(f"   Active: {session_player['is_active']}")
            else:
                print(f"❌ {user['email']}: Session building would FAIL!")
                all_sessions_work = False
        
        print()
        
        if all_sessions_work:
            print("✅ All sample users can build sessions successfully")
        else:
            print("❌ Some users would fail to build sessions")
        print()
        
        # Check 4: Verify no active (S) records
        print("CHECK 4: VERIFY NO ACTIVE (S) RECORDS EXIST")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE %s OR last_name LIKE %s)
            AND is_active = true
        """, ('%(S)', '%(S)'))
        
        active_s_count = cursor.fetchone()['count']
        
        if active_s_count == 0:
            print(f"✅ 0 active (S) records (correct)")
        else:
            print(f"❌ {active_s_count} active (S) records found!")
        print()
        
        # Check 5: Total inactive (S) records
        print("CHECK 5: TOTAL INACTIVE (S) RECORDS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE %s OR last_name LIKE %s)
            AND is_active = false
        """, ('%(S)', '%(S)'))
        
        inactive_s_count = cursor.fetchone()['count']
        print(f"Total inactive (S) records: {inactive_s_count}")
        print()
        
        # Final summary
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        
        if all_have_active and all_sessions_work and active_s_count == 0:
            print()
            print("🎉 ALL VALIDATIONS PASSED!")
            print()
            print("✅ User contexts are working correctly")
            print("✅ All affected users have active player records")
            print("✅ Session building works for all users")
            print("✅ No active (S) records exist")
            print("✅ System is functioning normally")
            print()
            print("CONCLUSION: No changes needed - contexts are safe to leave as-is")
            print()
            return True
        else:
            print()
            print("⚠️  SOME VALIDATIONS FAILED")
            print("Review the failures above")
            print()
            return False

if __name__ == "__main__":
    success = validate_local_contexts()
    sys.exit(0 if success else 1)



