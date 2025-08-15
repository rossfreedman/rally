"""
Mobile service module - handles all mobile-specific business logic
This module provides functions for mobile interface data processing and user interactions.
All data is loaded from database tables instead of JSON files for improved performance and consistency.
"""

import json
import os
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from urllib.parse import unquote

from database_utils import execute_query, execute_query_one, execute_update
from utils.date_utils import date_to_db_timestamp, normalize_date_string
from utils.logging import log_user_activity


def _load_players_data():
    """Load player data fresh from database with all statistics - no caching"""
    try:
        from database_utils import execute_query

        # Simple query that loads all players (we'll filter by league afterward)
        players_query = """
            SELECT 
                p.first_name as "First Name",
                p.last_name as "Last Name", 
                p.tenniscores_player_id as "Player ID",
                CASE WHEN p.pti IS NULL THEN 'N/A' ELSE p.pti::TEXT END as "PTI",
                COALESCE(p.wins, 0) as "Wins",
                COALESCE(p.losses, 0) as "Losses",
                c.name as "Club",
                s.name as "Series",
                l.league_id as "League",
                CASE 
                    WHEN COALESCE(p.wins, 0) + COALESCE(p.losses, 0) > 0 
                    THEN ROUND((COALESCE(p.wins, 0)::NUMERIC / (COALESCE(p.wins, 0) + COALESCE(p.losses, 0))) * 100, 1)::TEXT || '%'
                    ELSE '0%'
                END as "Win %"
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id  
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE p.tenniscores_player_id IS NOT NULL
            ORDER BY p.first_name, p.last_name
        """
        
        players_data = execute_query(players_query)
        print(f"Loaded fresh player data ({len(players_data)} players) from database")
        return players_data

    except Exception as e:
        print(f"Error loading player data from database: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []


def get_career_stats_from_db(player_id):
    """
    Get career stats from player_history table by player_id.
    Returns None if no historical data is found or if data is insufficient.
    """
    try:
        # Helper function to convert Decimal to float for template compatibility
        def decimal_to_float(value):
            """Convert Decimal to float, handle None values"""
            from decimal import Decimal
            if value is None:
                return None
            if isinstance(value, Decimal):
                return float(value)
            return value

        # First get the player's database ID
        player_query = """
            SELECT id FROM players WHERE tenniscores_player_id = %s
        """
        player_record = execute_query_one(player_query, [player_id])

        if not player_record:
            print(
                f"[DEBUG] get_career_stats_from_db: No player found for tenniscores_player_id {player_id}"
            )
            return None

        player_db_id = player_record["id"]

        # Query player_history table to get all historical PTI data
        career_query = """
            SELECT 
                date,
                end_pti,
                series
            FROM player_history
            WHERE player_id = %s
            ORDER BY date ASC
        """

        career_records = execute_query(career_query, [player_db_id])

        if not career_records or len(career_records) < 5:
            print(
                f"[DEBUG] get_career_stats_from_db: Insufficient career data for player {player_id} (found {len(career_records) if career_records else 0} records, need at least 5)"
            )
            # Try to get career stats anyway from players table even if not enough history

        # Get career stats directly from players table (imported from player_history.json)
        career_stats_query = """
            SELECT 
                career_wins,
                career_losses,
                career_matches,
                career_win_percentage,
                pti as current_pti
            FROM players
            WHERE id = %s
        """

        career_data = execute_query_one(career_stats_query, [player_db_id])

        if not career_data:
            print(
                f"[DEBUG] get_career_stats_from_db: No career data found for player {player_id}"
            )
            return None

        print(f"[DEBUG] Raw career data from DB: {career_data}")

        # Check if player has meaningful career data
        career_matches = career_data["career_matches"] or 0
        career_wins = career_data["career_wins"] or 0
        career_losses = career_data["career_losses"] or 0

        # Always show career stats even if 0 - remove the minimum requirement
        # This allows the UI to display the current state and shows that the feature is working
        # if career_matches < 1:  # Reduced from 5 to 1 to be less strict
        #     print(f"[DEBUG] get_career_stats_from_db: Insufficient career matches for player {player_id} (found {career_matches})")
        #     return None

        # Use the actual career data from JSON import
        total_matches = career_matches
        wins = career_wins
        losses = career_losses
        win_rate = decimal_to_float(career_data["career_win_percentage"]) or 0.0

        # Get current PTI as career PTI
        latest_pti = decimal_to_float(career_data["current_pti"]) or "N/A"

        career_stats = {
            "winRate": round(win_rate, 1),  # Convert to float and round
            "matches": total_matches,
            "wins": wins,
            "losses": losses,
            "pti": latest_pti,
        }

        print(
            f"[DEBUG] get_career_stats_from_db: Found career stats for player {player_id}: {total_matches} matches, {wins} wins, {losses} losses, {win_rate}% win rate"
        )
        return career_stats

    except Exception as e:
        print(
            f"[ERROR] get_career_stats_from_db: Error fetching career stats for player {player_id}: {e}"
        )
        return None


def get_player_analysis_by_name(player_name, viewing_user=None):
    """
    Returns the player analysis data for the given player name, as a dict.
    This function parses the player_name string into first and last name (if possible),
    then calls get_player_analysis with a constructed user dict.
    Handles single-word names gracefully.

    Args:
        player_name: Name of the player to analyze
        viewing_user: User object containing league_id for filtering data by league
    """
    # Defensive: handle empty or None
    if not player_name or not isinstance(player_name, str):
        return {
            "current_season": None,
            "court_analysis": {},
            "career_stats": None,
            "player_history": None,
            "videos": {"match": [], "practice": []},
            "trends": {},
            "career_pti_change": "N/A",
            "current_pti": None,
            "weekly_pti_change": None,
            "error": "Invalid player name.",
        }

    # Load player data from database based on viewing user's league for proper filtering
    try:
        # Note: execute_query and execute_query_one are already imported at module level

        # Get viewing user's league for filtering
        viewing_user_league = viewing_user.get("league_id", "") if viewing_user else ""

        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(viewing_user_league, str) and viewing_user_league != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [viewing_user_league]
                )
                if league_record:
                    league_id_int = league_record["id"]
                    print(
                        f"[DEBUG] Converted viewing user league_id '{viewing_user_league}' to integer: {league_id_int}"
                    )
                else:
                    print(
                        f"[WARNING] Viewing user league '{viewing_user_league}' not found in leagues table"
                    )
            except Exception as e:
                print(f"[DEBUG] Could not convert viewing user league ID: {e}")
        elif isinstance(viewing_user_league, int):
            league_id_int = viewing_user_league
            print(f"[DEBUG] Viewing user league_id already integer: {league_id_int}")

        # Query players table with league filtering
        if league_id_int:
            players_query = """
                SELECT 
                    first_name as "First Name",
                    last_name as "Last Name", 
                    tenniscores_player_id as "Player ID",
                    (SELECT name FROM clubs WHERE id = p.club_id) as "Club",
                    (SELECT name FROM series WHERE id = p.series_id) as "Series",
                    p.league_id as "League"
                FROM players p
                WHERE p.league_id = %s AND tenniscores_player_id IS NOT NULL
            """
            all_players_data = execute_query(players_query, [league_id_int])
        else:
            players_query = """
                SELECT 
                    first_name as "First Name",
                    last_name as "Last Name", 
                    tenniscores_player_id as "Player ID",
                    (SELECT name FROM clubs WHERE id = p.club_id) as "Club",
                    (SELECT name FROM series WHERE id = p.series_id) as "Series",
                    p.league_id as "League"
                FROM players p
                WHERE tenniscores_player_id IS NOT NULL
            """
            all_players_data = execute_query(players_query)

        print(f"[INFO] Loaded {len(all_players_data)} players from database")

    except Exception as e:
        print(f"[ERROR] Could not load players from database: {e}")
        all_players_data = []

    def normalize(name):
        return name.replace(",", "").replace("  ", " ").strip().lower()

    # Try to find the exact player by name matching
    player_name_normalized = normalize(player_name)
    found_player = None

    # If we have a league context, prioritize players from that league
    # If multiple players with same name exist, prefer the one from viewing user's league
    matching_players = []
    
    for p in all_players_data:
        # Construct full name from First Name and Last Name fields
        first_name = p.get("First Name", "")
        last_name = p.get("Last Name", "")
        full_name = f"{first_name} {last_name}".strip()
        player_record_name = normalize(full_name)

        if player_record_name == player_name_normalized:
            matching_players.append(p)
    
    if matching_players:
        if league_id_int and len(matching_players) > 1:
            # Multiple players found - prefer the one from viewing user's league
            for p in matching_players:
                if p.get("League") == league_id_int:
                    found_player = p
                    print(f"[DEBUG] Found player '{player_name}' from viewing user's league {league_id_int}")
                    break
            
            # If no player found in user's league, fall back to player with most data
            if not found_player:
                # Check which players have PTI data by looking for history records
                players_with_data = []
                for p in matching_players:
                    player_id = p.get("Player ID")
                    if player_id:
                        # Check if this player has PTI history
                        history_count_query = """
                            SELECT COUNT(*) as count 
                            FROM player_history ph 
                            JOIN players pl ON ph.player_id = pl.id 
                            WHERE pl.tenniscores_player_id = %s
                        """
                        history_result = execute_query_one(history_count_query, [player_id])
                        history_count = history_result["count"] if history_result else 0
                        players_with_data.append((p, history_count))
                
                # Sort by history count (descending) and pick the one with most data
                players_with_data.sort(key=lambda x: x[1], reverse=True)
                if players_with_data:
                    found_player = players_with_data[0][0]
                    data_count = players_with_data[0][1]
                    print(f"[DEBUG] Player '{player_name}' not found in user's league {league_id_int}, using player with most data: {data_count} history records from league {found_player.get('League')}")
                else:
                    found_player = matching_players[0]
                    print(f"[DEBUG] Player '{player_name}' not found in user's league {league_id_int}, using first match from league {found_player.get('League')}")
        else:
            # Single player found or no league context
            found_player = matching_players[0]
            print(f"[DEBUG] Found single player '{player_name}' from league {found_player.get('League')}")
    
    print(f"[DEBUG] Final selected player: {found_player.get('Player ID') if found_player else 'None'} from league {found_player.get('League') if found_player else 'None'}")

    if found_player:
        # If we found the player, create a better user dict with their player_id if available
        parts = player_name.strip().split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = " ".join(parts[1:])
        else:
            first_name = parts[0]
            last_name = parts[0]

        # Create user dict with potentially more complete information
        user_dict = {
            "first_name": first_name,
            "last_name": last_name,
            "tenniscores_player_id": found_player.get(
                "Player ID"
            ),  # Include player_id if available
            "league_id": found_player.get("League", "all"),  # Use League field
            "club": found_player.get("Club", ""),
            "series": found_player.get("Series", ""),
        }
    else:
        # Fallback to basic name parsing if no exact match found
        parts = player_name.strip().split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = " ".join(parts[1:])
        else:
            first_name = parts[0]
            last_name = parts[0]

        user_dict = {"first_name": first_name, "last_name": last_name}

    # Call get_player_analysis with constructed user dict
    result = get_player_analysis(user_dict)

    return result


