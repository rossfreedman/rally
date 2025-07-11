-- DbSchema Migration: 20250112_120000_add_is_private_to_pickup_games
-- Generated: 2025-01-12T12:00:00.000000
-- Description: Add is_private column to pickup_games table for public/private game distinction
-- 
-- This migration adds support for private pickup games (similar to group chats functionality)

BEGIN;

-- Add is_private column to pickup_games table
ALTER TABLE pickup_games 
ADD COLUMN is_private BOOLEAN NOT NULL DEFAULT FALSE;

-- Add index for better query performance on private/public filtering
CREATE INDEX idx_pickup_games_is_private ON pickup_games(is_private);

-- Add comment for documentation
COMMENT ON COLUMN pickup_games.is_private IS 'TRUE for private games (group-like), FALSE for public pickup games';

COMMIT;

-- Rollback script (uncomment if needed):
-- BEGIN;
-- DROP INDEX IF EXISTS idx_pickup_games_is_private;
-- ALTER TABLE pickup_games DROP COLUMN IF EXISTS is_private;
-- COMMIT; 