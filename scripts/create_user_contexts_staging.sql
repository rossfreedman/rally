-- Create user_contexts table on staging Railway
-- ===============================================
-- Run this via Railway SSH or psql connection

-- First check if table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'user_contexts'
);

-- Create user_contexts table
CREATE TABLE IF NOT EXISTS user_contexts (
    user_id INTEGER NOT NULL,
    league_id INTEGER,
    team_id INTEGER,
    series_id INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT user_contexts_pkey PRIMARY KEY (user_id),
    CONSTRAINT fk_user_contexts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_contexts_league FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE SET NULL,
    CONSTRAINT fk_user_contexts_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL,
    CONSTRAINT user_contexts_series_id_fkey FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET NULL
);

-- Grant permissions to all users
GRANT SELECT ON user_contexts TO PUBLIC;
GRANT INSERT ON user_contexts TO PUBLIC; 
GRANT UPDATE ON user_contexts TO PUBLIC;
GRANT DELETE ON user_contexts TO PUBLIC;

-- Verify table creation
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'user_contexts'
ORDER BY ordinal_position;

-- Test table access
SELECT COUNT(*) as record_count FROM user_contexts;

-- Show confirmation
SELECT 'user_contexts table created successfully!' as status;
