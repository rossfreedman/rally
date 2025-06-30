#!/usr/bin/env python3
"""
Deploy Production Migration - Using Public URL
==============================================

Uses Railway's DATABASE_PUBLIC_URL for external access.
"""

import subprocess
import sys
import os

def main():
    print("🚀 Production Migration - Using Public Database URL")
    print("=" * 50)
    
    # Check Railway status
    result = subprocess.run(['railway', 'status'], capture_output=True, text=True)
    print("📊 Railway Status:")
    print(result.stdout)
    
    if "production" not in result.stdout:
        print("❌ Not on production environment!")
        return 1
    
    migration_file = "migrations/production_fix_availability_user_id.sql"
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return 1
    
    print("🚨 DEPLOYING TO PRODUCTION NOW...")
    print("🔄 Applying migration using Railway public database URL...")
    
    # Use Railway's DATABASE_PUBLIC_URL directly
    cmd = ['railway', 'run', 'psql', '$DATABASE_PUBLIC_URL', '-f', migration_file]
    
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, text=True)
    
    if result.returncode == 0:
        print("✅ Migration applied successfully!")
        
        # Verify migration
        print("🔍 Verifying migration...")
        verify_cmd = ['railway', 'run', 'psql', '$DATABASE_PUBLIC_URL', '-c', """
        SELECT 
            CASE WHEN EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'player_availability' AND column_name = 'user_id'
            ) THEN 'Column exists' ELSE 'Column missing' END as status,
            COUNT(*) as total_records,
            COUNT(user_id) as records_with_user_id
        FROM player_availability;
        """]
        
        verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
        if verify_result.returncode == 0:
            print("✅ Verification completed:")
            print(verify_result.stdout)
        
        print("\n🎉 Production migration deployment completed!")
        print("   Test the fix at: https://rally.up.railway.app/mobile/availability")
        return 0
    else:
        print("❌ Migration failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 