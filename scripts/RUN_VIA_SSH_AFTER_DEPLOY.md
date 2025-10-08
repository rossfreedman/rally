# Run Career Stats Update After Git Deploy

The files are now deployed via git to staging. Here's how to run the update script:

## For Staging

### 1. Wait for Railway to deploy the staging branch
Check the Railway dashboard to ensure the deployment is complete.

### 2. SSH into staging
```bash
railway ssh --environment staging
```

### 3. Navigate to the app directory and run the script
```bash
cd /app
python3 scripts/update_production_career_stats.py staging
```

### 4. Expected output
```
🔍 Auto-detected environment: STAGING
🔄 Updating Career Stats in STAGING Database
============================================================
⚠️  WARNING: This will update staging database!
Database: switchback.proxy.rlwy.net:28473/railway
============================================================
📂 Loading career stats from: data/leagues/APTA_CHICAGO/players_career_stats.json
✅ Loaded 6446 player records

🚀 Starting update to staging database...

✅ Connected to staging database

📊 Progress: 500 players updated...
...
📊 Progress: 4,500 players updated...

💾 Committing updates to staging database...
✅ All updates committed successfully!

============================================================
📊 STAGING UPDATE SUMMARY
============================================================
Total records in JSON: 6,446
Successfully updated: 4,913
Skipped (no player in DB): 0
Skipped (no career stats): 1,533
Errors: 0
============================================================

✨ Jeff Day Update Details:
   ...

🎉 Staging career stats update completed!
✅ 4,913 players in staging now have correct career stats!
```

### 5. Exit SSH
```bash
exit
```

## For Production

After verifying staging works:

### 1. Merge staging to production
```bash
# On your local machine
git checkout production
git merge staging
git push origin production
```

### 2. Wait for Railway to deploy

### 3. SSH into production
```bash
railway ssh --environment production
```

### 4. Run the script
```bash
cd /app
python3 scripts/update_production_career_stats.py production
```

### 5. Exit
```bash
exit
```

## Verification

After running on staging/production, verify Jeff Day's stats:

```bash
# In the SSH session or via psql
python3 -c "
import sys
sys.path.append('/app')
from database_utils import execute_query_one

jeff = execute_query_one('''
    SELECT first_name, last_name, career_wins, career_losses, career_win_percentage
    FROM players WHERE tenniscores_player_id = %s
''', ['nndz-WkMrK3didnhnUT09'])

print(f'{jeff[\"first_name\"]} {jeff[\"last_name\"]}: {jeff[\"career_wins\"]}W-{jeff[\"career_losses\"]}L ({jeff[\"career_win_percentage\"]}%)')
"
```

Expected: `Jeff Day: 13W-11L (54.20%)`

## Notes

- The script auto-detects the environment when run on Railway
- No confirmation prompt - it runs immediately
- All updates are in a single transaction (safe rollback on error)
- Takes a few minutes to update 4,913 players
- ETL fixes are also deployed, preventing future overwrites

