#!/usr/bin/env python3
"""
Direct Staging Sync
==================

Directly sync staging database using SQL commands without alembic.
"""

import os
import sys
from sqlalchemy import create_engine, text

def sync_staging_direct():
    """Sync staging directly using SQL"""
    print("🚀 Direct staging sync...")
    
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        engine = create_engine(staging_url)
        
        with engine.connect() as conn:
            print("📋 Adding missing columns...")
            
            # Add missing columns one by one
            sql_commands = [
                # lineup_escrow columns
                "ALTER TABLE lineup_escrow ADD COLUMN IF NOT EXISTS recipient_team_id INTEGER REFERENCES teams(id)",
                "ALTER TABLE lineup_escrow ADD COLUMN IF NOT EXISTS initiator_team_id INTEGER REFERENCES teams(id)",
                
                # user_player_associations column
                "ALTER TABLE user_player_associations ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE",
                
                # match_scores columns
                "ALTER TABLE match_scores ADD COLUMN IF NOT EXISTS match_id VARCHAR(255)",
                "ALTER TABLE match_scores ADD COLUMN IF NOT EXISTS tenniscores_match_id VARCHAR(255)",
                
                # users columns
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS notifications_hidden BOOLEAN DEFAULT FALSE",
            ]
            
            for i, sql in enumerate(sql_commands, 1):
                try:
                    print(f"  {i}/{len(sql_commands)}: {sql[:50]}...")
                    conn.execute(text(sql))
                    print(f"    ✅ Success")
                except Exception as e:
                    print(f"    ⚠️  Warning: {e}")
                    # Continue with other commands
            
            # Create indexes
            print("📋 Creating indexes...")
            index_commands = [
                "CREATE INDEX IF NOT EXISTS idx_lineup_escrow_recipient_team ON lineup_escrow(recipient_team_id)",
                "CREATE INDEX IF NOT EXISTS idx_lineup_escrow_initiator_team ON lineup_escrow(initiator_team_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_player_associations_primary ON user_player_associations(is_primary)",
                "CREATE INDEX IF NOT EXISTS idx_match_scores_match_id ON match_scores(match_id)",
                "CREATE INDEX IF NOT EXISTS idx_match_scores_tenniscores_match_id ON match_scores(tenniscores_match_id)",
                "CREATE INDEX IF NOT EXISTS idx_users_team_id ON users(team_id)",
                "CREATE INDEX IF NOT EXISTS idx_users_notifications_hidden ON users(notifications_hidden)",
            ]
            
            for i, sql in enumerate(index_commands, 1):
                try:
                    print(f"  {i}/{len(index_commands)}: {sql[:50]}...")
                    conn.execute(text(sql))
                    print(f"    ✅ Success")
                except Exception as e:
                    print(f"    ⚠️  Warning: {e}")
            
            # Update alembic version
            print("📋 Updating schema version...")
            try:
                conn.execute(text("UPDATE alembic_version SET version_num = 'sync_all_env_001' WHERE version_num = 'c28892a55e1d'"))
                print("    ✅ Schema version updated")
            except Exception as e:
                print(f"    ⚠️  Warning: {e}")
            
            conn.commit()
            print("✅ Direct sync completed")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error in direct sync: {e}")
        return False

def verify_staging_sync():
    """Verify staging is now synced"""
    print("🔍 Verifying staging sync...")
    
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        engine = create_engine(staging_url)
        
        with engine.connect() as conn:
            # Check schema version
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"📋 Schema version: {version}")
            
            # Check key columns
            checks = [
                ("lineup_escrow recipient_team_id", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'lineup_escrow' AND column_name = 'recipient_team_id'"),
                ("lineup_escrow initiator_team_id", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'lineup_escrow' AND column_name = 'initiator_team_id'"),
                ("user_player_associations is_primary", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'user_player_associations' AND column_name = 'is_primary'"),
                ("users team_id", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'team_id'"),
                ("users notifications_hidden", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'notifications_hidden'"),
                ("match_scores match_id", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'match_scores' AND column_name = 'match_id'"),
                ("match_scores tenniscores_match_id", 
                 "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'match_scores' AND column_name = 'tenniscores_match_id'")
            ]
            
            all_present = True
            for check_name, query in checks:
                result = conn.execute(text(query))
                count = result.scalar()
                status = "✅" if count > 0 else "❌"
                present = count > 0
                print(f"{status} {check_name}: {'Present' if present else 'Missing'}")
                if not present:
                    all_present = False
            
            if all_present and version == 'sync_all_env_001':
                print("✅ Staging is now fully synced!")
                return True
            else:
                print("❌ Staging sync incomplete")
                return False
        
        engine.dispose()
        
    except Exception as e:
        print(f"❌ Error verifying staging sync: {e}")
        return False

def main():
    """Main function"""
    print("🏓 DIRECT STAGING SYNC")
    print("=" * 40)
    
    # Run direct sync
    if not sync_staging_direct():
        print("❌ Direct sync failed")
        return 1
    
    # Verify sync
    if not verify_staging_sync():
        print("❌ Staging verification failed")
        return 1
    
    print("\n✅ STAGING SYNC COMPLETE!")
    print("🌍 All three environments should now be in sync")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
