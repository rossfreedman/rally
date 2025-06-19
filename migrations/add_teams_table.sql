-- Add Teams Table
-- Date: 2024-12-19
-- Description: Create teams table to normalize team references

BEGIN;

-- Create teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    club_id INTEGER NOT NULL REFERENCES clubs(id),
    series_id INTEGER NOT NULL REFERENCES series(id),
    league_id INTEGER NOT NULL REFERENCES leagues(id),
    team_name VARCHAR(255) NOT NULL,
    external_team_id VARCHAR(255), -- For future ETL mapping
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one team per club/series/league combination
    UNIQUE(club_id, series_id, league_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_teams_club_id ON teams(club_id);
CREATE INDEX IF NOT EXISTS idx_teams_series_id ON teams(series_id);
CREATE INDEX IF NOT EXISTS idx_teams_league_id ON teams(league_id);
CREATE INDEX IF NOT EXISTS idx_teams_active ON teams(is_active) WHERE is_active = TRUE;

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_teams_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_teams_updated_at ON teams;
CREATE TRIGGER update_teams_updated_at 
    BEFORE UPDATE ON teams 
    FOR EACH ROW EXECUTE FUNCTION update_teams_updated_at_column();

-- Add helpful comments
COMMENT ON TABLE teams IS 'Team entities representing club participation in a series within a league';
COMMENT ON COLUMN teams.team_name IS 'Display name like "Tennaqua - Chicago 9"';
COMMENT ON COLUMN teams.external_team_id IS 'External system team ID for ETL mapping';

COMMIT; 