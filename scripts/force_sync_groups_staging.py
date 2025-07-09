#!/usr/bin/env python3
"""
Force Sync Groups Tables to Staging (Robust)
===========================================

This script forcibly creates the groups tables on staging with retries and better error handling.
"""

import os
import sys
import time
import psycopg2
from psycopg2 import sql

def create_groups_tables_robust():
    """Create groups tables with robust error handling and retries"""
    print("🚀 Force Syncing Groups Tables to Staging")
    print("=" * 50)
    
    # Use the staging DATABASE_PUBLIC_URL
    staging_url = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        print(f"\n🔄 Attempt {attempt + 1}/{max_retries}")
        
        try:
            # Create connection with timeout settings
            conn = psycopg2.connect(
                staging_url,
                connect_timeout=30,
                application_name='groups_migration'
            )
            
            print("✅ Connected to staging database")
            
            with conn.cursor() as cursor:
                print("📄 Executing groups table creation...")
                
                # Drop existing tables if they exist (for clean recreation)
                print("   🗑️  Dropping existing tables...")
                cursor.execute("DROP TABLE IF EXISTS group_members CASCADE;")
                cursor.execute("DROP TABLE IF EXISTS groups CASCADE;")
                cursor.execute("DROP FUNCTION IF EXISTS update_groups_updated_at() CASCADE;")
                
                # Create groups table
                print("   📝 Creating groups table...")
                cursor.execute("""
                    CREATE TABLE groups (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        creator_user_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        
                        CONSTRAINT fk_groups_creator_user_id 
                            FOREIGN KEY (creator_user_id) 
                            REFERENCES users(id) 
                            ON DELETE CASCADE
                    );
                """)
                
                # Create group_members table
                print("   📝 Creating group_members table...")
                cursor.execute("""
                    CREATE TABLE group_members (
                        id SERIAL PRIMARY KEY,
                        group_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        added_by_user_id INTEGER NOT NULL,
                        
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
                        
                        CONSTRAINT uc_unique_group_member 
                            UNIQUE (group_id, user_id)
                    );
                """)
                
                # Create indexes
                print("   📇 Creating indexes...")
                indexes = [
                    "CREATE INDEX idx_groups_creator ON groups(creator_user_id);",
                    "CREATE INDEX idx_groups_name ON groups(name);", 
                    "CREATE INDEX idx_groups_created_at ON groups(created_at);",
                    "CREATE INDEX idx_group_members_group ON group_members(group_id);",
                    "CREATE INDEX idx_group_members_user ON group_members(user_id);",
                    "CREATE INDEX idx_group_members_added_by ON group_members(added_by_user_id);"
                ]
                
                for index_sql in indexes:
                    cursor.execute(index_sql)
                
                # Create trigger function
                print("   ⚙️ Creating trigger function...")
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION update_groups_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                # Create trigger
                print("   ⚙️ Creating trigger...")
                cursor.execute("""
                    CREATE TRIGGER trigger_groups_updated_at
                        BEFORE UPDATE ON groups
                        FOR EACH ROW
                        EXECUTE FUNCTION update_groups_updated_at();
                """)
                
                # Verify tables exist
                print("   🔍 Verifying tables...")
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('groups', 'group_members')
                    ORDER BY table_name;
                """)
                
                tables = [row[0] for row in cursor.fetchall()]
                
                if 'groups' in tables and 'group_members' in tables:
                    print("   ✅ Tables verified successfully")
                    
                    # Test a simple insert to make sure it works
                    print("   🧪 Testing table functionality...")
                    cursor.execute("SELECT COUNT(*) FROM groups;")
                    count = cursor.fetchone()[0]
                    print(f"   ✅ Groups table accessible (current count: {count})")
                    
                    conn.commit()
                    print("\n🎉 Groups tables created successfully!")
                    
                    conn.close()
                    return True
                else:
                    print(f"   ❌ Verification failed. Found tables: {tables}")
                    conn.rollback()
                    conn.close()
                    continue
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            print(f"   ❌ Connection error: {error_msg}")
            
            if "timeout" in error_msg.lower():
                print("   🕒 Connection timeout - will retry...")
            elif "connection refused" in error_msg.lower():
                print("   🚫 Connection refused - check if database is running...")
            
            if attempt < max_retries - 1:
                print(f"   ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
            
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            if attempt < max_retries - 1:
                print(f"   ⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            continue
    
    print(f"\n❌ Failed after {max_retries} attempts")
    return False

def main():
    """Main function"""
    if create_groups_tables_robust():
        print("\n✅ SUCCESS!")
        print("=" * 30)
        print("🎯 Groups tables are now live on staging")
        print("🔗 Group Chats functionality should work")
        print("\n💡 Next: Test the Group Chats page on staging:")
        print("   https://rally-staging.up.railway.app/mobile/my-groups")
        return 0
    else:
        print("\n❌ FAILED!")
        print("Check error messages above.")
        print("Try again or contact Railway support if connection issues persist.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 