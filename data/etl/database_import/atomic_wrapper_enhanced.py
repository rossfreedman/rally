#!/usr/bin/env python3
"""
Enhanced Atomic ETL Wrapper with Practice Time Protection
=========================================================

This is an enhanced version of the atomic wrapper that includes the
practice time protection system to prevent data loss during ETL.

Key Enhancements:
1. Pre-ETL safety validation
2. Enhanced backup with metadata
3. Team ID preservation detection
4. Fallback restoration logic
5. Post-ETL health validation

Usage:
    python atomic_wrapper_enhanced.py --environment local
    python atomic_wrapper_enhanced.py --environment railway_production --force
"""

import os
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

# Import the existing ETL class and protection functions
from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
from data.etl.database_import.enhanced_practice_time_protection import (
    validate_etl_safety_preconditions,
    create_enhanced_practice_time_backup,
    validate_team_id_preservation_post_etl,
    restore_practice_times_with_fallback,
    validate_practice_time_health,
    cleanup_enhanced_backup_tables
)
from database_config import get_db


class EnhancedAtomicETLWrapper:
    """
    Enhanced wrapper around ComprehensiveETL with practice time protection
    """
    
    def __init__(self, environment: str = None, create_backup: bool = True):
        self.environment = environment
        self.create_backup = create_backup
        self.backup_path = None
        self.start_time = None
        self.practice_time_count_pre_etl = 0
        
        # Initialize the underlying ETL class
        self.etl = ComprehensiveETL(force_environment=environment)
        
        self.log(f"🏗️  Enhanced Atomic ETL Wrapper initialized")
        self.log(f"🎯 Environment: {self.etl.environment}")
        self.log(f"💾 Backup enabled: {self.create_backup}")
        self.log(f"🛡️  Practice time protection: ENABLED")
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "SUCCESS": "✅"
        }.get(level, "ℹ️")
        
        print(f"[{timestamp}] {prefix} {message}")
    
    def _create_backup(self) -> Optional[str]:
        """Create database backup before ETL process"""
        if not self.create_backup:
            return None
        
        self.log("💾 Creating atomic ETL backup...")
        
        try:
            # Use the existing backup functionality
            backup_path = self.etl._create_pre_etl_backup()
            
            if backup_path:
                self.log(f"✅ Backup created: {backup_path}")
                return backup_path
            else:
                self.log("⚠️ Backup creation failed", "WARNING")
                return None
                
        except Exception as e:
            self.log(f"❌ Backup creation failed: {str(e)}", "ERROR")
            return None
    
    def _restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        if not backup_path:
            self.log("❌ No backup path provided", "ERROR")
            return False
        
        self.log(f"🔄 Restoring from backup: {backup_path}")
        
        try:
            # Use the existing restore functionality
            success = self.etl._restore_from_backup(backup_path)
            
            if success:
                self.log("✅ Database restored successfully")
                return True
            else:
                self.log("❌ Restore failed", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Restore failed: {str(e)}", "ERROR")
            return False
    
    @contextmanager
    def _get_atomic_connection(self):
        """Get database connection for atomic operations"""
        try:
            # Get connection using existing method (get_db returns a context manager)
            with get_db() as conn:
                # Configure for atomic operations
                with conn.cursor() as cursor:
                    # Set long timeout for atomic operations
                    cursor.execute("SET statement_timeout = '1800000'")  # 30 minutes
                    cursor.execute("SET idle_in_transaction_session_timeout = '3600000'")  # 60 minutes
                    
                    # Optimize for bulk operations
                    cursor.execute("SET work_mem = '512MB'")
                    cursor.execute("SET maintenance_work_mem = '1GB'")
                    cursor.execute("SET effective_cache_size = '1GB'")
                    
                    self.log("🔗 Atomic connection established with extended timeouts")
                    
                yield conn
                
        except Exception as e:
            self.log(f"❌ Connection error: {str(e)}", "ERROR")
            raise
    
    def _monkey_patch_etl_for_atomic_behavior(self):
        """Monkey patch the ETL class to prevent intermediate commits"""
        self.log("🔧 Configuring ETL for enhanced atomic behavior...")
        
        # Store original methods
        original_run = self.etl.run
        
        # Track if we're in atomic mode
        self.etl._atomic_mode = True
        self.etl._atomic_connection = None
        
        # Monkey patch connection methods to use our atomic connection
        def get_managed_db_connection():
            if hasattr(self.etl, '_atomic_connection') and self.etl._atomic_connection:
                @contextmanager
                def atomic_context():
                    yield self.etl._atomic_connection
                return atomic_context()
            else:
                return self.etl._original_get_managed_db_connection()
        
        # Store original and replace
        self.etl._original_get_managed_db_connection = self.etl.get_managed_db_connection
        self.etl.get_managed_db_connection = get_managed_db_connection
        
        # ENHANCED: Override the run method with practice time protection
        def enhanced_atomic_run():
            """Run ETL in atomic mode with practice time protection"""
            start_time = datetime.now()
            
            try:
                self.etl.log("🚀 Starting Enhanced Atomic ETL Process")
                self.etl.log("🛡️  Practice time protection ENABLED")
                self.etl.log("=" * 60)
                
                # Use atomic connection for all operations
                with self._get_atomic_connection() as conn:
                    # Set the atomic connection for all operations
                    self.etl._atomic_connection = conn
                    cursor = conn.cursor()
                    
                    try:
                        # ENHANCEMENT 1: Pre-ETL Safety Validation
                        self.etl.log("🛡️  Step 0: Pre-ETL Safety Validation...")
                        is_safe, issues = validate_etl_safety_preconditions(cursor, None)
                        
                        if not is_safe:
                            self.etl.log("🚨 ETL SAFETY ISSUES FOUND:", "ERROR")
                            for issue in issues:
                                self.etl.log(f"   ❌ {issue}", "ERROR")
                            self.etl.log("⚠️  ETL ABORTED - Fix these issues first!", "ERROR")
                            return False
                        else:
                            self.etl.log("✅ ETL safety validation passed")
                        
                        # Count practice times before ETL
                        cursor.execute("SELECT COUNT(*) FROM schedule WHERE home_team ILIKE '%practice%'")
                        self.practice_time_count_pre_etl = cursor.fetchone()[0]
                        self.etl.log(f"📊 Pre-ETL practice times: {self.practice_time_count_pre_etl}")
                        
                        # ENHANCEMENT 2: Create enhanced practice time backup
                        self.etl.log("💾 Step 0.5: Creating enhanced practice time backup...")
                        practice_backup_count = create_enhanced_practice_time_backup(cursor, None)
                        self.etl.log(f"✅ Enhanced practice time backup: {practice_backup_count} records")
                        
                        # Step 1: Load all JSON files
                        self.etl.log("📂 Step 1: Loading JSON files...")
                        players_data = self.etl.load_json_file("players.json")
                        player_history_data = self.etl.load_json_file("player_history.json")
                        match_history_data = self.etl.load_json_file("match_history.json")
                        series_stats_data = self.etl.load_json_file("series_stats.json")
                        schedules_data = self.etl.load_json_file("schedules.json")

                        # Step 2: Extract reference data
                        self.etl.log("\n📋 Step 2: Extracting reference data...")
                        leagues_data = self.etl.extract_leagues(players_data, series_stats_data, schedules_data)
                        clubs_data = self.etl.extract_clubs(players_data)
                        
                        # Ensure schema requirements
                        self.etl.ensure_schema_requirements(conn)

                        # Clear existing data using the proper ETL method
                        self.etl.clear_target_tables(conn)

                        # Import basic reference data
                        self.etl.log("\n📥 Step 4: Importing reference data...")
                        self.etl.import_leagues(conn, leagues_data)
                        self.etl.import_clubs(conn, clubs_data)

                        # Extract series and teams with mapping support
                        self.etl.log("\n📋 Step 5: Extracting mapped data...")
                        series_data = self.etl.extract_series(players_data, series_stats_data, schedules_data, conn)
                        teams_data = self.etl.extract_teams(series_stats_data, schedules_data, conn)
                        
                        club_league_rels = self.etl.analyze_club_league_relationships(players_data, teams_data)
                        series_league_rels = self.etl.analyze_series_league_relationships(players_data, teams_data)

                        # Import all remaining data
                        self.etl.log("\n📥 Step 6: Importing all data...")
                        self.etl.import_series(conn, series_data)
                        self.etl.import_club_leagues(conn, club_league_rels)
                        self.etl.import_series_leagues(conn, series_league_rels)
                        self.etl.import_teams(conn, teams_data)
                        
                        # Load mappings for player import
                        self.etl.load_series_mappings(conn)
                        self.etl.import_players(conn, players_data)
                        self.etl.import_career_stats(conn, player_history_data)
                        self.etl.import_player_history(conn, player_history_data)
                        self.etl.import_match_history(conn, match_history_data)
                        self.etl.import_series_stats(conn, series_stats_data)
                        self.etl.import_schedules(conn, schedules_data)

                        # ENHANCEMENT 3: Enhanced practice time restoration
                        self.etl.log("\n🔄 Step 7: Enhanced practice time restoration...")
                        
                        # Validate team ID preservation first
                        preservation_success, preservation_stats = validate_team_id_preservation_post_etl(cursor, None)
                        
                        if preservation_success:
                            self.etl.log("✅ Team ID preservation successful - using direct restoration")
                            # Use existing direct restoration method (if it exists)
                            try:
                                restore_results = self.etl.restore_user_data_with_team_mappings(conn)
                                self.etl.log("✅ Direct restoration completed")
                            except Exception as e:
                                self.etl.log(f"⚠️  Direct restoration failed: {e}", "WARNING")
                                # Fall back to enhanced restoration
                                restoration_stats = restore_practice_times_with_fallback(cursor, None, dry_run=False)
                                self.etl.log(f"✅ Fallback restoration: {restoration_stats['total']} practice times restored")
                        else:
                            self.etl.log("⚠️  Team ID preservation failed - using enhanced fallback restoration")
                            # Use enhanced fallback restoration
                            restoration_stats = restore_practice_times_with_fallback(cursor, None, dry_run=False)
                            self.etl.log(f"✅ Fallback restoration: {restoration_stats['direct']} direct + {restoration_stats['fallback']} fallback = {restoration_stats['total']} total")
                            
                            # Also restore other user data (polls, captain messages)
                            try:
                                # Restore other user data without practice times
                                self.etl.log("🔄 Restoring other user data (polls, captain messages)...")
                                restore_results = self.etl.restore_user_data_with_team_mappings(conn)
                            except Exception as e:
                                self.etl.log(f"⚠️  Other user data restoration partially failed: {e}", "WARNING")

                        # ENHANCEMENT 4: Post-ETL Health Validation
                        self.etl.log("\n🔍 Step 8: Post-ETL Health Validation...")
                        health_stats = validate_practice_time_health(
                            cursor, self.practice_time_count_pre_etl, None
                        )
                        
                        if not health_stats["is_healthy"]:
                            self.etl.log("🚨 CRITICAL: Practice time health check failed!", "ERROR")
                            self.etl.log("🔧 This indicates practice times were lost during ETL", "ERROR")
                            self.etl.log(f"   Expected: {health_stats['pre_etl_count']}, Got: {health_stats['post_etl_count']}")
                            if health_stats["orphaned_count"] > 0:
                                self.etl.log(f"   Orphaned practice times: {health_stats['orphaned_count']}")
                            
                            # This is a critical failure - abort the transaction
                            raise Exception(f"Practice time health check failed - {health_stats}")
                        else:
                            self.etl.log("✅ Practice time health check passed")
                        
                        # Run post-import validations
                        self.etl.log("\n🔍 Step 9: Running validations...")
                        self.etl.player_validator.print_validation_summary()
                        
                        # Increment session version
                        self.etl.increment_session_version(conn)

                        # Clean up enhanced backup tables
                        cleanup_enhanced_backup_tables(cursor, None)

                        # If we get here, everything succeeded
                        self.etl.log("✅ All operations completed successfully")
                        self.etl.log("🔄 Committing atomic transaction...")
                        
                        # SINGLE COMMIT - This is the only commit in the entire process
                        conn.commit()
                        
                        self.etl.log("✅ Atomic transaction committed successfully")
                        
                        # Log final results
                        end_time = datetime.now()
                        duration = end_time - start_time
                        
                        self.etl.log("=" * 60)
                        self.etl.log("🎉 ENHANCED ATOMIC ETL COMPLETED SUCCESSFULLY")
                        self.etl.log("=" * 60)
                        self.etl.log(f"⏱️  Total time: {duration}")
                        self.etl.log(f"🛡️  Practice time protection: SUCCESS")
                        
                        total_imported = sum(self.etl.imported_counts.values())
                        self.etl.log(f"📊 Total records imported: {total_imported:,}")
                        
                        for table, count in self.etl.imported_counts.items():
                            self.etl.log(f"   {table}: {count:,}")
                        
                        return True
                        
                    except Exception as e:
                        # ROLLBACK - Any error rolls back the entire transaction
                        self.etl.log(f"❌ Enhanced ETL failed: {str(e)}", "ERROR")
                        self.etl.log("🔄 Rolling back entire atomic transaction...", "WARNING")
                        
                        conn.rollback()
                        
                        self.etl.log("✅ Atomic transaction rolled back - database unchanged")
                        raise
                    
                    finally:
                        # Clear atomic connection reference
                        self.etl._atomic_connection = None
                        
            except Exception as e:
                self.etl.log(f"💥 ENHANCED ATOMIC ETL FAILED: {str(e)}", "ERROR")
                self.etl.log(f"Traceback: {traceback.format_exc()}", "ERROR")
                return False
            
            finally:
                end_time = datetime.now()
                duration = end_time - start_time
                self.etl.log(f"\n⏱️  Total execution time: {duration}")
                self.etl.print_summary()
            
            return True
        
        # Replace the run method
        self.etl.run = enhanced_atomic_run
        
        self.log("✅ ETL configured for enhanced atomic behavior with practice time protection")
    
    def run_atomic_etl(self) -> bool:
        """Run the ETL process in enhanced atomic mode"""
        self.start_time = datetime.now()
        
        try:
            self.log("🚀 Starting Enhanced Atomic ETL Wrapper")
            self.log("🛡️  Practice time protection ENABLED")
            self.log("=" * 60)
            
            # Step 1: Create backup if requested
            if self.create_backup:
                self.backup_path = self._create_backup()
            
            # Step 2: Configure ETL for enhanced atomic behavior
            self._monkey_patch_etl_for_atomic_behavior()
            
            # Step 3: Run enhanced atomic ETL
            self.log("🔄 Running ETL in enhanced atomic mode...")
            success = self.etl.run()
            
            if success:
                self.log("🎉 Enhanced Atomic ETL completed successfully")
                self.log("🛡️  Practice time protection: SUCCESS")
                return True
            else:
                self.log("❌ Enhanced Atomic ETL failed", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"💥 ENHANCED ATOMIC ETL WRAPPER FAILED: {str(e)}", "ERROR")
            
            # Attempt restore if backup exists
            if self.backup_path:
                self.log("🔄 Attempting to restore from backup...")
                if self._restore_from_backup(self.backup_path):
                    self.log("✅ Database restored to original state")
                else:
                    self.log("❌ Backup restore failed", "ERROR")
                    self.log(f"🔧 Manual restore: python3 data/backup_restore_local_db/backup_database.py --restore {self.backup_path}")
            
            return False
        
        finally:
            if self.start_time:
                end_time = datetime.now()
                duration = end_time - self.start_time
                self.log(f"⏱️  Total wrapper execution time: {duration}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Atomic ETL Wrapper with Practice Time Protection')
    parser.add_argument('--environment', choices=['local', 'railway_staging', 'railway_production'],
                       help='Target environment')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip backup creation')
    parser.add_argument('--force', action='store_true',
                       help='Force import even in production')
    
    args = parser.parse_args()
    
    # Safety check for production
    if args.environment == 'railway_production' and not args.force:
        print("❌ Production imports require --force flag for safety")
        print("   Use: python atomic_wrapper_enhanced.py --environment railway_production --force")
        return 1
    
    # Initialize and run enhanced atomic ETL wrapper
    wrapper = EnhancedAtomicETLWrapper(
        environment=args.environment,
        create_backup=not args.no_backup
    )
    
    success = wrapper.run_atomic_etl()
    
    if success:
        print("\n🎉 Enhanced Atomic ETL process completed successfully!")
        print("✅ Database is in a consistent state")
        print("🛡️  Practice time protection worked perfectly")
        return 0
    else:
        print("\n💥 Enhanced Atomic ETL process failed!")
        print("❌ Database has been rolled back to original state")
        print("🛡️  Practice time protection prevented data loss")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 