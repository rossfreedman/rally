# Production Deployment Checklist - Substitute Player Fix

## Current Status

### ✅ **Completed (Local & Production Database)**
1. ✅ Fixed Denise Siegel's user account in production
2. ✅ Cleaned up 106 (S) duplicate records in production database
3. ✅ Modified scraper code files (2 files)
4. ✅ Tested locally - full scraper run validated (0 new (S) records)

### ⚠️ **NOT YET DEPLOYED (Code Changes)**
❌ Scraper code changes are only on local machine
❌ Production Railway instance still has OLD scraper code
❌ Next production cron run could create new (S) duplicates

---

## What Needs to Happen Next

### **CRITICAL: Deploy Scraper Code Changes**

Railway deploys from **git repository**, not local files. [[memory:535684]]

**Files Modified (need to be committed and pushed):**
1. `data/etl/scrapers/cnswpl/cnswpl_scrape_players_simple.py`
2. `data/etl/scrapers/cnswpl_scrape_match_scores.py`

**Changes Made:**
- Added `'(S)'` and `'(S↑)'` to substitute detection
- Enhanced match scraper to clean (S) from player names

---

## Step-by-Step Deployment Plan

### **Step 1: Check Current Git Status**
```bash
git status
```

**Expected:** 2 modified files in scrapers

---

### **Step 2: Review Changes**
```bash
git diff data/etl/scrapers/cnswpl/cnswpl_scrape_players_simple.py
git diff data/etl/scrapers/cnswpl_scrape_match_scores.py
```

**Verify:** (S) filter additions are correct

---

### **Step 3: Commit Changes**
```bash
git add data/etl/scrapers/cnswpl/cnswpl_scrape_players_simple.py
git add data/etl/scrapers/cnswpl/cnswpl_scrape_match_scores.py
git commit -m "fix | Prevent duplicate (S) player records in CNSWPL scrapers

- Enhanced cnswpl_scrape_players_simple.py to filter '(S)' and '(S↑)' suffixes
- Updated cnswpl_scrape_match_scores.py to clean (S) from player names
- Prevents creation of duplicate player records for substitutes
- Fixes support issue where users see wrong teams due to (S) duplicates
- Validated: 82-minute scraper run created 0 new (S) records
- Database cleanup: 106 legacy (S) records deactivated in production"
```

---

### **Step 4: Push to Git**
```bash
# Check which branch you're on
git branch

# Push to main (or appropriate branch)
git push origin main
```

---

### **Step 5: Verify Railway Deployment**
```bash
python scripts/check_deployment_status.py
```

**Wait for:** Railway to detect the push and redeploy (usually 1-2 minutes)

**Verify:** Deployment shows the new scraper code

---

### **Step 6: Monitor Next Production Cron Run**

**When:** Next scheduled CNSWPL scraper run

**Check After Run:**
```bash
# Run validation against production database
python3 scripts/production_validate_no_new_s_records.py
```

**Expected:**
- ✅ No new (S) player records created
- ✅ 170 active (S) records (unchanged)
- ✅ 106 inactive (S) records (unchanged)

---

## Verification Commands

### **Check if changes are on production:**
```bash
# SSH into Railway or check git commit hash
python scripts/check_deployment_status.py
```

### **After next cron run, validate:**
```bash
# Query production database
python3 << 'EOF'
import psycopg2
conn = psycopg2.connect("postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM players WHERE (first_name LIKE '%(S)' OR last_name LIKE '%(S)') AND is_active = true")
print(f"Active (S) records: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM players WHERE created_at > NOW() - INTERVAL '1 day' AND (first_name LIKE '%(S)' OR last_name LIKE '%(S)')")
print(f"(S) records created today: {cursor.fetchone()[0]}")
cursor.close()
conn.close()
EOF
```

---

## Risk Assessment

### **Current Risk:** 🟡 MEDIUM

**Why?**
- ✅ Database cleanup complete in production
- ❌ Code changes NOT deployed to production yet
- ⚠️ Next cron run could create new (S) records with old code

### **After Deployment:** 🟢 LOW

**Why?**
- ✅ Database cleanup complete
- ✅ Code changes deployed
- ✅ Validated locally
- ✅ Rollback available

---

## Timeline

| Step | Status | When |
|------|--------|------|
| Fix Denise's account | ✅ Done | Oct 14 (today) |
| Clean up 106 (S) records | ✅ Done | Oct 14 (today) |
| Fix scraper code | ✅ Done | Oct 14 (today) |
| Test locally | ✅ Done | Oct 14 (today) |
| **Commit & push code** | ⏳ **NEXT** | **Now** |
| Verify Railway deployment | ⏳ Pending | After push |
| Monitor next cron run | ⏳ Pending | Next scheduled run |

---

## Success Criteria

After deployment, production should have:
1. ✅ 170 active (S) records (legitimate substitute-only players)
2. ✅ 106 inactive (S) records (cleaned up duplicates)
3. ✅ 0 new (S) records created after next cron run
4. ✅ Denise sees Series I team correctly

---

## Rollback Plan

If issues arise after deployment:

**Option 1: Revert Code**
```bash
git revert <commit-hash>
git push origin main
```

**Option 2: Reactivate (S) Records**
```sql
UPDATE players SET is_active = true 
WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)';
```

**Option 3: Full Database Restore**
```bash
pg_restore backups/production_backup_before_substitute_cleanup_20251014_105223.dump
```

---

## Next Action Required

🔴 **IMMEDIATE:** Commit and push scraper changes to git

**Command:**
```bash
git add data/etl/scrapers/cnswpl/cnswpl_scrape_players_simple.py \
        data/etl/scrapers/cnswpl_scrape_match_scores.py
git commit -m "fix | Prevent duplicate (S) player records in CNSWPL scrapers"
git push origin main
```

**Why Urgent:** Next cron run could happen anytime and would use old code!

---

**Status:** ⚠️ WAITING FOR CODE DEPLOYMENT

