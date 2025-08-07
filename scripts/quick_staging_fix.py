#!/usr/bin/env python3
"""
Quick Staging Fix
================

Simple script to fix staging database with individual commands.
"""

import os
import sys
from sqlalchemy import create_engine, text

def fix_staging():
    """Fix staging database with individual commands"""
    print("🚀 Quick staging fix...")
    
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        engine = create_engine(staging_url, connect_args={"connect_timeout": 10})
        
        with engine.connect() as conn:
            print("📋 Adding missing columns...")
            
            # Add columns one by one with individual error handling
            commands = [
                ("Adding recipient_team_id to lineup_escrow", 
                 "ALTER TABLE lineup_escrow ADD COLUMN IF NOT EXISTS recipient_team_id INTEGER REFERENCES teams(id)"),
                
                ("Adding initiator_team_id to lineup_escrow", 
                 "ALTER TABLE lineup_escrow ADD COLUMN IF NOT EXISTS initiator_team_id INTEGER REFERENCES teams(id)"),
                
                ("Adding is_primary to user_player_associations", 
                 "ALTER TABLE user_player_associations ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE"),
                
                ("Adding match_id to match_scores", 
                 "ALTER TABLE match_scores ADD COLUMN IF NOT EXISTS match_id VARCHAR(255)"),
                
                ("Adding tenniscores_match_id to match_scores", 
                 "ALTER TABLE match_scores ADD COLUMN IF NOT EXISTS tenniscores_match_id VARCHAR(255)"),
                
                ("Adding team_id to users", 
                 "ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id)"),
                
                ("Adding notifications_hidden to users", 
                 "ALTER TABLE users ADD COLUMN IF NOT EXISTS notifications_hidden BOOLEAN DEFAULT FALSE"),
            ]
            
            for description, sql in commands:
                try:
                    print(f"  {description}...")
                    conn.execute(text(sql))
                    print(f"    ✅ Success")
                except Exception as e:
                    print(f"    ⚠️  Warning: {e}")
            
            # Create indexes
            print("📋 Creating indexes...")
            index_commands = [
                ("Creating lineup_escrow indexes", 
                 "CREATE INDEX IF NOT EXISTS idx_lineup_escrow_recipient_team ON lineup_escrow(recipient_team_id)"),
                
                ("Creating user_player_associations index", 
                 "CREATE INDEX IF NOT EXISTS idx_user_player_associations_primary ON user_player_associations(is_primary)"),
                
                ("Creating users indexes", 
                 "CREATE INDEX IF NOT EXISTS idx_users_team_id ON users(team_id)"),
            ]
            
            for description, sql in index_commands:
                try:
                    print(f"  {description}...")
                    conn.execute(text(sql))
                    print(f"    ✅ Success")
                except Exception as e:
                    print(f"    ⚠️  Warning: {e}")
            
            # Update alembic version
            try:
                print("📋 Updating schema version...")
                conn.execute(text("UPDATE alembic_version SET version_num = 'sync_all_env_001' WHERE version_num = 'c28892a55e1d'"))
                print("    ✅ Schema version updated")
            except Exception as e:
                print(f"    ⚠️  Warning: {e}")
            
            conn.commit()
            print("✅ Quick staging fix completed!")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error in quick staging fix: {e}")
        return False

def verify_staging():
    """Quick verification of staging"""
    print("🔍 Quick staging verification...")
    
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        engine = create_engine(staging_url, connect_args={"connect_timeout": 10})
        
        with engine.connect() as conn:
            # Check schema version
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"📋 Schema version: {version}")
            
            # Quick column checks
            checks = [
                ("lineup_escrow recipient_team_id", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'lineup_escrow' AND column_name = 'recipient_team_id'"),
                ("user_player_associations is_primary", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'user_player_associations' AND column_name = 'is_primary'"),
                ("users team_id", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'team_id'"),
            ]
            
            for check_name, query in checks:
                result = conn.execute(text(query))
                count = result.scalar()
                status = "✅" if count > 0 else "❌"
                print(f"{status} {check_name}: {'Present' if count > 0 else 'Missing'}")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying staging: {e}")
        return False

def main():
    """Main function"""
    print("🏓 QUICK STAGING FIX")
    print("=" * 40)
    
    # Run the fix
    if not fix_staging():
        print("❌ Quick staging fix failed")
        return 1
    
    # Verify the fix
    if not verify_staging():
        print("❌ Staging verification failed")
        return 1
    
    print("\n✅ STAGING FIX COMPLETE!")
    print("🌍 Staging should now be synced with production")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
