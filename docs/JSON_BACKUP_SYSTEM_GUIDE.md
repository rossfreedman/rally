# Rally JSON Backup & Directory Management System

## 🎉 **IMPLEMENTATION COMPLETED SUCCESSFULLY**

Rally's scraper system now includes comprehensive JSON backup protection and standardized directory management to prevent data loss and eliminate redundant directories.

## ✅ **What Was Implemented**

### 1. **JSON Backup Manager** 📦

**Location:** `data/etl/utils/json_backup_manager.py`

- **Automatic backup creation** before any scraper runs
- **Timestamped backup sessions** in `data/backups/backup_jsons/`
- **League-specific and all-league backup options**
- **Backup validation and summary reporting**
- **Automatic cleanup** of old backup sessions

### 2. **League Directory Standardization** 📁

**Location:** `data/etl/utils/league_directory_manager.py`

- **Eliminates redundant directories** (APTACHICAGO vs APTA_CHICAGO)
- **Standardized naming convention** for all leagues
- **Automatic migration** from legacy directory names
- **Comprehensive directory auditing**

### 3. **Master Scraper Integration** 🚀

**Enhanced:** `data/etl/scrapers/master_scraper.py`

- **Automatic backup creation** before every scraping operation
- **Backup status in notifications** and error messages
- **Backup summary in session metrics**
- **Graceful failure handling** with backup information

### 4. **Scraper Compatibility Updates** 🔧

**Updated scrapers:**
- `scrape_match_scores.py` - Uses standardized directories
- `scrape_stats.py` - Updated build_league_data_dir()
- `scrape_schedule.py` - Updated build_league_data_dir()
- `scraper_player_history_optimized.py` - Updated build_league_data_dir() (optimized version only)

## 🚀 **How It Works**

### **Automatic Backup Protection**

Every time the master scraper runs:

1. **📦 Backup Creation** - All JSON files backed up with timestamp
2. **🎯 Scraping Operation** - Normal scraper execution
3. **📊 Status Reporting** - Backup info included in results
4. **🔄 Recovery Ready** - Backup location provided if needed

### **Directory Standardization**

All league inputs now map to consistent directories:

```python
"aptachicago" → "APTA_CHICAGO"
"APTACHICAGO" → "APTA_CHICAGO"  # Legacy fixed
"apta" → "APTA_CHICAGO"
"nstf" → "NSTF"
"cnswpl" → "CNSWPL"
"cita" → "CITA"
```

## 📋 **Usage Examples**

### **Manual Backup Before Scraping**

```python
from data.etl.utils.json_backup_manager import backup_before_scraping

# Backup specific league
backup_manager = backup_before_scraping("aptachicago")

# Backup all leagues
backup_manager = backup_before_scraping()

# Get backup summary
summary = backup_manager.get_backup_summary()
print(f"Backed up {summary['total_files']} files")
```

### **Using Standardized Directory Paths**

```python
from data.etl.utils.league_directory_manager import get_league_file_path

# Get standardized file path (prevents APTACHICAGO vs APTA_CHICAGO)
file_path = get_league_file_path("aptachicago", "match_history.json")
# Returns: data/leagues/APTA_CHICAGO/match_history.json
```

### **Directory Auditing**

```python
from data.etl.utils.league_directory_manager import get_directory_manager

manager = get_directory_manager()
audit = manager.audit_directories()

print(f"Standard directories: {len(audit['standard_directories'])}")
print(f"Legacy directories: {len(audit['legacy_directories'])}")
```

## 🗂️ **Backup Structure**

Backups are organized by session timestamp:

```
data/backups/backup_jsons/
├── session_20250803_144502/
│   ├── APTA_CHICAGO/
│   │   ├── match_history.json
│   │   ├── players.json
│   │   └── schedules.json
│   ├── NSTF/
│   │   ├── match_history.json
│   │   └── players.json
│   └── CNSWPL/
│       └── match_history.json
└── session_20250803_150215/
    └── ...
```

## ⚙️ **Configuration**

### **Backup Settings**

- **Default backup location:** `data/backups/backup_jsons/`
- **Session naming:** `session_YYYYMMDD_HHMMSS`
- **Automatic cleanup:** Keep last 30 days (configurable)

### **Directory Mapping**

All mappings defined in `league_directory_manager.py`:

```python
LEAGUE_DIRECTORY_MAPPING = {
    "aptachicago": "APTA_CHICAGO",
    "apta_chicago": "APTA_CHICAGO", 
    "apta": "APTA_CHICAGO",
    "nstf": "NSTF",
    "cnswpl": "CNSWPL",
    "cita": "CITA",
}
```

## 🔧 **Master Scraper Workflow**

Enhanced workflow with backup protection:

1. **[1/4] Backup Creation** - JSON files backed up with timestamp
2. **[2/4] Strategy Analysis** - Determine scraping approach
3. **[3/4] Scraping Execution** - Run the actual scrapers
4. **[4/4] Completion** - Results with backup location info

## 🧪 **Testing & Validation**

### **Test Scripts**

- **`scripts/test_backup_system.py`** - Comprehensive test suite
- **`scripts/cleanup_redundant_directories.py`** - Directory cleanup
- **`data/etl/utils/league_directory_manager.py`** - Run directly to test

### **Validation Commands**

```bash
# Test backup system
python3 scripts/test_backup_system.py

# Test directory manager
python3 data/etl/utils/league_directory_manager.py

# Test JSON backup manager
python3 data/etl/utils/json_backup_manager.py
```

## 🛡️ **Data Protection Features**

### **Backup Safeguards**

- ✅ **Automatic backup** before every scraper run
- ✅ **Timestamped sessions** prevent backup conflicts
- ✅ **Size validation** confirms backup completeness
- ✅ **Error handling** graceful failure with warnings
- ✅ **Recovery info** provided in failure notifications

### **Directory Protection**

- ✅ **Standardized naming** prevents duplicate directories
- ✅ **Legacy migration** automatic cleanup of old directories
- ✅ **Input validation** handles various league name formats
- ✅ **Audit capabilities** detect and fix directory issues

## 📊 **Cleanup Summary**

### **Redundant Directory Removal**

- **❌ Removed:** `data/leagues/APTACHICAGO/` (contained only empty JSON)
- **✅ Kept:** `data/leagues/APTA_CHICAGO/` (contains 11MB+ of real data)
- **🔧 Fixed:** All scrapers now use standardized directory names

### **File Statistics**

- **APTA_CHICAGO/match_history.json:** 335,359 lines (11MB)
- **APTACHICAGO/match_history.json:** 0 lines (empty array)

## 💡 **Best Practices**

### **For Administrators**

1. **Monitor backup space** - Sessions accumulate over time
2. **Review backup summaries** in scraper notifications
3. **Test recovery procedures** periodically
4. **Clean up old backups** using built-in cleanup function

### **For Developers**

1. **Use standardized directory functions** for all new scrapers
2. **Include backup manager** in any custom scraping scripts
3. **Test with multiple league name variants** to ensure compatibility
4. **Check backup status** in error handling

## 🎉 **Benefits Achieved**

- **🛡️ Data Protection:** Automatic backup before every update
- **📁 Directory Consistency:** No more APTACHICAGO vs APTA_CHICAGO confusion
- **🔧 Maintainability:** Centralized directory and backup management
- **📊 Visibility:** Backup status included in all notifications
- **🚀 Reliability:** Graceful failure handling with recovery options

**Your Rally scraper system is now fully protected against data loss with comprehensive backup and directory management capabilities.**