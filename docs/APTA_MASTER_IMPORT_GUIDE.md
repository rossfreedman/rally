# APTA Master Import Guide

## Overview

The APTA Master Import system provides a comprehensive, automated solution for importing all APTA data in the correct sequence. This system ensures data consistency, prevents common issues, and provides detailed logging and validation.

## Scripts

### 1. `scripts/apta_master_import.py` - Main Python Script

The core Python script that orchestrates the entire import process.

**Features:**
- Automated execution of all import steps
- Comprehensive error handling and logging
- Dry-run mode for testing
- Detailed progress reporting
- Validation and summary reporting

### 2. `scripts/run_apta_import.sh` - Bash Wrapper

A convenient bash wrapper that provides a simple interface to the Python script.

**Features:**
- Colored output for better readability
- Command-line argument parsing
- Error handling and validation
- Easy-to-use interface

## Usage

### Basic Usage

```bash
# Run complete APTA import
./scripts/run_apta_import.sh

# Or using Python directly
python3 scripts/apta_master_import.py
```

### Advanced Usage

```bash
# Dry run (show what would be done without executing)
./scripts/run_apta_import.sh --dry-run

# Skip validation step
./scripts/run_apta_import.sh --skip-validation

# Process different league
./scripts/run_apta_import.sh --league CNSWPL

# Combine options
./scripts/run_apta_import.sh --league APTA_CHICAGO --dry-run
```

### Python Script Options

```bash
python3 scripts/apta_master_import.py [OPTIONS]

Options:
  --league LEAGUE        League to process (default: APTA_CHICAGO)
  --dry-run             Show what would be done without executing
  --skip-validation     Skip final validation step
  --help               Show help message
```

## Import Process

The master script executes the following steps in sequence:

### Step 1: End Season
- **Script:** `scripts/end_season_auto.py`
- **Purpose:** Clear all existing season data
- **Actions:**
  - Delete all schedules
  - Delete all match scores
  - Delete all series stats
  - Delete all player availability
  - Delete all teams, series, clubs, and players
  - Preserve user accounts and associations

### Step 2: Start Season
- **Script:** `data/etl/import/start_season.py`
- **Purpose:** Create the foundational data structure
- **Actions:**
  - Create clubs from player data
  - Create series (including SW series)
  - Create teams with proper club/series assignments
  - Create players with team assignments
  - Run integrity checks

### Step 3: Import Players
- **Script:** `data/etl/import/import_players.py`
- **Purpose:** Import comprehensive player data with career stats
- **Actions:**
  - Import player data from `players.json`
  - Import career stats from `player_history.json`
  - Ensure career stats consistency across team assignments
  - Run integrity checks

### Step 4: Import Schedules
- **Script:** `data/etl/import/import_schedules.py`
- **Purpose:** Import schedule data
- **Actions:**
  - Import schedule data from `schedules.json`
  - Match teams to schedule entries
  - Handle team name variations
  - Run integrity checks

### Step 5: Import Series History
- **Script:** `data/etl/import/import_series_history.py`
- **Purpose:** Import player history data
- **Actions:**
  - Import player history from `player_history.json`
  - Bulk insert for performance
  - Run integrity checks

### Step 6: Validation
- **Script:** `scripts/validate_apta_data.py`
- **Purpose:** Comprehensive data validation
- **Actions:**
  - Validate league, clubs, series, teams, players
  - Check for data consistency
  - Report any issues found

## Key Features

### 1. Career Stats Consistency
- **Problem Solved:** Players on multiple teams had inconsistent career stats
- **Solution:** Automatic consistency checking and fixing during import
- **Implementation:** Real-time consistency checks + post-import cleanup

### 2. Generic Series Prevention
- **Problem Solved:** Creation of generic "Series SW" instead of specific series
- **Solution:** Enhanced parsing logic and fallback handling
- **Implementation:** Improved `parse_team_name` function with proper SW series detection

### 3. Comprehensive Error Handling
- **Feature:** Each step is executed independently with error handling
- **Benefit:** If one step fails, you know exactly which step and why
- **Implementation:** Individual step functions with success/failure reporting

