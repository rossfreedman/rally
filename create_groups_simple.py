import os
import psycopg2

# Get database URL from environment (will be provided by Railway)
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("No DATABASE_URL found")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    print("Creating groups table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            creator_user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_groups_creator_user_id 
                FOREIGN KEY (creator_user_id) 
                REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    
    print("Creating group_members table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            id SERIAL PRIMARY KEY,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            added_by_user_id INTEGER NOT NULL,
            CONSTRAINT fk_group_members_group_id 
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            CONSTRAINT fk_group_members_user_id 
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_group_members_added_by_user_id 
                FOREIGN KEY (added_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT uc_unique_group_member UNIQUE (group_id, user_id)
        );
    """)
    
    print("Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_creator ON groups(creator_user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id);")
    
    conn.commit()
    print("SUCCESS: Groups tables created!")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM groups;")
    print(f"Groups table accessible: {cursor.fetchone()[0]} rows")
    
    conn.close()
    
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
