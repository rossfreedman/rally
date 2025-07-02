#!/usr/bin/env python3
"""
Debug script to test why Ross Freedman's analyze-me page isn't showing data on staging
"""

import os
import sys

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def debug_ross_matches():
    """Debug Ross Freedman's match data on staging"""
    
    # From the screenshot: Ross Freedman, Tennaqua, Series 22
    print("Debugging matches for Ross Freedman...")
    print()
    
    # Test 1: Find Ross in users table
    print("=== Test 1: Ross in users table ===")
    user_query = """
        SELECT id, email, first_name, last_name, league_context
        FROM users 
        WHERE email LIKE '%ross%' OR first_name ILIKE 'ross'
    """
    users = execute_query(user_query, [])
    
    print(f"Found {len(users)} user records for Ross:")
    for user in users:
        print(f"  - {user['first_name']} {user['last_name']} ({user['email']}) - league_context: {user['league_context']}")
    print()
    
    # Test 2: Find Ross in players table
    print("=== Test 2: Ross in players table ===")
    player_query = """
        SELECT id, first_name, last_name, tenniscores_player_id, league_id, team_id, club_id, series_id
        FROM players 
        WHERE first_name ILIKE 'ross' AND last_name ILIKE '%freed%'
    """
    players = execute_query(player_query, [])
    
    print(f"Found {len(players)} player records:")
    for player in players:
        print(f"  - {player['first_name']} {player['last_name']} (player_id: {player['tenniscores_player_id']}) - league: {player['league_id']}, team: {player['team_id']}")
    print()
    
    # If we found Ross, use his data for further testing
    if players:
        ross_player = players[0]  # Use first match
        player_id = ross_player['tenniscores_player_id']
        league_id = ross_player['league_id']
        team_id = ross_player['team_id']
        
        print(f"Using Ross's data:")
        print(f"  Player ID: {player_id}")
        print(f"  League ID: {league_id}")
        print(f"  Team ID: {team_id}")
        print()
        
        # Test 3: Check matches without any filtering
        print("=== Test 3: All matches for Ross (no filtering) ===")
        all_matches_query = """
            SELECT 
                id,
                TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                home_team,
                away_team,
                league_id,
                home_team_id,
                away_team_id,
                home_player_1_id,
                home_player_2_id,
                away_player_1_id,
                away_player_2_id
            FROM match_scores
            WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
            ORDER BY match_date DESC
            LIMIT 10
        """
        all_matches = execute_query(all_matches_query, [player_id, player_id, player_id, player_id])
        
        print(f"Found {len(all_matches)} matches (no filtering):")
        for match in all_matches:
            print(f"  - {match['Date']}: {match['home_team']} vs {match['away_team']} (league: {match['league_id']})")
            print(f"    Players: H1={match['home_player_1_id'][:12]}... H2={match['home_player_2_id'][:12]}...")
            print(f"             A1={match['away_player_1_id'][:12]}... A2={match['away_player_2_id'][:12]}...")
        print()
        
        # Test 4: Check matches with league filtering
        if league_id:
            print("=== Test 4: Matches with league filtering ===")
            league_matches_query = """
                SELECT 
                    id,
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team,
                    away_team,
                    league_id
                FROM match_scores
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC
                LIMIT 10
            """
            league_matches = execute_query(league_matches_query, [player_id, player_id, player_id, player_id, league_id])
            
            print(f"Found {len(league_matches)} matches with league filtering:")
            for match in league_matches:
                print(f"  - {match['Date']}: {match['home_team']} vs {match['away_team']}")
            print()
        
        # Test 5: Check what the mobile service would do
        print("=== Test 5: Mobile service simulation ===")
        from app.services.session_service import get_session_data_for_user
        
        # Try to find Ross's email
        ross_email = None
        if users:
            for user in users:
                if 'ross' in user['first_name'].lower() and 'freed' in user['last_name'].lower():
                    ross_email = user['email']
                    break
        
        if ross_email:
            print(f"Testing session service for {ross_email}")
            session_data = get_session_data_for_user(ross_email)
            
            if session_data:
                print("Session data found:")
                print(f"  Email: {session_data.get('email')}")
                print(f"  Player ID: {session_data.get('tenniscores_player_id')}")
                print(f"  League ID: {session_data.get('league_id')}")
                print(f"  Team ID: {session_data.get('team_id')}")
                print(f"  Club: {session_data.get('club')}")
                print(f"  Series: {session_data.get('series')}")
                
                # Test mobile service
                from app.services.mobile_service import get_player_analysis
                try:
                    analysis = get_player_analysis(session_data)
                    print(f"Mobile service result:")
                    print(f"  Current season matches: {analysis.get('current_season', {}).get('matches', 'N/A')}")
                    print(f"  Current season wins: {analysis.get('current_season', {}).get('wins', 'N/A')}")
                    print(f"  Current season losses: {analysis.get('current_season', {}).get('losses', 'N/A')}")
                    print(f"  Error: {analysis.get('error', 'None')}")
                except Exception as e:
                    print(f"Mobile service error: {e}")
            else:
                print("No session data found")
        else:
            print("Could not find Ross's email")
    else:
        print("No player records found for Ross - this might be the issue!")
    
    # Test 6: Check for any Tennaqua Series 22 data
    print("=== Test 6: Tennaqua Series 22 data ===")
    tennaqua_query = """
        SELECT p.first_name, p.last_name, p.tenniscores_player_id, c.name as club, s.name as series
        FROM players p
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        WHERE c.name ILIKE '%tennaqua%' AND s.name ILIKE '%22%'
        LIMIT 10
    """
    tennaqua_players = execute_query(tennaqua_query, [])
    
    print(f"Found {len(tennaqua_players)} Tennaqua Series 22 players:")
    for player in tennaqua_players:
        print(f"  - {player['first_name']} {player['last_name']} ({player['club']} {player['series']})")
    print()

if __name__ == "__main__":
    debug_ross_matches() 