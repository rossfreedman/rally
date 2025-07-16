-- Migration: Add temporary password tracking columns to users table
-- Date: 2025-01-15

-- Add columns to track temporary passwords
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS has_temporary_password BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS temporary_password_set_at TIMESTAMP;

-- Add index for efficient querying
CREATE INDEX IF NOT EXISTS idx_users_temporary_password 
ON users(has_temporary_password) 
WHERE has_temporary_password = TRUE;

-- Add comment for documentation
COMMENT ON COLUMN users.has_temporary_password IS 'Flag indicating if user has a temporary password that needs to be changed';
COMMENT ON COLUMN users.temporary_password_set_at IS 'Timestamp when temporary password was set'; 