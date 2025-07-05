-- Drop the deprecated series_name_mappings table
-- This table has been replaced by the series.display_name column system

-- Safety check: Ensure series.display_name column exists before dropping the old table
DO $$
BEGIN
    -- Check if display_name column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'series' AND column_name = 'display_name'
    ) THEN
        RAISE EXCEPTION 'Cannot drop series_name_mappings table: series.display_name column does not exist. Run the display_name migration first.';
    END IF;
    
    -- Check if we have data in the new system
    IF (SELECT COUNT(*) FROM series WHERE display_name IS NOT NULL) = 0 THEN
        RAISE EXCEPTION 'Cannot drop series_name_mappings table: No series have display names populated. Migration incomplete.';
    END IF;
    
    -- All safety checks passed - proceed with dropping the table
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'series_name_mappings'
    ) THEN
        DROP TABLE series_name_mappings CASCADE;
        RAISE NOTICE '✅ Successfully dropped series_name_mappings table';
    ELSE
        RAISE NOTICE 'ℹ️  series_name_mappings table already does not exist';
    END IF;
END $$;

-- Also drop any related indexes or constraints that might reference the old table
-- (Most should be dropped with CASCADE, but this is a safety measure)
DO $$
BEGIN
    -- Drop any remaining indexes that might reference the old table
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_series_mappings_lookup') THEN
        DROP INDEX IF EXISTS idx_series_mappings_lookup;
        RAISE NOTICE '✅ Dropped idx_series_mappings_lookup index';
    END IF;
    
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_series_mappings_active') THEN
        DROP INDEX IF EXISTS idx_series_mappings_active;
        RAISE NOTICE '✅ Dropped idx_series_mappings_active index';
    END IF;
END $$;

-- Verify the migration was successful
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'series_name_mappings'
    ) THEN
        RAISE NOTICE '🎉 Migration successful: series_name_mappings table has been removed';
        RAISE NOTICE '✅ Series name mapping now uses series.display_name column';
    ELSE
        RAISE EXCEPTION 'Migration failed: series_name_mappings table still exists';
    END IF;
END $$; 