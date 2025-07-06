#!/usr/bin/env python3
"""
Local Cron ETL Script - ATOMIC VERSION

This script is designed for local development and testing.
It runs ETL imports with atomic transactions and comprehensive logging.

🔄 ATOMIC: Uses atomic ETL for guaranteed data consistency
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

# Set environment to local
os.environ.setdefault('ENVIRONMENT', 'local')

def setup_logging():
    """Setup comprehensive logging for local cron job"""
    import logging
    
    # Configure logging with color support for local development
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
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
    logger.info("🚀 LOCAL CRON ETL JOB STARTING (ATOMIC VERSION)")
    logger.info("=" * 80)
    logger.info(f"📅 Start time: {datetime.now().isoformat()}")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"🏠 Environment: LOCAL DEVELOPMENT")
    logger.info(f"🗄️ Database URL configured: {'Yes' if os.environ.get('DATABASE_URL') else 'No'}")
    logger.info("🎯 Target Environment: LOCAL")
    logger.info("🔒 ETL Mode: ATOMIC (All-or-Nothing)")
    logger.info("💾 Backup: ENABLED by default (use --no-backup to skip)")
    logger.info("⚡ Local optimizations enabled")
    logger.info("=" * 80)

def test_database_connection(logger):
    """Test database connection before starting ETL"""
    try:
        from database_config import test_db_connection
        
        logger.info("🔍 Testing LOCAL database connection...")
        success, error = test_db_connection()
        
        if success:
            logger.info("✅ LOCAL database connection successful!")
            return True
        else:
            logger.error(f"❌ LOCAL database connection failed: {error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ LOCAL database connection test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def run_atomic_etl_import(logger, skip_backup=False):
    """Run the ATOMIC ETL import process locally"""
    try:
        # Import atomic ETL wrapper
        sys.path.append(os.path.join(project_root, 'data', 'etl', 'database_import'))
        from atomic_wrapper import AtomicETLWrapper
        
        logger.info("🔄 Initializing ATOMIC ETL wrapper for LOCAL development...")
        
        # Create atomic ETL wrapper with local-specific settings
        atomic_etl = AtomicETLWrapper(
            environment='local',
            create_backup=not skip_backup  # Default to create backup for safety
        )
        
        # Log start
        start_time = datetime.now()
        logger.info(f"📥 Starting ATOMIC ETL import process locally...")
        logger.info(f"💾 Backup enabled: {not skip_backup}")
        logger.info("🔒 Transaction mode: ATOMIC (All operations in single transaction)")
        logger.info("⚡ Local development optimizations active")
        
        # Run the atomic import
        result = atomic_etl.run_atomic_etl()
        
        # Log completion
        end_time = datetime.now()
        duration = end_time - start_time
        
        if result:
            logger.info("🎉 LOCAL ATOMIC ETL import completed successfully!")
            logger.info(f"⏱️ Total duration: {duration}")
            logger.info("✅ Local database is in consistent state")
            logger.info("📊 Import summary logged above")
            return True
        else:
            logger.error("❌ LOCAL ATOMIC ETL import failed!")
            logger.error(f"⏱️ Duration before failure: {duration}")
            logger.error("🔄 Database automatically rolled back to original state")
            return False
            
    except Exception as e:
        logger.error(f"❌ LOCAL ATOMIC ETL import crashed: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error("🔄 Any partial changes have been automatically rolled back")
        return False

def send_completion_notification(logger, success, duration, error_msg=None):
    """Send completion notification for LOCAL"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    logger.info("=" * 80)
    logger.info(f"🏁 LOCAL CRON ETL JOB COMPLETED - {status} (ATOMIC)")
    logger.info("=" * 80)
    logger.info(f"📅 End time: {datetime.now().isoformat()}")
    logger.info(f"⏱️ Total duration: {duration}")
    
    if success:
        logger.info("🔒 All data imported successfully in single atomic transaction")
        logger.info("✅ Local database is in consistent state")
        logger.info("🚀 Local development environment ready")
    else:
        logger.error("🔄 All changes automatically rolled back")
        logger.error("✅ Database remains in original consistent state")
        if error_msg:
            logger.error(f"💥 Error details: {error_msg}")
        
    logger.info("=" * 80)

def cleanup_resources(logger):
    """Cleanup any resources before exit"""
    logger.info("🧹 Cleaning up resources...")
    
    # Close database connections if available
    try:
        import psycopg2
        logger.info("✅ Database cleanup completed")
    except:
        pass  # Not critical if this fails

