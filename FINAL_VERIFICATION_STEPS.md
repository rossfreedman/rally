# Final Verification Steps

## ✅ Volume Mount Path Confirmed
The volume `CNSWPL_Scraper_Volume` is correctly mounted at:
- **Mount Path:** `/app/data/leagues`

## 📋 Next Steps

### Step 1: Update Environment Variable
In Railway Dashboard for `CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am`:
1. Go to **Settings** → **Variables**
2. Find `CNSWPL_CRON_VARIABLE`
3. Set it to: `/app/data/leagues` (should match the volume mount path)
4. Save

### Step 2: Restart the Service
To pick up the new environment variable:
1. In Railway Dashboard, go to the service
2. Click **Settings** → **Deploy** → **Redeploy** (or restart button)
3. Wait for service to restart

### Step 3: Verify Everything Works

After restart, SSH in and run:

```bash
# Re-enter SSH
railway shell --service CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am

# 1. Verify environment variable
echo $CNSWPL_CRON_VARIABLE
# Should output: /app/data/leagues

# 2. Verify path resolution
python3 -c "from data.etl.utils.league_directory_manager import get_league_file_path; print('Path:', get_league_file_path('cnswpl', 'match_scores.json'))"
# Should output: Path: /app/data/leagues/CNSWPL/match_scores.json

# 3. Verify file exists at correct location
ls -lh /app/data/leagues/CNSWPL/match_scores.json
# Should show: -rw-r--r-- 1 root root 1.7M Nov  3 17:51 /app/data/leagues/CNSWPL/match_scores.json

# 4. Test import (should work now!)
python3 data/etl/import/import_match_scores.py CNSWPL
# Should successfully import the matches
```

## ✅ Configuration Summary

| Item | Value | Status |
|------|-------|--------|
| Volume Mount | `/app/data/leagues` | ✅ Correct |
| CNSWPL_CRON_VARIABLE | `/app/data/leagues` | ⏳ Update Needed |
| File Location | `/app/data/leagues/CNSWPL/match_scores.json` | ✅ Moved |
| Code Fix | Import scripts use LeagueDirectoryManager | ✅ Complete |

## After Configuration

Once `CNSWPL_CRON_VARIABLE=/app/data/leagues` is set:
- ✅ Scraper will save to: `/app/data/leagues/CNSWPL/match_scores.json`
- ✅ Import will read from: `/app/data/leagues/CNSWPL/match_scores.json`
- ✅ Both use the same persistent volume
- ✅ Files will persist across container restarts
- ✅ Next scraper run will work correctly!


