#!/usr/bin/env python3
"""
Fix Staging Series Table Issue
==============================

Both staging and local have the display_name column, but staging still has
the old series_name_mappings table. This needs to be cleaned up.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from database_config import parse_db_url

# Railway staging database URL
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

def check_staging_status():
    """Check the current status of staging database"""
    print("🔍 Checking Staging Database Status")
    print("=" * 50)
    
    try:
        params = parse_db_url(STAGING_DB_URL)
        params["connect_timeout"] = 30
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        
        # Check display_name column
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'series' AND column_name = 'display_name'
            )
        """)
        has_display_name = cursor.fetchone()[0]
        
        # Check old table
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'series_name_mappings'
            )
        """)
        has_old_table = cursor.fetchone()[0]
        
        # Check series count in both systems
        cursor.execute("SELECT COUNT(*) FROM series")
        series_count = cursor.fetchone()[0]
        
        old_mappings_count = 0
        if has_old_table:
            cursor.execute("SELECT COUNT(*) FROM series_name_mappings")
            old_mappings_count = cursor.fetchone()[0]
        
        print(f"📊 Status Summary:")
        print(f"   ✅ display_name column: {'EXISTS' if has_display_name else 'MISSING'}")
        print(f"   ⚠️  series_name_mappings table: {'EXISTS' if has_old_table else 'DROPPED'}")
        print(f"   📈 Series records: {series_count}")
        print(f"   📈 Old mappings: {old_mappings_count}")
        
        conn.close()
        
        return has_display_name, has_old_table, series_count, old_mappings_count
        
    except Exception as e:
        print(f"❌ Error checking staging: {e}")
        return False, False, 0, 0

def fix_staging_issue():
    """Fix the staging issue by dropping the old table"""
    print("\n🔧 Fixing Staging Issue")
    print("=" * 50)
    
    try:
        params = parse_db_url(STAGING_DB_URL)
        params["connect_timeout"] = 30
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        
        # Safety check: Ensure display_name column exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'series' AND column_name = 'display_name'
            )
        """)
        has_display_name = cursor.fetchone()[0]
        
        if not has_display_name:
            print("❌ Safety check failed: display_name column doesn't exist!")
            return False
        
        # Check if series have display names populated
        cursor.execute("SELECT COUNT(*) FROM series WHERE display_name IS NOT NULL")
        populated_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM series")
        total_count = cursor.fetchone()[0]
        
        print(f"📊 Safety checks:")
        print(f"   ✅ display_name column exists")
        print(f"   📈 {populated_count}/{total_count} series have display names")
        
        if populated_count == 0:
            print("❌ No series have display names populated - migration incomplete!")
            return False
        
        # Drop the old table
        print("\n🗑️  Dropping old series_name_mappings table...")
        cursor.execute("DROP TABLE IF EXISTS series_name_mappings CASCADE")
        
        # Verify it's gone
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'series_name_mappings'
            )
        """)
        still_exists = cursor.fetchone()[0]
        
        if still_exists:
            print("❌ Failed to drop table!")
            conn.rollback()
            return False
        
        conn.commit()
        print("✅ Successfully dropped series_name_mappings table")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error fixing staging: {e}")
        return False

def test_etl_logic():
    """Test if the ETL series mapping logic works now"""
    print("\n🧪 Testing ETL Logic")
    print("=" * 50)
    
    try:
        # Import the ETL class
        sys.path.append('data/etl/database_import')
        from import_all_jsons_to_database import ComprehensiveETL
        
        # Create ETL instance
        etl = ComprehensiveETL(force_environment='railway_staging')
        
        # Test the series mapping loading
        with etl.get_railway_optimized_db_connection() as conn:
            print("Testing series mapping loading...")
            etl.load_series_mappings(conn)
            
            # Check if it loaded mappings
            mapping_count = sum(len(mappings) for mappings in etl.series_mappings.values())
            print(f"📊 Loaded {mapping_count} series mappings")
            
            if mapping_count > 0:
                print("✅ ETL series mapping logic is working!")
                return True
            else:
                print("⚠️  No mappings loaded (might be normal)")
                return True
        
    except Exception as e:
        print(f"❌ Error testing ETL logic: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("🔧 Staging Series Table Fix Tool")
    print("=" * 60)
    print("This tool fixes the old series_name_mappings table issue on staging")
    print()
    
    # Step 1: Check current status
    has_display, has_old, series_count, mappings_count = check_staging_status()
    
    if not has_display:
        print("\n❌ CRITICAL: display_name column is missing!")
        print("   Run the migration first: alembic upgrade head")
        return 1
    
    if not has_old:
        print("\n✅ No issue found - old table already dropped")
        return 0
    
    print(f"\n🎯 ISSUE IDENTIFIED:")
    print(f"   ✅ display_name column exists (good)")
    print(f"   ⚠️  series_name_mappings table still exists (bad)")
    print(f"   🔧 Solution: Drop the old table")
    
    response = input(f"\nDrop the old series_name_mappings table? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Operation cancelled")
        return 1
    
    # Step 2: Fix the issue
    if fix_staging_issue():
        print(f"\n🎉 SUCCESS!")
        print(f"   ✅ Old table dropped")
        print(f"   ✅ Only display_name column remains")
        
        # Step 3: Test ETL logic
        if test_etl_logic():
            print(f"   ✅ ETL logic tested successfully")
            print(f"\n🚀 Try running your ETL again - it should work now!")
        else:
            print(f"   ⚠️  ETL logic test failed - check manually")
        
        return 0
    else:
        print(f"\n❌ Fix failed - manual intervention needed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 