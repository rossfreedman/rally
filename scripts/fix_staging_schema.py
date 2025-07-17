#!/usr/bin/env python3
"""
Fix staging database schema - add missing tables and columns
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_staging_schema():
    """Fix missing schema components on staging database"""
    
    print("🔧 Fixing Staging Database Schema")
    print("=" * 50)
    
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
            
            # 1. Add team_id column to users table
            print("\n1️⃣ Adding team_id column to users table...")
            try:
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id)
                """)
                print("   ✅ team_id column added to users table")
            except Exception as e:
                print(f"   ❌ Error adding team_id: {e}")
            
            # 2. Create weather_cache table
            print("\n2️⃣ Creating weather_cache table...")
            try:
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
            except Exception as e:
                print(f"   ❌ Error creating weather_cache table: {e}")
            
            # 3. Create index on team_id for users table
            print("\n3️⃣ Creating index on team_id...")
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_team_id ON users(team_id)
                """)
                print("   ✅ team_id index created")
            except Exception as e:
                print(f"   ❌ Error creating team_id index: {e}")
            
            # 4. Populate team_id for users based on their primary player association
            print("\n4️⃣ Populating team_id for users...")
            try:
                cursor.execute("""
                    UPDATE users 
                    SET team_id = p.team_id
                    FROM user_player_associations upa
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    WHERE upa.user_id = users.id 
                    AND upa.is_primary = true
                    AND p.team_id IS NOT NULL
                    AND users.team_id IS NULL
                """)
                
                updated_count = cursor.rowcount
                print(f"   ✅ Updated {updated_count} users with team_id")
            except Exception as e:
                print(f"   ❌ Error populating team_id: {e}")
            
            # 5. Verify the fixes
            print("\n5️⃣ Verifying fixes...")
            
            # Check team_id column
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'team_id'
                )
            """)
            team_id_exists = cursor.fetchone()[0]
            print(f"   team_id column exists: {'✅' if team_id_exists else '❌'}")
            
            # Check weather_cache table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'weather_cache'
                )
            """)
            weather_cache_exists = cursor.fetchone()[0]
            print(f"   weather_cache table exists: {'✅' if weather_cache_exists else '❌'}")
            
            # Check users with team_id
            cursor.execute("SELECT COUNT(*) FROM users WHERE team_id IS NOT NULL")
            users_with_team = cursor.fetchone()[0]
            print(f"   Users with team_id: {users_with_team}")
            
            # Check captain_messages table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'captain_messages'
                )
            """)
            captain_messages_exists = cursor.fetchone()[0]
            print(f"   captain_messages table exists: {'✅' if captain_messages_exists else '❌'}")
        
        conn.commit()
        conn.close()
        print(f"\n✅ Schema fixes completed successfully")
        
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        return False
    
    return True

if __name__ == "__main__":
    fix_staging_schema() 