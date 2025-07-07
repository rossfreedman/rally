#!/usr/bin/env python3

"""
Check and upgrade Alembic migrations on staging to include pickup games tables
"""

import os
import sys
import subprocess
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def upgrade_staging_alembic():
    """Check and upgrade Alembic migrations on staging"""
    
    print("=== Upgrading Staging Database with Alembic ===")
    
    # Check if we're on staging
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    if railway_env != "staging":
        print(f"❌ This script only runs on staging. Current environment: {railway_env}")
        print(f"🔍 If you're on staging, the RAILWAY_ENVIRONMENT variable might not be set correctly")
        print(f"💡 You can still run this on staging Railway environment")
        # Don't return False here, allow it to continue on staging even if env var isn't set
    
    try:
        print("🔍 Checking current Alembic revision...")
        
        # Check current revision
        current_result = subprocess.run(
            ["alembic", "current"], 
            capture_output=True, 
            text=True, 
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        if current_result.returncode == 0:
            current_output = current_result.stdout.strip()
            print(f"📊 Current revision: {current_output}")
            
            # Check if we're already at the latest
            if "20484d947d9d" in current_output and "(head)" in current_output:
                print("✅ Staging is already at the latest revision - pickup games tables should exist")
                return True
            
        else:
            print(f"⚠️ Could not check current revision: {current_result.stderr}")
            print("🔄 Proceeding with upgrade anyway...")
        
        print("🔄 Running Alembic upgrade to head...")
        
        # Run alembic upgrade
        upgrade_result = subprocess.run(
            ["alembic", "upgrade", "head"], 
            capture_output=True, 
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        if upgrade_result.returncode == 0:
            print("✅ Alembic upgrade completed successfully!")
            print("📋 Upgrade output:")
            print(upgrade_result.stdout)
            
            # Verify the upgrade
            print("🔍 Verifying upgrade...")
            verify_result = subprocess.run(
                ["alembic", "current"], 
                capture_output=True, 
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            if verify_result.returncode == 0:
                final_revision = verify_result.stdout.strip()
                print(f"✅ Final revision: {final_revision}")
                
                if "20484d947d9d" in final_revision:
                    print("🎯 Pickup games migration successfully applied!")
                    return True
                else:
                    print("⚠️ Pickup games migration may not have been applied")
                    return False
            else:
                print("❌ Could not verify final revision")
                return False
                
        else:
            print(f"❌ Alembic upgrade failed: {upgrade_result.stderr}")
            print(f"📋 Error output: {upgrade_result.stdout}")
            return False
        
    except Exception as e:
        print(f"❌ Error during Alembic upgrade: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

def test_pickup_tables():
    """Test if pickup games tables exist after migration"""
    
    print("\n🧪 Testing pickup games tables...")
    
    try:
        from database_utils import execute_query_one
        
        # Test pickup_games table
        pg_check = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pickup_games'
            )
        """)
        
        pg_exists = pg_check["exists"] if pg_check else False
        print(f"📋 pickup_games table exists: {pg_exists}")
        
        # Test pickup_game_participants table
        pgp_check = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pickup_game_participants'
            )
        """)
        
        pgp_exists = pgp_check["exists"] if pgp_check else False
        print(f"📋 pickup_game_participants table exists: {pgp_exists}")
        
        if pg_exists and pgp_exists:
            print("✅ All pickup games tables exist - migration successful!")
            return True
        else:
            print("❌ Some pickup games tables are missing")
            return False
            
    except Exception as e:
        print(f"❌ Error testing tables: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Alembic upgrade process for staging...\n")
    
    upgrade_success = upgrade_staging_alembic()
    
    if upgrade_success:
        test_success = test_pickup_tables()
        
        if test_success:
            print("\n🎉 Staging database upgrade completed successfully!")
            print("👉 Pickup games page should now work: https://rally-staging.up.railway.app/mobile/pickup-games")
        else:
            print("\n💥 Migration completed but tables verification failed")
    else:
        print("\n💥 Migration failed - check the error messages above")
        print("🔧 You may need to run: alembic upgrade head manually on staging") 