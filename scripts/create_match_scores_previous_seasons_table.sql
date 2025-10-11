-- Create match_scores_previous_seasons table
-- This table mirrors match_scores but includes a season identifier column

CREATE TABLE IF NOT EXISTS match_scores_previous_seasons (
    id SERIAL PRIMARY KEY,
    league_id INTEGER REFERENCES leagues(id),
    match_date DATE,
    home_team TEXT,
    away_team TEXT,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_player_1_id TEXT,
    home_player_2_id TEXT,
    away_player_1_id TEXT,
    away_player_2_id TEXT,
    scores TEXT,
    winner TEXT CHECK (winner IN ('home', 'away', 'tie')),
    tenniscores_match_id TEXT,
    season VARCHAR(20),  -- Season identifier like "2024-2025"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_league_id ON match_scores_previous_seasons(league_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_match_date ON match_scores_previous_seasons(match_date);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_home_team_id ON match_scores_previous_seasons(home_team_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_away_team_id ON match_scores_previous_seasons(away_team_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_season ON match_scores_previous_seasons(season);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_tenniscores_match_id ON match_scores_previous_seasons(tenniscores_match_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_home_player_1_id ON match_scores_previous_seasons(home_player_1_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_home_player_2_id ON match_scores_previous_seasons(home_player_2_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_away_player_1_id ON match_scores_previous_seasons(away_player_1_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_away_player_2_id ON match_scores_previous_seasons(away_player_2_id);

-- Create composite index for player queries
CREATE INDEX IF NOT EXISTS idx_match_scores_prev_players_season ON match_scores_previous_seasons(season, home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id);

COMMENT ON TABLE match_scores_previous_seasons IS 'Match scores from previous seasons - mirrors match_scores with season identifier';
COMMENT ON COLUMN match_scores_previous_seasons.season IS 'Season identifier in format YYYY-YYYY (e.g., 2024-2025)';

