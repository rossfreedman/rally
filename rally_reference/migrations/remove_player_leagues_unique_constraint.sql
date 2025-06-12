-- Migration: Remove unique constraint on tenniscores_player_id in player_leagues
-- This allows players to exist in multiple leagues with the same tenniscores_player_id

BEGIN;

-- First, drop dependent foreign key constraints
ALTER TABLE match_scores DROP CONSTRAINT IF EXISTS match_scores_home_player_1_id_fkey;
ALTER TABLE match_scores DROP CONSTRAINT IF EXISTS match_scores_home_player_2_id_fkey;
ALTER TABLE match_scores DROP CONSTRAINT IF EXISTS match_scores_away_player_1_id_fkey;
ALTER TABLE match_scores DROP CONSTRAINT IF EXISTS match_scores_away_player_2_id_fkey;
ALTER TABLE player_history DROP CONSTRAINT IF EXISTS player_history_player_id_fkey;

-- Now drop the unique constraint
ALTER TABLE player_leagues DROP CONSTRAINT IF EXISTS unique_tenniscores_player_id;

-- Note: Foreign key constraints will be recreated after player data is imported

COMMIT; 