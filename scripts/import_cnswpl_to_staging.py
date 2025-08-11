#!/usr/bin/env python3
"""
Import CNSWPL Match Data to Staging
==================================

This script imports CNSWPL match data to the staging database to fix
the missing match data issue that's causing analyze-me and my-team
pages to show no data.
"""

import os
import sys
from pathlib import Path
import subprocess
from dotenv import load_dotenv

def import_cnswpl_to_staging():
    print("🚀 IMPORTING CNSWPL DATA TO STAGING")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    staging_db_url = os.getenv("DATABASE_PUBLIC_URL")
    
    if not staging_db_url:
        print("❌ Error: DATABASE_PUBLIC_URL environment variable not set.")
        print("Please set it to your Railway staging database URL.")
        sys.exit(1)
    
    # Set staging database as target
    os.environ['DATABASE_URL'] = staging_db_url
    os.environ['ENVIRONMENT'] = 'staging'
    
    print(f"🎯 Target: Staging database")
    print(f"📂 Data source: Local CNSWPL data")
    
    try:
        # Import match scores
        print(f"\n📊 Importing CNSWPL match scores...")
        result = subprocess.run([
            'python3', 'data/etl/database_import/import_all_jsons_to_database.py',
            '--match-scores'
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print(f"✅ Match scores imported successfully")
            print(result.stdout)
        else:
            print(f"❌ Match scores import failed:")
            print(result.stderr)
            return False
        
        # Import schedules
        print(f"\n📅 Importing CNSWPL schedules...")
        result = subprocess.run([
            'python3', 'data/etl/database_import/import_schedules.py'
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print(f"✅ Schedules imported successfully")
        else:
            print(f"❌ Schedules import failed:")
            print(result.stderr)
        
        # Import series stats
        print(f"\n📈 Importing CNSWPL series stats...")
        result = subprocess.run([
            'python3', 'data/etl/database_import/import_stats.py'
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print(f"✅ Series stats imported successfully")
        else:
            print(f"❌ Series stats import failed:")
            print(result.stderr)
        
        print(f"\n🎉 CNSWPL DATA IMPORT TO STAGING COMPLETE!")
        print(f"📱 Test Lisa Wagner's pages:")
        print(f"   - https://rally-staging.up.railway.app/mobile/analyze-me")
        print(f"   - https://rally-staging.up.railway.app/mobile/my-team")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed with error: {e}")
        return False

if __name__ == "__main__":
    success = import_cnswpl_to_staging()
    sys.exit(0 if success else 1)
