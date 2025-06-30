-- Production Fix: Add user_id column to player_availability table
-- ================================================================
-- 
-- This migration fixes the "column user_id does not exist" error
-- in the availability pages by adding the missing user_id column
-- and populating it with existing data.
--
-- Run this SQL in Railway's database console to fix the issue.
--

BEGIN;

-- Step 1: Check if user_id column already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'player_availability' 
        AND column_name = 'user_id'
    ) THEN
        RAISE NOTICE 'Adding user_id column to player_availability table...';
        
        -- Add user_id column with foreign key reference to users table
        ALTER TABLE player_availability 
        ADD COLUMN user_id INTEGER REFERENCES users(id);
        
        RAISE NOTICE 'user_id column added successfully';
    ELSE
        RAISE NOTICE 'user_id column already exists, skipping column creation';
    END IF;
END $$;

-- Step 2: Populate user_id for existing records
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    RAISE NOTICE 'Populating user_id for existing player_availability records...';
    
    -- Update existing records by linking through player associations
    UPDATE player_availability 
    SET user_id = (
        SELECT u.id 
        FROM players p
        JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
        JOIN users u ON upa.user_id = u.id
        WHERE p.id = player_availability.player_id
        LIMIT 1
    )
    WHERE user_id IS NULL AND player_id IS NOT NULL;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % records with user_id', updated_count;
END $$;

-- Step 3: Create performance indexes
DO $$
BEGIN
    RAISE NOTICE 'Creating performance indexes...';
    
    -- Index for user_id + match_date queries (most common lookup pattern)
    CREATE INDEX IF NOT EXISTS idx_availability_user_date 
    ON player_availability(user_id, match_date)
    WHERE user_id IS NOT NULL;
    
    -- Partial unique index to prevent duplicate availability per user per date
    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_user_date_availability 
    ON player_availability(user_id, match_date)
    WHERE user_id IS NOT NULL;
    
    RAISE NOTICE 'Indexes created successfully';
END $$;

-- Step 4: Verification and reporting
DO $$
DECLARE
    total_records INTEGER;
    records_with_user_id INTEGER;
    percentage NUMERIC;
BEGIN
    RAISE NOTICE 'Verifying migration results...';
    
    SELECT COUNT(*) INTO total_records FROM player_availability;
    SELECT COUNT(*) INTO records_with_user_id FROM player_availability WHERE user_id IS NOT NULL;
    
    IF total_records > 0 THEN
        percentage := ROUND((records_with_user_id::NUMERIC / total_records::NUMERIC) * 100, 1);
    ELSE
        percentage := 0;
    END IF;
    
    RAISE NOTICE '=== MIGRATION RESULTS ===';
    RAISE NOTICE 'Total availability records: %', total_records;
    RAISE NOTICE 'Records with user_id: %', records_with_user_id;
    RAISE NOTICE 'Population rate: %% (%)', percentage, '%';
    
    IF records_with_user_id > 0 THEN
        RAISE NOTICE '✅ Migration completed successfully!';
        RAISE NOTICE '✅ Users should now be able to view availability data properly';
    ELSE
        RAISE NOTICE '⚠️  No records were populated with user_id';
        RAISE NOTICE '   This may indicate missing user_player_associations data';
    END IF;
END $$;

COMMIT;

-- Final success message
SELECT 
    'Production availability schema migration completed!' as status,
    'The "column user_id does not exist" error should now be resolved' as result; 