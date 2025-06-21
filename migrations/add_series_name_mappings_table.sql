-- Add series name mappings table for flexible league naming conventions
-- This allows each league to have their own series naming patterns

CREATE TABLE IF NOT EXISTS series_name_mappings (
    id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    user_series_name VARCHAR(100) NOT NULL,
    database_series_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure no duplicate mappings per league
    UNIQUE(league_id, user_series_name),
    
    -- Foreign key to leagues table
    CONSTRAINT fk_series_mappings_league 
        FOREIGN KEY (league_id) 
        REFERENCES leagues(league_id) 
        ON DELETE CASCADE
);

-- Create index for fast lookups
CREATE INDEX idx_series_mappings_lookup ON series_name_mappings(league_id, user_series_name);

-- Insert known mappings for existing leagues
INSERT INTO series_name_mappings (league_id, user_series_name, database_series_name) VALUES
-- CNSWPL mappings (Division X -> Series X)
('CNSWPL', 'Division 1', 'Series 1'),
('CNSWPL', 'Division 2', 'Series 2'),
('CNSWPL', 'Division 3', 'Series 3'),
('CNSWPL', 'Division 4', 'Series 4'),
('CNSWPL', 'Division 5', 'Series 5'),
('CNSWPL', 'Division 6', 'Series 6'),
('CNSWPL', 'Division 7', 'Series 7'),
('CNSWPL', 'Division 8', 'Series 8'),
('CNSWPL', 'Division 9', 'Series 9'),
('CNSWPL', 'Division 10', 'Series 10'),
('CNSWPL', 'Division 11', 'Series 11'),
('CNSWPL', 'Division 12', 'Series 12'),
('CNSWPL', 'Division 13', 'Series 13'),
('CNSWPL', 'Division 14', 'Series 14'),
('CNSWPL', 'Division 15', 'Series 15'),
('CNSWPL', 'Division 16', 'Series 16'),
('CNSWPL', 'Division 17', 'Series 17'),
('CNSWPL', 'Division A', 'Series A'),
('CNSWPL', 'Division B', 'Series B'),
('CNSWPL', 'Division C', 'Series C'),
('CNSWPL', 'Division D', 'Series D'),
('CNSWPL', 'Division E', 'Series E'),
('CNSWPL', 'Division F', 'Series F'),
('CNSWPL', 'Division G', 'Series G'),
('CNSWPL', 'Division H', 'Series H'),
('CNSWPL', 'Division I', 'Series I'),
('CNSWPL', 'Division J', 'Series J'),
('CNSWPL', 'Division K', 'Series K'),
('CNSWPL', 'Division SN', 'Series SN'),

-- NSTF mappings (Series X -> SX)
('NSTF', 'Series 1', 'S1'),
('NSTF', 'Series 2A', 'S2A'),
('NSTF', 'Series 2B', 'S2B'),
('NSTF', 'Series 3', 'S3'),
('NSTF', 'Series A', 'SA'),

-- APTA_CHICAGO mappings (if needed - to be populated based on actual data)
-- ('APTA_CHICAGO', 'user_format', 'db_format'),

-- CITA mappings (if needed - to be populated based on actual data)
-- ('CITA', 'user_format', 'db_format')

ON CONFLICT (league_id, user_series_name) DO NOTHING;

COMMENT ON TABLE series_name_mappings IS 'Maps user-facing series names to database series names for each league';
COMMENT ON COLUMN series_name_mappings.league_id IS 'League identifier (CNSWPL, NSTF, etc.)';
COMMENT ON COLUMN series_name_mappings.user_series_name IS 'Series name as it appears in user session data';
COMMENT ON COLUMN series_name_mappings.database_series_name IS 'Series name as stored in database'; 