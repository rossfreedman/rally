# Series Name Mapping System

## 🎯 **Overview**

This document describes Rally's scalable, database-driven series name mapping system that handles league-specific naming conventions without hardcoded logic.

## 🚨 **Problem Solved**

### **Before:** Hardcoded Mappings
```python
# ❌ Not scalable - hardcoded for each league
if league_id == 'CNSWPL':
    mapped_series = series.replace('Division ', 'Series ')
elif league_id == 'NSTF':
    mapped_series = f'S{series.replace("Series ", "")}'
elif league_id == 'NEW_LEAGUE':
    # Would need code changes for every new league!
```

### **After:** Database-Driven Mappings
```python
# ✅ Scalable - works for any league via database
from utils.series_mapping_service import find_team_with_series_mapping
team = find_team_with_series_mapping(club, series, league_id, league_db_id)
```

## 🏗️ **System Architecture**

### **1. Database Table: `series_name_mappings`**
```sql
CREATE TABLE series_name_mappings (
    id SERIAL PRIMARY KEY,
    league_id VARCHAR(50) NOT NULL,           -- 'NSTF', 'CNSWPL', etc.
    user_series_name VARCHAR(100) NOT NULL,   -- 'Series 2B', 'Division 16'
    database_series_name VARCHAR(100) NOT NULL, -- 'S2B', 'Series 16'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(league_id, user_series_name),
    FOREIGN KEY (league_id) REFERENCES leagues(league_id)
);
```

### **2. Service Layer: `utils/series_mapping_service.py`**
- **`SeriesMappingService`**: Core mapping logic with caching
- **`find_team_with_series_mapping()`**: Integration function for team lookup
- **`add_mapping()`**: Add new mappings programmatically

### **3. Management Tool: `scripts/manage_series_mappings.py`**
- **Analyze**: Detect series patterns for new leagues
- **Add**: Add individual mappings
- **List**: View existing mappings
- **Auto-add**: Bulk add common patterns

## 📋 **Current League Mappings**

### **NSTF (North Shore Tennis Foundation)**
| User Format | Database Format | Example |
|-------------|-----------------|---------|
| `Series 1`  | `S1`           | User has "Series 1" → Database "S1" |
| `Series 2A` | `S2A`          | User has "Series 2A" → Database "S2A" |
| `Series 2B` | `S2B`          | **This was the original issue!** |
| `Series 3`  | `S3`           | User has "Series 3" → Database "S3" |
| `Series A`  | `SA`           | User has "Series A" → Database "SA" |

### **CNSWPL (Chicago North Shore Women's Platform Tennis League)**
| User Format | Database Format | Example |
|-------------|-----------------|---------|
| `Division 1` | `Series 1`     | User has "Division 1" → Database "Series 1" |
| `Division 16` | `Series 16`   | User has "Division 16" → Database "Series 16" |
| *(All divisions 1-17, A-K, SN)* | | |

### **APTA Chicago**
- **No mappings needed** - Uses consistent "Chicago X" format

### **CITA**
| User Format | Database Format | Example |
|-------------|-----------------|---------|
| `Boys Division` | `Boys`       | Demo mapping added |
| `Girls Division` | `Girls`     | Demo mapping added |

## 🛠️ **Adding New Leagues**

### **Step 1: Analyze Patterns**
```bash
python scripts/manage_series_mappings.py analyze LEAGUE_ID
```

**Example Output:**
```
🔍 ANALYZING SERIES PATTERNS FOR NEW_LEAGUE
📊 Found 15 series in NEW_LEAGUE
📋 Naming Patterns:
  - Custom format: Premier A
  - Custom format: Premier B  
  - Custom format: Elite 1
  - Custom format: Elite 2

💡 Mapping Suggestions:
  'Premier A' <- potential user formats: Division Premier A
  'Elite 1' <- potential user formats: Division Elite 1
```

### **Step 2: Add Mappings**
```bash
# Add individual mappings
python scripts/manage_series_mappings.py add LEAGUE_ID "User Format" "DB Format"

# Examples:
python scripts/manage_series_mappings.py add NEW_LEAGUE "Division Premier A" "Premier A"
python scripts/manage_series_mappings.py add NEW_LEAGUE "Division Elite 1" "Elite 1"
```

### **Step 3: Verify**
```bash
python scripts/manage_series_mappings.py list LEAGUE_ID
```

## 🔧 **How It Works**

### **Team Lookup Flow**
1. **Direct Lookup**: Try user's series name directly
2. **Mapping Lookup**: Query `series_name_mappings` table
3. **Mapped Lookup**: Try with mapped series name
4. **Cache Result**: Cache for future requests

### **Example: NSTF User**
```python
# User session data
user = {
    'club': 'Tennaqua',
    'series': 'Series 2B',  # ← User-facing format
    'league_id': 'NSTF'
}

# 1. Direct lookup fails: No team with series="Series 2B"
# 2. Check mapping: "Series 2B" → "S2B" 
# 3. Mapped lookup succeeds: Find team with series="S2B"
# 4. Return: Tennaqua S2B team with 12 matches ✅
```

## 📊 **Benefits**

### **✅ Scalability**
- **No code changes** needed for new leagues
- **Database-driven** configuration
- **Automatic caching** for performance

### **✅ Maintainability** 
- **Single source of truth** in database
- **Easy updates** via management scripts
- **Clear audit trail** with timestamps

### **✅ Flexibility**
- **Pattern detection** for new leagues
- **Bulk operations** for common patterns
- **Override capability** for special cases

### **✅ Performance**
- **In-memory caching** of mappings
- **Indexed lookups** in database
- **Fallback to direct lookup** if no mapping

## 🎯 **Future Enhancements**

### **Auto-Detection**
- Analyze user registration data to detect new patterns
- Suggest mappings based on failed team lookups
- Machine learning for pattern recognition

### **Web Interface**
- Admin UI for managing mappings
- Visual pattern analysis
- Bulk import/export capabilities

### **Advanced Patterns**
- Regular expression mappings
- Conditional mappings based on club
- Multi-step transformation chains

## 🔧 **Technical Integration**

### **In Mobile Service**
```python
# Old way (hardcoded)
if league_id == 'NSTF' and series.startswith('Series '):
    mapped_series = f'S{series.replace("Series ", "")}'

# New way (database-driven)
from utils.series_mapping_service import find_team_with_series_mapping
team_record = find_team_with_series_mapping(club, series, league_id, league_db_id)
```

### **Error Handling**
- **Graceful fallback** to direct lookup
- **Detailed logging** for debugging
- **Cache management** for consistency

## 📈 **Monitoring**

### **Key Metrics**
- **Mapping hit rate**: % of lookups using mappings
- **Cache performance**: Hit/miss ratios
- **Failed lookups**: Teams not found (potential new mappings needed)

### **Alerts**
- **High failure rate** for new leagues
- **Performance degradation** in mapping service
- **Foreign key violations** (invalid league IDs)

---

## 🎉 **Result**

The Rally platform now handles **any league's naming conventions** without code changes, providing a **scalable foundation** for growth while maintaining **100% backward compatibility** with existing functionality.

### **Impact**
- ✅ **Immediate Fix**: `/mobile/my-team` page works after ETL runs
- ✅ **Future-Proof**: New leagues can be added in minutes, not hours
- ✅ **Maintainable**: No more hardcoded mapping logic to maintain
- ✅ **Transparent**: Clear audit trail of all mapping changes 