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
        # Explicit cron job mode
        context['cron_job_mode'] == 'true' or
        
        # Flask app explicitly disabled
        context['flask_app'] == '' or
        
        # Command line arguments contain cron-related terms
        any('cron' in str(arg).lower() for arg in sys.argv) or
        any('pipeline' in str(arg).lower() for arg in sys.argv) or
        
        # No PORT environment variable (web deployments typically have this)
        not context['port'] or
        
        # Service name indicates cron job (Railway sometimes sets this)
        (context['railway_service_name'] and 'cron' in context['railway_service_name'].lower())
    )
    
    return is_cron_job, context

def run_cron_job(context):
    """Execute the cron job pipeline"""
    print("🤖 Smart Start: Detected CRON JOB execution")
    print("=" * 60)
    print("🔍 Execution Context:")
    for key, value in context.items():
        print(f"   {key}: {value}")
    print("=" * 60)
    
    # Find the correct path to the pipeline script
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
    
    if not pipeline_script:
        print("❌ Pipeline script not found! Checked paths:")
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
        
        print("\n🔄 Attempting direct import fallback...")
        try:
            # Fallback: Try to import and run the pipeline directly
            sys.path.insert(0, os.getcwd())
            from cronjobs.run_pipeline import main as pipeline_main
            print("✅ Successfully imported pipeline via direct import")
            print("🚀 Running pipeline via direct import...")
            pipeline_main()
            print("✅ Pipeline completed successfully via direct import")
            sys.exit(0)
        except Exception as ie:
            print(f"❌ Direct import fallback also failed: {ie}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    print("🚀 Starting Rally Data Pipeline (Cron Job Mode)")
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