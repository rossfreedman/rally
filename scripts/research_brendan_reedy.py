#!/usr/bin/env python3
"""
Deep dive research on Brendan Reedy to understand the duplicate player ID issue
"""

import sys
import os
sys.path.append(os.getcwd())

from database_utils import execute_query, execute_query_one

def main():
    print("=== Deep Research: Brendan Reedy ===\n")
    
    # 1. Find all Brendan Reedy records in players table
    print("1. All Brendan Reedy records in players table:")
    all_brendan = execute_query("""
        SELECT 
            id,
            first_name,
            last_name,
            tenniscores_player_id,
            team_id,
            league_id,
            club_id,
            series_id,
            is_active,
            captain_status,
            pti
        FROM players
        WHERE first_name = 'Brendan' AND last_name = 'Reedy'
        ORDER BY id
    """)
    
    print(f"   Found {len(all_brendan)} Brendan Reedy record(s):\n")
    
    for i, player in enumerate(all_brendan, 1):
        print(f"   Record {i}:")
        print(f"   - DB ID: {player['id']}")
        print(f"   - tenniscores_player_id: {player['tenniscores_player_id']}")
        print(f"   - Team ID: {player['team_id']}")
        print(f"   - League ID: {player['league_id']}")
        print(f"   - Club ID: {player['club_id']}")
        print(f"   - Series ID: {player['series_id']}")
        print(f"   - Is Active: {player['is_active']}")
        print(f"   - Captain: {player['captain_status']}")
        print(f"   - PTI: {player['pti']}")
        
        # Get team details
        if player['team_id']:
            team = execute_query_one("""
                SELECT t.team_name, c.name as club, s.name as series, l.league_id as league
                FROM teams t
                LEFT JOIN clubs c ON t.club_id = c.id
                LEFT JOIN series s ON t.series_id = s.id
                LEFT JOIN leagues l ON t.league_id = l.id
                WHERE t.id = %s
            """, [player['team_id']])
            
            if team:
                print(f"   - Team: {team['team_name']}")
                print(f"   - Club: {team['club']}")
                print(f"   - Series: {team['series']}")
                print(f"   - League: {team['league']}")
        print()
    
    # 2. Check matches for each player ID
    print("\n2. Match history for each player ID:\n")
    
    player_ids = [p['tenniscores_player_id'] for p in all_brendan]
    
    for player_id in player_ids:
        matches = execute_query("""
            SELECT 
                id,
                TO_CHAR(match_date, 'DD-Mon-YY') as date,
                home_team,
                away_team,
                home_team_id,
                away_team_id,
                home_player_1_id,
                home_player_2_id,
                away_player_1_id,
                away_player_2_id,
                winner,
                tenniscores_match_id
            FROM match_scores
            WHERE home_player_1_id = %s 
               OR home_player_2_id = %s 
               OR away_player_1_id = %s 
               OR away_player_2_id = %s
            ORDER BY match_date DESC
        """, [player_id, player_id, player_id, player_id])
        
        print(f"   Player ID: {player_id}")
        print(f"   - Total matches: {len(matches)}")
        
        if matches:
            print(f"   - Match details:")
            for match in matches:
                # Determine which position Brendan played
                position = None
                if match['home_player_1_id'] == player_id:
                    position = "Home Player 1"
                    partner = match['home_player_2_id']
                    team_id = match['home_team_id']
                elif match['home_player_2_id'] == player_id:
                    position = "Home Player 2"
                    partner = match['home_player_1_id']
                    team_id = match['home_team_id']
                elif match['away_player_1_id'] == player_id:
                    position = "Away Player 1"
                    partner = match['away_player_2_id']
                    team_id = match['away_team_id']
                elif match['away_player_2_id'] == player_id:
                    position = "Away Player 2"
                    partner = match['away_player_1_id']
                    team_id = match['away_team_id']
                
                # Get partner name
                partner_name = "Unknown"
                if partner:
                    partner_record = execute_query_one("""
                        SELECT first_name, last_name 
                        FROM players 
                        WHERE tenniscores_player_id = %s
                        LIMIT 1
                    """, [partner])
                    if partner_record:
                        partner_name = f"{partner_record['first_name']} {partner_record['last_name']}"
                
                print(f"     * {match['date']}: {match['home_team']} vs {match['away_team']}")
                print(f"       Team ID: {team_id}, Position: {position}, Partner: {partner_name}")
                print(f"       Winner: {match['winner']}, Match ID: {match['tenniscores_match_id']}")
        print()
    
    # 3. Check if there's a pattern - are these different teams or same team?
    print("\n3. Analysis:\n")
    
    if len(all_brendan) > 1:
        teams = set([p['team_id'] for p in all_brendan])
        print(f"   Brendan Reedy appears on {len(teams)} different team(s): {teams}")
        
        # Check if both IDs have the same team
        if len(teams) == 1:
            print(f"   ⚠️  DUPLICATE: Multiple player records for the SAME team!")
            print(f"   This is a data integrity issue - should be merged")
        else:
            print(f"   Different teams - might be legitimate if he switched teams")
    
    # 4. Check which ID is used in team roster vs match data
    print("\n4. Usage Analysis:")
    
    for player in all_brendan:
        player_id = player['tenniscores_player_id']
        team_id = player['team_id']
        
        # Check if this ID appears in match data for this team
        team_matches = execute_query_one("""
            SELECT COUNT(*) as match_count
            FROM match_scores
            WHERE (home_team_id = %s OR away_team_id = %s)
            AND (home_player_1_id = %s OR home_player_2_id = %s 
                 OR away_player_1_id = %s OR away_player_2_id = %s)
        """, [team_id, team_id, player_id, player_id, player_id, player_id])
        
        print(f"\n   Player ID: {player_id}")
        print(f"   - Listed on team {team_id} roster: YES")
        print(f"   - Appears in team {team_id} match data: {team_matches['match_count']} matches")
        
        if team_matches['match_count'] == 0:
            print(f"   - ⚠️  GHOST RECORD: In roster but NO match history")
        else:
            print(f"   - ✅ ACTIVE RECORD: Has actual match data")

if __name__ == "__main__":
    main()

