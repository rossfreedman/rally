-- Fix League Reference in User Player Associations
-- ================================================
-- Change the foreign key to reference stable league_id instead of auto-incremented id

BEGIN;

-- Step 1: Check current associations
SELECT 'BEFORE FIX' as status, COUNT(*) as total_associations FROM user_player_associations;

-- Step 2: Add new stable league_id column
ALTER TABLE user_player_associations 
ADD COLUMN stable_league_id VARCHAR(50);

-- Step 3: Populate with stable league IDs from current data
-- First, try to map existing league_id to stable values
UPDATE user_player_associations upa
SET stable_league_id = l.league_id
FROM leagues l
WHERE l.id = upa.league_id;

-- Step 4: For any unmapped records, set based on tenniscores_player_id pattern
UPDATE user_player_associations upa
SET stable_league_id = CASE 
    WHEN upa.tenniscores_player_id LIKE 'nndz-%' THEN 'APTA_CHICAGO'
    ELSE 'NSTF'
END
WHERE stable_league_id IS NULL;

-- Step 5: Verify all records have stable_league_id
DO $$
DECLARE
    unmapped_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO unmapped_count 
    FROM user_player_associations 
    WHERE stable_league_id IS NULL;
    
    IF unmapped_count > 0 THEN
        RAISE EXCEPTION 'ERROR: % associations still unmapped', unmapped_count;
    END IF;
    
    RAISE NOTICE 'SUCCESS: All associations mapped to stable league IDs';
END $$;

-- Step 6: Drop old foreign key constraint
ALTER TABLE user_player_associations 
DROP CONSTRAINT IF EXISTS fk_upa_league_id;

-- Step 7: Drop old league_id column  
ALTER TABLE user_player_associations 
DROP COLUMN league_id;

-- Step 8: Rename stable_league_id to league_id
ALTER TABLE user_player_associations 
RENAME COLUMN stable_league_id TO league_id;

-- Step 9: Set NOT NULL constraint
ALTER TABLE user_player_associations 
ALTER COLUMN league_id SET NOT NULL;

-- Step 10: Create new foreign key to stable league_id field
ALTER TABLE user_player_associations 
ADD CONSTRAINT fk_upa_league_id 
FOREIGN KEY (league_id) REFERENCES leagues(league_id);

-- Step 11: Update primary key to use new structure
ALTER TABLE user_player_associations 
DROP CONSTRAINT user_player_associations_pkey;

ALTER TABLE user_player_associations 
ADD CONSTRAINT user_player_associations_pkey 
PRIMARY KEY (user_id, tenniscores_player_id, league_id);

-- Step 12: Verify the fix
SELECT 'AFTER FIX' as status, COUNT(*) as total_associations FROM user_player_associations;

-- Show final associations
SELECT 
    'FINAL VERIFICATION' as status,
    u.email,
    upa.tenniscores_player_id,
    upa.league_id as stable_league_id,
    CASE WHEN p.id IS NOT NULL THEN 'RESOLVED' ELSE 'UNRESOLVED' END as player_status
FROM user_player_associations upa
JOIN users u ON upa.user_id = u.id
LEFT JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id 
                   AND p.league_id = (SELECT id FROM leagues WHERE league_id = upa.league_id)
ORDER BY u.email;

COMMIT;

SELECT '🎉 LEAGUE REFERENCE FIX COMPLETED!' as result; 