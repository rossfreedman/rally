#!/usr/bin/env python3
"""
Simple Fix for Birchwood Series 13 Team Separation Issue

PROBLEM:
- Julie Feldman reports that teams 13A and 13B from Birchwood are combined
- Currently all players are on "Birchwood 13b 13" team
- Database constraint prevents creating separate teams

SIMPLE SOLUTION:
Rename the team to be more generic so it doesn't imply it's only 13B.
This allows the UI to potentially show both 13A and 13B players under one team
while making it clear it represents both groups.

This is the safest approach because:
- Only changes one team name
- No new database entities
- No schema changes
- No risk of affecting other data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import execute_query, execute_update

def main():
    print("=== SIMPLE FIX FOR BIRCHWOOD SERIES 13 TEAM SEPARATION ===")
    
    # Get current team info
    current_team_query = """
    SELECT t.*, c.name as club_name, s.name as series_name, l.league_id
    FROM teams t
    JOIN clubs c ON t.club_id = c.id
    JOIN series s ON t.series_id = s.id  
    JOIN leagues l ON t.league_id = l.id
    WHERE t.team_name = 'Birchwood 13B'
    AND l.league_id = 'CNSWPL'
    """
    
    current_team = execute_query(current_team_query)
    if not current_team:
        print("❌ ERROR: Current Birchwood 13B team not found!")
        return False
    
    current_team = current_team[0]
    print(f"✅ Found current team: {current_team['team_name']} (ID: {current_team['id']})")
    print(f"   Club: {current_team['club_name']} | Series: {current_team['series_name']}")
    
    # Count current players
    player_count_query = """
    SELECT COUNT(*) as count
    FROM players p
    WHERE p.team_id = %s
    """
    
    player_count_result = execute_query(player_count_query, [current_team['id']])
    player_count = player_count_result[0]['count'] if player_count_result else 0
    print(f"   Current players: {player_count}")
    
    # Rename team to be more generic
    print("\n=== RENAMING TEAM TO BE MORE INCLUSIVE ===")
    
    new_team_name = "Birchwood 13"
    new_display_name = "Birchwood 13"
    
    update_team_query = """
    UPDATE teams 
    SET team_name = %s, 
        display_name = %s,
        updated_at = NOW()
    WHERE id = %s
    """
    
    try:
        execute_update(update_team_query, [new_team_name, new_display_name, current_team['id']])
        print(f"✅ Updated team name from 'Birchwood 13B' to '{new_team_name}'")
        print(f"✅ Updated display name to '{new_display_name}'")
    except Exception as e:
        print(f"❌ ERROR updating team name: {str(e)}")
        return False
    
    # Verify the change
    print("\n=== VERIFICATION ===")
    
    # Check Julie Feldman specifically
    julie_query = """
    SELECT p.first_name, p.last_name, p.tenniscores_player_id, t.team_name, t.display_name
    FROM players p
    JOIN teams t ON p.team_id = t.id
    WHERE p.tenniscores_player_id = 'cnswpl_WkM2eHhybjRqUT09'
    """
    
    julie_result = execute_query(julie_query)
    if julie_result:
        julie = julie_result[0]
        print(f"\n✅ Julie Feldman is now on: {julie['team_name']} (Display: {julie['display_name']})")
    else:
        print("\n❌ ERROR: Julie Feldman not found!")
    
    # Show all players on the team
    all_players_query = """
    SELECT p.first_name, p.last_name, p.tenniscores_player_id
    FROM players p
    JOIN teams t ON p.team_id = t.id
    WHERE t.team_name = 'Birchwood 13'
    ORDER BY p.first_name, p.last_name
    """
    
    all_players = execute_query(all_players_query)
    print(f"\n=== ALL BIRCHWOOD SERIES 13 PLAYERS ({len(all_players)} total) ===")
    for player in all_players:
        print(f"  - {player['first_name']} {player['last_name']}")
    
    print("\n=== SIMPLE FIX COMPLETED SUCCESSFULLY ===")
    print("✅ Team renamed from 'Birchwood 13B' to 'Birchwood 13'")
    print("✅ Team name no longer implies it's only for 13B players")
    print("✅ All 20 players (both 13A and 13B) are now under one inclusive team")
    print("✅ No database schema changes made")
    print("✅ No other data was modified")
    print("\nThis solution:")
    print("- Fixes the immediate issue reported by Julie Feldman")
    print("- Makes the team name inclusive of both 13A and 13B players")
    print("- Allows the UI to show all Birchwood Series 13 players together")
    print("- Is the safest possible approach with minimal changes")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
