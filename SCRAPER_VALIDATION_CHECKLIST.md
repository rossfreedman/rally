# CNSWPL Scraper Validation Checklist

## ✅ Success Indicators to Look For

### 1. All Steps Completed Successfully

Look for these messages in order:

```
✅ Scrape CNSWPL Players completed successfully
✅ Import CNSWPL Players completed successfully
✅ Scrape CNSWPL Match Scores completed successfully
✅ Import CNSWPL Match Scores completed successfully
✅ Scrape CNSWPL Series Stats completed successfully
✅ Import CNSWPL Series Stats completed successfully
🎉 Rally CNSWPL Full Runner Completed Successfully!
```

### 2. File Save Confirmation

**Match Scores File:**
```
💾 Saved final matches file: /app/data/leagues/CNSWPL/match_scores.json
📁 Results saved to: /app/data/leagues/CNSWPL/match_scores.json
✅ Successfully extracted X matches this run
```

**Players File:**
```
📁 Results saved to: /app/data/leagues/CNSWPL/players.json
```

**Stats File:**
```
📁 Results saved to: /app/data/leagues/CNSWPL/series_stats.json
```

### 3. Import Statistics

**Match Scores Import:**
```
Loaded X match records
Match scores: X inserted, Y updated, Z existing, 0 skipped, 0 validation failed
```

**Players Import:**
```
Loaded X player records
```

**Stats Import:**
```
Loaded X stat records
```

### 4. Path Confirmation

**Verify paths are correct (should show volume path):**
```
Input file: /app/data/leagues/CNSWPL/match_scores.json
```

**NOT:**
```
Input file: data/leagues/CNSWPL/match_scores.json  ❌ (relative path)
```

### 5. Integrity Checks

```
🔍 Running post-import integrity checks...
  ✅ All matches have proper team assignments
  ✅ No duplicate match records found
  ✅ All matches have dates
📊 Integrity check summary: 0 issues found
```

## ❌ Error Indicators to Watch For

### Critical Errors:
- `ERROR: File not found: data/leagues/CNSWPL/match_scores.json`
- `❌ Import CNSWPL Match Scores failed`
- `💥 Rally CNSWPL Full Runner Failed!`
- `Command returned non-zero exit status`

### Warning Signs:
- `⚠️ No new matches were extracted in this run` (might be OK if no new data)
- `⚠️ Could not import fix_team_names_from_players` (non-critical)

## 🔍 How to Check Logs

### Option 1: Railway Dashboard
1. Go to: https://railway.app
2. Select service: `CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am`
3. Click **"View Logs"** or **"Deployments"**
4. Look for most recent deployment/run
5. Scroll through logs looking for success indicators above

### Option 2: Railway CLI
```bash
railway logs --service CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am
```

### Option 3: SSH and Verify Files
```bash
railway shell --service CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am

# Check files exist with recent timestamps
ls -lh /app/data/leagues/CNSWPL/match_scores.json
ls -lh /app/data/leagues/CNSWPL/players.json
ls -lh /app/data/leagues/CNSWPL/series_stats.json

# Check file sizes (should be > 0)
du -h /app/data/leagues/CNSWPL/*.json

# Verify file content (first few lines)
head -20 /app/data/leagues/CNSWPL/match_scores.json
```

## 📊 Expected Results

### Successful Run Should Show:

1. **Total Duration**: Reasonable time (varies by data size)
2. **All 6 steps completed**: ✅ for each step
3. **Final message**: "🎉 Rally CNSWPL Full Runner Completed Successfully!"
4. **Files created**: match_scores.json, players.json, series_stats.json
5. **Files on volume**: `/app/data/leagues/CNSWPL/` (persistent location)
6. **Import stats**: At least some matches/players/stats imported
7. **No errors**: Clean run with no failure messages

## 🚨 Red Flags

If you see any of these, investigate:
- ❌ "File not found" errors
- ❌ Import step fails
- ❌ Files saved to wrong location (e.g., `/data/` instead of `/app/data/leagues/`)
- ❌ "Command returned non-zero exit status"
- ❌ Container restarts between scraper and import
- ❌ Zero records imported when there should be data

## ✅ Quick Validation Commands

After checking logs, verify files exist:

```bash
# In Railway SSH
railway shell --service CNSWPL_Cron_Service_Prod_Mon_Tues_Sat_9am

# Check all files
ls -lht /app/data/leagues/CNSWPL/*.json | head -5

# Verify match_scores.json exists and is recent
stat /app/data/leagues/CNSWPL/match_scores.json

# Check file is valid JSON
python3 -c "import json; f=open('/app/data/leagues/CNSWPL/match_scores.json'); data=json.load(f); print(f'Valid JSON with {len(data)} matches')"
```

## 📝 Validation Summary

- [ ] All 6 steps show ✅ success messages
- [ ] Final completion message appears
- [ ] Files saved to `/app/data/leagues/CNSWPL/` (volume location)
- [ ] Import shows records loaded and imported
- [ ] Integrity checks pass (0 issues)
- [ ] No "File not found" errors
- [ ] Files exist with recent timestamps
- [ ] Files are valid JSON

If all checked, the scraper run was successful! ✅

