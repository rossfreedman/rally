-- Comprehensive Team Format Mapping System
-- This table handles all possible user-facing format variations to database format mappings

CREATE TABLE IF NOT EXISTS team_format_mappings (
    id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,
    user_input_format VARCHAR(100) NOT NULL,
    database_series_format VARCHAR(100) NOT NULL,
    mapping_type VARCHAR(50) DEFAULT 'series_mapping',
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure no duplicate mappings per league
    UNIQUE(league_id, user_input_format),
    
    -- Foreign key to leagues table
    CONSTRAINT fk_team_format_mappings_league 
        FOREIGN KEY (league_id) 
        REFERENCES leagues(league_id) 
        ON DELETE CASCADE
);

-- Create indexes for fast lookups
CREATE INDEX idx_team_format_mappings_lookup ON team_format_mappings(league_id, user_input_format);
CREATE INDEX idx_team_format_mappings_active ON team_format_mappings(league_id, is_active);

-- CNSWPL Comprehensive Mappings (Chicago North Shore Women's Platform Tennis League)
INSERT INTO team_format_mappings (league_id, user_input_format, database_series_format, description) VALUES
-- Numeric series mappings (S1, S2, etc.)
('CNSWPL', 'Division 1', 'S1', 'Division format to short series format'),
('CNSWPL', 'Division 2', 'S2', 'Division format to short series format'),
('CNSWPL', 'Division 3', 'S3', 'Division format to short series format'),
('CNSWPL', 'Division 4', 'S4', 'Division format to short series format'),
('CNSWPL', 'Division 5', 'S5', 'Division format to short series format'),
('CNSWPL', 'Division 6', 'S6', 'Division format to short series format'),
('CNSWPL', 'Division 7', 'S7', 'Division format to short series format'),
('CNSWPL', 'Division 8', 'S8', 'Division format to short series format'),
('CNSWPL', 'Division 9', 'S9', 'Division format to short series format'),
('CNSWPL', 'Division 10', 'S10', 'Division format to short series format'),
('CNSWPL', 'Division 11', 'S11', 'Division format to short series format'),
('CNSWPL', 'Division 12', 'S12', 'Division format to short series format'),
('CNSWPL', 'Division 13', 'S13', 'Division format to short series format'),
('CNSWPL', 'Division 14', 'S14', 'Division format to short series format'),
('CNSWPL', 'Division 15', 'S15', 'Division format to short series format'),
('CNSWPL', 'Division 16', 'S16', 'Division format to short series format'),
('CNSWPL', 'Division 17', 'S17', 'Division format to short series format'),

-- Series format mappings
('CNSWPL', 'Series 1', 'S1', 'Long series format to short series format'),
('CNSWPL', 'Series 2', 'S2', 'Long series format to short series format'),
('CNSWPL', 'Series 3', 'S3', 'Long series format to short series format'),
('CNSWPL', 'Series 4', 'S4', 'Long series format to short series format'),
('CNSWPL', 'Series 5', 'S5', 'Long series format to short series format'),
('CNSWPL', 'Series 6', 'S6', 'Long series format to short series format'),
('CNSWPL', 'Series 7', 'S7', 'Long series format to short series format'),
('CNSWPL', 'Series 8', 'S8', 'Long series format to short series format'),
('CNSWPL', 'Series 9', 'S9', 'Long series format to short series format'),
('CNSWPL', 'Series 10', 'S10', 'Long series format to short series format'),
('CNSWPL', 'Series 11', 'S11', 'Long series format to short series format'),
('CNSWPL', 'Series 12', 'S12', 'Long series format to short series format'),
('CNSWPL', 'Series 13', 'S13', 'Long series format to short series format'),
('CNSWPL', 'Series 14', 'S14', 'Long series format to short series format'),
('CNSWPL', 'Series 15', 'S15', 'Long series format to short series format'),
('CNSWPL', 'Series 16', 'S16', 'Long series format to short series format'),
('CNSWPL', 'Series 17', 'S17', 'Long series format to short series format'),

-- Short numeric format mappings
('CNSWPL', '1', 'S1', 'Numeric only to short series format'),
('CNSWPL', '2', 'S2', 'Numeric only to short series format'),
('CNSWPL', '3', 'S3', 'Numeric only to short series format'),
('CNSWPL', '4', 'S4', 'Numeric only to short series format'),
('CNSWPL', '5', 'S5', 'Numeric only to short series format'),
('CNSWPL', '6', 'S6', 'Numeric only to short series format'),
('CNSWPL', '7', 'S7', 'Numeric only to short series format'),
('CNSWPL', '8', 'S8', 'Numeric only to short series format'),
('CNSWPL', '9', 'S9', 'Numeric only to short series format'),
('CNSWPL', '10', 'S10', 'Numeric only to short series format'),
('CNSWPL', '11', 'S11', 'Numeric only to short series format'),
('CNSWPL', '12', 'S12', 'Numeric only to short series format'),
('CNSWPL', '13', 'S13', 'Numeric only to short series format'),
('CNSWPL', '14', 'S14', 'Numeric only to short series format'),
('CNSWPL', '15', 'S15', 'Numeric only to short series format'),
('CNSWPL', '16', 'S16', 'Numeric only to short series format'),
('CNSWPL', '17', 'S17', 'Numeric only to short series format'),

-- Direct matches (identity mappings)
('CNSWPL', 'S1', 'S1', 'Direct match'),
('CNSWPL', 'S2', 'S2', 'Direct match'),
('CNSWPL', 'S3', 'S3', 'Direct match'),
('CNSWPL', 'S4', 'S4', 'Direct match'),
('CNSWPL', 'S5', 'S5', 'Direct match'),
('CNSWPL', 'S6', 'S6', 'Direct match'),
('CNSWPL', 'S7', 'S7', 'Direct match'),
('CNSWPL', 'S8', 'S8', 'Direct match'),
('CNSWPL', 'S9', 'S9', 'Direct match'),
('CNSWPL', 'S10', 'S10', 'Direct match'),
('CNSWPL', 'S11', 'S11', 'Direct match'),
('CNSWPL', 'S12', 'S12', 'Direct match'),
('CNSWPL', 'S13', 'S13', 'Direct match'),
('CNSWPL', 'S14', 'S14', 'Direct match'),
('CNSWPL', 'S15', 'S15', 'Direct match'),
('CNSWPL', 'S16', 'S16', 'Direct match'),
('CNSWPL', 'S17', 'S17', 'Direct match'),

-- Alphabetic series (SI = Series I)
('CNSWPL', 'Division I', 'SI', 'Division I to SI format'),
('CNSWPL', 'Series I', 'SI', 'Series I to SI format'),
('CNSWPL', 'I', 'SI', 'Letter I to SI format'),
('CNSWPL', 'SI', 'SI', 'Direct match'),

-- NSTF Mappings (North Shore Tennis Foundation)
('NSTF', 'Series 1', 'S1', 'Long series format to short format'),
('NSTF', 'Series 2A', 'S2A', 'Long series format to short format'),
('NSTF', 'Series 2B', 'S2B', 'Long series format to short format'),
('NSTF', 'Series 3', 'S3', 'Long series format to short format'),
('NSTF', 'Series A', 'SA', 'Long series format to short format'),

('NSTF', 'Division 1', 'S1', 'Division format to short format'),
('NSTF', 'Division 2A', 'S2A', 'Division format to short format'),
('NSTF', 'Division 2B', 'S2B', 'Division format to short format'),
('NSTF', 'Division 3', 'S3', 'Division format to short format'),
('NSTF', 'Division A', 'SA', 'Division format to short format'),

('NSTF', '1', 'S1', 'Numeric only to short format'),
('NSTF', '2A', 'S2A', 'Alphanumeric to short format'),
('NSTF', '2B', 'S2B', 'Alphanumeric to short format'),
('NSTF', '3', 'S3', 'Numeric only to short format'),
('NSTF', 'A', 'SA', 'Letter only to short format'),

('NSTF', 'S1', 'S1', 'Direct match'),
('NSTF', 'S2A', 'S2A', 'Direct match'),
('NSTF', 'S2B', 'S2B', 'Direct match'),
('NSTF', 'S3', 'S3', 'Direct match'),
('NSTF', 'SA', 'SA', 'Direct match'),

-- APTA Chicago Mappings (most complex with multiple formats)
('APTA_CHICAGO', 'Chicago 1', 'Chicago 1', 'Direct match'),
('APTA_CHICAGO', 'Chicago 2', 'Chicago 2', 'Direct match'),
('APTA_CHICAGO', 'Chicago 3', 'Chicago 3', 'Direct match'),
('APTA_CHICAGO', 'Chicago 4', 'Chicago 4', 'Direct match'),
('APTA_CHICAGO', 'Chicago 5', 'Chicago 5', 'Direct match'),
('APTA_CHICAGO', 'Chicago 6', 'Chicago 6', 'Direct match'),
('APTA_CHICAGO', 'Chicago 7', 'Chicago 7', 'Direct match'),
('APTA_CHICAGO', 'Chicago 8', 'Chicago 8', 'Direct match'),
('APTA_CHICAGO', 'Chicago 9', 'Chicago 9', 'Direct match'),
('APTA_CHICAGO', 'Chicago 10', 'Chicago 10', 'Direct match'),
('APTA_CHICAGO', 'Chicago 11', 'Chicago 11', 'Direct match'),
('APTA_CHICAGO', 'Chicago 12', 'Chicago 12', 'Direct match'),
('APTA_CHICAGO', 'Chicago 13', 'Chicago 13', 'Direct match'),
('APTA_CHICAGO', 'Chicago 14', 'Chicago 14', 'Direct match'),
('APTA_CHICAGO', 'Chicago 15', 'Chicago 15', 'Direct match'),
('APTA_CHICAGO', 'Chicago 16', 'Chicago 16', 'Direct match'),
('APTA_CHICAGO', 'Chicago 17', 'Chicago 17', 'Direct match'),
('APTA_CHICAGO', 'Chicago 18', 'Chicago 18', 'Direct match'),
('APTA_CHICAGO', 'Chicago 19', 'Chicago 19', 'Direct match'),
('APTA_CHICAGO', 'Chicago 20', 'Chicago 20', 'Direct match'),

-- Division format mappings for APTA Chicago
('APTA_CHICAGO', 'Division 6', 'Division 6', 'Direct match'),
('APTA_CHICAGO', 'Division 7', 'Division 7', 'Direct match'),
('APTA_CHICAGO', 'Division 9', 'Division 9', 'Direct match'),
('APTA_CHICAGO', 'Division 11', 'Division 11', 'Direct match'),
('APTA_CHICAGO', 'Division 13', 'Division 13', 'Direct match'),
('APTA_CHICAGO', 'Division 15', 'Division 15', 'Direct match'),
('APTA_CHICAGO', 'Division 17', 'Division 17', 'Direct match'),
('APTA_CHICAGO', 'Division 19', 'Division 19', 'Direct match'),

-- Short numeric mappings for APTA Chicago (defaulting to Chicago format)
('APTA_CHICAGO', '1', 'Chicago 1', 'Numeric to Chicago format'),
('APTA_CHICAGO', '2', 'Chicago 2', 'Numeric to Chicago format'),
('APTA_CHICAGO', '3', 'Chicago 3', 'Numeric to Chicago format'),
('APTA_CHICAGO', '4', 'Chicago 4', 'Numeric to Chicago format'),
('APTA_CHICAGO', '5', 'Chicago 5', 'Numeric to Chicago format'),
('APTA_CHICAGO', '6', 'Chicago 6', 'Numeric to Chicago format'),
('APTA_CHICAGO', '7', 'Chicago 7', 'Numeric to Chicago format'),
('APTA_CHICAGO', '8', 'Chicago 8', 'Numeric to Chicago format'),
('APTA_CHICAGO', '9', 'Chicago 9', 'Numeric to Chicago format'),
('APTA_CHICAGO', '10', 'Chicago 10', 'Numeric to Chicago format'),
('APTA_CHICAGO', '11', 'Chicago 11', 'Numeric to Chicago format'),
('APTA_CHICAGO', '12', 'Chicago 12', 'Numeric to Chicago format'),
('APTA_CHICAGO', '13', 'Chicago 13', 'Numeric to Chicago format'),
('APTA_CHICAGO', '14', 'Chicago 14', 'Numeric to Chicago format'),
('APTA_CHICAGO', '15', 'Chicago 15', 'Numeric to Chicago format'),
('APTA_CHICAGO', '16', 'Chicago 16', 'Numeric to Chicago format'),
('APTA_CHICAGO', '17', 'Chicago 17', 'Numeric to Chicago format'),
('APTA_CHICAGO', '18', 'Chicago 18', 'Numeric to Chicago format'),
('APTA_CHICAGO', '19', 'Chicago 19', 'Numeric to Chicago format'),
('APTA_CHICAGO', '20', 'Chicago 20', 'Numeric to Chicago format'),

-- SW (Southwest) format mappings for APTA Chicago  
('APTA_CHICAGO', 'S7 SW', 'S7 SW', 'Direct match'),
('APTA_CHICAGO', 'S9 SW', 'S9 SW', 'Direct match'),
('APTA_CHICAGO', 'S11 SW', 'S11 SW', 'Direct match'),
('APTA_CHICAGO', 'S13 SW', 'S13 SW', 'Direct match'),
('APTA_CHICAGO', 'S15 SW', 'S15 SW', 'Direct match'),
('APTA_CHICAGO', 'S17 SW', 'S17 SW', 'Direct match'),
('APTA_CHICAGO', 'S19 SW', 'S19 SW', 'Direct match'),
('APTA_CHICAGO', 'S21 SW', 'S21 SW', 'Direct match'),
('APTA_CHICAGO', 'S23 SW', 'S23 SW', 'Direct match'),
('APTA_CHICAGO', 'S25 SW', 'S25 SW', 'Direct match'),
('APTA_CHICAGO', 'S27 SW', 'S27 SW', 'Direct match'),
('APTA_CHICAGO', 'S29 SW', 'S29 SW', 'Direct match'),

-- CITA Basic Mappings (Complex tournament structure)
('CITA', 'Boys', 'SBoys', 'Boys division mapping'),
('CITA', 'Boys Division', 'SBoys', 'Boys division mapping'),
('CITA', 'Girls', 'SGirls', 'Girls division mapping'),  -- Assuming SGirls exists
('CITA', 'Girls Division', 'SGirls', 'Girls division mapping'),

-- Direct CITA matches for known formats
('CITA', 'SBoys', 'SBoys', 'Direct match'),
('CITA', 'S3.0 & Under Thur', 'S3.0 & Under Thur', 'Direct match'),
('CITA', 'S3.0 - 3.5 Singles Thur', 'S3.0 - 3.5 Singles Thur', 'Direct match'),
('CITA', 'S3.5 & Under Sat', 'S3.5 & Under Sat', 'Direct match'),
('CITA', 'S3.5 & Under Wed', 'S3.5 & Under Wed', 'Direct match'),
('CITA', 'S4.0 & Under Fri', 'S4.0 & Under Fri', 'Direct match'),
('CITA', 'S4.0 & Under Sat', 'S4.0 & Under Sat', 'Direct match'),
('CITA', 'S4.0 & Under Wed', 'S4.0 & Under Wed', 'Direct match'),
('CITA', 'S4.0 - 4.5 Singles Thur', 'S4.0 - 4.5 Singles Thur', 'Direct match'),
('CITA', 'S4.0 Singles Sun', 'S4.0 Singles Sun', 'Direct match'),
('CITA', 'S4.5 & Under Fri', 'S4.5 & Under Fri', 'Direct match'),
('CITA', 'S4.5 & Under Sat', 'S4.5 & Under Sat', 'Direct match'),
('CITA', 'S4.5 Singles Sun', 'S4.5 Singles Sun', 'Direct match'),
('CITA', 'SOpen Fri', 'SOpen Fri', 'Direct match')

ON CONFLICT (league_id, user_input_format) DO UPDATE SET 
    database_series_format = EXCLUDED.database_series_format,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- Add comments for documentation
COMMENT ON TABLE team_format_mappings IS 'Comprehensive mapping of user-facing series formats to database series formats for all leagues';
COMMENT ON COLUMN team_format_mappings.league_id IS 'League identifier (CNSWPL, NSTF, APTA_CHICAGO, CITA)';
COMMENT ON COLUMN team_format_mappings.user_input_format IS 'Format that users might enter or have in their session data';
COMMENT ON COLUMN team_format_mappings.database_series_format IS 'Actual series format as stored in the database';
COMMENT ON COLUMN team_format_mappings.mapping_type IS 'Type of mapping (series_mapping, team_mapping, etc.)';
COMMENT ON COLUMN team_format_mappings.description IS 'Human-readable description of this mapping'; 