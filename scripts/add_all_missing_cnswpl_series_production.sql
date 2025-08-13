-- Add ALL missing CNSWPL series to production (8 total: 13, 15, 17, C, H, I, J, K)

-- Add Series 13, 15, 17 (Day League)
INSERT INTO series (name, display_name) 
SELECT 'Series 13', 'Series 13' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series 13');

INSERT INTO series (name, display_name) 
SELECT 'Series 15', 'Series 15' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series 15');

INSERT INTO series (name, display_name) 
SELECT 'Series 17', 'Series 17' 
WHERE NOT EXISTS (SELECT 1 FROM series WHERE name = 'Series 17');

-- Add series_leagues associations for all 8 series
INSERT INTO series_leagues (series_id, league_id) 
SELECT s.id, l.id 
FROM series s, leagues l 
WHERE s.name IN ('Series 13', 'Series 15', 'Series 17', 'Series C', 'Series H', 'Series I', 'Series J', 'Series K')
  AND l.league_id = 'CNSWPL'
  AND NOT EXISTS (
    SELECT 1 FROM series_leagues sl 
    WHERE sl.series_id = s.id AND sl.league_id = l.id
  );

-- Create placeholder club for teams
INSERT INTO clubs (name) VALUES ('Placeholder Club') ON CONFLICT (name) DO NOTHING;

-- Add teams for Series 13, 15, 17 (Day League)
INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series 13 Team', 'Series 13 Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series 13' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series 13 Team' AND series_id = s.id);

INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series 15 Team', 'Series 15 Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series 15' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series 15 Team' AND series_id = s.id);

INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series 17 Team', 'Series 17 Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series 17' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series 17 Team' AND series_id = s.id);

-- Verify all 8 series were created with teams
SELECT 'VERIFICATION: All Missing Series Created' as title;
SELECT s.name as series_name, 
       CASE WHEN sl.league_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_league_association,
       COUNT(t.id) as team_count
FROM series s
LEFT JOIN series_leagues sl ON s.id = sl.series_id 
    AND sl.league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
LEFT JOIN teams t ON s.id = t.series_id
WHERE s.name IN ('Series 13', 'Series 15', 'Series 17', 'Series C', 'Series H', 'Series I', 'Series J', 'Series K')
GROUP BY s.name, sl.league_id
ORDER BY s.name;
