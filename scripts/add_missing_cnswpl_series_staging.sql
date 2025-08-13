
-- Add Series C if it doesn't exist
INSERT INTO series (name, display_name) 
SELECT 'Series C', 'Series C' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series C');


-- Add Series H if it doesn't exist
INSERT INTO series (name, display_name) 
SELECT 'Series H', 'Series H' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series H');


-- Add Series I if it doesn't exist
INSERT INTO series (name, display_name) 
SELECT 'Series I', 'Series I' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series I');


-- Add Series J if it doesn't exist
INSERT INTO series (name, display_name) 
SELECT 'Series J', 'Series J' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series J');


-- Add Series K if it doesn't exist
INSERT INTO series (name, display_name) 
SELECT 'Series K', 'Series K' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series K');


-- Add series_leagues associations for all missing series
INSERT INTO series_leagues (series_id, league_id) 
SELECT s.id, l.id 
FROM series s, leagues l 
WHERE s.name IN ('Series C', 'Series H', 'Series I', 'Series J', 'Series K')
  AND l.league_id = 'CNSWPL'
  AND NOT EXISTS (
    SELECT 1 FROM series_leagues sl 
    WHERE sl.series_id = s.id AND sl.league_id = l.id
  );


-- Verify the additions
SELECT 'VERIFICATION: Added Series' as title;
SELECT s.name as series_name, 
       CASE WHEN sl.league_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_association
FROM series s
LEFT JOIN series_leagues sl ON s.id = sl.series_id 
    AND sl.league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
WHERE s.name IN ('Series C', 'Series H', 'Series I', 'Series J', 'Series K')
ORDER BY s.name;
