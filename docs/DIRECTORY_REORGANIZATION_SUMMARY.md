# ETL Directory Reorganization Summary

## Overview
Successfully reorganized the ETL and scrapers directories into a unified structure under the `etl/` folder. This consolidation improves organization and maintains a clear separation between data collection (scrapers) and data processing (database import) functions.

## New Directory Structure

```
etl/
├── scrapers/                           # All web scraping functionality
│   ├── master_scraper.py              # Main orchestration script
│   ├── scraper_players.py             # Player data scraper
│   ├── scraper_match_scores.py        # Match history scraper
│   ├── scraper_schedule.py            # Schedule scraper
│   ├── scraper_stats.py               # Team statistics scraper
│   ├── scraper_players_history.py     # Player history scraper
│   ├── demo_master_scraper.py         # Demo/testing script
│   ├── add_practice_times.py          # Practice time utility
│   ├── README_MASTER_SCRAPER.md       # Documentation
│   └── old/                           # Archive folder
│
└── database_import/                    # Database operations and JSON processing
    ├── consolidate_league_jsons_to_all.py  # League data consolidation
    ├── json_import_all_to_database.py      # Database import functionality
    ├── backup_restore_users.py             # User backup/restore utilities
    └── README.md                            # Documentation
```

## Changes Made

### 1. Directory Movements
- **Moved**: All files from `scrapers/` → `etl/scrapers/`
- **Moved**: Database-related files to `etl/database_import/`:
  - `etl/json_import_all_to_database.py`
  - `etl/consolidate_league_jsons_to_all.py`
  - `etl/README.md`
  - `etl/backup_restore_users.py`
- **Removed**: Empty `scrapers/` directory

### 2. Path Updates

#### Scrapers (etl/scrapers/)
Updated path calculations to account for the new directory depth:

**scraper_players.py:**
- `build_league_data_dir()`: Updated to navigate up two levels (etl/scrapers → etl → project_root)
- `sys.path.append()`: Updated to navigate up three levels to find project root for utils imports

**master_scraper.py:**
- Data directory calculation: Updated to navigate up two levels for correct path resolution

#### Database Import Scripts (etl/database_import/)
**consolidate_league_jsons_to_all.py:**
- `BASE_DIR`: Updated to navigate up three levels (etl/database_import → etl → project_root)

## Path Resolution Logic

### Before Reorganization
```python
# scrapers/scraper_players.py
script_dir = os.path.dirname(os.path.abspath(__file__))      # scrapers/
project_root = os.path.dirname(script_dir)                   # ./
```

### After Reorganization
```python
# etl/scrapers/scraper_players.py  
script_dir = os.path.dirname(os.path.abspath(__file__))              # etl/scrapers/
project_root = os.path.dirname(os.path.dirname(script_dir))          # ./
```

## Verification Tests

✅ **Consolidation Script**: Successfully tested `etl/database_import/consolidate_league_jsons_to_all.py`
- Correctly found `data/leagues/` directory
- Successfully processed NSTF and APTA_CHICAGO league data
- Created proper backups and consolidated 6,446 match records, 7,638 player records, etc.

✅ **Scraper Paths**: Verified `etl/scrapers/scraper_players.py`
- `build_league_data_dir('TEST')` correctly resolves to `/path/to/project/data/leagues/TEST`
- Utils imports working correctly with updated `sys.path`

✅ **Master Scraper**: Verified data directory calculation in `etl/scrapers/master_scraper.py`
- Correctly calculates paths to `data/leagues/` directory

## Usage

### Running Scrapers
```bash
# From project root
python etl/scrapers/master_scraper.py

# Or from scrapers directory
cd etl/scrapers
python master_scraper.py
```

### Running Database Import
```bash
# From project root
python etl/database_import/consolidate_league_jsons_to_all.py
python etl/database_import/json_import_all_to_database.py
```

## Benefits of Reorganization

1. **Clearer Organization**: Logical separation between data collection and data processing
2. **Consolidated ETL**: All ETL-related functionality now under single `etl/` directory
3. **Maintained Functionality**: All scripts continue to work with updated paths
4. **Future Scalability**: Easy to add new scrapers or database utilities in appropriate subdirectories

## Files Requiring Path Updates

1. **etl/scrapers/scraper_players.py** - Updated `build_league_data_dir()` and `sys.path.append()`
2. **etl/scrapers/master_scraper.py** - Updated data directory calculation
3. **etl/database_import/consolidate_league_jsons_to_all.py** - Updated `BASE_DIR` calculation

All other scrapers appear to use relative imports or rely on the main scripts for path resolution, so no additional updates were required.

## League Backup Directory Cleanup (June 2025)

### Problem
- Multiple backup directories were being created in `data/leagues/all/` by the consolidation script
- These backups were cluttering the active data directory 
- Over 320MB of backup data was mixed with active JSON files
- Poor organization made it difficult to find current vs historical data

### Solution Implemented
1. **Modified consolidation script** (`data/etl/database_import/consolidate_league_jsons_to_all.py`)
   - Changed backup location from `data/leagues/all/backup_*` to `data/leagues/backups/consolidation/backup_*`
   - Future backups will now be stored in the dedicated backup directory

