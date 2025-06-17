# 🚀 ELT Quick Reference

Your complete guide to running the Rally ELT pipeline easily and repeatedly.

## 📁 File Locations

```
📂 rally/
├── 📁 etl/                              # Main ELT scripts
│   └── 📁 database_import/
│       └── json_import_all_to_database.py   # ⭐ MAIN ETL SCRIPT (includes career stats)
├── 📁 scripts/                         # Standalone utility scripts
│   └── import_career_stats.py          # ⚠️ DEPRECATED (use main ETL instead)
├── 📁 data/leagues/all/                 # Data sources
│   ├── players.json                     # Player data (from scrapers)
│   └── player_history.json             # Match history + career stats (from scrapers)
├── run_etl.py                          # 🆕 Command center (THIS IS WHAT YOU USE!)
└── validate_etl_pipeline.py            # 🆕 Proper validation
```

## 🎯 Simple Commands (Use These!)

### **Run Complete ELT Pipeline** ⭐ Most Common
```bash
# This now includes career stats automatically!
python etl/database_import/json_import_all_to_database.py
```

### **Alternative: Use Command Center** (if available)
```bash
python run_etl.py --run
```

### **Validate ELT Pipeline**
```bash
python validate_etl_pipeline.py
```

## 🔄 What Gets Imported (All in One Script!)

The main ETL script now imports **everything** in the correct order:

1. **Reference Data**: Leagues, clubs, series
2. **Relationships**: Club-league, series-league mappings  
3. **Players**: Current season data from `players.json`
4. **✨ Career Stats**: Career totals from `player_history.json` ← **NEW!**
5. **Player History**: Individual match records
6. **Match History**: All match results
7. **Series Stats**: Team performance data
8. **Schedules**: Upcoming matches

## ✅ Success Indicators

### **Complete Import Success:**
```
✅ Updated 2,102 players with career stats (0 not found, 0 errors)
✅ Imported 121,001 player history records (0 errors)
✅ ETL process completed successfully!

📊 IMPORT SUMMARY
   players             :      7,637 records
   career_stats        :      2,102 records  ← Look for this!
   player_history      :    121,001 records
   TOTAL               :    139,893 records
```

## 🚨 Important Changes (2025-06-16)

### **✅ What's New:**
- **Career stats now included** in main ETL script
- **Single script** handles everything 
- **No manual steps** required

### **⚠️ What's Deprecated:**
- `scripts/import_career_stats.py` is now **DEPRECATED**
- Don't run it separately anymore
- Main ETL script handles career stats automatically

### **🔄 Migration:**
**Before (2 steps):**
```bash
python etl/database_import/json_import_all_to_database.py
python scripts/import_career_stats.py  # ← Manual step
```

**After (1 step):**
```bash
python etl/database_import/json_import_all_to_database.py  # ← Everything included!
```

## 🎯 Quick Start for New Users

1. **First time setup:**
   ```bash
   # Check your data files exist
   ls -la data/leagues/all/players.json
   ls -la data/leagues/all/player_history.json
   ```

2. **Run the complete pipeline:**
   ```bash
   python etl/database_import/json_import_all_to_database.py
   ```

3. **Verify career stats were imported:**
   Look for this line in the output:
   ```
   ✅ Updated 2,102 players with career stats (0 not found, 0 errors)
   ```

## 💡 Pro Tips

- **Single script does everything**: No need for multiple manual steps
- **Career stats included**: Automatically imported from `player_history.json`
- **Check the summary**: Look for `career_stats: X records` in final summary
- **Don't use deprecated scripts**: Stick to the main ETL script

## 🚨 Troubleshooting

### **"Career stats not showing in UI"**
Check the ETL output for this line:
```bash
✅ Updated X players with career stats (0 not found, 0 errors)
```
If you see `Updated 0 players`, check that `player_history.json` exists and has career data.

### **"Database connection error"**
```bash
# Check database is running and accessible
python -c "from database_config import test_db_connection; test_db_connection()"
```

### **"Data files not found"**
```bash
# Make sure your JSON files exist:
ls -la data/leagues/all/players.json
ls -la data/leagues/all/player_history.json

# If missing, run your scrapers first
```

---

**That's it! Your ELT pipeline now handles career stats automatically in a single script.** 🚀 