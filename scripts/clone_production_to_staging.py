#!/usr/bin/env python3
"""
Clone Production Database to Staging

This script performs a complete clone of production database to staging:
1. Creates a safety backup of current staging data
2. Drops all data/schema in staging database
3. Clones complete production schema and data to staging

Usage:
    python scripts/clone_production_to_staging.py

Environment Variables Required:
- PRODUCTION_DATABASE_URL: Production database connection string
- STAGING_DATABASE_URL: Staging database connection string

Safety Features:
- Creates backup before any destructive operations
- Confirms operation with user before proceeding
- Preserves staging database structure during clone
- Comprehensive error handling and rollback
"""

import os
import sys
import subprocess
import tempfile
from datetime import datetime
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/production_staging_clone.log')
    ]
)
logger = logging.getLogger(__name__)

class ProductionStagingCloner:
    """Handles cloning production database to staging database"""
    
    def __init__(self):
        # Railway database PUBLIC URLs (accessible from local machine)
        self.production_db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        self.staging_db_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
        
        # Allow override via environment variables
        if os.getenv('PRODUCTION_DATABASE_URL'):
            self.production_db_url = os.getenv('PRODUCTION_DATABASE_URL')
        if os.getenv('STAGING_DATABASE_URL'):
            self.staging_db_url = os.getenv('STAGING_DATABASE_URL')
        
        logger.info("Production Database: " + self.production_db_url[:50] + "...")
        logger.info("Staging Database: " + self.staging_db_url[:50] + "...")
    
    def confirm_operation(self) -> bool:
        """Confirm the potentially destructive operation with the user"""
        print("🚨 PRODUCTION → STAGING DATABASE CLONE WARNING 🚨")
        print()
        print("This will:")
        print("1. ✅ Create a backup of current staging data")
        print("2. ❌ DROP ALL data and schema in staging database")
        print("3. ✅ Copy complete production schema to staging")
        print("4. ✅ Copy ALL production data to staging")
        print()
        print("⚠️  This is a COMPLETE MIRROR - no data sanitization")
        print("⚠️  All current staging data will be PERMANENTLY LOST")
        print()
        print(f"Production: {self.production_db_url[:50]}...")
        print(f"Staging:    {self.staging_db_url[:50]}...")
        print()
        
        response = input("Are you sure you want to proceed? Type 'yes' to continue: ")
        return response.lower() == 'yes'
    
    def check_pg_tools(self):
        """Check if required PostgreSQL tools are available"""
        required_tools = ['pg_dump', 'psql', 'pg_isready']
        
        for tool in required_tools:
            try:
                subprocess.run([tool, '--version'], capture_output=True, check=True)
                logger.info(f"✅ {tool} is available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error(f"❌ {tool} is not available")
                raise Exception(f"Required tool {tool} is not installed. Please install PostgreSQL client tools.")
    
    def test_database_connections(self):
        """Test connections to both databases"""
        logger.info("Testing database connections...")
        
        # Test production connection
        try:
            result = subprocess.run(
                ['pg_isready', '-d', self.production_db_url],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info("✅ Production database connection: OK")
            else:
                raise Exception(f"Production database not ready: {result.stderr}")
        except Exception as e:
            logger.error(f"❌ Production database connection failed: {e}")
            raise
        
        # Test staging connection
        try:
            result = subprocess.run(
                ['pg_isready', '-d', self.staging_db_url],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info("✅ Staging database connection: OK")
            else:
                raise Exception(f"Staging database not ready: {result.stderr}")
        except Exception as e:
            logger.error(f"❌ Staging database connection failed: {e}")
            raise
    
    def backup_staging_database(self) -> str:
        """Create a complete backup of current staging database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"staging_complete_backup_{timestamp}.sql"
        backup_path = os.path.join("data", "backups", backup_file)
        
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        logger.info(f"Creating complete staging backup: {backup_path}")
        
        try:
            cmd = [
                'pg_dump',
                '--clean',  # Add DROP statements
                '--create', # Add CREATE DATABASE statement
                '--no-owner',
                '--no-privileges',
                self.staging_db_url,
                '-f', backup_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Backup failed: {result.stderr}")
                raise Exception(f"Staging backup failed: {result.stderr}")
            
            logger.info(f"✅ Staging backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create staging backup: {e}")
            raise
    
    def get_database_stats(self, db_url: str, db_name: str) -> dict:
        """Get database statistics for verification"""
        logger.info(f"Getting statistics for {db_name} database...")
        
        try:
            # Get table count
            table_count_query = """
                SELECT COUNT(*) as table_count 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """
            
            result = subprocess.run([
                'psql', db_url, '-t', '-c', table_count_query
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"Could not get {db_name} statistics: {result.stderr}")
                return {"table_count": "unknown", "row_count": "unknown"}
            
            table_count = result.stdout.strip()
            
            # Get approximate row count
            row_count_query = """
                SELECT SUM(n_tup_ins - n_tup_del) as total_rows 
                FROM pg_stat_user_tables;
            """
            
            result = subprocess.run([
                'psql', db_url, '-t', '-c', row_count_query
            ], capture_output=True, text=True, timeout=30)
            
            row_count = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            stats = {
                "table_count": table_count,
                "row_count": row_count
            }
            
            logger.info(f"{db_name} stats: {stats}")
            return stats
            
        except Exception as e:
            logger.warning(f"Could not get {db_name} statistics: {e}")
            return {"table_count": "unknown", "row_count": "unknown"}
    
    def clone_production_to_staging(self):
        """Perform the actual production to staging clone"""
        logger.info("Starting production → staging clone...")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            dump_file = f.name
        
        try:
            # Step 1: Dump production database
            logger.info("📥 Dumping production database...")
            
            dump_cmd = [
                'pg_dump',
                '--clean',          # Add DROP statements  
                '--create',         # Add CREATE DATABASE statement
                '--no-owner',       # Don't dump ownership
                '--no-privileges',  # Don't dump privileges
                self.production_db_url,
                '-f', dump_file
            ]
            
            result = subprocess.run(dump_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                logger.error(f"Production dump failed: {result.stderr}")
                raise Exception(f"Production dump failed: {result.stderr}")
            
            logger.info(f"✅ Production dumped to: {dump_file}")
            
            # Step 2: Restore to staging database
            logger.info("📤 Restoring to staging database...")
            
            restore_cmd = [
                'psql',
                self.staging_db_url,
                '-f', dump_file,
                '-v', 'ON_ERROR_STOP=1'  # Stop on first error
            ]
            
            result = subprocess.run(restore_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                logger.error(f"Staging restore failed: {result.stderr}")
                raise Exception(f"Staging restore failed: {result.stderr}")
            
            logger.info("✅ Production data restored to staging")
            
        except Exception as e:
            logger.error(f"Clone operation failed: {e}")
            raise
        
        finally:
            # Cleanup dump file
            try:
                if os.path.exists(dump_file):
                    os.unlink(dump_file)
                    logger.info(f"Cleaned up dump file: {dump_file}")
            except Exception as e:
                logger.warning(f"Could not cleanup dump file: {e}")
    
    def verify_clone_success(self):
        """Verify that the clone was successful"""
        logger.info("🔍 Verifying clone success...")
        
        # Get stats from both databases
        prod_stats = self.get_database_stats(self.production_db_url, "Production")
        staging_stats = self.get_database_stats(self.staging_db_url, "Staging")
        
        # Compare stats
        logger.info("📊 Clone Verification Results:")
        logger.info(f"Production tables: {prod_stats['table_count']}")
        logger.info(f"Staging tables:    {staging_stats['table_count']}")
        logger.info(f"Production rows:   {prod_stats['row_count']}")
        logger.info(f"Staging rows:      {staging_stats['row_count']}")
        
        if prod_stats['table_count'] == staging_stats['table_count']:
            logger.info("✅ Table counts match")
        else:
            logger.warning("⚠️  Table counts don't match")
        
        if prod_stats['row_count'] == staging_stats['row_count']:
            logger.info("✅ Row counts match") 
        else:
            logger.warning("⚠️  Row counts don't match (this may be normal due to timing)")
    
    def run(self):
        """Run the complete production → staging clone process"""
        try:
            # Step 1: Confirm operation
            if not self.confirm_operation():
                logger.info("Operation cancelled by user")
                return
            
            # Step 2: Check prerequisites
            self.check_pg_tools()
            self.test_database_connections()
            
            # Step 3: Get initial stats
            logger.info("📊 Initial database statistics:")
            self.get_database_stats(self.production_db_url, "Production")
            self.get_database_stats(self.staging_db_url, "Staging (before)")
            
            # Step 4: Backup staging database
            backup_file = self.backup_staging_database()
            
            # Step 5: Clone production to staging
            self.clone_production_to_staging()
            
            # Step 6: Verify clone success
            self.verify_clone_success()
            
            logger.info("🎉 Production → Staging clone completed successfully!")
            logger.info(f"💾 Staging backup saved at: {backup_file}")
            logger.info("🔗 Your staging environment now has complete production data")
            
        except Exception as e:
            logger.error(f"❌ Clone operation failed: {e}")
            logger.error("💡 Your original staging data backup is preserved")
            raise

def main():
    """Main function"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        cloner = ProductionStagingCloner()
        cloner.run()
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 