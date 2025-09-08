"""
Admin routes blueprint - handles all administration functionality
This module contains routes for user management, system administration, and user activity tracking.
"""

import json
import os
import queue
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime
from functools import wraps

# Optional system monitoring imports
try:
    import psutil
except ImportError:
    psutil = None

from flask import (
    Blueprint,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    stream_template,
    url_for,
)

try:
    import select
except ImportError:
    select = None  # Windows doesn't have select module for pipes
import traceback

from app.services.admin_service import (
    delete_user_by_email,
    get_all_series_with_stats,
    get_all_users,
    get_all_users_with_player_contexts,
    get_user_activity_logs,
    is_user_admin,
    log_admin_action,
    update_club_name,
    update_series_name,
    update_user_info,
    get_detailed_logging_notifications_setting,
    set_detailed_logging_notifications_setting,
    get_lineup_escrow_analytics
)

# ETL service imports temporarily disabled
# from app.services.etl_service import get_etl_status, clear_etl_processes
from app.services.auth_service_refactored import fix_team_assignments_for_existing_users
from app.services.dashboard_service import (
    get_activity_heatmap_data,
    get_activity_stats,
    get_filter_options,
    get_player_activity_history,
    get_recent_activities,
    get_team_activity_history,
    get_top_active_players,
    log_activity,
    log_page_visit,
    log_user_action,
    format_page_name,
)
from database_utils import execute_query, execute_query_one, execute_update
from utils.auth import login_required
from utils.logging import log_user_activity

# Create admin blueprint
admin_bp = Blueprint("admin", __name__)

# Global variables for process management
active_processes = {"scraping": None, "importing": None}


