# Database Change Workflow Guide

## Overview
This guide outlines the proper workflow for making database changes to the Rally application, ensuring consistency across local, staging, and production environments.

## 🎯 Recommended Workflow: Alembic + Railway CLI

### Step 1: Make Changes Locally

#### Create Alembic Migration
```bash
# Navigate to project root
cd /path/to/rally

# Create new migration
alembic revision -m "Descriptive message about your change"
# Example: alembic revision -m "Add email_verified column to users table"
```

#### Edit Migration File
```python
# Edit the generated file in alembic/versions/
def upgrade() -> None:
    """Add your upgrade logic here"""
    op.add_column('users', 
                  sa.Column('email_verified', sa.Boolean(), 
                           nullable=False, server_default='false'))

def downgrade() -> None:
    """Add your downgrade logic here"""
    op.drop_column('users', 'email_verified')
```

#### Test Migration Locally
```bash
# Apply migration
alembic upgrade head

# Verify your changes work
# Test your application locally

# Test rollback capability
alembic downgrade -1  # Go back one migration
alembic upgrade head  # Apply again
```

### Step 2: Version Control
```bash
# Stage all changes
git add .

# Commit with descriptive message
git commit -m "Add email_verified column to users table

- Add email_verified boolean column with default false
- Include proper rollback in downgrade()
- Migration handles existing users safely"

# Push to repository
git push origin main
```

### Step 3: Deploy to Production

#### Method A: Direct psql (Recommended - Works Now)
```bash
# Switch to production environment
railway environment production
railway service "Rally Production Database"

# Get the public database URL
railway run env | grep DATABASE_PUBLIC_URL

# Run migration using public URL (replace with actual URL)
psql postgresql://postgres:PASSWORD@ballast.proxy.rlwy.net:PORT/railway \
  -f alembic/versions/YOUR_MIGRATION_FILE.py
```

#### Method B: Create SQL Export (Alternative)
```bash
# Generate SQL from Alembic migration
alembic upgrade --sql head > migration.sql

# Run the SQL file
psql postgresql://[PUBLIC_URL] -f migration.sql
```

#### Method C: Railway Alembic (When Working)
```bash
# This should work but currently has hostname issues
railway run alembic upgrade head
```

### Step 4: Verify Production
```bash
# Check migration was applied
railway run psql $DATABASE_PUBLIC_URL -c "\d your_table"

# Verify application works
# Test the affected functionality on live site
```

## 🚨 Emergency Rollback

If something goes wrong:

```bash
# Rollback one migration
railway run psql $DATABASE_PUBLIC_URL -c "
  UPDATE alembic_version SET version_num = 'PREVIOUS_VERSION_ID';
"

# Then run the downgrade SQL manually
# Or use Alembic if working:
railway run alembic downgrade -1
```

## 📝 Best Practices

### Migration Files
- **Always include downgrade()** logic for rollbacks
- **Use descriptive commit messages** that explain the change
- **Test both upgrade and downgrade** locally before deploying
- **Handle existing data** safely (use nullable=True or server_default)
- **Create indexes with IF NOT EXISTS** to avoid conflicts

### Example Migration Template
```python
def upgrade() -> None:
    """Add email_verified column to users table"""
    # Check if column already exists (safety check)
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'email_verified'
        )
    """))
    column_exists = result.fetchone()[0]
    
    if not column_exists:
        op.add_column('users', 
                      sa.Column('email_verified', sa.Boolean(), 
                               nullable=False, server_default='false'))
        print("✅ Added email_verified column")
    else:
        print("✅ email_verified column already exists")

def downgrade() -> None:
    """Remove email_verified column from users table"""
    op.drop_column('users', 'email_verified')
```

### Common Patterns
```python
# Adding a new table
op.create_table('new_table',
    sa.Column('id', sa.Integer(), primary_key=True),
    sa.Column('name', sa.String(255), nullable=False),
    sa.Column('created_at', sa.DateTime(), default=func.now())
)

# Adding an index
op.create_index('idx_users_email_verified', 'users', ['email_verified'])

# Adding a foreign key
op.add_column('posts', 
              sa.Column('user_id', sa.Integer(), 
                       sa.ForeignKey('users.id')))

# Data migration
op.execute("UPDATE users SET email_verified = true WHERE email LIKE '%@verified.com'")
```

## 🔧 Troubleshooting

### Common Issues
1. **"Column already exists"** - Add existence checks in migrations
2. **"Internal hostname error"** - Use DATABASE_PUBLIC_URL instead of DATABASE_URL
3. **"Migration not found"** - Make sure migration file is committed and synced
4. **"Permission denied"** - Check Railway authentication and environment

### Debugging Commands
```bash
# Check current migration status
alembic current

# See migration history
alembic history

# Check Railway connection
railway status

# View database structure
railway run psql $DATABASE_PUBLIC_URL -c "\dt"  # List tables
railway run psql $DATABASE_PUBLIC_URL -c "\d table_name"  # Describe table
```

## 📚 Reference

### Useful Commands
- `alembic revision -m "message"` - Create new migration
- `alembic upgrade head` - Apply all pending migrations
- `alembic downgrade -1` - Rollback one migration
- `alembic current` - Show current migration
- `alembic history` - Show migration history
- `railway environment production` - Switch to production
- `railway run env | grep DATABASE` - Show database URLs

### File Locations
- **Migrations**: `alembic/versions/`
- **Alembic Config**: `alembic.ini`
- **Database Models**: `app/models/database_models.py`

## 🎯 Summary

**For Future Database Changes:**
1. ✅ Use Alembic for all schema changes
2. ✅ Test locally first (upgrade + downgrade)
3. ✅ Commit to version control
4. ✅ Deploy using Railway CLI + psql with public URL
5. ✅ Verify production deployment
6. ✅ Always include rollback capability 