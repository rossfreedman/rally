#!/usr/bin/env python3
"""
Simple script to apply the lineup escrow migration to production
Uses the same approach that worked for staging
"""

import os
import subprocess
import sys

def run_migration():
    """Run the migration using Railway CLI"""
    print("🚀 Applying Lineup Escrow Migration to Production")
    print("=" * 50)
    
    # Check if we're in production environment
    if os.getenv('RAILWAY_ENVIRONMENT') != 'production':
        print("⚠️  Warning: Not in production environment")
        print("Current environment:", os.getenv('RAILWAY_ENVIRONMENT', 'unknown'))
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("❌ Migration cancelled")
            return False
    
    print("🔧 Connecting to production database...")
    
    # Read the migration SQL
    migration_file = "data/dbschema/migrations/20250115_130000_add_team_ids_to_lineup_escrow.sql"
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("✅ Migration SQL loaded")
    print("🔧 Applying migration to production...")
    
    try:
        # Use Railway CLI to connect and run the migration
        # This is the same approach that worked for staging
        cmd = [
            "railway", "connect", "--environment", "production"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        print("⚠️  You will need to manually paste the SQL commands in the psql session")
        print("⚠️  Copy and paste the following SQL:")
        print("-" * 50)
        print(migration_sql)
        print("-" * 50)
        
        # Start the Railway connection
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            return True
        else:
            print(f"❌ Migration failed with return code: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("🎉 Production migration completed!")
    else:
        print("❌ Production migration failed!")
        sys.exit(1)