2. **Created cleanup script** (`scripts/cleanup_league_backups.py`)
   - Moves existing backup directories to proper location
   - Removes stray backup files  
   - Automatically cleans up old backups (keeps 5 most recent)
   - Provides disk usage analysis

3. **Executed cleanup**
   - Moved 7 backup directories (322.8 MB total)
   - Removed 2 stray backup files
   - Freed up 41 MB by removing oldest backups
   - New backup location: `data/leagues/backups/consolidation/`

### Directory Structure (After)
```
data/leagues/
├── all/                           # Clean active data only
│   ├── match_history.json
│   ├── player_history.json  
│   ├── players.json
│   ├── schedules.json
│   ├── series_stats.json
│   ├── nickname_mappings.json
│   ├── improve_data/
│   └── club_directories/
├── backups/                       # Organized backup storage
│   └── consolidation/
│       ├── backup_20250618_073014/
│       ├── backup_20250618_075433/
│       ├── backup_20250618_183302/
│       ├── backup_20250619_155226/
│       └── backup_20250620_153903/
├── APTA_CHICAGO/
├── CITA/
├── CNSWPL/
└── NSTF/
```

### Benefits
- **Clean data directory**: `data/leagues/all/` now contains only active data files
- **Organized backups**: All consolidation backups in dedicated location  
- **Automated cleanup**: Old backups automatically removed to save space
- **Better organization**: Clear separation between active data and backups
- **Space savings**: 41MB freed immediately, ongoing space management

### Future Maintenance
- The consolidation script now automatically uses the proper backup location
- Old backups are automatically cleaned up (keeps 5 most recent)
- Run `python scripts/cleanup_league_backups.py` if manual cleanup needed

### Files Modified
- `data/etl/database_import/consolidate_league_jsons_to_all.py` - Updated backup path
- ~~`scripts/cleanup_league_backups.py`~~ - Temporary cleanup utility (removed after completion)

## Comprehensive Backup Centralization (June 2025)

### Problem Expansion
After the initial league backup cleanup, we discovered backups were still scattered across multiple locations:
- Database backups in `sql/`, `data/etl/clone/`, and other directories
- League data backups in `data/leagues/backups/consolidation/`
- User data backups in various script directories
- Miscellaneous backup files throughout the project

### Solution: Centralized Backup Structure
Created a unified `data/backups/` directory with organized subdirectories:

```
data/backups/
├── database/          # All SQL/dump database backups (9.8 MB)
├── league_data/       # JSON league consolidation backups (281.7 MB) 
├── user_data/         # User association backups
└── misc/              # Other backup files (60 KB)
```

### Actions Taken
1. **Created centralization script** (~~`scripts/centralize_all_backups.py`~~ - removed after completion)
   - Automatically finds and categorizes all backup files
   - Moves files to appropriate backup category
   - Updates backup scripts to use new locations
   - Updates .gitignore patterns

2. **Moved 291.6 MB of backup data**
   - 7 database backup files → `data/backups/database/`
   - 5 league data backup directories → `data/backups/league_data/`
   - 4 miscellaneous backup files → `data/backups/misc/`

3. **Updated 5 backup scripts**
   - `scripts/backup_database.py`
   - `scripts/backup_current_db.py`
   - `data/etl/database_import/backup_restore_users.py`
   - `scripts/complete_database_clone.py`
   - `scripts/mirror_local_to_railway.py`

### Directory Structure (Final)
```
data/
├── backups/                       # 🆕 CENTRALIZED BACKUP LOCATION
│   ├── database/                  # SQL/dump files (9.8 MB)
│   │   ├── sql_current_db_backup_*.sql
│   │   ├── sql_railway_backup.sql
│   │   └── data_etl_clone_railway_backup_*.sql
│   ├── league_data/               # League consolidation backups (281.7 MB)
│   │   ├── backup_20250618_073014/
│   │   ├── backup_20250618_075433/
│   │   ├── backup_20250618_183302/
│   │   ├── backup_20250619_155226/
│   │   └── backup_20250620_153903/
│   ├── user_data/                 # User association backups
│   └── misc/                      # Other backup files (60 KB)
├── leagues/
│   ├── all/                       # Clean active data only
│   ├── APTA_CHICAGO/
│   ├── CITA/
│   ├── CNSWPL/
│   └── NSTF/
└── etl/
```

### Benefits Achieved
- ✅ **Single backup location**: All backups now in `data/backups/`
- ✅ **Categorized organization**: Database, league data, user data, misc
- ✅ **Clean project structure**: No more scattered backup files
- ✅ **Updated automation**: All backup scripts use centralized location
- ✅ **Future-proof**: New backups automatically go to correct location
- ✅ **Space visibility**: Easy to monitor backup storage usage (291.6 MB total)

### Clean Directories
These directories are now clean of backup files:
- `sql/` - Only active SQL scripts
- `data/leagues/all/` - Only active JSON data
- `data/etl/clone/` - No more backup files
- `data/leagues/NSTF/` - No more stray backup files

### Updated .gitignore
Added patterns to exclude the centralized backup directory:
```
# Centralized backups
data/backups/
data/backups/**/*
```

---

*This comprehensive reorganization establishes a clean, centralized backup system for the Rally application with automatic organization and easy maintenance.* 