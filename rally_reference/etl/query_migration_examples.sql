-- Query Migration Examples: Multi-League Schema Updates
-- 
-- This file shows how to update existing queries that used the old single-league
-- schema to work with the new multi-league player_leagues join table.

-- =============================================================================
-- BEFORE: Old queries that need to be updated
-- =============================================================================

-- OLD: Get players in a specific league
-- SELECT * FROM players WHERE league_id = 'APTA_CHICAGO';

-- OLD: Get player with specific stats for a league  
-- SELECT p.*, s.wins, s.losses 
-- FROM players p 
-- JOIN series_stats s ON p.tenniscores_player_id = s.player_id 
-- WHERE p.league_id = 'APTA_CHICAGO';

-- =============================================================================
-- AFTER: Updated queries for multi-league schema
-- =============================================================================

-- NEW: Get players in a specific league
SELECT DISTINCT p.*
FROM players p
JOIN player_leagues pl ON p.id = pl.player_id
JOIN leagues l ON pl.league_id = l.id
WHERE l.league_id = 'APTA_CHICAGO' 
AND pl.is_active = true;

-- NEW: Get players in a specific league with league context
SELECT p.*, l.league_name, pl.club_id, pl.series_id
FROM players p
JOIN player_leagues pl ON p.id = pl.player_id
JOIN leagues l ON pl.league_id = l.id
WHERE l.league_id = 'APTA_CHICAGO' 
AND pl.is_active = true;

-- NEW: Get player stats for a specific league
SELECT p.first_name, p.last_name, p.tenniscores_player_id,
       l.league_name, s.wins, s.losses
FROM players p
JOIN player_leagues pl ON p.id = pl.player_id
JOIN leagues l ON pl.league_id = l.id
LEFT JOIN series_stats s ON p.tenniscores_player_id = s.player_id 
                          AND s.league_id = l.league_id
WHERE l.league_id = 'APTA_CHICAGO' 
AND pl.is_active = true;

-- NEW: Find players active in multiple leagues
SELECT p.first_name || ' ' || p.last_name as player_name,
       STRING_AGG(l.league_name, ', ') as leagues,
       COUNT(pl.league_id) as league_count
FROM players p
JOIN player_leagues pl ON p.id = pl.player_id
JOIN leagues l ON pl.league_id = l.id
WHERE pl.is_active = true
GROUP BY p.id, p.first_name, p.last_name
HAVING COUNT(pl.league_id) > 1
ORDER BY league_count DESC;

-- NEW: Get player availability with league context
SELECT pa.player_name, pa.match_date, pa.availability_status,
       l.league_name, s.name as series_name
FROM player_availability pa
JOIN series s ON pa.series_id = s.id
JOIN player_leagues pl ON pa.player_name = (
    SELECT p.first_name || ' ' || p.last_name 
    FROM players p 
    WHERE p.id = pl.player_id
)
JOIN leagues l ON pl.league_id = l.id
WHERE l.league_id = 'APTA_CHICAGO'
AND pl.is_active = true;

-- NEW: Club-specific queries with league context
SELECT c.name as club_name,
       l.league_name,
       COUNT(DISTINCT pl.player_id) as player_count
FROM clubs c
JOIN player_leagues pl ON c.id = pl.club_id
JOIN leagues l ON pl.league_id = l.id
WHERE pl.is_active = true
GROUP BY c.name, l.league_name
ORDER BY c.name, l.league_name;

-- =============================================================================
-- UTILITY QUERIES: For development and debugging
-- =============================================================================

-- Check data consistency: Players without league associations
SELECT p.tenniscores_player_id, p.first_name, p.last_name
FROM players p
LEFT JOIN player_leagues pl ON p.id = pl.player_id
WHERE pl.id IS NULL;

-- Check data consistency: League associations without players
SELECT pl.tenniscores_player_id, pl.id
FROM player_leagues pl
LEFT JOIN players p ON pl.player_id = p.id
WHERE p.id IS NULL;

-- League distribution summary
SELECT l.league_name,
       COUNT(DISTINCT pl.player_id) as unique_players,
       COUNT(pl.id) as total_associations,
       COUNT(DISTINCT pl.club_id) as clubs_count,
       COUNT(DISTINCT pl.series_id) as series_count
FROM player_leagues pl
JOIN leagues l ON pl.league_id = l.id
WHERE pl.is_active = true
GROUP BY l.league_name
ORDER BY unique_players DESC; 