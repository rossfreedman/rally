#!/usr/bin/env python3
"""
Test Environment Setup for ELT Scripts

This script creates a safe testing environment for validating ELT scripts
without affecting the production database.
"""

import os
import sys
import subprocess
import psycopg2
from datetime import datetime
import shutil
from pathlib import Path
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import get_db_url, parse_db_url

class ETLTestEnvironment:
    def __init__(self):
        self.test_db_name = "rally_etl_test"
        self.original_db_url = get_db_url()
        self.test_db_url = None
        self.backup_dir = Path("etl_test_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_test_database(self):
        """Create a test database and clone the current schema"""
        print("🔧 Setting up test database environment...")
        
        # Parse original DB connection
        db_params = parse_db_url(self.original_db_url)
        
        # Create test database
        admin_params = db_params.copy()
        admin_params['dbname'] = 'postgres'  # Connect to default DB to create new one
        
        try:
            # Use connection without context manager to avoid transaction issues
            conn = psycopg2.connect(**admin_params)
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Drop test database if it exists
                cursor.execute(f"DROP DATABASE IF EXISTS {self.test_db_name}")
                print(f"   Dropped existing test database: {self.test_db_name}")
                
                # Create new test database
                cursor.execute(f"CREATE DATABASE {self.test_db_name}")
                print(f"✅ Created test database: {self.test_db_name}")
            
            conn.close()
                    
        except Exception as e:
            print(f"❌ Error creating test database: {e}")
            if 'conn' in locals():
                conn.close()
            return False
            
        # Update test DB URL
        self.test_db_url = self.original_db_url.replace(db_params['dbname'], self.test_db_name)
        return True
    
    def backup_current_database(self):
        """Create a backup of the current database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"rally_pre_test_backup_{timestamp}.sql"
        
        print("💾 Creating backup of current database...")
        
        db_params = parse_db_url(self.original_db_url)
        
        # Use pg_dump to create backup
        dump_cmd = [
            'pg_dump',
            f"--host={db_params['host']}",
            f"--port={db_params['port']}",
            f"--username={db_params['user']}",
            f"--dbname={db_params['dbname']}",
            '--verbose',
            '--clean',
            '--no-owner',
            '--no-privileges',
            '--format=custom',
            '--file', str(backup_file)
        ]
        
        # Set password via environment
        env = os.environ.copy()
        env['PGPASSWORD'] = db_params['password']
        
        try:
            result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True, check=True)
            print(f"✅ Backup created: {backup_file}")
            return backup_file
        except subprocess.CalledProcessError as e:
            print(f"❌ Backup failed: {e}")
            print(f"   stderr: {e.stderr}")
            return None
    
    def clone_current_to_test(self):
        """Clone current database structure and data to test database"""
        print("📋 Cloning current database to test environment...")
        
        db_params = parse_db_url(self.original_db_url)
        test_params = parse_db_url(self.test_db_url)
        
        # Use pg_dump + pg_restore to clone
        dump_cmd = [
            'pg_dump',
            f"--host={db_params['host']}",
            f"--port={db_params['port']}",
            f"--username={db_params['user']}",
            f"--dbname={db_params['dbname']}",
            '--format=custom',
            '--no-owner',
            '--no-privileges'
        ]
        
        restore_cmd = [
            'pg_restore',
            f"--host={test_params['host']}",
            f"--port={test_params['port']}",
            f"--username={test_params['user']}",
            f"--dbname={test_params['dbname']}",
            '--clean',
            '--if-exists',  # Don't error if objects don't exist when dropping
            '--no-owner',
            '--no-privileges',
            '--exit-on-error'  # Only exit on real errors, not warnings
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_params['password']
        
        try:
            print("   Creating database dump...")
            # First create the dump
            dump_proc = subprocess.run(dump_cmd, env=env, capture_output=True)
            
            if dump_proc.returncode != 0:
                print(f"❌ Dump failed: {dump_proc.stderr.decode()}")
                return False
            
            print("   Restoring to test database...")
            # Then restore to test database
            restore_proc = subprocess.run(
                restore_cmd, 
                input=dump_proc.stdout, 
                env=env, 
                capture_output=True
            )
            
            # Check if restore completed (ignore warnings about missing objects)
            if restore_proc.returncode == 0:
                print("✅ Successfully cloned database to test environment")
                return True
            else:
                # Check stderr for real errors vs expected warnings
                stderr = restore_proc.stderr.decode()
                
                # These are expected warnings when using --clean on empty database
                expected_warnings = [
                    "does not exist",
                    "errors ignored on restore",
                    "warning: errors ignored"
                ]
                
                # Check if we only have expected warnings
                real_errors = []
                for line in stderr.split('\n'):
                    if 'error:' in line.lower() and not any(warning in line for warning in expected_warnings):
                        real_errors.append(line)
                
                if not real_errors:
                    print("✅ Successfully cloned database to test environment")
                    print("   (Ignored expected warnings about missing objects)")
                    return True
                else:
                    print("❌ Failed to clone database - real errors found:")
                    for error in real_errors:
                        print(f"   {error}")
                    return False
                
        except Exception as e:
            print(f"❌ Error cloning database: {e}")
            return False
    
    def generate_test_config(self):
        """Generate a test configuration file"""
        config = {
            "original_db_url": self.original_db_url,
            "test_db_url": self.test_db_url,
            "test_db_name": self.test_db_name,
            "created_at": datetime.now().isoformat(),
            "backup_dir": str(self.backup_dir)
        }
        
        config_file = "etl_test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"📝 Test configuration saved: {config_file}")
        return config_file
    
    def setup(self):
        """Complete test environment setup"""
        print("🚀 Setting up ELT test environment...")
        print("=" * 50)
        
        # Step 1: Backup current database
        backup_file = self.backup_current_database()
        if not backup_file:
            return False
        
        # Step 2: Create test database
        if not self.create_test_database():
            return False
        
        # Step 3: Clone current data to test
        if not self.clone_current_to_test():
            return False
        
        # Step 4: Generate config
        self.generate_test_config()
        
        print("=" * 50)
        print("✅ Test environment setup complete!")
        print(f"   Original DB: {self.original_db_url.split('@')[1].split('/')[0]}")
        print(f"   Test DB: {self.test_db_name}")
        print(f"   Backup: {backup_file}")
        print("\n🔄 Next steps:")
        print("   1. Run: python test_etl_validation.py")
        print("   2. Review validation results")
        print("   3. Run: python cleanup_test_environment.py")
        
        return True

def main():
    test_env = ETLTestEnvironment()
    success = test_env.setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 