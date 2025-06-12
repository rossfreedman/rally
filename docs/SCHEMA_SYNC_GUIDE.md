# 🗂️ Schema Synchronization Guide

Complete guide for keeping SQLAlchemy models and database schema in sync for the Rally application.

## 🎯 Current Status: ✅ SYNCHRONIZED

Your schema management system is now fully set up and operational!

- **✅ Alembic Initialized**: Baseline migration created and applied
- **✅ 15 Tables**: All database tables have corresponding SQLAlchemy models  
- **✅ Models Fixed**: Critical missing columns added to User and Player models
- **✅ Automation Tools**: Schema sync manager and workflow scripts ready
- **🌍 Multi-Environment**: Local ↔ Railway synchronization system

## 🛠️ Available Tools

### 1. Schema Sync Manager (`scripts/schema_sync_manager.py`)
Detects and analyzes differences between database and models.

```bash
# Check current sync status
python scripts/schema_sync_manager.py --check

# Generate detailed report
python scripts/schema_sync_manager.py --report

# Initialize Alembic (already done)
python scripts/schema_sync_manager.py --init-baseline
```

### 2. Schema Workflow (`scripts/schema_workflow.py`)
Complete automation for common schema management tasks.

```bash
# Quick status check
python scripts/schema_workflow.py --status

# Create migration for model changes
python scripts/schema_workflow.py --create-migration "add_new_column"

# Apply pending migrations
python scripts/schema_workflow.py --apply-migrations

# Complete sync workflow
python scripts/schema_workflow.py --sync

# Pre-commit validation
python scripts/schema_workflow.py --pre-commit

# Validate models
python scripts/schema_workflow.py --validate

# Create backup
python scripts/schema_workflow.py --backup
```

### 3. **🌍 Multi-Environment Sync (`scripts/multi_env_schema_sync.py`)**
**NEW!** Manages synchronization between local and Railway production databases.

```bash
# Check both environment status
python scripts/multi_env_schema_sync.py --status

# Test connections to both environments
python scripts/multi_env_schema_sync.py --test-connections

# Preview what would be deployed to Railway
python scripts/multi_env_schema_sync.py --sync-to-railway --dry-run

# Deploy local changes to Railway production
python scripts/multi_env_schema_sync.py --sync-to-railway

# Sync local to match Railway (for team coordination)
python scripts/multi_env_schema_sync.py --sync-from-railway

# Create production backup
python scripts/multi_env_schema_sync.py --backup railway
```

### 4. Standard Alembic Commands
Direct Alembic usage for advanced scenarios.

```bash
# Check current migration status
alembic current

# Create migration manually
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1

# Check if database is up to date
alembic check
```

## 🌍 Multi-Environment Workflow

### **Environment Configuration**

Your system automatically detects and manages:

- **🏠 Local Development**: `localhost:5432` (your PostgreSQL)
- **🚂 Railway Production**: `ballast.proxy.rlwy.net:40911` (Railway hosting)

### **Daily Development with Railway**

#### **1. Check Environment Status**
Always start by checking both environments:

```bash
python scripts/multi_env_schema_sync.py --status
```

This shows you:
- Connection status to both databases
- Current migration revisions
- Table counts
- Synchronization status

#### **2. Making Schema Changes**

When you modify SQLAlchemy models:

```bash
# Step 1: Create migration locally
python scripts/schema_workflow.py --create-migration "add_user_preferences"

# Step 2: Apply to local database
python scripts/schema_workflow.py --apply-migrations

# Step 3: Test your changes locally
# ... test your application ...

# Step 4: Preview Railway deployment
python scripts/multi_env_schema_sync.py --sync-to-railway --dry-run

# Step 5: Deploy to Railway production
python scripts/multi_env_schema_sync.py --sync-to-railway
```

#### **3. Team Coordination**

When a teammate deploys schema changes to Railway:

```bash
# Pull Railway's current state to your local
python scripts/multi_env_schema_sync.py --sync-from-railway

# This ensures your local matches production
```

### **Production Deployment Process**

The Railway deployment process includes automatic safeguards:

1. **🔍 Pre-flight Checks**:
   - Verifies local database is current
   - Tests Railway connectivity
   - Checks for conflicts

2. **📦 Automatic Backup**:
   - Creates Railway backup before changes
   - Saved as `backup_railway_YYYYMMDD_HHMMSS.sql`

