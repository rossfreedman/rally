#!/usr/bin/env python3
"""
Script to test and fix the league filtering issue in find-people-to-play functionality.
The issue is that Brett Pierson shows entries from both APTA Chicago and NSTF leagues when it should only show APTA Chicago.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def test_league_filtering():
    """Test the league filtering logic"""
    
    print("=== Testing League Filtering for Find People to Play ===\n")
    
    # 1. Check user's league context
    user_email = "rossfreedman@gmail.com"
    user_query = """
        SELECT u.email, u.league_context, l.league_name, l.league_id, l.id as league_db_id
        FROM users u
        LEFT JOIN leagues l ON u.league_context = l.id
        WHERE u.email = %s
    """
    user_info = execute_query_one(user_query, [user_email])
    print(f"1. User league context: {user_info}")
    
    if not user_info or not user_info['league_context']:
        print("❌ User has no league context set!")
        return
    
    user_league_db_id = user_info['league_context']
    print(f"✅ User league DB ID: {user_league_db_id} ({user_info['league_name']})")
    
    # 2. Test the exact query that should be used in find-people-to-play
    test_query = """
        SELECT 
            p.first_name as "First Name",
            p.last_name as "Last Name", 
            p.tenniscores_player_id as "Player ID",
            CASE WHEN p.pti IS NULL THEN 'N/A' ELSE p.pti::TEXT END as "PTI",
            c.name as "Club",
            s.name as "Series",
            l.league_name as "League",
            l.id as "League DB ID",
            t.id as "Team ID",
            t.team_name as "Team Name"
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id  
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.tenniscores_player_id IS NOT NULL
        AND p.league_id = %s
        AND p.is_active = true
        AND p.first_name ILIKE %s
        AND p.last_name ILIKE %s
        ORDER BY p.first_name, p.last_name, t.team_name
    """
    
    print(f"\n2. Testing database query with league filtering (league_id = {user_league_db_id}):")
    brett_players = execute_query(test_query, [user_league_db_id, '%brett%', '%pierson%'])
    
    print(f"Found {len(brett_players)} Brett Pierson entries with league filtering:")
    for player in brett_players:
        print(f"  - {player['First Name']} {player['Last Name']} | {player['Club']} | {player['Series']} | Team: {player['Team Name']} | League: {player['League']} (ID: {player['League DB ID']})")
    
    # 3. Test without league filtering to see what we SHOULD be filtering out
    test_query_no_filter = """
        SELECT 
            p.first_name as "First Name",
            p.last_name as "Last Name", 
            c.name as "Club",
            s.name as "Series",
            l.league_name as "League",
            l.id as "League DB ID",
            t.team_name as "Team Name"
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id  
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.tenniscores_player_id IS NOT NULL
        AND p.is_active = true
        AND p.first_name ILIKE %s
        AND p.last_name ILIKE %s
        ORDER BY p.first_name, p.last_name, t.team_name
    """
    
    print(f"\n3. Testing WITHOUT league filtering (to see what should be filtered out):")
    all_brett_players = execute_query(test_query_no_filter, ['%brett%', '%pierson%'])
    
    print(f"Found {len(all_brett_players)} Brett Pierson entries WITHOUT league filtering:")
    for player in all_brett_players:
        should_show = "✅ SHOW" if player['League DB ID'] == user_league_db_id else "❌ HIDE"
        print(f"  {should_show} - {player['First Name']} {player['Last Name']} | {player['Club']} | {player['Series']} | Team: {player['Team Name']} | League: {player['League']} (ID: {player['League DB ID']})")
    
    # 4. Summary
    print(f"\n=== SUMMARY ===")
    print(f"User should only see entries from league: {user_info['league_name']} (DB ID: {user_league_db_id})")
    print(f"With league filtering: {len(brett_players)} entries")
    print(f"Without league filtering: {len(all_brett_players)} entries")
    
    expected_entries = [p for p in all_brett_players if p['League DB ID'] == user_league_db_id]
    print(f"Expected entries after filtering: {len(expected_entries)}")
    
    if len(brett_players) == len(expected_entries):
        print("✅ League filtering is working correctly!")
    else:
        print("❌ League filtering is NOT working correctly!")
        print("The mobile_service.py file needs to be fixed to use proper league filtering.")

if __name__ == "__main__":
    test_league_filtering() 