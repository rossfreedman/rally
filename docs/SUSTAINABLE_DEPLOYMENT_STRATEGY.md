# Sustainable Deployment Strategy for Rally (Revised)

## Current Issue
Railway staging is deploying from `main` branch instead of `staging` branch, causing confusion about what's actually deployed where.

## Recommended Long-Term Strategy: **Staging → Production Flow**

### 1. **Three-Environment Strategy** (Best for Rally with real users)

```
feature branches (development)
    ↓ Pull Request
staging branch (pre-production testing)
    ↓ Manual promotion  
main branch (production-ready)
    ↓ Auto-deploy
Railway Production
```

**Why this works better for Rally:**
- ✅ **Safety**: Test everything on staging before production
- ✅ **User Protection**: Real users never see broken features
- ✅ **Confidence**: Deploy to production with certainty
- ✅ **Rollback**: Easy to revert if issues found
- ✅ **Parallel Development**: Multiple features can be tested on staging

### 2. **Environment Setup**

#### **Development Environment**
- **Branch**: Feature branches (`feature/session-refresh`)
- **Database**: Local PostgreSQL
- **Testing**: Local development and testing

#### **Staging Environment** 
- **Branch**: `staging`
- **Auto-deploy**: Yes (from staging branch)
- **Database**: Copy of production (sanitized/recent backup)
- **URL**: `rally-staging.up.railway.app`
- **Purpose**: Final testing before production

#### **Production Environment**
- **Branch**: `main` 
- **Auto-deploy**: Yes (from main branch)
- **Database**: Production data
- **URL**: `rally.up.railway.app`
- **Purpose**: Live user environment

### 3. **Development Workflow**

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/automatic-session-refresh

# 2. Develop and test locally
# ... make changes ...
python scripts/test_session_refresh.py  # Local testing
python deployment/pre_deployment_checklist.py

# 3. Deploy to staging for testing
python deployment/deploy_staging.py
# → Merges to staging and deploys to Railway staging

# 4. Test on staging
python deployment/test_staging_session_refresh.py
# Test manually in browser on staging URL
# Get feedback from users/team if needed

# 5. Deploy to production (when staging tests pass)
python deployment/deploy_production.py
# → Merges staging to main and deploys to Railway production

# 6. Verify production deployment
python deployment/test_production_session_refresh.py

# 7. Clean up feature branch
git branch -d feature/automatic-session-refresh
```

### 4. **Database Migration Strategy**

```bash
# Staging-first migration workflow
1. Create migration: migrations/add_feature.sql
2. Test locally: psql -d rally -f migrations/add_feature.sql
3. Apply to staging: psql "staging_url" -f migrations/add_feature.sql
4. Deploy code to staging: git push origin staging
5. Test staging thoroughly
6. Apply to production: psql "prod_url" -f migrations/add_feature.sql  
7. Deploy code to production: git push origin main
8. Verify production: python scripts/verify_migration.py
```

### 5. **Risk Management**

#### **Staging Testing Checklist**
- [ ] All automated tests pass
- [ ] Database migrations applied successfully
- [ ] Key user workflows tested manually
- [ ] Performance acceptable
- [ ] No console errors
- [ ] Mobile functionality works
- [ ] ETL processes tested (if applicable)

#### **Production Deployment Checklist**
- [ ] Staging tests passed completely
- [ ] Database migration tested on staging
- [ ] Rollback plan ready
- [ ] Monitoring alerts configured
- [ ] Off-hours deployment (if major change)

### 6. **Automation Scripts**

#### **Deploy to Staging** (`deployment/deploy_staging.py`)
```python
#!/usr/bin/env python3
"""
Deploy feature to staging for testing
"""
def deploy_to_staging(feature_branch):
    check_git_status()
    run_local_tests()
    merge_to_staging(feature_branch)
    apply_staging_migrations()
    run_staging_tests()
    notify_ready_for_testing()
```

#### **Deploy to Production** (`deployment/deploy_production.py`)
```python
#!/usr/bin/env python3
"""
Deploy staging to production after testing
"""
def deploy_to_production():
    verify_staging_tests_passed()
    merge_staging_to_main()
    apply_production_migrations()
    deploy_to_railway()
    run_production_verification()
    notify_deployment_complete()
```

#### **Rollback Script** (`scripts/rollback.py`)
```python
#!/usr/bin/env python3
"""
Emergency rollback script
"""
def rollback():
    revert_to_last_known_good()
    rollback_database_if_needed()
    verify_rollback()
    notify_team()
```

## Immediate Action Plan

### Phase 1: Fix Railway Environment Configuration
1. **Configure Railway Staging**: Deploy from `staging` branch
2. **Configure Railway Production**: Deploy from `main` branch  
3. **Verify environments are separate**: Different databases, URLs

### Phase 2: Establish Workflow
1. **Update git branching**: Use `staging` for pre-production
2. **Create deployment scripts**: Automate staging/production flow
3. **Document process**: Clear steps for all future development

### Phase 3: Test the New Workflow
1. **Test with small change**: Deploy something minor to staging first
2. **Verify staging testing**: Make sure everything works as expected
3. **Deploy to production**: Complete the full workflow

## Decision Matrix

| Approach | Safety | Speed | Complexity | Best For |
|----------|--------|-------|------------|----------|
| Direct to Production | Low | Fast | Low | Solo dev, low risk |
| Staging → Production | High | Medium | Medium | **Real users, Rally** |
| Feature Flags | High | Fast | High | Large teams |

## Recommendation for Rally

**Use Staging → Production Flow:**

1. **Feature branches** → **staging** (testing)
2. **staging** → **main** (production deployment)
3. **Database migrations** applied staging-first
4. **Comprehensive testing** on staging
5. **Automated verification** on production

This provides the right balance of safety and development speed for an application with real users.

## Migration Path from Current State

```bash
# Step 1: Configure Railway environments properly
# Production: Deploy from main branch
# Staging: Deploy from staging branch

# Step 2: Sync current state
git checkout staging
git reset --hard main  # Make staging match main
git push --force-with-lease origin staging

# Step 3: Use new workflow going forward
# All future development: feature → staging → main → production
```

### Benefits of This Approach:

✅ **User Safety**: Never deploy broken code to production  
✅ **Testing Confidence**: Full environment testing before deployment  
✅ **Parallel Development**: Multiple features can be tested  
✅ **Easy Rollback**: Clear revert path if issues arise  
✅ **Database Safety**: Migrations tested before production  
✅ **Team Collaboration**: Others can test on staging  

This strategy prevents production issues while maintaining development velocity. 