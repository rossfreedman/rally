-- Fix Schema Issues After ETL Import
-- Run this SQL directly on Railway database

-- 1. Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Initialize session_version
INSERT INTO system_settings (key, value, description) 
VALUES ('session_version', '5', 'Current session version for cache busting')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- 3. Add logo_filename column to clubs table
ALTER TABLE clubs 
ADD COLUMN IF NOT EXISTS logo_filename VARCHAR(255);

-- 4. Verify the fixes
SELECT 'system_settings table exists' as status 
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'system_settings');

SELECT 'logo_filename column exists' as status
WHERE EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'clubs' AND column_name = 'logo_filename'); 