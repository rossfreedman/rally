#!/usr/bin/env python3
"""
Sync Groups Tables to Staging
============================

Uses the Railway database connection to create the groups and group_members tables.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

def create_groups_tables_on_staging():
    """Create groups tables directly on staging database"""
    print("🚀 Syncing Groups Tables to Staging")
    print("=" * 40)
    
    # Railway database URL
    railway_url = os.getenv('DATABASE_PUBLIC_URL')
    if not railway_url:
        print("❌ DATABASE_PUBLIC_URL not set")
        return False
    
    print(f"🔗 Connecting to Railway staging...")
    
    try:
        conn = psycopg2.connect(railway_url)
        
        with conn.cursor() as cursor:
            print("📄 Creating groups tables...")
            
            # Create the groups table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    creator_user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Foreign key constraint
                    CONSTRAINT fk_groups_creator_user_id 
                        FOREIGN KEY (creator_user_id) 
                        REFERENCES users(id) 
                        ON DELETE CASCADE
                );
            """)
            print("   ✅ Groups table created")
            
            # Create the group_members table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    added_by_user_id INTEGER NOT NULL,
                    
                    -- Foreign key constraints
                    CONSTRAINT fk_group_members_group_id 
                        FOREIGN KEY (group_id) 
                        REFERENCES groups(id) 
                        ON DELETE CASCADE,
                        
                    CONSTRAINT fk_group_members_user_id 
                        FOREIGN KEY (user_id) 
                        REFERENCES users(id) 
                        ON DELETE CASCADE,
                        
                    CONSTRAINT fk_group_members_added_by_user_id 
                        FOREIGN KEY (added_by_user_id) 
                        REFERENCES users(id) 
                        ON DELETE CASCADE,
                    
                    -- Unique constraint to prevent duplicate memberships
                    CONSTRAINT uc_unique_group_member 
                        UNIQUE (group_id, user_id)
                );
            """)
            print("   ✅ Group members table created")
            
            # Create indexes
            print("📇 Creating indexes...")
            
            # Groups table indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_creator ON groups(creator_user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_created_at ON groups(created_at);")
            
            # Group members table indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_added_by ON group_members(added_by_user_id);")
            
            print("   ✅ Indexes created")
            
            # Create trigger function
            print("⚙️ Creating trigger function...")
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_groups_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            print("   ✅ Trigger function created")
            
            # Create trigger
            cursor.execute("""
                DROP TRIGGER IF EXISTS trigger_groups_updated_at ON groups;
                CREATE TRIGGER trigger_groups_updated_at
                    BEFORE UPDATE ON groups
                    FOR EACH ROW
                    EXECUTE FUNCTION update_groups_updated_at();
            """)
            print("   ✅ Trigger created")
            
            # Verify tables exist
            print("🔍 Verifying tables...")
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('groups', 'group_members')
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'groups' in tables and 'group_members' in tables:
                print("   ✅ Both tables verified successfully")
                
                # Check constraints
                cursor.execute("""
                    SELECT constraint_name, table_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name IN ('groups', 'group_members')
                    AND constraint_type = 'FOREIGN KEY'
                    ORDER BY table_name;
                """)
                
                constraints = cursor.fetchall()
                print(f"   ✅ {len(constraints)} foreign key constraints verified")
                
                conn.commit()
                print("\n🎉 Groups tables successfully synced to staging!")
                return True
            else:
                print(f"   ❌ Verification failed. Found tables: {tables}")
                return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function"""
    if create_groups_tables_on_staging():
        print("\n✅ SYNC COMPLETE!")
        print("=" * 20)
        print("📋 Groups tables are now available on staging")
        print("🔗 Group Chats functionality ready for testing")
        print("\n💡 Next steps:")
        print("   1. Test Group Chats functionality on staging")
        print("   2. Verify all CRUD operations work")
        print("   3. Run: python data/dbschema/compare_schemas_dbschema.py")
        print("   4. Deploy to production when ready")
        return 0
    else:
        print("\n❌ SYNC FAILED!")
        print("Check error messages above and retry.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 