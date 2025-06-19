-- Migration: Enforce player_id integrity in availability table
-- This prevents the root cause issue by making player_id mandatory

BEGIN;

-- Step 1: Verify current state
SELECT 'Current state check:' AS info;
SELECT 
    COUNT(*) as total_records,
    COUNT(player_id) as records_with_player_id,
    COUNT(*) - COUNT(player_id) as records_with_null_player_id
FROM player_availability;

-- Step 2: Show records that would be affected by NOT NULL constraint
SELECT 'Records with NULL player_id that need attention:' AS info;
SELECT id, player_name, match_date, series_id, availability_status
FROM player_availability 
WHERE player_id IS NULL
ORDER BY player_name, match_date;

-- Step 3: Add NOT NULL constraint to prevent future NULL player_id values
-- Note: This will fail if there are existing NULL values, which is intentional
-- The fix_availability_player_ids.py script should be run first to populate missing IDs

ALTER TABLE player_availability 
ALTER COLUMN player_id SET NOT NULL;

-- Step 4: Add additional data integrity constraints

-- Ensure player_id references a valid player
ALTER TABLE player_availability 
ADD CONSTRAINT fk_player_availability_player_id 
FOREIGN KEY (player_id) REFERENCES players(id);

-- Create partial unique index to prevent duplicate availability per player per date
-- (allows only one availability record per player per date per series)
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_player_availability 
ON player_availability(player_id, match_date, series_id)
WHERE player_id IS NOT NULL;

-- Step 5: Add check constraint for valid availability status
ALTER TABLE player_availability 
DROP CONSTRAINT IF EXISTS valid_availability_status;

ALTER TABLE player_availability 
ADD CONSTRAINT valid_availability_status 
CHECK (availability_status IN (1, 2, 3));

-- Step 6: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_player_availability_player_id 
ON player_availability(player_id);

CREATE INDEX IF NOT EXISTS idx_player_availability_date_series 
ON player_availability(match_date, series_id);

-- Step 7: Create a function to validate player lookups
CREATE OR REPLACE FUNCTION validate_player_exists(
    p_player_name VARCHAR(255),
    p_series_id INTEGER
) RETURNS INTEGER AS $$
DECLARE
    player_record_id INTEGER;
BEGIN
    -- Try to find the player by name and series
    SELECT id INTO player_record_id
    FROM players 
    WHERE CONCAT(first_name, ' ', last_name) = p_player_name
    AND series_id = p_series_id
    AND is_active = true;
    
    -- If not found, return NULL which will cause constraint violation
    RETURN player_record_id;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Add a trigger to automatically populate player_id on insert
-- This provides an extra safety net
CREATE OR REPLACE FUNCTION auto_populate_player_id() RETURNS TRIGGER AS $$
BEGIN
    -- If player_id is NULL, try to populate it
    IF NEW.player_id IS NULL THEN
        NEW.player_id := validate_player_exists(NEW.player_name, NEW.series_id);
        
        -- If still NULL, raise an error with helpful message
        IF NEW.player_id IS NULL THEN
            RAISE EXCEPTION 'Cannot create availability record: Player "%" not found in series ID % (or player is inactive). Please verify player name and series are correct.',
                NEW.player_name, NEW.series_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
DROP TRIGGER IF EXISTS trigger_auto_populate_player_id ON player_availability;
CREATE TRIGGER trigger_auto_populate_player_id
    BEFORE INSERT ON player_availability
    FOR EACH ROW
    EXECUTE FUNCTION auto_populate_player_id();

-- Step 9: Verification
SELECT 'Final verification:' AS info;
SELECT 
    COUNT(*) as total_records,
    COUNT(player_id) as records_with_player_id,
    COUNT(*) - COUNT(player_id) as records_with_null_player_id
FROM player_availability;

-- Show the constraints that are now active
SELECT 'Active constraints on player_availability:' AS info;
SELECT 
    conname as constraint_name,
    contype as constraint_type,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint 
WHERE conrelid = 'player_availability'::regclass
ORDER BY conname;

COMMIT; 