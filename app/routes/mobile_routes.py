"""
Mobile routes blueprint - handles all mobile interface functionality
This module contains routes for mobile-specific pages and user interactions.
"""

import json
import logging
import os
import re
from datetime import datetime
from urllib.parse import unquote

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from app.services.mobile_service import (
    get_all_team_availability_data,
    get_club_players_data,
    get_mobile_availability_data,
    get_mobile_club_data,
    get_mobile_improve_data,
    get_mobile_player_stats,
    get_mobile_schedule_data,
    get_mobile_series_data,
    get_mobile_team_data,
    get_player_analysis,
    get_player_analysis_by_name,
    get_player_search_data,
    get_practice_times_data,
    get_teams_players_data,
)

# Import the new simulation functionality
from app.services.simulation import (
    AdvancedMatchupSimulator,
    get_players_by_team,
    get_players_for_selection,
    get_teams_for_selection,
)
from database_utils import execute_query, execute_query_one, execute_update
from routes.act.availability import get_user_availability

# Import availability functions from existing routes
from routes.act.schedule import get_matches_for_user_club
from utils.auth import login_required
from utils.logging import log_user_activity



# Create logger
logger = logging.getLogger(__name__)

# Create mobile blueprint
mobile_bp = Blueprint("mobile", __name__)


@mobile_bp.route("/mobile/admin")
@login_required
def serve_mobile_admin():
    """Serve the mobile admin page - redirects to main admin"""
    return redirect(url_for("admin.serve_admin"))


def should_preserve_session_context(user_email: str, current_session: dict) -> bool:
    """
    Determine if we should preserve current session context or refresh from database.
    
    Returns False (refresh from DB) if:
    - League switch detected (database league_context != session league_context)
    - Session league data doesn't match database league_context (stale session)
    - Session is incomplete or invalid
    
    Returns True (preserve session) if:
    - Session has valid team context and matches database league context
    """
    try:
        # Get current league_context from database
        # execute_query_one is already imported at module level
        db_user_info = execute_query_one("SELECT league_context FROM users WHERE email = %s", [user_email])
        db_league_context = db_user_info.get("league_context") if db_user_info else None
        
        # Check if league context has changed in database (league switch detection)
        session_league_context = current_session.get("league_context")
        session_league_id = current_session.get("league_id")
        
        # If league context changed in database, always refresh (league switch occurred)
        league_switch_detected = (session_league_context != db_league_context)
        
        if league_switch_detected:
            print(f"[DEBUG] League switch detected: session_league_context={session_league_context} vs db_league_context={db_league_context}, will refresh from database")
            return False
        
        # ADDITIONAL CHECK: If session league_id doesn't match database league_context, session is stale
        league_mismatch_detected = (session_league_id != db_league_context)
        
        if league_mismatch_detected:
            print(f"[DEBUG] League mismatch detected: session_league_id={session_league_id} vs db_league_context={db_league_context}, will refresh from database")
            return False
        
        # Check if current session has valid team context AND correct league_id
        has_valid_team_context = (
            current_session.get("team_id") is not None and
            current_session.get("club") and
            current_session.get("series")
        )
        
        # CRITICAL FIX: Check if league_id is correct, not just if it exists
        has_correct_league_id = (session_league_id == db_league_context)
        
        # ONLY preserve session if BOTH team context AND league_id are correct
        if has_valid_team_context and has_correct_league_id:
            print(f"[DEBUG] Valid team context and correct league_id found, preserving session: {current_session.get('club')} - {current_session.get('series')} (league_id: {session_league_id})")
            return True
        else:
            if not has_correct_league_id:
                print(f"[DEBUG] League ID mismatch detected, will refresh from database: session_league_id={session_league_id} vs db_league_context={db_league_context}")
            else:
                print(f"[DEBUG] Session incomplete or invalid, will refresh from database")
            return False
            
    except Exception as e:
        print(f"[DEBUG] Error checking session context: {e}, will refresh from database")
        return False


@mobile_bp.route("/mobile")
@login_required
def serve_mobile():
    """Serve the mobile home page (submenu layout - primary layout)"""
    print(f"=== SERVE_MOBILE FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")

    # Don't handle admin routes
    if "/admin" in request.path:
        print("Admin route detected in mobile, redirecting to serve_admin")
        return redirect(url_for("admin.serve_admin"))

    # Use new session service to get fresh session data, BUT preserve team switches
    from app.services.session_service import get_session_data_for_user
    
    try:
        user_email = session["user"]["email"]
        
        print(f"[DEBUG] Checking session for user: {user_email}")
        
        # Check if we're currently impersonating - if so, ALWAYS preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            # During impersonation, never rebuild session - preserve manual selections
            print(f"[DEBUG] Impersonation active - preserving session as-is")
            session_data = {"user": session["user"], "authenticated": True}
        else:
            # Use helper function to determine if we should preserve session or refresh
            current_session = session.get("user", {})
            
            if should_preserve_session_context(user_email, current_session):
                # Preserve current session (team switch protection + no league switch detected)
                session_data = {"user": current_session, "authenticated": True}
            else:
                # Session is incomplete, invalid, or league switch detected - refresh from database
                fresh_session_data = get_session_data_for_user(user_email)
                    
                print(f"[DEBUG] Fresh session data result: {fresh_session_data}")
                
                if fresh_session_data:
                    # Update the Flask session with fresh data
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_data = {"user": fresh_session_data, "authenticated": True}
                    print(f"[DEBUG] Using fresh session data and updated Flask session")
                else:
                    # Fallback to old session if session service fails
                    session_data = {"user": session["user"], "authenticated": True}
                    print(f"[DEBUG] Using fallback session data: {session['user']}")
        
        # Log mobile access
        try:
            log_user_activity(
                session["user"]["email"], 
                "page_visit", 
                page="mobile_home_submenu",
                first_name=session["user"].get("first_name"),
                last_name=session["user"].get("last_name")
            )
        except Exception as e2:
            print(f"Error logging mobile access: {str(e2)}")

    except Exception as e:
        print(f"Error with new session service: {str(e)}")
        # Fallback to old session
        session_data = {"user": session["user"], "authenticated": True}
        try:
            log_user_activity(session["user"]["email"], "page_visit", page="mobile_home_submenu")
        except Exception as e2:
            print(f"Error logging mobile access: {str(e2)}")

    return render_template("mobile/home_submenu.html", session_data=session_data)


@mobile_bp.route("/mobile/alt1")
@login_required
def serve_mobile_alt1():
    """Serve the alternative mobile home page with white buttons and borders"""
    print(f"=== SERVE_MOBILE_ALT1 FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")

    # Don't handle admin routes
    if "/admin" in request.path:
        print("Admin route detected in mobile, redirecting to serve_admin")
        return redirect(url_for("admin.serve_admin"))

    # Use new session service to get fresh session data, BUT preserve team switches
    from app.services.session_service import get_session_data_for_user
    
    try:
        user_email = session["user"]["email"]
        
        print(f"[DEBUG] Checking session for user: {user_email}")
        
        # Check if we're currently impersonating - if so, ALWAYS preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            # During impersonation, never rebuild session - preserve manual selections
            print(f"[DEBUG] Impersonation active - preserving session as-is")
            session_data = {"user": session["user"], "authenticated": True}
        else:
            # Use helper function to determine if we should preserve session or refresh
            current_session = session.get("user", {})
            
            if should_preserve_session_context(user_email, current_session):
                # Preserve current session (team switch protection + no league switch detected)
                session_data = {"user": current_session, "authenticated": True}
            else:
                # Session is incomplete, invalid, or league switch detected - refresh from database
                fresh_session_data = get_session_data_for_user(user_email)
                    
                print(f"[DEBUG] Fresh session data result: {fresh_session_data}")
                
                if fresh_session_data:
                    # Update the Flask session with fresh data
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_data = {"user": fresh_session_data, "authenticated": True}
                    print(f"[DEBUG] Using fresh session data and updated Flask session")
                else:
                    # Fallback to old session if session service fails
                    session_data = {"user": session["user"], "authenticated": True}
                    print(f"[DEBUG] Using fallback session data: {session['user']}")
        
        # Log mobile access
        try:
            log_user_activity(
                session["user"]["email"], 
                "page_visit", 
                page="mobile_home_alt1",
                first_name=session["user"].get("first_name"),
                last_name=session["user"].get("last_name")
            )
        except Exception as e2:
            print(f"Error logging mobile access: {str(e2)}")

    except Exception as e:
        print(f"Error with new session service: {str(e)}")
        # Fallback to old session
        session_data = {"user": session["user"], "authenticated": True}
        try:
            log_user_activity(session["user"]["email"], "page_visit", page="mobile_home_alt1")
        except Exception as e2:
            print(f"Error logging mobile access: {str(e2)}")

    return render_template("mobile/mobile_home_alt1.html", session_data=session_data)


@mobile_bp.route("/mobile/classic")
@login_required
def serve_mobile_classic():
    """Serve the classic mobile home page with colored buttons"""
    print(f"=== SERVE_MOBILE_CLASSIC FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")

    # Don't handle admin routes
    if "/admin" in request.path:
        print("Admin route detected in mobile, redirecting to serve_admin")
        return redirect(url_for("admin.serve_admin"))

    # Use new session service to get fresh session data, BUT preserve team switches
    from app.services.session_service import get_session_data_for_user
    
    try:
        user_email = session["user"]["email"]
        
        print(f"[DEBUG] Checking session for user: {user_email}")
        
        # Check if we're currently impersonating - if so, ALWAYS preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            # During impersonation, never rebuild session - preserve manual selections
            print(f"[DEBUG] Impersonation active - preserving session as-is")
            session_data = {"user": session["user"], "authenticated": True}
        else:
            # Use helper function to determine if we should preserve session or refresh
            current_session = session.get("user", {})
            
            if should_preserve_session_context(user_email, current_session):
                # Preserve current session (team switch protection + no league switch detected)
                session_data = {"user": current_session, "authenticated": True}
            else:
                # Session is incomplete, invalid, or league switch detected - refresh from database
                fresh_session_data = get_session_data_for_user(user_email)
                    
                print(f"[DEBUG] Fresh session data result: {fresh_session_data}")
                
                if fresh_session_data:
                    # Update the Flask session with fresh data
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_data = {"user": fresh_session_data, "authenticated": True}
                    print(f"[DEBUG] Using fresh session data and updated Flask session")
                else:
                    # Fallback to old session if session service fails
                    session_data = {"user": session["user"], "authenticated": True}
                    print(f"[DEBUG] Using fallback session data: {session['user']}")
        
        # Log mobile access
        try:
            log_user_activity(
                session["user"]["email"], 
                "page_visit", 
                page="mobile_home_classic",
                first_name=session["user"].get("first_name"),
                last_name=session["user"].get("last_name")
            )
        except Exception as e2:
            print(f"Error logging mobile access: {str(e2)}")

    except Exception as e:
        print(f"Error with new session service: {str(e)}")
        # Fallback to old session
        session_data = {"user": session["user"], "authenticated": True}
        try:
            log_user_activity(session["user"]["email"], "page_visit", page="mobile_home_classic")
        except Exception as e2:
            print(f"Error logging mobile access: {str(e2)}")

    return render_template("mobile/index_old.html", session_data=session_data)


@mobile_bp.route("/mobile/rally")
@login_required
def serve_rally_mobile():
    """Redirect from old mobile interface to new one"""
    try:
        # Log the redirect
        log_user_activity(
            session["user"]["email"],
            "redirect",
            page="rally_mobile_to_new",
            details="Redirected from old mobile interface to new one",
        )
    except Exception as e:
        print(f"Error logging rally mobile redirect: {str(e)}")

    return redirect("/mobile")


@mobile_bp.route("/mobile/matches")
@login_required
def serve_mobile_matches():
    """Serve the mobile matches page"""
    session_data = {"user": session["user"], "authenticated": True}

    log_user_activity(session["user"]["email"], "page_visit", page="mobile_matches")
    return render_template("mobile/matches.html", session_data=session_data)


@mobile_bp.route("/mobile/rankings")
@login_required
def serve_mobile_rankings():
    """Serve the mobile rankings page"""
    session_data = {"user": session["user"], "authenticated": True}

    log_user_activity(session["user"]["email"], "page_visit", page="mobile_rankings")
    return render_template("mobile/rankings.html", session_data=session_data)


@mobile_bp.route("/mobile/profile")
@login_required
def serve_mobile_profile():
    """Serve the mobile profile page"""
    session_data = {"user": session["user"], "authenticated": True}

    log_user_activity(session["user"]["email"], "page_visit", page="mobile_profile")
    return render_template("mobile/profile.html", session_data=session_data)


@mobile_bp.route("/mobile/player-detail/<player_id>")
@login_required
def serve_mobile_player_detail(player_id):
    """Serve the mobile player detail page with proper team context filtering"""
    player_identifier = unquote(player_id)
    
    # Determine if this is a player_id (alphanumeric with dashes) or a player name
    # Player IDs look like: nndz-WlNhd3hMYi9nQT09
    # Composite IDs look like: nndz-WlNhd3hMYi9nQT09_team_123
    # CNSWPL IDs look like: cnswpl_2b49828960f4726c_team_96569
    # Player names look like: John Smith
    
    actual_player_id = player_identifier
    team_id = None
    player_name = None  # Initialize player_name
    
    # Check if this is a composite ID (player_id_team_teamID)
    if '_team_' in player_identifier:
        parts = player_identifier.split('_team_')
        if len(parts) == 2:
            actual_player_id = parts[0]
            try:
                team_id = int(parts[1])
            except ValueError:
                team_id = None
    
    # Enhanced player ID detection to include CNSWPL format
    is_player_id = bool(
        (re.match(r'^[a-zA-Z0-9\-]+$', actual_player_id) and '-' in actual_player_id) or  # Standard format
        actual_player_id.startswith('cnswpl_')  # CNSWPL format
    )
    
    # Get viewing user's league context for filtering
    viewing_user = session["user"].copy()
    viewing_user_league = viewing_user.get("league_id", "")
    league_id_int = None
    
    if isinstance(viewing_user_league, str) and viewing_user_league != "":
        try:
            league_record = execute_query_one(
                "SELECT id FROM leagues WHERE league_id = %s", [viewing_user_league]
            )
            if league_record:
                league_id_int = league_record["id"]
        except Exception:
            pass
    elif isinstance(viewing_user_league, int):
        league_id_int = viewing_user_league
    
    if is_player_id:
        # Look up player by tenniscores_player_id with proper team and league filtering
        if team_id:
            # Use team-specific lookup for better context
            player_query = """
                SELECT CONCAT(p.first_name, ' ', p.last_name) as full_name,
                       p.tenniscores_player_id, p.league_id, p.team_id
                FROM players p
                WHERE p.tenniscores_player_id = %s AND p.team_id = %s
                LIMIT 1
            """
            player_record = execute_query_one(player_query, [actual_player_id, team_id])
        else:
            # For multi-team players, prefer team with most recent activity in viewer's league
            if league_id_int:
                player_query = """
                    SELECT CONCAT(p.first_name, ' ', p.last_name) as full_name,
                           p.tenniscores_player_id, p.league_id, p.team_id,
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
                    WHERE p.tenniscores_player_id = %s AND p.league_id = %s AND p.is_active = TRUE
                    ORDER BY last_match_date DESC NULLS LAST, p.team_id DESC
                    LIMIT 1
                """
                player_record = execute_query_one(player_query, [actual_player_id, league_id_int])
            else:
                player_query = """
                    SELECT CONCAT(first_name, ' ', last_name) as full_name,
                           tenniscores_player_id, league_id, team_id
                    FROM players 
                    WHERE tenniscores_player_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                """
                player_record = execute_query_one(player_query, [actual_player_id])
        
        if player_record:
            # Format name as "First Last" for display
            full_name = player_record["full_name"]
            player_name = full_name
            print(f"[DEBUG] Found player record: {player_name} (ID: {actual_player_id}, Team: {team_id})")
            # Use the team_id from the database record if not explicitly provided
            if not team_id:
                team_id = player_record.get("team_id")
        else:
            # Player ID not found, try to get name using the mobile service function
            from app.services.mobile_service import get_player_name_from_id
            player_name = get_player_name_from_id(actual_player_id)
            print(f"[DEBUG] Player record not found, using fallback name: {player_name}")
            
            # If still no name found, show meaningful error
            if player_name == "Unknown Player" or "Player (" in player_name:
                session_data = {"user": session["user"], "authenticated": True}
                analyze_data = {"error": f"Player not found for ID: {player_identifier}"}
                return render_template(
                    "mobile/player_detail.html",
                    session_data=session_data,
                    analyze_data=analyze_data,
                    player_name=f"Player ID: {player_identifier}",
                )
    else:
        # Treat as player name - find best matching player record in viewer's league
        player_name = player_identifier
        name_parts = player_name.strip().split()
        
        if len(name_parts) >= 2:
            # Check if this is "Last, First" format (comma-separated)
            if ',' in player_name:
                # Handle "Last, First" format
                name_sections = player_name.split(',')
                if len(name_sections) == 2:
                    last_name = name_sections[0].strip()
                    first_name = name_sections[1].strip()
                else:
                    # Fallback to space splitting if comma format is malformed
                    first_name = name_parts[0]
                    last_name = " ".join(name_parts[1:])
            else:
                # Handle "First Last" format
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            
            # For name-based lookups, prefer player in viewer's league with recent activity
            if league_id_int:
                name_lookup_query = """
                    SELECT p.tenniscores_player_id, p.team_id, p.league_id,
                           (SELECT MAX(match_date) 
                            FROM match_scores ms 
                            WHERE (ms.home_player_1_id = p.tenniscores_player_id 
                                   OR ms.home_player_2_id = p.tenniscores_player_id
                                   OR ms.away_player_1_id = p.tenniscores_player_id 
                                   OR ms.away_player_2_id = p.tenniscores_player_id)
                            AND ms.league_id = p.league_id
                           ) as last_match_date
                    FROM players p
                    WHERE p.first_name = %s AND p.last_name = %s 
                    AND p.league_id = %s AND p.is_active = TRUE
                    ORDER BY last_match_date DESC NULLS LAST, p.id DESC
                    LIMIT 1
                """
                name_record = execute_query_one(name_lookup_query, [first_name, last_name, league_id_int])
            else:
                name_lookup_query = """
                    SELECT tenniscores_player_id, team_id, league_id
                    FROM players 
                    WHERE first_name = %s AND last_name = %s
                    ORDER BY id DESC
                    LIMIT 1
                """
                name_record = execute_query_one(name_lookup_query, [first_name, last_name])
            
            if name_record:
                actual_player_id = name_record["tenniscores_player_id"]
                team_id = name_record.get("team_id")
                # Convert to "First Last" format for display
                player_name = f"{first_name} {last_name}"
                print(f"[DEBUG] Name lookup found player_id {actual_player_id} with team_id {team_id}")
            else:
                print(f"[DEBUG] No player record found for name: {player_name}")

    # Create player user dict with team context for mobile service
    if actual_player_id:
        # CRITICAL FIX: Get target player's actual league_id instead of viewing user's league_id
        # This ensures the analysis shows matches from the correct league for the target player
        player_league_id = viewing_user.get("league_id")  # Default fallback
        
        # Try to get the target player's actual league from their player record
        if 'player_record' in locals() and player_record:
            # Use league_id from the player record we already found
            target_league_record = execute_query_one(
                "SELECT league_id FROM leagues WHERE id = %s", [player_record.get("league_id")]
            )
            if target_league_record:
                player_league_id = target_league_record["league_id"]
                print(f"[DEBUG] Using target player's league: {player_league_id}")
        elif actual_player_id:
            # Fallback: Look up any player record to get their league
            fallback_player_query = """
                SELECT l.league_id 
                FROM players p 
                JOIN leagues l ON p.league_id = l.id 
                WHERE p.tenniscores_player_id = %s 
                LIMIT 1
            """
            fallback_record = execute_query_one(fallback_player_query, [actual_player_id])
            if fallback_record:
                player_league_id = fallback_record["league_id"]
                print(f"[DEBUG] Using fallback player league: {player_league_id}")
        
    else:
        # Final fallback to name-based analysis
        from app.services.mobile_service import get_player_analysis_by_name
        analyze_data = get_player_analysis_by_name(player_name, viewing_user)

    # Get additional player info (team name and series) for the header using team context
    player_info = {"club": None, "series": None, "team_name": None, "tenniscores_player_id": actual_player_id, "team_id": team_id}
    if actual_player_id:
        # Use team-specific lookup for accurate context when team_id is available
        if team_id:
            player_info_query = """
                SELECT 
                    c.name as club_name,
                    s.name as series_name,
                    t.team_name
                FROM players p
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id = %s AND p.team_id = %s
                LIMIT 1
            """
            player_record = execute_query_one(player_info_query, [actual_player_id, team_id])
        else:
            # Fallback to any matching player record (multi-team scenario)
            if league_id_int:
                player_info_query = """
                    SELECT 
                        c.name as club_name,
                        s.name as series_name,
                        t.team_name
                    FROM players p
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    LEFT JOIN teams t ON p.team_id = t.id
                    WHERE p.tenniscores_player_id = %s AND p.league_id = %s
                    ORDER BY p.id DESC
                    LIMIT 1
                """
                player_record = execute_query_one(player_info_query, [actual_player_id, league_id_int])
            else:
                player_info_query = """
                    SELECT 
                        c.name as club_name,
                        s.name as series_name,
                        t.team_name
                    FROM players p
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    LEFT JOIN teams t ON p.team_id = t.id
                    WHERE p.tenniscores_player_id = %s
                    ORDER BY p.id DESC
                    LIMIT 1
                """
                player_record = execute_query_one(player_info_query, [actual_player_id])
        
        if player_record:
            # Format series name for display (e.g., "Chicago: 7" -> "Series 7")
            formatted_series = player_record["series_name"]
            if formatted_series:
                try:
                    if ":" in formatted_series:
                        series_number = formatted_series.split(":")[-1].strip()
                        formatted_series = f"Series {series_number}"
                    else:
                        # Handle format like "Chicago 7"
                        parts = formatted_series.split()
                        if len(parts) >= 2 and parts[-1].isdigit():
                            series_number = parts[-1]
                            formatted_series = f"Series {series_number}"
                    print(f"[DEBUG] Player detail - Formatted series '{player_record['series_name']}' -> '{formatted_series}'")
                except Exception as e:
                    print(f"[DEBUG] Could not format series for player detail: {e}")
                    pass
                    
            player_info = {
                "club": player_record["club_name"],
                "series": formatted_series, 
                "team_name": player_record["team_name"],
                "tenniscores_player_id": actual_player_id,
                "team_id": team_id
            }

    # Create a user dict with the specific player ID and team context for PTI delta calculation
    player_user_dict = {
        "first_name": player_name.split()[0] if player_name else "",
        "last_name": " ".join(player_name.split()[1:]) if len(player_name.split()) > 1 else "",
        "tenniscores_player_id": actual_player_id,
        "league_id": player_league_id,  # Use target player's league, not viewing user's
        "email": viewing_user.get("email", "")
    }
    
    # Add team context for filtering and substitute detection
    if team_id:
        player_user_dict["team_context"] = team_id
        player_user_dict["team_id"] = str(team_id)  # Add team_id for substitute detection
        print(f"[DEBUG] Player detail - Using player ID {actual_player_id} with team context {team_id}")
    else:
        print(f"[DEBUG] Player detail - Using player ID {actual_player_id} without specific team context")
    
    # Add club and series information for PTI delta calculation
    if 'player_info' in locals() and player_info:
        player_user_dict["club"] = player_info.get("club", "")
        player_user_dict["series"] = player_info.get("series", "")
        print(f"[DEBUG] Player detail - Added club '{player_user_dict['club']}' and series '{player_user_dict['series']}' for PTI delta calculation")
    
    # Get player analysis data with PTI delta calculation
    analyze_data = get_player_analysis(player_user_dict)

    # PTI data is now handled within the service function with proper league filtering
    
    # Get last season stats (2024-2025)
    from app.services.mobile_service import get_last_season_stats, get_current_season_partner_analysis
    last_season_stats = get_last_season_stats(actual_player_id, league_id_int, season="2024-2025")
    analyze_data["last_season"] = last_season_stats
    
    # Get current season partner analysis
    partner_analysis = get_current_season_partner_analysis(actual_player_id, league_id_int, team_id)
    analyze_data["partner_analysis"] = partner_analysis

    session_data = {"user": session["user"], "authenticated": True}
    team_or_club = player_info.get("team_name") or player_info.get("club") or "Unknown"
    
    # Debug: Log what player_name is being passed to template
    print(f"[DEBUG] Rendering template with player_name: '{player_name}' for player_id: '{actual_player_id}'")
    
    log_user_activity(
        session["user"]["email"],
        "page_visit",
        page="mobile_player_detail",
        details=f"Player Detail: {player_name} ({team_or_club})"
    )
    return render_template(
        "mobile/player_detail.html",
        session_data=session_data,
        analyze_data=analyze_data,
        player_name=player_name,
        player_info=player_info,
        viewing_user_league=viewing_user_league,
    )


