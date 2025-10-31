# Railway JSON File Persistence Issue

## Problem
JSON files created by scrapers (`match_scores.json`, `series_stats.json`, etc.) disappear in Railway production because:

1. **Railway filesystem is ephemeral** - files are lost when containers restart
2. **Deployments restart containers** - each deployment creates a new container
3. **Container restarts** - Railway may restart containers for various reasons

## Impact
- Scripts that depend on JSON files (like `fix_wilmette_h3_players.py`) fail because the files don't exist
- The scraper creates the files, but they're gone by the time the fix script runs

## Solutions

### Option 1: Run Both Scripts in Same Session (Recommended)
Run the scraper and fix script in the same SSH session without leaving:

```bash
railway shell --service 'Rally PRODUCTION App'

# Run scraper
python3 data/etl/scrapers/cnswpl_scrape_match_scores.py cnswpl

# Immediately run fix script (file still exists)
python3 scripts/fix_wilmette_h3_players.py
```

### Option 2: Query Database Instead of JSON
Modify scripts to query `match_scores` table directly instead of reading JSON files.

### Option 3: Use Railway Volumes (Future)
Railway supports persistent volumes, but requires configuration changes.

## Current Workaround
The script now uses `get_league_file_path()` to find the JSON, and will show diagnostic info if it's missing. For now, run both scraper and fix script in the same SSH session.

