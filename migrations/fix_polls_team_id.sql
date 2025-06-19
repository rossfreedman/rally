-- Fix polls table team_id to proper foreign key
-- Date: 2024-12-19
-- Description: Convert polls.team_id from TEXT to INTEGER foreign key

BEGIN;

-- First, clear any existing data in team_id since it's currently string format
UPDATE polls SET team_id = NULL WHERE team_id IS NOT NULL;

-- Change team_id column type from TEXT to INTEGER
ALTER TABLE polls ALTER COLUMN team_id TYPE INTEGER USING NULL;

-- Add foreign key constraint to teams table
ALTER TABLE polls ADD CONSTRAINT fk_polls_team_id FOREIGN KEY (team_id) REFERENCES teams(id);

-- Recreate the index (it may have been dropped during type change)
DROP INDEX IF EXISTS idx_polls_team_id;
CREATE INDEX idx_polls_team_id ON polls(team_id);

-- Update comment
COMMENT ON COLUMN polls.team_id IS 'Foreign key reference to teams table (INTEGER)';

COMMIT; 