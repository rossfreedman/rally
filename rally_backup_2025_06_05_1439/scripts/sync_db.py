#!/usr/bin/env python
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

def run_command(cmd):
    """Run a command and return its output"""
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode(), process.returncode

def sync_databases():
    """Sync databases between local and Railway"""
    load_dotenv()
    
    # Get database URLs
    local_db = os.getenv('DATABASE_URL')
    railway_db = os.getenv('RAILWAY_POSTGRES_URL')
    
    if not all([local_db, railway_db]):
        print("❌ Error: Both DATABASE_URL and RAILWAY_POSTGRES_URL must be set")
        return False
    
    # Create backup timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Backup local database
    print("📦 Backing up local database...")
    backup_file = f"backup_local_{timestamp}.sql"
    cmd = f"pg_dump {local_db} > {backup_file}"
    _, stderr, code = run_command(cmd)
    if code != 0:
        print(f"❌ Local backup failed: {stderr}")
        return False
    
    # Apply migrations to both databases
    print("🔄 Applying migrations to local database...")
    _, stderr, code = run_command(f"DATABASE_URL={local_db} alembic upgrade head")
    if code != 0:
        print(f"❌ Local migration failed: {stderr}")
        return False
        
    print("🔄 Applying migrations to Railway database...")
    _, stderr, code = run_command(f"DATABASE_URL={railway_db} alembic upgrade head")
    if code != 0:
        print(f"❌ Railway migration failed: {stderr}")
        return False
    
    print("✅ Database sync completed successfully!")
    print(f"Local backup saved as: {backup_file}")
    return True

if __name__ == "__main__":
    sync_databases() 