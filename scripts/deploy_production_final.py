#!/usr/bin/env python3
"""
Deploy Production Migration - Final Version
==========================================

Handles Railway internal hostname issues by using public proxy.
"""

import subprocess
import sys
import os

def run_migration_with_proxy():
    """Run migration using Railway's TCP proxy"""
    print("🔄 Applying migration using Railway TCP proxy...")
    
    migration_file = "migrations/production_fix_availability_user_id.sql"
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        # Get the DATABASE_URL and modify it to use public proxy
        env_result = subprocess.run(['railway', 'run', 'env'], capture_output=True, text=True)
        
        if env_result.returncode != 0:
            print("❌ Failed to get Railway environment variables")
            return False
        
        database_url = None
        for line in env_result.stdout.split('\n'):
            if line.startswith('DATABASE_URL='):
                database_url = line.split('=', 1)[1]
                break
        
        if not database_url:
            print("❌ DATABASE_URL not found in Railway environment")
            return False
        
        print(f"Found DATABASE_URL: {database_url[:50]}...")
        
        # Convert internal URL to public proxy URL
        if "postgres-o1a0.railway.internal" in database_url:
            # Replace internal hostname with public proxy
            public_url = database_url.replace(
                "postgres-o1a0.railway.internal:5432",
                "autorack.proxy.rlwy.net:28416"
            )
            print("🔄 Converting to public proxy URL...")
        else:
            public_url = database_url
        
        # Run psql with the public URL
        cmd = ['psql', public_url, '-f', migration_file]
        
        print(f"Running: psql [DATABASE_URL] -f {migration_file}")
        
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

def verify_migration_with_proxy():
    """Verify migration using public proxy"""
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
        # Get the DATABASE_URL and convert to public proxy
        env_result = subprocess.run(['railway', 'run', 'env'], capture_output=True, text=True)
        
        database_url = None
        for line in env_result.stdout.split('\n'):
            if line.startswith('DATABASE_URL='):
                database_url = line.split('=', 1)[1]
                break
        
        if not database_url:
            print("❌ DATABASE_URL not found")
            return False
        
        # Convert to public proxy URL
        if "postgres-o1a0.railway.internal" in database_url:
            public_url = database_url.replace(
                "postgres-o1a0.railway.internal:5432",
                "autorack.proxy.rlwy.net:28416"
            )
        else:
            public_url = database_url
        
        cmd = ['psql', public_url, '-c', verify_sql]
        
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
    print("🚀 Production Migration - Final Deployment")
    print("=" * 50)
    
    # Check Railway status
    try:
        result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
        if result.returncode == 0:
            print("📊 Railway Status:")
            print(result.stdout)
            if "production" not in result.stdout:
                print("❌ Not on production environment!")
                return 1
        else:
            print("❌ Railway not linked")
            return 1
    except Exception as e:
        print(f"❌ Error checking Railway status: {e}")
        return 1
    
    print("🚨 DEPLOYING TO PRODUCTION NOW...")
    
    # Run migration
    if not run_migration_with_proxy():
        return 1
    
    # Verify migration
    if not verify_migration_with_proxy():
        print("⚠️  Migration may have run but verification failed")
        print("   Check the production availability page manually")
    
    print("\n🎉 Production migration deployment completed!")
    print("   Test the fix at: https://rally.up.railway.app/mobile/availability")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 