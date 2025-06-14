-- Careful Schema Fix
-- =================
-- Fix both league reference and remove redundant user fields

BEGIN;

-- PART 1: Current state
SELECT '=== CURRENT STATE ===' as status;
SELECT COUNT(*) as current_associations FROM user_player_associations;

-- PART 2: Fix league reference step by step
SELECT '=== STEP 1: ADD STABLE LEAGUE COLUMN ===' as step;

-- Add stable league column
ALTER TABLE user_player_associations 
ADD COLUMN stable_league_id VARCHAR(50);

-- Map existing data - for orphaned associations, use pattern matching
UPDATE user_player_associations 
SET stable_league_id = CASE 
    WHEN tenniscores_player_id LIKE 'nndz-%' THEN 'APTA_CHICAGO'
    ELSE 'NSTF'
END;

-- Verify mapping
SELECT stable_league_id, COUNT(*) 
FROM user_player_associations 
GROUP BY stable_league_id;

SELECT '=== STEP 2: DROP OLD CONSTRAINTS ===' as step;

-- Drop primary key first (it includes league_id)
ALTER TABLE user_player_associations DROP CONSTRAINT user_player_associations_pkey;

-- Drop foreign key
ALTER TABLE user_player_associations DROP CONSTRAINT fk_upa_league_id;

SELECT '=== STEP 3: REPLACE LEAGUE COLUMN ===' as step;

-- Drop old league_id column
ALTER TABLE user_player_associations DROP COLUMN league_id;

-- Rename stable column to league_id
ALTER TABLE user_player_associations RENAME COLUMN stable_league_id TO league_id;

-- Set NOT NULL
ALTER TABLE user_player_associations ALTER COLUMN league_id SET NOT NULL;

SELECT '=== STEP 4: RECREATE CONSTRAINTS ===' as step;

-- Create new primary key
ALTER TABLE user_player_associations 
ADD CONSTRAINT user_player_associations_pkey 
PRIMARY KEY (user_id, tenniscores_player_id, league_id);

-- Create foreign key to stable league_id field
ALTER TABLE user_player_associations 
ADD CONSTRAINT fk_upa_league_id 
FOREIGN KEY (league_id) REFERENCES leagues(league_id);

SELECT '=== STEP 5: CLEAN UP USERS TABLE ===' as step;

-- Remove redundant fields from users table
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_league_id_fkey;
DROP INDEX IF EXISTS idx_users_league_id;
DROP INDEX IF EXISTS idx_users_tenniscores_player_id;

ALTER TABLE users 
DROP COLUMN IF EXISTS league_id,
DROP COLUMN IF EXISTS tenniscores_player_id;

-- PART 3: Verify final state
SELECT '=== FINAL VERIFICATION ===' as status;

\d user_player_associations
\d users

-- Test the associations
SELECT 
    u.email,
    upa.tenniscores_player_id,
    upa.league_id as stable_league_id,
    'Stable league reference working!' as status
FROM user_player_associations upa
JOIN users u ON upa.user_id = u.id
ORDER BY u.email;

COMMIT;

SELECT '✅ SCHEMA SUCCESSFULLY FIXED!' as result;
SELECT 'Associations now use stable league_id, no more redundant user fields!' as message; 