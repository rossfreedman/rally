#!/usr/bin/env python3
"""Debug script to investigate track-byes-courts page issues"""

import sys
sys.path.append('.')

from database_utils import execute_query, execute_query_one
from app.routes.mobile_routes import get_user_team_id, get_team_members_with_court_stats, get_mobile_team_data

def debug_track_byes_courts():
    """Debug the track-byes-courts functionality step by step"""
    
    # Test user (you can modify this to match your actual user data)
    test_user = {
        'id': 1,  # This should be your actual user ID from the users table
        'email': 'rossfreedman@gmail.com',
        'first_name': 'Ross',
        'last_name': 'Freedman',
        'club': 'Tennaqua',
        'series': 'Series 2B',
        'league_id': 'NSTF'
    }
    
    print("🔍 DEBUGGING TRACK-BYES-COURTS PAGE")
    print("=" * 60)
    print(f"Test user: {test_user['first_name']} {test_user['last_name']} ({test_user['email']})")
    print(f"Club: {test_user['club']}")
    print(f"Series: {test_user['series']}")
    print(f"League: {test_user['league_id']}")
    print()

    # Step 1: Check if user exists in database
    print("📋 Step 1: Checking user in database...")
    user_check = execute_query_one(
        "SELECT * FROM users WHERE email = %s", 
        [test_user['email']]
    )
    if user_check:
        print(f"✅ User found: ID={user_check['id']}, Name={user_check['first_name']} {user_check['last_name']}")
        test_user['id'] = user_check['id']  # Use actual user ID
    else:
        print("❌ User not found in database")
        return
    print()

    # Step 2: Check user-player associations
    print("📋 Step 2: Checking user-player associations...")
    associations = execute_query("""
        SELECT upa.*, p.first_name, p.last_name, p.team_id, p.is_active
        FROM user_player_associations upa
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        WHERE upa.user_id = %s
    """, [test_user['id']])
    
    if associations:
        print(f"✅ Found {len(associations)} player associations:")
        for assoc in associations:
            print(f"   - Player: {assoc['first_name']} {assoc['last_name']}")
            print(f"     Player ID: {assoc['tenniscores_player_id']}")
            print(f"     Team ID: {assoc['team_id']}")
            print(f"     Is Active: {assoc['is_active']}")
            print(f"     Is Primary: {assoc['is_primary']}")
    else:
        print("❌ No player associations found")
        return
    print()

    # Step 3: Get user's team ID
    print("📋 Step 3: Getting user's team ID...")
    team_id = get_user_team_id(test_user)
    if team_id:
        print(f"✅ Team ID found: {team_id}")
    else:
        print("❌ No team ID found")
        return
    print()

    # Step 4: Get team info
    print("📋 Step 4: Getting team information...")
    team_info = execute_query_one(
        "SELECT * FROM teams WHERE id = %s", 
        [team_id]
    )
    if team_info:
        print(f"✅ Team found: {team_info['team_name']}")
        print(f"   Team alias: {team_info.get('team_alias', 'None')}")
        print(f"   Club ID: {team_info['club_id']}")
        print(f"   Series ID: {team_info['series_id']}")
        print(f"   League ID: {team_info['league_id']}")
    else:
        print("❌ Team not found")
        return
    print()

    # Step 5: Get team members
    print("📋 Step 5: Getting team members...")
    team_members = execute_query("""
        SELECT p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id, p.is_active
        FROM players p
        WHERE p.team_id = %s AND p.is_active = TRUE
        ORDER BY p.first_name, p.last_name
    """, [team_id])
    
    if team_members:
        print(f"✅ Found {len(team_members)} team members:")
        for member in team_members:
            print(f"   - {member['first_name']} {member['last_name']}")
            print(f"     Player ID: {member['tenniscores_player_id']}")
            print(f"     PTI: {member.get('pti', 'N/A')}")
    else:
        print("❌ No team members found")
    print()

    # Step 6: Get team members with court stats
    print("📋 Step 6: Getting team members with court stats...")
    team_members_with_stats = get_team_members_with_court_stats(team_id, test_user)
    
    if team_members_with_stats:
        print(f"✅ Found {len(team_members_with_stats)} team members with stats:")
        for member in team_members_with_stats:
            court_total = sum(member['court_stats'].values()) if member['court_stats'] else 0
            print(f"   - {member['name']}")
            print(f"     Match count: {member['match_count']}")
            print(f"     Court assignments total: {court_total}")
            print(f"     Court stats: {member['court_stats']}")
    else:
        print("❌ No team members with stats found")
        
        # This would trigger the fallback to sample data
        print()
        print("🚨 This would trigger the fallback to sample data!")
        print("   The page would show:")
        print("   - John Smith (8 matches)")
        print("   - Sarah Johnson (6 matches)")
        print("   - Mike Davis (5 matches)")
        print("   - Lisa Wilson (7 matches)")
        print("   - David Brown (4 matches)")
        print("   - Emily Chen (9 matches)")
    print()

    # Step 7: Check match data
    print("📋 Step 7: Checking match data...")
    if team_info:
        team_name = team_info.get('team_alias') or team_info.get('team_name')
        matches = execute_query("""
            SELECT COUNT(*) as match_count
            FROM match_scores
            WHERE (home_team = %s OR away_team = %s)
            OR (home_team_id = %s OR away_team_id = %s)
        """, [team_name, team_name, team_id, team_id])
        
        if matches and matches[0]['match_count'] > 0:
            print(f"✅ Found {matches[0]['match_count']} matches for team")
        else:
            print("❌ No matches found for team")
            print(f"   Searched for team name: '{team_name}'")
            print(f"   Searched for team ID: {team_id}")

if __name__ == "__main__":
    debug_track_byes_courts() 