def admin_required(f):
    """Decorator to require admin privileges"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if not session.get("user"):
            return jsonify({"error": "Authentication required"}), 401
        
        # Check if currently impersonating - if so, check original admin session
        if session.get("impersonation_active"):
            original_admin = session.get("original_admin_session", {})
            if not original_admin.get("is_admin"):
                return jsonify({"error": "Admin access required"}), 403
        else:
            # Normal check - current user must be admin
            if not session["user"].get("is_admin"):
                return jsonify({"error": "Admin access required"}), 403
        
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route("/admin")
@login_required
@admin_required
def serve_admin():
    """Serve the admin dashboard"""
    print(f"=== SERVE_ADMIN FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"User in session: {session.get('user', 'No user')}")

    log_user_activity(
        session["user"]["email"], 
        "page_visit", 
        page="admin",
        first_name=session["user"].get("first_name"),
        last_name=session["user"].get("last_name")
    )

    # Always use the mobile admin template since it's responsive and works on all devices
    print("Rendering mobile admin template (responsive design)")
    return render_template("mobile/admin.html", session_data={"user": session["user"]})


@admin_bp.route("/admin/cockpit")
@login_required
@admin_required
def serve_admin_cockpit():
    """Serve the admin cockpit dashboard - desktop only real-time monitoring"""
    print(f"=== SERVE_ADMIN_COCKPIT FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"User in session: {session.get('user', 'No user')}")

    # Check if currently impersonating
    is_impersonating = session.get("impersonation_active", False)
    
    # Log cockpit access using comprehensive logging
    log_page_visit(
        user_email=session["user"]["email"],
        page="admin_cockpit",
        user_id=session["user"].get("id"),
        player_id=session["user"].get("player_id"),
        details=f"Admin accessed real-time cockpit dashboard",
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        is_impersonating=is_impersonating,
    )

    return render_template("cockpit.html", session_data={"user": session["user"]})


@admin_bp.route("/mobile/mcockpit")
@login_required
@admin_required
def serve_mobile_cockpit():
    """Serve the mobile cockpit dashboard - mobile-optimized real-time monitoring"""
    print(f"=== SERVE_MOBILE_COCKPIT FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"User in session: {session.get('user', 'No user')}")

    # Check if currently impersonating
    is_impersonating = session.get("impersonation_active", False)
    
    # Log mobile cockpit access using comprehensive logging
    log_page_visit(
        user_email=session["user"]["email"],
        page="mobile_mcockpit",
        user_id=session["user"].get("id"),
        player_id=session["user"].get("player_id"),
        details=f"Admin accessed mobile cockpit dashboard",
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        is_impersonating=is_impersonating,
    )

    return render_template("mobile/mcockpit.html", session_data={"user": session["user"]})


@admin_bp.route("/admin/users")
@login_required
@admin_required
def serve_admin_users():
    """Serve the admin users management page"""
    print(f"=== SERVE_ADMIN_USERS FUNCTION CALLED ===")

    log_user_activity(session["user"]["email"], "page_visit", page="admin_users")

    # Always use the mobile admin template since it's responsive and works on all devices
    return render_template(
        "mobile/admin_users.html", session_data={"user": session["user"]}
    )


@admin_bp.route("/admin/leagues")
@login_required
@admin_required
def serve_admin_leagues():
    """Serve the admin leagues management page"""
    log_user_activity(session["user"]["email"], "page_visit", page="admin_leagues")

    return render_template(
        "mobile/admin_leagues.html", session_data={"user": session["user"]}
    )


@admin_bp.route("/admin/clubs")
@login_required
@admin_required
def serve_admin_clubs():
    """Serve the admin clubs management page"""
    log_user_activity(session["user"]["email"], "page_visit", page="admin_clubs")

    return render_template(
        "mobile/admin_clubs.html", session_data={"user": session["user"]}
    )


@admin_bp.route("/admin/series")
@login_required
@admin_required
def serve_admin_series():
    """Serve the admin series management page"""
    log_user_activity(session["user"]["email"], "page_visit", page="admin_series")

    return render_template(
        "mobile/admin_series.html", session_data={"user": session["user"]}
    )


@admin_bp.route("/admin/etl")
@login_required
@admin_required
def serve_admin_etl():
    """Serve the admin ETL management page"""
    log_user_activity(session["user"]["email"], "page_visit", page="admin_etl")

    return render_template(
        "mobile/admin_etl.html", session_data={"user": session["user"]}
    )


@admin_bp.route("/admin/user-activity")
@login_required
@admin_required
def serve_admin_user_activity():
    """Serve the admin user activity page"""
    # Get email from query parameter
    email = request.args.get('email')
    
    user_data = None
    if email:
        try:
            # Get enhanced user data using the same service as the API
            response_data = get_user_activity_logs(email)
            user_data = response_data.get('user')
        except Exception as e:
            print(f"Error fetching user data for {email}: {str(e)}")
            user_data = None
    
    log_user_activity(
        session["user"]["email"], 
        "page_visit", 
        page="admin_user_activity",
        first_name=session["user"].get("first_name"),
        last_name=session["user"].get("last_name")
    )
    
    return render_template(
        "mobile/admin_user_activity.html", 
        session_data={"user": session["user"]},
        user=user_data
    )


@admin_bp.route("/admin/dashboard")
@login_required
@admin_required
def serve_admin_dashboard():
    """Serve the admin activity monitoring dashboard"""
    # Check if currently impersonating
    is_impersonating = session.get("impersonation_active", False)
    
    # Log dashboard access using comprehensive logging
    log_page_visit(
        user_email=session["user"]["email"],
        page="admin_dashboard",
        user_id=session["user"].get("id"),
        player_id=session["user"].get("player_id"),  # Get from session if available
        details=f"Admin accessed activity monitoring dashboard",
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        is_impersonating=is_impersonating,
    )

    return render_template(
        "mobile/admin_dashboard.html", session_data={"user": session["user"]}
    )


@admin_bp.route("/admin/test-notifications")
@login_required
@admin_required
def serve_admin_test_notifications():
    """Serve the admin test notifications page"""
    log_user_activity(session["user"]["email"], "page_visit", page="admin_test_notifications")
    
    return render_template(
        "mobile/admin_test_notifications.html", session_data={"user": session["user"]}
    )


@admin_bp.route("/mobile/team-notifications")
@login_required
def serve_team_notifications():
    """Serve the team notifications page for captains"""
    log_user_activity(session["user"]["email"], "page_visit", page="team_notifications")
    
    return render_template(
        "mobile/team_notifications.html", session_data={"user": session["user"]}
    )


@admin_bp.route("/admin/pre-register-user")
@login_required
@admin_required
def serve_pre_register_user():
    """Serve the admin pre-register user page"""
    log_user_activity(session["user"]["email"], "page_visit", page="admin_pre_register_user")
    
    return render_template(
        "admin/pre_register_user.html", session_data={"user": session["user"]}
    )


# ==========================================
# ETL API ENDPOINTS
# ==========================================


@admin_bp.route("/api/admin/etl/status")
@login_required
@admin_required
def get_etl_status():
    """Get current ETL system status"""
    try:
        # Check database connection
        database_connected = True
        try:
            execute_query("SELECT 1")
        except:
            database_connected = False

        # Get last scrape/import times (you can implement this by storing in a status table)
        # For now, we'll return placeholder values
        status = {
            "database_connected": database_connected,
            "last_scrape": None,  # TODO: Implement status tracking
            "last_import": None,  # TODO: Implement status tracking
            "scraping_active": bool(active_processes["scraping"]),
            "importing_active": bool(active_processes["importing"]),
        }

        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/etl/clear-processes", methods=["POST"])
@login_required
@admin_required
def clear_etl_processes():
    """Clear any stuck ETL processes"""
    try:
        user_email = session["user"]["email"]

        # Clear active processes
        active_processes["scraping"] = None
        active_processes["importing"] = None

        log_user_activity(
            user_email,
            "admin_action",
            action="clear_etl_processes",
            details="Cleared stuck ETL processes",
        )

        return jsonify({"status": "success", "message": "ETL processes cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/etl/scrape")
@login_required
@admin_required
def start_scraping():
    """Start the scraping process with real-time updates via Server-Sent Events"""
    league = request.args.get("league", "").strip()
    scrapers = request.args.get("scrapers", "").split(",")

    if not league:
        return jsonify({"error": "League subdomain is required"}), 400

    if active_processes["scraping"]:
        print(f"Scraping process already active, rejecting new request")
        return jsonify({"error": "Scraping process already running"}), 409

    # Capture session data before generator starts
    user_email = session["user"]["email"]

    def generate_scrape_events():
        """Generator function for server-sent events"""
        try:
            start_time = datetime.now()

            # Log the start of scraping
            log_user_activity(
                user_email,
                "admin_action",
                action="start_scraping",
                details=f"Started scraping for league: {league}, scrapers: {scrapers}",
            )

            start_msg = f"🚀 Starting scraping process for league: {league.upper()}"
            time_str = start_time.strftime("%H:%M:%S")
            time_msg = f"⏰ Process started at: {time_str}"
            url_msg = f"📊 Target URL: https://{league}.tenniscores.com"

            yield f"data: {json.dumps({'type': 'output', 'message': start_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': time_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': url_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 5})}\n\n"

            # Determine which scrapers to run
            if "all" in scrapers:
                yield f"data: {json.dumps({'type': 'output', 'message': '🎯 Running all scrapers (comprehensive mode)', 'status': 'info'})}\n\n"

                # Run master scraper
                yield f"data: {json.dumps({'type': 'output', 'message': '🎾 Starting master scraper...', 'status': 'info'})}\n\n"

                # Run master scraper and yield progress updates
                master_success = False
                try:
                    for update in run_master_scraper_generator(league):
                        yield update
                        if '"success": true' in update:
                            master_success = True

                    success = master_success
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Critical error in master scraper: {str(e)}'})}\n\n"
                    print(f"Error in master scraper: {traceback.format_exc()}")
                    success = False

            else:
                # Run individual scrapers
                scrapers_list = ", ".join(scrapers)
                yield f"data: {json.dumps({'type': 'output', 'message': f'🔧 Running selected scrapers: {scrapers_list}', 'status': 'info'})}\n\n"

                # Run individual scrapers and yield progress updates
                success_count = 0
                total_scrapers = len(scrapers)

                for i, scraper in enumerate(scrapers):
                    scraper_success = False
                    try:
                        for update in run_individual_scraper_generator(
                            league, scraper, i, total_scrapers
                        ):
                            yield update
                            if '"success": true' in update:
                                scraper_success = True

                        if scraper_success:
                            success_count += 1
                    except Exception as e:
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Critical error in {scraper}: {str(e)}'})}\n\n"
                        print(f"Error in scraper {scraper}: {traceback.format_exc()}")

                success = success_count == total_scrapers

            if success:
                yield f"data: {json.dumps({'type': 'output', 'message': '✅ Scraping completed successfully!', 'status': 'success'})}\n\n"
                yield f"data: {json.dumps({'type': 'progress', 'progress': 100})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'success': True, 'message': 'All scrapers completed successfully'})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'output', 'message': '❌ Scraping completed with errors', 'status': 'error'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'success': False, 'message': 'Scraping process had errors'})}\n\n"

        except Exception as e:
            error_msg = f"Critical error in scraping process: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            print(f"Scraping error: {traceback.format_exc()}")
        finally:
            active_processes["scraping"] = None
            print("Scraping process cleaned up")

    # Set up the scraping process
    active_processes["scraping"] = True

    return Response(
        generate_scrape_events(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@admin_bp.route("/api/admin/etl/import")
@login_required
@admin_required
def start_import():
    """Start the database import process with real-time updates via Server-Sent Events"""
    if active_processes["importing"]:
        return jsonify({"error": "Import process already running"}), 409

    # Capture session data before generator starts
    user_email = session["user"]["email"]

    def generate_import_events():
        """Generator function for server-sent events"""
        try:
            import_start_time = datetime.now()

            # Log the start of import
            log_user_activity(
                user_email,
                "admin_action",
                action="start_import",
                details="Started database import process",
            )

            import_msg = f"🗄️ Starting database import process..."
            time_str = import_start_time.strftime("%H:%M:%S")
            time_msg = f"⏰ Import started at: {time_str}"

            yield f"data: {json.dumps({'type': 'output', 'message': import_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': time_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 5})}\n\n"

            # Step 1: Consolidate league data
            yield f"data: {json.dumps({'type': 'output', 'message': '📋 Step 1: Consolidating league JSON files...', 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 5})}\n\n"

            # Run consolidation and yield updates
            consolidation_success = False
            try:
                for update in run_consolidation_script_generator():
                    yield update
                    if '"success": true' in update or "✅ Consolidation completed successfully!" in update:
                        consolidation_success = True
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Critical error in consolidation: {str(e)}'})}\n\n"
                print(f"Error in consolidation: {traceback.format_exc()}")
                consolidation_success = False

            if not consolidation_success:
                yield f"data: {json.dumps({'type': 'error', 'message': '❌ Failed to consolidate league data'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'output', 'message': '✅ League data consolidation completed', 'status': 'success'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 20})}\n\n"

            # Step 2: Import to database
            yield f"data: {json.dumps({'type': 'output', 'message': '💾 Step 2: Importing data to PostgreSQL database...', 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 25})}\n\n"

            # Run import and yield updates
            import_success = False
            try:
                for update in run_import_script_generator():
                    yield update
                    if '"success": true' in update or "✅ Database import completed successfully!" in update:
                        import_success = True
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Critical error in import: {str(e)}'})}\n\n"
                print(f"Error in import: {traceback.format_exc()}")
                import_success = False

            success2 = import_success

            # Calculate total import time
            import_end_time = datetime.now()
            import_duration = import_end_time - import_start_time
            duration_str = f"{int(import_duration.total_seconds()//60)}m {int(import_duration.total_seconds()%60)}s"

            if success2:
                success_msg = (
                    f"✅ Database import completed successfully in {duration_str}"
                )
                yield f"data: {json.dumps({'type': 'output', 'message': success_msg, 'status': 'success'})}\n\n"
                yield f"data: {json.dumps({'type': 'progress', 'progress': 100})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'success': True, 'message': 'Import process completed successfully'})}\n\n"
            else:
                error_msg = f"❌ Database import failed after {duration_str}"
                yield f"data: {json.dumps({'type': 'output', 'message': error_msg, 'status': 'error'})}\n\n"
                yield f"data: {json.dumps({'type': 'complete', 'success': False, 'message': 'Import process failed'})}\n\n"

        except Exception as e:
            error_msg = f"Critical error in import process: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            print(f"Import error: {traceback.format_exc()}")
        finally:
            active_processes["importing"] = None
            print("Import process cleaned up")

    # Set up the import process
    active_processes["importing"] = True

    return Response(
        generate_import_events(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ==========================================
# ETL HELPER FUNCTIONS
# ==========================================


def enhance_scraper_message(message, scraper_type):
    """Enhance scraper output messages with more descriptive information"""
    if not message:
        return message

    # Enhanced descriptions for stats scraper
    if scraper_type == "scrape_stats":
        if "Found" in message and "series" in message:
            return f"🏆 Discovery: {message}"
        elif "Processing" in message and "Series" in message:
            return f"📊 Analyzing: {message}"
        elif "Navigating to URL" in message:
            return f"🌐 Loading page: {message}"
        elif "Looking for Statistics link" in message:
            return f"🔍 Searching for statistics section on page"
        elif "Found Statistics link" in message:
            return f"✅ Statistics section located - accessing team data"
        elif "Found" in message and "teams" in message:
            return f"📈 Team data extraction: {message}"
        elif "Successfully scraped stats" in message:
            return f"✅ Data collection: {message}"
        elif "Discovery Phase" in message:
            return f"🔍 {message} - scanning league structure"
        elif "Scraping Phase" in message:
            return f"⚡ {message} - extracting team statistics"
        elif "SCRAPING COMPLETE" in message:
            return f"🎉 {message} - all team statistics collected"
        elif "Skipping library/PDF" in message:
            return f"⏸️ Filter: {message} - excluding non-statistics content"
        elif "library" in message.lower() and "skipping" in message.lower():
            return f"⏸️ Content filter: {message}"

    # Enhanced descriptions for other scrapers
    elif scraper_type == "scraper_schedule":
        if "Found" in message and "matches" in message:
            return f"📅 Match schedule: {message}"
        elif "Processing schedule" in message:
            return f"⏰ Schedule analysis: {message}"

    elif scraper_type == "scraper_players":
        if "Found" in message and "players" in message:
            return f"👥 Player roster: {message}"
        elif "Processing player" in message:
            return f"🎾 Player data: {message}"

    elif scraper_type == "scraper_match_scores":
        if "Found" in message and "matches" in message:
            return f"🏆 Match results: {message}"
        elif "Processing match" in message:
            return f"📊 Score analysis: {message}"

    # Default enhancement with emoji prefix
    return f"📋 {message}"


def run_master_scraper_generator(league):
    """Generator that runs the master scraper and yields progress updates"""
    try:
        master_start_time = datetime.now()

        # Get the project root directory with better detection
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

        # Try multiple possible locations for master scraper
        possible_master_paths = [
            os.path.join(project_root, "etl", "scrapers", "master_scraper.py"),
            os.path.join(project_root, "scrapers", "master_scraper.py"),
            os.path.join(os.getcwd(), "etl", "scrapers", "master_scraper.py"),
            os.path.join(os.getcwd(), "scrapers", "master_scraper.py"),
        ]

        master_scraper_path = None
        for path in possible_master_paths:
            if os.path.exists(path):
                master_scraper_path = path
                break

        if master_scraper_path is None:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Master scraper not found'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': '🔍 Searched paths: ' + ', '.join(possible_master_paths), 'status': 'info'})}\n\n"
            return

        # Enhanced master scraper logging
        master_msg = f"🎾 Launching master scraper for comprehensive data collection"
        time_str = master_start_time.strftime("%H:%M:%S")
        start_msg = f"⏰ Master scraper started at: {time_str}"
        path_msg = f"📁 Script path: {master_scraper_path}"

        yield f"data: {json.dumps({'type': 'output', 'message': master_msg, 'status': 'info'})}\n\n"
        yield f"data: {json.dumps({'type': 'output', 'message': start_msg, 'status': 'info'})}\n\n"
        yield f"data: {json.dumps({'type': 'output', 'message': path_msg, 'status': 'info'})}\n\n"

        # Set up environment for subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = project_root

        # Use Python to run the master scraper programmatically
        process = subprocess.Popen(
            [sys.executable, master_scraper_path],
            cwd=project_root,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Send the league input to the process
        process.stdin.write(f"{league}\ny\n")
        process.stdin.flush()
        process.stdin.close()

        # Read output in real-time
        progress = 10
        while True:
            output = process.stdout.readline()
            if not output and process.poll() is not None:
                break

            if output:
                # Filter out prompts and format output for display
                line = output.strip()
                if (
                    line
                    and not line.startswith("Enter league")
                    and not line.startswith("Ready to start")
                ):
                    yield f"data: {json.dumps({'type': 'output', 'message': line, 'status': 'info'})}\n\n"

                    # Update progress based on output
                    if "✅" in line or "completed" in line.lower():
                        progress = min(progress + 15, 95)
                        yield f"data: {json.dumps({'type': 'progress', 'progress': progress})}\n\n"

        # Check the return code and calculate duration
        master_end_time = datetime.now()
        master_duration = master_end_time - master_start_time
        duration_str = f"{int(master_duration.total_seconds()//60)}m {int(master_duration.total_seconds()%60)}s"

        return_code = process.poll()
        if return_code == 0:
            success_msg = f"✅ Master scraper completed successfully in {duration_str}"
            yield f"data: {json.dumps({'type': 'output', 'message': success_msg, 'status': 'success', 'success': True})}\n\n"
        else:
            error_msg = f"❌ Master scraper failed after {duration_str}"
            yield f"data: {json.dumps({'type': 'output', 'message': error_msg, 'status': 'error'})}\n\n"

    except Exception as e:
        print(f"Error running master scraper: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Error running master scraper: {str(e)}'})}\n\n"


def run_individual_scraper_generator(league, scraper, scraper_index, total_scrapers):
    """Generator that runs a single scraper and yields progress updates"""
    try:
        scraper_start_time = datetime.now()
        # Get project root with better detection for different environments
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

        # Try multiple possible locations for scrapers
        possible_scraper_paths = [
            os.path.join(project_root, "etl", "scrapers"),
            os.path.join(project_root, "scrapers"),
            os.path.join(os.getcwd(), "etl", "scrapers"),
            os.path.join(os.getcwd(), "scrapers"),
        ]

        scrapers_dir = None
        for path in possible_scraper_paths:
            if os.path.exists(path):
                scrapers_dir = path
                break

        if scrapers_dir is None:
            yield f"data: {json.dumps({'type': 'output', 'message': '❌ Could not locate scrapers directory', 'status': 'error'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': '🔍 Searched paths: ' + ', '.join(possible_scraper_paths), 'status': 'info'})}\n\n"
            return

        scraper_path = os.path.join(scrapers_dir, f"{scraper}.py")

        if not os.path.exists(scraper_path):
            yield f"data: {json.dumps({'type': 'output', 'message': '❌ Scraper not found: ' + scraper, 'status': 'error'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': '🔍 Debug info - Looking for file at: ' + scraper_path, 'status': 'warning'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': '📁 Project root: ' + project_root, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': '📂 Scrapers dir: ' + scrapers_dir, 'status': 'info'})}\n\n"

            # List files in scrapers directory for debugging
            try:
                if os.path.exists(scrapers_dir):
                    files = os.listdir(scrapers_dir)
                    py_files = [f for f in files if f.endswith(".py")]
                    yield f"data: {json.dumps({'type': 'output', 'message': '📋 Available scrapers: ' + ', '.join(py_files), 'status': 'info'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'output', 'message': '❌ Scrapers directory does not exist: ' + scrapers_dir, 'status': 'error'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'output', 'message': '❌ Error listing scrapers: ' + str(e), 'status': 'error'})}\n\n"

            return

        # Enhanced logging with progress and timing
        step_msg = f"🚀 Step {scraper_index + 1}/{total_scrapers}: Running {scraper}"
        time_str = scraper_start_time.strftime("%H:%M:%S")
        start_msg = f"⏰ Started at: {time_str}"
        target_msg = f"🎯 Target: https://{league}.tenniscores.com"

        yield f"data: {json.dumps({'type': 'output', 'message': step_msg, 'status': 'info'})}\n\n"
        yield f"data: {json.dumps({'type': 'output', 'message': start_msg, 'status': 'info'})}\n\n"
        yield f"data: {json.dumps({'type': 'output', 'message': target_msg, 'status': 'info'})}\n\n"

        # Pre-flight checks
        yield f"data: {json.dumps({'type': 'output', 'message': f'🔍 Pre-flight checks for {scraper}...', 'status': 'info'})}\n\n"
        yield f"data: {json.dumps({'type': 'output', 'message': f'📁 Script path: {scraper_path}', 'status': 'info'})}\n\n"
        yield f"data: {json.dumps({'type': 'output', 'message': f'🐍 Python executable: {sys.executable}', 'status': 'info'})}\n\n"

        # Check if Chrome is available
        try:
            import subprocess

            chrome_paths = [
                "google-chrome",
                "chromium",
                "chromium-browser",
                "/usr/bin/google-chrome",
                "/opt/google/chrome/chrome",
            ]
            chrome_found = False

            for chrome_path in chrome_paths:
                try:
                    chrome_check = subprocess.run(
                        ["which", chrome_path],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if chrome_check.returncode == 0:
                        yield f"data: {json.dumps({'type': 'output', 'message': f'✅ Chrome browser found at: {chrome_path}', 'status': 'info'})}\n\n"
                        chrome_found = True
                        break
                except:
                    continue

            if not chrome_found:
                yield f"data: {json.dumps({'type': 'output', 'message': f'⚠️ Chrome browser not found in standard locations', 'status': 'warning'})}\n\n"
                yield f"data: {json.dumps({'type': 'output', 'message': f'💡 This may cause the scraper to hang during initialization', 'status': 'warning'})}\n\n"
                yield f"data: {json.dumps({'type': 'output', 'message': f'🔧 Consider installing Chrome: brew install --cask google-chrome (macOS)', 'status': 'info'})}\n\n"
        except:
            yield f"data: {json.dumps({'type': 'output', 'message': f'⚠️ Could not check Chrome installation', 'status': 'warning'})}\n\n"

        # Run the individual scraper with real-time output
        env = os.environ.copy()
        env["PYTHONPATH"] = project_root
        env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output for real-time streaming

        try:
            # Enhanced debug information before starting
            yield f"data: {json.dumps({'type': 'output', 'message': f'🔧 Configuring environment variables...', 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': f'📝 PYTHONPATH: {project_root}', 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': f'📝 Working directory: {project_root}', 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': f'🚀 Launching scraper process...', 'status': 'info'})}\n\n"

            # Use Popen for real-time output streaming
            process = subprocess.Popen(
                [sys.executable, scraper_path],
                cwd=project_root,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Separate stderr for better error handling
                text=True,
                bufsize=0,  # Unbuffered for immediate output
                universal_newlines=True,
            )

            # Send the league input to the process
            process.stdin.write(f"{league}\n")
            process.stdin.flush()
            process.stdin.close()

            # Read output in real-time with timeout handling
            output_count = 0
            last_status_time = datetime.now()
            last_output_time = datetime.now()
            timeout_seconds = 600  # 10 minute timeout
            chrome_init_timeout = (
                300  # 5 minute timeout for Chrome initialization (after detection)
            )
            no_output_timeout = 15  # 15 second no-output timeout during Chrome init
            chrome_init_phase = True

            # Status message for initialization
            yield f"data: {json.dumps({'type': 'output', 'message': f'🔄 Starting {scraper} process - monitoring for first output...', 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': f'⏱️ Will switch to extended timeout once scraper output is detected', 'status': 'info'})}\n\n"

            while True:
                current_time = datetime.now()
                elapsed_seconds = (current_time - scraper_start_time).total_seconds()

                # Check for Chrome initialization timeout (shorter timeout during Chrome setup)
                if chrome_init_phase and elapsed_seconds > chrome_init_timeout:
                    process.terminate()
                    yield f"data: {json.dumps({'type': 'output', 'message': f'⏰ Chrome initialization timed out after {chrome_init_timeout}s', 'status': 'warning'})}\n\n"
                    yield f"data: {json.dumps({'type': 'output', 'message': f'💡 Chrome browser may not be available - scraper cannot start WebDriver', 'status': 'warning'})}\n\n"
                    break

                # Check for overall timeout
                if elapsed_seconds > timeout_seconds:
                    process.terminate()
                    yield f"data: {json.dumps({'type': 'output', 'message': f'⏰ {scraper} timed out after {timeout_seconds//60} minutes', 'status': 'warning'})}\n\n"
                    break

                # Check for no-output timeout (different timeouts for Chrome init vs normal operation)
                current_no_output_timeout = (
                    no_output_timeout if chrome_init_phase else 120
                )
                if (
                    current_time - last_output_time
                ).total_seconds() > current_no_output_timeout:
                    process.terminate()
                    if chrome_init_phase:
                        yield f"data: {json.dumps({'type': 'output', 'message': f'⏰ No output during Chrome initialization for {no_output_timeout}s', 'status': 'warning'})}\n\n"
                        yield f"data: {json.dumps({'type': 'output', 'message': f'🔍 Chrome driver likely hanging - check Chrome installation', 'status': 'warning'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'output', 'message': f'⏰ {scraper} timed out - no output for {current_no_output_timeout//60} minutes', 'status': 'warning'})}\n\n"
                    break

                # Check if process is still running
                if process.poll() is not None:
                    # Process finished, read any remaining output
                    remaining_output = process.stdout.read()
                    if remaining_output:
                        for line in remaining_output.strip().split("\n"):
                            if line.strip():
                                yield f"data: {json.dumps({'type': 'output', 'message': f'📋 {line.strip()}', 'status': 'info'})}\n\n"
                    break

                # Use select to check if output is available (non-blocking)
                if select and sys.platform != "win32":
                    ready, _, _ = select.select(
                        [process.stdout, process.stderr], [], [], 1
                    )  # 1 second timeout
                    if ready:
                        # Check stdout
                        if process.stdout in ready:
                            output = process.stdout.readline()
                            if output:
                                line = output.strip()
                                output_count += 1
                                last_output_time = current_time

                                # Always show actual scraper output with enhanced descriptions
                                if line:
                                    # Filter out input prompts but show meaningful output
                                    if not line.startswith(
                                        "Enter league"
                                    ) and not line.startswith("League subdomain"):
                                        enhanced_message = enhance_scraper_message(
                                            line, scraper
                                        )
                                        yield f"data: {json.dumps({'type': 'output', 'message': enhanced_message, 'status': 'info'})}\n\n"

                                        # Check if we've moved past Chrome initialization - more aggressive detection
                                        if chrome_init_phase and any(
                                            phrase in line.lower()
                                            for phrase in [
                                                "starting tennis",
                                                "session start",
                                                "processing",
                                                "found",
                                                "discovery",
                                                "navigating",
                                                "chrome",
                                                "driver",
                                                "scraper",
                                                "series",
                                                "url",
                                                "statistics",
                                                "teams",
                                                "completed",
                                            ]
                                        ):
                                            chrome_init_phase = False
                                            yield f"data: {json.dumps({'type': 'output', 'message': f'✅ Chrome driver operational - switching to full timeout mode', 'status': 'info'})}\n\n"

                        # Check stderr for real-time error monitoring
                        if process.stderr in ready:
                            error_output = process.stderr.readline()
                            if error_output:
                                error_line = error_output.strip()
                                yield f"data: {json.dumps({'type': 'output', 'message': f'⚠️ Error: {error_line}', 'status': 'warning'})}\n\n"
                else:
                    # Windows or no select available - use readline with timeout simulation
                    try:
                        # Check stdout
                        output = process.stdout.readline()
                        if output:
                            line = output.strip()
                            output_count += 1
                            last_output_time = current_time

                            # Always show actual scraper output with enhanced descriptions
                            if line:
                                # Filter out input prompts but show meaningful output
                                if not line.startswith(
                                    "Enter league"
                                ) and not line.startswith("League subdomain"):
                                    enhanced_message = enhance_scraper_message(
                                        line, scraper
                                    )
                                    yield f"data: {json.dumps({'type': 'output', 'message': enhanced_message, 'status': 'info'})}\n\n"

                                    # Check if we've moved past Chrome initialization (Windows) - more aggressive detection
                                    if chrome_init_phase and any(
                                        phrase in line.lower()
                                        for phrase in [
                                            "starting tennis",
                                            "session start",
                                            "processing",
                                            "found",
                                            "discovery",
                                            "navigating",
                                            "chrome",
                                            "driver",
                                            "scraper",
                                            "series",
                                            "url",
                                            "statistics",
                                            "teams",
                                            "completed",
                                        ]
                                    ):
                                        chrome_init_phase = False
                                        yield f"data: {json.dumps({'type': 'output', 'message': f'✅ Chrome driver operational - switching to full timeout mode', 'status': 'info'})}\n\n"

                        # Also check stderr for errors
                        try:
                            error_output = process.stderr.readline()
                            if error_output:
                                error_line = error_output.strip()
                                yield f"data: {json.dumps({'type': 'output', 'message': f'⚠️ Error: {error_line}', 'status': 'warning'})}\n\n"
                        except:
                            pass
                    except:
                        pass

                # Provide periodic status updates with detailed descriptions
                if (
                    current_time - last_status_time
                ).total_seconds() > 15:  # Every 15 seconds
                    elapsed = current_time - scraper_start_time
                    elapsed_str = f"{int(elapsed.total_seconds())}s"
                    if output_count > 0:
                        if scraper == "scrape_stats":
                            status_msg = f"⏱️ Statistics extraction running for {elapsed_str} - processed {output_count} data points"
                        elif scraper == "scraper_schedule":
                            status_msg = f"⏱️ Schedule scraping running for {elapsed_str} - processed {output_count} schedule entries"
                        elif scraper == "scraper_players":
                            status_msg = f"⏱️ Player data collection running for {elapsed_str} - processed {output_count} player records"
                        else:
                            status_msg = f"⏱️ {scraper} running for {elapsed_str} - {output_count} operations completed"
                    else:
                        status_msg = f"⏱️ {scraper} running for {elapsed_str} - Chrome driver initialization in progress..."
                    yield f"data: {json.dumps({'type': 'output', 'message': status_msg, 'status': 'info'})}\n\n"
                    last_status_time = current_time

            # Check for remaining stderr output
            stderr_output = process.stderr.read()
            if stderr_output:
                for error_line in stderr_output.strip().split("\n"):
                    if error_line.strip():
                        # Parse specific Chrome errors
                        if (
                            "chrome" in error_line.lower()
                            or "selenium" in error_line.lower()
                        ):
                            yield f"data: {json.dumps({'type': 'output', 'message': f'🔴 Chrome Driver Error: {error_line.strip()}', 'status': 'warning'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'output', 'message': f'⚠️ Error: {error_line.strip()}', 'status': 'warning'})}\n\n"

            # Calculate final timing
            scraper_end_time = datetime.now()
            scraper_duration = scraper_end_time - scraper_start_time
            duration_str = f"{scraper_duration.total_seconds():.1f}s"

            return_code = process.poll()
            if return_code == 0:
                success_msg = f"✅ {scraper} completed successfully in {duration_str} ({output_count} operations)"
                yield f"data: {json.dumps({'type': 'output', 'message': success_msg, 'status': 'success', 'success': True})}\n\n"
            else:
                error_msg = f"❌ {scraper} failed after {duration_str} (exit code: {return_code})"
                yield f"data: {json.dumps({'type': 'output', 'message': error_msg, 'status': 'error'})}\n\n"

        except subprocess.TimeoutExpired:
            scraper_end_time = datetime.now()
            scraper_duration = scraper_end_time - scraper_start_time
            duration_str = f"{scraper_duration.total_seconds():.1f}s"
            timeout_msg = (
                f"⏰ {scraper} timed out after {duration_str} (10 minute limit reached)"
            )
            yield f"data: {json.dumps({'type': 'output', 'message': timeout_msg, 'status': 'warning'})}\n\n"
        except Exception as e:
            scraper_end_time = datetime.now()
            scraper_duration = scraper_end_time - scraper_start_time
            duration_str = f"{scraper_duration.total_seconds():.1f}s"
            error_msg = f"❌ Error running {scraper} after {duration_str}: {str(e)}"
            yield f"data: {json.dumps({'type': 'output', 'message': error_msg, 'status': 'error'})}\n\n"

        # Update progress
        progress = int(((scraper_index + 1) / total_scrapers) * 90) + 10
        yield f"data: {json.dumps({'type': 'progress', 'progress': progress})}\n\n"

    except Exception as e:
        print(f"Error running scraper {scraper}: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Error running {scraper}: {str(e)}'})}\n\n"


def is_milestone_message(message):
    """Filter function to identify milestone messages worth showing to admin"""
    if not message:
        return False
    
    # Exclude verbose internal debug messages
    exclusion_patterns = [
        'utils.database_player_lookup',
        'database lookup for:',
        'first name variations:',
        'series variations:',
        'primary:',
        'fallback strategies',
        'name variation search',
        'exact match found',
        'no exact match found',
        'cannot determine correct player',
        'skipping association',
        'debug:',
        'info:',
        'warning:utils',
        'info:utils'
    ]
    
    message_lower = message.lower()
    if any(pattern in message_lower for pattern in exclusion_patterns):
        return False
    
    # Only show major milestones and critical errors
    milestone_patterns = [
        # Critical errors (not internal lookup failures)
        ('critical error', True),
        ('failed to connect', True),
        ('database connection', True),
        
        # Major step transitions
        ('🚀 starting', True),
        ('📋 step', True),
        ('💾 step', True),
        ('step 1:', True),
        ('step 2:', True),
        ('step 3:', True),
        ('step 4:', True),
        ('step 5:', True),
        ('step 6:', True),
        ('step 7:', True),
        ('step 8:', True),
        
        # Major completions with counts
        ('✅ imported', True),
        ('✅ consolidation completed', True),
        ('✅ database import completed', True),
        ('✅ etl process completed', True),
        ('imported.*records', True),
        
        # Connection and database setup
        ('connecting to database', True),
        ('connected to database', True),
        ('database connected', True),
        
        # Summary and totals
        ('import summary', True),
        ('total import time', True),
        ('total.*records', True),
        ('backup.*restored', True),
        ('session version', True)
    ]
    
    # Check for milestone patterns
    import re
    for pattern, _ in milestone_patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False

def calculate_consolidation_progress(message):
    """Calculate progress percentage for consolidation phase (0-20%)"""
    if not message:
        return 5
    
    message_lower = message.lower()
    
    if 'starting' in message_lower:
        return 5
    elif 'loading' in message_lower or 'reading' in message_lower:
        return 8
    elif 'consolidating' in message_lower:
        return 12
    elif 'writing' in message_lower or 'saving' in message_lower:
        return 16
    elif 'completed' in message_lower or '✅' in message:
        return 20
    
    return 10  # Default progress for consolidation phase

def calculate_import_progress(message):
    """Calculate progress percentage for import phase (20-95%)"""
    if not message:
        return 25
    
    message_lower = message.lower()
    
    # Database connection phase (20-25%)
    if 'connecting' in message_lower or 'database' in message_lower:
        return 25
    
    # Basic reference data (25-35%)
    elif 'leagues' in message_lower or 'clubs' in message_lower:
        return 30
    elif 'series' in message_lower and 'importing' in message_lower:
        return 35
    
    # Main data import phases (35-85%)
    elif 'teams' in message_lower and 'importing' in message_lower:
        return 40
    elif 'players' in message_lower and 'importing' in message_lower:
        return 50
    elif 'match' in message_lower and 'importing' in message_lower:
        return 65
    elif 'stats' in message_lower and 'importing' in message_lower:
        return 75
    elif 'schedule' in message_lower and 'importing' in message_lower:
        return 80
    
    # Final phases (85-95%)
    elif 'validation' in message_lower or 'orphan' in message_lower:
        return 85
    elif 'session' in message_lower or 'backup' in message_lower or 'restore' in message_lower:
        return 90
    elif 'completed' in message_lower or 'success' in message_lower or '✅' in message:
        return 95
    
    return 30  # Default progress for import phase

def run_consolidation_script_generator():
    """Generator that runs the consolidation script and yields milestone updates"""
    try:
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

        # Try multiple possible locations for consolidation script
        possible_consolidation_paths = [
            os.path.join(
                project_root,
                "data",
                "etl",
                "database_import",
                "consolidate_league_jsons_to_all.py",
            ),
            os.path.join(
                project_root,
                "etl",
                "database_import",
                "consolidate_league_jsons_to_all.py",
            ),
            os.path.join(project_root, "etl", "consolidate_league_jsons_to_all.py"),
            os.path.join(
                os.getcwd(),
                "data",
                "etl",
                "database_import",
                "consolidate_league_jsons_to_all.py",
            ),
            os.path.join(
                os.getcwd(),
                "etl",
                "database_import",
                "consolidate_league_jsons_to_all.py",
            ),
            os.path.join(os.getcwd(), "etl", "consolidate_league_jsons_to_all.py"),
        ]

        consolidation_script = None
        for path in possible_consolidation_paths:
            if os.path.exists(path):
                consolidation_script = path
                break

        if consolidation_script is None:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Consolidation script not found'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': '🔍 Searched paths: ' + ', '.join(possible_consolidation_paths), 'status': 'info'})}\n\n"
            return

        env = os.environ.copy()
        env["PYTHONPATH"] = project_root
        env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output for real-time display

        # Use Popen for real-time streaming output
        process = subprocess.Popen(
            [sys.executable, consolidation_script],
            cwd=project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        consolidation_success = True
        current_progress = 5
        
        try:
            # Read output line by line in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if line and is_milestone_message(line):
                        # Calculate and update progress
                        new_progress = calculate_consolidation_progress(line)
                        if new_progress > current_progress:
                            current_progress = new_progress
                            yield f"data: {json.dumps({'type': 'progress', 'progress': current_progress})}\n\n"
                        
                        # Format milestone message with proper line breaks
                        formatted_message = line.replace('] ', ']<br/>') if '] ' in line else line
                        yield f"data: {json.dumps({'type': 'output', 'message': f'📊 {formatted_message}', 'status': 'info'})}\n\n"
            
            # Wait for process to complete and get return code
            return_code = process.wait(timeout=300)  # 5 minute timeout
            
            if return_code == 0:
                yield f"data: {json.dumps({'type': 'output', 'message': '✅ Consolidation completed successfully!', 'status': 'success', 'success': True})}\n\n"
            else:
                consolidation_success = False
                yield f"data: {json.dumps({'type': 'output', 'message': '❌ Consolidation failed with exit code: ' + str(return_code), 'status': 'error'})}\n\n"
                
        except subprocess.TimeoutExpired:
            process.kill()
            consolidation_success = False
            yield f"data: {json.dumps({'type': 'output', 'message': '❌ Consolidation timed out after 5 minutes', 'status': 'error'})}\n\n"
        except Exception as e:
            process.kill()
            consolidation_success = False
            yield f"data: {json.dumps({'type': 'output', 'message': f'❌ Consolidation error: {str(e)}', 'status': 'error'})}\n\n"
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()

    except Exception as e:
        print(f"Error running consolidation script: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Error running consolidation: {str(e)}'})}\n\n"


def run_import_script_generator():
    """Generator that runs the import script and yields milestone updates"""
    try:
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

        # Try multiple possible locations for import script
        possible_import_paths = [
            os.path.join(
                project_root,
                "data",
                "etl",
                "database_import",
                "import_all_jsons_to_database.py",
            ),
            os.path.join(
                project_root, "etl", "database_import", "import_all_jsons_to_database.py"
            ),
            os.path.join(project_root, "etl", "import_all_jsons_to_database.py"),
            os.path.join(
                os.getcwd(),
                "data",
                "etl",
                "database_import",
                "import_all_jsons_to_database.py",
            ),
            os.path.join(
                os.getcwd(), "etl", "database_import", "import_all_jsons_to_database.py"
            ),
            os.path.join(os.getcwd(), "etl", "import_all_jsons_to_database.py"),
        ]

        import_script = None
        for path in possible_import_paths:
            if os.path.exists(path):
                import_script = path
                break

        if import_script is None:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Import script not found'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': '🔍 Searched paths: ' + ', '.join(possible_import_paths), 'status': 'info'})}\n\n"
            return

        env = os.environ.copy()
        env["PYTHONPATH"] = project_root
        env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output for real-time display

        # Use Popen for real-time streaming output
        process = subprocess.Popen(
            [sys.executable, import_script],
            cwd=project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        import_success = True
        current_progress = 20  # Start at 20% after consolidation
        
        try:
            # Read output line by line in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if line and is_milestone_message(line):
                        # Calculate and update progress
                        new_progress = calculate_import_progress(line)
                        if new_progress > current_progress:
                            current_progress = new_progress
                            yield f"data: {json.dumps({'type': 'progress', 'progress': current_progress})}\n\n"
                        
                        # Format milestone message with proper line breaks
                        formatted_message = line.replace('] ', ']<br/>') if '] ' in line else line
                        yield f"data: {json.dumps({'type': 'output', 'message': f'💾 {formatted_message}', 'status': 'info'})}\n\n"
            
            # Wait for process to complete and get return code
            return_code = process.wait(timeout=1800)  # 30 minute timeout
            
            if return_code == 0:
                yield f"data: {json.dumps({'type': 'output', 'message': '✅ Database import completed successfully!', 'status': 'success', 'success': True})}\n\n"
            else:
                import_success = False
                yield f"data: {json.dumps({'type': 'output', 'message': '❌ Database import failed with exit code: ' + str(return_code), 'status': 'error'})}\n\n"
                
        except subprocess.TimeoutExpired:
            process.kill()
            import_success = False
            yield f"data: {json.dumps({'type': 'output', 'message': '❌ Database import timed out after 30 minutes', 'status': 'error'})}\n\n"
        except Exception as e:
            process.kill()
            import_success = False
            yield f"data: {json.dumps({'type': 'output', 'message': f'❌ Database import error: {str(e)}', 'status': 'error'})}\n\n"
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()

    except Exception as e:
        print(f"Error running import script: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Error running import: {str(e)}'})}\n\n"


# ==========================================
# EXISTING ADMIN API ENDPOINTS
# ==========================================


@admin_bp.route("/api/admin/users")
@login_required
def get_admin_users():
    """Get all registered users with their club and series information"""
    try:
        users = get_all_users()
        return jsonify(users)
    except Exception as e:
        print(f"Error getting admin users: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/series")
@login_required
def get_admin_series():
    """Get all active series with player counts and active clubs"""
    try:
        series = get_all_series_with_stats()
        return jsonify(series)
    except Exception as e:
        print(f"Error getting admin series: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/clubs")
@login_required
def get_admin_clubs():
    """Get all clubs with player counts and active series"""
    try:
        clubs = execute_query(
            """
            SELECT c.id, c.name, COUNT(DISTINCT p.id) as player_count,
                   STRING_AGG(DISTINCT s.name, ', ') as active_series
            FROM clubs c
            LEFT JOIN players p ON c.id = p.club_id
            LEFT JOIN series s ON p.series_id = s.id
            GROUP BY c.id, c.name
            ORDER BY c.name
        """
        )

        return jsonify(
            [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "player_count": row["player_count"],
                    "active_series": row["active_series"] or "None",
                }
                for row in clubs
            ]
        )
    except Exception as e:
        print(f"Error getting admin clubs: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/leagues")
@login_required
def get_admin_leagues():
    """Get all leagues with club and series counts"""
    try:
        leagues = execute_query(
            """
            SELECT l.id, l.league_name, l.league_url,
                   COUNT(DISTINCT cl.club_id) as club_count,
                   COUNT(DISTINCT sl.series_id) as series_count
            FROM leagues l
            LEFT JOIN club_leagues cl ON l.id = cl.league_id
            LEFT JOIN series_leagues sl ON l.id = sl.league_id
            GROUP BY l.id, l.league_name, l.league_url
            ORDER BY l.league_name
        """
        )

        return jsonify(
            [
                {
                    "id": row["id"],
                    "league_name": row["league_name"],
                    "league_url": row["league_url"],
                    "club_count": row["club_count"],
                    "series_count": row["series_count"],
                }
                for row in leagues
            ]
        )
    except Exception as e:
        print(f"Error getting admin leagues: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/update-user", methods=["POST"])
@login_required
def update_user():
    """Update a user's information"""
    try:
        data = request.json
        email = data.get("email")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        club_name = data.get("club_name")
        series_name = data.get("series_name")

        if not all([email, first_name, last_name, club_name, series_name]):
            return jsonify({"error": "Missing required fields"}), 400

        # Use service layer to update user
        update_user_info(
            email,
            first_name,
            last_name,
            club_name,
            series_name,
            session["user"]["email"],
        )
        return jsonify({"status": "success"})

    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/update-club", methods=["POST"])
