#!/usr/bin/env python3
"""
Sync local user_contexts schema to match production
"""
import psycopg2
import sys

def sync_local_schema():
    """Update local user_contexts table to match production schema"""
    
    try:
        # Connect to local database
        conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5432/rally')
        cursor = conn.cursor()
        
        print("🔄 Syncing local user_contexts schema with production...")
        
        # Step 1: Backup any existing data
        print("📋 Backing up existing data...")
        cursor.execute("SELECT * FROM user_contexts")
        existing_data = cursor.fetchall()
        print(f"Found {len(existing_data)} existing records")
        
        # Step 2: Drop and recreate table with production schema
        print("🗑️  Dropping old table...")
        cursor.execute("DROP TABLE IF EXISTS user_contexts CASCADE")
        
        print("🏗️  Creating new table with production schema...")
        cursor.execute("""
            CREATE TABLE user_contexts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                league_id INTEGER REFERENCES leagues(id),
                team_id INTEGER REFERENCES teams(id),
                series_id INTEGER REFERENCES series(id),
                club VARCHAR(255),
                context_type VARCHAR(50) DEFAULT 'current',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(user_id, context_type)
            )
        """)
        
        # Step 3: Restore data if any existed
        if existing_data:
            print("💾 Restoring data with new schema...")
            for row in existing_data:
                # Map old schema to new schema
                # old: (user_id, active_league_id, active_team_id, last_updated)
                # new: (user_id, league_id, team_id, series_id, club, context_type, is_active, created_at, updated_at)
                cursor.execute("""
                    INSERT INTO user_contexts 
                    (user_id, league_id, team_id, context_type, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, 'current', true, %s, %s)
                """, (row[0], row[1], row[2], row[3], row[3]))  # use last_updated for both created/updated
        
        # Step 4: Create indexes
        print("📇 Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_contexts_user_id ON user_contexts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_contexts_active ON user_contexts(is_active)")
        
        # Commit changes
        conn.commit()
        
        # Step 5: Verify the new schema
        print("✅ Verifying new schema...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user_contexts' 
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print("New local schema:")
        for col_name, data_type in columns:
            print(f"  - {col_name}: {data_type}")
            
        cursor.close()
        conn.close()
        
        print("\n🎉 Local database schema successfully synced with production!")
        print("✅ Registration should now work consistently across all environments")
        
    except Exception as e:
        print(f"❌ Error syncing schema: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    response = input("🚨 This will DROP and recreate the user_contexts table locally. Continue? (y/N): ")
    if response.lower() in ['y', 'yes']:
        sync_local_schema()
    else:
        print("❌ Operation cancelled")
