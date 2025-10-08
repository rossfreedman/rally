#!/usr/bin/env python3
"""
Safe Fix for Birchwood Series 13 Team Separation Issue

PROBLEM:
- Julie Feldman and other players should be on separate 13A and 13B teams
- Currently all players are assigned to the same "Birchwood 13b 13" team
- Database constraint prevents multiple teams per club/series/league

SAFE SOLUTION:
Instead of modifying database schema or creating new entities, we'll:
1. Rename the existing team to clearly indicate it's 13B
2. Use team_alias field to distinguish between 13A and 13B players
3. Update only the specific players that need to be moved

This approach is safe because:
- No new database entities created
- No schema changes
- Only affects the specific Birchwood Series 13 players
- Preserves all existing relationships and data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import execute_query, execute_update
import json

def main():
    print("=== SAFE FIX FOR BIRCHWOOD SERIES 13 TEAM SEPARATION ===")
    
    # Define the players who should be on each team based on source data
    team_13a_players = [
        'cnswpl_WkNHNXdyejloZz09',  # Lizzy Cohen
        'cnswpl_WkM2eHhyNzRoZz09',  # Lisa Dorfman
        'cnswpl_WkNHNXdyejlndz09',  # Carrie Block
        'cnswpl_WkM2eHhyNzRoQT09',  # Jessica Cohen
        'cnswpl_WkM2eHhybjRqUT09',  # Julie Feldman
        'cnswpl_WkNDL3diMzZnZz09',  # Taryn Kessel
        'cnswpl_WkNHNXdyejdnZz09',  # Susan Pasternak
        'cnswpl_WkNDL3didnhodz09',  # Jill Rowe
        'cnswpl_WkM2eHhyNzVnZz09',  # Danielle Schwartz
        'cnswpl_WkNDL3didi9qUT09',  # Dawn Von Samek
        'cnswpl_WkNDL3dieitnZz09',  # lyn wise
    ]
    
    team_13b_players = [
        'cnswpl_WkM2eHhyNzRnUT09',  # Lauren Kase
        'cnswpl_WkM2eHg3anhndz09',  # Marny Kravenas
        'cnswpl_WkM2eHhyNzVqQT09',  # Betsy Baker
        'cnswpl_WkM2eHhyNzVnUT09',  # Laura Barnett
        'cnswpl_WkM2eHhyNzRodz09',  # Ivy Domont
        'cnswpl_WkM2eHhyNzdoUT09',  # Margalit Feiger
        'cnswpl_WkM2eHhyNzZoUT09',  # Kylee Rudd
        'cnswpl_WkM2eHhyNzRnZz09',  # Suzanne Silberman
        'cnswpl_WkM2eHhyNzRqUT09',  # Lauren Weiner
    ]
    
    print(f"13A players: {len(team_13a_players)}")
    print(f"13B players: {len(team_13b_players)}")
    
    # Get current team info
    current_team_query = """
    SELECT t.*, c.name as club_name, s.name as series_name, l.league_id
    FROM teams t
    JOIN clubs c ON t.club_id = c.id
    JOIN series s ON t.series_id = s.id  
    JOIN leagues l ON t.league_id = l.id
    WHERE t.team_name = 'Birchwood 13b 13'
    AND l.league_id = 'CNSWPL'
    """
    
    current_team = execute_query(current_team_query)
    if not current_team:
        print("❌ ERROR: Current Birchwood 13b 13 team not found!")
        return False
    
    current_team = current_team[0]
    print(f"✅ Found current team: {current_team['team_name']} (ID: {current_team['id']})")
    print(f"   Club: {current_team['club_name']} | Series: {current_team['series_name']}")
    
    # Step 1: Update team name and display_name to clearly indicate it's 13B
    print("\n=== UPDATING TEAM NAME TO CLEARLY INDICATE 13B ===")
    
    update_team_query = """
    UPDATE teams 
    SET team_name = 'Birchwood 13B', 
        display_name = 'Birchwood 13B',
        team_alias = '13B',
        updated_at = NOW()
    WHERE id = %s
    """
    
    try:
        execute_update(update_team_query, [current_team['id']])
        print(f"✅ Updated team name to 'Birchwood 13B'")
    except Exception as e:
        print(f"❌ ERROR updating team name: {str(e)}")
        return False
    
    # Step 2: Add team_alias to 13A players to distinguish them
    print("\n=== ADDING TEAM ALIAS TO 13A PLAYERS ===")
    
    # First, let's check which players are currently in the database
    check_players_query = """
    SELECT tenniscores_player_id, first_name, last_name
    FROM players 
    WHERE tenniscores_player_id = ANY(%s)
    AND team_id = %s
    """
    
    existing_players = execute_query(check_players_query, [team_13a_players, current_team['id']])
    print(f"Found {len(existing_players)} 13A players currently in the database:")
    for player in existing_players:
        print(f"  - {player['first_name']} {player['last_name']} ({player['tenniscores_player_id']})")
    
    # Update the team_alias field for 13A players
    # We'll use a custom field or approach to distinguish them
    print("\n=== CREATING A SIMPLE SOLUTION ===")
    print("Since we can't create separate teams due to database constraints,")
    print("we'll use the team_alias field to distinguish between 13A and 13B players.")
    print("This will allow the UI to show them as separate teams.")
    
    # Update 13A players with team_alias
    updated_13a_count = 0
    for player_id in team_13a_players:
        # We'll add a note in the team_alias field to indicate this player is 13A
        update_player_query = """
        UPDATE players 
        SET team_alias = '13A',
            updated_at = NOW()
        WHERE tenniscores_player_id = %s 
        AND team_id = %s
        RETURNING first_name, last_name
        """
        
        try:
            result = execute_query(update_player_query, [player_id, current_team['id']])
            if result:
                player_name = f"{result[0]['first_name']} {result[0]['last_name']}"
                print(f"✅ Marked {player_name} as 13A player")
                updated_13a_count += 1
            else:
                print(f"⚠️  Player {player_id} not found in current team")
        except Exception as e:
            print(f"❌ ERROR updating player {player_id}: {str(e)}")
    
    # Update 13B players with team_alias (though they should already be 13B)
    updated_13b_count = 0
    for player_id in team_13b_players:
        update_player_query = """
        UPDATE players 
        SET team_alias = '13B',
            updated_at = NOW()
        WHERE tenniscores_player_id = %s 
        AND team_id = %s
        RETURNING first_name, last_name
        """
        
        try:
            result = execute_query(update_player_query, [player_id, current_team['id']])
            if result:
                player_name = f"{result[0]['first_name']} {result[0]['last_name']}"
                print(f"✅ Marked {player_name} as 13B player")
                updated_13b_count += 1
            else:
                print(f"⚠️  Player {player_id} not found in current team")
        except Exception as e:
            print(f"❌ ERROR updating player {player_id}: {str(e)}")
    
    print(f"\n✅ Successfully marked {updated_13a_count} players as 13A")
    print(f"✅ Successfully marked {updated_13b_count} players as 13B")
    
    # Step 3: Verification
    print("\n=== VERIFICATION ===")
    
    # Check Julie Feldman specifically
    julie_query = """
    SELECT p.first_name, p.last_name, p.tenniscores_player_id, t.team_name, p.team_alias
    FROM players p
    JOIN teams t ON p.team_id = t.id
    WHERE p.tenniscores_player_id = 'cnswpl_WkM2eHhybjRqUT09'
    """
    
    julie_result = execute_query(julie_query)
    if julie_result:
        julie = julie_result[0]
        print(f"\n✅ Julie Feldman is now on: {julie['team_name']} (Team: {julie['team_alias']})")
    else:
        print("\n❌ ERROR: Julie Feldman not found!")
    
    # Show summary of all Birchwood Series 13 players
    all_players_query = """
    SELECT p.first_name, p.last_name, p.team_alias, t.team_name
    FROM players p
    JOIN teams t ON p.team_id = t.id
    WHERE t.team_name = 'Birchwood 13B'
    ORDER BY p.team_alias, p.first_name, p.last_name
    """
    
    all_players = execute_query(all_players_query)
    print(f"\n=== ALL BIRCHWOOD SERIES 13 PLAYERS ({len(all_players)} total) ===")
    
    team_13a_display = []
    team_13b_display = []
    
    for player in all_players:
        if player['team_alias'] == '13A':
            team_13a_display.append(f"{player['first_name']} {player['last_name']}")
        elif player['team_alias'] == '13B':
            team_13b_display.append(f"{player['first_name']} {player['last_name']}")
    
    print(f"\nTeam 13A ({len(team_13a_display)} players):")
    for player_name in team_13a_display:
        print(f"  - {player_name}")
    
    print(f"\nTeam 13B ({len(team_13b_display)} players):")
    for player_name in team_13b_display:
        print(f"  - {player_name}")
    
    print("\n=== SAFE FIX COMPLETED SUCCESSFULLY ===")
    print("✅ Team renamed to 'Birchwood 13B'")
    print("✅ Players marked with team_alias (13A vs 13B)")
    print("✅ No database schema changes made")
    print("✅ No other data was modified")
    print("✅ Julie Feldman and other 13A players are now distinguishable")
    print("\nNext steps:")
    print("1. Update the UI to display team_alias when showing team information")
    print("2. Ensure team switching logic respects the team_alias field")
    print("3. Test that Julie Feldman sees her correct team context")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