@mobile_bp.route("/mobile/last-season-stats/<player_id>")
@login_required
def serve_mobile_last_season_stats(player_id):
    """Serve the mobile Last Season Stats detail page"""
    from app.services.mobile_service import get_last_season_stats, get_last_season_partner_analysis, get_last_season_court_analysis
    from urllib.parse import unquote
    
    player_identifier = unquote(player_id)
    
    # Parse player_id and team_id (format: player_id or player_id_team_teamID)
    actual_player_id = player_identifier
    team_id = None
    
    if '_team_' in player_identifier:
        parts = player_identifier.split('_team_')
        if len(parts) == 2:
            actual_player_id = parts[0]
            try:
                team_id = int(parts[1])
            except ValueError:
                team_id = None
    
    # Get viewing user's league context
    viewing_user = session["user"].copy()
    viewing_user_league = viewing_user.get("league_id", "")
    league_id_int = None
    
    if isinstance(viewing_user_league, str) and viewing_user_league != "":
        try:
            league_record = execute_query_one(
                "SELECT id FROM leagues WHERE league_id = %s", [viewing_user_league]
            )
            if league_record:
                league_id_int = league_record["id"]
        except Exception:
            pass
    elif isinstance(viewing_user_league, int):
        league_id_int = viewing_user_league
    
    # Get player's name from current database
    player_name_query = """
        SELECT 
            CONCAT(p.first_name, ' ', p.last_name) as name,
            p.tenniscores_player_id
        FROM players p
        WHERE p.tenniscores_player_id = %s
        LIMIT 1
    """
    player_name_result = execute_query_one(player_name_query, [actual_player_id])
    player_name = player_name_result.get("name", "Unknown Player") if player_name_result else "Unknown Player"
    
    # Get player's last season team info from match_scores_previous_seasons
    # Find the most common team they played for in 2024-2025 season
    last_season_team_query = """
        SELECT 
            ms.home_team_id,
            ms.away_team_id,
            t_home.team_name as home_team_name,
            t_away.team_name as away_team_name,
            c_home.name as home_club,
            c_away.name as away_club,
            s_home.name as home_series,
            s_away.name as away_series,
            CASE 
                WHEN ms.home_player_1_id = %s OR ms.home_player_2_id = %s THEN ms.home_team_id
                ELSE ms.away_team_id
            END as player_team_id,
            CASE 
                WHEN ms.home_player_1_id = %s OR ms.home_player_2_id = %s THEN t_home.team_name
                ELSE t_away.team_name
            END as player_team_name,
            CASE 
                WHEN ms.home_player_1_id = %s OR ms.home_player_2_id = %s THEN c_home.name
                ELSE c_away.name
            END as player_club,
            CASE 
                WHEN ms.home_player_1_id = %s OR ms.home_player_2_id = %s THEN s_home.name
                ELSE s_away.name
            END as player_series
        FROM match_scores_previous_seasons ms
        LEFT JOIN teams t_home ON ms.home_team_id = t_home.id
        LEFT JOIN teams t_away ON ms.away_team_id = t_away.id
        LEFT JOIN clubs c_home ON t_home.club_id = c_home.id
        LEFT JOIN clubs c_away ON t_away.club_id = c_away.id
        LEFT JOIN series s_home ON t_home.series_id = s_home.id
        LEFT JOIN series s_away ON t_away.series_id = s_away.id
        WHERE ms.season = '2024-2025'
            AND (ms.home_player_1_id = %s OR ms.home_player_2_id = %s OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s)
    """
    
    if league_id_int:
        last_season_team_query += " AND ms.league_id = %s"
        last_season_matches = execute_query(last_season_team_query, 
            [actual_player_id, actual_player_id, actual_player_id, actual_player_id, 
             actual_player_id, actual_player_id, actual_player_id, actual_player_id,
             actual_player_id, actual_player_id, actual_player_id, actual_player_id, league_id_int])
    else:
        last_season_matches = execute_query(last_season_team_query, 
            [actual_player_id, actual_player_id, actual_player_id, actual_player_id, 
             actual_player_id, actual_player_id, actual_player_id, actual_player_id,
             actual_player_id, actual_player_id, actual_player_id, actual_player_id])
    
    # Find the most common team/club/series from last season matches
    player_info = {
        "name": player_name,
        "tenniscores_player_id": actual_player_id,
        "team_id": None,
        "club": None,
        "series": None,
        "team_name": None
    }
    
    if last_season_matches and len(last_season_matches) > 0:
        # Count occurrences of each team
        from collections import Counter
        team_counts = Counter()
        team_info = {}
        
        for match in last_season_matches:
            team_id = match.get("player_team_id")
            if team_id:
                team_counts[team_id] += 1
                team_info[team_id] = {
                    "team_name": match.get("player_team_name"),
                    "club": match.get("player_club"),
                    "series": match.get("player_series")
                }
        
        # Get most common team
        if team_counts:
            most_common_team_id = team_counts.most_common(1)[0][0]
            player_info.update({
                "team_id": most_common_team_id,
                "team_name": team_info[most_common_team_id]["team_name"],
                "club": team_info[most_common_team_id]["club"],
                "series": team_info[most_common_team_id]["series"]
            })
    
    # Get last season stats, partner analysis, and court analysis
    last_season_stats = get_last_season_stats(actual_player_id, league_id_int, season="2024-2025")
    partner_analysis = get_last_season_partner_analysis(actual_player_id, league_id_int, season="2024-2025")
    court_analysis = get_last_season_court_analysis(actual_player_id, league_id_int, season="2024-2025")
    
    session_data = {"user": session["user"], "authenticated": True}
    
    log_user_activity(
        session["user"]["email"],
        "page_visit",
        page="mobile_last_season_stats",
        details=f"Last Season Stats: {player_name}"
    )
    
    return render_template(
        "mobile/last_season_stats.html",
        session_data=session_data,
        player_name=player_name,
        player_info=player_info,
        last_season=last_season_stats,
        partner_analysis=partner_analysis,
        court_analysis=court_analysis,
        viewing_user_league=viewing_user_league,
    )


