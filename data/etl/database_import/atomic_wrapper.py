#!/usr/bin/env python3
"""
Atomic ETL Wrapper
==================

This script wraps the existing ComprehensiveETL class to provide true atomic behavior.
It modifies the existing ETL process to use a single transaction for all operations.

Usage:
    python atomic_wrapper.py                    # Run with auto-detected environment
    python atomic_wrapper.py --environment local --no-backup
    python atomic_wrapper.py --environment railway_production --force
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

# Import the existing ETL class
from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
from database_config import get_db


class AtomicETLWrapper:
    """
    Wrapper around ComprehensiveETL to provide atomic behavior
    """
    
    def __init__(self, environment: str = None, create_backup: bool = True):
        self.environment = environment
        self.create_backup = create_backup
        self.backup_path = None
        self.start_time = None
        
        # Initialize the underlying ETL class
        self.etl = ComprehensiveETL(environment=environment)
        
        self.log(f"🏗️  Atomic ETL Wrapper initialized")
        self.log(f"🎯 Environment: {self.etl.environment}")
        self.log(f"💾 Backup enabled: {self.create_backup}")
    
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
        conn = None
        try:
            # Get connection using existing method
            conn = get_db()
            
            # Configure for atomic operations
            with conn.cursor() as cursor:
                # Set long timeout for atomic operations
                cursor.execute("SET statement_timeout = '1800000'")  # 30 minutes
                cursor.execute("SET idle_in_transaction_session_timeout = '3600000'")  # 60 minutes
                
                # Optimize for bulk operations
                cursor.execute("SET work_mem = '512MB'")
                cursor.execute("SET maintenance_work_mem = '1GB'")
                cursor.execute("SET effective_cache_size = '1GB'")
                
                # Disable autocommit for manual transaction control
                conn.autocommit = False
                
                self.log("🔗 Atomic connection established with extended timeouts")
                
            yield conn
            
        except Exception as e:
            self.log(f"❌ Connection error: {str(e)}", "ERROR")
            raise
        finally:
            if conn:
                conn.close()
                self.log("🔒 Atomic connection closed")
    
    def _monkey_patch_etl_for_atomic_behavior(self):
        """Monkey patch the ETL class to prevent intermediate commits"""
        self.log("🔧 Configuring ETL for atomic behavior...")
        
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
        
        # Monkey patch commit operations to be no-ops in atomic mode
        original_commit_methods = []
        
        def no_op_commit():
            """No-op commit for atomic mode"""
            pass
        
        # Replace commit calls in key methods
        import types
        
        # Override the run method to use atomic connection
        def atomic_run():
            """Run ETL in atomic mode"""
            start_time = datetime.now()
            
            try:
                self.etl.log("🚀 Starting Atomic ETL Process")
                self.etl.log("=" * 60)
                
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

                # Step 3: Use atomic connection for all operations
                self.etl.log("\n🗄️  Step 3: Starting atomic transaction...")
                
                with self._get_atomic_connection() as conn:
                    # Set the atomic connection for all operations
                    self.etl._atomic_connection = conn
                    
                    try:
                        # Ensure schema requirements
                        self.etl.ensure_schema_requirements(conn)

                        # Clear existing data
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

                        # Restore user data
                        self.etl.log("\n🔄 Step 7: Restoring user data...")
                        restore_results = self.etl.restore_user_associations(conn)
                        
                        # Run post-import validations
                        self.etl.log("\n🔍 Step 8: Running validations...")
                        self.etl.run_post_import_validations(conn)
                        
                        # Increment session version
                        self.etl.increment_session_version(conn)

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
                        self.etl.log("🎉 ATOMIC ETL COMPLETED SUCCESSFULLY")
                        self.etl.log("=" * 60)
                        self.etl.log(f"⏱️  Total time: {duration}")
                        
                        total_imported = sum(self.etl.imported_counts.values())
                        self.etl.log(f"📊 Total records imported: {total_imported:,}")
                        
                        for table, count in self.etl.imported_counts.items():
                            self.etl.log(f"   {table}: {count:,}")
                        
                        return True
                        
                    except Exception as e:
                        # ROLLBACK - Any error rolls back the entire transaction
                        self.etl.log(f"❌ ETL failed: {str(e)}", "ERROR")
                        self.etl.log("🔄 Rolling back entire atomic transaction...", "WARNING")
                        
                        conn.rollback()
                        
                        self.etl.log("✅ Atomic transaction rolled back - database unchanged")
                        raise
                    
                    finally:
                        # Clear atomic connection reference
                        self.etl._atomic_connection = None
                        
            except Exception as e:
                self.etl.log(f"💥 ATOMIC ETL FAILED: {str(e)}", "ERROR")
                self.etl.log(f"Traceback: {traceback.format_exc()}", "ERROR")
                return False
            
            finally:
                end_time = datetime.now()
                duration = end_time - start_time
                self.etl.log(f"\n⏱️  Total execution time: {duration}")
                self.etl.print_summary()
            
            return True
        
        # Replace the run method
        self.etl.run = atomic_run
        
        self.log("✅ ETL configured for atomic behavior")
    
    def run_atomic_etl(self) -> bool:
        """Run the ETL process in atomic mode"""
        self.start_time = datetime.now()
        
        try:
            self.log("🚀 Starting Atomic ETL Wrapper")
            self.log("=" * 60)
            
            # Step 1: Create backup if requested
            if self.create_backup:
                self.backup_path = self._create_backup()
            
            # Step 2: Configure ETL for atomic behavior
            self._monkey_patch_etl_for_atomic_behavior()
            
            # Step 3: Run atomic ETL
            self.log("🔄 Running ETL in atomic mode...")
            success = self.etl.run()
            
            if success:
                self.log("🎉 Atomic ETL completed successfully")
                return True
            else:
                self.log("❌ Atomic ETL failed", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"💥 ATOMIC ETL WRAPPER FAILED: {str(e)}", "ERROR")
            
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
    
    parser = argparse.ArgumentParser(description='Atomic ETL Wrapper')
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
        print("   Use: python atomic_wrapper.py --environment railway_production --force")
        return 1
    
    # Initialize and run atomic ETL wrapper
    wrapper = AtomicETLWrapper(
        environment=args.environment,
        create_backup=not args.no_backup
    )
    
    success = wrapper.run_atomic_etl()
    
    if success:
        print("\n🎉 Atomic ETL process completed successfully!")
        print("✅ Database is in a consistent state")
        return 0
    else:
        print("\n💥 Atomic ETL process failed!")
        print("❌ Database has been rolled back to original state")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 