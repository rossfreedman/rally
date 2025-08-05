# Rally Database Switching

Simple approach to switch between databases with the same Rally application.

## Overview

Instead of maintaining separate applications, Rally now supports database switching via environment variables:

- **Main Database**: `rally` (production data)
- **Test Database**: `rally_test` (decommissioned - no longer available)

**Note**: Test database has been decommissioned to prevent accidental usage.

## Quick Start

### Step 1: Use Startup Scripts

```bash
# Start with main database
./start_rally_main.sh

# Start with main database (test script now uses main DB)
./start_rally_test.sh
```

### Option 2: Manual Environment Variables

```bash
# Main database
export RALLY_DATABASE=main
python server.py

# Test database (decommissioned - will fail)
export RALLY_DATABASE=test
python server.py
```

## Database URLs

- **Main**: `postgresql://localhost/rally`
- **Test**: `postgresql://postgres:postgres@localhost:5432/rally_test` (decommissioned)

You can override these with environment variables:
- `DATABASE_URL` (main database)
- `DATABASE_TEST_URL` (test database - decommissioned)

## ETL Testing

All new ETL files are in `data/etl_new/`:
- Core incremental ETL logic
- Change detection
- New processors and orchestrators

## Workflow

1. **Test**: `./start_rally_test.sh` (now uses main DB)
2. **Develop**: Modify files in `data/etl_new/`
3. **Switch**: `./start_rally_main.sh` (back to main DB)

## Benefits

✅ **Single application** - No duplicate code  
✅ **Easy switching** - Just change environment variable  
✅ **Same codebase** - All features work on both databases  
✅ **Organized ETL** - All new ETL code in one place  
✅ **No port conflicts** - Both use same port (5000)  
✅ **Safe testing** - Test DB is completely separate

## Migration from Rally2

The old Rally2 structure has been simplified:
- ❌ `server_incremental.py` - No longer needed
- ❌ `config_incremental.py` - Integrated into main config
- ❌ `start_incremental_rally.sh` - Replaced with simpler scripts
- ❌ Port 5001 - Everything uses port 5000
- ✅ `data/etl_new/` - All new ETL code here

## Test Database Decommissioning

The test database (`rally_test`) has been decommissioned to prevent accidental usage of test data in production scenarios. All operations now use the main database by default. 