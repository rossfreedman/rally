# Deployment Plan: Wilmette H(3) Match & Player Fix

**Status:** Ready for deployment  
**Date:** November 2, 2025  
**Fix Type:** Data import (matches + players)

## Overview

This plan deploys two fixes to staging and production:
1. **10/20 Match Import**: Import the 4 missing Wilmette H(3) vs Tennaqua H matches
2. **Player Name Fix**: Import 13 Wilmette H(3) players into the players table

## Safety Principles

1. ✅ **Always backup first** (database and code)
2. ✅ **Test on staging before production**
3. ✅ **Use SSH for production** (prevents long-running connection issues)
4. ✅ **Verify after each step**
5. ✅ **Rollback plan ready**

---

## Pre-Deployment Checklist

### 1. Backup Databases

**Staging:**
```bash
# Via Railway CLI or SSH
railway run --service <staging-service> python3 cb.py --database-only

# Or manually via SSH
railway ssh --service <staging-service>
pg_dump $DATABASE_URL > backup_staging_$(date +%Y%m%d_%H%M%S).sql
```

**Production:**
```bash
# Always backup production before any changes
railway ssh --service <production-service>
pg_dump $DATABASE_URL > backup_production_$(date +%Y%m%d_%H%M%S).sql

# Or use the backup script
python3 scripts/backup_production_database.py
```

### 2. Commit Code Changes

Ensure all code changes are committed:
- ✅ Debug logging in `import_match_scores.py`
- ✅ `fix_wilmette_h3_player_names.py` script
- ✅ `scrape_and_import_oct_20_match.py` script

```bash
git status
git add data/etl/import/import_match_scores.py scripts/fix_wilmette_h3_player_names.py scripts/scrape_and_import_oct_20_match.py
git commit -m "fix | Add debug logging and Wilmette H(3) player import script"
```

---

## STAGING Deployment

### Step 1: Deploy Code to Staging

```bash
# Merge and push to staging
git checkout staging
git merge main
git push origin staging

# Verify deployment succeeded
python3 scripts/check_deployment_status.py
```

### Step 2: Import Matches (Option A - Scrape Fresh)

If you want fresh data:
```bash
# SSH into staging cron service
railway ssh --service CNSWPL_Cron_Service_Staging

# Run the scraper for 10/20 only
python3 data/etl/scrapers/cnswpl_scrape_match_scores.py cnswpl --delta-mode --start-date 2025-10-20 --end-date 2025-10-20

# Import the matches
python3 data/etl/import/import_match_scores.py CNSWPL
```

### Step 2: Import Matches (Option B - Use Local JSON)

If you want to use the local JSON that's already scraped:
```bash
# Copy JSON to staging (via SSH or Railway volume)
# Then import
railway ssh --service <staging-app-service>
python3 data/etl/import/import_match_scores.py CNSWPL --file /path/to/match_scores.json
```

### Step 3: Import Players

```bash
# SSH into staging app service
railway ssh --service <staging-app-service>

# Run the player fix script
python3 scripts/fix_wilmette_h3_player_names.py
```

### Step 4: Verify Staging

```bash
# Check matches
railway ssh --service <staging-app-service>
python3 -c "
from database_config import get_db_url
import psycopg2
conn = psycopg2.connect(get_db_url())
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM match_scores WHERE league_id = 4785 AND match_date = '2025-10-20' AND tenniscores_match_id LIKE 'nndz-WWk2OHdyZnhqQT09%'\")
print(f'10/20 matches: {cur.fetchone()[0]}')
cur.execute(\"SELECT COUNT(*) FROM players WHERE team_id = 60050 AND league_id = 4785\")
print(f'Wilmette H(3) players: {cur.fetchone()[0]}')
"

# Test in staging UI
# Navigate to: https://rally-staging.up.railway.app/mobile/last-3-matches
# Verify player names display correctly
```

---

## PRODUCTION Deployment

**⚠️ Only proceed after staging is verified and working**

### Step 1: Backup Production Database

