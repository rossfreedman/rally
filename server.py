#!/usr/bin/env python3

"""
Rally Flask Application

This is the main server file for the Rally platform tennis management application.
Most routes have been moved to blueprints for better organization.
"""

import json
import logging
import os
import secrets
import sys
from datetime import datetime, timedelta

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
)
from flask_cors import CORS
from flask_socketio import SocketIO

from app.routes.admin_routes import admin_bp
from app.routes.api_routes import api_bp
from app.routes.auth_routes import auth_bp
from app.routes.mobile_routes import mobile_bp
from app.routes.background_jobs import background_bp
from app.routes.schema_fix_routes import schema_fix_bp

# Import blueprints
from app.routes.player_routes import player_bp
from app.routes.polls_routes import polls_bp

# Import database utilities
from database_config import test_db_connection
from database_utils import execute_query, execute_query_one, execute_update

# Import act routes initialization
from routes.act import init_act_routes
from utils.auth import login_required
from utils.logging import log_user_activity

# Import route validation utilities
from utils.route_validation import validate_routes_on_startup

# Import temporary password middleware
from app.middleware.temporary_password_middleware import TemporaryPasswordMiddleware

# Run database migrations before starting the application (non-blocking)
print("=== Running Database Migrations ===")
try:
    from scripts.run_migrations import run_all_migrations

    migration_success = run_all_migrations()
    if not migration_success:
        print("❌ Database migrations failed - application may not function correctly")
except Exception as e:
    print(f"Migration error: {e}")
    print("⚠️ Continuing with application startup...")

# Simple database connection test (non-blocking)
print("=== Testing Database Connection ===")
try:
    success, error = test_db_connection()
    if success:
        print("✅ Database connection successful!")
    else:
        print(f"⚠️ Database connection warning: {error}")
        print("⚠️ Application will start anyway - database connectivity will be retried as needed")
except Exception as e:
    print(f"⚠️ Database test error: {e}")
    print("⚠️ Application will start anyway - database connectivity will be retried as needed")

# Initialize Flask app
app = Flask(__name__, static_folder="static", static_url_path="/static")

# Determine environment
is_development = os.environ.get("FLASK_ENV") == "development"

# Register blueprints
app.register_blueprint(player_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(mobile_bp)
app.register_blueprint(api_bp)
app.register_blueprint(polls_bp)
app.register_blueprint(background_bp)
app.register_blueprint(schema_fix_bp)

# Initialize act routes (includes find-subs, availability, schedule, rally_ai, etc.)
init_act_routes(app)
print(
    "✅ Act routes initialized - Find Sub, Availability, Schedule, Rally AI routes enabled"
)

# Add template context processor for database mode
@app.context_processor
def inject_database_mode():
    """Make database mode available in all templates"""
    from database_config import get_database_mode, is_local_development
    return {
        'get_database_mode': get_database_mode,
        'is_local_development': is_local_development
    }

# Validate routes to detect conflicts
print("=== Validating Routes for Conflicts ===")
has_no_conflicts = validate_routes_on_startup(app)
if not has_no_conflicts:
    print("⚠️  Route conflicts detected! Check logs above for details.")
    print("⚠️  Application will continue but may have unexpected behavior.")
else:
    print("✅ Route validation passed - no conflicts detected")

# Set secret key
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

# Session config
app.config.update(
    SESSION_COOKIE_SECURE=not is_development,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    SESSION_COOKIE_NAME="rally_session",
    SESSION_COOKIE_PATH="/",
    SESSION_REFRESH_EACH_REQUEST=True,
)

# Configure CORS
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": (
                ["*"]
                if is_development
                else [
                    "https://*.up.railway.app",
                    "https://*.railway.app",
                    "https://lovetorally.com",
                    "https://www.lovetorally.com",
                ]
            ),
            "supports_credentials": True,
            "allow_headers": ["Content-Type", "X-Requested-With", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        }
    },
    expose_headers=["Set-Cookie"],
)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Initialize temporary password middleware
TemporaryPasswordMiddleware(app)
print("✅ Temporary password middleware initialized - users with temporary passwords will be redirected to change password page")

# Initialize session refresh middleware
from app.middleware.session_refresh_middleware import SessionRefreshMiddleware
SessionRefreshMiddleware(app)
print("✅ Session refresh middleware initialized - users will get automatic session refresh after ETL imports")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# ==========================================
# TEMPLATE FILTERS
# ==========================================


@app.template_filter("parse_date")
def parse_date(value):
    """
    Jinja2 filter to parse a date string or datetime.date into a datetime object.
    Handles multiple date formats.
    """
    from datetime import date

    if not value:
        return None

    # If already a datetime.date, convert to datetime with default time
    if isinstance(value, date):
        return datetime.combine(value, datetime.strptime("6:30 PM", "%I:%M %p").time())

    # If already a datetime, return as is
    if isinstance(value, datetime):
        return value

    # Try different date formats for strings
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%b-%y"]

    for fmt in formats:
        try:
            dt = datetime.strptime(str(value), fmt)
            # Add default time of 6:30 PM if not specified
            if dt.hour == 0 and dt.minute == 0:
                dt = dt.replace(hour=18, minute=30)
            return dt
        except ValueError:
            continue

    return None


@app.template_filter("pretty_date")
def pretty_date(value):
    """Format dates with day of week"""
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%y"]
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value

        # Format with day of week followed by date
        day_of_week = date_obj.strftime("%A")
        date_str = date_obj.strftime("%-m/%-d/%y")
        return f"{day_of_week} {date_str}"
    except Exception as e:
        print(f"Error formatting date: {e}")
        return value


@app.template_filter("strip_leading_zero")
def strip_leading_zero(value):
    """
    Removes leading zero from hour in a time string like '06:30 pm' -> '6:30 pm'
    """
    import re

    return re.sub(r"^0", "", value) if isinstance(value, str) else value


@app.template_filter("pretty_date_no_year")
def pretty_date_no_year(value):
    """Format dates for display without the year"""
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%y"]
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value

        # Format without year
        day_of_week = date_obj.strftime("%A")
        date_str = date_obj.strftime("%-m/%-d")
        return f"{day_of_week} {date_str}"

    except Exception as e:
        print(f"[PRETTY_DATE_NO_YEAR] Error formatting date: {e}")
        return str(value)


@app.template_filter("date_to_mmdd")
def date_to_mmdd(value):
    """Format dates as simple mm/dd"""
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%y"]
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value

        # Format as mm/dd
        return date_obj.strftime("%-m/%-d")

    except Exception as e:
        print(f"[DATE_TO_MMDD] Error formatting date: {e}")
        return str(value)


@app.template_filter("pretty_date_with_year")
def pretty_date_with_year(value):
    """Format dates as 'Tuesday 9/24/24'"""
    try:
        if isinstance(value, str):
            # Try different date formats
            formats = ["%Y-%m-%d", "%m/%d/%Y", "%d-%b-%y"]
            date_obj = None
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            if not date_obj:
                return value
        else:
            date_obj = value

        # Format as "Tuesday 9/24/24"
        day_of_week = date_obj.strftime("%A")
        date_str = date_obj.strftime("%-m/%-d/%y")
        return f"{day_of_week} {date_str}"

    except Exception as e:
        print(f"[PRETTY_DATE_WITH_YEAR] Error formatting date: {e}")
        return str(value)


@app.before_request
def log_request_info():
    """Log information about page requests (not static files)"""
    # Only log meaningful page requests, not static files
    if (not request.path.startswith('/static/') and 
        not request.path.startswith('/images/') and
        not request.path.endswith('.css') and
        not request.path.endswith('.js') and
        not request.path.endswith('.png') and
        not request.path.endswith('.ico') and
        request.path not in ['/health', '/api/admin/impersonation-status']):
        
        print(f"\n🔍 PAGE REQUEST: {request.method} {request.path}")
        if "user" in session:
            print(f"   User: {session['user']['email']}")
        print("=" * 50)


# ==========================================
# CORE ROUTES (Essential routes that stay in server.py)
# ==========================================


@app.route("/")
def serve_index():
    """Serve the index page"""
    if "user" not in session:
        return redirect("/login")
    return redirect("/mobile")





@app.route("/welcome")
@login_required
def serve_interstitial():
    """Serve the interstitial welcome page shown after login/registration"""
    # TEMPORARILY DISABLED - redirect directly to mobile
    return redirect("/mobile")
    
    # Original code (commented out):
    # session_data = {"user": session["user"], "authenticated": True}
    # log_user_activity(
    #     session["user"]["email"], 
    #     "page_visit", 
    #     page="interstitial_welcome",
    #     first_name=session["user"].get("first_name"),
    #     last_name=session["user"].get("last_name")
    # )
    # return render_template("interstitial.html", session_data=session_data)


@app.route("/contact-sub")
@login_required
def serve_contact_sub():
    """Serve the modern contact sub page"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(
        session["user"]["email"], 
        "page_visit", 
        page="contact_sub",
        first_name=session["user"].get("first_name"),
        last_name=session["user"].get("last_name")
    )
    return render_template("mobile/contact_sub.html", session_data=session_data)


@app.route("/pti_vs_opponents_analysis.html")
@login_required
def serve_pti_analysis():
    """Serve the PTI vs Opponents Analysis page"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(
        session["user"]["email"], 
        "page_visit", 
        page="pti_vs_opponents_analysis",
        first_name=session["user"].get("first_name"),
        last_name=session["user"].get("last_name")
    )
    return render_template(
        "analysis/pti_vs_opponents_analysis.html", session_data=session_data
    )


@app.route("/schedule")
@login_required
def serve_schedule_page():
    """Serve the schedule page"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(
        session["user"]["email"], 
        "page_visit", 
        page="schedule",
        first_name=session["user"].get("first_name"),
        last_name=session["user"].get("last_name")
    )
    return render_template("mobile/view_schedule.html", session_data=session_data)


@app.route("/create-team")
@login_required
def serve_create_team_page():
    """Serve the Create Team page using mobile layout"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(
        session["user"]["email"], 
        "page_visit", 
        page="create_team",
        first_name=session["user"].get("first_name"),
        last_name=session["user"].get("last_name")
    )
    
    return render_template("mobile/create_team.html", session_data=session_data)


@app.route("/<path:path>")
def serve_static(path):
    """Serve static files with authentication (except website directory)"""
    public_files = {
        "login.html",
        "signup.html",
        "forgot-password.html",
        "index.html",  # Allow public access to marketing site index
        "rally-logo.png",
        "rally-icon.png",
        "favicon.ico",
        "login.css",
        "signup.css",
        "preview.png",  # Allow public access for social media link previews
    }

    def is_public_file(file_path):
        filename = os.path.basename(file_path)
        return (
            filename in public_files
            or file_path.startswith("css/")
            or file_path.startswith("js/")
            or file_path.startswith("images/")
            or file_path.startswith("website/")  # Allow public access to marketing site
        )

    # Handle public files (including index.html) regardless of authentication
    if is_public_file(path):
        # Special handling for index.html - serve from website directory
        if path == "index.html":
            return send_from_directory("website", path)
        return send_from_directory(".", path)

    # Require authentication for all other files
    if "user" not in session:
        return redirect("/login")

    try:
        return send_from_directory(".", path)
    except FileNotFoundError:
        return "File not found", 404


@app.route("/static/components/<path:filename>")
def serve_component(filename):
    """Serve component files"""
    return send_from_directory("static/components", filename)


@app.route("/static/images/<path:filename>")
def serve_image(filename):
    """Serve image files without authentication"""
    return send_from_directory("static/images", filename)


@app.route("/static/<path:filename>")
def serve_static_files(filename):
    """Serve static files without authentication"""
    return send_from_directory("static", filename)


@app.route("/health")
def healthcheck():
    """Health check endpoint with database connectivity info"""
    health_status = {
        "status": "healthy",
        "message": "Rally server is running",
        "blueprints_registered": [
            "player_routes",
            "auth_routes", 
            "admin_routes",
            "mobile_routes",
            "api_routes",
            "rally_ai_routes",
        ],
    }
    
    # Test database connectivity (non-blocking)
    try:
        from database_config import test_db_connection
        db_success, db_error = test_db_connection()
        
        health_status["database"] = {
            "status": "connected" if db_success else "warning",
            "message": "Database connection successful" if db_success else f"Database warning: {db_error}",
            "railway_environment": os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
        }
    except Exception as e:
        health_status["database"] = {
            "status": "warning", 
            "message": f"Database test error: {str(e)}",
            "railway_environment": os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
        }
    
    return jsonify(health_status)


@app.route("/health/routes")
def routes_info():
    """Route information endpoint for debugging"""
    from utils.route_validation import RouteConflictDetector

    detector = RouteConflictDetector()
    analysis = detector.analyze_app_routes(app)

    return jsonify(
        {
            "total_routes": analysis["total_routes"],
            "conflicts": len(analysis["conflicts"]),
            "routes_by_blueprint": analysis["routes_by_blueprint"],
            "conflict_details": (
                analysis["conflicts"] if analysis["conflicts"] else None
            ),
        }
    )


