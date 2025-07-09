-- Migration: Add detailed logging notifications setting
-- Allows admin to toggle SMS notifications for every user activity

INSERT INTO system_settings (key, value, description)
VALUES (
    'detailed_logging_notifications', 
    'false', 
    'Enable/disable SMS notifications to admin for every user activity logged'
)
ON CONFLICT (key) DO NOTHING;

-- Verify the setting was added
SELECT key, value, description 
FROM system_settings 
WHERE key = 'detailed_logging_notifications'; 