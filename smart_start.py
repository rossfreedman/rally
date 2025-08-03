#!/usr/bin/env python3
"""
Smart Start Script for Railway Deployment
==========================================

This script intelligently detects whether Railway is starting:
1. A web server deployment (start Flask)
2. A cron job (run pipeline script)

Railway uses this as the default start command, but it routes to the appropriate
execution path based on environment variables and execution context.

Usage:
    python smart_start.py

Railway Configuration:
    nixpacks.toml: cmd = "python smart_start.py"
    railway.toml: command = "python cronjobs/run_pipeline.py" (cron jobs should override this)
"""

import os
import sys
import subprocess

def detect_execution_context():
    """
    Detect whether this is a cron job or web deployment based on environment variables
    and Railway-specific indicators.
    
    Returns:
        tuple: (is_cron_job: bool, context_info: dict)
    """
    context = {
        'cron_job_mode': os.environ.get('CRON_JOB_MODE'),
        'flask_app': os.environ.get('FLASK_APP'),
        'railway_service_name': os.environ.get('RAILWAY_SERVICE_NAME'),
        'railway_deployment_id': os.environ.get('RAILWAY_DEPLOYMENT_ID'),
        'port': os.environ.get('PORT'),
        'cmd_line_args': sys.argv,
        'working_dir': os.getcwd()
    }
    
    # Multiple detection methods for cron job identification
    is_cron_job = (
        # Explicit cron job mode (most reliable)
        context['cron_job_mode'] == 'true' or
        
        # Flask app explicitly disabled
        context['flask_app'] == '' or
        
        # Command line arguments contain cron-related terms
        any('cron' in str(arg).lower() for arg in sys.argv) or
        any('pipeline' in str(arg).lower() for arg in sys.argv)
        
        # REMOVED: PORT check and service name check as they cause false positives
        # Web deployments should start Flask unless explicitly disabled above
    )
    
    return is_cron_job, context