@mobile_bp.route("/mobile/view-schedule")
@login_required
def serve_mobile_view_schedule():
    """Serve the mobile View Schedule page with the user's schedule."""
    try:
        # Use session service to get fresh session data (same pattern as working routes)
        from app.services.session_service import get_session_data_for_user
        
        user_email = session["user"]["email"]
        
        # Check if we're currently impersonating - if so, preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            session_user = session["user"]
        else:
            # Check if current session has valid team context - if so, preserve it
            current_session = session.get("user", {})
            has_valid_team_context = (
                current_session.get("team_id") is not None and
                current_session.get("league_id") is not None and
                current_session.get("club") and
                current_session.get("series")
            )
            
            if has_valid_team_context:
                session_user = current_session
            else:
                # Session is incomplete or invalid, refresh from database
                fresh_session_data = get_session_data_for_user(user_email)
                
                if fresh_session_data:
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_user = fresh_session_data
                else:
                    session_user = session["user"]

        schedule_data = get_mobile_schedule_data(session_user)

        session_data = {"user": session_user, "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_view_schedule"
        )

        return render_template(
            "mobile/view_schedule.html", session_data=session_data, **schedule_data
        )

    except Exception as e:
        print(f"Error serving mobile view schedule: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        session_data = {"user": session.get("user", {}), "authenticated": True}

        return render_template(
            "mobile/view_schedule.html",
            session_data=session_data,
            error="Failed to load schedule data",
        )


@mobile_bp.route("/mobile/analyze-me")
@login_required
def serve_mobile_analyze_me():
    """Serve the mobile Analyze Me page"""
    try:
        # Use session service to get fresh session data, BUT preserve team switches (same as main mobile route)
        from app.services.session_service import get_session_data_for_user
        
        user_email = session["user"]["email"]
        
        # Check if we're currently impersonating - if so, ALWAYS preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            # During impersonation, never rebuild session - preserve manual selections
            session_user = session["user"]
        else:
            # Use helper function to determine if we should preserve session or refresh
            current_session = session.get("user", {})
            
            if should_preserve_session_context(user_email, current_session):
                # Preserve current session (team switch protection + no league switch detected)
                print(f"[DEBUG] Analyze-me - Preserving existing team context: {current_session.get('club')} - {current_session.get('series')}")
                session_user = current_session
            else:
                # Session is incomplete, invalid, or league switch detected - refresh from database
                print(f"[DEBUG] Analyze-me - Session incomplete or league switch detected, refreshing from database")
                fresh_session_data = get_session_data_for_user(user_email)
                
                if fresh_session_data:
                    # Update Flask session with fresh data
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_user = fresh_session_data
                    print(f"[DEBUG] Analyze-me - Refreshed session data: {fresh_session_data.get('tenniscores_player_id')} in {fresh_session_data.get('league_name')}")
                else:
                    # Fallback to existing session
                    session_user = session["user"]
                    print(f"[DEBUG] Analyze-me - Using existing session data")

        # Check if session already has a tenniscores_player_id (set by league switching)
        if session_user.get("tenniscores_player_id"):
            # Fix session data if league_id is None but league_name exists
            if session_user.get("league_id") is None and session_user.get("league_name"):
                try:
                    league_record = execute_query_one(
                        "SELECT id, league_id FROM leagues WHERE league_name = %s",
                        [session_user.get("league_name")],
                    )
                    if league_record:
                        session_user["league_id"] = league_record["id"]
                        # Update session for future requests
                        session["user"]["league_id"] = league_record["id"]
                except Exception as e:
                    pass

            # Add team context for multi-team players (same as player-detail route)
            user_team_id = session_user.get("team_id")
            if user_team_id:
                session_user["team_context"] = user_team_id
                print(f"[DEBUG] Analyze-me - Using team context: team_id={user_team_id}")
            else:
                print(f"[DEBUG] Analyze-me - No team context available")

            # Use the session data (now with resolved league_id and team_context if applicable)
            analyze_data = get_player_analysis(session_user)
            
            # Get current season partner analysis
            from app.services.mobile_service import get_current_season_partner_analysis
            player_id = session_user.get("tenniscores_player_id")
            league_id_int = session_user.get("league_id")
            team_context = session_user.get("team_context") or session_user.get("team_id")
            
            print(f"[DEBUG] Analyze-me partner analysis - player_id: {player_id}, league_id: {league_id_int}, team_context: {team_context}")
            
            if player_id:
                partner_analysis = get_current_season_partner_analysis(player_id, league_id_int, team_context)
                print(f"[DEBUG] Analyze-me partner analysis result: {len(partner_analysis) if partner_analysis else 0} partners found")
                analyze_data["partner_analysis"] = partner_analysis
            else:
                print(f"[DEBUG] Analyze-me - No player_id, cannot fetch partner analysis")
                analyze_data["partner_analysis"] = []
        else:
            # NO FALLBACK: Require proper player ID - no name-based lookups
            print(f"[ERROR] Analyze-me - No tenniscores_player_id in session, cannot proceed with name-based lookup")
            analyze_data = {
                "error": "Player ID not found in session. Please check your profile setup or contact support.",
                "current_season": None,
                "court_analysis": {},
                "career_stats": None,
            }

        # Ensure session data has proper series display name for header
        session_user_for_template = session["user"].copy()
        
        # Format series display name for header - check both series field and series_id
        current_series = session_user_for_template.get("series", "")
        
        try:
            # If we have a series field that looks like database format, format it
            if current_series and (":" in current_series or current_series.startswith("Chicago")):
                # Format database series names like "Chicago: 7" or "Chicago 7" -> "Series 7"
                if ":" in current_series:
                    series_number = current_series.split(":")[-1].strip()
                    formatted_series = f"Series {series_number}"
                else:
                    # Handle format like "Chicago 7"
                    parts = current_series.split()
                    if len(parts) >= 2 and parts[-1].isdigit():
                        series_number = parts[-1]
                        formatted_series = f"Series {series_number}"
                    else:
                        formatted_series = current_series
                session_user_for_template["series"] = formatted_series
                print(f"[DEBUG] Formatted series '{current_series}' -> '{formatted_series}'")
            
            # If no series field but we have series_id, look it up and format
            elif session_user_for_template.get("series_id") and not current_series:
                series_query = "SELECT name FROM series WHERE id = %s"
                series_data = execute_query_one(series_query, [session_user_for_template["series_id"]])
                if series_data:
                    series_name = series_data["name"]
                    if ":" in series_name:
                        series_number = series_name.split(":")[-1].strip()
                        formatted_series = f"Series {series_number}"
                    else:
                        parts = series_name.split()
                        if len(parts) >= 2 and parts[-1].isdigit():
                            series_number = parts[-1]
                            formatted_series = f"Series {series_number}"
                        else:
                            formatted_series = series_name
                    session_user_for_template["series"] = formatted_series
                    print(f"[DEBUG] Looked up and formatted series '{series_name}' -> '{formatted_series}'")
        except Exception as e:
            print(f"[DEBUG] Could not format series display name: {e}")
            pass

        session_data = {"user": session_user_for_template, "authenticated": True}

        # Get last updated timestamp from match_scores table
        last_updated = None
        try:
            last_updated_result = execute_query_one(
                "SELECT MAX(created_at) as last_updated FROM match_scores"
            )
            if last_updated_result and last_updated_result.get("last_updated"):
                last_updated = last_updated_result["last_updated"]
        except Exception as e:
            print(f"[WARNING] Could not fetch last_updated timestamp: {e}")

        # Enhanced logging for analyze-me page visit
        analyze_me_details = {
            "page": "mobile_analyze_me",
            "user_league": session["user"].get("league_id", "Unknown"),
            "user_club": session["user"].get("club", "Unknown"),
            "user_series": session["user"].get("series", "Unknown"),
            "user_team_id": session["user"].get("team_id"),
            "has_player_id": bool(session["user"].get("tenniscores_player_id")),
            "has_matches": bool(analyze_data.get("current_season", {}).get("matches", 0) > 0)
        }
        
        log_user_activity(
            session["user"]["email"], 
            "page_visit", 
            page="mobile_analyze_me",
            details=analyze_me_details
        )

        return render_template(
            "mobile/analyze_me.html",
            session_data=session_data,
            analyze_data=analyze_data,
            last_updated=last_updated,
        )

    except Exception as e:
        print(f"Error serving mobile analyze me: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        session_data = {"user": session["user"], "authenticated": True}

        # Create a basic analyze_data structure with error message for the template
        analyze_data = {
            "error": f"Failed to load analysis data: {str(e)}",
            "current_season": None,
            "court_analysis": {},
            "career_stats": None,
            "player_history": None,
            "current_pti": None,
            "weekly_pti_change": None,
        }

        return render_template(
            "mobile/analyze_me.html",
            session_data=session_data,
            analyze_data=analyze_data,
        )


@mobile_bp.route("/api/player-history-chart")
@login_required
def get_player_history_chart():
    """API endpoint to get player history data for PTI chart - matches rally_reference format"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        user = session["user"]
        player_id = user.get("tenniscores_player_id")
        player_name = (
            f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        )

        if not player_id:
            return jsonify({"error": "Player ID not found"}), 400

        # Get player's database ID - prioritize the player record that has actual PTI history
        player_query = """
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
        player_data = execute_query_one(player_query, [player_id])

        if not player_data:
            return jsonify({"error": "Player not found"}), 404

        player_db_id = player_data["id"]

        # Log which player record we're using for debugging
        print(
            f"[DEBUG] PTI Chart - Using player_id {player_db_id} with {player_data['history_count']} history records for tenniscores_player_id {player_id}"
        )

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

        if not pti_records:
            # If no records found by player_id, try series matching as fallback
            series_name = player_data.get("series_name", "")
            if series_name:
                series_patterns = [
                    f"%{series_name}%",
                    (
                        f"%{series_name.split()[0]}%"
                        if " " in series_name
                        else f"%{series_name}%"
                    ),
                ]

                for pattern in series_patterns:
                    series_history_query = """
                        SELECT 
                            date,
                            end_pti,
                            series,
                            TO_CHAR(date, 'MM/DD/YYYY') as formatted_date
                        FROM player_history
                        WHERE series ILIKE %s
                        ORDER BY date ASC
                    """

                    pti_records = execute_query(series_history_query, [pattern])
                    if pti_records:
                        break

        if not pti_records:
            return jsonify({"error": "No PTI history found"}), 404

        # Format matches data to match rally_reference format
        matches_data = []
        for record in pti_records:
            matches_data.append(
                {
                    "date": record["formatted_date"],  # MM/DD/YYYY format
                    "end_pti": float(record["end_pti"]),
                }
            )

        # Return data in the format expected by rally_reference JavaScript
        response_data = {
            "name": player_name,
            "matches": matches_data,
            "success": True,
            "data": matches_data,  # Include both formats for compatibility
            "player_name": player_name,
            "total_matches": len(matches_data),
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error fetching player history chart: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch player history chart"}), 500


@mobile_bp.route("/api/season-history")
@login_required
def get_season_history():
    """API endpoint to get previous season history data"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        user = session["user"]
        player_id = user.get("tenniscores_player_id")

        if not player_id:
            return jsonify({"error": "Player ID not found"}), 400

        # Get current team context from session service
        from app.services.session_service import get_session_data_for_user
        
        # Check if we're currently impersonating - if so, don't rebuild session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            # During impersonation, use current session data instead of rebuilding
            session_data = user
        else:
            session_data = get_session_data_for_user(user["email"])
        
        current_team_id = session_data.get("team_id") if session_data else None

        # Get player's database ID - prioritize the player record for current team context
        if current_team_id:
            # First try to get the player record that matches the current team context
            player_query = """
                SELECT 
                    p.id,
                    p.pti as current_pti,
                    p.series_id,
                    p.team_id,
                    s.name as series_name,
                    t.team_name,
                    (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id = %s AND p.team_id = %s
                ORDER BY history_count DESC, p.id DESC
            """
            player_data = execute_query_one(player_query, [player_id, current_team_id])
        else:
            # Fallback to any player record if no team context
            player_query = """
                SELECT 
                    p.id,
                    p.pti as current_pti,
                    p.series_id,
                    p.team_id,
                    s.name as series_name,
                    t.team_name,
                    (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id = %s
                ORDER BY history_count DESC, p.id DESC
            """
            player_data = execute_query_one(player_query, [player_id])

        if not player_data:
            return jsonify({"error": "Player not found"}), 404

        player_db_id = player_data["id"]
        player_team_id = player_data["team_id"]

        # Debug logging
        print(f"[DEBUG] Season History - Player ID: {player_id}")
        print(f"[DEBUG] Season History - Current Team Context: {current_team_id}")
        print(
            f"[DEBUG] Season History - Player DB ID: {player_db_id} (with {player_data['history_count']} history records)"
        )
        print(f"[DEBUG] Season History - Player Team ID: {player_team_id}")
        print(
            f"[DEBUG] Season History - Player Series: {player_data.get('series_name')}"
        )
        print(f"[DEBUG] Season History - Team Name: {player_data.get('team_name')}")
        print(
            f"[DEBUG] Season History - Player Current PTI: {player_data.get('current_pti')}"
        )
        print(f"[DEBUG] Season History - APPROACH: Using specific player_db_id {player_db_id} to eliminate cross-team contamination")

        # Get season history data for ONLY the current team/series context
        # Filter by specific player_id AND series to avoid showing multiple series per season
        current_series_name = player_data.get("series_name", "")
        
        # Previous Season History shows historical performance across all seasons
        # No team context restriction needed - this is about historical PTI progression
        print(f"[DEBUG] Season History - Player: {player_data.get('first_name', '')} {player_data.get('last_name', '')}, DB ID: {player_db_id}")
        if player_team_id and current_series_name:
            print(f"[DEBUG] Season History - Team context available (team_id: {player_team_id}, series: {current_series_name})")
        else:
            print(f"[DEBUG] Season History - No team context, showing historical data across all seasons")

        # CORE FIX: Use ONLY the specific player record ID for current team context
        # This eliminates all cross-team contamination
        debug_query = """
            SELECT series, date, end_pti 
            FROM player_history 
            WHERE player_id = %s
            ORDER BY date DESC 
        """
        debug_records = execute_query(debug_query, [player_db_id])
        print(
            f"[DEBUG] Season History - {len(debug_records)} player_history records for player_id {player_db_id} (team: {player_data.get('team_name')}, series: {current_series_name}):"
        )

        # Group by series to see what series this player actually has
        series_counts = {}
        for record in debug_records:
            series = record["series"]
            if series not in series_counts:
                series_counts[series] = 0
            series_counts[series] += 1

        print(f"[DEBUG] Season History - Series breakdown:")
        for series, count in series_counts.items():
            print(f"  {series}: {count} records")

        # Show first few records from each series
        print(f"[DEBUG] Season History - Sample records:")
        for record in debug_records[:10]:
            print(
                f"  Date: {record['date']}, Series: {record['series']}, PTI: {record['end_pti']}"
            )

        season_history_query = """
            WITH season_data AS (
                SELECT 
                    series,
                    -- Calculate tennis season year (Aug-May spans two calendar years)
                    -- If month >= 8 (Aug-Dec), season starts that year
                    -- If month < 8 (Jan-Jul), season started previous year
                    CASE 
                        WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                        ELSE EXTRACT(YEAR FROM date) - 1
                    END as season_year,
                    date,
                    end_pti,
                    ROW_NUMBER() OVER (
                        PARTITION BY series, 
                        CASE 
                            WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                            ELSE EXTRACT(YEAR FROM date) - 1
                        END 
                        ORDER BY date ASC
                    ) as rn_start,
                    ROW_NUMBER() OVER (
                        PARTITION BY series, 
                        CASE 
                            WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                            ELSE EXTRACT(YEAR FROM date) - 1
                        END 
                        ORDER BY date DESC
                    ) as rn_end
                FROM player_history
                WHERE player_id = %s
                ORDER BY date DESC
            ),
            career_start AS (
                SELECT end_pti as first_career_pti
                FROM season_data 
                ORDER BY date ASC 
                LIMIT 1
            ),
            season_boundaries AS (
                SELECT 
                    season_year,
                    MIN(date) as season_start_date,
                    MAX(date) as season_end_date,
                    COUNT(*) as matches_count
                FROM season_data
                GROUP BY season_year
                HAVING COUNT(*) >= 3  -- Only show seasons with at least 3 matches
            ),
            season_summary AS (
                SELECT 
                    sb.season_year,
                    CASE 
                        WHEN ROW_NUMBER() OVER (ORDER BY sb.season_year ASC) = 1 THEN 
                            cs.first_career_pti  -- Use career start PTI for first season
                        ELSE 
                            (SELECT end_pti FROM season_data sd WHERE sd.season_year = sb.season_year AND sd.date = sb.season_start_date LIMIT 1)
                    END as pti_start,
                    (SELECT end_pti FROM season_data sd WHERE sd.season_year = sb.season_year AND sd.date = sb.season_end_date LIMIT 1) as pti_end,
                    sb.matches_count,
                    -- Get the series with the highest numeric value (excluding tournaments)
                    (
                        SELECT series 
                        FROM season_data sd2
                        WHERE sd2.season_year = sb.season_year
                        AND POSITION('tournament' IN LOWER(series)) = 0
                        AND POSITION('pti' IN LOWER(series)) = 0
                        AND (
                            series ~ '^Series\s+[0-9]+'
                            OR series ~ '^Division\s+[0-9]+'
                            OR series ~ '^Chicago[:\s]+[0-9]+'
                        )
                        GROUP BY series
                        ORDER BY COUNT(*) DESC, series DESC
                        LIMIT 1
                    ) as most_active_series
                FROM season_boundaries sb
                CROSS JOIN career_start cs
            )
            SELECT 
                most_active_series as series,
                season_year,
                pti_start,
                pti_end,
                (pti_end - pti_start) as trend,
                matches_count
            FROM season_summary
            ORDER BY season_year ASC  -- Earliest seasons first
            LIMIT 10
        """

        # Debug: Let's also run the inner query to see what raw data the aggregation is working with
        debug_season_query = """
            SELECT 
                series,
                CASE 
                    WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                    ELSE EXTRACT(YEAR FROM date) - 1
                END as season_year,
                date,
                end_pti
            FROM player_history
            WHERE player_id = %s 
            ORDER BY season_year, series, date
        """
        debug_season_records = execute_query(debug_season_query, [player_db_id])
        print(f"[DEBUG] Season History - Raw records going into season aggregation:")
        for record in debug_season_records:
            print(
                f"  Season: {record['season_year']}, Series: {record['series']}, Date: {record['date']}, PTI: {record['end_pti']}"
            )

        season_records = execute_query(season_history_query, [player_db_id])

        print(
            f"[DEBUG] Season History - One-per-season query returned {len(season_records) if season_records else 0} records for player_id {player_db_id}"
        )
        if season_records:
            print(
                f"[DEBUG] Season History - One row per season results (NO year repetition):"
            )
            for record in season_records:
                print(
                    f"  Series: {record['series']}, Season: {record['season_year']}, PTI: {record['pti_start']} -> {record['pti_end']}, Matches: {record['matches_count']}"
                )
        
        # ENHANCED DEBUG: Show detailed series selection for 2024-2025 season specifically
        debug_2024_query = """
            SELECT 
                sd.series,
                COUNT(*) as match_count,
                MIN(sd.date) as first_match,
                MAX(sd.date) as last_match
            FROM player_history sd
            WHERE sd.player_id = %s
            AND CASE 
                WHEN EXTRACT(MONTH FROM sd.date) >= 8 THEN EXTRACT(YEAR FROM sd.date)
                ELSE EXTRACT(YEAR FROM sd.date) - 1
            END = 2024
            AND POSITION('tournament' IN LOWER(sd.series)) = 0
            AND POSITION('pti' IN LOWER(sd.series)) = 0
            AND (
                sd.series ~ '^Series\s+[0-9]+'
                OR sd.series ~ '^Division\s+[0-9]+'
                OR sd.series ~ '^Chicago[:\s]+[0-9]+'
            )
            GROUP BY sd.series
            ORDER BY COUNT(*) DESC, sd.series DESC
        """
        debug_2024_results = execute_query(debug_2024_query, [player_db_id])
        print(f"[DEBUG] Season History - 2024-2025 season series breakdown:")
        for record in debug_2024_results:
            print(f"  {record['series']}: {record['match_count']} matches ({record['first_match']} to {record['last_match']})")
        
        if debug_2024_results:
            selected_series = debug_2024_results[0]['series']
            print(f"[DEBUG] Season History - SELECTED for 2024-2025: {selected_series} (with {debug_2024_results[0]['match_count']} matches)")
        else:
            print(f"[DEBUG] Season History - NO SERIES FOUND for 2024-2025 season")

        if not season_records:
            print(
                f"[DEBUG] Season History - No season records found for player {player_id}"
            )
            return jsonify({"error": "No season history found"}), 404

        print(
            f"[DEBUG] Season History - Final results: {len(season_records)} records found"
        )

        # Format season data
        seasons = []
        for record in season_records:
            # Create season string (e.g., "2024-2025" for tennis season)
            season_year = int(record["season_year"])
            next_year = season_year + 1
            season_str = f"{season_year}-{next_year}"

            # Format trend with arrow (positive PTI change = worse performance = red)
            trend_value = float(record["trend"])
            if trend_value > 0:
                trend_display = f"+{trend_value:.1f} ▲"
                trend_class = (
                    "text-red-600"  # Positive = PTI went up = worse performance = red
                )
            elif trend_value < 0:
                trend_display = f"{trend_value:.1f} ▼"
                trend_class = "text-green-600"  # Negative = PTI went down = better performance = green
            else:
                trend_display = "0.0 ─"
                trend_class = "text-gray-500"

            seasons.append(
                {
                    "season": season_str,
                    "series": record["series"],
                    "pti_start": round(float(record["pti_start"]), 1),
                    "pti_end": round(float(record["pti_end"]), 1),
                    "trend": trend_value,
                    "trend_display": trend_display,
                    "trend_class": trend_class,
                    "matches_count": record["matches_count"],
                }
            )

        return jsonify(
            {
                "success": True,
                "seasons": seasons,
                "player_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            }
        )

    except Exception as e:
        print(f"Error fetching season history: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch season history"}), 500


@mobile_bp.route("/api/season-history-by-id/<player_id>")
@login_required
def get_player_season_history_by_id(player_id):
    """API endpoint to get previous season history data for a specific player by ID"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # URL decode the player ID
        from urllib.parse import unquote
        player_id = unquote(player_id)
        
        print(f"[DEBUG] Season History by ID - Player ID: {player_id}")

        # Find the player in the database by tenniscores_player_id, prioritizing the one with PTI history
        # FIXED: Use team context filtering just like /api/season-history endpoint
        from app.services.session_service import get_session_data_for_user
        
        # Get current user's session data to determine team context
        current_user_email = session.get("user", {}).get("email")
        session_data = None
        if current_user_email:
            session_data = get_session_data_for_user(current_user_email)
        
        current_team_id = session_data.get("team_id") if session_data else None
        
        # Get player's database ID - prioritize the player record for current team context
        if current_team_id:
            # First try to get the player record that matches the current team context
            player_query = """
                SELECT 
                    p.id,
                    p.tenniscores_player_id,
                    p.pti as current_pti,
                    p.series_id,
                    p.team_id,
                    s.name as series_name,
                    t.team_name,
                    p.first_name,
                    p.last_name,
                    (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id = %s AND p.team_id = %s
                ORDER BY history_count DESC, p.id DESC
                LIMIT 1
            """
            player_data = execute_query_one(player_query, [player_id, current_team_id])
            print(f"[DEBUG] Season History by ID - Team Context: Using team_id {current_team_id}")
        else:
            # Fallback to any player record if no team context
            player_query = """
                SELECT 
                    p.id,
                    p.tenniscores_player_id,
                    p.pti as current_pti,
                    p.series_id,
                    p.team_id,
                    s.name as series_name,
                    t.team_name,
                    p.first_name,
                    p.last_name,
                    (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id = %s
                ORDER BY history_count DESC, p.id DESC
                LIMIT 1
            """
            player_data = execute_query_one(player_query, [player_id])
            print(f"[DEBUG] Season History by ID - No Team Context: Using fallback query")

        if not player_data:
            print(f"[DEBUG] Season History by ID - Player '{player_id}' not found in database")
            return jsonify({"error": "Player not found"}), 404
        
        # FALLBACK FIX: If the team-specific player has no history, fall back to ANY player with history
        # BUT prioritize player records that match the current team context series if possible
        if player_data["history_count"] == 0:
            print(f"[DEBUG] Season History by ID - Team-specific player has no history, trying intelligent fallback")
            
            # Get current team's series name for preference
            current_team_series = player_data.get("series_name", "")
            
            # First try: Find a player record with history that matches current team's series
            if current_team_series:
                print(f"[DEBUG] Season History by ID - Trying fallback matching current series: {current_team_series}")
                series_specific_fallback = """
                    SELECT 
                        p.id,
                        p.tenniscores_player_id,
                        p.pti as current_pti,
                        p.series_id,
                        p.team_id,
                        s.name as series_name,
                        t.team_name,
                        p.first_name,
                        p.last_name,
                        (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                    FROM players p
                    LEFT JOIN series s ON p.series_id = s.id
                    LEFT JOIN teams t ON p.team_id = t.id
                    WHERE p.tenniscores_player_id = %s
                      AND s.name = %s
                      AND (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) > 0
                    ORDER BY history_count DESC, p.id DESC
                    LIMIT 1
                """
                series_fallback_data = execute_query_one(series_specific_fallback, [player_id, current_team_series])
                
                if series_fallback_data:
                    print(f"[DEBUG] Season History by ID - Series-specific fallback found player with {series_fallback_data['history_count']} history records")
                    player_data = series_fallback_data
                else:
                    print(f"[DEBUG] Season History by ID - No series-specific fallback found, trying any player with history")
            
            # Second try: Any player with history (original fallback)
            if player_data["history_count"] == 0:
                fallback_query = """
                    SELECT 
                        p.id,
                        p.tenniscores_player_id,
                        p.pti as current_pti,
                        p.series_id,
                        p.team_id,
                        s.name as series_name,
                        t.team_name,
                        p.first_name,
                        p.last_name,
                        (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
                    FROM players p
                    LEFT JOIN series s ON p.series_id = s.id
                    LEFT JOIN teams t ON p.team_id = t.id
                    WHERE p.tenniscores_player_id = %s
                      AND (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) > 0
                    ORDER BY history_count DESC, p.id DESC
                    LIMIT 1
                """
                fallback_data = execute_query_one(fallback_query, [player_id])
                
                if fallback_data:
                    print(f"[DEBUG] Season History by ID - General fallback found player with {fallback_data['history_count']} history records")
                    player_data = fallback_data
                else:
                    print(f"[DEBUG] Season History by ID - No fallback player with history found")
                    return jsonify({"error": "No season history found"}), 404

        player_db_id = player_data["id"]

        # Get current series for prioritization
        current_series_name = player_data.get("series_name", "")
        
        # Debug logging
        print(f"[DEBUG] Season History by ID - Found player: {player_data['first_name']} {player_data['last_name']}")
        print(f"[DEBUG] Season History by ID - Player DB ID: {player_db_id}")
        print(f"[DEBUG] Season History by ID - History count: {player_data['history_count']}")
        print(f"[DEBUG] Season History by ID - Current series: {current_series_name}")
        print(f"[DEBUG] Season History by ID - Current series will get PRIORITY 1 in selection logic")

        # ✅ FIXED: Get season history with current series prioritization
        season_history_query = """
            WITH season_data AS (
                SELECT 
                    series,
                    CASE 
                        WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                        ELSE EXTRACT(YEAR FROM date) - 1
                    END as season_year,
                    date,
                    end_pti
                FROM player_history
                WHERE player_id = %s
                ORDER BY date DESC
            ),
            career_start AS (
                SELECT end_pti as first_career_pti
                FROM season_data 
                ORDER BY date ASC 
                LIMIT 1
            ),
            season_boundaries AS (
                SELECT 
                    season_year,
                    MIN(date) as season_start_date,
                    MAX(date) as season_end_date,
                    COUNT(*) as matches_count
                FROM season_data
                GROUP BY season_year
                HAVING COUNT(*) >= 3  -- Only show seasons with at least 3 matches
            ),
            season_summary AS (
                SELECT 
                    sb.season_year,
                    CASE 
                        WHEN ROW_NUMBER() OVER (ORDER BY sb.season_year ASC) = 1 THEN 
                            cs.first_career_pti
                        ELSE 
                            (SELECT end_pti FROM season_data sd WHERE sd.season_year = sb.season_year AND sd.date = sb.season_start_date LIMIT 1)
                    END as pti_start,
                    (SELECT end_pti FROM season_data sd WHERE sd.season_year = sb.season_year AND sd.date = sb.season_end_date LIMIT 1) as pti_end,
                    sb.matches_count,
                    (
                        SELECT series 
                        FROM season_data sd2
                        WHERE sd2.season_year = sb.season_year
                        AND POSITION('tournament' IN LOWER(series)) = 0
                        AND POSITION('pti' IN LOWER(series)) = 0
                        AND (
                            series ~ '^Series\\s+[0-9]+'
                            OR series ~ '^Division\\s+[0-9]+'
                            OR series ~ '^Chicago[:\\s]+[0-9]+'
                        )
                        -- ✅ FIXED: Now prioritize by match count (most matches wins)
                        GROUP BY series
                        ORDER BY COUNT(*) DESC, series DESC
                        LIMIT 1
                    ) as preferred_series
                FROM season_boundaries sb
                CROSS JOIN career_start cs
            )
            SELECT 
                preferred_series as series,
                season_year,
                pti_start,
                pti_end,
                (pti_end - pti_start) as trend,
                matches_count
            FROM season_summary
            ORDER BY season_year ASC
            LIMIT 10
        """

        season_records = execute_query(season_history_query, [player_db_id])

        print(f"[DEBUG] Season History by ID - Query returned {len(season_records) if season_records else 0} records")
        
        # ENHANCED DEBUG: Show detailed series selection for 2024-2025 season specifically
        debug_2024_query = """
            SELECT 
                sd.series,
                COUNT(*) as match_count,
                MIN(sd.date) as first_match,
                MAX(sd.date) as last_match
            FROM player_history sd
            WHERE sd.player_id = %s
            AND CASE 
                WHEN EXTRACT(MONTH FROM sd.date) >= 8 THEN EXTRACT(YEAR FROM sd.date)
                ELSE EXTRACT(YEAR FROM sd.date) - 1
            END = 2024
            AND POSITION('tournament' IN LOWER(sd.series)) = 0
            AND POSITION('pti' IN LOWER(sd.series)) = 0
            AND (
                sd.series ~ '^Series\\s+[0-9]+'
                OR sd.series ~ '^Division\\s+[0-9]+'
                OR sd.series ~ '^Chicago[:\\s]+[0-9]+'
            )
            GROUP BY sd.series
            ORDER BY COUNT(*) DESC, sd.series DESC
        """
        debug_2024_results = execute_query(debug_2024_query, [player_db_id])
        print(f"[DEBUG] Season History by ID - 2024-2025 season series breakdown:")
        for record in debug_2024_results:
            print(f"  {record['series']}: {record['match_count']} matches ({record['first_match']} to {record['last_match']})")
        
        if debug_2024_results:
            selected_series = debug_2024_results[0]['series']
            print(f"[DEBUG] Season History by ID - SHOULD SELECT for 2024-2025: {selected_series} (with {debug_2024_results[0]['match_count']} matches)")
        else:
            print(f"[DEBUG] Season History by ID - NO SERIES FOUND for 2024-2025 season")
            
        # DEBUG: Show what the current query actually selected for 2024-2025
        for record in season_records:
            if record['season_year'] == 2024:
                print(f"[DEBUG] Season History by ID - ACTUALLY SELECTED for 2024-2025: {record['series']}")
                break

        if not season_records:
            print(f"[DEBUG] Season History by ID - No season records found for player {player_id}")
            return jsonify({"error": "No season history found"}), 404

        # Format season data
        seasons = []
        for record in season_records:
            season_year = int(record["season_year"])
            next_year = season_year + 1
            season_str = f"{season_year}-{next_year}"

            trend_value = float(record["trend"])
            if trend_value > 0:
                trend_display = f"+{trend_value:.1f} ▲"
                trend_class = "text-red-600"
            elif trend_value < 0:
                trend_display = f"{trend_value:.1f} ▼"
                trend_class = "text-green-600"
            else:
                trend_display = "0.0 ─"
                trend_class = "text-gray-500"

            seasons.append({
                "season": season_str,
                "series": record["series"],
                "pti_start": round(float(record["pti_start"]), 1),
                "pti_end": round(float(record["pti_end"]), 1),
                "trend": trend_value,
                "trend_display": trend_display,
                "trend_class": trend_class,
                "matches_count": record["matches_count"],
            })

        return jsonify({
            "success": True,
            "seasons": seasons,
            "player_name": f"{player_data['first_name']} {player_data['last_name']}",
        })

    except Exception as e:
        print(f"Error fetching season history by ID: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch season history"}), 500


@mobile_bp.route("/api/season-history/<player_name>")
@login_required
def get_player_season_history(player_name):
    """API endpoint to get previous season history data for a specific player"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # URL decode the player name
        from urllib.parse import unquote

        player_name = unquote(player_name)

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
                last_name = " ".join(name_parts[1:])
        
        if not first_name or not last_name:
            return jsonify({"error": f"Invalid player name format: {player_name}"}), 400

        # Find the player in the database by name, prioritizing the one with PTI history
        player_query = """
            SELECT 
                p.id,
                p.tenniscores_player_id,
                p.pti as current_pti,
                p.series_id,
                s.name as series_name,
                p.first_name,
                p.last_name,
                (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.first_name = %s AND p.last_name = %s
            ORDER BY history_count DESC, p.id DESC
            LIMIT 1
        """
        player_data = execute_query_one(player_query, [first_name, last_name])

        if not player_data:
            print(f"[DEBUG] Player Season History - Player '{player_name}' not found in database")
            return jsonify({"error": "Player not found"}), 404

        player_db_id = player_data["id"]
        tenniscores_player_id = player_data["tenniscores_player_id"]

        # Debug logging
        print(f"[DEBUG] Player Season History - Player Name: {player_name}")
        print(f"[DEBUG] Player Season History - Player DB ID: {player_db_id}")
        print(f"[DEBUG] Player Season History - TennisCore ID: {tenniscores_player_id}")
        print(f"[DEBUG] Player Season History - Player Series: {player_data.get('series_name')}")

        # Get season history using the team-specific player record
        # Fixed to show ONE row per season instead of multiple rows per series
        season_history_query = """
            WITH season_data AS (
                SELECT 
                    series,
                    -- Calculate tennis season year (Aug-May spans two calendar years)
                    CASE 
                        WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                        ELSE EXTRACT(YEAR FROM date) - 1
                    END as season_year,
                    date,
                    end_pti,
                    ROW_NUMBER() OVER (
                        PARTITION BY series, 
                        CASE 
                            WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                            ELSE EXTRACT(YEAR FROM date) - 1
                        END 
                        ORDER BY date ASC
                    ) as rn_start,
                    ROW_NUMBER() OVER (
                        PARTITION BY series, 
                        CASE 
                            WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                            ELSE EXTRACT(YEAR FROM date) - 1
                        END 
                        ORDER BY date DESC
                    ) as rn_end
                FROM player_history
                WHERE player_id = %s
                ORDER BY date DESC
            ),
            career_start AS (
                SELECT end_pti as first_career_pti
                FROM season_data 
                ORDER BY date ASC 
                LIMIT 1
            ),
            season_boundaries AS (
                SELECT 
                    season_year,
                    MIN(date) as season_start_date,
                    MAX(date) as season_end_date,
                    COUNT(*) as matches_count
                FROM season_data
                GROUP BY season_year
                HAVING COUNT(*) >= 3  -- Only show seasons with at least 3 matches
            ),
            season_summary AS (
                SELECT 
                    sb.season_year,
                    CASE 
                        WHEN ROW_NUMBER() OVER (ORDER BY sb.season_year ASC) = 1 THEN 
                            cs.first_career_pti  -- Use career start PTI for first season
                        ELSE 
                            (SELECT end_pti FROM season_data sd WHERE sd.season_year = sb.season_year AND sd.date = sb.season_start_date LIMIT 1)
                    END as pti_start,
                    (SELECT end_pti FROM season_data sd WHERE sd.season_year = sb.season_year AND sd.date = sb.season_end_date LIMIT 1) as pti_end,
                    sb.matches_count,
                    -- Get the series with the highest numeric value (excluding tournaments)
                    (
                        SELECT series 
                        FROM season_data sd2
                        WHERE sd2.season_year = sb.season_year
                        AND POSITION('tournament' IN LOWER(series)) = 0
                        AND POSITION('pti' IN LOWER(series)) = 0
                        AND (
                            series ~ '^Series\s+[0-9]+'
                            OR series ~ '^Division\s+[0-9]+'
                            OR series ~ '^Chicago[:\s]+[0-9]+'
                        )
                        GROUP BY series
                        ORDER BY COUNT(*) DESC, series DESC
                        LIMIT 1
                    ) as most_active_series
                FROM season_boundaries sb
                CROSS JOIN career_start cs
            )
            SELECT 
                most_active_series as series,
                season_year,
                pti_start,
                pti_end,
                (pti_end - pti_start) as trend,
                matches_count
            FROM season_summary
            ORDER BY season_year ASC  -- Earliest seasons first
            LIMIT 10
        """

        season_records = execute_query(season_history_query, [player_db_id])

        print(
            f"[DEBUG] Player Season History - Player ID {player_db_id} query returned {len(season_records) if season_records else 0} records"
        )
        
        # ENHANCED DEBUG: Show 2024-2025 series selection for this endpoint too
        debug_2024_query = """
            SELECT 
                sd.series,
                COUNT(*) as match_count,
                MIN(sd.date) as first_match,
                MAX(sd.date) as last_match
            FROM player_history sd
            WHERE sd.player_id = %s
            AND CASE 
                WHEN EXTRACT(MONTH FROM sd.date) >= 8 THEN EXTRACT(YEAR FROM sd.date)
                ELSE EXTRACT(YEAR FROM sd.date) - 1
            END = 2024
            AND POSITION('tournament' IN LOWER(sd.series)) = 0
            AND POSITION('pti' IN LOWER(sd.series)) = 0
            AND (
                sd.series ~ '^Series\s+[0-9]+'
                OR sd.series ~ '^Division\s+[0-9]+'
                OR sd.series ~ '^Chicago[:\s]+[0-9]+'
            )
            GROUP BY sd.series
            ORDER BY COUNT(*) DESC, sd.series DESC
        """
        debug_2024_results = execute_query(debug_2024_query, [player_db_id])
        print(f"[DEBUG] Player Season History - 2024-2025 season series breakdown:")
        for record in debug_2024_results:
            print(f"  {record['series']}: {record['match_count']} matches ({record['first_match']} to {record['last_match']})")
        
        if debug_2024_results:
            selected_series = debug_2024_results[0]['series']
            print(f"[DEBUG] Player Season History - SELECTED for 2024-2025: {selected_series} (with {debug_2024_results[0]['match_count']} matches)")
        else:
            print(f"[DEBUG] Player Season History - NO SERIES FOUND for 2024-2025 season")

        # SECOND: If no records found with player_id, try matching by tenniscores_player_id in the match data
        # This is a more targeted approach than the broad series matching
        if not season_records and tenniscores_player_id:
            print(
                f"[DEBUG] Player Season History - Trying tenniscores_player_id matching for {tenniscores_player_id}"
            )

            # Look for player_history records that might match this specific player by name patterns
            name_based_query = """
                WITH player_matches AS (
                    -- Find all player_history records where the player name matches our target player
                    SELECT ph.*, p2.first_name, p2.last_name
                    FROM player_history ph
                    JOIN players p2 ON ph.player_id = p2.id
                    WHERE p2.tenniscores_player_id = %s
                      OR (p2.first_name = %s AND p2.last_name = %s)
                ),
                season_data AS (
                    SELECT 
                        series,
                        CASE 
                            WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                            ELSE EXTRACT(YEAR FROM date) - 1
                        END as season_year,
                        date,
                        end_pti,
                        ROW_NUMBER() OVER (
                            PARTITION BY series, 
                            CASE 
                                WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                                ELSE EXTRACT(YEAR FROM date) - 1
                            END 
                            ORDER BY date ASC
                        ) as rn_start,
                        ROW_NUMBER() OVER (
                            PARTITION BY series, 
                            CASE 
                                WHEN EXTRACT(MONTH FROM date) >= 8 THEN EXTRACT(YEAR FROM date)
                                ELSE EXTRACT(YEAR FROM date) - 1
                            END 
                            ORDER BY date DESC
                        ) as rn_end
                    FROM player_matches
                    ORDER BY date DESC
                ),
                season_summary AS (
                    SELECT 
                        series,
                        season_year,
                        MAX(CASE WHEN rn_start = 1 THEN end_pti END) as pti_start,
                        MAX(CASE WHEN rn_end = 1 THEN end_pti END) as pti_end,
                        COUNT(*) as matches_count
                    FROM season_data
                    GROUP BY series, season_year
                    HAVING COUNT(*) >= 3
                )
                SELECT 
                    series,
                    season_year,
                    pti_start,
                    pti_end,
                    (pti_end - pti_start) as trend,
                    matches_count
                FROM season_summary
                ORDER BY season_year ASC, series
                LIMIT 10
            """

            season_records = execute_query(
                name_based_query,
                [
                    tenniscores_player_id,
                    player_data["first_name"],
                    player_data["last_name"],
                ],
            )

            print(
                f"[DEBUG] Player Season History - Name-based query returned {len(season_records) if season_records else 0} records"
            )

        if not season_records:
            print(
                f"[DEBUG] Player Season History - No season records found for player {player_name}"
            )
            return jsonify({"error": "No season history found"}), 404

        print(
            f"[DEBUG] Player Season History - Final results: {len(season_records)} records found for {player_name}"
        )
        for record in season_records:
            print(
                f"  Series: {record['series']}, Season: {record['season_year']}, PTI: {record['pti_start']} -> {record['pti_end']}"
            )

        # Format season data
        seasons = []
        for record in season_records:
            # Create season string (e.g., "2024-2025" for tennis season)
            season_year = int(record["season_year"])
            next_year = season_year + 1
            season_str = f"{season_year}-{next_year}"

            # Format trend with arrow (positive PTI change = worse performance = red)
            trend_value = float(record["trend"])
            if trend_value > 0:
                trend_display = f"+{trend_value:.1f} ▲"
                trend_class = (
                    "text-red-600"  # Positive = PTI went up = worse performance = red
                )
            elif trend_value < 0:
                trend_display = f"{trend_value:.1f} ▼"
                trend_class = "text-green-600"  # Negative = PTI went down = better performance = green
            else:
                trend_display = "0.0 ─"
                trend_class = "text-gray-500"

            seasons.append(
                {
                    "season": season_str,
                    "series": record["series"],
                    "pti_start": round(float(record["pti_start"]), 1),
                    "pti_end": round(float(record["pti_end"]), 1),
                    "trend": trend_value,
                    "trend_display": trend_display,
                    "trend_class": trend_class,
                    "matches_count": record["matches_count"],
                }
            )

        return jsonify(
            {"success": True, "seasons": seasons, "player_name": player_name}
        )

    except Exception as e:
        print(f"Error fetching player season history: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch season history"}), 500


@mobile_bp.route("/impersonate")
@login_required
def serve_impersonate():
    """Serve the team impersonation page"""
    try:
        user = session["user"]
        user_email = user["email"]
        
        # Get user's current team context
        team_id = user.get("team_id")
        if not team_id:
            return render_template("mobile/impersonate.html", 
                                 error="No team context found. Please ensure you're properly associated with a team.",
                                 team_members=[])
        
        # Get team members for impersonation
        team_members = get_team_members_for_impersonation(team_id, user_email)
        
        return render_template("mobile/impersonate.html", 
                             team_members=team_members,
                             current_user_email=user_email)
        
    except Exception as e:
        print(f"Error in serve_impersonate: {e}")
        return render_template("mobile/impersonate.html", 
                             error="Failed to load team members",
                             team_members=[])


def get_team_members_for_impersonation(team_id, current_user_email):
    """Get team members that can be impersonated by the current user"""
    try:
        query = """
            SELECT DISTINCT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                p.tenniscores_player_id,
                p.team_id,
                t.team_name,
                c.name as club_name,
                s.name as series_name,
                l.league_name
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            JOIN teams t ON p.team_id = t.id
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            JOIN leagues l ON p.league_id = l.id
            WHERE p.team_id = %s
            AND p.is_active = TRUE
            AND u.email != %s
            ORDER BY u.first_name, u.last_name
        """
        
        results = execute_query(query, [team_id, current_user_email])
        
        team_members = []
        for row in results:
            team_members.append({
                "id": row["id"],
                "email": row["email"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "tenniscores_player_id": row["tenniscores_player_id"],
                "team_id": row["team_id"],
                "team_name": row["team_name"],
                "club_name": row["club_name"],
                "series_name": row["series_name"],
                "league_name": row["league_name"],
                "display_name": f"{row['first_name']} {row['last_name']} ({row['email']})"
            })
        
        return team_members
        
    except Exception as e:
        print(f"Error getting team members for impersonation: {e}")
        return []


@mobile_bp.route("/api/team-impersonation/start", methods=["POST"])
@login_required
def start_team_impersonation():
    """Start impersonating a team member"""
    try:
        data = request.get_json()
        target_email = data.get("user_email")
        target_player_id = data.get("tenniscores_player_id")
        
        if not target_email:
            return jsonify({"error": "User email is required"}), 400
        
        # Get current user's team context
        current_user = session["user"]
        current_team_id = current_user.get("team_id")
        current_user_email = current_user["email"]
        
        if not current_team_id:
            return jsonify({"error": "No team context found"}), 400
        
        # Verify the target user is on the same team
        target_user_query = """
            SELECT DISTINCT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.is_admin,
                p.tenniscores_player_id,
                p.team_id,
                t.team_name,
                c.name as club_name,
                s.name as series_name,
                l.league_name
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            JOIN teams t ON p.team_id = t.id
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            JOIN leagues l ON p.league_id = l.id
            WHERE u.email = %s
            AND p.team_id = %s
            AND p.is_active = TRUE
        """
        
        target_user = execute_query_one(target_user_query, [target_email, current_team_id])
        
        if not target_user:
            return jsonify({"error": "User not found on your team"}), 404
        
        # Prevent impersonating admins
        if target_user.get("is_admin"):
            return jsonify({"error": "Cannot impersonate admin users"}), 403
        
        # Prevent self-impersonation
        if target_email == current_user_email:
            return jsonify({"error": "Cannot impersonate yourself"}), 400
        
        # Backup current session
        original_session = {
            "user": current_user,
            "impersonation_active": False
        }
        
        # Build target user session data
        from app.services.session_service import get_session_data_for_user_team
        
        target_session_data = get_session_data_for_user_team(target_email, current_team_id)
        
        if not target_session_data:
            return jsonify({"error": "Failed to build session data for target user"}), 500
        
        # Store impersonation state
        session["impersonation_active"] = True
        session["original_user_session"] = original_session
        session["impersonated_user_email"] = target_email
        session["impersonated_player_id"] = target_player_id
        session["impersonation_type"] = "team"  # Distinguish from admin impersonation
        
        # Replace current session with target user's session
        session["user"] = target_session_data
        session.modified = True
        
        # Log the impersonation
        log_user_activity(
            current_user_email,
            "team_impersonation",
            action="start_impersonation",
            details=f"Started impersonating team member: {target_email} ({target_user['first_name']} {target_user['last_name']})"
        )
        
        return jsonify({
            "success": True,
            "message": f"Successfully started impersonating {target_user['first_name']} {target_user['last_name']}",
            "impersonated_user": {
                "email": target_email,
                "first_name": target_user["first_name"],
                "last_name": target_user["last_name"],
                "team_name": target_user["team_name"],
                "club_name": target_user["club_name"],
                "series_name": target_user["series_name"]
            }
        })
        
    except Exception as e:
        print(f"Error in start_team_impersonation: {e}")
        return jsonify({"error": f"Failed to start impersonation: {str(e)}"}), 500


@mobile_bp.route("/api/team-impersonation/stop", methods=["POST"])
@login_required
def stop_team_impersonation():
    """Stop team impersonation and restore original session"""
    try:
        # Check if currently impersonating
        if not session.get("impersonation_active") or session.get("impersonation_type") != "team":
            return jsonify({"error": "Not currently impersonating a team member"}), 400
        
        # Get original session
        original_session = session.get("original_user_session")
        impersonated_email = session.get("impersonated_user_email")
        
        if not original_session:
            return jsonify({"error": "Original session not found"}), 500
        
        # Restore original session
        session["user"] = original_session["user"]
        
        # Clear impersonation state
        session.pop("impersonation_active", None)
        session.pop("original_user_session", None)
        session.pop("impersonated_user_email", None)
        session.pop("impersonated_player_id", None)
        session.pop("impersonation_type", None)
        session.modified = True
        
        # Log the impersonation stop
        current_user_email = session["user"]["email"]
        log_user_activity(
            current_user_email,
            "team_impersonation",
            action="stop_impersonation",
            details=f"Stopped impersonating team member: {impersonated_email}"
        )
        
        return jsonify({
            "success": True,
            "message": "Successfully stopped impersonation and restored your session"
        })
        
    except Exception as e:
        print(f"Error in stop_team_impersonation: {e}")
        return jsonify({"error": f"Failed to stop impersonation: {str(e)}"}), 500


@mobile_bp.route("/api/team-impersonation/status")
@login_required
def get_team_impersonation_status():
    """Get current team impersonation status"""
    try:
        is_impersonating = session.get("impersonation_active", False)
        impersonation_type = session.get("impersonation_type")
        
        if is_impersonating and impersonation_type == "team":
            impersonated_email = session.get("impersonated_user_email")
            current_user = session["user"]
            
            return jsonify({
                "is_impersonating": True,
                "impersonation_type": "team",
                "impersonated_user": {
                    "email": impersonated_email,
                    "first_name": current_user.get("first_name"),
                    "last_name": current_user.get("last_name"),
                    "team_name": current_user.get("team_name"),
                    "club_name": current_user.get("club"),
                    "series_name": current_user.get("series")
                }
            })
        else:
            return jsonify({
                "is_impersonating": False,
                "impersonation_type": None
            })
            
    except Exception as e:
        print(f"Error in get_team_impersonation_status: {e}")
        return jsonify({"error": f"Failed to get impersonation status: {str(e)}"}), 500


@mobile_bp.route("/mobile/my-team")
@login_required
def serve_mobile_my_team():
    """Serve the mobile My Team page"""
    try:
        # Use session service to get fresh session data (same pattern as working routes)
        from app.services.session_service import get_session_data_for_user
        
        user_email = session["user"]["email"]
        
        # Check if we're currently impersonating - if so, preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            session_user = session["user"]
        else:
            # Use helper function to determine if we should preserve session or refresh
            current_session = session.get("user", {})
            
            if should_preserve_session_context(user_email, current_session):
                # Preserve current session (team switch protection + no league switch detected)
                print(f"[DEBUG] My-team - Preserving existing team context: {current_session.get('club')} - {current_session.get('series')}")
                session_user = current_session
            else:
                # Session is incomplete, invalid, or league switch detected - refresh from database
                print(f"[DEBUG] My-team - Session incomplete or league switch detected, refreshing from database")
                fresh_session_data = get_session_data_for_user(user_email)
                
                if fresh_session_data:
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_user = fresh_session_data
                    print(f"[DEBUG] My-team - Refreshed session data: {fresh_session_data.get('tenniscores_player_id')} in {fresh_session_data.get('league_name')} team {fresh_session_data.get('team_id')}")
                else:
                    session_user = session["user"]
                    print(f"[DEBUG] My-team - Using existing session data")

        result = get_mobile_team_data(session_user)

        session_data = {"user": session_user, "authenticated": True}

        log_user_activity(session_user["email"], "page_visit", page="mobile_my_team")

        # Get last updated timestamp from match_scores table
        last_updated = None
        try:
            last_updated_result = execute_query_one(
                "SELECT MAX(created_at) as last_updated FROM match_scores"
            )
            if last_updated_result and last_updated_result.get("last_updated"):
                last_updated = last_updated_result["last_updated"]
        except Exception as e:
            print(f"[WARNING] Could not fetch last_updated timestamp: {e}")

        # Extract all data from result
        team_data = result.get("team_data")
        court_analysis = result.get("court_analysis", {})
        top_players = result.get("top_players", [])
        team_matches = result.get("team_matches", [])
        team_videos = result.get("team_videos", [])
        strength_of_schedule = result.get("strength_of_schedule", {})
        error = result.get("error")

        response = render_template(
            "mobile/my_team.html",
            session_data=session_data,
            team_data=team_data,
            court_analysis=court_analysis,
            top_players=top_players,
            team_matches=team_matches,
            team_videos=team_videos,
            strength_of_schedule=strength_of_schedule,
            error=error,
            last_updated=last_updated,
        )
        
        # Add cache-busting headers to ensure fresh data
        from flask import make_response
        response = make_response(response)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Last-Modified'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        
        return response

    except Exception as e:
        print(f"Error serving mobile my team: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        session_data = {"user": session["user"], "authenticated": True}

        return render_template(
            "mobile/my_team.html",
            session_data=session_data,
            team_data=None,
            court_analysis={},
            top_players=[],
            team_videos=[],
            strength_of_schedule={
                "sos_value": 0.0,
                "rank": 0,
                "total_teams": 0,
                "opponents_count": 0,
                "all_teams_sos": [],
                "user_team_name": "",
                "error": "Failed to load team data",
            },
            error="Failed to load team data",
        )


@mobile_bp.route("/mobile/myteam")
@login_required
def serve_mobile_myteam():
    """Redirect from old myteam path to my-team"""
    return redirect(url_for("mobile.serve_mobile_my_team"))


@mobile_bp.route("/mobile/settings")
@login_required
def serve_mobile_settings():
    """Serve the mobile settings page"""
    try:
        # Use session service to get fresh session data, BUT preserve team switches (same as main mobile route)
        from app.services.session_service import get_session_data_for_user
        
        user_email = session["user"]["email"]
        
        # Check if we're currently impersonating - if so, ALWAYS preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            # During impersonation, never rebuild session - preserve manual selections
            session_user = session["user"]
            print(f"[DEBUG] Settings: Impersonation active - preserving session as-is")
        else:
            # Use helper function to determine if we should preserve session or refresh
            current_session = session.get("user", {})
            
            # ALWAYS refresh session data for settings page to show latest personal data
            print(f"[DEBUG] Settings: Always refreshing from database to show latest personal data")
            fresh_session_data = get_session_data_for_user(user_email)
            
            if fresh_session_data:
                # Update Flask session with fresh data
                session["user"] = fresh_session_data
                session.modified = True
                session_user = fresh_session_data
                print(f"[DEBUG] Settings: Using fresh session data with latest personal info")
            else:
                # Fallback to existing session
                session_user = session["user"]
                print(f"[DEBUG] Settings: Using fallback session data: {session['user']}")

        session_data = {"user": session_user, "authenticated": True}

        log_user_activity(user_email, "page_visit", page="mobile_settings")
        return render_template("mobile/user_settings.html", session_data=session_data)
        
    except Exception as e:
        print(f"Error serving mobile settings: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        # Fallback to basic session data
        session_data = {"user": session["user"], "authenticated": True}
        log_user_activity(session["user"]["email"], "page_visit", page="mobile_settings")
        return render_template("mobile/user_settings.html", session_data=session_data)


@mobile_bp.route("/mobile/my-series")
@login_required
def serve_mobile_my_series():
    """Serve the mobile My Series page"""
    print(f"🏆 MY-SERIES ROUTE CALLED for user: {session.get('user', {}).get('email', 'unknown')}")
    try:
        # Use session service to get fresh session data (same pattern as working routes)
        from app.services.session_service import get_session_data_for_user
        
        user_email = session["user"]["email"]
        
        # Check if we're currently impersonating - if so, preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            session_user = session["user"]
        else:
            # Check if current session has valid team context - if so, preserve it
            current_session = session.get("user", {})
            has_valid_team_context = (
                current_session.get("team_id") is not None and
                current_session.get("league_id") is not None and
                current_session.get("club") and
                current_session.get("series")
            )
            
            if has_valid_team_context:
                session_user = current_session
            else:
                # Session is incomplete or invalid, refresh from database
                fresh_session_data = get_session_data_for_user(user_email)
                
                if fresh_session_data:
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_user = fresh_session_data
                else:
                    session_user = session["user"]

        print(f"🔍 Getting series data for user: {session_user}")
        series_data = get_mobile_series_data(session_user)
        print(f"✅ Series data retrieved: {'error' in series_data}")

        session_data = {"user": session_user, "authenticated": True}
        print(f"✅ Session data created")

        # Get last updated timestamp from match_scores table
        last_updated = None
        try:
            last_updated_result = execute_query_one(
                "SELECT MAX(created_at) as last_updated FROM match_scores"
            )
            if last_updated_result and last_updated_result.get("last_updated"):
                last_updated = last_updated_result["last_updated"]
        except Exception as e:
            print(f"[WARNING] Could not fetch last_updated timestamp: {e}")

        print(f"📱 Calling log_user_activity for my-series...")
        log_result = log_user_activity(
            session_user["email"], 
            "page_visit", 
            page="mobile_my_series",
            first_name=session_user.get("first_name"),
            last_name=session_user.get("last_name")
        )
        print(f"✅ Activity logged: {log_result}")

        print(f"🎨 Rendering template...")
        return render_template(
            "mobile/my_series.html", session_data=session_data, last_updated=last_updated, **series_data
        )

    except Exception as e:
        print(f"❌ ERROR in my-series route: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

        session_data = {"user": session.get("user", {}), "authenticated": True}

        return render_template(
            "mobile/my_series.html",
            session_data=session_data,
            error="Failed to load series data",
        )


@mobile_bp.route("/mobile/myseries")
@login_required
def redirect_myseries():
    """Redirect from old myseries path to my-series"""
    return redirect(url_for("mobile.serve_mobile_my_series"))


@mobile_bp.route("/mobile/teams-players", methods=["GET"])
@login_required
def mobile_teams_players():
    """Get teams and players for mobile interface - now supports team_id parameter"""
    try:
        # Handle legacy team name parameter and redirect to team_id
        legacy_team_name = request.args.get("team")
        if legacy_team_name:
            print(f"[DEBUG] teams-players: Legacy team name parameter detected: {legacy_team_name}")
            # Try to find team_id for this team name
            user = session["user"]
            user_league_id = user.get("league_id", "")
            
            # Convert league_id to integer if needed
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
            
            # Find team by name and redirect to team_id URL
            if league_id_int:
                team_lookup_query = """
                    SELECT id FROM teams 
                    WHERE team_name = %s AND league_id = %s AND is_active = TRUE
                """
                team_record = execute_query_one(team_lookup_query, [legacy_team_name, league_id_int])
                if team_record:
                    return redirect(f"/mobile/teams-players?team_id={team_record['id']}")
            
            # If not found, continue without team selection
            print(f"[DEBUG] teams-players: Could not find team_id for legacy team name: {legacy_team_name}")
        
        # Get team_id parameter from URL
        team_id = request.args.get("team_id")
        
        # Convert to integer if provided
        if team_id:
            try:
                team_id = int(team_id)
                print(f"[DEBUG] teams-players: Using team_id={team_id}")
            except (ValueError, TypeError):
                print(f"[DEBUG] teams-players: Invalid team_id parameter: {team_id}")
                team_id = None
        
        # Get teams and players data with team_id filtering
        data = get_teams_players_data(session["user"], team_id=team_id)

        # Add template compatibility variables
        template_data = {
            "session_data": {"user": session["user"], "authenticated": True},
            "all_teams_data": data.get("all_teams_data", []),
            "selected_team": data.get("selected_team"),
            "selected_team_id": data.get("selected_team_id"),
            "team_analysis_data": data.get("team_analysis_data"),
            "team_roster": data.get("team_roster", []),  # Add team roster data
            "error": data.get("error")
        }

        selected_team = data.get("selected_team")
        selected_team_id = data.get("selected_team_id")
        all_teams_data = data.get("all_teams_data", [])
        print(f"[DEBUG] selected_team: {selected_team}")
        print(f"[DEBUG] selected_team_id: {selected_team_id}")
        team_name = None
        if selected_team:
            if isinstance(selected_team, dict) and "team_name" in selected_team:
                team_name = selected_team["team_name"]
            elif isinstance(selected_team, str):
                team_name = selected_team
        elif selected_team_id and all_teams_data:
            # Try to find the team in all_teams_data
            for team in all_teams_data:
                if team.get("id") == selected_team_id and "team_name" in team:
                    team_name = team["team_name"]
                    break
        if not team_name:
            team_name = session["user"].get("club", "Unknown")
        log_user_activity(
            session["user"]["email"],
            "page_visit",
            page="mobile_teams_players",
            details=f"Competitive Teams Page: {team_name}"
        )

        return render_template("mobile/teams_players.html", **template_data)

    except Exception as e:
        print(f"Error in mobile teams players: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        # Try to get at least the teams data for the dropdown, even if there's an error
        try:
            fallback_data = get_teams_players_data(session["user"], team_id=None)
            all_teams_data = fallback_data.get("all_teams_data", [])
        except:
            all_teams_data = []

        return render_template(
            "mobile/teams_players.html",
            session_data={"user": session["user"], "authenticated": True},
            all_teams_data=all_teams_data,
            selected_team=None,
            selected_team_id=None,
            team_analysis_data=None,
            error="Failed to load teams and players data",
        )


@mobile_bp.route("/mobile/player-search", methods=["GET"])
@login_required
def mobile_player_search():
    """Serve the mobile player search page with enhanced fuzzy matching"""
    try:
        search_data = get_player_search_data(session["user"])

        # Enhanced logging for search activity with detailed information
        if search_data.get("search_attempted") and search_data.get("search_query"):
            matching_count = len(search_data.get("matching_players", []))
            
            # Create detailed search log
            search_details = {
                "search_query": search_data["search_query"],
                "first_name": search_data.get("first_name", ""),
                "last_name": search_data.get("last_name", ""),
                "results_count": matching_count,
                "user_league": session["user"].get("league_id", "Unknown"),
                "user_club": session["user"].get("club", "Unknown")
            }
            # Add filters_applied summary
            filters = []
            first = search_data.get("first_name")
            last = search_data.get("last_name")
            if first and last:
                filters.append(f"name: {first} {last}")
            elif first:
                filters.append(f"name: {first}")
            elif last:
                filters.append(f"name: {last}")
            if search_data.get("series"): filters.append(f"series: {search_data['series']}")
            if search_data.get("pti_min"): filters.append(f"PTI min: {search_data['pti_min']}")
            if search_data.get("pti_max"): filters.append(f"PTI max: {search_data['pti_max']}")
            filters_applied = ", ".join(filters) if filters else "no filters"
            search_details["filters_applied"] = filters_applied
            
            # Add details about the results if any found
            if matching_count > 0:
                result_names = [player.get("name", "Unknown") for player in search_data.get("matching_players", [])[:3]]
                search_details["top_results"] = result_names
            
            log_user_activity(
                session["user"]["email"],
                "player_search",
                action="search_executed",
                details=search_details
            )

        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_player_search"
        )

        return render_template(
            "mobile/player_search.html", session_data=session_data, **search_data
        )

    except Exception as e:
        print(f"Error in mobile player search: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        session_data = {"user": session["user"], "authenticated": True}

        return render_template(
            "mobile/player_search.html",
            session_data=session_data,
            first_name="",
            last_name="",
            search_attempted=False,
            matching_players=[],
            search_query=None,
            error="Failed to load player search data",
        )


@mobile_bp.route("/mobile/my-club")
@login_required
def my_club():
    """Serve the mobile My Club page"""
    print(f"🏆 MY-CLUB ROUTE CALLED for user: {session.get('user', {}).get('email', 'unknown')}")
    try:
        # Use session service to get fresh session data (same pattern as working routes)
        from app.services.session_service import get_session_data_for_user
        
        user_email = session["user"]["email"]
        
        # Check if we're currently impersonating - if so, preserve session
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            session_user = session["user"]
        else:
            # Check if current session has valid team context - if so, preserve it
            current_session = session.get("user", {})
            has_valid_team_context = (
                current_session.get("team_id") is not None and
                current_session.get("league_id") is not None and
                current_session.get("club") and
                current_session.get("series")
            )
            
            if has_valid_team_context:
                session_user = current_session
            else:
                # Session is incomplete or invalid, refresh from database
                fresh_session_data = get_session_data_for_user(user_email)
                
                if fresh_session_data:
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_user = fresh_session_data
                else:
                    session_user = session["user"]

        print(f"🔍 Getting club data for user: {session_user}")
        club_data = get_mobile_club_data(session_user)
        print(f"✅ Club data retrieved: {'error' in club_data}")

        session_data = {"user": session_user, "authenticated": True}
        print(f"✅ Session data created")

        # Get last updated timestamp from match_scores table
        last_updated = None
        try:
            last_updated_result = execute_query_one(
                "SELECT MAX(created_at) as last_updated FROM match_scores"
            )
            if last_updated_result and last_updated_result.get("last_updated"):
                last_updated = last_updated_result["last_updated"]
        except Exception as e:
            print(f"[WARNING] Could not fetch last_updated timestamp: {e}")

        print(f"📱 Calling log_user_activity for my-club...")
        log_result = log_user_activity(session_user["email"], "page_visit", page="mobile_my_club")
        print(f"✅ Activity logged: {log_result}")

        print(f"🎨 Rendering template...")
        return render_template(
            "mobile/my_club.html", session_data=session_data, last_updated=last_updated, **club_data
        )

    except Exception as e:
        print(f"❌ ERROR in my-club route: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

        session_data = {"user": session.get("user", {}), "authenticated": True}

        return render_template(
            "mobile/my_club.html",
            session_data=session_data,
            error="Failed to load club data",
        )


@mobile_bp.route("/mobile/player-stats")
@login_required
def serve_mobile_player_stats():
    """Serve the mobile player stats page"""
    try:
        stats_data = get_mobile_player_stats(session["user"])

        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_player_stats"
        )

        return render_template(
            "mobile/player_stats.html", session_data=session_data, **stats_data
        )

    except Exception as e:
        print(f"Error serving mobile player stats: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        session_data = {"user": session["user"], "authenticated": True}

        return render_template(
            "mobile/player_stats.html",
            session_data=session_data,
            error="Failed to load player stats",
        )


@mobile_bp.route("/mobile/improve")
@login_required
def serve_mobile_improve():
    """Serve the mobile improve page with paddle tips"""
    try:
        user = session.get("user")
        if not user:
            return redirect("/login")

        session_data = {"user": user, "authenticated": True}

        # Load improve data using service function
        improve_data = get_mobile_improve_data(user)

        log_user_activity(
            user["email"],
            "page_visit",
            page="mobile_improve",
            details="Accessed improve page",
        )

        return render_template(
            "mobile/improve.html",
            session_data=session_data,
            paddle_tips=improve_data.get("paddle_tips", []),
            training_guide=improve_data.get("training_guide", {}),
        )

    except Exception as e:
        print(f"Error serving improve page: {str(e)}")
        return redirect("/login")


@mobile_bp.route("/mobile/training-videos")
@login_required
def serve_mobile_training_videos():
    """Serve the mobile training videos page with YouTube-like interface"""
    try:
        user = session.get("user")
        if not user:
            return redirect("/login")

        session_data = {"user": user, "authenticated": True}

        # Load training videos from JSON file
        try:
            import json
            import os

            videos_path = os.path.join(
                "data",
                "leagues",
                "all",
                "improve_data",
                "platform_tennis_videos_full_30.json",
            )
            with open(videos_path, "r", encoding="utf-8") as f:
                training_videos = json.load(f)
        except Exception as e:
            print(f"Error loading training videos: {str(e)}")
            training_videos = []

        log_user_activity(
            user["email"],
            "page_visit",
            page="mobile_training_videos",
            details="Accessed training videos library",
        )

        return render_template(
            "mobile/training_videos.html",
            session_data=session_data,
            training_videos=training_videos,
        )

    except Exception as e:
        print(f"Error serving training videos page: {str(e)}")
        return redirect("/login")


@mobile_bp.route("/mobile/schedule-lesson")
@login_required
def serve_mobile_schedule_lesson():
    """Serve the mobile Schedule Lesson with Pro page"""
    try:
        # Get past lessons for the user
        user_email = session["user"]["email"]
        past_lessons_query = """
            SELECT 
                pl.id,
                pl.lesson_date,
                pl.lesson_time,
                pl.focus_areas,
                pl.notes,
                pl.status,
                pl.created_at,
                p.name as pro_name,
                p.bio as pro_bio,
                p.specialties as pro_specialties
            FROM pro_lessons pl
            LEFT JOIN pros p ON pl.pro_id = p.id
            WHERE pl.user_email = %s
            ORDER BY pl.lesson_date DESC, pl.lesson_time DESC
        """
        
        try:
            past_lessons = execute_query(past_lessons_query, [user_email])
        except Exception as e:
            # Tables don't exist yet, create sample data
            print(f"Tables not yet created: {e}")
            past_lessons = []
        
        # Get available pros
        pros_query = """
            SELECT 
                id,
                name,
                bio,
                specialties,
                hourly_rate,
                image_url,
                is_active
            FROM pros
            WHERE is_active = true
            ORDER BY name DESC
        """
        
        try:
            available_pros = execute_query(pros_query)
        except Exception as e:
            print(f"No pros table found: {e}")
            available_pros = []

        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_schedule_lesson"
        )

        response = render_template(
            "mobile/schedule_lesson.html",
            session_data=session_data,
            past_lessons=past_lessons,
            available_pros=available_pros,
        )
        
        # Add cache-busting headers to ensure fresh content
        from flask import make_response
        response = make_response(response)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Last-Modified'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        
        return response

    except Exception as e:
        print(f"Error serving mobile schedule lesson: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        session_data = {"user": session["user"], "authenticated": True}

        response = render_template(
            "mobile/schedule_lesson.html",
            session_data=session_data,
            past_lessons=[],
            available_pros=[],
            error="Failed to load lesson data",
        )
        
        # Add cache-busting headers even for error cases
        from flask import make_response
        response = make_response(response)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response


@mobile_bp.route("/api/schedule-lesson", methods=["POST"])
@login_required
def schedule_lesson_api():
    """API endpoint to handle lesson scheduling requests"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["pro_id", "lesson_date", "lesson_time", "focus_areas"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        user_email = session["user"]["email"]
        user_name = f"{session['user'].get('first_name', '')} {session['user'].get('last_name', '')}".strip()

        # For now, just log the lesson request (since tables may not exist yet)
        lesson_data = {
            "user_email": user_email,
            "user_name": user_name,
            "pro_id": data["pro_id"],
            "lesson_date": data["lesson_date"],
            "lesson_time": data["lesson_time"],
            "focus_areas": data["focus_areas"],
            "notes": data.get("notes", ""),
            "status": "pending"
        }
        
        print(f"[LESSON REQUEST] {lesson_data}")

        # Insert into database
        try:
            insert_query = """
                INSERT INTO pro_lessons (user_email, pro_id, lesson_date, lesson_time, focus_areas, notes, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            execute_update(insert_query, [
                user_email, data["pro_id"], data["lesson_date"], data["lesson_time"], 
                data["focus_areas"], data.get("notes", ""), "pending"
            ])
            print("✅ Lesson request saved to database")
        except Exception as db_error:
            print(f"⚠️ Could not save to database (tables may not exist yet): {db_error}")
            # Continue anyway - the request is still logged

        log_user_activity(
            user_email, 
            "lesson_request", 
            page="mobile_schedule_lesson",
            details=f"Requested lesson for {data['lesson_date']} at {data['lesson_time']} focusing on {data['focus_areas']}"
        )

        return jsonify({
            "success": True,
            "message": "Lesson request submitted successfully! We'll contact you soon to confirm."
        })

    except Exception as e:
        print(f"Error scheduling lesson: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to submit lesson request"}), 500


@mobile_bp.route("/api/lesson-requests", methods=["GET"])
@login_required
def get_lesson_requests():
    """API endpoint to get all lesson requests for pros to manage"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # Get all lesson requests from the database
        query = """
            SELECT 
                pl.id,
                pl.user_email,
                pl.lesson_date,
                pl.lesson_time,
                pl.focus_areas,
                pl.notes,
                pl.status,
                pl.created_at,
                CONCAT(u.first_name, ' ', u.last_name) as player_name,
                p.name as pro_name
            FROM pro_lessons pl
            LEFT JOIN users u ON pl.user_email = u.email
            LEFT JOIN pros p ON pl.pro_id = p.id
            ORDER BY pl.created_at DESC
        """
        
        try:
            lesson_requests = execute_query(query)
            
            # Format the response
            formatted_requests = []
            for request in lesson_requests:
                formatted_requests.append({
                    "id": request["id"],
                    "player_name": request["player_name"] or "Unknown Player",
                    "user_email": request["user_email"],
                    "lesson_date": request["lesson_date"],
                    "lesson_time": request["lesson_time"],
                    "focus_areas": request["focus_areas"],
                    "notes": request["notes"],
                    "status": request["status"],
                    "created_at": request["created_at"],
                    "pro_name": request["pro_name"]
                })
            
            return jsonify({
                "success": True,
                "lesson_requests": formatted_requests
            })
            
        except Exception as db_error:
            print(f"Database error getting lesson requests: {db_error}")
            # Return empty list if database error
            return jsonify({
                "success": True,
                "lesson_requests": []
            })

    except Exception as e:
        print(f"Error getting lesson requests: {str(e)}")
        return jsonify({"error": "Failed to get lesson requests"}), 500


@mobile_bp.route("/api/lesson-requests/<int:request_id>/confirm", methods=["POST"])
@login_required
def confirm_lesson_request(request_id):
    """API endpoint to confirm a lesson request"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # Update the lesson request status to confirmed
        update_query = """
            UPDATE pro_lessons 
            SET status = 'confirmed', updated_at = NOW()
            WHERE id = %s
        """
        
        try:
            execute_update(update_query, [request_id])
            
            # Get the lesson request details for logging
            get_request_query = """
                SELECT user_email, lesson_date, lesson_time, focus_areas
                FROM pro_lessons 
                WHERE id = %s
            """
            request_details = execute_query_one(get_request_query, [request_id])
            
            if request_details:
                log_user_activity(
                    session["user"]["email"], 
                    "lesson_confirmed", 
                    page="mobile_pros",
                    details=f"Confirmed lesson request for {request_details['user_email']} on {request_details['lesson_date']} at {request_details['lesson_time']}"
                )
            
            return jsonify({
                "success": True,
                "message": "Lesson request confirmed successfully!"
            })
            
        except Exception as db_error:
            print(f"Database error confirming lesson request: {db_error}")
            return jsonify({"error": "Failed to confirm lesson request"}), 500

    except Exception as e:
        print(f"Error confirming lesson request: {str(e)}")
        return jsonify({"error": "Failed to confirm lesson request"}), 500


@mobile_bp.route("/api/lesson-requests/<int:request_id>/decline", methods=["POST"])
@login_required
def decline_lesson_request(request_id):
    """API endpoint to decline a lesson request"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # Update the lesson request status to declined
        update_query = """
            UPDATE pro_lessons 
            SET status = 'declined', updated_at = NOW()
            WHERE id = %s
        """
        
        try:
            execute_update(update_query, [request_id])
            
            # Get the lesson request details for logging
            get_request_query = """
                SELECT user_email, lesson_date, lesson_time, focus_areas
                FROM pro_lessons 
                WHERE id = %s
            """
            request_details = execute_query_one(get_request_query, [request_id])
            
            if request_details:
                log_user_activity(
                    session["user"]["email"], 
                    "lesson_declined", 
                    page="mobile_pros",
                    details=f"Declined lesson request for {request_details['user_email']} on {request_details['lesson_date']} at {request_details['lesson_time']}"
                )
            
            return jsonify({
                "success": True,
                "message": "Lesson request declined successfully!"
            })
            
        except Exception as db_error:
            print(f"Database error declining lesson request: {db_error}")
            return jsonify({"error": "Failed to decline lesson request"}), 500

    except Exception as e:
        print(f"Error declining lesson request: {str(e)}")
        return jsonify({"error": "Failed to decline lesson request"}), 500


@mobile_bp.route("/api/pros-leagues", methods=["GET"])
@login_required
def get_pros_leagues():
    """API endpoint to get all leagues for pros page"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get all leagues
        leagues_query = """
            SELECT id, league_name, league_id
            FROM leagues
            ORDER BY league_name
        """
        
        leagues = execute_query(leagues_query)
        
        # Format the leagues for the frontend
        formatted_leagues = []
        for league in leagues:
            formatted_leagues.append({
                "id": league["id"],
                "name": league["league_name"],
                "league_id": league["league_id"]
            })
        
        return jsonify({
            "success": True,
            "leagues": formatted_leagues
        })
        
    except Exception as e:
        print(f"Error getting leagues: {str(e)}")
        return jsonify({"error": "Failed to get leagues"}), 500


@mobile_bp.route("/api/pros-teams", methods=["GET"])
@login_required
def get_pros_teams():
    """API endpoint to get all teams in the current league for the pros page team picklist"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        user = session["user"]
        club_name = user.get("club")
        league_id = user.get("league_id")
        
        if not club_name or not league_id:
            return jsonify({"error": "Club or league information not available"}), 400

        # Get all teams in the current league for the user's club, prioritizing user's associated team
        teams_query = """
            SELECT DISTINCT t.id, t.team_name, t.display_name, t.series_id, s.name as series_name, s.display_name as series_display_name, c.name as club_name,
                   CASE WHEN p.tenniscores_player_id IS NOT NULL THEN 1 ELSE 0 END as is_user_team
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            LEFT JOIN players p ON t.id = p.team_id
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            LEFT JOIN users u ON upa.user_id = u.id
            WHERE t.league_id = %s AND c.name = %s AND (u.email = %s OR u.email IS NULL)
            ORDER BY is_user_team DESC, t.display_name
        """
        
        teams = execute_query(teams_query, [league_id, club_name, user.get("email")])
        
        # Format the teams for the frontend
        formatted_teams = []
        for team in teams:
            # Use series display_name if available, otherwise fall back to series name
            series_display = team["series_display_name"] or team["series_name"]
            formatted_teams.append({
                "id": team["id"],
                "name": team["team_name"],
                "series_name": series_display,
                "display_name": team["display_name"] or f"{team['club_name']} - {series_display}" if series_display else team["team_name"]
            })
        
        return jsonify({
            "success": True,
            "teams": formatted_teams
        })
        
    except Exception as e:
        print(f"Error getting pros teams: {str(e)}")
        return jsonify({"error": "Failed to get teams"}), 500


@mobile_bp.route("/api/pros-teams-with-practices", methods=["GET"])
@login_required
def get_pros_teams_with_practices():
    """API endpoint to efficiently find teams that have practice times in a single query"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        user = session["user"]
        club_name = user.get("club")
        league_id = user.get("league_id")
        
        if not club_name or not league_id:
            return jsonify({"error": "Club or league information not available"}), 400

        # Single query to find teams with practice times
        teams_with_practices_query = """
            SELECT DISTINCT t.id, t.team_name, t.display_name, t.series_id, s.name as series_name, s.display_name as series_display_name, c.name as club_name,
                   COUNT(sch.id) as practice_count
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            LEFT JOIN schedule sch ON t.id = sch.home_team_id AND sch.home_team LIKE %s
            WHERE t.league_id = %s AND c.name = %s
            GROUP BY t.id, t.team_name, t.display_name, t.series_id, s.name, s.display_name, c.name
            HAVING COUNT(sch.id) > 0
            ORDER BY practice_count DESC, t.display_name
        """
        
        # Create practice pattern based on club name
        practice_pattern = f"%{club_name} Practice%"
        
        teams = execute_query(teams_with_practices_query, [practice_pattern, league_id, club_name])
        
        # Format the teams for the frontend
        formatted_teams = []
        for team in teams:
            # Use series display_name if available, otherwise fall back to series name
            series_display = team["series_display_name"] or team["series_name"]
            formatted_teams.append({
                "id": team["id"],
                "name": team["team_name"],
                "series_name": series_display,
                "display_name": team["display_name"] or f"{team['club_name']} - {series_display}" if series_display else team["team_name"],
                "practice_count": team["practice_count"]
            })
        
        return jsonify({
            "success": True,
            "teams": formatted_teams
        })
        
    except Exception as e:
        print(f"Error getting teams with practices: {str(e)}")
        return jsonify({"error": "Failed to get teams with practices"}), 500


@mobile_bp.route("/api/pros-team-schedule", methods=["GET"])
@login_required
def get_pros_team_schedule():
    """API endpoint to get schedule data for a specific team (for pros page)"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        team_id = request.args.get('team_id')
        if not team_id:
            return jsonify({"error": "Team ID is required"}), 400

        # Get team information
        team_query = """
            SELECT t.id, t.team_name, t.display_name, t.series_id, s.name as series_name, s.display_name as series_display_name, l.league_id, c.name as club_name
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN leagues l ON t.league_id = l.id
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE t.id = %s
        """
        
        team_info = execute_query_one(team_query, [team_id])
        
        if not team_info:
            return jsonify({"error": "Team not found"}), 404

        # Create a mock user object for the team
        series_display = team_info["series_display_name"] or team_info["series_name"]
        mock_user = {
            "club": team_info["club_name"],
            "series": series_display,
            "team_id": team_info["id"],
            "league_id": team_info["league_id"]
        }

        # Use the existing get_matches_for_user_club function but with the selected team
        from routes.act.schedule import get_matches_for_user_club
        matches = get_matches_for_user_club(mock_user)
        
        # Process the matches data (similar to team-schedule-data endpoint)
        match_dates = []
        event_details = {}
        players_schedule = {}
        
        print(f"Processing {len(matches)} matches for team {team_id}")
        
        for match in matches:
            # The get_matches_for_user_club function returns data with 'date' and 'time' fields
            # not 'match_date' and 'match_time'
            date_str = match.get("date", "")
            if not date_str:
                print(f"Warning: date not found in match: {match}")
                continue
                
            if date_str not in match_dates:
                match_dates.append(date_str)
            
            event_details[date_str] = {
                "type": match.get("type", "unknown"),
                "home_team": match.get("home_team", ""),
                "away_team": match.get("away_team", ""),
                "location": match.get("location", ""),
                "club_address": match.get("club_address", ""),
                "match_time": match.get("time", "")
            }
        
        # Get player availability data for this team
        # First get players with their user_id for stable availability lookup
        players_query = """
            SELECT DISTINCT 
                CONCAT(p.first_name, ' ', p.last_name) as name, 
                p.tenniscores_player_id,
                upa.user_id
            FROM players p
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE p.team_id = %s
            ORDER BY CONCAT(p.first_name, ' ', p.last_name)
        """
        
        players = execute_query(players_query, [team_id])
        
        for player in players:
            player_name = player["name"]
            players_schedule[player_name] = []
            
            # Get availability for each match date
            for date_str in match_dates:
                # Convert date from MM/DD/YYYY format to YYYY-MM-DD format for database query
                try:
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                    db_date_str = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    print(f"Warning: Could not parse date {date_str}")
                    db_date_str = date_str
                
                # Use user_id for stable availability lookup (primary method)
                availability = None
                if player["user_id"]:
                    availability_query = """
                        SELECT pa.availability_status, pa.notes
                        FROM player_availability pa
                        WHERE pa.user_id = %s AND DATE(pa.match_date AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
                    """
                    availability = execute_query_one(availability_query, [player["user_id"], db_date_str])
                
                # Fallback to player_id if user_id lookup failed
                if not availability and player["tenniscores_player_id"]:
                    # Get the internal player_id from tenniscores_player_id
                    player_id_query = """
                        SELECT id FROM players WHERE tenniscores_player_id = %s AND team_id = %s
                    """
                    player_record = execute_query_one(player_id_query, [player["tenniscores_player_id"], team_id])
                    if player_record:
                        availability_query = """
                            SELECT pa.availability_status, pa.notes
                            FROM player_availability pa
                            WHERE pa.player_id = %s AND DATE(pa.match_date AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
                        """
                        availability = execute_query_one(availability_query, [player_record["id"], db_date_str])
                
                if availability:
                    players_schedule[player_name].append({
                        "date": date_str,
                        "availability_status": availability["availability_status"],
                        "notes": availability["notes"]
                    })
                else:
                    players_schedule[player_name].append({
                        "date": date_str,
                        "availability_status": 0,
                        "notes": ""
                    })
        
        return jsonify({
            "success": True,
            "team_info": {
                "id": team_info["id"],
                "name": team_info["team_name"],
                "club": team_info["club_name"],
                "series_name": series_display,
                "display_name": team_info["display_name"] or f"{team_info['club_name']} - {series_display}"
            },
            "match_dates": match_dates,
            "event_details": event_details,
            "players_schedule": players_schedule
        })
        
    except Exception as e:
        print(f"Error getting pros team schedule: {str(e)}")
        return jsonify({"error": "Failed to get team schedule"}), 500


@mobile_bp.route("/api/debug-pros-data")
@login_required
def debug_pros_data():
    """Debug endpoint to see what data is being loaded for pros page"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        # Get the team schedule data
        from app.services.api_service import get_team_schedule_data_data
        response = get_team_schedule_data_data()
        
        # Parse the response to get the actual data
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            data = response[0].get_json() if isinstance(response, tuple) else response
        
        # Add debug information
        debug_info = {
            "user_session": {
                "email": user.get("email"),
                "club": user.get("club"),
                "series": user.get("series"),
                "team_id": user.get("team_id"),
                "league_id": user.get("league_id")
            },
            "api_response": data,
            "practice_dates_count": len([d for d in (data.get("match_dates", []) or []) if data.get("event_details", {}).get(d, {}).get("type") == "Practice"]),
            "total_dates_count": len(data.get("match_dates", []) or []),
            "event_details": data.get("event_details", {})
        }
        
        return jsonify(debug_info)

    except Exception as e:
        print(f"Error in debug endpoint: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Debug failed: {str(e)}"}), 500


@mobile_bp.route("/api/pros-clubs", methods=["GET"])
@login_required
def get_pros_clubs():
    """API endpoint to get all clubs in the selected league for pros page club picklist"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # Get league_id from query parameter or fall back to session
        league_id_param = request.args.get('league_id')
        
        if league_id_param:
            # Use the provided league_id parameter
            try:
                league_id_int = int(league_id_param)
            except ValueError:
                return jsonify({"error": "Invalid league ID parameter"}), 400
        else:
            # Fall back to session league_id for backward compatibility
            user = session["user"]
            league_id = user.get("league_id")
            
            if not league_id:
                return jsonify({"error": "League information not available"}), 400

            # Convert string league_id to integer if needed
            league_id_int = None
            if isinstance(league_id, str) and league_id != "":
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                except Exception as e:
                    print(f"Could not convert league ID: {e}")
            elif isinstance(league_id, int):
                league_id_int = league_id

            if not league_id_int:
                return jsonify({"error": "Invalid league ID"}), 400

        # Get all clubs in the selected league
        clubs_query = """
            SELECT DISTINCT c.id, c.name as club_name
            FROM clubs c
            JOIN teams t ON c.id = t.club_id
            WHERE t.league_id = %s
            ORDER BY c.name
        """
        
        clubs = execute_query(clubs_query, [league_id_int])
        
        # Format the clubs for the frontend
        formatted_clubs = []
        for club in clubs:
            formatted_clubs.append({
                "id": club["id"],
                "name": club["club_name"]
            })
        
        return jsonify({
            "success": True,
            "clubs": formatted_clubs
        })
        
    except Exception as e:
        print(f"Error getting pros clubs: {str(e)}")
        return jsonify({"error": "Failed to get clubs"}), 500


@mobile_bp.route("/api/pros-teams-by-club", methods=["GET"])
@login_required
def get_pros_teams_by_club():
    """API endpoint to get all teams for a specific club in the pros page"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        club_id = request.args.get('club_id')
        league_id_param = request.args.get('league_id')
        
        if not club_id:
            return jsonify({"error": "Club ID is required"}), 400

        if league_id_param:
            # Use the provided league_id parameter
            try:
                league_id_int = int(league_id_param)
            except ValueError:
                return jsonify({"error": "Invalid league ID parameter"}), 400
        else:
            # Fall back to session league_id for backward compatibility
            user = session["user"]
            league_id = user.get("league_id")
            
            if not league_id:
                return jsonify({"error": "League information not available"}), 400

            # Convert string league_id to integer if needed
            league_id_int = None
            if isinstance(league_id, str) and league_id != "":
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                except Exception as e:
                    print(f"Could not convert league ID: {e}")
            elif isinstance(league_id, int):
                league_id_int = league_id

            if not league_id_int:
                return jsonify({"error": "Invalid league ID"}), 400

        # Get all teams for the specified club in the selected league
        teams_query = """
            SELECT DISTINCT t.id, t.team_name, t.display_name, t.series_id, 
                   s.name as series_name, s.display_name as series_display_name,
                   c.name as club_name
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE t.league_id = %s AND t.club_id = %s
        """
        
        teams = execute_query(teams_query, [league_id_int, club_id])
        
        # Format the teams for the frontend
        formatted_teams = []
        for team in teams:
            series_display = team["series_display_name"] or team["series_name"]
            formatted_teams.append({
                "id": team["id"],
                "team_name": team["team_name"],
                "display_name": team["display_name"],
                "series_name": series_display,
                "club_name": team["club_name"]
            })
        
        # Custom sorting: extract number or letter from team name and sort
        def extract_sort_key(team):
            display_name = team["display_name"] or team["team_name"]
            
            # Extract the last part after the last space (e.g., "22" from "Tennaqua 22", "K" from "Tennaqua K")
            parts = display_name.split()
            if len(parts) > 1:
                last_part = parts[-1]
                
                # Try to convert to number first
                try:
                    return (0, int(last_part))  # Numbers come first, sorted numerically
                except ValueError:
                    # If not a number, treat as string
                    return (1, last_part)  # Letters come after numbers, sorted alphabetically
            else:
                # If no space found, use the whole name
                return (2, display_name)
        
        # Sort teams using the custom key
        formatted_teams.sort(key=extract_sort_key)
        
        return jsonify({
            "success": True,
            "teams": formatted_teams
        })
        
    except Exception as e:
        print(f"Error getting pros teams by club: {str(e)}")
        return jsonify({"error": "Failed to get teams"}), 500


@mobile_bp.route("/api/pros-team-details", methods=["GET"])
@login_required
def get_pros_team_details():
    """API endpoint to get team practices and players for pros page"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        team_id = request.args.get('team_id')
        league_id_param = request.args.get('league_id')
        
        if not team_id:
            return jsonify({"error": "Team ID is required"}), 400

        if league_id_param:
            # Use the provided league_id parameter
            try:
                league_id_int = int(league_id_param)
            except ValueError:
                return jsonify({"error": "Invalid league ID parameter"}), 400
        else:
            # Fall back to session league_id for backward compatibility
            user = session["user"]
            league_id = user.get("league_id")
            
            if not league_id:
                return jsonify({"error": "League information not available"}), 400

            # Convert string league_id to integer if needed
            league_id_int = None
            if isinstance(league_id, str) and league_id != "":
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                except Exception as e:
                    print(f"Could not convert league ID: {e}")
            elif isinstance(league_id, int):
                league_id_int = league_id

            if not league_id_int:
                return jsonify({"error": "Invalid league ID"}), 400

        # Get team information
        team_query = """
            SELECT t.id, t.team_name, t.display_name, t.series_id, 
                   s.name as series_name, s.display_name as series_display_name,
                   c.name as club_name
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE t.id = %s AND t.league_id = %s
        """
        
        team_info = execute_query_one(team_query, [team_id, league_id_int])
        
        if not team_info:
            return jsonify({"error": "Team not found"}), 404

        # Get team players
        players_query = """
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   CONCAT(p.first_name, ' ', p.last_name) as full_name
            FROM players p
            WHERE p.team_id = %s AND p.is_active = true
            ORDER BY 
                CASE WHEN p.captain_status = 'true' THEN 0 ELSE 1 END,
                p.last_name, p.first_name
        """
        
        players = execute_query(players_query, [team_id])
        
        # Get team practices (from schedule table, same logic as availability page)
        # Show all practices (past and future) like the availability page does
        practices_query = """
            SELECT DISTINCT 
                s.match_date as date,
                s.match_time as time,
                s.home_team,
                s.away_team,
                s.location,
                s.home_team_id,
                s.away_team_id
            FROM schedule s
            WHERE (s.home_team_id = %s OR s.away_team_id = %s)
            AND (
                s.home_team LIKE '%%Practice%%' OR 
                s.away_team LIKE '%%Practice%%' OR
                (s.away_team IS NULL OR s.away_team = '')
            )
            ORDER BY s.match_date, s.match_time
        """
        
        practices = execute_query(practices_query, [team_id, team_id])
        
        # Format the response
        formatted_players = []
        for player in players:
            formatted_players.append({
                "id": player["id"],
                "first_name": player["first_name"],
                "last_name": player["last_name"],
                "full_name": player["full_name"],
                "tenniscores_player_id": player["tenniscores_player_id"]
            })
        
        formatted_practices = []
        for practice in practices:
            # Format time display
            time_display = ""
            if practice["time"]:
                time_display = practice["time"].strftime("%H:%M")
            
            # Get practice description from home_team (which contains the practice info)
            practice_description = practice["home_team"] or "Practice"
            
            formatted_practices.append({
                "date": practice["date"].strftime("%Y-%m-%d") if practice["date"] else "",
                "time": time_display,
                "description": practice_description,
                "location": practice["location"] or ""
            })
        
        return jsonify({
            "success": True,
            "team": {
                "id": team_info["id"],
                "team_name": team_info["team_name"],
                "display_name": team_info["display_name"],
                "series_name": team_info["series_display_name"] or team_info["series_name"],
                "club_name": team_info["club_name"]
            },
            "players": formatted_players,
            "practices": formatted_practices
        })
        
    except Exception as e:
        print(f"Error getting pros team details: {str(e)}")
        return jsonify({"error": "Failed to get team details"}), 500


@mobile_bp.route("/api/pros-player-availability", methods=["GET"])
@login_required
def get_pros_player_availability():
    """API endpoint to get player availability for a specific practice date"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        team_id = request.args.get('team_id')
        practice_date = request.args.get('practice_date')
        league_id_param = request.args.get('league_id')
        
        if not team_id or not practice_date:
            return jsonify({"error": "Team ID and practice date are required"}), 400
        
        if league_id_param:
            # Use the provided league_id parameter
            try:
                league_id_int = int(league_id_param)
            except ValueError:
                return jsonify({"error": "Invalid league ID parameter"}), 400
        else:
            # Fall back to session league_id for backward compatibility
            user = session["user"]
            league_id = user.get("league_id")
            if not league_id:
                return jsonify({"error": "League information not available"}), 400
            
            # Convert league_id to integer if it's a string
            league_id_int = None
            if isinstance(league_id, str) and league_id != "":
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                except Exception as e:
                    print(f"Could not convert league ID: {e}")
            elif isinstance(league_id, int):
                league_id_int = league_id
            
            if not league_id_int:
                return jsonify({"error": "Invalid league ID"}), 400
        
        # Get team info to verify it exists and user has access
        team_query = """
            SELECT t.id, t.team_name, t.display_name, t.series_id, 
                   s.name as series_name, s.display_name as series_display_name,
                   c.name as club_name
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE t.id = %s AND t.league_id = %s
        """
        team_info = execute_query_one(team_query, [team_id, league_id_int])
        if not team_info:
            return jsonify({"error": "Team not found"}), 404
        
        # Get player availability for the specific practice date
        # Use the same logic as the availability page - look up by user_id for stability
        # Use timezone conversion to match availability page behavior
        availability_query = """
            SELECT 
                pa.availability_status,
                pa.notes,
                pa.updated_at,
                u.first_name,
                u.last_name,
                CONCAT(u.first_name, ' ', u.last_name) as player_name,
                upa.tenniscores_player_id
            FROM player_availability pa
            JOIN user_player_associations upa ON pa.user_id = upa.user_id
            JOIN users u ON upa.user_id = u.id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE p.team_id = %s 
            AND DATE(pa.match_date AT TIME ZONE 'UTC') = DATE(%s AT TIME ZONE 'UTC')
            ORDER BY u.last_name, u.first_name
        """
        
        availability_data = execute_query(availability_query, [team_id, practice_date])
        
        # Format the response
        formatted_availability = []
        for avail in availability_data:
            formatted_availability.append({
                "player_name": avail["player_name"],
                "tenniscores_player_id": avail["tenniscores_player_id"],
                "availability_status": avail["availability_status"],
                "notes": avail["notes"],
                "updated_at": avail["updated_at"].isoformat() if avail["updated_at"] else None
            })
        
        return jsonify({
            "success": True,
            "team": {
                "id": team_info["id"],
                "team_name": team_info["team_name"],
                "display_name": team_info["display_name"],
                "series_name": team_info["series_display_name"] or team_info["series_name"],
                "club_name": team_info["club_name"]
            },
            "practice_date": practice_date,
            "availability": formatted_availability
        })
    except Exception as e:
        print(f"Error getting pros player availability: {str(e)}")
        return jsonify({"error": "Failed to get player availability"}), 500


@mobile_bp.route("/mobile/email-team")
@login_required
def serve_mobile_email_team():
    """Serve the mobile email team page"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(session["user"]["email"], "page_visit", page="mobile_email_team")
    return render_template("mobile/email_team.html", session_data=session_data)


@mobile_bp.route("/mobile/practice-times")
@login_required
def serve_mobile_practice_times():
    """Serve the mobile practice times page"""
    try:
        practice_data = get_practice_times_data(session["user"])

        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_practice_times"
        )

        return render_template(
            "mobile/practice_times.html", session_data=session_data, **practice_data
        )

    except Exception as e:
        print(f"Error serving mobile practice times: {str(e)}")
        session_data = {"user": session["user"], "authenticated": True}

        return render_template(
            "mobile/practice_times.html",
            session_data=session_data,
            error="Failed to load practice times data",
        )


@mobile_bp.route("/mobile/availability")
@login_required
def serve_mobile_availability():
    """Serve the mobile availability page for viewing/setting user availability with team switching support"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "No user in session"}), 400

        user_email = user.get("email")
        
        # Check for team_id parameter for team switching
        requested_team_id = request.args.get('team_id')
        if requested_team_id:
            try:
                requested_team_id = int(requested_team_id)
                print(f"[DEBUG] Team switching requested: team_id={requested_team_id}")
                
                # Update session with new team context
                from app.services.session_service import get_session_data_for_user_team
                fresh_session_data = get_session_data_for_user_team(user_email, requested_team_id)
                
                if fresh_session_data:
                    # Update Flask session with new team context
                    session["user"] = fresh_session_data
                    session.modified = True
                    user = fresh_session_data
                    print(f"[DEBUG] Updated session to team {requested_team_id}")
                else:
                    print(f"[DEBUG] Failed to get session data for team {requested_team_id}")
            except (ValueError, TypeError):
                print(f"[DEBUG] Invalid team_id parameter: {requested_team_id}")

        # Get user's available teams for team switching (after team context is set)
        from app.services.session_service import get_user_teams_in_league
        current_league_id = user.get("league_id")
        if current_league_id:
            user_teams = get_user_teams_in_league(user_email, current_league_id)
            # Add league_name to each team for template compatibility
            for team in user_teams:
                team["league_name"] = user.get("league_name", "")
        else:
            user_teams = []
        
        # Get current team info
        current_team_info = None
        current_team_id = user.get("team_id")
        if current_team_id:
            for team in user_teams:
                if team.get("team_id") == current_team_id:
                    current_team_info = team
                    break

        # Get availability data using session service for accurate team_id filtering
        # IMPORTANT: Pass the user data directly to preserve team context
        availability_data = get_mobile_availability_data(user)

        # No auto-redirect - respect user's team selection and show appropriate messaging

        session_data = {"user": user, "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_availability"
        )

        return render_template(
            "mobile/availability.html",
            session_data=session_data,
            user_teams=user_teams,
            current_team_info=current_team_info,
            **availability_data
        )
    except Exception as e:
        print(f"Error serving mobile availability: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return f"Error loading availability page: {str(e)}", 500


@mobile_bp.route("/mobile/all-team-availability")
@login_required
def serve_all_team_availability():
    """Serve the mobile all team availability page"""
    from flask import current_app
    current_app.logger.error(f"🚨 ROUTE HIT: /mobile/all-team-availability")
    current_app.logger.error(f"🚨 User: {session.get('user', {}).get('email', 'Unknown')}")
    print(f"🚨 ROUTE CALLED: /mobile/all-team-availability")
    print(f"🚨 User: {session.get('user', {}).get('email', 'Unknown')}")
    try:
        # Get the selected date from query parameter
        selected_date = request.args.get("date")
        print(f"🚨 Selected date from URL: {selected_date}")

        # Check if user session needs refresh due to database updates
        user_email = session["user"]["email"]
        current_series_id = session["user"].get("series_id")
        
        # Force session refresh for debugging
        from app.services.session_service import get_session_data_for_user
        fresh_session = get_session_data_for_user(user_email)
        if fresh_session:
            session["user"] = fresh_session
            session.modified = True
            print(f"🚨 Refreshed session: {fresh_session.get('series')} (ID: {fresh_session.get('series_id')})")
        
        # Call the service function with the selected date
        print(f"🚨 About to call get_all_team_availability_data...")
        availability_data = get_all_team_availability_data(
            session["user"], selected_date
        )
        print(f"🚨 Function returned: {type(availability_data)} with keys: {list(availability_data.keys()) if isinstance(availability_data, dict) else 'Not a dict'}")

        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_all_team_availability"
        )

        print(f"🚨 About to render template with data: {list(availability_data.keys()) if isinstance(availability_data, dict) else 'Not a dict'}")
        current_app.logger.error(f"🚨 Rendering template with availability_data keys: {list(availability_data.keys()) if isinstance(availability_data, dict) else 'Not a dict'}")
        
        return render_template(
            "mobile/all_team_availability.html",
            session_data=session_data,
            **availability_data,
        )

    except Exception as e:
        print(f"Error serving mobile all team availability: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        session_data = {"user": session["user"], "authenticated": True}

        return render_template(
            "mobile/all_team_availability.html",
            session_data=session_data,
            error="Failed to load availability data",
        )


@mobile_bp.route("/mobile/team-schedule")
@login_required
def serve_mobile_team_schedule():
    """Serve the team schedule page with loading screen"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        club_name = user.get("club")
        series = user.get("series")

        if not club_name or not series:
            return render_template(
                "mobile/team_schedule.html",
                session_data={"user": user},
                error="Please set your club and series in your profile settings",
            )

        # Create a clean team name string for the title
        team_name = f"{club_name} - {series}"

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_team_schedule"
        )

        return render_template(
            "mobile/team_schedule.html", team=team_name, session_data={"user": user}
        )

    except Exception as e:
        print(f"❌ Error in serve_mobile_team_schedule: {str(e)}")
        import traceback

        print(traceback.format_exc())

        session_data = {"user": session.get("user"), "authenticated": True}

        return render_template(
            "mobile/team_schedule.html",
            session_data=session_data,
            error="An error occurred while loading the team schedule",
        )


@mobile_bp.route("/mobile/team-schedule-grid")
@login_required
def serve_mobile_team_schedule_grid():
    """Serve the team schedule grid page showing all players and their availability"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        club_name = user.get("club")
        series = user.get("series")

        if not club_name or not series:
            return render_template(
                "mobile/team_schedule_grid.html",
                session_data={"user": user},
                error="Please set your club and series in your profile settings",
            )

        # Create a clean team name string for the title
        team_name = f"{club_name} - {series}"

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_team_schedule_grid"
        )

        return render_template(
            "mobile/team_schedule_grid.html", team=team_name, session_data={"user": user}
        )

    except Exception as e:
        print(f"❌ Error in serve_mobile_team_schedule_grid: {str(e)}")
        import traceback

        print(traceback.format_exc())

        session_data = {"user": session.get("user"), "authenticated": True}

        return render_template(
            "mobile/team_schedule_grid.html",
            session_data=session_data,
            error="An error occurred while loading the team schedule grid",
        )


@mobile_bp.route("/mobile/pros")
@login_required
def serve_mobile_pros():
    """Serve the refactored pros page for viewing team practices and managing lesson requests"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_pros"
        )

        return render_template(
            "mobile/pros_refactored.html", 
            session_data={"user": user}
        )

    except Exception as e:
        print(f"❌ Error in serve_mobile_pros: {str(e)}")
        import traceback

        print(traceback.format_exc())

        session_data = {"user": session.get("user"), "authenticated": True}

        return render_template(
            "mobile/pros_refactored.html",
            session_data=session_data,
            error="An error occurred while loading the pros page",
        )


@mobile_bp.route("/mobile/pro")
@login_required
def serve_mobile_pro():
    """Serve the main pro page with two buttons: Team Practice Times and Lesson Requests"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_pro"
        )

        return render_template(
            "mobile/pro.html", 
            session_data={"user": user}
        )

    except Exception as e:
        print(f"❌ Error in serve_mobile_pro: {str(e)}")
        import traceback
        print(traceback.format_exc())

        session_data = {"user": session.get("user"), "authenticated": True}

        return render_template(
            "mobile/pro.html",
            session_data=session_data,
            error="An error occurred while loading the pro page",
        )


@mobile_bp.route("/mobile/lesson-requests")
@login_required
def serve_mobile_lesson_requests():
    """Serve the lesson requests page with mock data and accept/message functionality"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_lesson_requests"
        )

        # Mock lesson request data
        mock_lesson_requests = [
            {
                "id": 1,
                "student_name": "John Smith",
                "student_email": "john.smith@email.com",
                "lesson_date": "2024-01-15",
                "lesson_time": "2:00 PM",
                "focus_areas": "Backhand technique, Volley positioning",
                "notes": "Looking to improve consistency on backhand shots",
                "status": "pending",
                "created_at": "2024-01-10"
            },
            {
                "id": 2,
                "student_name": "Sarah Johnson",
                "student_email": "sarah.j@email.com",
                "lesson_date": "2024-01-18",
                "lesson_time": "10:00 AM",
                "focus_areas": "Serve technique",
                "notes": "Want to work on power and accuracy",
                "status": "pending",
                "created_at": "2024-01-11"
            },
            {
                "id": 3,
                "student_name": "Mike Davis",
                "student_email": "mike.davis@email.com",
                "lesson_date": "2024-01-20",
                "lesson_time": "4:00 PM",
                "focus_areas": "Court positioning, Strategy",
                "notes": "Preparing for upcoming tournament",
                "status": "confirmed",
                "created_at": "2024-01-09"
            },
            {
                "id": 4,
                "student_name": "Lisa Wilson",
                "student_email": "lisa.wilson@email.com",
                "lesson_date": "2024-01-22",
                "lesson_time": "3:00 PM",
                "focus_areas": "Return of serve",
                "notes": "Struggling with aggressive returns",
                "status": "pending",
                "created_at": "2024-01-12"
            }
        ]

        return render_template(
            "mobile/lesson_requests.html", 
            session_data={"user": user},
            lesson_requests=mock_lesson_requests
        )

    except Exception as e:
        print(f"❌ Error in serve_mobile_lesson_requests: {str(e)}")
        import traceback
        print(traceback.format_exc())

        session_data = {"user": session.get("user"), "authenticated": True}

        return render_template(
            "mobile/lesson_requests.html",
            session_data=session_data,
            lesson_requests=[],
            error="An error occurred while loading the lesson requests page",
        )


@mobile_bp.route("/mobile/schedule")
@login_required
def serve_mobile_schedule():
    """Serve the mobile schedule page"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        session_data = {"user": user, "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_schedule"
        )

        return render_template(
            "mobile/view_schedule.html", 
            session_data=session_data,
            matches=[],  # Empty for now, will be loaded via API
        )

    except Exception as e:
        print(f"❌ Error in serve_mobile_schedule: {str(e)}")
        import traceback
        print(traceback.format_exc())

        session_data = {"user": session.get("user"), "authenticated": True}
        return render_template(
            "mobile/view_schedule.html",
            session_data=session_data,
            error="An error occurred while loading the schedule",
        )


@mobile_bp.route("/mobile/availability-calendar")
@login_required
def serve_mobile_availability_calendar():
    """Serve the mobile availability calendar page"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "No user in session"}), 400

        user_id = user.get("id")
        player_name = f"{user['first_name']} {user['last_name']}"
        series = user["series"]

        # FIXED: Use the optimized team_id-based availability data (same as /mobile/availability)
        availability_data = get_mobile_availability_data(user)
        
        # Extract matches from the availability data
        matches = []
        for match_avail_pair in availability_data.get("match_avail_pairs", []):
            match_data = match_avail_pair[0]  # First element is the match
            matches.append(match_data)
        
        print(f"[CALENDAR] Found {len(matches)} matches for calendar using team_id approach")

        # Get this user's availability for each match using existing function
        # FIXED: Pass user_id parameter for proper user-player associations
        availability = get_user_availability(player_name, matches, series, user_id)

        session_data = {
            "user": user,
            "authenticated": True,
            "matches": matches,
            "availability": availability,
            "players": [{"name": player_name}],
        }

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_availability_calendar"
        )

        return render_template(
            "mobile/availability-calendar.html", session_data=session_data
        )

    except Exception as e:
        print(f"ERROR in mobile_availability_calendar: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return f"Error: {str(e)}", 500


@mobile_bp.route("/mobile/find-people-to-play")
@login_required
def serve_mobile_find_people_to_play():
    """Serve the mobile Find People to Play page"""
    try:
        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_find_people_to_play"
        )

        return render_template(
            "mobile/find_people_to_play.html", session_data=session_data
        )

    except Exception as e:
        print(f"Error serving find people to play page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/mobile/pickup-games")
