-- Add team_id columns to Schedule Table
-- Date: 2024-12-19
-- Description: Add home_team_id and away_team_id foreign keys to schedule table

BEGIN;

-- Add home_team_id and away_team_id columns to schedule table
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS home_team_id INTEGER REFERENCES teams(id);
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS away_team_id INTEGER REFERENCES teams(id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_schedule_home_team_id ON schedule(home_team_id);
CREATE INDEX IF NOT EXISTS idx_schedule_away_team_id ON schedule(away_team_id);

-- Add comments
COMMENT ON COLUMN schedule.home_team_id IS 'Foreign key reference to teams table for home team';
COMMENT ON COLUMN schedule.away_team_id IS 'Foreign key reference to teams table for away team';

COMMIT; 