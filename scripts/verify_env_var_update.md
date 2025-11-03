# How to Ensure Railway Environment Variable Update Takes Effect

## Problem
After updating `CNSWPL_CRON_VARIABLE` in Railway, it may still show the old value in SSH because:
1. The container hasn't restarted yet
2. Environment variables are loaded at container startup

## Solutions

### Option 1: Restart the Service (Recommended)
1. Go to Railway Dashboard
2. Select `CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am`
3. Click **Settings** → **Deploy** → **Redeploy** (or use the restart button)
4. Wait for the service to restart
5. SSH back in and verify

### Option 2: Wait for Next Deployment
The variable will be picked up automatically on the next deployment/restart.

### Option 3: Exit and Re-enter SSH
Sometimes re-entering SSH after Railway has updated the variable works:
```bash
exit  # Exit current SSH session
railway shell --service CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am  # Re-enter
echo $CNSWPL_CRON_VARIABLE  # Should now show /app/data/leagues
```

## Verification Steps

After restart/re-entry, verify:

```bash
# 1. Check variable
echo $CNSWPL_CRON_VARIABLE
# Expected: /app/data/leagues

# 2. Verify path resolution
python3 -c "from data.etl.utils.league_directory_manager import get_league_file_path; print('Path:', get_league_file_path('cnswpl', 'match_scores.json'))"
# Expected: /app/data/leagues/CNSWPL/match_scores.json

# 3. Verify file exists at correct location
ls -lh /app/data/leagues/CNSWPL/match_scores.json
# Should show the 1.7M file

# 4. Test import can find it
python3 data/etl/import/import_match_scores.py CNSWPL
# Should successfully import matches
```

## If Variable Still Shows /data

1. Double-check Railway Dashboard:
   - Go to Settings → Variables
   - Verify `CNSWPL_CRON_VARIABLE` is set to `/app/data/leagues`
   - Make sure you saved the changes
   - Check which service you updated (should be the production cron service)

2. Force a container restart:
   - Railway Dashboard → Service → Settings → Deploy
   - Click "Redeploy" or "Restart"

3. Check if there are multiple services:
   - Make sure you updated the correct service
   - Check if staging and production have separate variables


