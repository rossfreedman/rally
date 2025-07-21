#!/usr/bin/env python3
"""
Test Enhanced ETL League Context Protection
==========================================

This script tests the enhanced auto_fix_broken_league_contexts function
to ensure it correctly handles users missing league contexts after ETL.

Usage:
    python scripts/test_enhanced_etl_league_protection.py
"""

import os
import sys
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db
from data.etl.database_import.enhanced_league_context_protection import auto_fix_broken_league_contexts

def test_scenario_1_missing_associations():
    """Test users who have tenniscores_player_id but no associations"""
    print("🧪 TEST SCENARIO 1: Users missing player associations")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Find users missing associations
        cursor.execute("""
            SELECT 
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.tenniscores_player_id,
                u.league_context
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.tenniscores_player_id IS NOT NULL
            AND upa.user_id IS NULL
        """)
        
        missing_users = cursor.fetchall()
        print(f"   Found {len(missing_users)} users missing associations:")
        
        for user in missing_users:
            print(f"     - {user[2]} {user[3]} (ID: {user[0]}, Player: {user[4]}, League Context: {user[5]})")
        
        return len(missing_users)

def test_scenario_2_broken_contexts():
    """Test users with broken league contexts"""
    print("\n🧪 TEST SCENARIO 2: Users with broken league contexts")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Find users with broken league contexts
        cursor.execute("""
            SELECT 
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.league_context
            FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE u.league_context IS NOT NULL 
            AND l.id IS NULL
        """)
        
        broken_users = cursor.fetchall()
        print(f"   Found {len(broken_users)} users with broken contexts:")
        
        for user in broken_users:
            print(f"     - {user[2]} {user[3]} (ID: {user[0]}, Broken Context: {user[4]})")
        
        return len(broken_users)

def test_scenario_3_null_contexts():
    """Test users with NULL league contexts who have associations"""
    print("\n🧪 TEST SCENARIO 3: Users with NULL contexts who have associations")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Find users with NULL contexts who have associations
        cursor.execute("""
            SELECT DISTINCT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.league_context
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.league_context IS NULL
        """)
        
        null_users = cursor.fetchall()
        print(f"   Found {len(null_users)} users with NULL contexts who have associations:")
        
        for user in null_users:
            print(f"     - {user[2]} {user[3]} (ID: {user[0]}, Context: {user[4]})")
        
        return len(null_users)

def run_enhanced_fix():
    """Run the enhanced auto-fix function"""
    print("\n🔧 RUNNING ENHANCED AUTO-FIX...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            fixed_count = auto_fix_broken_league_contexts(cursor)
            conn.commit()
            
            print(f"\n✅ Enhanced auto-fix completed: {fixed_count} users processed")
            return fixed_count
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Enhanced auto-fix failed: {str(e)}")
            raise

def verify_final_state():
    """Verify the final state after the fix"""
    print("\n✅ VERIFYING FINAL STATE...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check users without league context
        cursor.execute("""
            SELECT COUNT(*) FROM users WHERE league_context IS NULL
        """)
        users_without_context = cursor.fetchone()[0]
        
        # Check users with valid league context
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            JOIN leagues l ON users.league_context = l.id
            WHERE users.league_context IS NOT NULL
        """)
        users_with_valid_context = cursor.fetchone()[0]
        
        # Check users with broken league context
        cursor.execute("""
            SELECT COUNT(*) FROM users u
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE u.league_context IS NOT NULL AND l.id IS NULL
        """)
        users_with_broken_context = cursor.fetchone()[0]
        
        print(f"   Users without league context: {users_without_context}")
        print(f"   Users with valid league context: {users_with_valid_context}")
        print(f"   Users with broken league context: {users_with_broken_context}")
        
        # Check league distribution
        cursor.execute("""
            SELECT l.league_name, COUNT(*) as user_count
            FROM users u
            JOIN leagues l ON u.league_context = l.id
            GROUP BY l.league_name
            ORDER BY user_count DESC
        """)
        distribution = cursor.fetchall()
        
        print("\n   League context distribution:")
        for league in distribution:
            print(f"     - {league[0]}: {league[1]} users")
        
        return {
            "without_context": users_without_context,
            "with_valid_context": users_with_valid_context,
            "with_broken_context": users_with_broken_context,
            "distribution": distribution
        }

def main():
    print("🔬 Enhanced ETL League Context Protection Test")
    print("=" * 60)
    
    try:
        # Test before state
        print("📊 BEFORE ENHANCEMENT:")
        missing_associations = test_scenario_1_missing_associations()
        broken_contexts = test_scenario_2_broken_contexts()
        null_contexts = test_scenario_3_null_contexts()
        
        total_issues = missing_associations + broken_contexts + null_contexts
        
        if total_issues == 0:
            print("\n🎉 No issues found - system is already healthy!")
            return
        
        print(f"\n📈 Total issues found: {total_issues}")
        
        # Run the enhanced fix
        fixed_count = run_enhanced_fix()
        
        # Verify final state
        final_state = verify_final_state()
        
        # Summary
        print("\n🎯 SUMMARY:")
        print(f"   Issues found: {total_issues}")
        print(f"   Users processed: {fixed_count}")
        print(f"   Users with broken contexts remaining: {final_state['with_broken_context']}")
        
        if final_state['with_broken_context'] == 0:
            print("\n🎉 SUCCESS: All league context issues resolved!")
            print("   Users will no longer see the league selection modal after ETL.")
        else:
            print(f"\n⚠️  WARNING: {final_state['with_broken_context']} users still have broken contexts")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 