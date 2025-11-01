# Railway Volume Setup for CNSWPL JSON Files

## Problem
JSON files created by scrapers were disappearing because they were being written to `/app/data/leagues/...` (ephemeral filesystem) instead of the Railway volume mounted at `/data`.

## Solution
Updated `data/etl/utils/league_directory_manager.py` to check for `CNSWPL_CRON_VARIABLE` environment variable.

### What Changed
- `LeagueDirectoryManager` now checks for `CNSWPL_CRON_VARIABLE` environment variable
- If set, uses that as the base directory (e.g., `/data` for volumes)
- If not set, defaults to `data/leagues` (works for local/dev)

### Railway Configuration Required
For the **CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am** service, add this environment variable:

**Environment Variable:**
- **Name:** `CNSWPL_CRON_VARIABLE`
- **Value:** `/data`

### How It Works
With the volume mounted at `/data` and `CNSWPL_CRON_VARIABLE=/data`:
- Scraper writes to `/data/leagues/CNSWPL/match_scores.json` ✅ (persists on volume)
- Import reads from `/data/leagues/CNSWPL/match_scores.json` ✅ (finds the file)
- Files persist across container restarts ✅

### Testing
After setting the environment variable:
1. Run the scraper: Files should save to `/data/leagues/CNSWPL/...`
2. Exit SSH session
3. Re-enter SSH session: Files should still be there

## Note
Other services (main app, etc.) don't need this variable - they'll continue using the default `data/leagues` path.

