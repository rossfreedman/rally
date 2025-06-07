-- Migration: Ensure user_instructions table exists
-- This script can be run directly on Railway database to fix the 500 error

-- Create user_instructions table if it doesn't exist
CREATE TABLE IF NOT EXISTS user_instructions (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    instruction TEXT NOT NULL,
    team_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- Create index for performance if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_user_instructions_email 
ON user_instructions(user_email);

-- Add missing columns if they don't exist (in case table exists but is incomplete)
DO $$ 
BEGIN
    -- Check and add user_email column if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_instructions' AND column_name='user_email'
    ) THEN
        ALTER TABLE user_instructions ADD COLUMN user_email VARCHAR(255) NOT NULL DEFAULT '';
    END IF;
    
    -- Check and add instruction column if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_instructions' AND column_name='instruction'
    ) THEN
        ALTER TABLE user_instructions ADD COLUMN instruction TEXT NOT NULL DEFAULT '';
    END IF;
    
    -- Check and add team_id column if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_instructions' AND column_name='team_id'
    ) THEN
        ALTER TABLE user_instructions ADD COLUMN team_id INTEGER;
    END IF;
    
    -- Check and add created_at column if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_instructions' AND column_name='created_at'
    ) THEN
        ALTER TABLE user_instructions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- Check and add is_active column if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='user_instructions' AND column_name='is_active'
    ) THEN
        ALTER TABLE user_instructions ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
END $$;

-- Verify the table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'user_instructions' 
ORDER BY ordinal_position; 