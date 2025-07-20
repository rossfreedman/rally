#!/usr/bin/env python3
"""
Fix Production Schema Issues After ETL

This script fixes the database schema issues that occur after ETL:
1. Creates missing weather_cache table
2. Adds missing updated_at column to series_stats
3. Fixes team position notification issues
"""

import os
import sys
import psycopg2
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

def create_weather_cache_table(conn):
    """Create weather_cache table if it doesn't exist"""
    cursor = conn.cursor()
    
    try:
        print("🔧 Creating weather_cache table...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_cache (
                id SERIAL PRIMARY KEY,
                location VARCHAR(255) NOT NULL,
                forecast_date DATE NOT NULL,
                weather_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create unique index
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_cache_location_date
            ON weather_cache(location, forecast_date)
        """)
        
        # Create index on created_at
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_cache_created_at
            ON weather_cache(created_at)
        """)
        
        # Create function to update updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_weather_cache_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        
        # Create trigger
        cursor.execute("""
            DROP TRIGGER IF EXISTS trigger_update_weather_cache_updated_at ON weather_cache;
            CREATE TRIGGER trigger_update_weather_cache_updated_at
            BEFORE UPDATE ON weather_cache
            FOR EACH ROW
            EXECUTE FUNCTION update_weather_cache_updated_at()
        """)
        
        conn.commit()
        print("   ✅ weather_cache table created with indexes and triggers")
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating weather_cache table: {e}")
        conn.rollback()
        return False

def add_updated_at_to_series_stats(conn):
    """Add updated_at column to series_stats table if it doesn't exist"""
    cursor = conn.cursor()
    
    try:
        print("🔧 Adding updated_at column to series_stats table...")
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'series_stats' AND column_name = 'updated_at'
        """)
        
        if cursor.fetchone()[0] > 0:
            print("   ✅ updated_at column already exists in series_stats")
            return True
        
        # Add updated_at column
        cursor.execute("""
            ALTER TABLE series_stats 
            ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
        
        # Update existing records
        cursor.execute("""
            UPDATE series_stats 
            SET updated_at = created_at 
            WHERE updated_at IS NULL
        """)
        
        # Create function to update updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_series_stats_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        
        # Create trigger
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_series_stats_updated_at ON series_stats;
            CREATE TRIGGER update_series_stats_updated_at
            BEFORE UPDATE ON series_stats
            FOR EACH ROW
            EXECUTE FUNCTION update_series_stats_updated_at()
        """)
        
        conn.commit()
        print("   ✅ updated_at column added to series_stats with trigger")
        return True
        
    except Exception as e:
        print(f"   ❌ Error adding updated_at to series_stats: {e}")
        conn.rollback()
        return False

def check_schema_health(conn):
    """Check the health of the database schema"""
    cursor = conn.cursor()
    
    print("\n🔍 Checking database schema health...")
    
    # Check weather_cache table
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = 'weather_cache'
    """)
    weather_cache_exists = cursor.fetchone()[0] > 0
    print(f"   weather_cache table exists: {'✅' if weather_cache_exists else '❌'}")
    
    # Check series_stats updated_at column
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name = 'series_stats' AND column_name = 'updated_at'
    """)
    updated_at_exists = cursor.fetchone()[0] > 0
    print(f"   series_stats.updated_at column exists: {'✅' if updated_at_exists else '❌'}")
    
    # Check series_stats columns
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'series_stats' 
        ORDER BY column_name
    """)
    columns = [row[0] for row in cursor.fetchall()]
    print(f"   series_stats columns: {columns}")
    
    return weather_cache_exists, updated_at_exists

def main():
    """Main function to fix production schema issues"""
    print("🚀 Fixing Production Schema Issues After ETL")
    print("=" * 60)
    
    try:
        # Get database connection
        with get_db() as conn:
            # Check current schema health
            weather_cache_ok, updated_at_ok = check_schema_health(conn)
            
            # Fix weather_cache table
            if not weather_cache_ok:
                create_weather_cache_table(conn)
            else:
                print("   ✅ weather_cache table already exists")
            
            # Fix series_stats updated_at column
            if not updated_at_ok:
                add_updated_at_to_series_stats(conn)
            else:
                print("   ✅ series_stats.updated_at column already exists")
            
            # Final health check
            print("\n🔍 Final schema health check...")
            weather_cache_ok, updated_at_ok = check_schema_health(conn)
            
            if weather_cache_ok and updated_at_ok:
                print("\n✅ All schema issues fixed successfully!")
                print("   - weather_cache table: ✅")
                print("   - series_stats.updated_at: ✅")
                print("   - Team position notifications should now work")
                print("   - Weather service should now work")
            else:
                print("\n❌ Some schema issues remain:")
                print(f"   - weather_cache table: {'✅' if weather_cache_ok else '❌'}")
                print(f"   - series_stats.updated_at: {'✅' if updated_at_ok else '❌'}")
                
    except Exception as e:
        print(f"❌ Error fixing schema issues: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 