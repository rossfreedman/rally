-- Migration: Enhanced Team Switching System
-- ==========================================
-- Add UserContext table and migrate from is_primary to dynamic context switching

BEGIN;

-- 1. Create UserContext table
CREATE TABLE IF NOT EXISTS user_contexts (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    active_league_id INTEGER REFERENCES leagues(id),
    active_team_id INTEGER REFERENCES teams(id),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_user_contexts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_contexts_league FOREIGN KEY (active_league_id) REFERENCES leagues(id),
    CONSTRAINT fk_user_contexts_team FOREIGN KEY (active_team_id) REFERENCES teams(id)
);

-- 2. Create indexes for performance
CREATE INDEX idx_user_contexts_league ON user_contexts (active_league_id);
CREATE INDEX idx_user_contexts_team ON user_contexts (active_team_id);
CREATE INDEX idx_user_contexts_updated ON user_contexts (last_updated);

-- 3. Migrate existing primary associations to user contexts
-- For users with primary associations, set their active context
INSERT INTO user_contexts (user_id, active_league_id, active_team_id, last_updated)
SELECT DISTINCT
    upa.user_id,
    p.league_id as active_league_id,
    p.team_id as active_team_id,
    CURRENT_TIMESTAMP as last_updated
FROM user_player_associations upa
JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
WHERE upa.is_primary = TRUE
  AND p.is_active = TRUE
  AND p.team_id IS NOT NULL
ON CONFLICT (user_id) DO UPDATE SET
    active_league_id = EXCLUDED.active_league_id,
    active_team_id = EXCLUDED.active_team_id,
    last_updated = EXCLUDED.last_updated;

-- 4. For users without team assignments but with primary players, set league context
INSERT INTO user_contexts (user_id, active_league_id, last_updated)
SELECT DISTINCT
    upa.user_id,
    p.league_id as active_league_id,
    CURRENT_TIMESTAMP as last_updated
FROM user_player_associations upa
JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
LEFT JOIN user_contexts uc ON upa.user_id = uc.user_id
WHERE upa.is_primary = TRUE
  AND p.is_active = TRUE
  AND uc.user_id IS NULL  -- Only users not already in user_contexts
ON CONFLICT (user_id) DO NOTHING;

-- 5. Drop is_primary column from user_player_associations
-- First check if the column exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_player_associations' 
        AND column_name = 'is_primary'
    ) THEN
        -- Drop the is_primary column
        ALTER TABLE user_player_associations DROP COLUMN is_primary;
        RAISE NOTICE 'Dropped is_primary column from user_player_associations';
    ELSE
        RAISE NOTICE 'is_primary column does not exist in user_player_associations';
    END IF;
END $$;

-- 6. Update primary key constraint if needed
-- The primary key should be (user_id, tenniscores_player_id)
DO $$
BEGIN
    -- Check if we need to update the primary key
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'user_player_associations'
        AND tc.constraint_type = 'PRIMARY KEY'
        AND kcu.column_name IN ('user_id', 'tenniscores_player_id')
        GROUP BY tc.constraint_name
        HAVING COUNT(*) = 2
    ) THEN
        -- Drop existing primary key if it exists
        ALTER TABLE user_player_associations DROP CONSTRAINT IF EXISTS user_player_associations_pkey;
        
        -- Add new primary key
        ALTER TABLE user_player_associations ADD CONSTRAINT user_player_associations_pkey 
        PRIMARY KEY (user_id, tenniscores_player_id);
        
        RAISE NOTICE 'Updated primary key for user_player_associations';
    ELSE
        RAISE NOTICE 'Primary key for user_player_associations already correct';
    END IF;
END $$;

COMMIT;

-- Verification queries
SELECT 'USER CONTEXTS CREATED' as status, COUNT(*) as count FROM user_contexts;

SELECT 'SAMPLE USER CONTEXTS' as status;
SELECT 
    u.email,
    uc.active_league_id,
    l.league_name,
    uc.active_team_id,
    t.team_name
FROM user_contexts uc
JOIN users u ON uc.user_id = u.id
LEFT JOIN leagues l ON uc.active_league_id = l.id
LEFT JOIN teams t ON uc.active_team_id = t.id
ORDER BY u.email
LIMIT 5;

SELECT 'MIGRATION COMPLETE' as status; 