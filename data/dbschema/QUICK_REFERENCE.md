# DbSchema Quick Reference 🚀

## ⚡ One-Command Workflows

```bash
# Complete schema deployment (interactive)
python data/dbschema/dbschema_workflow.py

# Automated staging deployment
python data/dbschema/dbschema_workflow.py --auto

# Full deployment to production
python data/dbschema/dbschema_workflow.py --production

# Integrated schema + app deployment
python deployment/deploy_schema_changes.py --production
```

## 🔧 Individual Commands

### Migration Management
```bash
# Generate migration
python data/dbschema/dbschema_migration_manager.py generate -d "description"

# Deploy to staging
python data/dbschema/dbschema_migration_manager.py deploy-staging

# Test staging
python data/dbschema/dbschema_migration_manager.py test-staging

# Deploy to production
python data/dbschema/dbschema_migration_manager.py deploy-production

# Check status
python data/dbschema/dbschema_migration_manager.py status

# View rollback options
python data/dbschema/dbschema_migration_manager.py rollback
```

### Setup & Validation
```bash
# Initial setup
python data/dbschema/setup_dbschema.py

# Validate connections
python data/dbschema/validate_dbschema_connections.py

# Compare schemas
python data/dbschema/compare_schemas_dbschema.py
```

## 🎯 Use Cases

| Scenario | Command |
|----------|---------|
| **New feature with schema changes** | `python deployment/deploy_schema_changes.py --production` |
| **Schema-only changes** | `python data/dbschema/dbschema_workflow.py --production` |
| **Quick staging test** | `python data/dbschema/dbschema_workflow.py --auto` |
| **Emergency schema fix** | `python data/dbschema/dbschema_migration_manager.py generate && deploy-staging` |
| **Check deployment status** | `python data/dbschema/dbschema_migration_manager.py status` |

## 🔒 Safety Features

- ✅ **Automatic backups** before all deployments
- ✅ **Staging testing** required before production
- ✅ **Confirmation prompts** for production changes
- ✅ **Rollback commands** available
- ✅ **Integration testing** with application

## 📁 File Locations

- **Migrations**: `data/dbschema/migrations/`
- **Backups**: `data/dbschema/migrations/*_backup_*.sql`
- **Applied Migrations**: `data/dbschema/migrations/applied_migrations.json`
- **DbSchema Project**: `database_schema/rally_schema.dbs`

## 🚨 Emergency Commands

```bash
# View latest backups
ls -la data/dbschema/migrations/*_backup_*.sql

# Restore staging from backup
psql $DATABASE_STAGING_URL -f data/dbschema/migrations/staging_backup_TIMESTAMP.sql

# Check all connections
python data/dbschema/validate_dbschema_connections.py
```

## 🔗 Environment Variables

```bash
# Required for production
export DATABASE_PUBLIC_URL="postgresql://..."

# Optional for staging
export DATABASE_STAGING_URL="postgresql://..."
```

---

**📖 Full Guide**: See `docs/DBSCHEMA_AUTOMATION_GUIDE.md` for complete documentation 