#!/usr/bin/env python3
"""
Fix staging database schema - run this on Railway staging environment
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_staging_schema_internal():
    """Fix missing schema components on staging database using internal Railway connection"""
    
    print("🔧 Fixing Staging Database Schema (Internal Railway Connection)")
    print("=" * 70)
    
    # Get the DATABASE_URL that the application is actually using
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    print(f"📡 Using DATABASE_URL: {database_url[:50]}...")
    
    try:
        # Parse and connect to the database
        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            sslmode="prefer",  # Use prefer for internal Railway connections
            connect_timeout=10
        )
        
        with conn.cursor() as cursor:
            
            # 1. Check if weather_cache table exists
            print("\n1️⃣ Checking weather_cache table...")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'weather_cache'
                )
            """)
            
            weather_cache_exists = cursor.fetchone()[0]
            print(f"   weather_cache table exists: {'✅' if weather_cache_exists else '❌'}")
            
            if not weather_cache_exists:
                print("   Creating weather_cache table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS weather_cache (
                        id SERIAL PRIMARY KEY,
                        location VARCHAR(500) NOT NULL,
                        forecast_date DATE NOT NULL,
                        weather_data JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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
                
                # Create trigger function for updated_at
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
                
                print("   ✅ weather_cache table created with indexes and triggers")
            else:
                print("   ✅ weather_cache table already exists")
            
            # 2. Check if updated_at column exists in series_stats
            print("\n2️⃣ Checking series_stats.updated_at column...")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'series_stats' AND column_name = 'updated_at'
                )
            """)
            
            updated_at_exists = cursor.fetchone()[0]
            print(f"   updated_at column exists: {'✅' if updated_at_exists else '❌'}")
            
            if not updated_at_exists:
                print("   Adding updated_at column...")
                cursor.execute("""
                    ALTER TABLE series_stats 
                    ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                """)
                print("   ✅ updated_at column added")
                
                # Create trigger function if it doesn't exist
                print("   Creating trigger function...")
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
                
                # Create trigger for series_stats
                print("   Creating trigger for series_stats...")
                cursor.execute("""
                    DROP TRIGGER IF EXISTS update_series_stats_updated_at ON series_stats;
                    CREATE TRIGGER update_series_stats_updated_at
                        BEFORE UPDATE ON series_stats
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column()
                """)
                print("   ✅ Trigger created")
                
                # Update existing records to have updated_at = created_at
                print("   Updating existing records...")
                cursor.execute("""
                    UPDATE series_stats 
                    SET updated_at = created_at 
                    WHERE updated_at IS NULL
                """)
                
                updated_count = cursor.rowcount
                print(f"   ✅ Updated {updated_count} existing records")
            else:
                print("   ✅ updated_at column already exists")
            
            # 3. Verify the fixes
            print("\n3️⃣ Verifying fixes...")
            
            # Test weather_cache query
            try:
                cursor.execute("SELECT COUNT(*) FROM weather_cache")
                count = cursor.fetchone()[0]
                print(f"   ✅ Weather cache query successful - {count} entries")
            except Exception as e:
                print(f"   ❌ Weather cache query failed: {str(e)}")
            
            # Test series_stats query with updated_at
            try:
                cursor.execute("""
                    SELECT 
                        ss.team,
                        ss.points,
                        ss.matches_won,
                        ss.matches_lost,
                        ss.matches_tied,
                        ss.league_id,
                        ss.series_id
                    FROM series_stats ss
                    WHERE ss.series_id = 11767 AND ss.league_id = 4733
                    AND ss.team = 'Tennaqua - 22'
                    ORDER BY ss.updated_at DESC
                    LIMIT 1
                """)
                
                result = cursor.fetchone()
                if result:
                    print(f"   ✅ Team position query successful - found: {result[0]}")
                else:
                    print(f"   ⚠️  Team position query successful but no results found")
                    
            except Exception as e:
                print(f"   ❌ Team position query failed: {str(e)}")
        
        conn.commit()
        conn.close()
        print(f"\n✅ Successfully fixed staging database schema")
        print(f"🎉 The application should now work without schema errors!")
        
    except Exception as e:
        print(f"❌ Error fixing staging schema: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_staging_schema_internal() 