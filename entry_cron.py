#!/usr/bin/env python3
"""
Rally Cron Job Entry Point
===========================

Lightweight wrapper script that prevents Flask startup and runs the pipeline directly.
This is an alternative approach to using cronjobs/run_pipeline.py directly.

This script:
- Sets environment variables IMMEDIATELY to prevent Flask startup
- Imports and runs the pipeline main function directly
- Provides clean separation between web server and cron job execution
- Ensures no Flask imports happen before cron job mode is set

Usage:
    python entry_cron.py

Railway Configuration:
    [deploy.cronJobs.etl_import]
    schedule = "0 2 * * *"
    command = "python entry_cron.py"
"""

# CRITICAL: Set environment variables BEFORE any other imports
import os
import sys

# Prevent Flask startup immediately
os.environ['CRON_JOB_MODE'] = 'true'
os.environ['FLASK_APP'] = ''
os.environ['FLASK_ENV'] = 'production'

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Print startup info for Railway logs
print("🚀 Rally Cron Entry Point")
print("=" * 50)
print(f"🔧 CRON_JOB_MODE: {os.environ.get('CRON_JOB_MODE')}")
print(f"🔧 FLASK_APP: {os.environ.get('FLASK_APP')}")
print(f"🔧 FLASK_ENV: {os.environ.get('FLASK_ENV')}")
print(f"📁 Project Root: {project_root}")
print("=" * 50)

def main():
    """
    Main entry point for cron job execution.
    Imports and runs the pipeline directly without Flask startup risk.
    """
    try:
        print("📋 Importing pipeline module...")
        
        # Import the pipeline main function directly
        # This import is safe because we've set CRON_JOB_MODE=true above
        from cronjobs.run_pipeline import main as pipeline_main
        
        print("✅ Pipeline module imported successfully")
        print("🚀 Starting pipeline execution...")
        
        # Run the pipeline
        pipeline_main()
        
    except ImportError as e:
        print(f"❌ Failed to import pipeline module: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()