3. **📋 Preview & Confirmation**:
   - Shows exactly what migrations will run
   - Requires explicit "yes" confirmation

4. **🚀 Safe Deployment**:
   - Applies migrations to Railway
   - Verifies post-deployment sync

5. **✅ Verification**:
   - Confirms both environments match
   - Reports any issues

### **Emergency Procedures**

#### **Railway Connection Issues**
```bash
# Test Railway connectivity
python scripts/multi_env_schema_sync.py --test-connections

# Check Railway status specifically
SYNC_RAILWAY=true alembic current
```

#### **Schema Rollback on Railway**
```bash
# Restore from backup (if needed)
psql postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway < backup_railway_20251211_143022.sql

# Reset to specific migration
SYNC_RAILWAY=true alembic downgrade <revision_id>
```

#### **Force Sync Railway to Local**
```bash
# WARNING: This replaces Railway schema with local
# 1. Backup Railway first
python scripts/multi_env_schema_sync.py --backup railway

# 2. Force sync (advanced users only)
SYNC_RAILWAY=true alembic stamp head
```

## 🔄 Daily Workflow

### When Making Model Changes

1. **Check multi-environment status**:
   ```bash
   python scripts/multi_env_schema_sync.py --status
   ```

2. **Modify SQLAlchemy models** in `app/models/database_models.py`

3. **Create migration**:
   ```bash
   python scripts/schema_workflow.py --create-migration "describe_your_changes"
   ```

4. **Apply locally and test**:
   ```bash
   python scripts/schema_workflow.py --apply-migrations
   ```

5. **Deploy to Railway**:
   ```bash
   # Preview first
   python scripts/multi_env_schema_sync.py --sync-to-railway --dry-run
   
   # Deploy when ready
   python scripts/multi_env_schema_sync.py --sync-to-railway
   ```

### Before Deploying

1. **Run pre-commit check**:
   ```bash
   python scripts/schema_workflow.py --pre-commit
   ```

2. **Check environment sync**:
   ```bash
   python scripts/multi_env_schema_sync.py --status
   ```

3. **Create Railway backup** (automatic with sync tool)

4. **Deploy with confidence**! 🚀

## 🚨 Common Scenarios

### Adding a New Table

1. **Create SQLAlchemy model** in `database_models.py`:
   ```python
   class NewTable(Base):
       __tablename__ = 'new_table'
       
       id = Column(Integer, primary_key=True)
       name = Column(String(255), nullable=False)
       created_at = Column(DateTime(timezone=True), default=func.now())
   ```

2. **Generate and apply migration locally**:
   ```bash
   python scripts/schema_workflow.py --create-migration "add_new_table"
   python scripts/schema_workflow.py --apply-migrations
   ```

3. **Deploy to Railway**:
   ```bash
   python scripts/multi_env_schema_sync.py --sync-to-railway
   ```

### **🌍 NEW: Initial Railway Setup**

If your Railway database doesn't have migrations initialized:

```bash
# Step 1: Initialize Railway with baseline
SYNC_RAILWAY=true alembic stamp head

# Step 2: Verify sync
python scripts/multi_env_schema_sync.py --status
```

### **🌍 NEW: Catching Up Railway Database**

If Railway is behind (like your current situation):

```bash
# Step 1: Check what's different  
python scripts/multi_env_schema_sync.py --status

# Step 2: Preview deployment
python scripts/multi_env_schema_sync.py --sync-to-railway --dry-run

# Step 3: Deploy all missing changes
python scripts/multi_env_schema_sync.py --sync-to-railway
```

### **🌍 NEW: Team Member Onboarding**

New team member setting up local environment:

```bash
# Step 1: Clone repo and set up local database
# Step 2: Sync local to match Railway production
python scripts/multi_env_schema_sync.py --sync-from-railway

# Step 3: Verify everything matches
python scripts/multi_env_schema_sync.py --status
```

### **🌍 NEW: Environment Drift Detection**

Weekly health check:

```bash
# Check if environments have drifted apart
python scripts/multi_env_schema_sync.py --status

# If issues detected, investigate and sync
python scripts/multi_env_schema_sync.py --sync-to-railway --dry-run
```

### Adding a Column

