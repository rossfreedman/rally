"""
Admin routes blueprint - handles all administration functionality
This module contains routes for user management, system administration, and user activity tracking.
"""

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for, send_from_directory, Response, stream_template
from functools import wraps
import os
import sqlite3
import subprocess
import threading
import queue
import json
import time
import sys
from datetime import datetime
try:
    import select
except ImportError:
    select = None  # Windows doesn't have select module for pipes
from utils.auth import login_required
from database_utils import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from app.services.admin_service import (
    get_all_users, get_all_series_with_stats, update_user_info, 
    update_club_name, update_series_name, delete_user_by_email,
    get_user_activity_logs, is_user_admin, log_admin_action
)
import traceback

# Create admin blueprint
admin_bp = Blueprint('admin', __name__)

# Global variables for process management
active_processes = {
    'scraping': None,
    'importing': None
}

def admin_required(f):
    """Decorator to check if user is an admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"=== ADMIN_REQUIRED CHECK ===")
        print(f"User in session: {'user' in session}")
        if 'user' in session:
            print(f"User email: {session['user']['email']}")
        
        if 'user' not in session:
            print("No user in session, redirecting to login")
            flash('Please log in first.', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            print(f"Checking admin status for: {session['user']['email']}")
            if not is_user_admin(session['user']['email']):
                print(f"User {session['user']['email']} is not admin, redirecting to index")
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('serve_index'))
                
            print("Admin check passed, proceeding to admin function")
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error checking admin status: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            flash('An error occurred while checking permissions.', 'error')
            return redirect(url_for('serve_index'))
            
    return decorated_function

@admin_bp.route('/admin')
@login_required
@admin_required
def serve_admin():
    """Serve the admin dashboard"""
    print(f"=== SERVE_ADMIN FUNCTION CALLED ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"User in session: {session.get('user', 'No user')}")
    
    log_user_activity(session['user']['email'], 'page_visit', page='admin')
    
    # Always use the mobile admin template since it's responsive and works on all devices
    print("Rendering mobile admin template (responsive design)")
    return render_template('mobile/admin.html', session_data={'user': session['user']})

@admin_bp.route('/admin/users')
@login_required
@admin_required
def serve_admin_users():
    """Serve the admin users management page"""
    print(f"=== SERVE_ADMIN_USERS FUNCTION CALLED ===")
    
    log_user_activity(session['user']['email'], 'page_visit', page='admin_users')
    
    # Always use the mobile admin template since it's responsive and works on all devices
    return render_template('mobile/admin_users.html', session_data={'user': session['user']})

@admin_bp.route('/admin/leagues')
@login_required
@admin_required
def serve_admin_leagues():
    """Serve the admin leagues management page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_leagues')
    
    return render_template('mobile/admin_leagues.html', session_data={'user': session['user']})

@admin_bp.route('/admin/clubs')
@login_required
@admin_required
def serve_admin_clubs():
    """Serve the admin clubs management page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_clubs')
    
    return render_template('mobile/admin_clubs.html', session_data={'user': session['user']})

@admin_bp.route('/admin/series')
@login_required
@admin_required
def serve_admin_series():
    """Serve the admin series management page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_series')
    
    return render_template('mobile/admin_series.html', session_data={'user': session['user']})

