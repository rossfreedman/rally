# Production SSH Instructions: Populate starting_pti

**Date:** October 19, 2025  
**Status:** ✅ Schema migration applied, ready for data population

---

## ✅ Completed: Schema Migration

The `starting_pti` column has been successfully added to production:

```sql
-- Production database status:
Total Players:        10,536
With starting_pti:         0  (ready to populate)

Column Details:
- starting_pti NUMERIC(5,2)
- Index: idx_players_starting_pti
```

---

## 🚀 SSH to Production and Populate Data

### Step 1: Open Railway Production Shell

In a **new interactive terminal**, run:

```bash
cd /Users/rossfreedman/dev/rally

# Link to production environment
railway link
# Select: rossfreedman's Projects > rally > production

# Open Railway shell
railway shell
```

---

### Step 2: Run Populate Script

Once in the Railway production shell, run:

```bash
# This will automatically use production DATABASE_URL
python scripts/populate_starting_pti.py
```

**Expected Output:**
```
📊 Loaded 5880 starting PTI records from CSV
   (Skipped 3245 rows with empty PTI values)
📊 Found 10536 active players in database

[... progress updates ...]

======================================================================
📊 SUMMARY
======================================================================
✅ Matches found:        5228
📝 Updates performed:    5228
⏭️  Already set:          0
⚠️  No CSV match:         5308

✅ Starting PTI population completed!
```

---

### Step 3: Verify Data Populated

After the script completes, verify in the same Railway shell:

```bash
# Quick verification (inside Railway shell)
psql $DATABASE_URL -c "SELECT COUNT(*) as total, COUNT(starting_pti) as populated FROM players WHERE is_active = true;"
```

**Expected Result:**
```
 total | populated 
-------+-----------
 10536 |      5228
```

---

### Step 4: Test Specific Record

Check Ross Freedman's record:

```bash
psql $DATABASE_URL -c "SELECT first_name, last_name, pti, starting_pti, (pti - starting_pti) as delta FROM players WHERE first_name = 'Ross' AND last_name = 'Freedman' LIMIT 1;"
```

**Expected Result:**
```
 first_name | last_name |  pti  | starting_pti | delta 
------------+-----------+-------+--------------+-------
 Ross       | Freedman  | 50.00 |        50.80 | -0.80
```

---

## Alternative: Direct psql Connection (if Railway shell unavailable)

If Railway shell is not available, you can populate directly via psql:

```bash
# From your local machine
export DATABASE_PUBLIC_URL="postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

python3 scripts/populate_starting_pti.py
```

**Note:** This will be slower due to network latency for 5,228 UPDATE queries.

---

## Verification After Population

### From Local Machine:

```bash
# Check count
psql "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway" \
  -c "SELECT COUNT(*) as total, COUNT(starting_pti) as populated FROM players WHERE is_active = true;"

# Check sample data
psql "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway" \
  -c "SELECT first_name, last_name, pti, starting_pti, (pti - starting_pti) as delta FROM players WHERE starting_pti IS NOT NULL ORDER BY RANDOM() LIMIT 5;"
```

---

## What Happens After Population

Once the data is populated:

1. **Immediate Effect:** Production analyze-me page will start showing PTI deltas from database
2. **No Code Deployment Needed:** Code already deployed (same as staging)
3. **Performance Improvement:** ~90% faster PTI lookups
4. **Data Source:** Database queries instead of CSV file reads

---

## Troubleshooting

### If Railway CLI doesn't work:

```bash
# Update Railway CLI
brew upgrade railway

# Or reinstall
brew uninstall railway
brew install railway
```

### If script fails partway:

The script is idempotent - you can safely re-run it. It will:
- Skip already-populated records (⏭️ Already set)
- Only update records that need updating

### Check logs:

```bash
# Inside Railway shell
tail -f /app/logs/populate_starting_pti.log
```

---

## Current Status

- ✅ Schema migration applied to production
- ✅ Column: `starting_pti NUMERIC(5,2)` exists
- ✅ Index: `idx_players_starting_pti` created
- ⏳ Data: Ready to populate (0/5228 currently)
- ✅ Code: Already deployed on production

**Next step:** SSH to production and run `python scripts/populate_starting_pti.py`

