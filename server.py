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


# ==========================================
# ERROR HANDLERS
# ==========================================


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


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


@app.route("/admin/run-alembic-migration")
def run_alembic_migration():
    """
    Web endpoint to run Alembic migration on production
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
        
        results = {
            "railway_env": railway_env,
            "timestamp": datetime.now().isoformat(),
            "migration_steps": []
        }
        
        # Step 1: Check current migration status
        results["migration_steps"].append("🔍 Checking current Alembic revision...")
        
        try:
            current_result = subprocess.run(
                ["python", "-m", "alembic", "current"], 
                capture_output=True, 
                text=True, 
                cwd="/app",
                timeout=30
            )
            
            if current_result.returncode == 0:
                current_output = current_result.stdout.strip()
                results["current_revision"] = current_output
                results["migration_steps"].append(f"📊 Current revision: {current_output}")
                
                # Check if already at the latest revision
                if "c28892a55e1d" in current_output:
                    results["migration_steps"].append("✅ Already at latest revision - checking tables...")
                    
                    # Verify tables exist
                    from database_utils import execute_query_one
                    
                    saved_lineups_check = execute_query_one("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'saved_lineups'
                        )
                    """)
                    
                    session_refresh_check = execute_query_one("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'user_session_refresh_signals'
                        )
                    """)
                    
                    if saved_lineups_check and saved_lineups_check["exists"] and session_refresh_check and session_refresh_check["exists"]:
                        return jsonify({
                            "status": "success",
                            "message": "Migration already complete - all tables exist",
                            "results": results,
                            "next_step": "Test https://www.lovetorally.com/mobile/lineup"
                        })
                        
            else:
                results["migration_steps"].append(f"⚠️ Could not check current revision: {current_result.stderr}")
                
        except Exception as e:
            results["migration_steps"].append(f"❌ Error checking revision: {str(e)}")
        
        # Step 2: Run the migration
        results["migration_steps"].append("🔄 Running Alembic upgrade to head...")
        
        upgrade_result = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"], 
            capture_output=True, 
            text=True,
            cwd="/app",
            timeout=120
        )
        
        if upgrade_result.returncode == 0:
            results["migration_steps"].append("✅ Alembic upgrade completed!")
            results["upgrade_output"] = upgrade_result.stdout
            results["migration_steps"].append("📋 Migration output captured")
            
            # Verify the migration worked
            results["migration_steps"].append("🧪 Verifying tables were created...")
            
            from database_utils import execute_query_one
            
            # Check saved_lineups table
            saved_lineups_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'saved_lineups'
                )
            """)
            
            saved_lineups_exists = saved_lineups_check and saved_lineups_check["exists"]
            results["saved_lineups_table_exists"] = saved_lineups_exists
            results["migration_steps"].append(f"📋 saved_lineups table exists: {saved_lineups_exists}")
            
            # Check user_session_refresh_signals table
            session_refresh_check = execute_query_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_session_refresh_signals'
                )
            """)
            
            session_refresh_exists = session_refresh_check and session_refresh_check["exists"]
            results["session_refresh_table_exists"] = session_refresh_exists
            results["migration_steps"].append(f"📋 user_session_refresh_signals table exists: {session_refresh_exists}")
            
            # Final verification
            if saved_lineups_exists and session_refresh_exists:
                results["migration_steps"].append("🎉 Migration successful - all tables created!")
                
                # Check final revision
                final_result = subprocess.run(
                    ["python", "-m", "alembic", "current"], 
                    capture_output=True, 
                    text=True,
                    cwd="/app",
                    timeout=30
                )
                
                if final_result.returncode == 0:
                    final_revision = final_result.stdout.strip()
                    results["final_revision"] = final_revision
                    results["migration_steps"].append(f"✅ Final revision: {final_revision}")
                
                return jsonify({
                    "status": "success",
                    "message": "Alembic migration completed successfully!",
                    "results": results,
                    "next_steps": [
                        "✅ Migration complete",
                        "👉 Test saved lineups: https://www.lovetorally.com/mobile/lineup",
                        "🎯 Both saved_lineups and session_refresh errors should be fixed"
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
