#!/usr/bin/env python3
"""
Investigate specific player data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def investigate_player(player_id):
    """Investigate a specific player's data"""
    
    print(f"🔍 Investigating Player ID: {player_id}")
    print("=" * 50)
    
    # 1. Get player basic info
    player_query = """
        SELECT 
            p.*,
            c.name as club_name,
            s.name as series_name,
            l.league_name as league_name
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE p.tenniscores_player_id = %s
        ORDER BY p.id DESC
    """
    
    players = execute_query(player_query, [player_id])
    
    if not players:
        print("❌ No player records found with this ID")
        return
    
    print(f"✅ Found {len(players)} player record(s):")
    for i, player in enumerate(players, 1):
        print(f"\n--- Player Record {i} ---")
        print(f"  Database ID: {player['id']}")
        print(f"  Name: {player['first_name']} {player['last_name']}")
        print(f"  Club: {player['club_name']}")
        print(f"  Series: {player['series_name']}")
        print(f"  League: {player['league_name']}")
        print(f"  League ID: {player['league_id']}")
        print(f"  Team ID: {player['team_id']}")
        print(f"  Series ID: {player['series_id']}")
    
    # 2. Get recent matches
    matches_query = """
        SELECT 
            ms.*,
            CASE 
                WHEN ms.home_player_1_id = %s OR ms.home_player_2_id = %s THEN 'home'
                ELSE 'away'
            END as player_side,
            CASE 
                WHEN ms.home_player_1_id = %s OR ms.home_player_2_id = %s THEN 
                    CASE WHEN ms.winner = ms.home_team THEN 'W' ELSE 'L' END
                ELSE 
                    CASE WHEN ms.winner = ms.away_team THEN 'W' ELSE 'L' END
            END as result
        FROM match_scores ms
        WHERE (ms.home_player_1_id = %s OR ms.home_player_2_id = %s OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s)
        ORDER BY ms.match_date DESC
        LIMIT 20
    """
    
    matches = execute_query(matches_query, [player_id] * 8)
    
    print(f"\n📊 Recent Matches ({len(matches)} found):")
    if matches:
        for match in matches:
            print(f"  {match['match_date']}: {match['home_team']} vs {match['away_team']} - {match['result']} ({match['player_side']})")
    else:
        print("  No matches found")
    
    # 3. Get user associations
    associations_query = """
        SELECT 
            upa.*,
            u.email,
            u.first_name,
            u.last_name
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        WHERE upa.tenniscores_player_id = %s
    """
    
    associations = execute_query(associations_query, [player_id])
    
    print(f"\n👤 User Associations ({len(associations)} found):")
    if associations:
        for assoc in associations:
            print(f"  User: {assoc['first_name']} {assoc['last_name']} ({assoc['email']})")
            print(f"    User ID: {assoc['user_id']}")
            print(f"    Association ID: {assoc['id']}")
    else:
        print("  No user associations found")
    
    # 4. Check for any issues
    print(f"\n🔍 Potential Issues:")
    
    # Check for multiple players with same ID
    duplicate_query = """
        SELECT COUNT(*) as count
        FROM players 
        WHERE tenniscores_player_id = %s
    """
    duplicate_count = execute_query_one(duplicate_query, [player_id])
    if duplicate_count['count'] > 1:
        print(f"  ⚠️  Multiple player records with same ID: {duplicate_count['count']}")
    
    # Check for orphaned records
    orphaned_query = """
        SELECT COUNT(*) as count
        FROM players 
        WHERE tenniscores_player_id = %s 
        AND (league_id IS NULL OR team_id IS NULL)
    """
    orphaned_count = execute_query_one(orphaned_query, [player_id])
    if orphaned_count['count'] > 0:
        print(f"  ⚠️  Orphaned player records: {orphaned_count['count']}")

if __name__ == "__main__":
    player_id = "nndz-WkMrK3didjlnUT09"
    investigate_player(player_id) 