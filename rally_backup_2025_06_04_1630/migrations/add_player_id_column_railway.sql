-- Add tenniscores_player_id column to player_availability table on Railway
BEGIN;

-- Add the new column
ALTER TABLE player_availability 
ADD COLUMN tenniscores_player_id VARCHAR(50);

-- Create an index for the new column for better query performance
CREATE INDEX idx_player_availability_tenniscores_id ON player_availability(tenniscores_player_id);

-- Try to populate existing records with player IDs where possible
-- This will match player names from availability records with users table
UPDATE player_availability 
SET tenniscores_player_id = users.tenniscores_player_id
FROM users 
WHERE player_availability.player_name = TRIM(users.first_name || ' ' || users.last_name)
AND users.tenniscores_player_id IS NOT NULL;

-- Add partial unique constraint that allows multiple NULLs but prevents duplicate player_id+date+series combinations
-- This ensures we can only have one availability record per player_id per date per series
CREATE UNIQUE INDEX idx_player_availability_unique_player_id 
ON player_availability(tenniscores_player_id, match_date, series_id) 
WHERE tenniscores_player_id IS NOT NULL;

COMMIT; 