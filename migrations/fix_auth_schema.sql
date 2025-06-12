-- ================================================================
-- Rally Database Schema Fix - Add Missing User Foreign Keys
-- ================================================================
-- 
-- This migration adds the missing club_id and series_id foreign key
-- columns to the users table to fix registration functionality.
-- This is a SURGICAL fix to make the auth system work with the 
-- current database schema.
-- ================================================================

BEGIN;

-- Add missing foreign key columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS club_id INTEGER REFERENCES clubs(id);

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS series_id INTEGER REFERENCES series(id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_club_id ON users(club_id);
CREATE INDEX IF NOT EXISTS idx_users_series_id ON users(series_id);

-- Add foreign key constraints for data integrity (only if they don't exist)
DO $$ 
BEGIN
    -- Add club_id foreign key constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_users_club_id'
    ) THEN
        ALTER TABLE users 
        ADD CONSTRAINT fk_users_club_id 
        FOREIGN KEY (club_id) REFERENCES clubs(id);
    END IF;
    
    -- Add series_id foreign key constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_users_series_id'
    ) THEN
        ALTER TABLE users 
        ADD CONSTRAINT fk_users_series_id 
        FOREIGN KEY (series_id) REFERENCES series(id);
    END IF;
END $$;

COMMIT;

-- Validation
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('club_id', 'series_id')
ORDER BY column_name; 