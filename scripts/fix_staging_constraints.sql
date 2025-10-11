-- Drop foreign key constraints that are causing import failures
-- These team IDs from 2024-2025 season don't exist in current staging teams table

ALTER TABLE match_scores_previous_seasons 
DROP CONSTRAINT IF EXISTS match_scores_previous_seasons_home_team_id_fkey;

ALTER TABLE match_scores_previous_seasons 
DROP CONSTRAINT IF EXISTS match_scores_previous_seasons_away_team_id_fkey;

ALTER TABLE match_scores_previous_seasons 
DROP CONSTRAINT IF EXISTS match_scores_previous_seasons_league_id_fkey;

-- Verify constraints are removed
SELECT conname 
FROM pg_constraint 
WHERE conrelid = 'match_scores_previous_seasons'::regclass 
AND contype = 'f';

