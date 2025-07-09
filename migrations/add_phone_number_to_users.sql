-- Migration: Add phone_number column to users table for SMS notifications
-- ================================================================
-- 
-- This migration adds the phone_number column to the users table
-- to support SMS notifications for polls and other features.
--
-- Run this SQL in Railway's database console or locally.
--

BEGIN;

-- Step 1: Add phone_number column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'phone_number'
    ) THEN
        RAISE NOTICE 'Adding phone_number column to users table...';
        
        -- Add phone_number column
        ALTER TABLE users 
        ADD COLUMN phone_number VARCHAR(20);
        
        RAISE NOTICE 'phone_number column added successfully';
    ELSE
        RAISE NOTICE 'phone_number column already exists, skipping column creation';
    END IF;
END $$;

-- Step 2: Create index for performance (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_users_phone_number 
ON users(phone_number) 
WHERE phone_number IS NOT NULL;

-- Step 3: Verification - show the new column structure
SELECT 
    column_name, 
    data_type, 
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name = 'phone_number';

COMMIT;

-- Note: Users can now add their phone numbers through profile settings
-- The phone_number field supports formats like: +1234567890, (555) 123-4567, etc.
-- The notifications service will validate and format phone numbers before sending SMS 