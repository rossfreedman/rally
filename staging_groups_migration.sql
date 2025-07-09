-- Create Groups Tables for Staging
-- ======================================

-- Create groups table
CREATE TABLE IF NOT EXISTS groups (
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

-- Create group_members table
CREATE TABLE IF NOT EXISTS group_members (
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_groups_creator ON groups(creator_user_id);
CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(name);
CREATE INDEX IF NOT EXISTS idx_groups_created_at ON groups(created_at);
CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_group_members_added_by ON group_members(added_by_user_id);

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION update_groups_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_groups_updated_at ON groups;
CREATE TRIGGER trigger_groups_updated_at
    BEFORE UPDATE ON groups
    FOR EACH ROW
    EXECUTE FUNCTION update_groups_updated_at();

-- Verify tables exist
SELECT 'Groups tables created successfully!' AS result; 