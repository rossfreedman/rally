# CNSWPL Scraper Path Resolution Fix

## Problem

The CNSWPL scraper runner failed in production with the error:
```
ERROR: File not found: data/leagues/CNSWPL/match_scores.json
❌ Import CNSWPL Match Scores failed
```

The scraper successfully created the file, but the import script couldn't find it.

## Root Cause

**Path Resolution Mismatch:**
- **Scraper** uses `LeagueDirectoryManager.get_league_file_path()` which respects `CNSWPL_CRON_VARIABLE`
- **Import scripts** used hardcoded relative paths like `data/leagues/{league_key}/match_scores.json`
- When `CNSWPL_CRON_VARIABLE` is set (e.g., `/app/data/leagues` on Railway), the scraper saves to an absolute path, but imports still looked for relative paths

## Solution

Updated all import scripts to use `LeagueDirectoryManager.get_league_file_path()` for consistent path resolution.

### Files Changed

1. **`data/etl/import/import_match_scores.py`**
   - Added import: `from data.etl.utils.league_directory_manager import get_league_file_path`
   - Changed path resolution to use `get_league_file_path(league_key, "match_scores.json")`

2. **`data/etl/import/import_stats.py`**
   - Added import: `from data.etl.utils.league_directory_manager import get_league_file_path`
   - Changed path resolution to use `get_league_file_path(league_key, "series_stats.json")`

3. **`data/etl/import/import_players.py`**
   - Added import: `from data.etl.utils.league_directory_manager import get_league_file_path`
   - Changed path resolution to use `get_league_file_path(league_key, "players.json")`

## Testing

### Local Testing

Run these scripts to verify path resolution works correctly:

```bash
# Test path resolution consistency
python3 scripts/test_path_resolution.py

# Test import script path resolution
python3 scripts/test_import_path_resolution.py

# Check Railway configuration (manual verification needed)
python3 scripts/check_railway_cnswpl_config.py
```

### Test Results

✅ **Path Consistency:** Scraper and import scripts now resolve to the same paths  
✅ **Case Insensitive:** Both `cnswpl` and `CNSWPL` resolve correctly  
✅ **Environment Variable:** Both respect `CNSWPL_CRON_VARIABLE` when set  
✅ **File Access:** Import scripts can find and read files created by scrapers

## Railway Configuration

### Required Environment Variable

**Service:** CNSWPL_Cron_Service (or similar)

**Variable:**
- **Name:** `CNSWPL_CRON_VARIABLE`
- **Value:** `/app/data/leagues`

### Required Volume

- **Mount Path:** `/app/data`
- **Purpose:** Persistent storage for JSON files

### Health Check

- **Status:** DISABLED (cron services don't need health checks)

## Verification Steps

1. **Check Railway Dashboard:**
   - Go to Railway dashboard: https://railway.app
   - Find your CNSWPL Cron service
   - Go to Settings → Variables
   - Verify `CNSWPL_CRON_VARIABLE = /app/data/leagues` is set

2. **Verify Volume:**
   - Go to Settings → Volumes
   - Verify a volume is mounted at `/app/data`

3. **Verify Health Check:**
   - Go to Settings → Health Check
   - Ensure health check is empty/disabled

4. **Deploy and Monitor:**
   - Deploy the updated code
   - Monitor the next cron run logs
   - Verify import step completes successfully

## Expected Behavior

### With CNSWPL_CRON_VARIABLE Set
- Scraper saves to: `/app/data/leagues/CNSWPL/match_scores.json`
- Import reads from: `/app/data/leagues/CNSWPL/match_scores.json`
- ✅ Files persist on Railway volume

### Without CNSWPL_CRON_VARIABLE (Local Development)
- Scraper saves to: `data/leagues/CNSWPL/match_scores.json`
- Import reads from: `data/leagues/CNSWPL/match_scores.json`
- ✅ Works for local development

## Benefits

1. **Consistency:** Scraper and import scripts use the same path resolution logic
2. **Flexibility:** Works with or without `CNSWPL_CRON_VARIABLE`
3. **Railway Compatibility:** Properly handles Railway volumes
4. **Maintainability:** Centralized path management via `LeagueDirectoryManager`

## Next Steps

1. ✅ Code changes completed
2. ✅ Local testing passed
3. ⏳ Verify Railway configuration matches requirements
4. ⏳ Deploy to Railway
5. ⏳ Monitor next cron run

## Related Documentation

- `md/RAILWAY_VOLUME_SETUP.md` - Railway volume setup instructions
- `md/RAILWAY_JSON_FILE_PERSISTENCE.md` - JSON file persistence on Railway
- `data/etl/utils/league_directory_manager.py` - Path resolution implementation


