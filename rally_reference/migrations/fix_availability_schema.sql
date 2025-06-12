-- Fix availability schema without losing data
BEGIN;

-- Drop the table if it exists and recreate with correct schema
DROP TABLE IF EXISTS player_availability;

CREATE TABLE player_availability (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    match_date DATE NOT NULL,
    availability_status INTEGER NOT NULL DEFAULT 3, -- 1: available, 2: unavailable, 3: not sure
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    series_id INTEGER NOT NULL REFERENCES series(id),
    UNIQUE(player_name, match_date, series_id),
    CONSTRAINT valid_availability_status CHECK (availability_status IN (1, 2, 3))
);

-- Create index for better performance
CREATE INDEX idx_player_availability ON player_availability(player_name, match_date, series_id);

COMMIT; 