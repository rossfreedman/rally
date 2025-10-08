# Upload and Run Career Stats Update via SSH

## Steps to Update Staging

### 1. SSH into Staging
```bash
railway ssh --environment staging
```

### 2. Create temp directory (on the server)
```bash
mkdir -p /tmp/rally_update
cd /tmp/rally_update
```

### 3. Upload files (from your local machine in a NEW terminal)
```bash
# Upload the JSON file
railway scp --environment staging data/leagues/APTA_CHICAGO/players_career_stats.json /tmp/rally_update/

# Upload the script
railway scp --environment staging scripts/update_production_career_stats.py /tmp/rally_update/
```

### 4. Run the script (back on the SSH session)
```bash
cd /tmp/rally_update
python3 update_production_career_stats.py staging
```

### 5. Clean up (after successful update)
```bash
rm -rf /tmp/rally_update
exit
```

## Steps to Update Production

Same steps, but replace `--environment staging` with `--environment production`:

### 1. SSH into Production
```bash
railway ssh --environment production
```

### 2. Create temp directory (on the server)
```bash
mkdir -p /tmp/rally_update
cd /tmp/rally_update
```

### 3. Upload files (from your local machine in a NEW terminal)
```bash
# Upload the JSON file
railway scp --environment production data/leagues/APTA_CHICAGO/players_career_stats.json /tmp/rally_update/

# Upload the script
railway scp --environment production scripts/update_production_career_stats.py /tmp/rally_update/
```

### 4. Run the script (back on the SSH session)
```bash
cd /tmp/rally_update
python3 update_production_career_stats.py production
```

### 5. Clean up (after successful update)
```bash
rm -rf /tmp/rally_update
exit
```

## Alternative: Use railway run

You can also run it directly from your local machine using Railway CLI:

```bash
# For staging:
railway run --environment staging python3 scripts/update_production_career_stats.py staging

# For production:
railway run --environment production python3 scripts/update_production_career_stats.py production
```

But this requires the JSON file to be accessible, so you'd need to ensure it's in the right location.

## Expected Output

```
🔄 Updating Career Stats in STAGING Database
============================================================
⚠️  WARNING: This will update staging database!
Database: switchback.proxy.rlwy.net:28473/railway
============================================================
📂 Loading career stats from: players_career_stats.json
✅ Loaded 6446 player records

🚀 Starting update to staging database...

✅ Connected to staging database

📊 Progress: 500 players updated...
📊 Progress: 1,000 players updated...
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
```

