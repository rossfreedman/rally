# New League Import & Team Format Mapping Guide

## 🔄 **Overview**

When you scrape/import a new league, users will initially get "team not found" errors until team format mappings are added. This guide shows how to quickly resolve this using our sophisticated mapping system.

## 📋 **Step-by-Step Workflow**

### **STEP 1: Import the New League** 
```bash
# Your existing ETL process
python data/etl/scrapers/new_league_scraper.py LEAGUE_ID
```

**What happens:**
- ✅ New league added to `leagues` table
- ✅ New teams added to `teams` table
- ✅ New series formats added to `series` table
- ❌ **Users get "team not found" errors** (expected)

### **STEP 2: Analyze the New League**
```bash
python scripts/manage_series_mappings.py analyze NEW_LEAGUE_ID
```

**Example Output:**
```
🔍 ANALYZING SERIES PATTERNS FOR MIDWEST_TENNIS
📊 Found 12 series in MIDWEST_TENNIS
📋 Naming Patterns:
  - Custom format: Level 4.0
  - Custom format: Level 4.5
  - Custom format: Division A
  - Custom format: Division B

💡 Mapping Suggestions:
  'Level 4.0' <- potential user formats: 4.0, L4.0
  'Division A' <- potential user formats: A, Div A
```

### **STEP 3: Add Mappings**

#### **Option A: Manual Mapping (Recommended for Complex Formats)**
```bash
# Add individual mappings
python scripts/manage_series_mappings.py add MIDWEST_TENNIS "4.0" "Level 4.0"
python scripts/manage_series_mappings.py add MIDWEST_TENNIS "4.5" "Level 4.5"
python scripts/manage_series_mappings.py add MIDWEST_TENNIS "A" "Division A"
python scripts/manage_series_mappings.py add MIDWEST_TENNIS "B" "Division B"
```

#### **Option B: Programmatic API (For Bulk Operations)**
```python
from utils.series_mapping_service import add_team_format_mapping

# Common mappings for level-based leagues
level_mappings = [
    ("4.0", "Level 4.0", "Short numeric to level format"),
    ("4.5", "Level 4.5", "Short numeric to level format"),
    ("Level 4.0", "Level 4.0", "Direct match"),
    ("Level 4.5", "Level 4.5", "Direct match"),
]

for user_format, db_format, description in level_mappings:
    add_team_format_mapping("MIDWEST_TENNIS", user_format, db_format, description)
```

#### **Option C: Auto-Add (For Standard Patterns)**
```bash
# Automatically adds common patterns
python scripts/manage_series_mappings.py auto-add MIDWEST_TENNIS
```

### **STEP 4: Verify the Mappings**
```bash
# List all mappings for the league
python scripts/manage_series_mappings.py list MIDWEST_TENNIS

# Test specific team lookup
python -c "
from utils.series_mapping_service import debug_team_lookup
result = debug_team_lookup('Oak Brook Elite', '4.0', 'MIDWEST_TENNIS', LEAGUE_DB_ID)
print(result)
"
```

## 🎯 **Common League Patterns & Quick Setup**

### **Pattern 1: Level-Based Leagues (Tennis Clubs)**
```bash
# Database has: "Level 4.0", "Level 4.5", "Level 5.0"
# Users might enter: "4.0", "4.5", "5.0"

python scripts/manage_series_mappings.py add LEAGUE_ID "4.0" "Level 4.0"
python scripts/manage_series_mappings.py add LEAGUE_ID "4.5" "Level 4.5"
python scripts/manage_series_mappings.py add LEAGUE_ID "5.0" "Level 5.0"
```

### **Pattern 2: Division-Based Leagues (Traditional)**
```bash
# Database has: "Division A", "Division B", "Division C"
# Users might enter: "A", "B", "C", "Div A"

python scripts/manage_series_mappings.py add LEAGUE_ID "A" "Division A"
python scripts/manage_series_mappings.py add LEAGUE_ID "B" "Division B"
python scripts/manage_series_mappings.py add LEAGUE_ID "Div A" "Division A"
```

### **Pattern 3: Numeric Series (Like CNSWPL)**
```bash
# Database has: "S1", "S2", "S16"  
# Users might enter: "Division 1", "Series 1", "1"

python scripts/manage_series_mappings.py add LEAGUE_ID "Division 1" "S1"
python scripts/manage_series_mappings.py add LEAGUE_ID "Series 1" "S1"
python scripts/manage_series_mappings.py add LEAGUE_ID "1" "S1"
```

### **Pattern 4: Location-Based (Like APTA Chicago)**
```bash
# Database has: "Chicago 11", "Chicago 13"
# Users might enter: "11", "13", "Division 11"

python scripts/manage_series_mappings.py add LEAGUE_ID "11" "Chicago 11"
python scripts/manage_series_mappings.py add LEAGUE_ID "Division 11" "Division 11"
```

## 🛠️ **Advanced Tools**

### **Debug Team Lookup**
```python
from utils.series_mapping_service import debug_team_lookup

# Get detailed debug info for a team lookup
debug_info = debug_team_lookup(
    club="Oak Brook Elite",
    user_series="4.0",
    league_id="MIDWEST_TENNIS", 
    league_db_id=1234
)

print("Steps taken:")
for step in debug_info['steps']:
    print(f"  {step}")
```

### **Coverage Analysis**
```python
from utils.series_mapping_service import get_comprehensive_team_format_mapper

mapper = get_comprehensive_team_format_mapper()
patterns = mapper.auto_detect_mapping_pattern("MIDWEST_TENNIS")

print(f"Series count: {patterns['series_count']}")
print(f"Existing mappings: {patterns['existing_mappings']}")
print(f"Unmapped series: {patterns['unmapped_series']}")
```

## 🔧 **Fallback Mechanisms**

The system automatically handles edge cases:

### **1. Direct Lookup**
- First tries exact series name match
- Fastest path for correctly formatted data

### **2. Mapped Lookup** 
- Checks `team_format_mappings` table
- Handles all user format variations

### **3. Fuzzy Matching**
- Looks for partial string matches
- Catches variations we didn't anticipate

### **4. Clear Error Messages**
- Shows similar teams from other leagues
- Helps admin understand what mappings to add

## ✅ **Benefits**

- **🔄 Zero Downtime**: Users get clear errors, not crashes
- **⚡ Fast Resolution**: Add mappings in minutes, not hours
- **📈 Scalable**: Works for unlimited leagues without code changes  
- **🎯 Smart Fallbacks**: Catches edge cases automatically
- **🛠️ Easy Tools**: Command line and programmatic APIs
- **📊 Analytics**: Coverage analysis shows mapping gaps

## 🚨 **Important Notes**

1. **Foreign Key Integrity**: Mappings can only be added for leagues that exist in the `leagues` table
2. **Cache Management**: System automatically clears cache when mappings are added
3. **Case Sensitivity**: Mappings are case-sensitive, plan accordingly
4. **Testing**: Always test with `debug_team_lookup()` before declaring success
5. **Documentation**: Update this guide when new patterns emerge

## 📞 **Quick Reference Commands**

```bash
# Analyze new league
python scripts/manage_series_mappings.py analyze LEAGUE_ID

# Add mapping  
python scripts/manage_series_mappings.py add LEAGUE_ID "User Format" "DB Format"

# List mappings
python scripts/manage_series_mappings.py list LEAGUE_ID

# Auto-add patterns
python scripts/manage_series_mappings.py auto-add LEAGUE_ID
```

**The my-team page will work perfectly once mappings are added!** 🏓 