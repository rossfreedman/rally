-- Migration: Normalize Multi-League Schema
-- Purpose: Remove league_id from players table and optimize player_leagues for many-to-many relationships

BEGIN;

-- Step 1: Remove league_id from players table (keep current_league_id for now as default preference)
ALTER TABLE players DROP COLUMN IF EXISTS league_id;

-- Step 2: Add helpful indexes for multi-league queries
CREATE INDEX IF NOT EXISTS idx_player_leagues_player_league 
ON player_leagues(player_id, league_id);

CREATE INDEX IF NOT EXISTS idx_player_leagues_tenniscores_league 
ON player_leagues(tenniscores_player_id, league_id);

-- Step 3: Clean up any duplicate records in player_leagues (keeping the most recent)
DELETE FROM player_leagues p1 
WHERE p1.id NOT IN (
    SELECT MAX(p2.id) 
    FROM player_leagues p2 
    WHERE p2.player_id = p1.player_id 
    AND p2.league_id = p1.league_id 
    AND p2.is_active = p1.is_active
);

COMMIT; 