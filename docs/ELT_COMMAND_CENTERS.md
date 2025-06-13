# Rally ELT Command Centers

Rally now has two command centers for running ELT operations:

## 🏓 Local Real Database Command Center (`etl/run_etl_local.py`)

Runs ELT operations against your **local real database**.

```bash
cd etl
python run_etl_local.py --run        # Run complete ELT pipeline
python run_etl_local.py --validate  # Validate ELT pipeline
python run_etl_local.py --run --validate # Run + validate
python run_etl_local.py --individual # Run scripts one by one
python run_etl_local.py --files     # Show file locations
```

**Use this for:**
- Local development data imports
- Regular ELT runs during development
- When you're confident your data is ready

## 🧪 Local Test Database Command Center (`etl/run_etl_test.py`)

Creates a **temporary local test database** and runs ELT operations safely.

```bash
cd etl
python run_etl_test.py --run         # Test ELT pipeline safely
python run_etl_test.py --validate   # Test validation
python run_etl_test.py --run --validate # Test everything
python run_etl_test.py --individual # Test scripts one by one
```

**Use this for:**
- Testing new scraped data
- Validating ELT scripts before production
- Experimenting with changes safely
- Learning how the ELT pipeline works

## How Local Test Database Center Works

1. **Creates Test Database**: Automatically creates `rally_etl_test` local database
2. **Clones Schema**: Copies your local real database structure (tables, indexes, constraints)
3. **Runs ELT Scripts**: Executes scripts against the test database using environment variables
4. **Validates Results**: Optionally runs validation checks
5. **Cleans Up**: Automatically deletes the test database when done

## Key Differences

| Feature | Local Real (`run_etl_local.py`) | Local Test (`run_etl_test.py`) |
|---------|-------------------------|-------------------------|
| Target Database | Local real database | Temporary local test database |
| Data Safety | ⚠️ Changes your real local data | ✅ Safe - isolated testing |
| Schema | Uses existing local schema | Clones local real database schema |
| Cleanup | No cleanup needed | Auto-deletes test database |
| Use Case | Local development imports | Safe testing |

## Examples

### Testing New Data Safely
```bash
# Test your latest scraped data before importing to your real local database
cd etl
python run_etl_test.py --run --validate
```

### Local Development Import
```bash
# Once tested, run against your real local database
cd etl
python run_etl_local.py --run --validate
```

### Troubleshooting Individual Scripts
```bash
# Test individual scripts with prompts
cd etl
python run_etl_test.py --individual
```

## File Locations

Both command centers are located in the `etl/` directory:

- `etl/run_etl_local.py` - Local real database command center
- `etl/run_etl_test.py` - Local test database command center
- `etl/README.md` - Complete ELT documentation

## Environment Variables

The test center automatically sets these environment variables to redirect scripts to the test database:

- `DATABASE_URL` - Points to test database
- `DATABASE_PUBLIC_URL` - Points to test database

## Recommendation

1. **Always test first**: Use `run_etl_test.py` when trying new data or changes
2. **Local development after validation**: Use `run_etl_local.py` only after successful testing
3. **Check validation**: Always use `--validate` to ensure data integrity
4. **Use `--files`**: When in doubt, check file locations with `--files` option

This two-tier approach ensures your real local database stays safe while giving you full testing capabilities! 