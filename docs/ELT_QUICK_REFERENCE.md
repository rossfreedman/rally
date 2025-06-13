# 🚀 ELT Quick Reference

Your complete guide to running the Rally ELT pipeline easily and repeatedly.

## 📁 File Locations

```
📂 rally/
├── 📁 etl/                              # Main ELT scripts
│   ├── run_all_etl.py                   # Master script
│   ├── import_reference_data.py         # Step 1: Leagues, clubs, series
│   ├── import_players.py                # Step 2: Players
│   ├── import_career_stats.py           # Step 3: Career stats
│   └── import_player_history.py         # Step 4: Match history
├── 📁 data/leagues/all/                 # Data sources
│   ├── players.json                     # Player data (from scrapers)
│   └── player_history.json             # Match history (from scrapers)
├── run_etl.py                          # 🆕 Command center (THIS IS WHAT YOU USE!)
└── validate_etl_pipeline.py            # 🆕 Proper validation
```

## 🎯 Simple Commands (Use These!)

### **See All Options**
```bash
python run_etl.py --help
```

### **Run Complete ELT Pipeline** ⭐ Most Common
```bash
python run_etl.py --run
```

### **Test Run (No Database Changes)**
```bash
python run_etl.py --dry-run
```

### **Validate ELT Pipeline**
```bash
python run_etl.py --validate
```

### **Run ELT + Validate** ⭐ Recommended
```bash
python run_etl.py --run --validate
```

### **Run Scripts One by One** (for debugging)
```bash
python run_etl.py --individual
```

### **Show File Locations**
```bash
python run_etl.py --files
```

## 🔄 Typical Workflow

### **1. Daily/Weekly Data Update**
```bash
# Step 1: Run your scrapers (separate process)
# Step 2: Run ELT pipeline
python run_etl.py --run
```

### **2. Test Before Important Updates**
```bash
# Test first
python run_etl.py --dry-run

# If looks good, run for real
python run_etl.py --run
```

### **3. Full Validation** (after changes to scripts)
```bash
python run_etl.py --run --validate
```

## 📊 What Each Command Does

| Command | What It Does |
|---------|-------------|
| `--run` | Imports all JSON data to database |
| `--validate` | Tests if scripts work correctly |
| `--dry-run` | Shows what would happen (no changes) |
| `--individual` | Runs scripts one by one with prompts |
| `--files` | Shows where everything is located |

## ✅ Success Indicators

### **ELT Run Success:**
```
✅ ELT Pipeline - SUCCESS
🎉 All operations completed successfully!
   Your database has been updated with the latest data.
```

### **Validation Success:**
```
🎯 ELT PIPELINE VALIDATION RESULTS
Overall Status: ✅ PASS
📋 Test Results:
   Script Reliability: ✅ PASS
   JSON Completeness:  ✅ PASS  
   Data Integrity:     ✅ PASS
```

## 🚨 Troubleshooting

### **"Data files not found"**
```bash
# Make sure your JSON files exist:
ls -la data/leagues/all/players.json
ls -la data/leagues/all/player_history.json

# If missing, run your scrapers first
```

### **"ELT Pipeline FAILED"**
```bash
# Run individual scripts to see which one fails:
python run_etl.py --individual
```

### **"Database connection error"**
```bash
# Check database is running and accessible
python -c "from database_config import test_db_connection; test_db_connection()"
```

## 🎯 Quick Start for New Users

1. **First time setup:**
   ```bash
   python run_etl.py --files        # See where everything is
   python run_etl.py --dry-run      # Test without changes
   ```

2. **Run the pipeline:**
   ```bash
   python run_etl.py --run --validate
   ```

3. **Regular updates:**
   ```bash
   python run_etl.py --run
   ```

## 💡 Pro Tips

- **Always validate after script changes:** `--run --validate`
- **Use dry-run first:** Test with `--dry-run` before real runs
- **Check data files:** Make sure JSON files are fresh from scrapers
- **Individual mode for debugging:** Use `--individual` to debug issues
- **Keep it simple:** Use `run_etl.py` instead of running scripts manually

---

**That's it! Your ELT pipeline is now super easy to run and repeat.** 🚀 