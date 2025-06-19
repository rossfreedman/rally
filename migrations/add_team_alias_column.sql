-- Add team_alias Column to Teams Table
-- Date: 2024-12-19
-- Description: Add team_alias field for flexible team display names

BEGIN;

-- Add team_alias column
ALTER TABLE teams ADD COLUMN IF NOT EXISTS team_alias VARCHAR(255);

-- Add comment explaining the purpose
COMMENT ON COLUMN teams.team_alias IS 'Optional display alias for team (e.g., "Series 22" instead of "Chicago - 22")';

-- Create index for team_alias searches
CREATE INDEX IF NOT EXISTS idx_teams_team_alias ON teams(team_alias) WHERE team_alias IS NOT NULL;

COMMIT; 