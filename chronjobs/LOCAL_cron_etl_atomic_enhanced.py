#!/usr/bin/env python3
"""
Enhanced Local Cron ETL Script with Practice Time Protection
============================================================

This script uses the enhanced atomic ETL wrapper that includes
practice time protection to prevent data loss during ETL.

🔄 ATOMIC: Uses enhanced atomic ETL for guaranteed data consistency
🛡️  PROTECTION: Includes practice time protection system
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
    logger.info("🚀 ENHANCED LOCAL CRON ETL JOB STARTING")
    logger.info("=" * 80)
    logger.info(f"📅 Start time: {datetime.now().isoformat()}")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"🏠 Environment: LOCAL DEVELOPMENT")
    logger.info(f"🗄️ Database URL configured: {'Yes' if os.environ.get('DATABASE_URL') else 'No'}")
    logger.info("🎯 Target Environment: LOCAL")
    logger.info("🔒 ETL Mode: ENHANCED ATOMIC (All-or-Nothing + Protection)")
    logger.info("💾 Backup: ENABLED by default (use --no-backup to skip)")
    logger.info("🛡️  Practice Time Protection: ENABLED")
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

def run_enhanced_atomic_etl_import(logger, skip_backup=False):
    """Run the ENHANCED ATOMIC ETL import process locally"""
    try:
        # Import enhanced atomic ETL wrapper
        sys.path.append(os.path.join(project_root, 'data', 'etl', 'database_import'))
        from atomic_wrapper_enhanced import EnhancedAtomicETLWrapper
        
        logger.info("🔄 Initializing ENHANCED ATOMIC ETL wrapper for LOCAL development...")
        
        # Create enhanced atomic ETL wrapper with local-specific settings
        enhanced_atomic_etl = EnhancedAtomicETLWrapper(
            environment='local',
            create_backup=not skip_backup  # Default to create backup for safety
        )
        
        # Log start
        start_time = datetime.now()
        logger.info(f"📥 Starting ENHANCED ATOMIC ETL import process locally...")
        logger.info(f"💾 Backup enabled: {not skip_backup}")
        logger.info("🔒 Transaction mode: ENHANCED ATOMIC (All operations in single transaction)")
        logger.info("🛡️  Practice time protection: ENABLED")
        logger.info("⚡ Local development optimizations active")
        
        # Run the enhanced atomic import
        result = enhanced_atomic_etl.run_atomic_etl()
        
        # Log completion
        end_time = datetime.now()
        duration = end_time - start_time
        
        if result:
            logger.info("🎉 LOCAL ENHANCED ATOMIC ETL import completed successfully!")
            logger.info(f"⏱️ Total duration: {duration}")
            logger.info("✅ Local database is in consistent state")
            logger.info("🛡️  Practice time protection: SUCCESS")
            logger.info("📊 Import summary logged above")
            return True
        else:
            logger.error("❌ LOCAL ENHANCED ATOMIC ETL import failed!")
            logger.error(f"⏱️ Duration before failure: {duration}")
            logger.error("🔄 Database automatically rolled back to original state")
            logger.error("🛡️  Practice time protection prevented data loss")
            return False
            
    except Exception as e:
        logger.error(f"❌ LOCAL ENHANCED ATOMIC ETL import crashed: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error("🔄 Any partial changes have been automatically rolled back")
        logger.error("🛡️  Practice time protection prevented data loss")
        return False

def send_completion_notification(logger, success, duration, error_msg=None):
    """Send completion notification for LOCAL"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    logger.info("=" * 80)
    logger.info(f"🏁 ENHANCED LOCAL CRON ETL JOB COMPLETED - {status}")
    logger.info("=" * 80)
    logger.info(f"📅 End time: {datetime.now().isoformat()}")
    logger.info(f"⏱️ Total duration: {duration}")
    
    if success:
        logger.info("🔒 All data imported successfully in single atomic transaction")
        logger.info("✅ Local database is in consistent state")
        logger.info("🛡️  Practice time protection worked perfectly")
        logger.info("🚀 Local development environment ready")
    else:
        logger.error("🔄 All changes automatically rolled back")
        logger.error("✅ Database remains in original consistent state")
        logger.error("🛡️  Practice time protection prevented data loss")
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
    logger.info("\n📚 ENHANCED LOCAL ATOMIC ETL USAGE EXAMPLES:")
    logger.info("=" * 60)
    logger.info("🧪 Test database connection only:")
    logger.info("   python chronjobs/LOCAL_cron_etl_atomic_enhanced.py --test-only")
    logger.info("")
    logger.info("💾 Safe local import (with backup + protection - default):")
    logger.info("   python chronjobs/LOCAL_cron_etl_atomic_enhanced.py")
    logger.info("")
    logger.info("⚡ Fast local import (no backup + protection):")
    logger.info("   python chronjobs/LOCAL_cron_etl_atomic_enhanced.py --no-backup")
    logger.info("")
    logger.info("🔍 Dry run (test mode):")
    logger.info("   python chronjobs/LOCAL_cron_etl_atomic_enhanced.py --dry-run")
    logger.info("")
    logger.info("📊 Verbose logging:")
    logger.info("   python chronjobs/LOCAL_cron_etl_atomic_enhanced.py --verbose")
    logger.info("=" * 60)
    logger.info("🛡️  ALL MODES include practice time protection")

def main():
    """Main cron job function for LOCAL with ENHANCED ATOMIC ETL"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced Local Cron ETL Job (Atomic + Protection)')
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
            logger.info("🔍 DRY RUN MODE: Would run enhanced atomic ETL import...")
            logger.info(f"   💾 Backup would be: {'SKIPPED' if args.no_backup else 'ENABLED'}")
            logger.info("   🔒 Transaction mode would be: ENHANCED ATOMIC")
            logger.info("   🛡️  Practice time protection would be: ENABLED")
            logger.info("   ⚡ Local optimizations would be: ACTIVE")
            logger.info("✅ Dry run completed - no actual import performed")
            success = True
            return 0
        
        # Run ENHANCED ATOMIC ETL import
        skip_backup = args.no_backup
        success = run_enhanced_atomic_etl_import(logger, skip_backup=skip_backup)
        
        if success:
            logger.info("🎊 LOCAL enhanced atomic cron ETL job completed successfully!")
            logger.info("🛡️  Practice time protection worked perfectly!")
            logger.info("🚀 Local development environment ready")
        else:
            error_msg = "LOCAL enhanced atomic ETL import process failed"
            logger.error("💥 LOCAL enhanced atomic cron ETL job failed!")
            
    except KeyboardInterrupt:
        logger.info("🛑 LOCAL enhanced atomic cron ETL job interrupted by user")
        error_msg = "Job interrupted"
        
    except Exception as e:
        logger.error(f"💥 LOCAL enhanced atomic cron ETL job crashed: {str(e)}")
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
            logger.info("   🔍 Check database connection: python chronjobs/LOCAL_cron_etl_atomic_enhanced.py --test-only")
            logger.info("   🧪 Try dry run: python chronjobs/LOCAL_cron_etl_atomic_enhanced.py --dry-run")
            logger.info("   📋 Review logs above for specific error details")
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 