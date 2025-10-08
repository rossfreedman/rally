#!/usr/bin/env python3
"""
Import APTA data directly to staging database.
This script connects to the staging database and runs the import.
"""

import os
import sys
import subprocess
from datetime import datetime

# Staging database URL
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

def main():
    print("🚀 IMPORTING APTA DATA TO STAGING DATABASE")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {STAGING_DB_URL}")
    print()
    
    # Set environment variable for staging database
    os.environ['DATABASE_URL'] = STAGING_DB_URL
    os.environ['RAILWAY_ENVIRONMENT'] = 'staging'
    
    # Check if we're in the right directory
    if not os.path.exists('data/etl/import/import_players.py'):
        print("❌ import_players.py not found. Please run from project root.")
        return False
    
    # Check if players.json exists
    players_json_path = 'data/leagues/APTA_CHICAGO/players.json'
    if not os.path.exists(players_json_path):
        print(f"❌ {players_json_path} not found.")
        return False
    
    print("✅ Found required files")
    print("✅ Database URL set for staging")
    print()
    
    # Run the import
    print("📥 Running APTA import to staging database...")
    try:
        result = subprocess.run([
            'python3', 'data/etl/import/import_players.py', 'APTA_CHICAGO'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Import completed successfully!")
            print()
            print("Output:")
            print(result.stdout)
            return True
        else:
            print("❌ Import failed!")
            print()
            print("Error output:")
            print(result.stderr)
            print()
            print("Standard output:")
            print(result.stdout)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Import timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"💥 Error running import: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
