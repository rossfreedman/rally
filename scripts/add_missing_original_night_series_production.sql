-- Add the missing original Night League series (A, B, D, E, F, G) to production
-- These existed on staging but are missing from production

-- Create the missing series
INSERT INTO series (name, display_name) 
SELECT 'Series A', 'Series A' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series A');

INSERT INTO series (name, display_name) 
SELECT 'Series B', 'Series B' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series B');

INSERT INTO series (name, display_name) 
SELECT 'Series D', 'Series D' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series D');

INSERT INTO series (name, display_name) 
SELECT 'Series E', 'Series E' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series E');

INSERT INTO series (name, display_name) 
SELECT 'Series F', 'Series F' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series F');

INSERT INTO series (name, display_name) 
SELECT 'Series G', 'Series G' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series G');

-- Add series_leagues associations for the missing series
INSERT INTO series_leagues (series_id, league_id) 
SELECT s.id, l.id 
FROM series s, leagues l 
WHERE s.name IN ('Series A', 'Series B', 'Series D', 'Series E', 'Series F', 'Series G')
  AND l.league_id = 'CNSWPL'
  AND NOT EXISTS (
    SELECT 1 FROM series_leagues sl 
    WHERE sl.series_id = s.id AND sl.league_id = l.id
  );

-- Create placeholder club if it doesn't exist
INSERT INTO clubs (name) VALUES ('Placeholder Club') ON CONFLICT (name) DO NOTHING;

-- Add teams for each missing series so they appear in API
INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series A Team', 'Series A Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series A' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series A Team' AND series_id = s.id);

INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series B Team', 'Series B Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series B' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series B Team' AND series_id = s.id);

INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series D Team', 'Series D Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series D' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series D Team' AND series_id = s.id);

INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series E Team', 'Series E Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series E' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series E Team' AND series_id = s.id);

INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series F Team', 'Series F Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series F' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series F Team' AND series_id = s.id);

INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series G Team', 'Series G Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series G' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series G Team' AND series_id = s.id);

-- Verify all Night League series A-K now exist
SELECT 'VERIFICATION: Complete Night League A-K Series' as title;
SELECT s.name as series_name, 
       CASE WHEN sl.league_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_league_association,
       COUNT(t.id) as team_count
FROM series s
LEFT JOIN series_leagues sl ON s.id = sl.series_id 
    AND sl.league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
LEFT JOIN teams t ON s.id = t.series_id
WHERE s.name IN ('Series A', 'Series B', 'Series C', 'Series D', 'Series E', 'Series F', 'Series G', 'Series H', 'Series I', 'Series J', 'Series K')
GROUP BY s.name, sl.league_id
ORDER BY s.name;
