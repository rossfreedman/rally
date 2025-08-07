#!/usr/bin/env python3
"""
Enhanced ETL Integration

This module provides drop-in replacement functionality for existing ETL classes
to enable bulletproof team ID preservation and comprehensive data protection.
"""

import logging
import sys
import os
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from data.etl.database_import.bulletproof_team_id_preservation import BulletproofTeamPreservation
from database_utils import execute_query, execute_query_one, execute_update, get_db

logger = logging.getLogger(__name__)

def bulletproof_import_teams(etl_instance, conn, teams_data: List[Dict]) -> Dict[str, int]:
    """
    Bulletproof team import function that replaces the standard import_teams method.
    
    This function provides comprehensive protection against orphaned records by:
    1. Validating database constraints before import
    2. Automatically repairing any constraint issues
    3. Creating comprehensive backups of user data
    4. Using bulletproof UPSERT strategy for team imports
    5. Restoring user data with multiple fallback strategies
    6. Detecting and fixing any remaining orphaned records
    
    Args:
        etl_instance: The ETL instance (for logging compatibility)
        conn: Database connection
        teams_data: List of team data dictionaries
        
    Returns:
        Dict[str, int]: Import statistics
    """
    
    logger.info("🚀 Starting Bulletproof Team Import")
    
    # Initialize bulletproof system
    bulletproof = BulletproofTeamPreservation()
    
    try:
        # Step 1: Validate constraints
        logger.info("🔍 Step 1: Validating database constraints...")
        is_safe, issues = bulletproof.validate_constraints(conn)
        
        if not is_safe:
            logger.warning("⚠️  Constraint issues detected, attempting repair...")
            for issue in issues:
                logger.warning(f"   ❌ {issue}")
            
            # Attempt to repair constraints
            if bulletproof.repair_constraints(conn):
                logger.info("✅ Constraints repaired successfully")
            else:
                logger.error("❌ Constraint repair failed - aborting import")
                return {'error': 'constraint_repair_failed'}
        
        # Step 2: Backup user data
        logger.info("💾 Step 2: Creating comprehensive user data backup...")
        backup_stats = bulletproof.backup_user_data(conn)
        logger.info(f"✅ Backup completed: {backup_stats}")
        
        # Step 3: Import teams using bulletproof strategy
        logger.info("🏆 Step 3: Importing teams with bulletproof UPSERT...")
        import_stats = bulletproof.import_teams_bulletproof(conn, teams_data)
        logger.info(f"✅ Team import completed: {import_stats}")
        
        # Step 4: Restore user data
        logger.info("🔄 Step 4: Restoring user data...")
        restore_stats = bulletproof.restore_user_data(conn)
        logger.info(f"✅ User data restoration completed: {restore_stats}")
        
        # Step 5: Detect and fix any remaining orphans
        logger.info("🔍 Step 5: Detecting and fixing orphaned records...")
        orphan_stats = bulletproof.detect_and_fix_orphans(conn)
        logger.info(f"✅ Orphan detection and fix completed: {orphan_stats}")
        
        # Step 6: Generate health report
        logger.info("📊 Step 6: Generating health report...")
        health_report = bulletproof.get_health_report()
        logger.info(f"📈 Health Score: {health_report['health_score']}/100")
        logger.info(f"🚨 Total Orphans: {health_report['total_orphans']}")
        
        # Step 7: Cleanup backup tables
        logger.info("🧹 Step 7: Cleaning up backup tables...")
        if bulletproof.cleanup_backup_tables(conn):
            logger.info("✅ Backup tables cleaned up successfully")
        else:
            logger.warning("⚠️  Backup cleanup failed (non-critical)")
        
        # Return comprehensive statistics
        final_stats = {
            'teams_preserved': import_stats.get('preserved', 0),
            'teams_created': import_stats.get('created', 0),
            'teams_updated': import_stats.get('updated', 0),
            'backup_records': sum(backup_stats.values()),
            'restored_records': sum(restore_stats.values()),
            'orphans_fixed': orphan_stats.get('fixed', 0),
            'health_score': health_report['health_score'],
            'total_orphans': health_report['total_orphans'],
            'status': 'success'
        }
        
        logger.info("🎉 Bulletproof Team Import completed successfully!")
        return final_stats
        
    except Exception as e:
        logger.error(f"❌ Bulletproof Team Import failed: {str(e)}")
        return {
            'error': str(e),
            'status': 'failed'
        }

def enable_bulletproof_etl(etl_class):
    """
    Enable bulletproof ETL for an existing ETL class by monkey patching.
    
    This function replaces the standard import_teams method with the bulletproof version.
    
    Args:
        etl_class: The ETL class to enhance
    """
    
    # Store the original method
    original_import_teams = getattr(etl_class, 'import_teams', None)
    
    def enhanced_import_teams(self, conn, teams_data):
        """
        Enhanced import_teams method with bulletproof protection.
        """
        return bulletproof_import_teams(self, conn, teams_data)
    
    # Replace the method
    etl_class.import_teams = enhanced_import_teams
    
    # Store reference to original for potential rollback
    etl_class._original_import_teams = original_import_teams
    
    logger.info(f"✅ Bulletproof ETL enabled for {etl_class.__name__}")

