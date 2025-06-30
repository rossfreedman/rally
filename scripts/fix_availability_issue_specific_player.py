#!/usr/bin/env python3
"""
Fix Availability Issue for Specific Player
==========================================

This script diagnoses and fixes the availability page issue for player ID: nndz-WkMrK3didjlnUT09
The issue is that the session service isn't returning the correct team_id for multi-team players.

Problem:
- User has multiple team associations
- Session service relies on league_context to pick the right player
- If league_context is NULL or wrong, no team_id is returned
- Without team_id, availability page shows no data

Solution:
- Check user's current league_context
- Verify which leagues/teams they're associated with
- Set league_context to their primary/most active league
- Verify session service returns correct data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update
from app.services.session_service import get_session_data_for_user

PROBLEM_PLAYER_ID = "nndz-WkMrK3didjlnUT09"

def diagnose_player_issue():
    """Diagnose the session/availability issue for the specific player"""
    print(f"🔍 DIAGNOSING AVAILABILITY ISSUE FOR PLAYER: {PROBLEM_PLAYER_ID}")
    print("=" * 80)
    
    # Step 1: Find the user record
    user_query = """
        SELECT u.id, u.email, u.first_name, u.last_name, u.league_context
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE upa.tenniscores_player_id = %s
        LIMIT 1
    """
    user_record = execute_query_one(user_query, [PROBLEM_PLAYER_ID])
    
    if not user_record:
        print(f"❌ No user found for player ID: {PROBLEM_PLAYER_ID}")
        return False
    
    print(f"✅ Found user: {user_record['first_name']} {user_record['last_name']} ({user_record['email']})")
    print(f"   User ID: {user_record['id']}")
    print(f"   Current league_context: {user_record['league_context']}")
    
    # Step 2: Check all player associations
    associations_query = """
        SELECT 
            p.id as player_db_id,
            p.tenniscores_player_id,
            p.team_id,
            p.league_id,
            p.club_id,
            p.series_id,
            p.is_active,
            l.league_name,
            l.league_id as league_string_id,
            c.name as club_name,
            s.name as series_name,
            t.team_name
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE upa.user_id = %s
        ORDER BY p.is_active DESC, p.league_id, p.club_id, p.series_id
    """
    associations = execute_query(associations_query, [user_record['id']])
    
    print(f"\n📋 PLAYER ASSOCIATIONS ({len(associations)} found):")
    for i, assoc in enumerate(associations, 1):
        status = "ACTIVE" if assoc['is_active'] else "INACTIVE"
        print(f"   {i}. {status} - League: {assoc['league_name']} ({assoc['league_string_id']})")
        print(f"      Club: {assoc['club_name']}, Series: {assoc['series_name']}")
        print(f"      Team: {assoc['team_name']} (ID: {assoc['team_id']})")
        print(f"      League DB ID: {assoc['league_id']}")
        print()
    
    # Step 3: Test current session service
    print("🧪 TESTING CURRENT SESSION SERVICE:")
    session_data = get_session_data_for_user(user_record['email'])
    
    if session_data:
        print(f"   ✅ Session service returned data:")
        print(f"      Team ID: {session_data.get('team_id')}")
        print(f"      League: {session_data.get('league_name')}")
        print(f"      Club: {session_data.get('club')}")
        print(f"      Series: {session_data.get('series')}")
        print(f"      Player ID: {session_data.get('tenniscores_player_id')}")
        
        if session_data.get('team_id'):
            print(f"   ✅ Has team_id - availability page should work")
            return True
        else:
            print(f"   ❌ Missing team_id - this is the problem!")
    else:
        print(f"   ❌ Session service returned no data")
    
    return False

def fix_player_league_context():
    """Fix the user's league_context to point to their most active league"""
    print(f"\n🔧 FIXING LEAGUE CONTEXT FOR PLAYER: {PROBLEM_PLAYER_ID}")
    print("=" * 80)
    
    # Find the user
    user_query = """
        SELECT u.id, u.email, u.league_context
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE upa.tenniscores_player_id = %s
        LIMIT 1
    """
    user_record = execute_query_one(user_query, [PROBLEM_PLAYER_ID])
    
    if not user_record:
        print(f"❌ User not found")
        return False
    
    # Find their most active league (one with most recent matches)
    most_active_league_query = """
        SELECT 
            p.league_id,
            l.league_name,
            l.league_id as league_string_id,
            p.team_id,
            COUNT(ms.id) as match_count,
            MAX(ms.match_date) as last_match_date
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN match_scores ms ON (
            (ms.home_player_1_id = p.tenniscores_player_id OR 
             ms.home_player_2_id = p.tenniscores_player_id OR
             ms.away_player_1_id = p.tenniscores_player_id OR 
             ms.away_player_2_id = p.tenniscores_player_id)
            AND ms.league_id = p.league_id
        )
        WHERE upa.user_id = %s
        AND p.is_active = TRUE
        AND p.team_id IS NOT NULL
        GROUP BY p.league_id, l.league_name, l.league_id, p.team_id
        ORDER BY last_match_date DESC NULLS LAST, match_count DESC
        LIMIT 1
    """
    best_league = execute_query_one(most_active_league_query, [user_record['id']])
    
    if not best_league:
        print(f"❌ No active leagues found for user")
        return False
    
    print(f"   🎯 Most active league: {best_league['league_name']} (DB ID: {best_league['league_id']})")
    print(f"      Match count: {best_league['match_count']}")
    print(f"      Last match: {best_league['last_match_date']}")
    print(f"      Team ID: {best_league['team_id']}")
    
    # Update user's league_context
    update_result = execute_update("""
        UPDATE users 
        SET league_context = %s
        WHERE id = %s
    """, [best_league['league_id'], user_record['id']])
    
    if update_result > 0:
        print(f"   ✅ Updated league_context to {best_league['league_id']}")
        return True
    else:
        print(f"   ❌ Failed to update league_context")
        return False

