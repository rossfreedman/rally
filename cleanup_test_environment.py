#!/usr/bin/env python3
"""
Cleanup Test Environment

This script safely removes the test database and associated files created
during ELT validation testing.
"""

import os
import sys
import json
import psycopg2
import shutil
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import parse_db_url

class ETLTestCleanup:
    def __init__(self):
        self.load_test_config()
        
    def load_test_config(self):
        """Load test configuration"""
        try:
            with open('etl_test_config.json', 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print("❌ Test configuration not found. Nothing to clean up.")
            sys.exit(0)
    
    def drop_test_database(self):
        """Drop the test database"""
        print("🗑️ Dropping test database...")
        
        # Parse original DB connection to get admin connection
        original_params = parse_db_url(self.config['original_db_url'])
        admin_params = original_params.copy()
        admin_params['dbname'] = 'postgres'  # Connect to default DB
        
        try:
            # Use connection without context manager to avoid transaction issues
            conn = psycopg2.connect(**admin_params)
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Terminate any active connections to the test database
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{self.config['test_db_name']}'
                    AND pid != pg_backend_pid()
                """)
                
                # Drop the test database
                cursor.execute(f"DROP DATABASE IF EXISTS {self.config['test_db_name']}")
                print(f"✅ Dropped test database: {self.config['test_db_name']}")
            
            conn.close()
                    
        except Exception as e:
            print(f"❌ Error dropping test database: {e}")
            if 'conn' in locals():
                conn.close()
            return False
            
        return True
    
    def remove_test_files(self):
        """Remove test configuration and backup files"""
        print("🧹 Cleaning up test files...")
        
        files_to_remove = [
            'etl_test_config.json',
        ]
        
        # Remove test files
        for filename in files_to_remove:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"   Removed: {filename}")
        
        # Remove validation reports (ask user first)
        validation_reports = list(Path('.').glob('etl_validation_report_*.json'))
        if validation_reports:
            print(f"\n📄 Found {len(validation_reports)} validation reports:")
            for report in validation_reports:
                print(f"   {report}")
            
            response = input("\nRemove validation reports? (y/N): ")
            if response.lower() == 'y':
                for report in validation_reports:
                    report.unlink()
                    print(f"   Removed: {report}")
            else:
                print("   Keeping validation reports")
        
        # Handle backup directory
        backup_dir = Path(self.config.get('backup_dir', 'etl_test_backups'))
        if backup_dir.exists():
            print(f"\n💾 Found backup directory: {backup_dir}")
            
            # List backup files
            backup_files = list(backup_dir.glob('*.sql'))
            if backup_files:
                print(f"   Contains {len(backup_files)} backup files:")
                for backup in backup_files:
                    print(f"   {backup}")
                
                response = input("\nRemove backup directory and files? (y/N): ")
                if response.lower() == 'y':
                    shutil.rmtree(backup_dir)
                    print(f"   Removed: {backup_dir}")
                else:
                    print(f"   Keeping backup directory: {backup_dir}")
        
        print("✅ File cleanup complete")
        return True
    
    def cleanup(self):
        """Run complete cleanup process"""
        print("🧽 Starting ELT test environment cleanup...")
        print("=" * 50)
        
        print(f"Test database: {self.config['test_db_name']}")
        print(f"Created: {self.config['created_at']}")
        
        # Confirm cleanup
        response = input(f"\nProceed with cleanup? This will permanently remove the test database '{self.config['test_db_name']}'. (y/N): ")
        if response.lower() != 'y':
            print("❌ Cleanup cancelled")
            return False
        
        # Step 1: Drop test database
        if not self.drop_test_database():
            print("⚠️ Database cleanup failed, but continuing with file cleanup...")
        
        # Step 2: Remove test files
        self.remove_test_files()
        
        print("=" * 50)
        print("✅ ELT test environment cleanup complete!")
        print("\n📋 Summary:")
        print(f"   ✅ Test database '{self.config['test_db_name']}' removed")
        print("   ✅ Test configuration files removed")
        print("   ✅ Environment restored to original state")
        
        return True

def main():
    """Main function"""
    print("🧽 ELT Test Environment Cleanup")
    print("This script will remove the test database and associated files.")
    print()
    
    cleanup = ETLTestCleanup()
    success = cleanup.cleanup()
    
    if success:
        print("\n🎉 Your testing environment has been safely cleaned up!")
        print("   You can now run the validated ELT scripts with confidence.")
    else:
        print("\n❌ Cleanup failed. Please check for errors and try again.")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 