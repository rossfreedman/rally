# Atomic ETL Guide

## Overview

The atomic ETL scripts provide **true transactional behavior** for database imports, ensuring either **ALL operations succeed** or **NONE of them do**. This solves the problem of partial data imports that leave the database in an inconsistent state.

## Problem Solved

### Before (Non-Atomic ETL)
- ETL process has multiple commits throughout
- If import fails partway through, database is left in partial state
- Application shows errors due to missing/inconsistent data
- Manual cleanup required

### After (Atomic ETL)
- Single transaction wraps entire ETL process
- **ALL operations succeed** → Single commit
- **ANY operation fails** → Complete rollback
- Database is never left in inconsistent state

## Available Scripts

### 1. `atomic_etl_import.py` - Standalone Atomic ETL
**Best for**: Simple, clean atomic imports with essential data only

```bash
# Basic usage
python data/etl/database_import/atomic_etl_import.py

# With options
python data/etl/database_import/atomic_etl_import.py --environment local --no-backup
python data/etl/database_import/atomic_etl_import.py --environment railway_staging
python data/etl/database_import/atomic_etl_import.py --environment railway_production --force
```

**Features:**
- ✅ Lightweight, purpose-built for atomic operations
- ✅ Essential data import (players, matches, basic stats)
- ✅ Fast execution
- ✅ Clear error handling
- ✅ Automatic backup/restore

### 2. `atomic_wrapper.py` - Atomic Wrapper for Full ETL
**Best for**: Full-featured imports with all existing ETL capabilities

```bash
# Basic usage
python data/etl/database_import/atomic_wrapper.py

# With options
python data/etl/database_import/atomic_wrapper.py --environment local --no-backup
python data/etl/database_import/atomic_wrapper.py --environment railway_staging
python data/etl/database_import/atomic_wrapper.py --environment railway_production --force
```

**Features:**
- ✅ Full ETL functionality (all data types, validations, associations)
- ✅ Wraps existing `ComprehensiveETL` class
- ✅ All existing features preserved
- ✅ Atomic transaction behavior added
- ✅ Backward compatible

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--environment` | Target environment (`local`, `railway_staging`, `railway_production`) | Auto-detect |
| `--no-backup` | Skip backup creation | Create backup |
| `--force` | Force import in production (safety check) | Require confirmation |

## Safety Features

### 1. Automatic Backup
- Creates full database backup before starting
- Automatic restore on failure
- Manual restore option if needed

### 2. Environment Detection
- Auto-detects local vs Railway environments
- Production requires `--force` flag for safety
- Environment-specific optimizations

### 3. Transaction Timeouts
- Extended timeouts for large imports
- Prevents timeout during long operations
- Optimized connection settings

### 4. Validation
- Pre-import data validation
- Post-import consistency checks
- Rollback on any validation failure

## Usage Examples

### Local Development
```bash
# Quick local import with backup
python data/etl/database_import/atomic_etl_import.py

# Local import without backup (faster)
python data/etl/database_import/atomic_etl_import.py --no-backup

# Full ETL features locally
python data/etl/database_import/atomic_wrapper.py --environment local
```

### Staging Environment
```bash
# Staging import with all features
python data/etl/database_import/atomic_wrapper.py --environment railway_staging

# Staging import without backup
python data/etl/database_import/atomic_wrapper.py --environment railway_staging --no-backup
```

### Production Environment
```bash
# Production import (requires --force)
python data/etl/database_import/atomic_wrapper.py --environment railway_production --force

