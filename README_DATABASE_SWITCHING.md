# Rally Database Switching

Simple approach to switch between databases with the same Rally application.

## Overview

Instead of maintaining separate applications, Rally now supports database switching via environment variables:

- **Main Database**: `rally` (production data)
- **Test Database**: `rally_test` (for testing new ETL)

## Quick Start

### Step 1: Clone Database (First Time Setup)

```bash
# Clone main database to test database
./clone_to_test_db.sh
```

### Step 2: Use Startup Scripts

```bash
# Start with main database
./start_rally_main.sh

# Start with test database  
./start_rally_test.sh
```

### Option 2: Manual Environment Variables

```bash
# Main database
export RALLY_DATABASE=main
python server.py

# Test database
export RALLY_DATABASE=test
python server.py
```

## Database URLs

- **Main**: `postgresql://localhost/rally`
- **Test**: `postgresql://postgres:postgres@localhost:5432/rally_test`

You can override these with environment variables:
- `DATABASE_URL` (main database)
- `DATABASE_TEST_URL` (test database)

## ETL Testing

All new ETL files are in `data/etl_new/`:
- Core incremental ETL logic
- Change detection
- New processors and orchestrators

## Workflow

1. **Clone**: `./clone_to_test_db.sh` (creates test DB with current data)
2. **Test**: `./start_rally_test.sh` (run Rally with test DB)
3. **Develop**: Modify files in `data/etl_new/`
4. **Switch**: `./start_rally_main.sh` (back to main DB)

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