```bash
# Critical: Always backup production first
railway ssh --service <production-app-service>
pg_dump $DATABASE_URL > backup_production_pre_wilmette_fix_$(date +%Y%m%d_%H%M%S).sql

# Verify backup was created
ls -lh backup_production_pre_wilmette_fix_*.sql
```

### Step 2: Deploy Code to Production

```bash
git checkout main
git merge staging
git push origin main

# Verify deployment
python3 scripts/check_deployment_status.py
```

### Step 3: Import Matches on Production

**Option A: Scrape Fresh (Recommended)**
```bash
# SSH into production cron service
railway ssh --service CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am

# Run scraper for 10/20 only
python3 data/etl/scrapers/cnswpl_scrape_match_scores.py cnswpl --delta-mode --start-date 2025-10-20 --end-date 2025-10-20

# Import matches
python3 data/etl/import/import_match_scores.py CNSWPL
```

**Option B: Copy JSON from Staging**
```bash
# If staging volume has the JSON, copy it to production volume
# Then import via SSH
railway ssh --service <production-app-service>
python3 data/etl/import/import_match_scores.py CNSWPL
```

### Step 4: Import Players on Production

```bash
# SSH into production app service
railway ssh --service <production-app-service>

# Run the player fix script
python3 scripts/fix_wilmette_h3_player_names.py
```

### Step 5: Verify Production

```bash
# Verify data
railway ssh --service <production-app-service>
python3 -c "
from database_config import get_db_url
import psycopg2
conn = psycopg2.connect(get_db_url())
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM match_scores WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL') AND match_date = '2025-10-20' AND tenniscores_match_id LIKE 'nndz-WWk2OHdyZnhqQT09%'\")
print(f'✅ 10/20 matches: {cur.fetchone()[0]} (expected: 4)')
cur.execute(\"SELECT COUNT(*) FROM players WHERE team_id = (SELECT id FROM teams WHERE team_name = 'Wilmette H(3)') AND league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')\")
print(f'✅ Wilmette H(3) players: {cur.fetchone()[0]} (expected: 13+)')
"

# Test in production UI
# Navigate to production URL and verify player names display
```

---

## Rollback Plan

If something goes wrong:

### For Matches:
```sql
-- Delete the imported matches
DELETE FROM match_scores 
WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
AND match_date = '2025-10-20'
AND tenniscores_match_id LIKE 'nndz-WWk2OHdyZnhqQT09%';
```

### For Players:
```sql
-- Remove players that were just created (check timestamps)
DELETE FROM players 
WHERE team_id = (SELECT id FROM teams WHERE team_name = 'Wilmette H(3)')
AND league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
AND created_at > '2025-11-02';  -- Adjust date as needed
```

### Full Database Restore:
```bash
# Restore from backup
railway ssh --service <service-name>
psql $DATABASE_URL < backup_<timestamp>.sql
```

---

## Verification Checklist

After each deployment, verify:

- [ ] Database backup created
- [ ] Code deployed successfully
- [ ] Matches imported (4 matches for 10/20)
- [ ] Players imported (13+ Wilmette H(3) players)
- [ ] Player names display correctly in UI
- [ ] No errors in Railway logs
- [ ] Other functionality still works

---

## Recommended Order

1. **Staging First:**
   - Backup staging DB
   - Deploy code
   - Import matches
   - Import players
   - Verify & test UI

2. **Production (After Staging Verified):**
   - Backup production DB
   - Deploy code
   - Import matches
   - Import players
   - Verify & test UI

---

## Time Estimates

- **Staging:** 10-15 minutes
- **Production:** 10-15 minutes
- **Verification:** 5 minutes each

**Total:** ~30-40 minutes for both environments

---

## Notes

- **SSH is recommended** for production to avoid connection timeouts
- **Volume mounting** should be configured per `md/RAILWAY_VOLUME_SETUP.md`
- **Scripts are idempotent** - safe to run multiple times
- **Player script** updates existing players if they're on wrong team

