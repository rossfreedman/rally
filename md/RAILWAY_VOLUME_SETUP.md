# Railway Volume Setup for CNSWPL JSON Files

## Problem
JSON files created by scrapers were disappearing because they were being written to the ephemeral filesystem instead of a persistent Railway volume. Additionally, import scripts expect files at `data/leagues/{league}/file.json` (relative path), which resolves to `/app/data/leagues/{league}/file.json` on Railway.

## Solution
Updated `data/etl/utils/league_directory_manager.py` to check for `CNSWPL_CRON_VARIABLE` environment variable. This allows scrapers to save files to a persistent volume location that matches what the import scripts expect.

### What Changed
- `LeagueDirectoryManager` now checks for `CNSWPL_CRON_VARIABLE` environment variable
- If set, uses that as the base directory (e.g., `/app/data/leagues` for volumes)
- If not set, defaults to `data/leagues` (works for local/dev)

### Railway Configuration Required

**1. Disable Health Check (CRITICAL for Cron Services)**
Cron services are NOT web servers and will fail health checks. In Railway:
- Go to your cron service settings (e.g., `CNSWPL_Cron_Service_Staging`)
- **Settings → Health Check**
- **Disable or remove the health check path** (set to empty or disable)
- Cron services run scripts on schedule and exit - they don't need health checks

**2. Attach Volume**
- Ensure a Railway Volume is created and attached to the cron service
- **Mount path:** `/app/data`
  - This matches where import scripts expect files (relative `data/leagues/...` resolves to `/app/data/leagues/...`)

**3. Add Environment Variable**
For the **CNSWPL_Cron_Service** (staging or production), add:
- **Name:** `CNSWPL_CRON_VARIABLE`
- **Value:** `/app/data/leagues`
  - This ensures scrapers save to the persistent volume location that matches import script expectations

### How It Works
With the volume mounted at `/app/data` and `CNSWPL_CRON_VARIABLE=/app/data/leagues`:
- Scraper writes to `/app/data/leagues/CNSWPL/match_scores.json` ✅ (persists on volume)
- Import reads from `data/leagues/CNSWPL/match_scores.json` ✅ (resolves to `/app/data/leagues/CNSWPL/match_scores.json`)
- Files persist across container restarts ✅
- Both scraper and import use the same persistent location ✅

### Troubleshooting

**Problem: Deployment fails with "Healthcheck failure"**
- **Solution:** Disable health check in cron service settings (see step 1 above)

**Problem: Files still saving to ephemeral filesystem instead of volume**
- Check that `CNSWPL_CRON_VARIABLE=/app/data/leagues` is set on the cron service (not main app)
- Check that volume is mounted at `/app/data` on the cron service
- Verify in logs: Files should show `/app/data/leagues/...` path
- Run diagnostic: `python3 scripts/check_cnswpl_json_location.py` (if available)

### Testing
After configuration:
1. Deploy the service (should succeed without health check errors)
2. SSH into the service: `railway shell --service CNSWPL_Cron_Service_Staging`
3. Run the scraper manually or wait for scheduled run
4. Check files: `ls -la /app/data/leagues/CNSWPL/` (should show JSON files)
5. Verify import can find files: `ls -la data/leagues/CNSWPL/` (should resolve to same location)
6. Exit and re-enter SSH: Files should still be there (persists on volume)

## Note
Other services (main app, etc.) don't need this variable - they'll continue using the default `data/leagues` path.

