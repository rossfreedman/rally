-- Add notes field to player_availability table
-- Migration: Add notes column for user availability comments

BEGIN;

-- Add notes column to player_availability table
ALTER TABLE player_availability 
ADD COLUMN notes TEXT;

-- Add comment to document the field
COMMENT ON COLUMN player_availability.notes IS 'Optional note/comment from user about their availability';

-- Create index for notes field if we ever want to search by notes content
-- (Optional, but good for future performance if needed)
CREATE INDEX IF NOT EXISTS idx_player_availability_notes 
ON player_availability USING gin(to_tsvector('english', notes))
WHERE notes IS NOT NULL AND notes != '';

COMMIT;

-- Success message
SELECT '✅ Successfully added notes field to player_availability table' AS result; 