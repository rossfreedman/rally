# APTA Master Import - Quick Reference

## Quick Commands

```bash
# Run complete APTA import
./scripts/run_apta_import.sh

# Test what would be done (dry run)
./scripts/run_apta_import.sh --dry-run

# Skip validation step
./scripts/run_apta_import.sh --skip-validation

# Process different league
./scripts/run_apta_import.sh --league CNSWPL

# Show help
./scripts/run_apta_import.sh --help
```

## Python Script Commands

```bash
# Run complete import
python3 scripts/apta_master_import.py

# Dry run
python3 scripts/apta_master_import.py --dry-run

# Skip validation
python3 scripts/apta_master_import.py --skip-validation

# Different league
python3 scripts/apta_master_import.py --league CNSWPL

# Show help
python3 scripts/apta_master_import.py --help
```

## Individual Step Commands

```bash
# Step 1: End Season
python3 scripts/end_season_auto.py APTA_CHICAGO

# Step 2: Start Season
python3 data/etl/import/start_season.py APTA_CHICAGO

# Step 3: Import Players
python3 data/etl/import/import_players.py APTA_CHICAGO

# Step 4: Import Schedules
python3 data/etl/import/import_schedules.py APTA_CHICAGO

# Step 5: Import Series History
python3 data/etl/import/import_series_history.py APTA_CHICAGO

# Step 6: Validation
python3 scripts/validate_apta_data.py
```

## What the Master Script Does

1. **End Season** - Clears all existing season data
2. **Start Season** - Creates clubs, series, teams, and players
3. **Import Players** - Imports player data with career stats (with consistency checking)
4. **Import Schedules** - Imports schedule data
5. **Import Series History** - Imports player history data
6. **Validation** - Runs comprehensive data validation

## Key Features

- ✅ **Career Stats Consistency** - Automatically ensures consistent career stats across team assignments
- ✅ **Generic Series Prevention** - Prevents creation of generic "Series SW"
- ✅ **Comprehensive Error Handling** - Each step runs independently with detailed error reporting
- ✅ **Dry Run Mode** - Test the process without executing
- ✅ **Detailed Logging** - Timestamped logs with progress tracking
- ✅ **Validation** - Comprehensive data validation and reporting

## Troubleshooting

```bash
# Check if scripts are executable
chmod +x scripts/run_apta_import.sh
chmod +x scripts/apta_master_import.py

# Test individual steps if master script fails
python3 scripts/validate_apta_data.py

# Check database connection
python3 -c "from database_config import get_db; print('DB OK')"
```

## Files Created

- `scripts/apta_master_import.py` - Main Python script
- `scripts/run_apta_import.sh` - Bash wrapper
- `docs/APTA_MASTER_IMPORT_GUIDE.md` - Comprehensive guide
- `docs/CAREER_STATS_CONSISTENCY_GUIDE.md` - Career stats guide
- `docs/PREVENT_GENERIC_SERIES_GUIDE.md` - Generic series prevention guide