@app.route("/debug/test-session-validation")
def test_session_validation():
    """
    Test session validation logic
    """
    try:
        from utils.auth import _session_needs_refresh, _refresh_session_from_db
        
        # Test with a mock session
        test_session = {
            "user": {
                "id": 904,
                "email": "bpierson@gmail.com", 
                "first_name": "Brett",
                "last_name": "Pierson",
                "is_admin": False,
                "ad_deuce_preference": "Ad",
                "dominant_hand": "Righty",
                "league_context": 4763,
                "club": "Tennaqua",
                "club_logo": "static/images/clubs/tennaqua_logo.png",
                "series": "Chicago 7",
                "club_id": 8888,
                "series_id": 13994,
                "team_id": 57325,
                "team_name": "Tennaqua - 7",
                "tenniscores_player_id": "nndz-WkNDd3liZitndz09",
                "league_id": 4763,
                "league_string_id": "APTA_CHICAGO",
                "league_name": "APTA Chicago",
                "settings": "{}"
            }
        }
        
        # Test session validation
        needs_refresh = _session_needs_refresh(test_session)
        
        return jsonify({
            "test": "session_validation",
            "session_data": test_session["user"],
            "needs_refresh": needs_refresh,
            "session_keys": list(test_session.keys()),
            "user_keys": list(test_session["user"].keys())
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/debug/test-wes-v2")
def test_wes_v2():
    """
    New debug endpoint to test Wes Maher's analyze-me issue on staging
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        test_email = "wmaher@gmail.com"
        
        # Test direct database query
        from database_utils import execute_query
        user_db = execute_query('SELECT id, email, league_context FROM users WHERE email = %s', [test_email])
        
        # Test session service
        from app.services.session_service import get_session_data_for_user
        session_data = get_session_data_for_user(test_email)
        
        # Convert session_data to user format for mobile service
        if session_data:
            session_user = {
                "email": session_data.get("email"),
                "first_name": session_data.get("first_name"),
                "last_name": session_data.get("last_name"),
                "tenniscores_player_id": session_data.get("tenniscores_player_id"),
                "club_id": session_data.get("club_id"),
                "series_id": session_data.get("series_id"),
                "league_id": session_data.get("league_id"),
                "team_id": session_data.get("team_id"),
                "club": session_data.get("club"),
                "series": session_data.get("series")
            }
            
            # Test mobile service
            from app.services.mobile_service import get_player_analysis
            mobile_data = get_player_analysis(session_user)
        else:
            session_user = None
            mobile_data = None
        
        return jsonify({
            "test": "wes_maher_v2",
            "railway_env": railway_env,
            "test_email": test_email,
            "database_direct": {
                "user_found": bool(user_db),
                "user_data": user_db[0] if user_db else None
            },
            "session_service": {
                "session_data_found": bool(session_data),
                "email": session_data.get("email") if session_data else None,
                "player_id": session_data.get("tenniscores_player_id") if session_data else None,
                "league_id": session_data.get("league_id") if session_data else None,
                "team_id": session_data.get("team_id") if session_data else None,
                "club": session_data.get("club") if session_data else None,
                "series": session_data.get("series") if session_data else None
            },
            "mobile_service": {
                "analyze_data_found": bool(mobile_data),
                "current_season_matches": mobile_data.get('current_season', {}).get('matches', 0) if mobile_data and mobile_data.get('current_season') else 0,
                "current_season_data": mobile_data.get('current_season') if mobile_data else None,
                "pti_score": mobile_data.get('current_pti') if mobile_data else None,
                "error": mobile_data.get('error') if mobile_data else None
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/test-ross-matches-detailed")
def test_ross_matches_detailed():
    """
    Detailed debug for Ross Freedman's match data - test both player IDs
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        # Ross's two player IDs from previous debug
        player_ids = ["nndz-WkMrK3didjlnUT09", "nndz-WlNhd3hMYi9nQT09"]
        
        results = {}
        
        for i, player_id in enumerate(player_ids):
            print(f"Testing player ID {i+1}: {player_id}")
            
            # Check matches for this player ID
            matches_query = """
                SELECT 
                    COUNT(*) as total_matches,
                    MIN(match_date) as earliest_match,
                    MAX(match_date) as latest_match
                FROM match_scores
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
            """
            match_stats = execute_query_one(matches_query, [player_id, player_id, player_id, player_id])
            
            # Get sample matches
            sample_query = """
                SELECT 
                    TO_CHAR(match_date, 'DD-Mon-YY') as date,
                    home_team,
                    away_team,
                    league_id,
                    home_team_id,
                    away_team_id
                FROM match_scores
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                ORDER BY match_date DESC
                LIMIT 3
            """
            sample_matches = execute_query(sample_query, [player_id, player_id, player_id, player_id])
            
            # Get player info
            player_info_query = """
                SELECT first_name, last_name, league_id, team_id, club_id, series_id
                FROM players
                WHERE tenniscores_player_id = %s
            """
            player_info = execute_query(player_info_query, [player_id])
            
            results[f"player_{i+1}"] = {
                "player_id": player_id,
                "player_records": len(player_info),
                "player_details": [{"league": p["league_id"], "team": p["team_id"], "club": p["club_id"], "series": p["series_id"]} for p in player_info],
                "total_matches": match_stats["total_matches"] if match_stats else 0,
                "date_range": f"{match_stats['earliest_match']} to {match_stats['latest_match']}" if match_stats and match_stats["total_matches"] > 0 else "No matches",
                "sample_matches": [{"date": m["date"], "teams": f"{m['home_team']} vs {m['away_team']}", "league": m["league_id"]} for m in sample_matches]
            }
        
        # Also check if there are any matches with similar player names
        name_matches_query = """
            SELECT DISTINCT
                home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                TO_CHAR(match_date, 'DD-Mon-YY') as date,
                home_team, away_team, match_date
            FROM match_scores
            WHERE home_team ILIKE %s OR away_team ILIKE %s
            ORDER BY match_date DESC
            LIMIT 5
        """
        tennaqua_matches = execute_query(name_matches_query, ['%tennaqua%', '%tennaqua%'])
        
        return jsonify({
            "debug": "ross_matches_detailed",
            "railway_env": railway_env,
            "player_analysis": results,
            "tennaqua_sample_matches": [
                {
                    "date": m["date"],
                    "teams": f"{m['home_team']} vs {m['away_team']}",
                    "player_ids": {
                        "home": [m["home_player_1_id"][:15] + "..." if m["home_player_1_id"] else None, 
                                m["home_player_2_id"][:15] + "..." if m["home_player_2_id"] else None],
                        "away": [m["away_player_1_id"][:15] + "..." if m["away_player_1_id"] else None,
                                m["away_player_2_id"][:15] + "..." if m["away_player_2_id"] else None]
                    }
                } for m in tennaqua_matches
            ],
            "summary": {
                "total_ross_matches_found": sum([results[f"player_{i+1}"]["total_matches"] for i in range(2)]),
                "tennaqua_matches_exist": len(tennaqua_matches) > 0
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/direct-search-ross")
def direct_search_ross():
    """
    Direct database search for Ross's player ID: nndz-WkMrK3didjlnUT09
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        player_id = "nndz-WkMrK3didjlnUT09"
        
        # Direct search - check each player position individually
        results = {}
        
        # Search home_player_1_id
        home1_query = """
            SELECT COUNT(*) as count, MIN(match_date) as earliest, MAX(match_date) as latest
            FROM match_scores
            WHERE home_player_1_id = %s
        """
        home1_result = execute_query_one(home1_query, [player_id])
        results["home_player_1"] = {
            "count": home1_result["count"] if home1_result else 0,
            "date_range": f"{home1_result['earliest']} to {home1_result['latest']}" if home1_result and home1_result["count"] > 0 else "No matches"
        }
        
        # Search home_player_2_id  
        home2_query = """
            SELECT COUNT(*) as count, MIN(match_date) as earliest, MAX(match_date) as latest
            FROM match_scores
            WHERE home_player_2_id = %s
        """
        home2_result = execute_query_one(home2_query, [player_id])
        results["home_player_2"] = {
            "count": home2_result["count"] if home2_result else 0,
            "date_range": f"{home2_result['earliest']} to {home2_result['latest']}" if home2_result and home2_result["count"] > 0 else "No matches"
        }
        
        # Search away_player_1_id
        away1_query = """
            SELECT COUNT(*) as count, MIN(match_date) as earliest, MAX(match_date) as latest
            FROM match_scores
            WHERE away_player_1_id = %s
        """
        away1_result = execute_query_one(away1_query, [player_id])
        results["away_player_1"] = {
            "count": away1_result["count"] if away1_result else 0,
            "date_range": f"{away1_result['earliest']} to {away1_result['latest']}" if away1_result and away1_result["count"] > 0 else "No matches"
        }
        
        # Search away_player_2_id
        away2_query = """
            SELECT COUNT(*) as count, MIN(match_date) as earliest, MAX(match_date) as latest
            FROM match_scores
            WHERE away_player_2_id = %s
        """
        away2_result = execute_query_one(away2_query, [player_id])
        results["away_player_2"] = {
            "count": away2_result["count"] if away2_result else 0,
            "date_range": f"{away2_result['earliest']} to {away2_result['latest']}" if away2_result and away2_result["count"] > 0 else "No matches"
        }
        
        # Get total count
        total_count = sum([results[pos]["count"] for pos in results.keys()])
        
        # Get sample matches if any exist
        sample_matches = []
        if total_count > 0:
            sample_query = """
                SELECT 
                    id,
                    TO_CHAR(match_date, 'DD-Mon-YY') as date,
                    home_team,
                    away_team,
                    league_id,
                    home_team_id,
                    away_team_id,
                    home_player_1_id,
                    home_player_2_id,
                    away_player_1_id,
                    away_player_2_id,
                    scores,
                    winner
                FROM match_scores
                WHERE home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s
                ORDER BY match_date DESC
                LIMIT 5
            """
            matches = execute_query(sample_query, [player_id, player_id, player_id, player_id])
            
            for match in matches:
                # Determine position
                position = "unknown"
                if match["home_player_1_id"] == player_id:
                    position = "home_player_1"
                elif match["home_player_2_id"] == player_id:
                    position = "home_player_2"
                elif match["away_player_1_id"] == player_id:
                    position = "away_player_1"
                elif match["away_player_2_id"] == player_id:
                    position = "away_player_2"
                
                sample_matches.append({
                    "id": match["id"],
                    "date": match["date"],
                    "teams": f"{match['home_team']} vs {match['away_team']}",
                    "league_id": match["league_id"],
                    "position": position,
                    "scores": match["scores"],
                    "winner": match["winner"]
                })
        
        # Also check what other player IDs are similar
        similar_query = """
            SELECT DISTINCT home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
            FROM match_scores
            WHERE home_player_1_id LIKE %s OR home_player_2_id LIKE %s OR away_player_1_id LIKE %s OR away_player_2_id LIKE %s
            LIMIT 10
        """
        similar_ids = execute_query(similar_query, [f"{player_id[:10]}%", f"{player_id[:10]}%", f"{player_id[:10]}%", f"{player_id[:10]}%"])
        
        unique_similar_ids = set()
        for row in similar_ids:
            for col in ["home_player_1_id", "home_player_2_id", "away_player_1_id", "away_player_2_id"]:
                if row[col] and row[col].startswith(player_id[:10]):
                    unique_similar_ids.add(row[col])
        
        return jsonify({
            "debug": "direct_search_ross",
            "player_id": player_id,
            "railway_env": railway_env,
            "position_breakdown": results,
            "total_matches": total_count,
            "sample_matches": sample_matches,
            "similar_player_ids": list(unique_similar_ids),
            "summary": f"Found {total_count} total matches for Ross's player ID {player_id}"
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/investigate-staging-ids")
def investigate_staging_ids():
    """
    Investigate the staging database ID mismatches for Ross Freedman
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        results = {}
        
        # Ross's details
        ross_player_id = "nndz-WkMrK3didjlnUT09"
        ross_email = "rossfreedman@gmail.com"
        
        # Staging IDs (wrong)
        staging_league_id = 4693
        staging_team_id = 42417
        
        # Local IDs (correct)  
        local_league_id = 4683
        local_team_id = 44279
        
        results["ross_info"] = {
            "player_id": ross_player_id,
            "email": ross_email,
            "staging_league_id": staging_league_id,
            "staging_team_id": staging_team_id,
            "local_league_id": local_league_id,
            "local_team_id": local_team_id
        }
        
        # 1. Check what staging league 4693 is
        staging_league = execute_query_one(
            "SELECT id, league_id, league_name FROM leagues WHERE id = %s",
            [staging_league_id]
        )
        results["staging_league_4693"] = staging_league
        
        # 2. Check what staging team 42417 is
        staging_team = execute_query_one(
            "SELECT id, team_name, league_id FROM teams WHERE id = %s",
            [staging_team_id]
        )
        results["staging_team_42417"] = staging_team
        
        # 3. Check if local league 4683 exists on staging
        local_league_on_staging = execute_query_one(
            "SELECT id, league_id, league_name FROM leagues WHERE id = %s",
            [local_league_id]
        )
        results["local_league_4683_on_staging"] = local_league_on_staging
        
        # 4. Check if local team 44279 exists on staging
        local_team_on_staging = execute_query_one(
            "SELECT id, team_name, league_id FROM teams WHERE id = %s",
            [local_team_id]
        )
        results["local_team_44279_on_staging"] = local_team_on_staging
        
        # 5. Search for Ross's matches by player ID (regardless of league/team)
        ross_matches = execute_query(
            """
            SELECT 
                league_id,
                home_team_id,
                away_team_id,
                home_team,
                away_team,
                COUNT(*) as match_count,
                MIN(TO_CHAR(match_date, 'YYYY-MM-DD')) as earliest_match,
                MAX(TO_CHAR(match_date, 'YYYY-MM-DD')) as latest_match
            FROM match_scores 
            WHERE home_player_1_id = %s OR home_player_2_id = %s 
               OR away_player_1_id = %s OR away_player_2_id = %s
            GROUP BY league_id, home_team_id, away_team_id, home_team, away_team
            ORDER BY match_count DESC
            """,
            [ross_player_id, ross_player_id, ross_player_id, ross_player_id]
        )
        results["ross_matches_found"] = ross_matches
        
        # 6. Check Ross's user association on staging
        ross_user = execute_query_one(
            "SELECT id, email, league_context FROM users WHERE email = %s",
            [ross_email]
        )
        results["ross_user"] = ross_user
        
        if ross_user:
            # Check his player associations
            associations = execute_query(
                """
                SELECT upa.tenniscores_player_id, p.league_id, p.team_id, 
                       t.team_name, l.league_name, p.first_name, p.last_name
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id  
                JOIN teams t ON p.team_id = t.id
                JOIN leagues l ON p.league_id = l.id
                WHERE upa.user_id = %s
                """,
                [ross_user['id']]
            )
            results["ross_associations"] = associations
        
        # Analysis
        analysis = {
            "staging_league_exists": staging_league is not None,
            "staging_team_exists": staging_team is not None, 
            "local_league_exists_on_staging": local_league_on_staging is not None,
            "local_team_exists_on_staging": local_team_on_staging is not None,
            "ross_matches_count": len(ross_matches) if ross_matches else 0,
            "ross_user_exists": ross_user is not None
        }
        
        if ross_matches:
            best_match = ross_matches[0]
            analysis["primary_match_league_id"] = best_match["league_id"]
            analysis["primary_match_count"] = best_match["match_count"]
            analysis["league_mismatch"] = best_match["league_id"] != staging_league_id
            
            if best_match["league_id"] != staging_league_id:
                analysis["recommended_fix"] = f"Update Ross's league_context from {staging_league_id} to {best_match['league_id']}"
        
        results["analysis"] = analysis
        
        return jsonify({
            "debug": "investigate_staging_ids",
            "railway_env": railway_env,
            "results": results
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/fix-ross-league-context")
def fix_ross_league_context():
    """
    Fix Ross's league context to point to the correct league where his matches exist
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        ross_email = "rossfreedman@gmail.com"
        ross_player_id = "nndz-WkMrK3didjlnUT09"
        
        # First find where Ross's matches actually exist
        ross_matches = execute_query(
            """
            SELECT 
                league_id,
                COUNT(*) as match_count
            FROM match_scores 
            WHERE home_player_1_id = %s OR home_player_2_id = %s 
               OR away_player_1_id = %s OR away_player_2_id = %s
            GROUP BY league_id
            ORDER BY match_count DESC
            """,
            [ross_player_id, ross_player_id, ross_player_id, ross_player_id]
        )
        
        if not ross_matches:
            return jsonify({
                "error": "No matches found for Ross - cannot determine correct league",
                "railway_env": railway_env
            }), 400
        
        # Use the league with the most matches
        correct_league_id = ross_matches[0]["league_id"]
        match_count = ross_matches[0]["match_count"]
        
        # Get current user data
        current_user = execute_query_one(
            "SELECT id, email, league_context FROM users WHERE email = %s",
            [ross_email]
        )
        
        if not current_user:
            return jsonify({
                "error": "Ross's user account not found",
                "railway_env": railway_env
            }), 404
        
        old_league_context = current_user["league_context"]
        
        # Update the league context
        rows_updated = execute_update(
            "UPDATE users SET league_context = %s WHERE email = %s",
            [correct_league_id, ross_email]
        )
        
        # Verify the update
        updated_user = execute_query_one(
            "SELECT id, email, league_context FROM users WHERE email = %s",
            [ross_email]
        )
        
        # Get league names for display
        old_league = execute_query_one(
            "SELECT league_name FROM leagues WHERE id = %s",
            [old_league_context]
        ) if old_league_context else None
        
        new_league = execute_query_one(
            "SELECT league_name FROM leagues WHERE id = %s", 
            [correct_league_id]
        )
        
        return jsonify({
            "debug": "fix_ross_league_context",
            "railway_env": railway_env,
            "fix_applied": True,
            "user_id": current_user["id"],
            "email": ross_email,
            "old_league_context": old_league_context,
            "old_league_name": old_league["league_name"] if old_league else "Unknown",
            "new_league_context": correct_league_id,
            "new_league_name": new_league["league_name"] if new_league else "Unknown", 
            "match_count_in_correct_league": match_count,
            "rows_updated": rows_updated,
            "verification": {
                "current_league_context": updated_user["league_context"],
                "update_successful": updated_user["league_context"] == correct_league_id
            },
            "next_steps": [
                "1. Log out and log back in to refresh session data",
                "2. Visit /mobile/analyze-me to see if data now appears",
                "3. Check that team switching still works properly"
            ]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/check-ross-second-player-id")
def check_ross_second_player_id():
    """
    Check if matches exist for Ross's second player ID on staging
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        # Ross's second player ID from the investigation
        second_player_id = "nndz-WlNhd3hMYi9nQT09"
        
        # Check matches for this player ID
        matches_query = """
            SELECT 
                COUNT(*) as total_matches,
                MIN(TO_CHAR(match_date, 'YYYY-MM-DD')) as earliest_match,
                MAX(TO_CHAR(match_date, 'YYYY-MM-DD')) as latest_match,
                league_id,
                home_team_id,
                away_team_id
            FROM match_scores
            WHERE home_player_1_id = %s OR home_player_2_id = %s 
               OR away_player_1_id = %s OR away_player_2_id = %s
            GROUP BY league_id, home_team_id, away_team_id
            ORDER BY COUNT(*) DESC
        """
        
        matches = execute_query(matches_query, [second_player_id, second_player_id, second_player_id, second_player_id])
        
        # Get sample matches
        sample_query = """
            SELECT 
                TO_CHAR(match_date, 'DD-Mon-YY') as date,
                home_team,
                away_team,
                winner,
                scores,
                league_id
            FROM match_scores
            WHERE home_player_1_id = %s OR home_player_2_id = %s 
               OR away_player_1_id = %s OR away_player_2_id = %s
            ORDER BY match_date DESC
            LIMIT 5
        """
        
        sample_matches = execute_query(sample_query, [second_player_id, second_player_id, second_player_id, second_player_id])
        
        # Check all player IDs that start with "nndz-W" to see the pattern
        pattern_query = """
            SELECT DISTINCT 
                CASE 
                    WHEN home_player_1_id LIKE 'nndz-W%' THEN home_player_1_id
                    WHEN home_player_2_id LIKE 'nndz-W%' THEN home_player_2_id  
                    WHEN away_player_1_id LIKE 'nndz-W%' THEN away_player_1_id
                    WHEN away_player_2_id LIKE 'nndz-W%' THEN away_player_2_id
                END as player_id,
                COUNT(*) as match_count
            FROM match_scores
            WHERE home_player_1_id LIKE 'nndz-W%' OR home_player_2_id LIKE 'nndz-W%' 
               OR away_player_1_id LIKE 'nndz-W%' OR away_player_2_id LIKE 'nndz-W%'
            GROUP BY 1
            ORDER BY match_count DESC
        """
        
        similar_players = execute_query(pattern_query, [])
        
        # Check total matches in database for context
        total_query = "SELECT COUNT(*) as total FROM match_scores"
        total_result = execute_query_one(total_query, [])
        
        return jsonify({
            "debug": "check_ross_second_player_id",
            "railway_env": railway_env,
            "second_player_id": second_player_id,
            "matches_found": matches,
            "total_match_groups": len(matches) if matches else 0,
            "total_matches": sum([m["total_matches"] for m in matches]) if matches else 0,
            "sample_matches": sample_matches,
            "similar_ross_players": similar_players,
            "database_total_matches": total_result["total"] if total_result else 0,
            "analysis": {
                "second_id_has_matches": len(matches) > 0 if matches else False,
                "database_has_data": total_result["total"] > 0 if total_result else False,
                "similar_players_count": len(similar_players) if similar_players else 0
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/search-any-ross-matches")
def search_any_ross_matches():
    """
    Broad search for any Ross-related matches in staging database
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        results = {}
        
        # 1. Search for any player IDs that contain "nndz-W" (Ross's pattern)
        pattern_search_query = """
            SELECT COUNT(*) as total_pattern_matches
            FROM match_scores
            WHERE home_player_1_id LIKE %s OR home_player_2_id LIKE %s 
            OR away_player_1_id LIKE %s OR away_player_2_id LIKE %s
        """
        pattern_count = execute_query_one(pattern_search_query, ['nndz-Wk%', 'nndz-Wk%', 'nndz-Wk%', 'nndz-Wk%'])
        
        results["pattern_matches"] = {
            "total_matches": pattern_count["total_pattern_matches"] if pattern_count else 0
        }
        
        # 2. Search players table for any Ross entries and get their exact player IDs
        ross_players_query = """
            SELECT DISTINCT tenniscores_player_id, first_name, last_name, league_id, team_id
            FROM players
            WHERE first_name ILIKE %s OR last_name ILIKE %s
            OR tenniscores_player_id LIKE %s
        """
        ross_players = execute_query(ross_players_query, ['%ross%', '%freed%', 'nndz-Wk%'])
        
        results["ross_players"] = [
            {
                "name": f"{p['first_name']} {p['last_name']}",
                "player_id": p["tenniscores_player_id"],
                "league": p["league_id"],
                "team": p["team_id"]
            } for p in ross_players
        ]
        
        # 3. For each Ross player ID found, check match counts
        results["match_counts_per_ross_id"] = {}
        for player in ross_players:
            pid = player["tenniscores_player_id"]
            count_query = """
                SELECT COUNT(*) as count
                FROM match_scores
                WHERE home_player_1_id = %s OR home_player_2_id = %s 
                OR away_player_1_id = %s OR away_player_2_id = %s
            """
            count_result = execute_query_one(count_query, [pid, pid, pid, pid])
            results["match_counts_per_ross_id"][pid] = count_result["count"] if count_result else 0
        
        # 4. Search for ANY matches with Tennaqua in team names
        tennaqua_query = """
            SELECT COUNT(*) as total_tennaqua_matches
            FROM match_scores
            WHERE home_team ILIKE %s OR away_team ILIKE %s
        """
        tennaqua_count = execute_query_one(tennaqua_query, ['%tennaqua%', '%tennaqua%'])
        results["tennaqua_total_matches"] = tennaqua_count["count"] if tennaqua_count else 0
        
        # 5. Sample of recent matches to see what player ID formats exist
        recent_matches_query = """
            SELECT 
                home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                TO_CHAR(match_date, 'YYYY-MM-DD') as date,
                home_team, away_team
            FROM match_scores
            ORDER BY match_date DESC
            LIMIT 5
        """
        recent_matches = execute_query(recent_matches_query, [])
        
        results["recent_matches_sample"] = [
            {
                "date": m["date"],
                "teams": f"{m['home_team']} vs {m['away_team']}",
                "player_ids": {
                    "home": [m["home_player_1_id"][:20] + "..." if m["home_player_1_id"] else None,
                             m["home_player_2_id"][:20] + "..." if m["home_player_2_id"] else None],
                    "away": [m["away_player_1_id"][:20] + "..." if m["away_player_1_id"] else None,
                             m["away_player_2_id"][:20] + "..." if m["away_player_2_id"] else None]
                }
            } for m in recent_matches
        ]
        
        # 6. Check total match_scores count
        total_query = "SELECT COUNT(*) as total FROM match_scores"
        total_result = execute_query_one(total_query, [])
        results["total_matches_in_db"] = total_result["count"] if total_result else 0
        
        return jsonify({
            "debug": "search_any_ross_matches",
            "railway_env": railway_env,
            "results": results,
            "summary": {
                "ross_player_ids_found": len(ross_players),
                "total_db_matches": results["total_matches_in_db"],
                "tennaqua_matches": results["tennaqua_total_matches"],
                "pattern_matches": results["pattern_matches"]["total_matches"]
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/fix-ross-associations-staging")
def fix_ross_associations_staging():
    """
    Find Ross's actual match data on staging and correctly associate his user account
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        ross_email = "rossfreedman@gmail.com"
        
        # Ross's known player IDs from the investigation
        player_ids = [
            "nndz-WkMrK3didjlnUT09",  # Primary from local
            "nndz-WlNhd3hMYi9nQT09"   # Secondary from staging associations
        ]
        
        results = {
            "ross_email": ross_email,
            "player_ids_checked": player_ids,
            "match_analysis": {},
            "current_associations": [],
            "fix_applied": False
        }
        
        # Step 1: Check matches for each player ID
        total_matches_found = 0
        best_player_id = None
        best_league_id = None
        best_match_count = 0
        
        for player_id in player_ids:
            matches_query = """
                SELECT 
                    league_id,
                    COUNT(*) as match_count,
                    MIN(TO_CHAR(match_date, 'YYYY-MM-DD')) as earliest_match,
                    MAX(TO_CHAR(match_date, 'YYYY-MM-DD')) as latest_match
                FROM match_scores
                WHERE home_player_1_id = %s OR home_player_2_id = %s 
                   OR away_player_1_id = %s OR away_player_2_id = %s
                GROUP BY league_id
                ORDER BY COUNT(*) DESC
            """
            
            matches = execute_query(matches_query, [player_id, player_id, player_id, player_id])
            
            player_total = sum([m["match_count"] for m in matches]) if matches else 0
            total_matches_found += player_total
            
            results["match_analysis"][player_id] = {
                "total_matches": player_total,
                "leagues": matches if matches else []
            }
            
            # Track the player ID with the most matches
            if player_total > best_match_count:
                best_match_count = player_total
                best_player_id = player_id
                if matches:
                    best_league_id = matches[0]["league_id"]  # League with most matches
        
        # Step 2: Get current user data and associations
        ross_user = execute_query_one(
            "SELECT id, email, league_context FROM users WHERE email = %s",
            [ross_email]
        )
        
        if not ross_user:
            return jsonify({
                "error": "Ross's user account not found",
                "results": results
            }), 404
        
        # Get current associations
        current_associations = execute_query(
            """
            SELECT upa.tenniscores_player_id, p.league_id, p.team_id, 
                   t.team_name, l.league_name, p.first_name, p.last_name
            FROM user_player_associations upa
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id  
            JOIN teams t ON p.team_id = t.id
            JOIN leagues l ON p.league_id = l.id
            WHERE upa.user_id = %s
            """,
            [ross_user['id']]
        )
        
        results["current_user"] = ross_user
        results["current_associations"] = current_associations
        results["total_matches_found"] = total_matches_found
        results["best_player_id"] = best_player_id
        results["best_league_id"] = best_league_id
        results["best_match_count"] = best_match_count
        
        # Step 3: Apply fix if we found matches
        if best_player_id and best_league_id and best_match_count > 0:
            # Update user's league_context to the league with the most matches
            old_league_context = ross_user["league_context"]
            
            if old_league_context != best_league_id:
                rows_updated = execute_update(
                    "UPDATE users SET league_context = %s WHERE email = %s",
                    [best_league_id, ross_email]
                )
                
                # Verify the update
                updated_user = execute_query_one(
                    "SELECT league_context FROM users WHERE email = %s",
                    [ross_email]
                )
                
                # Get league names for display
                old_league = execute_query_one(
                    "SELECT league_name FROM leagues WHERE id = %s",
                    [old_league_context]
                ) if old_league_context else None
                
                new_league = execute_query_one(
                    "SELECT league_name FROM leagues WHERE id = %s", 
                    [best_league_id]
                )
                
                results["fix_applied"] = True
                results["fix_details"] = {
                    "old_league_context": old_league_context,
                    "old_league_name": old_league["league_name"] if old_league else "Unknown",
                    "new_league_context": best_league_id,
                    "new_league_name": new_league["league_name"] if new_league else "Unknown",
                    "rows_updated": rows_updated,
                    "verification_successful": updated_user["league_context"] == best_league_id,
                    "match_count_in_new_league": best_match_count
                }
            else:
                results["fix_applied"] = False
                results["fix_details"] = {
                    "reason": "User already associated with correct league",
                    "current_league": best_league_id,
                    "match_count": best_match_count
                }
        else:
            results["fix_applied"] = False
            results["fix_details"] = {
                "reason": "No matches found for any of Ross's player IDs on staging",
                "recommendation": "Check if match data was imported for Ross, or if ETL import needs to be re-run"
            }
        
        return jsonify({
            "debug": "fix_ross_associations_staging",
            "railway_env": railway_env,
            "results": results,
            "next_steps": [
                "1. If fix was applied: Log out and log back in to refresh session",
                "2. Visit /mobile/analyze-me to verify data appears",
                "3. If no matches found: Check ETL import logs for Ross's data"
            ] if results["fix_applied"] else [
                "1. Investigate why no match data exists for Ross on staging",
                "2. Check ETL import process",
                "3. Verify player IDs are correct"
            ]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env,
            "results": results
        }), 500


@app.route("/debug/staging-database-health")
def staging_database_health():
    """
    Check overall health of staging database match data
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        results = {}
        
        # 1. Check total match count
        total_matches = execute_query_one("SELECT COUNT(*) as total FROM match_scores")
        results["total_matches"] = total_matches["total"] if total_matches else 0
        
        # 2. Check date range of matches
        date_range = execute_query_one(
            """
            SELECT 
                MIN(TO_CHAR(match_date, 'YYYY-MM-DD')) as earliest_match,
                MAX(TO_CHAR(match_date, 'YYYY-MM-DD')) as latest_match,
                COUNT(DISTINCT match_date) as unique_dates
            FROM match_scores
            """
        )
        results["date_range"] = date_range
        
        # 3. Check league distribution of matches
        league_distribution = execute_query(
            """
            SELECT 
                l.league_name,
                l.id as league_id,
                COUNT(ms.id) as match_count
            FROM leagues l
            LEFT JOIN match_scores ms ON l.id = ms.league_id
            GROUP BY l.id, l.league_name
            ORDER BY match_count DESC
            """
        )
        results["league_distribution"] = league_distribution
        
        # 4. Check for Tennaqua matches specifically
        tennaqua_matches = execute_query_one(
            """
            SELECT COUNT(*) as tennaqua_matches
            FROM match_scores
            WHERE home_team ILIKE '%tennaqua%' OR away_team ILIKE '%tennaqua%'
            """
        )
        results["tennaqua_matches"] = tennaqua_matches["tennaqua_matches"] if tennaqua_matches else 0
        
        # 5. Sample of recent matches
        recent_matches = execute_query(
            """
            SELECT 
                TO_CHAR(match_date, 'YYYY-MM-DD') as date,
                home_team,
                away_team,
                league_id,
                CASE 
                    WHEN home_player_1_id IS NOT NULL THEN 'has_players'
                    ELSE 'no_players'
                END as player_data_status
            FROM match_scores
            ORDER BY match_date DESC
            LIMIT 10
            """
        )
        results["recent_matches"] = recent_matches
        
        # 6. Player ID patterns - check what formats exist
        player_id_patterns = execute_query(
            """
            SELECT 
                SUBSTRING(home_player_1_id, 1, 10) as id_pattern,
                COUNT(*) as occurrence_count
            FROM match_scores
            WHERE home_player_1_id IS NOT NULL
            GROUP BY SUBSTRING(home_player_1_id, 1, 10)
            ORDER BY occurrence_count DESC
            LIMIT 10
            """
        )
        results["player_id_patterns"] = player_id_patterns
        
        # 7. Check for any "nndz-" pattern player IDs
        nndz_players = execute_query(
            """
            SELECT DISTINCT
                CASE 
                    WHEN home_player_1_id LIKE 'nndz-%' THEN home_player_1_id
                    WHEN home_player_2_id LIKE 'nndz-%' THEN home_player_2_id
                    WHEN away_player_1_id LIKE 'nndz-%' THEN away_player_1_id
                    WHEN away_player_2_id LIKE 'nndz-%' THEN away_player_2_id
                END as nndz_player_id,
                COUNT(*) as match_count
            FROM match_scores
            WHERE home_player_1_id LIKE 'nndz-%' OR home_player_2_id LIKE 'nndz-%'
               OR away_player_1_id LIKE 'nndz-%' OR away_player_2_id LIKE 'nndz-%'
            GROUP BY 1
            ORDER BY match_count DESC
            """
        )
        results["nndz_pattern_players"] = nndz_players
        
        # Analysis
        analysis = {
            "database_has_matches": results["total_matches"] > 0,
            "tennaqua_data_exists": results["tennaqua_matches"] > 0,
            "nndz_players_exist": len(nndz_players) > 0 if nndz_players else False,
            "leagues_with_data": len([l for l in league_distribution if l["match_count"] > 0]),
            "data_freshness": "recent" if date_range and date_range["latest_match"] and date_range["latest_match"] >= "2024-01-01" else "old_or_missing"
        }
        
        if results["total_matches"] == 0:
            analysis["diagnosis"] = "CRITICAL: No match data in staging database at all"
            analysis["recommendation"] = "Full ETL import required"
        elif results["tennaqua_matches"] == 0:
            analysis["diagnosis"] = "Tennaqua-specific data missing"
            analysis["recommendation"] = "Check Tennaqua ETL import specifically"
        elif len(nndz_players) == 0:
            analysis["diagnosis"] = "No 'nndz-' pattern player IDs found - player ID format issue"
            analysis["recommendation"] = "Check player ID generation/import process"
        else:
            analysis["diagnosis"] = "Database has data but Ross's specific records missing"
            analysis["recommendation"] = "Ross-specific ETL import issue"
        
        results["analysis"] = analysis
        
        return jsonify({
            "debug": "staging_database_health",
            "railway_env": railway_env,
            "results": results
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/check-etl-environment-status")
def check_etl_environment_status():
    """
    EMERGENCY: Check which environment ETL is running on and provide stop mechanism
    """
    try:
        import os
        import subprocess
        from database_utils import execute_query, execute_query_one
        
        # Get current environment details
        railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
        database_url = os.environ.get("DATABASE_URL", "not_set")
        
        # Check if this is production or staging based on environment variables
        is_production = "production" in railway_env.lower() if railway_env != "not_set" else False
        is_staging = "staging" in railway_env.lower() if railway_env != "not_set" else False
        
        results = {
            "current_environment": railway_env,
            "database_url_preview": database_url[:50] + "..." if database_url != "not_set" else "not_set",
            "is_production": is_production,
            "is_staging": is_staging,
            "timestamp": datetime.now().isoformat()
        }
        
        # Check recent database activity (ETL typically creates lots of inserts)
        try:
            recent_activity = execute_query_one(
                """
                SELECT 
                    COUNT(*) as total_matches,
                    MAX(created_at) as latest_created,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as recent_inserts
                FROM match_scores
                WHERE created_at IS NOT NULL
                """
            )
            
            if recent_activity:
                results["database_activity"] = {
                    "total_matches": recent_activity["total_matches"],
                    "latest_created": str(recent_activity["latest_created"]) if recent_activity["latest_created"] else None,
                    "recent_inserts": recent_activity["recent_inserts"],
                    "high_activity": recent_activity["recent_inserts"] > 100
                }
            else:
                # Fallback if created_at column doesn't exist
                basic_count = execute_query_one("SELECT COUNT(*) as total FROM match_scores")
                results["database_activity"] = {
                    "total_matches": basic_count["total"] if basic_count else 0,
                    "recent_inserts": "unknown - no created_at column",
                    "high_activity": False
                }
        except Exception as e:
            results["database_activity"] = {
                "error": str(e),
                "total_matches": "unknown"
            }
        
        # Check for running processes (this might not work in Railway environment)
        try:
            # Look for python processes that might be ETL
            proc_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            if proc_result.returncode == 0:
                python_processes = [line for line in proc_result.stdout.split('\n') if 'python' in line.lower() and ('etl' in line.lower() or 'import' in line.lower())]
                results["running_processes"] = {
                    "found_etl_processes": len(python_processes),
                    "processes": python_processes[:5]  # Limit to first 5
                }
            else:
                results["running_processes"] = {"error": "Could not check processes"}
        except Exception as e:
            results["running_processes"] = {"error": f"Process check failed: {str(e)}"}
        
        # Environment-specific warnings
        warnings = []
        if is_production:
            warnings.append("🚨 CRITICAL: You are on PRODUCTION environment!")
            warnings.append("🚨 If ETL is running here, it will overwrite production data!")
            warnings.append("🚨 STOP immediately if this was not intended!")
        elif is_staging:
            warnings.append("✅ You are on STAGING environment - safe to run ETL")
        else:
            warnings.append("⚠️ Environment unclear - verify before proceeding")
        
        results["warnings"] = warnings
        
        # Emergency actions available
        emergency_actions = []
        if is_production:
            emergency_actions.append({
                "action": "EMERGENCY_STOP_ETL",
                "description": "Kill any running ETL processes immediately",
                "endpoint": "/debug/emergency-stop-etl",
                "risk": "HIGH - Only use if ETL is running on wrong environment"
            })
        
        emergency_actions.append({
            "action": "CHECK_DATABASE_CHANGES",
            "description": "Check for recent database modifications",
            "endpoint": "/debug/check-recent-database-changes",
            "risk": "LOW - Read-only check"
        })
        
        results["emergency_actions"] = emergency_actions
        
        return jsonify({
            "debug": "check_etl_environment_status",
            "results": results,
            "immediate_action_needed": is_production and results["database_activity"].get("high_activity", False)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "emergency_note": "If you cannot determine environment, assume PRODUCTION and proceed with caution"
        }), 500


@app.route("/debug/emergency-stop-etl")
def emergency_stop_etl():
    """
    EMERGENCY: Attempt to stop any running ETL processes
    """
    try:
        import subprocess
        import signal
        import os
        
        railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
        
        results = {
            "environment": railway_env,
            "timestamp": datetime.now().isoformat(),
            "actions_taken": []
        }
        
        # Only allow this on production (where it would be an emergency)
        if "production" not in railway_env.lower():
            return jsonify({
                "error": "Emergency stop only available on production environment",
                "current_env": railway_env,
                "note": "Use normal process termination on other environments"
            }), 403
        
        # Try to find and kill ETL processes
        try:
            # Find processes with ETL-related keywords
            proc_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
            if proc_result.returncode == 0:
                lines = proc_result.stdout.split('\n')
                etl_processes = []
                
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['etl', 'import_all', 'scraper', 'import.py']):
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                pid = int(parts[1])
                                etl_processes.append({"pid": pid, "command": line})
                            except ValueError:
                                continue
                
                results["found_processes"] = len(etl_processes)
                
                # Kill the processes
                killed_processes = []
                for proc in etl_processes:
                    try:
                        os.kill(proc["pid"], signal.SIGTERM)  # Graceful termination first
                        killed_processes.append(f"SIGTERM sent to PID {proc['pid']}")
                        
                        # Wait a moment then force kill if needed
                        import time
                        time.sleep(2)
                        try:
                            os.kill(proc["pid"], signal.SIGKILL)  # Force kill
                            killed_processes.append(f"SIGKILL sent to PID {proc['pid']}")
                        except ProcessLookupError:
                            killed_processes.append(f"PID {proc['pid']} already terminated")
                            
                    except ProcessLookupError:
                        killed_processes.append(f"PID {proc['pid']} not found")
                    except PermissionError:
                        killed_processes.append(f"Permission denied for PID {proc['pid']}")
                
                results["actions_taken"] = killed_processes
                
            else:
                results["error"] = "Could not list processes"
                
        except Exception as e:
            results["error"] = f"Process termination failed: {str(e)}"
        
        # Additional safety measure - check if database is still being modified
        try:
            from database_utils import execute_query_one
            
            # Check if inserts are still happening
            count_before = execute_query_one("SELECT COUNT(*) as count FROM match_scores")
            import time
            time.sleep(3)
            count_after = execute_query_one("SELECT COUNT(*) as count FROM match_scores")
            
            if count_before and count_after:
                if count_after["count"] > count_before["count"]:
                    results["database_still_active"] = True
                    results["new_records"] = count_after["count"] - count_before["count"]
                else:
                    results["database_still_active"] = False
                    
        except Exception as e:
            results["database_check_error"] = str(e)
        
        return jsonify({
            "debug": "emergency_stop_etl",
            "results": results,
            "next_steps": [
                "1. Check if database modifications have stopped",
                "2. Verify no new records are being inserted",
                "3. If ETL was running on production, assess data integrity",
                "4. Re-run ETL on correct staging environment"
            ]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500




@app.route("/debug/check-recent-database-changes")
def check_recent_database_changes():
    """
    Check for recent database modifications to detect active ETL
    """
    try:
        from database_utils import execute_query, execute_query_one
        
        railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
        
        results = {
            "environment": railway_env,
            "timestamp": datetime.now().isoformat()
        }
        
        # Check match_scores table size over time
        current_count = execute_query_one("SELECT COUNT(*) as count FROM match_scores")
        results["current_match_count"] = current_count["count"] if current_count else 0
        
        # If there's a created_at or updated_at column, check recent activity
        try:
            recent_records = execute_query_one(
                """
                SELECT 
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '5 minutes') as last_5_min,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 minutes') as last_30_min,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as last_hour,
                    MAX(created_at) as latest_record
                FROM match_scores
                WHERE created_at IS NOT NULL
                """
            )
            
            if recent_records:
                results["recent_activity"] = {
                    "last_5_minutes": recent_records["last_5_min"],
                    "last_30_minutes": recent_records["last_30_min"], 
                    "last_hour": recent_records["last_hour"],
                    "latest_record": str(recent_records["latest_record"]) if recent_records["latest_record"] else None
                }
                
                # Determine if ETL is likely running
                if recent_records["last_5_min"] > 10:
                    results["etl_status"] = "LIKELY_RUNNING - High recent activity"
                elif recent_records["last_30_min"] > 50:
                    results["etl_status"] = "POSSIBLY_RUNNING - Moderate recent activity"
                else:
                    results["etl_status"] = "LIKELY_STOPPED - Low recent activity"
            
        except Exception as e:
            # Fallback - just monitor count changes
            results["created_at_check"] = f"Failed: {str(e)}"
            results["etl_status"] = "UNKNOWN - Cannot check timestamps"
        
        # Check other tables that ETL typically modifies
        table_counts = {}
        for table in ["players", "teams", "leagues", "clubs", "series"]:
            try:
                count = execute_query_one(f"SELECT COUNT(*) as count FROM {table}")
                table_counts[table] = count["count"] if count else 0
            except Exception as e:
                table_counts[table] = f"Error: {str(e)}"
        
        results["table_counts"] = table_counts
        
        # Real-time monitoring test
        print("Starting 10-second database monitoring test...")
        count_start = execute_query_one("SELECT COUNT(*) as count FROM match_scores")
        start_count = count_start["count"] if count_start else 0
        
        import time
        time.sleep(10)
        
        count_end = execute_query_one("SELECT COUNT(*) as count FROM match_scores")
        end_count = count_end["count"] if count_end else 0
        
        records_added = end_count - start_count
        results["realtime_test"] = {
            "duration_seconds": 10,
            "records_at_start": start_count,
            "records_at_end": end_count,
            "records_added": records_added,
            "active_insertion": records_added > 0
        }
        
        # Final assessment
        if records_added > 0:
            results["final_assessment"] = "🚨 ACTIVE ETL DETECTED - Database is being modified RIGHT NOW"
        elif results.get("recent_activity", {}).get("last_5_minutes", 0) > 5:
            results["final_assessment"] = "⚠️ RECENT ETL ACTIVITY - ETL was active in last 5 minutes"
        else:
            results["final_assessment"] = "✅ NO ACTIVE ETL - Database appears stable"
        
        return jsonify({
            "debug": "check_recent_database_changes",
            "results": results
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/admin/run-temp-password-migration")
def run_temp_password_migration():
    """
    Web endpoint to run temporary password migration on staging
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env not in ["staging", "production"]:
        return jsonify({
            "error": "This migration endpoint only works on staging or production",
            "railway_env": railway_env,
            "instructions": "Visit this URL on staging or production environment to run the migration"
        }), 403
    
    try:
        from database_utils import execute_update
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "migration_steps": []
        }
        
        # Step 1: Check if columns already exist
        results["migration_steps"].append("🔍 Checking if temporary password columns exist...")
        
        try:
            check_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('has_temporary_password', 'temporary_password_set_at')
            """
            from database_utils import execute_query
            existing_columns = execute_query(check_query)
            
            if existing_columns and len(existing_columns) >= 2:
                results["migration_steps"].append("✅ Temporary password columns already exist")
                results["columns_exist"] = True
                return jsonify({
                    "status": "success",
                    "message": "Temporary password columns already exist - no migration needed",
                    "results": results
                })
            else:
                results["migration_steps"].append("📋 Columns need to be added")
                results["columns_exist"] = False
                
        except Exception as e:
            results["migration_steps"].append(f"⚠️ Could not check columns: {str(e)}")
            results["columns_exist"] = False
        
        # Step 2: Run the migration
        results["migration_steps"].append("🔄 Running temporary password migration...")
        
        migration_sql = """
        -- Add columns to track temporary passwords
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS has_temporary_password BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS temporary_password_set_at TIMESTAMP;

        -- Add index for efficient querying
        CREATE INDEX IF NOT EXISTS idx_users_temporary_password 
        ON users(has_temporary_password) 
        WHERE has_temporary_password = TRUE;

        -- Add comment for documentation
        COMMENT ON COLUMN users.has_temporary_password IS 'Flag indicating if user has a temporary password that needs to be changed';
        COMMENT ON COLUMN users.temporary_password_set_at IS 'Timestamp when temporary password was set';
        """
        
        execute_update(migration_sql)
        results["migration_steps"].append("✅ Migration SQL executed successfully")
        
        # Step 3: Verify the migration
        results["migration_steps"].append("🧪 Verifying migration...")
        
        verify_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name IN ('has_temporary_password', 'temporary_password_set_at')
        """
        
        verify_columns = execute_query(verify_query)
        results["verification"] = {
            "columns_found": len(verify_columns) if verify_columns else 0,
            "column_names": [col["column_name"] for col in verify_columns] if verify_columns else []
        }
        
        if len(verify_columns) >= 2:
            results["migration_steps"].append("✅ Migration verification successful")
            results["success"] = True
            
            return jsonify({
                "status": "success",
                "message": "Temporary password migration completed successfully!",
                "results": results,
                "next_steps": [
                    "✅ Migration complete",
                    "👉 Try logging in again - the temporary password functionality should now work",
                    "🎯 The login error should be resolved"
                ]
            })
        else:
            results["migration_steps"].append("❌ Migration verification failed")
            results["success"] = False
            
            return jsonify({
                "status": "error",
                "message": "Migration ran but verification failed",
                "results": results
            }), 500
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": "Migration endpoint error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/admin/run-captain-messages-migration")
def run_captain_messages_migration():
    """
    Web endpoint to run captain messages migration on staging or production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env not in ["staging", "production"]:
        return jsonify({
            "error": "This migration endpoint only works on staging or production",
            "railway_env": railway_env,
            "instructions": "Visit this URL on staging or production environment to run the migration"
        }), 403
    
    try:
        from database_utils import execute_query_one, execute_update
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "migration_steps": []
        }
        
        # Step 1: Check if table already exists
        results["migration_steps"].append("🔍 Checking if captain_messages table exists...")
        
        try:
            table_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'captain_messages'
                )
            """)
            
            if table_check and table_check["exists"]:
                results["migration_steps"].append("✅ Captain messages table already exists")
                results["table_exists"] = True
                return jsonify({
                    "status": "success",
                    "message": "Captain messages table already exists - no migration needed",
                    "results": results
                })
            else:
                results["migration_steps"].append("📋 Table needs to be created")
                results["table_exists"] = False
                
        except Exception as e:
            results["migration_steps"].append(f"⚠️ Could not check table: {str(e)}")
            results["table_exists"] = False
        
        # Step 2: Run the migration
        results["migration_steps"].append("🔄 Running captain messages migration...")
        
        migration_sql = """
        -- Migration: Add Captain Messages Table
        -- Date: 2025-07-13 12:00:00
        -- Description: Adds captain_messages table for team captain messages

        CREATE TABLE IF NOT EXISTS captain_messages (
            id SERIAL PRIMARY KEY,
            team_id INTEGER NOT NULL REFERENCES teams(id),
            captain_user_id INTEGER NOT NULL REFERENCES users(id),
            message TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Index for fast lookup by team
        CREATE INDEX IF NOT EXISTS idx_captain_messages_team_id ON captain_messages(team_id);

        -- Add comment for documentation
        COMMENT ON TABLE captain_messages IS 'Stores captain messages for teams. These messages appear in the notifications feed for all team members.';
        """
        
        execute_update(migration_sql)
        results["migration_steps"].append("✅ Migration SQL executed successfully")
        
        # Step 3: Verify the migration
        results["migration_steps"].append("🧪 Verifying migration...")
        
        verify_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'captain_messages'
            )
        """
        
        verify_table = execute_query_one(verify_query)
        results["verification"] = {
            "table_exists": verify_table["exists"] if verify_table else False
        }
        
        if verify_table and verify_table["exists"]:
            results["migration_steps"].append("✅ Migration verification successful")
            results["success"] = True
            
            return jsonify({
                "status": "success",
                "message": "Captain messages migration completed successfully!",
                "results": results,
                "next_steps": [
                    "✅ Migration complete",
                    "👉 Captain messages functionality should now work",
                    "🎯 Team notifications should display captain messages"
                ]
            })
        else:
            results["migration_steps"].append("❌ Migration verification failed")
            results["success"] = False
            
            return jsonify({
                "status": "error",
                "message": "Migration ran but verification failed",
                "results": results
            }), 500
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": "Migration endpoint error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/admin/run-pickup-games-migration")
def run_pickup_games_migration():
    """
    Web endpoint to run pickup games migration on staging or production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env not in ["staging", "production"]:
        return jsonify({
            "error": "This migration endpoint only works on staging or production",
            "railway_env": railway_env,
            "instructions": "Visit this URL on staging or production environment to run the migration"
        }), 403
    
    try:
        import subprocess
        from database_utils import execute_query_one
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "migration_steps": []
        }
        
        # Step 1: Check current revision
        results["migration_steps"].append("🔍 Checking current Alembic revision...")
        
        try:
            current_result = subprocess.run(
                ["alembic", "current"], 
                capture_output=True, 
                text=True, 
                cwd="/app"
            )
            
            if current_result.returncode == 0:
                current_output = current_result.stdout.strip()
                results["current_revision"] = current_output
                results["migration_steps"].append(f"📊 Current revision: {current_output}")
                
                # Check if already at target revision
                if "20484d947d9d" in current_output:
                    results["migration_steps"].append("✅ Already at pickup games revision - checking tables...")
                    
                    # Verify tables exist
                    pg_check = execute_query_one("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'pickup_games'
                        )
                    """)
                    
                    if pg_check and pg_check["exists"]:
                        return jsonify({
                            "status": "success",
                            "message": "Migration already complete - pickup games tables exist",
                            "results": results,
                            "next_step": f"Visit https://rally-{railway_env}.up.railway.app/mobile/pickup-games to test"
                        })
                        
            else:
                results["migration_steps"].append(f"⚠️ Could not check current revision: {current_result.stderr}")
                
        except Exception as e:
            results["migration_steps"].append(f"❌ Error checking revision: {str(e)}")
        
        # Step 2: Run the migration
        results["migration_steps"].append("🔄 Running Alembic upgrade to head...")
        
        upgrade_result = subprocess.run(
            ["alembic", "upgrade", "head"], 
            capture_output=True, 
            text=True,
            cwd="/app"
        )
        
        if upgrade_result.returncode == 0:
            results["migration_steps"].append("✅ Alembic upgrade completed!")
            results["upgrade_output"] = upgrade_result.stdout
            results["migration_steps"].append("📋 Migration output captured")
            
            # Verify the migration worked
            results["migration_steps"].append("🧪 Verifying pickup games tables...")
            
            # Check pickup_games table
            pg_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pickup_games'
                )
            """)
            
            pg_exists = pg_check["exists"] if pg_check else False
            results["pickup_games_table_exists"] = pg_exists
            results["migration_steps"].append(f"📋 pickup_games table exists: {pg_exists}")
            
            # Check pickup_game_participants table
            pgp_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pickup_game_participants'
                )
            """)
            
            pgp_exists = pgp_check["exists"] if pgp_check else False
            results["pickup_game_participants_table_exists"] = pgp_exists
            results["migration_steps"].append(f"📋 pickup_game_participants table exists: {pgp_exists}")
            
            # Final verification
            if pg_exists and pgp_exists:
                results["migration_steps"].append("🎉 Migration successful - all tables created!")
                
                # Check final revision
                final_result = subprocess.run(
                    ["alembic", "current"], 
                    capture_output=True, 
                    text=True,
                    cwd="/app"
                )
                
                if final_result.returncode == 0:
                    final_revision = final_result.stdout.strip()
                    results["final_revision"] = final_revision
                    results["migration_steps"].append(f"✅ Final revision: {final_revision}")
                
                return jsonify({
                    "status": "success",
                    "message": "Pickup games migration completed successfully!",
                    "results": results,
                    "next_steps": [
                        "✅ Migration complete",
                        f"👉 Test pickup games: https://rally-{railway_env}.up.railway.app/mobile/pickup-games",
                        "🎯 The page should now load instead of being stuck on 'Loading upcoming games...'"
                    ]
                })
            else:
                results["migration_steps"].append("❌ Tables verification failed")
                return jsonify({
                    "status": "partial_success", 
                    "message": "Migration ran but table verification failed",
                    "results": results
                }), 500
                
        else:
            results["migration_steps"].append("❌ Alembic upgrade failed")
            results["upgrade_error"] = upgrade_result.stderr
            results["upgrade_output"] = upgrade_result.stdout
            
            return jsonify({
                "status": "error",
                "message": "Migration failed",
                "results": results,
                "error_details": upgrade_result.stderr
            }), 500
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": "Migration endpoint error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/admin/fix-series-dropdown")
def fix_series_dropdown():
    """
    Web endpoint to fix series dropdown display names on production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This series dropdown fix endpoint only works on production",
            "railway_env": railway_env,
            "instructions": "Visit this URL on production environment to fix the series dropdown"
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        import re
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "fix_steps": []
        }
        
        # Get APTA Chicago league ID
        chicago_league = execute_query_one("SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO'")
        if not chicago_league:
            return jsonify({
                "status": "error",
                "message": "APTA Chicago league not found",
                "results": results
            }), 404
            
        chicago_league_id = chicago_league['id']
        results["chicago_league_id"] = chicago_league_id
        results["fix_steps"].append(f"📋 Found APTA Chicago League ID: {chicago_league_id}")
        
        # Get current series
        current_series = execute_query(f"""
            SELECT s.id, s.name, s.display_name
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            WHERE sl.league_id = {chicago_league_id}
            ORDER BY s.name
        """)
        
        results["initial_series_count"] = len(current_series)
        results["fix_steps"].append(f"📊 Found {len(current_series)} series in APTA Chicago")
        
        # Fix regular Chicago series (Chicago X -> Series X)
        results["fix_steps"].append("🔧 Fixing regular Chicago series display names...")
        regular_fixes = 0
        
        for series in current_series:
            match = re.match(r'^Chicago (\d+)$', series['name'])
            if match:
                number = match.group(1)
                correct_display_name = f"Series {number}"
                
                if series['display_name'] != correct_display_name:
                    rows_updated = execute_update(
                        "UPDATE series SET display_name = %s WHERE id = %s",
                        [correct_display_name, series['id']]
                    )
                    if rows_updated > 0:
                        results["fix_steps"].append(f"  ✅ Fixed '{series['name']}': '{series['display_name']}' → '{correct_display_name}'")
                        regular_fixes += 1
        
        results["regular_fixes"] = regular_fixes
        results["fix_steps"].append(f"✅ Fixed {regular_fixes} regular series display names")
        
        # Fix SW series (Chicago X SW -> Series X SW)
        results["fix_steps"].append("🔧 Fixing SW series display names...")
        sw_fixes = 0
        
        for series in current_series:
            match = re.match(r'^Chicago (\d+) SW$', series['name'])
            if match:
                number = match.group(1)
                correct_display_name = f"Series {number} SW"
                
                if series['display_name'] != correct_display_name:
                    rows_updated = execute_update(
                        "UPDATE series SET display_name = %s WHERE id = %s",
                        [correct_display_name, series['id']]
                    )
                    if rows_updated > 0:
                        results["fix_steps"].append(f"  ✅ Fixed '{series['name']}': '{series['display_name']}' → '{correct_display_name}'")
                        sw_fixes += 1
        
        results["sw_fixes"] = sw_fixes
        results["fix_steps"].append(f"✅ Fixed {sw_fixes} SW series display names")
        
        # Remove incorrect/invalid series from APTA Chicago
        results["fix_steps"].append("🗑️ Removing incorrect/invalid series from APTA Chicago...")
        
        # List of series that should NOT be in APTA Chicago dropdown
        invalid_series_patterns = [
            'Division %',           # Division series (belong to CNSWPL)
            'Chicago Chicago',      # Duplicate/invalid entry
            'Legends',              # Invalid entry
            'SA',                   # Invalid entry  
            'SLegends',             # Invalid entry
        ]
        
        # Also remove standalone "Chicago" (without number)
        invalid_series_exact = ['Chicago']
        
        invalid_series = []
        
        # Find series matching patterns
        for pattern in invalid_series_patterns:
            pattern_series = execute_query(f"""
                SELECT s.id, s.name, s.display_name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE sl.league_id = {chicago_league_id}
                AND s.name LIKE '{pattern}'
            """)
            invalid_series.extend(pattern_series)
        
        # Find exact matches
        for exact_name in invalid_series_exact:
            exact_series = execute_query(f"""
                SELECT s.id, s.name, s.display_name
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                WHERE sl.league_id = {chicago_league_id}
                AND s.name = '{exact_name}'
            """)
            invalid_series.extend(exact_series)
        
        removed_count = 0
        for series in invalid_series:
            rows_deleted = execute_update(
                "DELETE FROM series_leagues WHERE series_id = %s AND league_id = %s",
                [series['id'], chicago_league_id]
            )
            if rows_deleted > 0:
                results["fix_steps"].append(f"  🗑️ Removed '{series['name']}' from APTA Chicago")
                removed_count += 1
        
        results["invalid_series_removed"] = removed_count
        results["fix_steps"].append(f"✅ Removed {removed_count} invalid series from APTA Chicago")
        
        # Verify final state
        final_series = execute_query(f"""
            SELECT s.name, s.display_name
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            WHERE sl.league_id = {chicago_league_id}
            ORDER BY s.name
        """)
        
        results["final_series_count"] = len(final_series)
        results["fix_steps"].append(f"🧪 Final verification: {len(final_series)} series")
        
        # Count consistent series
        consistent_count = 0
        for series in final_series:
            if series['display_name'] and series['display_name'].startswith('Series '):
                consistent_count += 1
        
        results["consistent_series_count"] = consistent_count
        results["fix_steps"].append(f"✅ {consistent_count}/{len(final_series)} series have consistent 'Series X' display names")
        
        # Sample results
        sample_series = []
        for series in final_series[:10]:
            display = series['display_name'] or series['name']
            sample_series.append(display)
        
        results["sample_series"] = sample_series
        
        return jsonify({
            "status": "success",
            "message": "Series dropdown fix completed successfully!",
            "results": results,
            "next_steps": [
                "✅ Series dropdown fix complete",
                "👉 Refresh pickup games page to see consistent 'Series X' format",
                "🎯 Dropdown should now show clean, consistent series names"
            ]
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": "Series dropdown fix error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/test-pickup-games-staging")
def test_pickup_games_staging():
    """
    Debug pickup games loading issue on staging
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "staging":
        return jsonify({
            "error": "This endpoint only works on staging",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        # Test 1: Check if pickup_games table exists
        try:
            table_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pickup_games'
                )
            """)
            results["tests"]["pickup_games_table_exists"] = table_check["exists"] if table_check else False
        except Exception as e:
            results["tests"]["pickup_games_table_exists"] = f"Error: {str(e)}"
        
        # Test 2: Check if pickup_game_participants table exists
        try:
            participants_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pickup_game_participants'
                )
            """)
            results["tests"]["pickup_game_participants_table_exists"] = participants_check["exists"] if participants_check else False
        except Exception as e:
            results["tests"]["pickup_game_participants_table_exists"] = f"Error: {str(e)}"
        
        # Test 3: Try to query pickup_games table
        try:
            count_query = "SELECT COUNT(*) as total FROM pickup_games"
            count_result = execute_query_one(count_query)
            results["tests"]["pickup_games_count"] = count_result["total"] if count_result else 0
        except Exception as e:
            results["tests"]["pickup_games_count"] = f"Error: {str(e)}"
        
        # Test 4: Try the exact API query that's failing
        try:
            now = datetime.now()
            current_date = now.date()
            current_time = now.time()
            
            # This is the exact query from the API
            upcoming_query = """
                SELECT 
                    pg.id,
                    pg.description,
                    pg.game_date,
                    pg.game_time,
                    pg.players_requested,
                    pg.players_committed,
                    pg.pti_low,
                    pg.pti_high,
                    pg.series_low,
                    pg.series_high,
                    pg.club_only,
                    pg.creator_user_id,
                    pg.created_at,
                    COUNT(pgp.id) as actual_participants
                FROM pickup_games pg
                LEFT JOIN pickup_game_participants pgp ON pg.id = pgp.pickup_game_id
                WHERE (pg.game_date > %s) OR (pg.game_date = %s AND pg.game_time > %s)
                GROUP BY pg.id
                ORDER BY pg.game_date ASC, pg.game_time ASC
            """
            
            upcoming_games = execute_query(upcoming_query, [current_date, current_date, current_time])
            results["tests"]["api_query_success"] = True
            results["tests"]["upcoming_games_count"] = len(upcoming_games) if upcoming_games else 0
            results["tests"]["upcoming_games_sample"] = upcoming_games[:3] if upcoming_games else []
            
        except Exception as e:
            results["tests"]["api_query_success"] = False
            results["tests"]["api_query_error"] = str(e)
            import traceback
            results["tests"]["api_query_traceback"] = traceback.format_exc()
        
        # Test 5: Check database schema for pickup tables
        try:
            schema_query = """
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'pickup_games'
                ORDER BY ordinal_position
            """
            schema_result = execute_query(schema_query)
            results["tests"]["pickup_games_schema"] = schema_result if schema_result else []
        except Exception as e:
            results["tests"]["pickup_games_schema"] = f"Error: {str(e)}"
        
        # Test 6: Check if there are any pickup games at all
        try:
            all_games_query = "SELECT id, description, game_date FROM pickup_games LIMIT 5"
            all_games = execute_query(all_games_query)
            results["tests"]["all_games_sample"] = []
            for game in (all_games or []):
                results["tests"]["all_games_sample"].append({
                    "id": game["id"],
                    "description": game["description"],
                    "game_date": str(game["game_date"])
                })
        except Exception as e:
            results["tests"]["all_games_sample"] = f"Error: {str(e)}"
        
        return jsonify({
            "debug": "test_pickup_games_staging",
            "results": results,
            "diagnosis": {
                "likely_cause": "pickup_games table missing or API query failing",
                "next_steps": [
                    "1. Check if database migration ran for pickup_games table",
                    "2. Verify table structure matches expected schema",
                    "3. Test API endpoint directly if tables exist"
                ]
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


# ==========================================
# ERROR HANDLERS
# ==========================================


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


@app.route("/debug/check-twilio-delivery")
def check_twilio_delivery():
    """
    Check Twilio delivery status for recent SMS messages to Ross
    """
    try:
        import os
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Get Twilio credentials using the same config as notifications service
        from config import TwilioConfig
        
        account_sid = TwilioConfig.ACCOUNT_SID
        auth_token = TwilioConfig.AUTH_TOKEN
        
        if not account_sid or not auth_token:
            return jsonify({
                "error": "Twilio credentials not available",
                "account_sid_available": bool(account_sid),
                "auth_token_available": bool(auth_token),
                "config_details": {
                    "account_sid": account_sid[:8] + "..." if account_sid else None,
                    "auth_token_exists": bool(auth_token)
                }
            }), 500
        
        # Check the specific message SIDs from recent logs
        message_sids = [
            'SM1a4b7be4941f362d9d4452d37f841dde',
            'SM1bf7e2be6e5a206571534818d1f86f4f', 
            'SM2c37139ae0cffe4f2109c0c874a52b05'
        ]
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "target_number": "+17732138911",
            "checked_messages": [],
            "recent_messages": []
        }
        
        # Set up HTTP auth for Twilio API
        auth = HTTPBasicAuth(account_sid, auth_token)
        
        # Check each specific message
        for sid in message_sids:
            try:
                # Get message details via HTTP API
                url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{sid}.json"
                response = requests.get(url, auth=auth, timeout=10)
                
                if response.status_code == 200:
                    message_data = response.json()
                    
                    message_info = {
                        "sid": sid,
                        "to": message_data.get("to"),
                        "body": message_data.get("body", "")[:50] + "..." if len(message_data.get("body", "")) > 50 else message_data.get("body", ""),
                        "status": message_data.get("status"),
                        "date_sent": message_data.get("date_sent"),
                        "price": f"${message_data.get('price')} {message_data.get('price_unit')}" if message_data.get('price') else "N/A",
                        "error_code": message_data.get("error_code"),
                        "error_message": message_data.get("error_message"),
                        "delivery_analysis": "Unknown"
                    }
                    
                    # Analyze delivery status
                    status = message_data.get("status")
                    if status == 'delivered':
                        message_info["delivery_analysis"] = "✅ Successfully delivered"
                    elif status == 'failed':
                        message_info["delivery_analysis"] = "❌ Delivery failed"
                    elif status == 'undelivered':
                        message_info["delivery_analysis"] = "⚠️ Undelivered (carrier issue)"
                    elif status == 'sent':
                        message_info["delivery_analysis"] = "📤 Sent (pending delivery)"
                    elif status == 'queued':
                        message_info["delivery_analysis"] = "⏳ Queued for sending"
                        
                    results["checked_messages"].append(message_info)
                else:
                    results["checked_messages"].append({
                        "sid": sid,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "delivery_analysis": "❌ Error fetching message"
                    })
                
            except Exception as e:
                results["checked_messages"].append({
                    "sid": sid,
                    "error": str(e),
                    "delivery_analysis": "❌ Error fetching message"
                })
        
        # Get recent messages to this number via HTTP API
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            params = {
                "To": "+17732138911",
                "PageSize": 15
            }
            response = requests.get(url, auth=auth, params=params, timeout=10)
            
            if response.status_code == 200:
                messages_data = response.json()
                for msg in messages_data.get("messages", []):
                    results["recent_messages"].append({
                        "sid": msg.get("sid"),
                        "status": msg.get("status"),
                        "body": msg.get("body", "")[:30] + "..." if len(msg.get("body", "")) > 30 else msg.get("body", ""),
                        "date_sent": msg.get("date_sent")
                    })
            else:
                results["recent_messages_error"] = f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            results["recent_messages_error"] = str(e)
        
        # Summary analysis
        delivered_count = len([m for m in results["checked_messages"] if m.get("status") == "delivered"])
        failed_count = len([m for m in results["checked_messages"] if m.get("status") == "failed"])
        
        results["summary"] = {
            "total_checked": len(message_sids),
            "delivered": delivered_count,
            "failed": failed_count,
            "diagnosis": "All messages sent successfully from our system" if delivered_count == len(message_sids) else "Some delivery issues detected"
        }
        
        return jsonify({
            "debug": "check_twilio_delivery",
            "results": results
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/debug/twilio-config")
def debug_twilio_config():
    """
    Debug endpoint to check actual Twilio configuration in production
    """
    try:
        from config import TwilioConfig
        import os
        
        # Also check detailed logging notifications setting
        detailed_logging_enabled = False
        detailed_logging_error = None
        try:
            from app.services.admin_service import get_detailed_logging_notifications_setting
            detailed_logging_enabled = get_detailed_logging_notifications_setting()
        except Exception as e:
            detailed_logging_error = str(e)
        
        return jsonify({
            "debug": "twilio_config",
            "environment_variables": {
                "TWILIO_ACCOUNT_SID_env": os.getenv("TWILIO_ACCOUNT_SID", "NOT_SET"),
                "TWILIO_AUTH_TOKEN_env": "SET" if os.getenv("TWILIO_AUTH_TOKEN") else "NOT_SET",
                "TWILIO_MESSAGING_SERVICE_SID_env": os.getenv("TWILIO_MESSAGING_SERVICE_SID", "NOT_SET"),
                "TWILIO_SENDER_PHONE_env": os.getenv("TWILIO_SENDER_PHONE", "NOT_SET")
            },
            "effective_config": {
                "ACCOUNT_SID": TwilioConfig.ACCOUNT_SID,
                "AUTH_TOKEN": "SET" if TwilioConfig.AUTH_TOKEN else "NOT_SET", 
                "MESSAGING_SERVICE_SID": TwilioConfig.MESSAGING_SERVICE_SID,
                "SENDER_PHONE": TwilioConfig.SENDER_PHONE
            },
            "config_validation": TwilioConfig.validate_config(),
            "detailed_logging": {
                "enabled": detailed_logging_enabled,
                "error": detailed_logging_error
            },
            "admin_phone_number": "773-213-8911",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/debug/enable-activity-logging-sms")
def enable_activity_logging_sms():
    """
    Debug endpoint to enable detailed logging notifications in production
    """
    try:
        from app.services.admin_service import set_detailed_logging_notifications_setting, get_detailed_logging_notifications_setting
        
        # Check current setting
        current_setting = get_detailed_logging_notifications_setting()
        
        # Enable detailed logging notifications
        set_detailed_logging_notifications_setting(enabled=True, admin_email="rossfreedman@gmail.com")
        
        # Verify it was set
        new_setting = get_detailed_logging_notifications_setting()
        
        return jsonify({
            "debug": "enable_activity_logging_sms",
            "before": current_setting,
            "after": new_setting,
            "success": new_setting == True,
            "message": "Detailed logging notifications enabled" if new_setting else "Failed to enable detailed logging notifications",
            "admin_phone": "773-213-8911",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/debug/test-activity-logging-sms")
def test_activity_logging_sms():
    """
    Debug endpoint to test the complete activity logging SMS flow step by step
    """
    try:
        results = {
            "debug": "test_activity_logging_sms",
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "final_result": None
        }
        
        # Test 1: Check if detailed logging notifications are enabled
        try:
            from app.services.admin_service import get_detailed_logging_notifications_setting
            detailed_enabled = get_detailed_logging_notifications_setting()
            results["tests"]["detailed_logging_enabled"] = {
                "success": True,
                "enabled": detailed_enabled,
                "message": f"Detailed logging notifications: {'ENABLED' if detailed_enabled else 'DISABLED'}"
            }
        except Exception as e:
            results["tests"]["detailed_logging_enabled"] = {
                "success": False,
                "error": str(e),
                "message": "Failed to check detailed logging setting"
            }
        
        # Test 2: Check Twilio configuration
        try:
            from config import TwilioConfig
            config_status = TwilioConfig.validate_config()
            results["tests"]["twilio_config"] = {
                "success": config_status["is_valid"],
                "config": config_status,
                "message": f"Twilio config: {'VALID' if config_status['is_valid'] else 'INVALID'}"
            }
        except Exception as e:
            results["tests"]["twilio_config"] = {
                "success": False,
                "error": str(e),
                "message": "Failed to validate Twilio config"
            }
        
        # Test 3: Test the activity SMS formatting function
        try:
            from utils.logging import _format_activity_for_sms
            test_message = _format_activity_for_sms(
                user_email="debug@test.com",
                activity_type="page_visit",
                page="mobile",
                action="debug_test",
                details={"test": "debug_data"},
                is_impersonating=False
            )
            results["tests"]["sms_formatting"] = {
                "success": True,
                "formatted_message": test_message,
                "message_length": len(test_message),
                "message": "SMS formatting successful"
            }
        except Exception as e:
            results["tests"]["sms_formatting"] = {
                "success": False,
                "error": str(e),
                "message": "Failed to format SMS message"
            }
        
        # Test 4: Test SMS sending directly with admin phone number
        try:
            from app.services.notifications_service import send_sms_notification
            from utils.logging import ADMIN_PHONE_NUMBER
            
            test_sms_message = "🧪 DEBUG: Testing activity logging SMS pipeline - " + datetime.now().strftime("%H:%M:%S")
            
            sms_result = send_sms_notification(
                to_number=ADMIN_PHONE_NUMBER,
                message=test_sms_message,
                test_mode=False
            )
            
            results["tests"]["direct_sms"] = {
                "success": sms_result["success"],
                "admin_phone": ADMIN_PHONE_NUMBER,
                "message_sid": sms_result.get("message_sid"),
                "error": sms_result.get("error"),
                "message": f"Direct SMS test: {'SUCCESS' if sms_result['success'] else 'FAILED'}"
            }
        except Exception as e:
            results["tests"]["direct_sms"] = {
                "success": False,
                "error": str(e),
                "message": "Failed to send direct SMS test"
            }
        
        # Test 5: Test the complete activity logging notification function
        try:
            from utils.logging import _send_detailed_logging_notification
            
            _send_detailed_logging_notification(
                user_email="debug@test.com",
                activity_type="page_visit",
                page="debug_test",
                action="complete_test",
                details={"debug": "complete_pipeline_test"},
                is_impersonating=False
            )
            
            results["tests"]["complete_pipeline"] = {
                "success": True,
                "message": "Complete activity logging pipeline test executed successfully"
            }
        except Exception as e:
            results["tests"]["complete_pipeline"] = {
                "success": False,
                "error": str(e),
                "message": "Complete activity logging pipeline test failed"
            }
        
        # Test 6: Test database logging (just to verify it works)
        try:
            from utils.logging import _log_to_database
            
            _log_to_database(
                user_email="debug@test.com",
                activity_type="debug_test",
                page="debug_page",
                action="database_test",
                details_json='{"debug": "database_test"}',
                is_impersonating=False
            )
            
            results["tests"]["database_logging"] = {
                "success": True,
                "message": "Database logging test successful"
            }
        except Exception as e:
            results["tests"]["database_logging"] = {
                "success": False,
                "error": str(e),
                "message": "Database logging test failed"
            }
        
        # Determine overall success
        all_tests_passed = all(test.get("success", False) for test in results["tests"].values())
        critical_tests_passed = (
            results["tests"].get("detailed_logging_enabled", {}).get("enabled", False) and
            results["tests"].get("twilio_config", {}).get("success", False) and
            results["tests"].get("direct_sms", {}).get("success", False)
        )
        
        if all_tests_passed:
            results["final_result"] = {
                "status": "SUCCESS",
                "message": "All tests passed! Activity logging SMS should work.",
                "recommendation": "Check if you received the debug SMS messages"
            }
        elif critical_tests_passed:
            results["final_result"] = {
                "status": "PARTIAL",
                "message": "Critical components work, but some tests failed",
                "recommendation": "Check failed tests for specific issues"
            }
        else:
            results["final_result"] = {
                "status": "FAILURE", 
                "message": "Critical components failed",
                "recommendation": "Fix the failed critical tests first"
            }
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/debug/investigate-victor-forman-production")
def investigate_victor_forman_production():
    """
    Investigate Victor Forman multiple registration issue in production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "investigation": {}
        }
        
        # 1. Find all users with Victor Forman name variations
        users_query = """
            SELECT 
                id, email, first_name, last_name, 
                created_at, last_login, league_context
            FROM users 
            WHERE (first_name ILIKE '%victor%' AND last_name ILIKE '%forman%')
               OR email ILIKE '%victor%' OR email ILIKE '%forman%'
            ORDER BY created_at ASC
        """
        
        victor_users = execute_query(users_query)
        results["investigation"]["victor_users"] = []
        
        for user in (victor_users or []):
            user_info = {
                "id": user['id'],
                "email": user['email'],
                "name": f"{user['first_name']} {user['last_name']}",
                "created_at": str(user['created_at']),
                "last_login": str(user['last_login']) if user['last_login'] else None,
                "league_context": user['league_context'],
                "associations": []
            }
            
            # Check associations for each user
            associations_query = """
                SELECT 
                    upa.tenniscores_player_id,
                    p.first_name, p.last_name,
                    l.league_name, c.name as club_name, s.name as series_name
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                WHERE upa.user_id = %s
            """
            
            associations = execute_query(associations_query, [user['id']])
            for assoc in (associations or []):
                user_info["associations"].append({
                    "player_name": f"{assoc['first_name']} {assoc['last_name']}",
                    "player_id": assoc['tenniscores_player_id'],
                    "league": assoc['league_name'],
                    "club": assoc['club_name'], 
                    "series": assoc['series_name']
                })
            
            results["investigation"]["victor_users"].append(user_info)
        
        # 2. Find all Victor Forman player records
        players_query = """
            SELECT 
                p.id, p.tenniscores_player_id, p.first_name, p.last_name,
                l.league_name, c.name as club_name, s.name as series_name,
                p.team_id, p.pti, p.wins, p.losses
            FROM players p
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id  
            LEFT JOIN series s ON p.series_id = s.id
            WHERE (p.first_name ILIKE '%victor%' AND p.last_name ILIKE '%forman%')
            ORDER BY l.league_name, c.name, s.name
        """
        
        victor_players = execute_query(players_query)
        results["investigation"]["victor_players"] = []
        
        for player in (victor_players or []):
            player_info = {
                "id": player['id'],
                "tenniscores_player_id": player['tenniscores_player_id'],
                "name": f"{player['first_name']} {player['last_name']}",
                "league": player['league_name'],
                "club": player['club_name'],
                "series": player['series_name'], 
                "team_id": player['team_id'],
                "stats": f"PTI: {player['pti']}, W-L: {player['wins']}-{player['losses']}",
                "associated_users": []
            }
            
            # Check which users are associated with this player
            player_associations_query = """
                SELECT 
                    upa.user_id,
                    u.email, u.first_name, u.last_name
                FROM user_player_associations upa
                JOIN users u ON upa.user_id = u.id
                WHERE upa.tenniscores_player_id = %s
            """
            
            player_assocs = execute_query(player_associations_query, [player['tenniscores_player_id']])
            for assoc in (player_assocs or []):
                player_info["associated_users"].append({
                    "user_id": assoc['user_id'],
                    "email": assoc['email'],
                    "name": f"{assoc['first_name']} {assoc['last_name']}"
                })
            
            results["investigation"]["victor_players"].append(player_info)
        
        # 3. Check for duplicate player ID associations (this is the core issue)
        duplicate_associations_query = """
            SELECT 
                upa.tenniscores_player_id,
                COUNT(*) as user_count,
                ARRAY_AGG(upa.user_id) as user_ids,
                ARRAY_AGG(u.email) as emails
            FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            GROUP BY upa.tenniscores_player_id
            HAVING COUNT(*) > 1
            ORDER BY user_count DESC
        """
        
        duplicates = execute_query(duplicate_associations_query)
        results["investigation"]["duplicate_associations"] = []
        
        for dup in (duplicates or []):
            dup_info = {
                "player_id": dup['tenniscores_player_id'],
                "user_count": dup['user_count'],
                "affected_users": []
            }
            
            for user_id, email in zip(dup['user_ids'], dup['emails']):
                dup_info["affected_users"].append({
                    "user_id": user_id,
                    "email": email
                })
            
            results["investigation"]["duplicate_associations"].append(dup_info)
        
        # 4. Summary analysis
        results["summary"] = {
            "victor_users_found": len(results["investigation"]["victor_users"]),
            "victor_players_found": len(results["investigation"]["victor_players"]), 
            "total_duplicate_associations": len(results["investigation"]["duplicate_associations"]),
            "issue_confirmed": len(results["investigation"]["victor_users"]) > 1 or len(results["investigation"]["duplicate_associations"]) > 0
        }
        
        # 5. Identify the specific problem
        if results["summary"]["victor_users_found"] > 1:
            results["problem_type"] = "MULTIPLE_USER_ACCOUNTS"
            results["problem_description"] = f"Found {results['summary']['victor_users_found']} different user accounts for Victor Forman"
        elif results["summary"]["total_duplicate_associations"] > 0:
            results["problem_type"] = "DUPLICATE_PLAYER_ASSOCIATIONS"
            results["problem_description"] = f"Found {results['summary']['total_duplicate_associations']} player IDs with multiple user associations"
        else:
            results["problem_type"] = "NO_ISSUE_DETECTED"
            results["problem_description"] = "Victor Forman setup appears correct"
        
        return jsonify({
            "debug": "investigate_victor_forman_production",
            "results": results
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/test-sms-direct")
def test_sms_direct():
    """
    Test SMS sending without Messaging Service to bypass potential A2P issues
    """
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        from config import TwilioConfig
        
        results = {
            "debug": "test_sms_direct",
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        # Test 1: Direct SMS without Messaging Service
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messages.json"
            
            # Use direct From/To without MessagingServiceSid
            data = {
                "To": "+17732138911",
                "From": TwilioConfig.SENDER_PHONE,  # +13128001632
                "Body": f"🔧 DIRECT SMS TEST (no messaging service) - {datetime.now().strftime('%H:%M:%S')}"
            }
            
            auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
            
            response = requests.post(url, data=data, auth=auth, timeout=30)
            response_data = response.json()
            
            if response.status_code == 201:
                results["tests"]["direct_sms_no_service"] = {
                    "success": True,
                    "message_sid": response_data.get("sid"),
                    "status": response_data.get("status"),
                    "from_number": data["From"],
                    "to_number": data["To"],
                    "message": "Direct SMS sent successfully (without messaging service)"
                }
            else:
                results["tests"]["direct_sms_no_service"] = {
                    "success": False,
                    "error": response_data.get("message", "Unknown error"),
                    "error_code": response_data.get("code"),
                    "status_code": response.status_code,
                    "message": "Direct SMS failed"
                }
                
        except Exception as e:
            results["tests"]["direct_sms_no_service"] = {
                "success": False,
                "error": str(e),
                "message": "Direct SMS test failed with exception"
            }
        
        # Test 2: SMS with Messaging Service (current method)
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messages.json"
            
            # Use Messaging Service (current production method)
            data = {
                "To": "+17732138911", 
                "MessagingServiceSid": TwilioConfig.MESSAGING_SERVICE_SID,
                "Body": f"🏗️ MESSAGING SERVICE TEST - {datetime.now().strftime('%H:%M:%S')}"
            }
            
            auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
            
            response = requests.post(url, data=data, auth=auth, timeout=30)
            response_data = response.json()
            
            if response.status_code == 201:
                results["tests"]["messaging_service_sms"] = {
                    "success": True,
                    "message_sid": response_data.get("sid"),
                    "status": response_data.get("status"), 
                    "messaging_service_sid": data["MessagingServiceSid"],
                    "to_number": data["To"],
                    "message": "Messaging Service SMS sent successfully"
                }
            else:
                results["tests"]["messaging_service_sms"] = {
                    "success": False,
                    "error": response_data.get("message", "Unknown error"),
                    "error_code": response_data.get("code"),
                    "status_code": response.status_code,
                    "message": "Messaging Service SMS failed"
                }
                
        except Exception as e:
            results["tests"]["messaging_service_sms"] = {
                "success": False,
                "error": str(e),
                "message": "Messaging Service SMS test failed with exception"
            }
        
        # Determine overall result
        direct_success = results["tests"].get("direct_sms_no_service", {}).get("success", False)
        service_success = results["tests"].get("messaging_service_sms", {}).get("success", False)
        
        if direct_success and service_success:
            results["conclusion"] = {
                "status": "BOTH_WORK",
                "message": "Both direct SMS and messaging service work - issue might be elsewhere",
                "recommendation": "Check message delivery status after a few minutes"
            }
        elif direct_success and not service_success:
            results["conclusion"] = {
                "status": "MESSAGING_SERVICE_ISSUE", 
                "message": "Direct SMS works but messaging service fails - use direct SMS",
                "recommendation": "Switch activity logging to use direct From/To instead of messaging service"
            }
        elif not direct_success and service_success:
            results["conclusion"] = {
                "status": "PHONE_NUMBER_ISSUE",
                "message": "Messaging service works but direct from number fails",
                "recommendation": "Check if sender phone number is properly configured"
            }
        else:
            results["conclusion"] = {
                "status": "BOTH_FAIL",
                "message": "Both methods fail - likely account or infrastructure issue",
                "recommendation": "Check Twilio account status and configuration"
            }
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/debug/fix-duplicate-player-associations-production")
def fix_duplicate_player_associations_production():
    """
    Fix duplicate player associations in production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "phase": "analysis",
            "duplicate_analysis": [],
            "fix_plan": [],
            "fixes_applied": False
        }
        
        # Phase 1: Analyze duplicates
        duplicates_query = """
            SELECT 
                upa.tenniscores_player_id,
                COUNT(*) as user_count,
                ARRAY_AGG(upa.user_id ORDER BY u.created_at ASC) as user_ids,
                ARRAY_AGG(u.email ORDER BY u.created_at ASC) as emails,
                ARRAY_AGG(u.created_at ORDER BY u.created_at ASC) as created_dates,
                ARRAY_AGG(u.last_login ORDER BY u.created_at ASC) as last_logins
            FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            GROUP BY upa.tenniscores_player_id
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """
        
        duplicates = execute_query(duplicates_query)
        
        if not duplicates:
            results["message"] = "No duplicate player associations found"
            return jsonify({
                "debug": "fix_duplicate_player_associations_production",
                "results": results
            })
        
        results["duplicates_found"] = len(duplicates)
        
        # Analyze each duplicate
        for dup in duplicates:
            player_id = dup['tenniscores_player_id']
            user_ids = dup['user_ids']
            emails = dup['emails']
            created_dates = dup['created_dates']
            last_logins = dup['last_logins']
            
            # Get player info
            player_info_query = """
                SELECT DISTINCT p.first_name, p.last_name, l.league_name, c.name as club_name, s.name as series_name
                FROM players p
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                WHERE p.tenniscores_player_id = %s
                LIMIT 1
            """
            
            player_info = execute_query_one(player_info_query, [player_id])
            
            user_details = []
            for i, (user_id, email, created_date, last_login) in enumerate(zip(user_ids, emails, created_dates, last_logins)):
                # Check user activity
                activity_query = """
                    SELECT 
                        COUNT(DISTINCT upa2.tenniscores_player_id) as total_associations,
                        u.first_name, u.last_name
                    FROM users u
                    LEFT JOIN user_player_associations upa2 ON u.id = upa2.user_id
                    WHERE u.id = %s
                    GROUP BY u.id, u.first_name, u.last_name
                """
                
                activity = execute_query_one(activity_query, [user_id])
                total_associations = activity['total_associations'] if activity else 0
                user_name = f"{activity['first_name']} {activity['last_name']}" if activity else "Unknown"
                
                user_details.append({
                    "user_id": user_id,
                    "email": email,
                    "name": user_name,
                    "created_at": str(created_date),
                    "last_login": str(last_login) if last_login else None,
                    "total_associations": total_associations,
                    "is_oldest": i == 0
                })
            
            # Determine fix strategy
            oldest_user = user_details[0]
            most_recent_login = None
            most_active_user = None
            
            for user in user_details:
                if user['last_login'] and (not most_recent_login or user['last_login'] > most_recent_login):
                    most_recent_login = user['last_login']
                    most_active_user = user
            
            # Decision logic
            if oldest_user['last_login']:
                keep_user = oldest_user
                reason = "Oldest user who has logged in"
            elif most_active_user:
                keep_user = most_active_user
                reason = "Most recent active user (oldest never logged in)"
            else:
                keep_user = oldest_user
                reason = "Oldest user (default - nobody has logged in)"
            
            remove_users = [u for u in user_details if u['user_id'] != keep_user['user_id']]
            
            duplicate_info = {
                "player_id": player_id,
                "player_info": {
                    "name": f"{player_info['first_name']} {player_info['last_name']}" if player_info else "Unknown",
                    "league": player_info['league_name'] if player_info else "Unknown",
                    "club": player_info['club_name'] if player_info else "Unknown",
                    "series": player_info['series_name'] if player_info else "Unknown"
                },
                "user_count": len(user_details),
                "users": user_details,
                "fix_strategy": {
                    "keep_user": keep_user,
                    "remove_users": remove_users,
                    "reason": reason
                }
            }
            
            results["duplicate_analysis"].append(duplicate_info)
        
        # Check if user wants to apply fixes
        apply_fixes = request.args.get('apply_fixes', 'false').lower() == 'true'
        
        if apply_fixes:
            results["phase"] = "applying_fixes"
            fixes_applied = 0
            
            for duplicate in results["duplicate_analysis"]:
                player_id = duplicate["player_id"]
                keep_user = duplicate["fix_strategy"]["keep_user"]
                remove_users = duplicate["fix_strategy"]["remove_users"]
                
                for user in remove_users:
                    try:
                        rows_deleted = execute_update(
                            "DELETE FROM user_player_associations WHERE user_id = %s AND tenniscores_player_id = %s",
                            [user['user_id'], player_id]
                        )
                        
                        if rows_deleted > 0:
                            fixes_applied += 1
                            
                    except Exception as fix_error:
                        results.setdefault("fix_errors", []).append({
                            "player_id": player_id,
                            "user_id": user['user_id'],
                            "error": str(fix_error)
                        })
            
            results["fixes_applied"] = True
            results["total_fixes_applied"] = fixes_applied
            
            # Verify no duplicates remain
            remaining_duplicates = execute_query("""
                SELECT 
                    upa.tenniscores_player_id,
                    COUNT(*) as user_count
                FROM user_player_associations upa
                GROUP BY upa.tenniscores_player_id
                HAVING COUNT(*) > 1
            """)
            
            results["remaining_duplicates"] = len(remaining_duplicates) if remaining_duplicates else 0
            results["success"] = results["remaining_duplicates"] == 0
        
        return jsonify({
            "debug": "fix_duplicate_player_associations_production",
            "results": results,
            "instructions": {
                "to_analyze_only": "Visit this endpoint normally",
                "to_apply_fixes": "Add ?apply_fixes=true to the URL to actually fix the duplicates",
                "warning": "Adding ?apply_fixes=true will make permanent changes to the database"
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/add-unique-player-constraint-production")
def add_unique_player_constraint_production():
    """
    Add unique constraint to prevent duplicate player associations in production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Check for existing violationsYeah
        violations_query = """
            SELECT 
                upa.tenniscores_player_id,
                COUNT(DISTINCT upa.user_id) as user_count,
                STRING_AGG(u.email, ', ') as user_emails
            FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            GROUP BY upa.tenniscores_player_id
            HAVING COUNT(DISTINCT upa.user_id) > 1
            ORDER BY user_count DESC
        """
        
        violations = execute_query(violations_query)
        results["checks"]["violations_found"] = len(violations) if violations else 0
        
        if violations:
            results["checks"]["violation_details"] = []
            for v in violations:
                results["checks"]["violation_details"].append({
                    "player_id": v['tenniscores_player_id'],
                    "user_count": v['user_count'],
                    "user_emails": v['user_emails']
                })
            
            results["error"] = f"Cannot add constraint - {len(violations)} violations found"
            results["recommendation"] = "Run /debug/fix-duplicate-player-associations-production?apply_fixes=true first"
            
            return jsonify({
                "debug": "add_unique_player_constraint_production",
                "results": results
            }), 400
        
        # Check for existing constraint
        constraint_query = """
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints 
            WHERE table_name = 'user_player_associations' 
            AND constraint_type = 'UNIQUE'
            AND constraint_name LIKE '%tenniscores_player_id%'
        """
        
        existing_constraints = execute_query(constraint_query)
        results["checks"]["existing_constraints"] = existing_constraints if existing_constraints else []
        
        if existing_constraints:
            results["message"] = "Unique constraint already exists"
            results["constraint_name"] = existing_constraints[0]["constraint_name"]
            return jsonify({
                "debug": "add_unique_player_constraint_production",
                "results": results
            })
        
        # Apply constraint
        apply_constraint = request.args.get('apply_constraint', 'false').lower() == 'true'
        
        if apply_constraint:
            results["phase"] = "applying_constraint"
            
            try:
                # Add the unique constraint
                constraint_sql = """
                    ALTER TABLE user_player_associations
                    ADD CONSTRAINT unique_tenniscores_player_id 
                    UNIQUE (tenniscores_player_id)
                """
                
                execute_update(constraint_sql)
                results["constraint_added"] = True
                
                # Add performance index
                index_sql = """
                    CREATE INDEX IF NOT EXISTS idx_upa_unique_player_check 
                    ON user_player_associations (tenniscores_player_id)
                """
                
                execute_update(index_sql)
                results["index_added"] = True
                
                # Verify constraint was added
                verify_query = """
                    SELECT constraint_name, constraint_type
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'user_player_associations' 
                    AND constraint_name = 'unique_tenniscores_player_id'
                """
                
                verification = execute_query_one(verify_query)
                results["verification"] = verification is not None
                results["constraint_name"] = verification["constraint_name"] if verification else None
                
                results["success"] = results["verification"]
                results["message"] = "Unique constraint successfully added" if results["success"] else "Constraint verification failed"
                
            except Exception as constraint_error:
                results["constraint_error"] = str(constraint_error)
                results["success"] = False
        else:
            results["message"] = "Constraint can be safely added"
            results["recommendation"] = "Add ?apply_constraint=true to apply the constraint"
        
        return jsonify({
            "debug": "add_unique_player_constraint_production",
            "results": results,
            "instructions": {
                "to_check_only": "Visit this endpoint normally",
                "to_apply_constraint": "Add ?apply_constraint=true to actually add the constraint",
                "warning": "Adding ?apply_constraint=true will make permanent schema changes"
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/cleanup-orphaned-duplicate-users-production")
def cleanup_orphaned_duplicate_users_production():
    """
    Clean up orphaned duplicate user accounts in production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "phase": "analysis",
            "orphaned_users": [],
            "cleanup_applied": False
        }
        
        # Find users with duplicate names but no associations and no login activity
        orphaned_query = """
            SELECT 
                u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login,
                COUNT(upa.user_id) as association_count
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.first_name = 'Victor' AND u.last_name = 'Forman'
            GROUP BY u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login
            HAVING COUNT(upa.user_id) = 0 AND u.last_login IS NULL
            ORDER BY u.created_at DESC
        """
        
        orphaned_users = execute_query(orphaned_query)
        
        if not orphaned_users:
            results["message"] = "No orphaned duplicate users found"
            return jsonify({
                "debug": "cleanup_orphaned_duplicate_users_production",
                "results": results
            })
        
        results["orphaned_count"] = len(orphaned_users)
        
        # Analyze each orphaned user
        for user in orphaned_users:
            user_info = {
                "user_id": user['id'],
                "email": user['email'],
                "name": f"{user['first_name']} {user['last_name']}",
                "created_at": str(user['created_at']),
                "last_login": str(user['last_login']) if user['last_login'] else None,
                "association_count": user['association_count'],
                "is_orphaned": user['association_count'] == 0 and user['last_login'] is None
            }
            
            # Additional safety checks
            created_date = user['created_at']
            if hasattr(created_date, 'date'):
                created_date = created_date.date()
            elif isinstance(created_date, str):
                created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).date()
            
            today = datetime.now().date()
            
            # Only consider for cleanup if:
            # 1. No associations
            # 2. Never logged in  
            # 3. Created recently (last 7 days) - safety measure
            days_old = (today - created_date).days
            user_info["days_old"] = days_old
            user_info["safe_to_delete"] = (
                user['association_count'] == 0 and 
                user['last_login'] is None and 
                days_old <= 7
            )
            
            results["orphaned_users"].append(user_info)
        
        # Check if user wants to apply cleanup
        apply_cleanup = request.args.get('apply_cleanup', 'false').lower() == 'true'
        
        if apply_cleanup:
            results["phase"] = "applying_cleanup"
            deleted_count = 0
            
            for user_info in results["orphaned_users"]:
                if user_info["safe_to_delete"]:
                    try:
                        # Double-check no associations exist (safety)
                        association_check = execute_query_one(
                            "SELECT COUNT(*) as count FROM user_player_associations WHERE user_id = %s",
                            [user_info["user_id"]]
                        )
                        
                        if association_check["count"] == 0:
                            # Delete the orphaned user
                            rows_deleted = execute_update(
                                "DELETE FROM users WHERE id = %s",
                                [user_info["user_id"]]
                            )
                            
                            if rows_deleted > 0:
                                deleted_count += 1
                                user_info["deleted"] = True
                            else:
                                user_info["deleted"] = False
                                user_info["delete_error"] = "No rows affected"
                        else:
                            user_info["deleted"] = False
                            user_info["delete_error"] = f"User has {association_check['count']} associations"
                            
                    except Exception as delete_error:
                        user_info["deleted"] = False
                        user_info["delete_error"] = str(delete_error)
                else:
                    user_info["deleted"] = False
                    user_info["delete_error"] = "Not marked as safe to delete"
            
            results["cleanup_applied"] = True
            results["users_deleted"] = deleted_count
            
            # Verify Victor Forman users remaining
            remaining_query = """
                SELECT id, email, first_name, last_name
                FROM users 
                WHERE first_name = 'Victor' AND last_name = 'Forman'
                ORDER BY created_at ASC
            """
            
            remaining_users = execute_query(remaining_query)
            results["remaining_victor_users"] = []
            
            for user in remaining_users:
                results["remaining_victor_users"].append({
                    "user_id": user['id'],
                    "email": user['email'],
                    "name": f"{user['first_name']} {user['last_name']}"
                })
            
            results["success"] = len(results["remaining_victor_users"]) == 1
        
        return jsonify({
            "debug": "cleanup_orphaned_duplicate_users_production",
            "results": results,
            "instructions": {
                "to_analyze_only": "Visit this endpoint normally",
                "to_apply_cleanup": "Add ?apply_cleanup=true to actually delete orphaned users",
                "warning": "Adding ?apply_cleanup=true will permanently delete user accounts",
                "safety_notes": [
                    "Only deletes users with no associations",
                    "Only deletes users who never logged in", 
                    "Only deletes users created within last 7 days",
                    "Double-checks safety before deletion"
                ]
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/delete-all-victor-forman-users-production")
def delete_all_victor_forman_users_production():
    """
    SIMPLE SOLUTION: Delete ALL Victor Forman users from production and start clean
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "phase": "analysis",
            "victor_users": [],
            "deletion_applied": False
        }
        
        # Find ALL Victor Forman users
        victor_query = """
            SELECT 
                u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login,
                COUNT(upa.user_id) as association_count
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.first_name = 'Victor' AND u.last_name = 'Forman'
            GROUP BY u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login
            ORDER BY u.created_at ASC
        """
        
        victor_users = execute_query(victor_query)
        
        if not victor_users:
            results["message"] = "No Victor Forman users found"
            return jsonify({
                "debug": "delete_all_victor_forman_users_production",
                "results": results
            })
        
        results["victor_users_found"] = len(victor_users)
        
        # Analyze each Victor user
        for user in victor_users:
            user_info = {
                "user_id": user['id'],
                "email": user['email'],
                "name": f"{user['first_name']} {user['last_name']}",
                "created_at": str(user['created_at']),
                "last_login": str(user['last_login']) if user['last_login'] else None,
                "association_count": user['association_count'],
                "has_logged_in": user['last_login'] is not None
            }
            
            # Get association details if any exist
            if user['association_count'] > 0:
                associations_query = """
                    SELECT 
                        upa.tenniscores_player_id,
                        p.first_name, p.last_name,
                        l.league_name, c.name as club_name
                    FROM user_player_associations upa
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    LEFT JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN clubs c ON p.club_id = c.id
                    WHERE upa.user_id = %s
                """
                
                associations = execute_query(associations_query, [user['id']])
                user_info["associations"] = []
                
                for assoc in (associations or []):
                    user_info["associations"].append({
                        "player_name": f"{assoc['first_name']} {assoc['last_name']}",
                        "player_id": assoc['tenniscores_player_id'],
                        "league": assoc['league_name'],
                        "club": assoc['club_name']
                    })
            
            results["victor_users"].append(user_info)
        
        # Check if user wants to apply deletion
        apply_deletion = request.args.get('delete_all', 'false').lower() == 'true'
        
        if apply_deletion:
            results["phase"] = "applying_deletion"
            deleted_count = 0
            deletion_details = []
            
            for user_info in results["victor_users"]:
                user_id = user_info["user_id"]
                user_email = user_info["email"]
                
                try:
                    # Step 1: Delete user associations first (if any)
                    associations_deleted = execute_update(
                        "DELETE FROM user_player_associations WHERE user_id = %s",
                        [user_id]
                    )
                    
                    # Step 2: Delete the user
                    user_deleted = execute_update(
                        "DELETE FROM users WHERE id = %s",
                        [user_id]
                    )
                    
                    if user_deleted > 0:
                        deleted_count += 1
                        deletion_details.append({
                            "user_id": user_id,
                            "email": user_email,
                            "associations_deleted": associations_deleted,
                            "user_deleted": True,
                            "status": "SUCCESS"
                        })
                    else:
                        deletion_details.append({
                            "user_id": user_id,
                            "email": user_email,
                            "associations_deleted": associations_deleted,
                            "user_deleted": False,
                            "status": "FAILED - User not found"
                        })
                        
                except Exception as delete_error:
                    deletion_details.append({
                        "user_id": user_id,
                        "email": user_email,
                        "user_deleted": False,
                        "status": f"ERROR: {str(delete_error)}"
                    })
            
            results["deletion_applied"] = True
            results["users_deleted"] = deleted_count
            results["deletion_details"] = deletion_details
            
            # Verify no Victor Forman users remain
            verification_query = """
                SELECT COUNT(*) as remaining_count
                FROM users 
                WHERE first_name = 'Victor' AND last_name = 'Forman'
            """
            
            verification = execute_query_one(verification_query)
            results["remaining_victor_users"] = verification["remaining_count"] if verification else "unknown"
            results["success"] = results["remaining_victor_users"] == 0
            
            if results["success"]:
                results["message"] = f"SUCCESS: All {deleted_count} Victor Forman users deleted. Database is clean."
            else:
                results["message"] = f"PARTIAL SUCCESS: {deleted_count} users deleted, but {results['remaining_victor_users']} still remain."
        
        return jsonify({
            "debug": "delete_all_victor_forman_users_production",
            "results": results,
            "instructions": {
                "to_analyze_only": "Visit this endpoint normally to see all Victor Forman users",
                "to_delete_all": "Add ?delete_all=true to permanently delete ALL Victor Forman users",
                "warning": "Adding ?delete_all=true will permanently delete ALL Victor Forman user accounts AND their associations",
                "simple_solution": "This endpoint takes the nuclear approach - deletes everything Victor Forman related and starts clean"
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/delete-remaining-victor-forman-production")
def delete_remaining_victor_forman_production():
    """
    Delete the remaining Victor Forman user (ID 49) by handling foreign key constraints properly
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "phase": "analysis",
            "target_user": None,
            "deletion_applied": False
        }
        
        # Find the remaining Victor Forman user
        victor_query = """
            SELECT 
                u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login,
                COUNT(upa.user_id) as association_count
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.first_name = 'Victor' AND u.last_name = 'Forman'
            GROUP BY u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login
            ORDER BY u.created_at ASC
        """
        
        victor_users = execute_query(victor_query)
        
        if not victor_users:
            results["message"] = "No Victor Forman users found - all already deleted"
            return jsonify({
                "debug": "delete_remaining_victor_forman_production",
                "results": results
            })
        
        if len(victor_users) > 1:
            results["error"] = f"Found {len(victor_users)} Victor Forman users - expected only 1 remaining"
            results["users_found"] = [{"id": u["id"], "email": u["email"]} for u in victor_users]
            return jsonify({
                "debug": "delete_remaining_victor_forman_production",
                "results": results
            }), 400
        
        # Get the target user (should be ID 49)
        target_user = victor_users[0]
        user_id = target_user['id']
        
        results["target_user"] = {
            "user_id": user_id,
            "email": target_user['email'],
            "name": f"{target_user['first_name']} {target_user['last_name']}",
            "created_at": str(target_user['created_at']),
            "last_login": str(target_user['last_login']) if target_user['last_login'] else None,
            "association_count": target_user['association_count']
        }
        
        # Check what will need to be deleted
        activity_count_query = "SELECT COUNT(*) as count FROM activity_log WHERE user_id = %s"
        activity_count = execute_query_one(activity_count_query, [user_id])
        results["target_user"]["activity_log_entries"] = activity_count["count"] if activity_count else 0
        
        polls_count_query = "SELECT COUNT(*) as count FROM polls WHERE created_by = %s"
        polls_count = execute_query_one(polls_count_query, [user_id])
        results["target_user"]["polls_created"] = polls_count["count"] if polls_count else 0
        
        # Get associations details
        if target_user['association_count'] > 0:
            associations_query = """
                SELECT 
                    upa.tenniscores_player_id,
                    p.first_name, p.last_name,
                    l.league_name, c.name as club_name
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id
                WHERE upa.user_id = %s
            """
            
            associations = execute_query(associations_query, [user_id])
            results["target_user"]["associations"] = []
            
            for assoc in (associations or []):
                results["target_user"]["associations"].append({
                    "player_name": f"{assoc['first_name']} {assoc['last_name']}",
                    "player_id": assoc['tenniscores_player_id'],
                    "league": assoc['league_name'],
                    "club": assoc['club_name']
                })
        
        # Check if user wants to apply deletion
        apply_deletion = request.args.get('delete_user_49', 'false').lower() == 'true'
        
        if apply_deletion:
            results["phase"] = "applying_deletion"
            deletion_steps = []
            
            try:
                # Step 1: Delete activity log entries
                activity_deleted = execute_update(
                    "DELETE FROM activity_log WHERE user_id = %s",
                    [user_id]
                )
                deletion_steps.append({
                    "step": 1,
                    "action": "Delete activity log entries",
                    "rows_affected": activity_deleted,
                    "status": "SUCCESS"
                })
                
                # Step 2: Delete polls created by user
                polls_deleted = execute_update(
                    "DELETE FROM polls WHERE created_by = %s",
                    [user_id]
                )
                deletion_steps.append({
                    "step": 2,
                    "action": "Delete polls created by user",
                    "rows_affected": polls_deleted,
                    "status": "SUCCESS"
                })
                
                # Step 3: Delete user associations
                associations_deleted = execute_update(
                    "DELETE FROM user_player_associations WHERE user_id = %s",
                    [user_id]
                )
                deletion_steps.append({
                    "step": 3,
                    "action": "Delete user player associations",
                    "rows_affected": associations_deleted,
                    "status": "SUCCESS"
                })
                
                # Step 4: Delete the user
                user_deleted = execute_update(
                    "DELETE FROM users WHERE id = %s",
                    [user_id]
                )
                deletion_steps.append({
                    "step": 4,
                    "action": "Delete user account",
                    "rows_affected": user_deleted,
                    "status": "SUCCESS" if user_deleted > 0 else "FAILED"
                })
                
                results["deletion_applied"] = True
                results["deletion_steps"] = deletion_steps
                results["success"] = user_deleted > 0
                
                # Verify no Victor Forman users remain
                verification_query = """
                    SELECT COUNT(*) as remaining_count
                    FROM users 
                    WHERE first_name = 'Victor' AND last_name = 'Forman'
                """
                
                verification = execute_query_one(verification_query)
                results["remaining_victor_users"] = verification["remaining_count"] if verification else "unknown"
                
                if results["success"] and results["remaining_victor_users"] == 0:
                    results["message"] = f"SUCCESS: User ID {user_id} (vforman@gmail.com) completely deleted. No Victor Forman users remain."
                else:
                    results["message"] = f"FAILED: User deletion failed or users still remain."
                    
            except Exception as delete_error:
                deletion_steps.append({
                    "step": "error",
                    "action": "Deletion process",
                    "error": str(delete_error),
                    "status": "ERROR"
                })
                results["deletion_steps"] = deletion_steps
                results["success"] = False
                results["message"] = f"ERROR during deletion: {str(delete_error)}"
        
        return jsonify({
            "debug": "delete_remaining_victor_forman_production",
            "results": results,
            "instructions": {
                "to_analyze_only": "Visit this endpoint normally to see what will be deleted",
                "to_delete_user_49": "Add ?delete_user_49=true to permanently delete the remaining Victor Forman user",
                "warning": "Adding ?delete_user_49=true will permanently delete User ID 49 and ALL associated data",
                "deletion_order": [
                    "1. Delete activity log entries (to satisfy foreign key constraints)",
                    "2. Delete polls created by user (to satisfy foreign key constraints)",
                    "3. Delete user player associations", 
                    "4. Delete user account",
                    "5. Verify no Victor Forman users remain"
                ]
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/investigate-ross-phone-production")
def investigate_ross_phone_production():
    """
    Detailed investigation of Ross's phone number in production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "phone_analysis": {}
        }
        
        # Ross's phone number
        ross_phone = "7732138911"
        
        # Test 1: Exact match
        exact_query = """
            SELECT id, email, first_name, last_name, phone_number, created_at, last_login
            FROM users
            WHERE phone_number = %s
        """
        exact_matches = execute_query(exact_query, [ross_phone])
        results["phone_analysis"]["exact_match"] = {
            "count": len(exact_matches),
            "users": [{"id": u["id"], "email": u["email"], "name": f"{u['first_name']} {u['last_name']}", "phone": u["phone_number"], "created": str(u["created_at"]), "last_login": str(u["last_login"]) if u["last_login"] else None} for u in exact_matches]
        }
        
        # Test 2: Phone number variations (like the password reset service)
        phone_variations = [
            ross_phone,                    # 7732138911
            f"+1{ross_phone}",            # +17732138911
            f"+{ross_phone}",             # +7732138911
            f"1{ross_phone}",             # 17732138911
        ]
        
        all_variation_matches = []
        for variation in phone_variations:
            variation_query = """
                SELECT id, email, first_name, last_name, phone_number, created_at, last_login
                FROM users
                WHERE phone_number = %s
            """
            matches = execute_query(variation_query, [variation])
            if matches:
                for match in matches:
                    if not any(m['id'] == match['id'] for m in all_variation_matches):
                        all_variation_matches.append(match)
        
        results["phone_analysis"]["variation_matches"] = {
            "count": len(all_variation_matches),
            "users": [{"id": u["id"], "email": u["email"], "name": f"{u['first_name']} {u['last_name']}", "phone": u["phone_number"], "created": str(u["created_at"]), "last_login": str(u["last_login"]) if u["last_login"] else None} for u in all_variation_matches]
        }
        
        # Test 3: Partial match (digits only)
        normalized_phone = ''.join(filter(str.isdigit, ross_phone))
        partial_query = """
            SELECT id, email, first_name, last_name, phone_number, created_at, last_login
            FROM users
            WHERE REPLACE(REPLACE(REPLACE(phone_number, '+', ''), '-', ''), ' ', '') LIKE %s
        """
        partial_phone = f"%{normalized_phone}%"
        partial_matches = execute_query(partial_query, [partial_phone])
        
        results["phone_analysis"]["partial_matches"] = {
            "count": len(partial_matches),
            "users": [{"id": u["id"], "email": u["email"], "name": f"{u['first_name']} {u['last_name']}", "phone": u["phone_number"], "created": str(u["created_at"]), "last_login": str(u["last_login"]) if u["last_login"] else None} for u in partial_matches]
        }
        
        # Test 4: Check all phone numbers in the database
        all_phones_query = """
            SELECT phone_number, COUNT(*) as count
            FROM users
            WHERE phone_number IS NOT NULL AND phone_number != ''
            GROUP BY phone_number
            ORDER BY count DESC, phone_number
        """
        all_phones = execute_query(all_phones_query)
        
        results["phone_analysis"]["all_phones_summary"] = {
            "total_unique_phones": len(all_phones),
            "phones_with_multiple_users": [p for p in all_phones if p["count"] > 1],
            "sample_phones": all_phones[:10]  # First 10 for reference
        }
        
        # Test 5: Check Ross's specific user record
        ross_user_query = """
            SELECT id, email, first_name, last_name, phone_number, created_at, last_login
            FROM users
            WHERE email = 'rossfreedman@gmail.com'
        """
        ross_user = execute_query_one(ross_user_query)
        
        if ross_user:
            results["phone_analysis"]["ross_user"] = {
                "id": ross_user["id"],
                "email": ross_user["email"],
                "name": f"{ross_user['first_name']} {ross_user['last_name']}",
                "phone": ross_user["phone_number"],
                "created": str(ross_user["created_at"]),
                "last_login": str(ross_user["last_login"]) if ross_user["last_login"] else None
            }
        
        return jsonify({
            "debug": "investigate_ross_phone_production",
            "results": results,
            "analysis": {
                "exact_matches_found": results["phone_analysis"]["exact_match"]["count"],
                "variation_matches_found": results["phone_analysis"]["variation_matches"]["count"],
                "partial_matches_found": results["phone_analysis"]["partial_matches"]["count"],
                "ross_user_found": "ross_user" in results["phone_analysis"],
                "likely_cause": "Phone number format differences or the password reset service is using different logic"
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/check-duplicate-phones-production")
def check_duplicate_phones_production():
    """
    Check for duplicate phone numbers in production database
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "duplicate_analysis": {}
        }
        
        # Find all phone numbers that appear more than once
        duplicate_phones_query = """
            SELECT 
                phone_number,
                COUNT(*) as user_count,
                ARRAY_AGG(id) as user_ids,
                ARRAY_AGG(email) as emails,
                ARRAY_AGG(first_name) as first_names,
                ARRAY_AGG(last_name) as last_names,
                ARRAY_AGG(created_at) as created_dates,
                ARRAY_AGG(last_login) as last_logins
            FROM users
            WHERE phone_number IS NOT NULL AND phone_number != ''
            GROUP BY phone_number
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, phone_number
        """
        
        duplicate_phones = execute_query(duplicate_phones_query)
        
        if not duplicate_phones:
            results["message"] = "No duplicate phone numbers found"
            return jsonify({
                "debug": "check_duplicate_phones_production",
                "results": results
            })
        
        results["total_duplicate_phones"] = len(duplicate_phones)
        
        # Analyze each duplicate phone number
        for dup in duplicate_phones:
            phone = dup['phone_number']
            user_count = dup['user_count']
            user_ids = dup['user_ids']
            emails = dup['emails']
            first_names = dup['first_names']
            last_names = dup['last_names']
            created_dates = dup['created_dates']
            last_logins = dup['last_logins']
            
            # Create user details for each duplicate
            users = []
            for i in range(user_count):
                user_info = {
                    "user_id": user_ids[i],
                    "email": emails[i],
                    "name": f"{first_names[i]} {last_names[i]}",
                    "created_at": str(created_dates[i]) if created_dates[i] else None,
                    "last_login": str(last_logins[i]) if last_logins[i] else None,
                    "has_logged_in": last_logins[i] is not None
                }
                users.append(user_info)
            
            # Sort users by activity (most recent first)
            users.sort(key=lambda x: (x['last_login'] or '1900-01-01', x['created_at'] or '1900-01-01'), reverse=True)
            
            # Determine which user would be selected for password reset
            selected_user = users[0] if users else None
            
            duplicate_info = {
                "phone_number": phone,
                "user_count": user_count,
                "users": users,
                "selected_for_password_reset": selected_user,
                "selection_reason": "Most recently active user"
            }
            
            results["duplicate_analysis"][phone] = duplicate_info
        
        # Special focus on Ross's phone number
        ross_phone = "7732138911"
        if ross_phone in results["duplicate_analysis"]:
            results["ross_phone_analysis"] = results["duplicate_analysis"][ross_phone]
        
        return jsonify({
            "debug": "check_duplicate_phones_production",
            "results": results,
            "summary": {
                "total_duplicate_phones": len(duplicate_phones),
                "ross_phone_has_duplicates": ross_phone in results["duplicate_analysis"],
                "recommendation": "Consider cleaning up duplicate accounts or implementing better phone number validation"
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/debug/delete-user-complete-production")
def delete_user_complete_production():
    """
    Delete any user completely from production by handling all foreign key constraints
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env != "production":
        return jsonify({
            "error": "This endpoint only works on production",
            "railway_env": railway_env
        }), 403
    
    try:
        from database_utils import execute_query, execute_query_one, execute_update
        
        # Get user identifier from query parameters
        user_id = request.args.get('user_id')
        user_email = request.args.get('user_email')
        
        if not user_id and not user_email:
            return jsonify({
                "error": "Must provide either user_id or user_email parameter",
                "examples": [
                    "?user_id=936",
                    "?user_email=victorformantest@gmail.com",
                    "?user_id=936&delete_user=true (to actually delete)"
                ]
            }), 400
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "phase": "analysis",
            "target_user": None,
            "deletion_applied": False
        }
        
        # Find the target user
        if user_id:
            user_query = """
                SELECT 
                    u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login,
                    COUNT(upa.user_id) as association_count
                FROM users u
                LEFT JOIN user_player_associations upa ON u.id = upa.user_id
                WHERE u.id = %s
                GROUP BY u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login
            """
            user_param = [int(user_id)]
        else:
            user_query = """
                SELECT 
                    u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login,
                    COUNT(upa.user_id) as association_count
                FROM users u
                LEFT JOIN user_player_associations upa ON u.id = upa.user_id
                WHERE u.email = %s
                GROUP BY u.id, u.email, u.first_name, u.last_name, u.created_at, u.last_login
            """
            user_param = [user_email]
        
        target_users = execute_query(user_query, user_param)
        
        if not target_users:
            results["message"] = f"No user found with {'ID ' + user_id if user_id else 'email ' + user_email}"
            return jsonify({
                "debug": "delete_user_complete_production",
                "results": results
            }), 404
        
        if len(target_users) > 1:
            results["error"] = f"Found {len(target_users)} users - query should return exactly 1"
            return jsonify({
                "debug": "delete_user_complete_production", 
                "results": results
            }), 400
        
        # Get the target user
        target_user = target_users[0]
        target_user_id = target_user['id']
        
        results["target_user"] = {
            "user_id": target_user_id,
            "email": target_user['email'],
            "name": f"{target_user['first_name']} {target_user['last_name']}",
            "created_at": str(target_user['created_at']),
            "last_login": str(target_user['last_login']) if target_user['last_login'] else None,
            "association_count": target_user['association_count']
        }
        
        # Check all foreign key constraint tables
        constraints_to_check = [
            ("activity_log", "user_id", "activity log entries"),
            ("polls", "created_by", "polls created"),
            ("user_player_associations", "user_id", "player associations")
        ]
        
        for table, column, description in constraints_to_check:
            count_query = f"SELECT COUNT(*) as count FROM {table} WHERE {column} = %s"
            try:
                count_result = execute_query_one(count_query, [target_user_id])
                results["target_user"][f"{table}_count"] = count_result["count"] if count_result else 0
            except Exception as e:
                results["target_user"][f"{table}_count"] = f"Error: {str(e)}"
        
        # Get association details if any exist
        if target_user['association_count'] > 0:
            associations_query = """
                SELECT 
                    upa.tenniscores_player_id,
                    p.first_name, p.last_name,
                    l.league_name, c.name as club_name, s.name as series_name
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                LEFT JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                WHERE upa.user_id = %s
            """
            
            associations = execute_query(associations_query, [target_user_id])
            results["target_user"]["associations"] = []
            
            for assoc in (associations or []):
                results["target_user"]["associations"].append({
                    "player_name": f"{assoc['first_name']} {assoc['last_name']}",
                    "player_id": assoc['tenniscores_player_id'],
                    "league": assoc['league_name'],
                    "club": assoc['club_name'],
                    "series": assoc['series_name']
                })
        
        # Check if user wants to apply deletion
        apply_deletion = request.args.get('delete_user', 'false').lower() == 'true'
        
        if apply_deletion:
            results["phase"] = "applying_deletion"
            deletion_steps = []
            
            try:
                # Step 1: Delete activity log entries
                activity_deleted = execute_update(
                    "DELETE FROM activity_log WHERE user_id = %s",
                    [target_user_id]
                )
                deletion_steps.append({
                    "step": 1,
                    "action": "Delete activity log entries",
                    "rows_affected": activity_deleted,
                    "status": "SUCCESS"
                })
                
                # Step 2: Delete polls created by user
                polls_deleted = execute_update(
                    "DELETE FROM polls WHERE created_by = %s",
                    [target_user_id]
                )
                deletion_steps.append({
                    "step": 2,
                    "action": "Delete polls created by user",
                    "rows_affected": polls_deleted,
                    "status": "SUCCESS"
                })
                
                # Step 3: Delete user associations
                associations_deleted = execute_update(
                    "DELETE FROM user_player_associations WHERE user_id = %s",
                    [target_user_id]
                )
                deletion_steps.append({
                    "step": 3,
                    "action": "Delete user player associations",
                    "rows_affected": associations_deleted,
                    "status": "SUCCESS"
                })
                
                # Step 4: Delete the user
                user_deleted = execute_update(
                    "DELETE FROM users WHERE id = %s",
                    [target_user_id]
                )
                deletion_steps.append({
                    "step": 4,
                    "action": "Delete user account",
                    "rows_affected": user_deleted,
                    "status": "SUCCESS" if user_deleted > 0 else "FAILED"
                })
                
                results["deletion_applied"] = True
                results["deletion_steps"] = deletion_steps
                results["success"] = user_deleted > 0
                
                if results["success"]:
                    results["message"] = f"SUCCESS: User ID {target_user_id} ({target_user['email']}) completely deleted."
                else:
                    results["message"] = f"FAILED: User deletion failed."
                    
            except Exception as delete_error:
                deletion_steps.append({
                    "step": "error",
                    "action": "Deletion process",
                    "error": str(delete_error),
                    "status": "ERROR"
                })
                results["deletion_steps"] = deletion_steps
                results["success"] = False
                results["message"] = f"ERROR during deletion: {str(delete_error)}"
        
        return jsonify({
            "debug": "delete_user_complete_production",
            "results": results,
            "instructions": {
                "to_analyze_only": "Visit this endpoint with user_id or user_email parameter to see what will be deleted",
                "to_delete_user": "Add &delete_user=true to permanently delete the user and ALL associated data",
                "warning": "Adding &delete_user=true will permanently delete the user account and ALL associated data",
                "examples": [
                    "?user_id=936 (analyze user ID 936)",
                    "?user_email=victorformantest@gmail.com (analyze by email)",
                    "?user_id=936&delete_user=true (delete user ID 936)",
                    "?user_email=victorformantest@gmail.com&delete_user=true (delete by email)"
                ],
                "deletion_order": [
                    "1. Delete activity log entries (foreign key constraint)",
                    "2. Delete polls created by user (foreign key constraint)",
                    "3. Delete user player associations",
                    "4. Delete user account",
                    "5. Verify deletion successful"
                ]
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500


@app.route("/api/switch-database", methods=["POST"])
def switch_database():
    """Switch between main and test databases"""
    try:
        from flask import request, jsonify
        import subprocess
        import os
        
        # Only allow in local development
        if os.getenv("RAILWAY_ENVIRONMENT") is not None or os.path.exists('/app'):
            return jsonify({
                'success': False,
                'error': 'Database switching only available in local development'
            }), 403
        
        data = request.get_json()
        new_mode = data.get('database_mode')
        
        if new_mode not in ['main', 'test']:
            return jsonify({
                'success': False,
                'error': 'Invalid database mode. Must be "main" or "test"'
            }), 400
        
        # Get current mode
        from database_config import get_database_mode
        current_mode = get_database_mode()
        
        if current_mode == new_mode:
            return jsonify({
                'success': False,
                'error': f'Already using {new_mode} database'
            }), 400
        
        # Set the new environment variable
        os.environ['RALLY_DATABASE'] = new_mode
        
        return jsonify({
            'success': True,
            'message': f'Switched from {current_mode} to {new_mode} database',
            'new_mode': new_mode
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to switch database: {str(e)}'
        }), 500


@app.route("/debug/fix-staging-schema")
def fix_staging_schema_debug():
    """Debug route to fix staging schema issues"""
    try:
        # Import the fix function
        from scripts.fix_staging_schema_internal import fix_staging_schema_internal
        
        # Run the fix
        success = fix_staging_schema_internal()
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Staging schema fixes applied successfully",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to apply staging schema fixes",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error applying schema fixes: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


# ==========================================
# SERVER STARTUP
# ==========================================

if __name__ == "__main__":
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get("PORT", 8080))

    # Determine if we're in development or production
    is_development = os.environ.get("FLASK_ENV") == "development"

    try:
        if is_development:
            print(f"🏓 Starting Rally server locally on port {port}")
            app.run(host="0.0.0.0", port=port, debug=True)
        else:
            print(f"🏓 Starting Rally server in production mode on port {port}")
            app.run(host="0.0.0.0", port=port, debug=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print("Address already in use")
            print(
                f"Port {port} is in use by another program. Either identify and stop that program, or start the server with a different port."
            )
        else:
            print(f"Failed to start server: {e}")
        sys.exit(1)

import os
print("DEBUG: PORT ENV =", os.environ.get("PORT"))

@app.route("/admin/run-saved-lineups-migration")
def run_saved_lineups_migration():
    """
    Web endpoint to run saved lineups migration on production
    """
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    
    if railway_env not in ["staging", "production"]:
        return jsonify({
            "error": "This migration endpoint only works on staging or production",
            "railway_env": railway_env,
            "instructions": "Visit this URL on staging or production environment to run the migration"
        }), 403
    
    try:
        from database_utils import execute_query_one, execute_update
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "migration_steps": []
        }
        
        # Step 1: Check if saved_lineups table already exists
        results["migration_steps"].append("🔍 Checking if saved_lineups table exists...")
        
        try:
            table_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'saved_lineups'
                )
            """)
            
            if table_check and table_check["exists"]:
                results["migration_steps"].append("✅ saved_lineups table already exists")
                results["table_exists"] = True
                return jsonify({
                    "status": "success",
                    "message": "saved_lineups table already exists - no migration needed",
                    "results": results
                })
            else:
                results["migration_steps"].append("📋 saved_lineups table needs to be created")
                results["table_exists"] = False
                
        except Exception as e:
            results["migration_steps"].append(f"⚠️ Could not check table: {str(e)}")
            results["table_exists"] = False
        
        # Step 2: Also check for lineup_escrow table (part of same migration)
        results["migration_steps"].append("🔍 Checking if lineup_escrow table exists...")
        
        try:
            escrow_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'lineup_escrow'
                )
            """)
            
            escrow_exists = escrow_check and escrow_check["exists"]
            results["migration_steps"].append(f"📋 lineup_escrow table exists: {escrow_exists}")
            results["escrow_table_exists"] = escrow_exists
                
        except Exception as e:
            results["migration_steps"].append(f"⚠️ Could not check lineup_escrow: {str(e)}")
            results["escrow_table_exists"] = False
        
        # Step 3: Run the migration
        results["migration_steps"].append("🔄 Running saved lineups migration...")
        
        migration_sql = """
        -- Migration: Add Lineup Escrow and Saved Lineups Tables
        -- Date: 2025-01-15 12:00:00
        -- Description: Adds tables for lineup escrow functionality and saved lineups

        -- Create lineup_escrow table
        CREATE TABLE IF NOT EXISTS lineup_escrow (
            id SERIAL PRIMARY KEY,
            escrow_token VARCHAR(255) NOT NULL UNIQUE,
            initiator_user_id INTEGER NOT NULL REFERENCES users(id),
            recipient_name VARCHAR(255) NOT NULL,
            recipient_contact VARCHAR(255) NOT NULL,
            contact_type VARCHAR(20) NOT NULL,
            initiator_lineup TEXT NOT NULL,
            recipient_lineup TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            initiator_submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            recipient_submitted_at TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE,
            subject VARCHAR(255),
            message_body TEXT NOT NULL,
            initiator_notified BOOLEAN DEFAULT FALSE,
            recipient_notified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Create lineup_escrow_views table
        CREATE TABLE IF NOT EXISTS lineup_escrow_views (
            id SERIAL PRIMARY KEY,
            escrow_id INTEGER NOT NULL REFERENCES lineup_escrow(id),
            viewer_user_id INTEGER REFERENCES users(id),
            viewer_contact VARCHAR(255) NOT NULL,
            viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            ip_address VARCHAR(45)
        );

        -- Create saved_lineups table
        CREATE TABLE IF NOT EXISTS saved_lineups (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            team_id INTEGER NOT NULL REFERENCES teams(id),
            lineup_name VARCHAR(255) NOT NULL,
            lineup_data TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id, team_id, lineup_name)
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_lineup_escrow_token ON lineup_escrow(escrow_token);
        CREATE INDEX IF NOT EXISTS idx_lineup_escrow_status ON lineup_escrow(status);
        CREATE INDEX IF NOT EXISTS idx_lineup_escrow_initiator ON lineup_escrow(initiator_user_id);
        CREATE INDEX IF NOT EXISTS idx_lineup_escrow_views_escrow_id ON lineup_escrow_views(escrow_id);
        CREATE INDEX IF NOT EXISTS idx_saved_lineups_user_team ON saved_lineups(user_id, team_id);
        CREATE INDEX IF NOT EXISTS idx_saved_lineups_active ON saved_lineups(is_active);

        -- Add comments for documentation
        COMMENT ON TABLE lineup_escrow IS 'Stores lineup escrow sessions for fair lineup disclosure between captains';
        COMMENT ON TABLE lineup_escrow_views IS 'Tracks who has viewed lineup escrow results';
        COMMENT ON TABLE saved_lineups IS 'Stores saved lineup configurations for users and teams';
        """
        
        execute_update(migration_sql)
        results["migration_steps"].append("✅ Migration SQL executed successfully")
        
        # Step 4: Verify the migration
        results["migration_steps"].append("🧪 Verifying migration...")
        
        # Check saved_lineups table
        verify_saved_lineups = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'saved_lineups'
            )
        """)
        
        saved_lineups_exists = verify_saved_lineups and verify_saved_lineups["exists"]
        results["migration_steps"].append(f"📋 saved_lineups table exists: {saved_lineups_exists}")
        
        # Check lineup_escrow table
        verify_escrow = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'lineup_escrow'
            )
        """)
        
        escrow_exists_after = verify_escrow and verify_escrow["exists"]
        results["migration_steps"].append(f"📋 lineup_escrow table exists: {escrow_exists_after}")
        
        # Check lineup_escrow_views table
        verify_escrow_views = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'lineup_escrow_views'
            )
        """)
        
        escrow_views_exists = verify_escrow_views and verify_escrow_views["exists"]
        results["migration_steps"].append(f"📋 lineup_escrow_views table exists: {escrow_views_exists}")
        
        results["verification"] = {
            "saved_lineups_exists": saved_lineups_exists,
            "lineup_escrow_exists": escrow_exists_after,
            "lineup_escrow_views_exists": escrow_views_exists
        }
        
        if all(results["verification"].values()):
            results["migration_steps"].append("✅ Migration verification successful")
            results["success"] = True
            
            return jsonify({
                "status": "success",
                "message": "Saved lineups migration completed successfully!",
                "results": results,
                "next_steps": [
                    "✅ Migration complete",
                    "👉 Test the lineup page: https://www.lovetorally.com/mobile/lineup",
                    "🎯 The 'Saved Lineups' section should now work without errors"
                ]
            })
        else:
            results["migration_steps"].append("❌ Migration verification failed")
            results["success"] = False
            
            return jsonify({
                "status": "error",
                "message": "Migration ran but verification failed",
                "results": results
            }), 500
        
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "message": "Migration endpoint error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "railway_env": railway_env
        }), 500
