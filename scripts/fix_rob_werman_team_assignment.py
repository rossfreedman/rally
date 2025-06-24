#!/usr/bin/env python3
"""
Fix Rob Werman's team assignment based on match participation

Based on the analysis, Rob Werman should be on "Tennaqua S2A" team
instead of "Tennaqua S1" since his matches show him playing for S2A.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def fix_rob_werman_team():
    """Fix Rob Werman's team assignment based on match analysis"""
    print("=" * 80)
    print("FIXING ROB WERMAN'S TEAM ASSIGNMENT")
    print("=" * 80)
    
    rob_player_id = "nndz-WlNld3g3bnhoQT09"
    current_team_id = 12340  # Tennaqua S1
    correct_team_id = 12344  # Tennaqua S2A
    
    print(f"Player: Rob Werman ({rob_player_id})")
    print(f"Current Team: Tennaqua S1 (ID: {current_team_id})")
    print(f"Target Team: Tennaqua S2A (ID: {correct_team_id})")
    print()
    
    # Step 1: Verify current state
    print("1. Verifying current state...")
    
    current_player = execute_query_one(
        "SELECT id, first_name, last_name, team_id FROM players WHERE tenniscores_player_id = %s", 
        [rob_player_id]
    )
    
    if not current_player:
        print("❌ Player not found!")
        return False
    
    print(f"✅ Found: {current_player['first_name']} {current_player['last_name']}")
    print(f"   Current Team ID: {current_player['team_id']}")
    
    if current_player['team_id'] != current_team_id:
        print(f"⚠️  Warning: Expected team {current_team_id}, found {current_player['team_id']}")
    
    # Step 2: Verify target team exists
    print("\n2. Verifying target team...")
    
    target_team = execute_query_one(
        "SELECT id, team_name, team_alias FROM teams WHERE id = %s", 
        [correct_team_id]
    )
    
    if not target_team:
        print("❌ Target team not found!")
        return False
    
    print(f"✅ Target team: {target_team['team_name']} / {target_team['team_alias']}")
    
    # Step 3: Check current players on target team
    current_s2a_players = execute_query(
        "SELECT first_name, last_name FROM players WHERE team_id = %s AND is_active = TRUE", 
        [correct_team_id]
    )
    
    print(f"   Current players on S2A: {len(current_s2a_players)}")
    for player in current_s2a_players:
        print(f"     - {player['first_name']} {player['last_name']}")
    
    # Step 4: Look for other players who should also be moved
    print("\n3. Finding other players who should be on S2A team...")
    
    # Get players who have played WITH Rob in S2A matches
    s2a_match_players_query = """
        SELECT DISTINCT 
            CASE 
                WHEN home_player_1_id != %s THEN home_player_1_id
                WHEN home_player_2_id != %s THEN home_player_2_id
                WHEN away_player_1_id != %s THEN away_player_1_id
                WHEN away_player_2_id != %s THEN away_player_2_id
            END as partner_id
        FROM match_scores 
        WHERE (home_team = 'Tennaqua S2A' OR away_team = 'Tennaqua S2A')
        AND (home_player_1_id = %s OR home_player_2_id = %s 
             OR away_player_1_id = %s OR away_player_2_id = %s)
        AND league_id = 4492
    """
    
    partner_ids = execute_query(s2a_match_players_query, [
        rob_player_id, rob_player_id, rob_player_id, rob_player_id,
        rob_player_id, rob_player_id, rob_player_id, rob_player_id
    ])
    
    potential_teammates = []
    for partner in partner_ids:
        if partner['partner_id']:
            player_info = execute_query_one(
                "SELECT id, first_name, last_name, team_id, tenniscores_player_id FROM players WHERE tenniscores_player_id = %s",
                [partner['partner_id']]
            )
            if player_info:
                potential_teammates.append(player_info)
    
    print(f"✅ Found {len(potential_teammates)} potential S2A teammates:")
    for teammate in potential_teammates:
        current_team_name = "Unknown"
        team_info = execute_query_one("SELECT team_name FROM teams WHERE id = %s", [teammate['team_id']])
        if team_info:
            current_team_name = team_info['team_name']
        
        print(f"   - {teammate['first_name']} {teammate['last_name']}")
        print(f"     Current team: {current_team_name} (ID: {teammate['team_id']})")
        print(f"     Player ID: {teammate['tenniscores_player_id']}")
    
    # Step 5: Ask for confirmation and perform the update
    print(f"\n4. Proposed changes:")
    print(f"   - Move Rob Werman from 'Tennaqua S1' to 'Tennaqua S2A'")
    for teammate in potential_teammates:
        if teammate['team_id'] != correct_team_id:
            team_info = execute_query_one("SELECT team_name FROM teams WHERE id = %s", [teammate['team_id']])
            current_team_name = team_info['team_name'] if team_info else "Unknown"
            print(f"   - Move {teammate['first_name']} {teammate['last_name']} from '{current_team_name}' to 'Tennaqua S2A'")
    
    response = input("\nProceed with these changes? (yes/no): ").lower().strip()
    
    if response in ['yes', 'y']:
        print("\n5. Executing changes...")
        
        # Update Rob's team
        try:
            execute_query(
                "UPDATE players SET team_id = %s WHERE tenniscores_player_id = %s",
                [correct_team_id, rob_player_id]
            )
            print(f"✅ Updated Rob Werman's team assignment")
        except Exception as e:
            print(f"❌ Error updating Rob: {e}")
            return False
        
        # Update teammates
        for teammate in potential_teammates:
            if teammate['team_id'] != correct_team_id:
                try:
                    execute_query(
                        "UPDATE players SET team_id = %s WHERE tenniscores_player_id = %s",
                        [correct_team_id, teammate['tenniscores_player_id']]
                    )
                    print(f"✅ Updated {teammate['first_name']} {teammate['last_name']}'s team assignment")
                except Exception as e:
                    print(f"❌ Error updating {teammate['first_name']} {teammate['last_name']}: {e}")
        
        print("\n✅ Team assignment fixes completed!")
        print("Rob Werman should now see all his actual teammates in the track-byes-courts page.")
        
    else:
        print("\n❌ Changes cancelled.")
    
    return True

if __name__ == "__main__":
    fix_rob_werman_team() 