1. **Add column to model**:
   ```python
   class ExistingTable(Base):
       # ... existing columns ...
       new_column = Column(String(100), nullable=True)
   ```

2. **Create migration**:
   ```bash
   python scripts/schema_workflow.py --create-migration "add_new_column_to_existing_table"
   ```

3. **Deploy to both environments**:
   ```bash
   # Local first
   python scripts/schema_workflow.py --apply-migrations
   
   # Then Railway
   python scripts/multi_env_schema_sync.py --sync-to-railway
   ```

### Modifying Column Types

1. **Update model**:
   ```python
   # Change from String(100) to String(255)
   name = Column(String(255), nullable=False)
   ```

2. **Generate migration** (Alembic will detect the type change):
   ```bash
   python scripts/schema_workflow.py --create-migration "increase_name_column_length"
   ```

3. **Deploy safely**:
   ```bash
   # Test locally first
   python scripts/schema_workflow.py --apply-migrations
   
   # Preview Railway changes
   python scripts/multi_env_schema_sync.py --sync-to-railway --dry-run
   
   # Deploy to Railway  
   python scripts/multi_env_schema_sync.py --sync-to-railway
   ```

### Handling Data Migrations

For complex changes requiring data transformation:

1. **Create empty migration**:
   ```bash
   alembic revision -m "data_migration_description"
   ```

2. **Edit migration file** to include data transformation logic:
   ```python
   def upgrade():
       # Schema changes
       op.add_column('table_name', sa.Column('new_column', sa.String(255)))
       
       # Data migration
       connection = op.get_bind()
       connection.execute(text("UPDATE table_name SET new_column = 'default_value'"))
   ```

3. **Deploy with extra caution**:
   ```bash
   # Test locally thoroughly
   python scripts/schema_workflow.py --apply-migrations
   
   # Create manual Railway backup
   python scripts/multi_env_schema_sync.py --backup railway
   
   # Deploy with confirmation
   python scripts/multi_env_schema_sync.py --sync-to-railway
   ```

## 🔧 Troubleshooting

### Schema Out of Sync

If you see schema differences:

```bash
# Check what's different
python scripts/schema_sync_manager.py --report

# Create migration to fix differences
python scripts/schema_workflow.py --sync
```

### **🌍 Environment Synchronization Issues**

#### **Railway Connection Problems**
```bash
# Test connectivity
python scripts/multi_env_schema_sync.py --test-connections

# Check specific Railway status
SYNC_RAILWAY=true alembic current
```

#### **Migration Version Mismatch**
```bash
# Check both environments
python scripts/multi_env_schema_sync.py --status

# If Railway is behind, sync it forward
python scripts/multi_env_schema_sync.py --sync-to-railway

# If local is behind, sync from Railway
python scripts/multi_env_schema_sync.py --sync-from-railway
```

#### **Railway Schema Completely Different**
If Railway has been modified outside of migrations:

1. **Create Railway backup**:
   ```bash
   python scripts/multi_env_schema_sync.py --backup railway
   ```

2. **Reset Railway to match local**:
   ```bash
   # Advanced: Force Railway to local state
   SYNC_RAILWAY=true alembic stamp head
   ```

3. **Deploy current local state**:
   ```bash
   python scripts/multi_env_schema_sync.py --sync-to-railway
   ```

### Migration Conflicts

If you have merge conflicts in migrations:

1. **Reset to clean state**:
   ```bash
   alembic downgrade base
   ```

2. **Merge migration files manually** or delete and recreate

3. **Re-apply migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Sync environments**:
   ```bash
   python scripts/multi_env_schema_sync.py --sync-to-railway
   ```

### Database Schema Drift

If database was modified directly (outside of migrations):

1. **Check differences**:
   ```bash
   python scripts/schema_sync_manager.py --report
   ```

2. **Options**:
   - **Update models** to match database, then create migration
   - **Create migration** to change database to match models
   - **Manual reconciliation** for complex cases

### Model Import Errors

If models fail to import:

```bash
# Validate models
python scripts/schema_workflow.py --validate
```

Common issues:
- **Circular imports**: Restructure relationships
- **Missing foreign keys**: Add proper ForeignKey constraints
- **Invalid column types**: Use supported SQLAlchemy types

## 📋 Best Practices

### Model Design

1. **Always use explicit table names**:
   ```python
   __tablename__ = 'explicit_name'
   ```

