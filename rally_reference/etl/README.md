# Rally ETL System

This directory contains ETL (Extract, Transform, Load) scripts for importing data into the Rally database from scraped JSON files.

## Multi-League Schema Overview

The Rally database now supports players being active in multiple leagues simultaneously. This was implemented to reflect the real-world scenario where players participate in both APTA Chicago and NSTF leagues.

### Schema Changes

#### Before (Single League)
- Players had a direct `league_id` column
- One player = One league only
- Queries: `SELECT * FROM players WHERE league_id = 'APTA_CHICAGO'`

#### After (Multi League)
- Players table no longer has `league_id` column
- New `player_leagues` join table for many-to-many relationships
- One player can be active in multiple leagues
- Queries: Join through `player_leagues` table

### Core Tables

#### `players`
- Stores canonical player information
- Primary key: `id` (auto-increment)
- Unique key: `tenniscores_player_id`
- Fields: `first_name`, `last_name`, `tenniscores_player_id`, etc.

#### `player_leagues`
- Join table for player-league associations
- Links players to leagues with context (club, series)
- Supports multiple league memberships per player
- Fields: `player_id`, `league_id`, `club_id`, `series_id`, `is_active`

#### `leagues`
- League reference data
- Primary key: `id` (auto-increment)
- Unique key: `league_id` (string like 'APTA_CHICAGO', 'NSTF')

## ETL Scripts

### `import_players.py`
Primary script for importing player data with multi-league support.

**Usage:**
```bash
# Dry run (analyze without changes)
python etl/import_players.py --dry-run

# Full import
python etl/import_players.py

# Custom file
python etl/import_players.py --file path/to/players.json
```

**Features:**
- Imports from `data/leagues/all/players.json` by default
- Creates/updates players in `players` table
- Creates league associations in `player_leagues` table
- Handles foreign key lookups with caching
- Supports upsert operations (INSERT ... ON CONFLICT)

### `run_all_etl.py`
Master script that runs all ETL processes in correct order.

**Usage:**
```bash
# Run all ETL processes
python etl/run_all_etl.py

# Dry run mode
python etl/run_all_etl.py --dry-run
```

## Query Migration

When updating existing code to use the new multi-league schema, queries need to be updated to join through the `player_leagues` table.

### Example Migration

**Old Query:**
```sql
SELECT * FROM players WHERE league_id = 'APTA_CHICAGO';
```

**New Query:**
```sql
SELECT DISTINCT p.*
FROM players p
JOIN player_leagues pl ON p.id = pl.player_id
JOIN leagues l ON pl.league_id = l.id
WHERE l.league_id = 'APTA_CHICAGO' 
AND pl.is_active = true;
```

See `query_migration_examples.sql` for more examples.

## Data Sources

All ETL scripts read from JSON files in the `data/leagues/` directory:

- `data/leagues/all/players.json` - Combined player data from all leagues
- `data/leagues/all/player_history.json` - Historical performance data
- `data/leagues/all/match_history.json` - Match results and scores

These files are populated by the scraper scripts in the `scrapers/` directory.

## Multi-League Benefits

1. **Accurate Data Model**: Reflects real-world player participation
2. **Better Analytics**: Can analyze cross-league performance
3. **Flexible Queries**: Can filter by single or multiple leagues
4. **Data Integrity**: Prevents duplicate player records

## Current Status

✅ **Completed:**
- Schema normalization (removed `league_id` from players)
- `player_leagues` join table implementation
- Player import ETL with multi-league support
- Query migration examples
- Master ETL runner script

🔄 **In Progress/Future:**
- Additional ETL scripts for other data types
- Application code updates to use new schema
- Foreign key constraint recreation for referential integrity

## Performance Considerations

- Added indexes on frequently joined columns
- Foreign key caching in ETL scripts reduces database lookups
- Batch operations for improved performance
- `is_active` flag allows soft deletion of league associations

## Monitoring

Check data consistency with these queries:

```sql
-- Players without league associations
SELECT COUNT(*) FROM players p
LEFT JOIN player_leagues pl ON p.id = pl.player_id
WHERE pl.id IS NULL;

-- League distribution
SELECT l.league_name, COUNT(DISTINCT pl.player_id) as unique_players
FROM player_leagues pl
JOIN leagues l ON pl.league_id = l.id
WHERE pl.is_active = true
GROUP BY l.league_name;
``` 