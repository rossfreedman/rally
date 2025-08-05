# Test Database Decommissioning Summary

## Overview

The local test database (`rally_test`) has been decommissioned to prevent accidental usage of test data in production scenarios. All operations now use the main database (`rally`) by default.

## Changes Made

### 1. Database Configuration (`database_config.py`)

**Before:**
```python
database_mode = os.getenv("RALLY_DATABASE", "test")  # "main" or "test"
```

**After:**
```python
database_mode = os.getenv("RALLY_DATABASE", "main")  # "main" or "test"
```

**Additional Warnings:**
- Added warning when test database mode is used
- Updated log messages to indicate test database is decommissioned

### 2. Start Scripts

**`start_rally_test.sh`:**
- Changed from `export RALLY_DATABASE=test` to `export RALLY_DATABASE=main`
- Updated messages to reflect main database usage
- Now uses main database instead of test database

### 3. Test Configuration Files

**Updated files:**
- `tests/conftest.py` - Changed test database URL to main database
- `ui_tests/conftest.py` - Changed test database URL to main database  
- `tests/quick_test.py` - Changed test database URL to main database
- `run_all_tests.sh` - Changed test database name to main database

**Before:**
```python
"TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rally_test"
```

**After:**
```python
"TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rally"
```

### 4. Documentation Updates

**`README_DATABASE_SWITCHING.md`:**
- Updated to reflect test database decommissioning
- Modified workflow to use main database
- Added warning about test database being decommissioned

**`clone_to_test_db.sh`:**
- Updated to warn that test database is decommissioned
- Changed from cloning functionality to informational script
- Added checks to verify test database is gone

### 5. Decommissioning Scripts

**Created:**
- `scripts/decommission_test_db.py` - Comprehensive decommissioning script
- `scripts/quick_decommission_test_db.py` - Quick decommissioning script

## Verification

### ✅ **Test Database Removed**
- `rally_test` database no longer exists
- Attempts to connect to test database fail with clear error message

### ✅ **Default Behavior**
- Default database is now main database (`rally`)
- All scripts use main database unless explicitly configured otherwise

### ✅ **Start Scripts Work**
- `./start_rally_main.sh` - Uses main database
- `./start_rally_test.sh` - Now uses main database (renamed for clarity)

### ✅ **Test Configuration**
- All test files now reference main database
- Tests will run against main database data

## Impact

### 🛡️ **Protection**
- Prevents accidental usage of test data in production scenarios
- Clear error messages when test database is attempted
- All operations use main database by default

### 🔧 **Development**
- Simplified environment - only one database to manage
- No confusion between test and main databases
- All testing uses real production data

### 📊 **Data Integrity**
- No risk of accidentally using test data
- All operations work with consistent dataset
- Single source of truth for all development

## Usage

### **Default Behavior**
```bash
# Uses main database automatically
python3 server.py
```

### **Explicit Main Database**
```bash
export RALLY_DATABASE=main
python3 server.py
```

### **Test Database (Will Fail)**
```bash
export RALLY_DATABASE=test
python3 server.py  # Will fail - test database doesn't exist
```

### **Start Scripts**
```bash
./start_rally_main.sh    # Uses main database
./start_rally_test.sh    # Now uses main database
```

## Files Modified

1. **`database_config.py`** - Changed default to main database
2. **`start_rally_test.sh`** - Now uses main database
3. **`tests/conftest.py`** - Updated test database URL
4. **`ui_tests/conftest.py`** - Updated test database URL
5. **`tests/quick_test.py`** - Updated test database URL
6. **`run_all_tests.sh`** - Updated test database name
7. **`README_DATABASE_SWITCHING.md`** - Updated documentation
8. **`clone_to_test_db.sh`** - Updated to warn about decommissioning

## Files Created

1. **`scripts/decommission_test_db.py`** - Comprehensive decommissioning script
2. **`scripts/quick_decommission_test_db.py`** - Quick decommissioning script
3. **`docs/TEST_DATABASE_DECOMMISSIONING_SUMMARY.md`** - This summary

## Benefits

✅ **Prevents Accidental Usage** - No more confusion between test and main databases  
✅ **Simplified Environment** - Only one database to manage  
✅ **Data Consistency** - All operations use same dataset  
✅ **Clear Error Messages** - Attempts to use test database fail clearly  
✅ **Updated Documentation** - All references updated to reflect changes  
✅ **Maintained Functionality** - All features work with main database 