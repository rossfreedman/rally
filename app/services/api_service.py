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
                    l.league_id
                FROM series_stats s
                LEFT JOIN leagues l ON s.league_id = l.id
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

            # TODO: Add court analysis from match_scores table if needed
            # For now, return basic team stats
            return jsonify(response)

        # If no team requested, get series standings for the user's series
        user = session.get("user")
        if not user or not user.get("series"):
            return jsonify({"error": "User series not found"}), 400

        user_series = user["series"]
        user_league_id = user.get("league_id")

        print(
            f"[DEBUG] Getting series stats for user series: {user_series}, league: {user_league_id}"
        )

        # CRITICAL FIX: Apply reverse series mapping
        # The user session contains database format (e.g., "S2B") but series_stats table 
        # uses user-facing format (e.g., "Series 2B"). Need to convert database format to user format.
        mapped_series = user_series  # Default to original
        
        if user_league_id:
            # Convert league_id to string format needed by team_format_mappings table
            league_id_str = None
            if isinstance(user_league_id, int):
                # Convert integer league_id to string league_id (e.g., 4554 -> "NSTF")
                try:
                    league_lookup = execute_query_one(
                        "SELECT league_id FROM leagues WHERE id = %s", [user_league_id]
                    )
                    if league_lookup:
                        league_id_str = league_lookup["league_id"]
                    else:
                        print(f"[DEBUG] Could not find string league_id for integer {user_league_id}")
                except Exception as e:
                    print(f"[DEBUG] Error looking up league_id: {e}")
            else:
                league_id_str = str(user_league_id)
            
            if league_id_str:
                print(f"[DEBUG] Using league_id_str: {league_id_str} for mapping lookup")
                
                # Simplified fallback for NSTF series mapping (known working patterns)
                if league_id_str == "NSTF" and user_series.startswith("S"):
                    # NSTF database format: S2B -> Series 2B
                    series_suffix = user_series[1:]  # Remove "S" prefix
                    mapped_series = f"Series {series_suffix}"
                    print(f"[DEBUG] Applied NSTF fallback mapping: '{user_series}' -> '{mapped_series}'")
                else:
                    # Try database query for other leagues
                    try:
                        reverse_mapping_query = """
                            SELECT user_input_format
                            FROM team_format_mappings
                            WHERE league_id = %s 
                            AND database_series_format = %s 
                            AND is_active = true
                            ORDER BY 
                                CASE WHEN user_input_format LIKE 'Series%' THEN 1 
                                     WHEN user_input_format LIKE 'Division%' THEN 2 
                                     ELSE 3 END,
                                LENGTH(user_input_format) DESC
                            LIMIT 1
                        """
                        
                        reverse_mapping = execute_query_one(reverse_mapping_query, [league_id_str, user_series])
                        
                        if reverse_mapping:
                            mapped_series = reverse_mapping["user_input_format"]
                            print(f"[DEBUG] Applied database reverse mapping: '{user_series}' -> '{mapped_series}' for league {league_id_str}")
                        else:
                            print(f"[DEBUG] No reverse mapping found for '{user_series}' in league {league_id_str}")
                            
                    except Exception as e:
                        print(f"[DEBUG] Reverse mapping query failed: {e}")
            else:
                print(f"[DEBUG] Could not determine string league_id from {user_league_id}")

        # Convert league_id string to integer foreign key if needed
        league_id_int = None
        if user_league_id:
            try:
                if isinstance(user_league_id, int):
                    league_id_int = user_league_id
                else:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                        print(
                            f"[DEBUG] Converted league_id '{user_league_id}' to integer: {league_id_int}"
                        )
            except Exception as e:
                print(f"[DEBUG] Could not convert league ID: {e}")

        # Query series stats from database, filtering by user's mapped series and league
        if league_id_int:
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
                    l.league_id
                FROM series_stats s
                LEFT JOIN leagues l ON s.league_id = l.id
                WHERE s.series = %s AND s.league_id = %s
                ORDER BY s.points DESC, s.team ASC
            """
            db_results = execute_query(series_stats_query, [mapped_series, league_id_int])
        else:
            # Fallback without league filtering
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
                    s.games_lost
                FROM series_stats s
                WHERE s.series = %s
                ORDER BY s.points DESC, s.team ASC
            """
            db_results = execute_query(series_stats_query, [mapped_series])

        print(f"[DEBUG] Found {len(db_results)} teams in mapped series '{mapped_series}' (original: '{user_series}')")

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
    """Research team data"""
    # Placeholder - will be filled with actual implementation from server.py
    return jsonify({"placeholder": "research_team"})


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

        # FIXED: Use team_id-based counting for accuracy (handle NULL league_id)
        practice_count_query = """
            SELECT COUNT(*) as count
            FROM schedule 
            WHERE home_team_id = %(team_id)s
            AND (league_id = %(league_id)s OR (league_id IS NULL AND %(league_id)s IS NOT NULL))
            AND home_team = %(practice_desc)s
        """

        try:
            practice_count_result = execute_query_one(
                practice_count_query,
                {
                    "team_id": user_team_id,
                    "league_id": league_id,
                    "practice_desc": practice_description,
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

        # FIXED: Remove practice entries using team_id for precision and security (handle NULL league_id)
        try:
            delete_query = """
                DELETE FROM schedule 
                WHERE home_team_id = %(team_id)s
                AND (league_id = %(league_id)s OR (league_id IS NULL AND %(league_id)s IS NOT NULL))
                AND home_team = %(practice_desc)s
            """

            execute_query(
                delete_query,
                {
                    "team_id": user_team_id,
                    "league_id": league_id,
                    "practice_desc": practice_description,
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
                completed_matches_query = """
                    SELECT COUNT(*) as count
                    FROM match_scores 
                    WHERE (home_team_id = %s OR away_team_id = %s)
                    AND match_date >= CURRENT_DATE - INTERVAL '6 months'
                """
                
                try:
                    completed_result = execute_query_one(completed_matches_query, [user_team_id, user_team_id])
                    completed_count = completed_result["count"] if completed_result else 0
                    
                    if completed_count > 0:
                        # Team exists and has recent matches, just no upcoming schedule
                        print(f"✓ Team {user_team_id} has {completed_count} recent completed matches but no upcoming schedule")
                        return jsonify({
                            "players_schedule": {},
                            "match_dates": [],
                            "event_details": {},
                            "message": f"No upcoming matches scheduled for your team. Your team has played {completed_count} matches in the last 6 months.",
                            "team_status": "active_no_schedule"
                        })
                    else:
                        # Team exists but no recent activity
                        print(f"⚠️ Team {user_team_id} has no recent matches")
                        return jsonify({
                            "players_schedule": {},
                            "match_dates": [],
                            "event_details": {},
                            "message": "No upcoming matches scheduled and no recent match activity for your team.",
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
                        FROM player_availability 
                        WHERE series_id = %(series_id)s 
                        AND (
                            player_id = ANY(%(player_ids)s) 
                            OR player_name = ANY(%(player_names)s)
                        )
                        AND DATE(match_date AT TIME ZONE 'UTC') = ANY(%(dates)s)
                    """
                    
                    batch_params = {
                        "series_id": series_record["id"],
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

                    availability.append(
                        {
                            "date": event_date,
                            "availability_status": status,
                            "notes": notes,
                            "event_type": event_info.get("type", "Unknown"),
                            "opponent": event_info.get("opponent", ""),
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