@admin_bp.route('/admin/etl')
@login_required
@admin_required
def serve_admin_etl():
    """Serve the admin ETL management page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_etl')
    
    return render_template('mobile/admin_etl.html', session_data={'user': session['user']})

@admin_bp.route('/admin/user-activity')
@login_required
@admin_required
def serve_admin_user_activity():
    """Serve the admin user activity page"""
    log_user_activity(session['user']['email'], 'page_visit', page='admin_user_activity')
    return render_template('mobile/admin_user_activity.html', session_data={'user': session['user']})

# ==========================================
# ETL API ENDPOINTS
# ==========================================

@admin_bp.route('/api/admin/etl/status')
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
            'database_connected': database_connected,
            'last_scrape': None,  # TODO: Implement status tracking
            'last_import': None,  # TODO: Implement status tracking
            'scraping_active': bool(active_processes['scraping']),
            'importing_active': bool(active_processes['importing'])
        }
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/etl/clear-processes', methods=['POST'])
@login_required
@admin_required
def clear_etl_processes():
    """Clear any stuck ETL processes"""
    try:
        user_email = session['user']['email']
        
        # Clear active processes
        active_processes['scraping'] = None
        active_processes['importing'] = None
        
        log_user_activity(
            user_email, 
            'admin_action', 
            action='clear_etl_processes',
            details="Cleared stuck ETL processes"
        )
        
        return jsonify({'status': 'success', 'message': 'ETL processes cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/etl/scrape')
@login_required
@admin_required
def start_scraping():
    """Start the scraping process with real-time updates via Server-Sent Events"""
    league = request.args.get('league', '').strip()
    scrapers = request.args.get('scrapers', '').split(',')
    
    if not league:
        return jsonify({'error': 'League subdomain is required'}), 400
    
    if active_processes['scraping']:
        print(f"Scraping process already active, rejecting new request")
        return jsonify({'error': 'Scraping process already running'}), 409
    
    # Capture session data before generator starts
    user_email = session['user']['email']
    
    def generate_scrape_events():
        """Generator function for server-sent events"""
        try:
            start_time = datetime.now()
            
            # Log the start of scraping
            log_user_activity(
                user_email, 
                'admin_action', 
                action='start_scraping',
                details=f"Started scraping for league: {league}, scrapers: {scrapers}"
            )
            
            start_msg = f"🚀 Starting scraping process for league: {league.upper()}"
            time_str = start_time.strftime('%H:%M:%S')
            time_msg = f"⏰ Process started at: {time_str}"
            url_msg = f"📊 Target URL: https://{league}.tenniscores.com"
            
            yield f"data: {json.dumps({'type': 'output', 'message': start_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': time_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': url_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 5})}\n\n"
            
            # Determine which scrapers to run
            if 'all' in scrapers:
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
                        for update in run_individual_scraper_generator(league, scraper, i, total_scrapers):
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
            active_processes['scraping'] = None
            print("Scraping process cleaned up")
    
    # Set up the scraping process
    active_processes['scraping'] = True
    
    return Response(
        generate_scrape_events(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )

@admin_bp.route('/api/admin/etl/import')
@login_required
@admin_required
def start_import():
    """Start the database import process with real-time updates via Server-Sent Events"""
    if active_processes['importing']:
        return jsonify({'error': 'Import process already running'}), 409
    
    # Capture session data before generator starts
    user_email = session['user']['email']
    
    def generate_import_events():
        """Generator function for server-sent events"""
        try:
            import_start_time = datetime.now()
            
            # Log the start of import
            log_user_activity(
                user_email, 
                'admin_action', 
                action='start_import',
                details="Started database import process"
            )
            
            import_msg = f"🗄️ Starting database import process..."
            time_str = import_start_time.strftime('%H:%M:%S')
            time_msg = f"⏰ Import started at: {time_str}"
            
            yield f"data: {json.dumps({'type': 'output', 'message': import_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'output', 'message': time_msg, 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 5})}\n\n"
            
            # Step 1: Consolidate league data
            yield f"data: {json.dumps({'type': 'output', 'message': '📋 Step 1: Consolidating league JSON files...', 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 20})}\n\n"
            
            # Run consolidation and yield updates
            consolidation_success = False
            try:
                for update in run_consolidation_script_generator():
                    yield update
                    if '"success": true' in update:
                        consolidation_success = True
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Critical error in consolidation: {str(e)}'})}\n\n"
                print(f"Error in consolidation: {traceback.format_exc()}")
                consolidation_success = False
            
            if not consolidation_success:
                yield f"data: {json.dumps({'type': 'error', 'message': '❌ Failed to consolidate league data'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'output', 'message': '✅ League data consolidation completed', 'status': 'success'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 50})}\n\n"
            
            # Step 2: Import to database
            yield f"data: {json.dumps({'type': 'output', 'message': '💾 Step 2: Importing data to PostgreSQL database...', 'status': 'info'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'progress': 70})}\n\n"
            
            # Run import and yield updates
            import_success = False
            try:
                for update in run_import_script_generator():
                    yield update
                    if '"success": true' in update:
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
                success_msg = f"✅ Database import completed successfully in {duration_str}"
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
            active_processes['importing'] = None
            print("Import process cleaned up")
    
    # Set up the import process
    active_processes['importing'] = True
    
    return Response(
        generate_import_events(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )

# ==========================================
# ETL HELPER FUNCTIONS
# ==========================================

def enhance_scraper_message(message, scraper_type):
    """Enhance scraper output messages with more descriptive information"""
    if not message:
        return message
    
    # Enhanced descriptions for stats scraper
    if scraper_type == 'scraper_stats':
        if 'Found' in message and 'series' in message:
            return f"🏆 Discovery: {message}"
        elif 'Processing' in message and 'Series' in message:
            return f"📊 Analyzing: {message}"
        elif 'Navigating to URL' in message:
            return f"🌐 Loading page: {message}"
        elif 'Looking for Statistics link' in message:
            return f"🔍 Searching for statistics section on page"
        elif 'Found Statistics link' in message:
            return f"✅ Statistics section located - accessing team data"
        elif 'Found' in message and 'teams' in message:
            return f"📈 Team data extraction: {message}"
        elif 'Successfully scraped stats' in message:
            return f"✅ Data collection: {message}"
        elif 'Discovery Phase' in message:
            return f"🔍 {message} - scanning league structure"
        elif 'Scraping Phase' in message:
            return f"⚡ {message} - extracting team statistics"
        elif 'SCRAPING COMPLETE' in message:
            return f"🎉 {message} - all team statistics collected"
        elif 'Skipping library/PDF' in message:
            return f"⏸️ Filter: {message} - excluding non-statistics content"
        elif 'library' in message.lower() and 'skipping' in message.lower():
            return f"⏸️ Content filter: {message}"
    
    # Enhanced descriptions for other scrapers
    elif scraper_type == 'scraper_schedule':
        if 'Found' in message and 'matches' in message:
            return f"📅 Match schedule: {message}"
        elif 'Processing schedule' in message:
            return f"⏰ Schedule analysis: {message}"
    
    elif scraper_type == 'scraper_players':
        if 'Found' in message and 'players' in message:
            return f"👥 Player roster: {message}"
        elif 'Processing player' in message:
            return f"🎾 Player data: {message}"
    
    elif scraper_type == 'scraper_match_scores':
        if 'Found' in message and 'matches' in message:
            return f"🏆 Match results: {message}"
        elif 'Processing match' in message:
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
            os.path.join(project_root, 'etl', 'scrapers', 'master_scraper.py'),
            os.path.join(project_root, 'scrapers', 'master_scraper.py'),
            os.path.join(os.getcwd(), 'etl', 'scrapers', 'master_scraper.py'),
            os.path.join(os.getcwd(), 'scrapers', 'master_scraper.py'),
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
        time_str = master_start_time.strftime('%H:%M:%S')
        start_msg = f"⏰ Master scraper started at: {time_str}"
        path_msg = f"📁 Script path: {master_scraper_path}"
        
        yield f"data: {json.dumps({'type': 'output', 'message': master_msg, 'status': 'info'})}\n\n"
        yield f"data: {json.dumps({'type': 'output', 'message': start_msg, 'status': 'info'})}\n\n"
        yield f"data: {json.dumps({'type': 'output', 'message': path_msg, 'status': 'info'})}\n\n"
        
        # Set up environment for subprocess
        env = os.environ.copy()
        env['PYTHONPATH'] = project_root
        
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
            universal_newlines=True
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
                if line and not line.startswith('Enter league') and not line.startswith('Ready to start'):
                    yield f"data: {json.dumps({'type': 'output', 'message': line, 'status': 'info'})}\n\n"
                    
                    # Update progress based on output
                    if '✅' in line or 'completed' in line.lower():
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
            os.path.join(project_root, 'etl', 'scrapers'),
            os.path.join(project_root, 'scrapers'),
            os.path.join(os.getcwd(), 'etl', 'scrapers'),
            os.path.join(os.getcwd(), 'scrapers'),
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
                    py_files = [f for f in files if f.endswith('.py')]
                    yield f"data: {json.dumps({'type': 'output', 'message': '📋 Available scrapers: ' + ', '.join(py_files), 'status': 'info'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'output', 'message': '❌ Scrapers directory does not exist: ' + scrapers_dir, 'status': 'error'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'output', 'message': '❌ Error listing scrapers: ' + str(e), 'status': 'error'})}\n\n"
            
            return
        
        # Enhanced logging with progress and timing
        step_msg = f"🚀 Step {scraper_index + 1}/{total_scrapers}: Running {scraper}"
        time_str = scraper_start_time.strftime('%H:%M:%S')
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
            chrome_paths = ['google-chrome', 'chromium', 'chromium-browser', '/usr/bin/google-chrome', '/opt/google/chrome/chrome']
            chrome_found = False
            
            for chrome_path in chrome_paths:
                try:
                    chrome_check = subprocess.run(['which', chrome_path], capture_output=True, text=True, timeout=5)
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
        env['PYTHONPATH'] = project_root
        env['PYTHONUNBUFFERED'] = '1'  # Force unbuffered output for real-time streaming
        
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
                universal_newlines=True
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
            chrome_init_timeout = 300  # 5 minute timeout for Chrome initialization (after detection)
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
                current_no_output_timeout = no_output_timeout if chrome_init_phase else 120
                if (current_time - last_output_time).total_seconds() > current_no_output_timeout:
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
                        for line in remaining_output.strip().split('\n'):
                            if line.strip():
                                yield f"data: {json.dumps({'type': 'output', 'message': f'📋 {line.strip()}', 'status': 'info'})}\n\n"
                    break
                
                # Use select to check if output is available (non-blocking)
                if select and sys.platform != 'win32':
                    ready, _, _ = select.select([process.stdout, process.stderr], [], [], 1)  # 1 second timeout
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
                                    if not line.startswith('Enter league') and not line.startswith('League subdomain'):
                                        enhanced_message = enhance_scraper_message(line, scraper)
                                        yield f"data: {json.dumps({'type': 'output', 'message': enhanced_message, 'status': 'info'})}\n\n"
                                        
                                        # Check if we've moved past Chrome initialization - more aggressive detection
                                        if chrome_init_phase and any(phrase in line.lower() for phrase in [
                                            'starting tennis', 'session start', 'processing', 'found', 'discovery', 'navigating', 
                                            'chrome', 'driver', 'scraper', 'series', 'url', 'statistics', 'teams', 'completed'
                                        ]):
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
                                if not line.startswith('Enter league') and not line.startswith('League subdomain'):
                                    enhanced_message = enhance_scraper_message(line, scraper)
                                    yield f"data: {json.dumps({'type': 'output', 'message': enhanced_message, 'status': 'info'})}\n\n"
                                    
                                    # Check if we've moved past Chrome initialization (Windows) - more aggressive detection
                                    if chrome_init_phase and any(phrase in line.lower() for phrase in [
                                        'starting tennis', 'session start', 'processing', 'found', 'discovery', 'navigating', 
                                        'chrome', 'driver', 'scraper', 'series', 'url', 'statistics', 'teams', 'completed'
                                    ]):
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
                if (current_time - last_status_time).total_seconds() > 15:  # Every 15 seconds
                    elapsed = current_time - scraper_start_time
                    elapsed_str = f"{int(elapsed.total_seconds())}s"
                    if output_count > 0:
                        if scraper == 'scraper_stats':
                            status_msg = f"⏱️ Statistics extraction running for {elapsed_str} - processed {output_count} data points"
                        elif scraper == 'scraper_schedule':
                            status_msg = f"⏱️ Schedule scraping running for {elapsed_str} - processed {output_count} schedule entries"
                        elif scraper == 'scraper_players':
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
                for error_line in stderr_output.strip().split('\n'):
                    if error_line.strip():
                        # Parse specific Chrome errors
                        if 'chrome' in error_line.lower() or 'selenium' in error_line.lower():
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
            timeout_msg = f"⏰ {scraper} timed out after {duration_str} (10 minute limit reached)"
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

def run_consolidation_script_generator():
    """Generator that runs the consolidation script and yields progress updates"""
    try:
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        # Try multiple possible locations for consolidation script
        possible_consolidation_paths = [
            os.path.join(project_root, 'etl', 'database_import', 'consolidate_league_jsons_to_all.py'),
            os.path.join(project_root, 'etl', 'consolidate_league_jsons_to_all.py'),
            os.path.join(os.getcwd(), 'etl', 'database_import', 'consolidate_league_jsons_to_all.py'),
            os.path.join(os.getcwd(), 'etl', 'consolidate_league_jsons_to_all.py'),
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
        env['PYTHONPATH'] = project_root
        
        result = subprocess.run(
            [sys.executable, consolidation_script],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Parse output for progress updates
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    yield f"data: {json.dumps({'type': 'output', 'message': line.strip(), 'status': 'info'})}\n\n"
        
        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip():
                    yield f"data: {json.dumps({'type': 'output', 'message': line.strip(), 'status': 'warning'})}\n\n"
        
        if result.returncode == 0:
            yield f"data: {json.dumps({'type': 'output', 'message': '✅ Consolidation completed successfully!', 'status': 'success', 'success': True})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'output', 'message': '❌ Consolidation failed', 'status': 'error'})}\n\n"
        
    except Exception as e:
        print(f"Error running consolidation script: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Error running consolidation: {str(e)}'})}\n\n"

def run_import_script_generator():
    """Generator that runs the import script and yields progress updates"""
    try:
        current_file = os.path.abspath(__file__)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        # Try multiple possible locations for import script
        possible_import_paths = [
            os.path.join(project_root, 'etl', 'database_import', 'json_import_all_to_database.py'),
            os.path.join(project_root, 'etl', 'json_import_all_to_database.py'),
            os.path.join(os.getcwd(), 'etl', 'database_import', 'json_import_all_to_database.py'),
            os.path.join(os.getcwd(), 'etl', 'json_import_all_to_database.py'),
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
        env['PYTHONPATH'] = project_root
        
        result = subprocess.run(
            [sys.executable, import_script],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout for database import
        )
        
        # Parse output for progress updates
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    yield f"data: {json.dumps({'type': 'output', 'message': line.strip(), 'status': 'info'})}\n\n"
        
        if result.stderr:
            for line in result.stderr.split('\n'):
                if line.strip():
                    yield f"data: {json.dumps({'type': 'output', 'message': line.strip(), 'status': 'warning'})}\n\n"
        
        if result.returncode == 0:
            yield f"data: {json.dumps({'type': 'output', 'message': '✅ Database import completed successfully!', 'status': 'success', 'success': True})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'output', 'message': '❌ Database import failed', 'status': 'error'})}\n\n"
        
    except Exception as e:
        print(f"Error running import script: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Error running import: {str(e)}'})}\n\n"

# ==========================================
# EXISTING ADMIN API ENDPOINTS
# ==========================================

@admin_bp.route('/api/admin/users')
@login_required
def get_admin_users():
    """Get all registered users with their club and series information"""
    try:
        users = get_all_users()
        return jsonify(users)
    except Exception as e:
        print(f"Error getting admin users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/series')
@login_required
def get_admin_series():
    """Get all active series with player counts and active clubs"""
    try:
        series = get_all_series_with_stats()
        return jsonify(series)
    except Exception as e:
        print(f"Error getting admin series: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/clubs')
@login_required
def get_admin_clubs():
    """Get all clubs with player counts and active series"""
    try:
        clubs = execute_query('''
            SELECT c.id, c.name, COUNT(DISTINCT p.id) as player_count,
                   STRING_AGG(DISTINCT s.name, ', ') as active_series
            FROM clubs c
            LEFT JOIN players p ON c.id = p.club_id
            LEFT JOIN series s ON p.series_id = s.id
            GROUP BY c.id, c.name
            ORDER BY c.name
        ''')
        
        return jsonify([{
            'id': row['id'],
            'name': row['name'],
            'player_count': row['player_count'],
            'active_series': row['active_series'] or 'None'
        } for row in clubs])
    except Exception as e:
        print(f"Error getting admin clubs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/leagues')
@login_required
def get_admin_leagues():
    """Get all leagues with club and series counts"""
    try:
        leagues = execute_query('''
            SELECT l.id, l.league_name, l.league_url,
                   COUNT(DISTINCT cl.club_id) as club_count,
                   COUNT(DISTINCT sl.series_id) as series_count
            FROM leagues l
            LEFT JOIN club_leagues cl ON l.id = cl.league_id
            LEFT JOIN series_leagues sl ON l.id = sl.league_id
            GROUP BY l.id, l.league_name, l.league_url
            ORDER BY l.league_name
        ''')
        
        return jsonify([{
            'id': row['id'],
            'league_name': row['league_name'],
            'league_url': row['league_url'],
            'club_count': row['club_count'],
            'series_count': row['series_count']
        } for row in leagues])
    except Exception as e:
        print(f"Error getting admin leagues: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/update-user', methods=['POST'])
@login_required
def update_user():
    """Update a user's information"""
    try:
        data = request.json
        email = data.get('email')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        club_name = data.get('club_name')
        series_name = data.get('series_name')
        
        if not all([email, first_name, last_name, club_name, series_name]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Use service layer to update user
        update_user_info(email, first_name, last_name, club_name, series_name, session['user']['email'])
        return jsonify({'status': 'success'})
            
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/update-club', methods=['POST'])
@login_required
def update_club():
    """Update a club's information"""
    try:
        data = request.json
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        if not all([old_name, new_name]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Use service layer to update club
        update_club_name(old_name, new_name)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating club: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/update-series', methods=['POST'])
@login_required
def update_series():
    """Update a series' information"""
    try:
        data = request.json
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        if not all([old_name, new_name]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Use service layer to update series
        update_series_name(old_name, new_name)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error updating series: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/delete-user', methods=['POST'])
@login_required
@admin_required
def delete_user():
    """Delete a user from the database"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Use service layer to delete user
        result = delete_user_by_email(email, session['user']['email'])
        return jsonify(result)
            
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/user-activity/<email>')
@login_required
def get_user_activity(email):
    """Get activity logs for a specific user"""
    try:
        # Use service layer to get user activity
        response_data = get_user_activity_logs(email)
        
        # Create response with cache-busting headers
        response = jsonify(response_data)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        print(f"Error getting user activity: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/user-activity')
@login_required
def user_activity():
    """Serve the user activity page"""
    print("\n=== Serving User Activity Page ===")
    print(f"User in session: {'user' in session}")
    print(f"Session contents: {session}")
    
    try:
        print("Attempting to log user activity page visit")
        log_user_activity(
            session['user']['email'],
            'page_visit',
            page='user_activity',
            details='Accessed user activity page'
        )
        print("Successfully logged user activity page visit")
    except Exception as e:
        print(f"Error logging user activity page visit: {str(e)}")
        print(traceback.format_exc())
    
    return send_from_directory('static', 'user-activity.html') 