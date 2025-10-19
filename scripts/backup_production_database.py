#!/usr/bin/env python3
"""
Backup Production Database
Creates a SQL dump of the production database before making changes
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Production database connection details
PRODUCTION_HOST = "ballast.proxy.rlwy.net"
PRODUCTION_PORT = "40911"
PRODUCTION_DB = "railway"
PRODUCTION_USER = "postgres"
PRODUCTION_PASSWORD = "HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq"

def backup_production_database():
    """Create a backup of the production database"""
    
    print("=" * 80)
    print("PRODUCTION DATABASE BACKUP")
    print("=" * 80)
    
    # Create backups directory if it doesn't exist
    backups_dir = Path("backups")
    backups_dir.mkdir(exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backups_dir / f"production_backup_{timestamp}.sql"
    
    print(f"\n📡 Database: {PRODUCTION_HOST}:{PRODUCTION_PORT}/{PRODUCTION_DB}")
    print(f"📁 Backup file: {backup_file}")
    print(f"⏰ Timestamp: {timestamp}")
    
    try:
        print("\n🔄 Creating backup (this may take a few minutes)...")
        
        # Set password in environment
        import os
        env = os.environ.copy()
        env['PGPASSWORD'] = PRODUCTION_PASSWORD
        
        # Run pg_dump command
        cmd = [
            'pg_dump',
            '-h', PRODUCTION_HOST,
            '-p', PRODUCTION_PORT,
            '-U', PRODUCTION_USER,
            '-d', PRODUCTION_DB,
            '--no-owner',
            '--no-acl',
            '-f', str(backup_file)
        ]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Get file size
            file_size = backup_file.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            print(f"\n✅ Backup completed successfully!")
            print(f"📊 Backup size: {size_mb:.2f} MB")
            print(f"📁 Location: {backup_file}")
            
            # List recent backups
            print("\n📋 Recent production backups:")
            backups = sorted(backups_dir.glob("production_backup_*.sql"), reverse=True)
            for i, backup in enumerate(backups[:5], 1):
                size = backup.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"   {i}. {backup.name} ({size:.2f} MB) - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            print("\n" + "=" * 80)
            print("✅ BACKUP COMPLETE - READY FOR MIGRATION")
            print("=" * 80)
            print("\nYou can now safely run the migration:")
            print("  python3 scripts/migrate_lesson_pricing_to_production.py")
            print("\nTo restore this backup if needed:")
            print(f"  psql -h {PRODUCTION_HOST} -p {PRODUCTION_PORT} -U {PRODUCTION_USER} -d {PRODUCTION_DB} < {backup_file}")
            print("=" * 80)
            
        else:
            print(f"\n❌ Backup failed!")
            print(f"Error: {result.stderr}")
            sys.exit(1)
            
    except FileNotFoundError:
        print("\n❌ Error: pg_dump command not found")
        print("Please install PostgreSQL client tools:")
        print("  macOS: brew install postgresql")
        print("  Ubuntu: sudo apt-get install postgresql-client")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    print("\n⚠️  PRODUCTION DATABASE BACKUP")
    print("This will create a SQL dump of the production database")
    print(f"Database: {PRODUCTION_HOST}:{PRODUCTION_PORT}/{PRODUCTION_DB}")
    print()
    
    response = input("Continue with backup? (yes/no): ").strip().lower()
    
    if response == 'yes':
        backup_production_database()
    else:
        print("\n❌ Backup cancelled")
        sys.exit(0)

