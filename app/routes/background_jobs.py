"""
Background Jobs Blueprint

Handles triggering and monitoring of background ETL processes
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from threading import Thread

from flask import Blueprint, jsonify, request, session
from utils.auth import login_required
from app.routes.admin_routes import admin_required

# Create background jobs blueprint
background_bp = Blueprint("background", __name__)

# Global variable to track background job status
background_job_status = {
    "active": False,
    "started_at": None,
    "progress": 0,
    "status": "idle",
    "last_update": None,
    "pid": None
}


@background_bp.route("/api/admin/background/etl/start", methods=["POST"])
@login_required
@admin_required
def start_background_etl():
    """Start ETL process as a background job"""
    global background_job_status
    
    # Check if a job is already running
    if background_job_status["active"]:
        return jsonify({
            "error": "Background ETL job is already running",
            "status": background_job_status
        }), 409
    
    try:
        # Get project root - FIXED: Only go up 2 levels, not 3
        script_dir = os.path.dirname(os.path.abspath(__file__))  # app/routes/
        app_dir = os.path.dirname(script_dir)  # app/
        project_root = os.path.dirname(app_dir)  # rally/ (project root)
        background_script = os.path.join(project_root, "chronjobs", "railway_background_etl.py")
        
        # Start background process
        process = subprocess.Popen(
            [sys.executable, "-u", background_script],  # -u for unbuffered output
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,  # Unbuffered
            env=dict(os.environ, PYTHONUNBUFFERED="1")  # Ensure Python output is unbuffered
        )
        
        # Update status
        background_job_status.update({
            "active": True,
            "started_at": datetime.now().isoformat(),
            "progress": 0,
            "status": "starting",
            "last_update": datetime.now().isoformat(),
            "pid": process.pid
        })
        
        # Start monitoring thread
        monitor_thread = Thread(target=monitor_background_job, args=(process,))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Background ETL job started",
            "job_status": background_job_status
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to start background ETL: {str(e)}"
        }), 500


@background_bp.route("/api/admin/background/etl/status")
@login_required
@admin_required  
def get_background_etl_status():
    """Get current status of background ETL job"""
    return jsonify({
        "status": "success",
        "job_status": background_job_status
    })


@background_bp.route("/api/admin/background/etl/stop", methods=["POST"])
@login_required
@admin_required
def stop_background_etl():
    """Stop the background ETL job"""
    global background_job_status
    
    if not background_job_status["active"]:
        return jsonify({
            "error": "No background ETL job is currently running"
        }), 400
    
    try:
        # Try to terminate the process
        pid = background_job_status.get("pid")
        if pid:
            try:
                os.kill(pid, 15)  # SIGTERM
                time.sleep(2)
                try:
                    os.kill(pid, 9)  # SIGKILL if still running
                except ProcessLookupError:
                    pass  # Process already dead
            except ProcessLookupError:
                pass  # Process already dead
        
        # Reset status
        background_job_status.update({
            "active": False,
            "status": "stopped",
            "last_update": datetime.now().isoformat(),
            "pid": None
        })
        
        return jsonify({
            "status": "success",
            "message": "Background ETL job stopped",
            "job_status": background_job_status
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to stop background ETL: {str(e)}"
        }), 500


def monitor_background_job(process):
    """Monitor the background job process"""
    global background_job_status
    
    try:
        while True:
            # Check if process is still running
            if process.poll() is not None:
                # Process finished
                return_code = process.returncode
                background_job_status.update({
                    "active": False,
                    "status": "completed" if return_code == 0 else "failed",
                    "last_update": datetime.now().isoformat(),
                    "progress": 100 if return_code == 0 else background_job_status["progress"],
                    "pid": None
                })
                break
            
            # Read output and update progress (simple progress estimation)
            try:
                output = process.stdout.readline()
                if output:
                    # Update last activity
                    background_job_status["last_update"] = datetime.now().isoformat()
                    
                    # Simple progress estimation based on log messages
                    if "Starting" in output:
                        background_job_status["progress"] = 5
                        background_job_status["status"] = "running"
                    elif "Importing players" in output:
                        background_job_status["progress"] = 20
                    elif "player history records" in output:
                        background_job_status["progress"] = 50
                    elif "match history records" in output:
                        background_job_status["progress"] = 75
                    elif "completed successfully" in output.lower():
                        background_job_status["progress"] = 100
                        background_job_status["status"] = "completing"
                        
            except:
                pass
            
            time.sleep(1)  # Check every second
            
    except Exception as e:
        background_job_status.update({
            "active": False,
            "status": "error",
            "last_update": datetime.now().isoformat(),
            "error": str(e),
            "pid": None
        }) 