#!/usr/bin/env python3
"""Debug script for specific player ID: nndz-WkMrK3dMMzdndz09"""

import sys
sys.path.append('.')

from database_utils import execute_query, execute_query_one

def debug_specific_player():
    """Debug the specific player ID that's not showing court assignments"""
    
    target_player_id = 'nndz-WkMrK3dMMzdndz09'
    
    print(f"🔍 DEBUGGING SPECIFIC PLAYER: {target_player_id}")
    print("=" * 70)
    
    # Step 1: Check if this player exists in the players table
    print("📋 Step 1: Checking if player exists in players table...")
    player = execute_query_one(
        "SELECT * FROM players WHERE tenniscores_player_id = %s", 
        [target_player_id]
    )
    
    if player:
        print(f"✅ Player found:")
        print(f"   ID: {player['id']}")
        print(f"   Name: {player['first_name']} {player['last_name']}")
        print(f"   Team ID: {player['team_id']}")
        print(f"   League ID: {player['league_id']}")
        print(f"   Is Active: {player['is_active']}")
    else:
        print("❌ Player not found in players table")
        return
    print()
    
    # Step 2: Check user associations for this player
    print("📋 Step 2: Checking user associations...")
    associations = execute_query("""
        SELECT upa.*, u.email, u.first_name as user_first_name, u.last_name as user_last_name
        FROM user_player_associations upa
        JOIN users u ON upa.user_id = u.id
        WHERE upa.tenniscores_player_id = %s
    """, [target_player_id])
    
    if associations:
        print(f"✅ Found {len(associations)} user associations:")
        for assoc in associations:
            print(f"   - User: {assoc['user_first_name']} {assoc['user_last_name']} ({assoc['email']})")
            print(f"     User ID: {assoc['user_id']}")
            print(f"     Is Primary: {assoc['is_primary']}")
    else:
        print("❌ No user associations found for this player")
    print()
    
    # Step 3: Check team information
    if player and player['team_id']:
        print("📋 Step 3: Checking team information...")
        team = execute_query_one(
            "SELECT * FROM teams WHERE id = %s", 
            [player['team_id']]
        )
        
        if team:
            print(f"✅ Team found:")
            print(f"   Team ID: {team['id']}")
            print(f"   Team Name: {team['team_name']}")
            print(f"   Team Alias: {team.get('team_alias', 'None')}")
            print(f"   Club ID: {team['club_id']}")
            print(f"   Series ID: {team['series_id']}")
            print(f"   League ID: {team['league_id']}")
        else:
            print("❌ Team not found")
        print()
        
        # Step 4: Check other team members
        print("📋 Step 4: Checking other team members...")
        team_members = execute_query("""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.is_active
            FROM players p
            WHERE p.team_id = %s
            ORDER BY p.first_name, p.last_name
        """, [player['team_id']])
        
        if team_members:
            print(f"✅ Found {len(team_members)} team members:")
            for i, member in enumerate(team_members, 1):
                highlight = "<<< TARGET PLAYER" if member['tenniscores_player_id'] == target_player_id else ""
                print(f"   {i:2d}. {member['first_name']} {member['last_name']} ({member['tenniscores_player_id']}) {highlight}")
        print()
    
    # Step 5: Check matches for this player
    print("📋 Step 5: Checking matches for this player...")
    matches = execute_query("""
        SELECT 
            TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
            home_team as "Home Team",
            away_team as "Away Team",
            winner as "Winner",
            home_player_1_id as "Home Player 1",
            home_player_2_id as "Home Player 2",
            away_player_1_id as "Away Player 1",
            away_player_2_id as "Away Player 2",
            league_id
        FROM match_scores
        WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
        ORDER BY match_date DESC
        LIMIT 10
    """, [target_player_id, target_player_id, target_player_id, target_player_id])
    
    if matches:
        print(f"✅ Found {len(matches)} recent matches:")
        for match in matches:
            is_home = target_player_id in [match['Home Player 1'], match['Home Player 2']]
            team = match['Home Team'] if is_home else match['Away Team']
            print(f"   - {match['Date']}: {team} (league: {match['league_id']})")
    else:
        print("❌ No matches found for this player")
    print()
    
    # Step 6: Check if this matches Ross's user session
    print("📋 Step 6: Checking against Ross's user data...")
    ross_user = execute_query_one(
        "SELECT * FROM users WHERE email = %s", 
        ['rossfreedman@gmail.com']
    )
    
    if ross_user:
        print(f"✅ Ross's user ID: {ross_user['id']}")
        
        # Check Ross's player associations
        ross_associations = execute_query("""
            SELECT upa.*, p.first_name, p.last_name, p.team_id
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE upa.user_id = %s
        """, [ross_user['id']])
        
        print(f"✅ Ross has {len(ross_associations)} player associations:")
        for assoc in ross_associations:
            match_indicator = "<<< MATCHES TARGET" if assoc['tenniscores_player_id'] == target_player_id else ""
            print(f"   - {assoc['first_name']} {assoc['last_name']} ({assoc['tenniscores_player_id']}) Team: {assoc['team_id']} {match_indicator}")
    
    print()
    print("🔍 SUMMARY:")
    print("-" * 50)
    if player:
        print(f"Player {target_player_id} exists and belongs to team {player['team_id']}")
        if associations:
            print(f"Player is associated with {len(associations)} user(s)")
        else:
            print("⚠️  Player has no user associations - this might be the issue!")
    else:
        print(f"❌ Player {target_player_id} does not exist in the database")

if __name__ == "__main__":
    debug_specific_player() 