def disable_bulletproof_etl(etl_class):
    """
    Disable bulletproof ETL and restore original method.
    
    Args:
        etl_class: The ETL class to restore
    """
    
    if hasattr(etl_class, '_original_import_teams'):
        etl_class.import_teams = etl_class._original_import_teams
        delattr(etl_class, '_original_import_teams')
        logger.info(f"✅ Bulletproof ETL disabled for {etl_class.__name__}")
    else:
        logger.warning(f"⚠️  No original method found for {etl_class.__name__}")

def create_bulletproof_etl_wrapper(etl_instance):
    """
    Create a bulletproof wrapper around an existing ETL instance.
    
    Args:
        etl_instance: The ETL instance to wrap
        
    Returns:
        BulletproofETLWrapper: Wrapped ETL instance with bulletproof protection
    """
    
    class BulletproofETLWrapper:
        """
        Wrapper class that provides bulletproof protection for ETL operations.
        """
        
        def __init__(self, original_etl):
            self.original_etl = original_etl
            self.bulletproof = BulletproofTeamPreservation()
            
        def run(self, *args, **kwargs):
            """
            Run ETL with bulletproof protection.
            """
            logger.info("🚀 Starting Bulletproof ETL Run")
            
            try:
                # Get database connection
                conn = get_db()
                
                # Step 1: Pre-ETL validation and backup
                logger.info("🔍 Pre-ETL validation and backup...")
                
                # Validate constraints
                is_safe, issues = self.bulletproof.validate_constraints(conn)
                if not is_safe:
                    logger.warning("⚠️  Constraint issues detected, attempting repair...")
                    if not self.bulletproof.repair_constraints(conn):
                        logger.error("❌ Constraint repair failed - aborting ETL")
                        return False
                
                # Backup user data
                backup_stats = self.bulletproof.backup_user_data(conn)
                logger.info(f"✅ Backup completed: {backup_stats}")
                
                # Step 2: Run original ETL with bulletproof team import
                logger.info("🏆 Running ETL with bulletproof protection...")
                
                # Replace the import_teams method temporarily
                original_method = getattr(self.original_etl, 'import_teams', None)
                self.original_etl.import_teams = lambda conn, teams_data: bulletproof_import_teams(self.original_etl, conn, teams_data)
                
                try:
                    # Run the original ETL
                    result = self.original_etl.run(*args, **kwargs)
                finally:
                    # Restore original method
                    if original_method:
                        self.original_etl.import_teams = original_method
                
                # Step 3: Post-ETL restoration and health check
                logger.info("🔄 Post-ETL restoration and health check...")
                
                # Detect and fix any remaining orphans
                orphan_stats = self.bulletproof.detect_and_fix_orphans(conn)
                logger.info(f"✅ Orphan detection and fix completed: {orphan_stats}")
                
                # Generate health report
                health_report = self.bulletproof.get_health_report()
                logger.info(f"📈 Final Health Score: {health_report['health_score']}/100")
                
                # Cleanup
                self.bulletproof.cleanup_backup_tables(conn)
                
                logger.info("🎉 Bulletproof ETL completed successfully!")
                return result
                
            except Exception as e:
                logger.error(f"❌ Bulletproof ETL failed: {str(e)}")
                return False
        
        def __getattr__(self, name):
            """
            Delegate all other attributes to the original ETL instance.
            """
            return getattr(self.original_etl, name)
    
    return BulletproofETLWrapper(etl_instance)

def emergency_repair_orphaned_records():
    """
    Emergency repair function for orphaned records.
    
    This function can be called independently to fix orphaned records
    without running a full ETL import.
    """
    
    logger.info("🚨 Starting Emergency Orphan Repair")
    
    try:
        conn = get_db()
        bulletproof = BulletproofTeamPreservation()
        
        # Detect and fix orphans
        orphan_stats = bulletproof.detect_and_fix_orphans(conn)
        
        # Generate health report
        health_report = bulletproof.get_health_report()
        
        logger.info(f"✅ Emergency repair completed: {orphan_stats}")
        logger.info(f"📈 Health Score: {health_report['health_score']}/100")
        
        return {
            'orphans_fixed': orphan_stats.get('fixed', 0),
            'health_score': health_report['health_score'],
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"❌ Emergency repair failed: {str(e)}")
        return {
            'error': str(e),
            'status': 'failed'
        }

def health_check_etl_system():
    """
    Comprehensive health check for the ETL system.
    
    Returns:
        Dict[str, Any]: Health report
    """
    
    logger.info("🔍 Running ETL System Health Check")
    
    try:
        conn = get_db()
        bulletproof = BulletproofTeamPreservation()
        
        # Generate health report
        health_report = bulletproof.get_health_report()
        
        # Additional checks
        constraint_check = bulletproof.validate_constraints(conn)
        
        health_report['constraint_status'] = 'healthy' if constraint_check[0] else 'needs_attention'
        health_report['constraint_issues'] = constraint_check[1] if not constraint_check[0] else []
        
        logger.info(f"📊 Health Check Results:")
        logger.info(f"   Health Score: {health_report['health_score']}/100")
        logger.info(f"   Total Orphans: {health_report['total_orphans']}")
        logger.info(f"   Constraint Status: {health_report['constraint_status']}")
        
        return health_report
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return {
            'error': str(e),
            'status': 'error'
        } 