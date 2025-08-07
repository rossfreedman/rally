-- Manual Staging Schema Sync
-- This script adds the missing columns to staging to sync with production

-- Add missing columns to lineup_escrow table
ALTER TABLE lineup_escrow 
ADD COLUMN IF NOT EXISTS recipient_team_id INTEGER REFERENCES teams(id);

ALTER TABLE lineup_escrow 
ADD COLUMN IF NOT EXISTS initiator_team_id INTEGER REFERENCES teams(id);

-- Add missing column to user_player_associations table
ALTER TABLE user_player_associations 
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE;

-- Add missing columns to match_scores table
ALTER TABLE match_scores 
ADD COLUMN IF NOT EXISTS match_id VARCHAR(255);

ALTER TABLE match_scores 
ADD COLUMN IF NOT EXISTS tenniscores_match_id VARCHAR(255);

-- Add missing columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS notifications_hidden BOOLEAN DEFAULT FALSE;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_lineup_escrow_recipient_team ON lineup_escrow(recipient_team_id);
CREATE INDEX IF NOT EXISTS idx_lineup_escrow_initiator_team ON lineup_escrow(initiator_team_id);
CREATE INDEX IF NOT EXISTS idx_user_player_associations_primary ON user_player_associations(is_primary);
CREATE INDEX IF NOT EXISTS idx_match_scores_match_id ON match_scores(match_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_tenniscores_match_id ON match_scores(tenniscores_match_id);
CREATE INDEX IF NOT EXISTS idx_users_team_id ON users(team_id);
CREATE INDEX IF NOT EXISTS idx_users_notifications_hidden ON users(notifications_hidden);

-- Update alembic version to match production
UPDATE alembic_version SET version_num = 'sync_all_env_001' WHERE version_num = 'c28892a55e1d';

-- Verify the changes
SELECT 'lineup_escrow columns' as table_name, 
       COUNT(*) as column_count 
FROM information_schema.columns 
WHERE table_name = 'lineup_escrow' 
  AND column_name IN ('recipient_team_id', 'initiator_team_id');

SELECT 'user_player_associations is_primary' as check_name,
       COUNT(*) as exists 
FROM information_schema.columns 
WHERE table_name = 'user_player_associations' 
  AND column_name = 'is_primary';

SELECT 'users columns' as table_name,
       COUNT(*) as column_count 
FROM information_schema.columns 
WHERE table_name = 'users' 
  AND column_name IN ('team_id', 'notifications_hidden');

SELECT 'alembic_version' as check_name, version_num FROM alembic_version;
