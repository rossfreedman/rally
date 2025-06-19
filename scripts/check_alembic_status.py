#!/usr/bin/env python3
"""
Alembic Status Checker
Check the current migration status on both local and Railway databases
"""

import os
import sys
import subprocess
from database_config import get_db_url
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_alembic_status(db_type):
    """Check Alembic status for a specific database"""
    
    if db_type == 'railway':
        os.environ['SYNC_RAILWAY'] = 'true'
        logger.info("🚂 Checking Railway database migration status...")
    else:
        os.environ.pop('SYNC_RAILWAY', None)
        logger.info("🏠 Checking Local database migration status...")
    
    try:
        # Get current database URL
        url = get_db_url()
        db_host = url.split('@')[1].split('/')[0] if '@' in url else 'unknown'
        logger.info(f"Database: {db_host}")
        
        # Check current migration status
        result = subprocess.run([
            sys.executable, "-m", "alembic", "current", "-v"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✅ {db_type.upper()} Database Migration Status:")
            print("-" * 50)
            print(result.stdout)
        else:
            print(f"\n❌ {db_type.upper()} Database Migration Status Error:")
            print("-" * 50)
            print(result.stderr)
        
        # Check migration history
        history_result = subprocess.run([
            sys.executable, "-m", "alembic", "history", "-v"
        ], capture_output=True, text=True)
        
        if history_result.returncode == 0:
            print(f"\n📜 {db_type.upper()} Migration History (last 10):")
            print("-" * 50)
            # Show only last 10 lines to avoid too much output
            lines = history_result.stdout.strip().split('\n')
            for line in lines[-10:]:
                print(line)
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"❌ Error checking {db_type} status: {e}")
        return False
    finally:
        os.environ.pop('SYNC_RAILWAY', None)

def main():
    """Main function to check both databases"""
    print("🔍 ALEMBIC MIGRATION STATUS CHECK")
    print("=" * 60)
    
    # Check local database
    local_ok = check_alembic_status('local')
    
    print("\n" + "=" * 60)
    
    # Check Railway database
    railway_ok = check_alembic_status('railway')
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("-" * 20)
    print(f"Local database: {'✅ OK' if local_ok else '❌ Error'}")
    print(f"Railway database: {'✅ OK' if railway_ok else '❌ Error'}")
    
    if local_ok and railway_ok:
        print("\n🎉 Both databases are accessible and have migration status!")
        return 0
    else:
        print("\n⚠️  One or both databases had issues!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 