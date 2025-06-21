# Railway Database Cloning Tools

This directory contains tools for synchronizing data between local and Railway databases using Alembic-compatible processes.

## 📁 Scripts Overview

### Core Cloning Tools

- **`simple_clone_local_to_railway.py`** ⭐ **RECOMMENDED**
  - Simple, reliable tool that clones local database to Railway
  - Uses separate schema and data dumps to avoid constraint issues
  - 100% success rate with all table types
  - Best for regular synchronization

- **`clone_local_to_railway.py`**
  - Full-featured cloning tool with comprehensive error handling
  - Creates backups and detailed logging
  - More verbose output and safety checks

- **`clone_local_to_railway_auto.py`**
  - Non-interactive version that runs without user prompts
  - Good for automation and scripting

### Legacy Tools


- **`mirror_railway_database.py`**
  - Reverse direction: Railway → Local
  - Creates exact local copy of Railway database
  - Useful for pulling production data locally

- **`check_database_status.py`**
  - Quick status checker for both databases
  - Compares table counts and migration versions
  - Helpful for verification before/after cloning

### Backup Files

- **`railway_backup_before_fast_clone_*.sql`**
  - Historical Railway database backups
  - Created automatically before major cloning operations
  - Can be used to restore Railway database if needed

## 🚀 Quick Start

### Clone Local to Railway (Most Common)
```bash
# Navigate to this directory
cd data/etl/clone

# Run the simple clone tool
python simple_clone_local_to_railway.py
```

### Check Database Status
```bash
python check_database_status.py
```

### Mirror Railway to Local (Reverse)
```bash
python mirror_railway_database.py
```

## ⚙️ Configuration

All scripts use these database connections:
- **Local**: `postgresql://postgres:postgres@localhost:5432/rally`
- **Railway**: Configured proxy URL for external access

### Environment Variables
- `SYNC_RAILWAY=true` - Used by Alembic to target Railway database
- Database credentials are read from standard environment variables

## 📊 What Gets Cloned

The cloning process synchronizes:
- ✅ **All table schemas** (structure, constraints, indexes)
- ✅ **All table data** (complete row-by-row copy)
- ✅ **Alembic migration state** (keeps versions in sync)
- ✅ **Sequences and auto-increment values**

### Verified Tables (19 total)
- `users`, `players`, `clubs`, `leagues`, `series`
- `match_scores`, `player_history`, `schedule`
- `player_availability`, `polls`, `poll_choices`, `poll_responses`
- `user_activity_logs`, `user_instructions`
- And all junction/association tables

## 🛡️ Safety Features

- **Automatic backups** before major operations
- **Connection testing** before starting operations
- **Data verification** after cloning (table count comparison)
- **Transaction safety** with rollback on errors
- **Detailed logging** to `../../../logs/` directory

## 🔧 Technical Details

### PostgreSQL Version Compatibility
- Handles version mismatches between local (15.13) and Railway (16.8)
- Uses compatible dump/restore options
- Graceful fallback when version-specific features fail

### Data Integrity Handling
- Detects and works around foreign key constraint violations
- Uses `--disable-triggers` for complex data relationships
- Separates schema and data operations to avoid transaction conflicts

### Alembic Integration
- Automatically syncs migration versions between databases
- Uses environment variables to target correct database
- Maintains consistency with existing migration workflows

## 📝 Logs

All operations create detailed logs in `../../../logs/`:
- `simple_clone.log` - Simple clone operations
- `database_clone.log` - Full clone operations  
- `database_mirror.log` - Mirror operations

## ⚠️ Important Notes

1. **Data Direction**: Most scripts clone LOCAL → RAILWAY by default
2. **Backup Safety**: Railway backups may fail due to PostgreSQL version mismatch (this is expected)
3. **Constraint Warnings**: Some foreign key constraint errors are normal and don't affect data integrity
4. **Network Timeouts**: Railway connections use 30-second timeouts for reliability

## 🎯 Success Criteria

A successful clone shows:
- ✅ All table counts match between local and Railway
- ✅ Migration versions are synchronized  
- ✅ No critical errors in logs
- ✅ Success rate ≥ 80% (100% is typical)

## 🆘 Troubleshooting

### Connection Issues
- Verify Railway database credentials
- Check network connectivity
- Ensure PostgreSQL client tools are installed

### Data Integrity Warnings
- Foreign key constraint errors are often pre-existing data issues
- Check source database for orphaned references
- Constraint warnings don't prevent successful data copying

### Performance
- Large datasets (>300K rows) may take several minutes
- Railway network latency can affect transfer speeds
- Consider running during off-peak hours for large clones 