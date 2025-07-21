# Enhanced ETL League Context Protection System

**Date**: January 21, 2025  
**Status**: ✅ IMPLEMENTED  
**Impact**: Eliminates league selection modal after ETL runs

## 🎯 **Problem Solved**

After ETL imports, users were losing their league context and being forced to manually select their league via a modal dialog. This happened because:

1. **Users had orphaned league contexts** pointing to non-existent league IDs
2. **Missing user_player_associations** prevented fallback restoration
3. **ETL protection system** couldn't restore contexts without proper associations

**Example users affected**: Stephen Statkus, Lisa Wagner (before fix)

## 🛡️ **Enhanced Solution**

### **Automatic 3-Step Protection Process**

The enhanced `auto_fix_broken_league_contexts()` function now runs automatically during ETL and handles:

#### **Step 1: Create Missing User-Player Associations**
```sql
-- Find users with tenniscores_player_id but no associations
SELECT u.id, u.tenniscores_player_id
FROM users u
LEFT JOIN user_player_associations upa ON u.id = upa.user_id
WHERE u.tenniscores_player_id IS NOT NULL AND upa.user_id IS NULL
```

- **Creates associations** for users who should have them
- **Validates player exists** before creating association
- **Handles unique constraints** (each player can only be associated with one user)

#### **Step 2: Fix Broken League Contexts**
```sql
-- Find users with broken league contexts (pointing to non-existent leagues)
SELECT u.id, u.league_context
FROM users u
LEFT JOIN leagues l ON u.league_context = l.id
WHERE u.league_context IS NOT NULL AND l.id IS NULL
```

- **Finds best league** using player associations and match activity
- **Updates broken contexts** to valid league IDs
- **Prioritizes**: Team assignment > Match activity > Recent activity

#### **Step 3: Set NULL League Contexts**
```sql
-- Find users with NULL contexts who now have associations
SELECT DISTINCT u.id
FROM users u
JOIN user_player_associations upa ON u.id = upa.user_id
WHERE u.league_context IS NULL
```

- **Sets league contexts** for users with valid associations
- **Uses intelligent scoring** to pick the best league
- **Updates both league_context and tenniscores_player_id**

#### **Step 4: Fix League ID Inconsistency**
```sql
-- Sync league_id to match league_context (prevents modal issues)
UPDATE users 
SET league_id = league_context
WHERE league_context IS NOT NULL
AND (league_id != league_context OR league_id IS NULL)
```

- **Syncs league_id = league_context** for all users
- **Prevents session validation failures** that cause league selection modal
- **Clears orphaned league_id values** for users with NULL contexts

### **Intelligent League Selection Algorithm**

The system uses this prioritization to pick the best league for each user:

1. **Team Assignment** (prefer leagues where user has team_id)
2. **Match Activity** (count matches in last 12 months)
3. **Recent Activity** (most recent match date)
4. **League ID** (for consistency in ties)

```sql
ORDER BY 
    has_team DESC,           -- Prefer leagues where they have team assignment
    match_count DESC,        -- Then by recent match activity
    last_match_date DESC,    -- Then by most recent activity
    l.id                     -- Finally by league ID for consistency
```

## 🔄 **Integration Points**

### **Automatic ETL Integration**

The enhanced protection runs automatically in:

1. **Enhanced Atomic ETL Wrapper** (`atomic_wrapper_enhanced.py`)
   - Step 7.6: Auto-fixing broken league contexts
   - Runs after league context restoration
   - Part of standard ETL process

2. **Standard ETL Process** (`import_all_jsons_to_database.py`)
   - Integrated into `restore_user_data_with_team_mappings()`
   - Runs during user data restoration phase

### **Manual Tools**

- **`scripts/test_enhanced_etl_league_protection.py`** - Test and verify the system
- **`scripts/fix_missing_league_contexts.py`** - Manual fix tool for specific users

## 📊 **Success Metrics**

### **Before Enhancement**
- Stephen Statkus: `league_context = NULL`, no associations
- Lisa Wagner: `league_context = NULL`, no associations
- **Result**: Both saw league selection modal

