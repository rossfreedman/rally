-- Migration script to update Rally's player_availability schema to match Rally Tennis
-- This fixes the timezone handling issues with availability dates

BEGIN;

-- Step 1: Backup existing data and show current state
SELECT 'Current player_availability table structure:' AS info;
\d player_availability

SELECT 'Current data count:' AS info;
SELECT COUNT(*) as total_records FROM player_availability;

-- Step 2: Add new column with timestamptz type
ALTER TABLE player_availability 
ADD COLUMN match_date_new TIMESTAMP WITH TIME ZONE;

-- Step 3: Migrate existing date data to timestamptz
-- Convert existing date values to midnight UTC timestamps
UPDATE player_availability 
SET match_date_new = (match_date::text || ' 00:00:00+00')::timestamp with time zone
WHERE match_date_new IS NULL;

-- Step 4: Verify the migration
SELECT 'Verification - checking converted dates:' AS info;
SELECT 
    player_name, 
    match_date as old_date, 
    match_date_new as new_timestamptz,
    availability_status,
    series_id
FROM player_availability 
ORDER BY match_date DESC 
LIMIT 5;

-- Step 5: Drop constraints and indexes that reference the old column
ALTER TABLE player_availability DROP CONSTRAINT IF EXISTS player_availability_player_name_match_date_series_id_key;
DROP INDEX IF EXISTS idx_player_availability;

-- Step 6: Drop the old column and rename the new one
ALTER TABLE player_availability DROP COLUMN match_date;
ALTER TABLE player_availability RENAME COLUMN match_date_new TO match_date;

-- Step 7: Add NOT NULL constraint
ALTER TABLE player_availability ALTER COLUMN match_date SET NOT NULL;

-- Step 8: Recreate constraints and indexes to match Rally Tennis
-- Add unique constraint
ALTER TABLE player_availability 
ADD CONSTRAINT player_availability_player_name_match_date_series_id_key 
UNIQUE (player_name, match_date, series_id);

-- Add check constraint to ensure midnight UTC timestamps
ALTER TABLE player_availability 
ADD CONSTRAINT match_date_must_be_midnight_utc 
CHECK (
    date_part('hour', match_date AT TIME ZONE 'UTC') = 0 AND 
    date_part('minute', match_date AT TIME ZONE 'UTC') = 0 AND 
    date_part('second', match_date AT TIME ZONE 'UTC') = 0
);

-- Recreate indexes to match Rally Tennis
CREATE INDEX idx_player_availability ON player_availability (player_name, match_date, series_id);
CREATE INDEX idx_player_availability_date_series ON player_availability (match_date, series_id);

-- Step 9: Show final structure
SELECT 'Final player_availability table structure:' AS info;
\d player_availability

-- Step 10: Verify data integrity
SELECT 'Final verification:' AS info;
SELECT 
    COUNT(*) as total_records,
    MIN(match_date) as earliest_date,
    MAX(match_date) as latest_date
FROM player_availability;

-- Show some sample data
SELECT 'Sample migrated data:' AS info;
SELECT 
    player_name, 
    match_date,
    date_part('hour', match_date AT TIME ZONE 'UTC') as utc_hour,
    date_part('minute', match_date AT TIME ZONE 'UTC') as utc_minute,
    availability_status,
    series_id
FROM player_availability 
ORDER BY match_date DESC 
LIMIT 3;

COMMIT;

-- Final success message
SELECT '✅ Migration completed successfully! Rally availability schema now matches Rally Tennis.' AS result; 