def embedded_pipeline_execution(context):
    """
    Embedded pipeline execution - runs directly in smart_start.py when entry_cron.py is missing.
    This is a complete standalone implementation of the Rally data pipeline.
    """
    import logging
    from datetime import datetime
    
    # Ensure Flask doesn't start during this execution
    os.environ['CRON_JOB_MODE'] = 'true'
    os.environ['FLASK_APP'] = ''
    os.environ['FLASK_ENV'] = 'production'
    
    print("🚀 Rally Data Pipeline Starting (Embedded in Smart Start)")
    print("=" * 60)
    print(f"🕐 Start Time: {datetime.now()}")
    print("📋 Pipeline Steps: Scraper → ETL Import")
    print("🔧 Running embedded pipeline (no external script dependencies)")
    print("🔧 Environment: CRON_JOB_MODE=true, FLASK_APP='', FLASK_ENV=production")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    start_time = datetime.now()
    
    # Send start SMS
    try:
        from app.services.notifications_service import send_sms
        start_time_formatted = start_time.strftime("%m-%d-%y @ %I:%M:%S %p")
        send_sms("17732138911", f"Rally Cronjob:\nSTARTING Cronjob a {start_time_formatted}")
        print("📱 Start SMS sent")
    except Exception as e:
        print(f"⚠️ Failed to send start SMS: {e}")
    
    # Step 1: Enhanced Master Scraper
    try:
        print("🔍 Starting enhanced master scraper with stealth measures...")
        print("🛡️ Features: Auto-detection, proxy rotation, CAPTCHA detection, retry logic")
        
        result = subprocess.run([
            sys.executable, 
            "data/etl/scrapers/master_scraper.py",
            "--max-retries", "5",
            "--min-delay", "3.0",
            "--max-delay", "8.0", 
            "--requests-per-proxy", "25",
            "--session-duration", "900",
            "--timeout", "45"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode != 0:
            print(f"❌ Enhanced scraper failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise Exception(f"Enhanced scraper subprocess failed")
        
        print("✅ Enhanced scraper complete: Data scraping finished successfully")
        
    except Exception as e:
        print(f"❌ Scraper failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    # Step 2: ETL Import
    try:
        print("📥 Starting ETL import...")
        
        result = subprocess.run([
            sys.executable, 
            "data/etl/database_import/master_import.py"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode != 0:
            print(f"❌ ETL import failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise Exception(f"ETL import subprocess failed")
        
        print("✅ ETL complete: Database import successful")
        
    except Exception as e:
        print(f"❌ ETL import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    # Pipeline completion
    end_time = datetime.now()
    duration = end_time - start_time
    total_seconds = duration.total_seconds()
    
    if total_seconds < 60:
        formatted_duration = f"{int(total_seconds)}s"
    else:
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        formatted_duration = f"{minutes}m {seconds}s"
    
    print("🎉 All done: Rally cron job completed successfully")
    print(f"📊 Total Pipeline Duration: {formatted_duration}")
    print("📱 Note: ETL import has already sent completion notification")

def run_cron_job(context):
    """Execute the cron job pipeline"""
    print("🤖 Smart Start: Detected CRON JOB execution")
    print("🔧 VERSION: Enhanced Smart Start v2.0 with embedded pipeline")
    print("=" * 60)
    print("🔍 Execution Context:")
    for key, value in context.items():
        print(f"   {key}: {value}")
    print("=" * 60)
    
    # FIRST: Check for entry_cron.py (our standalone solution)
    print("🔍 Priority Check: Looking for entry_cron.py...")
    entry_cron_path = os.path.join(os.getcwd(), "entry_cron.py")
    
    # Debug: List all .py files in root directory
    print("📄 Available .py files in /app:")
    try:
        for item in os.listdir(os.getcwd()):
            if item.endswith('.py'):
                print(f"   ✅ {item}")
    except Exception as e:
        print(f"   ❌ Could not list .py files: {e}")
    
    if os.path.exists(entry_cron_path):
        print(f"✅ Found entry_cron.py at: {entry_cron_path}")
        print("🚀 Executing entry_cron.py directly (priority method)...")
        
        try:
            result = subprocess.run([
                sys.executable, 
                "entry_cron.py"
            ], cwd=os.getcwd())
            
            print(f"🏁 entry_cron.py execution completed with exit code: {result.returncode}")
            sys.exit(result.returncode)
            
        except Exception as e:
            print(f"❌ Failed to execute entry_cron.py subprocess: {e}")
            # Fall through to direct import fallback
            
        # Direct import fallback for entry_cron.py
        try:
            print("🔄 Attempting direct import from entry_cron...")
            sys.path.insert(0, os.getcwd())
            from entry_cron import main as entry_main
            print("✅ Successfully imported entry_cron.main")
            print("🚀 Running pipeline via entry_cron.main...")
            entry_main()
            print("✅ Pipeline completed successfully via entry_cron")
            sys.exit(0)
        except Exception as ie:
            print(f"❌ entry_cron.py direct import also failed: {ie}")
            # Continue to embedded pipeline
    
    else:
        print(f"❌ entry_cron.py not found at: {entry_cron_path}")
        print("🔄 Using embedded pipeline as immediate fallback...")
        
        # EMBEDDED PIPELINE: If entry_cron.py is missing, run pipeline directly here
        try:
            embedded_pipeline_execution(context)
            sys.exit(0)
        except Exception as e:
            print(f"❌ Embedded pipeline also failed: {e}")
            import traceback
            traceback.print_exc()
            # Continue to legacy search
    
    # SECONDARY: Legacy pipeline script search (original logic)
    print("\n🔍 Secondary Check: Looking for legacy pipeline script...")
    possible_paths = [
        "cronjobs/run_pipeline.py",
        "./cronjobs/run_pipeline.py", 
        "/app/cronjobs/run_pipeline.py",
        os.path.join(os.getcwd(), "cronjobs", "run_pipeline.py"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "cronjobs", "run_pipeline.py")
    ]
    
    pipeline_script = None
    for path in possible_paths:
        if os.path.exists(path):
            pipeline_script = path
            print(f"✅ Found pipeline script at: {path}")
            break
    
    if pipeline_script:
        print("🚀 Starting Rally Data Pipeline (Legacy Mode)")
        print(f"📋 Command: python {pipeline_script}")
        print("=" * 60)
        
        try:
            # Set explicit cron job environment variables
            os.environ['CRON_JOB_MODE'] = 'true'
            os.environ['FLASK_APP'] = ''
            
            # Execute the pipeline script directly
            result = subprocess.run([
                sys.executable, 
                pipeline_script
            ], cwd=os.getcwd())
            
            print(f"🏁 Pipeline execution completed with exit code: {result.returncode}")
            sys.exit(result.returncode)
            
        except Exception as e:
            print(f"❌ Failed to execute pipeline: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # FINAL: Error - no pipeline found
    print("❌ No pipeline script found! Checked paths:")
    for path in possible_paths:
        print(f"   ❌ {path} (exists: {os.path.exists(path)})")
    
    # List current directory contents for debugging
    print(f"\n📁 Current directory contents ({os.getcwd()}):")
    try:
        for item in os.listdir(os.getcwd()):
            print(f"   📄 {item}")
            if os.path.isdir(item):
                print(f"      📁 {item}/ contents:")
                try:
                    for subitem in os.listdir(item):
                        print(f"         📄 {subitem}")
                except Exception as se:
                    print(f"         ❌ Could not list subdirectory: {se}")
    except Exception as e:
        print(f"   ❌ Could not list directory: {e}")
    
    print("\n❌ All pipeline methods exhausted - cron job failed")
    sys.exit(1)

def run_web_server(context):
    """Start the Flask web server"""
    print("🌐 Smart Start: Detected WEB SERVER deployment")
    print("=" * 60)
    print("🔍 Execution Context:")
    for key, value in context.items():
        print(f"   {key}: {value}")
    print("=" * 60)
    print("🚀 Starting Rally Flask Application (Web Server Mode)")
    print("📋 Command: python server.py")
    print("=" * 60)
    
    try:
        # Ensure web server environment variables are set
        if not os.environ.get('FLASK_ENV'):
            os.environ['FLASK_ENV'] = 'production'
        
        # Remove cron job indicators to ensure Flask starts
        os.environ.pop('CRON_JOB_MODE', None)
        
        # Execute the Flask server
        result = subprocess.run([
            sys.executable, 
            "server.py"
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
        print(f"🏁 Flask server exited with code: {result.returncode}")
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"❌ Failed to start Flask server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main execution logic"""
    print("🧠 Railway Smart Start Script")
    print("🔍 Detecting execution context...")
    
    is_cron_job, context = detect_execution_context()
    
    if is_cron_job:
        run_cron_job(context)
    else:
        run_web_server(context)

if __name__ == "__main__":
    main()