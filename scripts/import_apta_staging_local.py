#!/usr/bin/env python3
"""
Import APTA Chicago players to staging database from local machine.
This runs locally but connects to the staging database for faster execution.
"""

import sys
import os
import subprocess
from datetime import datetime

def main():
    print("🚀 IMPORTING APTA CHICAGO PLAYERS TO STAGING")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Set staging database URL as environment variable
    staging_db_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    print(f"📊 Target: Staging Database")
    print(f"🏆 League: APTA Chicago")
    print(f"📁 Source: data/leagues/APTA_CHICAGO/players.json")
    print()
    
    try:
        # Set environment variable for database URL
        env = os.environ.copy()
        env['DATABASE_URL'] = staging_db_url
        
        # Run the import using the existing script
        print("🔄 Starting import process...")
        cmd = [
            'python3', 
            'data/etl/import/import_players.py', 
            'APTA_CHICAGO',
            '--file', 'data/leagues/APTA_CHICAGO/players.json'
        ]
        
        print(f"Running: {' '.join(cmd)}")
        print()
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
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
    
    print()
    print(f"🏁 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
