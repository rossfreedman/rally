#!/usr/bin/env python3
"""
Apply Food Fields Migration
============================

Adds mens_food and womens_food columns to the food table.
This script applies the migration to the local database.

Usage:
    python scripts/apply_food_fields_migration.py
"""

import os
import sys
from pathlib import Path

# Add root directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database_config import parse_db_url
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def apply_migration():
    """Apply the food fields migration to local database"""
    
    print("=" * 70)
    print("🍽️  Food Fields Migration - Add Men's & Women's Paddle Options")
    print("=" * 70)
    print()
    
    # Get local database URL
    db_url = os.getenv('DATABASE_URL_LOCAL') or os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL_LOCAL or DATABASE_URL not found in environment")
        return False
    
    # Parse database URL
    db_config = parse_db_url(db_url)
    
    print(f"📊 Target Database: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print()
    
    # Read migration SQL
    migration_file = Path(__file__).parent.parent / 'migrations' / 'add_mens_womens_food_fields.sql'
    
    if not migration_file.exists():
        print(f"❌ ERROR: Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("📝 Migration SQL:")
    print("-" * 70)
    print(migration_sql)
    print("-" * 70)
    print()
    
    # Confirm execution
    response = input("🔄 Apply this migration to local database? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Migration cancelled")
        return False
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )
        conn.autocommit = False
        cursor = conn.cursor()
        
        print("✅ Connected successfully")
        print()
        
        # Execute migration
        print("🚀 Applying migration...")
        cursor.execute(migration_sql)
        
        # Verify columns were added
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'food' 
            AND column_name IN ('mens_food', 'womens_food')
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        
        if len(columns) == 2:
            print("✅ Migration applied successfully!")
            print()
            print("📋 New columns:")
            for col_name, data_type, is_nullable in columns:
                print(f"   - {col_name}: {data_type} (nullable: {is_nullable})")
            
            # Commit changes
            conn.commit()
            print()
            print("✅ Changes committed to database")
            
            cursor.close()
            conn.close()
            
            return True
        else:
            print("❌ ERROR: Expected 2 columns but found", len(columns))
            conn.rollback()
            cursor.close()
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ ERROR applying migration: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print()
    success = apply_migration()
    print()
    
    if success:
        print("=" * 70)
        print("✅ SUCCESS - Migration completed!")
        print("=" * 70)
        print()
        print("📝 Next Steps:")
        print("   1. Test the changes locally by visiting /food")
        print("   2. Verify data entry works with both men's and women's options")
        print("   3. Deploy to staging using: python data/dbschema/dbschema_workflow.py --auto")
        print("   4. Test on staging environment")
        print("   5. Deploy to production")
        print()
        sys.exit(0)
    else:
        print("=" * 70)
        print("❌ FAILED - Migration did not complete")
        print("=" * 70)
        print()
        sys.exit(1)

