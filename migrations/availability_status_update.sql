-- Update player_availability table to use availability_status instead of is_available
BEGIN;

-- Add new column
ALTER TABLE player_availability ADD COLUMN availability_status INTEGER;

-- Convert existing integer values to new status values
UPDATE player_availability 
SET availability_status = CASE 
    WHEN is_available = 1 THEN 1  -- 'Count me in!'
    WHEN is_available = 0 THEN 2  -- 'Sorry, can't'
    ELSE 3  -- 'Not sure yet'
END;

-- Make the new column not null after data migration
ALTER TABLE player_availability ALTER COLUMN availability_status SET NOT NULL;

-- Drop the old column
ALTER TABLE player_availability DROP COLUMN is_available;

-- Add check constraint to ensure valid status values
ALTER TABLE player_availability ADD CONSTRAINT valid_availability_status 
    CHECK (availability_status IN (1, 2, 3));

COMMIT; 