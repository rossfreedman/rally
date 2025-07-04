# Series ID Prevention Guide

## Overview

This guide ensures that the series_id foreign key system never breaks again by implementing comprehensive prevention, monitoring, and automatic fixes.

## Current Status

✅ **APTA Chicago**: 99.8% coverage (excellent)  
❌ **CITA**: 71.9% coverage (poor)  
❌ **CNSWPL**: 59.0% coverage (poor)  
❌ **NSTF**: 64.3% coverage (poor)  

**Overall Health Score: 83.3%** (815/978 records have series_id)

## Root Causes of NULL series_id Issues

1. **Missing Series Records**: Series exist in `series_stats` but not in `series` table
2. **ETL Import Issues**: New series_stats records created without series_id lookup
3. **League Expansion**: New leagues/series added without proper series table setup
4. **Manual Data Entry**: Direct database inserts bypassing series_id validation

## Prevention System

### 1. **Automated ETL Integration** ✅

The ETL script now automatically:
- **NEW**: Creates full database backup before import (Production/Staging)
- Populates `series_id` when creating new `series_stats` records  
- Runs post-import validation to catch NULL series_id issues
- Auto-populates missing series_id values after import
- **NEW**: Enhanced error handling with health score monitoring
- **NEW**: Critical alerts when health score drops below 85%
- **NEW**: Detailed failure reporting for debugging
- **NEW**: Final validation step ensures quality before completion

**Location**: `data/etl/database_import/import_all_jsons_to_database.py`

**ETL Process Flow**:
```
0. Create full database backup ← NEW SAFETY FEATURE
1. Import series_stats data
2. Validate import coverage  
3. Auto-populate missing series_id values ← AUTOMATIC
4. Check health score (fail if < 85%)
5. Continue with other imports
6. Final series_id health validation ← AUTOMATIC
7. Report final health score in summary
```

### 2. **Monitoring Tools** ✅

**Health Monitor**: `scripts/monitor_series_id_health.py`
```bash
# Check current health
python3 scripts/monitor_series_id_health.py

# Check specific league
python3 scripts/monitor_series_id_health.py --league NSTF

# Get detailed analysis
python3 scripts/monitor_series_id_health.py --fix --dry-run
```

**ETL Validator**: `scripts/etl_series_id_validator.py`
```bash
# Validate before ETL
python3 scripts/etl_series_id_validator.py --pre-etl

# Validate after ETL with auto-fix
python3 scripts/etl_series_id_validator.py --post-etl --auto-fix

# Generate coverage report
python3 scripts/etl_series_id_validator.py --report
```

### 3. **Database Constraints** ✅

**Foreign Key Constraint**: 
- `series_stats.series_id` → `series.id`
- Performance index on `series_stats.series_id`

**Applied via Alembic**:
```bash
python3 -m alembic upgrade head
```

### 4. **Auto-Population Script** ✅

**Population Script**: `scripts/populate_series_id_in_series_stats.py`
- Multiple matching strategies (exact, case-insensitive, format conversion)
- Handles series name variations
- Safe for repeated execution

## Operational Procedures

### **Daily Monitoring**
```bash
# Quick health check (add to cron)
python3 scripts/monitor_series_id_health.py | grep "HEALTH SCORE"
```

### **Before ETL Import**
```bash
# 1. Pre-ETL validation
python3 scripts/etl_series_id_validator.py --pre-etl

# 2. Run ETL import
python3 data/etl/database_import/import_all_jsons_to_database.py

# 3. Post-ETL validation with auto-fix
python3 scripts/etl_series_id_validator.py --post-etl --auto-fix
```

### **After Adding New League**
```bash
# 1. Check for missing series
python3 scripts/monitor_series_id_health.py --league NEW_LEAGUE_ID

# 2. Create missing series (if any)
python3 scripts/monitor_series_id_health.py --league NEW_LEAGUE_ID --fix --no-dry-run

# 3. Populate series_id values
python3 scripts/populate_series_id_in_series_stats.py
```

### **Weekly Health Check**
```bash
# Comprehensive health report
python3 scripts/etl_series_id_validator.py --report --auto-fix
```

