#!/usr/bin/env python3
"""
Verify Schema Status

Check if the schema fixes were actually applied to the Railway database
"""

import os
import sys

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# Force Railway database connection by setting DATABASE_URL to public URL
if not os.getenv("RAILWAY_ENVIRONMENT"):
    # We're running locally, force Railway public connection
    railway_public_url = os.getenv("DATABASE_PUBLIC_URL")
    if railway_public_url:
        os.environ["DATABASE_URL"] = railway_public_url
        print(f"🔗 Connecting to Railway database")
    else:
        print("❌ DATABASE_PUBLIC_URL not found in environment")
        sys.exit(1)

from database_utils import execute_query_one, execute_query

def main():
    print("🔍 Verifying Railway database schema status...")
    
    try:
        # Check 1: Does system_settings table exist?
        print("\n1️⃣ Checking system_settings table...")
        result = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'system_settings'
            )
        """)
        
        print(f"Debug: system_settings table check result = {result}")
        
        # Handle RealDictRow - access by key name
        system_settings_exists = result['exists'] if result else False
        
        if system_settings_exists:
            print("✅ system_settings table EXISTS")
            
            # Check if session_version exists
            version_result = execute_query_one("""
                SELECT value FROM system_settings WHERE key = 'session_version'
            """)
            print(f"Debug: session_version result = {version_result}")
            if version_result:
                print(f"✅ session_version = {version_result['value']}")
            else:
                print("❌ session_version key missing")
        else:
            print("❌ system_settings table MISSING")
        
        # Check 2: Does clubs.logo_filename column exist?
        print("\n2️⃣ Checking clubs.logo_filename column...")
        result = execute_query_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'clubs' AND column_name = 'logo_filename'
            )
        """)
        
        print(f"Debug: clubs.logo_filename check result = {result}")
        
        # Handle RealDictRow - access by key name
        logo_column_exists = result['exists'] if result else False
        
        if logo_column_exists:
            print("✅ clubs.logo_filename column EXISTS")
        else:
            print("❌ clubs.logo_filename column MISSING")
        
        # Check 3: Test the specific queries that were failing
        print("\n3️⃣ Testing problem queries...")
        
        try:
            test_result = execute_query_one("SELECT value FROM system_settings WHERE key = 'session_version' LIMIT 1")
            print(f"✅ system_settings query works, result: {test_result}")
        except Exception as e:
            print(f"❌ system_settings query fails: {e}")
        
        try:
            test_result = execute_query_one("SELECT c.name, c.logo_filename FROM clubs c LIMIT 1")
            print(f"✅ clubs.logo_filename query works, result: {test_result}")
        except Exception as e:
            print(f"❌ clubs.logo_filename query fails: {e}")
            
        print("\n" + "="*50)
        print("🎯 DIAGNOSIS:")
        
        print(f"system_settings_exists: {system_settings_exists}")
        print(f"logo_column_exists: {logo_column_exists}")
        
        if system_settings_exists and logo_column_exists:
            print("✅ Schema fixes are APPLIED successfully")
            print("📋 The database schema is correct")
            print("🤔 If you're still seeing errors, they may be:")
            print("   - Application cache issues")
            print("   - Session data problems") 
            print("   - Different error source")
        else:
            print("❌ Schema fixes are NOT applied")
            print("🔧 Need to apply the schema fixes manually")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking schema: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 