def get_mobile_schedule_data(user):
    """Get schedule data for mobile view schedule page using team_id for accurate filtering"""
    try:
        # Get user's current session data 
        user_email = user.get("email")
        if not user_email:
            return {"matches": [], "user_name": "", "error": "User email not found"}
        
        # Use session service to get current league context
        from app.services.session_service import get_session_data_for_user
        session_data = get_session_data_for_user(user_email)
        
        if not session_data:
            return {"matches": [], "user_name": user_email, "error": "Session data not found"}
            
        player_id = session_data.get("tenniscores_player_id")
        league_id = session_data.get("league_id") 
        
        if not player_id:
            return {"matches": [], "user_name": user_email, "error": "Player ID not found in session"}
        
        # Get user's team ID for accurate filtering
        team_query = """
            SELECT DISTINCT
                t.id as team_id,
                t.team_name,
                c.name as club_name,
                s.name as series_name,
                l.league_name,
                l.id as league_db_id
            FROM players p
            JOIN teams t ON (
                p.club_id = t.club_id AND 
                p.series_id = t.series_id AND
                p.league_id = t.league_id
            )
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            WHERE p.tenniscores_player_id = %s
            AND p.is_active = TRUE
            ORDER BY l.league_name
        """
        
        team_info = execute_query_one(team_query, [player_id])
        
        if not team_info:
            return {
                "matches": [], 
                "user_name": user_email, 
                "error": f"No active team found for player {player_id}"
            }
        
        # Use team_id from session if available, otherwise use team lookup
        user_team_id = session_data.get("team_id")
        if not user_team_id:
            # Fallback: get team_id from team lookup
            user_team_id = team_info["team_id"]
            
        team_name = team_info["team_name"]
        league_db_id = team_info["league_db_id"]
        
        print(f"[DEBUG] Schedule lookup: team_id={user_team_id}, team_name='{team_name}', league_db_id={league_db_id}")
        
        # Get schedule data from database using TEAM_ID filtering for accuracy
        # Show all historical schedule data (removed date filter to show completed seasons)
        schedule_query = """
            SELECT 
                TO_CHAR(match_date, 'YYYY-MM-DD') as match_date,
                TO_CHAR(match_date, 'Day, Mon DD') as formatted_date,
                TO_CHAR(match_time, 'HH12:MI AM') as match_time,
                home_team,
                away_team,
                location,
                'match' as event_type,
                CASE 
                    WHEN home_team_id = %s THEN 'home'
                    WHEN away_team_id = %s THEN 'away'
                    ELSE 'neutral'
                END as home_away,
                CASE 
                    WHEN home_team_id = %s THEN away_team
                    WHEN away_team_id = %s THEN home_team
                    ELSE 'Unknown'
                END as opponent,
                CASE 
                    WHEN match_date >= CURRENT_DATE THEN 'upcoming'
                    ELSE 'past'
                END as status
            FROM schedule
            WHERE (home_team_id = %s OR away_team_id = %s)
            AND league_id = %s
            ORDER BY match_date DESC, match_time DESC
            LIMIT 50
        """
        
        schedule_matches = execute_query(schedule_query, [
            user_team_id, user_team_id, user_team_id, user_team_id, user_team_id, user_team_id, league_db_id
        ])
        
        # No fallback query needed since we're now showing all historical data
        
        # Practice times would go here when practice_times table exists
        practice_times = []
        
        # Format matches for mobile display
        formatted_matches = []
        for match in (schedule_matches or []):
            # Add status indicator to formatted date
            status_indicator = "🕐" if match.get("status") == "upcoming" else "✅"
            formatted_date_with_status = f"{status_indicator} {match['formatted_date']}"
            
            formatted_matches.append({
                "date": match["match_date"],
                "formatted_date": formatted_date_with_status, 
                "time": match["match_time"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "location": match["location"],
                "event_type": match["event_type"],
                "home_away": match["home_away"],
                "opponent": match["opponent"],
                "status": match.get("status", "past")
            })
        
        # Format practice times
        formatted_practices = []
        for practice in (practice_times or []):
            formatted_practices.append({
                "day": practice["practice_day"],
                "time": practice["practice_time"], 
                "location": practice["practice_location"],
                "event_type": "practice"
            })
        
        print(f"[DEBUG] Found {len(formatted_matches)} matches and {len(formatted_practices)} practices")
        
        return {
            "matches": formatted_matches,
            "practices": formatted_practices,
            "user_name": f"{session_data.get('first_name', '')} {session_data.get('last_name', '')}".strip(),
            "team_name": team_name,
            "club_name": team_info["club_name"],
            "series_name": team_info["series_name"],
            "league_name": team_info["league_name"],
            "total_events": len(formatted_matches) + len(formatted_practices)
        }
        
    except Exception as e:
        print(f"Error getting mobile schedule data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "matches": [],
            "practices": [],
            "user_name": user.get("email", ""),
            "error": str(e)
        }


def get_player_analysis(user):
    """Get player analysis data for mobile interface"""
    try:
        # Ensure user data is a dictionary
        if not isinstance(user, dict):
            return {
                "current_season": None,
                "court_analysis": {},
                "career_stats": None,
                "player_history": None,
                "videos": {"match": [], "practice": []},
                "trends": {},
                "career_pti_change": "N/A",
                "current_pti": None,
                "weekly_pti_change": None,
                "pti_data_available": False,
                "error": "Invalid user data format"
            }

        # Get player ID from user data
        player_id = user.get("tenniscores_player_id")

        # Get team context if available (for multi-team players)
        team_context = user.get("team_context")

        # Get user's league for filtering
        user_league_id = user.get("league_id", "")
        user_league_name = user.get("league_name", "")

        # Convert string league_id to integer foreign key if needed
        league_id_int = None
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
        elif user_league_id is None and user_league_name:
            try:
                league_record = execute_query_one(
                    "SELECT id, league_id FROM leagues WHERE league_name = %s",
                    [user_league_name],
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                pass

        # Calculate current season boundaries for filtering
        from datetime import datetime
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        # Dynamic season logic: Use the most recent season with data
        # For now, include both 2024-2025 and 2025-2026 seasons to catch all recent matches
        # This ensures we don't miss matches from the current/upcoming season
        season_start = datetime(2024, 8, 1)  # August 1st, 2024
        season_end = datetime(2026, 7, 31)   # July 31st, 2026 (extended to catch 2025-2026 season)
        
        print(f"[DEBUG] Extended season period: {season_start.strftime('%Y-%m-%d')} to {season_end.strftime('%Y-%m-%d')}")
        
        # Get player history - show CURRENT SEASON matches for individual player analysis
        # ENHANCED: Add team context filtering for Court Performance accuracy
        # FIXED: Handle duplicate match records by using DISTINCT ON
        if league_id_int:
            # Show current season matches for this player in this league
            # Add CLUB-BASED filtering when team context is available - show own team + same club substitutes
            if team_context:
                # Get the club_id and series_id for the current team context
                team_info_query = """
                    SELECT club_id, series_id 
                    FROM teams 
                    WHERE id = %s
                """
                team_info_result = execute_query_one(team_info_query, [team_context])
                if not team_info_result or not team_info_result.get('club_id'):
                    print(f"[ERROR] Could not find team info for team {team_context}")
                    return {"player_analysis": []}
                
                current_club_id = team_info_result['club_id']
                current_series_id = team_info_result['series_id']
                print(f"[DEBUG] Club-based filtering: team {team_context} -> club {current_club_id}, series {current_series_id}")
                
                # CLUB-BASED LOGIC: Show own team + same club different series matches
                # 1. Current team matches (own team)
                # 2. Substitute matches (same club_id, different series)
                history_query = """
                    SELECT DISTINCT ON (ms.match_date, ms.home_team, ms.away_team, ms.winner, ms.scores, ms.tenniscores_match_id)
                        ms.id,
                        TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                        ms.home_team as "Home Team",
                        ms.away_team as "Away Team",
                        ms.home_team_id,
                        ms.away_team_id,
                        ms.winner as "Winner",
                        ms.scores as "Scores",
                        ms.home_player_1_id as "Home Player 1",
                        ms.home_player_2_id as "Home Player 2",
                        ms.away_player_1_id as "Away Player 1",
                        ms.away_player_2_id as "Away Player 2",
                        ms.tenniscores_match_id
                    FROM match_scores ms
                    JOIN teams ht ON ms.home_team_id = ht.id
                    JOIN teams at ON ms.away_team_id = at.id
                    WHERE (ms.home_player_1_id = %s OR ms.home_player_2_id = %s OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s)
                    AND ms.league_id = %s
                    AND ms.match_date >= %s AND ms.match_date <= %s
                    AND (ht.club_id = %s OR at.club_id = %s)
                    ORDER BY ms.match_date DESC, ms.home_team, ms.away_team, ms.winner, ms.scores, ms.tenniscores_match_id, ms.id DESC
                """
                query_params = [player_id, player_id, player_id, player_id, league_id_int, season_start, season_end, current_club_id, current_club_id]
            else:
                # Original query without team filtering (preserves substitute appearances)
                history_query = """
                    SELECT DISTINCT ON (match_date, home_team, away_team, winner, scores, tenniscores_match_id)
                        id,
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        home_team as "Home Team",
                        away_team as "Away Team",
                        home_team_id,
                        away_team_id,
                        winner as "Winner",
                        scores as "Scores",
                        home_player_1_id as "Home Player 1",
                        home_player_2_id as "Home Player 2",
                        away_player_1_id as "Away Player 1",
                        away_player_2_id as "Away Player 2",
                        tenniscores_match_id
                    FROM match_scores
                    WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                    AND league_id = %s
                    AND match_date >= %s AND match_date <= %s
                    ORDER BY match_date DESC, home_team, away_team, winner, scores, tenniscores_match_id, id DESC
                """
                query_params = [player_id, player_id, player_id, player_id, league_id_int, season_start, season_end]
                print(f"[DEBUG] Player analysis showing CURRENT SEASON matches: player_id={player_id}, league_id={league_id_int}")

            player_matches = execute_query(history_query, query_params)

        else:
            # No league context - show current season matches for this player across all leagues
            history_query = """
                SELECT DISTINCT ON (match_date, home_team, away_team, winner, scores, tenniscores_match_id)
                    id,
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    home_team_id,
                    away_team_id,
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2",
                    tenniscores_match_id
                FROM match_scores
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND match_date >= %s AND match_date <= %s
                ORDER BY match_date DESC, home_team, away_team, winner, scores, tenniscores_match_id, id DESC
            """
            query_params = [player_id, player_id, player_id, player_id, season_start, season_end]
            print(f"[DEBUG] Player analysis (no league): showing CURRENT SEASON matches for player_id={player_id}")
            player_matches = execute_query(history_query, query_params)

        # Calculate accurate match statistics
        total_matches = len(player_matches) if player_matches else 0
        wins = 0
        losses = 0

        if player_matches:
            for match in player_matches:
                # Determine if player was on home or away team
                is_home = player_id in [
                    match.get("Home Player 1"),
                    match.get("Home Player 2"),
                ]
                winner = match.get("Winner") or ""
                won = (is_home and winner.lower() == "home") or (
                    not is_home and winner.lower() == "away"
                )

                # Calculate win/loss based on team position and winner
                if won:
                    wins += 1
                else:
                    losses += 1

        # Calculate win rate
        win_rate = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0

        # Get PTI data from players table and player_history table
        pti_data = {
            "current_pti": None,
            "pti_change": None,
            "pti_data_available": False,
        }
        season_pti_change = "N/A"

        try:
            # Get current PTI and series info from players table - prioritize player with PTI history and team context
            if team_context:
                # Filter by specific team when team context is available
                player_pti_query = """
                    SELECT 
                        p.id,
                        p.pti as current_pti,
                        p.series_id,
                        s.name as series_name,
                        (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                    FROM players p
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id = %s AND p.team_id = %s
                    ORDER BY history_count DESC, p.id DESC
                """
                player_pti_data = execute_query_one(player_pti_query, [player_id, team_context])
                print(f"[DEBUG] PTI query with team context: player_id={player_id}, team_id={team_context}")
            else:
                # Original query without team filtering
                player_pti_query = """
                    SELECT 
                        p.id,
                        p.pti as current_pti,
                        p.series_id,
                        s.name as series_name,
                        (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                    FROM players p
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id = %s
                    ORDER BY history_count DESC, p.id DESC
                """
                player_pti_data = execute_query_one(player_pti_query, [player_id])

            if player_pti_data and (player_pti_data["current_pti"] is not None or player_pti_data["history_count"] > 0):
                current_pti = player_pti_data["current_pti"]
                series_name = player_pti_data["series_name"]
                history_count = player_pti_data["history_count"]

                # If current_pti is NULL but we have history, get the most recent PTI from history
                if current_pti is None and history_count > 0:
                    player_db_id = player_pti_data["id"]
                    recent_pti_query = """
                        SELECT end_pti
                        FROM player_history
                        WHERE player_id = %s
                        ORDER BY date DESC
                        LIMIT 1
                    """
                    recent_pti_result = execute_query_one(recent_pti_query, [player_db_id])
                    if recent_pti_result:
                        current_pti = recent_pti_result["end_pti"]

                # Get PTI history for this specific player using proper foreign key relationship
                pti_change = 0.0

                # Get player's database ID first
                player_db_id = player_pti_data["id"]

                # Method 1: Use proper foreign key to get this player's PTI history
                player_pti_history_query = """
                    SELECT 
                        date,
                        end_pti,
                        series,
                        TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
                    FROM player_history
                    WHERE player_id = %s
                    ORDER BY date DESC
                    LIMIT 10
                """

                player_pti_records = execute_query(player_pti_history_query, [player_db_id])

                if player_pti_records and len(player_pti_records) >= 2:
                    # Get the most recent and previous week's PTI values for this specific player
                    most_recent_pti = player_pti_records[0]["end_pti"]
                    previous_week_pti = player_pti_records[1]["end_pti"]
                    pti_change = most_recent_pti - previous_week_pti

                # Calculate season PTI change
                from datetime import datetime
                current_date = datetime.now()
                current_year = current_date.year
                current_month = current_date.month

                # Determine season year based on current date
                # Since we're in August 2025, we want the 2024-2025 season (Aug 2024 - Jul 2025)
                # which contains the player's data from Jan-Mar 2025
                if current_month >= 8:  # Aug-Dec: previous season (since we're in offseason)
                    season_start_year = current_year - 1
                else:  # Jan-Jul: previous season
                    season_start_year = current_year - 1

                season_start_date = f"{season_start_year}-08-01"
                season_end_date = f"{season_start_year + 1}-07-31"

                # Get PTI values at season start and most recent
                season_pti_query = """
                    SELECT 
                        date,
                        end_pti,
                        ROW_NUMBER() OVER (ORDER BY date ASC) as rn_start,
                        ROW_NUMBER() OVER (ORDER BY date DESC) as rn_end
                    FROM player_history
                    WHERE player_id = %s 
                    AND date >= %s 
                    AND date <= %s
                    ORDER BY date
                """

                season_pti_records = execute_query(season_pti_query, [player_db_id, season_start_date, season_end_date])

                if season_pti_records and len(season_pti_records) >= 2:
                    # Get first and last PTI values of the season
                    start_pti = season_pti_records[0]["end_pti"]
                    end_pti = season_pti_records[-1]["end_pti"]
                    season_pti_change = round(end_pti - start_pti, 1)

                # Convert Decimal types to float for template compatibility
                def decimal_to_float(value):
                    """Convert Decimal to float, handle None values"""
                    from decimal import Decimal
                    if value is None:
                        return None
                    if isinstance(value, Decimal):
                        return float(value)
                    return value

                pti_data = {
                    "current_pti": decimal_to_float(current_pti),
                    "pti_change": decimal_to_float(pti_change),
                    "pti_data_available": True,
                }

        except Exception as pti_error:
            print(f"Error fetching PTI data: {pti_error}")

        # Helper function to convert Decimal to float for template compatibility
        def decimal_to_float_season(value):
            """Convert Decimal to float, handle None values"""
            from decimal import Decimal
            if value is None:
                return None
            if isinstance(value, Decimal):
                return float(value)
            return value

        current_season = {
            "winRate": decimal_to_float_season(win_rate),
            "matches": total_matches,
            "wins": wins,
            "losses": losses,
            "ptiChange": decimal_to_float_season(season_pti_change) if season_pti_change != "N/A" else "N/A",
        }

        # Build career stats from player_history table
        career_stats = get_career_stats_from_db(player_id)

        # Calculate court analysis for individual player
        court_analysis = calculate_individual_court_analysis(player_matches, player_id, user, current_series_id, current_club_id, team_context)

        # Initialize empty player history
        player_history = {"progression": "", "seasons": []}

        # Return the complete data structure expected by the template
        result = {
            "current_season": current_season,
            "court_analysis": court_analysis,
            "career_stats": career_stats,
            "player_history": player_history,
            "match_history": player_matches or [],  # CRITICAL FIX: Include match history in result
            "videos": {"match": [], "practice": []},
            "trends": {},
            "career_pti_change": "N/A",
            "current_pti": decimal_to_float_season(pti_data.get("current_pti", 0.0)),
            "weekly_pti_change": decimal_to_float_season(pti_data.get("pti_change", 0.0)),
            "pti_data_available": pti_data.get("pti_data_available", False),
            "error": None
        }

        return result

    except Exception as e:
        print(f"Error getting player analysis: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "current_season": None,
            "court_analysis": {},
            "career_stats": None,
            "player_history": None,
            "videos": {"match": [], "practice": []},
            "trends": {},
            "career_pti_change": "N/A",
            "current_pti": None,
            "weekly_pti_change": None,
            "pti_data_available": False,
            "error": str(e)
        }


def calculate_individual_court_analysis(player_matches, player_id, user=None, current_series_id=None, current_club_id=None, team_context=None):
    """
    Calculate court analysis for an individual player based on their matches.
    Adapted from the team court analysis logic to work for individual players.
    
    Args:
        player_matches: List of match data for the player
        player_id: The tenniscores_player_id for the player
        
    Returns:
        Dict with court analysis data in the format expected by the template
    """
    try:
        from collections import defaultdict
        from datetime import datetime
        from database_utils import execute_query
        
        if not player_matches or not player_id:
            # Return empty court analysis with proper structure (default to 5 courts)
            return {
                f"court{i}": {
                    "winRate": 0,
                    "record": "0-0",
                    "topPartners": [],
                    "matches": 0,
                    "wins": 0,
                    "losses": 0
                }
                for i in range(1, 6)
            }
        


        def parse_date(date_str):
            if not date_str:
                return datetime.min
            # Handle the specific format from our database  
            for fmt in ("%d-%b-%y", "%d-%B-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(str(date_str), fmt)
                except ValueError:
                    continue
            return datetime.min

        # Get unique match dates for this player
        player_dates = []
        for match in player_matches:
            date_str = match.get("Date", "")
            parsed_date = parse_date(date_str)
            if parsed_date != datetime.min:
                player_dates.append(parsed_date.date())

        court_analysis = {}
        
        if player_dates:
            # Get all matches on those dates to determine correct court assignments
            # CRITICAL FIX: Filter by league to only get matches from the same league as the player
            league_id_for_query = user.get("league_id")
            league_id_int = None
            
            # Convert league_id to integer foreign key if needed
            if league_id_for_query:
                if isinstance(league_id_for_query, str) and league_id_for_query != "":
                    try:
                        league_record = execute_query_one(
                            "SELECT id FROM leagues WHERE league_id = %s", [league_id_for_query]
                        )
                        if league_record:
                            league_id_int = league_record["id"]
                    except Exception as e:
                        pass
                elif isinstance(league_id_for_query, int):
                    league_id_int = league_id_for_query
            
            # Calculate current season boundaries for court analysis filtering (matching JavaScript logic)
            current_date = datetime.now()
            current_month = current_date.month
            current_year = current_date.year
            
            # Dynamic season logic: Use the most recent season with data
            # For now, include both 2024-2025 and 2025-2026 seasons to catch all recent matches
            # This ensures we don't miss matches from the current/upcoming season
            season_start = datetime(2024, 8, 1)  # August 1st, 2024
            season_end = datetime(2026, 7, 31)   # July 31st, 2026 (extended to catch 2025-2026 season)
            
            if league_id_int:
                # FIXED: Use only the player's actual matches for court analysis
                # Don't fetch additional matches from database - only use matches where player participated
                all_matches_on_dates = player_matches
            else:
                # Fallback: Use only player's matches even without league filter
                all_matches_on_dates = player_matches

            # SIMPLIFIED: Find max court directly from player's matches
            max_court = 4  # Default to 4 courts
            for match in player_matches:
                tenniscores_match_id = match.get("tenniscores_match_id", "")
                if tenniscores_match_id and "_Line" in tenniscores_match_id:
                    line_parts = tenniscores_match_id.split("_Line")
                    if len(line_parts) > 1:
                        try:
                            court_number = int(line_parts[-1])
                            max_court = max(max_court, court_number)
                        except ValueError:
                            pass
            
            # Cap at 6 for safety
            max_court = min(max_court, 6)
            
            # Initialize court stats for all courts up to max_court
            for i in range(1, max_court + 1):
                court_name = f"court{i}"  # Template expects "court1", "court2", etc.
                court_matches = []

                # SIMPLIFIED: Find matches for this court directly from player's matches
                for match in player_matches:
                    tenniscores_match_id = match.get("tenniscores_match_id", "")
                    court_number = None
                    
                    if tenniscores_match_id and "_Line" in tenniscores_match_id:
                        # Extract court number from tenniscores_match_id (e.g., "12345_Line2" -> 2)
                        line_parts = tenniscores_match_id.split("_Line")
                        if len(line_parts) > 1:
                            try:
                                court_number = int(line_parts[-1])
                            except ValueError:
                                # Fallback to court 1 if parsing fails
                                court_number = 1
                        else:
                            court_number = 1
                    else:
                        # Fallback to court 1 if no tenniscores_match_id
                        court_number = 1
                    
                    if court_number == i:  # This match belongs to court i
                        court_matches.append(match)

                wins = losses = 0
                partner_win_counts = {}

                # Get user's team ID for substitute detection
                user_team_id = user.get("team_id") if user else None

                for match in court_matches:
                    # Determine if player was on home or away team
                    is_home = player_id in [
                        match.get("Home Player 1"),
                        match.get("Home Player 2"),
                    ]
                    
                    winner = match.get("Winner") or ""
                    winner_is_home = winner and winner.lower() == "home"
                    
                    # Check if this league has reversed team assignments
                    from utils.league_utils import has_reversed_team_assignments
                    league_id_str = user.get("league_name") if user else None
                    has_reversed = has_reversed_team_assignments(league_id_str) if league_id_str else False
                    
                    if has_reversed:
                        # For leagues with reversed team assignments (like NSTF): reverse the win logic
                        won = (is_home and not winner_is_home) or (not is_home and winner_is_home)
                    else:
                        # Standard logic for other leagues (APTA, etc.)
                        won = (is_home and winner_is_home) or (not is_home and not winner_is_home)

                    if won:
                        wins += 1
                    else:
                        losses += 1

                    # Track partner performance
                    if is_home:
                        partner = (
                            match.get("Home Player 2") 
                            if match.get("Home Player 1") == player_id 
                            else match.get("Home Player 1")
                        )
                        match_team_id = match.get("home_team_id")
                    else:
                        partner = (
                            match.get("Away Player 2") 
                            if match.get("Away Player 1") == player_id 
                            else match.get("Away Player 1")
                        )
                        match_team_id = match.get("away_team_id")

                    if partner and partner != player_id:
                        if partner not in partner_win_counts:
                            partner_win_counts[partner] = {"matches": 0, "wins": 0, "is_substitute": False, "substitute_series": None}
                        
                        partner_win_counts[partner]["matches"] += 1
                        if won:
                            partner_win_counts[partner]["wins"] += 1
                        
                        # ✅ ENHANCED: Check if this partner is a substitute using user's team context
                        # Get the player's own team ID prioritizing user's current team context
                        player_own_team_id = None
                        try:
                            # PRIORITY 1: Use user's current team context if available
                            if user and user.get("team_id"):
                                user_team_id = user.get("team_id")
                                
                                # Check if the player is actually on the user's current team
                                player_teams_query = """
                                    SELECT team_id 
                                    FROM players 
                                    WHERE tenniscores_player_id = %s 
                                    AND league_id = %s
                                    AND is_active = true
                                """
                                player_teams = execute_query(player_teams_query, [player_id, league_id_int])
                                player_team_ids = [team['team_id'] for team in player_teams if team['team_id']]
                                
                                if user_team_id in player_team_ids:
                                    # Player is on user's current team, use that as reference
                                    player_own_team_id = user_team_id
                                    print(f"[DEBUG] Court analysis: Using user team context {user_team_id} for player {player_id}")
                                elif player_team_ids:
                                    # Player is not on user's team, use their primary team
                                    player_own_team_id = player_team_ids[0]  # Pick first team
                                    print(f"[DEBUG] Court analysis: Player {player_id} not on user team {user_team_id}, using primary team {player_own_team_id}")
                            else:
                                # FALLBACK: Legacy method - get any team for this player
                                player_team_query = """
                                    SELECT team_id 
                                    FROM players 
                                    WHERE tenniscores_player_id = %s 
                                    AND league_id = %s
                                    AND is_active = true
                                    LIMIT 1
                                """
                                player_team_result = execute_query_one(player_team_query, [player_id, league_id_int])
                                if player_team_result:
                                    player_own_team_id = player_team_result["team_id"]
                                    print(f"[DEBUG] Court analysis: Using legacy team lookup {player_own_team_id} for player {player_id}")
                                    
                        except Exception as e:
                            print(f"Error getting player's own team: {e}")
                        
                        # CLUB-BASED SUBSTITUTE DETECTION:
                        # Check if this is a substitute match (same club, different series from user's current series)
                        try:
                            # Determine if this match is a substitute match for the logged-in player
                            # A substitute match is when player played for same club but different series
                            if match_team_id != team_context:  # Not the player's current team
                                # Check if match team is same club but different series
                                match_team_query = """
                                    SELECT club_id, series_id
                                    FROM teams 
                                    WHERE id = %s
                                """
                                match_team_result = execute_query_one(match_team_query, [match_team_id])
                                
                                if (match_team_result and 
                                    match_team_result.get('club_id') == current_club_id and
                                    match_team_result.get('series_id') != current_series_id):
                                    
                                    # This is a substitute match - mark partner as being in a substitute context
                                    partner_win_counts[partner]["is_substitute"] = True
                                    
                                    # Get series name for substitute label
                                    try:
                                        series_query = """
                                            SELECT s.name as series_name, s.display_name as series_display_name
                                            FROM teams t
                                            JOIN series s ON t.series_id = s.id
                                            WHERE t.id = %s
                                        """
                                        series_result = execute_query_one(series_query, [match_team_id])
                                        if series_result:
                                            series_name = series_result.get("series_display_name") or series_result["series_name"]
                                            from app.routes.api_routes import convert_chicago_to_series_for_ui
                                            display_series_name = convert_chicago_to_series_for_ui(series_name)
                                            partner_win_counts[partner]["substitute_series"] = display_series_name
                                    except Exception as e:
                                        print(f"Error getting series name for substitute: {e}")
                                        partner_win_counts[partner]["substitute_series"] = "Unknown Series"
                        except Exception as e:
                            print(f"Error checking substitute status: {e}")
                            # Default to not a substitute if we can't determine

                win_rate = (
                    round((wins / (wins + losses) * 100), 1)
                    if (wins + losses) > 0
                    else 0
                )
                record = f"{wins}-{losses}"

                # Top partners by performance (show top 3)
                top_partners = []
                for partner_id, stats in partner_win_counts.items():
                    partner_name = get_player_name_from_id(partner_id)
                    if partner_name and stats["matches"] > 0:
                        partner_win_rate = round((stats["wins"] / stats["matches"]) * 100, 1)
                        partner_data = {
                            "name": partner_name,
                            "matches": stats["matches"],
                            "wins": stats["wins"],
                            "losses": stats["matches"] - stats["wins"], 
                            "winRate": partner_win_rate
                        }
                        
                        # Add substitute information if this partner was a substitute
                        if stats.get("is_substitute", False):
                            substitute_series = stats.get("substitute_series", "Unknown Series")
                            partner_data["isSubstitute"] = True
                            partner_data["substituteSeries"] = substitute_series
                        else:
                            partner_data["isSubstitute"] = False
                        
                        top_partners.append(partner_data)

                # Sort by win rate, then by matches played
                top_partners.sort(key=lambda x: (-x["winRate"], -x["matches"]))
                # Show all partners (no limit - ensuring all players are displayed)

                court_analysis[court_name] = {
                    "winRate": win_rate,
                    "record": record,
                    "topPartners": top_partners,
                    "matches": wins + losses,
                    "wins": wins,
                    "losses": losses
                }
        else:
            # No matches found - initialize empty courts (default to 5)
            for i in range(1, 6):
                court_name = f"court{i}"
                court_analysis[court_name] = {
                    "winRate": 0,
                    "record": "0-0",
                    "topPartners": [],
                    "matches": 0,
                    "wins": 0,
                    "losses": 0
                }

        return court_analysis

    except Exception as e:
        print(f"Error calculating individual court analysis: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        # Return empty court analysis on error
        return {
            f"court{i}": {
                "winRate": 0,
                "record": "0-0",
                "topPartners": [],
                "matches": 0,
                "wins": 0,
                "losses": 0
            }
            for i in range(1, 6)
        }


def get_mobile_availability_data(user):
    """Get availability data for mobile availability page using team_id for accurate filtering"""
    try:
        # Import database utilities at the top
        from database_utils import execute_query, execute_query_one
        
        # Use user data directly (preserves team context from route)
        user_email = user.get("email", "")
        
        # Use the user data passed in directly instead of calling session service again
        # This preserves any team-specific context that was set in the route
        session_data = user
        
        if not session_data:
            return {
                "match_avail_pairs": [],
                "players": [{"name": user_email}],
                "error": "Could not load session data"
            }
        
        team_id = session_data.get("team_id")
        league_id = session_data.get("league_id")  # integer DB ID
        player_name = f"{session_data.get('first_name', '')} {session_data.get('last_name', '')}".strip()
        
        # FALLBACK: If no team_id in session, try to get it directly from database
        if not team_id:
            print(f"[DEBUG] No team_id in session for {user_email}, attempting database fallback...")
            
            # Try primary query first (when team_id exists)
            primary_fallback_query = """
                SELECT p.team_id, p.tenniscores_player_id, t.team_name, 
                       c.name as club_name, s.name as series_name, l.league_name,
                       p.league_id, l.id as league_db_id
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN teams t ON p.team_id = t.id
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                JOIN leagues l ON p.league_id = l.id
                JOIN users u ON upa.user_id = u.id
                WHERE u.email = %s 
                AND p.is_active = TRUE 
                AND p.team_id IS NOT NULL
                AND (u.league_context IS NULL OR p.league_id = u.league_context)
                ORDER BY 
                    CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END,
                    p.team_id DESC
                LIMIT 1
            """
            fallback_result = execute_query_one(primary_fallback_query, [user_email])
            
            # If no team found via team_id, try fallback using club + series matching (like my-team fix)
            if not fallback_result:
                print(f"[DEBUG] No team found via team_id for {user_email}, trying club+series fallback...")
                series_fallback_query = """
                    SELECT t.id as team_id, p.tenniscores_player_id, t.team_name, 
                           c.name as club_name, s.name as series_name, l.league_name,
                           p.league_id, l.id as league_db_id
                    FROM user_player_associations upa
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    JOIN clubs c ON p.club_id = c.id
                    JOIN series s ON p.series_id = s.id
                    JOIN leagues l ON p.league_id = l.id
                    JOIN users u ON upa.user_id = u.id
                    JOIN teams t ON (t.club_id = c.id AND t.team_alias = s.name)
                    WHERE u.email = %s 
                    AND p.is_active = TRUE
                    AND t.is_active = TRUE
                    AND (u.league_context IS NULL OR p.league_id = u.league_context)
                    ORDER BY 
                        CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END,
                        t.id DESC
                    LIMIT 1
                """
                fallback_result = execute_query_one(series_fallback_query, [user_email])
                
                if fallback_result:
                    print(f"[DEBUG] Found team via club+series fallback: {fallback_result['team_name']} (ID: {fallback_result['team_id']})")
            
            if fallback_result:
                team_id = fallback_result["team_id"]
                league_id = fallback_result["league_db_id"]
                print(f"[DEBUG] Fallback found team_id={team_id} for player in {fallback_result['club_name']} {fallback_result['series_name']}")
            else:
                # Still no team found - return empty result with helpful error
                return {
                    "match_avail_pairs": [],
                    "players": [{"name": player_name}],
                    "error": f"No active team found for {player_name}. Please check your profile settings."
                }
        
        print(f"Getting availability data for user: {user_email}, team_id: {team_id}, league_id: {league_id}")

        # Get upcoming matches/practices using team_id only (clean approach)
        # Use a very simple query to avoid any SQL parsing issues
        print(f"[DEBUG] Getting matches for team_id={team_id}, league_id={league_id}")
        
        # Get simple schedule query for all matches (including completed seasons)
        # ENHANCED: Show all matches for team instead of restricting to 30 days to support completed seasons
        # FIXED: Added DISTINCT and LIMIT to handle corrupted duplicate data
        simple_query = """
        SELECT DISTINCT
            match_date as date, 
            match_time as time, 
            home_team, 
            away_team, 
            location
        FROM schedule 
        WHERE (home_team_id = %s OR away_team_id = %s)
        ORDER BY match_date ASC, match_time ASC
        LIMIT 100  -- Prevent processing thousands of duplicate records
        """
        
        print(f"[DEBUG] Executing simple query with params: {(team_id, team_id)}")
        user_matches = execute_query(simple_query, (team_id, team_id))
        
        # FALLBACK: If no matches found by team_id, try team name matching
        if not user_matches and session_data.get("club") and session_data.get("series"):
            print(f"[DEBUG] No matches found by team_id, trying team name fallback...")
            
            # Get the team name from teams table
            team_name_query = """
                SELECT team_name FROM teams WHERE id = %s
            """
            team_result = execute_query_one(team_name_query, [team_id])
            
            if team_result:
                base_team_name = team_result["team_name"]
                print(f"[DEBUG] Base team name from teams table: {base_team_name}")
                
                # Try different team name formats that might exist in schedule table
                team_name_patterns = [
                    base_team_name,  # Exact match
                    f"{base_team_name} - Series {session_data.get('series', '').replace('S', '')}",  # NSTF format: "Tennaqua S2B" -> "Tennaqua S2B - Series 2B"
                ]
                
                for pattern in team_name_patterns:
                    print(f"[DEBUG] Trying team name pattern: '{pattern}'")
                    
                    fallback_query = """
                    SELECT DISTINCT
                        match_date as date, 
                        match_time as time, 
                        home_team, 
                        away_team, 
                        location
                    FROM schedule 
                    WHERE (home_team = %s OR away_team = %s)
                    AND league_id = %s
                    AND match_date >= CURRENT_DATE - INTERVAL '30 days'  -- Only show recent/future matches
                    ORDER BY match_date ASC, match_time ASC
                    LIMIT 100  -- Prevent processing thousands of duplicate records
                    """
                    
                    user_matches = execute_query(fallback_query, (pattern, pattern, league_id))
                    
                    if user_matches:
                        print(f"[DEBUG] Found {len(user_matches)} matches using pattern: '{pattern}'")
                        break
                else:
                    print(f"[DEBUG] No matches found with any team name pattern")
            else:
                print(f"[DEBUG] Could not find team name for team_id {team_id}")
        
        # Filter manually for league (removed future date filter)
        filtered_matches = []
        
        for match in user_matches:
            match_date = match.get('date')
            if match_date:
                # Add type field manually - properly classify practice vs match
                home_team = match.get('home_team', '')
                away_team = match.get('away_team', '')
                
                # Detect practice sessions (contain "Practice" in home_team or no away_team)
                is_practice = (
                    'Practice' in home_team or 
                    (not away_team or away_team.strip() == '')
                )
                
                match['type'] = 'practice' if is_practice else 'match'
                filtered_matches.append(match)
        
        user_matches = filtered_matches
        
        print(f"Found {len(user_matches)} upcoming matches/practices for team_id {team_id}")
        
        # Format matches for the template
        formatted_matches = []
        for match in user_matches:
            # Format raw date and time values from database
            raw_date = match.get("date")
            raw_time = match.get("time")
            
            # Format date as MM/DD/YYYY
            formatted_date = ""
            if raw_date:
                formatted_date = raw_date.strftime("%m/%d/%Y")
            
            # Format time as HH:MM AM/PM
            formatted_time = ""
            if raw_time:
                # raw_time is a time object, format it
                formatted_time = raw_time.strftime("%I:%M %p").lstrip('0')
            
            # Check if this is a home match by comparing location with user's club
            # Get current team's club name to compare with match location
            team_club_query = """
                SELECT c.name as club_name 
                FROM teams t 
                JOIN clubs c ON t.club_id = c.id 
                WHERE t.id = %s
            """
            team_club_info = execute_query_one(team_club_query, [team_id])
            current_club_name = team_club_info["club_name"] if team_club_info else ""
            
            # A match is "home" if the location matches the user's club
            match_location = match.get("location", "").strip()
            is_home_match = (match_location == current_club_name)
            
            # If it's a home match, get other teams at the same club with home matches on this date
            # OPTIMIZATION: Only call this function for actual matches, not practices, to avoid infinite loops
            other_home_teams = []
            if is_home_match and raw_date and match.get("type") == "match" and match.get("away_team"):  # Only for actual matches with opponents, not practices
                other_home_teams = get_other_home_teams_at_club_on_date(team_id, raw_date, user_email)
            
            match_data = {
                "date": formatted_date,
                "time": formatted_time,
                "location": match.get("location", ""),
                "home_team": match.get("home_team", ""),
                "away_team": match.get("away_team", ""),
                "type": match.get("type", "match"),
                "is_home_match": is_home_match,
                "other_home_teams": other_home_teams
            }
            formatted_matches.append(match_data)
            
            # OPTIMIZATION: Reduced debug output to prevent spam
            # if match.get("type") == "practice":
            #     print(f"  ✓ Practice found: {match.get('home_team')} on {match.get('date')}")
            # else:
            #     print(f"  ✓ Match found: {match.get('home_team')} vs {match.get('away_team')} on {match.get('date')}")
        
        # Get the user's player ID for availability lookup
        player_record = None
        if session_data.get("tenniscores_player_id"):
            # Try by tenniscores_player_id first (preferred)
            player_query = """
                SELECT id, tenniscores_player_id, series_id 
                FROM players 
                WHERE tenniscores_player_id = %s AND league_id = %s
            """
            player_record = execute_query_one(player_query, (session_data["tenniscores_player_id"], league_id))
        
        if not player_record:
            # Fallback: try by player name and series
            series_id = session_data.get("series_id")
            if series_id:
                player_query = """
                    SELECT id, tenniscores_player_id, series_id 
                    FROM players 
                    WHERE player_name = %s AND series_id = %s AND league_id = %s
                """
                player_record = execute_query_one(player_query, (player_name, series_id, league_id))
        
        # Get availability data using STABLE USER_ID APPROACH
        # CRITICAL FIX: Use user_id instead of player_id for stable lookups that survive ETL imports
        availability_data = {}
        user_id = session_data.get("id")  # Get user_id from session data
        
        if user_id:
            print(f"Getting availability using stable user_id={user_id} (ETL-resilient approach)")
            
            # STABLE APPROACH: Query by user_id + match_date (same pattern as availability protection)
            availability_query = """
                SELECT 
                    DATE(match_date AT TIME ZONE 'UTC') as match_date,
                    availability_status, 
                    notes 
                FROM player_availability 
                WHERE user_id = %s
            """
            availability_records = execute_query(availability_query, (user_id,))
            
            # Map numeric status to string status for template
            status_map = {
                1: "available",
                2: "unavailable", 
                3: "not_sure",
                None: None  # No selection made
            }
            
            # Build availability lookup by date
            for avail in availability_records:
                match_date = avail["match_date"]
                if match_date:
                    # Convert date object to MM/DD/YYYY format
                    if hasattr(match_date, 'strftime'):
                        date_key = match_date.strftime("%m/%d/%Y")
                    else:
                        # Handle case where it's a string
                        date_key = str(match_date)
                        
                    numeric_status = avail["availability_status"]
                    string_status = status_map.get(numeric_status)
                    availability_data[date_key] = {
                        "status": string_status,
                        "notes": avail.get("notes", "")
                    }
            
            print(f"Found availability data for {len(availability_data)} dates using stable user_id approach")
            
            # DEBUG: Log specific dates found
            for date_key, avail_info in availability_data.items():
                print(f"  {date_key}: {avail_info['status']} - {avail_info['notes']}")
        else:
            print(f"No user_id found in session data - using legacy player_id approach")
            
            # FALLBACK: Original logic for backward compatibility
            if player_record:
                player_id = player_record["id"]
                series_id = player_record["series_id"]
                
                print(f"Getting availability for player_id={player_id}, series_id={series_id}")
                
                availability_query = """
                    SELECT 
                        DATE(match_date AT TIME ZONE 'UTC') as match_date,
                        availability_status, 
                        notes 
                    FROM player_availability 
                    WHERE player_id = %s AND series_id = %s
                """
                availability_records = execute_query(availability_query, (player_id, series_id))
                
                # Map numeric status to string status for template
                status_map = {
                    1: "available",
                    2: "unavailable", 
                    3: "not_sure",
                    None: None  # No selection made
                }
                
                # Build availability lookup by date
                for avail in availability_records:
                    match_date = avail["match_date"]
                    if match_date:
                        # Convert date object to MM/DD/YYYY format
                        if hasattr(match_date, 'strftime'):
                            date_key = match_date.strftime("%m/%d/%Y")
                        else:
                            # Handle case where it's a string
                            date_key = str(match_date)
                            
                        numeric_status = avail["availability_status"]
                        string_status = status_map.get(numeric_status)
                        availability_data[date_key] = {
                            "status": string_status,
                            "notes": avail.get("notes", "")
                        }
                
                print(f"Found availability data for {len(availability_data)} dates")
            else:
                print(f"No player record found for {player_name} in league {league_id}")

        # Create match-availability pairs with actual availability data
        match_avail_pairs = []
        for match in formatted_matches:
            match_date = match["date"]  # Already in MM/DD/YYYY format
            
            # Get availability for this date
            availability = availability_data.get(match_date, {"status": None, "notes": ""})
            match_avail_pairs.append((match, availability))

        return {
            "match_avail_pairs": match_avail_pairs,
            "players": [{"name": player_name}],
        }

    except Exception as e:
        print(f"Error getting mobile availability data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "match_avail_pairs": [],
            "players": [{"name": user.get("email", "Unknown")}],
            "error": str(e)
        }


def get_recent_matches_for_user_club(user):
    """
    Get the last 6 weeks of matches for a user's club, grouped by date.
    FIXED: Only queries matches from user's specific league and club from session.

    Args:
        user: User object containing club and league information from session

    Returns:
        Dict with matches grouped by date for the last 6 weeks
    """
    try:
        from database_utils import execute_query, execute_query_one

        if not user or not user.get("club"):
            return {}

        user_club = user["club"]
        user_league_id = user.get("league_id", "")
        user_league_name = user.get("league_name", "")

        print(f"[DEBUG] get_recent_matches: Filtering by session - club: '{user_club}', league_id: '{user_league_id}', league_name: '{user_league_name}'")

        # FIXED: Convert string league_id to integer primary key for database filtering
        user_league_db_id = None
        if user_league_id:
            try:
                # Handle both string and integer league_id from session
                if isinstance(user_league_id, str) and user_league_id != "":
                    league_lookup = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", (user_league_id,)
                    )
                    if league_lookup:
                        user_league_db_id = league_lookup["id"]
                        print(f"[DEBUG] get_recent_matches: Converted user league_id '{user_league_id}' to database ID: {user_league_db_id}")
                    else:
                        print(f"[DEBUG] get_recent_matches: No league found for league_id '{user_league_id}'")
                elif isinstance(user_league_id, int):
                    user_league_db_id = user_league_id
                    print(f"[DEBUG] get_recent_matches: Using integer league_id directly: {user_league_db_id}")
            except Exception as e:
                print(f"[DEBUG] get_recent_matches: Error looking up league ID: {e}")

        # If no league context, try to get from user's primary association
        if user_league_db_id is None:
            try:
                user_email = user.get("email", "")
                if user_email:
                    print(f"[DEBUG] get_recent_matches: No league in session, looking up primary association for {user_email}")
                    primary_league_query = """
                        SELECT l.id, l.league_id, l.league_name, u.league_context
                        FROM users u
                        JOIN user_player_associations upa ON u.id = upa.user_id
                        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                        JOIN leagues l ON p.league_id = l.id
                        WHERE u.email = %s 
                        AND (u.league_context IS NULL OR p.league_id = u.league_context)
                        ORDER BY (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END)
                        LIMIT 1
                    """
                    primary_league = execute_query_one(primary_league_query, [user_email])
                    if primary_league:
                        user_league_db_id = primary_league["id"]
                        print(f"[DEBUG] get_recent_matches: Found primary league: {primary_league['league_name']} (DB ID: {user_league_db_id})")
                    else:
                        print(f"[DEBUG] get_recent_matches: No primary league association found for {user_email}")
            except Exception as e:
                print(f"[DEBUG] get_recent_matches: Error looking up primary league: {e}")

        # FIXED: Query matches directly with league and club filtering in the SQL query
        if user_league_db_id:
            matches_query = """
                SELECT 
                    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.scores as "Scores",
                    ms.winner as "Winner",
                    ms.home_player_1_id as "Home Player 1",
                    ms.home_player_2_id as "Home Player 2", 
                    ms.away_player_1_id as "Away Player 1",
                    ms.away_player_2_id as "Away Player 2",
                    ms.league_id,
                    ms.tenniscores_match_id as "Tenniscores Match ID",
                    '' as "Time",
                    '' as "Location",
                    '' as "Court",
                    '' as "Series"
                FROM match_scores ms
                WHERE ms.league_id = %s 
                AND (ms.home_team LIKE %s OR ms.away_team LIKE %s)
                ORDER BY ms.match_date DESC
                LIMIT 200
            """
            club_pattern = f"%{user_club}%"
            league_filtered_matches = execute_query(matches_query, [user_league_db_id, club_pattern, club_pattern])
        else:
            # Fallback: no league filtering if we can't determine league
            print(f"[DEBUG] get_recent_matches: No league context available, falling back to club-only filtering")
            matches_query = """
                SELECT 
                    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.scores as "Scores",
                    ms.winner as "Winner",
                    ms.home_player_1_id as "Home Player 1",
                    ms.home_player_2_id as "Home Player 2", 
                    ms.away_player_1_id as "Away Player 1",
                    ms.away_player_2_id as "Away Player 2",
                    ms.league_id,
                    ms.tenniscores_match_id as "Tenniscores Match ID",
                    '' as "Time",
                    '' as "Location",
                    '' as "Court",
                    '' as "Series"
                FROM match_scores ms
                WHERE (ms.home_team LIKE %s OR ms.away_team LIKE %s)
                ORDER BY ms.match_date DESC
                LIMIT 200
            """
            club_pattern = f"%{user_club}%"
            league_filtered_matches = execute_query(matches_query, [club_pattern, club_pattern])

        print(f"[DEBUG] get_recent_matches_for_user_club: Found {len(league_filtered_matches)} matches for club '{user_club}' in league {user_league_db_id} ('{user_league_name}')")

        # FIXED: Since we filtered in SQL, normalize the match data directly
        club_matches = []
        for match in league_filtered_matches:
            # Normalize keys to snake_case for consistent usage
            normalized_match = {
                "date": match.get("Date", ""),
                "time": match.get("Time", ""),
                "location": match.get("Location", ""),
                "home_team": match.get("Home Team", ""),
                "away_team": match.get("Away Team", ""),
                "winner": match.get("Winner", ""),
                "scores": match.get("Scores", ""),
                "home_player_1": match.get("Home Player 1", ""),
                "home_player_2": match.get("Home Player 2", ""),
                "away_player_1": match.get("Away Player 1", ""),
                "away_player_2": match.get("Away Player 2", ""),
                "tenniscores_match_id": match.get("Tenniscores Match ID", ""),
                "court": match.get("Court", ""),
                "series": match.get("Series", ""),
            }
            club_matches.append(normalized_match)

        print(f"[DEBUG] Processing {len(club_matches)} matches for club '{user_club}' in league '{user_league_name}'")

        # Sort matches by date to get chronological order
        def parse_date(date_str):
            for fmt in ("%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.min

        sorted_matches = sorted(
            club_matches, key=lambda x: parse_date(x["date"]), reverse=True
        )

        if not sorted_matches:
            return {}

        # Group matches by date and get the last 10 unique dates
        matches_by_date = {}
        for match in sorted_matches:
            date = match["date"]
            if date not in matches_by_date:
                matches_by_date[date] = []
            matches_by_date[date].append(match)

        print(f"[DEBUG] Matches grouped by date:")
        for date, date_matches in matches_by_date.items():
            print(f"  {date}: {len(date_matches)} matches")

        # Get the 6 most recent dates
        recent_dates = sorted(matches_by_date.keys(), key=parse_date, reverse=True)[:6]
        print(f"[DEBUG] Selected {len(recent_dates)} most recent dates: {recent_dates}")

        # Build the result with only the recent dates
        recent_matches_by_date = {}
        for date in recent_dates:
            # Sort matches for this date by court number
            def court_sort_key(match):
                court = match.get("court", "")
                if not court or not str(court).strip():
                    return float("inf")  # Put empty courts at the end
                try:
                    return int(court)
                except (ValueError, TypeError):
                    return float("inf")  # Put non-numeric courts at the end

            sorted_date_matches = sorted(matches_by_date[date], key=court_sort_key)
            recent_matches_by_date[date] = sorted_date_matches
            print(f"[DEBUG] Date {date}: Including {len(sorted_date_matches)} matches")

        return recent_matches_by_date

    except Exception as e:
        print(f"Error getting recent matches for user club: {e}")
        return {}


def calculate_player_streaks(club_name, user_league_db_id=None):
    """Calculate winning and losing streaks for players across ALL matches for the club - only show significant streaks (+5/-5)"""
    try:
        from database_utils import execute_query

        # Load ALL match history data from database
        all_matches = execute_query(
            """
            SELECT 
                TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                ms.home_team as "Home Team",
                ms.away_team as "Away Team",
                ms.winner as "Winner",
                ms.home_player_1_id as "Home Player 1",
                ms.home_player_2_id as "Home Player 2",
                ms.away_player_1_id as "Away Player 1", 
                ms.away_player_2_id as "Away Player 2",
                ms.league_id
            FROM match_scores ms
            ORDER BY ms.match_date DESC
        """
        )

        # Filter matches by user's league if provided
        if user_league_db_id:

            def is_match_in_user_league(match):
                match_league_id = match.get("league_id")

                # Integer comparison - match if league IDs are equal
                return match_league_id == user_league_db_id

            league_filtered_matches = [
                match for match in all_matches if is_match_in_user_league(match)
            ]
            print(
                f"[DEBUG] calculate_player_streaks: Filtered from {len(all_matches)} to {len(league_filtered_matches)} matches for user's league (user_league_db_id: {user_league_db_id})"
            )
            all_matches = league_filtered_matches

        player_stats = {}

        # Sort matches by date, handling None values
        def parse_date(date_str):
            for fmt in ("%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.min

        def sort_key(x):
            date = parse_date(x.get("Date", ""))
            return date or datetime(9999, 12, 31)

        # Filter and normalize all matches for the club
        club_matches = []
        for match in all_matches:
            home_team = match.get("Home Team", "")
            away_team = match.get("Away Team", "")

            if not (home_team.startswith(club_name) or away_team.startswith(club_name)):
                continue

            # Normalize match data
            normalized_match = {
                "date": match.get("Date", ""),
                "home_team": home_team,
                "away_team": away_team,
                "winner": match.get("Winner", ""),
                "home_player_1": match.get("Home Player 1", ""),
                "home_player_2": match.get("Home Player 2", ""),
                "away_player_1": match.get("Away Player 1", ""),
                "away_player_2": match.get("Away Player 2", ""),
            }
            club_matches.append(normalized_match)

        sorted_matches = sorted(club_matches, key=sort_key)

        print(
            f"[DEBUG] Found {len(sorted_matches)} total matches for club '{club_name}' across all time"
        )

        for match in sorted_matches:
            home_team = match.get("home_team", "")
            away_team = match.get("away_team", "")

            # Get all players from the match
            players = [
                match.get("home_player_1", ""),
                match.get("home_player_2", ""),
                match.get("away_player_1", ""),
                match.get("away_player_2", ""),
            ]

            for player in players:
                if not player:  # Handle None values
                    continue
                player = player.strip()
                if not player or player.lower() == "bye":
                    continue

                if player not in player_stats:
                    player_stats[player] = {
                        "matches": [],  # Store all match results for this player
                        "series": (
                            home_team.split(" - ")[1]
                            if " - " in home_team and home_team.startswith(club_name)
                            else (
                                away_team.split(" - ")[1]
                                if " - " in away_team
                                and away_team.startswith(club_name)
                                else ""
                            )
                        ),
                    }

                # Determine if player won
                is_home_player = player in [
                    match.get("home_player_1", ""),
                    match.get("home_player_2", ""),
                ]
                won = (is_home_player and match.get("winner") == "home") or (
                    not is_home_player and match.get("winner") == "away"
                )

                # Store match result
                player_stats[player]["matches"].append(
                    {"date": match.get("date", ""), "won": won}
                )

        # Calculate streaks for each player
        significant_streaks = []

        for player, stats in player_stats.items():
            if (
                len(stats["matches"]) < 5
            ):  # Need at least 5 matches to have a significant streak
                continue

            matches = sorted(stats["matches"], key=lambda x: parse_date(x["date"]))

            current_streak = 0
            best_win_streak = 0
            best_loss_streak = 0
            last_match_date = matches[-1]["date"] if matches else ""

            # Calculate current streak and best streaks
            for i, match in enumerate(matches):
                if i == 0:
                    current_streak = 1 if match["won"] else -1
                    best_win_streak = 1 if match["won"] else 0
                    best_loss_streak = 1 if not match["won"] else 0
                else:
                    prev_match = matches[i - 1]
                    if match["won"] == prev_match["won"]:
                        # Streak continues
                        if match["won"]:
                            current_streak = (
                                current_streak + 1 if current_streak > 0 else 1
                            )
                            best_win_streak = max(best_win_streak, current_streak)
                        else:
                            current_streak = (
                                current_streak - 1 if current_streak < 0 else -1
                            )
                            best_loss_streak = max(
                                best_loss_streak, abs(current_streak)
                            )
                    else:
                        # Streak broken
                        current_streak = 1 if match["won"] else -1
                        if match["won"]:
                            best_win_streak = max(best_win_streak, 1)
                        else:
                            best_loss_streak = max(best_loss_streak, 1)

            # Only include players with significant WINNING streaks (current +5 or best +5) AND no losing streaks
            has_significant_current_win = current_streak >= 5
            has_significant_best_win = best_win_streak >= 5
            is_currently_on_losing_streak = current_streak < 0

            if (has_significant_current_win or has_significant_best_win) and not is_currently_on_losing_streak:
                best_streak = max(best_win_streak, best_loss_streak)
                # Convert player ID to readable name
                player_display_name = get_player_name_from_id(player)
                significant_streaks.append(
                    {
                        "player_name": player_display_name,
                        "current_streak": current_streak,
                        "best_streak": best_streak,
                        "last_match_date": last_match_date,
                        "series": stats["series"],
                        "total_matches": len(matches),
                    }
                )

        # Sort by current streak (win streaks highest to lowest, then loss streaks)
        significant_streaks.sort(
            key=lambda x: (-x["current_streak"], -x["best_streak"])
        )

        print(
            f"[DEBUG] Found {len(significant_streaks)} players with significant winning streaks (5+ wins)"
        )

        return significant_streaks

    except Exception as e:
        print(f"Error calculating player streaks: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return []


def get_mobile_club_data(user):
    """Get comprehensive club data for mobile my club page - using match_history.json for completed matches"""
    try:
        # FIXED: Get club information from user's player associations since users table doesn't have club field
        club_name = user.get("club", "")
        user_league_id = user.get("league_id", "")
        user_email = user.get("email", "")

        print(f"[DEBUG] get_mobile_club_data called with user: {user}")
        print(f"[DEBUG] club_name: '{club_name}', league_id: '{user_league_id}', email: '{user_email}'")

        # If club_name is missing from session, look it up from user's player associations
        if not club_name and user_email:
            print(f"[DEBUG] Club name missing from session, looking up from player associations...")
            try:
                from database_utils import execute_query_one
                
                # Get club information from user's primary player association
                club_lookup_query = """
                    SELECT c.name as club_name, p.league_id, l.league_id as league_code
                    FROM users u
                    JOIN user_player_associations upa ON u.id = upa.user_id
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    JOIN clubs c ON p.club_id = c.id
                    JOIN leagues l ON p.league_id = l.id
                    WHERE u.email = %s 
                    AND (upa.is_primary = true OR upa.is_primary IS NULL)
                    ORDER BY upa.is_primary DESC NULLS LAST
                    LIMIT 1
                """
                
                club_info = execute_query_one(club_lookup_query, [user_email])
                if club_info:
                    club_name = club_info["club_name"]
                    # Also update league information if missing
                    if not user_league_id:
                        user_league_id = club_info["league_id"]
                    
                    print(f"[DEBUG] Found club from player associations: '{club_name}', league_id: {user_league_id}")
                else:
                    print(f"[DEBUG] No player association found for user {user_email}")
                    
            except Exception as e:
                print(f"[DEBUG] Error looking up club from player associations: {e}")

        if not club_name:
            print(f"[DEBUG] No club name found, returning error")
            return {
                "team_name": "Unknown",
                "this_week_results": [],
                "tennaqua_standings": [],
                "head_to_head": [],
                "player_streaks": [],
                "error": "No club information found in user profile. Please ensure you are linked to a player record.",
            }

        print(f"[DEBUG] Looking for matches from club: '{club_name}'")

        # Get recent matches from match_history.json (completed matches with results) - now grouped by date
        # First, update the user object with the club information we found
        user_with_club = user.copy()
        user_with_club["club"] = club_name
        if user_league_id:
            user_with_club["league_id"] = user_league_id
            
        matches_by_date = get_recent_matches_for_user_club(user_with_club)

        print(f"[DEBUG] Found matches for {len(matches_by_date)} different dates")

        # Initialize default values
        weekly_results = []
        tennaqua_standings = []
        head_to_head = []

        # Process each date's matches into weekly results if we have any
        if matches_by_date:
            for date, matches_data in matches_by_date.items():
                print(f"[DEBUG] Processing date {date} with {len(matches_data)} matches")

                # Group matches by team for this date
                team_matches = {}
                matches_processed = 0
                matches_skipped = 0

                for match in matches_data:
                    home_team = match["home_team"]
                    away_team = match["away_team"]

                    if club_name in home_team:
                        team = home_team
                        opponent = (
                            away_team.split(" - ")[0] if " - " in away_team else away_team
                        )
                        is_home = True
                        matches_processed += 1
                    elif club_name in away_team:
                        team = away_team
                        opponent = (
                            home_team.split(" - ")[0] if " - " in home_team else home_team
                        )
                        is_home = False
                        matches_processed += 1
                    else:
                        matches_skipped += 1
                        print(
                            f"[DEBUG] Skipping match - home: '{home_team}', away: '{away_team}' (club '{club_name}' not found)"
                        )
                        continue

                    if team not in team_matches:
                        team_matches[team] = {
                            "opponent": opponent,
                            "matches": [],
                            "team_points": 0,
                            "opponent_points": 0,
                            "series": team.split(" - ")[1] if " - " in team else team,
                        }

                    # Calculate points for this match based on set scores
                    scores = match["scores"].split(", ") if match["scores"] else []
                    match_team_points = 0
                    match_opponent_points = 0

                    # Points for each set
                    for set_score in scores:
                        if "-" in set_score:
                            try:
                                our_score, their_score = map(int, set_score.split("-"))
                                
                                # NSTF league has reversed team assignments - need to reverse score logic too
                                if user_league_id == "4933":  # NSTF league
                                    # For NSTF: if we're using away players when is_home=True, then we need to reverse the score logic
                                    if is_home:
                                        our_score, their_score = their_score, our_score
                                else:
                                    # Standard logic for other leagues (APTA, etc.)
                                    if not is_home:
                                        our_score, their_score = their_score, our_score

                                if our_score > their_score:
                                    match_team_points += 1
                                else:
                                    match_opponent_points += 1
                            except (ValueError, IndexError):
                                continue

                    # Bonus point for match win
                    # NSTF league has reversed team assignments - need to reverse win/loss logic too
                    if user_league_id == "4933":  # NSTF league
                        # For NSTF: if we're using away players when is_home=True, then we need to reverse the win logic
                        if (is_home and match["winner"] == "away") or (
                            not is_home and match["winner"] == "home"
                        ):
                            match_team_points += 1
                        else:
                            match_opponent_points += 1
                    else:
                        # Standard logic for other leagues (APTA, etc.)
                        if (is_home and match["winner"] == "home") or (
                            not is_home and match["winner"] == "away"
                        ):
                            match_team_points += 1
                        else:
                            match_opponent_points += 1

                    # Update total points
                    team_matches[team]["team_points"] += match_team_points
                    team_matches[team]["opponent_points"] += match_opponent_points

                    # Add match details
                    # FIXED: Use tenniscores_match_id to determine court number from line number
                    tenniscores_match_id = match.get("tenniscores_match_id", "")
                    court_num = None
                    
                    if tenniscores_match_id and "_Line" in tenniscores_match_id:
                        # Extract court number from tenniscores_match_id (e.g., "12345_Line2_Line2" -> 2)
                        # Handle duplicate _Line pattern by taking the last occurrence
                        line_parts = tenniscores_match_id.split("_Line")
                        if len(line_parts) > 1:
                            line_part = line_parts[-1]  # Take the last part
                            try:
                                court_num = int(line_part)
                            except ValueError:
                                # Fallback to database ID order if parsing fails
                                court_num = len(team_matches[team]["matches"]) + 1
                        else:
                            # Fallback to database ID order if no line number found
                            court_num = len(team_matches[team]["matches"]) + 1
                    else:
                        # Fallback to database ID order if no tenniscores_match_id
                        court_num = len(team_matches[team]["matches"]) + 1

                    # Resolve player IDs to readable names
                    home_player_1_name = (
                        get_player_name_from_id(match["home_player_1"])
                        if match.get("home_player_1")
                        else "Unknown"
                    )
                    home_player_2_name = (
                        get_player_name_from_id(match["home_player_2"])
                        if match.get("home_player_2")
                        else "Unknown"
                    )
                    away_player_1_name = (
                        get_player_name_from_id(match["away_player_1"])
                        if match.get("away_player_1")
                        else "Unknown"
                    )
                    away_player_2_name = (
                        get_player_name_from_id(match["away_player_2"])
                        if match.get("away_player_2")
                        else "Unknown"
                    )

                    # NSTF league has reversed team assignments - need to reverse score display and win logic
                    if user_league_id == "4933":  # NSTF league
                        # For NSTF: reverse the score display and win logic
                            if is_home:
                                # When home team, show away players first (our team) vs home players (opponents)
                                home_players_display = f"{away_player_1_name}/{away_player_2_name}"
                                away_players_display = f"{home_player_1_name}/{home_player_2_name}"
                                # Keep original scores for display (don't reverse them)
                                scores_display = match["scores"]
                                # NSTF league has reversed team assignments - need to invert the won logic for correct colors
                                actual_won = (is_home and match["winner"] == "home") or (not is_home and match["winner"] == "away")
                                won = actual_won  # Use actual win logic for NSTF (no inversion needed)
                            else:
                                # When away team, show home players first (our team) vs away players (opponents)
                                home_players_display = f"{home_player_1_name}/{home_player_2_name}"
                                away_players_display = f"{away_player_1_name}/{away_player_2_name}"
                                scores_display = match["scores"]
                                # NSTF league has reversed team assignments - need to invert the won logic for correct colors
                                actual_won = (is_home and match["winner"] == "home") or (not is_home and match["winner"] == "away")
                                won = actual_won  # Use actual win logic for NSTF (no inversion needed)
                    else:
                        # Standard logic for other leagues (APTA, etc.)
                        home_players_display = (
                            f"{home_player_1_name}/{home_player_2_name}"
                            if is_home
                            else f"{away_player_1_name}/{away_player_2_name}"
                        )
                        away_players_display = (
                            f"{away_player_1_name}/{away_player_2_name}"
                            if is_home
                            else f"{home_player_1_name}/{home_player_2_name}"
                        )
                        scores_display = match["scores"]
                        won = (is_home and match["winner"] == "home") or (not is_home and match["winner"] == "away")
                    
                    team_matches[team]["matches"].append(
                        {
                            "court": court_num,
                            "home_players": home_players_display,
                            "away_players": away_players_display,
                            "scores": scores_display,
                            "won": won,
                        }
                    )

                print(
                    f"[DEBUG] Date {date}: Processed {matches_processed} matches, skipped {matches_skipped}, found {len(team_matches)} teams"
                )
                for team, data in team_matches.items():
                    print(
                        f"  Team '{team}': {len(data['matches'])} matches vs {data['opponent']}"
                    )

                # Convert this date's matches to results format
                date_results = []
                for team_data in team_matches.values():
                    date_results.append(
                        {
                            "series": (
                                f"Series {team_data['series']}"
                                if team_data["series"].isdigit()
                                else team_data["series"]
                            ),
                            "opponent": team_data["opponent"],
                            "score": f"{team_data['team_points']}-{team_data['opponent_points']}",
                            "won": team_data["team_points"] > team_data["opponent_points"],
                            "match_details": sorted(
                                team_data["matches"], key=lambda x: x["court"]
                            ),
                        }
                    )

                # Sort results by opponent name
                date_results.sort(key=lambda x: x["opponent"])

                # Add this week's results to the weekly results
                weekly_results.append({"date": date, "results": date_results})

        # Sort weekly results by date (most recent first)
        def parse_date(date_str):
            for fmt in ("%d-%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.min

        weekly_results.sort(key=lambda x: parse_date(x["date"]), reverse=True)

        # Calculate club standings using series_stats table - much simpler and faster
        from database_utils import execute_query, execute_query_one

        # Get user league information for filtering
        user_league_name = user.get("league_name", "")
        
        print(f"[DEBUG] Session league context - league_id: '{user_league_id}', league_name: '{user_league_name}'")

        # Convert string league_id to integer primary key for proper filtering
        user_league_db_id = None
        if user_league_id:
            try:
                if isinstance(user_league_id, str) and user_league_id != "":
                    league_lookup = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", (user_league_id,)
                    )
                    if league_lookup:
                        user_league_db_id = league_lookup["id"]
                        print(f"[DEBUG] Converted string league_id '{user_league_id}' to database ID: {user_league_db_id}")
                elif isinstance(user_league_id, int):
                    user_league_db_id = user_league_id
            except Exception as e:
                print(f"[DEBUG] Error looking up league ID: {e}")
                
        # Fallback to primary league association if needed
        if user_league_db_id is None:
            try:
                user_email = user.get("email", "")
                if user_email:
                    primary_league_query = """
                        SELECT l.id, u.league_context FROM users u
                        JOIN user_player_associations upa ON u.id = upa.user_id
                        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                        JOIN leagues l ON p.league_id = l.id
                        WHERE u.email = %s 
                        AND (u.league_context IS NULL OR p.league_id = u.league_context)
                        ORDER BY (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END)
                        LIMIT 1
                    """
                    primary_league = execute_query_one(primary_league_query, [user_email])
                    if primary_league:
                        user_league_db_id = primary_league["id"]
            except Exception as e:
                print(f"[DEBUG] Error looking up primary league: {e}")

        tennaqua_standings = []
        try:
            # Simple direct query from series_stats - no complex calculations needed
            club_standings_query = """
                SELECT 
                    ss.series,
                    ss.team,
                    ss.points,
                    ss.matches_won + ss.matches_lost + ss.matches_tied as total_matches,
                    ss.points as total_points,
                    CASE 
                        WHEN (ss.matches_won + ss.matches_lost + ss.matches_tied) > 0 
                        THEN ROUND(CAST(ss.points AS DECIMAL) / (ss.matches_won + ss.matches_lost + ss.matches_tied), 1)
                        ELSE 0 
                    END as avg_points
                FROM series_stats ss
                WHERE ss.team LIKE %s 
                AND (%s IS NULL OR ss.league_id = %s)
                ORDER BY ss.series, ss.points DESC
            """
            
            club_teams = execute_query(club_standings_query, [f"{club_name}%", user_league_db_id, user_league_db_id])
            print(f"[DEBUG] Found {len(club_teams)} {club_name} teams in series_stats")

            for team_stats in club_teams:
                series = team_stats["series"]
                
                # Get all teams in this series for ranking
                series_teams_query = """
                    SELECT ss.team, ss.points,
                           CASE 
                               WHEN (ss.matches_won + ss.matches_lost + ss.matches_tied) > 0 
                               THEN ROUND(CAST(ss.points AS DECIMAL) / (ss.matches_won + ss.matches_lost + ss.matches_tied), 1)
                               ELSE 0 
                           END as avg_points
                    FROM series_stats ss
                    WHERE ss.series = %s 
                    AND (%s IS NULL OR ss.league_id = %s)
                    ORDER BY ss.points DESC
                """
                
                series_teams = execute_query(series_teams_query, [series, user_league_db_id, user_league_db_id])
                
                # Find our team's position
                place = 1
                for i, team in enumerate(series_teams, 1):
                    if team["team"] == team_stats["team"]:
                        place = i
                        break
                
                tennaqua_standings.append({
                    "series": series,
                    "team_name": team_stats["team"],
                    "place": place,
                    "total_points": int(team_stats["total_points"]),
                    "avg_points": float(team_stats["avg_points"]),
                    "playoff_contention": place <= 8,
                    "total_teams_in_series": len(series_teams),
                })

            # Sort standings by place (ascending)
            tennaqua_standings.sort(key=lambda x: x["place"])

        except Exception as e:
            print(f"Error loading series stats from database: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")

        # Calculate head-to-head records (filtered by user's league)
        head_to_head = {}

        # Load ALL match history from database for comprehensive head-to-head records
        try:
            all_match_history = execute_query(
                """
                SELECT 
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.winner as "Winner",
                    ms.league_id
                FROM match_scores ms
                ORDER BY ms.match_date DESC
            """
            )

            # Filter match history by user's current league session context
            def is_match_in_user_league(match):
                match_league_id = match.get("league_id")

                # Handle case where user_league_db_id is None or empty
                if user_league_db_id is None:
                    # If user has no league specified, include all matches
                    return True

                # FIXED: Use integer-to-integer comparison for current league only
                return match_league_id == user_league_db_id

            league_filtered_matches = [
                match for match in all_match_history if is_match_in_user_league(match)
            ]
            print(
                f"[DEBUG] Filtered from {len(all_match_history)} total matches to {len(league_filtered_matches)} matches in user's current league (session league_id: '{user_league_id}' -> db_id: {user_league_db_id}, league_name: '{user_league_name}')"
            )

            for match in league_filtered_matches:
                home_team = match.get("Home Team", "")
                away_team = match.get("Away Team", "")
                winner = match.get("Winner", "")

                if not all([home_team, away_team, winner]):
                    continue

                # Check if this match involves our club
                if club_name in home_team:
                    opponent = (
                        away_team.split(" - ")[0] if " - " in away_team else away_team
                    )
                    won = winner == "home"
                elif club_name in away_team:
                    opponent = (
                        home_team.split(" - ")[0] if " - " in home_team else home_team
                    )
                    won = winner == "away"
                else:
                    continue

                if opponent not in head_to_head:
                    head_to_head[opponent] = {"wins": 0, "losses": 0, "total": 0}

                head_to_head[opponent]["total"] += 1
                if won:
                    head_to_head[opponent]["wins"] += 1
                else:
                    head_to_head[opponent]["losses"] += 1

            print(
                f"[DEBUG] Found head-to-head records against {len(head_to_head)} different clubs"
            )

        except Exception as e:
            print(f"Error loading all match history for head-to-head: {str(e)}")
            # Fallback to recent matches if all match history fails
            for date, matches_data in matches_by_date.items():
                for match in matches_data:
                    home_team = match.get("home_team", "")
                    away_team = match.get("away_team", "")
                    winner = match.get("winner", "")

                    if not all([home_team, away_team, winner]):
                        continue

                    if club_name in home_team:
                        opponent = (
                            away_team.split(" - ")[0]
                            if " - " in away_team
                            else away_team
                        )
                        won = winner == "home"
                    elif club_name in away_team:
                        opponent = (
                            home_team.split(" - ")[0]
                            if " - " in home_team
                            else home_team
                        )
                        won = winner == "away"
                    else:
                        continue

                    if opponent not in head_to_head:
                        head_to_head[opponent] = {"wins": 0, "losses": 0, "total": 0}

                    head_to_head[opponent]["total"] += 1
                    if won:
                        head_to_head[opponent]["wins"] += 1
                    else:
                        head_to_head[opponent]["losses"] += 1

        # Convert head-to-head to list
        head_to_head = [
            {
                "opponent": opponent,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "total": stats["total"],
                "matches_scheduled": stats["total"],  # For template compatibility
            }
            for opponent, stats in head_to_head.items()
        ]

        # Sort by win percentage (highest to lowest), then by total matches as tiebreaker
        head_to_head.sort(
            key=lambda x: (x["wins"] / x["total"] if x["total"] > 0 else 0, x["total"]),
            reverse=True,
        )

        # Calculate player streaks (filtered by user's current league)
        print(f"[DEBUG] Calling calculate_player_streaks with club_name='{club_name}', user_league_db_id={user_league_db_id}")
        player_streaks = calculate_player_streaks(club_name, user_league_db_id)

        return {
            "team_name": club_name,
            "weekly_results": weekly_results,
            "tennaqua_standings": tennaqua_standings,
            "head_to_head": head_to_head,
            "player_streaks": player_streaks,
        }

    except Exception as e:
        print(f"Error getting mobile club data: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "team_name": user.get("club", "Unknown"),
            "weekly_results": [],
            "tennaqua_standings": [],
            "head_to_head": [],
            "player_streaks": [],
            "error": str(e),
        }


def get_mobile_player_stats(user):
    """Get player stats for mobile player stats page"""
    try:
        # TODO: Extract player stats logic from server.py
        return {
            "player_stats": {},
            "recent_matches": [],
            "error": "Function not yet extracted from server.py",
        }
    except Exception as e:
        print(f"Error getting mobile player stats: {str(e)}")
        return {"error": str(e)}


def get_practice_times_data(user):
    """Get practice times data for mobile practice times page"""
    try:
        # Get user's club and series information for context
        user_club = user.get("club", "")
        user_series = user.get("series", "")

        # For now, this just returns context data for the form
        # The actual logic is in the API endpoints for add/remove
        return {
            "user_club": user_club,
            "user_series": user_series,
            "practice_times": [],
            "user_preferences": {},
        }
    except Exception as e:
        print(f"Error getting practice times data: {str(e)}")
        return {
            "user_club": user.get("club", ""),
            "user_series": user.get("series", ""),
            "practice_times": [],
            "user_preferences": {},
            "error": str(e),
        }


def get_all_team_availability_data(user, selected_date=None):
    """
    Get all team availability data for mobile page - uses user-player associations for proper player lookup

    FIXED: Now uses the same user-player association system as the working availability functions
    instead of relying on JSON files. This ensures proper handling of users with multiple
    player records sharing the same Player ID.
    """
    try:
        # Handle missing parameters
        if not selected_date:
            return {
                "players_schedule": {},
                "selected_date": "today",
                "error": "No date selected",
            }

        # Get user information
        if not user:
            return {
                "players_schedule": {},
                "selected_date": selected_date,
                "error": "User not found in session",
            }

        user_id = user.get("id")
        club_name = user.get("club")
        series = user.get("series")

        print(
            f"\n=== ALL TEAM AVAILABILITY DATA REQUEST (FIXED WITH USER ASSOCIATIONS) ==="
        )
        print(f"User: {user.get('email')} (ID: {user_id})")
        print(f"Club: {club_name}")
        print(f"Series: {series}")
        print(f"Selected Date: {selected_date}")

        if not club_name or not series:
            return {
                "players_schedule": {},
                "selected_date": selected_date,
                "error": "Please verify your club and series are correct in your profile settings",
            }

        # Get series ID from database
        from database_utils import execute_query, execute_query_one
        from utils.date_utils import date_to_db_timestamp

        series_record = execute_query_one(
            "SELECT id, name FROM series WHERE name = %s", (series,)
        )
        if not series_record:
            print(f"❌ Series not found: {series}")
            return {
                "players_schedule": {},
                "selected_date": selected_date,
                "error": f'Series "{series}" not found in database',
            }

        # Convert selected_date once for all queries
        try:
            if "/" in selected_date:
                # Convert MM/DD/YYYY to proper UTC timestamp
                selected_date_utc = date_to_db_timestamp(selected_date)
            else:
                # Convert YYYY-MM-DD to proper UTC timestamp
                selected_date_utc = date_to_db_timestamp(selected_date)

            print(
                f"Converted selected_date {selected_date} to UTC timestamp: {selected_date_utc}"
            )
        except Exception as e:
            print(f"❌ Error converting selected_date {selected_date}: {e}")
            return {
                "players_schedule": {},
                "selected_date": selected_date,
                "error": f"Invalid date format: {selected_date}",
            }

        # FIXED: Use database to get team players instead of JSON files
        # Get all players for this club and series from the database
        try:
            team_players_query = """
                SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                       c.name as club_name, s.name as series_name
                FROM players p
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                WHERE c.name = %s AND s.name = %s AND p.is_active = true
                ORDER BY p.first_name, p.last_name
            """

            team_players_data = execute_query(team_players_query, (club_name, series))

            if not team_players_data:
                print(f"❌ No players found in database for {club_name} - {series}")
                return {
                    "players_schedule": {},
                    "selected_date": selected_date,
                    "error": f"No players found for {club_name} - {series}",
                }

            print(
                f"Found {len(team_players_data)} players in database for {club_name} - {series}"
            )

            # Create lookup structures for efficient processing
            team_player_names = []
            team_players_display = {}
            player_id_lookup = {}

            for player in team_players_data:
                full_name = f"{player['first_name']} {player['last_name']}"
                team_player_names.append(full_name)
                team_players_display[full_name] = f"{full_name} ({club_name})"
                player_id_lookup[full_name] = player["id"]  # Store internal player ID

        except Exception as e:
            print(f"❌ Error querying team players from database: {e}")
            import traceback

            print(traceback.format_exc())
            return {
                "players_schedule": {},
                "selected_date": selected_date,
                "error": "Error loading player data from database",
            }

        # Use clean player_id-only query now that data integrity is fixed
        try:
            # Get all internal player IDs for the bulk query
            internal_player_ids = list(player_id_lookup.values())

            # Create a single query to get all availability data using internal player IDs
            placeholders = ",".join(["%s"] * len(internal_player_ids))
            bulk_query = f"""
                SELECT pa.player_id, pa.player_name, pa.availability_status, pa.notes
                FROM player_availability pa
                WHERE pa.player_id IN ({placeholders})
                AND pa.series_id = %s 
                AND DATE(pa.match_date AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
            """

            # Parameters: all internal player IDs + series_id + date
            bulk_params = tuple(internal_player_ids) + (
                series_record["id"],
                selected_date_utc,
            )

            print(
                f"Executing clean availability query for {len(internal_player_ids)} players using player IDs..."
            )
            availability_results = execute_query(bulk_query, bulk_params)

            # Convert results to dictionary for fast lookup by internal player ID
            availability_lookup = {}
            for result in availability_results:
                availability_lookup[result["player_id"]] = {
                    "availability_status": result["availability_status"],
                    "notes": result.get("notes", "") or "",
                }

            print(f"Found availability data for {len(availability_lookup)} players")

        except Exception as e:
            print(f"❌ Error in availability query: {e}")
            import traceback

            print(traceback.format_exc())
            return {
                "players_schedule": {},
                "selected_date": selected_date,
                "error": "Error querying availability data",
            }

        # Build players_schedule efficiently using internal player IDs
        players_schedule = {}
        for player_name in team_player_names:
            # Get internal player ID for this player
            internal_player_id = player_id_lookup[player_name]

            # Get availability data from lookup (default to status 0 and empty notes if not found)
            availability_data = availability_lookup.get(
                internal_player_id, {"availability_status": 0, "notes": ""}
            )
            status = availability_data["availability_status"]
            notes = availability_data["notes"]

            # Create availability record
            availability = [
                {"date": selected_date, "availability_status": status, "notes": notes}
            ]

            # Store with display name
            display_name = team_players_display[player_name]
            players_schedule[display_name] = availability

        if not players_schedule:
            print("❌ No player schedules created")
            return {
                "players_schedule": {},
                "selected_date": selected_date,
                "error": "No player schedules found for your series",
            }

        print(
            f"✅ Successfully created availability schedule for {len(players_schedule)} players using user-player associations"
        )

        return {"players_schedule": players_schedule, "selected_date": selected_date}

    except Exception as e:
        print(f"Error getting all team availability data: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "players_schedule": {},
            "selected_date": selected_date or "today",
            "error": str(e),
        }


def get_club_players_data(
    user,
    series_filter=None,
    first_name_filter=None,
    last_name_filter=None,
    pti_min=None,
    pti_max=None,
    club_only=True,
):
    """Get players with optional filtering (filtered by user's league and optionally by club)"""
    try:
        # Get user's club and league from user data
        user_club = user.get("club")
        user_league_id = user.get("league_id", "")
        user_league_context = user.get("league_context")  # This should be the integer DB ID

        if club_only and not user_club:
            return {
                "players": [],
                "available_series": [],
                "pti_range": {"min": -30, "max": 100},
                "user_club": user_club or "Unknown Club",
                "error": "User club not found",
            }

        print(f"\n=== DEBUG: get_club_players_data ===")
        print(f"User club: '{user_club}', league_id: '{user_league_id}', league_context: '{user_league_context}'")
        print(f"Club only: {club_only}")
        print(
            f"Filters - Series: {series_filter}, First: {first_name_filter}, Last: {last_name_filter}, PTI: {pti_min}-{pti_max}"
        )

        # Get the correct league database ID
        user_league_db_id = None
        
        # First try league_context (should be integer DB ID)
        if user_league_context:
            try:
                user_league_db_id = int(user_league_context)
                print(f"Using league_context as DB ID: {user_league_db_id}")
            except (ValueError, TypeError):
                print(f"league_context is not a valid integer: {user_league_context}")

        # Fallback: convert string league_id to DB ID
        if not user_league_db_id and user_league_id:
            try:
                if isinstance(user_league_id, int):
                    user_league_db_id = user_league_id
                    print(f"league_id is already integer: {user_league_db_id}")
                else:
                    # Convert string league_id to integer DB ID
                    from database_utils import execute_query_one
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        user_league_db_id = league_record["id"]
                        print(f"Converted league_id '{user_league_id}' to DB ID: {user_league_db_id}")
                    else:
                        print(f"League '{user_league_id}' not found in database")
            except Exception as e:
                print(f"Error converting league_id: {e}")

        if not user_league_db_id:
            # Final fallback: get user's league from their player record
            try:
                user_email = user.get("email")
                if user_email:
                    from database_utils import execute_query_one
                    user_player_query = """
                        SELECT DISTINCT p.league_id 
                        FROM players p
                        JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                        JOIN users u ON upa.user_id = u.id
                        WHERE u.email = %s AND p.is_active = true
                        LIMIT 1
                    """
                    user_player_result = execute_query_one(user_player_query, [user_email])
                    if user_player_result:
                        user_league_db_id = user_player_result["league_id"]
                        print(f"[FALLBACK] Found user's league from player record: {user_league_db_id}")
                    else:
                        print(f"[FALLBACK] No player record found for email: {user_email}")
            except Exception as e:
                print(f"[FALLBACK] Error looking up user's league: {e}")
        
        if not user_league_db_id:
            return {
                "players": [],
                "available_series": [],
                "pti_range": {"min": -30, "max": 100},
                "user_club": user_club or "Unknown Club",
                "error": f"Could not determine user's league context",
            }

        # MAJOR CHANGE: Load players directly from database with team information
        # This creates separate entries for players on multiple teams
        from database_utils import execute_query, execute_query_one
        
        print(f"Loading players for league database ID: {user_league_db_id}")
        
        try:
            # OPTIMIZED: Single comprehensive query using CTEs to get all data at once
            # This eliminates N+1 queries by calculating everything in one go
            comprehensive_query = """
                WITH player_latest_pti AS (
                    -- Get the most recent PTI from player_history for players with NULL PTI
                    SELECT DISTINCT ON (player_id) 
                        player_id, 
                        end_pti as latest_pti
                    FROM player_history 
                    WHERE end_pti IS NOT NULL
                    ORDER BY player_id, date DESC
                ),
                player_match_records AS (
                    -- Calculate win/loss records for each player-team combination in one query
                    SELECT 
                        player_id,
                        team_id,
                        SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN NOT won THEN 1 ELSE 0 END) as losses
                    FROM (
                        -- Home team players
                        SELECT 
                            NULLIF(TRIM(ms.home_player_1_id), '') as player_id,
                            ms.home_team_id as team_id,
                            ms.winner = 'home' as won
                        FROM match_scores ms 
                        WHERE ms.league_id = %s AND ms.winner IS NOT NULL
                        AND NULLIF(TRIM(ms.home_player_1_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        SELECT 
                            NULLIF(TRIM(ms.home_player_2_id), '') as player_id,
                            ms.home_team_id as team_id,
                            ms.winner = 'home' as won
                        FROM match_scores ms 
                        WHERE ms.league_id = %s AND ms.winner IS NOT NULL
                        AND NULLIF(TRIM(ms.home_player_2_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        -- Away team players  
                        SELECT 
                            NULLIF(TRIM(ms.away_player_1_id), '') as player_id,
                            ms.away_team_id as team_id,
                            ms.winner = 'away' as won
                        FROM match_scores ms 
                        WHERE ms.league_id = %s AND ms.winner IS NOT NULL
                        AND NULLIF(TRIM(ms.away_player_1_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        SELECT 
                            NULLIF(TRIM(ms.away_player_2_id), '') as player_id,
                            ms.away_team_id as team_id,
                            ms.winner = 'away' as won
                        FROM match_scores ms 
                        WHERE ms.league_id = %s AND ms.winner IS NOT NULL
                        AND NULLIF(TRIM(ms.away_player_2_id), '') IS NOT NULL
                    ) all_player_matches
                    WHERE player_id IS NOT NULL
                    GROUP BY player_id, team_id
                )
                SELECT 
                    p.first_name as "First Name",
                    p.last_name as "Last Name", 
                    p.tenniscores_player_id as "Player ID",
                    p.id as "Database ID",
                    -- Use current PTI or fallback to latest from history
                    COALESCE(p.pti, pti.latest_pti) as "Current PTI",
                    c.name as "Club",
                    s.name as "Series",
                    l.league_id as "League",
                    t.id as "Team ID",
                    t.team_name as "Team Name",
                    -- Use calculated records or default to 0
                    COALESCE(pmr.wins, 0) as "Wins",
                    COALESCE(pmr.losses, 0) as "Losses"
                FROM players p
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id  
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN player_latest_pti pti ON p.id = pti.player_id
                LEFT JOIN player_match_records pmr ON p.tenniscores_player_id = pmr.player_id 
                    AND t.id = pmr.team_id
                WHERE p.tenniscores_player_id IS NOT NULL
                AND p.league_id = %s
                AND p.is_active = true
                ORDER BY p.first_name, p.last_name, t.team_name
            """
            
            # Execute the comprehensive query with league_id repeated for each CTE
            all_players = execute_query(comprehensive_query, (
                user_league_db_id,  # For first player_match_records subquery
                user_league_db_id,  # For second player_match_records subquery  
                user_league_db_id,  # For third player_match_records subquery
                user_league_db_id,  # For fourth player_match_records subquery
                user_league_db_id   # For main query
            ))
            
            print(f"Loaded {len(all_players)} player-team entries with records from database (OPTIMIZED)")
            
            # Convert PTI values to strings and handle nulls
            for player in all_players:
                current_pti = player.get("Current PTI")
                if current_pti is not None:
                    player["PTI"] = str(current_pti)
                else:
                    player["PTI"] = "N/A"
            
            print("Optimized query completed - no N+1 queries needed!")
            
            # Debug: Check for Werman specifically to diagnose the multi-team issue
            werman_entries = [p for p in all_players if "werman" in p.get("Last Name", "").lower()]
            if werman_entries:
                print(f"[DEBUG] Found {len(werman_entries)} Werman entries in database:")
                for entry in werman_entries:
                    print(f"  - {entry.get('First Name')} {entry.get('Last Name')} in {entry.get('Series')} at {entry.get('Club')} (Team: {entry.get('Team Name')}, Team ID: {entry.get('Team ID')}) - Record: {entry.get('Wins')}W-{entry.get('Losses')}L")
            else:
                print(f"[DEBUG] No Werman entries found in database")
                
        except Exception as e:
            print(f"Error loading players from database: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {
                "players": [],
                "available_series": [],
                "pti_range": {"min": -30, "max": 100},
                "user_club": user_club or "Unknown Club",
                "error": f"Failed to load player data: {str(e)}",
            }

        # League filtering is now handled by the database query above

        if not all_players:
            return {
                "players": [],
                "available_series": [],
                "pti_range": {"min": -30, "max": 100},
                "pti_filters_available": False,
                "user_club": user_club or "Unknown Club",
                "error": "Error loading player data",
            }

        # Check if players in this league have valid PTI values
        valid_pti_count = 0
        total_players_checked = 0
        for player in all_players:
            total_players_checked += 1
            try:
                pti_str = str(player.get("PTI", "N/A")).strip()
                if pti_str and pti_str != "N/A" and pti_str != "":
                    float(pti_str)  # Test if it's a valid number
                    valid_pti_count += 1
            except (ValueError, TypeError):
                continue

        # Determine if PTI filters should be available
        # Show PTI filters only if at least 10% of players have valid PTI values
        pti_percentage = (
            (valid_pti_count / total_players_checked * 100)
            if total_players_checked > 0
            else 0
        )
        pti_filters_available = pti_percentage >= 10.0

        print(
            f"[DEBUG] PTI analysis: {valid_pti_count}/{total_players_checked} players have valid PTI ({pti_percentage:.1f}%)"
        )
        print(f"[DEBUG] PTI filters available: {pti_filters_available}")

        # Debug: Show unique clubs in data and check counts
        clubs_in_data = set()
        user_club_count = 0
        for player in all_players:
            clubs_in_data.add(player["Club"])
            if player["Club"] == user_club:
                user_club_count += 1

        print(f"Total players in file: {len(all_players)}")
        if club_only:
            print(f"Players with user's club '{user_club}': {user_club_count}")
        else:
            print(f"Showing players from all clubs (club_only=False)")
        print(f"All clubs in data: {sorted(list(clubs_in_data))}")

        # Load contact information from CSV directory file
        contact_info = {}
        try:
            # Get user's league for dynamic path
            # FIXED: Use league_string_id instead of league_id (which is now an integer)
            user_league_string_id = user.get("league_string_id", "")

            # Use dynamic path based on league
            if user_league_string_id and not user_league_string_id.startswith("APTA"):
                # For non-APTA leagues, use league-specific path
                csv_path = os.path.join(
                    "data",
                    "leagues",
                    user_league_string_id,
                    "club_directories",
                    "directory_tennaqua.csv",
                )
            else:
                # For APTA leagues, use the main directory
                csv_path = os.path.join(
                    "data",
                    "leagues",
                    "all",
                    "club_directories",
                    "directory_tennaqua.csv",
                )

            print(f"Looking for contact info CSV at: {csv_path}")

            if os.path.exists(csv_path):
                import csv

                with open(csv_path, "r") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        # Create full name from CSV columns (First and Last Name)
                        first_name = row.get("First", "").strip()
                        last_name = row.get("Last Name", "").strip()

                        if first_name and last_name:
                            full_name = f"{first_name} {last_name}"
                            contact_info[full_name.lower()] = {
                                "phone": row.get("Phone", "").strip(),
                                "email": row.get("Email", "").strip(),
                            }

                print(f"Loaded {len(contact_info)} contact records from CSV file")
            else:
                print(f"Contact CSV file not found at: {csv_path}")

        except Exception as e:
            print(f"Error loading contact info from CSV: {e}")
            # Continue without contact info

        # Calculate PTI range from ALL players in the file (for slider bounds)
        all_pti_values = []
        for player in all_players:
            try:
                pti_value = float(player["PTI"])
                all_pti_values.append(pti_value)
            except (ValueError, TypeError):
                continue

        # Set PTI range based on all players in the system
        pti_range = {"min": -30, "max": 100}
        if all_pti_values:
            pti_range = {"min": min(all_pti_values), "max": max(all_pti_values)}

        # Filter players by club and other criteria
        filtered_players = []
        club_series = (
            set()
        )  # Track all series (at user's club if club_only, otherwise all clubs)
        
        # Debug: Track Werman entries through filtering
        werman_entries_processed = 0
        werman_entries_filtered = []

        for player in all_players:
            # Debug: Track Werman entries specifically
            is_werman = "werman" in player.get("Last Name", "").lower()
            if is_werman:
                werman_entries_processed += 1
                print(f"[DEBUG] Processing Werman entry #{werman_entries_processed}: {player.get('First Name')} {player.get('Last Name')} in {player.get('Series')}")
            
            # Debug: Log first few club comparisons
            if len(filtered_players) < 3:
                if club_only:
                    print(
                        f"Comparing: player['Club']='{player['Club']}' == user_club='{user_club}' ? {player['Club'] == user_club}"
                    )
                else:
                    print(
                        f"Including player from club: '{player['Club']}' (club_only=False)"
                    )

            # Filter by club based on club_only parameter
            club_match = True  # Default to include all players if not filtering by club
            if club_only:
                club_match = (
                    player["Club"] == user_club
                )  # Only include players from user's club
                
                # Debug: Track Werman club filtering
                if is_werman and not club_match:
                    print(f"[DEBUG] Werman filtered out by club: '{player['Club']}' != '{user_club}'")

            if club_match:
                club_series.add(player["Series"])

                # Handle PTI values - allow "N/A" and non-numeric values
                try:
                    pti_value = float(player["PTI"])
                except (ValueError, TypeError):
                    # For "N/A" or non-numeric PTI, set a default value that won't be filtered out
                    pti_value = 50.0  # Use middle value so it passes most PTI filters
                    print(
                        f"Player {player['First Name']} {player['Last Name']} has non-numeric PTI '{player['PTI']}', using default value 50.0"
                    )

                # Apply filters with Werman-specific debugging
                if series_filter and player["Series"] != series_filter:
                    if is_werman:
                        print(f"[DEBUG] Werman filtered out by series: {player['Series']} != {series_filter}")
                    continue

                if (
                    first_name_filter
                    and first_name_filter.lower() not in player["First Name"].lower()
                ):
                    if is_werman:
                        print(f"[DEBUG] Werman filtered out by first name: '{first_name_filter}' not in '{player['First Name']}'")
                    continue

                if (
                    last_name_filter
                    and last_name_filter.lower() not in player["Last Name"].lower()
                ):
                    if is_werman:
                        print(f"[DEBUG] Werman filtered out by last name: '{last_name_filter}' not in '{player['Last Name']}'")
                    continue

                if pti_min is not None and pti_value < pti_min:
                    if is_werman:
                        print(f"[DEBUG] Werman filtered out by PTI min: {pti_value} < {pti_min}")
                    continue

                if pti_max is not None and pti_value > pti_max:
                    if is_werman:
                        print(f"[DEBUG] Werman filtered out by PTI max: {pti_value} > {pti_max}")
                    continue

                # Get real contact info from CSV
                player_name = f"{player['First Name']} {player['Last Name']}"
                player_contact = contact_info.get(player_name.lower(), {})

                # Use clean player name - club and series will be shown separately
                display_name = player_name

                # Calculate win percentage in Python (since we removed it from SQL)
                wins = player["Wins"]
                losses = player["Losses"]
                total_matches = wins + losses
                if total_matches > 0:
                    win_percentage = (wins / total_matches) * 100
                    win_rate = f"{win_percentage:.1f}%"
                else:
                    win_rate = "0%"

                # Debug: Track if this is a Werman entry being added
                if is_werman:
                    print(f"[DEBUG] Adding Werman to filtered results: {display_name} in {player['Series']} (PTI: {player['PTI']}, Record: {wins}W-{losses}L)")
                    werman_entries_filtered.append({
                        "name": display_name,
                        "series": player["Series"],
                        "team_name": player.get("Team Name", "")
                    })

                # Debug PTI values for troubleshooting
                if "morgan" in display_name.lower():
                    print(f"[DEBUG] PTI for {display_name}: '{player['PTI']}' (type: {type(player['PTI'])})")

                # Create unique identifier that includes team context for players on multiple teams
                # Use format: playerID_teamID to distinguish between same player on different teams
                team_id = player.get("Team ID")
                if team_id:
                    unique_player_id = f"{player['Player ID']}_team_{team_id}"
                else:
                    unique_player_id = player["Player ID"]

                # Add player to results with clean player name
                filtered_players.append(
                    {
                        "name": display_name,  # Clean player name without team info
                        "firstName": player["First Name"],
                        "lastName": player["Last Name"],
                        "playerId": unique_player_id,  # Unique ID that includes team context
                        "club": player["Club"],  # Add club name for display
                        "series": player["Series"],
                        "pti": player["PTI"],  # Keep original PTI value for display
                        "wins": wins,
                        "losses": losses,
                        "winRate": win_rate,  # Calculate win rate in Python
                        "phone": player_contact.get("phone", ""),
                        "email": player_contact.get("email", ""),
                    }
                )

        # Sort players by PTI (ascending - lower PTI is better)
        # Handle "N/A" PTI values by treating them as a high number for sorting
        def get_sort_pti(player):
            try:
                return float(player["pti"])
            except (ValueError, TypeError):
                return 999.0  # Put "N/A" values at the end

        filtered_players.sort(key=get_sort_pti)

        if club_only:
            print(f"Found {len(filtered_players)} players at {user_club}")
        else:
            print(f"Found {len(filtered_players)} players from all clubs")
        print(f"Available series: {sorted(club_series)}")
        print(f"PTI range (from all players): {pti_range}")
        
        # Debug: Final Werman summary
        print(f"[DEBUG] WERMAN SUMMARY:")
        print(f"  - Database entries processed: {werman_entries_processed}")
        print(f"  - Entries that passed filtering: {len(werman_entries_filtered)}")
        if werman_entries_filtered:
            for entry in werman_entries_filtered:
                print(f"    * {entry['name']} in {entry['series']} (Team: {entry['team_name']})")
        
        print("=== END DEBUG ===\n")

        return {
            "players": filtered_players,
            "available_series": sorted(
                club_series,
                key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 999,
            ),
            "pti_range": pti_range,
            "pti_filters_available": pti_filters_available,
            "user_club": user_club or "Unknown Club",
            "debug": {
                "user_club": user_club,
                "club_only": club_only,
                "total_players_in_file": len(all_players),
                "players_at_user_club": user_club_count,
                "all_clubs": sorted(list(clubs_in_data)),
            },
        }

    except Exception as e:
        print(f"Error getting club players data: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "players": [],
            "available_series": [],
            "pti_range": {"min": -30, "max": 100},
            "pti_filters_available": False,
            "user_club": user.get("club") or "Unknown Club",
            "error": str(e),
        }


def get_mobile_improve_data(user):
    """Get data for the mobile improve page including paddle tips and training guide"""
    try:
        # Load paddle tips from JSON file
        paddle_tips = []
        try:
            # Use current working directory since server.py runs from project root
            tips_path = os.path.join(
                "data", "leagues", "all", "improve_data", "paddle_tips.json"
            )
            with open(tips_path, "r", encoding="utf-8") as f:
                tips_data = json.load(f)
                paddle_tips = tips_data.get("paddle_tips", [])
        except Exception as tips_error:
            print(f"Error loading paddle tips: {str(tips_error)}")
            # Continue without tips if file can't be loaded

        # Load training guide data for video references
        training_guide = {}
        try:
            # Use current working directory since server.py runs from project root
            guide_path = os.path.join(
                "data",
                "leagues",
                "all",
                "improve_data",
                "complete_platform_tennis_training_guide.json",
            )
            with open(guide_path, "r", encoding="utf-8") as f:
                training_guide = json.load(f)
        except Exception as guide_error:
            print(f"Error loading training guide: {str(guide_error)}")
            # Continue without training guide if file can't be loaded

        return {"paddle_tips": paddle_tips, "training_guide": training_guide}

    except Exception as e:
        print(f"Error getting mobile improve data: {str(e)}")
        return {"paddle_tips": [], "training_guide": {}, "error": str(e)}


def get_mobile_team_data(user):
    """Get team data for mobile my team page - enhanced with team context support for multi-team users"""
    try:
        # ENHANCED TEAM CONTEXT SUPPORT (same pattern as analyze-me and track-byes-courts)
        # Use priority-based team detection to handle multi-team users properly
        
        user_email = user.get("email")
        player_id = user.get("tenniscores_player_id")
        
        if not player_id:
            return {
                "team_data": None,
                "court_analysis": {},
                "top_players": [],
                "error": "Player ID not found. Please check your profile setup.",
            }

        # PRIORITY-BASED TEAM DETECTION (same as analyze-me page)
        team_id = None
        team_name = None
        league_id_int = None
        
        # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
        session_team_id = user.get("team_id")
        print(f"[DEBUG] My-team: session_team_id from user: {session_team_id}")
        
        if session_team_id:
            try:
                # Get team info for the specific team_id from session
                session_team_query = """
                    SELECT t.id, t.team_name, t.display_name, t.league_id
                    FROM teams t
                    WHERE t.id = %s AND t.is_active = TRUE
                """
                session_team_result = execute_query_one(session_team_query, [session_team_id])
                if session_team_result:
                    team_id = session_team_result['id'] 
                    team_name = session_team_result['team_name']
                    display_name = session_team_result['display_name']
                    league_id_int = session_team_result['league_id']
                    print(f"[DEBUG] My-team: Using team_id from session: team_id={team_id}, team_name={team_name}, display_name={display_name}")
                else:
                    print(f"[DEBUG] My-team: Session team_id {session_team_id} not found in teams table")
            except Exception as e:
                print(f"[DEBUG] My-team: Error getting team from session team_id {session_team_id}: {e}")
        
        # PRIORITY 2: Use team_context from user if provided (from composite player URL)
        if not team_id:
            team_context = user.get("team_context")
            if team_context:
                try:
                    # Get team info for the specific team_id from team context
                    team_context_query = """
                        SELECT t.id, t.team_name, t.display_name, t.league_id
                        FROM teams t
                        WHERE t.id = %s AND t.is_active = TRUE
                    """
                    team_context_result = execute_query_one(team_context_query, [team_context])
                    if team_context_result:
                        team_id = team_context_result['id'] 
                        team_name = team_context_result['team_name']
                        display_name = team_context_result['display_name']
                        league_id_int = team_context_result['league_id']
                        print(f"[DEBUG] My-team: Using team_context from URL: team_id={team_id}, team_name={team_name}")
                    else:
                        print(f"[DEBUG] My-team: team_context {team_context} not found in teams table")
                except Exception as e:
                    print(f"[DEBUG] My-team: Error getting team from team_context {team_context}: {e}")
        
        # PRIORITY 3: Fallback to session service
        if not team_id:
            print(f"[DEBUG] My-team: No direct team_id, using session service fallback")
            from app.services.session_service import get_session_data_for_user
            session_data = get_session_data_for_user(user_email)
            if session_data:
                team_id = session_data.get("team_id")
                if team_id:
                    try:
                        session_team_query = """
                            SELECT t.id, t.team_name, t.display_name, t.league_id
                            FROM teams t
                            WHERE t.id = %s AND t.is_active = TRUE
                        """
                        session_team_result = execute_query_one(session_team_query, [team_id])
                        if session_team_result:
                            team_name = session_team_result['team_name']
                            display_name = session_team_result['display_name']
                            league_id_int = session_team_result['league_id']
                            print(f"[DEBUG] My-team: Session service provided: team_id={team_id}, team_name={team_name}")
                    except Exception as e:
                        print(f"[DEBUG] My-team: Error getting team name from session service team_id: {e}")
        
        # PRIORITY 4: Legacy fallback - find first team for player (last resort)
        if not team_id:
            print(f"[DEBUG] My-team: Using legacy fallback - finding first team for player {player_id}")
            # Try primary query first (when team_id exists)
            team_query = """
                SELECT t.id, t.team_name, t.display_name, p.league_id
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id = %s 
                AND p.is_active = TRUE
                LIMIT 1
            """
            
            team_record = execute_query_one(team_query, [player_id])
            
            # If no team found via team_id, try fallback query using club + series matching
            if not team_record:
                print(f"[DEBUG] My-team: No team found via team_id for player {player_id}, trying fallback...")
                fallback_query = """
                    SELECT t.id, t.team_name, t.display_name, p.league_id
                    FROM players p
                    JOIN clubs c ON p.club_id = c.id
                    JOIN series s ON p.series_id = s.id
                    JOIN teams t ON (t.club_id = c.id AND t.team_alias = s.name)
                    WHERE p.tenniscores_player_id = %s 
                    AND p.is_active = TRUE
                    AND t.is_active = TRUE
                    LIMIT 1
                """
                team_record = execute_query_one(fallback_query, [player_id])
                
                if team_record:
                    print(f"[DEBUG] My-team: Found team via fallback: {team_record['team_name']} (ID: {team_record['id']})")
            
            if team_record:
                team_id = team_record["id"]
                team_name = team_record["team_name"]
                display_name = team_record["display_name"]
                league_id_int = team_record["league_id"]
            else:
                # Get player info for better error message
                player_info_query = """
                    SELECT p.first_name, p.last_name, c.name as club_name, s.name as series_name
                    FROM players p
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id = %s
                """
                player_info = execute_query_one(player_info_query, [player_id])
                
                if player_info:
                    error_msg = f"No active team found for {player_info['first_name']} {player_info['last_name']} ({player_info['club_name']}, {player_info['series_name']}). Please contact support."
                else:
                    error_msg = f"No active team found for player ID {player_id}. Please contact support."
                
                return {
                    "team_data": None,
                    "court_analysis": {},
                    "top_players": [],
                    "error": error_msg,
                }

        print(f"[DEBUG] My-team: Final team selection: team_id={team_id}, team_name={team_name}, display_name={display_name}")
        print(f"[DEBUG] My-team: Using league_id: {league_id_int}")

        # Get team stats from series_stats table first
        team_stats_query = """
            SELECT 
                team,
                points,
                matches_won,
                matches_lost,
                lines_won,
                lines_lost,
                sets_won,
                sets_lost,
                games_won,
                games_lost
            FROM series_stats
            WHERE team = %s AND league_id = %s
        """
        print(f"[DEBUG] My-team: Querying series_stats with team='{team_name}' and league_id={league_id_int}")
        team_stats = execute_query_one(team_stats_query, [team_name, league_id_int])
        print(f"[DEBUG] My-team: Team stats query result: {team_stats}")
        
        # Let's also check what teams exist in series_stats for this league
        check_teams_query = """
            SELECT DISTINCT team, league_id 
            FROM series_stats 
            WHERE league_id = %s
            ORDER BY team
        """
        existing_teams = execute_query(check_teams_query, [league_id_int])
        print(f"[DEBUG] My-team: Teams in series_stats for league {league_id_int}: {[t['team'] for t in existing_teams]}")

        # If no stats found in series_stats, calculate them from match_scores
        if not team_stats:
            print(f"[DEBUG] My-team: No stats found in series_stats for {team_name}, calculating from match_scores...")
            
            # Let's check what teams exist in match_scores for this league
            check_match_teams_query = """
                SELECT DISTINCT home_team, away_team
                FROM match_scores 
                WHERE league_id = %s 
                AND (home_team ILIKE %s OR away_team ILIKE %s)
                LIMIT 10
            """
            similar_match_teams = execute_query(check_match_teams_query, [league_id_int, f"%{team_name.split()[0]}%", f"%{team_name.split()[0]}%"])
            print(f"[DEBUG] My-team: Similar teams in match_scores: {similar_match_teams}")
            
            matches_query = """
                WITH team_matches AS (
                    SELECT 
                        match_date,
                        home_team,
                        away_team,
                        winner,
                        scores,
                        CASE 
                            WHEN home_team = %s THEN 'home'
                            WHEN away_team = %s THEN 'away'
                        END as team_side
                    FROM match_scores
                    WHERE (home_team = %s OR away_team = %s)
                    AND league_id = %s
                )
                SELECT
                    COUNT(*) as total_matches,
                    SUM(CASE 
                        WHEN (team_side = 'home' AND winner = 'home') OR 
                             (team_side = 'away' AND winner = 'away') 
                        THEN 1 ELSE 0 
                    END) as matches_won,
                    SUM(CASE 
                        WHEN (team_side = 'home' AND winner = 'away') OR 
                             (team_side = 'away' AND winner = 'home') 
                        THEN 1 ELSE 0 
                    END) as matches_lost,
                    COUNT(*) as lines_won,  -- Each match is one line
                    0 as lines_lost,        -- We'll calculate this after
                    0 as sets_won,          -- We'll calculate these from scores
                    0 as sets_lost,
                    0 as games_won,
                    0 as games_lost
                FROM team_matches
            """
            
            print(f"[DEBUG] My-team: Running match stats query with team='{team_name}' (4 times) and league_id={league_id_int}")
            match_stats = execute_query_one(matches_query, [team_name, team_name, team_name, team_name, league_id_int])
            print(f"[DEBUG] My-team: Match stats query result: {match_stats}")
            
            if match_stats and match_stats["total_matches"] > 0:
                # Create stats object
                team_stats = {
                    "team": team_name,
                    "points": match_stats["matches_won"] * 2,  # 2 points per win
                    "matches_won": match_stats["matches_won"],
                    "matches_lost": match_stats["matches_lost"],
                    "lines_won": match_stats["matches_won"],
                    "lines_lost": match_stats["matches_lost"],
                    "sets_won": 0,
                    "sets_lost": 0,
                    "games_won": 0,
                    "games_lost": 0
                }
            else:
                # No matches found - return empty stats
                team_stats = {
                    "team": team_name,
                    "points": 0,
                    "matches_won": 0,
                    "matches_lost": 0,
                    "lines_won": 0,
                    "lines_lost": 0,
                    "sets_won": 0,
                    "sets_lost": 0,
                    "games_won": 0,
                    "games_lost": 0
                }

        # Get team matches for match history (FIXED: Added tenniscores_match_id for court analysis)
        matches_query = """
            SELECT 
                TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                home_team as "Home Team",
                away_team as "Away Team",
                winner as "Winner",
                scores as "Scores",
                home_player_1_id as "Home Player 1",
                home_player_2_id as "Home Player 2",
                away_player_1_id as "Away Player 1",
                away_player_2_id as "Away Player 2",
                tenniscores_match_id,
                id
            FROM match_scores
            WHERE (home_team = %s OR away_team = %s)
            AND league_id = %s
            ORDER BY match_date DESC
        """
        team_matches = execute_query(matches_query, [team_name, team_name, league_id_int])
        print(f"[DEBUG] My-team: Found {len(team_matches)} team matches")

        # Calculate team analysis
        team_analysis = calculate_team_analysis_mobile(team_stats, team_matches, team_name, league_id_int, team_id)

        # Get team members/roster with court stats
        from app.routes.mobile_routes import get_team_members_with_court_stats
        team_members = get_team_members_with_court_stats(team_id, user)
        print(f"[DEBUG] My-team: Found {len(team_members)} team members for team_id={team_id}")

        # Transform to match template expectations
        overview = team_analysis.get("overview", {})
        
        # Convert to template format
        team_data_formatted = {
            "matches": {
                "won": overview.get("match_record", "0-0").split("-")[0],
                "lost": overview.get("match_record", "0-0").split("-")[1], 
                "percentage": f"{overview.get('match_win_rate', 0)}%"
            },
            "lines": {
                "percentage": f"{overview.get('line_win_rate', 0)}%"
            },
            "sets": {
                "percentage": f"{overview.get('set_win_rate', 0)}%"
            },
            "games": {
                "percentage": f"{overview.get('game_win_rate', 0)}%"
            },
            "points": overview.get("points", 0),
            "display_name": display_name,
            "team": team_name
        }

        # Convert team members to top_players format for template
        top_players = []
        for member in team_members:
            # Calculate win rate for this player
            player_matches = member.get("match_count", 0)
            player_wins = 0
            player_losses = 0
            
            # Get player's match history to calculate wins/losses
            if player_matches > 0:
                player_id = member.get("tenniscores_player_id")
                player_matches_query = """
                    SELECT 
                        CASE 
                            WHEN (home_player_1_id = %s OR home_player_2_id = %s) AND winner = 'home' THEN 1
                            WHEN (away_player_1_id = %s OR away_player_2_id = %s) AND winner = 'away' THEN 1
                            ELSE 0
                        END as won
                    FROM match_scores
                    WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                    AND league_id = %s
                    AND (home_team = %s OR away_team = %s)
                """
                player_results = execute_query(player_matches_query, [
                    player_id, player_id, player_id, player_id,
                    player_id, player_id, player_id, player_id,
                    league_id_int, team_name, team_name
                ])
                
                for result in player_results:
                    if result["won"] == 1:
                        player_wins += 1
                    else:
                        player_losses += 1
            
            win_rate = round((player_wins / (player_wins + player_losses)) * 100, 1) if (player_wins + player_losses) > 0 else 0
            
            player_data = {
                "name": member.get("name", ""),
                "matches": player_matches,
                "winRate": win_rate,
                "best_partner": "N/A",  # Could be calculated if needed
                "is_substitute": member.get("is_substitute", False)
            }
            top_players.append(player_data)

        # Get last 3 team matches for the template
        last_3_matches_query = """
            SELECT 
                TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                home_team as "Home Team",
                away_team as "Away Team",
                winner as "Winner",
                scores as "Scores",
                home_player_1_id as "Home Player 1",
                home_player_2_id as "Home Player 2",
                away_player_1_id as "Away Player 1",
                away_player_2_id as "Away Player 2"
            FROM match_scores
            WHERE (home_team = %s OR away_team = %s)
            AND league_id = %s
            ORDER BY match_date DESC
            LIMIT 3
        """
        last_3_matches = execute_query(last_3_matches_query, [team_name, team_name, league_id_int])
        
        # Format matches for template
        formatted_matches = []
        for match in last_3_matches:
            is_home = match.get("Home Team") == team_name
            opponent = match.get("Away Team") if is_home else match.get("Home Team")
            winner = match.get("Winner", "")
            winner_is_home = winner and winner.lower() == "home"
            team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)
            
            # Get player names
            home_player_1 = get_player_name_from_id(match.get("Home Player 1", ""))
            home_player_2 = get_player_name_from_id(match.get("Home Player 2", ""))
            away_player_1 = get_player_name_from_id(match.get("Away Player 1", ""))
            away_player_2 = get_player_name_from_id(match.get("Away Player 2", ""))
            
            formatted_match = {
                "date": match.get("Date", ""),
                "opponent": opponent,
                "result": "W" if team_won else "L",
                "scores": match.get("Scores", ""),
                "home_players": f"{home_player_1 or 'Unknown'} & {home_player_2 or 'Unknown'}",
                "away_players": f"{away_player_1 or 'Unknown'} & {away_player_2 or 'Unknown'}"
            }
            formatted_matches.append(formatted_match)
        
        # Return in the expected structure for the route
        return {
            "team_data": team_data_formatted,
            "court_analysis": team_analysis.get("court_analysis", {}),
            "top_players": top_players,
            "team_matches": formatted_matches,
            "strength_of_schedule": {},  # This would come from a separate function if needed
            "error": None,
        }

    except Exception as e:
        print(f"Error getting mobile team data: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "team_data": None,
            "court_analysis": {},
            "top_players": [],
            "error": str(e),
        }


def get_mobile_series_data(user):
    """Get series data for mobile my series page"""
    try:
        # Get basic series info
        user_series = user.get("series")
        user_club = user.get("club")

        # Calculate comprehensive Strength of Schedule data
        sos_data = calculate_strength_of_schedule(user)

        return {
            "user_series": user_series,
            "user_club": user_club,
            "success": True,
            # Historical SoS data
            "sos_value": sos_data.get("sos_value"),
            "sos_rank": sos_data.get("rank"),
            "sos_opponents_count": sos_data.get("opponents_count"),
            "sos_all_teams": sos_data.get("all_teams_sos", []),
            # Remaining SoS data
            "remaining_sos_value": sos_data.get("remaining_sos_value"),
            "remaining_sos_rank": sos_data.get("remaining_rank"),
            "sos_remaining_opponents_count": sos_data.get("remaining_opponents_count"),
            "sos_all_teams_remaining": sos_data.get("all_teams_remaining_sos", []),
            "has_remaining_schedule": sos_data.get("has_remaining_schedule", False),
            # Comparison analysis
            "schedule_comparison": sos_data.get("schedule_comparison", {}),
            # General data
            "sos_total_teams": sos_data.get("total_teams"),
            "sos_user_team_name": sos_data.get("user_team_name"),
            "sos_error": sos_data.get("error"),
        }
    except Exception as e:
        print(f"Error getting mobile series data: {str(e)}")
        return {"error": str(e)}


def get_teams_players_data(user, team_id=None):
    """Get teams and players data for mobile interface - filtered by user's league and optionally by team_id"""
    try:
        # Get user's league for filtering
        user_league_id = user.get("league_id", "")

        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
                    print(
                        f"[DEBUG] Converted league_id '{user_league_id}' to integer: {league_id_int}"
                    )
                else:
                    print(
                        f"[WARNING] League '{user_league_id}' not found in leagues table"
                    )
            except Exception as e:
                print(f"[DEBUG] Could not convert league ID: {e}")
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
            print(f"[DEBUG] League_id already integer: {league_id_int}")

        # Query team stats and matches from database
        # Note: execute_query and execute_query_one are already imported at module level

        # Get all teams in user's league with their IDs - only filter if we have a valid league_id
        if league_id_int:
            teams_query = """
                SELECT DISTINCT t.id as team_id, t.team_name, t.display_name
                FROM teams t
                JOIN series_stats ss ON t.team_name = ss.team
                WHERE ss.league_id = %s AND t.league_id = %s
                ORDER BY t.team_name
            """
            all_teams_data = execute_query(teams_query, [league_id_int, league_id_int])
        else:
            teams_query = """
                SELECT DISTINCT t.id as team_id, t.team_name, t.display_name
                FROM teams t
                JOIN series_stats ss ON t.team_name = ss.team
                ORDER BY t.team_name
            """
            all_teams_data = execute_query(teams_query)

        # Convert to list format for backward compatibility and add team IDs
        all_teams = []
        team_id_to_name = {}
        team_name_to_id = {}
        for team_data in all_teams_data:
            team_name = team_data["team_name"]
            tid = team_data["team_id"]
            display_name = team_data["display_name"] or team_name
            
            all_teams.append(team_name)
            team_id_to_name[tid] = team_name
            team_name_to_id[team_name] = tid

        print(f"[DEBUG] Found {len(all_teams)} teams in league {league_id_int}")
        print(f"[DEBUG] Sample teams_data: {all_teams_data[:3] if all_teams_data else 'None'}")

        # If team_id is provided, validate it and get team name
        selected_team = None
        if team_id and team_id in team_id_to_name:
            selected_team = team_id_to_name[team_id]
            print(f"[DEBUG] Selected team_id {team_id} -> team_name '{selected_team}'")
        elif team_id:
            print(f"[WARNING] Invalid team_id {team_id} - not found in user's league")
            return {
                "team_analysis_data": None,
                "all_teams": all_teams,
                "selected_team": None,
                "error": f"Team ID {team_id} not found"
            }

        if not selected_team:
            # No team selected or invalid team
            print(f"[DEBUG] No team selected, returning teams data with {len(all_teams_data)} teams")
            return {
                "team_analysis_data": None,
                "all_teams": all_teams,
                "all_teams_data": all_teams_data,  # Include team IDs for frontend
                "selected_team": None,
                "selected_team_id": None,
            }

        # Get team stats using team_id for accuracy
        if league_id_int:
            team_stats_query = """
                SELECT ss.*
                FROM series_stats ss
                JOIN teams t ON ss.team = t.team_name
                WHERE t.id = %s AND ss.league_id = %s
            """
            team_stats = execute_query_one(team_stats_query, [team_id, league_id_int])
        else:
            team_stats_query = """
                SELECT ss.*
                FROM series_stats ss
                JOIN teams t ON ss.team = t.team_name
                WHERE t.id = %s
            """
            team_stats = execute_query_one(team_stats_query, [team_id])

        # Get team matches using team_id for accuracy
        if league_id_int:
            matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_team_id = %s OR away_team_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC
            """
            team_matches = execute_query(matches_query, [team_id, team_id, league_id_int])
        else:
            matches_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                    home_team as "Home Team",
                    away_team as "Away Team",
                    winner as "Winner",
                    scores as "Scores",
                    home_player_1_id as "Home Player 1",
                    home_player_2_id as "Home Player 2",
                    away_player_1_id as "Away Player 1",
                    away_player_2_id as "Away Player 2"
                FROM match_scores
                WHERE (home_team_id = %s OR away_team_id = %s)
                ORDER BY match_date DESC
            """
            team_matches = execute_query(matches_query, [team_id, team_id])

        print(f"[DEBUG] Found {len(team_matches)} matches for team_id {team_id}")

        # Calculate team analysis
        team_analysis_data = calculate_team_analysis_mobile(
            team_stats, team_matches, selected_team, league_id_int, team_id
        )

        return {
            "team_analysis_data": team_analysis_data,
            "all_teams": all_teams,
            "all_teams_data": all_teams_data,  # Include team IDs for frontend
            "selected_team": selected_team,
            "selected_team_id": team_id,
        }

    except Exception as e:
        print(f"Error getting teams players data: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "team_analysis_data": None,
            "all_teams": [],
            "all_teams_data": [],
            "selected_team": None,
            "selected_team_id": None,
            "error": str(e),
        }


def transform_team_stats_to_overview_mobile(stats):
    """Transform team stats to overview format for mobile use"""
    if not stats:
        return {
            "points": 0,
            "match_win_rate": 0.0,
            "match_record": "0-0",
            "line_win_rate": 0.0,
            "set_win_rate": 0.0,
            "game_win_rate": 0.0,
        }

    # Handle case where stats is a list (from database query)
    if isinstance(stats, list) and len(stats) > 0:
        stats = stats[0]  # Take the first item from the list

    # Handle both nested structure (legacy) and flat structure (database)
    if "matches" in stats and isinstance(stats["matches"], dict):
        # Legacy nested structure
        matches = stats.get("matches", {})
        lines = stats.get("lines", {})
        sets = stats.get("sets", {})
        games = stats.get("games", {})
        points = stats.get("points", 0)

        overview = {
            "points": points,
            "match_win_rate": float(matches.get("percentage", "0").replace("%", "")),
            "match_record": f"{matches.get('won', 0)}-{matches.get('lost', 0)}",
            "line_win_rate": float(lines.get("percentage", "0").replace("%", "")),
            "set_win_rate": float(sets.get("percentage", "0").replace("%", "")),
            "game_win_rate": float(games.get("percentage", "0").replace("%", "")),
        }
    else:
        # Flat database structure
        points = stats.get("points", 0)

        # Match stats
        matches_won = stats.get("matches_won", 0)
        matches_lost = stats.get("matches_lost", 0)
        matches_total = matches_won + matches_lost
        match_win_rate = (
            round((matches_won / matches_total) * 100, 1) if matches_total > 0 else 0.0
        )

        # Line stats
        lines_won = stats.get("lines_won", 0)
        lines_lost = stats.get("lines_lost", 0)
        lines_total = lines_won + lines_lost
        line_win_rate = (
            round((lines_won / lines_total) * 100, 1) if lines_total > 0 else 0.0
        )

        # Set stats
        sets_won = stats.get("sets_won", 0)
        sets_lost = stats.get("sets_lost", 0)
        sets_total = sets_won + sets_lost
        set_win_rate = (
            round((sets_won / sets_total) * 100, 1) if sets_total > 0 else 0.0
        )

        # Game stats
        games_won = stats.get("games_won", 0)
        games_lost = stats.get("games_lost", 0)
        games_total = games_won + games_lost
        game_win_rate = (
            round((games_won / games_total) * 100, 1) if games_total > 0 else 0.0
        )

        overview = {
            "points": points,
            "match_win_rate": match_win_rate,
            "match_record": f"{matches_won}-{matches_lost}",
            "line_win_rate": line_win_rate,
            "set_win_rate": set_win_rate,
            "game_win_rate": game_win_rate,
        }

    return overview


def calculate_team_analysis_mobile(team_stats, team_matches, team, league_id_int, team_id=None):
    """Calculate comprehensive team analysis for mobile interface"""
    try:
        # Use the same transformation as desktop for correct stats
        overview = transform_team_stats_to_overview_mobile(team_stats)

        # Match Patterns
        total_matches = len(team_matches)
        straight_set_wins = 0
        comeback_wins = 0
        three_set_wins = 0
        three_set_losses = 0

        for match in team_matches:
            is_home = match.get("Home Team") == team
            winner = match.get("Winner", "")
            winner_is_home = winner and winner.lower() == "home"
            team_won = (is_home and winner_is_home) or (
                not is_home and not winner_is_home
            )

            # Get the scores
            scores_str = match.get("Scores", "")
            if scores_str is None:
                scores = []
            else:
                scores = scores_str.split(", ")
            if len(scores) == 2 and team_won:
                straight_set_wins += 1
            if len(scores) == 3:
                if team_won:
                    three_set_wins += 1
                    # Check for comeback win - lost first set but won the match
                    if scores[0]:
                        first_set = scores[0].split("-")
                        if len(first_set) == 2:
                            try:
                                home_score, away_score = map(int, first_set)
                                if is_home and home_score < away_score:
                                    comeback_wins += 1
                                elif not is_home and away_score < home_score:
                                    comeback_wins += 1
                            except ValueError:
                                pass  # Skip if scores can't be parsed
                else:
                    three_set_losses += 1

        three_set_record = f"{three_set_wins}-{three_set_losses}"
        match_patterns = {
            "total_matches": total_matches,
            "set_win_rate": overview["set_win_rate"],
            "three_set_record": three_set_record,
            "straight_set_wins": straight_set_wins,
            "comeback_wins": comeback_wins,
        }

        # Court Analysis - Use correct assignment logic (like analyze-me page)
        from collections import defaultdict
        from datetime import datetime

        def parse_date(date_str):
            if not date_str:
                return datetime.min
            # Handle the specific format from our database
            for fmt in ("%d-%b-%y", "%d-%B-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(str(date_str), fmt)
                except ValueError:
                    continue
            return datetime.min

        # Get team match dates
        team_dates = []
        for match in team_matches:
            date_str = match.get("Date", "")
            parsed_date = parse_date(date_str)
            if parsed_date != datetime.min:
                team_dates.append(parsed_date.date())

        court_analysis = {}
        if team_matches:
            # Get all matches for the team with tenniscores_match_id to determine court assignments
            # Use team_id filtering to get all matches for the team (same as API)
            all_matches_query = """
                SELECT 
                    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                    ms.match_date,
                    ms.id,
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.winner as "Winner",
                    ms.home_player_1_id as "Home Player 1",
                    ms.home_player_2_id as "Home Player 2",
                    ms.away_player_1_id as "Away Player 1",
                    ms.away_player_2_id as "Away Player 2",
                    ms.tenniscores_match_id
                FROM match_scores ms
                WHERE (ms.home_team_id = %s OR ms.away_team_id = %s)
                AND ms.league_id = %s
                AND ms.match_date >= %s AND ms.match_date <= %s
                ORDER BY ms.match_date ASC, ms.id ASC
            """
            
            # Calculate current season boundaries (same as API)
            season_start = datetime(2024, 8, 1)  # August 1st, 2024
            season_end = datetime(2026, 7, 31)   # July 31st, 2026
            
            all_matches = execute_query(all_matches_query, [team_id, team_id, league_id_int, season_start, season_end])
            
            # Find maximum court number from tenniscores_match_id suffixes
            max_court = 0
            for match in all_matches:
                match_id = match.get("tenniscores_match_id", "")
                if "_Line" in match_id:
                    try:
                        court_num = int(match_id.split("_Line")[1])
                        max_court = max(max_court, court_num)
                    except (ValueError, IndexError):
                        continue
            
            # Use the maximum court number found, but cap at 6 for safety
            max_court = min(max_court, 6)
            
            for i in range(1, max_court + 1):
                court_name = f"court{i}"  # Template expects "court1", "court2", etc.
                court_matches = []

                # Find matches for this court using tenniscores_match_id
                for match in all_matches:
                    match_id = match.get("tenniscores_match_id", "")
                    if "_Line" in match_id:
                        try:
                            court_num = int(match_id.split("_Line")[1])
                            if court_num == i:  # This match belongs to court i
                                court_matches.append(match)
                        except (ValueError, IndexError):
                            continue
                


                wins = losses = 0
                player_win_counts = {}

                for match in court_matches:
                    is_home = match.get("Home Team") == team
                    winner = match.get("Winner", "")
                    winner_is_home = winner and winner.lower() == "home"
                    
                    # Check if this league has reversed team assignments
                    from utils.league_utils import has_reversed_team_assignments
                    # Get league name from database using league_id_int
                    league_name_query = "SELECT league_id FROM leagues WHERE id = %s"
                    league_record = execute_query_one(league_name_query, [league_id_int])
                    league_id_str = league_record.get("league_id") if league_record else None
                    has_reversed = has_reversed_team_assignments(league_id_str) if league_id_str else False
                    
                    if has_reversed:
                        # For leagues with reversed team assignments (like NSTF): reverse the win logic
                        team_won = (is_home and not winner_is_home) or (not is_home and winner_is_home)
                    else:
                        # Standard logic for other leagues (APTA, etc.)
                        team_won = (is_home and winner_is_home) or (not is_home and not winner_is_home)

                    if team_won:
                        wins += 1
                    else:
                        losses += 1

                    # Check if this league has reversed team assignments for player assignments
                    if has_reversed:
                        # For leagues with reversed team assignments (like NSTF): home players are from opposing team
                        players = (
                            [match.get("Away Player 1"), match.get("Away Player 2")]
                            if is_home
                            else [match.get("Home Player 1"), match.get("Home Player 2")]
                        )
                    else:
                        # Standard logic for other leagues (APTA, etc.)
                        players = (
                            [match.get("Home Player 1"), match.get("Home Player 2")]
                            if is_home
                            else [match.get("Away Player 1"), match.get("Away Player 2")]
                        )
                    
                    # Get the team ID for this match to check for substitutes
                    match_team_id = match.get("Home Team") if is_home else match.get("Away Team")
                    
                    for p in players:
                        if not p:
                            continue
                        
                        if p not in player_win_counts:
                            player_win_counts[p] = {"matches": 0, "wins": 0, "is_substitute": False}
                        
                        # Check if this player is a substitute
                        if not player_win_counts[p].get("is_substitute_checked"):
                            is_sub = is_substitute_player(p, match_team_id, user_team_id=team_id)
                            player_win_counts[p]["is_substitute"] = is_sub
                            player_win_counts[p]["is_substitute_checked"] = True
                        
                        player_win_counts[p]["matches"] += 1
                        if team_won:
                            player_win_counts[p]["wins"] += 1

                win_rate = (
                    round((wins / (wins + losses) * 100), 1)
                    if (wins + losses) > 0
                    else 0
                )
                record = f"{wins}-{losses} ({win_rate}%)"

                # All players who played on this court (no limit)
                key_players = sorted(
                    [
                        {
                            "name": get_player_name_from_id(p),
                            "winRate": round((d["wins"] / d["matches"]) * 100, 1),  # Template expects camelCase
                            "matches": d["matches"],
                            "wins": d["wins"],  # Template expects wins
                            "losses": d["matches"] - d["wins"],  # Template expects losses
                            "isSubstitute": d.get("is_substitute", False),  # Add substitute indicator
                        }
                        for p, d in player_win_counts.items()
                        if get_player_name_from_id(p) is not None  # Only include players with valid names
                    ],
                    key=lambda x: (-x["winRate"], -x["matches"]),  # Sort by win rate first, then by matches played
                )

                # Summary sentence
                if win_rate >= 60:
                    perf = "strong performance"
                elif win_rate >= 45:
                    perf = "solid performance"
                else:
                    perf = "average performance"

                if key_players:
                    contributors = " and ".join(
                        [
                            f"{kp['name']} ({kp['winRate']}% in {kp['matches']} matches)"
                            for kp in key_players
                        ]
                    )
                    summary = f"This court has shown {perf} with a {win_rate}% win rate. Key contributors: {contributors}."
                else:
                    summary = (
                        f"This court has shown {perf} with a {win_rate}% win rate."
                    )

                court_analysis[court_name] = {
                    "matches": wins + losses,  # Add total matches count
                    "wins": wins,  # Add wins count
                    "losses": losses,  # Add losses count
                    "record": record,
                    "winRate": win_rate,  # Template expects camelCase
                    "key_players": key_players,  # Add key_players for compatibility
                    "topPartners": key_players,  # Template expects topPartners (same data)
                    "summary": summary,
                }
                


        # Top Players Table
        player_stats = defaultdict(
            lambda: {"matches": 0, "wins": 0, "courts": {}, "partners": {}}
        )

        if team_matches:
            # Get all matches with tenniscores_match_id for court assignment
            all_matches_with_id = execute_query(
                """
                SELECT 
                    TO_CHAR(ms.match_date, 'DD-Mon-YY') as "Date",
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.winner as "Winner",
                    ms.home_player_1_id as "Home Player 1",
                    ms.home_player_2_id as "Home Player 2",
                    ms.away_player_1_id as "Away Player 1",
                    ms.away_player_2_id as "Away Player 2",
                    ms.tenniscores_match_id
                FROM match_scores ms
                WHERE (ms.home_team = %s OR ms.away_team = %s)
                AND ms.league_id = %s
                ORDER BY ms.match_date ASC, ms.id ASC
            """,
                [team, team, league_id_int],
            )

            for match in all_matches_with_id:
                is_home = match.get("Home Team") == team
                player1 = (
                    match.get("Home Player 1")
                    if is_home
                    else match.get("Away Player 1")
                )
                player2 = (
                    match.get("Home Player 2")
                    if is_home
                    else match.get("Away Player 2")
                )
                winner = match.get("Winner", "")
                winner_is_home = winner and winner.lower() == "home"
                team_won = (is_home and winner_is_home) or (
                    not is_home and not winner_is_home
                )

                # Determine court assignment from tenniscores_match_id
                match_id = match.get("tenniscores_match_id", "")
                court_num = None
                if match_id and "_Line" in match_id:
                    try:
                        court_num = int(match_id.split("_Line")[1])
                    except (ValueError, IndexError):
                        pass

                # If no court from tenniscores_match_id, use same fallback logic as API
                if court_num is None:
                    # Use database ID order within team matchup (same as individual player analysis)
                    match_date = match.get("Date")
                    home_team = match.get("Home Team", "")
                    away_team = match.get("Away Team", "")
                    
                    # Find all matches on this date with these teams
                    same_matchup_query = """
                        SELECT id, tenniscores_match_id
                        FROM match_scores
                        WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                        AND home_team = %s AND away_team = %s
                        ORDER BY id ASC
                    """
                    
                    try:
                        same_matchup_matches = execute_query(same_matchup_query, [match_date, home_team, away_team])
                        
                        # Find position of current match in this group
                        current_match_id = match.get("id")
                        match_position = 0
                        for i, matchup_match in enumerate(same_matchup_matches):
                            if matchup_match.get("id") == current_match_id:
                                match_position = i
                                break
                        
                        # Assign court based on position (1-4, same as API and individual analysis)
                        court_num = (match_position % 4) + 1
                        
                    except Exception as e:
                        court_num = 1  # Ultimate fallback

                # Skip matches where we still can't determine court (should be rare now)
                if court_num is None:
                    continue

                for player in [player1, player2]:
                    if not player:
                        continue
                    if player not in player_stats:
                        player_stats[player] = {
                            "matches": 0,
                            "wins": 0,
                            "courts": {},
                            "partners": {},
                        }

                    player_stats[player]["matches"] += 1
                    if team_won:
                        player_stats[player]["wins"] += 1

                    # Court - Use correct court assignment
                    court = f"Court {court_num}"  # Keep readable format for best_court field
                    if court not in player_stats[player]["courts"]:
                        player_stats[player]["courts"][court] = {
                            "matches": 0,
                            "wins": 0,
                        }
                    player_stats[player]["courts"][court]["matches"] += 1
                    if team_won:
                        player_stats[player]["courts"][court]["wins"] += 1

                    # Partner
                    partner = player2 if player == player1 else player1
                    if partner:
                        if partner not in player_stats[player]["partners"]:
                            player_stats[player]["partners"][partner] = {
                                "matches": 0,
                                "wins": 0,
                            }
                        player_stats[player]["partners"][partner]["matches"] += 1
                        if team_won:
                            player_stats[player]["partners"][partner]["wins"] += 1

        # Build top_players list from player_stats
        top_players = []
        for player_id, stats in player_stats.items():
            # Convert player ID to name
            player_name = get_player_name_from_id(player_id)

            # Calculate win rate
            win_rate = (
                round((stats["wins"] / stats["matches"]) * 100, 1)
                if stats["matches"] > 0
                else 0
            )

            # Best court - Fixed logic: >3 matches (>=4) AND >=70% win rate
            best_court = None
            best_court_rate = 0
            for court, cstats in stats["courts"].items():
                if cstats["matches"] > 3:  # More than 3 matches (>=4)
                    rate = (
                        round((cstats["wins"] / cstats["matches"]) * 100, 1)
                        if cstats["matches"] > 0
                        else 0
                    )
                    if rate >= 70.0:  # Must have 70% or greater win rate
                        if rate > best_court_rate or (
                            rate == best_court_rate and cstats["matches"] > 0
                        ):
                            best_court_rate = rate
                            best_court = court

            # Best partner
            best_partner = None
            best_partner_rate = 0
            print(
                f"[DEBUG PARTNER2] Player {player_name} has {len(stats['partners'])} partners:"
            )
            for partner_id, pstats in stats["partners"].items():
                partner_name_debug = get_player_name_from_id(partner_id)
                print(
                    f"  - {partner_name_debug} (ID: {partner_id}): {pstats['matches']} matches, {pstats['wins']} wins"
                )
                if (
                    pstats["matches"] >= 2
                ):  # Require at least 2 matches for meaningful partnership
                    rate = (
                        round((pstats["wins"] / pstats["matches"]) * 100, 1)
                        if pstats["matches"] > 0
                        else 0
                    )
                    print(f"    -> Qualified: {rate}% win rate")
                    if rate >= 60.0:  # Must have 60% or greater win rate for best partner
                        if rate > best_partner_rate or (
                            rate == best_partner_rate and pstats["matches"] > 0
                        ):
                            best_partner_rate = rate
                            best_partner = get_player_name_from_id(partner_id)
                            print(f"    -> NEW BEST: {best_partner} with {rate}%")
                    else:
                        print(f"    -> Win rate too low ({rate}% < 60%)")
                else:
                    print(f"    -> Not enough matches ({pstats['matches']} < 2)")
            print(f"  Final best partner: {best_partner} ({best_partner_rate}%)")

            # Get PTI data for this player
            player_pti = None
            if player_id:
                try:
                    # Query PTI from players table
                    pti_query = """
                        SELECT p.pti 
                        FROM players p 
                        WHERE p.tenniscores_player_id = %s 
                        AND p.league_id = %s 
                        AND p.is_active = true
                        ORDER BY p.id DESC 
                        LIMIT 1
                    """
                    pti_result = execute_query_one(pti_query, [player_id, league_id_int])
                    if pti_result and pti_result["pti"] is not None:
                        player_pti = float(pti_result["pti"])
                except Exception as e:
                    print(f"[DEBUG] Error getting PTI for player {player_id}: {e}")
                    player_pti = None

            top_players.append(
                {
                    "name": player_name,
                    "matches": stats["matches"],
                    "winRate": win_rate,  # Changed to camelCase for consistency
                    "best_court": best_court or "Threshold not met",
                    "best_partner": best_partner if best_partner else "Threshold not met",
                    "pti": player_pti,  # Add PTI data for template
                }
            )

        # Sort players by matches played (descending)
        top_players = sorted(top_players, key=lambda x: -x["matches"])

        # Narrative summary
        summary = (
            f"{team} has accumulated {overview['points']} points this season with a "
            f"{overview['match_win_rate']}% match win rate. The team shows "
            f"strong resilience with {match_patterns['comeback_wins']} comeback victories "
            f"and has won {match_patterns['straight_set_wins']} matches in straight sets.\n"
            f"Their performance metrics show a {overview['game_win_rate']}% game win rate and "
            f"{overview['set_win_rate']}% set win rate, with particularly "
            f"{'strong' if overview['line_win_rate'] >= 50 else 'consistent'} line play at "
            f"{overview['line_win_rate']}%.\n"
            f"In three-set matches, the team has a record of {match_patterns['three_set_record']}, "
            f"demonstrating their {'strength' if three_set_wins > three_set_losses else 'areas for improvement'} in extended matches."
        )

        return {
            "overview": overview,
            "match_patterns": match_patterns,
            "court_analysis": court_analysis,
            "top_players": top_players,
            "summary": summary,
        }

    except Exception as e:
        print(f"Error calculating team analysis: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "overview": {},
            "match_patterns": {},
            "court_analysis": {},
            "top_players": [],
            "summary": f"Error calculating team analysis: {str(e)}",
        }


def get_player_search_data(user):
    """Get player search data for mobile interface using dynamic stats calculation"""
    try:
        from flask import request

        # Get search parameters from request
        first_name = request.args.get("first_name", "").strip()
        last_name = request.args.get("last_name", "").strip()

        search_attempted = bool(first_name or last_name)
        matching_players = []
        search_query = None

        if search_attempted:
            # Build search query description
            if first_name and last_name:
                search_query = f'"{first_name} {last_name}"'
            elif first_name:
                search_query = f'first name "{first_name}"'
            elif last_name:
                search_query = f'last name "{last_name}"'

            # Get user's leagues for filtering - handle users with multiple league associations
            user_league_id = user.get("league_id", "")
            print(f"[DEBUG] get_player_search_data: User league_id: '{user_league_id}'")

            # Convert string league_id to integer foreign key for database queries
            league_id_int = None
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

            # Search for players in database
            search_conditions = []
            search_params = []

            if first_name:
                search_conditions.append("LOWER(p.first_name) LIKE LOWER(%s)")
                search_params.append(f"%{first_name}%")

            if last_name:
                search_conditions.append("LOWER(p.last_name) LIKE LOWER(%s)")
                search_params.append(f"%{last_name}%")

            # Base query to find matching players with team information
            # This creates separate entries for players on multiple teams
            base_query = """
                SELECT 
                    p.first_name,
                    p.last_name,
                    p.tenniscores_player_id,
                    p.pti,
                    p.league_id,
                    c.name as club_name,
                    s.name as series_name,
                    l.league_id as league_code,
                    t.id as team_id,
                    t.team_alias
                FROM players p
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id IS NOT NULL
                AND p.is_active = true
            """

            if search_conditions:
                base_query += " AND " + " AND ".join(search_conditions)

            # Add league filtering if available
            if league_id_int:
                base_query += " AND p.league_id = %s"
                search_params.append(league_id_int)

            base_query += " ORDER BY p.first_name, p.last_name, t.team_name"

            candidate_players = execute_query(base_query, search_params)
            print(
                f"[DEBUG] Found {len(candidate_players)} candidate players from database"
            )

            # Calculate current season dates (Aug 1 - July 31)
            from datetime import date, datetime

            current_date = datetime.now()
            # Use same season definition as player detail page for consistency
            from datetime import datetime
            
            # Dynamic season logic: Use the most recent season with data
            # For now, include both 2024-2025 and 2025-2026 seasons to catch all recent matches
            # This ensures we don't miss matches from the current/upcoming season
            season_start = datetime(2024, 8, 1)  # August 1st, 2024
            season_end = datetime(2026, 7, 31)   # July 31st, 2026 (extended to catch 2025-2026 season)
            
            season_start_date = season_start.date()
            season_end_date = season_end.date()
            
            print(f"[DEBUG] Player search using same season as player detail: {season_start_date} to {season_end_date}")

            # Load all matches for this league in one query for efficient team-specific calculation
            print("Loading match data for team-specific record calculation...")
            if league_id_int:
                matches_query = """
                    SELECT 
                        ms.home_player_1_id, ms.home_player_2_id, 
                        ms.away_player_1_id, ms.away_player_2_id,
                        ms.home_team_id, ms.away_team_id, ms.winner,
                        ms.match_date
                    FROM match_scores ms 
                    WHERE ms.league_id = %s 
                    AND ms.winner IS NOT NULL
                    AND ms.match_date >= %s
                    AND ms.match_date <= %s
                """
                all_matches = execute_query(matches_query, [league_id_int, season_start_date, season_end_date])
            else:
                matches_query = """
                    SELECT 
                        ms.home_player_1_id, ms.home_player_2_id, 
                        ms.away_player_1_id, ms.away_player_2_id,
                        ms.home_team_id, ms.away_team_id, ms.winner,
                        ms.match_date
                    FROM match_scores ms 
                    WHERE ms.winner IS NOT NULL
                    AND ms.match_date >= %s
                    AND ms.match_date <= %s
                """
                all_matches = execute_query(matches_query, [season_start_date, season_end_date])
            
            print(f"Loaded {len(all_matches)} matches for team-specific record calculation")
            
            # Build player-team records
            player_team_records = {}  # Key: (player_id, team_id), Value: {wins: X, losses: Y}
            
            for match in all_matches:
                home_players = [match["home_player_1_id"], match["home_player_2_id"]]
                away_players = [match["away_player_1_id"], match["away_player_2_id"]]
                home_team_id = match["home_team_id"]
                away_team_id = match["away_team_id"]
                winner = match["winner"]
                
                # Process home team players
                for player_id in home_players:
                    if player_id:
                        key = (player_id, home_team_id)
                        if key not in player_team_records:
                            player_team_records[key] = {"wins": 0, "losses": 0}
                        
                        if winner == "home":
                            player_team_records[key]["wins"] += 1
                        elif winner == "away":
                            player_team_records[key]["losses"] += 1
                
                # Process away team players
                for player_id in away_players:
                    if player_id:
                        key = (player_id, away_team_id)
                        if key not in player_team_records:
                            player_team_records[key] = {"wins": 0, "losses": 0}
                        
                        if winner == "away":
                            player_team_records[key]["wins"] += 1
                        elif winner == "home":
                            player_team_records[key]["losses"] += 1

            # For each candidate player-team combination, get their team-specific stats
            for player in candidate_players:
                player_id = player["tenniscores_player_id"]
                team_id = player["team_id"]
                player_name = f"{player['first_name']} {player['last_name']}"

                # Get team-specific wins and losses
                if player_id and team_id:
                    key = (player_id, team_id)
                    record = player_team_records.get(key, {"wins": 0, "losses": 0})
                    wins = record["wins"]
                    losses = record["losses"]
                else:
                    wins = 0
                    losses = 0

                total_matches = wins + losses

                # Format PTI for display
                pti_value = player["pti"]
                if pti_value and pti_value != "N/A":
                    try:
                        float(pti_value)
                        current_pti_display = str(pti_value)
                    except (ValueError, TypeError):
                        current_pti_display = "N/A"
                else:
                    current_pti_display = "N/A"

                # Get club and series info
                club = player["club_name"] or "Unknown"
                series = player["series_name"] or "Unknown"

                matching_players.append(
                    {
                        "name": player_name,
                        "first_name": player["first_name"],
                        "last_name": player["last_name"],
                        "player_id": player_id,
                        "team_id": team_id,
                        "current_pti": current_pti_display,
                        "total_matches": total_matches,
                        "wins": wins,
                        "losses": losses,
                        "club": club,
                        "series": series,
                        "team_alias": player.get("team_alias", ""),
                    }
                )

                print(
                    f"[DEBUG] {player_name} ({player.get('team_alias', 'No team')}): {total_matches} matches ({wins}-{losses}) in current season"
                )

            # Sort by name for consistent results
            matching_players.sort(key=lambda x: x["name"].lower())

            print(
                f"[DEBUG] Found {len(matching_players)} players matching search criteria with calculated stats"
            )

        return {
            "first_name": first_name,
            "last_name": last_name,
            "search_attempted": search_attempted,
            "search_query": search_query,
            "matching_players": matching_players,
        }

    except Exception as e:
        print(f"Error getting player search data: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "first_name": "",
            "last_name": "",
            "search_attempted": False,
            "search_query": None,
            "matching_players": [],
            "error": str(e),
        }


def get_player_name_from_id(player_id):
    """Get player's first and last name from their TennisScores player ID"""
    if not player_id or not player_id.strip():
        return "Unknown Player"

    try:
        player = execute_query_one(
            "SELECT first_name, last_name FROM players WHERE tenniscores_player_id = %s",
            [player_id],
        )
        if player:
            return f"{player['first_name']} {player['last_name']}"
        else:
            # Fallback: show truncated ID if no name found
            return f"Player ({player_id[:8]}...)"
    except Exception as e:
        print(f"Error looking up player name for ID {player_id}: {e}")
        return "Unknown Player"


def calculate_strength_of_schedule(user):
    """
    Calculate comprehensive Strength of Schedule (SoS) analysis for the user's team.

    This function provides:
    1. Historical SoS - opponents already played
    2. Remaining SoS - opponents yet to be played  
    3. Comparison analysis - easier/harder remaining schedule

    Args:
        user: User object containing player info and team membership

    Returns:
        dict: {
            'sos_value': float,           # Historical SoS (rounded to 2 decimal places)
            'remaining_sos_value': float, # Remaining SoS (rounded to 2 decimal places)
            'rank': int,                  # Team's historical SoS rank (1 = toughest schedule)
            'remaining_rank': int,        # Team's remaining SoS rank
            'total_teams': int,           # Total teams in series
            'opponents_count': int,       # Number of unique opponents faced
            'remaining_opponents_count': int, # Number of unique remaining opponents
            'schedule_comparison': dict,  # Analysis of remaining vs historical
            'all_teams_sos': list,       # All teams' historical SoS rankings
            'all_teams_remaining_sos': list, # All teams' remaining SoS rankings
            'user_team_name': str,       # User's team name
            'error': str or None
        }
    """
    try:
        # Get user's team information
        club = user.get("club")
        series = user.get("series")
        league_id = user.get("league_id", "")

        if not club or not series:
            return {
                "sos_value": 0.0,
                "remaining_sos_value": "N/A",
                "remaining_sos_actual": None,
                "rank": 0,
                "remaining_rank": None,
                "total_teams": 0,
                "opponents_count": 0,
                "remaining_opponents_count": 0,
                "has_remaining_schedule": False,
                "schedule_comparison": {},
                "all_teams_sos": [],
                "all_teams_remaining_sos": [],
                "user_team_name": "",
                "error": "User club or series not found",
            }

        # Convert league_id to integer foreign key for database queries
        league_id_int = None
        if isinstance(league_id, str) and league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
            except Exception as e:
                print(
                    f"[DEBUG] calculate_strength_of_schedule: Could not convert league ID: {e}"
                )
        elif isinstance(league_id, int):
            league_id_int = league_id

        # Determine team name using same logic as get_mobile_team_data
        if league_id == "NSTF":
            import re

            series_match = re.search(r"Series\s+(.+)", series)
            if series_match:
                series_suffix = series_match.group(1)
                team = f"{club} S{series_suffix}"
            else:
                series_suffix = series.replace("Series", "").strip()
                team = f"{club} S{series_suffix}" if series_suffix else f"{club} S1"
        elif league_id == "CNSWPL":
            # CNSWPL uses format "Club Number" (no hyphen), e.g. "Tennaqua 12"
            import re
            m = re.search(r"(\d+[a-z]*)", series)  # Handle both "12" and "12a" formats
            series_num = m.group(1) if m else ""
            team = f"{club} {series_num}"
        else:
            # APTA and other leagues use "Club - Number" format
            import re

            m = re.search(r"(\d+)", series)
            series_num = m.group(1) if m else ""
            team = f"{club} - {series_num}"

        print(
            f"[DEBUG] calculate_strength_of_schedule: Calculating comprehensive SoS for team '{team}'"
        )

        # ===== STEP 1: HISTORICAL SOS (Completed Matches) =====
        if league_id_int:
            historical_matches_query = """
                SELECT 
                    home_team,
                    away_team,
                    winner,
                    match_date
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                AND winner IS NOT NULL
                AND winner != ''
                AND match_date <= CURRENT_DATE
                ORDER BY match_date
            """
            historical_matches = execute_query(historical_matches_query, [team, team, league_id_int])
        else:
            historical_matches_query = """
                SELECT 
                    home_team,
                    away_team,
                    winner,
                    match_date
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND winner IS NOT NULL
                AND winner != ''
                AND match_date <= CURRENT_DATE
                ORDER BY match_date
            """
            historical_matches = execute_query(historical_matches_query, [team, team])

        # Extract historical opponents
        historical_opponents = set()
        for match in historical_matches:
            home_team = match["home_team"]
            away_team = match["away_team"]
            if home_team == team:
                historical_opponents.add(away_team)
            else:
                historical_opponents.add(home_team)

        print(f"[DEBUG] Found {len(historical_opponents)} historical opponents: {list(historical_opponents)}")

        # Calculate historical SOS
        historical_sos_value = 0.0
        if historical_opponents:
            historical_opponent_avg_points = []
            for opponent in historical_opponents:
                opponent_stats = _get_opponent_stats(opponent, league_id_int)
                if opponent_stats:
                    historical_opponent_avg_points.append(opponent_stats)
            
            if historical_opponent_avg_points:
                historical_sos_value = round(sum(historical_opponent_avg_points) / len(historical_opponent_avg_points), 2)

        # ===== STEP 2: REMAINING SOS (Future/Actual Matches) =====
        # Check for actual future matches first
        remaining_matches = _get_actual_future_matches(team, league_id_int)
        
        # If no actual future matches exist, don't simulate - return empty
        if not remaining_matches:
            print(f"[DEBUG] No actual future matches found for {team}. Remaining SOS analysis not available.")
        
        # Extract remaining opponents
        remaining_opponents = set()
        for match in remaining_matches:
            home_team = match["home_team"]
            away_team = match["away_team"]
            if home_team == team:
                remaining_opponents.add(away_team)  
            else:
                remaining_opponents.add(home_team)

        print(f"[DEBUG] Found {len(remaining_opponents)} remaining opponents: {list(remaining_opponents)}")

        # Calculate remaining SOS only if actual future matches exist
        remaining_sos_value = None
        if remaining_opponents:
            remaining_opponent_avg_points = []
            for opponent in remaining_opponents:
                opponent_stats = _get_opponent_stats(opponent, league_id_int)
                if opponent_stats:
                    remaining_opponent_avg_points.append(opponent_stats)
            
            if remaining_opponent_avg_points:
                remaining_sos_value = round(sum(remaining_opponent_avg_points) / len(remaining_opponent_avg_points), 2)
        
        # Set display values based on whether remaining schedule exists
        remaining_sos_display = remaining_sos_value if remaining_sos_value is not None else "N/A"
        has_remaining_schedule = remaining_sos_value is not None

        # ===== STEP 3: GET ALL TEAMS FOR LEAGUE-WIDE RANKINGS =====
        all_teams = _get_all_teams_in_series(series, league_id_int, team)
        
        # ===== STEP 4: CALCULATE LEAGUE-WIDE HISTORICAL SOS RANKINGS =====
        all_teams_historical_sos = []
        for team_record in all_teams:
            team_name = team_record["team"]
            team_historical_sos = _calculate_team_historical_sos(team_name, league_id_int)
            all_teams_historical_sos.append((team_name, team_historical_sos))

        # Sort and rank historical SOS
        all_teams_historical_sos.sort(key=lambda x: x[1], reverse=True)
        user_historical_rank = 0
        all_teams_sos = []

        for i, (team_name, team_sos) in enumerate(all_teams_historical_sos):
            rank = i + 1
            is_user_team = team_name == team
            if is_user_team:
                user_historical_rank = rank

            all_teams_sos.append({
                "team_name": team_name,
                "sos_value": team_sos,
                "rank": rank,
                "is_user_team": is_user_team,
            })

        # ===== STEP 5: CALCULATE LEAGUE-WIDE REMAINING SOS RANKINGS (only if remaining schedule exists) =====
        user_remaining_rank = None
        all_teams_remaining_sos = []
        
        if has_remaining_schedule:
            all_teams_remaining_sos_data = []
            for team_record in all_teams:
                team_name = team_record["team"]
                team_remaining_sos = _calculate_team_remaining_sos(team_name, league_id_int, historical_opponents)
                if team_remaining_sos is not None:  # Only include teams with remaining matches
                    all_teams_remaining_sos_data.append((team_name, team_remaining_sos))

            if all_teams_remaining_sos_data:
                # Sort and rank remaining SOS
                all_teams_remaining_sos_data.sort(key=lambda x: x[1], reverse=True)

                for i, (team_name, team_sos) in enumerate(all_teams_remaining_sos_data):
                    rank = i + 1
                    is_user_team = team_name == team
                    if is_user_team:
                        user_remaining_rank = rank

                    all_teams_remaining_sos.append({
                        "team_name": team_name,
                        "sos_value": team_sos,
                        "rank": rank,
                        "is_user_team": is_user_team,
                    })

        # ===== STEP 6: SCHEDULE COMPARISON ANALYSIS =====
        schedule_comparison = _analyze_schedule_comparison(
            historical_sos_value, remaining_sos_value, 
            user_historical_rank, user_remaining_rank,
            len(all_teams), has_remaining_schedule
        )

        print(f"[DEBUG] Team '{team}' - Historical SOS: {historical_sos_value} (#{user_historical_rank}), Remaining SOS: {remaining_sos_value} (#{user_remaining_rank})")

        return {
            "sos_value": historical_sos_value,
            "remaining_sos_value": remaining_sos_display,
            "remaining_sos_actual": remaining_sos_value,  # For calculations
            "rank": user_historical_rank,
            "remaining_rank": user_remaining_rank,
            "total_teams": len(all_teams),
            "opponents_count": len(historical_opponents),
            "remaining_opponents_count": len(remaining_opponents),
            "has_remaining_schedule": has_remaining_schedule,
            "schedule_comparison": schedule_comparison,
            "all_teams_sos": all_teams_sos,
            "all_teams_remaining_sos": all_teams_remaining_sos,
            "user_team_name": team,
            "error": None,
        }

    except Exception as e:
        print(f"[ERROR] calculate_strength_of_schedule: {str(e)}")
        import traceback

        print(
            f"[ERROR] calculate_strength_of_schedule traceback: {traceback.format_exc()}"
        )
        return {
            "sos_value": 0.0,
            "remaining_sos_value": "N/A",
            "remaining_sos_actual": None,
            "rank": 0,
            "remaining_rank": None,
            "total_teams": 0,
            "opponents_count": 0,
            "remaining_opponents_count": 0,
            "has_remaining_schedule": False,
            "schedule_comparison": {},
            "all_teams_sos": [],
            "all_teams_remaining_sos": [],
            "user_team_name": "",
            "error": str(e),
        }


def _get_opponent_stats(opponent, league_id_int):
    """Get opponent's average points per match from series_stats"""
    try:
        if league_id_int:
            stats_query = """
                SELECT 
                    points,
                    matches_won,
                    matches_lost,
                    matches_tied
                FROM series_stats
                WHERE team = %s AND league_id = %s
            """
            opponent_stats = execute_query_one(stats_query, [opponent, league_id_int])
        else:
            stats_query = """
                SELECT 
                    points,
                    matches_won,
                    matches_lost,
                    matches_tied
                FROM series_stats
                WHERE team = %s
            """
            opponent_stats = execute_query_one(stats_query, [opponent])

        if opponent_stats:
            points = opponent_stats["points"] or 0
            matches_played = (
                (opponent_stats["matches_won"] or 0)
                + (opponent_stats["matches_lost"] or 0)
                + (opponent_stats["matches_tied"] or 0)
            )

            if matches_played > 0:
                avg_points = round(points / matches_played, 2)
                print(f"[DEBUG] {opponent} - {points} points in {matches_played} matches = {avg_points} avg")
                return avg_points
            else:
                print(f"[DEBUG] {opponent} - No matches played, skipping")
                return None
        else:
            print(f"[DEBUG] {opponent} - No stats found, skipping")
            return None
    except Exception as e:
        print(f"[ERROR] Getting opponent stats for {opponent}: {str(e)}")
        return None


def _get_actual_future_matches(team, league_id_int):
    """
    Get actual future matches from the schedule table.
    UPDATED: Now returns all matches (not just future) to support completed seasons.
    """
    try:
        print("[DEBUG] Getting all matches from schedule table...")
        
        if league_id_int:
            matches_query = """
                SELECT 
                    home_team,
                    away_team,
                    match_date,
                    match_time,
                    location
                FROM schedule
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                ORDER BY match_date DESC, match_time DESC
            """
            matches = execute_query(matches_query, [team, team, league_id_int])
        else:
            matches_query = """
                SELECT 
                    home_team,
                    away_team,
                    match_date,
                    match_time,
                    location
                FROM schedule
                WHERE (home_team = %s OR away_team = %s)
                ORDER BY match_date DESC, match_time DESC
            """
            matches = execute_query(matches_query, [team, team])

        print(f"[DEBUG] Found {len(matches)} total matches (including historical)")
        return matches

    except Exception as e:
        print(f"[ERROR] Getting matches: {str(e)}")
        return []


def _simulate_remaining_schedule(team, league_id_int, historical_opponents):
    """
    Simulate remaining schedule for testing purposes.
    Since all schedules are historical, we create a simulated remaining schedule.
    """
    try:
        print("[DEBUG] Simulating remaining schedule for testing...")
        
        # Get all possible opponents from the league
        if league_id_int:
            all_opponents_query = """
                SELECT DISTINCT 
                    CASE 
                        WHEN home_team = %s THEN away_team 
                        ELSE home_team 
                    END as opponent
                FROM match_scores 
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                AND CASE 
                    WHEN home_team = %s THEN away_team 
                    ELSE home_team 
                END IS NOT NULL
            """
            all_possible_opponents = execute_query(all_opponents_query, [team, team, team, league_id_int, team])
        else:
            all_opponents_query = """
                SELECT DISTINCT 
                    CASE 
                        WHEN home_team = %s THEN away_team 
                        ELSE home_team 
                    END as opponent
                FROM match_scores 
                WHERE (home_team = %s OR away_team = %s)
                AND CASE 
                    WHEN home_team = %s THEN away_team 
                    ELSE home_team 
                END IS NOT NULL
            """
            all_possible_opponents = execute_query(all_opponents_query, [team, team, team, team])

        # Convert to set of opponent names
        all_opponents = {opp["opponent"] for opp in all_possible_opponents if opp["opponent"]}
        
        # Simulate remaining opponents (teams not yet played or need rematches)
        import random
        remaining_opponents = list(all_opponents - historical_opponents)
        
        # If no remaining opponents, simulate rematches with some historical opponents
        if not remaining_opponents:
            remaining_opponents = random.sample(list(historical_opponents), min(3, len(historical_opponents)))
        
        # Create simulated matches
        simulated_matches = []
        for i, opponent in enumerate(remaining_opponents[:4]):  # Limit to 4 remaining matches
            # Alternate home/away
            if i % 2 == 0:
                simulated_matches.append({
                    "home_team": team,
                    "away_team": opponent,
                    "match_date": f"2024-{6 + i//2:02d}-{15 + i*7:02d}"  # Future dates
                })
            else:
                simulated_matches.append({
                    "home_team": opponent,
                    "away_team": team,
                    "match_date": f"2024-{6 + i//2:02d}-{15 + i*7:02d}"  # Future dates
                })

        print(f"[DEBUG] Simulated {len(simulated_matches)} remaining matches")
        return simulated_matches

    except Exception as e:
        print(f"[ERROR] Simulating remaining schedule: {str(e)}")
        return []


def _get_all_teams_in_series(series, league_id_int, team):
    """Get all teams in the same series for league-wide rankings"""
    try:
        if league_id_int:
            all_teams_query = """
                SELECT DISTINCT team 
                FROM series_stats 
                WHERE series = %s AND league_id = %s
                AND team IS NOT NULL
            """
            all_teams = execute_query(all_teams_query, [series, league_id_int])
        else:
            all_teams_query = """
                SELECT DISTINCT team 
                FROM series_stats 
                WHERE series = %s
                AND team IS NOT NULL
            """
            all_teams = execute_query(all_teams_query, [series])

        if not all_teams:
            # Fallback: get teams from match data
            if league_id_int:
                fallback_query = """
                    SELECT DISTINCT 
                        CASE 
                            WHEN home_team = %s THEN away_team 
                            ELSE home_team 
                        END as team
                    FROM match_scores 
                    WHERE (home_team = %s OR away_team = %s)
                    AND league_id = %s
                    UNION 
                    SELECT %s as team
                """
                all_teams = execute_query(fallback_query, [team, team, team, league_id_int, team])
            else:
                fallback_query = """
                    SELECT DISTINCT 
                        CASE 
                            WHEN home_team = %s THEN away_team 
                            ELSE home_team 
                        END as team
                    FROM match_scores 
                    WHERE (home_team = %s OR away_team = %s)
                    UNION 
                    SELECT %s as team
                """
                all_teams = execute_query(fallback_query, [team, team, team, team])

        return all_teams

    except Exception as e:
        print(f"[ERROR] Getting all teams in series: {str(e)}")
        return []


def _calculate_team_historical_sos(team_name, league_id_int):
    """Calculate historical SOS for a specific team"""
    try:
        # Get historical matches for this team
        if league_id_int:
            team_matches_query = """
                SELECT home_team, away_team, winner
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                AND winner IS NOT NULL
                AND winner != ''
                AND match_date <= CURRENT_DATE
            """
            team_match_records = execute_query(team_matches_query, [team_name, team_name, league_id_int])
        else:
            team_matches_query = """
                SELECT home_team, away_team, winner
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND winner IS NOT NULL
                AND winner != ''
                AND match_date <= CURRENT_DATE
            """
            team_match_records = execute_query(team_matches_query, [team_name, team_name])

        # Get opponents for this team
        team_opponents = set()
        for match in team_match_records:
            if match["home_team"] == team_name:
                team_opponents.add(match["away_team"])
            else:
                team_opponents.add(match["home_team"])

        # Calculate average points for opponents
        team_opponent_avg_points = []
        for opponent in team_opponents:
            opponent_stats = _get_opponent_stats(opponent, league_id_int)
            if opponent_stats:
                team_opponent_avg_points.append(opponent_stats)

        # Calculate SoS for this team
        if team_opponent_avg_points:
            team_sos = round(sum(team_opponent_avg_points) / len(team_opponent_avg_points), 2)
            return team_sos
        else:
            return 0.0

    except Exception as e:
        print(f"[ERROR] Calculating historical SOS for {team_name}: {str(e)}")
        return 0.0


def _calculate_team_remaining_sos(team_name, league_id_int, user_historical_opponents):
    """Calculate remaining SOS for a specific team"""
    try:
        # Get actual remaining schedule for this team
        remaining_matches = _get_actual_future_matches(team_name, league_id_int)
        
        # Get remaining opponents
        remaining_opponents = set()
        for match in remaining_matches:
            if match["home_team"] == team_name:
                remaining_opponents.add(match["away_team"])
            else:
                remaining_opponents.add(match["home_team"])

        # Calculate average points for remaining opponents
        remaining_opponent_avg_points = []
        for opponent in remaining_opponents:
            opponent_stats = _get_opponent_stats(opponent, league_id_int)
            if opponent_stats:
                remaining_opponent_avg_points.append(opponent_stats)

        # Calculate remaining SOS for this team
        if remaining_opponent_avg_points:
            team_remaining_sos = round(sum(remaining_opponent_avg_points) / len(remaining_opponent_avg_points), 2)
            return team_remaining_sos
        else:
            return None  # No remaining matches or no valid opponent data

    except Exception as e:
        print(f"[ERROR] Calculating remaining SOS for {team_name}: {str(e)}")
        return None


def _analyze_schedule_comparison(historical_sos, remaining_sos, historical_rank, remaining_rank, total_teams, has_remaining_schedule):
    """Analyze the comparison between historical and remaining schedule difficulty"""
    try:
        # If no remaining schedule exists, provide appropriate messaging
        if not has_remaining_schedule or remaining_sos is None:
            historical_percentile = round((total_teams - historical_rank + 1) / total_teams * 100, 1) if historical_rank else 50.0
            
            return {
                "sos_difference": None,
                "rank_difference": None,
                "difficulty_assessment": "no_remaining_schedule",
                "difficulty_text": "no remaining matches scheduled",
                "historical_percentile": historical_percentile,
                "remaining_percentile": None,
                "summary": "Your season schedule is complete. No remaining matches are currently scheduled.",
                "recommendation": "Season analysis shows your team faced opponents with an average strength rating. Focus on reviewing completed matches for insights."
            }
        
        # Calculate difference only if remaining schedule exists
        sos_difference = remaining_sos - historical_sos
        rank_difference = remaining_rank - historical_rank  # Higher rank number = easier schedule
        
        # Determine if remaining schedule is easier or harder
        if sos_difference > 0.2:
            difficulty_assessment = "significantly_harder"
            difficulty_text = "significantly harder"
        elif sos_difference > 0.05:
            difficulty_assessment = "harder"
            difficulty_text = "harder"
        elif sos_difference < -0.2:
            difficulty_assessment = "significantly_easier"
            difficulty_text = "significantly easier"
        elif sos_difference < -0.05:
            difficulty_assessment = "easier"
            difficulty_text = "easier"
        else:
            difficulty_assessment = "similar"
            difficulty_text = "similar difficulty"

        # Calculate percentile improvements
        historical_percentile = round((total_teams - historical_rank + 1) / total_teams * 100, 1)
        remaining_percentile = round((total_teams - remaining_rank + 1) / total_teams * 100, 1)
        
        # Generate summary text
        if difficulty_assessment in ["significantly_easier", "easier"]:
            summary = f"Good news! Your remaining schedule is {difficulty_text} than what you've played so far."
        elif difficulty_assessment in ["significantly_harder", "harder"]:
            summary = f"Your remaining schedule is {difficulty_text} than what you've played so far."
        else:
            summary = f"Your remaining schedule has {difficulty_text} to what you've played so far."

        return {
            "sos_difference": round(sos_difference, 2),
            "rank_difference": rank_difference,
            "difficulty_assessment": difficulty_assessment,
            "difficulty_text": difficulty_text,
            "historical_percentile": historical_percentile,
            "remaining_percentile": remaining_percentile,
            "summary": summary,
            "recommendation": _generate_schedule_recommendation(difficulty_assessment, sos_difference, rank_difference)
        }

    except Exception as e:
        print(f"[ERROR] Analyzing schedule comparison: {str(e)}")
        return {
            "sos_difference": 0.0,
            "rank_difference": 0,
            "difficulty_assessment": "unknown",
            "difficulty_text": "unknown",
            "historical_percentile": 50.0,
            "remaining_percentile": 50.0,
            "summary": "Unable to analyze schedule comparison.",
            "recommendation": ""
        }


def _generate_schedule_recommendation(difficulty_assessment, sos_difference, rank_difference):
    """Generate strategic recommendations based on schedule analysis"""
    if difficulty_assessment == "significantly_easier":
        return "This is a great opportunity to improve your standings. Focus on consistency and capitalize on these easier matchups."
    elif difficulty_assessment == "easier":
        return "Your remaining opponents are slightly weaker. This could be a good chance to gain ground in the standings."
    elif difficulty_assessment == "significantly_harder":
        return "Your toughest matches are ahead. Focus on preparation and consider this valuable experience against strong opponents."
    elif difficulty_assessment == "harder":
        return "Your remaining schedule is more challenging. Use this as motivation to elevate your game."
    else:
        return "Your remaining schedule difficulty is consistent with what you've faced. Continue your current approach."


def get_other_home_teams_at_club_on_date(team_id, match_date, user_email):
    """
    Find other teams at the same club who have home matches on the specified date.
    
    Args:
        team_id: Current user's team ID
        match_date: Date object to check for other home matches
        user_email: User's email for logging
        
    Returns:
        List of series names (e.g., ["Series 7", "Series 23", "Series 38"])
    """
    try:
        from database_utils import execute_query, execute_query_one
        
        # Get current team's club_id and league_id
        team_info_query = """
            SELECT club_id, league_id, c.name as club_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            WHERE t.id = %s
        """
        team_info = execute_query_one(team_info_query, [team_id])
        
        if not team_info:
            print(f"[DEBUG] get_other_home_teams_at_club_on_date: No team info found for team_id {team_id}")
            return []
            
        club_id = team_info["club_id"]
        league_id = team_info["league_id"]
        club_name = team_info["club_name"]
        
        # OPTIMIZATION: Reduced debug output to prevent spam
        # print(f"[DEBUG] get_other_home_teams_at_club_on_date: Looking for other teams at {club_name} (club_id {club_id}), league_id {league_id} on {match_date}")
        
        # REMOVED: Excessive debug query that was causing performance issues
        
        # Now find ONLY teams that are playing AT HOME (location matches club name)
        # This is more accurate than relying on home_team_id which might be inconsistent
        home_matches_query = """
            SELECT DISTINCT s.display_name as series_name
            FROM schedule sc
            JOIN teams t ON (sc.home_team_id = t.id OR sc.away_team_id = t.id)
            JOIN series s ON t.series_id = s.id
            JOIN clubs c ON t.club_id = c.id
            WHERE sc.match_date = %s 
                AND sc.location = %s
                AND t.club_id = %s
                AND t.league_id = %s
                AND t.id != %s
                AND t.is_active = TRUE
            ORDER BY s.display_name
        """
        
        other_teams = execute_query(home_matches_query, [match_date, club_name, club_id, league_id, team_id])
        
        if other_teams:
            series_names = [team["series_name"] for team in other_teams]
            # OPTIMIZATION: Reduced debug output
            # print(f"[DEBUG] get_other_home_teams_at_club_on_date: Found {len(series_names)} other teams playing at home at {club_name}: {series_names}")
            return series_names
        else:
            # OPTIMIZATION: Reduced debug output
            # print(f"[DEBUG] get_other_home_teams_at_club_on_date: No other teams found playing at home at {club_name} on {match_date}")
            return []
            
    except Exception as e:
        print(f"[ERROR] get_other_home_teams_at_club_on_date: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return []


def is_substitute_player(player_id, match_team_id, user_league_id=None, user_team_id=None):
    """
    ✅ ENHANCED: Determine if a player is a substitute with user team context support
    
    Args:
        player_id: The player's tenniscores_player_id
        match_team_id: The team ID or team name they're playing for in this match
        user_league_id: Optional league ID for context (deprecated)
        user_team_id: User's current team context (preferred method)
        
    Returns:
        bool: True if player is a substitute, False otherwise
    """
    try:
        # ✅ ENHANCED: Use user's current team context if available
        if user_team_id:
            # Get all teams for this player to check against user's current team
            player_teams_query = """
                SELECT team_id, league_id, club_id, series_id
                FROM players 
                WHERE tenniscores_player_id = %s AND is_active = true
            """
            player_teams = execute_query(player_teams_query, (player_id,))
            
            if not player_teams:
                # Player has no team assignments, not a substitute
                return False
            
            # Check if player is registered with the user's current team
            player_team_ids = [team['team_id'] for team in player_teams if team['team_id']]
            
            if user_team_id in player_team_ids:
                # Player is registered with user's current team, use that as reference
                reference_team_id = user_team_id
                print(f"[DEBUG] Substitute check: Using user team context {user_team_id} for player {player_id}")
            else:
                # Player is not on user's current team, use their primary team
                # This handles cases where we're looking at other players
                primary_team_record = max(player_teams, key=lambda x: (x.get('wins', 0), -x.get('losses', 0)))
                reference_team_id = primary_team_record.get('team_id')
                print(f"[DEBUG] Substitute check: Player {player_id} not on user team {user_team_id}, using primary team {reference_team_id}")
        else:
            # ✅ FALLBACK: Legacy method - use player's primary team assignment
            player_query = """
                SELECT team_id, league_id, club_id, series_id
                FROM players 
                WHERE tenniscores_player_id = %s AND is_active = true
                ORDER BY wins DESC, losses ASC
                LIMIT 1
            """
            player_record = execute_query_one(player_query, (player_id,))
            
            if not player_record or not player_record.get('team_id'):
                # Player has no primary team assignment, not a substitute
                return False
                
            reference_team_id = player_record.get('team_id')
            print(f"[DEBUG] Substitute check: Using legacy primary team {reference_team_id} for player {player_id}")
        
        # Handle case where match_team_id is a team name (string) instead of team ID (integer)
        if isinstance(match_team_id, str):
            # Look up the team ID from the team name
            team_lookup_query = """
                SELECT id FROM teams WHERE team_name = %s
            """
            team_record = execute_query_one(team_lookup_query, (match_team_id,))
            if team_record:
                match_team_id = team_record.get('id')
            else:
                # If we can't find the team, assume not a substitute
                print(f"[DEBUG] Substitute check: Could not find team ID for team name '{match_team_id}'")
                return False
        
        # ✅ ENHANCED: Compare with reference team (user's team context or player's primary team)
        is_sub = reference_team_id != match_team_id
        print(f"[DEBUG] Substitute check: Player {player_id} - Reference team: {reference_team_id}, Match team: {match_team_id}, Is substitute: {is_sub}")
        return is_sub
        
    except Exception as e:
        print(f"Error determining substitute status for player {player_id}: {e}")
        return False