def verify_fix():
    """Verify that the fix worked"""
    print(f"\n✅ VERIFYING FIX FOR PLAYER: {PROBLEM_PLAYER_ID}")
    print("=" * 80)
    
    # Find the user email
    user_query = """
        SELECT u.email, u.league_context
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE upa.tenniscores_player_id = %s
        LIMIT 1
    """
    user_record = execute_query_one(user_query, [PROBLEM_PLAYER_ID])
    
    if not user_record:
        print(f"❌ User not found")
        return False
    
    print(f"   📧 Testing session for: {user_record['email']}")
    print(f"   🎯 League context: {user_record['league_context']}")
    
    # Test session service again
    session_data = get_session_data_for_user(user_record['email'])
    
    if session_data:
        print(f"   ✅ Session service results:")
        print(f"      Team ID: {session_data.get('team_id')} {'✅' if session_data.get('team_id') else '❌'}")
        print(f"      League: {session_data.get('league_name')}")
        print(f"      Club: {session_data.get('club')}")
        print(f"      Series: {session_data.get('series')}")
        
        if session_data.get('team_id'):
            print(f"\n   🎉 SUCCESS! User now has team_id - availability page should work!")
            return True
        else:
            print(f"\n   ❌ Still missing team_id - fix did not work")
            return False
    else:
        print(f"   ❌ Session service still returns no data")
        return False

def main():
    """Main function to diagnose and fix the issue"""
    print("🚀 FIXING AVAILABILITY ISSUE FOR SPECIFIC PLAYER")
    print("=" * 80)
    print(f"Target Player ID: {PROBLEM_PLAYER_ID}")
    print(f"Issue: Availability page empty on Railway but works locally")
    print(f"Root Cause: Missing team_id in session data for multi-team player")
    print()
    
    # Step 1: Diagnose the current issue
    is_working = diagnose_player_issue()
    
    if is_working:
        print(f"\n🎉 No fix needed - availability should already be working!")
        return
    
    # Step 2: Apply the fix
    print(f"\n" + "="*80)
    fix_success = fix_player_league_context()
    
    if not fix_success:
        print(f"\n❌ Fix failed - could not update league context")
        return
    
    # Step 3: Verify the fix worked
    print(f"\n" + "="*80)
    verify_success = verify_fix()
    
    if verify_success:
        print(f"\n🎉 SUCCESS! The availability issue should now be resolved!")
        print(f"   The user's league_context has been set to their most active league.")
        print(f"   The session service now returns the correct team_id.")
        print(f"   The availability page should now show matches on Railway.")
    else:
        print(f"\n❌ Fix verification failed - manual investigation needed")

if __name__ == "__main__":
    main() 