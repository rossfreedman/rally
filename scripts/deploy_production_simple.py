#!/usr/bin/env python3
"""
Simple Production Migration Deployment
====================================

Deploy the availability fix to production using Railway CLI with public database URL.
This avoids the internal hostname connection issues.
"""

import subprocess
import sys
import os

def run_migration_via_psql():
    """Run the migration using psql via Railway CLI"""
    print("🔄 Applying migration to production via Railway CLI + psql...")
    
    # The migration SQL file
    migration_file = "migrations/production_fix_availability_user_id.sql"
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        # Use Railway CLI to run psql with the migration file
        # Railway CLI automatically provides the DATABASE_URL environment variable
        cmd = [
            'railway', 'run', 
            'psql', '$DATABASE_URL', 
            '-f', migration_file
        ]
        
        print(f"Running: {' '.join(cmd)}")
        print("This will connect to the currently linked Railway environment...")
        
        result = subprocess.run(cmd, text=True)
        
        if result.returncode == 0:
            print("✅ Migration applied successfully!")
            return True
        else:
            print("❌ Migration failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    print("🔍 Verifying migration...")
    
    verify_sql = """
    SELECT 
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'player_availability' AND column_name = 'user_id'
        ) THEN 'Column exists' ELSE 'Column missing' END as status,
        COUNT(*) as total_records,
        COUNT(user_id) as records_with_user_id
    FROM player_availability;
    """
    
    try:
        cmd = ['railway', 'run', 'psql', '$DATABASE_URL', '-c', verify_sql]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Verification completed:")
            print(result.stdout)
            return True
        else:
            print("❌ Verification failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error running verification: {e}")
        return False

def check_railway_status():
    """Check Railway connection and environment"""
    try:
        result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📊 Railway Status:")
            print(result.stdout)
            return True
        else:
            print("❌ Railway not linked. Run: railway link")
            return False
    except Exception as e:
        print(f"❌ Error checking Railway status: {e}")
        return False

def main():
    print("🚀 Simple Production Migration Deployment")
    print("=" * 50)
    
    # Check Railway status
    if not check_railway_status():
        return 1
    
    # Confirm environment
    print("\n⚠️  IMPORTANT: Make sure you're linked to PRODUCTION environment")
    print("   If you see 'staging' above, run: railway link and select production")
    response = input("\nContinue with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled")
        return 0
    
    # Run migration
    if not run_migration_via_psql():
        return 1
    
    # Verify migration
    if not verify_migration():
        print("⚠️  Migration may have run but verification failed")
        print("   Check the production availability page manually")
    
    print("\n🎉 Migration deployment completed!")
    print("   Test the fix at: https://rally.up.railway.app/mobile/availability")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 