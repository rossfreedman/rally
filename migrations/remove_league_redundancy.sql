-- Remove Final League Redundancy
-- ==============================
-- Remove league_id from user_player_associations since it can be derived from players table

BEGIN;

SELECT '=== CURRENT SCHEMA ===' as status;
\d user_player_associations

-- Show current associations with derived league info
SELECT 'Current associations (league derived from player):' as demo;
SELECT 
    u.email,
    upa.tenniscores_player_id,
    upa.league_id as stored_league,
    l.league_id as derived_league,
    CASE WHEN upa.league_id = l.league_id THEN '✅ MATCH' ELSE '❌ MISMATCH' END as validation
FROM user_player_associations upa
JOIN users u ON upa.user_id = u.id
JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id
JOIN leagues l ON p.league_id = l.id;

SELECT '=== REMOVING REDUNDANT LEAGUE_ID ===' as step;

-- Drop foreign key constraint
ALTER TABLE user_player_associations DROP CONSTRAINT fk_upa_league_id;

-- Drop primary key (includes league_id)
ALTER TABLE user_player_associations DROP CONSTRAINT user_player_associations_pkey;

-- Remove redundant league_id column
ALTER TABLE user_player_associations DROP COLUMN league_id;

-- Create new primary key without league_id
ALTER TABLE user_player_associations 
ADD CONSTRAINT user_player_associations_pkey 
PRIMARY KEY (user_id, tenniscores_player_id);

SELECT '=== FINAL NORMALIZED SCHEMA ===' as status;
\d user_player_associations

-- Test that we can still get all the same info
SELECT 'Testing normalized associations:' as test;
SELECT 
    u.email,
    upa.tenniscores_player_id,
    l.league_id as league,
    p.first_name || ' ' || p.last_name as player_name,
    upa.is_primary
FROM user_player_associations upa
JOIN users u ON upa.user_id = u.id
JOIN players p ON p.tenniscores_player_id = upa.tenniscores_player_id
JOIN leagues l ON p.league_id = l.id
ORDER BY u.email;

SELECT 
    'FINAL SUMMARY' as summary,
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM user_player_associations) as total_associations;

COMMIT;

SELECT '🎉 FULLY NORMALIZED! No more redundant league storage!' as result; 