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
        win_rate = round(career_data["career_win_percentage"] or 0, 1)

        # Get current PTI as career PTI
        latest_pti = career_data["current_pti"] or "N/A"

        career_stats = {
            "winRate": win_rate,
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
        # First try to get upcoming matches (future + recent past)
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
            AND match_date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY match_date ASC, match_time ASC
            LIMIT 20
        """
        
        schedule_matches = execute_query(schedule_query, [
            user_team_id, user_team_id, user_team_id, user_team_id, user_team_id, user_team_id, league_db_id
        ])
        
        # If no recent/upcoming matches, get the most recent completed matches
        if not schedule_matches:
            recent_matches_query = """
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
                    'past' as status
                FROM schedule
                WHERE (home_team_id = %s OR away_team_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC, match_time DESC
                LIMIT 10
            """
            
            schedule_matches = execute_query(recent_matches_query, [
                user_team_id, user_team_id, user_team_id, user_team_id, user_team_id, user_team_id, league_db_id
            ])
        
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
        # Debug print to see what we're getting
        print(f"[DEBUG] get_player_analysis: User type: {type(user)}, Data: {user}")

        # Ensure user data is a dictionary
        if not isinstance(user, dict):
            print(
                f"[ERROR] get_player_analysis: User data is not a dictionary: {type(user)}"
            )
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
                "error": "Invalid user data format",
            }

        # Get player ID from user data
        player_id = user.get("tenniscores_player_id")
        if not player_id:
            print(
                "[ERROR] get_player_analysis: No tenniscores_player_id found in user data"
            )
            return {
                "current_season": {
                    "winRate": 0,
                    "matches": 0,
                    "wins": 0,
                    "losses": 0,
                    "ptiChange": "N/A",
                },
                "court_analysis": {
                    "court1": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                    "court2": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                    "court3": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                    "court4": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                },
                "career_stats": {
                    "winRate": 0,
                    "matches": 0,
                    "wins": 0,
                    "losses": 0,
                    "pti": "N/A",
                },
                "player_history": {"progression": "", "seasons": []},
                "videos": {"match": [], "practice": []},
                "trends": {},
                "career_pti_change": "N/A",
                "current_pti": None,
                "weekly_pti_change": None,
                "pti_data_available": False,
                "error": "Player ID not found",
            }

        # Get user's league for filtering
        user_league_id = user.get("league_id", "")
        user_league_name = user.get("league_name", "")
        print(
            f"[DEBUG] get_player_analysis: User league_id string: '{user_league_id}', league_name: '{user_league_name}'"
        )

        # DEBUGGING: Track league ID conversion issues and force fresh data
        print(f"[SESSION-DEBUG] Raw user data from session:")
        print(
            f"  league_id: {user.get('league_id')} (type: {type(user.get('league_id'))})"
        )
        print(f"  league_name: {user.get('league_name')}")
        print(f"  tenniscores_player_id: {user.get('tenniscores_player_id')}")

        # Force refresh league data from database respecting user's league_context
        if hasattr(user, "get") and user.get("email"):
            try:
                fresh_user_data = execute_query_one(
                    """
                    SELECT u.id, u.email, u.first_name, u.last_name, u.league_context,
                           p.tenniscores_player_id, l.id as league_db_id, l.league_id, l.league_name
                    FROM users u
                    JOIN user_player_associations upa ON u.id = upa.user_id
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    JOIN leagues l ON p.league_id = l.id
                    WHERE u.email = %s 
                    AND (u.league_context IS NULL OR p.league_id = u.league_context)
                    ORDER BY (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END)
                    LIMIT 1
                """,
                    [user["email"]],
                )

                if fresh_user_data:
                    print(f"[SESSION-DEBUG] Fresh database lookup:")
                    print(f"  league_db_id: {fresh_user_data['league_db_id']}")
                    print(f"  league_id: {fresh_user_data['league_id']}")
                    print(f"  league_name: {fresh_user_data['league_name']}")

                    # Use fresh data instead of potentially stale session data
                    user_league_id = fresh_user_data["league_id"]
                    user_league_name = fresh_user_data["league_name"]
                    print(f"[SESSION-DEBUG] Using fresh league data: {user_league_id}")
                else:
                    print(f"[SESSION-DEBUG] No fresh data found, using session data")
            except Exception as e:
                print(f"[SESSION-DEBUG] Error getting fresh data: {e}")
                # Continue with session data if refresh fails

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
        elif user_league_id is None and user_league_name:
            # Handle case where league_id is None but league_name exists
            print(
                f"[DEBUG] league_id is None, attempting to resolve from league_name: '{user_league_name}'"
            )
            try:
                league_record = execute_query_one(
                    "SELECT id, league_id FROM leagues WHERE league_name = %s",
                    [user_league_name],
                )
                if league_record:
                    league_id_int = league_record["id"]
                    resolved_league_id = league_record["league_id"]
                    print(
                        f"[DEBUG] Resolved league_name '{user_league_name}' to league_id '{resolved_league_id}' (db_id: {league_id_int})"
                    )
                else:
                    print(
                        f"[WARNING] League name '{user_league_name}' not found in leagues table"
                    )
            except Exception as e:
                print(f"[DEBUG] Could not resolve league from league_name: {e}")

        # Query player history and match data from database
        # Note: execute_query and execute_query_one are already imported at module level

        # Use player_id to get the correct team for this league (fixes multi-team issue)
        user_team_id = None
        user_team_name = None
        
        # PRIORITY 1: Use team_context from user if provided (from composite player URL)
        team_context = user.get("team_context") if user else None
        if team_context:
            try:
                # Get team name for the specific team_id from team context
                team_context_query = """
                    SELECT t.id, t.team_name
                    FROM teams t
                    WHERE t.id = %s
                """
                team_context_result = execute_query_one(team_context_query, [team_context])
                if team_context_result:
                    user_team_id = team_context_result['id'] 
                    user_team_name = team_context_result['team_name']
                    print(f"[DEBUG] Using team_context from URL: team_id={user_team_id}, team_name={user_team_name}")
                else:
                    print(f"[DEBUG] team_context {team_context} not found in teams table")
            except Exception as e:
                print(f"[DEBUG] Error getting team from team_context {team_context}: {e}")
        
        # PRIORITY 2: Fallback to database lookup if no team_context provided
        if not user_team_id and player_id and league_id_int:
            try:
                # For multi-team players, prefer team with most recent match activity in this league
                team_selection_query = """
                    SELECT p.team_id, t.team_name,
                           (SELECT MAX(match_date) 
                            FROM match_scores ms 
                            WHERE (ms.home_player_1_id = p.tenniscores_player_id 
                                   OR ms.home_player_2_id = p.tenniscores_player_id
                                   OR ms.away_player_1_id = p.tenniscores_player_id 
                                   OR ms.away_player_2_id = p.tenniscores_player_id)
                            AND (ms.home_team_id = p.team_id OR ms.away_team_id = p.team_id)
                            AND ms.league_id = p.league_id
                           ) as last_match_date
                    FROM players p
                    JOIN teams t ON p.team_id = t.id
                    WHERE p.tenniscores_player_id = %s AND p.league_id = %s AND p.is_active = TRUE
                    ORDER BY last_match_date DESC NULLS LAST, p.team_id DESC
                    LIMIT 1
                """
                team_result = execute_query_one(team_selection_query, [player_id, league_id_int])
                if team_result:
                    user_team_id = team_result['team_id']
                    user_team_name = team_result['team_name']
                    print(f"[DEBUG] Selected team using player_id fallback: team_id={user_team_id}, team_name={user_team_name}")
            except Exception as e:
                print(f"[DEBUG] Error getting team for player_id {player_id}: {e}")

        # Get player history - filter by league AND team to fix multi-team issue
        if league_id_int and user_team_id:
            # Use team_id filtering like track-byes-courts for most reliable results
            history_query = """
                SELECT 
                    id,
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
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                AND (home_team_id = %s OR away_team_id = %s)
                ORDER BY match_date DESC
            """
            player_matches = execute_query(
                history_query,
                [player_id, player_id, player_id, player_id, league_id_int, user_team_id, user_team_id],
            )
            print(f"[DEBUG] Filtered matches by team_id {user_team_id} ('{user_team_name}'): {len(player_matches) if player_matches else 0} matches")
        elif league_id_int:
            # Fallback: filter by league only (original behavior for single-team players)
            history_query = """
                SELECT 
                    id,
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
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC
            """
            player_matches = execute_query(
                history_query,
                [player_id, player_id, player_id, player_id, league_id_int],
            )
        else:
            # No league filtering if we don't have a valid league_id
            history_query = """
                SELECT 
                    id,
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
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                ORDER BY match_date DESC
            """
            player_matches = execute_query(
                history_query, [player_id, player_id, player_id, player_id]
            )

        # FIX: Calculate accurate wins/losses from match results
        print(
            f"[DEBUG] Found {len(player_matches) if player_matches else 0} matches for analysis"
        )

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
                if is_home and won:
                    wins += 1
                elif not is_home and not won:
                    wins += 1
                else:
                    losses += 1

            print(
                f"[DEBUG] Calculated match stats: {wins} wins, {losses} losses from {total_matches} matches"
            )

        if not player_matches:
            print(
                f"[DEBUG] get_player_analysis: No detailed matches found for player {player_id} in league {league_id_int}"
            )
            print(
                f"[DEBUG] Falling back to aggregate player stats from players table..."
            )

            # Fall back to aggregate stats from players table when detailed match data isn't available
            try:
                if league_id_int:
                    aggregate_query = """
                        SELECT wins, losses, pti, first_name, last_name
                        FROM players 
                        WHERE tenniscores_player_id = %s AND league_id = %s
                    """
                    aggregate_stats = execute_query_one(
                        aggregate_query, [player_id, league_id_int]
                    )
                else:
                    aggregate_query = """
                        SELECT wins, losses, pti, first_name, last_name
                        FROM players 
                        WHERE tenniscores_player_id = %s
                    """
                    aggregate_stats = execute_query_one(aggregate_query, [player_id])

                if aggregate_stats:
                    print(
                        f"[DEBUG] Found aggregate stats: will be used as fallback if detailed analysis fails"
                    )
                    # Don't return early - continue to detailed court analysis
                else:
                    print(f"[DEBUG] No aggregate stats found in players table either")
            except Exception as e:
                print(f"[DEBUG] Error getting aggregate stats: {e}")

            # Final fallback - return zeros with corrected match stats
            return {
                "current_season": {
                    "winRate": 0,
                    "matches": 0,
                    "wins": 0,
                    "losses": 0,
                    "ptiChange": "N/A",
                },
                "court_analysis": {
                    "court1": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                    "court2": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                    "court3": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                    "court4": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                },
                "career_stats": {
                    "winRate": 0,
                    "matches": 0,
                    "wins": 0,
                    "losses": 0,
                    "pti": "N/A",
                },
                "player_history": {"progression": "", "seasons": []},
                "videos": {"match": [], "practice": []},
                "trends": {},
                "career_pti_change": "N/A",
                "current_pti": None,
                "weekly_pti_change": None,
                "pti_data_available": False,
                "error": None,
            }

        # Get PTI data from players table and player_history table
        pti_data = {
            "current_pti": None,
            "pti_change": None,
            "pti_data_available": False,
        }

        try:
            # Get current PTI and series info from players table - prioritize player with PTI history
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

                print(
                    f"[DEBUG] Mobile Service - Using player_id {player_pti_data['id']} with {history_count} history records"
                )
                
                # If current_pti is NULL but we have history, get the most recent PTI from history
                if current_pti is None and history_count > 0:
                    print(f"[DEBUG] Current PTI is NULL, getting most recent from {history_count} history records")
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
                        print(f"[DEBUG] Using most recent PTI from history: {current_pti}")
                
                print(
                    f"[DEBUG] Final PTI value: {current_pti} for series: {series_name}"
                )

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

                player_pti_records = execute_query(
                    player_pti_history_query, [player_db_id]
                )

                if player_pti_records and len(player_pti_records) >= 2:
                    # Get the most recent and previous week's PTI values for this specific player
                    most_recent_pti = player_pti_records[0]["end_pti"]
                    previous_week_pti = player_pti_records[1]["end_pti"]
                    pti_change = most_recent_pti - previous_week_pti
                    print(
                        f"[DEBUG] Weekly PTI change via player FK: {pti_change:+.1f} (from {player_pti_records[1]['formatted_date']} to {player_pti_records[0]['formatted_date']})"
                    )

                elif series_name:
                    # Fallback: Try series matching with flexible name patterns
                    series_patterns = [
                        series_name,  # Exact: "Chicago 22"
                        series_name.replace(" ", ": "),  # With colon: "Chicago: 22"
                        f"%{series_name}%",  # Fuzzy: "%Chicago 22%"
                        f"%{series_name.replace(' ', ': ')}%",  # Fuzzy with colon: "%Chicago: 22%"
                    ]

                    for pattern in series_patterns:
                        history_query = """
                            SELECT 
                                date,
                                end_pti,
                                series,
                                TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
                            FROM player_history
                            WHERE series ILIKE %s
                            ORDER BY date DESC
                            LIMIT 10
                        """

                        history_records = execute_query(history_query, [pattern])

                        if history_records and len(history_records) >= 2:
                            # Find the most recent and previous PTI values for this series
                            recent_pti = history_records[0]["end_pti"]
                            previous_pti = history_records[1]["end_pti"]
                            pti_change = recent_pti - previous_pti
                            print(
                                f"[DEBUG] PTI change via series pattern '{pattern}': {pti_change:+.1f}"
                            )
                            break
                    else:
                        print(
                            f"[DEBUG] No series history found for PTI change calculation"
                        )

                pti_data = {
                    "current_pti": current_pti,
                    "pti_change": pti_change,
                    "pti_data_available": True,
                }
                print(
                    f"[DEBUG] PTI data available: Current={current_pti}, Change={pti_change:+.1f}"
                )
            else:
                print(f"[DEBUG] No current PTI found in players table for {player_id}")
                print(
                    f"[DEBUG] This is expected for leagues like CNSWPL that don't track PTI ratings"
                )

        except Exception as pti_error:
            print(f"[DEBUG] Error fetching PTI data: {pti_error}")
            # Don't create sample data - only show PTI card if real data exists

        # Helper function to get player name from ID
        def get_player_name(player_id):
            if not player_id:
                return None
            try:
                # Try to get player name from database
                if league_id_int:
                    name_query = """
                        SELECT first_name, last_name FROM players 
                        WHERE tenniscores_player_id = %s AND league_id = %s
                    """
                    player_record = execute_query_one(
                        name_query, [player_id, league_id_int]
                    )
                else:
                    name_query = """
                        SELECT first_name, last_name FROM players 
                        WHERE tenniscores_player_id = %s
                    """
                    player_record = execute_query_one(name_query, [player_id])

                if player_record:
                    return f"{player_record['first_name']} {player_record['last_name']}"
                else:
                    # FIXED: For substitute players from other leagues/teams
                    # Try to find the player across ALL leagues if not found in current league
                    if league_id_int:  # Only do cross-league search if we were filtering by league initially
                        cross_league_query = """
                            SELECT first_name, last_name FROM players 
                            WHERE tenniscores_player_id = %s
                            ORDER BY league_id LIMIT 1
                        """
                        cross_league_record = execute_query_one(cross_league_query, [player_id])
                        if cross_league_record:
                            partner_name = f"{cross_league_record['first_name']} {cross_league_record['last_name']}"
                            print(f"[DEBUG] Found substitute player from different league: {partner_name} (ID: {player_id})")
                            return partner_name
                    
                    # Fallback: return truncated player ID if no name found anywhere
                    return f"Player {player_id[:8]}..."
            except Exception as e:
                print(f"[DEBUG] Error getting player name for {player_id}: {e}")
                return f"Player {player_id[:8]}..."

        # Calculate court analysis using CORRECT logic based on match position within team's matches on each date
        court_analysis = {}

        # Always show 4 courts
        max_courts = 4

        # Get all matches on the dates this player played to determine correct court assignments
        from collections import defaultdict
        from datetime import datetime

        # Initialize court analysis dictionary
        court_analysis = {}
        player_stats = defaultdict(
            lambda: {"matches": 0, "wins": 0, "courts": {}, "partners": {}}
        )

        def parse_date(date_str):
            if not date_str:
                return datetime.min
            # Handle the specific format from our database: "DD-Mon-YY"
            for fmt in ("%d-%b-%y", "%d-%B-%y", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return datetime.min

        # Get player match dates
        player_dates = []
        for match in player_matches:
            date_str = match.get("Date", "")
            parsed_date = parse_date(date_str)
            if parsed_date != datetime.min:
                player_dates.append(parsed_date.date())

        # FIXED: Use REAL court assignments based on match position within team matchup
        # Court Number = ROW_NUMBER() of match within same team matchup on same date
        
        # Initialize court stats for tracking real court performance
        court_stats = {
            f"court{i}": {
                "matches": 0,
                "wins": 0,
                "losses": 0,
                "partners": defaultdict(lambda: {"matches": 0, "wins": 0, "losses": 0}),
            }
            for i in range(1, max_courts + 1)
        }
        
        # Process each match to determine ACTUAL court assignment
        # First, get ALL team matchups and their match counts for context
        all_team_matchups = {}
        for match in player_matches:
            match_date = match.get("Date")
            home_team = match.get("Home Team", "")
            away_team = match.get("Away Team", "")
            matchup_key = f"{match_date}|{home_team}|{away_team}"
            
            if matchup_key not in all_team_matchups:
                # Get ALL matches for this team matchup on this date, filtered by league and team context
                if league_id_int and user_team_id:
                    # Filter by league_id and team_id for accurate court assignment for this specific team
                    team_matchup_query = """
                        SELECT id
                        FROM match_scores 
                        WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                        AND home_team = %s 
                        AND away_team = %s
                        AND league_id = %s
                        AND (home_team_id = %s OR away_team_id = %s)
                        ORDER BY id ASC
                    """
                    all_matches = execute_query(team_matchup_query, [match_date, home_team, away_team, league_id_int, user_team_id, user_team_id])
                    print(f"[DEBUG] Found {len(all_matches)} matches for team matchup with team filtering")
                elif league_id_int:
                    # Fallback: filter by league only
                    team_matchup_query = """
                        SELECT id
                        FROM match_scores 
                        WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                        AND home_team = %s 
                        AND away_team = %s
                        AND league_id = %s
                        ORDER BY id ASC
                    """
                    all_matches = execute_query(team_matchup_query, [match_date, home_team, away_team, league_id_int])
                    print(f"[DEBUG] Found {len(all_matches)} matches for team matchup with league filtering")
                else:
                    # No filtering (original behavior)
                    team_matchup_query = """
                        SELECT id
                        FROM match_scores 
                        WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                        AND home_team = %s 
                        AND away_team = %s
                        ORDER BY id ASC
                    """
                    all_matches = execute_query(team_matchup_query, [match_date, home_team, away_team])
                    print(f"[DEBUG] Found {len(all_matches)} matches for team matchup with no filtering")
                
                all_team_matchups[matchup_key] = [m["id"] for m in all_matches]
        
        # Now process each match with correct court assignment
        for match in player_matches:
            match_date = match.get("Date")
            home_team = match.get("Home Team", "")
            away_team = match.get("Away Team", "")
            match_id = match.get("id")

            # FIXED: Use REAL court assignment based on position in team matchup
            matchup_key = f"{match_date}|{home_team}|{away_team}"
            team_match_ids = all_team_matchups.get(matchup_key, [])
            
            # Find this match's position in the ordered team matchup
            court_num = None
            for i, team_match_id in enumerate(team_match_ids, 1):
                if team_match_id == match_id:
                    court_num = i  # Position in team matchup = Court number
                    break

            # FIXED: Instead of skipping matches, assign them to a court
            if court_num is None or court_num > max_courts:
                # Fallback: Distribute unassignable matches evenly across courts 1-4
                # Use match_id modulo to ensure consistent assignment
                fallback_court = (match_id % max_courts) + 1
                court_num = fallback_court
                print(f"[DEBUG] Match {match_id} assigned to fallback court {court_num}")

            court_key = f"court{court_num}"

            # Determine if player won
            is_home = player_id in [
                match.get("Home Player 1"),
                match.get("Home Player 2"),
            ]
            winner = match.get("Winner") or ""
            won = (is_home and winner.lower() == "home") or (
                not is_home and winner.lower() == "away"
            )

            # Update court performance stats
            court_stats[court_key]["matches"] += 1
            if won:
                court_stats[court_key]["wins"] += 1
            else:
                court_stats[court_key]["losses"] += 1

            # Track REAL partnerships on REAL courts
            if is_home:
                partner_id = (
                    match.get("Home Player 2")
                    if match.get("Home Player 1") == player_id
                    else match.get("Home Player 1")
                )
                partner_name_from_json = (
                    match.get("Home Player 2")
                    if match.get("Home Player 1") == player_id
                    else match.get("Home Player 1")
                )
            else:
                partner_id = (
                    match.get("Away Player 2")
                    if match.get("Away Player 1") == player_id
                    else match.get("Away Player 1")
                )
                partner_name_from_json = (
                    match.get("Away Player 2")
                    if match.get("Away Player 1") == player_id
                    else match.get("Away Player 1")
                )

            print(f"[DEBUG PARTNER] Match {match_id} on {court_key}: player_id={player_id}, partner_id={partner_id}, partner_name_from_json={partner_name_from_json}")

            partner_name = None
            if partner_id:
                # Standard case: we have a partner ID, look up the name
                partner_name = get_player_name(partner_id)
                print(f"[DEBUG PARTNER]   Partner name resolved via ID: {partner_name}")
                if partner_name and partner_name.startswith("Player "):
                    print(f"[DEBUG PARTNER]   Fallback logic triggered for partner_id={partner_id}")
            elif partner_name_from_json and isinstance(partner_name_from_json, str) and not partner_name_from_json.startswith("nndz-"):
                # FIXED: Handle substitute players where we have name but no ID
                print(f"[DEBUG PARTNER]   No partner_id but found partner name in JSON: '{partner_name_from_json}'")
                
                # Try to look up the player ID by name across all leagues
                try:
                    name_parts = partner_name_from_json.strip().split()
                    if len(name_parts) >= 2:
                        first_name = name_parts[0]
                        last_name = " ".join(name_parts[1:])
                        
                        # Search across all leagues for this player name
                        name_lookup_query = """
                            SELECT tenniscores_player_id, first_name, last_name, league_id
                            FROM players 
                            WHERE LOWER(first_name) = LOWER(%s) AND LOWER(last_name) = LOWER(%s)
                            ORDER BY league_id
                            LIMIT 1
                        """
                        name_lookup_result = execute_query_one(name_lookup_query, [first_name, last_name])
                        
                        if name_lookup_result:
                            partner_id = name_lookup_result['tenniscores_player_id']
                            partner_name = f"{name_lookup_result['first_name']} {name_lookup_result['last_name']}"
                            print(f"[DEBUG PARTNER]   Found partner by name lookup: {partner_name} (ID: {partner_id}, League: {name_lookup_result['league_id']})")
                        else:
                            # Fallback: use the name directly from JSON if no ID found
                            partner_name = partner_name_from_json
                            print(f"[DEBUG PARTNER]   Using partner name directly from JSON: {partner_name}")
                    else:
                        partner_name = partner_name_from_json
                        print(f"[DEBUG PARTNER]   Using partner name directly (insufficient name parts): {partner_name}")
                        
                except Exception as e:
                    print(f"[DEBUG PARTNER]   Error looking up partner by name: {e}")
                    partner_name = partner_name_from_json
                    print(f"[DEBUG PARTNER]   Using partner name directly from JSON after error: {partner_name}")
            else:
                print(f"[DEBUG PARTNER]   No partner_id or valid partner name found for this match.")

            if partner_name:
                court_stats[court_key]["partners"][partner_name]["matches"] += 1
                if won:
                    court_stats[court_key]["partners"][partner_name]["wins"] += 1
                else:
                    court_stats[court_key]["partners"][partner_name]["losses"] += 1

        # Build court_analysis using REAL court performance data
        total_court_matches = 0
        for i in range(1, max_courts + 1):
            court_key = f"court{i}"
            stat = court_stats[court_key]
            
            court_matches = stat["matches"]
            court_wins = stat["wins"]
            court_losses = stat["losses"]
            court_win_rate = (
                round((court_wins / court_matches) * 100, 1) if court_matches > 0 else 0
            )
            
            total_court_matches += court_matches
            print(f"[DEBUG] {court_key}: {court_matches} matches ({court_wins}-{court_losses})")

            # Get REAL partners with their REAL performance on this REAL court
            top_partners = []
            for partner_name, partner_stats in stat["partners"].items():
                if partner_name and partner_stats["matches"] > 0:
                    partner_wins = partner_stats["wins"]
                    partner_losses = partner_stats["losses"]
                    match_count = partner_stats["matches"]
                    partner_win_rate = (
                        round((partner_wins / match_count) * 100, 1)
                        if match_count > 0
                        else 0
                    )

                    top_partners.append(
                        {
                            "name": partner_name,
                            "matches": match_count,
                            "wins": partner_wins,
                            "losses": partner_losses,
                            "winRate": partner_win_rate,
                        }
                    )

            # Sort by number of matches together (descending)
            top_partners.sort(key=lambda p: p["matches"], reverse=True)

            court_analysis[court_key] = {
                "winRate": court_win_rate,
                "record": f"{court_wins}-{court_losses}",
                "matches": court_matches,
                "topPartners": top_partners,  # All partners on this court
            }

        # Use the corrected win/loss calculations from earlier in the function
        # (total_matches, wins, losses are already calculated correctly above)
        win_rate = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0
        print(
            f"[DEBUG] Using corrected stats: {wins}-{losses} = {win_rate}% win rate from {total_matches} matches"
        )
        print(f"[DEBUG] Total matches: {total_matches}, Court matches total: {total_court_matches}")
        
        if total_matches != total_court_matches:
            print(f"[WARNING] Match count mismatch! Total: {total_matches}, Courts: {total_court_matches}")


        
        if total_matches == total_court_matches:
            print(f"[SUCCESS] Match counts match perfectly: {total_matches} = {total_court_matches}")
        else:
            print(f"[WARNING] Match count mismatch detected")

        # Build current season stats
        # Calculate PTI change for current season (start to end of season)
        season_pti_change = "N/A"
        if pti_data.get("pti_data_available", False):
            try:
                # Get season start and end PTI values from player_history
                current_pti = pti_data.get("current_pti")

                # Get player's database ID for history lookup - prioritize player with PTI history
                player_pti_query = """
                    SELECT 
                        p.id,
                        p.series_id,
                        s.name as series_name,
                        (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                    FROM players p
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id = %s
                    ORDER BY history_count DESC, p.id DESC
                """
                player_pti_data = execute_query_one(player_pti_query, [player_id])

                if player_pti_data:
                    player_db_id = player_pti_data["id"]
                    series_name = player_pti_data["series_name"]

                    # Calculate current tennis season dates (Aug 1 - July 31)
                    from datetime import datetime

                    current_date = datetime.now()
                    current_year = current_date.year
                    current_month = current_date.month

                    # Determine season year based on current date
                    if current_month >= 8:  # Aug-Dec: current season
                        season_start_year = current_year
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

                    season_pti_records = execute_query(
                        season_pti_query,
                        [player_db_id, season_start_date, season_end_date],
                    )

                    if season_pti_records and len(season_pti_records) >= 2:
                        # Get first and last PTI values of the season
                        start_pti = season_pti_records[0]["end_pti"]
                        end_pti = season_pti_records[-1]["end_pti"]
                        season_pti_change = round(end_pti - start_pti, 1)
                        print(
                            f"[DEBUG] Season PTI change: {start_pti} -> {end_pti} = {season_pti_change:+.1f}"
                        )
                    elif series_name:
                        # Fallback: Use series matching for season PTI calculation
                        series_season_query = """
                            SELECT 
                                date,
                                end_pti
                            FROM player_history
                            WHERE series ILIKE %s 
                            AND date >= %s 
                            AND date <= %s
                            ORDER BY date
                        """

                        series_pti_records = execute_query(
                            series_season_query,
                            [f"%{series_name}%", season_start_date, season_end_date],
                        )

                        if series_pti_records and len(series_pti_records) >= 2:
                            start_pti = series_pti_records[0]["end_pti"]
                            end_pti = series_pti_records[-1]["end_pti"]
                            season_pti_change = round(end_pti - start_pti, 1)
                            print(
                                f"[DEBUG] Season PTI change via series fallback: {start_pti} -> {end_pti} = {season_pti_change:+.1f}"
                            )

            except Exception as pti_season_error:
                print(
                    f"[DEBUG] Error calculating season PTI change: {pti_season_error}"
                )
                season_pti_change = "N/A"

        current_season = {
            "winRate": win_rate,
            "matches": total_matches,
            "wins": wins,
            "losses": losses,
            "ptiChange": season_pti_change,
        }

        # Build career stats from player_history table
        career_stats = get_career_stats_from_db(player_id)

        # Show career stats if they exist in the database
        # (Remove the logic that hides career stats when they match current season)

        # Player history (empty for now since we don't have PTI data)
        player_history = {"progression": "", "seasons": []}

        # Return the complete data structure expected by the template
        result = {
            "current_season": current_season,
            "court_analysis": court_analysis,
            "career_stats": career_stats,
            "player_history": player_history,
            "videos": {"match": [], "practice": []},
            "trends": {},
            "career_pti_change": "N/A",
            "current_pti": pti_data.get("current_pti", 0.0),
            "weekly_pti_change": pti_data.get("pti_change", 0.0),
            "pti_data_available": pti_data.get("pti_data_available", False),
            "error": None,
        }

        return result

    except Exception as e:
        print(f"Error getting player analysis: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "current_season": {
                "winRate": 0,
                "matches": 0,
                "wins": 0,
                "losses": 0,
                "ptiChange": "N/A",
            },
            "court_analysis": {
                "court1": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                "court2": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                "court3": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
                "court4": {"winRate": 0, "record": "0-0", "matches": 0, "topPartners": []},
            },
            "career_stats": {
                "winRate": 0,
                "matches": 0,
                "wins": 0,
                "losses": 0,
                "pti": "N/A",
            },
            "player_history": {"progression": "", "seasons": []},
            "videos": {"match": [], "practice": []},
            "trends": {},
            "career_pti_change": "N/A",
            "current_pti": None,
            "weekly_pti_change": None,
            "pti_data_available": False,
            "error": str(e),
        }


def get_mobile_availability_data(user):
    """Get availability data for mobile availability page using team_id for accurate filtering"""
    try:
        # Import database utilities at the top
        from database_utils import execute_query, execute_query_one
        
        # Get user's team information using session service
        from app.services.session_service import get_session_data_for_user
        
        user_email = user.get("email", "")
        session_data = get_session_data_for_user(user_email)
        
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
            
            # Get user's player associations directly from database
            fallback_query = """
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
                ORDER BY 
                    CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END,
                    p.team_id DESC
                LIMIT 1
            """
            fallback_result = execute_query_one(fallback_query, [user_email])
            
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
        
        simple_query = """
        SELECT 
            match_date as date, 
            match_time as time, 
            home_team, 
            away_team, 
            location
        FROM schedule 
        WHERE home_team_id = %s OR away_team_id = %s
        ORDER BY match_date ASC, match_time ASC
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
                    SELECT 
                        match_date as date, 
                        match_time as time, 
                        home_team, 
                        away_team, 
                        location
                    FROM schedule 
                    WHERE (home_team = %s OR away_team = %s)
                    AND league_id = %s
                    ORDER BY match_date ASC, match_time ASC
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
                # Add type field manually
                home_team = match.get('home_team', '')
                match['type'] = 'practice' if 'Practice' in home_team else 'match'
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
            
            match_data = {
                "date": formatted_date,
                "time": formatted_time,
                "location": match.get("location", ""),
                "home_team": match.get("home_team", ""),
                "away_team": match.get("away_team", ""),
                "type": match.get("type", "match")
            }
            formatted_matches.append(match_data)
            
            if match.get("type") == "practice":
                print(f"  ✓ Practice found: {match.get('home_team')} on {match.get('date')}")
            else:
                print(f"  ✓ Match found: {match.get('home_team')} vs {match.get('away_team')} on {match.get('date')}")
        
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
        
        # Get availability data for this player
        availability_data = {}
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
                                if not is_home:
                                    our_score, their_score = their_score, our_score

                                if our_score > their_score:
                                    match_team_points += 1
                                else:
                                    match_opponent_points += 1
                            except (ValueError, IndexError):
                                continue

                    # Bonus point for match win
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
                    court = match.get("court", "")
                    try:
                        court_num = (
                            int(court)
                            if court and court.strip()
                            else len(team_matches[team]["matches"]) + 1
                        )
                    except (ValueError, TypeError):
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

                    team_matches[team]["matches"].append(
                        {
                            "court": court_num,
                            "home_players": (
                                f"{home_player_1_name}/{home_player_2_name}"
                                if is_home
                                else f"{away_player_1_name}/{away_player_2_name}"
                            ),
                            "away_players": (
                                f"{away_player_1_name}/{away_player_2_name}"
                                if is_home
                                else f"{home_player_1_name}/{home_player_2_name}"
                            ),
                            "scores": match["scores"],
                            "won": (is_home and match["winner"] == "home")
                            or (not is_home and match["winner"] == "away"),
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
            user_league_id = user.get("league_id", "")

            # Use dynamic path based on league
            if user_league_id and not user_league_id.startswith("APTA"):
                # For non-APTA leagues, use league-specific path
                csv_path = os.path.join(
                    "data",
                    "leagues",
                    user_league_id,
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
    """Get team data for mobile my team page"""
    print(f"🚨 FUNCTION CALLED: get_mobile_team_data with user: {user}")
    try:
        # DEBUG: Start database debug FIRST
        print(f"[DEBUG DATABASE QUERY] Starting database debug at function start...")

        # Extract team name from user club and series (same logic as backup)
        club = user.get("club")
        series = user.get("series")

        # If club/series not in session, try to get from database using email
        if not club or not series:
            print(
                f"[DEBUG] Missing club/series in session, attempting database lookup..."
            )
            user_email = user.get("email")
            if user_email:
                user_lookup_query = """
                    SELECT u.email, u.first_name, u.last_name, u.league_context,
                           c.name as club_name, s.name as series_name, l.league_name, l.id as league_db_id
                    FROM users u 
                    JOIN user_player_associations upa ON u.id = upa.user_id
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id  
                    LEFT JOIN leagues l ON p.league_id = l.id
                    WHERE u.email = %s 
                    AND (u.league_context IS NULL OR p.league_id = u.league_context)
                    ORDER BY (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END)
                    LIMIT 1
                """
                user_data = execute_query_one(user_lookup_query, [user_email])
                if user_data:
                    club = user_data["club_name"]
                    series = user_data["series_name"]
                    print(f"[DEBUG] Found club/series from database: {club}/{series}")
                else:
                    print(f"[DEBUG] No user data found in database for {user_email}")

        if not club or not series:
            print(
                f"[DEBUG ERROR] User club or series not found: club={club}, series={series}"
            )
            print(f"[DEBUG ERROR] Session keys available: {list(user.keys())}")
            return {
                "team_data": None,
                "court_analysis": {},
                "top_players": [],
                "error": f"User club or series not found. Club: {club}, Series: {series}. Please check your profile settings.",
            }

        # Get team_id using proper database relationships instead of string construction
        league_id = user.get("league_id", "")

        # If league_id not in session, try to get from database using email
        if not league_id:
            print(
                f"[DEBUG] Missing league_id in session, attempting database lookup..."
            )
            user_email = user.get("email")
            if user_email:
                league_lookup_query = """
                    SELECT l.league_id, l.id as league_db_id, u.league_context
                    FROM users u 
                    JOIN user_player_associations upa ON u.id = upa.user_id
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    JOIN leagues l ON p.league_id = l.id
                    WHERE u.email = %s 
                    AND (u.league_context IS NULL OR p.league_id = u.league_context)
                    ORDER BY (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END)
                    LIMIT 1
                """
                league_data = execute_query_one(league_lookup_query, [user_email])
                if league_data:
                    league_id = league_data["league_id"]
                    print(f"[DEBUG] Found league_id from database: {league_id}")

        # Convert league_id to integer foreign key for database queries
        league_id_int = None
        if isinstance(league_id, str) and league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
                    print(
                        f"[DEBUG] get_mobile_team_data: Converted league_id '{league_id}' to integer: {league_id_int}"
                    )
                else:
                    print(
                        f"[WARNING] get_mobile_team_data: League '{league_id}' not found in leagues table"
                    )
                    return {
                        "team_data": None,
                        "court_analysis": {},
                        "top_players": [],
                        "error": f"League not found: {league_id}",
                    }
            except Exception as e:
                print(f"[DEBUG] get_mobile_team_data: Could not convert league ID: {e}")
                return {
                    "team_data": None,
                    "court_analysis": {},
                    "top_players": [],
                    "error": f"Failed to resolve league: {str(e)}",
                }
        elif isinstance(league_id, int):
            league_id_int = league_id
            print(
                f"[DEBUG] get_mobile_team_data: League_id already integer: {league_id_int}"
            )
        else:
            print(f"[DEBUG ERROR] No valid league_id found: {league_id}")
            return {
                "team_data": None,
                "court_analysis": {},
                "top_players": [],
                "error": f"No valid league found. Please check your profile settings.",
            }

        # Get the user's team using proper joins (much more reliable!)
        team_query = """
            SELECT t.id, t.team_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            WHERE c.name = %s 
            AND s.name = %s 
            AND l.id = %s
        """

        # SCALABLE: Use database-driven series name mapping service
        from utils.series_mapping_service import find_team_with_series_mapping

        # Try to find team using the series mapping service
        # This handles all league-specific naming conventions via database table
        team_record = find_team_with_series_mapping(
            club, series, league_id, league_id_int
        )

        if not team_record:
            print(
                f"[DEBUG] get_mobile_team_data: Team not found - club: {club}, series: {series}, league_id: {league_id_int}"
            )

            # Check if this is a league with no teams (data issue)
            league_teams_count_query = """
                SELECT 
                    (SELECT COUNT(*) FROM teams WHERE league_id = %s) as team_count,
                    l.league_name
                FROM leagues l
                WHERE l.id = %s
            """
            league_info = execute_query_one(
                league_teams_count_query, [league_id_int, league_id_int]
            )

            if league_info and league_info["team_count"] == 0:
                # League has no teams - this is a data issue
                error_msg = f'No team data available for {league_info["league_name"]} league.\n\n'
                error_msg += f"Your player profile is set up correctly, but team/match data has not been imported for this league yet.\n\n"
                error_msg += f'Team analysis will be available once match data is imported for {league_info["league_name"]}.'

                return {
                    "team_data": None,
                    "court_analysis": {},
                    "top_players": [],
                    "error": error_msg,
                }

            # Try to find similar teams to provide helpful error message
            similar_teams_query = """
                SELECT t.team_name, c.name as club, s.name as series, l.league_name
                FROM teams t
                JOIN clubs c ON t.club_id = c.id
                JOIN series s ON t.series_id = s.id
                JOIN leagues l ON t.league_id = l.id
                WHERE (c.name ILIKE %s OR s.name ILIKE %s OR t.team_name ILIKE %s)
                LIMIT 5
            """
            search_pattern = f"%{club}%"
            series_pattern = f"%{series}%"
            team_pattern = f"%{club}%{series}%"
            similar_teams = execute_query(
                similar_teams_query, [search_pattern, series_pattern, team_pattern]
            )

            error_msg = f"Team not found: {club} / {series}"
            if similar_teams:
                error_msg += f"\n\nSimilar teams found:"
                for team in similar_teams:
                    error_msg += f'\n- {team["team_name"]} ({team["club"]} / {team["series"]}, {team["league_name"]})'

            return {
                "team_data": None,
                "court_analysis": {},
                "top_players": [],
                "error": error_msg,
            }

        team_id = team_record["id"]
        team = team_record["team_name"]  # Use the actual team name from database

        print(
            f"[DEBUG] get_mobile_team_data: Found team_id={team_id}, team_name='{team}' for user {user.get('first_name')} {user.get('last_name')}"
        )

        # MORE DEBUG: Show that we reached this point
        print(f"[DEBUG DATABASE QUERY] About to query database for team: {team}")

        # Query team stats and matches from database
        # Note: execute_query and execute_query_one are already imported at module level

        # Get team stats
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
            WHERE team = %s
        """
        team_stats = execute_query_one(team_stats_query, [team])

        # Get team matches using team_id (faster and more accurate!)
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
                id
            FROM match_scores
            WHERE (home_team_id = %s OR away_team_id = %s)
            ORDER BY match_date DESC
        """
        team_matches = execute_query(matches_query, [team_id, team_id])

        # DEBUG: Raw database query to understand the data structure
        print(f"[DEBUG DATABASE QUERY] Starting database debug...")
        try:
            print(f"[DEBUG] Team: {team}, League ID Int: {league_id_int}")

            # Simple debug query first using team_id
            simple_query = "SELECT COUNT(*) as total FROM match_scores WHERE (home_team_id = %s OR away_team_id = %s)"
            if league_id_int:
                simple_query += " AND league_id = %s"
                total_count = execute_query_one(
                    simple_query, [team_id, team_id, league_id_int]
                )
            else:
                total_count = execute_query_one(simple_query, [team_id, team_id])

            print(f"[DEBUG] Total matches for {team}: {total_count['total']}")

            # Now try the detailed query using team_id
            if league_id_int:
                debug_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as formatted_date,
                        id,
                        home_team,
                        away_team,
                        winner,
                        scores
                    FROM match_scores
                    WHERE (home_team_id = %s OR away_team_id = %s)
                    AND league_id = %s
                    ORDER BY match_date DESC, id ASC
                    LIMIT 20
                """
                debug_matches = execute_query(debug_query, [team_id, team_id, league_id_int])
            else:
                debug_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as formatted_date,
                        id,
                        home_team,
                        away_team,
                        winner,
                        scores
                    FROM match_scores
                    WHERE (home_team_id = %s OR away_team_id = %s)
                    ORDER BY match_date DESC, id ASC
                    LIMIT 20
                """
                debug_matches = execute_query(debug_query, [team_id, team_id])

            print(f"[DEBUG] Raw matches from database (first 20):")
            for i, match in enumerate(debug_matches):
                print(
                    f"  {i+1}. ID={match['id']}, Date={match['formatted_date']}, {match['home_team']} vs {match['away_team']}"
                )
                print(f"      Winner={match['winner']}, Scores={match['scores']}")

            # Check for court columns
            print(f"[DEBUG] Checking match_scores table structure...")
            court_check_query = """
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = 'match_scores' 
                AND column_name ILIKE '%court%'
                ORDER BY column_name
            """
            court_columns = execute_query(court_check_query)

            if court_columns:
                print(
                    f"[DEBUG] Found court columns: {[(col['column_name'], col['data_type']) for col in court_columns]}"
                )

                # Sample actual court data
                court_cols = [col["column_name"] for col in court_columns]
                sample_query = f"""
                    SELECT id, TO_CHAR(match_date, 'DD-Mon-YY') as date, {', '.join(court_cols)}
                    FROM match_scores
                    WHERE (home_team_id = %s OR away_team_id = %s)
                    ORDER BY match_date DESC
                    LIMIT 5
                """
                if league_id_int:
                    sample_query = f"""
                        SELECT id, TO_CHAR(match_date, 'DD-Mon-YY') as date, {', '.join(court_cols)}
                        FROM match_scores
                        WHERE (home_team_id = %s OR away_team_id = %s) AND league_id = %s
                        ORDER BY match_date DESC
                        LIMIT 5
                    """
                    sample_data = execute_query(
                        sample_query, [team_id, team_id, league_id_int]
                    )
                else:
                    sample_data = execute_query(sample_query, [team_id, team_id])

                print(f"[DEBUG] Sample court data:")
                for row in sample_data:
                    court_vals = ", ".join(
                        [f"{col}={row.get(col)}" for col in court_cols]
                    )
                    print(f"  ID={row['id']}, Date={row['date']}: {court_vals}")
            else:
                print(f"[DEBUG] No court columns found in match_scores table")

        except Exception as e:
            print(f"[DEBUG ERROR] Database debug failed: {str(e)}")
            import traceback

            print(f"[DEBUG ERROR] Traceback: {traceback.format_exc()}")

        # Get user's player_id for partnership analysis
        player_id = user.get("tenniscores_player_id")
        if not player_id:
            print(f"[DEBUG] No tenniscores_player_id found for user: {user.get('email')}")

        # Calculate court analysis and top players
        court_analysis = {}
        top_players = []
        max_courts = 4  # Default number of courts

        # Import defaultdict at function level for use in court analysis
        from collections import defaultdict

        # Initialize variables that are used outside the conditional blocks
        player_stats = defaultdict(
            lambda: {"matches": 0, "wins": 0, "courts": {}, "partners": {}}
        )
        wins = 0  # Initialize wins counter

        if team_matches:

            # Group by date to understand court patterns
            matches_by_date = defaultdict(list)
            for match in team_matches:
                date = match.get("Date")
                matches_by_date[date].append(match)

            court_stats = {
                f"court{i}": {
                    "matches": 0,
                    "wins": 0,
                    "losses": 0,
                    "players": defaultdict(
                        lambda: {"matches": 0, "wins": 0, "losses": 0}
                    ),
                }
                for i in range(1, 5)
            }
            player_stats = defaultdict(
                lambda: {"matches": 0, "wins": 0, "courts": {}, "partners": {}}
            )

            # FIXED: Instead of artificial court assignments, show actual partnerships
            # Group partnerships by frequency and show real match data
            
            # Track actual partnerships from real matches
            actual_partnerships = defaultdict(lambda: {"matches": 0, "wins": 0, "losses": 0})
            
            # Process each match to get actual partnerships and calculate wins
            for match in team_matches:
                is_home = match.get("Home Team") == team
                winner = match.get("Winner") or ""
                won = (is_home and winner.lower() == "home") or (
                    not is_home and winner.lower() == "away"
                )
                team_won = (is_home and won) or (
                    not is_home and not won
                )
                
                # Count wins for overall team statistics
                if team_won:
                    wins += 1

                # Get all players from this match for roster stats
                if is_home:
                    team_player_1_id = match.get("Home Player 1")
                    team_player_2_id = match.get("Home Player 2")
                else:
                    team_player_1_id = match.get("Away Player 1")
                    team_player_2_id = match.get("Away Player 2")

                # Process each player's individual stats for the roster
                for player_id_current in [team_player_1_id, team_player_2_id]:
                    if player_id_current:
                        player_name = get_player_name_from_id(player_id_current)
                        if player_name:
                            # Initialize player stats if not exists
                            if player_name not in player_stats:
                                player_stats[player_name] = {
                                    "matches": 0,
                                    "wins": 0,
                                    "courts": {},
                                    "partners": {}
                                }
                            
                            # Update match count and wins
                            player_stats[player_name]["matches"] += 1
                            if team_won:
                                player_stats[player_name]["wins"] += 1
                            
                            # Assign court for this match (simplified court assignment)
                            # In a real system, this would use proper court assignment logic
                            # For now, we'll distribute players across courts based on match frequency
                            court_num = ((player_stats[player_name]["matches"] - 1) % 4) + 1
                            court_name = f"Court {court_num}"
                            
                            if court_name not in player_stats[player_name]["courts"]:
                                player_stats[player_name]["courts"][court_name] = {
                                    "matches": 0,
                                    "wins": 0
                                }
                            player_stats[player_name]["courts"][court_name]["matches"] += 1
                            if team_won:
                                player_stats[player_name]["courts"][court_name]["wins"] += 1
                            
                            # Track partner for this player
                            partner_id_current = team_player_2_id if player_id_current == team_player_1_id else team_player_1_id
                            if partner_id_current:
                                partner_name = get_player_name_from_id(partner_id_current)
                                if partner_name:
                                    if partner_name not in player_stats[player_name]["partners"]:
                                        player_stats[player_name]["partners"][partner_name] = {
                                            "matches": 0,
                                            "wins": 0
                                        }
                                    player_stats[player_name]["partners"][partner_name]["matches"] += 1
                                    if won:
                                        player_stats[player_name]["partners"][partner_name]["wins"] += 1

                # Get actual partner from this specific match (only if player_id is available)
                if player_id:
                    if is_home:
                        partner_id = (
                            match.get("Home Player 2")
                            if match.get("Home Player 1") == player_id
                            else match.get("Home Player 1")
                        )
                    else:
                        partner_id = (
                            match.get("Away Player 2")
                            if match.get("Away Player 1") == player_id
                            else match.get("Away Player 1")
                        )

                    if partner_id:
                        partner_name = get_player_name_from_id(partner_id)
                        if partner_name:
                            actual_partnerships[partner_name]["matches"] += 1
                            if won:
                                actual_partnerships[partner_name]["wins"] += 1
                            else:
                                actual_partnerships[partner_name]["losses"] += 1

            # Convert actual partnerships to sorted list by frequency
            partnership_list = []
            for partner_name, stats in actual_partnerships.items():
                if stats["matches"] > 0:
                    partner_win_rate = (
                        round((stats["wins"] / stats["matches"]) * 100, 1)
                        if stats["matches"] > 0
                        else 0
                    )
                    partnership_list.append({
                        "name": partner_name,
                        "matches": stats["matches"],
                        "wins": stats["wins"],
                        "losses": stats["losses"],
                        "winRate": partner_win_rate,
                    })

            # Sort by number of matches together (descending)
            partnership_list.sort(key=lambda p: p["matches"], reverse=True)

            # Build court_analysis using REAL court assignments (like analyze-me page)
            court_analysis = {}
            max_courts = 4  # Standard number of courts to display

            if team_matches:
                # FIXED: Use REAL court assignments based on match position within team matchup
                # Court Number = ROW_NUMBER() of match within same team matchup on same date
                
                # Initialize court stats for tracking real court performance
                court_stats = {
                    f"court{i}": {
                        "matches": 0,
                        "wins": 0,
                        "losses": 0,
                        "partners": defaultdict(lambda: {"matches": 0, "wins": 0, "losses": 0}),
                    }
                    for i in range(1, max_courts + 1)
                }
                
                # Process each match to determine ACTUAL court assignment
                # First, get ALL team matchups and their match counts for context
                all_team_matchups = {}
                for match in team_matches:
                    match_date = match.get("Date")
                    home_team = match.get("Home Team", "")
                    away_team = match.get("Away Team", "")
                    matchup_key = f"{match_date}|{home_team}|{away_team}"
                    
                    if matchup_key not in all_team_matchups:
                        # Get ALL matches for this team matchup on this date, filtered by team
                        if team_id:
                            # Filter by team_id for accurate court assignment
                            team_matchup_query = """
                                SELECT id
                                FROM match_scores 
                                WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                                AND home_team = %s 
                                AND away_team = %s
                                AND (home_team_id = %s OR away_team_id = %s)
                                ORDER BY id ASC
                            """
                            all_matches = execute_query(team_matchup_query, [match_date, home_team, away_team, team_id, team_id])
                        else:
                            # Fallback: no team filtering
                            team_matchup_query = """
                                SELECT id
                                FROM match_scores 
                                WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                                AND home_team = %s 
                                AND away_team = %s
                                ORDER BY id ASC
                            """
                            all_matches = execute_query(team_matchup_query, [match_date, home_team, away_team])
                        
                        all_team_matchups[matchup_key] = [m["id"] for m in all_matches]
                
                # Process each match to assign to correct court using analyze-me logic
                # First organize all matches by team matchup for proper court assignment
                matches_by_matchup = defaultdict(list)
                for match in team_matches:
                    match_date = match.get("Date")
                    home_team = match.get("Home Team", "")
                    away_team = match.get("Away Team", "")
                    matchup_key = f"{match_date}|{home_team}|{away_team}"
                    matches_by_matchup[matchup_key].append(match)

                # For each team matchup, sort matches and assign courts
                for matchup_key, matchup_matches in matches_by_matchup.items():
                    # Sort by match ID to ensure consistent court assignment
                    matchup_matches.sort(key=lambda m: m.get("id", 0))
                    
                    # Assign each match in this matchup to a court
                    for court_position, match in enumerate(matchup_matches, 1):
                        if court_position > max_courts:
                            court_position = ((court_position - 1) % max_courts) + 1
                        
                        court_key = f"court{court_position}"

                        # Determine if team won this match
                        is_home = match.get("Home Team") == team
                        winner = match.get("Winner") or ""
                        winner_is_home = winner.lower() == "home"
                        team_won = (is_home and winner_is_home) or (
                            not is_home and not winner_is_home
                        )

                        # Update court performance stats
                        court_stats[court_key]["matches"] += 1
                        if team_won:
                            court_stats[court_key]["wins"] += 1
                        else:
                            court_stats[court_key]["losses"] += 1

                        # Track REAL partnerships on REAL courts
                        if is_home:
                            player1_id = match.get("Home Player 1")
                            player2_id = match.get("Home Player 2")
                        else:
                            player1_id = match.get("Away Player 1")
                            player2_id = match.get("Away Player 2")

                        # Add both players to this specific court (not all courts)
                        for current_player_id in [player1_id, player2_id]:
                            if current_player_id:
                                player_name = get_player_name_from_id(current_player_id)
                                if player_name:
                                    # Track this player's performance on this specific court only
                                    court_stats[court_key]["partners"][player_name]["matches"] += 1
                                    if team_won:
                                        court_stats[court_key]["partners"][player_name]["wins"] += 1
                                    else:
                                        court_stats[court_key]["partners"][player_name]["losses"] += 1

                # Build court_analysis using REAL court performance data
                for i in range(1, max_courts + 1):
                    court_key = f"court{i}"
                    stat = court_stats[court_key]
                    
                    court_matches = stat["matches"]
                    court_wins = stat["wins"]
                    court_losses = stat["losses"]
                    court_win_rate = (
                        round((court_wins / court_matches) * 100, 1) if court_matches > 0 else 0
                    )

                    # Get ALL players with their REAL performance on this REAL court
                    all_court_players = []
                    for player_name, court_player_stats in stat["partners"].items():
                        if player_name and court_player_stats["matches"] > 0:
                            player_wins = court_player_stats["wins"]
                            player_losses = court_player_stats["losses"]
                            match_count = court_player_stats["matches"]
                            player_win_rate = (
                                round((player_wins / match_count) * 100, 1)
                                if match_count > 0
                                else 0
                            )

                            all_court_players.append(
                                {
                                    "name": player_name,
                                    "matches": match_count,
                                    "wins": player_wins,
                                    "losses": player_losses,
                                    "winRate": player_win_rate,
                                }
                            )

                    # Sort by number of matches on this court (descending), then by win rate
                    all_court_players.sort(key=lambda p: (p["matches"], p["winRate"]), reverse=True)

                    court_analysis[court_key] = {
                        "winRate": court_win_rate,
                        "record": f"{court_wins}-{court_losses}",
                        "topPartners": all_court_players,  # ALL players on this court
                    }
            else:
                # If no matches, show empty courts
                for i in range(1, max_courts + 1):
                    court_key = f"court{i}"
                    court_analysis[court_key] = {
                        "winRate": 0,
                        "record": "0-0",
                        "topPartners": [],
                    }

        # Build top_players list
        top_players = []
        for name, stats in player_stats.items():
            # Show all players regardless of match count
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
            for partner, pstats in stats["partners"].items():
                if (
                    pstats["matches"] >= 3
                ):  # Require at least 3 matches for meaningful partnership
                    rate = (
                        round((pstats["wins"] / pstats["matches"]) * 100, 1)
                        if pstats["matches"] > 0
                        else 0
                    )
                    if rate >= 70.0:  # Must have 70% or greater win rate for best partner
                        if rate > best_partner_rate or (
                            rate == best_partner_rate and pstats["matches"] > 0
                        ):
                            best_partner_rate = rate
                            best_partner = partner

            # Removed temporary debug code for Andrew Franger
            
            top_players.append(
                {
                    "name": name,
                    "matches": stats["matches"],
                    "win_rate": win_rate,
                    "best_court": best_court or "N/A",
                    "best_partner": best_partner if best_partner else "N/A",
                }
            )

        top_players = sorted(top_players, key=lambda x: -x["matches"])

        # Build team stats
        if team_stats:
            # Calculate percentages safely
            matches_won = team_stats.get("matches_won", 0)
            matches_lost = team_stats.get("matches_lost", 0)
            matches_total = matches_won + matches_lost
            matches_pct = (
                f"{round((matches_won / matches_total) * 100, 1)}%"
                if matches_total > 0
                else "0%"
            )

            lines_won = team_stats.get("lines_won", 0)
            lines_lost = team_stats.get("lines_lost", 0)
            lines_total = lines_won + lines_lost
            lines_pct = (
                f"{round((lines_won / lines_total) * 100, 1)}%"
                if lines_total > 0
                else "0%"
            )

            sets_won = team_stats.get("sets_won", 0)
            sets_lost = team_stats.get("sets_lost", 0)
            sets_total = sets_won + sets_lost
            sets_pct = (
                f"{round((sets_won / sets_total) * 100, 1)}%"
                if sets_total > 0
                else "0%"
            )

            games_won = team_stats.get("games_won", 0)
            games_lost = team_stats.get("games_lost", 0)
            games_total = games_won + games_lost
            games_pct = (
                f"{round((games_won / games_total) * 100, 1)}%"
                if games_total > 0
                else "0%"
            )

            team_data = {
                "team": team,
                "points": team_stats.get("points", 0),
                "matches": {
                    "won": matches_won,
                    "lost": matches_lost,
                    "percentage": matches_pct,
                },
                "lines": {
                    "won": lines_won,
                    "lost": lines_lost,
                    "percentage": lines_pct,
                },
                "sets": {"won": sets_won, "lost": sets_lost, "percentage": sets_pct},
                "games": {
                    "won": games_won,
                    "lost": games_lost,
                    "percentage": games_pct,
                },
            }
        else:
            team_data = {
                "team": team,
                "points": 0,
                "matches": {"won": 0, "lost": 0, "percentage": "0%"},
                "lines": {"won": 0, "lost": 0, "percentage": "0%"},
                "sets": {"won": 0, "lost": 0, "percentage": "0%"},
                "games": {"won": 0, "lost": 0, "percentage": "0%"},
            }

        return {
            "team_data": team_data,
            "court_analysis": court_analysis,
            "top_players": top_players,
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


def get_teams_players_data(user):
    """Get teams and players data for mobile interface - filtered by user's league"""
    try:
        from flask import request

        # Get team parameter from request
        team = request.args.get("team")

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

        # Get all teams in user's league - only filter if we have a valid league_id
        if league_id_int:
            teams_query = """
                SELECT DISTINCT team
                FROM series_stats
                WHERE league_id = %s
                ORDER BY team
            """
            all_teams = [
                row["team"] for row in execute_query(teams_query, [league_id_int])
            ]
        else:
            teams_query = """
                SELECT DISTINCT team
                FROM series_stats
                ORDER BY team
            """
            all_teams = [row["team"] for row in execute_query(teams_query)]

        if not team or team not in all_teams:
            # No team selected or invalid team
            return {
                "team_analysis_data": None,
                "all_teams": all_teams,
                "selected_team": None,
            }

        # Get team stats
        if league_id_int:
            team_stats_query = """
                SELECT *
                FROM series_stats
                WHERE team = %s AND league_id = %s
            """
            team_stats = execute_query_one(team_stats_query, [team, league_id_int])
        else:
            team_stats_query = """
                SELECT *
                FROM series_stats
                WHERE team = %s
            """
            team_stats = execute_query_one(team_stats_query, [team])

        # Get team matches
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
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                ORDER BY match_date DESC
            """
            team_matches = execute_query(matches_query, [team, team, league_id_int])
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
                WHERE (home_team = %s OR away_team = %s)
                ORDER BY match_date DESC
            """
            team_matches = execute_query(matches_query, [team, team])

        # Calculate team analysis
        team_analysis_data = calculate_team_analysis_mobile(
            team_stats, team_matches, team
        )

        return {
            "team_analysis_data": team_analysis_data,
            "all_teams": all_teams,
            "selected_team": team,
        }

    except Exception as e:
        print(f"Error getting teams players data: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return {
            "team_analysis_data": None,
            "all_teams": [],
            "selected_team": None,
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


def calculate_team_analysis_mobile(team_stats, team_matches, team):
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
            winner_is_home = match.get("Winner", "").lower() == "home"
            team_won = (is_home and winner_is_home) or (
                not is_home and not winner_is_home
            )

            # Get the scores
            scores = match.get("Scores", "").split(", ")
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
        if team_dates:
            # Get all matches on those dates to determine correct court assignments
            all_matches_on_dates = execute_query(
                """
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
                    ms.away_player_2_id as "Away Player 2"
                FROM match_scores ms
                WHERE ms.match_date = ANY(%s)
                ORDER BY ms.match_date ASC, ms.id ASC
            """,
                (team_dates,),
            )

            # Group matches by date and team matchup
            matches_by_date_and_teams = defaultdict(lambda: defaultdict(list))
            for match in all_matches_on_dates:
                date = match.get("Date")
                home_team = match.get("Home Team", "")
                away_team = match.get("Away Team", "")
                team_matchup = f"{home_team} vs {away_team}"
                matches_by_date_and_teams[date][team_matchup].append(match)

            # Initialize court stats for 4 courts
            for i in range(1, 5):
                court_name = f"Court {i}"
                court_matches = []

                # Find matches for this court using correct logic
                for match in team_matches:
                    match_date = match.get("Date")
                    home_team = match.get("Home Team", "")
                    away_team = match.get("Away Team", "")
                    team_matchup = f"{home_team} vs {away_team}"

                    # Find this specific match in the grouped data
                    team_day_matches = matches_by_date_and_teams[match_date][
                        team_matchup
                    ]

                    # Check if this match is assigned to court i
                    for j, team_match in enumerate(team_day_matches, 1):
                        # Match by checking if it's the same match (by players)
                        if (
                            match.get("Home Player 1")
                            == team_match.get("Home Player 1")
                            and match.get("Home Player 2")
                            == team_match.get("Home Player 2")
                            and match.get("Away Player 1")
                            == team_match.get("Away Player 1")
                            and match.get("Away Player 2")
                            == team_match.get("Away Player 2")
                        ):
                            if j == i:  # This match belongs to court i
                                court_matches.append(match)
                            break

                wins = losses = 0
                player_win_counts = {}

                for match in court_matches:
                    is_home = match.get("Home Team") == team
                    winner_is_home = match.get("Winner", "").lower() == "home"
                    team_won = (is_home and winner_is_home) or (
                        not is_home and not winner_is_home
                    )

                    if team_won:
                        wins += 1
                    else:
                        losses += 1

                    players = (
                        [match.get("Home Player 1"), match.get("Home Player 2")]
                        if is_home
                        else [match.get("Away Player 1"), match.get("Away Player 2")]
                    )
                    for p in players:
                        if not p:
                            continue
                        if p not in player_win_counts:
                            player_win_counts[p] = {"matches": 0, "wins": 0}
                        player_win_counts[p]["matches"] += 1
                        if team_won:
                            player_win_counts[p]["wins"] += 1

                win_rate = (
                    round((wins / (wins + losses) * 100), 1)
                    if (wins + losses) > 0
                    else 0
                )
                record = f"{wins}-{losses} ({win_rate}%)"

                # Top players by win rate (show all players for this court)
                key_players = sorted(
                    [
                        {
                            "name": get_player_name_from_id(p),
                            "win_rate": round((d["wins"] / d["matches"]) * 100, 1),
                            "matches": d["matches"],
                        }
                        for p, d in player_win_counts.items()
                    ],
                    key=lambda x: -x["win_rate"],
                )[:3]

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
                            f"{kp['name']} ({kp['win_rate']}% in {kp['matches']} matches)"
                            for kp in key_players
                        ]
                    )
                    summary = f"This court has shown {perf} with a {win_rate}% win rate. Key contributors: {contributors}."
                else:
                    summary = (
                        f"This court has shown {perf} with a {win_rate}% win rate."
                    )

                court_analysis[court_name] = {
                    "record": record,
                    "win_rate": win_rate,
                    "key_players": key_players,
                    "summary": summary,
                }

        # Top Players Table
        player_stats = defaultdict(
            lambda: {"matches": 0, "wins": 0, "courts": {}, "partners": {}}
        )

        if team_dates:
            for match in team_matches:
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
                winner_is_home = match.get("Winner", "").lower() == "home"
                team_won = (is_home and winner_is_home) or (
                    not is_home and not winner_is_home
                )

                # Determine correct court assignment for this match
                match_date = match.get("Date")
                home_team = match.get("Home Team", "")
                away_team = match.get("Away Team", "")
                team_matchup = f"{home_team} vs {away_team}"

                team_day_matches = matches_by_date_and_teams[match_date][team_matchup]
                court_num = None

                # Find the position of this match within the team's matches
                for i, team_match in enumerate(team_day_matches, 1):
                    if (
                        match.get("Home Player 1") == team_match.get("Home Player 1")
                        and match.get("Home Player 2")
                        == team_match.get("Home Player 2")
                        and match.get("Away Player 1")
                        == team_match.get("Away Player 1")
                        and match.get("Away Player 2")
                        == team_match.get("Away Player 2")
                    ):
                        court_num = min(i, 4)  # Cap at 4 courts
                        break

                if court_num is None:
                    continue  # Skip if court can't be determined

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
                    court = f"Court {court_num}"
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
                    pstats["matches"] >= 3
                ):  # Require at least 3 matches for meaningful partnership
                    rate = (
                        round((pstats["wins"] / pstats["matches"]) * 100, 1)
                        if pstats["matches"] > 0
                        else 0
                    )
                    print(f"    -> Qualified: {rate}% win rate")
                    if rate >= 70.0:  # Must have 70% or greater win rate for best partner
                        if rate > best_partner_rate or (
                            rate == best_partner_rate and pstats["matches"] > 0
                        ):
                            best_partner_rate = rate
                            best_partner = get_player_name_from_id(partner_id)
                            print(f"    -> NEW BEST: {best_partner} with {rate}%")
                    else:
                        print(f"    -> Win rate too low ({rate}% < 70%)")
                else:
                    print(f"    -> Not enough matches ({pstats['matches']} < 3)")
            print(f"  Final best partner: {best_partner} ({best_partner_rate}%)")

            top_players.append(
                {
                    "name": player_name,
                    "matches": stats["matches"],
                    "win_rate": win_rate,
                    "best_court": best_court or "N/A",
                    "best_partner": best_partner if best_partner else "N/A",
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
                    t.team_name
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
            current_year = current_date.year
            current_month = current_date.month

            # Determine season year based on current date
            if current_month >= 8:  # Aug-Dec: current season
                season_start_year = current_year
            else:  # Jan-Jul: previous season
                season_start_year = current_year - 1

            season_start_date = date(season_start_year, 8, 1)
            season_end_date = date(season_start_year + 1, 7, 31)

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
                        "team_name": player.get("team_name", ""),
                    }
                )

                print(
                    f"[DEBUG] {player_name} ({player.get('team_name', 'No team')}): {total_matches} matches ({wins}-{losses}) in current season"
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
        else:
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
    Returns empty list if no future matches are scheduled.
    """
    try:
        print("[DEBUG] Checking for actual future matches in schedule table...")
        
        if league_id_int:
            future_matches_query = """
                SELECT 
                    home_team,
                    away_team,
                    match_date,
                    match_time,
                    location
                FROM schedule
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
                AND match_date > CURRENT_DATE
                ORDER BY match_date, match_time
            """
            future_matches = execute_query(future_matches_query, [team, team, league_id_int])
        else:
            future_matches_query = """
                SELECT 
                    home_team,
                    away_team,
                    match_date,
                    match_time,
                    location
                FROM schedule
                WHERE (home_team = %s OR away_team = %s)
                AND match_date > CURRENT_DATE
                ORDER BY match_date, match_time
            """
            future_matches = execute_query(future_matches_query, [team, team])

        print(f"[DEBUG] Found {len(future_matches)} actual future matches")
        return future_matches

    except Exception as e:
        print(f"[ERROR] Getting actual future matches: {str(e)}")
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
