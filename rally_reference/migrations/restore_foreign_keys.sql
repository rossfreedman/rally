-- Migration: Restore Foreign Key Constraints
-- Purpose: Restore foreign key constraints that were removed during multi-league migration

BEGIN;

-- Restore foreign key constraints for match_scores table
ALTER TABLE match_scores 
ADD CONSTRAINT match_scores_home_player_1_id_fkey 
FOREIGN KEY (home_player_1_id) REFERENCES players(id);

ALTER TABLE match_scores 
ADD CONSTRAINT match_scores_home_player_2_id_fkey 
FOREIGN KEY (home_player_2_id) REFERENCES players(id);

ALTER TABLE match_scores 
ADD CONSTRAINT match_scores_away_player_1_id_fkey 
FOREIGN KEY (away_player_1_id) REFERENCES players(id);

ALTER TABLE match_scores 
ADD CONSTRAINT match_scores_away_player_2_id_fkey 
FOREIGN KEY (away_player_2_id) REFERENCES players(id);

-- Restore foreign key constraint for player_history table
ALTER TABLE player_history 
ADD CONSTRAINT player_history_player_id_fkey 
FOREIGN KEY (player_id) REFERENCES players(id);

COMMIT; 