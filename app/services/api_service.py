"""
API Service Module

This module contains business logic for API routes.
Functions handle data processing, database queries, and response formatting for API endpoints.
"""

import json
import os
import traceback

from flask import jsonify, request, session

from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from utils.series_matcher import normalize_series_for_storage, series_match


def calculate_points_progression(series_stats, matches_path):
    """Calculate cumulative points progression over time for teams in the series - FIXED: Uses database instead of JSON"""
    try:
        from database_utils import execute_query
        
        # FIXED: Get matches from database instead of JSON
        all_matches_query = """
            SELECT 
                TO_CHAR(match_date, 'DD-Mon-YY') as date,
                home_team,
                away_team,
                winner
            FROM match_scores
            ORDER BY match_date ASC
        """
        
        db_matches = execute_query(all_matches_query)
        
        # Convert to expected format
        all_matches = []
        for match in db_matches:
            all_matches.append({
                "Date": match["date"],
                "Home Team": match["home_team"],
                "Away Team": match["away_team"],
                "Winner": match["winner"]
            })

        # Get team names from series stats
        team_names = [team["team"] for team in series_stats]
        if not team_names:
            return {}

        # Filter matches for teams in this series
        series_matches = []
        for match in all_matches:
            home_team = match.get("Home Team", "")
            away_team = match.get("Away Team", "")
            if home_team in team_names or away_team in team_names:
                series_matches.append(match)

        # Sort matches by date
        from datetime import datetime

        def parse_date(date_str):
            try:
                # Handle different date formats
                if "-" in date_str:
                    return datetime.strptime(date_str, "%d-%b-%y")
                return datetime.strptime(date_str, "%m/%d/%Y")
            except:
                return datetime.now()

        series_matches.sort(key=lambda m: parse_date(m.get("Date", "")))

        # Calculate cumulative points for each team over time
        team_progression = {}
        team_points = {}
        match_weeks = []

        # Initialize team points
        for team_name in team_names:
            team_progression[team_name] = []
            team_points[team_name] = 0

        # Group matches by week (approximate)
        current_week = 0
        last_date = None
        week_matches = 0

        for i, match in enumerate(series_matches):
            match_date = parse_date(match.get("Date", ""))

            # Check if we've moved to a new week (7+ days difference or every 12 matches)
            if (last_date and (match_date - last_date).days >= 7) or week_matches >= 12:
                current_week += 1
                week_matches = 0
                # Record current points for all teams at end of week
                if current_week <= len(match_weeks):
                    match_weeks.append(f"Week {current_week}")
                    for team_name in team_names:
                        team_progression[team_name].append(team_points[team_name])

            home_team = match.get("Home Team", "")
            away_team = match.get("Away Team", "")
            winner = match.get("Winner", "")

            # Simplified points system based on line wins
            # Each match represents one line, winner gets 1 point
            if home_team in team_names:
                if winner == "home":
                    team_points[home_team] += 1

            if away_team in team_names:
                if winner == "away":
                    team_points[away_team] += 1

            last_date = match_date
            week_matches += 1

        # Add final week if we have remaining matches
        if week_matches > 0:
            match_weeks.append(f"Week {current_week + 1}")
            for team_name in team_names:
                team_progression[team_name].append(team_points[team_name])

        return {"weeks": match_weeks, "teams": team_progression}

    except Exception as e:
        print(f"Error calculating points progression: {str(e)}")
        return {}


