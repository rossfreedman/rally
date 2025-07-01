import json
import os
from datetime import datetime

from flask import jsonify, render_template, request, session

from utils.auth import login_required
from utils.db import execute_query
from utils.logging import log_user_activity


def init_find_people_to_play_routes(app):
    # Route moved to mobile_routes.py blueprint

    @app.route("/api/debug-session")
    def debug_session():
        """Debug endpoint to show session data"""
        try:
            return jsonify(
                {
                    "session_has_user": "user" in session,
                    "session_user": session.get("user", "No user in session"),
                    "session_keys": list(session.keys()) if session else "No session",
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Route moved to api_routes.py blueprint

    # Removed duplicate /api/club-players endpoint - now handled by api_bp blueprint

    @app.route("/api/test-tennaqua-players")
    def test_tennaqua_players():
        """Test endpoint to simulate what the logged-in user should see at Tennaqua"""
        try:
            # Simulate user session data for Ross at Tennaqua, Chicago 22
            user_club = "Tennaqua"

            print(f"\n=== TESTING TENNAQUA PLAYERS ===")
            print(f"Simulating user club: '{user_club}'")

            # Load player data
            players_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "data",
                "players.json",
            )
            with open(players_path, "r") as f:
                all_players = json.load(f)

            # Debug: Show unique clubs in data and check for Tennaqua
            clubs_in_data = set()
            tennaqua_count = 0
            for player in all_players:
                clubs_in_data.add(player["Club"])
                if player["Club"] == user_club:
                    tennaqua_count += 1

            print(f"Total players in file: {len(all_players)}")
            print(f"Players with club '{user_club}': {tennaqua_count}")
            print(f"All clubs in data: {sorted(list(clubs_in_data))}")

            # Show some specific club comparisons for debugging
            user_club_lower = user_club.lower().strip()
            exact_matches = [
                club
                for club in clubs_in_data
                if club.lower().strip() == user_club_lower
            ]
            partial_matches = [
                club
                for club in clubs_in_data
                if user_club_lower in club.lower() or club.lower() in user_club_lower
            ]

            print(f"Exact club matches for '{user_club}': {exact_matches}")
            print(f"Partial club matches for '{user_club}': {partial_matches}")
            print(f"User club normalized: '{user_club_lower}'")

            # Filter players by club using the same logic as the real route
            filtered_players = []
            club_series = set()

            # Debug: Show club matching attempts
            print(
                f"Attempting to match user club '{user_club}' (normalized: '{user_club_lower}')"
            )

            for player in all_players:
                player_club = player["Club"].strip()
                player_club_lower = player_club.lower()

                # Debug: Log first few club comparisons
                if len(filtered_players) < 3:
                    print(
                        f"Comparing: player['Club']='{player_club}' (normalized: '{player_club_lower}') == user_club='{user_club}' (normalized: '{user_club_lower}') ? {player_club_lower == user_club_lower}"
                    )

                # Try multiple matching strategies:
                club_match = (
                    player_club_lower == user_club_lower
                    or user_club_lower in player_club_lower
                    or player_club_lower in user_club_lower
                )

                if club_match:
                    club_series.add(player["Series"])

                    # Add player to results (simplified version)
                    filtered_players.append(
                        {
                            "name": f"{player['First Name']} {player['Last Name']}",
                            "firstName": player["First Name"],
                            "lastName": player["Last Name"],
                            "series": player["Series"],
                            "pti": player["PTI"],
                            "wins": player["Wins"],
                            "losses": player["Losses"],
                            "winRate": player["Win %"],
                        }
                    )

            # Sort series properly (numbers before letters)
            def get_series_sort_key(series_name):
                import re
                
                # Handle series with numeric values: "Chicago 1", "Series 2", "Division 3", etc.
                match = re.match(r'^(?:(Chicago|Series|Division)\s+)?(\d+)([a-zA-Z\s]*)$', series_name)
                if match:
                    prefix = match.group(1) or ''
                    number = int(match.group(2))
                    suffix = match.group(3).strip() if match.group(3) else ''
                    
                    # Sort by: prefix priority, then number, then suffix
                    prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                    return (0, prefix_priority, number, suffix)  # Numeric series first
                
                # Handle letter-only series (Series A, Series B, etc.)
                match = re.match(r'^(?:(Chicago|Series|Division)\s+)?([A-Z]+)$', series_name)
                if match:
                    prefix = match.group(1) or ''
                    letter = match.group(2)
                    prefix_priority = {'Chicago': 0, 'Series': 1, 'Division': 2}.get(prefix, 3)
                    return (1, prefix_priority, 0, letter)  # Letters after numbers
                
                # Everything else goes last (sorted alphabetically)
                return (2, 0, 0, series_name)

            available_series_sorted = sorted(club_series, key=get_series_sort_key)

            print(f"Found {len(filtered_players)} players at {user_club}")
            print(f"Available series: {available_series_sorted}")
            print("=== END TEST ===\n")

            return jsonify(
                {
                    "total_players_found": len(filtered_players),
                    "available_series": available_series_sorted,
                    "first_10_players": filtered_players[:10],
                    "user_club": user_club,
                    "debug_info": {
                        "exact_matches": exact_matches,
                        "partial_matches": partial_matches,
                        "total_in_file": len(all_players),
                    },
                }
            )

        except Exception as e:
            print(f"\nERROR in test: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route("/api/test-club-players/<club_name>")
    def test_club_players(club_name):
        """Test endpoint to check players for a specific club"""
        try:
            # Load player data
            players_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "data",
                "players.json",
            )
            with open(players_path, "r") as f:
                all_players = json.load(f)

            # Count players at this club
            club_players = [p for p in all_players if p["Club"] == club_name]

            return jsonify(
                {
                    "club_name": club_name,
                    "players_found": len(club_players),
                    "first_5_players": club_players[:5] if club_players else [],
                    "all_unique_clubs": sorted(
                        list(set(p["Club"] for p in all_players))
                    ),
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
