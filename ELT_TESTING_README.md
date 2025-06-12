# 🧪 ELT Testing Framework

This framework provides a safe and comprehensive way to test your ELT scripts to ensure they produce 100% accurate and complete results that match your current database.

## 🎯 Overview

The testing framework creates an isolated test environment where:
1. **Safety First**: Your production database remains untouched
2. **Complete Validation**: Scripts are tested against real data
3. **Detailed Comparison**: Row counts, checksums, and content validation
4. **Easy Cleanup**: Everything is restored to original state

## 🚀 Quick Start

### Step 1: Set Up Test Environment
```bash
python test_etl_environment.py
```

This script will:
- ✅ Create a backup of your current database
- ✅ Create a test database (`rally_etl_test`)
- ✅ Clone your current data to the test environment
- ✅ Generate test configuration

### Step 2: Run Validation
```bash
python test_etl_validation.py
```

This script will:
- 🧹 Clear the test database (keeping structure)
- 🔄 Run your ELT scripts against empty test database
- 📊 Compare results with original database
- 📝 Generate detailed validation report

### Step 3: Clean Up
```bash
python cleanup_test_environment.py
```

This script will:
- 🗑️ Remove test database
- 🧹 Clean up temporary files
- 📋 Restore environment to original state

## 📊 What Gets Validated

### ✅ Data Completeness
- **Row Counts**: Ensures all expected records are imported
- **Table Coverage**: Verifies all tables are populated correctly
- **Missing Data**: Identifies any gaps in the import process

### ✅ Data Accuracy
- **Content Checksums**: Validates data integrity at byte level
- **Value Comparison**: Ensures imported data matches source data
- **Relationship Integrity**: Verifies foreign key relationships

### ✅ Process Reliability
- **Error Handling**: Tests script behavior with edge cases
- **Idempotency**: Ensures scripts can be run multiple times safely
- **Performance**: Monitors execution time and resource usage

## 📋 Understanding Results

### ✅ **PASS** - Perfect Match
```
✅ PASS - Databases are identical
Total Tables: 15
Row Count Mismatches: 0
Checksum Mismatches: 0
```
**Your ELT scripts are working perfectly!**

### ⚠️ **WARNING** - Content Differences
```
⚠️ WARNING - 2 tables have different checksums
Row Count Mismatches: 0
Checksum Mismatches: 2
```
**Same number of rows, but content differs. Check for:**
- Data transformation logic
- Default value handling
- Date/time formatting issues

### ❌ **FAIL** - Missing Data
```
❌ FAIL - 3 tables have different row counts
Row Count Mismatches: 3
```
**Missing or extra data. Check for:**
- Filtering logic in scripts
- Data source availability
- Foreign key constraint issues

## 🔍 Detailed Reports

Each validation run generates a timestamped JSON report:
```
etl_validation_report_20231215_143022.json
```

The report includes:
- **Summary Statistics**: Overall pass/fail status
- **Row Count Details**: Per-table comparison
- **Checksum Analysis**: Content integrity validation
- **Error Details**: Specific issues encountered

## 🛠️ Troubleshooting

### Common Issues

#### 🔧 **Connection Errors**
```bash
# Check database connectivity
python -c "from database_config import test_db_connection; test_db_connection()"
```

#### 🔧 **Permission Issues**
Ensure your database user has:
- `CREATE DATABASE` permissions
- Full access to source database
- `pg_dump` and `pg_restore` access

#### 🔧 **Memory Issues**
For large databases:
- Run during off-peak hours
- Monitor disk space for backups
- Consider testing subsets of data first

### Script-Specific Issues

#### 🔧 **ELT Script Failures**
1. Check the detailed validation report
2. Examine stdout/stderr in error details
3. Test individual scripts with `--dry-run`
4. Verify data source file availability

#### 🔧 **Checksum Mismatches**
Common causes:
- **Timestamps**: Auto-generated `created_at` fields
- **Sequences**: Auto-increment ID differences
- **Floating Point**: Precision differences in calculations
- **JSON Ordering**: Object key order variations

## 📁 Files Created

### Temporary Files
- `etl_test_config.json` - Test configuration
- `etl_test_backups/` - Database backups
- `etl_validation_report_*.json` - Validation results

### Database Objects
- `rally_etl_test` - Test database (automatically removed)

## 🔒 Safety Features

### ✅ **Isolated Testing**
- Test database is completely separate
- Production data never modified
- Environment variables properly isolated

### ✅ **Automatic Backups**
- Current database backed up before testing
- Multiple backup formats supported
- Backup verification included

### ✅ **Rollback Capability**
- Original database remains unchanged
- Easy restoration from backups if needed
- Clean state restoration

### ✅ **Permission Verification**
- Checks database permissions before starting
- Validates backup/restore capabilities
- Confirms cleanup permissions

## 🎯 Best Practices

### Before Testing
1. **Verify Data Sources**: Ensure JSON files are current
2. **Check Disk Space**: Backups require significant space
3. **Review Scripts**: Use `--dry-run` first on individual scripts
4. **Timing**: Run during low-activity periods

### During Testing
1. **Monitor Progress**: Watch for errors in real-time
2. **Resource Usage**: Monitor CPU/memory consumption
3. **Backup Verification**: Ensure backups complete successfully

### After Testing
1. **Review Reports**: Analyze any discrepancies thoroughly
2. **Document Issues**: Note any script improvements needed
3. **Clean Up**: Run cleanup script to restore environment
4. **Version Control**: Commit validated script changes

## 🚨 Emergency Procedures

### If Something Goes Wrong

#### 🆘 **Test Database Issues**
```bash
# Manually drop test database if needed
psql -c "DROP DATABASE IF EXISTS rally_etl_test;"
```

#### 🆘 **Restore from Backup**
```bash
# List available backups
ls -la etl_test_backups/

# Restore if needed (CAUTION: This overwrites current database)
pg_restore -d your_database_name etl_test_backups/backup_file.sql
```

#### 🆘 **Force Cleanup**
```bash
# If cleanup script fails
rm -f etl_test_config.json
rm -f etl_validation_report_*.json
rm -rf etl_test_backups/
```

## 💡 Tips for Success

### 📈 **Iterative Testing**
1. Start with individual scripts using `--dry-run`
2. Test with subset of data first
3. Run full validation when confident
4. Address issues incrementally

### 🔍 **Issue Resolution**
1. **Row Count Differences**: Check filtering logic and data availability
2. **Checksum Mismatches**: Focus on data transformation and default values  
3. **Script Errors**: Review logs and verify data source accessibility
4. **Performance Issues**: Consider batch sizing and memory usage

### 📊 **Monitoring Progress**
- Use separate terminal windows for real-time monitoring
- Check database connections during long-running operations
- Monitor system resources (CPU, memory, disk)

---

## 🎉 Success!

When your validation shows:
```
✅ PASS - Databases are identical
```

You can confidently run your ELT scripts knowing they will produce accurate, complete results that match your current database exactly.

**Your data pipeline is validated and ready for production use!** 🚀 