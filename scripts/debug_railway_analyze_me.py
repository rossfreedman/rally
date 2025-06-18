#!/usr/bin/env python3
"""
Debug script to diagnose analyze-me issues on Railway vs Local
Run this on both environments to compare data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def debug_user_data(email='jredland@gmail.com'):
    """Debug user data differences"""
    print(f"=== DEBUGGING USER DATA FOR {email} ===")
    
    # 1. Check user table data
    print("\n1. USER TABLE DATA:")
    user_query = """
        SELECT id, email, first_name, last_name, league_id, league_name, 
               club, series, tenniscores_player_id, is_admin
        FROM users 
        WHERE email = %s
    """
    user_data = execute_query_one(user_query, [email])
    if user_data:
        print(f"   User ID: {user_data['id']}")
        print(f"   Name: {user_data['first_name']} {user_data['last_name']}")
        print(f"   League ID: {user_data['league_id']} (type: {type(user_data['league_id'])})")
        print(f"   League Name: {user_data['league_name']}")
        print(f"   Club: {user_data['club']}")
        print(f"   Series: {user_data['series']}")
        print(f"   Player ID: {user_data['tenniscores_player_id']}")
    else:
        print("   ❌ User not found!")
        return
    
    # 2. Check leagues table
    print("\n2. LEAGUES TABLE:")
    leagues_query = "SELECT id, league_id, league_name FROM leagues ORDER BY id"
    leagues = execute_query(leagues_query)
    for league in leagues:
        print(f"   ID {league['id']}: '{league['league_id']}' -> '{league['league_name']}'")
    
    # 3. Check if user's league_name can be resolved
    print("\n3. LEAGUE RESOLUTION:")
    if user_data['league_name']:
        league_lookup = execute_query_one(
            "SELECT id, league_id FROM leagues WHERE league_name = %s",
            [user_data['league_name']]
        )
        if league_lookup:
            print(f"   ✅ '{user_data['league_name']}' resolves to: ID {league_lookup['id']}, league_id '{league_lookup['league_id']}'")
        else:
            print(f"   ❌ '{user_data['league_name']}' does NOT resolve to any league")
    
    # 4. Check player data
    print("\n4. PLAYER DATA:")
    if user_data['tenniscores_player_id']:
        player_query = """
            SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
                   p.league_id, p.club_id, p.series_id, p.is_active,
                   l.league_name, l.league_id as league_identifier,
                   c.name as club_name, s.name as series_name
            FROM players p
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id  
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
        """
        players = execute_query(player_query, [user_data['tenniscores_player_id']])
        if players:
            print(f"   Found {len(players)} player record(s):")
            for i, player in enumerate(players, 1):
                print(f"   Player {i}:")
                print(f"     DB ID: {player['id']}")
                print(f"     Name: {player['first_name']} {player['last_name']}")
                print(f"     League: {player['league_name']} (ID: {player['league_id']}, identifier: '{player['league_identifier']}')")
                print(f"     Club: {player['club_name']} (ID: {player['club_id']})")
                print(f"     Series: {player['series_name']} (ID: {player['series_id']})")
                print(f"     Active: {player['is_active']}")
        else:
            print(f"   ❌ No player found with ID: {user_data['tenniscores_player_id']}")
    
    # 5. Check match data
    print("\n5. MATCH DATA:")
    if user_data['tenniscores_player_id']:
        # Count matches without league filter
        total_matches_query = """
            SELECT COUNT(*) as count
            FROM match_scores
            WHERE (home_player_1_id = %s OR home_player_2_id = %s 
                   OR away_player_1_id = %s OR away_player_2_id = %s)
        """
        total_matches = execute_query_one(total_matches_query, 
            [user_data['tenniscores_player_id']] * 4)
        print(f"   Total matches (no league filter): {total_matches['count']}")
        
        # Count matches per league
        matches_by_league_query = """
            SELECT l.league_name, l.league_id, COUNT(*) as count
            FROM match_scores ms
            LEFT JOIN leagues l ON ms.league_id = l.id
            WHERE (ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
                   OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s)
            GROUP BY l.league_name, l.league_id, ms.league_id
            ORDER BY count DESC
        """
        matches_by_league = execute_query(matches_by_league_query,
            [user_data['tenniscores_player_id']] * 4)
        
        if matches_by_league:
            print("   Matches by league:")
            for match_data in matches_by_league:
                league_name = match_data['league_name'] or 'NULL'
                league_id = match_data['league_id'] or 'NULL'
                print(f"     {league_name} ({league_id}): {match_data['count']} matches")
        else:
            print("   ❌ No matches found for this player")
    
    # 6. Environment check
    print("\n6. ENVIRONMENT:")
    import os
    db_host = os.getenv('DATABASE_URL', 'Not set')
    if 'railway' in db_host.lower():
        print("   🚂 Running on Railway")
    elif 'localhost' in db_host or '127.0.0.1' in db_host:
        print("   🏠 Running locally")
    else:
        print(f"   ❓ Unknown environment: {db_host[:50]}...")


def debug_session_vs_db_mismatch():
    """Check for common session vs database mismatches"""
    print("\n=== SESSION VS DATABASE MISMATCH ANALYSIS ===")
    
    # Find users where session data might not match database
    mismatch_query = """
        SELECT u.email, u.first_name, u.last_name,
               u.league_id as user_league_id, u.league_name as user_league_name,
               p.league_id as player_league_id, l.league_name as player_league_name,
               l.league_id as player_league_identifier
        FROM users u
        LEFT JOIN players p ON u.tenniscores_player_id = p.tenniscores_player_id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE u.tenniscores_player_id IS NOT NULL
        AND (u.league_id IS NULL OR u.league_id != p.league_id)
        ORDER BY u.email
    """
    
    mismatches = execute_query(mismatch_query)
    if mismatches:
        print(f"Found {len(mismatches)} users with potential session/database mismatches:")
        for user in mismatches:
            print(f"  {user['email']} ({user['first_name']} {user['last_name']}):")
            print(f"    User table: league_id={user['user_league_id']}, league_name='{user['user_league_name']}'")
            print(f"    Player table: league_id={user['player_league_id']}, league_name='{user['player_league_name']}' ('{user['player_league_identifier']}')")
    else:
        print("✅ No obvious session/database mismatches found")


if __name__ == "__main__":
    debug_user_data()
    debug_session_vs_db_mismatch() 