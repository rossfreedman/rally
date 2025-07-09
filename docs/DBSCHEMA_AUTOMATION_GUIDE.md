# DbSchema Automation Guide for Rally 🎯

**Complete automation for database schema changes from local → staging → production**

## 🚀 Quick Start

### 1. **Set Up DbSchema** (One-time setup)
```bash
# Install DbSchema and set up project
python data/dbschema/setup_dbschema.py

# Validate connections
python data/dbschema/validate_dbschema_connections.py
```

### 2. **Deploy Schema Changes** (Everyday workflow)
```bash
# Option A: Interactive workflow (recommended for learning)
python data/dbschema/dbschema_workflow.py

# Option B: Automated workflow (staging only)
python data/dbschema/dbschema_workflow.py --auto

# Option C: Complete deployment (staging + production)
python data/dbschema/dbschema_workflow.py --production
```

### 3. **Integrated Deployment** (Schema + Application)
```bash
# Deploy both schema and application changes together
python deployment/deploy_schema_changes.py --production
```

## 📁 File Overview

| File | Purpose |
|------|---------|
| `dbschema_migration_manager.py` | Core migration management |
| `dbschema_workflow.py` | Complete automated workflow |
| `deploy_schema_changes.py` | Integration with app deployment |
| `setup_dbschema.py` | Initial DbSchema setup |
| `validate_dbschema_connections.py` | Connection testing |
| `compare_schemas_dbschema.py` | Schema comparison |

## 🔄 Automated Workflows

### **Workflow 1: Schema-Only Deployment**

**Purpose**: Deploy database schema changes independently

```bash
python data/dbschema/dbschema_workflow.py
```

**Steps**:
1. 📝 Generate migration from local schema
2. 🧪 Deploy to staging with backup
3. ✅ Test staging environment
4. 🚀 Deploy to production (optional)
5. 🔍 Validate production deployment

### **Workflow 2: Integrated Deployment**

**Purpose**: Deploy schema + application changes together

```bash
python deployment/deploy_schema_changes.py --production
```

**Steps**:
1. 🔍 Prerequisites check
2. 📝 Deploy schema to staging
3. 📦 Deploy application to staging
4. 🧪 Integration testing on staging
5. 🚀 Deploy both to production
6. ✅ Production validation

## 🛠️ Individual Commands

### **Migration Management**
```bash
# Generate migration from local changes
python data/dbschema/dbschema_migration_manager.py generate --description "add_user_preferences"

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

### **Environment Comparison**
```bash
# Compare local vs Railway schemas
python data/dbschema/compare_schemas_dbschema.py

# Validate all connections
python data/dbschema/validate_dbschema_connections.py
```

## 🏗️ Architecture

### **Migration Flow**
```
Local Schema Changes
        ↓
Generate Migration File
        ↓
Deploy to Staging (with backup)
        ↓
Test on Staging
        ↓
Deploy to Production (with confirmation)
        ↓
Validate Production
```

### **Integration with Railway**
```
DbSchema Migration ───┐
                      ├─→ Staging Environment
Application Deploy ───┘         ↓
                                Testing
                                ↓
DbSchema Migration ───┐
                      ├─→ Production Environment
Application Deploy ───┘         ↓
                              Validation
```

## 📋 Environment Setup

### **Required Environment Variables**
```bash
# Staging database (optional but recommended)
DATABASE_STAGING_URL="postgresql://user:pass@staging-host:port/database"

# Production database
DATABASE_PUBLIC_URL="postgresql://user:pass@production-host:port/database"
```

### **DbSchema Configuration**
- **Local Connection**: `localhost:5432/rally`
- **Staging Connection**: Via `DATABASE_STAGING_URL`
- **Production Connection**: Via `DATABASE_PUBLIC_URL`

## 🔒 Safety Features

### **Automatic Backups**
- ✅ Schema backup before staging deployment
- ✅ Schema backup before production deployment
- ✅ Timestamped backup files in `data/dbschema/migrations/`

### **Validation Steps**
- ✅ Schema comparison after deployment
- ✅ Application tests on staging
- ✅ Production validation tests
- ✅ Integration testing checklist

### **Confirmation Requirements**
- ✅ Interactive confirmations for production
- ✅ Explicit "YES" confirmation for production schema changes
- ✅ "PRODUCTION" confirmation for integrated deployments

## 📝 Migration Files

### **File Structure**
```
data/dbschema/migrations/
├── 20241208_143000_add_user_preferences.sql
├── 20241208_150000_update_team_structure.sql
├── staging_backup_20241208_143000.sql
├── production_backup_20241208_150000.sql
└── applied_migrations.json
```

### **Migration File Format**
```sql
-- DbSchema Migration: 20241208_143000_add_user_preferences
-- Generated: 2024-12-08T14:30:00.000000
-- Description: Add user preferences table

BEGIN;

-- Migration starts here
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    preference_key VARCHAR(255) NOT NULL,
    preference_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_key ON user_preferences(preference_key);

-- Migration ends here

COMMIT;

