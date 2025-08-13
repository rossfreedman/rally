-- Add minimal teams for missing CNSWPL series so they appear in API
-- This is required because the API filters out series with 0 teams

-- Create a generic club for the placeholder teams
INSERT INTO clubs (name) VALUES ('Placeholder Club') ON CONFLICT (name) DO NOTHING;

-- Add one team to each missing series to satisfy the API filter
-- Series C
INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series C Team', 'Series C Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series C' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series C Team' AND series_id = s.id);

-- Series H
INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series H Team', 'Series H Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series H' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series H Team' AND series_id = s.id);

-- Series I
INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series I Team', 'Series I Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series I' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series I Team' AND series_id = s.id);

-- Series J
INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series J Team', 'Series J Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series J' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series J Team' AND series_id = s.id);

-- Series K
INSERT INTO teams (team_name, display_name, series_id, league_id, club_id, is_active)
SELECT 'Series K Team', 'Series K Team', s.id, l.id, c.id, true
FROM series s, leagues l, clubs c
WHERE s.name = 'Series K' AND l.league_id = 'CNSWPL' AND c.name = 'Placeholder Club'
AND NOT EXISTS (SELECT 1 FROM teams WHERE team_name = 'Series K Team' AND series_id = s.id);

-- Verify teams were created
SELECT 'VERIFICATION: Teams Created for Missing Series' as title;
SELECT s.name as series_name, COUNT(t.id) as team_count
FROM series s
LEFT JOIN teams t ON s.id = t.series_id
WHERE s.name IN ('Series C', 'Series H', 'Series I', 'Series J', 'Series K')
GROUP BY s.name
ORDER BY s.name;