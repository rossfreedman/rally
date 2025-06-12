-- Migration: Add career stats columns to players table
-- These will store the career wins/losses data from player_history.json

BEGIN;

-- Add career stats columns
ALTER TABLE players 
ADD COLUMN IF NOT EXISTS career_wins integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS career_losses integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS career_matches integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS career_win_percentage numeric(5,2) DEFAULT 0.00;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_players_career_stats ON players(career_wins, career_losses);

-- Add comments to clarify the difference
COMMENT ON COLUMN players.wins IS 'Current season wins';
COMMENT ON COLUMN players.losses IS 'Current season losses';
COMMENT ON COLUMN players.win_percentage IS 'Current season win percentage';
COMMENT ON COLUMN players.career_wins IS 'Career total wins from player_history.json';
COMMENT ON COLUMN players.career_losses IS 'Career total losses from player_history.json';
COMMENT ON COLUMN players.career_matches IS 'Career total matches (wins + losses)';
COMMENT ON COLUMN players.career_win_percentage IS 'Career win percentage';

COMMIT; 