# Database Synchronization Guide

## Overview
This guide ensures local, staging, and production databases stay synchronized for reliable development and testing.

## Quick Reference Commands

### Production → Local (Full Clone)
```bash
# Complete sync with production data
python scripts/clone_production_to_local.py
```

### Local → Production (Deploy Changes)  
```bash
# Deploy tested changes to production
python data/etl/clone/clone_local_to_railway_auto.py
```

### Production → Staging
```bash
# Sync staging with production for testing
python scripts/clone_production_to_staging_v2.py
```

## When to Sync

### Clone Production → Local When:
- 🐛 Debugging production-specific issues
- 🧪 Testing fixes with real production data  
- 📊 Analyzing production data patterns
- 🔄 Starting new development work

### Clone Local → Production When:
- ✅ All changes tested locally
- ✅ Database migrations validated
- ✅ Ready to deploy new features

## Best Practices

### Before Any Sync:
1. **Commit current work**: `git add . && git commit -m "WIP: before sync"`
2. **Check migrations**: `alembic current` and `alembic history`
3. **Run tests**: Ensure local tests pass

### After Production → Local Sync:
1. **Verify migration state**: `alembic current`
2. **Test critical functions**: User management, data queries
3. **Run validation**: `python scripts/compare_databases.py`

### Database Sync Schedule:
- **Weekly**: Clone production → local for fresh data
- **Before major features**: Ensure working with current production state
- **After production issues**: Clone to debug with exact data

## Troubleshooting

### Foreign Key Constraint Errors:
- Usually indicates missing cascade deletes in code
- Fix deletion order in service functions
- Test locally before deploying

### Migration State Issues:
```bash
# Check current state
alembic current

# Sync migration state without data changes
alembic stamp head
```

### Large Database Performance:
- Use selective sync scripts for specific tables
- Consider data sampling for development
- Regular cleanup of old test data

## Safety Measures

### Always Backup Before Sync:
- Scripts automatically create backups
- Manual backup: `pg_dump rally > backup_$(date +%Y%m%d).sql`

### Verify After Sync:
- Check critical table counts
- Test core functionality
- Validate user authentication

### Recovery Plan:
1. Restore from automatic backup
2. Check git history for code changes  
3. Re-run migrations if needed
4. Contact team if issues persist

## Related Scripts

- `clone_production_to_local.py` - Full production data clone
- `clone_local_to_railway_auto.py` - Deploy local to production  
- `compare_databases.py` - Verify database states match
- `complete_database_clone.py` - Bidirectional cloning tool 