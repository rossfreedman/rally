#!/usr/bin/env python3
"""
Run temporary password migration on staging database.
"""

import os
import sys
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_temp_password_migration():
    """Run the temporary password migration on staging"""
    
    # Load environment variables
    load_dotenv()
    
    # Check if we're on staging
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "not_set")
    if railway_env != "staging":
        print(f"❌ This script should only be run on staging environment")
        print(f"   Current environment: {railway_env}")
        return False
    
    try:
        from database_utils import execute_update
        
        print("🔄 Running temporary password migration...")
        
        # Migration SQL
        migration_sql = """
        -- Add columns to track temporary passwords
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS has_temporary_password BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS temporary_password_set_at TIMESTAMP;

        -- Add index for efficient querying
        CREATE INDEX IF NOT EXISTS idx_users_temporary_password 
        ON users(has_temporary_password) 
        WHERE has_temporary_password = TRUE;

        -- Add comment for documentation
        COMMENT ON COLUMN users.has_temporary_password IS 'Flag indicating if user has a temporary password that needs to be changed';
        COMMENT ON COLUMN users.temporary_password_set_at IS 'Timestamp when temporary password was set';
        """
        
        # Execute the migration
        execute_update(migration_sql)
        
        print("✅ Temporary password migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = run_temp_password_migration()
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        sys.exit(1) 