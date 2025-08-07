#!/usr/bin/env python3
"""
Alembic Staging Upgrade
=======================

Run alembic upgrade on staging database using proper environment setup.
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upgrade_staging():
    """Run alembic upgrade on staging"""
    print("🚀 Running alembic upgrade on staging...")
    
    # Set staging database URL
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    # Set environment variables
    env = os.environ.copy()
    env["DATABASE_URL"] = staging_url
    env["PYTHONPATH"] = os.getcwd()
    
    print(f"📋 Staging URL: {staging_url.split('@')[1] if '@' in staging_url else 'unknown'}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    try:
        # Run alembic upgrade with timeout
        result = subprocess.run([
            "python3", "-m", "alembic", "upgrade", "head"
        ], env=env, capture_output=True, text=True, timeout=120)  # 2 minute timeout
        
        if result.returncode == 0:
            print("✅ Alembic upgrade successful")
            print("📋 Output:")
            print(result.stdout)
            return True
        else:
            print("❌ Alembic upgrade failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Alembic upgrade timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running alembic upgrade: {e}")
        return False

def check_staging_version():
    """Check current staging schema version"""
    print("🔍 Checking staging schema version...")
    
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(staging_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"📋 Current version: {version}")
            
            # Check if it's the latest
            if version == 'sync_all_env_001':
                print("✅ Staging is at the latest version!")
                return True
            else:
                print(f"⚠️  Staging needs upgrade from {version} to sync_all_env_001")
                return False
        
        engine.dispose()
        
    except Exception as e:
        print(f"❌ Error checking staging version: {e}")
        return False

def main():
    """Main function"""
    print("🏓 ALEMBIC STAGING UPGRADE")
    print(f"📅 {datetime.now()}")
    print("=" * 50)
    
    # Check current version
    if not check_staging_version():
        print("❌ Could not check staging version")
        return 1
    
    # Confirm upgrade
    print("\n⚠️  This will upgrade staging to the latest schema version.")
    print()
    
    response = input("Do you want to proceed? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Upgrade cancelled")
        return 0
    
    # Run upgrade
    print("\n📦 Running alembic upgrade...")
    if not upgrade_staging():
        print("❌ Staging upgrade failed.")
        return 1
    
    # Verify upgrade
    print("\n🔍 Verifying upgrade...")
    if check_staging_version():
        print("\n✅ STAGING UPGRADE COMPLETE!")
        print("🌍 Staging is now synced with production")
        return 0
    else:
        print("\n❌ Staging upgrade verification failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
