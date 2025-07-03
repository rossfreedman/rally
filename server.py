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


@app.route("/index.html")
def redirect_index_html():
    """Redirect index.html to mobile"""
    return redirect("/mobile")


@app.route("/contact-sub")
@login_required
def serve_contact_sub():
    """Serve the modern contact sub page"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(session["user"]["email"], "page_visit", page="contact_sub")
    return render_template("mobile/contact_sub.html", session_data=session_data)


@app.route("/pti_vs_opponents_analysis.html")
@login_required
def serve_pti_analysis():
    """Serve the PTI vs Opponents Analysis page"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(
        session["user"]["email"], "page_visit", page="pti_vs_opponents_analysis"
    )
    return render_template(
        "analysis/pti_vs_opponents_analysis.html", session_data=session_data
    )


@app.route("/schedule")
@login_required
def serve_schedule_page():
    """Serve the schedule page"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(session["user"]["email"], "page_visit", page="schedule")
    return render_template("mobile/view_schedule.html", session_data=session_data)


@app.route("/create-team")
@login_required
def serve_create_team_page():
    """Serve the Create Team page using mobile layout"""
    session_data = {"user": session["user"], "authenticated": True}
    log_user_activity(session["user"]["email"], "page_visit", page="create_team")
    
    return render_template("mobile/create_team.html", session_data=session_data)


@app.route("/<path:path>")
@login_required
def serve_static(path):
    """Serve static files with authentication"""
    public_files = {
        "login.html",
        "signup.html",
        "forgot-password.html",
        "rally-logo.png",
        "rally-icon.png",
        "favicon.ico",
        "login.css",
        "signup.css",
    }

    def is_public_file(file_path):
        filename = os.path.basename(file_path)
        return (
            filename in public_files
            or file_path.startswith("css/")
            or file_path.startswith("js/")
            or file_path.startswith("images/")
        )

    if is_public_file(path):
        return send_from_directory(".", path)

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


# ==========================================
# ERROR HANDLERS
# ==========================================


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


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
