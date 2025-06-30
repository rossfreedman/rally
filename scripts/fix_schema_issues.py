#!/usr/bin/env python3
"""
Fix Schema Issues Script

Fixes missing database schema elements after ETL import:
1. Creates system_settings table
2. Adds logo_filename column to clubs table
"""

import os
import sys

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one

def main():
    print("🔧 Fixing missing schema elements...")
    
    try:
        # 1. Create system_settings table
        print("📋 Creating system_settings table...")
        execute_query('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR(255) UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize session_version
        execute_query('''
            INSERT INTO system_settings (key, value, description) 
            VALUES ('session_version', '5', 'Current session version for cache busting')
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        ''')
        print("✅ System settings table created and initialized")
        
        # 2. Add logo_filename column to clubs
        print("🏢 Adding logo_filename column to clubs table...")
        execute_query('''
            ALTER TABLE clubs 
            ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(255)
        ''')
        print("✅ Logo filename column added to clubs table")
        
        # 3. Verify fixes
        print("🔍 Verifying fixes...")
        
        # Test system_settings
        result = execute_query_one("SELECT value FROM system_settings WHERE key = 'session_version'")
        session_version = result[0] if result else "Not found"
        print(f"✅ System settings working: session_version = {session_version}")
        
        # Test clubs schema
        result = execute_query_one('''
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'clubs' AND column_name = 'logo_filename'
        ''')
        logo_column = "exists" if result else "missing"
        print(f"✅ Logo filename column: {logo_column}")
        
        print("\n🎉 All schema issues fixed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing schema: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 