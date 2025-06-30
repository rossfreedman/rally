# Rally Deployment Scripts

This folder contains all deployment-related scripts for the Rally platform. These scripts provide a safe, structured approach to deploying code from development through staging to production.

## 🏗️ Deployment Workflow

```
feature branch → staging → production
      ↓             ↓          ↓
   local test    staging    production
                  test       deploy
```

## 📁 Scripts Overview

### Core Deployment Scripts

#### `deploy_staging.py`
**Purpose**: Deploy feature branch to staging for testing
**Usage**: `python deployment/deploy_staging.py`
- Merges current feature branch to staging
- Triggers Railway staging deployment
- Runs automated staging tests
- Provides testing checklist

#### `deploy_production.py`
**Purpose**: Deploy staging to production after testing
**Usage**: `python deployment/deploy_production.py`
- Verifies staging tests pass
- Requires explicit confirmation
- Merges staging to main
- Triggers Railway production deployment
- Runs production verification

### Testing Scripts

#### `test_staging_session_refresh.py`
**Purpose**: Test automatic session refresh on staging
**Usage**: `python deployment/test_staging_session_refresh.py`
- Tests database session versioning
- Verifies staging app response
- Validates session refresh logic
- Simulates ETL runs

#### `test_production_session_refresh.py`
**Purpose**: Verify session refresh on production
**Usage**: `python deployment/test_production_session_refresh.py`
- Validates production deployment
- Tests session versioning system
- Verifies ETL integration
- Confirms user experience

### Utility Scripts

#### `pre_deployment_checklist.py`
**Purpose**: Pre-flight checks before any deployment
**Usage**: `python deployment/pre_deployment_checklist.py`
- Checks git status
- Runs local tests
- Validates migrations
- Production readiness check

#### `check_deployment_status.py`
**Purpose**: Check if local changes are deployed
**Usage**: `python deployment/check_deployment_status.py`
- Compares local vs origin
- Shows unpushed commits
- Deployment sync status

#### `milestone.py`
**Purpose**: Comprehensive deployment workflow
**Usage**: `python deployment/milestone.py --branch staging`
- All-in-one deployment tool
- Database sync checking
- Automated backups
- Complete workflow management

## 🚀 Quick Start Guide

### 1. **Deploy Feature to Staging**
```bash
# From your feature branch
python deployment/deploy_staging.py
```

### 2. **Test on Staging**
```bash
# Automated tests
python deployment/test_staging_session_refresh.py

# Manual testing
# Visit https://rally-staging.up.railway.app
# Test key functionality
```

### 3. **Deploy to Production**
```bash
# After staging tests pass
python deployment/deploy_production.py
```

### 4. **Verify Production**
```bash
python deployment/test_production_session_refresh.py
```

## 📋 Deployment Checklist Templates

### Staging Deployment Checklist
- [ ] Feature branch is complete
- [ ] Local tests pass
- [ ] No uncommitted changes
- [ ] Ready for staging testing

**Command**: `python deployment/deploy_staging.py`

### Staging Testing Checklist
- [ ] Automated tests pass
- [ ] Login functionality works
- [ ] Key user workflows function
- [ ] No console errors
- [ ] Mobile functionality works
- [ ] ETL processes work (if applicable)
- [ ] Performance acceptable

### Production Deployment Checklist
- [ ] All staging tests passed
- [ ] Database migrations ready
- [ ] No breaking changes
- [ ] Rollback plan ready
- [ ] Off-hours deployment (for major changes)

**Command**: `python deployment/deploy_production.py`

## 🗄️ Database Migrations

### Staging-First Migration Workflow
```bash
# 1. Create migration file
migrations/add_new_feature.sql

# 2. Apply to staging
psql "staging_db_url" -f migrations/add_new_feature.sql

# 3. Deploy code to staging
python deployment/deploy_staging.py

# 4. Test thoroughly on staging

# 5. Apply to production
psql "production_db_url" -f migrations/add_new_feature.sql

# 6. Deploy to production
python deployment/deploy_production.py
```

## 🛡️ Safety Features

### Pre-deployment Validation
- Git status checks
- Uncommitted changes detection
- Local test execution
- Migration file detection

### Staging Protection
- Automated test execution
- Manual testing checklists
- Deployment verification
- Rollback preparation

### Production Protection
- Explicit confirmation required
- Staging test verification
- Database migration checks
- Post-deployment monitoring

## 🔧 Environment Configuration

### Railway Environments
- **Staging**: Deploys from `staging` branch
  - URL: `https://rally-staging.up.railway.app`
  - Database: Staging database (copy of production)
  
- **Production**: Deploys from `main` branch
  - URL: `https://rally.up.railway.app`
  - Database: Production database (live user data)

## 📊 Monitoring and Rollback

### Post-deployment Monitoring
- Error rate monitoring
- User feedback tracking
- Performance metrics
- Functionality verification

### Emergency Rollback
```bash
# If issues arise in production
git checkout main
git revert <problematic-commit>
git push origin main
# Apply database rollback if needed
```

## 🎯 Best Practices

1. **Always test on staging first** - Never deploy directly to production
2. **Use automated tests** - Run verification scripts after every deployment
3. **Database migrations** - Always test on staging before production
4. **Monitor after deployment** - Watch for errors and user issues
5. **Keep rollback ready** - Have a plan to revert if needed

## 📞 Support

If you encounter issues with deployments:

1. Check the script output for error messages
2. Verify Railway environment status
3. Run the appropriate test script
4. Check git status and branch state
5. Review recent commits for breaking changes

## 🔄 Continuous Improvement

These scripts are designed to evolve. As Rally grows, consider adding:
- Automated testing in CI/CD
- Blue-green deployments
- Feature flag deployments
- Performance monitoring integration
- Slack/email notifications 