#!/usr/bin/env python3
"""
Add updated_at column to series_stats table on staging
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def add_updated_at_to_series_stats():
    """Add updated_at column to series_stats table on staging"""
    
    print("🔧 Adding updated_at column to series_stats table")
    print("=" * 60)
    
    # Staging database URL
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        # Parse and connect to staging database
        parsed = urlparse(staging_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            sslmode="require",
            connect_timeout=10
        )
        
        with conn.cursor() as cursor:
            
            # 1. Check if updated_at column already exists
            print("\n1️⃣ Checking if updated_at column exists...")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'series_stats' AND column_name = 'updated_at'
                )
            """)
            
            column_exists = cursor.fetchone()[0]
            print(f"   updated_at column exists: {'✅' if column_exists else '❌'}")
            
            if column_exists:
                print("   ✅ Column already exists - no action needed")
                return True
            
            # 2. Add updated_at column
            print("\n2️⃣ Adding updated_at column...")
            cursor.execute("""
                ALTER TABLE series_stats 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            """)
            print("   ✅ updated_at column added")
            
            # 3. Create trigger function if it doesn't exist
            print("\n3️⃣ Creating trigger function...")
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """)
            print("   ✅ Trigger function created")
            
            # 4. Create trigger for series_stats
            print("\n4️⃣ Creating trigger for series_stats...")
            cursor.execute("""
                DROP TRIGGER IF EXISTS update_series_stats_updated_at ON series_stats;
                CREATE TRIGGER update_series_stats_updated_at
                    BEFORE UPDATE ON series_stats
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column()
            """)
            print("   ✅ Trigger created")
            
            # 5. Update existing records to have updated_at = created_at
            print("\n5️⃣ Updating existing records...")
            cursor.execute("""
                UPDATE series_stats 
                SET updated_at = created_at 
                WHERE updated_at IS NULL
            """)
            
            updated_count = cursor.rowcount
            print(f"   ✅ Updated {updated_count} existing records")
            
            # 6. Verify the changes
            print("\n6️⃣ Verifying changes...")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'series_stats' AND column_name = 'updated_at'
            """)
            
            column_info = cursor.fetchone()
            if column_info:
                print(f"   ✅ Column verified: {column_info[0]} ({column_info[1]})")
            else:
                print("   ❌ Column not found after creation")
                return False
            
            # Check trigger
            cursor.execute("""
                SELECT trigger_name 
                FROM information_schema.triggers 
                WHERE event_object_table = 'series_stats' 
                AND trigger_name = 'update_series_stats_updated_at'
            """)
            
            trigger_exists = cursor.fetchone()
            print(f"   Trigger exists: {'✅' if trigger_exists else '❌'}")
        
        conn.commit()
        conn.close()
        print(f"\n✅ Successfully added updated_at column to series_stats table")
        
    except Exception as e:
        print(f"❌ Error adding updated_at column: {e}")
        return False
    
    return True

if __name__ == "__main__":
    add_updated_at_to_series_stats() 