@login_required
def serve_mobile_pickup_games():
    """Serve the mobile Pickup Games page"""
    try:
        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_pickup_games"
        )

        return render_template("mobile/pickup_games.html", session_data=session_data)

    except Exception as e:
        print(f"Error serving pickup games page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/mobile/my-groups")
@login_required
def serve_mobile_my_groups():
    """Redirect to pickup games page - Groups functionality has been merged into Private Games tab"""
    from flask import redirect
    
    log_user_activity(
        session["user"]["email"], "page_redirect", 
        details="my-groups redirected to pickup-games (merged functionality)"
    )
    
    # Redirect to pickup games page where groups are now shown in Private Games tab
    return redirect("/mobile/pickup-games")


@mobile_bp.route("/mobile/private-groups")
@login_required
def serve_mobile_private_groups():
    """Serve the mobile Private Groups page (hidden)"""
    try:
        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_private_groups"
        )

        return render_template("mobile/private_groups.html", session_data=session_data)

    except Exception as e:
        print(f"Error serving private groups page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/mobile/create-pickup-game")
@login_required
def serve_mobile_create_pickup_game():
    """Serve the mobile Create Pickup Game page"""
    try:
        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_create_pickup_game"
        )

        return render_template("mobile/create_pickup_game.html", session_data=session_data)

    except Exception as e:
        print(f"Error serving create pickup game page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/mobile/reserve-court")
