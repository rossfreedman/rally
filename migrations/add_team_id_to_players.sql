-- Add team_id to Players Table
-- Date: 2024-12-19
-- Description: Add team_id foreign key to players table for proper team relationships

BEGIN;

-- Add team_id column to players table
ALTER TABLE players ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id);

-- Add comment
COMMENT ON COLUMN players.team_id IS 'Foreign key reference to teams table';

COMMIT; 