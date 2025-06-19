-- Fix Polls Team ID Type
-- Created: 2024-06-19
-- Description: Change team_id column from INTEGER to TEXT to support string team identifiers like "Tennaqua-Chicago_9"

-- First, update any existing NULL team_id values to avoid issues
UPDATE polls SET team_id = NULL WHERE team_id IS NULL;

-- Change the team_id column type from INTEGER to TEXT
ALTER TABLE polls ALTER COLUMN team_id TYPE TEXT USING team_id::TEXT;

-- Update the comment to reflect the new usage
COMMENT ON COLUMN polls.team_id IS 'Team identifier string in format "Club-Series" (e.g., "Tennaqua-Chicago_9")';

-- The index on team_id should still work with TEXT type
-- But let's recreate it to be safe
DROP INDEX IF EXISTS idx_polls_team_id;
CREATE INDEX idx_polls_team_id ON polls(team_id); 