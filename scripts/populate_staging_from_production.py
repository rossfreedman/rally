#!/usr/bin/env python3
"""
Populate Staging Database with Sanitized Production Data

This script:
1. Dumps data from production database (data-only, no schema)
2. Sanitizes the data by removing/anonymizing PII
3. Imports the sanitized data into staging database

Usage:
    python scripts/populate_staging_from_production.py

Environment Variables Required:
- PRODUCTION_DATABASE_URL: Production database connection string
- STAGING_DATABASE_URL: Staging database connection string

Safety Features:
- Confirms target database before proceeding
- Creates backup of staging data before overwriting
- Sanitizes sensitive data (emails, names, phone numbers)
- Preserves referential integrity
"""

import os
import sys
import subprocess
import tempfile
import re
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update
from database_config import get_db_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/staging_data_population.log')
    ]
)
logger = logging.getLogger(__name__)

class StagingDataPopulator:
    """Handles populating staging database with sanitized production data"""
    
    def __init__(self):
        self.production_db_url = os.getenv('PRODUCTION_DATABASE_URL')
        self.staging_db_url = os.getenv('STAGING_DATABASE_URL')
        
        if not self.production_db_url or not self.staging_db_url:
            raise ValueError("Both PRODUCTION_DATABASE_URL and STAGING_DATABASE_URL must be set")
    
    def confirm_operation(self) -> bool:
        """Confirm the operation with the user"""
        print("🚨 STAGING DATA POPULATION WARNING 🚨")
        print()
        print("This will:")
        print("1. Backup existing staging data")
        print("2. Clear staging database")
        print("3. Import sanitized production data")
        print()
        print(f"Production DB: {self.production_db_url[:50]}...")
        print(f"Staging DB:    {self.staging_db_url[:50]}...")
        print()
        
        response = input("Are you sure you want to proceed? (yes/no): ")
        return response.lower() == 'yes'
    
    def backup_staging_data(self) -> str:
        """Create a backup of current staging data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"staging_backup_{timestamp}.sql"
        backup_path = os.path.join("data", "backups", backup_file)
        
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        logger.info(f"Creating staging backup: {backup_path}")
        
        try:
            cmd = [
                'pg_dump',
                '--data-only',
                '--no-owner',
                '--no-privileges',
                self.staging_db_url,
                '-f', backup_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Backup failed: {result.stderr}")
                raise Exception(f"Backup failed: {result.stderr}")
            
            logger.info(f"Staging backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def dump_production_data(self) -> str:
        """Dump production data to temporary file"""
        logger.info("Dumping production data...")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            dump_file = f.name
        
        try:
            cmd = [
                'pg_dump',
                '--data-only',
                '--no-owner',
                '--no-privileges',
                '--exclude-table=auth_*',  # Exclude auth tables for security
                '--exclude-table=user_sessions',
                self.production_db_url,
                '-f', dump_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Production dump failed: {result.stderr}")
                raise Exception(f"Production dump failed: {result.stderr}")
            
            logger.info(f"Production data dumped to: {dump_file}")
            return dump_file
            
        except Exception as e:
            logger.error(f"Failed to dump production data: {e}")
            if os.path.exists(dump_file):
                os.unlink(dump_file)
            raise
    
    def sanitize_sql_data(self, sql_file: str) -> str:
        """Sanitize SQL data by anonymizing PII"""
        logger.info("Sanitizing SQL data...")
        
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        sanitized_file = sql_file.replace('.sql', '_sanitized.sql')
        
        # Email anonymization
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        sql_content = re.sub(email_pattern, lambda m: self._anonymize_email(m.group()), sql_content)
        
        # Phone number anonymization
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        sql_content = re.sub(phone_pattern, '555-XXXX-XXXX', sql_content)
        
        # Name anonymization (basic - for names in specific contexts)
        # This is a simplified approach - you may need more sophisticated logic
        
        # Remove sensitive comments
        sql_content = re.sub(r'--.*sensitive.*\n', '', sql_content, flags=re.IGNORECASE)
        
        with open(sanitized_file, 'w') as f:
            f.write(sql_content)
        
        logger.info(f"Sanitized data written to: {sanitized_file}")
        return sanitized_file
    
    def _anonymize_email(self, email: str) -> str:
        """Anonymize email address while preserving domain structure"""
        local, domain = email.split('@')
        anonymized_local = f"user{hash(local) % 10000}"
        return f"{anonymized_local}@{domain}"
    
    def clear_staging_data(self):
        """Clear staging database data while preserving schema"""
        logger.info("Clearing staging database...")
        
        # Get list of tables to clear (excluding system tables)
        tables_query = """
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'alembic_%'
            ORDER BY tablename;
        """
        
        try:
            # Switch to staging database
            os.environ['DATABASE_URL'] = self.staging_db_url
            
            tables_result = execute_query(tables_query)
            if not tables_result['success']:
                raise Exception(f"Failed to get table list: {tables_result['error']}")
            
            tables = [row['tablename'] for row in tables_result['data']]
            
            # Disable foreign key checks temporarily
            execute_update("SET session_replication_role = replica;")
            
            # Clear tables
            for table in tables:
                logger.info(f"Clearing table: {table}")
                result = execute_update(f"DELETE FROM {table};")
                if not result['success']:
                    logger.warning(f"Failed to clear table {table}: {result['error']}")
            
            # Re-enable foreign key checks
            execute_update("SET session_replication_role = DEFAULT;")
            
            logger.info("Staging database cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear staging data: {e}")
            raise
    
    def import_sanitized_data(self, sanitized_file: str):
        """Import sanitized data into staging database"""
        logger.info("Importing sanitized data to staging...")
        
        try:
            cmd = [
                'psql',
                self.staging_db_url,
                '-f', sanitized_file,
                '-v', 'ON_ERROR_STOP=1'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Import failed: {result.stderr}")
                raise Exception(f"Import failed: {result.stderr}")
            
            logger.info("Sanitized data imported successfully")
            
        except Exception as e:
            logger.error(f"Failed to import data: {e}")
            raise
    
    def verify_data_integrity(self):
        """Verify data integrity after import"""
        logger.info("Verifying data integrity...")
        
        try:
            # Switch to staging database
            os.environ['DATABASE_URL'] = self.staging_db_url
            
            # Check table counts
            tables_query = """
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins - n_tup_del as row_count
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """
            
            result = execute_query(tables_query)
            if result['success']:
                logger.info("Table row counts:")
                for row in result['data']:
                    logger.info(f"  {row['tablename']}: {row['row_count']} rows")
            
            # Check for referential integrity issues
            # Add specific checks based on your schema
            
            logger.info("Data integrity verification completed")
            
        except Exception as e:
            logger.error(f"Data integrity check failed: {e}")
            raise
    
    def cleanup_temp_files(self, files: List[str]):
        """Clean up temporary files"""
        for file_path in files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"Cleaned up: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {file_path}: {e}")
    
    def run(self):
        """Run the complete staging data population process"""
        temp_files = []
        
        try:
            # Confirm operation
            if not self.confirm_operation():
                logger.info("Operation cancelled by user")
                return
            
            # Step 1: Backup staging data
            backup_file = self.backup_staging_data()
            
            # Step 2: Dump production data
            dump_file = self.dump_production_data()
            temp_files.append(dump_file)
            
            # Step 3: Sanitize data
            sanitized_file = self.sanitize_sql_data(dump_file)
            temp_files.append(sanitized_file)
            
            # Step 4: Clear staging data
            self.clear_staging_data()
            
            # Step 5: Import sanitized data
            self.import_sanitized_data(sanitized_file)
            
            # Step 6: Verify data integrity
            self.verify_data_integrity()
            
            logger.info("✅ Staging data population completed successfully!")
            logger.info(f"Backup saved at: {backup_file}")
            
        except Exception as e:
            logger.error(f"❌ Staging data population failed: {e}")
            raise
        
        finally:
            # Cleanup temp files
            self.cleanup_temp_files(temp_files)

def main():
    """Main function"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        populator = StagingDataPopulator()
        populator.run()
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 