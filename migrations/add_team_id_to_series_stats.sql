-- Add team_id to Series Stats Table
-- Date: 2024-12-19
-- Description: Add team_id foreign key to series_stats table for proper team statistics

BEGIN;

-- Add team_id column to series_stats table
ALTER TABLE series_stats ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_series_stats_team_id ON series_stats(team_id);

-- Add comment
COMMENT ON COLUMN series_stats.team_id IS 'Foreign key reference to teams table';

COMMIT; 