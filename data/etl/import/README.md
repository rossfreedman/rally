# Season Management Scripts

Two simple Python scripts for managing league-specific season resets in the Rally app.

## Prerequisites

- Python 3.11+
- PostgreSQL database
- `psycopg2-binary` package
- `DATABASE_URL` environment variable set (PostgreSQL URI)

## Scripts

### 1. end_season.py

Removes season-specific data for a single league while preserving:
- `leagues` table
- `users` table  
- `user_player_associations` table
- `players` table

**Usage:**
```bash
python3 data/etl/import/end_season.py <LEAGUE_KEY>
```

**Example:**
```bash
python3 data/etl/import/end_season.py CNSWPL
```

**What it deletes (in safe dependency order):**
1. `match_scores` - via league_id or team join
2. `schedules` - via league_id or team join
3. `player_availability` - via league_id or player join
4. `stats` - via league_id or team join
5. `teams` - via league_id
6. `series` - via league_id
7. `clubs` - via league_id

### 2. start_season.py

Bootstraps clubs, series, teams, and players from `players.json` for a single league with strict de-duplication using upserts.

**Usage:**
```bash
python3 data/etl/import/start_season.py <LEAGUE_KEY>
```

**Example:**
```bash
python3 data/etl/import/start_season.py CNSWPL
```

**What it creates/upserts:**
1. **Clubs** - `UNIQUE(name, league_id)` constraint
2. **Series** - `UNIQUE(name, league_id)` constraint  
3. **Teams** - `UNIQUE(name, league_id)` constraint, requires valid club_id and series_id
4. **Players** - `UNIQUE(external_id)` if available, else `UNIQUE(name, league_id)`

**Input file:** `data/leagues/<LEAGUE_KEY>/players.json`

**JSON structure expected:**
```json
[
  {
    "League": "APTA_CHICAGO",
    "Club": "Glen View",
    "Series": "Series 1", 
    "Team": "Glen View 1",
    "Player ID": "nndz-WkNPd3hMendqQT09",
    "First Name": "Peter",
    "Last Name": "Rose"
  }
]
```

## Features

- **Idempotent**: Safe to run multiple times
- **Transaction-safe**: All operations wrapped in single transaction with rollback on error
- **Duplicate prevention**: Uses PostgreSQL upserts with proper conflict resolution
- **Flexible**: Automatically detects table structure (e.g., external_id column presence)
- **Clear output**: Shows counts of inserted/existing/skipped records

## Error Handling

- Clear error messages for missing league keys
- Graceful handling of missing JSON files
- Database connection error handling
- Transaction rollback on any failure

## Database Schema Requirements

The scripts assume these tables exist with the specified unique constraints:

```sql
leagues(id, key, name)
clubs(id, name, league_id, UNIQUE(name, league_id))
series(id, name, league_id, UNIQUE(name, league_id))
teams(id, name, club_id, series_id, league_id, UNIQUE(name, league_id))
players(id, name, league_id, external_id?)
```

## Workflow

1. **End current season:**
   ```bash
   python3 data/etl/import/end_season.py CNSWPL
   ```

2. **Start new season:**
   ```bash
   python3 data/etl/import/start_season.py CNSWPL
   ```

## Notes

- Scripts are designed to be simple and dependency-light
- No external config files required
- Uses environment variables for database connection
- Preserves all user data and associations
- Handles both direct league_id columns and join-based deletions