@login_required
def serve_mobile_reserve_court():
    """Serve the mobile Reserve Court page"""
    try:
        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_reserve_court"
        )

        return render_template("mobile/reserve-court.html", session_data=session_data)

    except Exception as e:
        print(f"Error serving reserve court page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/mobile/share-rally")
@login_required
def serve_mobile_share_rally():
    """Serve the mobile Share Rally page"""
    try:
        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_share_rally"
        )

        return render_template("mobile/share_rally.html", session_data=session_data)

    except Exception as e:
        print(f"Error serving share rally page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/api/share-rally", methods=["POST"])
@login_required
def send_share_rally_mms():
    """Send MMS invitation to share Rally with friends"""
    try:
        from app.services.notifications_service import send_mms_notification
        
        data = request.get_json()
        friend_name = data.get("friend_name", "").strip()
        phone_number = data.get("phone_number", "").strip()
        custom_message = data.get("message", "").strip()
        rally_link = "https://www.lovetorally.com"
        
        # Validate required fields
        if not friend_name:
            return jsonify({"success": False, "error": "Friend's name is required"}), 400
        
        if not phone_number:
            return jsonify({"success": False, "error": "Phone number is required"}), 400
        
        # Create the MMS message
        if custom_message:
            message = custom_message
            # Append the link if not present
            if rally_link not in message:
                message = message.rstrip('.') + f" {rally_link}"
        else:
            message = f"Hey {friend_name}, you should check out this new app for paddle, tennis and pickleball. It's called Rally. Click the link below to check it out: {rally_link}"
        
        # Get sender's name for logging
        sender_name = f"{session['user'].get('first_name', '')} {session['user'].get('last_name', '')}"
        sender_email = session['user']['email']
        
        # Log the sharing activity
        log_user_activity(
            sender_email, 
            "share_rally_mms", 
            page="mobile_share_rally", 
            details={
                "friend_name": friend_name,
                "phone_number": phone_number[-4:] if len(phone_number) > 4 else "****",  # Only log last 4 digits
                "message_length": len(message),
                "has_custom_message": bool(custom_message)
            }
        )
        
        # Send the MMS
        result = send_mms_notification(
            to_number=phone_number,
            message=message,
            test_mode=False
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": f"Rally invitation sent to {friend_name}!",
                "message_sid": result.get("message_sid")
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Failed to send MMS")
            }), 400
    
    except Exception as e:
        print(f"Error sending share rally MMS: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred while sending the invitation"}), 500