-- Rollback script (uncomment if needed):
-- BEGIN;
-- DROP TABLE user_preferences;
-- COMMIT;
```

## 🧪 Testing Strategy

### **Staging Tests**
1. **Automated Tests**: Via `test_staging_session_refresh.py`
2. **Schema Validation**: Compare local vs staging schemas
3. **Manual Testing Checklist**:
   - [ ] Login functionality works
   - [ ] Schema changes reflected in UI
   - [ ] New features work as expected
   - [ ] Existing functionality preserved
   - [ ] No console errors

### **Production Tests**
1. **Automated Tests**: Via `test_production_session_refresh.py`
2. **Schema Validation**: Production schema integrity
3. **Post-Deployment Monitoring**:
   - [ ] Monitor application logs
   - [ ] Check key user workflows
   - [ ] Verify database performance
   - [ ] Monitor error rates

## 🚨 Rollback Procedures

### **Automatic Rollback Information**
```bash
# View available backups
python data/dbschema/dbschema_migration_manager.py rollback
```

### **Manual Rollback Steps**
```bash
# Restore staging from backup
psql $DATABASE_STAGING_URL -f data/dbschema/migrations/staging_backup_TIMESTAMP.sql

# Restore production from backup (EMERGENCY ONLY)
psql $DATABASE_PUBLIC_URL -f data/dbschema/migrations/production_backup_TIMESTAMP.sql
```

## 📈 Usage Examples

### **Example 1: Add New Table**
```bash
# 1. Make schema changes in local database (via DbSchema GUI or SQL)
# 2. Generate migration
python data/dbschema/dbschema_migration_manager.py generate --description "add_notifications_table"

# 3. Deploy to staging
python data/dbschema/dbschema_migration_manager.py deploy-staging

# 4. Test on staging
python data/dbschema/dbschema_migration_manager.py test-staging

# 5. Deploy to production
python data/dbschema/dbschema_migration_manager.py deploy-production
```

### **Example 2: Integrated Feature Deployment**
```bash
# Deploy new feature with schema + app changes
python deployment/deploy_schema_changes.py --production
```

### **Example 3: Emergency Schema Fix**
```bash
# Quick schema fix to staging only
python data/dbschema/dbschema_workflow.py --auto
```

## 🔧 Troubleshooting

### **Common Issues**

#### ❌ "DbSchema CLI not found"
```bash
# Solution: Install DbSchema and add to PATH
# Download from: https://dbschema.com/download.html
# Add to PATH: /Applications/DbSchema.app/Contents/bin/dbschema
```

#### ❌ "Migration failed on staging"
```bash
# Check staging database connection
python data/dbschema/validate_dbschema_connections.py

# Review migration file for syntax errors
cat data/dbschema/migrations/latest_migration.sql

# Check staging logs for detailed errors
```

#### ❌ "Schema comparison failed"
```bash
# Update environment variables
export DATABASE_STAGING_URL="postgresql://..."
export DATABASE_PUBLIC_URL="postgresql://..."

# Retry comparison
python data/dbschema/compare_schemas_dbschema.py
```

### **Support Commands**
```bash
# Check all connections
python data/dbschema/validate_dbschema_connections.py

# View migration status
python data/dbschema/dbschema_migration_manager.py status

# Compare schemas
python data/dbschema/compare_schemas_dbschema.py

# Check deployment status
python deployment/check_deployment_status.py
```

## 🎯 Best Practices

### **Development Workflow**
1. **Design in DbSchema**: Use visual tools to design schema changes
2. **Test Locally**: Ensure changes work in local environment
3. **Generate Migration**: Use automated migration generation
4. **Deploy to Staging**: Always test on staging first
5. **Validate Changes**: Run comprehensive tests
6. **Deploy to Production**: Only after staging validation

### **Safety Guidelines**
- ✅ **Always backup** before production changes
- ✅ **Test on staging** before production
- ✅ **Monitor post-deployment** for issues
- ✅ **Have rollback plan** ready
- ✅ **Document changes** in migration descriptions

### **Performance Considerations**
- ⚡ **Index Management**: Add indexes for new columns
- ⚡ **Constraint Timing**: Add constraints during low-traffic periods
- ⚡ **Data Migration**: Use batched updates for large tables
- ⚡ **Lock Minimization**: Design migrations to minimize table locks

## 🔗 Integration with Existing Workflow

### **Git Integration**
```bash
# Schema changes are tracked in git
git add data/dbschema/migrations/
git commit -m "Add user preferences schema migration"

# Deploy with existing deployment workflow
python deployment/deploy_schema_changes.py --production
```

### **Railway Integration**
- **Staging Environment**: Automatic deployment on staging branch push
- **Production Environment**: Automatic deployment on main branch push
- **Database Migrations**: Applied before application deployment

### **Monitoring Integration**
- **Health Checks**: Integrated with existing health monitoring
- **Error Tracking**: Schema deployment errors tracked in logs
- **Performance Monitoring**: Database performance impact measured

---

## 🎉 You're Ready!

This automation system provides:
- ✅ **Safe schema deployments** with automatic backups
- ✅ **Integrated testing** on staging before production
- ✅ **Rollback capabilities** for emergency situations
- ✅ **Integration** with existing Rally deployment workflow

Start with the interactive workflow to learn the system, then use automated workflows for regular deployments.

**Next Steps**:
1. Run the setup: `python data/dbschema/setup_dbschema.py`
2. Make a test schema change
3. Try the workflow: `python data/dbschema/dbschema_workflow.py` 