# 🚀 Comprehensive Staging Deployment Guide

## Overview

This guide covers the complete staging deployment process for the Rally platform, including all ETL processes, scrapers, and database schema updates.

## 🎯 What's New in This Deployment

### 1. **Modular ETL Structure**
- **New Structure**: Reorganized ETL scripts into modular components
- **Master ETL**: `data/etl/database_import/master_etl.py` orchestrates all imports
- **Individual Scripts**: 
  - `import_players.py` - Player data import
  - `import_match_scores.py` - Match results import
  - `import_schedules.py` - Schedule import
  - `import_stats.py` - Statistics import

### 2. **Enhanced Scrapers**
- **Incremental Scraping**: `scrape_match_scores_incremental.py` for efficient updates
- **Stealth Browser**: `stealth_browser.py` for improved scraping reliability
- **Player Scraping**: `scrape_players.py` for targeted player data collection

### 3. **Database Schema Updates**
- **New Models**: Updated SQLAlchemy models with enhanced relationships
- **User Context**: Dynamic user context for multi-league/multi-team users
- **Group System**: Complete group management system
- **Lineup Escrow**: Fair lineup disclosure system
- **Pickup Games**: Casual match organization system

### 4. **Staging Automation**
- **Cron Jobs**: Automated ETL processes every 30 minutes
- **Health Checks**: Comprehensive validation and monitoring
- **Backup System**: Automatic staging database backups

## 🚀 Quick Deployment

### Option 1: Automated Deployment (Recommended)
```bash
# Run the comprehensive deployment script
python scripts/deploy_staging_comprehensive.py
```

This script will:
1. ✅ Backup current staging database
2. ✅ Update database schema
3. ✅ Validate ETL processes
4. ✅ Update scrapers
5. ✅ Update cron jobs
6. ✅ Deploy to staging
7. ✅ Validate deployment
8. ✅ Test ETL processes

### Option 2: Manual Deployment
```bash
# 1. Commit all changes
git add -A
git commit -m "deploy | Update ETL structure and database schema"

# 2. Deploy to staging
git checkout staging
git merge main
git push origin staging

# 3. Test ETL on staging
python data/etl/database_import/master_etl.py --environment staging
```

## 📋 Detailed Deployment Steps

### Step 1: Pre-Deployment Checklist

#### Verify Local Environment
```bash
# Check all required files exist
ls -la data/etl/database_import/
ls -la data/etl/scrapers/
ls -la chronjobs/

# Test ETL scripts locally
python data/etl/database_import/master_etl.py --environment staging --test-only
```

#### Database Schema Validation
```bash
# Check for pending migrations
alembic current
alembic history

# Validate models
python -c "from app.models.database_models import Base; print('✅ Models loaded successfully')"
```

### Step 2: Staging Database Preparation

#### Backup Current Staging
```bash
# Create backup
pg_dump "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway" > backups/staging_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Apply Schema Updates
```bash
# Apply any pending migrations
alembic upgrade head

# Verify schema
python scripts/validate_staging_schema.py
```

### Step 3: Deploy Application

#### Push to Staging Branch
```bash
# Switch to staging branch
git checkout staging

# Merge latest changes
git merge main

# Push to trigger deployment
git push origin staging
```

#### Monitor Deployment
```bash
# Check deployment status
railway status --environment staging

# Monitor logs
railway logs --environment staging
```

### Step 4: Test ETL Processes

#### Run Master ETL
```bash
# Test ETL on staging
python data/etl/database_import/master_etl.py --environment staging

# Run full import if needed
python data/etl/database_import/master_etl.py --environment staging --full-import
```

#### Validate Results
```bash
# Check data integrity
python scripts/validate_staging_data.py

# Test scrapers
python data/etl/scrapers/scrape_players.py --test-only
```

### Step 5: Verify Functionality

#### Health Checks
```bash
# Test staging URL
curl https://rally-staging.up.railway.app/health

# Test key endpoints
curl https://rally-staging.up.railway.app/api/health
```

#### Manual Testing
1. **User Registration**: Test new user signup
2. **League Switching**: Test multi-league functionality
3. **Team Management**: Test team switching and context
4. **ETL Processes**: Test data import and updates
5. **Mobile Interface**: Test mobile-specific features

## 🔧 Configuration Files

### Railway Configuration (`railway.toml`)
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn server:app"
healthcheckPath = "/health"
healthcheckTimeout = 300

[[cron]]
command = "python chronjobs/railway_cron_etl_staging.py"
schedule = "*/30 * * * *"

[[cron]]
command = "python chronjobs/railway_cron_etl_staging.py --full-import"
schedule = "0 */6 * * *"
```

### Environment Variables
```bash
# Staging Environment
FLASK_ENV=staging
DEBUG=True
DATABASE_URL=postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway
RAILWAY_ENVIRONMENT=staging
```

## 📊 Monitoring and Validation

### ETL Monitoring
```bash
# Check ETL logs
tail -f logs/master_etl.log

# Monitor cron job execution
railway logs --environment staging | grep "cron"
```

### Data Validation
```bash
# Check table counts
python scripts/check_staging_data_counts.py

# Validate relationships
python scripts/validate_staging_relationships.py
```

### Performance Monitoring
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://rally-staging.up.railway.app/

# Monitor database performance
python scripts/monitor_staging_performance.py
```

## 🚨 Troubleshooting

### Common Issues

#### ETL Import Failures
```bash
# Check database connection
python scripts/test_staging_connection.py

# Verify JSON data files
ls -la data/leagues/all/

# Test individual import scripts
python data/etl/database_import/import_players.py --test-only
```

#### Schema Migration Issues
```bash
# Check migration status
alembic current --url "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

# Reset migrations if needed
alembic stamp head --url "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
```

#### Deployment Failures
```bash
# Check Railway status
railway status --environment staging

# View deployment logs
railway logs --environment staging --tail 100

# Restart deployment if needed
railway up --environment staging
```

### Rollback Procedures

#### Database Rollback
```bash
# Restore from backup
psql "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway" < backups/staging_backup_YYYYMMDD_HHMMSS.sql
```

#### Application Rollback
```bash
# Revert to previous commit
git checkout staging
git reset --hard HEAD~1
git push origin staging --force
```

## 📈 Success Metrics

### Deployment Success Indicators
- ✅ All ETL scripts execute without errors
- ✅ Database schema matches expected structure
- ✅ Application responds to health checks
- ✅ User registration and login work
- ✅ League switching functionality works
- ✅ Mobile interface functions properly
- ✅ Cron jobs execute successfully

### Performance Benchmarks
- **Page Load Times**: < 3 seconds for main pages
- **ETL Duration**: < 10 minutes for full import
- **Database Queries**: < 1 second for standard queries
- **API Response**: < 500ms for API endpoints

## 🔄 Maintenance

### Regular Tasks
- **Weekly**: Refresh staging data from production
- **Monthly**: Review and cleanup staging backups
- **Quarterly**: Update staging environment configuration

### Monitoring Alerts
- ETL job failures
- Database connection issues
- High response times
- Schema validation failures

## 📞 Support

For issues with staging deployment:
1. Check logs in `logs/staging_deployment.log`
2. Review Railway deployment status
3. Test individual components
4. Consult this guide for troubleshooting steps

---

**Last Updated**: January 2025  
**Version**: 2.0  
**Environment**: Staging 