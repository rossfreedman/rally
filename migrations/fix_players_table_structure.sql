-- Migration: Fix Players Table Structure
-- Purpose: Make email and password_hash nullable since players table should store 
-- player data from scraped sources, not authentication data

BEGIN;

-- Make email and password_hash nullable in players table
ALTER TABLE players ALTER COLUMN email DROP NOT NULL;
ALTER TABLE players ALTER COLUMN password_hash DROP NOT NULL;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_players_names 
ON players(first_name, last_name);

CREATE INDEX IF NOT EXISTS idx_players_tenniscores_id 
ON players(tenniscores_player_id);

COMMIT; 