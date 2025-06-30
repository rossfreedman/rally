#!/usr/bin/env python3
"""
Manual Schema Fix

Apply the schema fixes that the ETL should have applied but apparently didn't
"""

import os
import sys

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one

def main():
    print("🔧 Applying manual schema fixes...")
    
    try:
        # Fix 1: Create system_settings table
        print("\n1️⃣ Creating system_settings table...")
        execute_query("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR(255) UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ system_settings table created/verified")
        
        # Fix 2: Initialize session_version
        print("\n2️⃣ Setting session_version...")
        execute_query("""
            INSERT INTO system_settings (key, value, description) 
            VALUES ('session_version', '6', 'Current session version for cache busting')
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """)
        print("✅ session_version initialized")
        
        # Fix 3: Add logo_filename column to clubs
        print("\n3️⃣ Adding logo_filename column to clubs...")
        execute_query("""
            ALTER TABLE clubs 
            ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(255)
        """)
        print("✅ logo_filename column added")
        
        # Verify the fixes worked
        print("\n🔍 Verifying fixes...")
        
        # Check system_settings
        result = execute_query_one("SELECT value FROM system_settings WHERE key = 'session_version'")
        if result:
            print(f"✅ session_version = {result[0]}")
        else:
            print("❌ session_version not found")
        
        # Check logo_filename column
        result = execute_query_one("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'clubs' AND column_name = 'logo_filename'
        """)
        if result:
            print("✅ logo_filename column exists")
        else:
            print("❌ logo_filename column missing")
        
        print("\n🎉 Schema fixes applied successfully!")
        print("🔄 Try accessing the application now - the errors should be resolved")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying schema fixes: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 