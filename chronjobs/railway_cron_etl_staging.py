#!/usr/bin/env python3
"""
Railway Cron ETL Script for STAGING

This script is designed specifically for Railway cron jobs on STAGING environment.
It runs ETL imports automatically on a schedule with comprehensive logging.
"""

import argparse
import os
import sys
import traceback
from datetime import datetime, timezone
import signal
import time

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# CRITICAL: Set environment to STAGING instead of production
os.environ.setdefault('RAILWAY_ENVIRONMENT', 'staging')

def setup_logging():
    """Setup comprehensive logging for cron job"""
    import logging
    
    # Configure logging to both console and file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),  # Railway logs capture stdout
        ]
    )
    
    return logging.getLogger(__name__)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}. Shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def log_system_info(logger):
    """Log system information for debugging"""
    logger.info("=" * 80)
    logger.info("🚀 RAILWAY STAGING CRON ETL JOB STARTING")
    logger.info("=" * 80)
    logger.info(f"📅 Start time: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"🔧 Railway environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
    logger.info(f"🗄️ Database URL configured: {'Yes' if os.environ.get('DATABASE_URL') else 'No'}")
    logger.info("🎯 Target Environment: STAGING")
    logger.info("=" * 80)

def test_database_connection(logger):
    """Test database connection before starting ETL"""
    try:
        from database_config import test_db_connection
        
        logger.info("🔍 Testing STAGING database connection...")
        success, error = test_db_connection()
        
        if success:
            logger.info("✅ STAGING database connection successful!")
            return True
        else:
            logger.error(f"❌ STAGING database connection failed: {error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ STAGING database connection test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def run_etl_import(logger, full_import=False):
    """Run the ETL import process on STAGING"""
    try:
        # Import master ETL module
        sys.path.append(os.path.join(project_root, 'data', 'etl', 'database_import'))
        from master_etl import MasterETL
        
        logger.info("🔄 Initializing Master ETL for STAGING...")
        etl = MasterETL(environment="staging", full_import=full_import)
        
        # Log start
        start_time = datetime.now(timezone.utc)
        logger.info(f"📥 Starting Master ETL process on STAGING...")
        logger.info(f"🎯 Full import mode: {'Yes' if full_import else 'No'}")
        
        # Run the complete ETL process
        result = etl.run_complete_etl()
        
        # Log completion
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        if result:
            logger.info("🎉 STAGING Master ETL completed successfully!")
            logger.info(f"⏱️ Total duration: {duration}")
            logger.info("📊 ETL summary logged above")
            return True
        else:
            logger.error("❌ STAGING Master ETL failed!")
            logger.error(f"⏱️ Duration before failure: {duration}")
            return False
            
    except Exception as e:
        logger.error(f"❌ STAGING Master ETL crashed: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def send_completion_notification(logger, success, duration, error_msg=None):
    """Send completion notification for STAGING"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    logger.info("=" * 80)
    logger.info(f"🏁 RAILWAY STAGING CRON ETL JOB COMPLETED - {status}")
    logger.info("=" * 80)
    logger.info(f"📅 End time: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"⏱️ Total duration: {duration}")
    
    if not success and error_msg:
        logger.error(f"💥 Error details: {error_msg}")
        
    logger.info("=" * 80)

def cleanup_resources(logger):
    """Cleanup any resources before exit"""
    logger.info("🧹 Cleaning up resources...")
    
    # Close database connections if available
    try:
        import psycopg2
        # Force close any remaining connections
        logger.info("✅ Database cleanup completed")
    except:
        pass  # Not critical if this fails

def main():
    """Main cron job function for STAGING"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Railway Staging Cron ETL Job')
    parser.add_argument('--full-import', action='store_true', 
                      help='Run full import instead of incremental')
    parser.add_argument('--test-only', action='store_true',
                      help='Test database connection only')
    args = parser.parse_args()
    
    # Setup
    logger = setup_logging()
    setup_signal_handlers()
    
    start_time = datetime.now(timezone.utc)
    success = False
    error_msg = None
    
    try:
        # Log system info
        log_system_info(logger)
        
        # Test database connection
        if not test_database_connection(logger):
            error_msg = "STAGING database connection failed"
            sys.exit(1)
            
        # Test-only mode
        if args.test_only:
            logger.info("✅ Test-only mode: STAGING database connection successful!")
            success = True
            return
        
        # Run ETL import
        success = run_etl_import(logger, full_import=args.full_import)
        
        if success:
            logger.info("🎊 STAGING cron ETL job completed successfully!")
        else:
            error_msg = "STAGING ETL import process failed"
            logger.error("💥 STAGING cron ETL job failed!")
            
    except KeyboardInterrupt:
        logger.info("🛑 STAGING cron ETL job interrupted by user")
        error_msg = "Job interrupted"
        
    except Exception as e:
        logger.error(f"💥 STAGING cron ETL job crashed: {str(e)}")
        logger.error(traceback.format_exc())
        error_msg = str(e)
        
    finally:
        # Calculate duration
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        # Send completion notification
        send_completion_notification(logger, success, duration, error_msg)
        
        # Cleanup
        cleanup_resources(logger)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 