## Fixing Current Issues

### **Option 1: Manual Series Creation**
For each missing series, create records in `series` and `series_leagues` tables:

```sql
-- Example: Create missing CITA series
INSERT INTO series (name, created_at) VALUES ('Series 3.0 - 3.5 Singles Thur', CURRENT_TIMESTAMP);
INSERT INTO series_leagues (series_id, league_id, created_at) 
VALUES (LAST_INSERT_ID(), (SELECT id FROM leagues WHERE league_id = 'CITA'), CURRENT_TIMESTAMP);
```

### **Option 2: Automated Fix** (Recommended)
```bash
# This will create missing series and populate series_id values
python3 scripts/monitor_series_id_health.py --fix --no-dry-run
```

### **Option 3: Gradual Approach**
1. Fix one league at a time:
   ```bash
   python3 scripts/monitor_series_id_health.py --league CITA --fix --no-dry-run
   python3 scripts/monitor_series_id_health.py --league CNSWPL --fix --no-dry-run
   python3 scripts/monitor_series_id_health.py --league NSTF --fix --no-dry-run
   ```

## Alert Thresholds

- **✅ EXCELLENT**: 95%+ coverage
- **⚠️ GOOD**: 85-94% coverage  
- **⚠️ FAIR**: 75-84% coverage
- **❌ POOR**: <75% coverage

## Troubleshooting

### **Problem**: New series_stats records have NULL series_id
**Solution**: 
1. Check if series exists: `SELECT * FROM series WHERE name = 'SERIES_NAME'`
2. If missing, create series record
3. Run population script: `python3 scripts/populate_series_id_in_series_stats.py`

### **Problem**: ETL import creates many NULL series_id records
**Solution**:
1. Check ETL logs for series lookup failures
2. Ensure series table has all required series before import
3. Run post-ETL validation: `python3 scripts/etl_series_id_validator.py --post-etl --auto-fix`

### **Problem**: Health score suddenly drops
**Solution**:
1. Check recent changes: `git log --oneline -10`
2. Run health monitor: `python3 scripts/monitor_series_id_health.py`
3. Check for missing series: Look for "Found X series that don't exist in series table"
4. Auto-fix: `python3 scripts/monitor_series_id_health.py --fix --no-dry-run`

## Testing

### **Verify Implementation**
```bash
# Test all validation
python3 scripts/test_series_id_implementation.py

# Check specific functionality
python3 -c "
from database_utils import execute_query_one
# Test series_id query
result = execute_query_one('SELECT COUNT(*) as count FROM series_stats WHERE series_id IS NOT NULL')
print(f'Records with series_id: {result[\"count\"]}')
"
```

### **Integration Tests**
1. **API Test**: Visit `/mobile/my-series` - should show data without "No Series Data" error
2. **Query Test**: Verify series standings load correctly
3. **ETL Test**: Run ETL import and confirm no new NULL series_id records

## Maintenance Schedule

### **Monthly**
- Run comprehensive health report
- Review leagues with <85% coverage
- Plan fixes for persistently problematic series

### **Quarterly** 
- Review series naming conventions
- Update population script with new name variations
- Audit series table for cleanup opportunities

### **Before Major Updates**
- Run pre-update validation
- Create database backup
- Test series_id functionality in staging

## Success Metrics

- **Primary**: >95% series_id coverage across all leagues
- **Secondary**: Zero "No Series Data" errors in production
- **Tertiary**: ETL imports complete without series_id issues

## Emergency Procedures

### **If Series Data Disappears**
1. Check series_id health: `python3 scripts/monitor_series_id_health.py`
2. Check recent database changes: Review git history and deployment logs
3. Run emergency fix: `python3 scripts/etl_series_id_validator.py --auto-fix`
4. Verify fix: Test affected pages like `/mobile/my-series`

### **If ETL Import Fails**
1. Check ETL logs for series lookup errors
2. Run pre-ETL validation: `python3 scripts/etl_series_id_validator.py --pre-etl`
3. Fix issues before retrying import
4. Run post-ETL validation after successful import

This prevention system ensures that the series_id foreign key relationships remain healthy and the "No Series Data" issues never recur. 