import json
import os
import re
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import unquote

from flask import (
    Blueprint,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from utils.auth import login_required
from utils.logging import log_user_activity
from utils.series_matcher import normalize_series_for_storage, series_match

# Create Blueprint
player_bp = Blueprint("player", __name__)


@player_bp.route("/api/players")
@login_required
def get_players_by_series():
    """Get all players for a specific series, optionally filtered by team and club"""
    try:
        from app.services.player_service import get_players_by_league_and_series

        # Get series and optional team from query parameters
        series = request.args.get("series")
        team_id = request.args.get("team_id")

        if not series:
            return jsonify({"error": "Series parameter is required"}), 400

        print(f"\n=== DEBUG: get_players_by_series (DATABASE) ===")
        print(f"Requested series: {series}")
        print(f"Requested team: {team_id}")
        print(f"User series: {session['user'].get('series')}")
        print(f"User club: {session['user'].get('club')}")
        print(f"User league: {session['user'].get('league_id')}")

        # Get user information
        user_league_id = session["user"].get("league_id", "")
        user_club = session["user"].get("club")

        # Get players from database using new multi-league schema
        all_players = get_players_by_league_and_series(
            league_id=user_league_id, series_name=series, club_name=user_club
        )

        # Handle team filtering if requested
        team_players = set()
        if team_id:
            # Load matches data for team filtering (still from JSON for now)
            try:
                app_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                if user_league_id and not user_league_id.startswith("APTA"):
                    matches_path = os.path.join(
                        app_dir, "data", "leagues", user_league_id, "match_history.json"
                    )
                else:
                    matches_path = os.path.join(
                        app_dir, "data", "leagues", "all", "match_history.json"
                    )

                if os.path.exists(matches_path):
                    with open(matches_path, "r") as f:
                        matches = json.load(f)

                    # Get all players who have played for this team
                    for match in matches:
                        match_league_id = match.get("league_id")
                        if user_league_id.startswith("APTA"):
                            if match_league_id != user_league_id:
                                continue
                        else:
                            if match_league_id != user_league_id:
                                continue

                        if match["Home Team"] == team_id:
                            team_players.add(match["Home Player 1"])
                            team_players.add(match["Home Player 2"])
                        elif match["Away Team"] == team_id:
                            team_players.add(match["Away Player 1"])
                            team_players.add(match["Away Player 2"])
            except Exception as e:
                print(
                    f"Warning: Error loading matches data for team filtering: {str(e)}"
                )
                team_id = None  # Continue without team filtering

        # Filter by team if specified (database stats are already included)
        final_players = []
        if team_id and team_players:
            # Filter players to only those on the team
            for player in all_players:
                if player["name"] in team_players:
                    final_players.append(player)
        else:
            # Return all players with their database stats
            final_players = all_players

        print(
            f"Found {len(final_players)} players in {series}{' for team ' + team_id if team_id else ''} and club {user_club}"
        )
        print("=== END DEBUG ===\n")
        return jsonify(final_players)

    except Exception as e:
        series_param = request.args.get("series", "unknown")
        print(f"\nERROR getting players for series {series_param}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@player_bp.route("/api/team-players/<team_id>")
@login_required
def get_team_players(team_id):
    """Get all players for a specific team"""
    try:
        app_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        user_league_id = session["user"].get("league_id", "")

        # Load player PTI data from JSON with dynamic path
        if user_league_id and not user_league_id.startswith("APTA"):
            # For non-APTA leagues, use league-specific path
            players_path = os.path.join(
                app_dir, "data", "leagues", user_league_id, "players.json"
            )
        else:
            # For APTA leagues, use the main players file
            players_path = os.path.join(
                app_dir, "data", "leagues", "all", "players.json"
            )

        with open(players_path, "r") as f:
            all_players = json.load(f)

        pti_dict = {}
        for player in all_players:
            # Check league filtering for PTI data
            player_league = player.get("League", player.get("league_id"))
            if user_league_id.startswith("APTA"):
                # For APTA users, only include players from the same APTA league
                if player_league != user_league_id:
                    continue
            else:
                # For other leagues, match the league_id
                if player_league != user_league_id:
                    continue

            player_name = f"{player['Last Name']} {player['First Name']}"
            pti_dict[player_name] = float(player["PTI"])

        # Use dynamic path for matches
        if user_league_id and not user_league_id.startswith("APTA"):
            matches_path = os.path.join(
                app_dir, "data", "leagues", user_league_id, "match_history.json"
            )
        else:
            matches_path = os.path.join(
                app_dir, "data", "leagues", "all", "match_history.json"
            )

        with open(matches_path, "r") as f:
            matches = json.load(f)

        # Track unique players and their stats
        players = {}

        # Group matches by date to determine court numbers
        date_matches = {}
        for match in matches:
            # Add league filtering for matches
            match_league_id = match.get("league_id")
            if user_league_id.startswith("APTA"):
                # For APTA users, match exact APTA league ID
                if match_league_id != user_league_id:
                    continue
            else:
                # For other leagues, match the league_id
                if match_league_id != user_league_id:
                    continue

            if match["Home Team"] == team_id or match["Away Team"] == team_id:
                date = match["Date"]
                if date not in date_matches:
                    date_matches[date] = []
                date_matches[date].append(match)

        # Sort dates and assign court numbers
        sorted_dates = sorted(date_matches.keys())

        for date in sorted_dates:
            day_matches = date_matches[date]
            # Sort by time if available, otherwise use original order
            day_matches.sort(key=lambda m: m.get("Time", ""))

            for court_idx, match in enumerate(day_matches):
                court_num = (court_idx % 4) + 1  # Courts 1-4

                # Determine if team was home or away
                is_home = match["Home Team"] == team_id
                player1 = match["Home Player 1"] if is_home else match["Away Player 1"]
                player2 = match["Home Player 2"] if is_home else match["Away Player 2"]

                # Skip if players are missing
                if not player1 or not player2:
                    continue

                # Determine if team won
                winner_is_home = match.get("Winner") == "home"
                team_won = (is_home and winner_is_home) or (
                    not is_home and not winner_is_home
                )

                # Track stats for each player
                for player_name in [player1, player2]:
                    if player_name not in players:
                        players[player_name] = {
                            "name": player_name,
                            "matches": 0,
                            "wins": 0,
                            "courts": {
                                "Court 1": {"matches": 0, "wins": 0},
                                "Court 2": {"matches": 0, "wins": 0},
                                "Court 3": {"matches": 0, "wins": 0},
                                "Court 4": {"matches": 0, "wins": 0},
                            },
                            "partners": {},
                            "pti": pti_dict.get(player_name, 0.0),
                        }

                    player_stats = players[player_name]
                    player_stats["matches"] += 1

                    if team_won:
                        player_stats["wins"] += 1

                    # Court stats
                    court_name = f"Court {court_num}"
                    player_stats["courts"][court_name]["matches"] += 1
                    if team_won:
                        player_stats["courts"][court_name]["wins"] += 1

                    # Partner stats
                    partner = player2 if player_name == player1 else player1
                    if partner not in player_stats["partners"]:
                        player_stats["partners"][partner] = {"matches": 0, "wins": 0}
                    player_stats["partners"][partner]["matches"] += 1
                    if team_won:
                        player_stats["partners"][partner]["wins"] += 1

        # Convert to list and add calculated fields
        result_players = []
        for player_name, stats in players.items():
            win_rate = (
                (stats["wins"] / stats["matches"] * 100) if stats["matches"] > 0 else 0
            )

            # Find best court
            best_court = None
            best_court_rate = 0
            for court, court_stats in stats["courts"].items():
                if court_stats["matches"] >= 2:
                    court_rate = court_stats["wins"] / court_stats["matches"] * 100
                    if court_rate > best_court_rate:
                        best_court_rate = court_rate
                        best_court = f"{court} ({court_rate:.1f}%)"

            # Find best partner
            best_partner = None
            best_partner_rate = 0
            for partner, partner_stats in stats["partners"].items():
                if partner_stats["matches"] >= 2:
                    partner_rate = (
                        partner_stats["wins"] / partner_stats["matches"] * 100
                    )
                    if partner_rate > best_partner_rate:
                        best_partner_rate = partner_rate
                        best_partner = f"{partner} ({partner_rate:.1f}%)"

            result_players.append(
                {
                    "name": player_name,
                    "matches": stats["matches"],
                    "wins": stats["wins"],
                    "losses": stats["matches"] - stats["wins"],
                    "winRate": round(win_rate, 1),
                    "pti": stats["pti"],
                    "bestCourt": best_court or "N/A",
                    "bestPartner": best_partner or "N/A",
                    "courts": stats["courts"],
                    "partners": stats["partners"],
                }
            )

        # Sort by matches played (desc), then by win rate (desc)
        result_players.sort(key=lambda p: (-p["matches"], -p["winRate"]))

        return jsonify({"players": result_players, "teamId": team_id})

    except Exception as e:
        print(f"Error getting team players: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@player_bp.route("/player-detail/<player_name>")
@login_required
def serve_player_detail(player_name):
    """Serve the desktop player detail page"""
    from app.services.player_service import get_player_analysis_by_name

    analyze_data = get_player_analysis_by_name(player_name)

    session_data = {"user": session["user"], "authenticated": True}

    log_user_activity(
        session["user"]["email"],
        "page_visit",
        page="player_detail",
        details=f"Viewed player {player_name}",
    )
    return render_template(
        "player_detail.html",
        session_data=session_data,
        analyze_data=analyze_data,
        player_name=player_name,
    )


@player_bp.route("/api/player-history")
@login_required
def get_player_history():
    """Get player history from match data"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Not authenticated"}), 401

        app_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        user_league_id = user.get("league_id", "")

        # Use dynamic path based on league
        if user_league_id and not user_league_id.startswith("APTA"):
            player_history_path = os.path.join(
                app_dir, "data", "leagues", user_league_id, "player_history.json"
            )
        else:
            player_history_path = os.path.join(
                app_dir, "data", "leagues", "all", "player_history.json"
            )

        # Check if file exists before trying to open it
        if not os.path.exists(player_history_path):
            return jsonify({"error": "Player history data not available"}), 404

        with open(player_history_path, "r") as f:
            all_player_history = json.load(f)

        # Filter player history by league
        player_history = []
        for player in all_player_history:
            player_league = player.get("League", player.get("league_id"))
            if user_league_id.startswith("APTA"):
                # For APTA users, only include players from the same APTA league
                if player_league == user_league_id:
                    player_history.append(player)
            else:
                # For other leagues, match the league_id
                if player_league == user_league_id:
                    player_history.append(player)

        # Find the current user's player record
        user_name = f"{user['first_name']} {user['last_name']}"

        from app.services.player_service import find_player_in_history

        player_record = find_player_in_history(user, player_history)

        if not player_record:
            return jsonify({"error": f"No history found for player: {user_name}"}), 404

        return jsonify(player_record)

    except FileNotFoundError:
        return jsonify({"error": "Player history data not available"}), 404
    except Exception as e:
        print(f"Error getting player history: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@player_bp.route("/api/player-history/<player_name>")
@login_required
def get_specific_player_history(player_name):
    """Get history for a specific player"""
    try:
        app_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        user_league_id = session["user"].get("league_id", "")

        # Use dynamic path based on league
        if user_league_id and not user_league_id.startswith("APTA"):
            player_history_path = os.path.join(
                app_dir, "data", "leagues", user_league_id, "player_history.json"
            )
        else:
            player_history_path = os.path.join(
                app_dir, "data", "leagues", "all", "player_history.json"
            )

        with open(player_history_path, "r") as f:
            all_player_history = json.load(f)

        # Filter player history by league
        player_history = []
        for player in all_player_history:
            player_league = player.get("League", player.get("league_id"))
            if user_league_id.startswith("APTA"):
                # For APTA users, only include players from the same APTA league
                if player_league == user_league_id:
                    player_history.append(player)
            else:
                # For other leagues, match the league_id
                if player_league == user_league_id:
                    player_history.append(player)

        # Helper function to normalize names for comparison
        def normalize(name):
            return name.lower().strip().replace(",", "").replace(".", "")

        # Find the player's record by matching name (case-insensitive)
        target_normalized = normalize(player_name)
        player_record = None

        for player in player_history:
            if normalize(player.get("name", "")) == target_normalized:
                player_record = player
                break

        if not player_record:
            return (
                jsonify({"error": f"No history found for player: {player_name}"}),
                404,
            )

        return jsonify(player_record)

    except Exception as e:
        print(f"Error getting player history for {player_name}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