@login_required
def update_club():
    """Update a club's information"""
    try:
        data = request.json
        old_name = data.get("old_name")
        new_name = data.get("new_name")

        if not all([old_name, new_name]):
            return jsonify({"error": "Missing required fields"}), 400

        # Use service layer to update club
        update_club_name(old_name, new_name)
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error updating club: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/update-series", methods=["POST"])
@login_required
def update_series():
    """Update a series' information"""
    try:
        data = request.json
        old_name = data.get("old_name")
        new_name = data.get("new_name")

        if not all([old_name, new_name]):
            return jsonify({"error": "Missing required fields"}), 400

        # Use service layer to update series
        update_series_name(old_name, new_name)
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error updating series: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/delete-user", methods=["POST"])
@login_required
@admin_required
def delete_user():
    """Delete a user from the database"""
    try:
        data = request.json
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Use service layer to delete user
        result = delete_user_by_email(email, session["user"]["email"])
        return jsonify(result)

    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/remove-cita-files", methods=["POST"])
@login_required
@admin_required
def remove_cita_files():
    """Remove CITA league files from data/leagues directory"""
    try:
        data = request.json
        dry_run = data.get("dry_run", True)  # Default to dry run for safety
        
        # Import the CITA file remover
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from scripts.remove_cita_files_production import CITAFileRemover
        
        # Create remover instance and run
        remover = CITAFileRemover()
        success = remover.run_removal(dry_run=dry_run)
        
        # Collect results
        result = {
            "success": success,
            "dry_run": dry_run,
            "removed_files": getattr(remover, 'removed_files', []),
            "removed_dirs": getattr(remover, 'removed_dirs', []),
            "message": "CITA file removal completed successfully" if success else "CITA file removal failed"
        }
        
        # Log admin action
        action_type = "CITA File Removal (Dry Run)" if dry_run else "CITA File Removal (Live)"
        log_admin_action(
            admin_email=session["user"]["email"],
            action_type=action_type,
            details=f"Success: {success}, Files: {len(result['removed_files'])}, Dirs: {len(result['removed_dirs'])}"
        )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error removing CITA files: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/user-activity/<email>")