# Production with backup skip (not recommended)
python data/etl/database_import/atomic_wrapper.py --environment railway_production --force --no-backup
```

## How It Works

### 1. Atomic Transaction Flow
```
1. Create backup (optional)
2. Start single database transaction
3. Clear all target tables
4. Import all data (no intermediate commits)
5. Validate all data
6. SUCCESS: Single commit → All changes saved
7. FAILURE: Rollback → Database unchanged
```

### 2. Error Handling
```
If ANY step fails:
├── Rollback entire transaction
├── Database returns to original state
├── Attempt automatic restore from backup
└── Log detailed error information
```

### 3. Backup Strategy
```
Backup created before import:
├── Full database dump
├── Stored in data/backups/
├── Automatic restore on failure
└── Manual restore option available
```

## Monitoring and Logging

### Success Indicators
```
✅ Database backup completed successfully
✅ All operations completed successfully
✅ Atomic transaction committed successfully
🎉 ATOMIC ETL COMPLETED SUCCESSFULLY
```

### Failure Indicators
```
❌ ETL failed: [error message]
🔄 Rolling back entire atomic transaction...
✅ Atomic transaction rolled back - database unchanged
✅ Database restored to original state
```

### Progress Monitoring
```
📂 Loading JSON data files...
🔍 Validating data...
🧹 Clearing target tables...
📥 Importing leagues...
📥 Importing players...
📊 Total records imported: 45,234
```

## Troubleshooting

### Common Issues

#### 1. Timeout Errors
```
Error: "statement_timeout"
Solution: Increase timeout or reduce batch size
```

#### 2. Memory Issues
```
Error: "out of memory"
Solution: Use smaller batches or increase available memory
```

#### 3. Connection Issues
```
Error: "connection lost"
Solution: Check network stability and database availability
```

#### 4. Lock Conflicts
```
Error: "could not obtain lock"
Solution: Ensure no other processes are accessing the database
```

### Recovery Procedures

#### 1. Automatic Recovery
- Atomic ETL automatically rolls back on failure
- Database remains in consistent state
- Backup automatically restored if available

#### 2. Manual Recovery
```bash
# If automatic restore fails, restore manually
python data/backup_restore_local_db/backup_database.py --restore [backup_path]
```

#### 3. Verify Database State
```bash
# Check database health after recovery
python data/etl/validation/etl_validation_pipeline.py
```

## Performance Considerations

### Batch Sizes
- **Local**: 1000 records per batch
- **Railway Staging**: 500 records per batch
- **Railway Production**: 1000 records per batch

### Memory Usage
- **Work Memory**: 256MB-512MB
- **Maintenance Memory**: 512MB-1GB
- **Cache Size**: 512MB-1GB

### Connection Settings
- **Statement Timeout**: 30-60 minutes
- **Idle Timeout**: 60-120 minutes
- **Connection Pooling**: Disabled during atomic operations

## Best Practices

### 1. Pre-Import Checklist
- [ ] Verify JSON data files exist
- [ ] Check available disk space
- [ ] Ensure database is accessible
- [ ] Confirm no other ETL processes running
- [ ] Review environment settings

### 2. During Import
- [ ] Monitor progress logs
- [ ] Watch for error messages
- [ ] Don't interrupt the process
- [ ] Ensure stable network connection

### 3. Post-Import Validation
- [ ] Check import summary
- [ ] Validate key metrics
- [ ] Test application functionality
- [ ] Verify user data integrity

### 4. Rollback Strategy
- [ ] Always create backups for production
- [ ] Test restore procedures
- [ ] Document recovery steps
- [ ] Have rollback plan ready

## Comparison with Original ETL

| Feature | Original ETL | Atomic ETL |
|---------|-------------|------------|
| **Transaction Model** | Multiple commits | Single transaction |
| **Failure Recovery** | Manual cleanup | Automatic rollback |
| **Data Consistency** | Partial states possible | Always consistent |
| **Backup Integration** | Manual process | Automatic backup/restore |
| **Error Handling** | Continue on errors | Fail fast, rollback |
| **Performance** | Optimized for speed | Optimized for reliability |
| **Complexity** | Complex state management | Simple all-or-nothing |

## Migration from Original ETL

### Step 1: Test with Atomic ETL
```bash
# Test locally first
python data/etl/database_import/atomic_wrapper.py --environment local

# Test on staging
python data/etl/database_import/atomic_wrapper.py --environment railway_staging
```

### Step 2: Update Scripts
```bash
# Replace existing ETL calls with atomic versions
# OLD: python data/etl/database_import/import_all_jsons_to_database.py
# NEW: python data/etl/database_import/atomic_wrapper.py
```

### Step 3: Update Documentation
- Update deployment scripts
- Update operational procedures
- Train team on new atomic behavior

## Conclusion

The atomic ETL scripts provide a robust, reliable solution for database imports that eliminates the risk of partial data states. By wrapping the entire ETL process in a single transaction, you get:

- **Guaranteed consistency**: Database is never left in a partial state
- **Automatic recovery**: Failures are handled gracefully with automatic rollback
- **Safety features**: Backups, validations, and safety checks built-in
- **Operational simplicity**: All-or-nothing behavior is easier to reason about

**Recommendation**: Use `atomic_wrapper.py` for production systems to maintain all existing ETL functionality while gaining atomic transaction benefits. 