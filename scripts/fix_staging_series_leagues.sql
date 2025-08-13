-- Fix missing CNSWPL series_leagues associations on staging
-- Add associations for the 8 manually added series

-- Get CNSWPL league ID (should be consistent across environments)
\set cnswpl_league_id (SELECT id FROM leagues WHERE league_id = 'CNSWPL')

-- Add series_leagues associations for missing CNSWPL series
-- These series were manually added but missing the league associations

INSERT INTO series_leagues (series_id, league_id) 
SELECT s.id, l.id 
FROM series s, leagues l 
WHERE s.name IN ('Series 13', 'Series 15', 'Series 17', 'Series C', 'Series H', 'Series I', 'Series J', 'Series K')
  AND l.league_id = 'CNSWPL'
  AND NOT EXISTS (
    SELECT 1 FROM series_leagues sl 
    WHERE sl.series_id = s.id AND sl.league_id = l.id
  );

-- Verify the fix
SELECT 'VERIFICATION: CNSWPL Series with League Associations' as title;
SELECT s.name as series_name, COUNT(sl.league_id) as has_association
FROM series s
LEFT JOIN series_leagues sl ON s.id = sl.series_id AND sl.league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
WHERE s.name IN ('Series 13', 'Series 15', 'Series 17', 'Series C', 'Series H', 'Series I', 'Series J', 'Series K')
GROUP BY s.name
ORDER BY s.name;