2. **Use timezone-aware DateTime**:
   ```python
   created_at = Column(DateTime(timezone=True), default=func.now())
   ```

3. **Add proper indexes**:
   ```python
   __table_args__ = (
       Index('idx_user_email', 'email'),
   )
   ```

4. **Use meaningful constraints**:
   ```python
   __table_args__ = (
       UniqueConstraint('email', name='unique_user_email'),
   )
   ```

### Migration Management

1. **Descriptive migration messages**:
   ```bash
   alembic revision -m "add_user_preferences_table"
   ```

2. **Review generated migrations** before applying

3. **Test migrations** on development database first

4. **Backup before production migrations**

5. **Keep migrations small and focused**

### **🌍 Multi-Environment Best Practices**

1. **Always check environment status** before starting work:
   ```bash
   python scripts/multi_env_schema_sync.py --status
   ```

2. **Use dry-run for production previews**:
   ```bash
   python scripts/multi_env_schema_sync.py --sync-to-railway --dry-run
   ```

3. **Create backups before major changes**:
   ```bash
   python scripts/multi_env_schema_sync.py --backup railway
   ```

4. **Coordinate with team** on schema changes

5. **Deploy during low-traffic periods**

6. **Monitor Railway after deployments**

### Development Workflow

1. **Check schema status** before starting work:
   ```bash
   python scripts/schema_workflow.py --status
   ```

2. **Create feature branch** for schema changes

3. **Include migrations** in pull requests

4. **Run pre-commit checks**:
   ```bash
   python scripts/schema_workflow.py --pre-commit
   ```

5. **🌍 Verify environment sync** before merging:
   ```bash
   python scripts/multi_env_schema_sync.py --status
   ```

## 🚀 Advanced Features

### Multiple Environments

Configure different database URLs for different environments:

```python
# In alembic/env.py, already configured:
def get_url():
    if os.getenv("SYNC_RAILWAY") == "true":
        return "postgresql://postgres:password@railway.app:5432/railway"
    else:
        return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rally")
```

### **🌍 Environment-Specific Operations**

```bash
# Run any Alembic command against Railway
SYNC_RAILWAY=true alembic current
SYNC_RAILWAY=true alembic history
SYNC_RAILWAY=true alembic upgrade head

# Run against local (default)
alembic current
alembic history
alembic upgrade head
```

### Custom Migration Templates

Customize `alembic/script.py.mako` for your team's standards.

### Automated Testing

Add to your CI/CD pipeline:

```yaml
# .github/workflows/schema-check.yml
- name: Schema Validation
  run: python scripts/schema_workflow.py --pre-commit

- name: Environment Sync Check
  run: python scripts/multi_env_schema_sync.py --status
```

## 📊 Monitoring

### Regular Health Checks

Run weekly to catch drift:

```bash
# Check overall health
python scripts/schema_workflow.py --status

# Check multi-environment sync
python scripts/multi_env_schema_sync.py --status

# Detailed analysis
python scripts/schema_sync_manager.py --report
```

### **🌍 Production Monitoring**

Monitor Railway deployment health:

```bash
# Check Railway specifically
SYNC_RAILWAY=true alembic current

# Test Railway connectivity
python scripts/multi_env_schema_sync.py --test-connections

# Compare with local
python scripts/multi_env_schema_sync.py --status
```

### Metrics to Track

- Number of pending migrations
- Schema drift incidents
- Migration success rate
- Database backup frequency
- **🌍 Environment synchronization lag**
- **🌍 Railway deployment success rate**

## 🎉 Success! Your Schema is Now Multi-Environment Managed

You now have a robust system for keeping your SQLAlchemy models and database schema in perfect sync **across local and Railway production environments**. The tools will help you:

- **Detect schema changes** automatically
- **Generate migrations** for model changes  
- **Validate consistency** before deployment
- **Handle complex scenarios** with confidence
- **🌍 Deploy safely to Railway production**
- **🌍 Keep environments synchronized**
- **🌍 Coordinate with team members**

**Next Steps:**
1. Try making a small model change and deploying to Railway
2. Add the pre-commit check to your development workflow
3. Set up automated schema validation in CI/CD
4. Train your team on the new multi-environment workflow
5. **🌍 Set up regular environment sync checks**

Happy coding! 🚀 