#!/usr/bin/env python3
"""
Apply Production Migration via Railway CLI
==========================================

This script uses the Railway CLI to apply the availability user_id migration
to the production database. Much easier than using the web console!
"""

import subprocess
import sys
import os

def check_railway_cli():
    """Check if Railway CLI is installed"""
    try:
        result = subprocess.run(['railway', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Railway CLI found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Railway CLI not responding properly")
            return False
    except FileNotFoundError:
        print("❌ Railway CLI not found")
        print("   Install it with: brew install railway")
        print("   Or visit: https://docs.railway.app/develop/cli")
        return False

def check_railway_auth():
    """Check if user is authenticated with Railway"""
    try:
        result = subprocess.run(['railway', 'whoami'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Authenticated as: {result.stdout.strip()}")
            return True
        else:
            print("❌ Not authenticated with Railway")
            print("   Run: railway login")
            return False
    except Exception as e:
        print(f"❌ Error checking Railway auth: {e}")
        return False

def link_to_project():
    """Check if we're linked to the Rally project"""
    try:
        result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
        if result.returncode == 0 and 'rally' in result.stdout.lower():
            print("✅ Linked to Rally project")
            return True
        else:
            print("❌ Not linked to Rally project")
            print("   Run: railway link")
            print("   Then select your Rally project")
            return False
    except Exception as e:
        print(f"❌ Error checking project link: {e}")
        return False

def apply_migration():
    """Apply the migration using Railway CLI"""
    migration_file = "migrations/production_fix_availability_user_id.sql"
    
    # Check if migration file exists
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"🔄 Applying migration from {migration_file}...")
    
    try:
        # Use Railway CLI to run psql with the migration file
        # The DATABASE_URL environment variable will be automatically available
        cmd = [
            'railway', 'run', 
            'psql', '$DATABASE_URL', 
            '-f', migration_file,
            '-v', 'ON_ERROR_STOP=1'  # Stop on first error
        ]
        
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration applied successfully!")
            print("\nMigration output:")
            print(result.stdout)
            return True
        else:
            print("❌ Migration failed!")
            print("Error output:")
            print(result.stderr)
            print("Standard output:")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

def verify_migration():
    """Verify the migration was applied successfully"""
    print("🔍 Verifying migration...")
    
    verify_sql = """
    SELECT 
        CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'player_availability' 
            AND column_name = 'user_id'
        ) THEN 'Column exists' ELSE 'Column missing' END as column_status,
        (SELECT COUNT(*) FROM player_availability) as total_records,
        (SELECT COUNT(*) FROM player_availability WHERE user_id IS NOT NULL) as records_with_user_id;
    """
    
    try:
        cmd = [
            'railway', 'run',
            'psql', '$DATABASE_URL',
            '-c', verify_sql
        ]
        
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

def main():
    print("🚀 Railway CLI Production Migration")
    print("=" * 50)
    
    # Check prerequisites
    if not check_railway_cli():
        return 1
    
    if not check_railway_auth():
        return 1
    
    if not link_to_project():
        return 1
    
    # Apply migration
    if not apply_migration():
        return 1
    
    # Verify migration
    if not verify_migration():
        print("⚠️  Migration applied but verification failed")
        print("   Please check the production availability page manually")
        return 1
    
    print("\n🎉 Production availability fix completed!")
    print("   Users should now be able to view schedule data properly")
    print("   Test at: https://rally.up.railway.app/mobile/availability")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 