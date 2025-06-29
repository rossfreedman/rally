# Fix Glen Oak Availability Issue - Action Plan

## 🎯 Problem Identified
Glen Oak teams in SW series had no availability data due to SW series formatting bug in scrapers.

## ✅ Bug Fixed  
All scrapers now properly format SW series as "Chicago X SW" instead of "Series X SW":
- `scraper_schedule.py` ✅ Fixed
- `scraper_stats.py` ✅ Fixed  
- `scraper_match_scores.py` ✅ Fixed

## 🚀 Next Steps

### 1. Re-scrape APTA Chicago Schedules
```bash
cd /Users/rossfreedman/dev/rally
python data/etl/scrapers/scraper_schedule.py
# When prompted, enter: aptachicago
```

### 2. Re-import Data to Database
```bash
python data/etl/database_import/import_all_jsons_to_database.py
```

### 3. Test Glen Oak Availability
1. Login as Glen Oak player (nndz-WlNlN3liMzhoUT09)
2. Check availability page for schedule data
3. Verify Glen Oak SW teams now show match schedules

## 📊 Expected Results After Fix

**Before:**
- Glen Oak SW schedules: 0 entries
- Glen Oak availability: "No data"

**After:**  
- Glen Oak SW schedules: 50+ entries across multiple SW series
- Glen Oak availability: Full schedule showing upcoming matches

## 🔍 Verification Commands

```bash
# Check if SW schedules exist with correct format
grep -c "Chicago.*SW" data/leagues/APTA_CHICAGO/schedules.json

# Check if Glen Oak SW schedules exist  
grep -c "Glen Oak.*SW" data/leagues/APTA_CHICAGO/schedules.json

# Verify data consistency
python scripts/debug_sw_series_discovery.py
```

## 🎯 Key Glen Oak SW Teams to Verify
- Glen Oak - 11 SW (Series 11 SW)
- Glen Oak - 15 SW (Series 15 SW) 
- Glen Oak - 19 SW (Series 19 SW)
- Glen Oak - 23 SW (Series 23 SW)
- Glen Oak - 25 SW (Series 25 SW)
- Glen Oak I/II - 27 SW (Series 27 SW) 