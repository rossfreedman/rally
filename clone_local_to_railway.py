#!/usr/bin/env python3
"""
Clone Local Database to Railway
Safely syncs Railway database to exactly match local database (schema + data)
"""

import os
import sys
import subprocess
import json
import tempfile
from datetime import datetime
import psycopg2
from contextlib import contextmanager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseCloner:
    def __init__(self):
        self.local_url = "postgresql://postgres:postgres@localhost:5432/rally"
        self.railway_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        self.backup_file = None
        
    def backup_railway_database(self):
        """Create a backup of Railway database before making changes"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_file = f"railway_backup_before_clone_{timestamp}.sql"
        
        logger.info("🔄 Creating backup of Railway database...")
        
        try:
            # Use pg_dump to create backup
            result = subprocess.run([
                'pg_dump', 
                self.railway_url,
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                '-f', self.backup_file
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Railway database backup created: {self.backup_file}")
                return True
            else:
                logger.error(f"❌ Backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backup error: {e}")
            return False
    
    def generate_schema_migration(self):
        """Generate Alembic migration for schema differences"""
        logger.info("📝 Generating Alembic schema migration...")
        
        try:
            # Set environment to use Railway database for comparison
            os.environ['SYNC_RAILWAY'] = 'true'
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            migration_name = f"clone_local_to_railway_schema_{timestamp}"
            
            result = subprocess.run([
                sys.executable, "-m", "alembic", "revision", "--autogenerate",
                "--message", migration_name
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Schema migration generated successfully!")
                
                # Extract migration file path
                lines = result.stdout.strip().split('\n')
                migration_file = None
                for line in lines:
                    if 'Generating' in line and '.py' in line:
                        migration_file = line.split()[-1]
                        break
                
                return migration_file
            else:
                logger.error(f"❌ Migration generation failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Migration generation error: {e}")
            return None
        finally:
            os.environ.pop('SYNC_RAILWAY', None)
    
    def apply_schema_migration(self):
        """Apply the generated schema migration to Railway"""
        logger.info("🔄 Applying schema migration to Railway...")
        
        try:
            os.environ['SYNC_RAILWAY'] = 'true'
            
            result = subprocess.run([
                sys.executable, "-m", "alembic", "upgrade", "head"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Schema migration applied successfully!")
                return True
            else:
                logger.error(f"❌ Schema migration failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Schema migration error: {e}")
            return False
        finally:
            os.environ.pop('SYNC_RAILWAY', None)
    
    def get_table_dependencies(self):
        """Get table dependencies to determine import order"""
        # Tables that should be imported first (no foreign key dependencies)
        base_tables = [
            'alembic_version',
            'users', 
            'leagues',
            'clubs',
            'series'
        ]
        
        # Tables with foreign key dependencies (import after base tables)
        dependent_tables = [
            'club_leagues',
            'series_leagues', 
            'player_history',
            'user_player_associations',
            'player_availability',
            'schedule',
            'match_scores',
            'series_stats',
            'user_instructions',
            'user_activity_logs'
        ]
        
        return base_tables + dependent_tables
    
    def truncate_railway_tables(self):
        """Truncate Railway tables to prepare for data import"""
        logger.info("🗑️  Truncating Railway tables for fresh data import...")
        
        try:
            import psycopg2
            conn = psycopg2.connect(self.railway_url)
            
            with conn.cursor() as cursor:
                # Get all table names except alembic_version
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename != 'alembic_version'
                    ORDER BY tablename
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Disable foreign key constraints temporarily
                cursor.execute("SET session_replication_role = replica;")
                
                # Truncate all tables
                for table in tables:
                    cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                    logger.info(f"  Truncated: {table}")
                
                # Re-enable foreign key constraints
                cursor.execute("SET session_replication_role = DEFAULT;")
                
                conn.commit()
                logger.info("✅ All Railway tables truncated successfully!")
                return True
                
        except Exception as e:
            logger.error(f"❌ Table truncation failed: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def copy_table_data(self, table_name):
        """Copy data from local table to Railway table"""
        try:
            import psycopg2
            
            # Connect to both databases
            local_conn = psycopg2.connect(self.local_url)
            railway_conn = psycopg2.connect(self.railway_url)
            
            with local_conn.cursor() as local_cursor, railway_conn.cursor() as railway_cursor:
                # Get column names
                local_cursor.execute(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    ORDER BY ordinal_position
                """)
                columns = [row[0] for row in local_cursor.fetchall()]
                
                if not columns:
                    logger.warning(f"No columns found for table {table_name}")
                    return True
                
                # Get data from local
                local_cursor.execute(f"SELECT * FROM {table_name}")
                rows = local_cursor.fetchall()
                
                if not rows:
                    logger.info(f"  {table_name}: No data to copy")
                    return True
                
                # Prepare insert statement
                placeholders = ', '.join(['%s'] * len(columns))
                column_names = ', '.join(columns)
                insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
                
                # Insert data in batches
                batch_size = 1000
                total_rows = len(rows)
                
                for i in range(0, total_rows, batch_size):
                    batch = rows[i:i + batch_size]
                    railway_cursor.executemany(insert_sql, batch)
                
                railway_conn.commit()
                logger.info(f"  {table_name}: Copied {total_rows} rows")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to copy data for {table_name}: {e}")
            return False
        finally:
            if 'local_conn' in locals():
                local_conn.close()
            if 'railway_conn' in locals():
                railway_conn.close()
    
    def copy_all_data(self):
        """Copy all data from local to Railway in correct order"""
        logger.info("📊 Copying all data from local to Railway...")
        
        tables = self.get_table_dependencies()
        failed_tables = []
        
        for table in tables:
            logger.info(f"Copying table: {table}")
            if not self.copy_table_data(table):
                failed_tables.append(table)
        
        if failed_tables:
            logger.warning(f"⚠️  Failed to copy some tables: {failed_tables}")
            return False
        else:
            logger.info("✅ All data copied successfully!")
            return True
    
    def verify_clone_success(self):
        """Verify that Railway database now matches local database"""
        logger.info("🔍 Verifying clone success...")
        
        try:
            # Run our comparison script
            result = subprocess.run([
                sys.executable, "compare_databases.py"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Clone verification: Databases are identical!")
                return True
            else:
                logger.warning("⚠️  Clone verification: Some differences remain")
                logger.warning(result.stdout)
                return False
                
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
    
    def run_complete_clone(self):
        """Run the complete cloning process"""
        logger.info("🚀 Starting complete database clone: Local → Railway")
        logger.info("=" * 60)
        
        steps = [
            ("Creating Railway backup", self.backup_railway_database),
            ("Generating schema migration", lambda: self.generate_schema_migration() is not None),
            ("Applying schema migration", self.apply_schema_migration),
            ("Truncating Railway tables", self.truncate_railway_tables),
            ("Copying all data", self.copy_all_data),
            ("Verifying clone success", self.verify_clone_success)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\n📋 Step: {step_name}")
            if not step_func():
                logger.error(f"❌ FAILED: {step_name}")
                logger.error("🛑 Clone process stopped due to error")
                
                if self.backup_file:
                    logger.info(f"💾 Railway backup available at: {self.backup_file}")
                    logger.info("You can restore Railway database using:")
                    logger.info(f"psql {self.railway_url} < {self.backup_file}")
                
                return False
            else:
                logger.info(f"✅ SUCCESS: {step_name}")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 DATABASE CLONE COMPLETED SUCCESSFULLY!")
        logger.info("✅ Railway database now perfectly matches local database")
        
        if self.backup_file:
            logger.info(f"💾 Railway backup saved at: {self.backup_file}")
        
        return True

def main():
    """Main function with user confirmation"""
    print("🏓 RALLY DATABASE CLONE: Local → Railway")
    print("=" * 60)
    print("This will make Railway database identical to local database.")
    print("⚠️  WARNING: This will REPLACE all data in Railway database!")
    print()
    print("📋 Process Overview:")
    print("1. Backup Railway database")
    print("2. Generate schema migration using Alembic")
    print("3. Apply schema changes to Railway")
    print("4. Truncate Railway tables")
    print("5. Copy all data from local to Railway")
    print("6. Verify clone success")
    print()
    
    # Get user confirmation
    response = input("🤔 Do you want to proceed? (type 'YES' to confirm): ").strip()
    
    if response != 'YES':
        print("👍 Clone cancelled. No changes made.")
        return 0
    
    print("\n🚀 Starting clone process...")
    
    cloner = DatabaseCloner()
    success = cloner.run_complete_clone()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 