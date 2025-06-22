#!/usr/bin/env python3
"""Debug script to check player data for nndz-WkMrK3didjlnUT09"""

from database_utils import execute_query


def main():
    player_id = "nndz-WkMrK3didjlnUT09"

    print(f"=== DEBUGGING PLAYER ID: {player_id} ===")
    print()

    # Check if this player exists in the players table
    players = execute_query(
        "SELECT * FROM players WHERE tenniscores_player_id = %s", [player_id]
    )
    print("=== PLAYERS TABLE ===")
    if players:
        for player in players:
            print(
                f"ID: {player['id']}, Name: {player['first_name']} {player['last_name']}, League ID: {player.get('league_id', 'N/A')}"
            )
    else:
        print("No players found with this ID")
    print()

    # Check if this player exists in match_scores
    matches = execute_query(
        "SELECT COUNT(*) as match_count FROM match_scores WHERE home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s",
        [player_id, player_id, player_id, player_id],
    )
    print("=== MATCH COUNT ===")
    print(
        f'Player {player_id} has {matches[0]["match_count"]} matches in match_scores table'
    )
    print()

    # Check if this player exists in the users table
    users = execute_query(
        "SELECT * FROM users WHERE tenniscores_player_id = %s", [player_id]
    )
    print("=== USERS TABLE ===")
    if users:
        for user in users:
            print(
                f'ID: {user["id"]}, Name: {user["first_name"]} {user["last_name"]}, Email: {user["email"]}, Player ID: {user["tenniscores_player_id"]}'
            )
    else:
        print("No users found with this player ID")
    print()

    # Check Ross Freedman's user record
    ross_users = execute_query(
        "SELECT * FROM users WHERE email = %s", ["rossfreedman@gmail.com"]
    )
    print("=== ROSS USER DATA ===")
    if ross_users:
        for user in ross_users:
            print(
                f'ID: {user["id"]}, Name: {user["first_name"]} {user["last_name"]}, Email: {user["email"]}, Player ID: {user["tenniscores_player_id"]}'
            )
    else:
        print("No user found with rossfreedman@gmail.com")
    print()

    # Check player data with league information
    player_with_league = execute_query(
        """
        SELECT p.*, l.league_name, l.league_id as league_identifier, 
               c.name as club_name, s.name as series_name
        FROM players p
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        WHERE p.tenniscores_player_id = %s
    """,
        [player_id],
    )
    print("=== PLAYER WITH LEAGUE DATA ===")
    if player_with_league:
        for player in player_with_league:
            print(f"Player ID: {player['tenniscores_player_id']}")
            print(f"Name: {player['first_name']} {player['last_name']}")
            print(f"League: {player['league_name']} ({player['league_identifier']})")
            print(f"Club: {player['club_name']}")
            print(f"Series: {player['series_name']}")
            print(f"Active: {player.get('is_active', 'N/A')}")
            print(f"PTI: {player.get('pti', 'N/A')}")
            print(f"Wins: {player.get('wins', 'N/A')}")
            print(f"Losses: {player.get('losses', 'N/A')}")
            print()
    else:
        print("No player records found with this player ID in the current schema")


if __name__ == "__main__":
    main()
