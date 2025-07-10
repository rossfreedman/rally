#!/usr/bin/env python3
"""
Investigate Victor Forman multiple registration issue in production
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def investigate_victor_forman_issue():
    """Investigate Victor Forman multiple user registrations"""
    
    print("🔍 Investigating Victor Forman multiple registration issue...")
    
    # 1. Find all users with Victor Forman name
    users_query = """
        SELECT 
            id, email, first_name, last_name, 
            created_at, last_login, league_context
        FROM users 
        WHERE (first_name ILIKE '%victor%' AND last_name ILIKE '%forman%')
           OR email ILIKE '%victor%forman%'
        ORDER BY created_at ASC
    """
    
    victor_users = execute_query(users_query)
    print(f"\n📊 Found {len(victor_users)} Victor Forman user accounts:")
    
    for i, user in enumerate(victor_users, 1):
        print(f"\n{i}. User ID: {user['id']}")
        print(f"   Email: {user['email']}")
        print(f"   Name: {user['first_name']} {user['last_name']}")
        print(f"   Created: {user['created_at']}")
        print(f"   Last Login: {user['last_login']}")
        print(f"   League Context: {user['league_context']}")
        
        # Check associations for each user
        associations_query = """
            SELECT 
                upa.tenniscores_player_id,
                p.first_name, p.last_name,
                l.league_name, c.name as club_name, s.name as series_name
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE upa.user_id = %s
        """
        
        associations = execute_query(associations_query, [user['id']])
        print(f"   Associations: {len(associations)}")
        
        for assoc in associations:
            print(f"     - Player: {assoc['first_name']} {assoc['last_name']}")
            print(f"       ID: {assoc['tenniscores_player_id']}")
            print(f"       League: {assoc['league_name']}")
            print(f"       Club: {assoc['club_name']}")
            print(f"       Series: {assoc['series_name']}")
    
    # 2. Find all Victor Forman player records
    print(f"\n🎾 Searching for Victor Forman player records...")
    
    players_query = """
        SELECT 
            p.id, p.tenniscores_player_id, p.first_name, p.last_name,
            l.league_name, c.name as club_name, s.name as series_name,
            p.team_id, p.pti, p.wins, p.losses
        FROM players p
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN clubs c ON p.club_id = c.id  
        LEFT JOIN series s ON p.series_id = s.id
        WHERE (p.first_name ILIKE '%victor%' AND p.last_name ILIKE '%forman%')
        ORDER BY l.league_name, c.name, s.name
    """
    
    victor_players = execute_query(players_query)
    print(f"\n📊 Found {len(victor_players)} Victor Forman player records:")
    
    for i, player in enumerate(victor_players, 1):
        print(f"\n{i}. Player ID: {player['id']}")
        print(f"   TennisCore ID: {player['tenniscores_player_id']}")
        print(f"   Name: {player['first_name']} {player['last_name']}")
        print(f"   League: {player['league_name']}")
        print(f"   Club: {player['club_name']}")
        print(f"   Series: {player['series_name']}")
        print(f"   Team ID: {player['team_id']}")
        print(f"   PTI: {player['pti']}, W-L: {player['wins']}-{player['losses']}")
        
        # Check if this player is associated with any users
        player_associations_query = """
            SELECT 
                upa.user_id,
                u.email, u.first_name, u.last_name
            FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            WHERE upa.tenniscores_player_id = %s
        """
        
        player_assocs = execute_query(player_associations_query, [player['tenniscores_player_id']])
        print(f"   Associated with {len(player_assocs)} user(s):")
        
        for assoc in player_assocs:
            print(f"     - User: {assoc['email']} ({assoc['first_name']} {assoc['last_name']})")
    
    # 3. Check for duplicate player ID associations
    print(f"\n🚨 Checking for duplicate player ID associations...")
    
    duplicate_associations_query = """
        SELECT 
            upa.tenniscores_player_id,
            COUNT(*) as user_count,
            ARRAY_AGG(upa.user_id) as user_ids,
            ARRAY_AGG(u.email) as emails
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        GROUP BY upa.tenniscores_player_id
        HAVING COUNT(*) > 1
        ORDER BY user_count DESC
    """
    
    duplicates = execute_query(duplicate_associations_query)
    print(f"\nFound {len(duplicates)} player IDs with multiple user associations:")
    
    for dup in duplicates:
        print(f"\n🔴 Player ID: {dup['tenniscores_player_id']}")
        print(f"   Associated with {dup['user_count']} users:")
        
        for i, (user_id, email) in enumerate(zip(dup['user_ids'], dup['emails'])):
            print(f"     {i+1}. User ID {user_id}: {email}")
    
    # 4. Summary and recommendations
    print(f"\n📋 SUMMARY:")
    print(f"   - Victor Forman users found: {len(victor_users)}")
    print(f"   - Victor Forman players found: {len(victor_players)}")
    print(f"   - Total duplicate player associations: {len(duplicates)}")
    
    if len(victor_users) > 1:
        print(f"\n⚠️  ISSUE CONFIRMED: Multiple Victor Forman users exist")
        print(f"   This suggests the registration system allowed duplicate registrations")
        print(f"   for the same player identity.")
    
    if duplicates:
        print(f"\n🚨 CRITICAL: {len(duplicates)} player IDs have multiple user associations")
        print(f"   This violates the intended 1-player-to-1-user mapping")

if __name__ == "__main__":
    investigate_victor_forman_issue()
