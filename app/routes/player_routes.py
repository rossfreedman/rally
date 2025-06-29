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

        # Get user information - FIXED: Use string league ID instead of integer
        user_league_string_id = session["user"].get("league_string_id", "")
        user_league_id = session["user"].get("league_id", "")  # Keep for team filtering
        user_club = session["user"].get("club")

        # Get players from database using new multi-league schema
        all_players = get_players_by_league_and_series(
            league_id=user_league_string_id, series_name=series, club_name=user_club
        )

        # Handle team filtering if requested
        team_players = set()
        if team_id:
            # FIXED: Get team players from database instead of JSON
            try:
                from database_utils import execute_query
                
                # Convert string league_id to integer foreign key if needed
                league_id_int = None
                if user_league_id:
                    if isinstance(user_league_id, str) and user_league_id != "":
                        try:
                            from database_utils import execute_query_one
                            league_record = execute_query_one(
                                "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                            )
                            if league_record:
                                league_id_int = league_record["id"]
                        except Exception as e:
                            pass
                    elif isinstance(user_league_id, int):
                        league_id_int = user_league_id

                # Get all players who have played for this team from database (FIXED: Use team_id)
                if league_id_int:
                    # Try using team_id as integer first (new optimized approach)
                    try:
                        team_id_int = int(team_id)
                        team_players_query = """
                            SELECT DISTINCT 
                                home_player_1_id as player_id FROM match_scores 
                            WHERE home_team_id = %s AND league_id = %s AND home_player_1_id IS NOT NULL
                            UNION
                            SELECT DISTINCT 
                                home_player_2_id as player_id FROM match_scores 
                            WHERE home_team_id = %s AND league_id = %s AND home_player_2_id IS NOT NULL
                            UNION
                            SELECT DISTINCT 
                                away_player_1_id as player_id FROM match_scores 
                            WHERE away_team_id = %s AND league_id = %s AND away_player_1_id IS NOT NULL
                            UNION
                            SELECT DISTINCT 
                                away_player_2_id as player_id FROM match_scores 
                            WHERE away_team_id = %s AND league_id = %s AND away_player_2_id IS NOT NULL
                        """
                        team_player_records = execute_query(team_players_query, [
                            team_id_int, league_id_int, team_id_int, league_id_int,
                            team_id_int, league_id_int, team_id_int, league_id_int
                        ])
                        print(f"[DEBUG] Using team_id optimization: Found {len(team_player_records)} players for team_id {team_id_int}")
                    except ValueError:
                        # Fallback to team name if team_id is not an integer
                        team_players_query = """
                            SELECT DISTINCT 
                                home_player_1_id as player_id FROM match_scores 
                            WHERE home_team = %s AND league_id = %s AND home_player_1_id IS NOT NULL
                            UNION
                            SELECT DISTINCT 
                                home_player_2_id as player_id FROM match_scores 
                            WHERE home_team = %s AND league_id = %s AND home_player_2_id IS NOT NULL
                            UNION
                            SELECT DISTINCT 
                                away_player_1_id as player_id FROM match_scores 
                            WHERE away_team = %s AND league_id = %s AND away_player_1_id IS NOT NULL
                            UNION
                            SELECT DISTINCT 
                                away_player_2_id as player_id FROM match_scores 
                            WHERE away_team = %s AND league_id = %s AND away_player_2_id IS NOT NULL
                        """
                        team_player_records = execute_query(team_players_query, [
                            team_id, league_id_int, team_id, league_id_int,
                            team_id, league_id_int, team_id, league_id_int
                        ])
                        print(f"[DEBUG] Using team_name fallback: Found {len(team_player_records)} players for team_name {team_id}")
                    
                    # Convert player IDs to names for filtering
                    for record in team_player_records:
                        player_id = record['player_id']
                        if player_id:
                            # Get player name from database
                            try:
                                from database_utils import execute_query_one
                                player_name_query = """
                                    SELECT first_name, last_name FROM players 
                                    WHERE tenniscores_player_id = %s
                                """
                                player_data = execute_query_one(player_name_query, [player_id])
                                if player_data:
                                    player_name = f"{player_data['first_name']} {player_data['last_name']}"
                                    team_players.add(player_name)
                            except Exception as e:
                                # Fallback: use player ID as name if lookup fails
                                team_players.add(player_id)
                                
            except Exception as e:
                print(
                    f"Warning: Error loading team players from database: {str(e)}"
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
    """Get all players for a specific team - FIXED: Uses database instead of JSON"""
    try:
        from database_utils import execute_query, execute_query_one
        from collections import defaultdict
        
        user_league_id = session["user"].get("league_id", "")

        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if user_league_id:
            if isinstance(user_league_id, str) and user_league_id != "":
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                except Exception as e:
                    pass
            elif isinstance(user_league_id, int):
                league_id_int = user_league_id

        if not league_id_int:
            return jsonify({"error": "League context required"}), 400

        # FIXED: Get team matches from database using team_id optimization
        try:
            team_id_int = int(team_id)
            team_matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as match_date_formatted,
                    match_date,
                    home_team,
                    away_team,
                    winner,
                    scores,
                    home_player_1_id,
                    home_player_2_id,
                    away_player_1_id,
                    away_player_2_id,
                    id
                FROM match_scores
                WHERE (home_team_id = %s OR away_team_id = %s)
                AND league_id = %s
                ORDER BY match_date, id
            """
            matches = execute_query(team_matches_query, [team_id_int, team_id_int, league_id_int])
            print(f"[DEBUG] Using team_id optimization: Found {len(matches)} matches for team_id {team_id_int}")
        except ValueError:
            # Fallback to team name if team_id is not an integer
            team_matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as match_date_formatted,
                    match_date,
                    home_team,
                    away_team,
                    winner,
                    scores,
                    home_player_1_id,
                    home_player_2_id,
                    away_player_1_id,
                    away_player_2_id,
                    id
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                ORDER BY match_date, id
            """
            matches = execute_query(team_matches_query, [team_id, team_id, league_id_int])
            print(f"[DEBUG] Using team_name fallback: Found {len(matches)} matches for team_name {team_id}")
        
        if not matches:
            return jsonify({"players": [], "teamId": team_id})

        # Track unique players and their stats
        players = {}

        # Group matches by date to determine court numbers (same logic as before)
        date_matches = defaultdict(list)
        for match in matches:
            date = match["match_date_formatted"]
            date_matches[date].append(match)

        # Sort dates and assign court numbers
        sorted_dates = sorted(date_matches.keys())

        for date in sorted_dates:
            day_matches = date_matches[date]
            # Sort by match ID as proxy for time
            day_matches.sort(key=lambda m: m.get("id", 0))

            for court_idx, match in enumerate(day_matches):
                court_num = (court_idx % 4) + 1  # Courts 1-4

                # Determine if team was home or away
                is_home = match["home_team"] == team_id
                player1_id = match["home_player_1_id"] if is_home else match["away_player_1_id"]
                player2_id = match["home_player_2_id"] if is_home else match["away_player_2_id"]

                # Skip if players are missing
                if not player1_id or not player2_id:
                    continue

                # Get player names from database
                player1_name = None
                player2_name = None
                
                for player_id in [player1_id, player2_id]:
                    try:
                        player_query = """
                            SELECT first_name, last_name, pti FROM players 
                            WHERE tenniscores_player_id = %s AND league_id = %s
                        """
                        player_data = execute_query_one(player_query, [player_id, league_id_int])
                        if player_data:
                            player_name = f"{player_data['first_name']} {player_data['last_name']}"
                            if player_id == player1_id:
                                player1_name = player_name
                            else:
                                player2_name = player_name
                                
                            # Initialize player if not seen before
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
                                    "pti": float(player_data.get("pti", 0.0)),
                                }
                    except Exception as e:
                        print(f"Error getting player data for {player_id}: {e}")
                        continue

                # Skip if we couldn't get player names
                if not player1_name or not player2_name:
                    continue

                # Determine if team won
                winner_is_home = match.get("winner") == "home"
                team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)

                # Track stats for each player
                for player_name in [player1_name, player2_name]:
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
                    partner = player2_name if player_name == player1_name else player1_name
                    if partner not in player_stats["partners"]:
                        player_stats["partners"][partner] = {"matches": 0, "wins": 0}
                    player_stats["partners"][partner]["matches"] += 1
                    if team_won:
                        player_stats["partners"][partner]["wins"] += 1

        # Convert to list and add calculated fields (same logic as before)
        result_players = []
        for player_name, stats in players.items():
            win_rate = (
                (stats["wins"] / stats["matches"] * 100) if stats["matches"] > 0 else 0
            )

            # Find best court - Fixed logic: >3 matches (>=4) AND >=70% win rate
            best_court = None
            best_court_rate = 0
            for court, court_stats in stats["courts"].items():
                if court_stats["matches"] > 3:  # More than 3 matches (>=4)
                    court_rate = court_stats["wins"] / court_stats["matches"] * 100
                    if court_rate >= 70.0:  # Must have 70% or greater win rate
                        if court_rate > best_court_rate:
                            best_court_rate = court_rate
                            best_court = court

            # Find best partner
            best_partner = None
            best_partner_rate = 0
            for partner, partner_stats in stats["partners"].items():
                if partner_stats["matches"] >= 2:
                    partner_rate = (
                        partner_stats["wins"] / partner_stats["matches"] * 100
                    )
                    if partner_rate >= 60.0:  # Must have 60% or greater win rate
                        if partner_rate > best_partner_rate:
                            best_partner_rate = partner_rate
                            best_partner = partner

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
    """Get player history from database - FIXED: Uses database instead of JSON"""
    try:
        from database_utils import execute_query, execute_query_one
        
        user = session.get("user")
        if not user:
            return jsonify({"error": "Not authenticated"}), 401

        player_id = user.get("tenniscores_player_id")
        user_league_id = user.get("league_id", "")

        if not player_id:
            return jsonify({"error": "Player ID not found in session"}), 400

        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if user_league_id:
            if isinstance(user_league_id, str) and user_league_id != "":
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                except Exception as e:
                    pass
            elif isinstance(user_league_id, int):
                league_id_int = user_league_id

        # FIXED: Get player history from database instead of JSON
        if league_id_int:
            # Get player's database ID first
            player_db_query = """
                SELECT id, first_name, last_name, pti 
                FROM players 
                WHERE tenniscores_player_id = %s AND league_id = %s
            """
            player_db_data = execute_query_one(player_db_query, [player_id, league_id_int])
        else:
            # Fallback without league filter
            player_db_query = """
                SELECT id, first_name, last_name, pti 
                FROM players 
                WHERE tenniscores_player_id = %s
                ORDER BY id DESC
                LIMIT 1
            """
            player_db_data = execute_query_one(player_db_query, [player_id])

        if not player_db_data:
            user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
            return jsonify({"error": f"No history found for player: {user_name}"}), 404

        player_db_id = player_db_data["id"]

        # Get PTI history from player_history table
        pti_history_query = """
            SELECT 
                date,
                end_pti,
                series,
                TO_CHAR(date, 'MM/DD/YYYY') as formatted_date
            FROM player_history
            WHERE player_id = %s
            ORDER BY date ASC
        """

        pti_records = execute_query(pti_history_query, [player_db_id])

        # Format response to match expected structure
        player_record = {
            "name": f"{player_db_data['first_name']} {player_db_data['last_name']}",
            "current_pti": float(player_db_data.get("pti", 0.0)),
            "matches": []
        }

        # Convert PTI history to matches format
        for record in pti_records:
            player_record["matches"].append({
                "date": record["formatted_date"],
                "end_pti": float(record["end_pti"]),
                "series": record["series"]
            })

        return jsonify(player_record)

    except Exception as e:
        print(f"Error getting player history: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@player_bp.route("/api/player-history/<player_name>")
@login_required
def get_specific_player_history(player_name):
    """Get history for a specific player - FIXED: Uses database instead of JSON"""
    try:
        from database_utils import execute_query, execute_query_one
        
        user_league_id = session["user"].get("league_id", "")

        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if user_league_id:
            if isinstance(user_league_id, str) and user_league_id != "":
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                except Exception as e:
                    pass
            elif isinstance(user_league_id, int):
                league_id_int = user_league_id

        # FIXED: Find player by name in database instead of JSON
        # Parse the player name to first and last name
        name_parts = player_name.strip().split()
        if len(name_parts) < 2:
            return jsonify({"error": f"Invalid player name format: {player_name}"}), 400
        
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:])  # Handle names with multiple last name parts

        # Search for player in database, prioritizing the one with PTI history
        if league_id_int:
            player_search_query = """
                SELECT 
                    p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id,
                    (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                FROM players p
                WHERE LOWER(p.first_name) = LOWER(%s) AND LOWER(p.last_name) = LOWER(%s)
                AND p.league_id = %s
                ORDER BY history_count DESC, p.id DESC
                LIMIT 1
            """
            player_data = execute_query_one(player_search_query, [first_name, last_name, league_id_int])
        else:
            # Fallback without league filter
            player_search_query = """
                SELECT 
                    p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id,
                    (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                FROM players p
                WHERE LOWER(p.first_name) = LOWER(%s) AND LOWER(p.last_name) = LOWER(%s)
                ORDER BY history_count DESC, p.id DESC
                LIMIT 1
            """
            player_data = execute_query_one(player_search_query, [first_name, last_name])

        if not player_data:
            return (
                jsonify({"error": f"No history found for player: {player_name}"}),
                404,
            )

        player_db_id = player_data["id"]

        # Get PTI history from player_history table
        pti_history_query = """
            SELECT 
                date,
                end_pti,
                series,
                TO_CHAR(date, 'MM/DD/YYYY') as formatted_date
            FROM player_history
            WHERE player_id = %s
            ORDER BY date ASC
        """

        pti_records = execute_query(pti_history_query, [player_db_id])

        # Format response to match expected structure
        player_record = {
            "name": f"{player_data['first_name']} {player_data['last_name']}",
            "current_pti": float(player_data.get("pti", 0.0)),
            "player_id": player_data["tenniscores_player_id"],
            "matches": []
        }

        # Convert PTI history to matches format
        for record in pti_records:
            player_record["matches"].append({
                "date": record["formatted_date"],
                "end_pti": float(record["end_pti"]),
                "series": record["series"]
            })

        return jsonify(player_record)

    except Exception as e:
        print(f"Error getting player history for {player_name}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
