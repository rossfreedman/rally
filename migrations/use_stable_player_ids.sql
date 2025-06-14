-- Migration: Use Stable Player Identifiers
-- =========================================
-- This changes user_player_associations to use tenniscores_player_id
-- instead of the auto-generated player.id

BEGIN;

-- 1. Add new columns for stable identifiers
ALTER TABLE user_player_associations 
ADD COLUMN tenniscores_player_id VARCHAR(255),
ADD COLUMN league_id INTEGER REFERENCES leagues(id);

-- 2. Populate new columns from existing relationships (if data exists)
UPDATE user_player_associations upa
SET 
    tenniscores_player_id = p.tenniscores_player_id,
    league_id = p.league_id
FROM players p
WHERE upa.player_id = p.id;

-- 3. Create new unique constraint
ALTER TABLE user_player_associations
ADD CONSTRAINT unique_user_player_league 
UNIQUE (user_id, tenniscores_player_id, league_id);

-- 4. Drop old foreign key constraint
ALTER TABLE user_player_associations
DROP CONSTRAINT user_player_associations_player_id_fkey;

-- 5. Drop old primary key and player_id column
ALTER TABLE user_player_associations
DROP CONSTRAINT user_player_associations_pkey,
DROP COLUMN player_id;

-- 6. Create new primary key
ALTER TABLE user_player_associations
ADD PRIMARY KEY (user_id, tenniscores_player_id, league_id);

-- 7. Add NOT NULL constraints
ALTER TABLE user_player_associations
ALTER COLUMN tenniscores_player_id SET NOT NULL,
ALTER COLUMN league_id SET NOT NULL;

-- 8. Create indexes
CREATE INDEX idx_upa_tenniscores_player_id ON user_player_associations (tenniscores_player_id);
CREATE INDEX idx_upa_league_id ON user_player_associations (league_id);

COMMIT;

-- Note: You'll also need to update your application code to join using:
-- JOIN user_player_associations upa ON upa.tenniscores_player_id = p.tenniscores_player_id 
--   AND upa.league_id = p.league_id
-- instead of:
-- JOIN user_player_associations upa ON upa.player_id = p.id 