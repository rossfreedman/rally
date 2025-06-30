#!/usr/bin/env python3
"""
Railway Schema Check

Simple script to verify schema fixes on Railway database
Run this with: railway shell python scripts/railway_schema_check.py
"""

import psycopg2
import os
from urllib.parse import urlparse

def main():
    print("🔍 Checking Railway database schema status...")
    
    # Get Railway database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found")
        return False
    
    # Parse database URL
    parsed = urlparse(db_url)
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            sslmode='prefer'
        )
        
        cursor = conn.cursor()
        print("✅ Connected to Railway database")
        
        # Check 1: system_settings table
        print("\n1️⃣ Checking system_settings table...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'system_settings'
            )
        """)
        system_settings_exists = cursor.fetchone()[0]
        
        if system_settings_exists:
            print("✅ system_settings table EXISTS")
            
            # Check session_version
            cursor.execute("SELECT value FROM system_settings WHERE key = 'session_version'")
            version_result = cursor.fetchone()
            if version_result:
                print(f"✅ session_version = {version_result[0]}")
            else:
                print("❌ session_version key missing")
        else:
            print("❌ system_settings table MISSING")
        
        # Check 2: clubs.logo_filename column
        print("\n2️⃣ Checking clubs.logo_filename column...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'clubs' AND column_name = 'logo_filename'
            )
        """)
        logo_column_exists = cursor.fetchone()[0]
        
        if logo_column_exists:
            print("✅ clubs.logo_filename column EXISTS")
        else:
            print("❌ clubs.logo_filename column MISSING")
        
        # Test the queries that were failing
        print("\n3️⃣ Testing problem queries...")
        try:
            cursor.execute("SELECT value FROM system_settings WHERE key = 'session_version' LIMIT 1")
            result = cursor.fetchone()
            print(f"✅ system_settings query works: {result}")
        except Exception as e:
            print(f"❌ system_settings query fails: {e}")
        
        try:
            cursor.execute("SELECT c.name, c.logo_filename FROM clubs c LIMIT 1")
            result = cursor.fetchone()
            print(f"✅ clubs.logo_filename query works: {result}")
        except Exception as e:
            print(f"❌ clubs.logo_filename query fails: {e}")
        
        # Summary
        print("\n" + "="*50)
        print("🎯 DIAGNOSIS:")
        print(f"system_settings_exists: {system_settings_exists}")
        print(f"logo_column_exists: {logo_column_exists}")
        
        if system_settings_exists and logo_column_exists:
            print("✅ Schema fixes are APPLIED successfully")
            print("📋 The database schema is correct")
        else:
            print("❌ Schema fixes are NOT applied")
            print("🔧 The ETL schema fixes didn't work properly")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 