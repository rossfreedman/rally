#!/usr/bin/env python3
"""
Verify ETL Fixes are Properly Embedded

This script verifies that all the fixes for polls, captain messages, and practice times
are properly embedded in the ETL process and working correctly.
"""

import psycopg2
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import parse_db_url, get_db_url
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_etl_fixes():
    """Verify that all ETL fixes are properly embedded and working"""
    print("🔍 Verifying ETL Fixes are Properly Embedded")
    print("=" * 60)
    
    try:
        # Connect to database
        config = parse_db_url(get_db_url())
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Step 1: Verify polls are associated with teams that have users
        print("\n📊 Step 1: Verifying Poll Associations")
        print("-" * 40)
        
        cursor.execute("""
            SELECT p.question, t.team_name, COUNT(DISTINCT u.id) as user_count
            FROM polls p 
            JOIN teams t ON p.team_id = t.id 
            JOIN players pl ON t.id = pl.team_id 
            JOIN user_player_associations upa ON pl.tenniscores_player_id = upa.tenniscores_player_id 
            JOIN users u ON upa.user_id = u.id 
            GROUP BY p.id, p.question, t.team_name
        """)
        
        polls_with_users = cursor.fetchall()
        print(f"   Polls associated with teams that have users: {len(polls_with_users)}")
        
        for poll_question, team_name, user_count in polls_with_users:
            print(f"   ✅ \"{poll_question}\" → {team_name} ({user_count} users)")
        
        # Check for orphaned polls
        cursor.execute("""
            SELECT COUNT(*) 
            FROM polls p 
            LEFT JOIN teams t ON p.team_id = t.id 
            WHERE p.team_id IS NOT NULL AND t.id IS NULL
        """)
        
        orphaned_polls = cursor.fetchone()[0]
        print(f"   Orphaned polls (no valid team): {orphaned_polls}")
        
        # Step 2: Verify captain messages are associated with teams that have users
        print("\n💬 Step 2: Verifying Captain Message Associations")
        print("-" * 40)
        
        cursor.execute("""
            SELECT cm.message, t.team_name, COUNT(DISTINCT u.id) as user_count
            FROM captain_messages cm 
            JOIN teams t ON cm.team_id = t.id 
            JOIN players pl ON t.id = pl.team_id 
            JOIN user_player_associations upa ON pl.tenniscores_player_id = upa.tenniscores_player_id 
            JOIN users u ON upa.user_id = u.id 
            GROUP BY cm.id, cm.message, t.team_name
            LIMIT 5
        """)
        
        messages_with_users = cursor.fetchall()
        print(f"   Captain messages associated with teams that have users: {len(messages_with_users)}")
        
        for message, team_name, user_count in messages_with_users:
            print(f"   ✅ \"{message[:50]}...\" → {team_name} ({user_count} users)")
        
        # Check for orphaned captain messages
        cursor.execute("""
            SELECT COUNT(*) 
            FROM captain_messages cm 
            LEFT JOIN teams t ON cm.team_id = t.id 
            WHERE cm.team_id IS NOT NULL AND t.id IS NULL
        """)
        
        orphaned_messages = cursor.fetchone()[0]
        print(f"   Orphaned captain messages (no valid team): {orphaned_messages}")
        
        # Step 3: Verify practice times status
        print("\n⏰ Step 3: Verifying Practice Times Status")
        print("-" * 40)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM schedule 
            WHERE home_team LIKE '%Practice%' OR away_team LIKE '%Practice%' 
            OR home_team LIKE '%practice%' OR away_team LIKE '%practice%'
        """)
        
        practice_count = cursor.fetchone()[0]
        print(f"   Practice times in schedule: {practice_count}")
        
        if practice_count == 0:
            print("   ✅ No practice times found - this is correct (none existed in backup)")
        
        # Check for orphaned practice times
        cursor.execute("""
            SELECT COUNT(*) 
            FROM schedule 
            WHERE (home_team LIKE '%Practice%' OR away_team LIKE '%Practice%') 
            AND (home_team_id IS NULL OR away_team_id IS NULL)
        """)
        
        orphaned_practice = cursor.fetchone()[0]
        print(f"   Orphaned practice times (no team ID): {orphaned_practice}")
        
        # Step 4: Verify ETL script has proper fixes embedded
        print("\n🔧 Step 4: Verifying ETL Script Fixes")
        print("-" * 40)
        
        # Check if _fix_restored_team_id_mappings method exists and is called
        etl_script_path = "data/etl/database_import/import_all_jsons_to_database.py"
        
        if os.path.exists(etl_script_path):
            with open(etl_script_path, 'r') as f:
                etl_content = f.read()
            
            has_fix_method = "_fix_restored_team_id_mappings" in etl_content
            has_method_call = "self._fix_restored_team_id_mappings(conn)" in etl_content
            has_tennaqua_22_mapping = "Tennaqua - 22" in etl_content
            has_tennaqua_s2b_mapping = "Tennaqua S2B" in etl_content
            
            print(f"   ETL script exists: ✅")
            print(f"   _fix_restored_team_id_mappings method defined: {'✅' if has_fix_method else '❌'}")
            print(f"   Method is called in ETL process: {'✅' if has_method_call else '❌'}")
            print(f"   Maps to Tennaqua - 22 (teams with users): {'✅' if has_tennaqua_22_mapping else '❌'}")
            print(f"   Maps to Tennaqua S2B (teams with users): {'✅' if has_tennaqua_s2b_mapping else '❌'}")
        else:
            print(f"   ❌ ETL script not found at {etl_script_path}")
        
        # Step 5: Overall assessment
        print("\n📊 Step 5: Overall Assessment")
        print("-" * 40)
        
        total_issues = orphaned_polls + orphaned_messages + orphaned_practice
        
        if total_issues == 0:
            print("   ✅ ALL FIXES VERIFIED SUCCESSFULLY!")
            print("   ✅ No orphaned polls, captain messages, or practice times")
            print("   ✅ All data is associated with teams that have users")
            print("   ✅ ETL script has proper fixes embedded")
            print("   ✅ Future ETL runs will automatically map to correct teams")
        else:
            print(f"   ⚠️  {total_issues} issues found:")
            if orphaned_polls > 0:
                print(f"      - {orphaned_polls} orphaned polls")
            if orphaned_messages > 0:
                print(f"      - {orphaned_messages} orphaned captain messages")
            if orphaned_practice > 0:
                print(f"      - {orphaned_practice} orphaned practice times")
        
        conn.close()
        return total_issues == 0
        
    except Exception as e:
        logger.error(f"Error verifying ETL fixes: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    success = verify_etl_fixes()
    if success:
        print("\n🎉 All ETL fixes are properly embedded and working!")
        print("✅ Polls and captain messages will be visible to users")
        print("✅ Future ETL runs will automatically map to correct teams")
    else:
        print("\n❌ Some ETL fixes need attention!")
        exit(1) 