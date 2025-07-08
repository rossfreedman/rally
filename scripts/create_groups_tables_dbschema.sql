-- =====================================================
-- Create Groups Tables for Rally Application
-- To run in DBSchema: Copy this entire script into the SQL Editor and execute
-- =====================================================

-- Drop tables if they exist (for clean recreation)
DROP TABLE IF EXISTS group_members CASCADE;
DROP TABLE IF EXISTS groups CASCADE;

-- Drop trigger function if it exists
DROP FUNCTION IF EXISTS update_groups_updated_at() CASCADE;

-- =====================================================
-- CREATE GROUPS TABLE
-- =====================================================

CREATE TABLE groups (
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

-- =====================================================
-- CREATE GROUP_MEMBERS TABLE
-- =====================================================

CREATE TABLE group_members (
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

-- =====================================================
-- CREATE INDEXES FOR PERFORMANCE
-- =====================================================

-- Groups table indexes
CREATE INDEX idx_groups_creator ON groups(creator_user_id);
CREATE INDEX idx_groups_name ON groups(name);
CREATE INDEX idx_groups_created_at ON groups(created_at);

-- Group members table indexes
CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user ON group_members(user_id);
CREATE INDEX idx_group_members_added_by ON group_members(added_by_user_id);

-- =====================================================
-- CREATE TRIGGER FUNCTION FOR UPDATED_AT
-- =====================================================

CREATE OR REPLACE FUNCTION update_groups_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- CREATE TRIGGER
-- =====================================================

CREATE TRIGGER trigger_groups_updated_at
    BEFORE UPDATE ON groups
    FOR EACH ROW
    EXECUTE FUNCTION update_groups_updated_at();

-- =====================================================
-- VERIFY TABLES WERE CREATED
-- =====================================================

-- Show table structures
\d groups;
\d group_members;

-- Show constraints
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name IN ('groups', 'group_members');

-- Show indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('groups', 'group_members')
ORDER BY tablename, indexname;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

SELECT 'Groups tables created successfully! 🎉' AS status; 