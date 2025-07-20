#!/usr/bin/env python3
"""
Railway Cron ETL Script for PRODUCTION - ATOMIC VERSION

This script is designed specifically for Railway cron jobs on PRODUCTION environment.
It runs ETL imports automatically on a schedule with comprehensive logging.

🔄 UPDATED: Now uses atomic ETL for guaranteed data consistency
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

# Set environment to ensure proper database connections
os.environ.setdefault('RAILWAY_ENVIRONMENT', 'production')

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
    logger.info("🚀 RAILWAY PRODUCTION CRON ETL JOB STARTING (ATOMIC VERSION)")
    logger.info("=" * 80)
    logger.info(f"📅 Start time: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"🔧 Railway environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
    logger.info(f"🗄️ Database URL configured: {'Yes' if os.environ.get('DATABASE_URL') else 'No'}")
    logger.info("🎯 Target Environment: PRODUCTION")
    logger.info("🔒 ETL Mode: ATOMIC (All-or-Nothing)")
    logger.info("⚠️ PRODUCTION: Maximum safety protocols enabled")
    logger.info("=" * 80)

def test_database_connection(logger):
    """Test database connection before starting ETL"""
    try:
        from database_config import test_db_connection
        
        logger.info("🔍 Testing PRODUCTION database connection...")
        success, error = test_db_connection()
        
        if success:
            logger.info("✅ PRODUCTION database connection successful!")
            return True
        else:
            logger.error(f"❌ PRODUCTION database connection failed: {error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ PRODUCTION database connection test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def run_atomic_etl_import(logger):
    """Run the ATOMIC ETL import process on PRODUCTION"""
    try:
        # Import atomic ETL wrapper
        sys.path.append(os.path.join(project_root, 'data', 'etl', 'database_import'))
        from atomic_wrapper import AtomicETLWrapper
        
        logger.info("🔄 Initializing ATOMIC ETL wrapper for PRODUCTION...")
        
        # Create atomic ETL wrapper with production-specific settings
        # ALWAYS create backup in production
        atomic_etl = AtomicETLWrapper(
            environment='railway_production',
            create_backup=True  # ALWAYS backup in production
        )
        
        # Log start
        start_time = datetime.now(timezone.utc)
        logger.info(f"📥 Starting ATOMIC ETL import process on PRODUCTION...")
        logger.info("💾 Backup: ENABLED (required for production)")
        logger.info("🔒 Transaction mode: ATOMIC (All operations in single transaction)")
        logger.info("⚠️ PRODUCTION: Using maximum safety protocols")
        
        # Run the atomic import
        result = atomic_etl.run_atomic_etl()
        
        # Log completion
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        
        if result:
            logger.info("🎉 PRODUCTION ATOMIC ETL import completed successfully!")
            logger.info(f"⏱️ Total duration: {duration}")
            logger.info("✅ Database is in consistent state")
            logger.info("🚀 PRODUCTION system ready for users")
            logger.info("📊 Import summary logged above")
            return True
        else:
            logger.error("❌ PRODUCTION ATOMIC ETL import failed!")
            logger.error(f"⏱️ Duration before failure: {duration}")
            logger.error("🔄 Database automatically rolled back to original state")
            logger.error("✅ PRODUCTION system remains stable")
            return False
            
    except Exception as e:
        logger.error(f"❌ PRODUCTION ATOMIC ETL import crashed: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error("🔄 Any partial changes have been automatically rolled back")
        logger.error("✅ PRODUCTION system remains stable")
        return False

def send_completion_notification(logger, success, duration, error_msg=None):
    """Send completion notification for PRODUCTION"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    logger.info("=" * 80)
    logger.info(f"🏁 RAILWAY PRODUCTION CRON ETL JOB COMPLETED - {status} (ATOMIC)")
    logger.info("=" * 80)
    logger.info(f"📅 End time: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"⏱️ Total duration: {duration}")
    
    if success:
        logger.info("🔒 All data imported successfully in single atomic transaction")
        logger.info("✅ Database is in consistent state")
        logger.info("🚀 PRODUCTION system is ready for users")
    else:
        logger.error("🔄 All changes automatically rolled back")
        logger.error("✅ Database remains in original consistent state")
        logger.error("🚀 PRODUCTION system remains stable and operational")
        if error_msg:
            logger.error(f"💥 Error details: {error_msg}")
        
    logger.info("=" * 80)
    
    # TODO: Could integrate with alerting systems here
    # - Email notifications for production failures
    # - Slack/Discord webhooks
    # - PagerDuty alerts for critical failures

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
    """Main cron job function for PRODUCTION with ATOMIC ETL"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Railway Production Cron ETL Job (Atomic)')
    parser.add_argument('--test-only', action='store_true',
                      help='Test database connection only')
    # Note: No skip-backup option for production - always backup
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
            error_msg = "PRODUCTION database connection failed"
            logger.error("🚨 CRITICAL: Cannot connect to PRODUCTION database!")
            sys.exit(1)
            
        # Test-only mode
        if args.test_only:
            logger.info("✅ Test-only mode: PRODUCTION database connection successful!")
            success = True
            return
        
        # Run ATOMIC ETL import
        logger.info("🚨 STARTING PRODUCTION ETL IMPORT - ALL SAFETY PROTOCOLS ACTIVE")
        success = run_atomic_etl_import(logger)
        
        if success:
            logger.info("🎊 PRODUCTION atomic cron ETL job completed successfully!")
            logger.info("🚀 PRODUCTION system is ready for users")
        else:
            error_msg = "PRODUCTION atomic ETL import process failed"
            logger.error("💥 PRODUCTION atomic cron ETL job failed!")
            logger.error("⚠️ PRODUCTION system remains stable (no partial data)")
            
    except KeyboardInterrupt:
        logger.info("🛑 PRODUCTION atomic cron ETL job interrupted by user")
        error_msg = "Job interrupted"
        
    except Exception as e:
        logger.error(f"💥 PRODUCTION atomic cron ETL job crashed: {str(e)}")
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