@mobile_bp.route("/mobile/support")
def serve_mobile_support():
    """Serve the mobile Support page - accessible to both authenticated and unauthenticated users"""
    try:
        # Check if user is authenticated
        if "user" in session:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"], "page_visit", page="mobile_support"
            )
        else:
            # For unauthenticated users, create minimal session data
            session_data = {"user": None, "authenticated": False}

        return render_template("mobile/support.html", session_data=session_data)

    except Exception as e:
        print(f"Error serving support page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/mobile/swag")
def serve_mobile_swag():
    """Serve the mobile SWAG (merchandise) page - accessible to both authenticated and unauthenticated users"""
    try:
        # Check if user is authenticated
        if "user" in session:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"], "page_visit", page="mobile_swag"
            )
        else:
            # For unauthenticated users, create minimal session data
            session_data = {"user": None, "authenticated": False}

        return render_template("mobile/swag.html", session_data=session_data)

    except Exception as e:
        print(f"Error serving swag page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/api/support", methods=["POST"])
def send_support_request():
    """Send support request SMS to admin - accessible to both authenticated and unauthenticated users"""
    try:
        from app.services.notifications_service import send_sms_notification
        
        data = request.get_json()
        user_name = data.get("user_name", "").strip()
        message = data.get("message", "").strip()
        user_phone = data.get("user_phone", "").strip()  # For unauthenticated users
        
        # Validate required fields
        if not user_name:
            return jsonify({"success": False, "error": "Your name is required"}), 400
        
        if not message:
            return jsonify({"success": False, "error": "Message is required"}), 400
        
        # Determine user email and authentication status
        if "user" in session:
            # Authenticated user
            sender_email = session['user']['email']
            sender_name = f"{session['user'].get('first_name', '')} {session['user'].get('last_name', '')}"
            # Get phone number from session data for authenticated users
            user_phone = session['user'].get('phone_number', '').strip()
            is_authenticated = True
        else:
            # Unauthenticated user
            if not user_phone:
                return jsonify({"success": False, "error": "Phone number is required"}), 400
            sender_email = "No email provided"  # Default since we removed email requirement
            sender_name = user_name
            is_authenticated = False
        
        # Gather user context information for authenticated users
        user_context_info = ""
        if is_authenticated:
            try:
                from database_utils import execute_query_one
                
                # Get user's current team context from session
                user_data = session.get('user', {})
                
                # Build context string with available data
                context_parts = []
                
                # League information - try multiple field names
                league_name = user_data.get('league_name') or user_data.get('league_string_id')
                if league_name and league_name.strip():
                    context_parts.append(f"League: {league_name}")
                
                # Club information
                club = user_data.get('club')
                if club and club.strip():
                    context_parts.append(f"Club: {club}")
                
                # Series information
                series = user_data.get('series')
                if series and series.strip():
                    context_parts.append(f"Series: {series}")
                
                # Team information
                team_name = user_data.get('team_name')
                if team_name and team_name.strip():
                    context_parts.append(f"Team: {team_name}")
                
                # Player ID
                player_id = user_data.get('tenniscores_player_id')
                if player_id and player_id.strip():
                    context_parts.append(f"Player ID: {player_id}")
                
                # If we have context parts, join them
                if context_parts:
                    user_context_info = f" | {' | '.join(context_parts)}"
                else:
                    # Fallback: try to get context from database using email
                    user_email = user_data.get('email')
                    if user_email:
                        # Get fresh context from database
                        context_query = """
                        SELECT DISTINCT ON (u.id)
                            l.name as league_name, c.name as club, s.name as series, 
                            t.name as team_name, p.tenniscores_player_id
                        FROM users u
                        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
                        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = true
                        LEFT JOIN teams t ON p.team_id = t.id
                        LEFT JOIN clubs c ON p.club_id = c.id
                        LEFT JOIN series s ON p.series_id = s.id
                        LEFT JOIN leagues l ON t.league_id = l.id
                        WHERE u.email = %s
                        LIMIT 1
                        """
                        context_result = execute_query_one(context_query, [user_email])
                        
                        if context_result:
                            fallback_parts = []
                            if context_result.get('league_name'):
                                fallback_parts.append(f"League: {context_result['league_name']}")
                            if context_result.get('club'):
                                fallback_parts.append(f"Club: {context_result['club']}")
                            if context_result.get('series'):
                                fallback_parts.append(f"Series: {context_result['series']}")
                            if context_result.get('team_name'):
                                fallback_parts.append(f"Team: {context_result['team_name']}")
                            if context_result.get('tenniscores_player_id'):
                                fallback_parts.append(f"Player ID: {context_result['tenniscores_player_id']}")
                            
                            if fallback_parts:
                                user_context_info = f" | {' | '.join(fallback_parts)}"
                
            except Exception as e:
                print(f"Error gathering user context: {str(e)}")
                user_context_info = " | Error gathering context"
        
        # Create the support SMS content
        auth_status = "Authenticated User" if is_authenticated else "Unauthenticated User"
        phone_info = f" | Phone: {user_phone}" if user_phone else ""
        sms_message = f"Rally Support Request from {user_name} ({sender_email}){phone_info}{user_context_info} [{auth_status}]: {message}"
        
        # Log the support request (only if we have session data for authenticated users)
        if is_authenticated:
            log_user_activity(
                sender_email, 
                "support_request", 
                page="mobile_support", 
                details={
                    "user_name": user_name,
                    "email_address": sender_email,
                    "phone_number": user_phone or "Not provided",
                    "message_length": len(message),
                    "authenticated": True,
                    "user_context": user_context_info.strip(" | ") if user_context_info else "No context available"
                }
            )
        else:
            # For unauthenticated users, just log to console
            print(f"Support request from unauthenticated user: {user_name} | Phone: {user_phone}")
        
        # Send the support SMS to admin
        result = send_sms_notification(
            to_number="7732138911",  # Admin phone number
            message=sms_message,
            test_mode=False
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": f"Support request sent successfully! We'll get back to you soon."
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Failed to send support request")
            }), 400
    
    except Exception as e:
        print(f"Error sending support request: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred while sending the support request"}), 500


@mobile_bp.route("/api/swag-request", methods=["POST"])
def send_swag_request():
    """Send swag/merchandise request SMS to admin - accessible to both authenticated and unauthenticated users"""
    try:
        from app.services.notifications_service import send_sms_notification
        
        data = request.get_json()
        user_name = data.get("user_name", "").strip()
        product = data.get("product", "").strip()
        price = data.get("price", "").strip()
        notes = data.get("notes", "").strip()
        user_phone = data.get("user_phone", "").strip()  # For unauthenticated users
        
        # Validate required fields
        if not user_name:
            return jsonify({"success": False, "error": "Your name is required"}), 400
        
        if not product:
            return jsonify({"success": False, "error": "Product selection is required"}), 400
        
        # Determine user email and authentication status
        if "user" in session:
            # Authenticated user
            sender_email = session['user']['email']
            sender_name = f"{session['user'].get('first_name', '')} {session['user'].get('last_name', '')}"
            # Get phone number from session data for authenticated users
            user_phone = session['user'].get('phone_number', '').strip()
            is_authenticated = True
        else:
            # Unauthenticated user
            if not user_phone:
                return jsonify({"success": False, "error": "Phone number is required"}), 400
            sender_email = "No email provided"
            sender_name = user_name
            is_authenticated = False
        
        # Create the swag request SMS content
        auth_status = "Authenticated User" if is_authenticated else "Unauthenticated User"
        phone_info = f" | Phone: {user_phone}" if user_phone else ""
        notes_info = f" | Notes: {notes}" if notes else ""
        sms_message = f"Rally SWAG Request from {user_name} ({sender_email}){phone_info} [{auth_status}]: Product: {product} ({price}){notes_info}"
        
        # Log the swag request (only if we have session data for authenticated users)
        if is_authenticated:
            log_user_activity(
                session["user"]["email"], 
                "swag_request",
                metadata={
                    "user_name": user_name,
                    "product": product,
                    "price": price,
                    "notes": notes,
                    "phone": user_phone,
                    "authenticated": True
                }
            )
        else:
            # For unauthenticated users, just log to console
            print(f"SWAG request from unauthenticated user: {user_name} | Phone: {user_phone} | Product: {product}")
        
        # Send the swag request SMS to admin
        result = send_sms_notification(
            to_number="7732138911",  # Admin phone number
            message=sms_message,
            test_mode=False
        )
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": f"Your {product} request has been sent! We'll reach out shortly to complete your order."
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Failed to send swag request")
            }), 400
    
    except Exception as e:
        print(f"Error sending swag request: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred while sending the swag request"}), 500


@mobile_bp.route("/mobile/create-team")
@login_required
def serve_mobile_create_team():
    """Serve the mobile Create Team page"""
    try:
        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_create_team"
        )

        return render_template("mobile/create_team.html", session_data=session_data)

    except Exception as e:
        print(f"Error serving create team page: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/mobile/register-my-team")
@login_required
def serve_mobile_register_my_team():
    """Serve the mobile Register my Team page for captains"""
    try:
        user = session["user"]
        user_id = user.get("id")
        team_id = user.get("team_id")
        club = user.get("club", "")
        series = user.get("series", "")
        league_id = user.get("league_id", "")
        
        if not team_id:
            return render_template(
                "mobile/register_my_team.html",
                error="Team ID not found. Please contact support to fix your team assignment.",
                session_data={"user": user}
            )
        
        # Get all players for this team
        try:
            # Convert league_id to integer if needed
            league_id_int = None
            if league_id:
                if isinstance(league_id, str) and league_id != "":
                    try:
                        league_record = execute_query_one(
                            "SELECT id FROM leagues WHERE league_id = %s", [league_id]
                        )
                        if league_record:
                            league_id_int = league_record["id"]
                    except Exception as e:
                        pass
                elif isinstance(league_id, int):
                    league_id_int = league_id
            
            # Get players for the team using team_id
            if league_id_int:
                players_query = """
                    SELECT DISTINCT 
                        p.id, 
                        p.first_name, 
                        p.last_name, 
                        p.tenniscores_player_id,
                        u.id as user_id,
                        u.email,
                        u.phone_number
                    FROM players p
                    LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                    LEFT JOIN users u ON upa.user_id = u.id
                    WHERE p.team_id = %s AND p.league_id = %s AND p.is_active = true
                    ORDER BY p.first_name, p.last_name
                """
                players_data = execute_query(players_query, [team_id, league_id_int])
            else:
                players_query = """
                    SELECT DISTINCT 
                        p.id, 
                        p.first_name, 
                        p.last_name, 
                        p.tenniscores_player_id,
                        u.id as user_id,
                        u.email,
                        u.phone_number
                    FROM players p
                    LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                    LEFT JOIN users u ON upa.user_id = u.id
                    WHERE p.team_id = %s AND p.is_active = true
                    ORDER BY 
                        CASE WHEN p.captain_status = 'true' THEN 0 ELSE 1 END,
                        p.first_name, p.last_name
                """
                players_data = execute_query(players_query, [team_id])

            # Format players data
            players = []
            for player in players_data:
                players.append({
                    "id": player["id"],
                    "name": f"{player['first_name']} {player['last_name']}",
                    "first_name": player["first_name"],
                    "last_name": player["last_name"],
                    "tenniscores_player_id": player["tenniscores_player_id"],
                    "user_id": player.get("user_id"),
                    "email": player.get("email"),
                    "phone_number": player.get("phone_number", ""),
                    "has_account": player.get("user_id") is not None
                })

            return render_template(
                "mobile/register_my_team.html",
                players=players,
                team_info={
                    "club": club,
                    "series": series,
                    "league_id": league_id
                },
                session_data={"user": user}
            )

        except Exception as e:
            logger.error(f"Error getting team players for register-my-team: {e}")
            return render_template(
                "mobile/register_my_team.html",
                error=f"Error loading team players: {str(e)}",
                session_data={"user": user}
            )

    except Exception as e:
        logger.error(f"Error serving register-my-team page: {e}")
        return render_template(
            "mobile/register_my_team.html",
            error="An error occurred loading the page",
            session_data={"user": user if 'user' in locals() else {}}
        )


@mobile_bp.route("/mobile/matchup-simulator")
@login_required
def serve_mobile_matchup_simulator():
    """Serve the mobile Matchup Simulator page"""
    try:
        # Get user's league ID and series for filtering
        user_league_id = session["user"].get("league_id")
        user_series = session["user"].get("series")
        user_club = session["user"].get("club")
        print(
            f"[DEBUG] serve_mobile_matchup_simulator: User league_id: '{user_league_id}', series: '{user_series}', club: '{user_club}'"
        )

        # Get available teams for selection filtered by user's series (all teams in series)
        available_teams = get_teams_for_selection(
            user_league_id, user_series, None  # Don't filter by club - show all teams in series
        )
        print(
            f"[DEBUG] serve_mobile_matchup_simulator: Found {len(available_teams)} teams in league '{user_league_id}', series '{user_series}'"
        )

        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_matchup_simulator"
        )

        response = render_template(
            "mobile/matchup_simulator.html",
            session_data=session_data,
            available_teams=available_teams,
        )

        # Add cache-busting headers
        from flask import make_response

        response = make_response(response)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response

    except Exception as e:
        print(f"Error serving mobile matchup simulator: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")

        session_data = {"user": session["user"], "authenticated": True}

        return render_template(
            "mobile/matchup_simulator.html",
            session_data=session_data,
            available_teams=[],
            error="Failed to load team data",
        )


