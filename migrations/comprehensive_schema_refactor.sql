-- ================================================================
-- Rally Database Schema Comprehensive Refactoring Migration
-- ================================================================
-- 
-- CRITICAL: This migration transforms the schema to support:
-- 1. Clean separation between users (authentication) and players (data)
-- 2. One-to-many user-to-player associations via junction table
-- 3. League-specific player records with integrated statistics
-- 4. Proper INTEGER foreign keys throughout the system
--
-- BACKUP REQUIRED: Take full database backup before running!
-- ================================================================

BEGIN;

-- ================================================================
-- PHASE 1: PREPARATION & SAFETY
-- ================================================================

-- Create backup reference for original users data before dropping columns
CREATE TEMP TABLE users_backup AS 
SELECT id, email, club_id, series_id, league_id, tenniscores_player_id 
FROM users;

-- Drop problematic foreign key constraints temporarily
-- (We'll recreate them with proper INTEGER references later)
DO $$ 
DECLARE
    r RECORD;
BEGIN
    -- Drop foreign key constraints that reference TEXT columns we're changing
    FOR r IN (
        SELECT conname, conrelid::regclass as table_name
        FROM pg_constraint 
        WHERE contype = 'f' 
        AND confrelid IN (
            SELECT oid FROM pg_class WHERE relname IN ('leagues', 'players')
        )
    ) LOOP
        EXECUTE 'ALTER TABLE ' || r.table_name || ' DROP CONSTRAINT IF EXISTS ' || r.conname;
    END LOOP;
END $$;

-- ================================================================
-- PHASE 2: ADD UPDATED_AT COLUMNS TO CORE TABLES
-- ================================================================

ALTER TABLE leagues 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE clubs 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE series 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Create trigger function for updating updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
DROP TRIGGER IF EXISTS update_leagues_updated_at ON leagues;
CREATE TRIGGER update_leagues_updated_at 
    BEFORE UPDATE ON leagues 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_clubs_updated_at ON clubs;
CREATE TRIGGER update_clubs_updated_at 
    BEFORE UPDATE ON clubs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_series_updated_at ON series;
CREATE TRIGGER update_series_updated_at 
    BEFORE UPDATE ON series 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- PHASE 3: TRANSFORM PLAYERS TABLE
-- ================================================================

-- Step 3.1: Remove authentication-related columns from players
ALTER TABLE players 
DROP COLUMN IF EXISTS password_hash,
DROP COLUMN IF EXISTS club_automation_password,
DROP COLUMN IF EXISTS is_admin,
DROP COLUMN IF EXISTS last_login;

-- Step 3.2: Add new statistical and status columns
ALTER TABLE players 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS pti NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS wins INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS losses INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS win_percentage NUMERIC(5,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS captain_status VARCHAR(50),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Step 3.3: Rename current_league_id to league_id
ALTER TABLE players 
RENAME COLUMN current_league_id TO league_id;

-- Step 3.4: Update NOT NULL constraints for required fields
ALTER TABLE players 
ALTER COLUMN first_name SET NOT NULL,
ALTER COLUMN last_name SET NOT NULL,
ALTER COLUMN league_id SET NOT NULL,
ALTER COLUMN club_id SET NOT NULL,
ALTER COLUMN series_id SET NOT NULL;

-- Step 3.5: Drop old unique constraint on tenniscores_player_id
ALTER TABLE players 
DROP CONSTRAINT IF EXISTS users_tenniscores_player_id_unique;

-- Step 3.6: Populate is_active from player_leagues where possible
UPDATE players 
SET is_active = pl.is_active
FROM player_leagues pl
WHERE players.id = pl.player_id
AND pl.is_active IS NOT NULL;

-- Step 3.7: Add new composite unique constraint
ALTER TABLE players 
ADD CONSTRAINT unique_player_in_league 
UNIQUE (tenniscores_player_id, league_id);

-- Step 3.8: Add updated_at trigger
DROP TRIGGER IF EXISTS update_players_updated_at ON players;
CREATE TRIGGER update_players_updated_at 
    BEFORE UPDATE ON players 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- PHASE 4: TRANSFORM USERS TABLE  
-- ================================================================

-- Remove redundant columns that now belong to players
ALTER TABLE users 
DROP COLUMN IF EXISTS club_id,
DROP COLUMN IF EXISTS series_id,
DROP COLUMN IF EXISTS league_id,
DROP COLUMN IF EXISTS tenniscores_player_id;

-- Drop associated index
DROP INDEX IF EXISTS idx_users_league_id;

-- ================================================================
-- PHASE 5: CREATE USER_PLAYER_ASSOCIATIONS TABLE
-- ================================================================

CREATE TABLE IF NOT EXISTS user_player_associations (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, player_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_upa_user_id ON user_player_associations (user_id);
CREATE INDEX IF NOT EXISTS idx_upa_player_id ON user_player_associations (player_id);
CREATE INDEX IF NOT EXISTS idx_upa_primary ON user_player_associations (user_id, is_primary) WHERE is_primary = TRUE;

-- ================================================================
-- PHASE 6: POPULATE USER_PLAYER_ASSOCIATIONS
-- ================================================================

-- Populate associations based on backed up user data
INSERT INTO user_player_associations (user_id, player_id, is_primary, created_at)
SELECT DISTINCT
    ub.id AS user_id,
    p.id AS player_id,
    TRUE AS is_primary,  -- Mark as primary association
    CURRENT_TIMESTAMP
FROM users_backup ub
JOIN players p ON p.tenniscores_player_id = ub.tenniscores_player_id
JOIN leagues l ON p.league_id = l.id AND l.id = ub.league_id
WHERE ub.tenniscores_player_id IS NOT NULL
ON CONFLICT (user_id, player_id) DO NOTHING;

-- ================================================================
-- PHASE 7: UPDATE FOREIGN KEYS IN OTHER TABLES
-- ================================================================

-- 7.1: Update match_scores table
ALTER TABLE match_scores ADD COLUMN IF NOT EXISTS new_league_id INTEGER;

UPDATE match_scores ms
SET new_league_id = l.id
FROM leagues l
WHERE ms.league_id = l.league_id;

ALTER TABLE match_scores 
DROP COLUMN IF EXISTS league_id,
RENAME COLUMN new_league_id TO league_id;

ALTER TABLE match_scores 
ADD CONSTRAINT fk_match_scores_league_id 
FOREIGN KEY (league_id) REFERENCES leagues(id);

-- 7.2: Update player_history table
ALTER TABLE player_history ADD COLUMN IF NOT EXISTS new_league_id INTEGER;
ALTER TABLE player_history ADD COLUMN IF NOT EXISTS new_player_id INTEGER;

-- Update league references
UPDATE player_history ph
SET new_league_id = l.id
FROM leagues l
WHERE ph.league_id = l.league_id;

-- Update player references (this is complex due to potential ambiguity)
-- We'll match on tenniscores_player_id and league
UPDATE player_history ph
SET new_player_id = p.id
FROM players p
JOIN leagues l ON p.league_id = l.id
WHERE ph.player_id = p.tenniscores_player_id
AND ph.new_league_id = p.league_id;

ALTER TABLE player_history 
DROP COLUMN IF EXISTS league_id,
DROP COLUMN IF EXISTS player_id,
RENAME COLUMN new_league_id TO league_id,
RENAME COLUMN new_player_id TO player_id;

ALTER TABLE player_history 
ADD CONSTRAINT fk_player_history_league_id 
FOREIGN KEY (league_id) REFERENCES leagues(id),
ADD CONSTRAINT fk_player_history_player_id 
FOREIGN KEY (player_id) REFERENCES players(id);

-- 7.3: Update schedule table
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS new_league_id INTEGER;

UPDATE schedule s
SET new_league_id = l.id
FROM leagues l
WHERE s.league_id = l.league_id;

ALTER TABLE schedule 
DROP COLUMN IF EXISTS league_id,
RENAME COLUMN new_league_id TO league_id;

ALTER TABLE schedule 
ADD CONSTRAINT fk_schedule_league_id 
FOREIGN KEY (league_id) REFERENCES leagues(id);

-- 7.4: Update series_stats table
ALTER TABLE series_stats ADD COLUMN IF NOT EXISTS new_league_id INTEGER;

UPDATE series_stats ss
SET new_league_id = l.id
FROM leagues l
WHERE ss.league_id = l.league_id;

ALTER TABLE series_stats 
DROP COLUMN IF EXISTS league_id,
RENAME COLUMN new_league_id TO league_id;

ALTER TABLE series_stats 
ADD CONSTRAINT fk_series_stats_league_id 
FOREIGN KEY (league_id) REFERENCES leagues(id);

-- 7.5: Update player_availability table
ALTER TABLE player_availability ADD COLUMN IF NOT EXISTS new_player_id INTEGER;

-- Match player_availability to players table
UPDATE player_availability pa
SET new_player_id = p.id
FROM players p
JOIN series s ON p.series_id = s.id
WHERE pa.tenniscores_player_id = p.tenniscores_player_id
AND pa.series_id = p.series_id;

-- For records without tenniscores_player_id, try name matching
UPDATE player_availability pa
SET new_player_id = p.id
FROM players p
JOIN series s ON p.series_id = s.id
WHERE pa.new_player_id IS NULL
AND pa.series_id = p.series_id
AND TRIM(LOWER(pa.player_name)) = TRIM(LOWER(p.first_name || ' ' || p.last_name));

ALTER TABLE player_availability 
DROP COLUMN IF EXISTS tenniscores_player_id,
RENAME COLUMN new_player_id TO player_id;

-- Add foreign key constraint (allow NULL for unmatched records)
ALTER TABLE player_availability 
ADD CONSTRAINT fk_player_availability_player_id 
FOREIGN KEY (player_id) REFERENCES players(id);

-- ================================================================
-- PHASE 8: CLEAN UP DEPRECATED TABLES AND INDEXES
-- ================================================================

-- Remove player_leagues table (no longer needed)
DROP TABLE IF EXISTS player_leagues;

-- Remove obsolete indexes
DROP INDEX IF EXISTS idx_player_leagues_player_league;
DROP INDEX IF EXISTS idx_player_leagues_tenniscores_league; 
DROP INDEX IF EXISTS idx_player_leagues_player_id_active;
DROP INDEX IF EXISTS idx_player_leagues_league_id;
DROP INDEX IF EXISTS idx_player_leagues_player_id;
DROP INDEX IF EXISTS idx_player_leagues_tenniscores_id;

-- ================================================================
-- PHASE 9: CREATE NEW OPTIMIZED INDEXES
-- ================================================================

-- Players table indexes
CREATE INDEX IF NOT EXISTS idx_players_league_id ON players(league_id);
CREATE INDEX IF NOT EXISTS idx_players_club_id ON players(club_id);
CREATE INDEX IF NOT EXISTS idx_players_series_id ON players(series_id);
CREATE INDEX IF NOT EXISTS idx_players_tenniscores_id ON players(tenniscores_player_id);
CREATE INDEX IF NOT EXISTS idx_players_names ON players(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_players_active ON players(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_players_league_active ON players(league_id, is_active) WHERE is_active = TRUE;

-- Update existing indexes that may have incorrect names
DROP INDEX IF EXISTS users_email_key;  -- This was on players table
CREATE UNIQUE INDEX IF NOT EXISTS idx_players_email ON players(email) WHERE email IS NOT NULL;

-- Foreign key performance indexes
CREATE INDEX IF NOT EXISTS idx_match_scores_league_id ON match_scores(league_id);
CREATE INDEX IF NOT EXISTS idx_player_history_league_id ON player_history(league_id);
CREATE INDEX IF NOT EXISTS idx_player_history_player_id ON player_history(player_id);
CREATE INDEX IF NOT EXISTS idx_schedule_league_id ON schedule(league_id);
CREATE INDEX IF NOT EXISTS idx_series_stats_league_id ON series_stats(league_id);
CREATE INDEX IF NOT EXISTS idx_player_availability_player_id ON player_availability(player_id);

-- ================================================================
-- PHASE 10: VALIDATION QUERIES
-- ================================================================

-- Create a view to validate the migration
CREATE OR REPLACE VIEW migration_validation AS
SELECT 
    'users' as table_name,
    COUNT(*) as record_count,
    'Authentication-only fields' as description
FROM users
UNION ALL
SELECT 
    'players' as table_name,
    COUNT(*) as record_count,
    'League-specific player records' as description
FROM players
UNION ALL
SELECT 
    'user_player_associations' as table_name,
    COUNT(*) as record_count,
    'User-to-player links' as description
FROM user_player_associations
UNION ALL
SELECT 
    'match_scores' as table_name,
    COUNT(*) as record_count,
    'With INTEGER league_id FK' as description
FROM match_scores
WHERE league_id IS NOT NULL;

-- Clean up temporary table
DROP TABLE IF EXISTS users_backup;

COMMIT;

-- ================================================================
-- POST-MIGRATION VALIDATION
-- ================================================================

-- Run this after COMMIT to validate the migration
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Run the following to validate:';
    RAISE NOTICE 'SELECT * FROM migration_validation;';
    RAISE NOTICE 'SELECT COUNT(*) FROM user_player_associations;';
    RAISE NOTICE 'SELECT COUNT(*) FROM players WHERE is_active = TRUE;';
END $$; 