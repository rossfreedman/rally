-- DbSchema Migration: 20250117_140000_add_club_id_to_pickup_games
-- Generated: 2025-01-17T14:00:00.000000
-- Description: Add club_id column to pickup_games table for proper club filtering
-- 
-- This migration adds club_id foreign key to pickup_games table to enable proper
-- club-based filtering so players only see pickup games from their own club.

BEGIN;

-- Add club_id column to pickup_games table
ALTER TABLE pickup_games 
ADD COLUMN club_id INTEGER REFERENCES clubs(id) ON DELETE SET NULL;

-- Add index for better query performance on club filtering
CREATE INDEX idx_pickup_games_club_id ON pickup_games(club_id);

-- Add comment for documentation
COMMENT ON COLUMN pickup_games.club_id IS 'Club that hosts this pickup game. NULL means game is not club-specific.';

-- Update existing pickup games to have no specific club (NULL club_id)
-- This makes existing games visible to all clubs until manually configured
UPDATE pickup_games SET club_id = NULL WHERE club_id IS NULL;

COMMIT;

-- Rollback script (uncomment if needed):
-- BEGIN;
-- DROP INDEX IF EXISTS idx_pickup_games_club_id;
-- ALTER TABLE pickup_games DROP COLUMN IF EXISTS club_id;
-- COMMIT; 