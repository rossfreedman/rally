import json
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd
from rapidfuzz import fuzz

from database_utils import execute_query, execute_query_one
from utils.logging import log_user_activity
from utils.match_utils import names_match, normalize_name

logger = logging.getLogger(__name__)


def get_player_analysis_by_name(player_name):
    """
    Returns the player analysis data for the given player name, as a dict.
    This function parses the player_name string into first and last name (if possible),
    then calls get_player_analysis with a constructed user dict.
    Handles single-word names gracefully.
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
            "error": "Invalid player name.",
        }
    # Try to split into first and last name
    parts = player_name.strip().split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = " ".join(parts[1:])
    else:
        # If only one part, use as both first and last name
        first_name = parts[0]
        last_name = parts[0]
    # Call get_player_analysis with constructed user dict
    user_dict = {"first_name": first_name, "last_name": last_name}
    return get_player_analysis(user_dict)


def get_player_analysis(user):
    """
    Returns the player analysis data for the given user, as a dict.
    Uses match_history.json for current season stats and court analysis,
    and player_history.json for career stats and player history.
    Always returns all expected keys, even if some are None or empty.
    """

    # For now, return a basic structure to avoid breaking the application
    # This will need to be fully implemented by moving the complex logic from server.py
    return {
        "current_season": {
            "winRate": 0,
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "ptiChange": "N/A",
        },
        "court_analysis": {
            "court1": {"winRate": 0, "record": "0-0", "topPartners": []},
            "court2": {"winRate": 0, "record": "0-0", "topPartners": []},
            "court3": {"winRate": 0, "record": "0-0", "topPartners": []},
            "court4": {"winRate": 0, "record": "0-0", "topPartners": []},
        },
        "career_stats": {"winRate": 0, "matches": 0, "pti": "N/A"},
        "player_history": {"progression": "", "seasons": []},
        "videos": {"match": [], "practice": []},
        "trends": {},
        "career_pti_change": "N/A",
        "error": None,
    }


def get_season_from_date(date_str):
    """Get season string from date"""
    try:
        if isinstance(date_str, str):
            dt = datetime.strptime(date_str, "%m/%d/%Y")
        else:
            dt = date_str

        if dt.month >= 8:  # August or later
            start_year = dt.year
            end_year = dt.year + 1
        else:
            start_year = dt.year - 1
            end_year = dt.year
        return f"{start_year}-{end_year}"
    except:
        return None


def build_season_history(player):
    """Build season history from player matches"""
    matches = player.get("matches", [])
    if not matches:
        return []

    # Helper to parse date robustly
    def parse_date(d):
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(d, fmt)
            except Exception:
                continue
        return d  # fallback to string if parsing fails

    # Group matches by season
    season_matches = defaultdict(list)
    for m in matches:
        season = get_season_from_date(m.get("date", ""))
        if season:
            season_matches[season].append(m)

    seasons = []
    for season, ms in season_matches.items():
        ms_sorted = sorted(ms, key=lambda x: parse_date(x.get("date", "")))
        pti_start = ms_sorted[0].get("end_pti", None)
        pti_end = ms_sorted[-1].get("end_pti", None)
        series = ms_sorted[0].get("series", "")
        trend = (
            (pti_end - pti_start)
            if pti_start is not None and pti_end is not None
            else None
        )

        # Round trend to 1 decimal
        if trend is not None:
            trend_rounded = round(trend, 1)
            trend_str = (
                f"+{trend_rounded}" if trend_rounded >= 0 else str(trend_rounded)
            )
        else:
            trend_str = ""

        seasons.append(
            {
                "season": season,
                "series": series,
                "ptiStart": pti_start,
                "ptiEnd": pti_end,
                "trend": trend_str,
            }
        )

    # Sort by season (descending)
    seasons.sort(key=lambda s: s["season"], reverse=True)
    return seasons


def search_players_with_fuzzy_logic(first_name_query, last_name_query):
    """Search for players using fuzzy logic matching - FIXED: Uses database instead of JSON"""
    try:
        from database_utils import execute_query
        
        results = []

        # FIXED: Search players in database instead of JSON
        try:
            # Get all players from database with basic info
            players_query = """
                SELECT p.first_name, p.last_name, p.pti,
                       s.name as series_name, c.name as club_name,
                       l.league_id
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE p.is_active = true
                ORDER BY p.first_name, p.last_name
            """
            
            players_data = execute_query(players_query)

            for player in players_data:
                first_name = player.get("first_name", "")
                last_name = player.get("last_name", "")

                # Calculate fuzzy match scores
                first_score = (
                    fuzz.partial_ratio(first_name_query.lower(), first_name.lower())
                    if first_name_query
                    else 100
                )
                last_score = (
                    fuzz.partial_ratio(last_name_query.lower(), last_name.lower())
                    if last_name_query
                    else 100
                )

                # Only include if both scores are reasonably high
                if first_score >= 70 and last_score >= 70:
                    full_name = f"{first_name} {last_name}"
                    results.append(
                        {
                            "name": full_name,
                            "source": "players",
                            "match_score": (first_score + last_score) / 2,
                            "series": player.get("series_name", ""),
                            "club": player.get("club_name", ""),
                            "pti": player.get("pti", "N/A"),
                            "league": player.get("league_id", ""),
                        }
                    )
        except Exception as e:
            print(f"Error searching players database: {str(e)}")

        # FIXED: Search player history in database instead of JSON
        try:
            # Get recent PTI data from player_history table
            history_query = """
                SELECT p.first_name, p.last_name, ph.end_pti, ph.series
                FROM player_history ph
                JOIN players p ON ph.player_id = p.id
                WHERE ph.date = (
                    SELECT MAX(date) 
                    FROM player_history ph2 
                    WHERE ph2.player_id = ph.player_id
                )
                GROUP BY p.first_name, p.last_name, ph.end_pti, ph.series
            """
            
            history_data = execute_query(history_query)

            for player in history_data:
                first_name = player.get("first_name", "")
                last_name = player.get("last_name", "")
                full_name = f"{first_name} {last_name}"

                # Calculate fuzzy match scores
                first_score = (
                    fuzz.partial_ratio(first_name_query.lower(), first_name.lower())
                    if first_name_query
                    else 100
                )
                last_score = (
                    fuzz.partial_ratio(last_name_query.lower(), last_name.lower())
                    if last_name_query
                    else 100
                )

                # Only include if both scores are reasonably high and not already in results
                if first_score >= 70 and last_score >= 70:
                    # Check if already in results from players query
                    already_exists = any(
                        r["name"].lower() == full_name.lower() for r in results
                    )
                    if not already_exists:
                        results.append(
                            {
                                "name": full_name,
                                "source": "history",
                                "match_score": (first_score + last_score) / 2,
                                "series": player.get("series", ""),
                                "club": "",  # Not available in history data
                                "pti": player.get("end_pti", "N/A"),
                                "league": "",  # Would need join to get this
                            }
                        )
        except Exception as e:
            print(f"Error searching player history database: {str(e)}")

        # Sort by match score (descending) and limit results
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:20]  # Limit to top 20 results

    except Exception as e:
        print(f"Error in fuzzy player search: {str(e)}")
        return []


def find_player_in_history(user, player_history=None):
    """
    Find a player in the player history data based on user information.
    FIXED: Uses database instead of JSON, with player ID lookup for reliability.
    """
    try:
        from database_utils import execute_query, execute_query_one
        
        # FIXED: Use player ID from session for reliable identification
        player_id = user.get("tenniscores_player_id")
        user_league_id = user.get("league_id", "")

        if player_id:
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

            # Get player's database ID first
            if league_id_int:
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

            if player_db_data:
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

                return player_record

        # FALLBACK: If no player ID, try name-based search (as backup only)
        first_name = user.get("first_name", "").strip()
        last_name = user.get("last_name", "").strip()

        if not first_name or not last_name:
            return None

        # Search by name in database
        name_search_query = """
            SELECT id, first_name, last_name, pti 
            FROM players 
            WHERE LOWER(first_name) = LOWER(%s) AND LOWER(last_name) = LOWER(%s)
        """
        
        if league_id_int:
            name_search_query += " AND league_id = %s"
            player_db_data = execute_query_one(name_search_query, [first_name, last_name, league_id_int])
        else:
            player_db_data = execute_query_one(name_search_query, [first_name, last_name])
            
        if player_db_data:
            player_db_id = player_db_data["id"]

            # Get PTI history
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

            return player_record

        return None

    except Exception as e:
        print(f"Error finding player in history: {str(e)}")
        return None


def get_players_by_league_and_series_id(league_id, series_id, club_name=None, team_id=None):
    """
    Get players for a specific league and series using direct series_id lookup
    OPTIMIZED: Uses series_id directly instead of inefficient string name matching

    Args:
        league_id (str): League identifier (e.g., 'APTA_CHICAGO', 'NSTF')
        series_id (int): Series ID for direct database lookup
        club_name (str, optional): Club name for additional filtering
        team_id (int/str, optional): Team ID for team-specific filtering (preferred over club_name)

    Returns:
        list: List of player dictionaries with stats and position preference
    """
    try:
        base_query = """
            SELECT DISTINCT p.tenniscores_player_id, p.first_name, p.last_name,
                   p.club_id, p.series_id, p.team_id, c.name as club_name, s.name as series_name,
                   l.league_name, l.league_id, p.pti, p.wins, p.losses, p.win_percentage,
                   u.ad_deuce_preference, u.dominant_hand
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            LEFT JOIN users u ON upa.user_id = u.id
            WHERE l.league_id = %(league_id)s 
            AND p.is_active = true
            AND p.series_id = %(series_id)s
        """

        params = {"league_id": league_id, "series_id": series_id}
        print(f"[DEBUG] Direct series_id query: series_id={series_id}, league_id={league_id}")

        # FIXED: Prioritize team_id filtering over club_name filtering
        if team_id:
            # Use team_id for precise team filtering (preferred method)
            try:
                team_id_int = int(team_id)
                base_query += " AND p.team_id = %(team_id)s"
                params["team_id"] = team_id_int
                print(f"[DEBUG] Using team_id {team_id_int} for team filtering")
            except (ValueError, TypeError):
                print(f"[WARNING] Invalid team_id '{team_id}', falling back to club filtering")
                # Fallback to club filtering if team_id is invalid
                if club_name:
                    base_query += " AND c.name = %(club_name)s"
                    params["club_name"] = club_name
        elif club_name:
            # Use club filtering only if no team_id provided
            base_query += " AND c.name = %(club_name)s"
            params["club_name"] = club_name
            print(f"[DEBUG] Using club_name '{club_name}' for filtering")

        base_query += " ORDER BY p.last_name, p.first_name"

        players = execute_query(base_query, params)
        print(f"[DEBUG] Direct ID query found {len(players)} players")

        # Format for API response
        formatted_players = []
        for player in players:
            # Calculate record from match_scores table for accurate data
            # Convert league_id string to integer for match_scores lookup
            league_id_int = None
            if player.get("league_id"):
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [player["league_id"]]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                except Exception:
                    pass
            
            player_record = calculate_player_record_from_match_scores(
                player["tenniscores_player_id"], 
                league_id=league_id_int,
                team_id=player.get("team_id")
            )
            
            # Use calculated record instead of stored values
            wins = player_record["wins"]
            losses = player_record["losses"]
            win_rate = player_record["win_rate"]

            # Get preferences from database, default to None if not set
            position_preference = player.get("ad_deuce_preference")
            hand_preference = player.get("dominant_hand")

            formatted_players.append(
                {
                    "name": f"{player['first_name']} {player['last_name']}",
                    "player_id": player["tenniscores_player_id"],
                    "series": player["series_name"],
                    "club": player["club_name"],
                    "league": player["league_id"],
                    "pti": player.get("pti"),
                    "rating": player.get("pti"),  # Alias for pti
                    "wins": wins,
                    "losses": losses,
                    "winRate": win_rate,
                    "position_preference": position_preference,  # Ad/Deuce preference
                    "hand_preference": hand_preference,  # Lefty/Righty preference
                }
            )

        return formatted_players

    except Exception as e:
        logger.error(
            f"Error fetching players for league {league_id}, series_id {series_id}: {e}"
        )
        return []


def get_players_by_league_and_series(league_id, series_name, club_name=None, team_id=None):
    """
    Get players for a specific league and series, optionally filtered by club or team
    FIXED: Uses series_id and team_id lookups instead of unreliable string name matching

    Args:
        league_id (str): League identifier (e.g., 'APTA_CHICAGO', 'NSTF')
        series_name (str): Series name for filtering (will be converted to series_id)
        club_name (str, optional): Club name for additional filtering
        team_id (int/str, optional): Team ID for team-specific filtering (preferred over club_name)

    Returns:
        list: List of player dictionaries with stats and position preference
    """
    try:
        from utils.series_mapping_service import get_database_name
        
        base_query = """
            SELECT DISTINCT p.tenniscores_player_id, p.first_name, p.last_name,
                   p.club_id, p.series_id, c.name as club_name, s.name as series_name,
                   l.league_name, l.league_id, p.pti, p.wins, p.losses, p.win_percentage,
                   u.ad_deuce_preference, u.dominant_hand
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            LEFT JOIN users u ON upa.user_id = u.id
            WHERE l.league_id = %(league_id)s 
            AND p.is_active = true
        """

        params = {"league_id": league_id}

        # FIXED: Convert series_name to series_id for reliable matching
        if series_name:
            # First, try to get the correct database series name using our mapping service
            database_series_name = get_database_name(series_name)
            
            # If mapping fails, try using the series_name as-is (might already be database format)
            if not database_series_name:
                database_series_name = series_name
                print(f"[DEBUG] No mapping found for '{series_name}', using as-is")
            else:
                print(f"[DEBUG] Mapped '{series_name}' -> '{database_series_name}'")
            
            # Get the series_id from the database
            series_query = """
                SELECT s.id as series_id
                FROM series s
                WHERE s.name = %(database_series_name)s
                LIMIT 1
            """
            series_result = execute_query_one(series_query, {"database_series_name": database_series_name})
            
            if series_result:
                # Use series_id for exact matching instead of string name matching
                base_query += " AND p.series_id = %(series_id)s"
                params["series_id"] = series_result["series_id"]
                print(f"[DEBUG] Using series_id {series_result['series_id']} for series '{series_name}' -> '{database_series_name}'")
            else:
                # Final fallback: try direct name matching with original series_name
                base_query += " AND s.name = %(series_name)s"
                params["series_name"] = series_name
                print(f"[DEBUG] No series_id found, fallback to direct name matching for '{series_name}'")

        # FIXED: Prioritize team_id filtering over club_name filtering
        if team_id:
            # Use team_id for precise team filtering (preferred method)
            try:
                team_id_int = int(team_id)
                base_query += " AND p.team_id = %(team_id)s"
                params["team_id"] = team_id_int
                print(f"[DEBUG] Using team_id {team_id_int} for team filtering")
            except (ValueError, TypeError):
                print(f"[WARNING] Invalid team_id '{team_id}', falling back to club filtering")
                # Fallback to club filtering if team_id is invalid
                if club_name:
                    base_query += " AND c.name = %(club_name)s"
                    params["club_name"] = club_name
        elif club_name:
            # Use club filtering only if no team_id provided
            base_query += " AND c.name = %(club_name)s"
            params["club_name"] = club_name
            print(f"[DEBUG] Using club_name '{club_name}' for filtering")

        base_query += " ORDER BY p.last_name, p.first_name"

        players = execute_query(base_query, params)

        # Format for API response
        formatted_players = []
        for player in players:
            # Calculate win rate
            wins = player.get("wins", 0) or 0
            losses = player.get("losses", 0) or 0
            total_matches = wins + losses
            win_rate = (
                f"{(wins / total_matches * 100):.1f}%" if total_matches > 0 else "0.0%"
            )

            # Get preferences from database, default to None if not set
            position_preference = player.get("ad_deuce_preference")
            hand_preference = player.get("dominant_hand")

            formatted_players.append(
                {
                    "name": f"{player['first_name']} {player['last_name']}",
                    "player_id": player["tenniscores_player_id"],
                    "series": player["series_name"],
                    "club": player["club_name"],
                    "league": player["league_id"],
                    "pti": player.get("pti"),
                    "rating": player.get("pti"),  # Alias for pti
                    "wins": wins,
                    "losses": losses,
                    "winRate": win_rate,
                    "position_preference": position_preference,  # Ad/Deuce preference
                    "hand_preference": hand_preference,  # Lefty/Righty preference
                }
            )

        return formatted_players

    except Exception as e:
        logger.error(
            f"Error fetching players for league {league_id}, series {series_name}: {e}"
        )
        return []


def get_player_by_tenniscores_id(tenniscores_player_id, league_id=None):
    """
    Get player information by Tenniscores Player ID

    Args:
        tenniscores_player_id (str): Tenniscores Player ID
        league_id (str, optional): League to filter by for multi-league players

    Returns:
        dict|None: Player information or None if not found
    """
    try:
        query = """
            SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
                   p.club_id, p.series_id, c.name as club_name, 
                   s.name as series_name, l.league_name, l.league_id
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %(player_id)s
            AND p.is_active = true
        """

        params = {"player_id": tenniscores_player_id}

        if league_id:
            query += " AND l.league_id = %(league_id)s"
            params["league_id"] = league_id

        result = execute_query_one(query, params)

        if result:
            return {
                "id": result["id"],
                "tenniscores_player_id": result["tenniscores_player_id"],
                "first_name": result["first_name"],
                "last_name": result["last_name"],
                "club_name": result["club_name"],
                "series_name": result["series_name"],
                "league_id": result["league_id"],
                "league_name": result["league_name"],
            }
        return None

    except Exception as e:
        logger.error(f"Error fetching player {tenniscores_player_id}: {e}")
        return None


def find_player_in_history(user, player_history_data):
    """
    Find a user's player record in the player history data

    Args:
        user (dict): User session data with first_name, last_name, league_id
        player_history_data (list): List of player history records

    Returns:
        dict|None: Player history record or None if not found
    """
    user_name = f"{user['first_name']} {user['last_name']}"
    user_league_id = user.get("league_id")

    # Helper function to normalize names for comparison
    def normalize(name):
        return name.lower().strip().replace(",", "").replace(".", "")

    target_normalized = normalize(user_name)

    for player in player_history_data:
        # Check league match first
        player_league = player.get("League", player.get("league_id"))
        if user_league_id and player_league != user_league_id:
            continue

        # Check name match
        if normalize(player.get("name", "")) == target_normalized:
            return player

    return None


def get_team_players_by_team_id(team_id, user_league_id):
    """
    Get all players for a specific team using match history and database

    Args:
        team_id (str): Team identifier
        user_league_id (str): User's league for filtering

    Returns:
        list: List of team players with stats
    """
    # This would require loading match history to find team players
    # For now, return empty list - this needs match history integration
    logger.warning(
        f"get_team_players_by_team_id not fully implemented for team {team_id}"
    )
    return []


def search_players_by_name(search_term, league_id=None, limit=20):
    """
    Search players by name across leagues

    Args:
        search_term (str): Name search term
        league_id (str, optional): Limit to specific league
        limit (int): Maximum number of results

    Returns:
        list: Matching players
    """
    try:
        query = """
            SELECT DISTINCT p.tenniscores_player_id, p.first_name, p.last_name,
                   c.name as club_name, s.name as series_name, l.league_id
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.is_active = true
            AND (LOWER(p.first_name || ' ' || p.last_name) LIKE LOWER(%(search)s)
                 OR LOWER(p.last_name || ' ' || p.first_name) LIKE LOWER(%(search)s))
        """

        params = {"search": f"%{search_term}%"}

        if league_id:
            query += " AND l.league_id = %(league_id)s"
            params["league_id"] = league_id

        query += " ORDER BY p.last_name, p.first_name LIMIT %(limit)s"
        params["limit"] = limit

        results = execute_query(query, params)

        return [
            {
                "name": f"{r['first_name']} {r['last_name']}",
                "player_id": r["tenniscores_player_id"],
                "club": r["club_name"],
                "series": r["series_name"],
                "league": r["league_id"],
            }
            for r in results
        ]

    except Exception as e:
        logger.error(f"Error searching players: {e}")
        return []


def calculate_player_record_from_match_scores(player_id, league_id=None, team_id=None):
    """
    Calculate player's win/loss record from match_scores table
    
    Args:
        player_id (str): Player's tenniscores_player_id
        league_id (int, optional): League ID to filter matches
        team_id (int, optional): Team ID to filter matches
        
    Returns:
        dict: Dictionary with wins, losses, total_matches, and win_rate
    """
    try:
        # Base query to count wins and losses
        base_query = """
            SELECT 
                COUNT(CASE WHEN winner = 'home' AND (home_player_1_id = %s OR home_player_2_id = %s) THEN 1 END) as home_wins,
                COUNT(CASE WHEN winner = 'away' AND (away_player_1_id = %s OR away_player_2_id = %s) THEN 1 END) as away_wins,
                COUNT(CASE WHEN winner = 'home' AND (away_player_1_id = %s OR away_player_2_id = %s) THEN 1 END) as home_losses,
                COUNT(CASE WHEN winner = 'away' AND (home_player_1_id = %s OR home_player_2_id = %s) THEN 1 END) as away_losses,
                COUNT(*) as total_matches
            FROM match_scores 
            WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
        """
        
        params = [player_id] * 12  # 12 placeholders for the 12 %s in the query
        
        # Add league filtering if provided
        if league_id:
            base_query += " AND league_id = %s"
            params.append(league_id)
            
        # Add team filtering if provided
        if team_id:
            base_query += " AND (home_team_id = %s OR away_team_id = %s)"
            params.append(team_id)
            params.append(team_id)
        
        result = execute_query_one(base_query, params)
        
        if not result:
            return {"wins": 0, "losses": 0, "total_matches": 0, "win_rate": "0.0%"}
        
        # Calculate totals
        total_wins = (result.get("home_wins", 0) or 0) + (result.get("away_wins", 0) or 0)
        total_losses = (result.get("home_losses", 0) or 0) + (result.get("away_losses", 0) or 0)
        total_matches = result.get("total_matches", 0) or 0
        
        # Calculate win rate
        if total_matches > 0:
            win_rate = f"{(total_wins / total_matches * 100):.1f}%"
        else:
            win_rate = "0.0%"
        
        return {
            "wins": total_wins,
            "losses": total_losses,
            "total_matches": total_matches,
            "win_rate": win_rate
        }
        
    except Exception as e:
        logger.error(f"Error calculating player record for {player_id}: {e}")
        return {"wins": 0, "losses": 0, "total_matches": 0, "win_rate": "0.0%"}