@login_required
def get_user_activity(email):
    """Get activity logs for a specific user"""
    try:
        # Use service layer to get user activity
        response_data = get_user_activity_logs(email)

        # Create response with cache-busting headers
        response = jsonify(response_data)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        print(f"Error getting user activity: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/user-activity")
@login_required
def user_activity():
    """Serve the user activity page"""
    print("\n=== Serving User Activity Page ===")
    print(f"User in session: {'user' in session}")
    print(f"Session contents: {session}")

    try:
        print("Attempting to log user activity page visit")
        log_user_activity(
            session["user"]["email"],
            "page_visit",
            page="user_activity",
            details="Accessed user activity page",
            first_name=session["user"].get("first_name"),
            last_name=session["user"].get("last_name")
        )
        print("Successfully logged user activity page visit")
    except Exception as e:
        print(f"Error logging user activity page visit: {str(e)}")
        print(traceback.format_exc())

    return send_from_directory("static", "user-activity.html")


# ==========================================
# DASHBOARD API ENDPOINTS
# ==========================================


@admin_bp.route("/api/admin/dashboard/activities")
@login_required
@admin_required
def get_dashboard_activities():
    """Get recent activities for dashboard timeline"""
    try:
        # Get query parameters
        limit = int(request.args.get("limit", 50))
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        action_type = request.args.get("action_type")
        team_id = request.args.get("team_id")
        player_id = request.args.get("player_id")
        exclude_impersonated = request.args.get("exclude_impersonated", "false").lower() == "true"
        exclude_admin = request.args.get("exclude_admin", "true").lower() == "true"

        # Build filters
        filters = {}
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        if action_type:
            filters["action_type"] = action_type
        if team_id:
            filters["team_id"] = int(team_id)
        if player_id:
            filters["player_id"] = int(player_id)
        
        filters["exclude_impersonated"] = exclude_impersonated
        filters["exclude_admin"] = exclude_admin

        activities = get_recent_activities(limit=limit, filters=filters)

        return jsonify(
            {
                "status": "success",
                "activities": activities,
                "total_count": len(activities),
            }
        )

    except Exception as e:
        print(f"Error getting dashboard activities: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/dashboard/heatmap")
@login_required
@admin_required
def get_dashboard_heatmap():
    """Get activity heatmap data for dashboard"""
    try:
        days = int(request.args.get("days", 30))
        heatmap_data = get_activity_heatmap_data(days=days)

        return jsonify({"status": "success", "heatmap_data": heatmap_data})

    except Exception as e:
        print(f"Error getting dashboard heatmap: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/dashboard/top-players")
# @login_required  # Temporarily removed for debugging
# @admin_required  # Temporarily removed for debugging
def get_dashboard_top_players():
    """Get top active players for dashboard"""
    try:
        limit = int(request.args.get("limit", 10))
        exclude_impersonated = request.args.get("exclude_impersonated", "false").lower() == "true"
        exclude_admin = request.args.get("exclude_admin", "false").lower() == "true"
        
        # Build filters for the top players function
        filters = {
            "exclude_impersonated": exclude_impersonated,
            "exclude_admin": exclude_admin
        }
        
        top_players = get_top_active_players(limit=limit, filters=filters)

        return jsonify({"status": "success", "top_players": top_players})

    except Exception as e:
        print(f"Error getting dashboard top players: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/dashboard/stats")
