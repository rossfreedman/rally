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
from database_utils import execute_query, execute_query_one
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
            # Check if current session has valid team context - if so, preserve it
            current_session = session.get("user", {})
            has_valid_team_context = (
                current_session.get("team_id") is not None and
                current_session.get("league_id") is not None and
                current_session.get("club") and
                current_session.get("series")
            )
            
            if has_valid_team_context:
                # Current session already has valid team context (likely from team switch)
                # Don't override it with database refresh
                print(f"[DEBUG] Preserving existing team context: {current_session.get('club')} - {current_session.get('series')}")
                session_data = {"user": current_session, "authenticated": True}
            else:
                # Session is incomplete or invalid, refresh from database
                print(f"[DEBUG] Getting fresh session data for user: {user_email}")
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
            # Check if current session has valid team context - if so, preserve it
            current_session = session.get("user", {})
            has_valid_team_context = (
                current_session.get("team_id") is not None and
                current_session.get("league_id") is not None and
                current_session.get("club") and
                current_session.get("series")
            )
            
            if has_valid_team_context:
                # Current session already has valid team context (likely from team switch)
                # Don't override it with database refresh
                print(f"[DEBUG] Preserving existing team context: {current_session.get('club')} - {current_session.get('series')}")
                session_data = {"user": current_session, "authenticated": True}
            else:
                # Session is incomplete or invalid, refresh from database
                print(f"[DEBUG] Getting fresh session data for user: {user_email}")
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
            # Check if current session has valid team context - if so, preserve it
            current_session = session.get("user", {})
            has_valid_team_context = (
                current_session.get("team_id") is not None and
                current_session.get("league_id") is not None and
                current_session.get("club") and
                current_session.get("series")
            )
            
            if has_valid_team_context:
                # Current session already has valid team context (likely from team switch)
                # Don't override it with database refresh
                print(f"[DEBUG] Preserving existing team context: {current_session.get('club')} - {current_session.get('series')}")
                session_data = {"user": current_session, "authenticated": True}
            else:
                # Session is incomplete or invalid, refresh from database
                print(f"[DEBUG] Getting fresh session data for user: {user_email}")
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
    # Player names look like: John Smith
    
    actual_player_id = player_identifier
    team_id = None
    
    # Check if this is a composite ID (player_id_team_teamID)
    if '_team_' in player_identifier:
        parts = player_identifier.split('_team_')
        if len(parts) == 2:
            actual_player_id = parts[0]
            try:
                team_id = int(parts[1])
            except ValueError:
                team_id = None
    
    is_player_id = bool(re.match(r'^[a-zA-Z0-9\-]+$', actual_player_id) and '-' in actual_player_id)
    
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
            player_name = player_record["full_name"]
            # Use the team_id from the database record if not explicitly provided
            if not team_id:
                team_id = player_record.get("team_id")
        else:
            # Player ID not found, return error
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
                print(f"[DEBUG] Name lookup found player_id {actual_player_id} with team_id {team_id}")
            else:
                print(f"[DEBUG] No player record found for name: {player_name}")

    # Create player user dict with team context for mobile service
    if actual_player_id:
        # Create a user dict with the specific player ID and team context
        player_user_dict = {
            "first_name": player_name.split()[0] if player_name else "",
            "last_name": " ".join(player_name.split()[1:]) if len(player_name.split()) > 1 else "",
            "tenniscores_player_id": actual_player_id,
            "league_id": viewing_user.get("league_id"),
            "email": viewing_user.get("email", "")
        }
        
        # Add team context for filtering
        if team_id:
            player_user_dict["team_context"] = team_id
            print(f"[DEBUG] Player detail - Using player ID {actual_player_id} with team context {team_id}")
        else:
            print(f"[DEBUG] Player detail - Using player ID {actual_player_id} without specific team context")
        
        # Import the direct player analysis function
        from app.services.mobile_service import get_player_analysis
        analyze_data = get_player_analysis(player_user_dict)
    else:
        # Final fallback to name-based analysis
        from app.services.mobile_service import get_player_analysis_by_name
        analyze_data = get_player_analysis_by_name(player_name, viewing_user)

    # Get additional player info (team name and series) for the header using team context
    player_info = {"club": None, "series": None, "team_name": None}
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
                "team_name": player_record["team_name"]
            }

    # PTI data is now handled within the service function with proper league filtering

    session_data = {"user": session["user"], "authenticated": True}
    team_or_club = player_info.get("team_name") or player_info.get("club") or "Unknown"
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
            # Check if current session has valid team context - if so, preserve it
            current_session = session.get("user", {})
            has_valid_team_context = (
                current_session.get("team_id") is not None and
                current_session.get("league_id") is not None and
                current_session.get("club") and
                current_session.get("series")
            )
            
            if has_valid_team_context:
                # Current session already has valid team context (likely from team switch)
                # Don't override it with database refresh
                session_user = current_session
            else:
                # Session is incomplete or invalid, refresh from database
                fresh_session_data = get_session_data_for_user(user_email)
                
                if fresh_session_data:
                    # Update Flask session with fresh data
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_user = fresh_session_data
                else:
                    # Fallback to existing session
                    session_user = session["user"]

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
        else:
            # Fallback: Look up player data from database using name matching
            player_query = """
                SELECT 
                    first_name,
                    last_name,
                    email,
                    tenniscores_player_id,
                    club_id,
                    series_id,
                    league_id,
                    team_id
                FROM players 
                WHERE first_name = %s AND last_name = %s
                ORDER BY id DESC
                LIMIT 1
            """

            player_data = execute_query_one(
                player_query,
                [session_user.get("first_name"), session_user.get("last_name")],
            )

            if player_data:
                # Create a complete user object with both session and database data
                complete_user = {
                    "email": session_user.get("email"),
                    "first_name": player_data["first_name"],
                    "last_name": player_data["last_name"],
                    "tenniscores_player_id": player_data["tenniscores_player_id"],
                    "club_id": player_data["club_id"],
                    "series_id": player_data["series_id"],
                    "league_id": player_data["league_id"],
                }
                
                # Add team context from database lookup if available
                if player_data.get("team_id"):
                    complete_user["team_context"] = player_data["team_id"]
                    print(f"[DEBUG] Analyze-me fallback - Using team context from DB: team_id={player_data['team_id']}")
                
                analyze_data = get_player_analysis(complete_user)
            else:
                analyze_data = {
                    "error": "Player data not found in database",
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
                        ORDER BY 
                            CASE 
                                WHEN series ~ '\d+' THEN 
                                    CAST(regexp_replace(series, '[^0-9]', '', 'g') AS INTEGER)
                                ELSE 0 
                            END DESC
                        LIMIT 1
                    ) as highest_series
                FROM season_boundaries sb
                CROSS JOIN career_start cs
            )
            SELECT 
                highest_series as series,
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
            WHERE p.tenniscores_player_id = %s
            ORDER BY history_count DESC, p.id DESC
            LIMIT 1
        """
        player_data = execute_query_one(player_query, [player_id])

        if not player_data:
            print(f"[DEBUG] Season History by ID - Player '{player_id}' not found in database")
            return jsonify({"error": "Player not found"}), 404

        player_db_id = player_data["id"]

        # Debug logging
        print(f"[DEBUG] Season History by ID - Found player: {player_data['first_name']} {player_data['last_name']}")
        print(f"[DEBUG] Season History by ID - Player DB ID: {player_db_id}")
        print(f"[DEBUG] Season History by ID - History count: {player_data['history_count']}")

        # Get season history using the same query as the name-based endpoint
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
                        ORDER BY 
                            CASE 
                                WHEN series ~ '\\d+' THEN 
                                    CAST(regexp_replace(series, '[^0-9]', '', 'g') AS INTEGER)
                                ELSE 0 
                            END DESC
                        LIMIT 1
                    ) as highest_series
                FROM season_boundaries sb
                CROSS JOIN career_start cs
            )
            SELECT 
                highest_series as series,
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
            WHERE CONCAT(p.first_name, ' ', p.last_name) = %s
            ORDER BY history_count DESC, p.id DESC
            LIMIT 1
        """
        player_data = execute_query_one(player_query, [player_name])

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
                        ORDER BY 
                            CASE 
                                WHEN series ~ '\d+' THEN 
                                    CAST(regexp_replace(series, '[^0-9]', '', 'g') AS INTEGER)
                                ELSE 0 
                            END DESC
                        LIMIT 1
                    ) as highest_series
                FROM season_boundaries sb
                CROSS JOIN career_start cs
            )
            SELECT 
                highest_series as series,
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

        result = get_mobile_team_data(session_user)

        session_data = {"user": session_user, "authenticated": True}

        log_user_activity(session_user["email"], "page_visit", page="mobile_my_team")

        # Extract all data from result
        team_data = result.get("team_data")
        court_analysis = result.get("court_analysis", {})
        top_players = result.get("top_players", [])
        strength_of_schedule = result.get("strength_of_schedule", {})
        error = result.get("error")

        response = render_template(
            "mobile/my_team.html",
            session_data=session_data,
            team_data=team_data,
            court_analysis=court_analysis,
            top_players=top_players,
            strength_of_schedule=strength_of_schedule,
            error=error,
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
            # Check if current session has valid team context - if so, preserve it
            current_session = session.get("user", {})
            has_valid_team_context = (
                current_session.get("team_id") is not None and
                current_session.get("league_id") is not None and
                current_session.get("club") and
                current_session.get("series")
            )
            
            if has_valid_team_context:
                # Current session already has valid team context (likely from team switch)
                # Don't override it with database refresh
                session_user = current_session
                print(f"[DEBUG] Settings: Preserving existing team context: {current_session.get('club')} - {current_session.get('series')}")
            else:
                # Session is incomplete or invalid, refresh from database
                print(f"[DEBUG] Settings: Getting fresh session data for user: {user_email}")
                fresh_session_data = get_session_data_for_user(user_email)
                
                if fresh_session_data:
                    # Update Flask session with fresh data
                    session["user"] = fresh_session_data
                    session.modified = True
                    session_user = fresh_session_data
                    print(f"[DEBUG] Settings: Using fresh session data and updated Flask session")
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
            "mobile/my_series.html", session_data=session_data, **series_data
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
            details=f"Visited Competitive Teams Page: {team_name}"
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

        print(f"📱 Calling log_user_activity for my-club...")
        log_result = log_user_activity(session_user["email"], "page_visit", page="mobile_my_club")
        print(f"✅ Activity logged: {log_result}")

        print(f"🎨 Rendering template...")
        return render_template(
            "mobile/my_club.html", session_data=session_data, **club_data
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
            "status": "requested"
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
                data["focus_areas"], data.get("notes", ""), "requested"
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
    try:
        # Get the selected date from query parameter
        selected_date = request.args.get("date")

        # Call the service function with the selected date
        availability_data = get_all_team_availability_data(
            session["user"], selected_date
        )

        session_data = {"user": session["user"], "authenticated": True}

        log_user_activity(
            session["user"]["email"], "page_visit", page="mobile_all_team_availability"
        )

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
                    p.pti
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
                    p.pti
                FROM players p
                WHERE p.team_id = %s AND p.is_active = true
                ORDER BY p.first_name, p.last_name
            """
            players_data = execute_query(players_query, [team_id])

        # Format players data
        players = [
            {
                "id": player["id"],
                "name": f"{player['first_name']} {player['last_name']}",
                "pti": player.get("pti", 0),
            }
            for player in players_data
        ]

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
    """Get all active players for a team with their court assignment statistics"""

    try:
        if not team_id:
            return []

        # Get team members
        team_members_query = """
            SELECT p.id, p.first_name, p.last_name, p.pti, p.tenniscores_player_id
            FROM players p
            WHERE p.team_id = %s AND p.is_active = TRUE
            ORDER BY p.first_name, p.last_name
        """

        members = execute_query(team_members_query, [team_id])
        if not members:
            return []

        # Get user's league_id for filtering (extract once at top)
        user_league_id = user.get("league_id")

        # Get team name for match filtering
        team_name_query = """
            SELECT team_name, team_alias FROM teams WHERE id = %s
        """
        team_info = execute_query_one(team_name_query, [team_id])
        team_name = (
            team_info.get("team_alias") or team_info.get("team_name")
            if team_info
            else None
        )

        if not team_name:
            return []

        # Try both team_id and team_name approaches
        team_matches = []

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

        # First try using team_id (more reliable) with league filter
        if team_id:
            if league_id_int:
                matches_by_id_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        match_date,
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
                    AND league_id = %s
                    ORDER BY match_date, id
                """
                team_matches = execute_query(
                    matches_by_id_query, [team_id, team_id, league_id_int]
                )
            else:
                matches_by_id_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        match_date,
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
                    ORDER BY match_date, id
                """
                team_matches = execute_query(matches_by_id_query, [team_id, team_id])

        # If no matches by team_id, try team_name with league filter
        if not team_matches and team_name:
            if league_id_int:
                matches_by_name_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        match_date,
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
                    WHERE (home_team = %s OR away_team = %s)
                    AND league_id = %s
                    ORDER BY match_date, id
                """
                team_matches = execute_query(
                    matches_by_name_query, [team_name, team_name, league_id_int]
                )
            else:
                matches_by_name_query = """
                    SELECT 
                        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
                        match_date,
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
                    WHERE (home_team = %s OR away_team = %s)
                    ORDER BY match_date, id
                """
                team_matches = execute_query(
                    matches_by_name_query, [team_name, team_name]
                )

        # Use the same court assignment logic as my-team page with league filtering
        court_assignments = calculate_player_court_stats(
            team_matches, team_name, members, user_league_id, team_id
        )

        # If no court assignments found, create sample data for testing court display
        if not any(court_assignments.values()):
            court_assignments = create_sample_court_data(members)

        # Build final member list with court stats and calculated match counts
        members_with_stats = []
        for member in members:
            full_name = f"{member['first_name']} {member['last_name']}"
            player_court_stats = court_assignments.get(
                member["tenniscores_player_id"], {}
            )

            # Get actual match count for this player filtered by team and league
            # For multi-team players, this ensures we count matches for THIS specific team
            player_match_count = get_player_match_count(
                member["tenniscores_player_id"], user_league_id, team_id
            )

            member_data = {
                "id": member["id"],
                "name": full_name,
                "first_name": member["first_name"],
                "last_name": member["last_name"],
                "pti": member.get("pti", 0),
                "tenniscores_player_id": member["tenniscores_player_id"],
                "court_stats": player_court_stats,
                "match_count": player_match_count,
            }
            members_with_stats.append(member_data)

            court_total = sum(player_court_stats.values()) if player_court_stats else 0

        # Sort team members by match count (most to least)
        members_with_stats.sort(key=lambda member: member["match_count"], reverse=True)

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
            session_data = get_session_data_for_user(user_email)
        
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
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
        from database_utils import execute_query, execute_query_one
        
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
    return render_template("mobile/lineup_escrow_confirmation.html")


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