def get_series_stats_data():
    """Get series statistics data from PostgreSQL database"""
    try:
        import traceback

        from flask import jsonify, request, session

        from database_utils import execute_query, execute_query_one

        # Get the requested team from query params (for individual team analysis)
        requested_team = request.args.get("team")

        if requested_team:
            # Individual team analysis - query the database for this specific team
            team_stats_query = """
                SELECT 
                    s.series,
                    s.team,
                    s.points,
                    s.matches_won,
                    s.matches_lost,
                    s.matches_tied,
                    s.lines_won,
                    s.lines_lost,
                    s.sets_won,
                    s.sets_lost,
                    s.games_won,
                    s.games_lost,
                    l.league_id,
                    t.display_name
                FROM series_stats s
                LEFT JOIN leagues l ON s.league_id = l.id
                LEFT JOIN teams t ON s.team = t.team_name AND s.league_id = t.league_id
                WHERE s.team = %s
            """
            team_stats = execute_query_one(team_stats_query, [requested_team])

            if not team_stats:
                return jsonify({"error": "Team not found"}), 404

            # Calculate percentages
            total_matches = (
                team_stats["matches_won"]
                + team_stats["matches_lost"]
                + (team_stats["matches_tied"] or 0)
            )
            match_percentage = (
                f"{round((team_stats['matches_won'] / total_matches) * 100, 1)}%"
                if total_matches > 0
                else "0%"
            )

            total_lines = team_stats["lines_won"] + team_stats["lines_lost"]
            line_percentage = (
                f"{round((team_stats['lines_won'] / total_lines) * 100, 1)}%"
                if total_lines > 0
                else "0%"
            )

            total_sets = team_stats["sets_won"] + team_stats["sets_lost"]
            set_percentage = (
                f"{round((team_stats['sets_won'] / total_sets) * 100, 1)}%"
                if total_sets > 0
                else "0%"
            )

            total_games = team_stats["games_won"] + team_stats["games_lost"]
            game_percentage = (
                f"{round((team_stats['games_won'] / total_games) * 100, 1)}%"
                if total_games > 0
                else "0%"
            )

            # Format the response with team analysis data
            response = {
                "team_analysis": {
                    "overview": {
                        "points": team_stats["points"],
                        "match_record": f"{team_stats['matches_won']}-{team_stats['matches_lost']}",
                        "match_win_rate": match_percentage,
                        "line_win_rate": line_percentage,
                        "set_win_rate": set_percentage,
                        "game_win_rate": game_percentage,
                    }
                }
            }

            # Add display name if available
            if team_stats.get("display_name"):
                response["team_analysis"]["display_name"] = team_stats["display_name"]

            return jsonify(response)

        # If no team requested, get series standings for the user's series
        user = session.get("user")
        
        # ENHANCED: Use series_id for direct lookups, with fallback to name matching
        user_series_id = user.get("series_id")
        user_league_id = user.get("league_id")
        
        # Get the string league ID for proper league format detection
        user_league_string_id = user.get("league_string_id")  # Should be "CNSWPL"
        
        # Convert league_id to integer DB ID if necessary
        user_league_db_id = user_league_id
        if isinstance(user_league_id, str):
            try:
                # Look up the integer DB ID for the league
                league_lookup_query = "SELECT id FROM leagues WHERE league_id = %s"
                league_record = execute_query_one(league_lookup_query, [user_league_id])
                if league_record:
                    user_league_db_id = league_record["id"]
                    user_league_string_id = user_league_id  # Store the original string
                    print(f"[DEBUG] Converted league_id '{user_league_id}' -> DB ID {user_league_db_id}")
                else:
                    print(f"[DEBUG] No league found for league_id '{user_league_id}'")
                    user_league_db_id = None
            except Exception as e:
                print(f"[DEBUG] Error converting league_id: {e}")
                user_league_db_id = user_league_id
        elif isinstance(user_league_id, int) and not user_league_string_id:
            # Look up the string ID from the integer ID
            try:
                league_lookup_query = "SELECT league_id FROM leagues WHERE id = %s"
                league_record = execute_query_one(league_lookup_query, [user_league_id])
                if league_record:
                    user_league_string_id = league_record["league_id"]
                    user_league_db_id = user_league_id
                    print(f"[DEBUG] Resolved DB ID {user_league_id} -> league_id '{user_league_string_id}'")
            except Exception as e:
                print(f"[DEBUG] Error resolving league string ID: {e}")
        
        print(f"[DEBUG] Getting series stats for user series_id: {user_series_id}, league: {user_league_id} (DB ID: {user_league_db_id})")
        
        # Strategy 1: Use series_id for direct lookup if available
        db_results = []
        if user_series_id:
            print(f"[DEBUG] Attempting direct series_id lookup: {user_series_id}")
            
            if user_league_db_id:
                series_stats_query = """
                    SELECT 
                        s.series,
                        s.team,
                        s.points,
                        s.matches_won,
                        s.matches_lost,
                        s.matches_tied,
                        s.lines_won,
                        s.lines_lost,
                        s.lines_for,
                        s.lines_ret,
                        s.sets_won,
                        s.sets_lost,
                        s.games_won,
                        s.games_lost,
                        l.league_id,
                        t.display_name
                    FROM series_stats s
                    LEFT JOIN leagues l ON s.league_id = l.id
                    LEFT JOIN teams t ON s.team = t.team_name AND s.league_id = t.league_id
                    WHERE s.series_id = %s AND s.league_id = %s
                    ORDER BY s.points DESC, s.team ASC
                """
                db_results = execute_query(series_stats_query, [user_series_id, user_league_db_id])
            else:
                series_stats_query = """
                    SELECT 
                        s.series,
                        s.team,
                        s.points,
                        s.matches_won,
                        s.matches_lost,
                        s.matches_tied,
                        s.lines_won,
                        s.lines_lost,
                        s.lines_for,
                        s.lines_ret,
                        s.sets_won,
                        s.sets_lost,
                        s.games_won,
                        s.games_lost,
                        t.display_name
                    FROM series_stats s
                    LEFT JOIN teams t ON s.team = t.team_name
                    WHERE s.series_id = %s
                    ORDER BY s.points DESC, s.team ASC
                """
                db_results = execute_query(series_stats_query, [user_series_id])
            
            print(f"[DEBUG] Direct series_id lookup found {len(db_results)} teams")
        
        # Strategy 2: Fallback to series name matching if series_id lookup failed
        if not db_results:
            print(f"[DEBUG] Falling back to series name matching")
            
            # Resolve the actual series name from the series_id
            resolved_series_name = None
            if user_series_id:
                series_lookup_query = "SELECT name FROM series WHERE id = %s"
                series_record = execute_query_one(series_lookup_query, [user_series_id])
                if series_record:
                    resolved_series_name = series_record["name"]
                    print(f"[DEBUG] Resolved series_id {user_series_id} -> '{resolved_series_name}'")
                else:
                    print(f"[DEBUG] No series found for series_id {user_series_id}")
            
            # Fallback to series name from session if series_id resolution fails
            if not resolved_series_name:
                resolved_series_name = user.get("series")
                print(f"[DEBUG] Using session series name: '{resolved_series_name}'")
            
            if not resolved_series_name:
                return jsonify({"error": "User series not found"}), 400

            # NORMALIZE SERIES NAME: Handle different league formats
            # APTA/NSTF: "Series 2B" -> "S2B" 
            # CNSWPL: "Series 12" -> "Series 12" (keep as-is)
            normalized_series_name = resolved_series_name
            if resolved_series_name and resolved_series_name.startswith("Series "):
                if user_league_string_id == "CNSWPL":
                    # CNSWPL uses full "Series 12" format in database
                    normalized_series_name = resolved_series_name
                    print(f"[DEBUG] CNSWPL series name kept as-is: '{resolved_series_name}'")
                else:
                    # APTA/NSTF use "S2B" format 
                    series_parts = resolved_series_name.split(" ", 1)
                    if len(series_parts) > 1:
                        series_number = series_parts[1]
                        normalized_series_name = f"S{series_number}"
                        print(f"[DEBUG] Normalized series name: '{resolved_series_name}' -> '{normalized_series_name}'")

            # Query series stats using normalized series name
            if user_league_db_id:
                series_stats_query = """
                    SELECT 
                        s.series,
                        s.team,
                        s.points,
                        s.matches_won,
                        s.matches_lost,
                        s.matches_tied,
                        s.lines_won,
                        s.lines_lost,
                        s.lines_for,
                        s.lines_ret,
                        s.sets_won,
                        s.sets_lost,
                        s.games_won,
                        s.games_lost,
                        l.league_id,
                        t.display_name
                    FROM series_stats s
                    LEFT JOIN leagues l ON s.league_id = l.id
                    LEFT JOIN teams t ON s.team = t.team_name AND s.league_id = t.league_id
                                    WHERE s.series = %s AND s.league_id = %s
                ORDER BY s.points DESC, s.team ASC
                """
                db_results = execute_query(series_stats_query, [normalized_series_name, user_league_db_id])
            else:
                series_stats_query = """
                    SELECT 
                        s.series,
                        s.team,
                        s.points,
                        s.matches_won,
                        s.matches_lost,
                        s.matches_tied,
                        s.lines_won,
                        s.lines_lost,
                        s.lines_for,
                        s.lines_ret,
                        s.sets_won,
                        s.sets_lost,
                        s.games_won,
                        s.games_lost,
                        t.display_name
                    FROM series_stats s
                    LEFT JOIN teams t ON s.team = t.team_name
                                    WHERE s.series = %s
                ORDER BY s.points DESC, s.team ASC
                """
                db_results = execute_query(series_stats_query, [normalized_series_name])
            
            print(f"[DEBUG] Series name fallback found {len(db_results)} teams")

        print(f"[DEBUG] Total teams found: {len(db_results)}")

        # Transform database results to match the expected frontend format
        teams = []
        for row in db_results:
            # Calculate percentages
            total_matches = (
                row["matches_won"] + row["matches_lost"] + (row["matches_tied"] or 0)
            )
            match_percentage = (
                f"{round((row['matches_won'] / total_matches) * 100, 1)}%"
                if total_matches > 0
                else "0%"
            )

            total_lines = row["lines_won"] + row["lines_lost"]
            line_percentage = (
                f"{round((row['lines_won'] / total_lines) * 100, 1)}%"
                if total_lines > 0
                else "0%"
            )

            total_sets = row["sets_won"] + row["sets_lost"]
            set_percentage = (
                f"{round((row['sets_won'] / total_sets) * 100, 1)}%"
                if total_sets > 0
                else "0%"
            )

            total_games = row["games_won"] + row["games_lost"]
            game_percentage = (
                f"{round((row['games_won'] / total_games) * 100, 1)}%"
                if total_games > 0
                else "0%"
            )

            team_data = {
                "series": row["series"],
                "team": row["team"],
                "display_name": row.get("display_name", row["team"]),  # Use display_name if available
                "league_id": row.get("league_id", user_league_id),
                "points": row["points"],
                "matches": {
                    "won": row["matches_won"],
                    "lost": row["matches_lost"],
                    "tied": row["matches_tied"] or 0,
                    "percentage": match_percentage,
                },
                "lines": {
                    "won": row["lines_won"],
                    "lost": row["lines_lost"],
                    "for": row.get("lines_for", 0),
                    "ret": row.get("lines_ret", 0),
                    "percentage": line_percentage,
                },
                "sets": {
                    "won": row["sets_won"],
                    "lost": row["sets_lost"],
                    "percentage": set_percentage,
                },
                "games": {
                    "won": row["games_won"],
                    "lost": row["games_lost"],
                    "percentage": game_percentage,
                },
            }
            teams.append(team_data)

        print(f"[DEBUG] Returning {len(teams)} teams for series standings")

        # Return the teams data (points progression can be added later if needed)
        return jsonify({"teams": teams, "pointsProgression": {}})  # Placeholder for now

    except Exception as e:
        print(f"Error getting series stats from database: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "Failed to get series stats from database"}), 500


def get_players_by_series_data():
    """Get all players for a specific series, optionally filtered by team and club"""
    try:
        import json
        import os
        import traceback

        from flask import jsonify, request, session

        from utils.series_matcher import normalize_series_for_storage, series_match

        # Get series and optional team from query parameters
        series = request.args.get("series")
        team_id = request.args.get("team_id")

        if not series:
            return jsonify({"error": "Series parameter is required"}), 400

        print(f"\n=== DEBUG: get_players_by_series ===")
        print(f"Requested series: {series}")
        print(f"Requested team: {team_id}")
        print(f"User series: {session['user'].get('series')}")
        print(f"User club: {session['user'].get('club')}")

        # FIXED: Get data from database instead of JSON files
        from database_utils import execute_query, execute_query_one
        
        # Get user's league context
        user_league = session["user"].get("league_id", "APTA").upper()
        
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if user_league:
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league]
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                print(f"Warning: Could not convert league ID: {e}")

        print(f"User league: {user_league} (DB ID: {league_id_int})")

        # FIXED: Load player data from database instead of JSON
        if league_id_int:
            players_query = """
                SELECT p.first_name, p.last_name, p.pti, p.wins, p.losses, p.win_percentage,
                       s.name as series_name, c.name as club_name
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN clubs c ON p.club_id = c.id
                WHERE p.league_id = %s AND p.is_active = true
                ORDER BY p.first_name, p.last_name
            """
            all_players_db = execute_query(players_query, [league_id_int])
        else:
            # Fallback without league filter
            players_query = """
                SELECT p.first_name, p.last_name, p.pti, p.wins, p.losses, p.win_percentage,
                       s.name as series_name, c.name as club_name
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN clubs c ON p.club_id = c.id
                WHERE p.is_active = true
                ORDER BY p.first_name, p.last_name
            """
            all_players_db = execute_query(players_query)
        
        # Convert to expected format
        all_players = []
        for player in all_players_db:
            # Calculate win percentage if not stored
            wins = player.get("wins", 0) or 0
            losses = player.get("losses", 0) or 0
            total_matches = wins + losses
            win_percentage = f"{(wins / total_matches * 100):.1f}%" if total_matches > 0 else "0.0%"
            
            all_players.append({
                "First Name": player["first_name"],
                "Last Name": player["last_name"],
                "PTI": player.get("pti", 0.0),
                "Wins": wins,
                "Losses": losses,
                "Win %": win_percentage,
                "Series": player.get("series_name", ""),
                "Club": player.get("club_name", "")
            })

        # FIXED: Load matches data from database if team filtering is needed
        team_players = set()
        if team_id:
            try:
                if league_id_int:
                    team_matches_query = """
                        SELECT home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
                        FROM match_scores
                        WHERE (home_team = %s OR away_team = %s) AND league_id = %s
                    """
                    team_matches = execute_query(team_matches_query, [team_id, team_id, league_id_int])
                else:
                    team_matches_query = """
                        SELECT home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
                        FROM match_scores
                        WHERE home_team = %s OR away_team = %s
                    """
                    team_matches = execute_query(team_matches_query, [team_id, team_id])
                
                # Get player names from player IDs
                for match in team_matches:
                    for player_id in [match["home_player_1_id"], match["home_player_2_id"], 
                                    match["away_player_1_id"], match["away_player_2_id"]]:
                        if player_id:
                            try:
                                player_name_query = """
                                    SELECT first_name, last_name FROM players 
                                    WHERE tenniscores_player_id = %s
                                """
                                player_data = execute_query_one(player_name_query, [player_id])
                                if player_data:
                                    player_name = f"{player_data['first_name']} {player_data['last_name']}"
                                    team_players.add(player_name)
                            except Exception as e:
                                continue
                                
                print(f"Found {len(team_players)} team players for {team_id}")
            except Exception as e:
                print(f"Warning: Error loading team matches from database: {str(e)}")
                # Continue without team filtering if matches data can't be loaded
                team_id = None

        # Get user's club from session
        user_club = session["user"].get("club")

        # Filter players by series, team if specified, and club
        players = []
        for player in all_players:
            # Use our new series matching functionality
            if series_match(player["Series"], series):
                # Create player name in the same format as match data
                player_name = f"{player['First Name']} {player['Last Name']}"

                # If team_id is specified, only include players from that team
                if not team_id or player_name in team_players:
                    # Only include players from the same club as the user
                    if player["Club"] == user_club:
                        players.append(
                            {
                                "name": player_name,
                                "series": normalize_series_for_storage(
                                    player["Series"]
                                ),  # Normalize series format
                                "rating": str(player["PTI"]),
                                "pti": str(
                                    player["PTI"]
                                ),  # Add pti field for compatibility
                                "wins": str(player["Wins"]),
                                "losses": str(player["Losses"]),
                                "winRate": player["Win %"],
                            }
                        )

        print(
            f"Found {len(players)} players in {series}{' for team ' + team_id if team_id else ''} and club {user_club}"
        )
        print("=== END DEBUG ===\n")
        return jsonify(players)

    except Exception as e:
        print(f"\nERROR getting players for series {series}: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


def get_team_players_data(team_id):
    """Get team players data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "team_players", "team_id": team_id})


def test_log_data():
    """Test log data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "test_log"})