@mobile_bp.route("/api/run-simulation", methods=["POST"])
@login_required
def run_matchup_simulation():
    """API endpoint to run head-to-head simulation"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract team player IDs
        team_a_players = data.get("team_a_players", [])
        team_b_players = data.get("team_b_players", [])

        if len(team_a_players) != 2 or len(team_b_players) != 2:
            return jsonify({"error": "Each team must have exactly 2 players"}), 400

        # Convert to integers
        try:
            team_a_players = [int(pid) for pid in team_a_players]
            team_b_players = [int(pid) for pid in team_b_players]
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid player IDs provided"}), 400

        # Get user's league ID for filtering
        user_league_id = session["user"].get("league_id")

        # Run the simulation
        simulator = AdvancedMatchupSimulator()
        result = simulator.simulate_matchup(
            team_a_players, team_b_players, user_league_id
        )

        if "error" in result:
            return jsonify(result), 400

        # Log the simulation
        team_a_names = [p["name"] for p in result["team_a"]["players"]]
        team_b_names = [p["name"] for p in result["team_b"]["players"]]

        log_user_activity(
            session["user"]["email"],
            "simulation_run",
            page="mobile_matchup_simulator",
            details=f"Team A: {' & '.join(team_a_names)} vs Team B: {' & '.join(team_b_names)}",
        )

        return jsonify(result)

    except Exception as e:
        print(f"Error running simulation: {str(e)}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Simulation failed. Please try again."}), 500


@mobile_bp.route("/api/get-team-players/<int:team_id>")
@login_required
def get_team_players(team_id):
    """API endpoint to get players for a specific team using team_id"""
    try:
        if "user" not in session:
            return jsonify({"error": "Not authenticated"}), 401

        # Get user's league ID for filtering
        user_league_id = session["user"].get("league_id")
        print(
            f"[DEBUG] get_team_players: User league_id from session: '{user_league_id}' for team_id '{team_id}'"
        )

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
                print(f"[DEBUG] Could not convert league ID: {e}")
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id

        # Get team info first
        team_query = """
            SELECT t.id, t.team_name, COALESCE(t.team_alias, t.team_name) as display_name,
                   c.name as club_name, s.name as series_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            WHERE t.id = %s
        """
        if league_id_int:
            team_query += " AND t.league_id = %s"
            team_info = execute_query_one(team_query, [team_id, league_id_int])
        else:
            team_info = execute_query_one(team_query, [team_id])

        if not team_info:
            return jsonify({
                "success": False,
                "error": f"Team ID {team_id} not found",
                "players": [],
                "team_id": team_id,
            }), 404

        team_name = team_info["team_name"]
        display_name = team_info["display_name"]

        # Get players for the team using team_id
        if league_id_int:
            players_query = """
                SELECT DISTINCT 
                    p.id, 
                    p.first_name, 
                    p.last_name, 
                    p.pti,
                    p.tenniscores_player_id
                FROM players p
                WHERE p.team_id = %s AND p.league_id = %s AND p.is_active = true
                ORDER BY p.first_name, p.last_name
            """
            players_data = execute_query(players_query, [team_id, league_id_int])
        else:
            players_query = """
                SELECT DISTINCT 
                    p.id, 
                    p.first_name, 
                    p.last_name, 
                    p.pti,
                    p.tenniscores_player_id
                FROM players p
                WHERE p.team_id = %s AND p.is_active = true
                ORDER BY 
                    CASE WHEN p.captain_status = 'true' THEN 0 ELSE 1 END,
                    p.first_name, p.last_name
            """
            players_data = execute_query(players_query, [team_id])

        # Check if players are substitutes for this team
        from app.services.mobile_service import is_substitute_player
        
        # Format players data with substitute information
        players = []
        for player in players_data:
            is_substitute = False
            if player.get('tenniscores_player_id'):
                # Check if this player is a substitute for the current team
                is_substitute = is_substitute_player(
                    player['tenniscores_player_id'], 
                    team_id, 
                    user_league_id=user_league_id,
                    user_team_id=team_id
                )
            
            players.append({
                "id": player["id"],
                "name": f"{player['first_name']} {player['last_name']}",
                "pti": player.get("pti", 0),
                "isSubstitute": is_substitute
            })

        print(
            f"[DEBUG] get_team_players: Found {len(players)} players for team_id '{team_id}' ({display_name}) in league '{user_league_id}'"
        )

        if not players:
            return jsonify({
                "success": False,
                "error": f"No players found for team {display_name}",
                "players": [],
                "team_id": team_id,
                "team_name": display_name,
            }), 404

        return jsonify({
            "success": True, 
            "players": players, 
            "team_id": team_id,
            "team_name": display_name
        })

    except Exception as e:
        print(f"Error getting team players: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({"error": "Failed to get team players"}), 500


# Debug endpoint removed - new AdvancedMatchupSimulator uses sophisticated algorithms
# instead of the legacy debug functionality


@mobile_bp.route("/api/get-series")
@login_required
def get_series_for_subs():
    """Get all series data for substitute player discovery"""
    try:
        from app.services.admin_service import get_all_series_with_stats
        
        series = get_all_series_with_stats()
        
        # Get current user's series
        current_user_series = session["user"].get("series")
        
        # Format the response to match what find-subs expects
        return jsonify({
            "all_series_objects": series,
            "all_series": [s["name"] for s in series],  # Fallback series names
            "series": current_user_series  # Current user's series
        })
        
    except Exception as e:
        print(f"Error getting series for subs: {str(e)}")
        return jsonify({"error": str(e)}), 500


@mobile_bp.route("/api/get-team-series/<int:team_id>")
def get_team_series(team_id):
    """Get series information for a team ID"""
    try:
        # execute_query is already imported at module level
        
        query = """
            SELECT s.name as series_name, s.id as series_id
            FROM teams t
            JOIN series s ON t.series_id = s.id
            WHERE t.id = %s
        """
        
        result = execute_query(query, (team_id,))
        
        if result:
            return jsonify({
                "success": True,
                "series_name": result[0]['series_name'],
                "series_id": result[0]['series_id']
            })
        else:
            return jsonify({
                "success": False,
                "error": "Team not found"
            }), 404
            
    except Exception as e:
        print(f"Error getting team series: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@mobile_bp.route("/api/escrow-subs")
def get_escrow_subs():
    """Get substitute players for escrow opposing captain - no login required"""
    try:
        from app.services.player_service import get_players_by_league_and_series_id
        
        # Get parameters
        club_name = request.args.get("club_name")
        user_series = request.args.get("user_series", "Series 22")  # Default fallback
        
        if not club_name:
            return jsonify({"error": "club_name parameter is required"}), 400
        
        print(f"\n=== DEBUG: get_escrow_subs ===")
        print(f"Requested club_name: {club_name}")
        print(f"User series (for filtering): {user_series}")
        
        # Get the user's series value for comparison
        user_series_value = get_series_comparison_value(user_series)
        if not user_series_value:
            print("Could not determine user series value")
            return jsonify([])
        
        print(f"User series value: {user_series_value}")
        
        # Get all series in the league efficiently with a single query
        all_series_query = """
            SELECT DISTINCT s.id, s.name
            FROM series s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = %s
            ORDER BY s.name
        """
        
        all_series = execute_query(all_series_query, ("APTA_CHICAGO",))
        print(f"Found {len(all_series)} total series in APTA_CHICAGO")
        
        # Find higher series only (exclude same series)
        higher_series_ids = []
        for series in all_series:
            series_name = series['name']
            series_value = get_series_comparison_value(series_name)
            
            if series_value and is_higher_series(series_value, user_series_value):
                higher_series_ids.append(series['id'])
                print(f"Higher series found: {series_name} (ID: {series['id']})")
        
        print(f"Found {len(higher_series_ids)} higher series")
        
        if not higher_series_ids:
            print("No higher series found")
            return jsonify([])
        
        # Get players from all higher series at the specified club in one efficient query
        placeholders = ','.join(['%s'] * len(higher_series_ids))
        players_query = f"""
            SELECT DISTINCT 
                p.id,
                p.first_name,
                p.last_name,
                CONCAT(p.first_name, ' ', p.last_name) as name,
                c.name as club,
                s.name as series,
                p.pti,
                p.pti as rating,
                p.wins,
                p.losses,
                p.win_percentage as win_rate,
                p.series_id
            FROM players p
            JOIN clubs c ON p.club_id = c.id
            JOIN series s ON p.series_id = s.id
            WHERE p.series_id IN ({placeholders})
            AND c.name = %s
            AND p.league_id = (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')
        """
        
        params = higher_series_ids + [club_name]
        all_players = execute_query(players_query, params)
        
        print(f"Total found {len(all_players)} players in higher series at {club_name}")
        
        # Apply Rally's Recommendation Algorithm: PTI (70%), win rate (20%), series level (10%)
        for player in all_players:
            player['compositeScore'] = calculate_composite_score(player, user_series_value)
        
        # Debug: Show top 5 players before sorting
        print("Top 5 players before sorting:")
        for i, player in enumerate(all_players[:5]):
            print(f"  {i+1}. {player['name']} - PTI: {player['pti']}, Score: {player['compositeScore']:.2f}")
        
        # Sort by composite score (highest first - higher composite score means better player)
        all_players.sort(key=lambda x: x['compositeScore'], reverse=True)
        
        # Debug: Show top 5 players after sorting
        print("Top 5 players after sorting:")
        for i, player in enumerate(all_players[:5]):
            print(f"  {i+1}. {player['name']} - PTI: {player['pti']}, Score: {player['compositeScore']:.2f}")
        
        print("=== END DEBUG ===\n")
        
        return jsonify(all_players)
        
    except Exception as e:
        print(f"Error getting escrow subs: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


def get_series_comparison_value(series_name):
    """Get series comparison value for ranking (same logic as frontend)"""
    if not series_name:
        return None
    
    # Handle numeric series (e.g., "Series 1", "Series 2", "Chicago 22")
    import re
    numeric_match = re.search(r'(\d+)', series_name)
    if numeric_match:
        return {"type": "numeric", "value": int(numeric_match.group(1))}
    
    # Handle letter series (e.g., "Series A", "Series B", "Division G")
    letter_match = re.search(r'([A-Z])', series_name)
    if letter_match:
        letter = letter_match.group(1).upper()
        precedence = ord(letter) - ord('A') + 1  # A=1, B=2, etc.
        return {"type": "letter", "value": precedence}
    
    return None


def is_higher_series(series_value, user_series_value):
    """Check if series_value is higher than user_series_value"""
    if not series_value or not user_series_value:
        return False
    
    # Both must be same type
    if series_value["type"] != user_series_value["type"]:
        return False
    
    # For numeric series, higher number = higher series (Series 23 > Series 22)
    if series_value["type"] == "numeric":
        return series_value["value"] > user_series_value["value"]
    
    # For letter series, higher letter = higher series (Series B > Series A)
    if series_value["type"] == "letter":
        return series_value["value"] > user_series_value["value"]
    
    return False


def calculate_composite_score(player, user_series_value):
    """Calculate Rally's Recommendation Algorithm composite score: PTI (70%), win rate (20%), series level (10%)"""
    try:
        # Get PTI (70% weight)
        pti = float(player.get('pti', 0) or 0)
        
        # Get win rate (20% weight)
        win_rate = float(player.get('win_rate', 0) or 0)
        
        # Get series level (10% weight)
        series_name = player.get('series', '')
        series_value = get_series_comparison_value(series_name)
        
        # Calculate composite score
        score = 0
        
        # PTI component (70%) - lower PTI is better, so invert it
        # Use a baseline of 100 and subtract PTI to make lower values give higher scores
        score += (100 - pti) * 0.7
        
        # Win rate component (20%)
        score += win_rate * 0.2
        
        # Series level component (10%) - higher series get higher scores
        if series_value:
            if series_value["type"] == "numeric":
                # For numeric series, higher numbers are higher series (Series 23 > Series 22)
                # Give bonus points for being in higher series
                series_bonus = (series_value["value"] - user_series_value["value"]) * 2
                score += max(0, series_bonus) * 0.1
            elif series_value["type"] == "letter":
                # For letter series, higher letters are higher series (Series B > Series A)
                if user_series_value["type"] == "numeric":
                    # If user is in numeric series, any letter series gets bonus
                    score += 5 * 0.1
                else:
                    # Both letter series - compare
                    series_bonus = (series_value["value"] - user_series_value["value"]) * 2
                    score += max(0, series_bonus) * 0.1
        
        return score
        
    except (ValueError, TypeError) as e:
        print(f"Error calculating composite score for player {player.get('name', 'unknown')}: {e}")
        return 0




@mobile_bp.route("/mobile/polls")
@login_required
def serve_mobile_polls():
    """Serve the mobile team polls management page"""
    # Check if user is admin
    from app.services.admin_service import is_user_admin

    user_is_admin = is_user_admin(session["user"]["email"])

    session_data = {
        "user": session["user"],
        "authenticated": True,
        "is_admin": user_is_admin,
    }

    log_user_activity(session["user"]["email"], "page_visit", page="mobile_polls")
    return render_template("mobile/team_polls.html", session_data=session_data)


@mobile_bp.route("/mobile/polls/<int:poll_id>")
def serve_mobile_poll_vote(poll_id):
    """Serve the mobile poll voting page (public link)"""
    # Check if user is logged in
    if "user" not in session:
        # Store the poll URL for redirect after login
        session["redirect_after_login"] = f"/mobile/polls/{poll_id}"
        return redirect("/login")

    session_data = {"user": session["user"], "authenticated": True, "poll_id": poll_id}

    log_user_activity(
        session["user"]["email"],
        "page_visit",
        page="mobile_poll_vote",
        details=f"Poll {poll_id}",
    )
    return render_template(
        "mobile/poll_vote.html", session_data=session_data, poll_id=poll_id
    )


def get_user_team_id(user):
    """Get user's team ID from their player association (integer foreign key)
    Uses tenniscores_player_id for reliable identification instead of name matching
    For multi-team players, prefer teams with most recent match activity in current league
    """
    try:
        user_id = user.get("id")
        player_id = user.get("tenniscores_player_id")  # Use player ID instead of names
        email = user.get("email")

        # Get user's league context if available
        user_league_id = user.get("league_id")

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

        # Try multiple approaches to find the user's team
        team_id = None

        # Approach 1: If we have user_id, try user_player_associations with league filter
        if user_id and league_id_int:
            league_filtered_query = """
                SELECT p.team_id, p.league_id, l.league_id as league_code
                FROM players p
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                WHERE upa.user_id = %s AND p.is_active = TRUE AND p.team_id IS NOT NULL
                AND p.league_id = %s
                LIMIT 1
            """
            result = execute_query_one(league_filtered_query, [user_id, league_id_int])
            if result:
                team_id = result["team_id"]

        # Approach 2: Use tenniscores_player_id for reliable lookup (FIXED: no more name matching)
        if not team_id and player_id and league_id_int:
            player_id_query = """
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
                AND p.team_id IS NOT NULL
                ORDER BY last_match_date DESC NULLS LAST, p.team_id DESC
                LIMIT 1
            """
            result = execute_query_one(player_id_query, [player_id, league_id_int])
            if result:
                team_id = result["team_id"]
                print(f"[DEBUG] get_user_team_id: Found team {result['team_name']} (ID: {team_id}) for player {player_id}")

        # Approach 3: Fallback to any league if we have player_id but no league context
        if not team_id and player_id:
            fallback_query = """
                SELECT p.team_id, t.team_name,
                       (SELECT MAX(match_date) 
                        FROM match_scores ms 
                        WHERE (ms.home_player_1_id = p.tenniscores_player_id 
                               OR ms.home_player_2_id = p.tenniscores_player_id
                               OR ms.away_player_1_id = p.tenniscores_player_id 
                               OR ms.away_player_2_id = p.tenniscores_player_id)
                        AND (ms.home_team_id = p.team_id OR ms.away_team_id = p.team_id)
                       ) as last_match_date
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id = %s AND p.is_active = TRUE 
                AND p.team_id IS NOT NULL
                ORDER BY last_match_date DESC NULLS LAST, p.team_id DESC
                LIMIT 1
            """
            result = execute_query_one(fallback_query, [player_id])
            if result:
                team_id = result["team_id"]
                print(f"[DEBUG] get_user_team_id: Fallback found team {result['team_name']} (ID: {team_id}) for player {player_id}")

        # REMOVED: All name-based approaches (Approaches 2-4 from original)
        # Name matching was the root cause of Rob Werman's issue

        return team_id

    except Exception as e:
        print(f"Error getting user team ID: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return None


def get_player_match_count(player_id, user_league_id=None, team_id=None):
    """Get match count for a specific player, filtered by league and optionally by team"""
    try:
        if not player_id:
            return 0

            # Always use a simple, reliable count query
        if user_league_id:
            # Convert string league_id to integer foreign key if needed
            league_id_int = None
            if isinstance(user_league_id, str) and user_league_id != "":
                try:
                    # First try league_id column (string comparison only to avoid type errors)
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                    else:
                        # Try using the league_id directly as an integer
                        try:
                            league_id_int = int(user_league_id)
                        except ValueError:
                            pass
                except Exception as e:
                    print(f"Error converting league ID: {e}")
            elif isinstance(user_league_id, int):
                league_id_int = user_league_id

            if league_id_int:
                # Use a more specific query that avoids any potential duplication
                if team_id:
                    # Filter by both league and team for team-specific counts
                    # This ensures we ONLY count matches where this player played FOR this specific team
                    match_count_query = """
                        SELECT COUNT(DISTINCT id) as match_count
                        FROM match_scores
                        WHERE (home_player_1_id = %s 
                           OR home_player_2_id = %s 
                           OR away_player_1_id = %s 
                           OR away_player_2_id = %s)
                        AND league_id = %s
                        AND (home_team_id = %s OR away_team_id = %s)
                    """
                    result = execute_query_one(
                        match_count_query,
                        [
                            player_id,
                            player_id,
                            player_id,
                            player_id,
                            league_id_int,
                            team_id,
                            team_id,
                        ],
                    )
                else:
                    # Filter by league only
                    match_count_query = """
                        SELECT COUNT(DISTINCT id) as match_count
                        FROM match_scores
                        WHERE (home_player_1_id = %s 
                           OR home_player_2_id = %s 
                           OR away_player_1_id = %s 
                           OR away_player_2_id = %s)
                        AND league_id = %s
                    """
                    result = execute_query_one(
                        match_count_query,
                        [player_id, player_id, player_id, player_id, league_id_int],
                    )
            else:
                # Fallback to no league filter if conversion failed
                match_count_query = """
                    SELECT COUNT(DISTINCT id) as match_count
                    FROM match_scores
                    WHERE home_player_1_id = %s 
                       OR home_player_2_id = %s 
                       OR away_player_1_id = %s 
                       OR away_player_2_id = %s
                """
                result = execute_query_one(
                    match_count_query, [player_id, player_id, player_id, player_id]
                )
        else:
            # No league filter provided
            match_count_query = """
                SELECT COUNT(DISTINCT id) as match_count
                FROM match_scores
                WHERE home_player_1_id = %s 
                   OR home_player_2_id = %s 
                   OR away_player_1_id = %s 
                   OR away_player_2_id = %s
            """
            result = execute_query_one(
                match_count_query, [player_id, player_id, player_id, player_id]
            )

        match_count = result["match_count"] if result else 0

        # Additional validation - ensure count is reasonable
        if team_id and match_count > 25:
            # With team filtering, counts should be much lower
            print(
                f"[WARNING] Suspiciously high team-specific match count ({match_count}) for player {player_id}"
            )
            print(f"[WARNING] This suggests the team filter isn't working properly")
        elif not team_id and match_count > 30:
            print(
                f"[WARNING] Suspiciously high match count ({match_count}) for player {player_id}"
            )
            print(
                f"[WARNING] This might indicate a data issue or cross-league contamination"
            )

            # If no team filter but we have league filter, still reasonable
            if not user_league_id:
                # For safety, cap at a reasonable maximum when no filters
                match_count = min(match_count, 25)
                print(
                    f"[WARNING] Capped match count to {match_count} for safety (no filters)"
                )

        return match_count

    except Exception as e:
        print(f"Error getting match count for player {player_id}: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return 0


def get_team_members_with_court_stats(team_id, user):
    """Get all active players for a team with their court assignment statistics - OPTIMIZED VERSION"""

    try:
        if not team_id:
            return []

        # Get user's league_id for filtering (extract once at top)
        user_league_id = user.get("league_id")
        
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

        # OPTIMIZED: Single comprehensive query using CTEs to eliminate N+1 queries
        # This replaces ~100+ individual queries with 1 comprehensive query
        if league_id_int:
            comprehensive_query = """
                WITH team_player_matches AS (
                    -- Get all matches for this team's players with court assignment info
                    SELECT 
                        ms.id as match_id,
                        ms.home_player_1_id,
                        ms.home_player_2_id,
                        ms.away_player_1_id,
                        ms.away_player_2_id,
                        ms.winner,
                        ms.home_team,
                        ms.away_team,
                        TO_CHAR(ms.match_date, 'DD-Mon-YY') as match_date_formatted,
                        ms.match_date,
                        -- Determine court position by ordering within team matchup
                        ROW_NUMBER() OVER (
                            PARTITION BY ms.match_date, ms.home_team, ms.away_team 
                            ORDER BY ms.id
                        ) as court_num
                    FROM match_scores ms
                    WHERE (ms.home_team_id = %s OR ms.away_team_id = %s)
                    AND ms.league_id = %s
                ),
                player_match_stats AS (
                    -- Calculate match counts, wins, and court assignments for each player
                    SELECT 
                        player_id,
                        COUNT(DISTINCT match_id) as match_count,
                        SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN NOT won THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN court_num = 1 THEN 1 ELSE 0 END) as court1,
                        SUM(CASE WHEN court_num = 2 THEN 1 ELSE 0 END) as court2,
                        SUM(CASE WHEN court_num = 3 THEN 1 ELSE 0 END) as court3,
                        SUM(CASE WHEN court_num = 4 THEN 1 ELSE 0 END) as court4,
                        SUM(CASE WHEN court_num = 5 THEN 1 ELSE 0 END) as court5,
                        SUM(CASE WHEN court_num = 6 THEN 1 ELSE 0 END) as court6
                    FROM (
                        -- Home team players
                        SELECT 
                            tpm.match_id,
                            NULLIF(TRIM(tpm.home_player_1_id), '') as player_id,
                            tpm.winner = 'home' as won,
                            LEAST(tpm.court_num, 6) as court_num
                        FROM team_player_matches tpm
                        WHERE NULLIF(TRIM(tpm.home_player_1_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        SELECT 
                            tpm.match_id,
                            NULLIF(TRIM(tpm.home_player_2_id), '') as player_id,
                            tpm.winner = 'home' as won,
                            LEAST(tpm.court_num, 6) as court_num
                        FROM team_player_matches tpm
                        WHERE NULLIF(TRIM(tpm.home_player_2_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        -- Away team players
                        SELECT 
                            tpm.match_id,
                            NULLIF(TRIM(tpm.away_player_1_id), '') as player_id,
                            tpm.winner = 'away' as won,
                            LEAST(tpm.court_num, 6) as court_num
                        FROM team_player_matches tpm
                        WHERE NULLIF(TRIM(tpm.away_player_1_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        SELECT 
                            tpm.match_id,
                            NULLIF(TRIM(tpm.away_player_2_id), '') as player_id,
                            tpm.winner = 'away' as won,
                            LEAST(tpm.court_num, 6) as court_num
                        FROM team_player_matches tpm
                        WHERE NULLIF(TRIM(tpm.away_player_2_id), '') IS NOT NULL
                    ) all_player_matches
                    WHERE player_id IS NOT NULL
                    GROUP BY player_id
                )
                SELECT 
                    p.id,
                    p.first_name,
                    p.last_name,
                    p.pti,
                    p.tenniscores_player_id,
                    p.captain_status,
                    COALESCE(pms.match_count, 0) as match_count,
                    COALESCE(pms.wins, 0) as wins,
                    COALESCE(pms.losses, 0) as losses,
                    COALESCE(pms.court1, 0) as court1,
                    COALESCE(pms.court2, 0) as court2,
                    COALESCE(pms.court3, 0) as court3,
                    COALESCE(pms.court4, 0) as court4,
                    COALESCE(pms.court5, 0) as court5,
                    COALESCE(pms.court6, 0) as court6
                FROM players p
                LEFT JOIN player_match_stats pms ON p.tenniscores_player_id = pms.player_id
                WHERE p.team_id = %s AND p.league_id = %s AND p.is_active = TRUE
                ORDER BY 
                    CASE WHEN p.captain_status = 'true' THEN 0 ELSE 1 END,
                    p.last_name, p.first_name
            """
            
            members_data = execute_query(comprehensive_query, [team_id, team_id, league_id_int, team_id, league_id_int])
        else:
            # Fallback without league filter
            comprehensive_query = """
                WITH team_player_matches AS (
                    -- Get all matches for this team's players with court assignment info
                    SELECT 
                        ms.id as match_id,
                        ms.home_player_1_id,
                        ms.home_player_2_id,
                        ms.away_player_1_id,
                        ms.away_player_2_id,
                        ms.winner,
                        ms.home_team,
                        ms.away_team,
                        TO_CHAR(ms.match_date, 'DD-Mon-YY') as match_date_formatted,
                        ms.match_date,
                        -- Determine court position by ordering within team matchup
                        ROW_NUMBER() OVER (
                            PARTITION BY ms.match_date, ms.home_team, ms.away_team 
                            ORDER BY ms.id
                        ) as court_num
                    FROM match_scores ms
                    WHERE (ms.home_team_id = %s OR ms.away_team_id = %s)
                ),
                player_match_stats AS (
                    -- Calculate match counts, wins, and court assignments for each player
                    SELECT 
                        player_id,
                        COUNT(DISTINCT match_id) as match_count,
                        SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN NOT won THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN court_num = 1 THEN 1 ELSE 0 END) as court1,
                        SUM(CASE WHEN court_num = 2 THEN 1 ELSE 0 END) as court2,
                        SUM(CASE WHEN court_num = 3 THEN 1 ELSE 0 END) as court3,
                        SUM(CASE WHEN court_num = 4 THEN 1 ELSE 0 END) as court4,
                        SUM(CASE WHEN court_num = 5 THEN 1 ELSE 0 END) as court5,
                        SUM(CASE WHEN court_num = 6 THEN 1 ELSE 0 END) as court6
                    FROM (
                        -- Home team players
                        SELECT 
                            tpm.match_id,
                            NULLIF(TRIM(tpm.home_player_1_id), '') as player_id,
                            tpm.winner = 'home' as won,
                            LEAST(tpm.court_num, 6) as court_num
                        FROM team_player_matches tpm
                        WHERE NULLIF(TRIM(tpm.home_player_1_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        SELECT 
                            tpm.match_id,
                            NULLIF(TRIM(tpm.home_player_2_id), '') as player_id,
                            tpm.winner = 'home' as won,
                            LEAST(tpm.court_num, 6) as court_num
                        FROM team_player_matches tpm
                        WHERE NULLIF(TRIM(tpm.home_player_2_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        -- Away team players
                        SELECT 
                            tpm.match_id,
                            NULLIF(TRIM(tpm.away_player_1_id), '') as player_id,
                            tpm.winner = 'away' as won,
                            LEAST(tpm.court_num, 6) as court_num
                        FROM team_player_matches tpm
                        WHERE NULLIF(TRIM(tpm.away_player_1_id), '') IS NOT NULL
                        
                        UNION ALL
                        
                        SELECT 
                            tpm.match_id,
                            NULLIF(TRIM(tpm.away_player_2_id), '') as player_id,
                            tpm.winner = 'away' as won,
                            LEAST(tpm.court_num, 6) as court_num
                        FROM team_player_matches tpm
                        WHERE NULLIF(TRIM(tpm.away_player_2_id), '') IS NOT NULL
                    ) all_player_matches
                    WHERE player_id IS NOT NULL
                    GROUP BY player_id
                )
                SELECT 
                    p.id,
                    p.first_name,
                    p.last_name,
                    p.pti,
                    p.tenniscores_player_id,
                    p.captain_status,
                    COALESCE(pms.match_count, 0) as match_count,
                    COALESCE(pms.wins, 0) as wins,
                    COALESCE(pms.losses, 0) as losses,
                    COALESCE(pms.court1, 0) as court1,
                    COALESCE(pms.court2, 0) as court2,
                    COALESCE(pms.court3, 0) as court3,
                    COALESCE(pms.court4, 0) as court4,
                    COALESCE(pms.court5, 0) as court5,
                    COALESCE(pms.court6, 0) as court6
                FROM players p
                LEFT JOIN player_match_stats pms ON p.tenniscores_player_id = pms.player_id
                WHERE p.team_id = %s AND p.is_active = TRUE
                ORDER BY 
                    CASE WHEN p.captain_status = 'true' THEN 0 ELSE 1 END,
                    p.last_name, p.first_name
            """
            
            members_data = execute_query(comprehensive_query, [team_id, team_id, team_id])

        if not members_data:
            return []

        # Transform to the expected format
        members_with_stats = []
        for member in members_data:
            full_name = f"{member['last_name']}, {member['first_name']}"
            
            # Build court stats dictionary in the expected format
            court_stats = {}
            for court_num in range(1, 7):  # Courts 1-6
                court_key = f"court{court_num}"
                court_count = member.get(court_key, 0)
                if court_count > 0:
                    court_stats[court_key] = court_count

            member_data = {
                "id": member["id"],
                "name": full_name,
                "first_name": member["first_name"],
                "last_name": member["last_name"],
                "pti": member.get("pti", 0),
                "tenniscores_player_id": member["tenniscores_player_id"],
                "captain_status": member.get("captain_status"),
                "court_stats": court_stats,
                "match_count": member.get("match_count", 0),
                "wins": member.get("wins", 0),  # Include wins from optimized query
                "losses": member.get("losses", 0),  # Include losses from optimized query
            }
            members_with_stats.append(member_data)

        print(f"[OPTIMIZED] Loaded {len(members_with_stats)} team members with 1 comprehensive query instead of ~{len(members_with_stats) * 10}+ individual queries")
        return members_with_stats

    except Exception as e:
        print(f"Error getting team members with court stats: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return []


def create_sample_court_data(members):
    """Create sample court assignment data for testing when no real data is found"""
    import random

    court_assignments = {}

    for i, member in enumerate(members):
        if member.get("tenniscores_player_id"):
            # Create random court assignments
            court_assignments[member["tenniscores_player_id"]] = {
                "court1": random.randint(0, 8),
                "court2": random.randint(0, 8),
                "court3": random.randint(0, 8),
                "court4": random.randint(0, 8),
            }

    return court_assignments


def calculate_player_court_stats(team_matches, team_name, members, user_league_id=None, team_id=None):
    """Calculate how many times each player played on each court, filtered by league and team context"""
    try:
        from collections import defaultdict
        from datetime import datetime

        # Create player court statistics
        player_court_stats = defaultdict(lambda: defaultdict(int))

        # Create lookup of tenniscores_player_id to full name
        player_name_lookup = {}
        for member in members:
            if member.get("tenniscores_player_id"):
                full_name = f"{member['first_name']} {member['last_name']}"
                player_name_lookup[member["tenniscores_player_id"]] = full_name

        # Convert league_id for filtering if provided
        league_id_int = None
        if user_league_id:
            if isinstance(user_league_id, str) and user_league_id != "":
                try:
                    # First try league_id column (string comparison only to avoid type errors)
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                    else:
                        # Try using the league_id directly as an integer
                        try:
                            league_id_int = int(user_league_id)
                        except ValueError:
                            pass
                except Exception as e:
                    pass
            elif isinstance(user_league_id, int):
                league_id_int = user_league_id

        # For each team member, get their matches filtered by league context
        for member in members:
            player_id = member.get("tenniscores_player_id")
            if not player_id:
                continue

            player_name = f"{member['first_name']} {member['last_name']}"

            # Get player matches filtered by league and team if available
            if league_id_int and team_id:
                # Filter by both league and team for multi-team players
                all_player_matches_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        match_date,
                        home_team as "Home Team",
                        away_team as "Away Team",
                        home_player_1_id as "Home Player 1",
                        home_player_2_id as "Home Player 2",
                        away_player_1_id as "Away Player 1",
                        away_player_2_id as "Away Player 2",
                        id
                    FROM match_scores
                    WHERE (home_player_1_id = %s 
                       OR home_player_2_id = %s 
                       OR away_player_1_id = %s 
                       OR away_player_2_id = %s)
                    AND league_id = %s
                    AND (home_team_id = %s OR away_team_id = %s)
                    ORDER BY match_date, id
                """
                player_matches = execute_query(
                    all_player_matches_query,
                    [player_id, player_id, player_id, player_id, league_id_int, team_id, team_id],
                )
            elif league_id_int:
                # Filter by league only if no team_id available
                all_player_matches_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        match_date,
                        home_team as "Home Team",
                        away_team as "Away Team",
                        home_player_1_id as "Home Player 1",
                        home_player_2_id as "Home Player 2",
                        away_player_1_id as "Away Player 1",
                        away_player_2_id as "Away Player 2",
                        id
                    FROM match_scores
                    WHERE (home_player_1_id = %s 
                       OR home_player_2_id = %s 
                       OR away_player_1_id = %s 
                       OR away_player_2_id = %s)
                    AND league_id = %s
                    ORDER BY match_date, id
                """
                player_matches = execute_query(
                    all_player_matches_query,
                    [player_id, player_id, player_id, player_id, league_id_int],
                )
            elif team_id:
                # Filter by team only if no league filter available
                all_player_matches_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        match_date,
                        home_team as "Home Team",
                        away_team as "Away Team",
                        home_player_1_id as "Home Player 1",
                        home_player_2_id as "Home Player 2",
                        away_player_1_id as "Away Player 1",
                        away_player_2_id as "Away Player 2",
                        id
                    FROM match_scores
                    WHERE (home_player_1_id = %s 
                       OR home_player_2_id = %s 
                       OR away_player_1_id = %s 
                       OR away_player_2_id = %s)
                    AND (home_team_id = %s OR away_team_id = %s)
                    ORDER BY match_date, id
                """
                player_matches = execute_query(
                    all_player_matches_query,
                    [player_id, player_id, player_id, player_id, team_id, team_id],
                )
            else:
                # Fallback to all matches if no filters available
                all_player_matches_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        match_date,
                        home_team as "Home Team",
                        away_team as "Away Team",
                        home_player_1_id as "Home Player 1",
                        home_player_2_id as "Home Player 2",
                        away_player_1_id as "Away Player 1",
                        away_player_2_id as "Away Player 2",
                        id
                    FROM match_scores
                    WHERE (home_player_1_id = %s 
                       OR home_player_2_id = %s 
                       OR away_player_1_id = %s 
                       OR away_player_2_id = %s)
                    ORDER BY match_date, id
                """
                player_matches = execute_query(
                    all_player_matches_query,
                    [player_id, player_id, player_id, player_id],
                )

            if not player_matches:
                continue

            # Group player's matches by date and team matchup (same logic as existing court systems)
            matches_by_date_and_teams = defaultdict(lambda: defaultdict(list))
            for match in player_matches:
                date = match.get("Date")
                home_team = match.get("Home Team", "")
                away_team = match.get("Away Team", "")
                team_matchup = f"{home_team} vs {away_team}"
                matches_by_date_and_teams[date][team_matchup].append(match)

            # Process each match to determine court assignment
            for match in player_matches:
                # Determine if player is home or away in this match
                is_home_player = (
                    match.get("Home Player 1") == player_id
                    or match.get("Home Player 2") == player_id
                )

                # Determine court assignment using the correct team matchup logic
                match_date = match.get("Date")
                home_team = match.get("Home Team", "")
                away_team = match.get("Away Team", "")
                team_matchup = f"{home_team} vs {away_team}"
                match_id = match.get("id")

                # Get ALL matches for this team matchup on this date, ordered by database ID
                # Include league filter if available to ensure we're looking at the right context
                if league_id_int:
                    team_matchup_query = """
                        SELECT id, home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
                        FROM match_scores 
                        WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                        AND home_team = %s 
                        AND away_team = %s
                        AND league_id = %s
                        ORDER BY id
                    """
                    team_day_matches_ordered = execute_query(
                        team_matchup_query, [match_date, home_team, away_team, league_id_int]
                    )
                else:
                    team_matchup_query = """
                        SELECT id, home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
                        FROM match_scores 
                        WHERE TO_CHAR(match_date, 'DD-Mon-YY') = %s
                        AND home_team = %s 
                        AND away_team = %s
                        ORDER BY id
                    """
                    team_day_matches_ordered = execute_query(
                        team_matchup_query, [match_date, home_team, away_team]
                    )

                # Find this match's position within the ordered team matchup to assign court
                court_num = None
                for i, team_match in enumerate(team_day_matches_ordered, 1):
                    if team_match.get("id") == match_id:
                        court_num = min(i, 6)  # Courts 1-6 max within this team matchup
                        break

                if court_num is None:
                    continue

                court_key = f"court{court_num}"
                player_court_stats[player_id][court_key] += 1

        # Convert defaultdict to regular dict for JSON serialization
        result_court_stats = {}
        for player_id, courts in player_court_stats.items():
            result_court_stats[player_id] = dict(courts)

        return result_court_stats

    except Exception as e:
        print(f"Error calculating player court stats: {e}")
        return {}


def get_mobile_track_byes_data(user):
    """Get track byes and court assignment data for mobile interface using priority-based team detection like analyze-me"""
    try:
        from app.services.session_service import get_session_data_for_user
        
        user_email = user.get("email")
        player_id = user.get("tenniscores_player_id")
        
        # PRIORITY-BASED TEAM DETECTION (same as analyze-me page)
        user_team_id = None
        user_team_name = None
        
        # PRIORITY 1: Use team_id from session if available (most reliable for multi-team players)
        session_team_id = user.get("team_id")
        print(f"[DEBUG] Track-byes-courts: session_team_id from user: {session_team_id}")
        
        if session_team_id:
            try:
                # Get team name for the specific team_id from session
                session_team_query = """
                    SELECT t.id, t.team_name
                    FROM teams t
                    WHERE t.id = %s
                """
                session_team_result = execute_query_one(session_team_query, [session_team_id])
                if session_team_result:
                    user_team_id = session_team_result['id'] 
                    user_team_name = session_team_result['team_name']
                    print(f"[DEBUG] Track-byes-courts: Using team_id from session: team_id={user_team_id}, team_name={user_team_name}")
                else:
                    print(f"[DEBUG] Track-byes-courts: Session team_id {session_team_id} not found in teams table")
            except Exception as e:
                print(f"[DEBUG] Track-byes-courts: Error getting team from session team_id {session_team_id}: {e}")
        
        # PRIORITY 2: Use team_context from user if provided (from composite player URL)
        if not user_team_id:
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
                        print(f"[DEBUG] Track-byes-courts: Using team_context from URL: team_id={user_team_id}, team_name={user_team_name}")
                    else:
                        print(f"[DEBUG] Track-byes-courts: team_context {team_context} not found in teams table")
                except Exception as e:
                    print(f"[DEBUG] Track-byes-courts: Error getting team from team_context {team_context}: {e}")
        
        # PRIORITY 3: Use session service as fallback if no direct team_id
        if not user_team_id:
            print(f"[DEBUG] Track-byes-courts: No direct team_id, using session service fallback")
            session_data = get_session_data_for_user(user_email)
            if session_data:
                user_team_id = session_data.get("team_id")
                if user_team_id:
                    try:
                        session_team_query = """
                            SELECT t.id, t.team_name
                            FROM teams t
                            WHERE t.id = %s
                        """
                        session_team_result = execute_query_one(session_team_query, [user_team_id])
                        if session_team_result:
                            user_team_name = session_team_result['team_name']
                            print(f"[DEBUG] Track-byes-courts: Session service provided: team_id={user_team_id}, team_name={user_team_name}")
                    except Exception as e:
                        print(f"[DEBUG] Track-byes-courts: Error getting team name from session service team_id: {e}")
        
        # If still no team, return error
        if not user_team_id:
            return {
                "team_members": [],
                "current_team_info": None,
                "user_teams": [],
                "available_courts": [
                    {"key": "court1", "name": "Court 1"},
                    {"key": "court2", "name": "Court 2"},
                    {"key": "court3", "name": "Court 3"},
                    {"key": "court4", "name": "Court 4"},
                ],
                "error": "No team ID found - please check your profile settings"
            }
        
        print(f"[DEBUG] Track-byes-courts: Final team selection: team_id={user_team_id}, team_name={user_team_name}")
        
        # Get team members with court stats using existing function
        team_members = get_team_members_with_court_stats(user_team_id, user)
        
        # Get additional team info from session or database
        # Check if we're currently impersonating - if so, don't rebuild session
        from flask import session as flask_session
        is_impersonating = flask_session.get("impersonation_active", False)
        
        if is_impersonating:
            # During impersonation, use current session data instead of rebuilding
            session_data = user
        else:
            # Use helper function to determine if we should preserve session or refresh
            current_session = session.get("user", {})
            
            if should_preserve_session_context(user_email, current_session):
                # Preserve current session (team switch protection + no league switch detected)
                session_data = current_session
                print(f"[DEBUG] Track-byes-courts - Preserving existing team context: {current_session.get('club')} - {current_session.get('series')}")
            else:
                # Session is incomplete, invalid, or league switch detected - refresh from database
                session_data = get_session_data_for_user(user_email)
                print(f"[DEBUG] Track-byes-courts - Session incomplete or league switch detected, refreshing from database")
        
        # Get current team info
        current_team_info = {
            "team_id": user_team_id,
            "team_name": user_team_name or session_data.get("series", "Unknown Team"),
            "club_name": session_data.get("club", "Unknown Club") if session_data else "Unknown Club",
            "series_name": session_data.get("series", "Unknown Series") if session_data else "Unknown Series"
        }
        
        # For now, just return single team - multi-team support can be added later
        user_teams = [current_team_info]
        
        # Standard courts available
        available_courts = [
            {"key": "court1", "name": "Court 1"},
            {"key": "court2", "name": "Court 2"},
            {"key": "court3", "name": "Court 3"},
            {"key": "court4", "name": "Court 4"},
        ]
        
        return {
            "team_members": team_members,
            "current_team_info": current_team_info,
            "user_teams": user_teams,
            "available_courts": available_courts,
            "team_id": user_team_id
        }
        
    except Exception as e:
        logger.error(f"Error getting mobile track byes data: {str(e)}")
        import traceback
        print(f"[DEBUG] Track-byes-courts error traceback: {traceback.format_exc()}")
        return {
            "team_members": [],
            "current_team_info": None,
            "user_teams": [],
            "available_courts": [
                {"key": "court1", "name": "Court 1"},
                {"key": "court2", "name": "Court 2"},
                {"key": "court3", "name": "Court 3"},
                {"key": "court4", "name": "Court 4"},
            ],
            "error": str(e)
        }


def get_court_assignments_data(user):
    """Get court assignments data for mobile interface"""
    try:
        # This is a simplified version - could be expanded for more complex court assignment tracking
        return {
            "assignments_summary": "Court assignments based on historical match data",
            "last_updated": datetime.now().strftime("%m-%d-%y @ %I:%M %p"),
            "data_source": "Database match records"
        }
        
    except Exception as e:
        logger.error(f"Error getting court assignments data: {str(e)}")
        return {
            "assignments_summary": "Error loading court assignments",
            "last_updated": None,
            "data_source": "Error",
            "error": str(e)
        }


@mobile_bp.route("/mobile/track-byes-courts")
@login_required
def serve_track_byes_courts():
    """Serve the Track Byes & Court Assignments page with simple league switching"""
    try:
        from app.services.session_service import switch_user_league, get_session_data_for_user
        
        user = session["user"]
        user_email = user.get("email")

        # Handle league switching via URL parameter (?league_id=APTA_CHICAGO or ?league_id=NSTF)
        requested_league_id = request.args.get('league_id')
        if requested_league_id:
            logger.info(f"League switch requested via URL: {user_email} -> {requested_league_id}")
            
            # Switch to new league - but not during impersonation
            is_impersonating = session.get("impersonation_active", False)
            
            if is_impersonating:
                logger.info(f"Impersonation active - preserving context instead of switching leagues")
            elif switch_user_league(user_email, requested_league_id):
                # Update session with fresh data
                fresh_session_data = get_session_data_for_user(user_email)
                if fresh_session_data:
                    session["user"] = fresh_session_data
                    session.modified = True
                    user = session["user"]  # Use updated user data
                    logger.info(f"Successfully switched to {fresh_session_data['league_name']}")
                else:
                    logger.warning(f"Failed to refresh session after league switch")
            else:
                logger.warning(f"Failed to switch to league: {requested_league_id}")

        # Get updated track byes and courts data
        track_byes_data = get_mobile_track_byes_data(user)
        court_assignments_data = get_court_assignments_data(user)
        
        session_data = {"user": user, "authenticated": True}
        log_user_activity(user["email"], "page_visit", page="track_byes_courts")
        
        # Extract data for template - the template expects individual variables, not nested data
        return render_template(
            "mobile/track_byes_courts.html",
            session_data=session_data,
            team_members=track_byes_data.get("team_members", []),
            current_team_info=track_byes_data.get("current_team_info"),
            user_teams=track_byes_data.get("user_teams", []),
            available_courts=track_byes_data.get("available_courts", []),
            team_id=track_byes_data.get("team_id"),
            court_assignments_data=court_assignments_data,
        )
        
    except Exception as e:
        logger.error(f"Error serving track-byes-courts: {str(e)}")
        return render_template(
            "mobile/error.html",
            error_message="Failed to load track byes and courts data"
        ), 500


# Upload endpoint removed - professional photos now in place

@mobile_bp.route("/pti-calculator")
@login_required
def pti_calculator():
    """Serve the PTI calculator page"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(session["user"]["email"], "page_visit", page="pti_calculator")
    return render_template("mobile/pti_calculator.html", session_data=session_data)


@mobile_bp.route("/api/calculate-pti", methods=["POST"])
@login_required
def calculate_pti_adjustment():
    """Calculate PTI adjustments based on match results using Glicko-2 algorithm"""
    try:
        data = request.get_json()
        
        # Extract input data
        player_pti = float(data.get('player_pti', 0))
        partner_pti = float(data.get('partner_pti', 0))
        opp1_pti = float(data.get('opp1_pti', 0))
        opp2_pti = float(data.get('opp2_pti', 0))
        
        # Map numeric experience values to strings for v4 algorithm
        def map_experience(exp_val):
            exp_val = float(exp_val)
            if exp_val >= 7.0:
                return "New Player"
            elif exp_val >= 5.0:
                return "1-10"
            elif exp_val >= 4.0:
                return "10-30"
            else:
                return "30+"
        
        player_exp = map_experience(data.get('player_exp', 3.2))
        partner_exp = map_experience(data.get('partner_exp', 3.2))
        opp1_exp = map_experience(data.get('opp1_exp', 3.2))
        opp2_exp = map_experience(data.get('opp2_exp', 3.2))
        
        match_score = data.get('match_score', '')
        
        # Import and use PTI calculation service v6 (matches original exactly)
        from app.services.pti_calculator_service_v6 import calculate_pti_v6
        
        result = calculate_pti_v6(
            player_pti, partner_pti, opp1_pti, opp2_pti,
            player_exp, partner_exp, opp1_exp, opp2_exp,
            match_score
        )
        
        # v6 returns {"success": True/False, "result": {...}}
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error calculating PTI adjustment: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@mobile_bp.route("/debug/teams-check")
def debug_teams_check():
    """Debug route to check teams table structure and data"""
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        html = "<h2>Teams Debug</h2>"
        
        # Check if teams table exists
        try:
            result = execute_query_one("SELECT COUNT(*) as count FROM teams")
            total_teams = result["count"] if result else 0
            html += f"<p>✅ Teams table exists with {total_teams} total teams</p>"
        except Exception as e:
            html += f"<p>❌ Teams table issue: {e}</p>"
            return html
        
        # Check league 4687 specifically
        try:
            result = execute_query_one("SELECT COUNT(*) as count FROM teams WHERE league_id = 4687")
            league_teams = result["count"] if result else 0
            html += f"<p>League 4687 has {league_teams} teams</p>"
        except Exception as e:
            html += f"<p>❌ League 4687 query failed: {e}</p>"
        
        # Check sample teams with joins
        try:
            query = """
                SELECT t.id, t.team_name, c.name as club_name, s.name as series_name
                FROM teams t
                LEFT JOIN clubs c ON t.club_id = c.id
                LEFT JOIN series s ON t.series_id = s.id
                WHERE t.league_id = 4687 AND t.is_active = TRUE
                LIMIT 5
            """
            sample_teams = execute_query(query)
            html += f"<p>Sample teams (found {len(sample_teams) if sample_teams else 0}):</p><ul>"
            for team in sample_teams or []:
                html += f"<li>ID: {team['id']}, Name: {team['team_name']}, Club: {team['club_name']}, Series: {team['series_name']}</li>"
            html += "</ul>"
        except Exception as e:
            html += f"<p>❌ Sample teams query failed: {e}</p>"
        
        return html
        
    except Exception as e:
        return f"Error: {str(e)}"


@mobile_bp.route("/mobile/text-group/<int:group_id>")
@login_required
def serve_text_group(group_id):
    """Serve the mobile text group page for sending SMS to group members"""
    try:
        user = session["user"]
        user_id = user.get("id")
        
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        # Get group details and verify user has access
        from app.services.groups_service import GroupsService
        from app.models.database_models import SessionLocal
        
        with SessionLocal() as db_session:
            groups_service = GroupsService(db_session)
            result = groups_service.get_group_details(group_id, user_id)
            
            if not result["success"]:
                return render_template(
                    "mobile/text_group.html",
                    session_data={"user": user, "authenticated": True},
                    error=result.get("error", "Group not found"),
                    group=None
                )
            
            group = result["group"]
            
        session_data = {"user": user, "authenticated": True}
        
        log_user_activity(
            user["email"], "page_visit", 
            page="text_group",
            details=f"Group: {group['name']}"
        )
        
        return render_template(
            "mobile/text_group.html",
            session_data=session_data,
            group=group,
            error=None
        )
        
    except Exception as e:
        print(f"Error serving text group page: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        session_data = {"user": session.get("user"), "authenticated": True}
        
        return render_template(
            "mobile/text_group.html",
            session_data=session_data,
            error="Failed to load group details",
            group=None
        )


@mobile_bp.route("/mobile/lineup_escrow_confirmation")
@login_required
def serve_mobile_lineup_escrow_confirmation():
    """Serve the mobile lineup escrow confirmation page"""
    # Ensure session data is available for template
    session_data = {"user": session["user"], "authenticated": True}
    return render_template("mobile/lineup_escrow_confirmation.html", session_data=session_data)


@mobile_bp.route('/mobile/grid-layout')
@login_required
def mobile_grid_layout():
    """Serve the old grid layout as an alternative option"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(
        session["user"]["email"], 
        "page_visit", 
        page="mobile_grid_layout",
        first_name=session["user"].get("first_name"),
        last_name=session["user"].get("last_name")
    )
    return render_template("mobile/index.html", session_data=session_data)


@mobile_bp.route("/mobile/all-teams-schedule")
@login_required
def serve_mobile_all_teams_schedule():
    """Serve the all teams schedule page with loading screen"""
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Please log in first"}), 401

        club_name = user.get("club")
        series = user.get("series")

        if not club_name or not series:
            return render_template(
                "mobile/all_teams_schedule.html",
                session_data={"user": user},
                error="Please set your club and series in your profile settings",
            )

        # Create a clean team name string for the title with proper series format
        # Convert Chicago/Division format to Series format for consistency
        if series and series.startswith("Chicago "):
            formatted_series = series.replace("Chicago ", "Series ")
        elif series and series.startswith("Division "):
            formatted_series = series.replace("Division ", "Series ")
        else:
            formatted_series = series
            
        team_name = f"{club_name} - {formatted_series}"

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_all_teams_schedule"
        )

        return render_template(
            "mobile/all_teams_schedule.html", team=team_name, session_data={"user": user}
        )

    except Exception as e:
        print(f"❌ Error in serve_mobile_all_teams_schedule: {str(e)}")
        import traceback

        print(traceback.format_exc())

        session_data = {"user": session.get("user"), "authenticated": True}

        return render_template(
            "mobile/all_teams_schedule.html",
            session_data=session_data,
            error="An error occurred while loading the all teams schedule",
        )


@mobile_bp.route("/install")
def install():
    """Serve the install page with iOS/Android instructions"""
    # Ensure session data is available for template
    session_data = {"user": session.get("user"), "authenticated": True}
    return render_template("install.html", session_data=session_data)






