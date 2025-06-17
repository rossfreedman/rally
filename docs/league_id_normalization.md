# League ID Normalization System

## Overview

This document describes the comprehensive league ID normalization system implemented to ensure consistent league identifiers across all data sources and systems in the Rally application.

## Problem Statement

The Rally application was experiencing inconsistencies with league IDs across different data sources:
- Some files had `"nsft"` (lowercase) while others had `"NSTF"` (uppercase)
- Scrapers were using different naming conventions 
- ETL processes were failing due to mismatched league IDs
- No centralized system for managing league ID variations

## Solution: Centralized League Normalization

### 1. Central Utility (`utils/league_utils.py`)

Created a centralized utility that:
- **Defines canonical league IDs**: `APTA_CHICAGO`, `NSTF`, `CITA`, `APTA_NATIONAL`
- **Maps all known variations** to canonical formats
- **Provides normalization functions** for consistent usage across the system
- **Includes legacy compatibility** for existing scrapers

#### Key Functions:
- `normalize_league_id(league_id)` - Main normalization function
- `validate_league_id(league_id)` - Validates league IDs
- `get_league_display_name(league_id)` - Human-readable names
- `get_league_url(league_id)` - Official league URLs
- `standardize_league_id(subdomain)` - Legacy compatibility for scrapers

### 2. ETL Script Updates (`etl/database_import/json_import_all_to_database.py`)

Updated the comprehensive ETL script to:
- **Use normalization in all imports**: players, series stats, schedules, match history, player history
- **Normalize league references**: in relationship analysis and league extraction
- **Remove duplicate utility functions**: centralized in `league_utils.py`

**Result**: ETL now runs with **0 errors** instead of previous warnings about unrecognized league IDs

### 3. Data File Normalization

Created and ran a one-time normalization script that:
- **Processed 37 JSON files** across all league directories
- **Fixed 536 league ID inconsistencies** (8 files updated)
- **Created backups** of all modified files
- **Converted all `"nsft"` → `"NSTF"`** entries

### 4. Scraper Updates

Updated existing scrapers to use the centralized utility:
- `etl/scrapers/scraper_players.py` - Now imports from `league_utils`
- `etl/scrapers/scraper_stats.py` - Now imports from `league_utils`
- Removed duplicate `standardize_league_id` functions

## Canonical League ID Mappings

| Variations | Canonical ID | Display Name |
|------------|--------------|--------------|
| `nstf`, `nsft`, `north_shore`, `northshore` | `NSTF` | North Shore Tennis Foundation |
| `aptachicago`, `apta_chicago`, `chicago` | `APTA_CHICAGO` | APTA Chicago |
| `aptanational`, `apta_national`, `national` | `APTA_NATIONAL` | APTA National |
| `cita` | `CITA` | CITA |

## Benefits

### ✅ **Immediate Benefits**
- **ETL processes run cleanly** with no league ID warnings or errors
- **Data consistency** across all JSON files and database
- **Centralized management** of league ID variations
- **Future-proof** system for adding new leagues

### 🔄 **Future Benefits**
- **Easy league addition** - just update the central mapping
- **Automatic normalization** for all new data
- **No more manual league ID management** across different parts of the system
- **Consistent league references** in UI and API responses

## Usage Examples

### In ETL Scripts
```python
from utils.league_utils import normalize_league_id

# Automatically handles any variation
league_id = normalize_league_id("nsft")  # Returns "NSTF"
league_id = normalize_league_id("apta_chicago")  # Returns "APTA_CHICAGO"
```

### In Scrapers
```python
from utils.league_utils import standardize_league_id

# For subdomain-based normalization
league_id = standardize_league_id("nstf")  # Returns "NSTF"
```

### For Display Names
```python
from utils.league_utils import get_league_display_name

display_name = get_league_display_name("NSTF")  # Returns "North Shore Tennis Foundation"
```

## Implementation Results

### Before Normalization
```
[WARNING] League not found: nsft for team Birchwood S1
[WARNING] League not found: nsft for team Wilmette S1 T2
[WARNING] League not found: nsft for team Lake Forest S1
...
✅ Imported 545 series stats records (24 errors)
```

### After Normalization  
```
✅ Imported 569 series stats records (0 errors)
✅ All league IDs normalized and recognized
✅ No warnings or lookup failures
```

## Maintenance

The normalization system is designed to be:
- **Self-maintaining** - all new league variations just need to be added to the central mapping
- **Backwards compatible** - existing code continues to work
- **Extensible** - easy to add new leagues or variations

To add a new league variation:
1. Update `LEAGUE_ID_MAPPINGS` in `utils/league_utils.py`
2. Add display name to `get_league_display_name()`
3. Add URL to `get_league_url()` if available

## Files Modified

- ✅ `utils/league_utils.py` - Created centralized utility
- ✅ `etl/database_import/json_import_all_to_database.py` - Updated ETL script
- ✅ `etl/scrapers/scraper_players.py` - Updated to use centralized utility
- ✅ `etl/scrapers/scraper_stats.py` - Updated to use centralized utility
- ✅ `data/leagues/**/*.json` - Normalized 536 league ID inconsistencies 