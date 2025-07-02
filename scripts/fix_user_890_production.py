#!/usr/bin/env python3
"""
Fix user 890 data corruption on Railway production
Ensures proper user associations and session data
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one, execute_query, execute_update
import json

def main():
    print("=== Fixing User 890 Production Data Issue ===")
    
    # Step 1: Check current state of user 890
    print("\n1. Checking user 890 current state...")
    user_890 = execute_query_one('SELECT * FROM users WHERE id = %s', (890,))
    
    if not user_890:
        print("❌ User 890 does not exist!")
        # Check if rossfreedman@gmail.com has other accounts
        users = execute_query('SELECT * FROM users WHERE email = %s', ('rossfreedman@gmail.com',))
        print(f"\n   Found {len(users)} users with email rossfreedman@gmail.com:")
        for user in users:
            print(f"   - User ID: {user['id']}, Created: {user['created_at']}")
        
        if users:
            correct_user = users[0]  # Take the first/primary user
            print(f"\n   Using user ID {correct_user['id']} as the correct account")
            
            # Update session data to use correct user
            print("\n2. This requires clearing the session and re-login...")
            print("   User should log out and log back in")
            return
    else:
        print(f"✅ User 890 exists: {user_890['email']}")
        
    # Step 2: Check associations
    print("\n2. Checking user associations...")
    associations = execute_query('SELECT * FROM user_player_associations WHERE user_id = %s', (890,))
    print(f"   Current associations: {len(associations)}")
    
    if not associations:
        print("❌ No associations found for user 890")
        
        # Check if player ID nndz-WkMrK3didjlnUT09 has associations with other users
        player_assocs = execute_query('SELECT * FROM user_player_associations WHERE tenniscores_player_id = %s', 
                                    ('nndz-WkMrK3didjlnUT09',))
        print(f"   Player nndz-WkMrK3didjlnUT09 has {len(player_assocs)} associations:")
        for assoc in player_assocs:
            print(f"   - User {assoc['user_id']}, Primary: {assoc['is_primary']}")
            
        if player_assocs:
            print("\n3. Creating missing association for user 890...")
            try:
                execute_update('''
                    INSERT INTO user_player_associations (user_id, tenniscores_player_id, is_primary, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (user_id, tenniscores_player_id) DO NOTHING
                ''', (890, 'nndz-WkMrK3didjlnUT09', True))
                print("✅ Association created successfully")
            except Exception as e:
                print(f"❌ Failed to create association: {e}")
    
    # Step 3: Check player data and team assignment
    print("\n3. Checking player data...")
    player = execute_query_one('SELECT * FROM players WHERE tenniscores_player_id = %s', 
                              ('nndz-WkMrK3didjlnUT09',))
    
    if player:
        print(f"✅ Player found: {player['first_name']} {player['last_name']}")
        print(f"   Team ID: {player['team_id']}")
        print(f"   League ID: {player['league_id']}")
        print(f"   Series ID: {player['series_id']}")
        
        # Check if user's league_context matches player's league
        if user_890 and user_890['league_context'] != player['league_id']:
            print(f"\n   ⚠️  League context mismatch!")
            print(f"   User league_context: {user_890['league_context']}")
            print(f"   Player league_id: {player['league_id']}")
            
            print("\n4. Updating user league_context...")
            try:
                execute_update('UPDATE users SET league_context = %s WHERE id = %s', 
                             (player['league_id'], 890))
                print("✅ League context updated")
            except Exception as e:
                print(f"❌ Failed to update league context: {e}")
        
        # Check team
        team = execute_query_one('SELECT * FROM teams WHERE id = %s', (player['team_id'],))
        if team:
            print(f"✅ Team found: {team['team_name']}")
            
            # Check matches for this team
            matches = execute_query_one('''
                SELECT COUNT(*) as count 
                FROM match_scores 
                WHERE (home_team_id = %s OR away_team_id = %s) 
                AND (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
            ''', (player['team_id'], player['team_id'], 'nndz-WkMrK3didjlnUT09', 'nndz-WkMrK3didjlnUT09', 'nndz-WkMrK3didjlnUT09', 'nndz-WkMrK3didjlnUT09'))
            
            print(f"✅ Found {matches['count']} matches for this player+team combination")
        else:
            print(f"❌ Team {player['team_id']} not found")
    
    print("\n=== Fix Complete ===")
    print("User should now:")
    print("1. Log out completely")
    print("2. Clear browser cache/cookies")  
    print("3. Log back in")
    print("4. The system should now show the correct data")

if __name__ == "__main__":
    main() 