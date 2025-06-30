-- Fix Railway Schema Issues
-- Run this on Railway with: railway connect

-- Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initialize session_version
INSERT INTO system_settings (key, value, description) 
VALUES ('session_version', '6', 'Current session version for cache busting')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Add logo_filename column to clubs
ALTER TABLE clubs 
ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(255);

-- Verify fixes
SELECT 'system_settings table check:' as check_type, 
       EXISTS(SELECT FROM information_schema.tables WHERE table_name = 'system_settings') as exists;

SELECT 'session_version check:' as check_type, 
       value as exists 
FROM system_settings WHERE key = 'session_version';

SELECT 'logo_filename column check:' as check_type,
       EXISTS(SELECT FROM information_schema.columns WHERE table_name = 'clubs' AND column_name = 'logo_filename') as exists; 