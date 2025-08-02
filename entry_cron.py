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
import subprocess

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

def run_master_scraper():
    """Run the enhanced master scraper step using subprocess to avoid Flask imports"""
    try:
        # Run enhanced master scraper as subprocess to avoid Flask app startup
        result = subprocess.run([
            sys.executable, 
            "data/etl/scrapers/master_scraper.py",
            "--max-retries", "5",
            "--min-delay", "3.0",
            "--max-delay", "8.0", 
            "--requests-per-proxy", "25",
            "--session-duration", "900",
            "--timeout", "45"
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode != 0:
            print(f"❌ Enhanced scraper failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise Exception(f"Enhanced scraper subprocess failed with return code {result.returncode}")
        
        print("✅ Enhanced scraper complete: Data scraping finished successfully")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced scraper failed: {str(e)}")
        raise

def run_etl_import():
    """Run the ETL import step using subprocess to avoid Flask imports"""
    try:
        # Run master importer as subprocess to avoid Flask app startup
        result = subprocess.run([
            sys.executable, 
            "data/etl/database_import/master_import.py"
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode != 0:
            print(f"❌ ETL import failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise Exception(f"ETL import subprocess failed with return code {result.returncode}")
        
        print("✅ ETL complete: Database import successful")
        return True
        
    except Exception as e:
        print(f"❌ ETL import failed: {str(e)}")
        raise

def send_start_sms(start_time):
    """Send start SMS notification with isolated import"""
    try:
        from app.services.notifications_service import send_sms
        start_time_formatted = start_time.strftime("%m-%d-%y @ %I:%M:%S %p")
        send_sms("17732138911", f"Rally Cronjob:\nSTARTING Cronjob a {start_time_formatted}")
        print("📱 Start SMS sent")
    except Exception as e:
        print(f"⚠️ Failed to send start SMS: {e}")

def run_constraint_fix():
    """Run database constraint fixer to resolve ETL import issues"""
    try:
        print("🔧 Starting Database Constraint Fix...")
        
        # Import the constraint fixer
        from scripts.fix_missing_database_constraints import DatabaseConstraintFixer
        
        fixer = DatabaseConstraintFixer()
        success = fixer.fix_all_constraints()
        
        if success:
            print("✅ Database constraints fixed successfully!")
            return True
        else:
            print("❌ Failed to fix some database constraints")
            return False
            
    except Exception as e:
        print(f"❌ Constraint fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Main entry point for cron job execution.
    Standalone pipeline implementation that doesn't depend on cronjobs/run_pipeline.py
    """
    import logging
    from datetime import datetime
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)
    
    # Check if we should only run constraint fix
    fix_constraints_mode = os.environ.get('FIX_CONSTRAINTS', '').lower() == 'true'
    
    start_time = datetime.now()
    
    if fix_constraints_mode:
        print("🔧 Rally Database Constraint Fix Mode")
        print("=" * 60)
        print(f"🕐 Start Time: {start_time}")
        print("📋 Mode: Fix Database Constraints Only")
        print("🔧 Running from entry_cron.py (constraint fix mode)")
        print("=" * 60)
        
        success = run_constraint_fix()
        
        end_time = datetime.now()
        duration = end_time - start_time
        total_seconds = duration.total_seconds()
        
        if success:
            print(f"🎉 Constraint fix completed successfully in {int(total_seconds)}s")
            print("💡 You can now run the normal ETL pipeline")
            sys.exit(0)
        else:
            print(f"❌ Constraint fix failed after {int(total_seconds)}s")
            sys.exit(1)
    
    # Normal pipeline mode
    print("🚀 Rally Data Pipeline Starting (Standalone Entry Point)")
    print("=" * 60)
    print(f"🕐 Start Time: {start_time}")
    print("📋 Pipeline Steps: Scraper → ETL Import")
    print("🔧 Running from entry_cron.py (no cronjobs dependency)")
    print("=" * 60)
    
    # Send start SMS
    send_start_sms(start_time)
    
    # Step 1: Enhanced Master Scraper
    try:
        print("🔍 Starting enhanced master scraper with stealth measures...")
        print("🛡️ Features: Auto-detection, proxy rotation, CAPTCHA detection, retry logic")
        
        run_master_scraper()
        
        print("✅ Enhanced scraper complete: Data scraping finished successfully")
        
    except Exception as e:
        error_msg = f"❌ Scraper failed: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 2: ETL Import
    try:
        print("📥 Starting ETL import...")
        
        run_etl_import()
        
        print("✅ ETL complete: Database import successful")
        
    except Exception as e:
        error_msg = f"❌ ETL import failed: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
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
    
    sys.exit(0)

if __name__ == "__main__":
    main()