def verify_logging_data():
    """Verify logging data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "verify_logging"})


def log_click_data():
    """Log click data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "log_click"})


def research_team_data():
    """Research team data - returns team statistics and overview"""
    try:
        from flask import request, session
        from database_utils import execute_query_one, execute_query
        
        # Get team name from query parameter
        team_name = request.args.get("team")
        if not team_name:
            return jsonify({"error": "Team name is required"}), 400
        
        print(f"[DEBUG] research_team_data: Looking up team '{team_name}'")
        
        # Get user's league context for filtering
        user = session.get("user", {})
        user_league_id = user.get("league_id", "")
        
        # Convert league_id to integer if needed
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
                    print(f"[DEBUG] Could not convert league ID: {e}")
            elif isinstance(user_league_id, int):
                league_id_int = user_league_id
        
        # Get team info and stats from database
        team_query = """
            SELECT 
                t.id as team_id,
                t.team_name,
                t.display_name,
                c.name as club_name,
                s.name as series_name,
                l.league_id,
                ss.points,
                ss.matches_won,
                ss.matches_lost,
                ss.matches_tied,
                ss.lines_won,
                ss.lines_lost,
                ss.sets_won,
                ss.sets_lost,
                ss.games_won,
                ss.games_lost
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            LEFT JOIN series_stats ss ON ss.team = t.team_name AND ss.league_id = t.league_id
            WHERE t.team_name = %s
        """
        
        params = [team_name]
        if league_id_int:
            team_query += " AND t.league_id = %s"
            params.append(league_id_int)
        
        team_data = execute_query_one(team_query, params)
        
        if not team_data:
            return jsonify({"error": "Team not found"}), 404
        
        # Calculate additional statistics
        total_matches = (team_data.get("matches_won", 0) + 
                        team_data.get("matches_lost", 0) + 
                        team_data.get("matches_tied", 0))
        
        win_percentage = 0
        if total_matches > 0:
            win_percentage = round((team_data.get("matches_won", 0) / total_matches) * 100, 1)
        
        # Get recent match results for form analysis
        recent_matches_query = """
            SELECT 
                TO_CHAR(ms.match_date, 'DD-Mon-YY') as date,
                ms.home_team,
                ms.away_team,
                ms.winner,
                ms.scores,
                CASE 
                    WHEN ms.home_team_id = %s AND ms.winner = 'home' THEN 'W'
                    WHEN ms.away_team_id = %s AND ms.winner = 'away' THEN 'W'
                    ELSE 'L'
                END as result
            FROM match_scores ms
            WHERE (ms.home_team_id = %s OR ms.away_team_id = %s)
            ORDER BY ms.match_date DESC
            LIMIT 5
        """
        recent_matches = execute_query(recent_matches_query, [
            team_data["team_id"], team_data["team_id"], 
            team_data["team_id"], team_data["team_id"]
        ])
        
        # Calculate additional statistics for frontend compatibility
        total_lines = team_data.get("lines_won", 0) + team_data.get("lines_lost", 0)
        line_win_percentage = 0
        if total_lines > 0:
            line_win_percentage = round((team_data.get("lines_won", 0) / total_lines) * 100, 1)
        
        total_sets = team_data.get("sets_won", 0) + team_data.get("sets_lost", 0)
        set_win_percentage = 0
        if total_sets > 0:
            set_win_percentage = round((team_data.get("sets_won", 0) / total_sets) * 100, 1)
        
        total_games = team_data.get("games_won", 0) + team_data.get("games_lost", 0)
        game_win_percentage = 0
        if total_games > 0:
            game_win_percentage = round((team_data.get("games_won", 0) / total_games) * 100, 1)
        
        # Build response with frontend-compatible field names
        response_data = {
            "team": {
                "id": team_data["team_id"],
                "name": team_data["team_name"],
                "display_name": team_data["display_name"],
                "club": team_data["club_name"],
                "series": team_data["series_name"],
                "league": team_data["league_id"]
            },
            "overview": {
                "points": team_data.get("points", 0),
                "match_record": f"{team_data.get('matches_won', 0)}-{team_data.get('matches_lost', 0)}",
                "match_win_rate": win_percentage,
                "line_win_rate": line_win_percentage,
                "set_win_rate": set_win_percentage,
                "game_win_rate": game_win_percentage,
                # Keep original fields for backward compatibility
                "matches_played": total_matches,
                "matches_won": team_data.get("matches_won", 0),
                "matches_lost": team_data.get("matches_lost", 0),
                "matches_tied": team_data.get("matches_tied", 0),
                "win_percentage": win_percentage,
                "lines_won": team_data.get("lines_won", 0),
                "lines_lost": team_data.get("lines_lost", 0),
                "sets_won": team_data.get("sets_won", 0),
                "sets_lost": team_data.get("sets_lost", 0),
                "games_won": team_data.get("games_won", 0),
                "games_lost": team_data.get("games_lost", 0)
            },
            "recent_form": [match["result"] for match in recent_matches],
            "recent_matches": recent_matches
        }
        
        print(f"[DEBUG] research_team_data: Returning data for team '{team_name}'")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[ERROR] research_team_data: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


def get_player_court_stats_data(player_name):
    """Get player court statistics data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "player_court_stats", "player_name": player_name})


def research_my_team_data():
    """Research my team data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "research_my_team"})


def research_me_data():
    """Research me data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "research_me"})


def get_win_streaks_data():
    """Get win streaks data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "win_streaks"})


def get_player_streaks_data():
    """Get player streaks data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "player_streaks"})


def get_enhanced_streaks_data():
    """Get enhanced streaks data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "enhanced_streaks"})


