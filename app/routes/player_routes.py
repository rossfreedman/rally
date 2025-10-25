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
        from app.services.player_service import get_players_by_league_and_series_id
        from database_utils import execute_query_one, execute_query

        # FIXED: Accept both series_id (preferred) and series (backward compatibility)
        series_id = request.args.get("series_id")
        series = request.args.get("series")
        team_id = request.args.get("team_id")

        # Require either series_id or series parameter
        if not series_id and not series:
            return jsonify({"error": "Either series_id or series parameter is required"}), 400

        print(f"\n=== DEBUG: get_players_by_series (ID-BASED) ===")
        print(f"Requested series_id: {series_id}")
        print(f"Requested series (fallback): {series}")
        print(f"Requested team: {team_id}")
        print(f"User series: {session['user'].get('series')}")
        print(f"User club: {session['user'].get('club')}")
        print(f"User league: {session['user'].get('league_id')}")

        # Get user information - FIXED: Use string league ID instead of integer
        user_league_string_id = session["user"].get("league_string_id", "")
        user_league_id = session["user"].get("league_id", "")  # Keep for team filtering
        user_club = session["user"].get("club")

        # FIXED: Convert integer league_id to string league_id if needed
        if not user_league_string_id and user_league_id:
            try:
                # Convert integer league_id to string league_id
                league_record = execute_query_one(
                    "SELECT league_id FROM leagues WHERE id = %s", [user_league_id]
                )
                if league_record:
                    user_league_string_id = league_record["league_id"]
                    print(f"[DEBUG] Converted league_id {user_league_id} -> {user_league_string_id}")
                else:
                    print(f"[DEBUG] No league found for id {user_league_id}")
            except Exception as e:
                print(f"[DEBUG] Error converting league_id: {e}")
                
        # Get user club from session or from player association
        if not user_club:
            try:
                # Get club from player association
                club_record = execute_query_one(
                    """
                    SELECT c.name as club_name
                    FROM user_player_associations upa
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    JOIN clubs c ON p.club_id = c.id
                    WHERE upa.user_id = %s
                    LIMIT 1
                    """, [session["user"]["id"]]
                )
                if club_record:
                    user_club = club_record["club_name"]
                    print(f"[DEBUG] Got club from association: {user_club}")
            except Exception as e:
                print(f"[DEBUG] Error getting club from association: {e}")

        # FIXED: Use series_id directly if provided, otherwise convert series name to series_id
        if series_id:
            # Direct series_id query (preferred method)
            # PROTECTION: Gracefully handle invalid series_id after ETL runs
            try:
                # First verify the series_id exists
                series_verification = execute_query_one(
                    "SELECT id, name FROM series WHERE id = %s", [series_id]
                )
                
                if series_verification:
                    # Valid series_id - proceed with ID-based query
                    all_players = get_players_by_league_and_series_id(
                        league_id=user_league_string_id, 
                        series_id=series_id, 
                        club_name=user_club if not team_id else None,
                        team_id=team_id
                    )
                    print(f"[DEBUG] Used valid series_id {series_id} -> '{series_verification['name']}'")
                else:
                    # Invalid series_id (likely after ETL) - auto-fallback to name lookup
                    print(f"[DEBUG] Series_id {series_id} not found (likely after ETL), switching to name-based fallback")
                    
                    # If series name was provided as well, use it as fallback
                    if series:
                        converted_series_id = execute_query_one(
                            "SELECT id FROM series WHERE name = %s LIMIT 1", [series]
                        )
                        if converted_series_id:
                            all_players = get_players_by_league_and_series_id(
                                league_id=user_league_string_id, 
                                series_id=converted_series_id["id"], 
                                club_name=user_club if not team_id else None,
                                team_id=team_id
                            )
                            print(f"[DEBUG] Fallback: Found new series_id {converted_series_id['id']} for series '{series}'")
                        else:
                            print(f"[DEBUG] No fallback series name provided")
                            return jsonify({"error": f"Series_id {series_id} is invalid and no fallback series name provided"}), 404
                    else:
                        print(f"[DEBUG] No fallback series name available")
                        return jsonify({"error": f"Series_id {series_id} is invalid (possibly after ETL run). Please refresh and try again."}), 404
                        
            except Exception as e:
                print(f"[DEBUG] Error verifying series_id {series_id}: {e}")
                return jsonify({"error": "Database error during series lookup"}), 500
        else:
            # Fallback: convert series name to series_id first, then query by ID
            try:
                series_record = execute_query_one(
                    "SELECT id FROM series WHERE name = %s LIMIT 1", [series]
                )
                if series_record:
                    converted_series_id = series_record["id"]
                    all_players = get_players_by_league_and_series_id(
                        league_id=user_league_string_id, 
                        series_id=converted_series_id, 
                        club_name=user_club if not team_id else None,
                        team_id=team_id
                    )
                    print(f"[DEBUG] Converted series '{series}' -> series_id {converted_series_id}")
                else:
                    print(f"[DEBUG] Could not find series_id for series name '{series}'")
                    return jsonify({"error": f"Series '{series}' not found"}), 404
            except Exception as e:
                print(f"[DEBUG] Error converting series name to ID: {e}")
                return jsonify({"error": "Failed to lookup series"}), 500

        # Handle team filtering if requested
        team_players = set()
        if team_id:
            # FIXED: Get team players from database instead of JSON
            try:
                
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

                # REMOVED: Match-based team filtering logic that was causing the issue
                # The get_players_by_league_and_series_id function already handles team filtering correctly
                # by using the team_id parameter to get ALL registered team members, not just those who have played matches
                
            except Exception as e:
                print(
                    f"Warning: Error loading team players from database: {str(e)}"
                )
                team_id = None  # Continue without team filtering

        # Filter by team if specified (database stats are already included)
        final_players = []
        if team_id:
            # FIXED: Use the team filtering from get_players_by_league_and_series_id instead of match-based filtering
            # This ensures we get ALL registered team members, not just those who have played matches
            final_players = all_players  # all_players already contains team-filtered results from get_players_by_league_and_series_id
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
                                # Handle None PTI values
                                pti_value = player_data.get("pti")
                                if pti_value is None:
                                    pti_value = 0.0
                                
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
                                    "pti": float(pti_value),
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

    # Try to get player_id from analyze_data if available
    player_id = None
    if isinstance(analyze_data, dict):
        player_id = analyze_data.get("tenniscores_player_id")

    team_or_club = analyze_data.get("team_name") or analyze_data.get("club") or "Unknown"
    log_user_activity(
        session["user"]["email"],
        "page_visit",
        page="player_detail",
        details=f"Player Detail: {player_name} ({team_or_club})",
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

        # Get current PTI - handle None values properly
        current_pti = player_db_data.get("pti")
        if current_pti is None:
            # If current PTI is None, get the most recent PTI from history
            if pti_records:
                current_pti = pti_records[-1]["end_pti"]  # Most recent record
            else:
                current_pti = 0.0

        # Format response to match expected structure
        player_record = {
            "name": f"{player_db_data['first_name']} {player_db_data['last_name']}",
            "current_pti": float(current_pti),
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


@player_bp.route("/api/player-history-by-id/<player_id>")
@login_required
def get_player_history_by_id(player_id):
    """Get history for a specific player by player ID - FIXED: Uses player ID for accurate lookup"""
    try:
        from database_utils import execute_query, execute_query_one
        
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # Get user's league context
        user_data = session.get("user", {})
        league_id = user_data.get("league_id")
        league_id_int = int(league_id) if league_id else None

        # Search for player by tenniscores_player_id in database
        if league_id_int:
            player_search_query = """
                SELECT 
                    p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id,
                    (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                FROM players p
                WHERE p.tenniscores_player_id = %s AND p.league_id = %s
                LIMIT 1
            """
            player_data = execute_query_one(player_search_query, [player_id, league_id_int])
        else:
            # Fallback without league filter
            player_search_query = """
                SELECT 
                    p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id,
                    (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                FROM players p
                WHERE p.tenniscores_player_id = %s
                LIMIT 1
            """
            player_data = execute_query_one(player_search_query, [player_id])

        if not player_data:
            return (
                jsonify({"error": f"No history found for player ID: {player_id}"}),
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

        # Get current PTI - handle None values properly
        current_pti = player_data.get("pti")
        if current_pti is None:
            # If no current PTI, get the most recent from history
            if pti_records:
                current_pti = pti_records[-1]["end_pti"]
            else:
                current_pti = 0.0

        # Format response
        response_data = {
            "player_id": player_data["tenniscores_player_id"],
            "name": f"{player_data['first_name']} {player_data['last_name']}",
            "current_pti": float(current_pti),
            "history_count": player_data.get("history_count", 0),
            "matches": []
        }

        # Add PTI history
        for record in pti_records:
            response_data["matches"].append({
                "date": record["formatted_date"],
                "end_pti": float(record["end_pti"]),
                "series": record["series"]
            })

        return jsonify(response_data)

    except Exception as e:
        print(f"Error getting player history by ID: {str(e)}")
        return jsonify({"error": "Failed to get player history"}), 500


@player_bp.route("/api/player-history-with-context/<player_name>")
@login_required
def get_player_history_with_context(player_name):
    """Get history for a specific player with team/club context - FIXED: Uses team context for accurate lookup"""
    try:
        from database_utils import execute_query, execute_query_one
        from flask import request
        
        user_league_id = session["user"].get("league_id", "")
        team_id = request.args.get('team_id')
        club_id = request.args.get('club_id')

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

        # Parse player name to handle both "First Last" and "Last, First" formats
        first_name = None
        last_name = None
        
        if ',' in player_name:
            # Handle "Last, First" format
            name_sections = player_name.split(',')
            if len(name_sections) == 2:
                last_name = name_sections[0].strip()
                first_name = name_sections[1].strip()
        else:
            # Handle "First Last" format
            name_parts = player_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])  # Handle names with multiple last name parts
        
        if not first_name or not last_name:
            return jsonify({"error": f"Invalid player name format: {player_name}"}), 400

        # Search for player in database with team/club context
        if league_id_int:
            if team_id:
                # Prioritize player from specified team
                player_search_query = """
                    SELECT 
                        p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id,
                        (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count,
                        CASE WHEN p.team_id = %s THEN 1 ELSE 0 END as is_target_team
                    FROM players p
                    WHERE LOWER(p.first_name) = LOWER(%s) AND LOWER(p.last_name) = LOWER(%s)
                    AND p.league_id = %s
                    ORDER BY is_target_team DESC, history_count DESC, p.id DESC
                    LIMIT 1
                """
                player_data = execute_query_one(player_search_query, [team_id, first_name, last_name, league_id_int])
            elif club_id:
                # Prioritize player from specified club
                player_search_query = """
                    SELECT 
                        p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id,
                        (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count,
                        CASE WHEN p.club_id = %s THEN 1 ELSE 0 END as is_target_club
                    FROM players p
                    WHERE LOWER(p.first_name) = LOWER(%s) AND LOWER(p.last_name) = LOWER(%s)
                    AND p.league_id = %s
                    ORDER BY is_target_club DESC, history_count DESC, p.id DESC
                    LIMIT 1
                """
                player_data = execute_query_one(player_search_query, [club_id, first_name, last_name, league_id_int])
            else:
                # Fallback: prioritize by PTI history
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

        # Get current PTI - handle None values properly
        current_pti = player_data.get("pti")
        if current_pti is None:
            # If current PTI is None, get the most recent PTI from history
            if pti_records:
                current_pti = pti_records[-1]["end_pti"]  # Most recent record
            else:
                current_pti = 0.0

        # Format response to match expected structure
        player_record = {
            "name": f"{player_data['first_name']} {player_data['last_name']}",
            "current_pti": float(current_pti),
            "player_id": player_data["tenniscores_player_id"],
            "matches": []
        }

        # Convert PTI history to matches format
        for record in pti_records:
            player_record["matches"].append({
                "date": record["formatted_date"],
                "pti": float(record["end_pti"]),
                "series": record["series"]
            })

        return jsonify(player_record)

    except Exception as e:
        print(f"Error in get_player_history_with_context: {e}")
        import traceback
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
        # Parse player name to handle both "First Last" and "Last, First" formats
        first_name = None
        last_name = None
        
        if ',' in player_name:
            # Handle "Last, First" format
            name_sections = player_name.split(',')
            if len(name_sections) == 2:
                last_name = name_sections[0].strip()
                first_name = name_sections[1].strip()
        else:
            # Handle "First Last" format
            name_parts = player_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])  # Handle names with multiple last name parts
        
        if not first_name or not last_name:
            return jsonify({"error": f"Invalid player name format: {player_name}"}), 400

        # Search for player in database, prioritizing current team context
        user_team_id = session["user"].get("team_id")
        
        if league_id_int:
            if user_team_id:
                # Prioritize player from current team first
                player_search_query = """
                    SELECT 
                        p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id,
                        (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count,
                        CASE WHEN p.team_id = %s THEN 1 ELSE 0 END as is_current_team
                    FROM players p
                    WHERE LOWER(p.first_name) = LOWER(%s) AND LOWER(p.last_name) = LOWER(%s)
                    AND p.league_id = %s
                    ORDER BY is_current_team DESC, history_count DESC, p.id DESC
                    LIMIT 1
                """
                player_data = execute_query_one(player_search_query, [user_team_id, first_name, last_name, league_id_int])
            else:
                # Fallback: prioritize by PTI history
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

        # Get current PTI - handle None values properly
        current_pti = player_data.get("pti")
        if current_pti is None:
            # If current PTI is None, get the most recent PTI from history
            if pti_records:
                current_pti = pti_records[-1]["end_pti"]  # Most recent record
            else:
                current_pti = 0.0

        # Format response to match expected structure
        player_record = {
            "name": f"{player_data['first_name']} {player_data['last_name']}",
            "current_pti": float(current_pti),
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
