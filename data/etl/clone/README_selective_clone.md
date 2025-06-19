# Selective Table Clone Tool

This tool allows you to clone only specific tables from your local Rally database to Railway, rather than cloning the entire database.

## Usage

```bash
python data/etl/clone/clone_local_to_railway_selective.py
```

## Configuration

Edit the `TABLES_TO_CLONE` list at the top of the script to specify which tables you want to clone:

```python
TABLES_TO_CLONE = [
    # Core lookup tables first
    'users',
    'companies',
    'contacts',
    
    # Main data tables
    'activities',
    'opportunities',
    'deals',
    
    # Junction/relationship tables last
    'activity_contacts',
    'opportunity_contacts',
]
```

### Configuration Options

- **`TABLES_TO_CLONE`**: List of table names to clone (order matters for foreign keys)
- **`TRUNCATE_BEFORE_CLONE`**: Whether to clear existing data before cloning (default: True)
- **`DISABLE_FK_CHECKS`**: Whether to disable foreign key checks during cloning (default: True)

## Features

### ✅ Safety Features
- **Backup Creation**: Creates a backup of existing Railway table data before overwriting
- **Table Verification**: Ensures all specified tables exist in both databases before starting
- **Connection Testing**: Verifies database connections before proceeding
- **Data Verification**: Compares row counts after cloning to ensure success

### ⚡ Performance Features
- **Data-Only Dumps**: Only transfers data (assumes schema already exists)
- **Selective Operations**: Only affects specified tables, leaving others untouched
- **Foreign Key Handling**: Properly manages foreign key constraints during the process
- **Dependency Order**: Respects table dependencies when truncating/restoring

### 🔧 Technical Features
- **PostgreSQL Compatible**: Uses native PostgreSQL tools (pg_dump, psql)
- **Railway Optimized**: Handles Railway-specific connection requirements
- **Comprehensive Logging**: Detailed logs saved to `logs/selective_database_clone.log`
- **Error Handling**: Graceful error handling with detailed error messages

## Example Output

```
Selective Table Clone Tool (Local to Railway)
============================================================
📋 Tables to clone: users, companies, contacts, activities
🗑️  Truncate before clone: True
🔗 Disable FK checks: True
⚠️  This will REPLACE specified Railway table data with local data!
Starting in 3 seconds...

🚀 Starting selective table clone process...
📋 Tables to clone: users, companies, contacts, activities
✅ Local database connected: PostgreSQL 15.4
✅ Railway database connected: PostgreSQL 15.4
✅ Railway tables backed up successfully to railway_selective_backup_20241201_143022.sql
✅ Local tables dumped successfully to local_selective_dump_20241201_143022.sql
✅ Truncated table: activities
✅ Truncated table: contacts
✅ Truncated table: companies
✅ Truncated table: users
✅ Data insertion detected: 4 COPY operations, 0 INSERT operations
✅ Local tables restored to Railway database successfully
✅ users: 150 rows (matches)
✅ companies: 75 rows (matches)
✅ contacts: 300 rows (matches)
✅ activities: 1250 rows (matches)
✅ Selective clone verification successful - all specified table counts match!
🎉 Selective table clone completed successfully!
📁 Railway backup created: railway_selective_backup_20241201_143022.sql
🔄 Railway tables now match local: users, companies, contacts, activities
```

## When to Use

- **Development Testing**: When you want to sync specific test data
- **Incremental Updates**: When only certain tables have changed
- **Performance**: When full database clone is too slow/expensive
- **Selective Sync**: When you want to preserve some Railway data while updating others

## Important Notes

1. **Table Dependencies**: List tables in dependency order (parent tables before child tables)
2. **Schema Assumptions**: This tool assumes the table schemas already exist in Railway
3. **Data Replacement**: Existing data in specified tables will be replaced
4. **Backup Files**: Backup files are created but not automatically cleaned up
5. **Foreign Keys**: The tool can handle foreign key constraints but depends on proper table ordering

## Troubleshooting

- **Connection Issues**: Ensure Railway proxy is running and accessible
- **Foreign Key Errors**: Check table order in `TABLES_TO_CLONE`
- **Missing Tables**: Verify table names exist in both databases
- **Permission Errors**: Ensure database users have proper permissions
- **Version Conflicts**: Check that PostgreSQL versions are compatible

## Logs

All operations are logged to `logs/selective_database_clone.log` for debugging and audit purposes. 