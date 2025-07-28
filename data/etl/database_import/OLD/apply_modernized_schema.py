#!/usr/bin/env python3
"""
Apply Modernized ETL Schema Changes
===================================

This script applies the necessary database schema changes for the modernized ETL system:
1. Adds tenniscores_match_id column to match_scores table
2. Creates unique index for upsert operations
"""

import os
import sys

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from database_config import get_db


def apply_schema_migration():
    """Apply the tenniscores_match_id schema migration"""
    print("🔧 Applying Modernized ETL Schema Changes...")
    
    # Read the migration SQL
    migration_file = os.path.join(
        project_root,
        "data", "dbschema", "migrations", "20250115_140000_add_tenniscores_match_id.sql"
    )
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Connect to database and apply migration
        with get_db() as conn:
            cursor = conn.cursor()
            
            print("📊 Executing schema migration...")
            cursor.execute(migration_sql)
            conn.commit()
            
            print("✅ Schema migration applied successfully!")
            
            # Verify the changes
            cursor.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'match_scores' AND column_name = 'tenniscores_match_id'
            """)
            
            result = cursor.fetchone()
            if result:
                print(f"✅ Verified: tenniscores_match_id column added ({result[1]})")
            else:
                print("⚠️ Warning: Could not verify column addition")
            
            # Check index
            cursor.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'match_scores' 
                AND indexname = 'idx_match_scores_tenniscores_match_id'
            """)
            
            index_result = cursor.fetchone()
            if index_result:
                print("✅ Verified: Unique index created")
            else:
                print("⚠️ Warning: Could not verify index creation")
            
            cursor.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MODERNIZED ETL SCHEMA MIGRATION")
    print("=" * 60)
    
    success = apply_schema_migration()
    
    if success:
        print("\n🎉 Schema migration complete!")
        print("\nNext steps:")
        print("1. Run: python data/etl/database_import/modernized_import_filterable.py")
        print("2. Test with a specific league and series")
        print("3. Re-run the same import to verify upsert functionality")
    else:
        print("\n❌ Schema migration failed. Please check the error above.") 