def find_training_video_data():
    """Find relevant training videos based on user prompt"""
    try:
        import json
        import os

        from flask import jsonify, request

        data = request.get_json()
        if not data:
            return jsonify({"videos": [], "error": "No data provided"})

        user_prompt = data.get("content", "").lower().strip()

        if not user_prompt:
            return jsonify({"videos": [], "video": None})

        # Load training guide data
        try:
            # Use current working directory since server.py runs from project root
            guide_path = os.path.join(
                "data",
                "leagues",
                "apta",
                "improve_data",
                "complete_platform_tennis_training_guide.json",
            )
            with open(guide_path, "r", encoding="utf-8") as f:
                training_guide = json.load(f)
        except Exception as e:
            print(f"Error loading training guide: {str(e)}")
            return jsonify(
                {"videos": [], "video": None, "error": "Could not load training guide"}
            )

        # Search through training guide sections
        matching_sections = []

        def search_sections(data):
            """Search through the training guide sections"""
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and "Reference Videos" in value:
                        # Calculate relevance based on section title
                        relevance_score = calculate_video_relevance(
                            user_prompt, key.lower()
                        )

                        if relevance_score > 0:
                            # Get all videos from Reference Videos
                            videos = value.get("Reference Videos", [])
                            if videos and len(videos) > 0:
                                # Add each video with the section info
                                for video in videos:
                                    matching_sections.append(
                                        {
                                            "title": key.replace("_", " ").title(),
                                            "video": video,
                                            "relevance_score": relevance_score,
                                        }
                                    )

        def calculate_video_relevance(query, section_title):
            """Calculate relevance score for video matching"""
            score = 0
            query_words = query.split()

            # Exact match in section title gets highest score
            if query == section_title:
                score += 200

            # Query appears as a word in the section title
            if query in section_title.split():
                score += 150

            # Query appears anywhere in section title
            if query in section_title:
                score += 100

            # Partial word matches in section title
            for word in query_words:
                if word in section_title:
                    score += 50

            return score

        # Perform the search
        search_sections(training_guide)

        # Sort by relevance score and return all relevant matches
        if matching_sections:
            matching_sections.sort(key=lambda x: x["relevance_score"], reverse=True)

            # Filter to only include videos with sufficient relevance
            relevant_videos = []
            for match in matching_sections:
                if match["relevance_score"] >= 50:  # Minimum threshold for relevance
                    relevant_videos.append(
                        {
                            "title": match["video"]["title"],
                            "url": match["video"]["url"],
                            "topic": match["title"],
                            "relevance_score": match["relevance_score"],
                        }
                    )

            # Return both formats for backward compatibility
            response = {"videos": relevant_videos}

            # Include the best video as 'video' for backward compatibility
            if relevant_videos:
                response["video"] = relevant_videos[0]  # Best match (highest relevance)

            return jsonify(response)

        return jsonify({"videos": [], "video": None})

    except Exception as e:
        print(f"Error finding training video: {str(e)}")
        return jsonify({"videos": [], "video": None, "error": str(e)})


def remove_practice_times_data():
    """API endpoint to remove practice times for the user's series from the schedule"""
    try:
        import json
        import os

        from flask import jsonify, session

        from utils.logging import log_user_activity

        # Get user's club and series to determine which practice times to remove
        user = session["user"]
        user_club = user.get("club", "")
        user_series = user.get("series", "")

        if not user_club:
            return jsonify({"success": False, "message": "User club not found"}), 400

        if not user_series:
            return jsonify({"success": False, "message": "User series not found"}), 400

        # Get league ID for the user
        from database_utils import execute_query, execute_query_one

        league_id = None
        try:
            user_league = execute_query_one(
                """
                SELECT l.id 
                FROM users u 
                LEFT JOIN leagues l ON u.league_id = l.id 
                WHERE u.email = %(email)s
            """,
                {"email": user["email"]},
            )

            if user_league:
                league_id = user_league["id"]
        except Exception as e:
            print(f"Could not get league ID for user: {e}")

        # FIXED: Use priority-based team detection (same as availability page and other functions)
        user_team_id = None
        
        # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
        session_team_id = user.get("team_id")
        print(f"[DEBUG] Practice removal: session_team_id from user: {session_team_id}")
        
        if session_team_id:
            user_team_id = session_team_id
            print(f"[DEBUG] Practice removal: Using team_id from session: {user_team_id}")
        
        # PRIORITY 2: Use team_context from user if provided
        if not user_team_id:
            team_context = user.get("team_context")
            if team_context:
                user_team_id = team_context
                print(f"[DEBUG] Practice removal: Using team_context: {user_team_id}")
        
        # PRIORITY 3: Fallback to session service
        if not user_team_id:
            try:
                from app.services.session_service import get_session_data_for_user
                session_data = get_session_data_for_user(user["email"])
                if session_data:
                    user_team_id = session_data.get("team_id")
                    print(f"[DEBUG] Practice removal: Found team_id via session service: {user_team_id}")
            except Exception as e:
                print(f"Could not get team ID via session service: {e}")

        if not user_team_id:
            return jsonify({"success": False, "message": "Could not determine your team. Please check your profile settings."}), 400

        # Count practice entries before removal using team_id for precision
        practice_description = f"{user_club} Practice - {user_series}"

        # FIXED: Use team_id-based counting for accuracy (ignore league_id mismatch)
        practice_count_query = """
            SELECT COUNT(*) as count
            FROM schedule 
            WHERE home_team_id = %(team_id)s
            AND home_team LIKE '%%Practice%%'
        """

        try:
            practice_count_result = execute_query_one(
                practice_count_query,
                {
                    "team_id": user_team_id,
                },
            )
            practice_count = (
                practice_count_result["count"] if practice_count_result else 0
            )
            print(
                f"Found {practice_count} practice entries for team_id {user_team_id} ({user_club} - {user_series}) to remove"
            )
        except Exception as e:
            print(f"Error counting practice entries: {e}")
            practice_count = 0

        if practice_count == 0:
            return jsonify(
                {
                    "success": True,
                    "message": "No practice times found to remove.",
                    "count": 0,
                    "series": user_series,
                    "club": user_club,
                }
            )

        # FIXED: Remove practice entries using team_id for precision and security (ignore league_id mismatch)
        try:
            delete_query = """
                DELETE FROM schedule 
                WHERE home_team_id = %(team_id)s
                AND home_team LIKE '%%Practice%%'
            """

            execute_query(
                delete_query,
                {
                    "team_id": user_team_id,
                },
            )

            print(
                f"Successfully removed {practice_count} practice entries for team_id {user_team_id}"
            )

        except Exception as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Failed to remove practices from database: {str(e)}",
                    }
                ),
                500,
            )

        # Log the activity
        log_user_activity(
            user["email"],
            "practice_times_removed",
            details=f"Removed {practice_count} practice times for {user_series} at {user_club} (team_id: {user_team_id})",
        )

        return jsonify(
            {
                "success": True,
                "message": f"Successfully removed {practice_count} practice times from the schedule!",
                "count": practice_count,
                "series": user_series,
                "club": user_club,
            }
        )

    except Exception as e:
        print(f"Error removing practice times: {str(e)}")
        return (
            jsonify({"success": False, "message": "An unexpected error occurred"}),
            500,
        )


