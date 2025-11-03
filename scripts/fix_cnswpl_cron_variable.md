# Fix for CNSWPL_CRON_VARIABLE Configuration

## Problem Identified

From Railway SSH diagnostics:
- `CNSWPL_CRON_VARIABLE=/data` (WRONG)
- Scraper saves to: `/data/CNSWPL/match_scores.json` (not on volume)
- Volume is mounted at: `/app/data`
- Files should be at: `/app/data/leagues/CNSWPL/match_scores.json`

## Solution

**Update Railway Environment Variable:**

1. Go to Railway Dashboard: https://railway.app
2. Select service: `CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am` (or your production service)
3. Go to Settings → Variables
4. **Change:**
   - Current: `CNSWPL_CRON_VARIABLE=/data`
   - **New:** `CNSWPL_CRON_VARIABLE=/app/data/leagues`

## Verify the Fix

After updating the variable:

1. SSH into Railway:
   ```bash
   railway shell --service CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am
   ```

2. Verify the variable is set correctly:
   ```bash
   echo $CNSWPL_CRON_VARIABLE
   # Should output: /app/data/leagues
   ```

3. Verify the path resolution:
   ```bash
   python3 -c "from data.etl.utils.league_directory_manager import get_league_file_path; print(get_league_file_path('cnswpl', 'match_scores.json'))"
   # Should output: /app/data/leagues/CNSWPL/match_scores.json
   ```

4. Check if the old file exists at wrong location:
   ```bash
   ls -lh /data/CNSWPL/match_scores.json 2>/dev/null || echo 'File not at old location (good)'
   ```

5. After next scraper run, verify file is saved to correct location:
   ```bash
   ls -lh /app/data/leagues/CNSWPL/match_scores.json
   ```

## Move Existing Files (Optional)

If the scraper has already created files at `/data/CNSWPL/`, you may want to move them to the correct location:

```bash
# In Railway SSH session:
# 1. Check what exists at wrong location
ls -la /data/CNSWPL/ 2>/dev/null || echo 'No files at /data/CNSWPL/'

# 2. If files exist, move them (after updating the variable):
mv /data/CNSWPL/match_scores.json /app/data/leagues/CNSWPL/match_scores.json
mv /data/CNSWPL/*.json /app/data/leagues/CNSWPL/ 2>/dev/null || true
```

## Why This Happened

The `LeagueDirectoryManager` uses `CNSWPL_CRON_VARIABLE` as the base directory. When set to `/data`, it saves files to:
- `/data/CNSWPL/match_scores.json` ❌ (not on volume, will be lost)

When set correctly to `/app/data/leagues`, it saves to:
- `/app/data/leagues/CNSWPL/match_scores.json` ✅ (on volume, persists)

## After Fix

Once `CNSWPL_CRON_VARIABLE=/app/data/leagues` is set:
- ✅ Scraper will save to volume location
- ✅ Import script (with our fix) will find files at same location
- ✅ Files will persist across container restarts
- ✅ Both scraper and import use same path resolution


