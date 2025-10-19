-- Migration: Add starting_pti to players table
-- Date: 2025-10-19 13:30:00
-- Description: Adds starting_pti column to players table for season starting PTI values

BEGIN;

-- Add starting_pti column to players table
ALTER TABLE players 
ADD COLUMN starting_pti NUMERIC(5, 2);

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_players_starting_pti ON players(starting_pti);

-- Add comment for documentation
COMMENT ON COLUMN players.starting_pti IS 'PTI value at the start of the current season (2025). Used to calculate PTI delta for player analysis.';

COMMIT;

-- Rollback script (uncomment if needed):
-- BEGIN;
-- DROP INDEX IF EXISTS idx_players_starting_pti;
-- ALTER TABLE players DROP COLUMN IF EXISTS starting_pti;
-- COMMIT;

