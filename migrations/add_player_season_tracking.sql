-- Add table for tracking player season statistics
-- Similar to availability but for season-long counts

CREATE TABLE IF NOT EXISTS player_season_tracking (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(255) NOT NULL,  -- tenniscores_player_id
    league_id INTEGER REFERENCES leagues(id),
    season_year INTEGER NOT NULL,     -- e.g., 2024, 2025
    forced_byes INTEGER DEFAULT 0,
    not_available INTEGER DEFAULT 0,
    injury INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one record per player per season per league
    UNIQUE(player_id, league_id, season_year)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_player_season_tracking_player_id ON player_season_tracking(player_id);
CREATE INDEX IF NOT EXISTS idx_player_season_tracking_league_season ON player_season_tracking(league_id, season_year);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_player_season_tracking_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_player_season_tracking_updated_at
    BEFORE UPDATE ON player_season_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_player_season_tracking_updated_at();

-- Insert comment for documentation
COMMENT ON TABLE player_season_tracking IS 'Tracks season-long statistics for players including forced byes, unavailability, and injury counts';
COMMENT ON COLUMN player_season_tracking.player_id IS 'References tenniscores_player_id from players table';
COMMENT ON COLUMN player_season_tracking.season_year IS 'Tennis season year (Aug-July seasons)';
COMMENT ON COLUMN player_season_tracking.forced_byes IS 'Number of forced byes for this player this season';
COMMENT ON COLUMN player_season_tracking.not_available IS 'Number of times player was not available this season';
COMMENT ON COLUMN player_season_tracking.injury IS 'Number of injury-related absences this season'; 