@login_required
@admin_required
def get_dashboard_stats():
    """Get overall activity statistics for dashboard"""
    try:
        exclude_impersonated = request.args.get("exclude_impersonated", "false").lower() == "true"
        exclude_admin = request.args.get("exclude_admin", "false").lower() == "true"
        
        # Build filters for the stats function
        filters = {
            "exclude_impersonated": exclude_impersonated,
            "exclude_admin": exclude_admin
        }
        
        stats = get_activity_stats(filters=filters)

        return jsonify({"status": "success", "stats": stats})

    except Exception as e:
        print(f"Error getting dashboard stats: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/dashboard/filters")
@login_required
@admin_required
def get_dashboard_filters():
    """Get filter options for dashboard"""
    try:
        filter_options = get_filter_options()

        return jsonify({"status": "success", "filters": filter_options})

    except Exception as e:
        print(f"Error getting dashboard filters: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ==========================================
# COCKPIT DASHBOARD API ENDPOINTS
# ==========================================

@admin_bp.route("/api/admin/cockpit/real-time-stats")
@login_required
@admin_required
def get_cockpit_real_time_stats():
    """Get real-time statistics for cockpit dashboard"""
    try:
        # Get comprehensive stats including trends
        exclude_impersonated = request.args.get("exclude_impersonated", "false").lower() == "true"
        exclude_admin = request.args.get("exclude_admin", "false").lower() == "true"
        
        filters = {
            "exclude_impersonated": exclude_impersonated,
            "exclude_admin": exclude_admin
        }
        
        # Get current stats
        current_stats = get_activity_stats(filters=filters)
        
        # Get historical data for trends (yesterday only)
        from datetime import datetime, timedelta
        now = datetime.now()
        yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday_start.replace(hour=23, minute=59, second=59)
        
        yesterday_filters = filters.copy()
        yesterday_filters["date_from"] = yesterday_start.isoformat()
        yesterday_filters["date_to"] = yesterday_end.isoformat()
        
        yesterday_stats = get_activity_stats(filters=yesterday_filters)
        
        # Calculate trends (today vs yesterday)
        trends = {
            "total_activities_change": calculate_percentage_change(
                current_stats.get("today_activities", 0),  # Compare today's activities
                yesterday_stats.get("today_activities", 0)  # vs yesterday's activities
            ),
            "today_activities_change": calculate_percentage_change(
                current_stats.get("today_activities", 0),
                yesterday_stats.get("today_activities", 0)
            ),
            "active_users_change": calculate_percentage_change(
                current_stats.get("active_users_today", 0),
                yesterday_stats.get("active_users_today", 0)
            )
        }
        
        # Add system health indicators
        system_health = {
            "database": "online",
            "api_services": "online", 
            "background_jobs": "running",
            "memory_usage": "45%",
            "cpu_usage": "12%",
            "error_rate": "0.1%"
        }
        
        return jsonify({
            "status": "success",
            "stats": current_stats,
            "trends": trends,
            "system_health": system_health,
            "timestamp": now.isoformat()
        })

    except Exception as e:
        print(f"Error getting cockpit real-time stats: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/cockpit/detailed-activities")
@login_required
@admin_required
def get_cockpit_detailed_activities():
    """Get detailed activities for cockpit with enhanced information"""
    try:
        # Get query parameters
        limit = int(request.args.get("limit", 100))
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        action_type = request.args.get("action_type")
        team_id = request.args.get("team_id")
        player_id = request.args.get("player_id")
        exclude_impersonated = request.args.get("exclude_impersonated", "false").lower() == "true"
        exclude_admin = request.args.get("exclude_admin", "false").lower() == "true"

        # Build filters
        filters = {}
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        if action_type:
            filters["action_type"] = action_type
        if team_id:
            filters["team_id"] = int(team_id)
        if player_id:
            filters["player_id"] = int(player_id)
        
        filters["exclude_impersonated"] = exclude_impersonated
        filters["exclude_admin"] = exclude_admin

        # Get activities with enhanced details
        activities = get_recent_activities(limit=limit, filters=filters)
        
        # Enhance activities with additional context
        enhanced_activities = []
        for activity in activities:
            enhanced_activity = activity.copy()
            
            # Add detailed action description
            enhanced_activity["detailed_description"] = get_detailed_action_description(activity)
            
            # Add browser/device info
            if activity.get("user_agent"):
                enhanced_activity["browser_info"] = parse_user_agent(activity["user_agent"])
            
            # Add location info if available
            if activity.get("ip_address"):
                enhanced_activity["location_info"] = get_location_info(activity["ip_address"])
            
            # Add session context
            enhanced_activity["session_context"] = get_session_context(activity)
            
            enhanced_activities.append(enhanced_activity)

        return jsonify({
            "status": "success",
            "activities": enhanced_activities,
            "total_count": len(enhanced_activities),
            "filters_applied": filters
        })

    except Exception as e:
        print(f"Error getting cockpit detailed activities: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/test/session-check")
def session_check():
    """Check session data without authentication"""
    try:
        return jsonify({
            "status": "success",
            "session": {
                "has_user": "user" in session,
                "user_email": session.get("user", {}).get("email", "No email"),
                "is_admin": session.get("user", {}).get("is_admin", False),
                "session_keys": list(session.keys())
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/cockpit/activity-trends")
@login_required
@admin_required
def get_cockpit_activity_trends():
    """Get activity trends data for charts"""
    try:
        hours = int(request.args.get("hours", 24))
        
        # Get hourly activity data for the specified period
        from datetime import datetime, timedelta
        now = datetime.now()
        start_time = now - timedelta(hours=hours)
        
        # Query for hourly activity counts
        query = """
        SELECT 
            DATE_TRUNC('hour', timestamp) as hour,
            activity_type as action_type,
            COUNT(*) as count
        FROM user_activity_logs 
        WHERE timestamp >= %s AND timestamp <= %s
        GROUP BY DATE_TRUNC('hour', timestamp), activity_type
        ORDER BY hour DESC
        """
        
        results = execute_query(query, (start_time, now))
        
        # Process data for chart
        chart_data = {
            "labels": [],
            "datasets": {}
        }
        
        # Group by action type
        action_types = {}
        for row in results:
            hour = row['hour'].strftime("%H:%M")
            action_type = row['action_type']
            count = row['count']
            
            if hour not in chart_data["labels"]:
                chart_data["labels"].insert(0, hour)
            
            if action_type not in action_types:
                action_types[action_type] = {}
            action_types[action_type][hour] = count
        
        # Create datasets for each action type
        for action_type, hourly_data in action_types.items():
            data = []
            for label in chart_data["labels"]:
                data.append(hourly_data.get(label, 0))
            
            chart_data["datasets"][action_type] = {
                "label": action_type.replace("_", " ").title(),
                "data": data,
                "borderColor": get_action_type_color(action_type),
                "backgroundColor": f"rgba({get_action_type_rgb(action_type)}, 0.1)",
                "tension": 0.4
            }
        
        return jsonify({
            "status": "success",
            "chart_data": chart_data,
            "period_hours": hours
        })

    except Exception as e:
        print(f"Error getting cockpit activity trends: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/cockpit/debug-session")
def debug_session():
    """Debug endpoint to check session data"""
    try:
        session_data = {
            "has_user": "user" in session,
            "user_data": session.get("user", {}),
            "is_admin": session.get("user", {}).get("is_admin", False),
            "impersonation_active": session.get("impersonation_active", False),
            "session_keys": list(session.keys())
        }
        return jsonify({
            "status": "success",
            "session": session_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/cockpit/test-activity-trends")
def test_cockpit_activity_trends():
    """Test endpoint for activity trends without authentication"""
    try:
        hours = int(request.args.get("hours", 24))
        
        # Get hourly activity data for the specified period
        from datetime import datetime, timedelta
        now = datetime.now()
        start_time = now - timedelta(hours=hours)
        
        # Query for hourly activity counts
        query = """
        SELECT 
            DATE_TRUNC('hour', timestamp) as hour,
            activity_type as action_type,
            COUNT(*) as count
        FROM user_activity_logs 
        WHERE timestamp >= %s AND timestamp <= %s
        GROUP BY DATE_TRUNC('hour', timestamp), action_type
        ORDER BY hour DESC
        """
        
        results = execute_query(query, (start_time, now))
        
        # Process data for chart
        chart_data = {
            "labels": [],
            "datasets": {}
        }
        
        # Group by action type
        action_types = {}
        for row in results:
            hour = row['hour'].strftime("%H:%M")
            action_type = row['action_type']
            count = row['count']
            
            if hour not in chart_data["labels"]:
                chart_data["labels"].insert(0, hour)
            
            if action_type not in action_types:
                action_types[action_type] = {}
            action_types[action_type][hour] = count
        
        # Create datasets for each action type
        for action_type, hourly_data in action_types.items():
            data = []
            for label in chart_data["labels"]:
                data.append(hourly_data.get(label, 0))
            
            chart_data["datasets"][action_type] = {
                "label": action_type.replace("_", " ").title(),
                "data": data,
                "borderColor": get_action_type_color(action_type),
                "backgroundColor": f"rgba({get_action_type_rgb(action_type)}, 0.1)",
                "tension": 0.4
            }
        
        return jsonify({
            "status": "success",
            "chart_data": chart_data,
            "period_hours": hours
        })

    except Exception as e:
        print(f"Error getting test activity trends: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/cockpit/system-metrics")
@login_required
@admin_required
def get_cockpit_system_metrics():
    """Get system performance metrics"""
    try:
        # This would typically integrate with system monitoring
        # For now, we'll provide simulated data
        
        # Get actual system metrics if available
        if psutil:
            try:
                memory = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=1)
                disk = psutil.disk_usage('/')
            except:
                # Fallback values if psutil fails
                memory = type('obj', (object,), {'percent': 45})()
                cpu_percent = 12
                disk = type('obj', (object,), {'percent': 60})()
        else:
            # Fallback values if psutil not available
            memory = type('obj', (object,), {'percent': 45})()
            cpu_percent = 12
            disk = type('obj', (object,), {'percent': 60})()
        
        metrics = {
            "memory_usage": f"{memory.percent}%",
            "cpu_usage": f"{cpu_percent}%",
            "disk_usage": f"{disk.percent}%",
            "database_connections": get_database_connection_count(),
            "active_sessions": get_active_session_count(),
            "error_rate": get_error_rate(),
            "response_time_avg": get_average_response_time()
        }
        
        return jsonify({
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Error getting cockpit system metrics: {str(e)}")
        return jsonify({"error": str(e)}), 500




@admin_bp.route("/api/admin/cockpit/page-analytics")
@login_required
@admin_required
def get_cockpit_page_analytics():
    """Get page visit analytics for mobile cockpit"""
    try:
        from datetime import datetime, timedelta
        
        # Get date range for today
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Query page visits for today
        query = """
        SELECT 
            page,
            COUNT(*) as page_views,
            COUNT(DISTINCT user_email) as unique_visitors
        FROM user_activity_logs 
        WHERE activity_type = 'page_visit' 
        AND timestamp >= %s AND timestamp <= %s
        GROUP BY page
        ORDER BY page_views DESC
        LIMIT 10
        """
        
        cursor = get_db_connection().cursor()
        cursor.execute(query, (today_start, today_end))
        page_stats = cursor.fetchall()
        
        # Calculate total metrics
        total_page_views = sum(row[1] for row in page_stats)
        total_unique_visitors = len(set(row[2] for row in page_stats))
        
        # Format top pages
        top_pages = []
        for row in page_stats:
            page_name = format_page_name(row[0])
            top_pages.append({
                'page': row[0],
                'views': row[1],
                'name': page_name
            })
        
        # Mock additional metrics (these would come from more complex queries)
        analytics_data = {
            "total_page_views": total_page_views,
            "unique_visitors": total_unique_visitors,
            "avg_session_duration": "4m 32s",  # Would calculate from session data
            "bounce_rate": "23%",  # Would calculate from single-page sessions
            "top_pages": top_pages
        }
        
        return jsonify({
            "status": "success",
            "analytics": analytics_data,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Error getting page analytics: {str(e)}")
        return jsonify({"error": str(e)}), 500




@admin_bp.route("/api/admin/cockpit/most-active-pages")
@login_required
@admin_required
def get_cockpit_most_active_pages():
    """Get most active pages for mobile cockpit"""
    try:
        from datetime import datetime, timedelta
        
        # Get parameters
        limit = int(request.args.get("limit", 10))
        exclude_admin = request.args.get("exclude_admin", "true").lower() == "true"
        exclude_impersonated = request.args.get("exclude_impersonated", "false").lower() == "true"
        
        # Get date range for today
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Build query
        query = """
        SELECT 
            page as page_id,
            COUNT(*) as visit_count
        FROM user_activity_logs 
        WHERE activity_type = 'page_visit' 
        AND timestamp >= %s AND timestamp <= %s
        """
        
        params = [today_start, today_end]
        
        # Add admin filtering if needed
        if exclude_admin:
            query += " AND user_email NOT IN (SELECT email FROM users WHERE is_admin = true)"
        
        # Add impersonation filtering if needed
        if exclude_impersonated:
            query += " AND details NOT LIKE '%[IMPERSONATION]%'"
        
        query += """
        GROUP BY page
        ORDER BY visit_count DESC
        LIMIT %s
        """
        params.append(limit)
        
        page_stats = execute_query(query, params)
        
        # Format pages
        pages = []
        for row in page_stats:
            page_id = row['page_id']
            page_name = format_page_name(page_id)
            pages.append({
                'page_id': page_id,
                'page_name': page_name,
                'visit_count': row['visit_count']
            })
        
        return jsonify({
            "status": "success",
            "pages": pages,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        print(f"Error getting most active pages: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/cockpit/user-count-trends")
@login_required
@admin_required
def get_cockpit_user_count_trends():
    """Get user count trends over time for cockpit dashboard"""
    try:
        from datetime import datetime, timedelta
        from core.database import execute_query
        
        # Get date range (default to last 30 days)
        days = int(request.args.get("days", 30))
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Query user count trends by day
        query = """
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as user_count
        FROM users 
        WHERE created_at >= %s AND created_at <= %s
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at) ASC
        """
        
        results = execute_query(query, (start_date, end_date))
        
        # Format data for chart
        chart_data = {
            "labels": [],
            "datasets": [{
                "label": "New Users",
                "data": [],
                "borderColor": "#10645c",
                "backgroundColor": "rgba(16, 100, 92, 0.1)",
                "fill": True,
                "tension": 0.4
            }]
        }
        
        # Create a complete date range
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            chart_data["labels"].append(date_str)
            
            # Find user count for this date
            user_count = 0
            for row in results:
                if str(row['date']) == date_str:
                    user_count = row['user_count']
                    break
            
            chart_data["datasets"][0]["data"].append(user_count)
            current_date += timedelta(days=1)
        
        # Calculate total users and growth
        total_users = execute_query("SELECT COUNT(*) as total FROM users")[0]['total']
        previous_period_users = execute_query("""
            SELECT COUNT(*) as total FROM users 
            WHERE created_at < %s
        """, (start_date,))[0]['total']
        
        growth_rate = 0
        if previous_period_users > 0:
            growth_rate = ((total_users - previous_period_users) / previous_period_users) * 100
        
        return jsonify({
            "status": "success",
            "chart_data": chart_data,
            "total_users": total_users,
            "growth_rate": round(growth_rate, 1),
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        
    except Exception as e:
        print(f"Error getting user count trends: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/dashboard/player/<int:player_id>/activities")
@login_required
@admin_required
def get_player_activities(player_id):
    """Get activity history for a specific player"""
    try:
        limit = int(request.args.get("limit", 100))
        activities = get_player_activity_history(player_id=player_id, limit=limit)

        return jsonify(
            {"status": "success", "player_id": player_id, "activities": activities}
        )

    except Exception as e:
        print(f"Error getting player activities: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/dashboard/team/<int:team_id>/activities")
@login_required
@admin_required
def get_team_activities(team_id):
    """Get activity history for a specific team"""
    try:
        limit = int(request.args.get("limit", 100))
        activities = get_team_activity_history(team_id=team_id, limit=limit)

        return jsonify(
            {"status": "success", "team_id": team_id, "activities": activities}
        )

    except Exception as e:
        print(f"Error getting team activities: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/fix-team-assignments", methods=["POST"])
@login_required
def fix_team_assignments():
    """Fix team assignments for existing users who don't have teams assigned"""
    try:
        # Check admin permissions
        if not is_user_admin(session["user"]["email"]):
            return jsonify({"error": "Admin access required"}), 403

        # Run the team assignment fix
        result = fix_team_assignments_for_existing_users()

        if result["success"]:
            return jsonify(
                {
                    "success": True,
                    "message": result["message"],
                    "stats": {
                        "total_players": result["total_players"],
                        "fixed_count": result["fixed_count"],
                        "failed_count": result["failed_count"],
                    },
                }
            )
        else:
            return jsonify({"success": False, "error": result["error"]}), 500

    except Exception as e:
        print(f"Error in admin team assignment fix: {str(e)}")
        return jsonify({"error": "Failed to fix team assignments"}), 500


# ==========================================
# ENHANCED USER IMPERSONATION ENDPOINTS
# ==========================================

@admin_bp.route("/api/admin/users-for-impersonation")
@login_required
@admin_required
def get_users_for_impersonation():
    """Get all users with their player contexts for impersonation dropdown"""
    try:
        from app.services.admin_service import get_all_users_with_player_contexts
        users = get_all_users_with_player_contexts()
        return jsonify(users)
    except Exception as e:
        print(f"Error getting users for impersonation: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/start-impersonation", methods=["POST"])
@login_required
@admin_required
def start_impersonation():
    """Start impersonating another user in a specific player context (admin only)"""
    try:
        data = request.get_json()
        target_email = data.get("user_email")
        target_player_id = data.get("tenniscores_player_id")  # Can be null for users without player contexts
        
        if not target_email:
            return jsonify({"error": "User email is required"}), 400
        
        # Verify the target user exists
        target_user = execute_query_one(
            "SELECT * FROM users WHERE email = %s", [target_email]
        )
        
        if not target_user:
            return jsonify({"error": "Target user not found"}), 404
        
        # Prevent admins from impersonating other admins
        if target_user.get("is_admin"):
            return jsonify({"error": "Cannot impersonate other admin users"}), 403
        
        # Handle users with and without player contexts
        player_association = None
        if target_player_id:
            # Verify the user has access to this player ID
            player_association = execute_query_one(
                """
                SELECT upa.*, p.first_name as player_first_name, p.last_name as player_last_name,
                       c.name as club_name, s.name as series_name, l.league_name, l.league_id, l.id as league_db_id,
                       t.id as team_id, t.team_name, p.club_id, p.series_id
                FROM user_player_associations upa
                JOIN users u ON upa.user_id = u.id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                JOIN leagues l ON p.league_id = l.id
                JOIN teams t ON p.team_id = t.id
                WHERE u.email = %s AND upa.tenniscores_player_id = %s
                """, 
                [target_email, target_player_id]
            )
            
            if not player_association:
                return jsonify({"error": "User does not have access to this player ID"}), 403
        
        # Backup current admin session before impersonation
        admin_session_backup = dict(session["user"])
        
        # If a specific player was selected, update the user's league_context to that player's league
        if player_association:
            try:
                execute_query(
                    "UPDATE users SET league_context = %s WHERE email = %s",
                    [player_association["league_db_id"], target_email]
                )
                print(f"[IMPERSONATION] Set league_context to {player_association['league_db_id']} for {target_email}")
            except Exception as e:
                print(f"[IMPERSONATION] Warning: Could not set league_context: {e}")
        
        # Get target user's full session data using the session service
        from app.services.session_service import get_session_data_for_user, get_session_data_for_user_team
        
        # If a specific player context was selected, use team-specific session building
        if player_association and player_association.get("team_id"):
            print(f"[IMPERSONATION] Building session for specific team: {player_association['team_id']} ({player_association['club_name']}, {player_association['series_name']})")
            target_session_data = get_session_data_for_user_team(target_email, player_association["team_id"])
        else:
            # Use generic session building (respects league_context)
            print(f"[IMPERSONATION] Building generic session data for {target_email}")
            target_session_data = get_session_data_for_user(target_email)
        
        if not target_session_data:
            return jsonify({"error": "Failed to build session data for target user"}), 500
        
        # Preserve admin status for impersonation
        target_session_data["is_admin"] = admin_session_backup.get("is_admin", False)
        
        # Store impersonation state in session
        session["impersonation_active"] = True
        session["original_admin_session"] = admin_session_backup
        session["impersonated_user_email"] = target_email
        session["impersonated_player_id"] = target_player_id  # Can be None
        
        # Replace current session with target user's session
        session["user"] = target_session_data
        session.modified = True
        
        # Log the impersonation start with or without player context
        if player_association:
            log_details = f"Started impersonating user: {target_email} as player: {target_player_id} ({player_association['club_name']}, {player_association['series_name']})"
            success_message = f"Successfully started impersonating {target_email} as {player_association['player_first_name']} {player_association['player_last_name']}"
            player_context = {
                "tenniscores_player_id": target_player_id,
                "player_name": f"{player_association['player_first_name']} {player_association['player_last_name']}",
                "club_name": player_association['club_name'],
                "series_name": player_association['series_name'],
                "league_name": player_association['league_name']
            }
        else:
            log_details = f"Started impersonating user: {target_email} (no player context)"
            success_message = f"Successfully started impersonating {target_email} (no player context)"
            player_context = None
        
        log_admin_action(
            admin_session_backup["email"],
            "start_impersonation",
            log_details
        )
        
        log_user_activity(
            admin_session_backup["email"],
            "admin_action",
            action="start_impersonation",
            details=f"Started impersonating {target_email} as {target_player_id or 'no player context'}",
        )
        
        return jsonify({
            "success": True,
            "message": success_message,
            "impersonated_user": {
                "email": target_email,
                "first_name": target_session_data.get("first_name", ""),
                "last_name": target_session_data.get("last_name", ""),
                "player_context": player_context
            }
        })
        
    except Exception as e:
        print(f"Error starting impersonation: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to start impersonation: {str(e)}"}), 500


@admin_bp.route("/api/admin/stop-impersonation", methods=["POST"])
@login_required
def stop_impersonation():
    """Stop impersonating and restore original admin session"""
    try:
        # Check if currently impersonating
        if not session.get("impersonation_active"):
            return jsonify({"error": "Not currently impersonating"}), 400
        
        # Get original admin session
        original_admin_session = session.get("original_admin_session")
        impersonated_email = session.get("impersonated_user_email")
        impersonated_player_id = session.get("impersonated_player_id")
        
        if not original_admin_session:
            return jsonify({"error": "Original admin session not found"}), 500
        
        # Verify the original session belongs to an admin
        if not original_admin_session.get("is_admin"):
            return jsonify({"error": "Original session is not an admin"}), 403
        
        # Restore original admin session
        session["user"] = original_admin_session
        
        # Clear impersonation state
        session.pop("impersonation_active", None)
        session.pop("original_admin_session", None)
        session.pop("impersonated_user_email", None)
        session.pop("impersonated_player_id", None)
        session.modified = True
        
        # Log the impersonation stop
        log_admin_action(
            original_admin_session["email"],
            "stop_impersonation",
            f"Stopped impersonating user: {impersonated_email} (player: {impersonated_player_id})"
        )
        
        log_user_activity(
            original_admin_session["email"],
            "admin_action",
            action="stop_impersonation",
            details=f"Stopped impersonating {impersonated_email} ({impersonated_player_id})",
        )
        
        return jsonify({
            "success": True,
            "message": "Successfully stopped impersonation and restored admin session"
        })
        
    except Exception as e:
        print(f"Error stopping impersonation: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to stop impersonation: {str(e)}"}), 500


@admin_bp.route("/api/admin/impersonation-status")
@login_required  
def get_impersonation_status():
    """Check current impersonation status"""
    try:
        is_impersonating = session.get("impersonation_active", False)
        
        if is_impersonating:
            # Get impersonated user info
            current_user = session.get("user", {})
            original_admin = session.get("original_admin_session", {})
            impersonated_player_id = session.get("impersonated_player_id")
            
            return jsonify({
                "is_impersonating": True,
                "impersonated_user": {
                    "email": current_user.get("email"),
                    "first_name": current_user.get("first_name"),
                    "last_name": current_user.get("last_name"),
                    "tenniscores_player_id": impersonated_player_id,
                    "player_context": current_user.get("primary_player", {})
                },
                "original_admin": {
                    "email": original_admin.get("email"),
                    "first_name": original_admin.get("first_name"),
                    "last_name": original_admin.get("last_name")
                }
            })
        else:
            return jsonify({
                "is_impersonating": False
            })
            
    except Exception as e:
        print(f"Error checking impersonation status: {str(e)}")
        return jsonify({"error": f"Failed to check impersonation status: {str(e)}"}), 500


@admin_bp.route('/create-groups-tables', methods=['GET'])
@admin_required
def create_groups_tables():
    """Temporary route to create groups tables on staging"""
    try:
        from app.models.database_models import db
        
        # Create groups table
        db.engine.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                creator_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_groups_creator_user_id 
                    FOREIGN KEY (creator_user_id) 
                    REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        
        # Create group_members table
        db.engine.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id SERIAL PRIMARY KEY,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by_user_id INTEGER NOT NULL,
                CONSTRAINT fk_group_members_group_id 
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                CONSTRAINT fk_group_members_user_id 
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_group_members_added_by_user_id 
                    FOREIGN KEY (added_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT uc_unique_group_member UNIQUE (group_id, user_id)
            );
        """)
        
        # Create indexes
        db.engine.execute("CREATE INDEX IF NOT EXISTS idx_groups_creator ON groups(creator_user_id);")
        db.engine.execute("CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(name);")
        db.engine.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);")
        db.engine.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id);")
        
        # Verify tables exist
        result = db.engine.execute("SELECT COUNT(*) FROM groups;").fetchone()
        groups_count = result[0] if result else 0
        
        return f"SUCCESS: Groups tables created! Groups table has {groups_count} rows."
        
    except Exception as e:
        return f"ERROR: Failed to create groups tables: {str(e)}", 500


@admin_bp.route("/api/admin/notifications/status")
@login_required
@admin_required
def get_notifications_status():
    """Get Twilio configuration status"""
    try:
        from app.services.notifications_service import get_twilio_status
        
        status = get_twilio_status()
        return jsonify({"status": "success", "twilio_status": status})
    
    except Exception as e:
        print(f"Error getting notification status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/notifications/predefined-messages")
@login_required
@admin_required
def get_predefined_messages():
    """Get predefined message templates"""
    try:
        from app.services.notifications_service import get_predefined_messages
        
        messages = get_predefined_messages()
        return jsonify({"status": "success", "messages": messages})
    
    except Exception as e:
        print(f"Error getting predefined messages: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/admin/notifications/send-sms", methods=["POST"])
@login_required
@admin_required
def send_test_sms():
    """Send a test SMS message"""
    try:
        from app.services.notifications_service import send_sms_notification
        
        data = request.json
        to_number = data.get("to_number", "").strip()
        message = data.get("message", "").strip()
        test_mode = data.get("test_mode", False)
        
        if not to_number:
            return jsonify({"success": False, "error": "Phone number is required"}), 400
        
        if not message:
            return jsonify({"success": False, "error": "Message content is required"}), 400
        
        # Log admin action
        admin_email = session["user"]["email"]
        admin_name = f"{session['user'].get('first_name', '')} {session['user'].get('last_name', '')}"
        
        log_admin_action(
            admin_email=admin_email,
            action="send_test_sms",
            details={
                "to_number": to_number,
                "message_preview": message[:50] + "..." if len(message) > 50 else message,
                "test_mode": test_mode,
                "message_length": len(message)
            }
        )
        
        # Send the SMS
        result = send_sms_notification(to_number, message, test_mode=test_mode)
        
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    except Exception as e:
        print(f"Error sending test SMS: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# DETAILED LOGGING NOTIFICATIONS ENDPOINTS
# ==========================================

@admin_bp.route("/api/admin/detailed-logging-notifications/status")
@login_required
@admin_required
def get_detailed_logging_notifications_status():
    """Get the current status of detailed logging notifications"""
    try:
        from app.services.admin_service import get_detailed_logging_notifications_setting
        
        is_enabled = get_detailed_logging_notifications_setting()
        
        return jsonify({
            "success": True,
            "enabled": is_enabled,
            "admin_phone": "773-213-8911",  # Ross's phone number
            "feature_description": "Send SMS alert to admin for every user activity when enabled"
        })
        
    except Exception as e:
        print(f"Error getting detailed logging notifications status: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/detailed-logging-notifications/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_detailed_logging_notifications():
    """Enable or disable detailed logging notifications"""
    try:
        from app.services.admin_service import (
            get_detailed_logging_notifications_setting,
            set_detailed_logging_notifications_setting
        )
        
        data = request.get_json()
        enabled = data.get("enabled")
        
        if enabled is None:
            return jsonify({"success": False, "error": "enabled parameter is required"}), 400
        
        # Validate that it's a boolean
        if not isinstance(enabled, bool):
            return jsonify({"success": False, "error": "enabled must be true or false"}), 400
        
        admin_email = session["user"]["email"]
        
        # Set the new value
        success = set_detailed_logging_notifications_setting(enabled, admin_email)
        
        if success:
            status_text = "enabled" if enabled else "disabled"
            
            return jsonify({
                "success": True,
                "enabled": enabled,
                "message": f"Detailed logging notifications {status_text} successfully",
                "admin_phone": "773-213-8911"
            })
        else:
            return jsonify({"success": False, "error": "Failed to update setting"}), 500
        
    except Exception as e:
        print(f"Error toggling detailed logging notifications: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# TEAM NOTIFICATIONS ENDPOINTS
# ==========================================

@admin_bp.route("/api/team-notifications/team-info")
@login_required
def get_team_notifications_team_info():
    """Get team information for notifications"""
    try:
        user = session["user"]
        user_id = user["id"]
        
        # Get user's team information
        team_query = """
            SELECT 
                t.id as team_id,
                t.team_name as team_name,
                l.league_name as league_name,
                s.name as series_name,
                COUNT(p.id) as member_count,
                COUNT(CASE WHEN u.phone_number IS NOT NULL AND u.phone_number != '' THEN 1 END) as members_with_phones
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            JOIN series s ON t.series_id = s.id
            JOIN players p ON t.id = p.team_id
            LEFT JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            LEFT JOIN users u ON upa.user_id = u.id
            WHERE t.id = (
                SELECT DISTINCT p2.team_id
                FROM players p2
                JOIN user_player_associations upa2 ON p2.tenniscores_player_id = upa2.tenniscores_player_id
                WHERE upa2.user_id = %s AND p2.team_id IS NOT NULL
                LIMIT 1
            )
            GROUP BY t.id, t.team_name, l.league_name, s.name
            LIMIT 1
        """
        
        team_info = execute_query_one(team_query, [user_id])
        
        if not team_info:
            return jsonify({
                "status": "error",
                "error": "No team found for user"
            }), 404
        
        return jsonify({
            "status": "success",
            "team_info": {
                "team_id": team_info["team_id"],
                "team_name": team_info["team_name"],
                "league_name": team_info["league_name"],
                "series_name": team_info["series_name"],
                "member_count": team_info["member_count"],
                "members_with_phones": team_info["members_with_phones"]
            }
        })
        
    except Exception as e:
        print(f"Error getting team info for notifications: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500


@admin_bp.route("/api/team-notifications/templates")
@login_required
def get_team_notification_templates():
    """Get team notification templates"""
    try:
        from app.services.notifications_service import get_team_notification_templates
        
        templates = get_team_notification_templates()
        return jsonify({"status": "success", "templates": templates})
        
    except Exception as e:
        print(f"Error getting team notification templates: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500


@admin_bp.route("/api/team-notifications/send", methods=["POST"])
@login_required
def send_team_notification():
    """Send notification to team members"""
    try:
        from app.services.notifications_service import send_sms_notification
        
        data = request.json
        message = data.get("message", "").strip()
        test_mode = data.get("test_mode", False)
        selected_recipients = data.get("recipients", [])  # Get selected recipients from frontend
        
        if not message:
            return jsonify({"success": False, "error": "Message content is required"}), 400
        
        if len(message) > 1600:
            return jsonify({"success": False, "error": "Message too long (max 1600 characters)"}), 400
        
        user = session["user"]
        user_id = user["id"]
        
        # Determine which team members to send to
        if selected_recipients and len(selected_recipients) > 0:
            # Send to specifically selected recipients
            print(f"Sending SMS to {len(selected_recipients)} selected recipients")
            print(f"Selected recipients data: {selected_recipients}")
            
            # Use the selected recipients directly instead of doing a database lookup
            # This prevents sending to multiple users with the same phone number
            team_members = []
            for r in selected_recipients:
                name = r.get('name', '')
                phone = r.get('phone', '')
                
                if not phone:
                    continue
                    
                # Parse name into first and last
                name_parts = name.split(' ', 1)
                first_name = name_parts[0] if len(name_parts) > 0 else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                team_members.append({
                    'id': None,  # Not needed for SMS sending
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone
                })
            
            print(f"Using {len(team_members)} selected recipients directly")
            
        else:
            # Send to all team members (when "All Team Members" is selected)
            print(f"Sending SMS to all team members")
            
            # Get team members with phone numbers
            members_query = """
                SELECT DISTINCT
                    u.id,
                    u.first_name,
                    u.last_name,
                    u.phone_number
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN teams t ON p.team_id = t.id
                WHERE t.id = (
                    SELECT DISTINCT p2.team_id
                    FROM players p2
                    JOIN user_player_associations upa2 ON p2.tenniscores_player_id = upa2.tenniscores_player_id
                    WHERE upa2.user_id = %s AND p2.team_id IS NOT NULL
                    LIMIT 1
                )
                AND u.phone_number IS NOT NULL 
                AND u.phone_number != ''
                AND u.id != %s  -- Don't send to self
            """
            
            team_members = execute_query(members_query, [user_id, user_id])
        
        print(f"Found {len(team_members)} team members to send SMS to")
        team_member_info = []
        for m in team_members:
            team_member_info.append(f"{m['first_name']} {m['last_name']} ({m['phone_number']})")
        print(f"Team members: {team_member_info}")
        
        if not team_members:
            return jsonify({
                "success": False,
                "error": "No team members with phone numbers found"
            }), 400
        
        # Log the action
        log_user_activity(
            user["email"],
            "team_notification_sent",
            action="send_team_notification",
            details={
                "recipient_count": len(team_members),
                "message_preview": message[:50] + "..." if len(message) > 50 else message,
                "test_mode": test_mode
            }
        )
        
        # Deduplicate phone numbers to avoid sending multiple SMS to the same number
        unique_phones = {}
        for member in team_members:
            phone = member["phone_number"]
            if phone not in unique_phones:
                unique_phones[phone] = {
                    "phone": phone,
                    "members": []
                }
            unique_phones[phone]["members"].append(f"{member['first_name']} {member['last_name']}")
        
        print(f"Sending SMS to {len(unique_phones)} unique phone numbers (covering {len(team_members)} team members)")
        
        # Send SMS to each unique phone number
        successful_sends = 0
        failed_sends = 0
        send_results = []
        
        for phone, phone_data in unique_phones.items():
            try:
                result = send_sms_notification(
                    to_number=phone,
                    message=message,
                    test_mode=test_mode
                )
                
                if result["success"]:
                    successful_sends += 1
                    # Create result entry for each member with this phone number
                    for member_name in phone_data["members"]:
                        send_results.append({
                            "name": member_name,
                            "phone": phone,
                            "status": "sent",
                            "message_sid": result.get("message_sid")
                        })
                else:
                    failed_sends += 1
                    # Create result entry for each member with this phone number
                    for member_name in phone_data["members"]:
                        send_results.append({
                            "name": member_name,
                            "phone": phone,
                            "status": "failed",
                            "error": result.get("error")
                        })
                    
            except Exception as e:
                failed_sends += 1
                # Create result entry for each member with this phone number
                for member_name in phone_data["members"]:
                    send_results.append({
                        "name": member_name,
                        "phone": phone,
                        "status": "failed",
                        "error": f"Unexpected error: {str(e)}"
                    })
        
        return jsonify({
            "success": True,
            "message": f"Team notification processed",
            "recipients_sent": successful_sends,
            "recipients_failed": failed_sends,
            "total_recipients": len(team_members),
            "test_mode": test_mode,
            "send_results": send_results
        })
        
    except Exception as e:
        print(f"Error sending team notification: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route("/api/admin/pre-register-user", methods=["POST"])
@login_required
@admin_required
def api_pre_register_user():
    """Admin API endpoint to pre-register a single user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        # Extract and validate required fields
        email = data.get("email", "").strip().lower()
        first_name = data.get("firstName", "").strip()
        last_name = data.get("lastName", "").strip()
        phone_number = data.get("phoneNumber", "").strip()
        league_id = data.get("league", "").strip()
        club_name = data.get("club", "").strip()
        series_name = data.get("series", "").strip()
        
        # Registration options
        generate_password = data.get("generatePassword", True)
        send_notifications = data.get("sendNotifications", True)
        
        # Validate required fields
        missing_fields = []
        if not email:
            missing_fields.append("email")
        if not first_name:
            missing_fields.append("firstName")
        if not last_name:
            missing_fields.append("lastName")
        if not phone_number:
            missing_fields.append("phoneNumber")
        if not league_id:
            missing_fields.append("league")
        if not club_name:
            missing_fields.append("club")
        if not series_name:
            missing_fields.append("series")
        
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # ✅ PHONE NORMALIZATION: Normalize phone number before registration
        from utils.phone_utils import validate_and_normalize_phone_input
        
        phone_result = validate_and_normalize_phone_input(phone_number, "phone number")
        if not phone_result['success']:
            return jsonify({
                "success": False,
                "error": phone_result['error']
            }), 400
        
        normalized_phone = phone_result['normalized_phone']
        print(f"Admin pre-registration: Phone number normalized: '{phone_number}' -> '{normalized_phone}'")
        
        # Import the registration function
        from app.services.auth_service_refactored import register_user
        import secrets
        import string
        
        # Generate temporary password if requested
        temp_password = None
        if generate_password:
            # Generate secure temporary password
            alphabet = string.ascii_letters + string.digits
            temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
        else:
            # Use a default temporary password
            temp_password = "Rally2024!"
        
        # Log admin action
        admin_email = session["user"]["email"]
        log_admin_action(
            admin_email,
            "pre_register_user",
            {
                "target_email": email,
                "target_name": f"{first_name} {last_name}",
                "league_id": league_id,
                "club_name": club_name,
                "series_name": series_name,
                "phone_number": phone_number,
                "generate_password": generate_password,
                "send_notifications": send_notifications
            }
        )
        
        # Attempt to register the user
        registration_result = register_user(
            email=email,
            password=temp_password,
            first_name=first_name,
            last_name=last_name,
            league_id=league_id,
            club_name=club_name,
            series_name=series_name,
            phone_number=normalized_phone,
            ad_deuce_preference="Ad",  # Default
            dominant_hand="Right"     # Default
        )
        
        if not registration_result["success"]:
            return jsonify({
                "success": False,
                "error": registration_result["error"]
            }), 400
        
        # Send SMS notification if requested
        if send_notifications:
            try:
                from app.services.notifications_service import send_sms_message
                
                message = f"Welcome to Rally! Your account has been created.\n\nLogin at: https://lovetorally.com\nEmail: {email}\nTemp Password: {temp_password}\n\nPlease change your password after first login."
                
                # Format phone number for SMS (add +1 prefix)
                formatted_phone = f"+1{phone_number}"
                sms_result = send_sms_message(formatted_phone, message)
                
                if not sms_result["success"]:
                    # Log SMS failure but don't fail the registration
                    print(f"SMS notification failed for {email}: {sms_result.get('error', 'Unknown error')}")
                    
            except Exception as sms_error:
                # Log SMS error but don't fail the registration
                print(f"SMS notification error for {email}: {str(sms_error)}")
        
        # Return success response
        response_data = {
            "success": True,
            "message": f"User {first_name} {last_name} ({email}) has been successfully registered."
        }
        
        # Include temp password in response if generated
        if generate_password:
            response_data["tempPassword"] = temp_password
            
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in pre-register user: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Registration failed: {str(e)}"
        }), 500


@admin_bp.route('/admin/lineup-escrow-analytics')
@login_required
def admin_lineup_escrow_analytics():
    """Admin page for lineup escrow analytics."""
    if not session.get("user")["is_admin"]:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    analytics = get_lineup_escrow_analytics()
    
    if analytics is None:
        flash('Error loading analytics data.', 'error')
        return redirect(url_for('admin_index'))
    
    return render_template('admin/lineup_escrow_analytics.html', analytics=analytics)

@admin_bp.route('/admin/add-player')
@admin_required
def add_player_page():
    """Admin page for adding individual players"""
    return render_template('admin/add_player.html')

@admin_bp.route("/api/admin/add-player", methods=["POST"])
@admin_required
def add_player_api():
    """API endpoint to search for a player and show confirmation"""
    try:
        data = request.get_json()
        league_subdomain = data.get('league_subdomain')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        club = data.get('club')
        series = data.get('series')
        
        if not all([league_subdomain, first_name, last_name, club, series]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Import the player scraper service
        from app.services.player_scraper_service import PlayerScraperService
        
        # Create scraper service instance
        scraper_service = PlayerScraperService()
        
        # Search for the player (but don't save yet)
        result = scraper_service.search_for_player(league_subdomain, first_name, last_name, club, series)
        
        if result:
            return jsonify({
                "success": True,
                "message": "Player found! Please review the information below.",
                "player_data": result,
                "needs_confirmation": True
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Could not find player {first_name} {last_name} in {club}, {series}"
            }), 400
            
    except Exception as e:
        print(f"Error searching for player: {e}")
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/api/admin/confirm-add-player", methods=["POST"])
@admin_required
def confirm_add_player_api():
    """API endpoint to confirm and add a player after review"""
    try:
        data = request.get_json()
        league_subdomain = data.get('league_subdomain')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        club = data.get('club')
        series = data.get('series')
        player_data = data.get('player_data')  # Get the player data from frontend
        
        if not all([league_subdomain, first_name, last_name, club, series]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Import the player scraper service
        from app.services.player_scraper_service import PlayerScraperService
        
        # Create scraper service instance
        scraper_service = PlayerScraperService()
        
        # Now save the player to JSON and database using the provided player data
        result = scraper_service.save_player_data(league_subdomain, first_name, last_name, club, series, player_data)
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "message": f"Player {first_name} {last_name} has been successfully added to the system!",
                "player_data": result.get('player_data', {})
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error occurred')
            }), 400
            
    except Exception as e:
        print(f"Error confirming player addition: {e}")
        return jsonify({"error": str(e)}), 500


# ==========================================
# COCKPIT DASHBOARD HELPER FUNCTIONS
# ==========================================

def calculate_percentage_change(current, previous):
    """Calculate percentage change between two values"""
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)


def get_detailed_action_description(activity):
    """Get detailed description for an activity"""
    action_type = activity.get("action_type", "")
    base_description = activity.get("action_description", action_type)
    page = activity.get("page", "")
    
    # If we already have a proper description, use it
    if action_type == 'page_visit' and base_description and not base_description.startswith('page_visit'):
        return base_description
    
    # Add more context based on action type
    descriptions = {
        'page_visit': f"{format_page_name(page) if page else 'Unknown Page'}",
        'login': "Logged in successfully",
        'logout': "Logged out",
        'registration_successful': "New user registration completed",
        'registration_failed': "User registration failed",
        'player_search': "Searched for players",
        'team_switch': "Switched team context",
        'settings_update': "Updated user settings",
        'poll_voted': "Voted in poll",
        'poll_created': "Created new poll",
        'availability_update': "Updated availability",
        'ai_chat': "Used AI chat feature",
        'simulation_run': "Ran simulation",
        'score_submitted': "Submitted match score",
        'team_email': "Sent team email",
        'court_reservation': "Made court reservation",
        'admin_action': "Admin action performed",
        'user_action': "User action performed"
    }
    
    return descriptions.get(action_type, base_description)


def format_page_name(page: str) -> str:
    """Format page identifier into a readable display name - matches dashboard_service.py"""
    page_names = {
        # Mobile App Pages
        "mobile_home": "Home Page",
        "mobile_matches": "Matches",
        "mobile_rankings": "Rankings",
        "mobile_profile": "Profile",
        "mobile_view_schedule": "Schedule",
        "mobile_analyze_me": "Analyze Me",
        "mobile_my_team": "My Team Page",
        "mobile_settings": "Settings",
        "mobile_my_series": "My Series Page",
        "mobile_teams_players": "Teams & Players",
        "mobile_player_search": "Player Search",
        "mobile_my_club": "My Club Page",
        "mobile_player_stats": "Player Stats",
        "mobile_email_team": "Email Team",
        "mobile_practice_times": "Practice Times",
        "mobile_availability": "Availability",
        "mobile_availability_calendar": "Availability Calendar",
        "mobile_all_team_availability": "Team Availability",
        "mobile_team_schedule": "Team Schedule",
        "mobile_matchup_simulator": "Matchup Simulator",
        "mobile_polls": "Team Polls",
        "mobile_poll_vote": "Poll Vote",
        "mobile_ask_ai": "Ask AI",
        "mobile_find_subs": "Find Subs",
        "mobile_find_people_to_play": "Find People to Play",
        "mobile_lineup": "Lineup",
        "mobile_lineup_escrow": "Lineup Escrow",
        "mobile_improve": "Improve Game",
        "mobile_training_videos": "Training Videos",
        "mobile_reserve_court": "Reserve Court",
        "mobile_player_detail": "Player Detail",
        "mobile_track_byes_courts": "Track Byes & Courts",
        "mobile_create_pickup_game": "Create Pickup Game",
        "mobile_pickup_games": "Pickup Games",
        "mobile_rally": "Rally AI Chat",
        "mobile_schedule": "Schedule Page",
        # Utility Pages
        "track_byes_courts": "Track Byes & Courts",
        "contact_sub": "Contact Sub",
        "player_detail": "Player Detail",
        "pti_vs_opponents_analysis": "PTI vs Opponents Analysis",
        "find_people_to_play": "Find People to Play",
        "pickup_games": "Pickup Games",
        "private_groups": "Private Groups",
        "create_pickup_game": "Create Pickup Game",
        "reserve_court": "Reserve Court",
        "share_rally": "Share Rally",
        "create_team": "Create Team",
        "matchup_simulator": "Matchup Simulator",
        "polls": "Polls",
        "schedule_lesson": "Schedule Lesson",
        "email_team": "Email Team",
        "practice_times": "Practice Times",
        "availability": "Availability",
        "team_schedule": "Team Schedule",
        "player_search": "Player Search",
        "player_stats": "Player Stats",
        "my_series": "My Series",
        "analyze_me": "Analyze Me",
        "my_team": "My Team",
        "my_club": "My Club",
        "user_activity": "User Activity",
        "home_submenu": "Home Page",
        "home_alt1": "Home Page",
        "home_classic": "Home Page",
        # Admin Pages
        "admin": "Admin Dashboard",
        "admin_users": "Admin - User Management",
        "admin_leagues": "Admin - League Management",
        "admin_clubs": "Admin - Club Management",
        "admin_series": "Admin - Series Management",
        "admin_etl": "Admin - Data Import",
        "admin_user_activity": "Admin - User Activity",
        "admin_dashboard": "Admin - Activity Dashboard",
        "admin_cockpit": "Admin - Rally Cockpit",
        # Authentication Pages
        "login": "Login Page",
        "logout": "Logout",
        "register": "Registration Page",
        # API Endpoints
        "api": "API Endpoint",
        # Other Pages
        "pti_calculator": "PTI Calculator",
        "schedule": "Schedule Page",
        "matches": "Matches Page",
        "rankings": "Rankings Page",
        "profile": "Profile Page",
        "settings": "Settings Page",
        # Common patterns that might appear
        "home": "Home Page",
        "index": "Home Page",
        "main": "Main Page",
        "dashboard": "Dashboard",
        "welcome": "Welcome Page",
        "interstitial": "Welcome Page",
        "interstitial_welcome": "Welcome Page",
        "contact_sub": "Contact Substitute",
        "contact-sub": "Contact Substitute",
        "user_activity": "User Activity Page",
        "user-activity": "User Activity Page",
        "api": "API Endpoint",
        "static": "Static Resource",
        "favicon.ico": "Favicon",
        "robots.txt": "Robots File",
        "sitemap.xml": "Sitemap"
    }

    # Check for exact matches first
    if page in page_names:
        return page_names[page]
    
    # Handle pages that start with mobile/
    if page.startswith('mobile/'):
        clean_page = page.replace('mobile/', '').replace('-', '_')
        mobile_key = f"mobile_{clean_page}"
        if mobile_key in page_names:
            return page_names[mobile_key]
    
    # Handle admin pages
    if page.startswith('admin_') or page.startswith('admin/'):
        clean_page = page.replace('admin/', '').replace('admin_', '')
        return f"Admin - {clean_page.replace('_', ' ').title()}"
    
    # Handle API endpoints
    if page.startswith('api/'):
        return f"API - {page.replace('api/', '').replace('_', ' ').title()}"
    
    # Fallback: clean up the page name
    return page.replace('_', ' ').replace('-', ' ').title()


def parse_user_agent(user_agent):
    """Parse user agent string to extract browser and device info"""
    if not user_agent:
        return {"browser": "Unknown", "device": "Unknown"}
    
    browser = "Unknown"
    device = "Desktop"
    
    # Browser detection
    if "Chrome" in user_agent:
        browser = "Chrome"
    elif "Firefox" in user_agent:
        browser = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        browser = "Safari"
    elif "Edge" in user_agent:
        browser = "Edge"
    
    # Device detection
    if "Mobile" in user_agent or "Android" in user_agent:
        device = "Mobile"
    elif "Tablet" in user_agent or "iPad" in user_agent:
        device = "Tablet"
    
    return {"browser": browser, "device": device}


def get_location_info(ip_address):
    """Get location information from IP address (simplified)"""
    # This would typically use a geolocation service
    # For now, return basic info
    return {
        "country": "US",
        "region": "Unknown",
        "city": "Unknown"
    }


def get_session_context(activity):
    """Get session context information"""
    return {
        "is_impersonated": activity.get("is_impersonated", False),
        "session_duration": "Unknown",
        "page_views": 1
    }


def get_action_type_color(action_type):
    """Get color for action type"""
    color_map = {
        'page_visit': '#3B82F6',
        'login': '#10B981',
        'logout': '#6B7280',
        'registration_successful': '#10B981',
        'registration_failed': '#EF4444',
        'player_search': '#3B82F6',
        'team_switch': '#8B5CF6',
        'settings_update': '#F59E0B',
        'poll_voted': '#10B981',
        'poll_created': '#3B82F6',
        'availability_update': '#10B981',
        'ai_chat': '#8B5CF6',
        'simulation_run': '#F59E0B',
        'score_submitted': '#F59E0B',
        'team_email': '#3B82F6',
        'court_reservation': '#10B981',
        'admin_action': '#EF4444',
        'user_action': '#6B7280'
    }
    return color_map.get(action_type, '#6B7280')


def get_action_type_rgb(action_type):
    """Get RGB values for action type color"""
    color_map = {
        'page_visit': '59, 130, 246',
        'login': '16, 185, 129',
        'logout': '107, 114, 128',
        'registration_successful': '16, 185, 129',
        'registration_failed': '239, 68, 68',
        'player_search': '59, 130, 246',
        'team_switch': '139, 92, 246',
        'settings_update': '245, 158, 11',
        'poll_voted': '16, 185, 129',
        'poll_created': '59, 130, 246',
        'availability_update': '16, 185, 129',
        'ai_chat': '139, 92, 246',
        'simulation_run': '245, 158, 11',
        'score_submitted': '245, 158, 11',
        'team_email': '59, 130, 246',
        'court_reservation': '16, 185, 129',
        'admin_action': '239, 68, 68',
        'user_action': '107, 114, 128'
    }
    return color_map.get(action_type, '107, 114, 128')


def get_database_connection_count():
    """Get current database connection count"""
    try:
        # This would typically query the database for connection count
        return 5  # Simulated value
    except:
        return 0


def get_active_session_count():
    """Get current active session count"""
    try:
        # This would typically count active sessions
        return 12  # Simulated value
    except:
        return 0


def get_error_rate():
    """Get current error rate from actual system data"""
    try:
        # Check for failed activities or system errors in the last hour
        from datetime import datetime, timedelta
        
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Count total activities in the last hour
        total_query = """
        SELECT COUNT(*) as total_count
        FROM user_activity_logs 
        WHERE timestamp >= %s
        """
        
        # Count failed/error activities (you can expand this logic)
        error_query = """
        SELECT COUNT(*) as error_count
        FROM user_activity_logs 
        WHERE timestamp >= %s 
        AND (details LIKE '%error%' OR details LIKE '%failed%' OR details LIKE '%exception%')
        """
        
        total_result = execute_query_one(total_query, (one_hour_ago,))
        error_result = execute_query_one(error_query, (one_hour_ago,))
        
        total_count = total_result.get('total_count', 0) if total_result else 0
        error_count = error_result.get('error_count', 0) if error_result else 0
        
        if total_count == 0:
            return "0.0%"
        
        error_rate = (error_count / total_count) * 100
        return f"{error_rate:.1f}%"
        
    except Exception as e:
        print(f"Error calculating error rate: {e}")
        return "0.0%"  # Default to healthy state


def get_average_response_time():
    """Get average response time"""
    try:
        # This would typically calculate from performance metrics
        return "120ms"  # Simulated value
    except:
        return "Unknown"