### **After Enhancement**
- Stephen Statkus: `league_context = 4887` (APTA Chicago), proper associations
- Lisa Wagner: `league_context = 4889` (CNSWPL), proper associations
- **Result**: No users see league selection modal

### **Test Results**
```
🎯 SUMMARY:
   Issues found: 2
   Users processed: 4
   Users with broken contexts remaining: 0

🎉 SUCCESS: All league context issues resolved!
   Users will no longer see the league selection modal after ETL.
```

### **Production Fix Results**
```
🔧 League ID Inconsistency Fix - EXECUTE
============================================================
Found 15 users with inconsistent league data (including Ross Freedman)

✅ Updated 15 users - set league_id = league_context
✅ Successfully fixed 15 users

Final validation:
  - Users with orphaned league_id: 0
  - Users with inconsistent league_id/context: 0 
  - Users with consistent league_id/context: 15

🎉 SUCCESS: All league_id inconsistencies resolved!
   Users should no longer see the league selection modal.
```

## 🧪 **Testing**

### **Automated Testing**
Run the test script to verify the system works:
```bash
python scripts/test_enhanced_etl_league_protection.py
```

### **Manual Verification**
Check league context health:
```sql
-- Users without league context (should be 0)
SELECT COUNT(*) FROM users WHERE league_context IS NULL;

-- Users with broken league context (should be 0)
SELECT COUNT(*) FROM users u
LEFT JOIN leagues l ON u.league_context = l.id
WHERE u.league_context IS NOT NULL AND l.id IS NULL;

-- League distribution
SELECT l.league_name, COUNT(*) as user_count
FROM users u
JOIN leagues l ON u.league_context = l.id
GROUP BY l.league_name
ORDER BY user_count DESC;
```

## 🔧 **Troubleshooting**

### **If Users Still See Modal After ETL**

1. **Check for broken contexts**:
   ```sql
   SELECT u.id, u.email, u.league_context
   FROM users u
   LEFT JOIN leagues l ON u.league_context = l.id
   WHERE u.league_context IS NOT NULL AND l.id IS NULL;
   ```

2. **Check for missing associations**:
   ```sql
   SELECT u.id, u.email, u.tenniscores_player_id
   FROM users u
   LEFT JOIN user_player_associations upa ON u.id = upa.user_id
   WHERE u.tenniscores_player_id IS NOT NULL AND upa.user_id IS NULL;
   ```

3. **Run manual fix**:
   ```bash
   python scripts/fix_missing_league_contexts.py --execute
   ```

### **Common Issues**

- **Player already associated**: Each `tenniscores_player_id` can only be associated with one user
- **No match activity**: Users without matches get assigned based on team assignment
- **Multiple leagues**: System picks the most active league for the user

## 📝 **Code Locations**

### **Core Protection Logic**
- `data/etl/database_import/enhanced_league_context_protection.py`
  - `auto_fix_broken_league_contexts()` - Main function (enhanced)

### **ETL Integration**
- `data/etl/database_import/atomic_wrapper_enhanced.py`
  - Step 7.6: Auto-fix integration
- `data/etl/database_import/import_all_jsons_to_database.py`
  - `restore_user_data_with_team_mappings()` - Standard integration

### **Testing & Tools**
- `scripts/test_enhanced_etl_league_protection.py` - Comprehensive testing
- `scripts/fix_missing_league_contexts.py` - Manual fix tool for specific users
- `scripts/fix_league_id_inconsistency.py` - Fix league_id/league_context inconsistency

## 🎉 **Benefits**

1. **Automatic Protection** - No manual intervention needed after ETL
2. **Intelligent Restoration** - Picks the best league for each user
3. **Comprehensive Coverage** - Handles all types of league context issues
4. **Zero User Impact** - Users never see the league selection modal
5. **Backward Compatible** - Works with existing ETL processes
6. **Fully Tested** - Comprehensive test suite validates functionality

---

**Next ETL Run**: Users will automatically retain their league contexts without any manual selection required. 