def get_team_schedule_data_data():
    """Get team schedule data - OPTIMIZED for faster loading with priority-based team detection"""
    try:
        import json
        import os
        import traceback
        from datetime import datetime

        from flask import jsonify, session

        from database_utils import execute_query, execute_query_one

        # Import the get_matches_for_user_club function
        from routes.act.schedule import get_matches_for_user_club

        print("\n=== TEAM SCHEDULE DATA API REQUEST (OPTIMIZED) ===")
        # Get the team from user's session data
        user = session.get("user")
        if not user:
            print("❌ No user in session")
            return jsonify({"error": "Not authenticated"}), 401

        user_email = user.get("email")
        print(f"User: {user_email}")

        # PRIORITY-BASED TEAM DETECTION (same as analyze-me, track-byes-courts, and polls pages)
        user_team_id = None
        user_team_name = None
        club_name = None
        series = None
        
        # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
        session_team_id = user.get("team_id")
        print(f"[DEBUG] Team-schedule: session_team_id from user: {session_team_id}")
        
        if session_team_id:
            try:
                # Get team info for the specific team_id from session
                session_team_query = """
                    SELECT t.id, t.team_name, c.name as club_name, s.name as series_name
                    FROM teams t
                    JOIN clubs c ON t.club_id = c.id
                    JOIN series s ON t.series_id = s.id
                    WHERE t.id = %s
                """
                session_team_result = execute_query_one(session_team_query, [session_team_id])
                if session_team_result:
                    user_team_id = session_team_result['id'] 
                    user_team_name = session_team_result['team_name']
                    club_name = session_team_result['club_name']
                    series = session_team_result['series_name']
                    print(f"[DEBUG] Team-schedule: Using team_id from session: team_id={user_team_id}, team_name={user_team_name}, club={club_name}, series={series}")
                else:
                    print(f"[DEBUG] Team-schedule: Session team_id {session_team_id} not found in teams table")
            except Exception as e:
                print(f"[DEBUG] Team-schedule: Error getting team from session team_id {session_team_id}: {e}")
        
        # PRIORITY 2: Use team_context from user if provided (from composite player URL)
        if not user_team_id:
            team_context = user.get("team_context") if user else None
            if team_context:
                try:
                    # Get team info for the specific team_id from team context
                    team_context_query = """
                        SELECT t.id, t.team_name, c.name as club_name, s.name as series_name
                        FROM teams t
                        JOIN clubs c ON t.club_id = c.id
                        JOIN series s ON t.series_id = s.id
                        WHERE t.id = %s
                    """
                    team_context_result = execute_query_one(team_context_query, [team_context])
                    if team_context_result:
                        user_team_id = team_context_result['id'] 
                        user_team_name = team_context_result['team_name']
                        club_name = team_context_result['club_name']
                        series = team_context_result['series_name']
                        print(f"[DEBUG] Team-schedule: Using team_context from URL: team_id={user_team_id}, team_name={user_team_name}, club={club_name}, series={series}")
                    else:
                        print(f"[DEBUG] Team-schedule: team_context {team_context} not found in teams table")
                except Exception as e:
                    print(f"[DEBUG] Team-schedule: Error getting team from team_context {team_context}: {e}")
        
        # PRIORITY 3: Fallback to legacy session club/series if no direct team_id
        if not user_team_id:
            print(f"[DEBUG] Team-schedule: No direct team_id, using legacy session club/series")
            club_name = user.get("club")
            series = user.get("series")
            
            if not club_name or not series:
                print("❌ Missing club or series in session")
                return jsonify({"error": "Club or series not set in profile"}), 400
                
            print(f"[DEBUG] Team-schedule: Legacy fallback: club={club_name}, series={series}")

        print(f"[DEBUG] Team-schedule: Final team selection: team_id={user_team_id}, club={club_name}, series={series}")

        if not club_name or not series:
            print("❌ Missing club or series after team detection")
            return jsonify({"error": "Club or series not set in profile"}), 400

        # Get series ID first since we want all players in the series
        series_query = "SELECT id, name FROM series WHERE name = %(name)s"
        print(f"Executing series query: {series_query}")

        try:
            series_record = execute_query(series_query, {"name": series})
        except Exception as e:
            print(f"❌ Database error querying series: {e}")
            # Continue without database series ID - we can still show the schedule
            series_record = [{"id": None, "name": series}]

        if not series_record:
            print(f"❌ Series not found: {series}")
            # Continue without database series ID - we can still show the schedule
            series_record = [{"id": None, "name": series}]

        series_record = series_record[0]
        print(f"✓ Using series: {series_record}")

        # Get all players from database for this series and club
        try:
            # Query players from the database instead of JSON file
            players_query = """
                SELECT 
                    p.id as player_id,
                    p.first_name,
                    p.last_name,
                    c.name as club_name,
                    s.name as series_name,
                    p.tenniscores_player_id,
                    l.league_id
                FROM players p
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id  
                JOIN leagues l ON p.league_id = l.id
                WHERE s.name = %(series)s 
                AND c.name = %(club_name)s
            """

            # Add league filtering if user has a league_id
            user_league_id = user.get("league_id", "")
            if user_league_id:
                try:
                    league_id_int = int(user_league_id)
                    players_query += " AND l.id = %(league_id)s"  # Use l.id (primary key) instead of l.league_id
                    players_params = {
                        "series": series,
                        "club_name": club_name,
                        "league_id": league_id_int,
                    }
                except (ValueError, TypeError) as e:
                    print(
                        f"Warning: Invalid league_id '{user_league_id}', skipping league filter: {e}"
                    )
                    players_params = {"series": series, "club_name": club_name}
            else:
                players_params = {"series": series, "club_name": club_name}

            print(f"Executing players query: {players_query}")
            print(f"With parameters: {players_params}")

            players_data = execute_query(players_query, players_params)

            # Format players data
            team_players = []
            for player in players_data:
                full_name = f"{player['first_name']} {player['last_name']}"
                team_players.append(
                    {
                        "player_name": full_name,
                        "club_name": player["club_name"],
                        "player_id": player[
                            "tenniscores_player_id"
                        ],  # Use tenniscores_player_id for consistency
                        "internal_id": player[
                            "player_id"
                        ],  # Store internal DB ID for availability queries
                    }
                )

            print(
                f"✓ Found {len(team_players)} players in database for {club_name} - {series}"
            )

            if not team_players:
                print("❌ No players found in database")
                return (
                    jsonify({"error": f"No players found for {club_name} - {series}"}),
                    404,
                )

        except Exception as e:
            print(f"❌ Error querying players from database: {e}")
            return jsonify({"error": "Error loading player data from database"}), 500

        # Use the same logic as get_matches_for_user_club to get matches
        print("\n=== Getting matches using same logic as availability page ===")
        
        # ENHANCED: Pass the detected team_id to get_matches_for_user_club for better reliability
        user_with_team_id = user.copy()
        if user_team_id:
            user_with_team_id["team_id"] = user_team_id
            print(f"[DEBUG] Team-schedule: Passing team_id {user_team_id} to get_matches_for_user_club")
        
        matches = get_matches_for_user_club(user_with_team_id)

        if not matches:
            print("❌ No upcoming matches found")
            
            # IMPROVED ERROR HANDLING: Check if team exists but just has no upcoming schedule
            if user_team_id:
                # Check if this team has any completed matches (to confirm team exists and is active)
                # UPDATED: Show all historical matches (removed 6-month filter to support completed seasons)
                completed_matches_query = """
                    SELECT COUNT(*) as count
                    FROM match_scores 
                    WHERE (home_team_id = %s OR away_team_id = %s)
                """
                
                try:
                    completed_result = execute_query_one(completed_matches_query, [user_team_id, user_team_id])
                    completed_count = completed_result["count"] if completed_result else 0
                    
                    if completed_count > 0:
                        # Team exists and has completed matches, just no upcoming schedule  
                        print(f"✓ Team {user_team_id} has {completed_count} completed matches but no upcoming schedule")
                        return jsonify({
                            "players_schedule": {},
                            "match_dates": [],
                            "event_details": {},
                            "message": f"No upcoming matches scheduled for your team. Your team has played {completed_count} matches total. You can view historical schedule data on other pages.",
                            "team_status": "active_no_schedule"
                        })
                    else:
                        # Team exists but no match activity
                        print(f"⚠️ Team {user_team_id} has no match history")
                        return jsonify({
                            "players_schedule": {},
                            "match_dates": [],
                            "event_details": {},
                            "message": "No upcoming matches scheduled and no match history for your team.",
                            "team_status": "inactive"
                        })
                        
                except Exception as e:
                    print(f"Error checking completed matches: {e}")
            
            # Fallback error for teams without team_id or when query fails
            return jsonify({
                "players_schedule": {},
                "match_dates": [],
                "event_details": {},
                "message": "No upcoming matches or practices found for your team.",
                "team_status": "no_schedule"
            })

        print(f"✓ Found {len(matches)} matches/practices")

        # Convert matches to the format expected by team schedule page
        event_dates = []
        event_details = {}

        for match in matches:
            match_date = match.get("date", "")
            if not match_date:
                continue

            try:
                # Convert from MM/DD/YYYY to YYYY-MM-DD
                date_obj = datetime.strptime(match_date, "%m/%d/%Y")
                formatted_date = date_obj.strftime("%Y-%m-%d")

                event_dates.append(formatted_date)

                # Determine event details based on match type
                if match.get("type") == "practice":
                    event_details[formatted_date] = {
                        "type": "Practice",
                        "description": match.get("description", "Team Practice"),
                        "location": match.get("location", club_name),
                        "time": match.get("time", ""),
                    }
                    print(f"✓ Added practice date: {match_date}")
                else:
                    # It's a match
                    home_team = match.get("home_team", "")
                    away_team = match.get("away_team", "")

                    # Determine opponent
                    # Extract the number from the series name and use it directly for the team suffix
                    # E.g., "Chicago 22" -> "22", "Chicago 6" -> "6"
                    series_number = series.split()[-1] if " " in series else series
                    team_suffix = series_number
                    user_team_pattern = f"{club_name} - {team_suffix}"
                    print(
                        f"Using team pattern: {user_team_pattern} (series: {series} -> suffix: {team_suffix})"
                    )

                    opponent = ""
                    if home_team == user_team_pattern:
                        opponent = away_team.replace(f" - {team_suffix}", "").strip()
                    elif away_team == user_team_pattern:
                        opponent = home_team.replace(f" - {team_suffix}", "").strip()

                    event_details[formatted_date] = {
                        "type": "Match",
                        "opponent": opponent,
                        "home_team": home_team,
                        "away_team": away_team,
                        "location": match.get("location", ""),
                        "time": match.get("time", ""),
                    }
                    print(
                        f"✓ Added match date: {match_date} - {user_team_pattern} vs {opponent}"
                    )

            except ValueError as e:
                print(f"Invalid date format: {match_date}, error: {e}")
                continue

        event_dates = sorted(list(set(event_dates)))  # Remove duplicates and sort
        print(f"✓ Found {len(event_dates)} total event dates (matches + practices)")

        # OPTIMIZATION: Batch fetch all availability data in one query instead of N+M individual queries
        print("\n=== OPTIMIZATION: Batch fetching all availability data ===")
        availability_lookup = {}  # (player_id, date) -> {status, notes}
        
        if series_record["id"] is not None and team_players and event_dates:
            try:
                # Get all player IDs for the query
                player_ids = [p["internal_id"] for p in team_players if p.get("internal_id")]
                player_names = [p["player_name"] for p in team_players]
                
                # Convert event_dates to date objects for the query
                date_objects = []
                for event_date in event_dates:
                    try:
                        date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
                        date_objects.append(date_obj)
                    except ValueError:
                        continue
                
                if player_ids and date_objects:
                    # Single optimized query to get ALL availability data at once
                    batch_query = """
                        SELECT 
                            player_id,
                            player_name,
                            DATE(match_date AT TIME ZONE 'UTC') as match_date,
                            availability_status,
                            notes
                        FROM player_availability pa
                        JOIN players p ON pa.player_id = p.id
                        WHERE pa.series_id = p.series_id 
                        AND (
                            pa.player_id = ANY(%(player_ids)s) 
                            OR pa.player_name = ANY(%(player_names)s)
                        )
                        AND DATE(pa.match_date AT TIME ZONE 'UTC') = ANY(%(dates)s)
                    """
                    
                    batch_params = {
                        "player_ids": player_ids,
                        "player_names": player_names,
                        "dates": date_objects,
                    }
                    
                    print(f"✓ Executing single batch query for {len(player_ids)} players and {len(date_objects)} dates")
                    availability_records = execute_query(batch_query, batch_params)
                    
                    # Build lookup dictionaries for fast access
                    for record in availability_records:
                        player_id = record.get("player_id")
                        player_name = record.get("player_name")
                        match_date = record.get("match_date")
                        status = record.get("availability_status", 0)
                        notes = record.get("notes", "")
                        
                        # Create lookup keys for both player_id and player_name
                        if player_id and match_date:
                            availability_lookup[(player_id, match_date)] = {"status": status, "notes": notes}
                        if player_name and match_date:
                            availability_lookup[(player_name, match_date)] = {"status": status, "notes": notes}
                    
                    print(f"✓ Built availability lookup with {len(availability_records)} records")
                
            except Exception as e:
                print(f"Warning: Batch availability query failed, falling back to defaults: {e}")
                availability_lookup = {}

        # Build player schedules using the optimized lookup
        players_schedule = {}
        print("\nProcessing player availability (OPTIMIZED):")
        
        for player in team_players:
            availability = []
            player_name = player["player_name"]
            internal_player_id = player.get("internal_id")
            
            print(f"✓ Processing {player_name} (ID: {internal_player_id})")

            for event_date in event_dates:
                try:
                    # Convert event_date string to datetime.date object for lookup
                    event_date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()

                    # Fast lookup instead of database query
                    status = 0  # Default
                    notes = ""
                    
                    # Try lookup by internal player_id first
                    if internal_player_id:
                        lookup_data = availability_lookup.get((internal_player_id, event_date_obj))
                        if lookup_data:
                            status = lookup_data["status"]
                            notes = lookup_data["notes"]
                    
                    # Fallback to player_name lookup if needed
                    if status == 0 and not notes:
                        lookup_data = availability_lookup.get((player_name, event_date_obj))
                        if lookup_data:
                            status = lookup_data["status"]
                            notes = lookup_data["notes"]

                    # Get event details for this date
                    event_info = event_details.get(event_date, {})

                    # Keep date in YYYY-MM-DD format for frontend JavaScript compatibility
                    # The formatDateString function in team_schedule.html expects YYYY-MM-DD format
                    frontend_date = event_date  # Already in YYYY-MM-DD format

                    availability.append(
                        {
                            "date": frontend_date,
                            "availability_status": status,
                            "notes": notes,
                            "event_type": event_info.get("type", "Unknown"),
                            "opponent": event_info.get("opponent", ""),
                            "home_team": event_info.get("home_team", ""),
                            "away_team": event_info.get("away_team", ""),
                            "description": event_info.get("description", ""),
                            "location": event_info.get("location", ""),
                            "time": event_info.get("time", ""),
                        }
                    )
                except Exception as e:
                    print(
                        f"Error processing availability for {player_name} on {event_date}: {e}"
                    )
                    # Skip this date if there's an error
                    continue

            # Store player schedule
            players_schedule[player_name] = availability
            print(f"✓ Added {player_name} with {len(availability)} dates")

        if not players_schedule:
            print("❌ No player schedules created")
            return jsonify({"error": "No player schedules found for your series"}), 404

        print(f"\n✅ OPTIMIZATION COMPLETE:")
        print(f"✓ Final players_schedule has {len(players_schedule)} players")
        print(f"✓ Event details for {len(event_details)} dates")
        print(f"✓ Used single batch query instead of {len(team_players) * len(event_dates)} individual queries")

        # Return JSON response
        return jsonify(
            {
                "players_schedule": players_schedule,
                "match_dates": event_dates,
                "event_details": event_details,
            }
        )

    except Exception as e:
        print(f"❌ Error in get_team_schedule_data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500


def get_all_teams_schedule_data_data():
    """Get all teams schedule data with team filter - OPTIMIZED for faster loading with priority-based team detection"""
    try:
        import json
        import os
        import traceback
        from datetime import datetime

        from flask import jsonify, session, request

        from database_utils import execute_query, execute_query_one

        # Import the get_matches_for_user_club function
        from routes.act.schedule import get_matches_for_user_club

        print("\n=== ALL TEAMS SCHEDULE DATA API REQUEST (OPTIMIZED) ===")
        # Get the team from user's session data
        user = session.get("user")
        if not user:
            print("❌ No user in session")
            return jsonify({"error": "Not authenticated"}), 401

        user_email = user.get("email")
        print(f"User: {user_email}")

        # Get the selected team_id from the request
        selected_team_id = request.args.get('team_id')
        print(f"Selected team_id: {selected_team_id}")

        # PRIORITY-BASED TEAM DETECTION (same as analyze-me, track-byes-courts, and polls pages)
        user_team_id = None
        user_team_name = None
        club_name = None
        series = None
        
        # If a specific team is selected, use that team_id
        if selected_team_id:
            try:
                # Get team info for the selected team_id
                selected_team_query = """
                    SELECT t.id, t.team_name, c.name as club_name, s.name as series_name
                    FROM teams t
                    JOIN clubs c ON t.club_id = c.id
                    JOIN series s ON t.series_id = s.id
                    WHERE t.id = %s
                """
                selected_team_result = execute_query_one(selected_team_query, [selected_team_id])
                if selected_team_result:
                    user_team_id = selected_team_result['id'] 
                    user_team_name = selected_team_result['team_name']
                    club_name = selected_team_result['club_name']
                    series = selected_team_result['series_name']
                    print(f"[DEBUG] All-teams-schedule: Using selected team_id: team_id={user_team_id}, team_name={user_team_name}, club={club_name}, series={series}")
                else:
                    print(f"[DEBUG] All-teams-schedule: Selected team_id {selected_team_id} not found in teams table")
            except Exception as e:
                print(f"[DEBUG] All-teams-schedule: Error getting team from selected team_id {selected_team_id}: {e}")
        
        # If no team selected, fall back to user's current team
        if not user_team_id:
            # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
            session_team_id = user.get("team_id")
            print(f"[DEBUG] All-teams-schedule: session_team_id from user: {session_team_id}")
            
            if session_team_id:
                try:
                    # Get team info for the specific team_id from session
                    session_team_query = """
                        SELECT t.id, t.team_name, c.name as club_name, s.name as series_name
                        FROM teams t
                        JOIN clubs c ON t.club_id = c.id
                        JOIN series s ON t.series_id = s.id
                        WHERE t.id = %s
                    """
                    session_team_result = execute_query_one(session_team_query, [session_team_id])
                    if session_team_result:
                        user_team_id = session_team_result['id'] 
                        user_team_name = session_team_result['team_name']
                        club_name = session_team_result['club_name']
                        series = session_team_result['series_name']
                        print(f"[DEBUG] All-teams-schedule: Using team_id from session: team_id={user_team_id}, team_name={user_team_name}, club={club_name}, series={series}")
                    else:
                        print(f"[DEBUG] All-teams-schedule: Session team_id {session_team_id} not found in teams table")
                except Exception as e:
                    print(f"[DEBUG] All-teams-schedule: Error getting team from session team_id {session_team_id}: {e}")
            
            # PRIORITY 2: Use team_context from user if provided (from composite player URL)
            if not user_team_id:
                team_context = user.get("team_context") if user else None
                if team_context:
                    try:
                        # Get team info for the specific team_id from team context
                        team_context_query = """
                            SELECT t.id, t.team_name, c.name as club_name, s.name as series_name
                            FROM teams t
                            JOIN clubs c ON t.club_id = c.id
                            JOIN series s ON t.series_id = s.id
                            WHERE t.id = %s
                        """
                        team_context_result = execute_query_one(team_context_query, [team_context])
                        if team_context_result:
                            user_team_id = team_context_result['id'] 
                            user_team_name = team_context_result['team_name']
                            club_name = team_context_result['club_name']
                            series = team_context_result['series_name']
                            print(f"[DEBUG] All-teams-schedule: Using team_context from URL: team_id={user_team_id}, team_name={user_team_name}, club={club_name}, series={series}")
                        else:
                            print(f"[DEBUG] All-teams-schedule: team_context {team_context} not found in teams table")
                    except Exception as e:
                        print(f"[DEBUG] All-teams-schedule: Error getting team from team_context {team_context}: {e}")
            
            # PRIORITY 3: Fallback to legacy session club/series if no direct team_id
            if not user_team_id:
                print(f"[DEBUG] All-teams-schedule: No direct team_id, using legacy session club/series")
                club_name = user.get("club")
                series = user.get("series")
                
                if not club_name or not series:
                    print("❌ Missing club or series in session")
                    return jsonify({"error": "Club or series not set in profile"}), 400
                    
                print(f"[DEBUG] All-teams-schedule: Legacy fallback: club={club_name}, series={series}")

        print(f"[DEBUG] All-teams-schedule: Final team selection: team_id={user_team_id}, club={club_name}, series={series}")

        if not club_name or not series:
            print("❌ Missing club or series after team detection")
            return jsonify({"error": "Club or series not set in profile"}), 400

        # Get series ID first since we want all players in the series
        series_query = "SELECT id, name FROM series WHERE name = %(name)s"
        print(f"Executing series query: {series_query}")

        try:
            series_record = execute_query(series_query, {"name": series})
        except Exception as e:
            print(f"❌ Database error querying series: {e}")
            # Continue without database series ID - we can still show the schedule
            series_record = [{"id": None, "name": series}]

        if not series_record:
            print(f"❌ Series not found: {series}")
            # Continue without database series ID - we can still show the schedule
            series_record = [{"id": None, "name": series}]

        series_record = series_record[0]
        print(f"✓ Using series: {series_record}")

        # Get all players from database for this series and club
        try:
            # Query players from the database instead of JSON file
            players_query = """
                SELECT 
                    p.id as player_id,
                    p.first_name,
                    p.last_name,
                    c.name as club_name,
                    s.name as series_name,
                    p.tenniscores_player_id,
                    l.league_id
                FROM players p
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id  
                JOIN leagues l ON p.league_id = l.id
                WHERE s.name = %(series)s 
                AND c.name = %(club_name)s
            """

            # Add league filtering if user has a league_id
            user_league_id = user.get("league_id", "")
            if user_league_id:
                try:
                    league_id_int = int(user_league_id)
                    players_query += " AND l.id = %(league_id)s"  # Use l.id (primary key) instead of l.league_id
                    players_params = {
                        "series": series,
                        "club_name": club_name,
                        "league_id": league_id_int,
                    }
                except (ValueError, TypeError) as e:
                    print(
                        f"Warning: Invalid league_id '{user_league_id}', skipping league filter: {e}"
                    )
                    players_params = {"series": series, "club_name": club_name}
            else:
                players_params = {"series": series, "club_name": club_name}

            print(f"Executing players query: {players_query}")
            print(f"With parameters: {players_params}")

            players_data = execute_query(players_query, players_params)

            # Format players data
            team_players = []
            for player in players_data:
                full_name = f"{player['first_name']} {player['last_name']}"
                team_players.append(
                    {
                        "player_name": full_name,
                        "club_name": player["club_name"],
                        "player_id": player[
                            "tenniscores_player_id"
                        ],  # Use tenniscores_player_id for consistency
                        "internal_id": player[
                            "player_id"
                        ],  # Store internal DB ID for availability queries
                    }
                )

            print(
                f"✓ Found {len(team_players)} players in database for {club_name} - {series}"
            )

            if not team_players:
                print("❌ No players found in database")
                return (
                    jsonify({"error": f"No players found for {club_name} - {series}"}),
                    404,
                )

        except Exception as e:
            print(f"❌ Error querying players from database: {e}")
            return jsonify({"error": "Error loading player data from database"}), 500

        # Use the same logic as get_matches_for_user_club to get matches
        print("\n=== Getting matches using same logic as availability page ===")
        
        # ENHANCED: Pass the detected team_id to get_matches_for_user_club for better reliability
        user_with_team_id = user.copy()
        if user_team_id:
            user_with_team_id["team_id"] = user_team_id
            print(f"[DEBUG] All-teams-schedule: Passing team_id {user_team_id} to get_matches_for_user_club")
        
        all_events = get_matches_for_user_club(user_with_team_id)
        
        # Filter for only practice times
        matches = [event for event in all_events if event.get("type") == "practice"]

        if not matches:
            print("❌ No upcoming practice times found")
            
            # IMPROVED ERROR HANDLING: Check if team exists but just has no upcoming schedule
            if user_team_id:
                # Check if this team has any completed matches (to confirm team exists and is active)
                # UPDATED: Show all historical matches (removed 6-month filter to support completed seasons)
                completed_matches_query = """
                    SELECT COUNT(*) as count
                    FROM match_scores 
                    WHERE (home_team_id = %s OR away_team_id = %s)
                """
                
                try:
                    completed_result = execute_query_one(completed_matches_query, [user_team_id, user_team_id])
                    completed_count = completed_result["count"] if completed_result else 0
                    
                    if completed_count > 0:
                        # Team exists and has completed matches, just no upcoming schedule  
                        print(f"✓ Team {user_team_id} has {completed_count} completed matches but no upcoming schedule")
                        return jsonify({
                            "players_schedule": {},
                            "match_dates": [],
                            "event_details": {},
                            "message": f"No upcoming practice times scheduled for your team. Your team has played {completed_count} matches total. You can view historical schedule data on other pages.",
                            "team_status": "active_no_schedule"
                        })
                    else:
                        # Team exists but no match activity
                        print(f"⚠️ Team {user_team_id} has no match history")
                        return jsonify({
                            "players_schedule": {},
                            "match_dates": [],
                            "event_details": {},
                            "message": "No upcoming practice times scheduled and no match history for your team.",
                            "team_status": "inactive"
                        })
                        
                except Exception as e:
                    print(f"Error checking completed matches: {e}")
            
            # Fallback error for teams without team_id or when query fails
            return jsonify({
                "players_schedule": {},
                "match_dates": [],
                "event_details": {},
                "message": "No upcoming practice times found for your team.",
                "team_status": "no_schedule"
            })

        print(f"✓ Found {len(matches)} practice times")

        # Convert matches to the format expected by team schedule page
        event_dates = []
        event_details = {}

        for match in matches:
            match_date = match.get("date", "")
            if not match_date:
                continue

            try:
                # Convert from MM/DD/YYYY to YYYY-MM-DD
                date_obj = datetime.strptime(match_date, "%m/%d/%Y")
                formatted_date = date_obj.strftime("%Y-%m-%d")

                event_dates.append(formatted_date)

                # All events are practice times now
                event_details[formatted_date] = {
                    "type": "Practice",
                    "description": match.get("description", "Team Practice"),
                    "location": match.get("location", club_name),
                    "time": match.get("time", ""),
                }
                print(f"✓ Added practice date: {match_date}")

            except ValueError as e:
                print(f"Invalid date format: {match_date}, error: {e}")
                continue

        event_dates = sorted(list(set(event_dates)))  # Remove duplicates and sort
        print(f"✓ Found {len(event_dates)} total practice dates")

        # OPTIMIZATION: Batch fetch all availability data in one query instead of N+M individual queries
        print("\n=== OPTIMIZATION: Batch fetching all availability data ===")
        availability_lookup = {}  # (player_id, date) -> {status, notes}
        
        if series_record["id"] is not None and team_players and event_dates:
            try:
                # Get all player IDs for the query
                player_ids = [p["internal_id"] for p in team_players if p.get("internal_id")]
                player_names = [p["player_name"] for p in team_players]
                
                # Convert event_dates to date objects for the query
                date_objects = []
                for event_date in event_dates:
                    try:
                        date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
                        date_objects.append(date_obj)
                    except ValueError:
                        continue
                
                if player_ids and date_objects:
                    # Single optimized query to get ALL availability data at once
                    batch_query = """
                        SELECT 
                            player_id,
                            player_name,
                            DATE(match_date AT TIME ZONE 'UTC') as match_date,
                            availability_status,
                            notes
                        FROM player_availability pa
                        JOIN players p ON pa.player_id = p.id
                        WHERE pa.series_id = p.series_id 
                        AND (
                            pa.player_id = ANY(%(player_ids)s) 
                            OR pa.player_name = ANY(%(player_names)s)
                        )
                        AND DATE(pa.match_date AT TIME ZONE 'UTC') = ANY(%(dates)s)
                    """
                    
                    batch_params = {
                        "player_ids": player_ids,
                        "player_names": player_names,
                        "dates": date_objects,
                    }
                    
                    print(f"✓ Executing single batch query for {len(player_ids)} players and {len(date_objects)} dates")
                    availability_records = execute_query(batch_query, batch_params)
                    
                    # Build lookup dictionaries for fast access
                    for record in availability_records:
                        player_id = record.get("player_id")
                        player_name = record.get("player_name")
                        match_date = record.get("match_date")
                        status = record.get("availability_status", 0)
                        notes = record.get("notes", "")
                        
                        # Create lookup keys for both player_id and player_name
                        if player_id and match_date:
                            availability_lookup[(player_id, match_date)] = {"status": status, "notes": notes}
                        if player_name and match_date:
                            availability_lookup[(player_name, match_date)] = {"status": status, "notes": notes}
                    
                    print(f"✓ Built availability lookup with {len(availability_records)} records")
                
            except Exception as e:
                print(f"Warning: Batch availability query failed, falling back to defaults: {e}")
                availability_lookup = {}

        # Build player schedules using the optimized lookup
        players_schedule = {}
        print("\nProcessing player availability (OPTIMIZED):")
        
        for player in team_players:
            availability = []
            player_name = player["player_name"]
            internal_player_id = player.get("internal_id")
            
            print(f"✓ Processing {player_name} (ID: {internal_player_id})")

            for event_date in event_dates:
                try:
                    # Convert event_date string to datetime.date object for lookup
                    event_date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()

                    # Fast lookup instead of database query
                    status = 0  # Default
                    notes = ""
                    
                    # Try lookup by internal player_id first
                    if internal_player_id:
                        lookup_data = availability_lookup.get((internal_player_id, event_date_obj))
                        if lookup_data:
                            status = lookup_data["status"]
                            notes = lookup_data["notes"]
                    
                    # Fallback to player_name lookup if needed
                    if status == 0 and not notes:
                        lookup_data = availability_lookup.get((player_name, event_date_obj))
                        if lookup_data:
                            status = lookup_data["status"]
                            notes = lookup_data["notes"]

                    # Get event details for this date
                    event_info = event_details.get(event_date, {})

                    # Keep date in YYYY-MM-DD format for frontend JavaScript compatibility
                    # The formatDateString function in team_schedule.html expects YYYY-MM-DD format
                    frontend_date = event_date  # Already in YYYY-MM-DD format

                    availability.append(
                        {
                            "date": frontend_date,
                            "availability_status": status,
                            "notes": notes,
                            "event_type": event_info.get("type", "Unknown"),
                            "opponent": event_info.get("opponent", ""),
                            "home_team": event_info.get("home_team", ""),
                            "away_team": event_info.get("away_team", ""),
                            "description": event_info.get("description", ""),
                            "location": event_info.get("location", ""),
                            "time": event_info.get("time", ""),
                        }
                    )
                except Exception as e:
                    print(
                        f"Error processing availability for {player_name} on {event_date}: {e}"
                    )
                    # Skip this date if there's an error
                    continue

            # Store player schedule
            players_schedule[player_name] = availability
            print(f"✓ Added {player_name} with {len(availability)} dates")

        if not players_schedule:
            print("❌ No player schedules created")
            return jsonify({"error": "No player schedules found for your series"}), 404

        print(f"\n✅ OPTIMIZATION COMPLETE:")
        print(f"✓ Final players_schedule has {len(players_schedule)} players")
        print(f"✓ Event details for {len(event_details)} dates")
        print(f"✓ Used single batch query instead of {len(team_players) * len(event_dates)} individual queries")

        # Return JSON response
        return jsonify(
            {
                "players_schedule": players_schedule,
                "match_dates": event_dates,
                "event_details": event_details,
            }
        )

    except Exception as e:
        print(f"❌ Error in get_all_teams_schedule_data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500


def add_practice_times_data():
    """API endpoint to add practice times to the schedule"""
    try:
        import json
        import os
        from datetime import datetime, timedelta
        from flask import jsonify, session, request

        from utils.logging import log_user_activity

        # Get form data
        data = request.form
        
        # Validate required fields
        first_date = data.get("first_date")
        last_date = data.get("last_date")
        day = data.get("day")
        time = data.get("time")
        
        if not all([first_date, last_date, day, time]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        
        # Parse dates
        try:
            first_date_obj = datetime.strptime(first_date, "%Y-%m-%d").date()
            last_date_obj = datetime.strptime(last_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format"}), 400
        
        # Get user's team information
        user = session["user"]
        user_club = user.get("club", "")
        user_series = user.get("series", "")
        
        if not user_club:
            return jsonify({"success": False, "message": "User club not found"}), 400
        
        if not user_series:
            return jsonify({"success": False, "message": "User series not found"}), 400
        
        # Get team_id using the same priority-based logic as removal
        user_team_id = None
        
        # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
        session_team_id = user.get("team_id")
        print(f"[DEBUG] Practice addition: session_team_id from user: {session_team_id}")
        
        if session_team_id:
            user_team_id = session_team_id
            print(f"[DEBUG] Practice addition: Using team_id from session: {user_team_id}")
        
        # PRIORITY 2: Use team_context from user if provided
        if not user_team_id:
            team_context = user.get("team_context")
            if team_context:
                user_team_id = team_context
                print(f"[DEBUG] Practice addition: Using team_context: {user_team_id}")
        
        # PRIORITY 3: Fallback to session service
        if not user_team_id:
            try:
                from app.services.session_service import get_session_data_for_user
                session_data = get_session_data_for_user(user["email"])
                if session_data:
                    user_team_id = session_data.get("team_id")
                    print(f"[DEBUG] Practice addition: Found team_id via session service: {user_team_id}")
            except Exception as e:
                print(f"Could not get team ID via session service: {e}")
        
        if not user_team_id:
            return jsonify({"success": False, "message": "Could not determine your team. Please check your profile settings."}), 400
        
        # Generate practice dates between first_date and last_date for the specified day
        practice_dates = []
        current_date = first_date_obj
        
        while current_date <= last_date_obj:
            if current_date.strftime("%A") == day:
                practice_dates.append(current_date)
            current_date += timedelta(days=1)
        
        if not practice_dates:
            return jsonify({"success": False, "message": f"No {day}s found between {first_date} and {last_date}"}), 400
        
        # Get league_id from the team (not from user, to avoid NULL issues)
        from database_utils import execute_query, execute_query_one
        
        team_league_result = execute_query_one(
            "SELECT league_id FROM teams WHERE id = %s",
            [user_team_id]
        )
        
        league_id = team_league_result["league_id"] if team_league_result else None
        print(f"[DEBUG] Practice addition: team_league_result={team_league_result}, league_id={league_id}")
        
        # Get the actual team and series names from the database (not from user session)
        team_info = execute_query_one(
            """SELECT t.team_name, s.name as series_name, c.name as club_name 
               FROM teams t 
               JOIN series s ON t.series_id = s.id 
               JOIN clubs c ON t.club_id = c.id 
               WHERE t.id = %s""",
            [user_team_id]
        )
        
        if not team_info:
            return jsonify({"success": False, "message": "Could not find team information"}), 400
        
        actual_team_name = team_info["team_name"]
        actual_series_name = team_info["series_name"] 
        actual_club_name = team_info["club_name"]
        
        print(f"[DEBUG] Practice addition: actual_team_name={actual_team_name}, actual_series_name={actual_series_name}, actual_club_name={actual_club_name}")
        
        # Create practice description using actual team/series names from database
        practice_description = f"{actual_club_name} Practice - {actual_series_name}"
        print(f"[DEBUG] Practice addition: practice_description={practice_description}")
        
        # Insert practice times
        practices_added = []
        inserted_count = 0
        
        for practice_date in practice_dates:
            try:
                # Check if practice already exists using team_id and date only (ignore name variations)
                existing = execute_query_one(
                    "SELECT id FROM schedule WHERE home_team_id = %s AND match_date = %s AND home_team LIKE '%%Practice%%'",
                    [user_team_id, practice_date]
                )
                
                if not existing:
                    # Insert new practice time
                    result = execute_query(
                        """INSERT INTO schedule 
                           (league_id, home_team_id, home_team, match_date, match_time)
                           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                        [league_id, user_team_id, practice_description, practice_date, time]
                    )
                    
                    if result:
                        inserted_count += 1
                        practices_added.append({
                            "date": practice_date.strftime("%Y-%m-%d"),
                            "time": time
                        })
                        print(f"✓ Added practice: {practice_date} at {time}")
                    else:
                        print(f"⚠️ Failed to insert practice: {practice_date} at {time}")
                else:
                    print(f"⚠️ Practice already exists: {practice_date} at {time}")
                    
            except Exception as e:
                print(f"❌ Error adding practice for {practice_date}: {e}")
                continue
        
        if inserted_count == 0:
            return jsonify({
                "success": False, 
                "message": "No new practice times were added. They may already exist."
            }), 400
        
        # Log the activity
        log_user_activity(
            user["email"],
            "practice_times_added",
            details=f"Added {inserted_count} practice times for {user_series} {day}s at {time} at {user_club} (team_id: {user_team_id})",
        )
        
        return jsonify({
            "success": True,
            "message": f"Successfully added {inserted_count} practice times!",
            "count": inserted_count,
            "day": day,
            "time": time,
            "series": user_series,
            "club": user_club,
            "first_date": first_date,
            "last_date": last_date,
            "practices_added": practices_added
        })
        
    except Exception as e:
        print(f"Error adding practice times: {str(e)}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500
