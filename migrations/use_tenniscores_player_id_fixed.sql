-- Migration: Use tenniscores_player_id in User Player Associations
-- ===========================================================
-- This migration changes user_player_associations to use stable
-- tenniscores_player_id + league_id instead of auto-generated player_id
-- This makes user associations ETL-resilient.

-- SAFETY CHECKS BEFORE MIGRATION
-- ==============================

-- Check 1: Verify all players have tenniscores_player_id
DO $$
DECLARE
    missing_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO missing_count 
    FROM players 
    WHERE tenniscores_player_id IS NULL OR tenniscores_player_id = '';
    
    IF missing_count > 0 THEN
        RAISE EXCEPTION 'MIGRATION ABORTED: Found % players without tenniscores_player_id', missing_count;
    END IF;
    
    RAISE NOTICE 'Safety Check 1 PASSED: All players have tenniscores_player_id';
END $$;

-- Check 2: Verify all players have league_id
DO $$
DECLARE
    missing_league_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO missing_league_count 
    FROM players 
    WHERE league_id IS NULL;
    
    IF missing_league_count > 0 THEN
        RAISE EXCEPTION 'MIGRATION ABORTED: Found % players without league_id', missing_league_count;
    END IF;
    
    RAISE NOTICE 'Safety Check 2 PASSED: All players have league_id';
END $$;

-- Check 3: Verify unique constraint will work
DO $$
DECLARE
    duplicate_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO duplicate_count 
    FROM (
        SELECT tenniscores_player_id, league_id, COUNT(*)
        FROM players
        GROUP BY tenniscores_player_id, league_id
        HAVING COUNT(*) > 1
    ) duplicates;
    
    IF duplicate_count > 0 THEN
        RAISE EXCEPTION 'MIGRATION ABORTED: Found % duplicate tenniscores_player_id + league_id combinations', duplicate_count;
    END IF;
    
    RAISE NOTICE 'Safety Check 3 PASSED: No duplicate tenniscores_player_id + league_id combinations';
END $$;

-- SHOW CURRENT STATE
-- ==================
SELECT 
    'BEFORE MIGRATION' as status,
    COUNT(*) as total_associations,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT player_id) as unique_players
FROM user_player_associations;

-- BEGIN MIGRATION
-- ===============
BEGIN;

-- Step 1: Create backup table for rollback safety
DROP TABLE IF EXISTS user_player_associations_backup;
CREATE TABLE user_player_associations_backup AS 
SELECT * FROM user_player_associations;

-- Step 2: Add new columns for stable identifiers
ALTER TABLE user_player_associations 
ADD COLUMN tenniscores_player_id VARCHAR(255),
ADD COLUMN league_id INTEGER;

-- Step 3: Populate new columns from existing relationships
UPDATE user_player_associations upa
SET 
    tenniscores_player_id = p.tenniscores_player_id,
    league_id = p.league_id
FROM players p
WHERE upa.player_id = p.id;

-- Step 4: Verify all records were successfully mapped
DO $$
DECLARE
    unmapped_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO unmapped_count 
    FROM user_player_associations 
    WHERE tenniscores_player_id IS NULL OR league_id IS NULL;
    
    IF unmapped_count > 0 THEN
        RAISE EXCEPTION 'MIGRATION FAILED: Found % unmapped records', unmapped_count;
    END IF;
    
    RAISE NOTICE 'Step 4 COMPLETED: All records successfully mapped';
END $$;

-- Step 5: Set NOT NULL constraints on new columns
ALTER TABLE user_player_associations
ALTER COLUMN tenniscores_player_id SET NOT NULL,
ALTER COLUMN league_id SET NOT NULL;

-- Step 6: Drop old constraints and indexes
ALTER TABLE user_player_associations
DROP CONSTRAINT IF EXISTS user_player_associations_pkey CASCADE,
DROP CONSTRAINT IF EXISTS user_player_associations_player_id_fkey CASCADE;

-- Drop old indexes
DROP INDEX IF EXISTS idx_upa_user_id;
DROP INDEX IF EXISTS idx_upa_player_id;
DROP INDEX IF EXISTS idx_upa_primary;

-- Step 7: Create new primary key and constraints
ALTER TABLE user_player_associations
ADD CONSTRAINT user_player_associations_pkey 
PRIMARY KEY (user_id, tenniscores_player_id, league_id);

-- Add foreign key constraint for league_id
ALTER TABLE user_player_associations
ADD CONSTRAINT fk_upa_league_id 
FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE;

-- Add foreign key constraint for user_id (keep this one)
ALTER TABLE user_player_associations
ADD CONSTRAINT fk_upa_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Step 8: Create new indexes for performance
CREATE INDEX idx_upa_user_id ON user_player_associations (user_id);
CREATE INDEX idx_upa_tenniscores_player_id ON user_player_associations (tenniscores_player_id);
CREATE INDEX idx_upa_league_id ON user_player_associations (league_id);
CREATE INDEX idx_upa_primary ON user_player_associations (user_id, is_primary) WHERE is_primary = TRUE;

-- Step 9: Remove old player_id column
ALTER TABLE user_player_associations
DROP COLUMN player_id;

-- COMMIT THE MIGRATION
COMMIT;

-- SHOW FINAL STATE
-- ================
SELECT 
    'AFTER MIGRATION' as status,
    COUNT(*) as total_associations,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT (tenniscores_player_id, league_id)) as unique_player_league_combinations
FROM user_player_associations;

-- SHOW NEW SCHEMA
-- ===============
\d user_player_associations;

-- VERIFICATION QUERIES
-- ===================
SELECT 'MIGRATION VERIFICATION' as status;

-- Verify no orphaned associations
SELECT 
    'Orphaned associations check' as check_name,
    COUNT(*) as count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END as result
FROM user_player_associations upa
LEFT JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id 
                   AND p.league_id = upa.league_id
WHERE p.id IS NULL;

-- Show sample associations with player names
SELECT 
    'Sample associations' as check_name,
    u.email,
    upa.tenniscores_player_id,
    p.first_name || ' ' || p.last_name as player_name,
    l.league_id,
    upa.is_primary
FROM user_player_associations upa
JOIN users u ON upa.user_id = u.id
JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id 
               AND p.league_id = upa.league_id
JOIN leagues l ON l.id = upa.league_id
ORDER BY u.email, upa.is_primary DESC
LIMIT 10;

-- SUCCESS MESSAGE
SELECT '🎉 MIGRATION COMPLETED SUCCESSFULLY!' as status;
SELECT 'User-player associations now use stable tenniscores_player_id + league_id' as message;
SELECT 'ETL process will no longer break user associations' as benefit; 