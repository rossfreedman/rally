# Rally Database Scripts

This directory contains utility scripts for managing the Rally database, particularly for test data cleanup.

## Scripts Overview

### 🧹 `cleanup_test_database.py`
**Comprehensive test database cleanup script**

Safely removes test data from the database while preserving production data. Handles foreign key constraints by cleaning up data in the correct order.

**Usage:**
```bash
# Dry run to see what would be deleted
python scripts/cleanup_test_database.py --dry-run --verbose

# Actually clean up test data
python scripts/cleanup_test_database.py --verbose

# Clean only recent test data (last 24 hours)
python scripts/cleanup_test_database.py --recent-only 24

# Clean all test data including fixtures and reference data
python scripts/cleanup_test_database.py --all-test-data --include-reference-data
```

**Features:**
- ✅ Safe deletion respecting foreign key constraints
- ✅ Dry run mode for safe testing
- ✅ Configurable time windows for recent data
- ✅ Comprehensive test pattern recognition
- ✅ Optional reference data cleanup

### 🗂️ `cleanup_reference_data.py`
**Test reference data cleanup script**

Specifically targets test leagues, clubs, series, and their dependent data (teams, players). Perfect for cleaning up fake leagues from dropdowns.

**Usage:**
```bash
# See what test reference data exists
python scripts/cleanup_reference_data.py --dry-run --verbose

# Clean up test leagues, clubs, and series
python scripts/cleanup_reference_data.py --verbose

# Automatic cleanup (useful for scripts)
echo "y" | python scripts/cleanup_reference_data.py --verbose
```

**What it removes:**
- 🏆 Test leagues (`FAKE_LEAGUE`, `TEST_LEAGUE`, etc.)
- 🏛️ Test clubs (`Test Club`, `Fake Club`, etc.)
- 📊 Test series (`Test Series`, `Fake Series`, etc.)
- 👥 Associated teams and players

### ⚡ `quick_cleanup.py`
**Fast test data cleanup**

Lightweight script for quickly removing common test data patterns. Designed for test runners and CI/CD pipelines.

**Usage:**
```bash
# Quick cleanup before tests
python scripts/quick_cleanup.py

# Check cleanup status  
python scripts/test_database_utils.py status
```

**Features:**
- ⚡ Fast execution (< 5 seconds)
- 🎯 Targets most common test patterns
- 🔄 Safe for repeated execution
- 📊 Shows cleanup summary

### 🔧 `test_database_utils.py`
**Test database utility functions**

Collection of utility functions for managing test database state.

**Usage:**
```bash
# Check database status
python scripts/test_database_utils.py status

# Verify cleanup
python scripts/test_database_utils.py verify

# Reset to clean state
python scripts/test_database_utils.py reset
```

**Functions:**
- 📊 Database state monitoring
- ✅ Cleanup verification
- 🧹 Quick reset capabilities
- 📈 Test data statistics

## Common Workflows

### 🧪 **Before Running Tests**
```bash
# Quick cleanup to ensure clean test environment
python scripts/quick_cleanup.py

# Verify clean state
python scripts/test_database_utils.py status
```

### 🗂️ **Cleaning Fake Reference Data**
```bash
# Remove fake leagues from dropdowns
python scripts/cleanup_reference_data.py --verbose

# Comprehensive cleanup including reference data
python scripts/cleanup_test_database.py --include-reference-data --verbose
```

### 🔍 **Investigation Mode**
```bash
# See what would be cleaned without deleting anything
python scripts/cleanup_test_database.py --dry-run --verbose --all-test-data

# Check specific reference data
python scripts/cleanup_reference_data.py --dry-run --verbose
```

### 💪 **Complete Database Reset**
```bash
# Nuclear option - clean everything
python scripts/cleanup_test_database.py --all-test-data --include-reference-data
```

## Safety Features

- 🛡️ **Dry Run Mode**: All scripts support `--dry-run` to preview changes
- 🔗 **Foreign Key Respect**: Proper deletion order prevents constraint violations  
- 🎯 **Pattern Recognition**: Smart identification of test vs. production data
- ✅ **Confirmation Prompts**: User confirmation required for destructive operations
- 📊 **Detailed Logging**: Comprehensive progress reporting with `--verbose`

## Integration

These scripts are designed to integrate with:
- 🧪 **Test Runners**: Automated cleanup before/after test suites
- 🚀 **CI/CD Pipelines**: Maintaining clean staging environments  
- 🔄 **Daily Maintenance**: Scheduled cleanup of accumulated test data
- 🐛 **Development Workflows**: Quick cleanup during active development

## Troubleshooting

**Issue**: Scripts fail with import errors
```bash
# Ensure you're in the project root
cd /path/to/rally
python scripts/cleanup_test_database.py
```

**Issue**: Permission denied errors
```bash
# Check database permissions
python -c "from database_utils import execute_query; print('Connection OK')"
```

**Issue**: Foreign key constraint errors
```bash
# Use the comprehensive script which handles constraints
python scripts/cleanup_test_database.py --include-reference-data
```

## Test Data Patterns

The scripts identify test data using these patterns:

### Email Patterns
- `%test%` - General test emails
- `%example.com%` - Example domain emails  
- `%weak%` - Password testing emails
- `%xss%` - Security testing emails
- `%injection%` - SQL injection testing
- `%api@%` - API testing emails
- `%loadtest%` - Load testing emails

### Name Patterns
- `Test%` - Test users
- `Invalid%` - Invalid data testing
- `XSS%` - Cross-site scripting tests
- `SQL%` - SQL injection tests
- `Weak%` - Password testing

## Database Schema Dependencies

```
users
├── activity_log (user_id → users.id)
├── user_player_associations (user_id → users.id)
└── polls (created_by → users.id)
    ├── poll_choices (poll_id → polls.id)
    └── poll_responses (poll_id → polls.id)
```

## Error Handling

- Scripts continue on non-critical errors
- Database connection issues are logged
- Foreign key violations are handled gracefully
- Rollback on transaction failures

## Best Practices

1. **Always use dry-run first**: `--dry-run --verbose`
2. **Regular cleanup**: Run cleanup after test sessions
3. **Monitor database growth**: Use status commands
4. **Backup before major cleanups**: For production environments
5. **Test isolation**: Clean before each test run 