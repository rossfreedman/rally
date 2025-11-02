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

### Option 3: Use Railway Volumes ✅ (Implemented)
Railway volumes are now configured. See `md/RAILWAY_VOLUME_SETUP.md` for complete setup instructions.

**Configuration:**
- Volume mounted at `/app/data`
- Environment variable: `CNSWPL_CRON_VARIABLE=/app/data/leagues`
- Files persist at `/app/data/leagues/CNSWPL/` (matches import script expectations)

## Current Solution ✅
Railway volumes are now configured. Scrapers save to persistent storage at `/app/data/leagues/CNSWPL/`, and import scripts find files at the same location via relative path `data/leagues/CNSWPL/`. Files persist across container restarts and deployments.

