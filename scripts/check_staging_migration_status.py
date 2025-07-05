#!/usr/bin/env python3
"""
Check Staging Migration Status
=============================

This script checks if staging is missing the series.display_name migration
that's causing the ETL to fail.
"""

import os
import sys
import subprocess
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from database_config import parse_db_url

# Railway staging database URL
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

def check_staging_schema():
    """Check staging database schema for missing columns"""
    print("🔍 Checking Staging Database Schema")
    print("=" * 50)
    
    try:
        # Connect to staging
        params = parse_db_url(STAGING_DB_URL)
        params["connect_timeout"] = 30
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        
        # Check if display_name column exists in series table
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'series' 
            ORDER BY column_name
        """)
        
        series_columns = cursor.fetchall()
        
        print("📊 Series table columns on staging:")
        has_display_name = False
        for col_name, data_type, nullable in series_columns:
            if col_name == 'display_name':
                has_display_name = True
                print(f"   ✅ {col_name} ({data_type}) - {'NULL' if nullable == 'YES' else 'NOT NULL'}")
            else:
                print(f"   📝 {col_name} ({data_type}) - {'NULL' if nullable == 'YES' else 'NOT NULL'}")
        
        if not has_display_name:
            print("   ❌ Missing display_name column!")
        
        # Check if series_name_mappings table exists (should be dropped)
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'series_name_mappings'
            )
        """)
        
        has_old_table = cursor.fetchone()[0]
        
        print(f"\n📊 Old series_name_mappings table: {'EXISTS' if has_old_table else 'DROPPED'}")
        
        # Check alembic migration version
        cursor.execute("""
            SELECT version_num FROM alembic_version
        """)
        
        current_version = cursor.fetchone()[0]
        print(f"\n📊 Current Alembic version: {current_version}")
        
        # Summary
        print(f"\n📋 STAGING SCHEMA STATUS:")
        print(f"   display_name column: {'✅ EXISTS' if has_display_name else '❌ MISSING'}")
        print(f"   series_name_mappings: {'⚠️ STILL EXISTS' if has_old_table else '✅ DROPPED'}")
        print(f"   migration version: {current_version}")
        
        needs_migration = not has_display_name or has_old_table
        
        if needs_migration:
            print(f"\n🚨 ISSUE IDENTIFIED:")
            print(f"   Staging is missing the display_name migration!")
            print(f"   This is why ETL works locally but fails on staging.")
            return False
        else:
            print(f"\n✅ Schema looks good!")
            return True
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking staging schema: {e}")
        return False

def check_local_schema():
    """Check local database schema for comparison"""
    print("\n🏠 Checking Local Database Schema")
    print("=" * 50)
    
    try:
        # Connect to local
        LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
        params = parse_db_url(LOCAL_DB_URL)
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        
        # Check if display_name column exists in series table
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'series' 
            ORDER BY column_name
        """)
        
        series_columns = cursor.fetchall()
        
        print("📊 Series table columns on local:")
        has_display_name = False
        for col_name, data_type, nullable in series_columns:
            if col_name == 'display_name':
                has_display_name = True
                print(f"   ✅ {col_name} ({data_type}) - {'NULL' if nullable == 'YES' else 'NOT NULL'}")
            else:
                print(f"   📝 {col_name} ({data_type}) - {'NULL' if nullable == 'YES' else 'NOT NULL'}")
        
        # Check alembic migration version
        cursor.execute("""
            SELECT version_num FROM alembic_version
        """)
        
        current_version = cursor.fetchone()[0]
        print(f"\n📊 Local Alembic version: {current_version}")
        
        conn.close()
        return has_display_name
        
    except Exception as e:
        print(f"❌ Error checking local schema: {e}")
        return False

def run_migration_on_staging():
    """Run the missing migration on staging"""
    print("\n🚀 Running Migration on Staging")
    print("=" * 50)
    
    try:
        # Set environment to target staging
        env = os.environ.copy()
        env["SYNC_RAILWAY_STAGING"] = "true"
        
        # Run alembic upgrade
        print("Running: alembic upgrade head")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            print("📋 Migration output:")
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print(f"   {line}")
            return True
        else:
            print("❌ Migration failed!")
            print("Error output:")
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        print(f"   {line}")
            return False
        
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        return False

def main():
    """Main function"""
    print("🔧 ETL Series Migration Fix Tool")
    print("=" * 60)
    print("This tool checks and fixes the missing display_name migration on staging")
    print()
    
    # Step 1: Check local schema (for comparison)
    local_ok = check_local_schema()
    
    # Step 2: Check staging schema
    staging_ok = check_staging_schema()
    
    if local_ok and not staging_ok:
        print(f"\n💡 DIAGNOSIS CONFIRMED:")
        print(f"   ✅ Local has display_name column (ETL works)")
        print(f"   ❌ Staging missing display_name column (ETL fails)")
        print(f"   🎯 Solution: Run missing migration on staging")
        
        response = input(f"\nRun migration on staging? (yes/no): ")
        if response.lower() == "yes":
            if run_migration_on_staging():
                print(f"\n🎉 SUCCESS!")
                print(f"   ✅ Migration completed on staging")
                print(f"   ✅ ETL should now work on staging")
                print(f"   🚀 Try running your ETL again!")
                return 0
            else:
                print(f"\n❌ Migration failed - manual intervention needed")
                return 1
        else:
            print(f"❌ Migration cancelled")
            return 1
    
    elif staging_ok:
        print(f"\n✅ Staging schema looks correct")
        print(f"   The issue might be something else...")
        return 0
    
    else:
        print(f"\n❌ Unable to diagnose the issue")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 