-- Migration: Add Unique Player ID Constraint
-- ==========================================
-- Prevent multiple users from associating with the same player ID

BEGIN;

-- First, check for existing violations
SELECT 
    'EXISTING VIOLATIONS CHECK' as status,
    upa.tenniscores_player_id,
    COUNT(DISTINCT upa.user_id) as user_count,
    STRING_AGG(u.email, ', ') as user_emails
FROM user_player_associations upa
JOIN users u ON upa.user_id = u.id
GROUP BY upa.tenniscores_player_id
HAVING COUNT(DISTINCT upa.user_id) > 1;

-- Add unique constraint to prevent future violations
ALTER TABLE user_player_associations
ADD CONSTRAINT unique_tenniscores_player_id 
UNIQUE (tenniscores_player_id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_upa_unique_player_check 
ON user_player_associations (tenniscores_player_id);

COMMIT;

-- Verification
SELECT 
    'CONSTRAINT VERIFICATION' as status,
    constraint_name, 
    constraint_type
FROM information_schema.table_constraints 
WHERE table_name = 'user_player_associations' 
AND constraint_type = 'UNIQUE'; 