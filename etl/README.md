# ETL Scripts

## comprehensive_json_import.py

A comprehensive ETL script that imports data from JSON files in `data/leagues/all/` into the PostgreSQL database in the correct order based on foreign key constraints.

### Overview

This script imports data from the following JSON files:
1. `players.json` - Player information including league, club, series associations
2. `player_history.json` - Historical PTI data for players across different dates  
3. `match_history.json` - Individual match results and scores
4. `series_stats.json` - Team statistics by series within leagues
5. `schedules.json` - Upcoming match schedules

### Import Order

The script imports data in the following dependency order to respect foreign key constraints:

1. **Extract and import leagues** from `players.json` → `leagues` table
2. **Extract and import clubs** from `players.json` → `clubs` table  
3. **Extract and import series** from `players.json` → `series` table
4. **Analyze and import club-league relationships** → `club_leagues` table
5. **Analyze and import series-league relationships** → `series_leagues` table
6. **Import players** from `players.json` → `players` table
7. **Import player history** from `player_history.json` → `player_history` table
8. **Import match history** from `match_history.json` → `match_scores` table
9. **Import series stats** from `series_stats.json` → `series_stats` table
10. **Import schedules** from `schedules.json` → `schedule` table

### Features

- **Automatic data clearing**: Clears existing data from target tables before import
- **Foreign key constraint handling**: Imports data in the correct order
- **Comprehensive error handling**: Rollback on failure
- **Progress monitoring**: Real-time logging and progress updates
- **Data validation**: Handles invalid data values (e.g., 'unknown' winner values)
- **Batch processing**: Commits data in batches for better performance

### Usage

```bash
# Run the ETL script
python etl/comprehensive_json_import.py
```

### Output

The script provides detailed logging including:
- File loading progress
- Data extraction statistics  
- Import progress with record counts
- Error reporting
- Final summary with total imported records

### Sample Output

```
🚀 Starting Comprehensive JSON ETL Process
============================================================
📂 Step 1: Loading JSON files...
✅ Loaded 3,111 records from players.json
✅ Loaded 2,102 records from player_history.json
✅ Loaded 6,446 records from match_history.json
✅ Loaded 208 records from series_stats.json
✅ Loaded 1,909 records from schedules.json

📋 Step 2: Extracting reference data...
✅ Found 2 unique leagues: APTA_CHICAGO, NSTF
✅ Found 45 unique clubs
✅ Found 23 unique series
✅ Found 53 club-league relationships
✅ Found 23 series-league relationships

📥 Step 4: Importing data in dependency order...
✅ Imported 2 leagues
✅ Imported 45 clubs
✅ Imported 23 series
✅ Imported 53 club-league relationships
✅ Imported 23 series-league relationships
✅ Imported 3,111 players (0 errors)
✅ Imported 118,866 player history records (0 errors)
✅ Imported 6,446 match history records (0 errors)
✅ Imported 28 series stats records (0 errors)
✅ Imported 1,857 schedule records (0 errors)

🎉 ETL process completed successfully!
Total: 130,454 records imported
```

### Requirements

- PostgreSQL database with proper schema
- Python packages: `psycopg2`, `python-dotenv`
- JSON files in `data/leagues/all/` directory
- Database connection configured via `DATABASE_URL` environment variable

### Error Handling

- **Rollback on failure**: If any errors occur, all changes are rolled back
- **Transaction management**: Uses database transactions to ensure data consistency
- **Error logging**: Comprehensive error reporting with specific error details
- **Data validation**: Handles invalid data formats and missing fields gracefully

### Notes

- The script clears all existing data from target tables before importing
- Uses batch commits for better performance with large datasets
- Validates data constraints (e.g., winner field must be 'home' or 'away')
- Handles nested JSON structures (e.g., player history matches within player records)
- Maps tenniscores player IDs to database player IDs for relationships 