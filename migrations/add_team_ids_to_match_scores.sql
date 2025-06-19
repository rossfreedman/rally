-- Add team_id columns to Match Scores Table
-- Date: 2024-12-19
-- Description: Add home_team_id and away_team_id foreign keys to match_scores table

BEGIN;

-- Add home_team_id and away_team_id columns to match_scores table
ALTER TABLE match_scores ADD COLUMN IF NOT EXISTS home_team_id INTEGER REFERENCES teams(id);
ALTER TABLE match_scores ADD COLUMN IF NOT EXISTS away_team_id INTEGER REFERENCES teams(id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_match_scores_home_team_id ON match_scores(home_team_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_away_team_id ON match_scores(away_team_id);

-- Add comments
COMMENT ON COLUMN match_scores.home_team_id IS 'Foreign key reference to teams table for home team';
COMMENT ON COLUMN match_scores.away_team_id IS 'Foreign key reference to teams table for away team';

COMMIT; 