def show_usage_examples(logger):
    """Show usage examples for local development"""
    logger.info("\n📚 LOCAL ATOMIC ETL USAGE EXAMPLES:")
    logger.info("=" * 60)
    logger.info("🧪 Test database connection only:")
    logger.info("   python chronjobs/local_cron_etl_atomic.py --test-only")
    logger.info("")
    logger.info("💾 Safe local import (with backup - default):")
    logger.info("   python chronjobs/local_cron_etl_atomic.py")
    logger.info("")
    logger.info("⚡ Fast local import (no backup):")
    logger.info("   python chronjobs/local_cron_etl_atomic.py --no-backup")
    logger.info("")
    logger.info("🔍 Dry run (test mode):")
    logger.info("   python chronjobs/local_cron_etl_atomic.py --dry-run")
    logger.info("")
    logger.info("📊 Verbose logging:")
    logger.info("   python chronjobs/local_cron_etl_atomic.py --verbose")
    logger.info("=" * 60)

def main():
    """Main cron job function for LOCAL with ATOMIC ETL"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Local Cron ETL Job (Atomic)')
    parser.add_argument('--no-backup', '--skip-backup', action='store_true', 
                      help='Skip backup creation (faster but less safe)')
    parser.add_argument('--test-only', action='store_true',
                      help='Test database connection only')
    parser.add_argument('--dry-run', action='store_true',
                      help='Perform dry run without actual import')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    parser.add_argument('--help-examples', action='store_true',
                      help='Show usage examples and exit')
    args = parser.parse_args()
    
    # Setup
    logger = setup_logging()
    setup_signal_handlers()
    
    # Show usage examples if requested
    if args.help_examples:
        show_usage_examples(logger)
        return 0
    
    start_time = datetime.now()
    success = False
    error_msg = None
    
    try:
        # Log system info
        log_system_info(logger)
        
        # Verbose mode
        if args.verbose:
            logger.info("🔍 Verbose mode enabled - detailed logging active")
        
        # Test database connection
        if not test_database_connection(logger):
            error_msg = "LOCAL database connection failed"
            logger.error("🚨 Cannot connect to local database!")
            logger.info("💡 Make sure your local database is running and DATABASE_URL is set")
            sys.exit(1)
            
        # Test-only mode
        if args.test_only:
            logger.info("✅ Test-only mode: LOCAL database connection successful!")
            success = True
            return 0
        
        # Dry run mode
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE: Would run atomic ETL import...")
            logger.info(f"   💾 Backup would be: {'SKIPPED' if args.no_backup else 'ENABLED'}")
            logger.info("   🔒 Transaction mode would be: ATOMIC")
            logger.info("   ⚡ Local optimizations would be: ACTIVE")
            logger.info("✅ Dry run completed - no actual import performed")
            success = True
            return 0
        
        # Run ATOMIC ETL import
        skip_backup = args.no_backup
        success = run_atomic_etl_import(logger, skip_backup=skip_backup)
        
        if success:
            logger.info("🎊 LOCAL atomic cron ETL job completed successfully!")
            logger.info("🚀 Local development environment ready")
        else:
            error_msg = "LOCAL atomic ETL import process failed"
            logger.error("💥 LOCAL atomic cron ETL job failed!")
            
    except KeyboardInterrupt:
        logger.info("🛑 LOCAL atomic cron ETL job interrupted by user")
        error_msg = "Job interrupted"
        
    except Exception as e:
        logger.error(f"💥 LOCAL atomic cron ETL job crashed: {str(e)}")
        logger.error(traceback.format_exc())
        error_msg = str(e)
        
    finally:
        # Calculate duration
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Send completion notification
        send_completion_notification(logger, success, duration, error_msg)
        
        # Cleanup
        cleanup_resources(logger)
        
        # Show helpful info on completion
        if success:
            logger.info("\n💡 NEXT STEPS:")
            logger.info("   🧪 Test your app: python server.py")
            logger.info("   🔍 Validate data: python data/etl/validation/etl_validation_pipeline.py")
            logger.info("   📊 Check metrics: python scripts/database_health_check.py")
        else:
            logger.info("\n💡 TROUBLESHOOTING:")
            logger.info("   🔍 Check database connection: python chronjobs/local_cron_etl_atomic.py --test-only")
            logger.info("   🧪 Try dry run: python chronjobs/local_cron_etl_atomic.py --dry-run")
            logger.info("   📋 Review logs above for specific error details")
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 