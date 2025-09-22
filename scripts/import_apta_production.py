#!/usr/bin/env python3
"""
Import APTA Chicago players to production database.
This script connects to the production database and runs the import.
"""

import os
import sys
import subprocess
from datetime import datetime

# Production database URL
PRODUCTION_DB_URL = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

def main():
    print("🚀 IMPORTING APTA CHICAGO PLAYERS TO PRODUCTION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: Production")
    print()
    
    # Set environment variable for production database
    env = os.environ.copy()
    env['DATABASE_URL'] = PRODUCTION_DB_URL
    env['RAILWAY_ENVIRONMENT'] = 'production'
    
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
    print("✅ Database URL set for production")
    print()
    
    # Run the import using the same script as staging
    print("📥 Running APTA import to production database...")
    try:
        result = subprocess.run([
            'python3', 
            'data/etl/import/import_players.py', 
            'APTA_CHICAGO',
            '--file', 'data/leagues/APTA_CHICAGO/players.json'
        ], env=env, capture_output=True, text=True)
        
        # Print the output
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Import completed successfully!")
            return True
        else:
            print(f"❌ Import failed with return code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
