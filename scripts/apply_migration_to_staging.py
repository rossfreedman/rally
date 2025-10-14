#!/usr/bin/env python3
"""
Apply Alembic Migration to Staging
===================================

This script applies the latest alembic migration directly to the staging database.
"""

import os
import sys
from pathlib import Path

# Add root directory to path
sys.path.append(str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command

def main():
    """Apply migration to staging database."""
    
    print("=" * 70)
    print("🚀 Applying Alembic Migration to Staging Database")
    print("=" * 70)
    print()
    
    # Staging database URL
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    print(f"📊 Target Database: staging (Railway)")
    print(f"🔗 URL: {staging_url.split('@')[1]}")  # Hide password
    print()
    
    # Confirm execution
    response = input("🔄 Apply migration to STAGING database? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Migration cancelled")
        return False
    
    try:
        # Create alembic config
        alembic_ini_path = Path(__file__).parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        
        # Override the database URL to use staging
        alembic_cfg.set_main_option("sqlalchemy.url", staging_url)
        
        print("🔌 Connecting to staging database...")
        print("📋 Checking current version...")
        
        # Get current version
        command.current(alembic_cfg)
        
        print()
        print("🚀 Applying migration...")
        
        # Run upgrade
        command.upgrade(alembic_cfg, "head")
        
        print()
        print("✅ Migration applied successfully!")
        print()
        print("📋 New version:")
        command.current(alembic_cfg)
        
        return True
            
    except Exception as e:
        print(f"❌ ERROR applying migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    success = main()
    print()
    
    if success:
        print("=" * 70)
        print("✅ SUCCESS - Migration completed on staging!")
        print("=" * 70)
        print()
        print("📝 Next Steps:")
        print("   1. Test the changes on staging environment")
        print("   2. Verify food table has mens_food and womens_food columns")
        print("   3. Verify videos table was created")
        print("   4. Test functionality on staging")
        print()
        sys.exit(0)
    else:
        print("=" * 70)
        print("❌ FAILED - Migration did not complete")
        print("=" * 70)
        print()
        sys.exit(1)

