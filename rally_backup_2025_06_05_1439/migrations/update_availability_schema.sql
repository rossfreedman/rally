-- Migration to update player_availability table schema
BEGIN;

-- Add new column
ALTER TABLE player_availability ADD COLUMN availability_status INTEGER;

-- Convert existing boolean values to new status values
UPDATE player_availability 
SET availability_status = CASE 
    WHEN is_available = TRUE THEN 1  -- available
    WHEN is_available = FALSE THEN 2  -- unavailable
    ELSE 3  -- not sure
END;

-- Make the new column not null with default
ALTER TABLE player_availability ALTER COLUMN availability_status SET NOT NULL;
ALTER TABLE player_availability ALTER COLUMN availability_status SET DEFAULT 3;

-- Add check constraint
ALTER TABLE player_availability ADD CONSTRAINT valid_availability_status 
    CHECK (availability_status IN (1, 2, 3));

-- Drop the old column
ALTER TABLE player_availability DROP COLUMN is_available;

COMMIT; 