### 4. Dry Run Mode
- **Feature:** Test the import process without actually executing
- **Benefit:** Verify the process will work before running it
- **Usage:** `--dry-run` flag

### 5. Detailed Logging
- **Feature:** Timestamped logging with different levels
- **Benefit:** Easy to track progress and debug issues
- **Implementation:** Structured logging with INFO, ERROR, WARNING levels

## Output Example

```
[23:47:56] INFO: 🚀 Starting APTA Master Import Process
[23:47:56] INFO: League: APTA_CHICAGO
[23:47:56] INFO: Dry Run: False
[23:47:56] INFO: Skip Validation: False
[23:47:56] INFO: ============================================================
[23:47:56] INFO: STEP 1: ENDING SEASON
[23:47:56] INFO: ============================================================
[23:47:56] INFO: Running: End Season
[23:47:56] INFO: ✅ End Season completed successfully
[23:47:56] INFO: ============================================================
[23:47:56] INFO: STEP 2: STARTING SEASON
[23:47:56] INFO: ============================================================
[23:47:56] INFO: Running: Start Season
[23:47:56] INFO: ✅ Start Season completed successfully
...
[23:47:56] INFO: ============================================================
[23:47:56] INFO: IMPORT SUMMARY
[23:47:56] INFO: ============================================================
[23:47:56] INFO: End Season           | ✅ Success       | Cleared all season data
[23:47:56] INFO: Start Season         | ✅ Success       | Created clubs, series, teams, and players
[23:47:56] INFO: Import Players       | ✅ Success       | Imported players with career stats
[23:47:56] INFO: Import Schedules     | ✅ Success       | Imported schedule data
[23:47:56] INFO: Import Series History | ✅ Success       | Imported player history data
[23:47:56] INFO: Validation           | ✅ Success       | Data validation completed
[23:47:56] INFO: ============================================================
[23:47:56] INFO: Total execution time: 0:05:23.123456
[23:47:56] INFO: Results: 6 successful, 0 warnings, 0 failed
[23:47:56] INFO: 🎉 All steps completed successfully!
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x scripts/run_apta_import.sh
   chmod +x scripts/apta_master_import.py
   ```

2. **Python Not Found**
   ```bash
   # Make sure Python 3 is installed and in PATH
   which python3
   ```

3. **Database Connection Issues**
   - Check `database_config.py` settings
   - Ensure PostgreSQL is running
   - Verify database credentials

4. **Missing Data Files**
   - Ensure `data/leagues/APTA_CHICAGO/` directory exists
   - Check for required JSON files:
     - `players.json`
     - `schedules.json`
     - `player_history.json`

### Debug Mode

For detailed debugging, run individual steps:

```bash
# Test individual steps
python3 scripts/end_season_auto.py APTA_CHICAGO
python3 data/etl/import/start_season.py APTA_CHICAGO
python3 data/etl/import/import_players.py APTA_CHICAGO
python3 data/etl/import/import_schedules.py APTA_CHICAGO
python3 data/etl/import/import_series_history.py APTA_CHICAGO
python3 scripts/validate_apta_data.py
```

## Best Practices

1. **Always run dry-run first** to verify the process
2. **Backup your database** before running the import
3. **Check validation results** for any data issues
4. **Monitor logs** for any warnings or errors
5. **Test in staging** before running in production

## File Structure

```
scripts/
├── apta_master_import.py      # Main Python script
├── run_apta_import.sh         # Bash wrapper
├── end_season_auto.py         # Automated end season
└── validate_apta_data.py      # Data validation

data/etl/import/
├── start_season.py            # Start season script
├── import_players.py          # Player import with career stats
├── import_schedules.py        # Schedule import
└── import_series_history.py   # Series history import

docs/
└── APTA_MASTER_IMPORT_GUIDE.md # This guide
```

## Support

For issues or questions:
1. Check the logs for specific error messages
2. Run individual steps to isolate the problem
3. Use dry-run mode to test changes
4. Review the validation output for data issues
