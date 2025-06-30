-- Fix League Context for Specific Player on Railway
-- ==================================================
-- This fixes the availability issue for player nndz-WkMrK3didjlnUT09
-- by setting their league_context to their most active league

-- Step 1: Check current state
SELECT 
    u.id, u.email, u.first_name, u.last_name, u.league_context,
    'CURRENT STATE' as status
FROM users u
JOIN user_player_associations upa ON u.id = upa.user_id
WHERE upa.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09';

-- Step 2: Show all player associations
SELECT 
    p.league_id, l.league_name, l.league_id as league_string_id,
    p.team_id, t.team_name, c.name as club, s.name as series,
    p.is_active,
    'ASSOCIATIONS' as info
FROM user_player_associations upa
JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
LEFT JOIN leagues l ON p.league_id = l.id
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN clubs c ON p.club_id = c.id
LEFT JOIN series s ON p.series_id = s.id
JOIN users u ON upa.user_id = u.id
WHERE upa.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09'
ORDER BY p.is_active DESC, p.league_id;

-- Step 3: Find the most active league (most recent matches)
SELECT 
    p.league_id,
    l.league_name,
    p.team_id,
    COUNT(ms.id) as match_count,
    MAX(ms.match_date) as last_match_date,
    'BEST LEAGUE CANDIDATE' as info
FROM user_player_associations upa
JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
LEFT JOIN leagues l ON p.league_id = l.id
LEFT JOIN match_scores ms ON (
    (ms.home_player_1_id = p.tenniscores_player_id OR 
     ms.home_player_2_id = p.tenniscores_player_id OR
     ms.away_player_1_id = p.tenniscores_player_id OR 
     ms.away_player_2_id = p.tenniscores_player_id)
    AND ms.league_id = p.league_id
)
JOIN users u ON upa.user_id = u.id
WHERE upa.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09'
AND p.is_active = TRUE
AND p.team_id IS NOT NULL
GROUP BY p.league_id, l.league_name, p.team_id
ORDER BY last_match_date DESC NULLS LAST, match_count DESC
LIMIT 1;

-- Step 4: Apply the fix - set league_context to most active league
-- (This will be APTA Chicago league which has ID 4489 on Railway)
UPDATE users 
SET league_context = (
    SELECT p.league_id
    FROM user_player_associations upa
    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
    LEFT JOIN match_scores ms ON (
        (ms.home_player_1_id = p.tenniscores_player_id OR 
         ms.home_player_2_id = p.tenniscores_player_id OR
         ms.away_player_1_id = p.tenniscores_player_id OR 
         ms.away_player_2_id = p.tenniscores_player_id)
        AND ms.league_id = p.league_id
    )
    WHERE upa.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09'
    AND p.is_active = TRUE
    AND p.team_id IS NOT NULL
    GROUP BY p.league_id
    ORDER BY MAX(ms.match_date) DESC NULLS LAST, COUNT(ms.id) DESC
    LIMIT 1
)
WHERE id IN (
    SELECT u.id
    FROM users u
    JOIN user_player_associations upa ON u.id = upa.user_id
    WHERE upa.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09'
);

-- Step 5: Verify the fix
SELECT 
    u.id, u.email, u.first_name, u.last_name, u.league_context,
    l.league_name,
    'AFTER FIX' as status
FROM users u
JOIN user_player_associations upa ON u.id = upa.user_id
LEFT JOIN leagues l ON u.league_context = l.id
WHERE upa.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09';

-- Step 6: Test session query (what the session service will return)
SELECT 
    u.id,
    u.email, 
    u.first_name, 
    u.last_name,
    u.is_admin,
    u.ad_deuce_preference,
    u.dominant_hand,
    u.league_context,
    p.tenniscores_player_id,
    p.team_id,
    p.club_id,
    p.series_id,
    c.name as club,
    s.name as series,
    l.id as league_db_id,
    l.league_id as league_string_id,
    l.league_name,
    'SESSION SERVICE RESULT' as test_type
FROM users u
LEFT JOIN user_player_associations upa ON u.id = upa.user_id
LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
    AND p.league_id = u.league_context 
    AND p.is_active = TRUE
LEFT JOIN clubs c ON p.club_id = c.id
LEFT JOIN series s ON p.series_id = s.id
LEFT JOIN leagues l ON p.league_id = l.id
WHERE u.id IN (
    SELECT u2.id
    FROM users u2
    JOIN user_player_associations upa2 ON u2.id = upa2.user_id
    WHERE upa2.tenniscores_player_id = 'nndz-WkMrK3didjlnUT09'
)
ORDER BY (CASE WHEN p.tenniscores_player_id IS NOT NULL THEN 1 ELSE 2 END)
LIMIT 1; 